"""Beat evidence with explicit meter/downbeat assumptions."""

from dataclasses import dataclass

import librosa
import numpy as np


@dataclass
class Rhythm:
    bpm: float
    confidence: float
    beats: list[float]
    boundaries: list[float]
    warnings: list[str]


def analyze_rhythm(y, sr: int, start: float, quarters: float, bpm_override: float | None) -> Rhythm:
    duration = len(y) / sr
    envelope = librosa.onset.onset_strength(y=y, sr=sr, hop_length=512)
    tempo, frames = librosa.beat.beat_track(onset_envelope=envelope, sr=sr, hop_length=512, trim=False)
    estimated = float(np.asarray(tempo).reshape(-1)[0])
    detected = librosa.frames_to_time(frames, sr=sr, hop_length=512)
    warnings = [
        "Meter is a user-selected assumption; the first detected beat is treated as the downbeat. Review the grid."
    ]
    if estimated <= 0 or len(detected) < 3:
        bpm = bpm_override or 120.0
        confidence = 0.0
        offset = 0.0
        warnings.append(
            "No reliable pulse detected. A provisional 120 BPM grid is used unless you supplied a tempo."
        )
    else:
        bpm = bpm_override or estimated
        intervals = np.diff(detected)
        regularity = np.clip(1 - np.std(intervals) / max(np.mean(intervals), 1e-6), 0, 1)
        # This is a heuristic confidence, not a calibrated probability.
        confidence = float(regularity * min(1, len(detected) / 16) * 0.8)
        offset = float(detected[0])
    bpm = float(np.clip(bpm, 30, 300))
    if bpm_override or len(detected) < 3:
        beats = np.arange(offset, duration, 60 / bpm)
    else:
        beats = detected[detected < duration]
    if len(beats) < 2:
        beats = np.arange(0, duration, 60 / bpm)
    # Interpolate detected quarter-note positions, preserving rubato in boundaries.
    beat_positions = np.arange(0, max(1, len(beats)), quarters)
    boundaries = list(np.interp(beat_positions, np.arange(len(beats)), beats))
    # Retain the attack/pickup before the first beat instead of silently discarding it.
    boundaries[0] = 0.0
    if duration - boundaries[-1] < 0.15 and len(boundaries) > 1:
        boundaries.pop()
    boundaries.append(duration)
    return Rhythm(
        round(bpm, 2),
        round(confidence, 3),
        [float(b + start) for b in beats],
        [float(b + start) for b in boundaries],
        warnings,
    )
