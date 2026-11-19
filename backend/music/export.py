"""Portable notation and print-ready chord charts."""

from io import BytesIO
import textwrap

from music21 import bar, clef, expressions, layout, metadata, meter, midi, note, stream, tempo
from music21.musicxml.m21ToXml import GeneralObjectExporter
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, letter
from reportlab.pdfgen import canvas

from backend.models import Project
from backend.music.chart_style import chart_font
from backend.music.theory import chord_object, nashville_chord, nashville_reference, notation_key


def score(project: Project, *, rhythm=False, first_bar=1):
    result = stream.Score()
    result.metadata = metadata.Metadata(title=project.title, composer=project.composer)
    part = stream.Part()
    part.partName = ""
    part.style.printPartName = False
    part.insert(0, clef.TrebleClef())
    part.insert(0, notation_key(project.key, project.key_mode))
    part.insert(0, tempo.MetronomeMark(number=project.bpm))
    last_meter = None
    prior_symbol = None
    for number, measure in enumerate(project.measures, first_bar):
        m = stream.Measure(number=number)
        if not measure.chords:
            prior_symbol = None
        signature = f"{measure.meter.numerator}/{measure.meter.denominator}"
        if signature != last_meter:
            m.insert(0, meter.TimeSignature(signature))
            last_meter = signature
        if measure.section:
            if number > first_bar:
                m.insert(0, layout.SystemLayout(isNew=True))
            m.insert(0, expressions.RehearsalMark(measure.section))
        if measure.cue:
            m.insert(0, expressions.TextExpression(measure.cue))
        for event in sorted(measure.chords, key=lambda c: c.beat):
            carry = (
                rhythm
                and not event.manual
                and event.beat == 0
                and event.symbol == prior_symbol
                and not measure.section
                and not measure.repeat_start
            )
            prior_symbol = event.symbol
            if carry:
                continue
            if event.symbol == "?":
                continue
            chord = chord_object(event.symbol)
            chord.writeAsChord = False
            m.insert(event.beat, chord)
        position = 0.0
        if rhythm:
            beat_length = 4 / measure.meter.denominator
            for i in range(measure.meter.numerator):
                slash = note.Unpitched(quarterLength=beat_length)
                slash.displayStep, slash.displayOctave = "B", 4
                slash.notehead, slash.noteheadFill, slash.stemDirection = "slash", True, "noStem"
                m.insert(i * beat_length, slash)
            position = measure.meter.quarters
        else:
            for event in sorted(measure.notes, key=lambda n: n.beat):
                if event.beat > position:
                    m.insert(position, note.Rest(quarterLength=event.beat - position))
                n = note.Note(event.midi, quarterLength=event.duration)
                m.insert(event.beat, n)
                position = event.beat + event.duration
        if position < measure.meter.quarters:
            m.insert(position, note.Rest(quarterLength=measure.meter.quarters - position))
        if measure.repeat_start:
            m.leftBarline = bar.Repeat(direction="start")
        if measure.repeat_end:
            m.rightBarline = bar.Repeat(direction="end")
        part.append(m)
    if rhythm:
        part.streamStatus.beams = True  # Rhythm slashes are stemless, including in eighth-note meters.
    result.append(part)
    return result


def musicxml(project: Project, *, rhythm=False, first_bar=1) -> bytes:
    has_melody = any(measure.notes for measure in project.measures)
    has_harmony = any(chord.symbol not in {"?", "NC", "N.C."} for m in project.measures for chord in m.chords)
    return GeneralObjectExporter(
        score(project, rhythm=rhythm or (has_harmony and not has_melody), first_bar=first_bar)
    ).parse()


def midi_bytes(project: Project) -> bytes:
    if not any(m.notes for m in project.measures):
        raise ValueError("Add melody notes before exporting MIDI")
    # Harmony symbols remain text; MIDI contains only the melody/rest timeline.
    file = midi.translate.streamToMidiFile(score(project))
    return file.writestr()


