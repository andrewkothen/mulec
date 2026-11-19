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


def group_sections(starts, timbre, chroma):
    """Compare complete contours at different lengths, independent of instrumentation."""
    count = len(timbre)
    segments = list(zip(starts, [*starts[1:], count]))
    representatives, groups = [], []
    for a, b in segments:
        scores = []
        for c, d in representatives:
            # A local alignment tolerates stretched phrases while requiring coverage
            # of both passages. Similar key alone is insufficient.
            distance = 1 - chroma[a:b] @ chroma[c:d].T
            band = np.abs(np.linspace(0, 1, b - a)[:, None] - np.linspace(0, 1, d - c)[None, :]) <= 0.18
            allowed = np.where(band, distance, np.inf)
            similarity = 1 - (allowed.min(axis=0).mean() + allowed.min(axis=1).mean()) / 2
            texture = float(np.mean(timbre[a:b], axis=0) @ np.mean(timbre[c:d], axis=0))
            scores.append(similarity if similarity >= 0.93 and texture > -0.2 else 0)
        if scores and max(scores) > 0:
            group = int(np.argmax(scores))
        else:
            group = len(representatives)
            representatives.append((a, b))
        groups.append(group)
    return groups


def suggest_sections(samples, rate, measures: list[Measure], origin=0.0, *, existing=False) -> dict[str, str]:
    """Return suggested section labels keyed by the first bar of each occurrence."""
    if len(measures) < 8 or len(samples) < 2 * rate or np.max(np.abs(samples)) < 1e-5:
        return {}
    timbre, chroma = _bar_features(samples, rate, measures, origin)
    timbre_similarity, chroma_similarity = timbre @ timbre.T, chroma @ chroma.T
    starts = (
        [i for i, measure in enumerate(measures) if i == 0 or measure.section.strip()]
        if existing
        else _section_starts(0.64 * timbre_similarity + 0.36 * chroma_similarity)
    )
    groups = group_sections(starts, timbre, chroma)
    labels = {}
    names = {}
    for start, group in zip(starts, groups):
        name = measures[start].section.strip()
        automatic = (len(name) == 1 and name.isupper()) or name.startswith("Section ")
        if group not in names:
            names[group] = (
                name
                if existing and name and not automatic
                else chr(65 + group)
                if group < 26
                else f"Section {group + 1}"
            )
        labels[measures[start].id] = names[group]
    return labels
