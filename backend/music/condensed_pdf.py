"""Short musical measures with staff lines, rhythm slashes and readable chords."""

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import BaseDocTemplate, Flowable, Frame, PageTemplate, Paragraph, Spacer, Table

from backend.music.arrangement import arrangement
from backend.music.chart_style import beat_label, chart_font, chord_changes, jazz_symbol


def label(part):
    return part["name"] + (f" *{part['variant']}" if part["variant"] else "")


def _items(part):
    items = []
    for block in part["blocks"]:
        if block.get("reference"):
            ref = block["reference"]
            text = f"{block['first']}-{block['first'] + ref['length'] - 1}: play {label(ref)} {ref['first']}-{ref['first'] + ref['length'] - 1}"
            if block["times"] > 1:
                text += f" x{block['times']}"
            items.append({"reference": text})
        for i, bar in enumerate(block["bars"]):
            items.append(
                dict(
                    bar,
                    number=block["first"] + i,
                    repeat_start=bar["repeat_start"] or (block["times"] > 1 and i == 0),
                    repeat_end=bar["repeat_end"] or (block["times"] > 1 and i == len(block["bars"]) - 1),
                    passes=block["times"] if i == 0 and block["times"] > 1 else 0,
                )
            )
    return items


class ChordRow(Flowable):
    def __init__(self, items, widths, size, previous_meter):
        super().__init__()
        self.items, self.widths, self.width = items, widths, sum(widths)
        self.labels, self.tags, self.cues = [], [], []
        font, prior = chart_font(), None
        cue_style = ParagraphStyle("cue", fontName=font, fontSize=9, leading=11)
        chord_style = ParagraphStyle("chords", fontName=font, fontSize=size, leading=size + 3)
        for item in items:
            if "reference" in item:
                self.labels.append(
                    Paragraph(
                        escape(item["reference"]),
                        ParagraphStyle("ref", parent=chord_style, fontSize=12, leading=15),
                    )
                )
                self.tags.append("")
                self.cues.append(None)
                prior = None
                continue
            meter = (item["meter"]["numerator"], item["meter"]["denominator"])
            tags = [
                f"{meter[0]}/{meter[1]}" if meter != previous_meter else "",
                f"x{item['passes']}" if item["passes"] else "",
            ]
            self.tags.append(" ".join(filter(None, tags)))
            previous_meter = meter
            events = chord_changes(item["chords"], None if item["repeat_start"] else prior)
            prior = item["chords"][-1]["symbol"] if item["chords"] else None
            symbols = [
                escape(jazz_symbol(event["symbol"]))
                + (
                    f"<super><font size='7'>{escape(beat_label(event['beat'], meter[1]))}</font></super>"
                    if len(item["chords"]) > 1 or event["beat"] > 0
                    else ""
                )
                for event in events
            ]
            self.labels.append(
                Paragraph(
                    "&#160;&#160;".join(symbols) if symbols else "/" if item["chords"] else "-", chord_style
                )
            )
            self.cues.append(Paragraph(escape(item["cue"]), cue_style) if item["cue"] else None)
        self.cue_height = max(
            (cue.wrap(w - 12, 10000)[1] for cue, w in zip(self.cues, widths) if cue), default=0
        )
        self.label_height = max(p.wrap(w - 12, 10000)[1] for p, w in zip(self.labels, widths))
        self.height = self.label_height + 31 + self.cue_height

    def draw(self):
        c, font, x = self.canv, chart_font(), 0
        bottom = self.cue_height + 7
        staff_top = bottom + 16
        c.setLineWidth(0.4)
        for i, (item, width) in enumerate(zip(self.items, self.widths)):
            end = x + width
            if "reference" not in item:
                for line in range(5):
                    y = bottom + line * 4
                    c.line(x, y, end, y)
                c.line(x, bottom, x, staff_top)
                for beat in range(item["meter"]["numerator"]):
                    sx = x + 9 + (width - 18) * (beat + 0.5) / item["meter"]["numerator"]
                    path = c.beginPath()
                    path.moveTo(sx - 2.5, bottom + 3)
                    path.lineTo(sx + 3.5, bottom + 12)
                    path.lineTo(sx + 3.5, bottom + 9)
                    path.lineTo(sx - 2.5, bottom)
                    path.close()
                    c.drawPath(path, fill=1, stroke=0)
                c.line(end, bottom, end, staff_top)
            c.setFont(font, 7)
            if "reference" not in item:
                c.drawString(x + 4, self.height - 7, str(item["number"]))
                if self.tags[i]:
                    c.drawRightString(end - 4, self.height - 7, self.tags[i])
                for direction in ("repeat_start", "repeat_end"):
                    if item[direction]:
                        rx = x + 3 if direction == "repeat_start" else end - 3
                        c.line(rx, bottom, rx, staff_top)
                        for y in (bottom + 6, bottom + 10):
                            c.circle(
                                rx + (3 if direction == "repeat_start" else -3), y, 0.7, stroke=0, fill=1
                            )
            _, h = self.labels[i].wrap(width - 12, 10000)
            self.labels[i].drawOn(c, x + 6, staff_top + 2 + self.label_height - h)
            if self.cues[i]:
                _, h = self.cues[i].wrap(width - 12, 10000)
                self.cues[i].drawOn(c, x + 6, bottom - h)
            x = end


