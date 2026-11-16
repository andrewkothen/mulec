"""Optional offline inference using separately installed CPU models."""

from bisect import bisect_right
import json
import logging
import os
from pathlib import Path
import re
import subprocess

import numpy as np

from backend.models import Chord, KeyAlternative, Measure
from backend.music.theory import FLATS, SHARPS, chord_object, conventional_key, notation_key, pitch_class

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / ".tools/harmony"
PYTHON = Path("Scripts/python.exe" if os.name == "nt" else "bin/python")
QUALITIES = {"maj": "", "min": "m", "min7": "m7", "minmaj7": "mM7", "hdim7": "m7b5", "sus4(b7)": "7sus4"}
logger = logging.getLogger(__name__)


def predict(model: str, wave: Path, model_dir: Path) -> list[dict] | None:
    python = model_dir / model / PYTHON
    if not python.exists():
        return None
    try:
        output = subprocess.run(
            [str(python), str(ROOT / "scripts/harmony_model.py"), model, str(wave.resolve())],
            capture_output=True,
            text=True,
            timeout=420,
            check=True,
        )
        return json.loads(output.stdout) or None
    except (OSError, ValueError, subprocess.SubprocessError):
        logger.exception("Local %s model failed", model)
        return None


def ranked_key(predictions: list[dict]) -> tuple[str, str, float, list[KeyAlternative]]:
    first = predictions[0]
    mode = first["mode"]
    tonic = conventional_key(pitch_class(first["key"]), mode)
    next_score = predictions[1]["score"]
    # Show close alternatives without presenting model scores as calibrated odds.
    alternatives = [
        KeyAlternative(key=conventional_key(pitch_class(other["key"]), other["mode"]), mode=other["mode"])
        for other in predictions[1:3]
        if other["score"] >= first["score"] * 0.55
    ]
    return tonic, mode, round(first["score"] - next_score, 3), alternatives


def chord_symbol(label: str, prefer_sharps: bool) -> str:
    if label in {"N", "X"}:
        return "?"
    root, separator, description = label.partition(":")
    if not separator:
        return "?"
    quality, _, bass = description.partition("/")
    names = SHARPS if prefer_sharps else FLATS
    try:
        pc = pitch_class(root)
        symbol = names[pc] + QUALITIES.get(quality, quality)
        if bass:
            degree = re.fullmatch(r"([b#]?)([1-7])", bass)
            if degree:
                offset = [0, 2, 4, 5, 7, 9, 11][int(degree[2]) - 1]
                bass_pc = (pc + offset + {"b": -1, "": 0, "#": 1}[degree[1]]) % 12
            else:
                bass_pc = pitch_class(bass)
            if bass_pc != pc:
                symbol += "/" + names[bass_pc]
        chord_object(symbol)
    except ValueError:
        return "?"
    return symbol


def align_chords(
    predictions: list[dict], measures: list[Measure], start: float, key: str, mode: str, y, sample_rate: int
) -> list[list[Chord]]:
    prefer_sharps = notation_key(key, mode).sharps > 0
    starts = [s["start_time"] + start for s in predictions]
    ends = [s["end_time"] + start for s in predictions]
    symbols = [chord_symbol(s["chord"], prefer_sharps) for s in predictions]
    result = []
    for measure in measures:
        chords = []
        quarters = measure.meter.quarters
        seconds_per_beat = (measure.end - measure.start) / quarters
        for beat in np.arange(0, quarters, 0.5):
            end = min(beat + 0.5, quarters)
            center = measure.start + (beat + end) / 2 * seconds_per_beat
            i = bisect_right(starts, center) - 1
            symbol = symbols[i] if i >= 0 and center < ends[i] else "?"
            if symbol == "?":
                a = max(0, round((measure.start + beat * seconds_per_beat - start) * sample_rate))
                b = round((measure.start + end * seconds_per_beat - start) * sample_rate)
                if b > a and y[a:b].size and np.max(np.abs(y[a:b])) < 0.004:
                    symbol = "N.C."
            if not chords or chords[-1].symbol != symbol:
                chords.append(Chord(beat=float(beat), symbol=symbol, confidence=None))
        result.append(chords)
    return result
