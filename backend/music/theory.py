"""Chord parsing and transposition independent of inference."""

import re

from music21 import harmony, pitch, key

FLATS = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]
SHARPS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
ROOT = re.compile(r"^([A-G])([b#]?)(.*)$")


def notation_key(tonic: str, mode: str):
    """Keep user spelling when engravable; respell theoretical signatures.

    OSMD/VexFlow supports ordinary signatures (-7 through +7 fifths).
    Db minor has -8 fifths, so export its pitch-equivalent C# minor.
    This never changes a note's pitch or the user's tonal-center decision.
    """
    pitch_class(tonic)
    result = key.Key(tonic.replace("b", "-"), mode)
    if abs(result.sharps) > 7:
        result = key.Key(result.tonic.getEnharmonic(), mode)
    return result


def conventional_key(root: int, mode: str) -> str:
    names = (
        ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "G#", "A", "Bb", "B"]
        if mode == "minor"
        else ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
    )
    return names[root % 12]


def pitch_class(name: str) -> int:
    if not re.fullmatch(r"[A-G][b#]?", name):
        raise ValueError("Use a note name such as C, F# or Bb")
    return int(pitch.Pitch(name.replace("b", "-")).pitchClass)


def chord_object(symbol: str):
    symbol = symbol.strip().replace("♭", "b").replace("♯", "#")
    if symbol in ("N.C.", "NC", "?"):
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


def transpose_chord(symbol: str, semitones: int, prefer_sharps: bool | None = None) -> str:
    chord_object(symbol)
    if symbol == "?":
        return "?"
    if symbol in ("N.C.", "NC"):
        return "N.C."
    match = ROOT.fullmatch(symbol)
    root, accidental, suffix = match.groups()
    names = SHARPS if (prefer_sharps if prefer_sharps is not None else "#" in accidental) else FLATS
    transposed = names[(pitch_class(root + accidental) + semitones) % 12]
    bass = re.search(r"/([A-G][b#]?)$", suffix)
    if bass:
        suffix = suffix[: bass.start()] + "/" + names[(pitch_class(bass[1]) + semitones) % 12]
    return transposed + suffix


def transpose_project(project, semitones: int):
    copy = project.model_copy(deep=True)
    copy.key = conventional_key(pitch_class(copy.key) + semitones, copy.key_mode)
    prefer_sharps = notation_key(copy.key, copy.key_mode).sharps > 0
    for measure in copy.measures:
        for chord in measure.chords:
            chord.symbol = transpose_chord(chord.symbol, semitones, prefer_sharps)
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