def render(project, paper="letter"):
    plan, font = arrangement(project, condensed=True), chart_font()
    width, height = A4 if paper == "a4" else letter
    usable = width - 84

    def build(size):
        output = BytesIO()
        text = ParagraphStyle("text", fontName=font, fontSize=10, leading=13, spaceAfter=4)
        heading = ParagraphStyle("heading", parent=text, fontSize=16, leading=19, spaceBefore=6, spaceAfter=2)
        header = [
            Paragraph(
                escape(project.title),
                ParagraphStyle("title", parent=text, fontSize=25, leading=29, alignment=1),
            ),
            Paragraph(
                escape(
                    " / ".join(
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
                ),
                text,
            ),
            Paragraph(
                escape(" / ".join(label(step) for step in plan["order"])),
                ParagraphStyle("order", parent=text, fontSize=13, leading=16),
            ),
            Paragraph(
                "Condensed / x4 = four total passes; / = continue chord; * = variation. Small numbers = beats; references point to exact earlier phrases.",
                text,
            ),
        ]
        header_height = sum(p.wrap(usable, 10000)[1] + p.getSpaceAfter() for p in header) + 8

        def frame(name, frame_height):
            return Frame(
                42,
                34,
                usable,
                frame_height,
                id=name,
                leftPadding=0,
                rightPadding=0,
                topPadding=0,
                bottomPadding=0,
            )

        pages = []

        def page(c, doc):
            pages.append(doc.page)
            c.setFont(font, 9)
            c.drawString(42, 18, project.title[:90])
            c.drawRightString(width - 42, 18, str(doc.page))
            if doc.page == 1:
                y = height - 32
                for p in header:
                    _, h = p.wrap(usable, 10000)
                    y -= h
                    p.drawOn(c, 42, y)
                    y -= p.getSpaceAfter()
            else:
                c.drawString(42, height - 23, project.title[:90] + " / Condensed")

        document = BaseDocTemplate(
            output, pagesize=(width, height), title=project.title, author=project.composer or "Mulec"
        )
        document.addPageTemplates(
            [
                PageTemplate(
                    id="first",
                    frames=[frame("first", height - 66 - header_height)],
                    onPage=page,
                    autoNextPageTemplate="later",
                ),
                PageTemplate(id="later", frames=[frame("later", height - 76)], onPage=page),
            ]
        )
        story = []
        for part in plan["parts"]:
            detail = f"{part['length']} bars"
            if part["ending"]:
                detail = f"Play {part['name']} 1-{part['from_bar'] - 1}, then ending below"
            title = Paragraph(escape(label(part)) + f" <font size='9'> / {escape(detail)}</font>", heading)
            items, offset = _items(part), 0
            part_rows = [[title]]
            previous_meter = (project.meter.numerator, project.meter.denominator)
            while offset < len(items):
                row, widths = [], []
                for item in items[offset : offset + 6]:
                    if "reference" in item:
                        occupied = max(90, min(usable, stringWidth(item["reference"], font, 12) + 18))
                    else:
                        occupied = max(
                            78,
                            sum(
                                stringWidth(jazz_symbol(chord["symbol"]), font, size)
                                + (13 if len(item["chords"]) > 1 else 5)
                                for chord in item["chords"]
                            )
                            + 16,
                        )
                    occupied = min(usable, occupied)
                    if row and sum(widths) + occupied > usable:
                        break
                    row.append(item)
                    widths.append(occupied)
                slack = min(10, (usable - sum(widths)) / len(row))
                row_flow = ChordRow(row, [w + slack for w in widths], size, previous_meter)
                part_rows.append([row_flow])
                for item in row:
                    if "reference" not in item:
                        previous_meter = (item["meter"]["numerator"], item["meter"]["denominator"])
                offset += len(row)
            story.append(
                Table(
                    part_rows,
                    colWidths=[usable],
                    repeatRows=1,
                    hAlign="LEFT",
                    style=[
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ],
                )
            )
            story.append(Spacer(1, 8))
        if not story:
            story.append(Paragraph("No measures yet.", text))
        document.build(story)
        return output.getvalue(), len(pages)

    for size in (16, 15, 14, 13, 12):
        content, count = build(size)
        if count <= 2:
            break
    return content
