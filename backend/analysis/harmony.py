"""Conservative chroma template matching with transition smoothing.

Template vocabulary deliberately favors triads and sevenths. Extensions and
alterations remain editable but are not guessed from mixed audio.
"""
from dataclasses import dataclass

import librosa
import numpy as np

from backend.models import Chord
from backend.music.theory import FLATS, quantize

QUALITIES = {"": [0, 4, 7], "m": [0, 3, 7], "7": [0, 4, 7, 10],
             "maj7": [0, 4, 7, 11], "m7": [0, 3, 7, 10], "m7b5": [0, 3, 6, 10],
             "dim": [0, 3, 6], "dim7": [0, 3, 6, 9], "aug": [0, 4, 8],
             "sus2": [0, 2, 7], "sus4": [0, 5, 7], "add9": [0, 2, 4, 7]}
MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


@dataclass
class HarmonicFeatures:
    chroma: np.ndarray
    times: np.ndarray
    rms: np.ndarray
    key: str
    mode: str
    confidence: float


def extract_features(y, sr: int, start: float) -> HarmonicFeatures:
    harmonic = librosa.effects.harmonic(y, margin=3)
    chroma = librosa.feature.chroma_stft(y=harmonic, sr=sr, n_fft=4096, hop_length=512)
    rms = librosa.feature.rms(y=y, frame_length=4096, hop_length=512)[0]
    times = librosa.frames_to_time(np.arange(chroma.shape[1]), sr=sr, hop_length=512) + start
    average = np.mean(chroma, axis=1)
    scores = []
    for mode, profile in (("major", MAJOR), ("minor", MINOR)):
        for root in range(12):
            correlation = np.corrcoef(average, np.roll(profile, root))[0, 1]
            scores.append((float(np.nan_to_num(correlation)), root, mode))
    scores.sort(reverse=True)
    best, second = scores[:2]
    confidence = float(np.clip((best[0] - second[0]) * 3, 0, 0.9))
    return HarmonicFeatures(chroma, times, rms, FLATS[best[1]], best[2], confidence)


def estimate_chords(features: HarmonicFeatures, start: float, end: float, quarters: float) -> list[Chord]:
    templates, names, penalties = [], [], []
    for root in range(12):
        for quality, intervals in QUALITIES.items():
            vector = np.zeros(12)
            vector[(np.array(intervals) + root) % 12] = 1
            templates.append(vector / np.linalg.norm(vector))
            names.append(FLATS[root] + quality)
            penalties.append(0.035 if len(intervals) > 3 else 0)
    matrix = np.array(templates)
    # Half-quarter windows permit changes between beats; duplicates collapse.
    beat_offsets = np.arange(0, quarters, 0.5)
    emissions, strengths = [], []
    for beat in beat_offsets:
        a = start + (end - start) * beat / quarters
        b = min(end, a + (end - start) * 0.5 / quarters)
        mask = (features.times >= a) & (features.times < b)
        vector = np.mean(features.chroma[:, mask], axis=1) if mask.any() else np.zeros(12)
        vector = np.maximum(vector - np.max(vector) * 0.15, 0)
        vector /= max(np.linalg.norm(vector), 1e-10)
        emissions.append(matrix @ vector - np.array(penalties))
        strengths.append(float(np.mean(features.rms[:len(features.times)][mask])) if mask.any() else 0)
    scores = np.array(emissions)
    # Viterbi cost discourages transient changes without forcing a genre progression.
    costs = scores[0].copy()
    back = []
    transition = np.full((len(names), len(names)), -0.12)
    np.fill_diagonal(transition, 0)
    for score in scores[1:]:
        candidates = costs[:, None] + transition
        back.append(np.argmax(candidates, axis=0))
        costs = score + np.max(candidates, axis=0)
    states = [int(np.argmax(costs))]
    for pointer in reversed(back):
        states.append(int(pointer[states[-1]]))
    states.reverse()
    events = []
    for i, state in enumerate(states):
        ranked = np.sort(scores[i])
        confidence = float(np.clip((scores[i, state] - 0.45) * 0.9 + (ranked[-1] - ranked[-2]) * 2, 0, 0.9))
        silent = strengths[i] < 0.004
        symbol = "N.C." if silent or scores[i, state] < 0.5 else names[state]
        confidence = 0.0 if silent else confidence
        if not events or events[-1].symbol != symbol:
            events.append(Chord(beat=float(quantize(beat_offsets[i])), symbol=symbol,
                                confidence=round(confidence, 3)))
    return events
