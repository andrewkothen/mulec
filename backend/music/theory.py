"""Chord parsing and transposition independent of inference."""
import re

from music21 import harmony, pitch

FLATS = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
SHARPS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
ROOT = re.compile(r"^([A-G])([b#]?)(.*)$")


def pitch_class(name: str) -> int:
    if not re.fullmatch(r"[A-G][b#]?", name):
        raise ValueError("Use a note name such as C, F# or Bb")
    return int(pitch.Pitch(name.replace("b", "-")).pitchClass)


def chord_object(symbol: str):
    symbol = symbol.strip().replace("♭", "b").replace("♯", "#")
    if symbol in ("N.C.", "NC"):
        return harmony.NoChord()
    match = ROOT.fullmatch(symbol)
    if not match:
        raise ValueError("Use a chord such as Cmaj7, Dm7, G7b9 or Bb/F")
    root, accidental, suffix = match.groups()
    suffix = suffix.replace("ø", "m7b5").replace("Δ", "maj7")
    suffix = re.sub(r"/([A-G])b$", r"/\1-", suffix)
    # music21 calls half-diminished seventh m7b5 and accepts jazz extensions.
    try:
        return harmony.ChordSymbol(root + accidental.replace("b", "-") + suffix)
    except (ValueError, TypeError, harmony.HarmonyException, pitch.PitchException) as exc:
        raise ValueError(f"Unsupported chord: {symbol}. Try Cmaj7, Dm7, G7b9, Bb/F or N.C.") from exc


def transpose_chord(symbol: str, semitones: int) -> str:
    chord_object(symbol)
    if symbol in ("N.C.", "NC"):
        return "N.C."
    match = ROOT.fullmatch(symbol)
    root, accidental, suffix = match.groups()
    names = SHARPS if "#" in accidental else FLATS
    transposed = names[(pitch_class(root + accidental) + semitones) % 12]
    bass = re.search(r"/([A-G][b#]?)$", suffix)
    if bass:
        suffix = suffix[:bass.start()] + "/" + names[(pitch_class(bass[1]) + semitones) % 12]
    return transposed + suffix


def transpose_project(project, semitones: int):
    copy = project.model_copy(deep=True)
    copy.key = FLATS[(pitch_class(copy.key) + semitones) % 12]
    for measure in copy.measures:
        for chord in measure.chords:
            chord.symbol = transpose_chord(chord.symbol, semitones)
        for note in measure.notes:
            if not 0 <= note.midi + semitones <= 127:
                raise ValueError("Transposition moves a note outside MIDI range")
            note.midi += semitones
    return copy


def seconds_to_beat(seconds: float, start: float, end: float, quarters: float) -> float:
    if end <= start:
        raise ValueError("Invalid measure boundary")
    return (seconds - start) / (end - start) * quarters


def quantize(beat: float, subdivision: float = 0.5) -> float:
    if subdivision <= 0:
        raise ValueError("Subdivision must be positive")
    return round(beat / subdivision) * subdivision
