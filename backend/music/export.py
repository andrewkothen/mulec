"""Portable notation and print-ready chord charts."""

from io import BytesIO
import textwrap

from music21 import bar, clef, expressions, key, metadata, meter, midi, note, stream, tempo
from music21.musicxml.m21ToXml import GeneralObjectExporter
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, letter
from reportlab.pdfgen import canvas

from backend.models import Project
from backend.music.theory import chord_object


def score(project: Project):
    result = stream.Score()
    result.metadata = metadata.Metadata(title=project.title, composer=project.composer)
    part = stream.Part()
    part.partName = "Concert chart"
    part.insert(0, clef.TrebleClef())
    part.insert(0, key.Key(project.key.replace("b", "-"), project.key_mode))
    part.insert(0, tempo.MetronomeMark(number=project.bpm))
    last_meter = None
    for number, measure in enumerate(project.measures, 1):
        m = stream.Measure(number=number)
        signature = f"{measure.meter.numerator}/{measure.meter.denominator}"
        if signature != last_meter:
            m.insert(0, meter.TimeSignature(signature))
            last_meter = signature
        if measure.section:
            m.insert(0, expressions.RehearsalMark(measure.section))
        if measure.cue:
            m.insert(0, expressions.TextExpression(measure.cue))
        for event in sorted(measure.chords, key=lambda c: c.beat):
            chord = chord_object(event.symbol)
            chord.writeAsChord = False
            m.insert(event.beat, chord)
        position = 0.0
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
    result.append(part)
    return result


def musicxml(project: Project) -> bytes:
    return GeneralObjectExporter(score(project)).parse()


def midi_bytes(project: Project) -> bytes:
    if not any(m.notes for m in project.measures):
        raise ValueError("Add melody notes before exporting MIDI")
    # Harmony symbols remain text; MIDI contains only the melody/rest timeline.
    file = midi.translate.streamToMidiFile(score(project))
    return file.writestr()


def pdf(project: Project, paper="letter", part_label="Concert pitch") -> bytes:
    output = BytesIO()
    size = A4 if paper == "a4" else letter
    width, height = size
    c = canvas.Canvas(output, pagesize=size)
    c.setTitle(project.title)
    c.setAuthor(project.composer or "Mulec")
    margin, page = 42, 0
    ink, muted = HexColor("#17262b"), HexColor("#67757a")

    def fit(text, font, maximum, available):
        font_size = maximum
        while c.stringWidth(text, font, font_size) > available and font_size > 7:
            font_size -= 0.5
        return font_size

    def header():
        nonlocal page
        page += 1
        c.setFillColor(ink)
        c.setFont("Helvetica-Bold", fit(project.title, "Helvetica-Bold", 24, width - 2 * margin))
        c.drawString(margin, height - 56, project.title)
        c.setFont("Helvetica", fit(project.composer, "Helvetica", 10, width - 2 * margin))
        c.drawString(margin, height - 74, project.composer)
        c.setFont("Helvetica", 10)
        c.drawString(
            margin,
            height - 98,
            f"{project.key} {project.key_mode}  |  {project.meter.numerator}/{project.meter.denominator}  |  quarter = {project.bpm:g}  |  {project.feel}",
        )
        c.setFillColor(muted)
        c.setFont("Helvetica", 9)
        c.drawRightString(width - margin, height - 114, part_label + " / Chord chart")
        c.setStrokeColor(ink)
        c.line(margin, height - 124, width - margin, height - 124)
        c.setFont("Helvetica", 8)
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
            c.setFont("Helvetica-Bold", 11)
            c.drawString(margin, y, row[0].section)
            y -= 20
        cell_width = (width - 2 * margin) / capacity
        for offset, m in enumerate(row):
            x = margin + offset * cell_width
            c.setStrokeColor(HexColor("#a7b2b5"))
            c.line(x, y - 8, x, y - row_height + 8)
            c.line(x, y - row_height + 8, x + cell_width, y - row_height + 8)
            c.setFillColor(muted)
            c.setFont("Helvetica", 8)
            c.drawString(x + 8, y - 8, str(index + offset + 1))
            suffix = (" |:" if m.repeat_start else "") + (" :|" if m.repeat_end else "")
            if m.meter != project.meter:
                suffix = f"{m.meter.numerator}/{m.meter.denominator}" + suffix
            c.drawRightString(x + cell_width - 8, y - 8, suffix)
            for j, event in enumerate(sorted(m.chords, key=lambda v: v.beat)):
                label = event.symbol
                c.setFillColor(ink)
                c.setFont(
                    "Helvetica-Bold", fit(label, "Helvetica-Bold", min(14, line_height - 2), cell_width - 40)
                )
                c.drawString(x + 8, y - 28 - j * line_height, label)
                c.setFillColor(muted)
                c.setFont("Helvetica", 7)
                c.drawRightString(x + cell_width - 8, y - 28 - j * line_height, f"{event.beat + 1:g}")
            c.setFont("Helvetica-Oblique", 8)
            for j, line in enumerate(textwrap.wrap(m.cue, 25)):
                c.drawString(x + 8, y - 34 - len(m.chords) * line_height - j * 11, line)
        c.line(margin + len(row) * cell_width, y - 8, margin + len(row) * cell_width, y - row_height + 8)
        y -= row_height + 16
        index += len(row)
    c.save()
    return output.getvalue()
