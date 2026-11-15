"""Original synthetic fixture, generated locally. CC0; no sampled recordings."""
from pathlib import Path

import numpy as np
import soundfile as sf


def make_demo(path: Path, bars: int = 8) -> Path:
    sr, bpm = 22050, 120
    duration = bars * 4 * 60 / bpm
    y = np.zeros(int(sr * duration))
    progression = [[60, 64, 67, 71], [57, 60, 64, 67], [62, 65, 69, 72], [55, 59, 62, 65]]
    rng = np.random.default_rng(17)
    for bar in range(bars):
        for beat in range(4):
            start = int((bar * 2 + beat * 0.5) * sr)
            t = np.arange(int(0.48 * sr)) / sr
            envelope = np.minimum(t / 0.008, 1) * np.exp(-t * 2.5)
            tone = sum(np.sin(2*np.pi*440*2**((midi-69)/12)*t) for midi in progression[bar % 4])
            y[start:start+len(t)] += tone * envelope * 0.13
            click = rng.normal(size=int(sr * 0.02)) * np.exp(-np.arange(int(sr * 0.02)) / 70) * 0.15
            y[start:start+len(click)] += click
    sf.write(path, y, sr)
    return path
