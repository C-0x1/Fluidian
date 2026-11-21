#!/usr/bin/env python3
"""Regenerate the Fluidian brand assets from one definition.

    python3 tools/brand.py

Writes the logo (``runtime/logo.svg``, ``docs/assets/logo.svg``), the bare mark
(``docs/assets/mark.svg``), the wordmark for light and dark pages (``docs/assets/wordmark.svg``,
``wordmark-dark.svg``), the README
banner (``docs/assets/banner.svg``), the installable-app icons (``runtime/pwa/*.png``)
and the mark the runtime draws (``runtime/brand.js``).

The mark is a ribbon: one stroke bends from the top arm of an F into its stem, and
the crossbar is a wave. The palette is Deep Blue: a tile that falls from pure blue
through navy into midnight, and a ribbon that runs from white into sky blue.

Needs fontTools with brotli (``pip install fonttools brotli``) to outline the wordmark
from the bundled Inter, and ``rsvg-convert`` (librsvg) to rasterise the app icons.
"""
import io
import json
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "engine"))
from fluidian import __version__  # noqa: E402
from fluidian.colors import BRAND  # noqa: E402

BLUE, NAVY, SKY, MIDNIGHT, WHITE = BRAND["blue"], BRAND["navy"], BRAND["sky"], BRAND["midnight"], BRAND["white"]
BRIGHT = "#2f5bff"   # blue lifted far enough to read on midnight; used only for small accents in the banner

# The mark, drawn in a 64 x 64 box. Two strokes, round caps, one weight.
STEM = "M44.500 17H30c-6 0-10 4-10 10v20.500"
WAVE = "M20 34.500c4.500-4 9-4 12.800-.5s7.700 4 11.700-.3"
WEIGHT = 7.5


def gradient(ident, x1=16, y1=13, x2=46, y2=50):
    """The ribbon's paint: white into sky blue."""
    return ('<linearGradient id="%s" gradientUnits="userSpaceOnUse" x1="%s" y1="%s" x2="%s" y2="%s">'
            '<stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>' % (ident, x1, y1, x2, y2, WHITE, SKY))


def strokes(paint):
    return ('<g fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round" stroke-linejoin="round"><path d="%s"/><path d="%s"/></g>'
            % (paint, WEIGHT, STEM, WAVE))


def tile_defs(prefix=""):
    return (gradient(prefix + "g")
            + '<linearGradient id="%st" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="%s"/><stop offset=".52" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>' % (prefix, BLUE, NAVY, MIDNIGHT)
            + '<radialGradient id="%sa" cx="14%%" cy="6%%" r="70%%"><stop offset="0" stop-color="#3d6bff" stop-opacity=".85"/><stop offset="1" stop-color="%s" stop-opacity="0"/></radialGradient>' % (prefix, BLUE)
            + '<linearGradient id="%ss" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".34"/><stop offset=".55" stop-color="#fff" stop-opacity="0"/></linearGradient>' % prefix)


def tile(prefix="", radius=17.0, size=64):
    """The mark on its blue tile, as SVG elements in a ``size`` box."""
    r = radius
    return ('<rect width="{s}" height="{s}" rx="{r}" fill="url(#{p}t)"/><rect width="{s}" height="{s}" rx="{r}" fill="url(#{p}a)"/>'
            '<rect x=".5" y=".5" width="{i}" height="{i}" rx="{ri}" fill="none" stroke="url(#{p}s)"/>'
            .format(s=size, r=r, p=prefix, i=size - 1, ri=r - 0.5) + strokes("url(#%sg)" % prefix))


def logo_svg():
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="Fluidian">\n  <defs>%s</defs>\n  %s\n</svg>\n'
            % (tile_defs(), tile()))


def mark_svg():
    """The mark alone, in blue, for a light background of your own."""
    paint = ('<linearGradient id="g" gradientUnits="userSpaceOnUse" x1="16" y1="13" x2="46" y2="50"><stop offset="0" stop-color="%s"/>'
             '<stop offset="1" stop-color="%s"/></linearGradient>' % (BLUE, NAVY))
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="12 9 40 46" role="img" aria-label="Fluidian">\n  <defs>%s</defs>\n  %s\n</svg>\n'
            % (paint, strokes("url(#g)")))


def full_bleed_svg(inset):
    """A square icon with no rounded corners: the platform applies its own mask. ``inset`` shrinks the mark into the safe zone."""
    scale = 1 - 2 * inset
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><defs>%s</defs>'
            '<rect width="64" height="64" fill="url(#t)"/><rect width="64" height="64" fill="url(#a)"/>'
            '<g transform="translate(%s %s) scale(%s)">%s</g></svg>'
            % (tile_defs(), 64 * inset, 64 * inset, scale, strokes("url(#g)")))