def pdf(project: Project, paper="letter", part_label="Concert pitch", *, nashville=False) -> bytes:
    output = BytesIO()
    font = chart_font()
    size = A4 if paper == "a4" else letter
    width, height = size
    c = canvas.Canvas(output, pagesize=size)
    c.setTitle(project.title)
    c.setAuthor(project.composer or "Mulec")
    margin, page = 42, 0
    ink, muted = HexColor("#17262b"), HexColor("#67757a")
    reference = nashville_reference(project.key, project.key_mode) if nashville else None
    chart_label = f"Nashville numbers (1 = {reference})" if reference else "Chord chart"
    if part_label != "Concert pitch":
        chart_label = f"{part_label} / {chart_label}"

    def fit(text, font, maximum, available):
        font_size = maximum
        while c.stringWidth(text, font, font_size) > available and font_size > 7:
            font_size -= 0.5
        return font_size

    def header():
        nonlocal page
        page += 1
        c.setFillColor(ink)
        c.setFont(font, fit(project.title, font, 24, width - 2 * margin))
        c.drawString(margin, height - 56, project.title)
        c.setFont(font, fit(project.composer, font, 10, width - 2 * margin))
        c.drawString(margin, height - 74, project.composer)
        c.setFont(font, 10)
        c.drawString(
            margin,
            height - 98,
            f"{project.key} {project.key_mode}  |  {project.meter.numerator}/{project.meter.denominator}  |  quarter = {project.bpm:g}  |  {project.feel}",
        )
        c.setFillColor(muted)
        c.setFont(font, 9)
        c.drawRightString(width - margin, height - 114, chart_label)
        c.setStrokeColor(ink)
        c.line(margin, height - 124, width - margin, height - 124)
        c.setFont(font, 8)
        c.drawString(margin, 25, "MULEC  /  Rehearsal chart")
        c.drawRightString(width - margin, 25, str(page))
        return height - 145

    y = header()
    # A row stops at a section boundary. Dense measures get fewer columns.
    index = 0
    while index < len(project.measures):
        row = []
        capacity = 2 if any(len(m.chords) > 4 for m in project.measures[index : index + 4]) else 4
        for m in project.measures[index : index + capacity]:
            if row and m.section:
                break
            row.append(m)
        cue_lines = max((len(textwrap.wrap(m.cue, 25)) for m in row), default=0)
        event_lines = max((len(m.chords) for m in row), default=1)
        line_height = min(16, (height - 270 - cue_lines * 11) / max(1, event_lines))
        row_height = max(80, 38 + event_lines * line_height + cue_lines * 11)
        if y - row_height - (20 if row[0].section else 0) < 50:
            c.showPage()
            y = header()
        if row[0].section:
            c.setFillColor(ink)
            c.setFont(font, 11)
            c.drawString(margin, y, row[0].section)
            y -= 20
        cell_width = (width - 2 * margin) / capacity
        for offset, m in enumerate(row):
            x = margin + offset * cell_width
            c.setStrokeColor(HexColor("#a7b2b5"))
            c.line(x, y - 8, x, y - row_height + 8)
            c.line(x, y - row_height + 8, x + cell_width, y - row_height + 8)
            c.setFillColor(muted)
            c.setFont(font, 8)
            c.drawString(x + 8, y - 8, str(index + offset + 1))
            suffix = (" |:" if m.repeat_start else "") + (" :|" if m.repeat_end else "")
            if m.meter != project.meter:
                suffix = f"{m.meter.numerator}/{m.meter.denominator}" + suffix
            c.drawRightString(x + cell_width - 8, y - 8, suffix)
            for j, event in enumerate(sorted(m.chords, key=lambda v: v.beat)):
                label = nashville_chord(event.symbol, reference) if reference else event.symbol
                c.setFillColor(ink)
                c.setFont(font, fit(label, font, min(14, line_height - 2), cell_width - 40))
                c.drawString(x + 8, y - 28 - j * line_height, label)
                c.setFillColor(muted)
                c.setFont(font, 7)
                c.drawRightString(x + cell_width - 8, y - 28 - j * line_height, f"{event.beat + 1:g}")
            c.setFont(font, 8)
            for j, line in enumerate(textwrap.wrap(m.cue, 25)):
                c.drawString(x + 8, y - 34 - len(m.chords) * line_height - j * 11, line)
        c.line(margin + len(row) * cell_width, y - 8, margin + len(row) * cell_width, y - row_height + 8)
        y -= row_height + 16
        index += len(row)
    c.save()
    return output.getvalue()


def arrangement_pdf(project: Project, paper="letter", *, condensed=False) -> bytes:
    if condensed:
        from backend.music.condensed_pdf import render
    else:
        from backend.music.rhythm_pdf import render

    return render(project, paper)
