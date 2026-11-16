from io import BytesIO
import xml.etree.ElementTree as ET

import pytest
from pydantic import ValidationError
from pypdf import PdfReader

from backend.models import Chord, Measure, Meter, Note, Project
from backend.music.export import midi_bytes, musicxml, pdf
from backend.music.theory import (
    chord_object,
    quantize,
    seconds_to_beat,
    transpose_chord,
    transpose_project,
    notation_key,
)


@pytest.mark.parametrize(
    "tonic",
    [
        "C",
        "C#",
        "Db",
        "D",
        "Eb",
        "E",
        "Fb",
        "E#",
        "F",
        "F#",
        "Gb",
        "G",
        "G#",
        "Ab",
        "A",
        "Bb",
        "B",
        "Cb",
        "B#",
    ],
)
@pytest.mark.parametrize("mode", ["major", "minor"])
def test_all_key_spellings_export_with_supported_signatures(tonic, mode):
    project = Project(key=tonic, key_mode=mode, measures=[Measure(notes=[Note(midi=61, duration=4)])])
    xml = ET.fromstring(musicxml(project))
    assert -7 <= int(xml.findtext(".//key/fifths")) <= 7
    assert notation_key(tonic, mode).tonic.pitchClass == notation_key(tonic, "major").tonic.pitchClass
    assert xml.findtext(".//key/mode") == mode
    assert xml.findtext(".//pitch/alter") == "1"  # respelling signature must not transpose notes


def test_db_minor_regression_and_unresolved_harmony():
    project = Project(key="Db", key_mode="minor", measures=[Measure(chords=[Chord(symbol="?")])])
    xml = ET.fromstring(musicxml(project))
    assert xml.findtext(".//key/fifths") == "4"
    assert xml.find(".//harmony") is None
    assert "Harmony to review" in musicxml(project).decode()
    assert transpose_chord("?", 2) == "?"


@pytest.mark.parametrize(
    "symbol",
    [
        "Cmaj7",
        "Dm7",
        "G7b9",
        "Fm7b5",
        "Bdim7",
        "Caug",
        "Dsus2",
        "Gsus4",
        "Cadd9",
        "Bb/F",
        "C13",
        "G7#9",
        "D7#11",
        "G7b13",
        "N.C.",
    ],
)
def test_jazz_chord_vocabulary(symbol):
    chord_object(symbol)


def example():
    return Project(
        title="Sunday Sketch",
        composer="Mulec",
        measures=[
            Measure(
                section="A",
                chords=[Chord(symbol="Cmaj7"), Chord(symbol="G7b9", beat=2)],
                notes=[Note(beat=0, duration=1.5, midi=60), Note(beat=2, duration=2, midi=64)],
                repeat_start=True,
            ),
            Measure(start=2, end=4, chords=[Chord(symbol="Bb/F")], repeat_end=True),
        ],
    )


def test_transpose_preserves_quality_and_slash_bass():
    assert transpose_chord("Bbmaj7/F", 2) == "Cmaj7/G"
    assert transpose_chord("C7b9", -2) == "Bb7b9"
    assert transpose_chord("N.C.", 9) == "N.C."
    project = example()
    part = transpose_project(project, 9)
    assert part.key == "A"
    assert part.measures[0].notes[0].midi == 69
    assert project.measures[0].notes[0].midi == 60


def test_timing_and_quantization():
    assert seconds_to_beat(11, 10, 12, 4) == 2
    assert quantize(1.28) == 1.5
    assert Meter(numerator=6, denominator=8).quarters == 3


def test_timeline_validation():
    with pytest.raises(ValidationError):
        Measure(chords=[Chord(beat=4)])
    with pytest.raises(ValidationError):
        Measure(notes=[Note(duration=3), Note(beat=2)])
    with pytest.raises(ValidationError):
        Project(measures=[Measure(start=0, end=3), Measure(start=2, end=4)])
    with pytest.raises(ValidationError):
        Project(bpm=float("nan"))


def test_musicxml_contains_harmony_melody_repeats_and_metadata():
    xml = ET.fromstring(musicxml(example()))
    assert xml.findtext("work/work-title") == "Sunday Sketch"
    assert len(xml.findall(".//harmony")) == 3
    assert xml.find(".//pitch") is not None
    assert xml.find(".//rest") is not None
    assert len(xml.findall(".//repeat")) == 2
    assert xml.findtext(".//rehearsal") == "A"
    assert xml.findtext(".//bass/bass-step") == "F"
    assert midi_bytes(example()).startswith(b"MThd")


@pytest.mark.parametrize("paper,width,height", [("letter", 612, 792), ("a4", 595.28, 841.89)])
def test_pdf_readable_content_and_paper(paper, width, height):
    reader = PdfReader(BytesIO(pdf(example(), paper)))
    assert abs(float(reader.pages[0].mediabox.width) - width) < 0.02
    assert abs(float(reader.pages[0].mediabox.height) - height) < 0.02
    text = reader.pages[0].extract_text()
    assert "Sunday Sketch" in text and "Cmaj7" in text and "G7b9" in text


def test_dense_pdf_paginates():
    p = example()
    p.measures = [
        Measure(
            start=i * 2,
            end=i * 2 + 2,
            chords=[Chord(symbol="Cmaj7", beat=j / 2) for j in range(8)],
            section="A" if i % 8 == 0 else "",
        )
        for i in range(80)
    ]
    reader = PdfReader(BytesIO(pdf(p)))
    assert len(reader.pages) > 1
    assert "80" in reader.pages[-1].extract_text()