# --- the wordmark: Inter, outlined so that it looks the same wherever the file is shown -----
def outline(text, size, weight=640, tracking=-0.032):
    """(path of the letters, path of the dots on the i's, advance width) for ``text`` set in the bundled Inter."""
    from fontTools.pens.recordingPen import DecomposingRecordingPen
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont

    font = TTFont(os.path.join(ROOT, "runtime", "fonts", "InterVariable.woff2"))
    axes = {axis.axisTag: axis for axis in font["fvar"].axes}
    place = {"wght": weight}
    if "opsz" in axes:
        place["opsz"] = axes["opsz"].maxValue   # the display cut: tighter and finer, meant for large sizes
    buffer = io.BytesIO()
    font.flavor = None
    instantiateVariableFont(font, place).save(buffer)
    font = TTFont(io.BytesIO(buffer.getvalue()))
    glyphs, cmap, upm = font.getGlyphSet(), font.getBestCmap(), font["head"].unitsPerEm
    scale = size / upm
    number = lambda v: ("%.2f" % v).rstrip("0").rstrip(".")  # noqa: E731
    letters, dots, x = SVGPathPen(glyphs, ntos=number), SVGPathPen(glyphs, ntos=number), 0.0
    for char in text:
        name = cmap[ord(char)]
        record = DecomposingRecordingPen(glyphs)
        glyphs[name].draw(record)
        contours, current = [], []
        for op, args in record.value:
            current.append((op, args))
            if op in ("closePath", "endPath"):
                contours.append(current)
                current = []
        if char == "i" and len(contours) > 1:   # the dot is the contour that sits highest
            top = max(contours, key=lambda c: min(p[1] for _, a in c for p in a if p is not None))
        else:
            top = None
        for contour in contours:
            pen = TransformPen(dots if contour is top else letters, (scale, 0, 0, -scale, x, 0))
            for op, args in contour:
                getattr(pen, op)(*args)
        x += (glyphs[name].width + tracking * upm) * scale
    return letters.getCommands(), dots.getCommands(), x - tracking * size


def wordmark_svg(dark=False):
    size, gap = 41, 17
    letters, dots, width = outline("Fluidian", size)
    total = 64 + gap + width + 2
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} 64" role="img" aria-label="Fluidian">\n'
            '  <defs>{defs}</defs>\n  {tile}\n'
            '  <g transform="translate({x} 46.500)"><path fill="{ink}" d="{letters}"/><path fill="{dot}" d="{dots}"/></g>\n</svg>\n'
            .format(w=total, defs=tile_defs(), tile=tile(), x=64 + gap, letters=letters, dots=dots,
                    ink=WHITE if dark else MIDNIGHT, dot=SKY if dark else BLUE))


