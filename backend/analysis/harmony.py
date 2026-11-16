"""Conservative harmony from harmonic CQT, with cross-bar smoothing.

A template match is evidence, not a verified chord. Unsupported/ambiguous
voicings become '?' instead of a fabricated chord or a false N.C. marking.
"""

from dataclasses import dataclass
import librosa
import numpy as np

from backend.models import Chord, Measure
from backend.music.theory import FLATS, SHARPS, conventional_key, notation_key, pitch_class

QUALITIES = {
    "": [0, 4, 7],
    "m": [0, 3, 7],
    "7": [0, 4, 7, 10],
    "maj7": [0, 4, 7, 11],
    "m7": [0, 3, 7, 10],
    "m7b5": [0, 3, 6, 10],
    "dim": [0, 3, 6],
    "dim7": [0, 3, 6, 9],
    "aug": [0, 4, 8],
    "sus2": [0, 2, 7],
    "sus4": [0, 5, 7],
    "add9": [0, 2, 4, 7],
}
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
    # Log-frequency bands resolve bass pitches more evenly than a short FFT.
    chroma = librosa.feature.chroma_cqt(
        y=harmonic,
        sr=sr,
        hop_length=512,
        fmin=librosa.note_to_hz("C2"),
        n_octaves=6,
        tuning=None,
    )
    rms = librosa.feature.rms(y=y, frame_length=4096, hop_length=512)[0]
    times = librosa.frames_to_time(np.arange(chroma.shape[1]), sr=sr, hop_length=512) + start
    average = np.average(chroma, axis=1, weights=np.maximum(rms[: chroma.shape[1]], 1e-8))
    scores = []
    for mode, profile in (("major", MAJOR), ("minor", MINOR)):
        for root in range(12):
            correlation = np.corrcoef(average, np.roll(profile, root))[0, 1]
            scores.append((float(np.nan_to_num(correlation)), root, mode))
    scores.sort(reverse=True)
    best, second = scores[:2]
    confidence = float(np.clip((best[0] - second[0]) * 3, 0, 0.9))
    return HarmonicFeatures(chroma, times, rms, conventional_key(best[1], best[2]), best[2], confidence)


def estimate_chart_chords(
    features: HarmonicFeatures,
    measures: list[Measure],
    known_key: str | None = None,
    known_mode: str = "major",
) -> list[list[Chord]]:
    if not measures:
        return []
    tonic, mode = (known_key, known_mode) if known_key else (features.key, features.mode)
    names = SHARPS if notation_key(tonic, mode).sharps > 0 else FLATS
    scale = {
        (pitch_class(tonic) + n) % 12
        for n in ([0, 2, 4, 5, 7, 9, 11] if mode == "major" else [0, 2, 3, 5, 7, 8, 10])
    }
    templates, symbols, tone_sets, penalties = [], [], [], []
    for root in range(12):
        for quality, intervals in QUALITIES.items():
            tones = (np.array(intervals) + root) % 12
            vector = np.zeros(12)
            vector[tones] = 1
            templates.append(vector / np.linalg.norm(vector))
            symbols.append(names[root] + quality)
            tone_sets.append((root, quality, tones))
            # Weak tonal context breaks close ties, but permits evidenced borrowed chords.
            penalties.append(
                (0.075 if len(intervals) > 3 else 0)
                + 0.08 * sum(int(t) not in scale for t in tones) / len(tones)
            )
    matrix = np.array(templates)
    emissions, supported, strengths, locations = [], [], [], []
    for measure_index, measure in enumerate(measures):
        q = measure.meter.quarters
        half_beat = (measure.end - measure.start) * 0.5 / q
        for beat in np.arange(0, q, 0.5):
            a = measure.start + (measure.end - measure.start) * beat / q
            # A little overlapping context suppresses isolated strum/onset artifacts.
            mask = (features.times >= a - half_beat * 0.25) & (features.times < a + half_beat * 1.25)
            vector = np.median(features.chroma[:, mask], axis=1) if mask.any() else np.zeros(12)
            peak = max(float(np.max(vector)), 1e-10)
            relative = vector / peak
            vector = np.maximum(relative - 0.12, 0)
            vector /= max(np.linalg.norm(vector), 1e-10)
            evidence = []
            for root, quality, tones in tone_sets:
                # A strong single pitch must not become a major-seventh chord.
                core = relative[root] >= 0.18 and relative[tones[1]] >= 0.24 and relative[tones[2]] >= 0.10
                if quality in ("sus2", "sus4", "aug", "dim", "dim7", "m7b5", "add9"):
                    core = bool(np.min(relative[tones]) >= 0.24)
                if len(tones) > 3:
                    core = core and relative[tones[-1]] >= 0.32
                evidence.append(core)
            scores = matrix @ vector - np.array(penalties) - np.where(evidence, 0, 0.22)
            emissions.append(scores)
            supported.append(evidence)
            strengths.append(float(np.mean(features.rms[: len(features.times)][mask])) if mask.any() else 0)
            locations.append((measure_index, float(beat)))
    scores = np.array(emissions)
    # Full-chart Viterbi, O(frames * states); transitions no longer reset each bar.
    costs = scores[0].copy()
    back = []
    for score in scores[1:]:
        best = int(np.argmax(costs))
        switching = costs[best] - 0.24
        stay = costs >= switching
        back.append(np.where(stay, np.arange(len(symbols)), best))
        costs = score + np.where(stay, costs, switching)
    states = [int(np.argmax(costs))]
    for pointer in reversed(back):
        states.append(int(pointer[states[-1]]))
    states.reverse()
    # Assess complete sustained candidates, not each noisy sub-window in isolation.
    # This avoids alternating a chord and '?' on every strum within the same chord.
    accepted = np.zeros(len(states), dtype=bool)
    boundaries = np.r_[0, np.flatnonzero(np.diff(states)) + 1, len(states)]
    for a, b in zip(boundaries, boundaries[1:]):
        state = states[a]
        support = np.mean([supported[i][state] for i in range(a, b)])
        accepted[a:b] = b - a >= 2 and support >= 0.6 and np.median(scores[a:b, state]) >= 0.68
    result: list[list[Chord]] = [[] for _ in measures]
    for i, (measure_index, beat) in enumerate(locations):
        state = states[i]
        ranked = np.sort(scores[i])
        confidence = float(np.clip((scores[i, state] - 0.5) + (ranked[-1] - ranked[-2]) * 2, 0, 0.9))
        if strengths[i] < 0.004:
            symbol, confidence = "N.C.", 0.0
        elif not accepted[i]:
            symbol, confidence = "?", 0.0
        else:
            symbol = symbols[state]
        events = result[measure_index]
        if not events or events[-1].symbol != symbol:
            events.append(Chord(beat=beat, symbol=symbol, confidence=round(confidence, 3)))
        else:
            events[-1].confidence = min(events[-1].confidence, round(confidence, 3))
    return result


def estimate_chords(features: HarmonicFeatures, start: float, end: float, quarters: float) -> list[Chord]:
    from backend.models import Meter

    denominator = 4 if float(quarters).is_integer() else 8
    measure = Measure(
        start=start, end=end, meter=Meter(numerator=int(quarters * denominator / 4), denominator=denominator)
    )
    return estimate_chart_chords(features, [measure])[0]
