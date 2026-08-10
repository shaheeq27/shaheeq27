#!/usr/bin/env python3
"""
make_info_card.py

Writes info-card.svg: a neofetch-style panel (title bar + colored
key/value rows) that fades and slides in line by line.

This is hand-authored, not image-derived - it's the "story numbers
can't tell" companion to the contribution heatmap, so the content
below (role, stack, highlights) is a template. Edit the ROWS list
to match your own background before using this on a real profile.

Usage:
    python scripts/make_info_card.py

Env vars:
    STATIC=1   emit a frozen (no-animation) frame, useful for local
               Quick Look / image-viewer previews where SMIL/CSS
               animation won't play anyway.
"""

import os
from pathlib import Path

TITLE = "shaheeq@github"
SEPARATOR_CHAR = "-"

# --- EDIT THIS to reflect your own background -----------------------
# Keep this distinct from the heatmap: the heatmap already shows your
# GitHub activity, so this card is for things a calendar can't show.
ROWS = [
    ("", "PROFILE"),
    ("Role", "Computer Science"),
    ("Focus", "AI / Full Stack"),
    ("", ""),
    ("", "STACK"),
    ("", "Python • C++ • TypeScript"),
    ("", "React • Next.js"),
    ("", ""),
    ("", "PROJECTS"),
    (">", "AgriNova"),
    (">", "Sudoholic"),
    (">", "DSA Learner"),
    ("", ""),
    ("", "LEARNING"),
    ("", "AI / LLMs / Systems"),
]
# ----------------------------------------------------------------------

LABEL_COLOR = "#39d353"   # GitHub contribution green, ties the two
                          # cards together visually
VALUE_COLOR = "#c9d1d9"
TITLE_COLOR = "#58a6ff"
BG_COLOR = "#0d1117"
BORDER_COLOR = "#30363d"

FONT_FAMILY = "'SF Mono','Fira Code','Consolas',monospace"
FONT_SIZE = 15
LINE_HEIGHT = 30
PADDING = 24

ROW_STAGGER = 0.18   # seconds between each line's fade-in start
FADE_DURATION = 0.4


def escape_xml(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_svg(static: bool) -> str:
    width = 490
    # title bar + separator + one line per row + top/bottom padding
    height = PADDING * 2 + LINE_HEIGHT * (len(ROWS) + 2)

    lines_markup = []
    y = PADDING + FONT_SIZE

    # Title line
    title_text = escape_xml(TITLE)
    lines_markup.append(
        f'<text x="{PADDING}" y="{y}" font-family="{FONT_FAMILY}" '
        f'font-size="{FONT_SIZE + 2}" font-weight="600" fill="{TITLE_COLOR}">{title_text}</text>'
    )
    y += LINE_HEIGHT

    # Separator
    sep_text = SEPARATOR_CHAR * 28
    lines_markup.append(
        f'<text x="{PADDING}" y="{y}" font-family="{FONT_FAMILY}" '
        f'font-size="{FONT_SIZE}" fill="{BORDER_COLOR}">{sep_text}</text>'
    )
    y += LINE_HEIGHT

    for i, (label, value) in enumerate(ROWS):
        start_time = (i + 2) * ROW_STAGGER

        if not label and not value:
            y += LINE_HEIGHT * 0.45
            continue

        if value in {"PROFILE", "STACK", "PROJECTS", "LEARNING"}:
            text = escape_xml(value)
            line_content = (
                f'<text x="{PADDING}" y="{y}" font-family="{FONT_FAMILY}" '
                f'font-size="{FONT_SIZE - 1}" font-weight="600" fill="{LABEL_COLOR}">'
                f'── {text} ─────────────────</text>'
            )
        elif label == ">":
            text = escape_xml(value)
            line_content = (
                f'<text x="{PADDING + 12}" y="{y}" font-family="{FONT_FAMILY}" '
                f'font-size="{FONT_SIZE}" fill="{VALUE_COLOR}">› {text}</text>'
            )
        elif not label:
            text = escape_xml(value)
            line_content = (
                f'<text x="{PADDING + 12}" y="{y}" font-family="{FONT_FAMILY}" '
                f'font-size="{FONT_SIZE}" fill="{VALUE_COLOR}">{text}</text>'
            )
        else:
            label_text = escape_xml(label)
            value_text = escape_xml(value)
            line_content = (
                f'<text x="{PADDING}" y="{y}" font-family="{FONT_FAMILY}" '
                f'font-size="{FONT_SIZE}" fill="{VALUE_COLOR}">'
                f'<tspan fill="{LABEL_COLOR}" font-weight="600">{label_text:<10}</tspan>'
                f'{value_text}</text>'
            )

        if not static:
            line_content = (
                f'<g opacity="0" transform="translate(-6 0)">'
                f'<animate attributeName="opacity" from="0" to="1" dur="0.35s" '
                f'begin="{start_time:.2f}s" fill="freeze" />'
                f'<animateTransform attributeName="transform" type="translate" '
                f'from="-6 0" to="0 0" dur="0.35s" fill="freeze" '
                f'begin="{start_time:.2f}s" />'
                f'{line_content}</g>'
            )

        lines_markup.append(line_content)
        y += LINE_HEIGHT

    return f"""<svg viewBox="0 0 {width} {height:.0f}" width="{width}" height="{height:.0f}"
     xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" rx="6" fill="{BG_COLOR}" stroke="{BORDER_COLOR}" stroke-width="1" />
  <g>{''.join(lines_markup)}
  </g>
</svg>
"""


def main():
    static = os.environ.get("STATIC") == "1"
    svg = build_svg(static)

    out_path = "info-card.svg"
    Path(out_path).write_text(svg, encoding="utf-8")
    print(f"[make_info_card] wrote {out_path}{' (static frame)' if static else ''}")


if __name__ == "__main__":
    main()