def banner_svg():
    letters, dots, width = outline("Fluidian", 92, weight=660)
    sans = "Inter, 'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif"
    mono = "'JetBrains Mono', 'SF Mono', Menlo, Consolas, monospace"
    with open(os.path.join(ROOT, "spec", "capabilities.json"), encoding="utf-8") as fh:
        capabilities = len(json.load(fh)["capabilities"])
    with open(os.path.join(ROOT, "spec", "components.json"), encoding="utf-8") as fh:
        components = len(json.load(fh)["components"])
    from fluidian.colors import THEMES
    pills = [("%d AI capabilities" % capabilities, 206), ("%d components" % components, 176), ("%d themes" % len(THEMES), 132),
             ("14 languages", 156), ("iOS · Android · web · desktop", 292)]
    chips, x = [], 98
    for label, w in pills:
        chips.append('<g transform="translate(%d 326)"><rect width="%d" height="40" rx="20" fill="#ffffff" fill-opacity=".07" stroke="#ffffff" stroke-opacity=".16"/>'
                     '<text x="%d" y="26" text-anchor="middle">%s</text></g>' % (x, w, w // 2, label))
        x += w + 14
    return '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 400" role="img" aria-label="Fluidian — the AI-native UI framework">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{navy}"/><stop offset=".5" stop-color="{midnight}"/><stop offset="1" stop-color="#03061f"/></linearGradient>
    <linearGradient id="brand" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{white}"/><stop offset="1" stop-color="{sky}"/></linearGradient>
    <linearGradient id="line" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{bright}"/><stop offset="1" stop-color="{sky}"/></linearGradient>
    {tile_defs}
    <radialGradient id="glowA" cx="8%" cy="0%" r="55%"><stop offset="0" stop-color="{blue}" stop-opacity=".85"/><stop offset="1" stop-color="{blue}" stop-opacity="0"/></radialGradient>
    <radialGradient id="glowB" cx="96%" cy="104%" r="55%"><stop offset="0" stop-color="{blue}" stop-opacity=".55"/><stop offset="1" stop-color="{blue}" stop-opacity="0"/></radialGradient>
    <radialGradient id="glowC" cx="62%" cy="-10%" r="40%"><stop offset="0" stop-color="{sky}" stop-opacity=".22"/><stop offset="1" stop-color="{sky}" stop-opacity="0"/></radialGradient>
    <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse"><path d="M32 0H0V32" fill="none" stroke="#ffffff" stroke-opacity=".045"/></pattern>
  </defs>
  <rect width="1280" height="400" rx="28" fill="url(#bg)"/>
  <rect width="1280" height="400" rx="28" fill="url(#glowA)"/>
  <rect width="1280" height="400" rx="28" fill="url(#glowB)"/>
  <rect width="1280" height="400" rx="28" fill="url(#glowC)"/>
  <rect width="1280" height="400" rx="28" fill="url(#grid)"/>
  <path d="M560 30c90-34 170-30 250 0s150 30 230-4 150-30 250 6" fill="none" stroke="url(#line)" stroke-width="1.6" stroke-opacity=".5"/>
  <path d="M520 300c110-40 200-34 300 0s190 30 280-6 130-26 190-8" fill="none" stroke="url(#line)" stroke-width="1.2" stroke-opacity=".32"/>

  <g transform="translate(96 84) scale(1.5625)">{tile}</g>
  <g transform="translate(224 168)"><path fill="{white}" d="{letters}"/><path fill="{sky}" d="{dots}"/></g>
  <text x="98" y="250" font-family="{sans}" font-size="34" font-weight="600" letter-spacing="-.6" fill="{sky}">The AI-native UI framework</text>
  <text x="98" y="298" font-family="{sans}" font-size="21" fill="#c9d6f5">Write the interface once, in any of 14 languages. The kernel makes it understand people.</text>

  <g font-family="{sans}" font-size="17" font-weight="600" fill="#eef3ff">
    {chips}
  </g>

  <g transform="translate(912 52)" font-family="{mono}" font-size="15">
    <rect width="290" height="212" rx="16" fill="#03061f" fill-opacity=".72" stroke="#ffffff" stroke-opacity=".16"/>
    <circle cx="22" cy="22" r="5" fill="{sky}"/><circle cx="40" cy="22" r="5" fill="{bright}"/><circle cx="58" cy="22" r="5" fill="{white}" fill-opacity=".7"/>
    <text x="20" y="62" fill="#8fa3d8">ui.table()</text>
    <text x="38" y="88" fill="#eef3ff">.prop(<tspan fill="{sky}">"rows"</tspan>, invoices)</text>
    <text x="38" y="114" fill="#eef3ff">.ai(<tspan fill="#9db4ff">"data.query"</tspan>)</text>
    <text x="20" y="150" fill="#8fa3d8">ui.input(<tspan fill="{sky}">"when"</tspan>)</text>
    <text x="38" y="178" fill="#eef3ff">.ai(<tspan fill="#9db4ff">"input.natural_date"</tspan>)</text>
  </g>
</svg>
'''.format(blue=BLUE, navy=NAVY, sky=SKY, midnight=MIDNIGHT, white=WHITE, bright=BRIGHT, tile_defs=tile_defs(), tile=tile(),
           letters=letters, dots=dots, sans=sans, mono=mono, chips="\n    ".join(chips))


def runtime_js():
    """The mark as the browser runtime draws it (NavBar and Footer with ``logo="fluidian"``, the gallery's rail, DevTools)."""
    data = {"stem": STEM, "wave": WAVE, "weight": WEIGHT, "tile": [[0, BLUE], [0.52, NAVY], [1, MIDNIGHT]], "ribbon": [[0, WHITE], [1, SKY]]}
    return ("// The Fluidian mark. Generated by tools/brand.py; edit the definition there.\n"
            "export const FLUIDIAN_MARK = %s;\n" % json.dumps(data, indent=2))


def write(path, text):
    full = os.path.join(ROOT, path)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(text)
    print("wrote %s" % path)


def raster(svg, path, size):
    full = os.path.join(ROOT, path)
    subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size), "-o", full], input=svg.encode("utf-8"), check=True)
    if shutil.which("pngquant"):
        subprocess.run(["pngquant", "--force", "--quality=80-98", "--ext", ".png", full], check=False)
    print("wrote %s (%d x %d)" % (path, size, size))


def main():
    write("runtime/logo.svg", logo_svg())
    write("docs/assets/logo.svg", logo_svg())
    write("docs/assets/mark.svg", mark_svg())
    write("runtime/brand.js", runtime_js())
    try:
        write("docs/assets/wordmark.svg", wordmark_svg())
        write("docs/assets/wordmark-dark.svg", wordmark_svg(dark=True))
        write("docs/assets/banner.svg", banner_svg())
    except ImportError as exc:
        sys.exit("The wordmark and banner need fontTools with brotli (pip install fonttools brotli): %s" % exc)
    if not shutil.which("rsvg-convert"):
        sys.exit("The app icons need rsvg-convert (sudo apt-get install librsvg2-bin); the SVG files above were written.")
    raster(logo_svg(), "runtime/pwa/icon-192.png", 192)
    raster(logo_svg(), "runtime/pwa/icon-512.png", 512)
    raster(full_bleed_svg(0.10), "runtime/pwa/maskable-512.png", 512)
    raster(full_bleed_svg(0.02), "runtime/pwa/apple-touch-icon.png", 180)
    print("Fluidian %s brand assets are up to date." % __version__)


if __name__ == "__main__":
    main()
