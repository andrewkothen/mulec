"""Compact, handwritten rhythm charts with a bounded, legible page-fit pass."""

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import Flowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer

from backend.models import Project
from backend.music.arrangement import arrangement
from backend.music.chart_style import beat_label, chart_font, chord_changes, jazz_symbol


def _bars(part):
    result = []
    for block in part["blocks"]:
        for i, bar in enumerate(block["bars"]):
            result.append(
                dict(
                    bar,
                    number=block["first"] + i,
                    begin=block["times"] > 1 and i == 0,
                    finish=block["times"] > 1 and i == len(block["bars"]) - 1,
                    passes=block["times"],
                )
            )
    return result


class RhythmRow(Flowable):
    def __init__(self, bars, width, size, first_meter):
        super().__init__()
        self.bars, self.width, self.size, self.first_meter = bars, width, size, first_meter
        cue_style = ParagraphStyle("cue", fontName=chart_font(), fontSize=9, leading=11)
        self.cues = [Paragraph(escape(bar["cue"]), cue_style) if bar["cue"] else None for bar in bars]
        self.cue_height = max(
            (cue.wrap(width / len(bars) - 12, 10000)[1] for cue in self.cues if cue), default=0
        )
        self.harmonies = []
        previous_meter = first_meter
        previous_chord = None
        for bar in bars:
            signature = (bar["meter"]["numerator"], bar["meter"]["denominator"])
            available = (
                width / len(bars)
                - 16
                - (15 if signature != previous_meter else 0)
                - (5 if bar["begin"] or bar["repeat_start"] else 0)
            )
            previous_meter = signature
            lines, line, used = [], [], 0
            events = chord_changes(
                bar["chords"], None if bar["begin"] or bar["repeat_start"] else previous_chord
            )
            if bar["chords"]:
                previous_chord = sorted(bar["chords"], key=lambda chord: chord["beat"])[-1]["symbol"]
            else:
                previous_chord = None
            for event in events:
                label = jazz_symbol(event["symbol"])
                text_size = max(
                    12, min(size, (available - 9) * size / max(1, stringWidth(label, chart_font(), size)))
                )
                occupied = (
                    stringWidth(label, chart_font(), text_size) + (9 if len(bar["chords"]) > 1 else 0) + 7
                )
                if line and used + occupied > available:
                    lines.append(line)
                    line, used = [], 0
                line.append((event, label, text_size, occupied))
                used += occupied
            self.harmonies.append([*lines, line] if line else [[]])
        self.harmony_lines = max(map(len, self.harmonies))
        self.cue_gap = 10 if self.cue_height and any(bar["begin"] for bar in bars) else 0
        self.height = 31 + size * 0.9 + self.cue_height + self.cue_gap + (self.harmony_lines - 1) * (size + 8)

    def draw(self):
        c, font, size = self.canv, chart_font(), self.size
        cell = self.width / len(self.bars)
        bottom, gap = 9 + self.cue_height + self.cue_gap, 4
        c.setStrokeColorRGB(0, 0, 0)
        c.setFillColorRGB(0, 0, 0)
        c.setLineWidth(0.38)
        for line in range(5):
            c.line(0, bottom + line * gap, self.width, bottom + line * gap)
        last_meter = self.first_meter
        for i, bar in enumerate(self.bars):
            x, end = i * cell, (i + 1) * cell
            numerator, denominator = bar["meter"]["numerator"], bar["meter"]["denominator"]
            signature = (numerator, denominator)
            c.line(x, bottom, x, bottom + 4 * gap)
            left = x + 8
            if signature != last_meter:
                c.setFont(font, 12)
                c.drawString(left, bottom + 10, str(numerator))
                c.drawString(left, bottom - 1, str(denominator))
                left += 15
            last_meter = signature
            if bar["begin"] or bar["repeat_start"]:
                c.setLineWidth(1.3)
                c.line(x + 2, bottom, x + 2, bottom + 16)
                c.setLineWidth(0.38)
                for y in (bottom + 6, bottom + 10):
                    c.circle(x + 6, y, 0.8, stroke=0, fill=1)
                left += 5
            if bar["finish"] or bar["repeat_end"]:
                c.setLineWidth(1.3)
                c.line(end - 2, bottom, end - 2, bottom + 16)
                c.setLineWidth(0.38)
                for y in (bottom + 6, bottom + 10):
                    c.circle(end - 6, y, 0.8, stroke=0, fill=1)
            if i == 0:
                c.setFont(font, 8)
                c.drawRightString(x - 4, bottom + 20, str(bar["number"]))
            if bar["begin"]:
                c.setFont(font, 9)
                c.drawString(x + 6, bottom - 9, f"x{bar['passes']}")
            # Dense changes wrap before chord text would fall below twelve points.
            for line_index, events in enumerate(self.harmonies[i]):
                remaining = max(0, end - left - 8 - sum(event[3] for event in events))
                cursor = left
                y = bottom + 20 + (self.harmony_lines - line_index - 1) * (size + 8)
                for event, label, text_size, occupied in events:
                    c.setFont(font, text_size)
                    c.drawString(cursor, y, label)
                    if len(bar["chords"]) > 1:
                        c.setFont(font, 7)
                        c.drawString(
                            cursor + stringWidth(label, font, text_size) + 1,
                            y + 5,
                            beat_label(event["beat"], denominator),
                        )
                    cursor += occupied + remaining / max(1, len(events))
            # Slashes show the selected meter. Chord-change beat cues stay explicit.
            for beat in range(numerator):
                sx = left + (end - left - 10) * (beat + 0.5) / numerator
                path = c.beginPath()
                path.moveTo(sx - 3, bottom + 4)
                path.lineTo(sx + 4, bottom + 13)
                path.lineTo(sx + 4, bottom + 10)
                path.lineTo(sx - 3, bottom + 1)
                path.close()
                c.drawPath(path, fill=1, stroke=0)
            if self.cues[i]:
                _, h = self.cues[i].wrap(cell - 12, 10000)
                self.cues[i].drawOn(c, x + 6, bottom - 5 - h - self.cue_gap)
        c.line(self.width, bottom, self.width, bottom + 4 * gap)


