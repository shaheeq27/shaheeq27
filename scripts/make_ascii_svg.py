#!/usr/bin/env python3
"""
make_ascii_svg.py

Converts source-prepped.png into avi-ascii.svg: a monochrome ASCII
portrait that prints itself row by row via SMIL animation, then
freezes (no looping).

Usage:
    python scripts/make_ascii_svg.py [prepped-image.png] [output.svg]

Defaults: source-prepped.png -> avi-ascii.svg
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

# Bright -> dark. Leading space is deliberate: it maps the brightest
# pixels (the white background from prep_photo.py) to "print nothing",
# so only the subject actually renders as visible characters.
RAMP = " .`:-=+*cs#%@"

GRID_COLS = 100
GRID_ROWS = 53

FONT_SIZE = 8
CHAR_W = FONT_SIZE * 0.6   # monospace advance width approximation
CHAR_H = FONT_SIZE * 1.0

FILL_COLOR = "#9aa5b1"     # single light-gray fill (monochrome by design)
BG_COLOR = "#0d1117"       # GitHub dark-mode background, so the SVG
                           # blends in whether the profile is viewed
                           # in light or dark mode

ROW_ANIM_DURATION = 0.55   # seconds per row wipe
ROW_STAGGER = 0.045        # seconds between each row's start time


def image_to_ascii_grid(img_path: str, cols: int, rows: int) -> list[list[str]]:
    img = Image.open(img_path).convert("L")
    img = img.resize((cols, rows), Image.LANCZOS)
    arr = np.array(img).astype(np.float32) / 255.0  # 0=black, 1=white

    ramp_len = len(RAMP)
    grid = []
    for r in range(rows):
        row_chars = []
        for c in range(cols):
            brightness = arr[r, c]
            # invert: bright pixel (1.0) -> index 0 (space)
            idx = int((1.0 - brightness) * (ramp_len - 1))
            idx = max(0, min(ramp_len - 1, idx))
            row_chars.append(RAMP[idx])
        grid.append(row_chars)
    return grid


def escape_xml(ch: str) -> str:
    return (
        ch.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_svg(grid: list[list[str]]) -> str:
    width = GRID_COLS * CHAR_W + 20
    height = GRID_ROWS * CHAR_H + 20

    rows_markup = []
    for r, row_chars in enumerate(grid):
        line = "".join(row_chars)
        # Skip fully-blank rows entirely - no point animating nothing
        if line.strip() == "":
            continue

        y = 10 + (r + 1) * CHAR_H
        text_content = "".join(escape_xml(ch) for ch in line)
        row_width = len(line) * CHAR_W

        start_time = r * ROW_STAGGER

        # Each row is clipped by a rect that animates its width from 0
        # to full, creating a left-to-right wipe. A small "cursor"
        # block rides the leading edge of the clip and disappears once
        # the row finishes - one clean pass, not a looping typewriter.
        clip_id = f"clip-row-{r}"
        rows_markup.append(f"""
    <clipPath id="{clip_id}">
      <rect x="10" y="{y - CHAR_H}" width="0" height="{CHAR_H + 2}">
        <animate attributeName="width" from="0" to="{row_width}"
                 begin="{start_time:.3f}s" dur="{ROW_ANIM_DURATION}s"
                 fill="freeze" calcMode="linear" />
      </rect>
    </clipPath>
    <g clip-path="url(#{clip_id})">
      <text x="10" y="{y}" font-family="'SF Mono','Fira Code','Consolas',monospace"
            font-size="{FONT_SIZE}" fill="{FILL_COLOR}" xml:space="preserve">{text_content}</text>
    </g>
    <rect x="10" y="{y - CHAR_H}" width="2" height="{CHAR_H + 2}" fill="{FILL_COLOR}" opacity="0.85">
      <animate attributeName="x" from="10" to="{10 + row_width}"
               begin="{start_time:.3f}s" dur="{ROW_ANIM_DURATION}s"
               fill="freeze" calcMode="linear" />
      <animate attributeName="opacity" from="0.85" to="0"
               begin="{start_time + ROW_ANIM_DURATION:.3f}s" dur="0.15s"
               fill="freeze" />
    </rect>""")

    body = "".join(rows_markup)

    return f"""<svg viewBox="0 0 {width:.0f} {height:.0f}" width="{width:.0f}" height="{height:.0f}"
     xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" fill="{BG_COLOR}" />
  <g>{body}
  </g>
</svg>
"""


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "source-prepped.png"
    out = sys.argv[2] if len(sys.argv) > 2 else "avi-ascii.svg"

    if not Path(src).exists():
        print(f"[make_ascii_svg] ERROR: {src} not found. Run prep_photo.py first.", file=sys.stderr)
        sys.exit(1)

    grid = image_to_ascii_grid(src, GRID_COLS, GRID_ROWS)
    svg = build_svg(grid)

    Path(out).write_text(svg, encoding="utf-8")
    print(f"[make_ascii_svg] wrote {out}")


if __name__ == "__main__":
    main()
