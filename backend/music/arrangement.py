"""A playable arrangement with recurring parts and explicit changed endings."""

from backend.models import Measure, Project
from backend.music.chart_style import chord_changes, jazz_symbol


def sections(project: Project):
    starts = [i for i, m in enumerate(project.measures) if i == 0 or m.section.strip()]
    return [
        {"first": a, "end": b, "name": project.measures[a].section.strip() or "Opening"}
        for a, b in zip(starts, [*starts[1:], len(project.measures)])
    ]


def _signature(measure: Measure):
    # Include rhythm, slash bass, cues and melody. Only redundant carry symbols collapse.
    changes = []
    for chord in sorted(measure.chords, key=lambda c: c.beat):
        if not changes or changes[-1][1] != chord.symbol or chord.manual:
            changes.append((chord.beat, chord.symbol))
    return (
        measure.meter.numerator,
        measure.meter.denominator,
        tuple(changes),
        measure.cue,
        tuple((n.beat, n.duration, n.midi) for n in measure.notes),
        measure.repeat_start,
        measure.repeat_end,
    )


def blocks(measures: list[Measure], offset=0):
    """Find adjacent exact repetitions without discarding a musical change."""
    signatures = [_signature(m) for m in measures]
    result = []
    i = 0
    while i < len(measures):
        best_size, best_count, saved = 1, 1, 0
        for size in range(1, min(16, (len(measures) - i) // 2) + 1):
            chunk = measures[i : i + size]
            if not any(c.symbol not in {"?", "NC", "N.C."} for m in chunk for c in m.chords):
                continue
            count = 1
            while (
                i + (count + 1) * size <= len(measures)
                and signatures[i : i + size] == signatures[i + count * size : i + (count + 1) * size]
                and not any(m.repeat_start or m.repeat_end for m in measures[i : i + (count + 1) * size])
            ):
                count += 1
            if size * (count - 1) > saved:
                best_size, best_count, saved = size, count, size * (count - 1)
        if best_count == 1 and result and result[-1]["times"] == 1:
            result[-1]["bars"].append(measures[i].model_dump())
        else:
            result.append(
                {
                    "first": offset + i + 1,
                    "times": best_count,
                    "bars": [m.model_dump() for m in measures[i : i + best_size]],
                }
            )
        i += best_size * best_count
    return result


def _condense(parts, signatures):
    """Reference exact earlier printed phrases; never reference another reference."""
    phrases = {}

    def eligible(bar):
        return (
            not bar["repeat_start"]
            and not bar["repeat_end"]
            and any(c["symbol"] not in {"?", "NC", "N.C."} for c in bar["chords"])
            and all(c["symbol"] != "?" for c in bar["chords"])
        )

    for part in parts:
        condensed = []
        for block in part["blocks"]:
            bars, start = block["bars"], 0
            pending = []
            pending_first = block["first"]
            keys = [signatures[bar["id"]] for bar in bars]
            while start < len(bars):
                best = None
                if start + 4 <= len(bars) and all(eligible(bar) for bar in bars[start : start + 4]):
                    for source, source_block, offset in phrases.get(tuple(keys[start : start + 4]), []):
                        source_bars = source_block["bars"]
                        length = 4
                        while start + length < len(bars) and offset + length < len(source_bars):
                            target = bars[start + length]
                            if (
                                not eligible(target)
                                or signatures[target["id"]] != signatures[source_bars[offset + length]["id"]]
                            ):
                                break
                            length += 1
                        # A repeated block stays a single unit unless all of it matches.
                        if block["times"] > 1 and (start != 0 or length != len(bars)):
                            continue
                        if best is None or length > best[0]:
                            best = (length, source, source_block, offset)
                if best:
                    if pending:
                        condensed.append({"first": pending_first, "times": 1, "bars": pending})
                        pending = []
                    length, source, source_block, offset = best
                    condensed.append(
                        {
                            "first": block["first"] + start,
                            "times": block["times"],
                            "bars": [],
                            "reference": {
                                "name": source["name"],
                                "variant": source["variant"],
                                "first": source_block["first"] + offset,
                                "length": length,
                            },
                        }
                    )
                    start += length
                    pending_first = block["first"] + start
                else:
                    pending.append(bars[start])
                    start += 1
            if pending:
                condensed.append({"first": pending_first, "times": block["times"], "bars": pending})
        part["blocks"] = condensed
        for block in condensed:
            bars = block["bars"]
            for offset in range(len(bars) - 3):
                chunk = bars[offset : offset + 4]
                if all(eligible(bar) for bar in chunk):
                    key = tuple(signatures[bar["id"]] for bar in chunk)
                    phrases.setdefault(key, []).append((part, block, offset))


def arrangement(project: Project, *, condensed=False):
    parts, order = [], []
    groups = {}
    for occurrence in sections(project):
        name = occurrence["name"]
        key = name.casefold()
        bars = project.measures[occurrence["first"] : occurrence["end"]]
        signature = [_signature(m) for m in bars]
        group = groups.setdefault(key, [])
        match = next((p for p in group if p["_signature"] == signature), None)
        if match is None:
            prefix = 0
            if group:
                reference = group[0]["_signature"]
                while prefix < min(len(reference), len(signature)) and reference[prefix] == signature[prefix]:
                    prefix += 1
            # Print a changed ending on its own when the opening is already written.
            ending = prefix >= 4 and prefix < len(bars)
            match = {
                "id": bars[0].id,
                "name": name,
                "variant": len(group),
                "ending": ending,
                "from_bar": prefix + 1 if ending else 1,
                "length": len(bars),
                "blocks": blocks(bars[prefix:] if ending else bars, prefix if ending else 0),
                "_signature": signature,
            }
            group.append(match)
            parts.append(match)
        order.append(
            {
                "id": bars[0].id,
                "part": match["id"],
                "name": name,
                "variant": match["variant"],
                "first": occurrence["first"],
                "end": occurrence["end"],
                "time": bars[0].start,
                "duration": bars[-1].end - bars[0].start,
            }
        )
    if condensed:
        _condense(parts, {bar.id: _signature(bar) for bar in project.measures})
    for part in parts:
        del part["_signature"]
        for block in part["blocks"]:
            for bar in block["bars"]:
                bar["chords"] = chord_changes(bar["chords"])
                for chord in bar["chords"]:
                    chord["display"] = jazz_symbol(chord["symbol"])
    written = sum(len(block["bars"]) for part in parts for block in part["blocks"])
    return {
        "parts": parts,
        "order": order,
        "written_bars": written,
        "total_bars": len(project.measures),
        "condensed": condensed,
    }
