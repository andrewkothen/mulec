"""A playable arrangement with recurring parts and explicit changed endings."""

from backend.models import Measure, Project


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
        if not changes or changes[-1][1] != chord.symbol:
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


def arrangement(project: Project):
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
    for part in parts:
        del part["_signature"]
    written = sum(len(block["bars"]) for part in parts for block in part["blocks"])
    return {"parts": parts, "order": order, "written_bars": written, "total_bars": len(project.measures)}
