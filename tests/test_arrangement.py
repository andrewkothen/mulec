from io import BytesIO

import numpy as np
from pypdf import PdfReader

from backend.analysis.form import group_sections
from backend.models import Chord, Measure, Meter, Note, Project
from backend.music.arrangement import arrangement
from backend.music.chart_style import beat_label, chord_changes, jazz_symbol
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
    assert "x3" in text and "Changed ending from bar 14" in text
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


def test_jazz_shorthand_preserves_chord_quality_bass_and_beat_units():
    expected = {
        "Bbmaj7/D": "B♭△7/D",
        "F#m7b5": "F♯ø7",
        "Ebm9": "E♭-9",
        "C7b9#11": "C7♭9♯11",
        "Gdim7": "G°7",
        "N.C.": "N.C.",
    }
    assert {symbol: jazz_symbol(symbol) for symbol in expected} == expected
    assert beat_label(3.5) == "4&"
    assert beat_label(1.5, 8) == "4"
    events = [{"symbol": "C", "beat": beat, "manual": beat == 2} for beat in range(3)]
    assert [event["beat"] for event in chord_changes(events)] == [0, 2]
    assert len(events) == 3


def test_rehearsal_length_pdf_fits_four_pages_and_embeds_the_chart_font():
    # Distinct beat positions prevent artificial repeat compression in this fixture.
    p = Project(
        title="Rehearsal length",
        measures=[
            Measure(
                start=i * 2,
                end=i * 2 + 2,
                section="Verse" if i == 0 else "",
                chords=[Chord(symbol=["Cmaj7", "Am7", "Dm7", "G7"][i % 4], beat=(i % 16) / 8)],
                cue="End of arrangement" if i == 159 else f"Cue {i}" if i % 7 == 0 else "",
            )
            for i in range(160)
        ],
    )
    document = PdfReader(BytesIO(arrangement_pdf(p)))
    assert 2 <= len(document.pages) <= 4
    assert "End of arrangement" in "".join(page.extract_text() for page in document.pages)
    embedded = [
        font.get_object()
        for page in document.pages
        for font in page["/Resources"]["/Font"].get_object().values()
    ]
    assert any("MulecJazz" in font.get("/BaseFont", "") and "/FontDescriptor" in font for font in embedded)


def test_condense_references_exact_phrases_across_names_but_keeps_changes():
    phrase = ["Cmaj7", "Dm7", "Em7", "Fmaj7", "G7", "Am7", "Dm9", "G"]
    symbols = phrase + ["Eb", "Ab", "Fm", "Bb7"] + phrase + ["D7", "G7"]
    p = Project(
        measures=[bar(s, i, {0: "A", 8: "Bridge", 12: "Verse"}.get(i, "")) for i, s in enumerate(symbols)]
    )
    original = p.model_dump()
    full, short = arrangement(p), arrangement(p, condensed=True)
    assert short["written_bars"] == full["written_bars"] - 8
    verse = short["parts"][-1]
    assert verse["blocks"][0]["reference"] == {"name": "A", "variant": 0, "first": 1, "length": 8}
    assert [c["symbol"] for b in verse["blocks"][1]["bars"] for c in b["chords"]] == ["D7", "G7"]
    assert p.model_dump() == original
    p.measures[17].cue = "Stop here"
    changed = arrangement(p, condensed=True)
    assert any(
        b["cue"] == "Stop here"
        for part in changed["parts"]
        for block in part["blocks"]
        for b in block["bars"]
    )
    text = "\n".join(
        page.extract_text() for page in PdfReader(BytesIO(arrangement_pdf(p, condensed=True))).pages
    )
    assert "Stop here" in text and "play A" in text


def test_condense_keeps_repeat_counts_and_uses_direct_printed_references():
    phrase = ["C", "Dm", "F", "G"]
    p = Project(measures=[bar(s, i, {0: "A", 8: "B", 20: "C"}.get(i, "")) for i, s in enumerate(phrase * 9)])
    plan = arrangement(p, condensed=True)
    assert plan["written_bars"] == 4
    assert plan["parts"][1]["blocks"][0]["times"] == 3
    assert plan["parts"][2]["blocks"][0]["times"] == 4
    assert all(
        b["reference"]["name"] == "A" for part in plan["parts"] for b in part["blocks"] if "reference" in b
    )
    p.measures[8].meter = Meter(numerator=3)
    different = arrangement(p, condensed=True)["parts"][1]["blocks"]
    assert different[0]["bars"][0]["meter"]["numerator"] == 3


def test_condensed_pdf_fits_rehearsal_length_in_two_pages_with_final_cue():
    p = Project(
        title="Condense print regression",
        measures=[
            Measure(
                start=i * 2,
                end=i * 2 + 2,
                section=f"Part {i // 16 + 1}" if i % 16 == 0 else "",
                chords=[Chord(symbol=["Cmaj7", "Dm7", "F", "G7"][i % 4], beat=(i % 16) / 8)],
                cue="Final cue" if i == 159 else "",
            )
            for i in range(160)
        ],
    )
    for paper in ("letter", "a4"):
        doc = PdfReader(BytesIO(arrangement_pdf(p, paper, condensed=True)))
        assert len(doc.pages) <= 2
        assert "Final cue" in "".join(page.extract_text() for page in doc.pages)


def test_condensed_pdf_repeats_section_heading_on_continuation_pages():
    project = Project(
        title="Long form",
        measures=[
            Measure(
                start=i * 2,
                end=i * 2 + 2,
                section="Extended solo" if i == 0 else "",
                chords=[Chord(symbol="G7", beat=1.5)],
                cue=f"Rehearsal cue {i + 1}",
            )
            for i in range(180)
        ],
    )
    for paper in ("letter", "a4"):
        doc = PdfReader(BytesIO(arrangement_pdf(project, paper, condensed=True)))
        assert len(doc.pages) > 1
        assert all("Extended solo" in page.extract_text() for page in doc.pages)
        text = "".join(page.extract_text() for page in doc.pages)
        assert "Rehearsal cue 180" in text
        assert "2&" in text  # A lone offbeat chord still carries its entrance.
