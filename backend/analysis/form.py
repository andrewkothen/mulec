"""Suggest bar-aligned form from changes and recurrences in the recording."""

import librosa
import numpy as np
from scipy.signal import find_peaks, resample_poly

from backend.models import Measure


def _normalize(values):
    return values / np.maximum(np.linalg.norm(values, axis=1, keepdims=True), 1e-6)


def _bar_features(samples, rate, measures, origin):
    # One shared spectrum supplies both harmonic and timbral evidence.
    samples = resample_poly(samples, 1, 2)
    hop, fft = 512, 2048
    rate /= 2
    power = np.abs(librosa.stft(samples, n_fft=fft, hop_length=hop)) ** 2
    mel = librosa.feature.melspectrogram(S=power, sr=rate, n_fft=fft, n_mels=48)
    timbre = librosa.feature.mfcc(S=librosa.power_to_db(mel), n_mfcc=14)
    chroma = librosa.feature.chroma_stft(S=power, sr=rate, n_fft=fft, tuning=0)
    start, end = np.rint(
        (np.array([(bar.start, bar.end) for bar in measures]).T - origin) * rate / hop
    ).astype(int)
    start = np.clip(start, 0, power.shape[1] - 1)
    end = np.clip(end, start + 1, power.shape[1])

    def per_bar(features):
        integral = np.pad(np.cumsum(features, axis=1, dtype=np.float64), ((0, 0), (1, 0)))
        return ((integral[:, end] - integral[:, start]) / (end - start)).T

    bars = per_bar(timbre)
    bars = (bars - np.median(bars, axis=0)) / np.maximum(bars.std(axis=0), 1e-6)
    return _normalize(bars), _normalize(per_bar(chroma))


def _section_starts(similarity):
    count = len(similarity)
    novelty = np.zeros(count)
    # Contrast within either side of a boundary with the cross-boundary block.
    for half in (2, 4, 8):
        for i in range(half, count - half + 1):
            before = slice(i - half, i)
            after = slice(i, i + half)
            novelty[i] += (
                similarity[before, before].mean()
                + similarity[after, after].mean()
                - 2 * similarity[before, after].mean()
            ) / 3
    peaks, _ = find_peaks(novelty, distance=6, prominence=0.29)
    boundaries = [int(i) for i in peaks if 4 <= i <= count - 4]
    starts = [0]
    for end in [*boundaries, count]:
        while end - starts[-1] > 24:
            # Keep the reading view usable through a long passage with few changes.
            lower = starts[-1] + 12
            upper = min(starts[-1] + 24, end - 8)
            starts.append(lower + int(np.argmax(novelty[lower : upper + 1])) if upper >= lower else lower)
        if end < count:
            starts.append(end)
    return starts


def _match(first, second, timbre, chroma):
    a, b = first
    c, d = second
    longest = max(b - a, d - c)
    best = 0.0
    for shift in range(-2, 3):
        left, right = a + max(0, -shift), c + max(0, shift)
        length = min(b - left, d - right)
        if length < 4 or length / longest < 0.75:
            continue
        rows, cols = np.arange(left, left + length), np.arange(right, right + length)
        harmony = chroma[rows, cols].mean()
        texture = timbre[rows, cols].mean()
        if harmony >= 0.88 and texture >= 0.35:
            best = max(best, (0.6 * harmony + 0.4 * texture) * length / longest)
    return best


def suggest_sections(samples, rate, measures: list[Measure], origin=0.0) -> dict[str, str]:
    """Return suggested section labels keyed by the first bar of each occurrence."""
    if len(measures) < 8 or len(samples) < 2 * rate or np.max(np.abs(samples)) < 1e-5:
        return {}
    timbre, chroma = _bar_features(samples, rate, measures, origin)
    timbre_similarity, chroma_similarity = timbre @ timbre.T, chroma @ chroma.T
    starts = _section_starts(0.64 * timbre_similarity + 0.36 * chroma_similarity)
    representatives = []
    labels = {}
    for start, end in zip(starts, [*starts[1:], len(measures)]):
        segment = (start, end)
        matches = [_match(segment, prior, timbre_similarity, chroma_similarity) for prior in representatives]
        if matches and max(matches) > 0:
            group = int(np.argmax(matches))
        else:
            group = len(representatives)
            representatives.append(segment)
        labels[measures[start].id] = chr(65 + group) if group < 26 else f"Section {group + 1}"
    return labels
