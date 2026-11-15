"""Optional pYIN monophonic guide; never claims source separation."""

import librosa
import numpy as np

from backend.models import Note
from backend.music.theory import quantize, seconds_to_beat


def extract_melody(y, sr, start, measures, sensitivity):
    sample = librosa.resample(y, orig_sr=sr, target_sr=8000)
    f0, voiced, probability = librosa.pyin(
        sample, sr=8000, fmin=80, fmax=1200, frame_length=1024, hop_length=256
    )
    pitches = np.where(
        voiced & (probability >= sensitivity), np.rint(librosa.hz_to_midi(np.nan_to_num(f0, nan=440))), -1
    ).astype(int)
    times = librosa.frames_to_time(np.arange(len(pitches) + 1), sr=8000, hop_length=256) + start
    changes = np.r_[0, np.flatnonzero(np.diff(pitches)) + 1, len(pitches)]
    for a, b in zip(changes, changes[1:]):
        if pitches[a] < 0 or times[b] - times[a] < 0.09:
            continue
        for measure in measures:
            left, right = max(times[a], measure.start), min(times[b], measure.end)
            if right <= left:
                continue
            q = measure.meter.quarters
            beat = max(0, quantize(seconds_to_beat(left, measure.start, measure.end, q)))
            stop = min(q, quantize(seconds_to_beat(right, measure.start, measure.end, q)))
            previous_end = max((n.beat + n.duration for n in measure.notes), default=0)
            beat = max(beat, previous_end)
            if stop > beat:
                measure.notes.append(
                    Note(
                        beat=beat,
                        duration=stop - beat,
                        midi=int(pitches[a]),
                        confidence=round(float(np.mean(probability[a:b])), 3),
                    )
                )
