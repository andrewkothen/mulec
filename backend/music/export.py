"""Portable notation and print-ready chord charts."""

from io import BytesIO
import textwrap

from music21 import bar, clef, expressions, layout, metadata, meter, midi, note, stream, tempo
from music21.musicxml.m21ToXml import GeneralObjectExporter
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, letter
from reportlab.pdfgen import canvas

from backend.models import Project
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
        c.drawRightString(width - margin, height - 114, chart_label)
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
                label = nashville_chord(event.symbol, reference) if reference else event.symbol
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


def arrangement_pdf(project: Project, paper="letter") -> bytes:
    """Print the arrangement order and each part once, including changed endings."""
    from xml.sax.saxutils import escape

    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    from backend.music.arrangement import arrangement

    plan = arrangement(project)
    output = BytesIO()
    page_size = A4 if paper == "a4" else letter
    usable = page_size[0] - 84
    document = SimpleDocTemplate(
        output,
        pagesize=page_size,
        leftMargin=42,
        rightMargin=42,
        topMargin=36,
        bottomMargin=36,
        title=project.title,
        author=project.composer or "Mulec",
    )
    title_style = ParagraphStyle("Title", fontName="Helvetica-Bold", fontSize=22, leading=26, spaceAfter=8)
    text_style = ParagraphStyle("Text", fontName="Helvetica", fontSize=10, leading=14, spaceAfter=8)
    part_style = ParagraphStyle("Part", fontName="Helvetica-Bold", fontSize=13, leading=17, spaceBefore=10)
    chord_style = ParagraphStyle(
        "Chords", fontName="Helvetica-Bold", fontSize=12, leading=18, splitLongWords=True
    )
    story = [Paragraph(escape(project.title), title_style)]
    metadata_text = " · ".join(
        filter(
            None,
            [
                project.composer,
                f"{project.key} {project.key_mode}",
                f"{project.meter.numerator}/{project.meter.denominator}",
                f"{project.bpm:g} BPM",
            ],
        )
    )
    story.append(Paragraph(escape(metadata_text), text_style))
    order = " → ".join(
        step["name"] + (f" *{step['variant']}" if step["variant"] else "") for step in plan["order"]
    )
    # PDF's built-in fonts do not include the arrow glyph.
    story.append(Paragraph(escape(order.replace("→", "/")), part_style))
    if any(part["variant"] for part in plan["parts"]):
        story.append(Paragraph("* Changed ending or variation, shown below.", text_style))
    story.append(Spacer(1, 12))
    for part in plan["parts"]:
        times = [step["time"] for step in plan["order"] if step["part"] == part["id"]]
        timestamps = ", ".join(f"{int(t) // 60}:{int(t) % 60:02d}" for t in times)
        heading = escape(part["name"]) + (f" *{part['variant']}" if part["variant"] else "")
        detail = f"Changed ending from bar {part['from_bar']}" if part["ending"] else f"{part['length']} bars"
        heading += f"  <font size='9'>{detail} / {timestamps}</font>"
        header = Paragraph(heading, part_style)
        cells = []
        for block in part["blocks"]:
            for i, measure in enumerate(block["bars"]):
                events = measure["chords"]
                symbols = [
                    escape(event["symbol"])
                    + (
                        f"<super><font size='7'> {event['beat'] + 1:g}</font></super>"
                        if len(events) > 1
                        else ""
                    )
                    for event in events
                ]
                label = "  ".join(symbols) or "-"
                cue = f"<br/><font size='8'>{escape(measure['cue'])}</font>" if measure["cue"] else ""
                repeat = ""
                if i == 0 and block["times"] > 1:
                    last = block["first"] + len(block["bars"]) - 1
                    scope = str(block["first"]) if len(block["bars"]) == 1 else f"{block['first']}-{last}"
                    repeat = f"<br/><font size='8'>Play {scope}: {block['times']}x</font>"
                cells.append(
                    Paragraph(
                        f"<font size='7'>{block['first'] + i}</font><br/>{label}{repeat}{cue}", chord_style
                    )
                )
        rows = [cells[offset : offset + 4] for offset in range(0, len(cells), 4)]
        for i, row in enumerate(rows):
            row += [""] * (4 - len(row))
            grid = Table([row], colWidths=[usable / 4] * 4)
            grid.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LINEBEFORE", (0, 0), (-1, -1), 0.45, colors.grey),
                        ("LINEAFTER", (-1, 0), (-1, -1), 0.45, colors.grey),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            story.append(KeepTogether([header, grid]) if i == 0 else grid)
        story.append(Spacer(1, 6))
    document.build(story)
    return output.getvalue()
