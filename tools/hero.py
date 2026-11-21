#!/usr/bin/env python3
"""Compose docs/assets/hero.png, the collage at the top of the README, from eight screenshots.

    python3 tools/screenshots.py     # capture the screens first
    python3 tools/hero.py

Needs Pillow (``pip install pillow``); pngquant is used to shrink the result when it is installed.
"""
import os
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREENS = os.path.join(ROOT, "docs", "assets", "screens")
OUT = os.path.join(ROOT, "docs", "assets", "hero.png")
PICKS = ["landing-fluidian", "store-kordo", "dash-devops", "landing-canvasly", "mobile-themes", "dash-projects", "store-crate", "dash-trading"]
WIDTH, PAD, GAP, COLUMNS, RADIUS = 2400, 44, 26, 4, 22
GLOWS = [(0.08, 0.02, 700, (0, 0, 255, 150)), (0.94, 0.98, 680, (0, 0, 255, 110)), (0.60, 0.00, 520, (126, 200, 227, 44))]   # the Deep Blue palette


def rounded_mask(width, height, radius):
    mask = Image.new("L", (width * 2, height * 2), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, width * 2 - 1, height * 2 - 1), radius * 2, fill=255)
    return mask.resize((width, height), Image.LANCZOS)


def main():
    files = sorted(f for f in os.listdir(SCREENS) if f.endswith(".png"))
    by_slug = {f.split("-", 1)[1][:-4]: f for f in files}
    missing = [p for p in PICKS if p not in by_slug]
    if missing:
        sys.exit("Missing screenshots: %s. Run tools/screenshots.py first." % ", ".join(missing))
    cell_w = (WIDTH - 2 * PAD - (COLUMNS - 1) * GAP) // COLUMNS
    cell_h = int(cell_w * 0.64)
    rows = (len(PICKS) + COLUMNS - 1) // COLUMNS
    height = 2 * PAD + rows * cell_h + (rows - 1) * GAP
    canvas = Image.linear_gradient("L").rotate(-60, expand=True).resize((WIDTH, height))
    canvas = Image.merge("RGB", [canvas.point(lambda v, a=a, b=b: a + (b - a) * v // 255) for a, b in ((0, 5), (12, 10), (102, 48))]).convert("RGBA")
    glow = Image.new("RGBA", (WIDTH, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    for fx, fy, radius, colour in GLOWS:
        cx, cy = int(WIDTH * fx), int(height * fy)
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=colour)
    canvas = Image.alpha_composite(canvas, glow.filter(ImageFilter.GaussianBlur(220)))
    mask = rounded_mask(cell_w, cell_h, RADIUS)
    for index, slug in enumerate(PICKS):
        shot = Image.open(os.path.join(SCREENS, by_slug[slug])).convert("RGB")
        shot = shot.resize((cell_w, int(shot.height * cell_w / shot.width)), Image.LANCZOS).crop((0, 0, cell_w, cell_h))
        x, y = PAD + (index % COLUMNS) * (cell_w + GAP), PAD + (index // COLUMNS) * (cell_h + GAP)
        shadow = Image.new("RGBA", (WIDTH, height), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle((x, y + 14, x + cell_w, y + cell_h + 14), RADIUS, fill=(0, 0, 0, 150))
        canvas = Image.alpha_composite(canvas, shadow.filter(ImageFilter.GaussianBlur(22)))
        canvas.paste(shot, (x, y), mask)
        edge = Image.new("RGBA", (WIDTH, height), (0, 0, 0, 0))
        ImageDraw.Draw(edge).rounded_rectangle((x, y, x + cell_w - 1, y + cell_h - 1), RADIUS, outline=(255, 255, 255, 46), width=2)
        canvas = Image.alpha_composite(canvas, edge)
    out = Image.new("RGBA", (WIDTH, height), (0, 0, 0, 0))
    out.paste(canvas, (0, 0), rounded_mask(WIDTH, height, 28))
    out.save(OUT)
    if shutil.which("pngquant"):
        subprocess.run(["pngquant", "--force", "--quality=75-95", "--ext", ".png", OUT], check=False)
    print("%s  %dx%d  %d KB" % (os.path.relpath(OUT, ROOT), WIDTH, height, os.path.getsize(OUT) // 1024))


if __name__ == "__main__":
    main()
