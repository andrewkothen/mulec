from io import BytesIO

import numpy as np
from pypdf import PdfReader

from backend.analysis.form import group_sections
from backend.models import Chord, Measure, Meter, Note, Project
from backend.music.arrangement import arrangement
from backend.music.export import arrangement_pdf


def bar(symbol, i, section=""):
    return Measure(start=i * 2, end=i * 2 + 2, section=section, chords=[Chord(symbol=symbol)])


def test_pattern_count_and_changed_ending_keep_arrangement_order():
    symbols = ["C", "Am", "F", "G"] * 3 + ["Dm", "G"]
    p = Project(
        measures=[
            bar(s, i, "Verse" if i in (0, len(symbols)) else "")
            for i, s in enumerate(symbols + symbols[:-1] + ["G7"])
        ]
    )
    result = arrangement(p)
    assert len(result["parts"]) == 2
    assert [o["name"] for o in result["order"]] == ["Verse", "Verse"]
    first, ending = result["parts"]
    assert first["blocks"][0]["times"] == 3
    assert len(first["blocks"][0]["bars"]) == 4
    assert ending["ending"] and ending["from_bar"] == len(symbols)
    assert ending["blocks"][0]["bars"][0]["chords"][0]["symbol"] == "G7"
    assert result["written_bars"] == 7
    text = "\n".join(page.extract_text() for page in PdfReader(BytesIO(arrangement_pdf(p))).pages)
    assert "Play 1-4: 3x" in text and "Changed ending from bar 14" in text
    assert len(p.measures) == 28


def test_identical_return_is_written_once_but_different_meter_and_notes_are_preserved():
    p = Project(measures=[bar("C", 0, "A"), bar("G", 1), bar("F", 2, "B"), bar("C", 3, "A"), bar("G", 4)])
    result = arrangement(p)
    assert len(result["parts"]) == 2
    assert result["order"][0]["part"] == result["order"][2]["part"]
    p.measures[4].meter = Meter(numerator=3)
    p.measures[4].notes = [Note(midi=64)]
    assert len(arrangement(p)["parts"]) == 3


def test_similar_key_without_the_ordered_pattern_does_not_group():
    chroma = np.tile(np.eye(12)[:4], (2, 1))
    chroma = np.concatenate([chroma, chroma[::-1], chroma])
    timbre = np.tile(np.eye(2)[0], (24, 1))
    assert group_sections([0, 8, 16], timbre, chroma) == [0, 1, 0]
