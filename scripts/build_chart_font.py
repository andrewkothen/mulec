"""Rebuild the OFL jazz font for both browser and ReportLab (development only).

Requires fontTools. The derivative is renamed to respect the reserved font name.
"""

from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont


def main():
    root = Path(__file__).resolve().parents[1] / "frontend/public/fonts"
    source = TTFont(root / "MuseJazzText.otf")
    glyph_set = source.getGlyphSet()
    order = source.getGlyphOrder() + ["mulecMajorTriangle"]
    glyphs = {}
    for name in source.getGlyphOrder():
        pen = TTGlyphPen(None)
        glyph_set[name].draw(Cu2QuPen(pen, max_err=1.0, reverse_direction=True))
        glyphs[name] = pen.glyph()
    # Standard Unicode triangle for readable, searchable major-chord shorthand.
    pen = TTGlyphPen(None)
    for points in [[(20, 0), (280, 540), (540, 0)], [(110, 55), (450, 55), (280, 415)]]:
        pen.moveTo(points[0])
        for point in points[1:]:
            pen.lineTo(point)
        pen.closePath()
    glyphs["mulecMajorTriangle"] = pen.glyph()
    cmap = source.getBestCmap() | {0x25B3: "mulecMajorTriangle", 0x0394: "mulecMajorTriangle"}
    builder = FontBuilder(source["head"].unitsPerEm, isTTF=True)
    builder.setupGlyphOrder(order)
    builder.setupCharacterMap(cmap)
    builder.setupGlyf(glyphs)
    builder.setupHorizontalMetrics(source["hmtx"].metrics | {"mulecMajorTriangle": (570, 20)})
    builder.setupHorizontalHeader(ascent=source["hhea"].ascent, descent=source["hhea"].descent)
    builder.setupNameTable(
        {
            "familyName": "Mulec Jazz",
            "styleName": "Regular",
            "uniqueFontIdentifier": "MulecJazz-1.0",
            "fullName": "Mulec Jazz",
            "psName": "MulecJazz",
            "version": "Version 1.0",
            "copyright": source["name"].getDebugName(0),
            "licenseDescription": source["name"].getDebugName(13),
            "licenseInfoURL": "https://openfontlicense.org",
        }
    )
    builder.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=1500, usWinDescent=500)
    builder.setupPost()
    for tag in ("GDEF", "GPOS", "GSUB"):
        builder.font[tag] = source[tag]
    builder.save(root / "MulecJazz.ttf")


if __name__ == "__main__":
    main()