def render(project: Project, paper="letter") -> bytes:
    plan, font = arrangement(project), chart_font()
    page_size = A4 if paper == "a4" else letter
    usable = page_size[0] - 84

    def build(size):
        output = BytesIO()
        document = SimpleDocTemplate(
            output,
            pagesize=page_size,
            leftMargin=42,
            rightMargin=42,
            topMargin=32,
            bottomMargin=34,
            title=project.title,
            author=project.composer or "Mulec",
        )
        style = ParagraphStyle("text", fontName=font, fontSize=11, leading=14, spaceAfter=7)
        title = ParagraphStyle("title", parent=style, fontSize=28, leading=32, alignment=1, spaceAfter=10)
        heading = ParagraphStyle("part", parent=style, fontSize=16, leading=20, spaceBefore=8, spaceAfter=4)
        story = [Paragraph(escape(project.title), title)]
        if project.composer:
            story.append(
                Paragraph(escape(project.composer), ParagraphStyle("composer", parent=style, alignment=2))
            )
        story.append(
            Paragraph(
                escape(
                    f"{project.key} {project.key_mode} / {project.meter.numerator}/{project.meter.denominator} / {project.bpm:g} BPM"
                ),
                style,
            )
        )
        order = " / ".join(
            step["name"] + (f" *{step['variant']}" if step["variant"] else "") for step in plan["order"]
        )
        story.append(Paragraph(escape(order), ParagraphStyle("order", parent=style, fontSize=14, leading=18)))
        legend = "x4 = four total passes. △ = major; - = minor. Small numbers = beats (& = offbeat). Unlabeled slashes continue the chord."
        if any(part["variant"] for part in plan["parts"]):
            legend += " * = changed ending or variation."
        story.append(
            Paragraph(escape(legend), ParagraphStyle("legend", parent=style, fontSize=9, leading=12))
        )
        for part in plan["parts"]:
            label = part["name"] + (f" *{part['variant']}" if part["variant"] else "")
            detail = (
                f"Changed ending from bar {part['from_bar']}: play {part['name']} 1-{part['from_bar'] - 1}, then below"
                if part["ending"]
                else f"{part['length']} bars"
            )
            header = Paragraph(escape(label) + f" <font size='10'> / {escape(detail)}</font>", heading)
            bars, offset = _bars(part), 0
            previous_meter = (project.meter.numerator, project.meter.denominator)
            while offset < len(bars):
                sample = bars[offset : offset + 4]
                demand = max(
                    (
                        sum(
                            stringWidth(jazz_symbol(ch["symbol"]), font, size)
                            + (9 if len(bar["chords"]) > 1 else 0)
                            + 4
                            for ch in bar["chords"]
                        )
                        + 24
                        for bar in sample
                    ),
                    default=0,
                )
                capacity = 1 if demand > usable / 2 else 2 if demand > usable / 4 else 4
                row = bars[offset : offset + capacity]
                flow = RhythmRow(row, usable * len(row) / capacity, size, previous_meter)
                story.append(KeepTogether([header, flow]) if offset == 0 else flow)
                previous_meter = (row[-1]["meter"]["numerator"], row[-1]["meter"]["denominator"])
                offset += len(row)
            story.append(Spacer(1, 3))
        pages = []

        def footer(c, _):
            pages.append(c.getPageNumber())
            c.setFont(font, 9)
            c.drawString(42, 18, project.title)
            c.drawRightString(page_size[0] - 42, 18, str(c.getPageNumber()))

        document.build(story, onFirstPage=footer, onLaterPages=footer)
        return output.getvalue(), len(pages)

    # Target four pages through spacing and type size, with a readable lower bound.
    # Very long/dense scores can exceed the target; no music is omitted to force a fit.
    target = 2 if plan["written_bars"] <= 80 else 3 if plan["written_bars"] <= 120 else 4
    for size in (17, 16, 15, 14, 13, 12):
        content, pages = build(size)
        if pages <= target:
            break
    return content
