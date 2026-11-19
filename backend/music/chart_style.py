"""Shared chart-only typography and jazz shorthand; stored chord symbols stay intact."""

from functools import lru_cache
from pathlib import Path
import re

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def jazz_symbol(symbol: str) -> str:
    text = re.sub(r"^([A-G][b#]?)(?:m7b5|ø7)", r"\1ø7", symbol)
    text = re.sub(r"^([A-G][b#]?)maj", r"\1△", text)
    text = re.sub(r"^([A-G][b#]?)m(?!aj)", r"\1-", text)
    text = text.replace("dim", "°")
    return text.replace("b", "♭").replace("#", "♯")


def chord_changes(chords, previous=None):
    """Hide redundant inferred carries; retain deliberate edits and unresolved events."""
    changes = []
    for chord in sorted(chords, key=lambda event: event["beat"]):
        symbol = chord["symbol"]
        if symbol != previous or chord.get("manual") or symbol in {"?", "NC", "N.C."}:
            changes.append(chord)
        previous = symbol
    return changes


@lru_cache(maxsize=1)
def chart_font():
    path = Path(__file__).resolve().parents[2] / "frontend/public/fonts/MulecJazz.ttf"
    pdfmetrics.registerFont(TTFont("MulecJazz", str(path)))
    pdfmetrics.registerFontFamily("MulecJazz", normal="MulecJazz", bold="MulecJazz", italic="MulecJazz")
    return "MulecJazz"


def beat_label(beat: float, denominator=4) -> str:
    value = beat * denominator / 4 + 1
    return f"{int(value)}&" if value % 1 == 0.5 else f"{value:g}"
