#!/usr/bin/env python3
"""Render the contribution heatmap as a tiny arcade game.

The grid stays visually GitHub-like, while a small fighter flies below it,
fires upward, briefly knocks out cells, and lets them regenerate.
"""

import hashlib
import calendar
from datetime import date, timedelta
from pathlib import Path

PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]
BOX, GAP = 11, 3
LEFT, TOP, RIGHT = 30, 20, 20
WEEKS = 53
FONT = "'SF Mono','Fira Code','Consolas',monospace"
PLANE_Y = 150


def level(seed: str) -> int:
    value = int(hashlib.sha256(seed.encode()).hexdigest()[:8], 16) % 100
    if value < 14:
        return 0
    if value < 34:
        return 1
    if value < 58:
        return 2
    if value < 80:
        return 3
    if value < 94:
        return 4
    return 5


def main():
    width = LEFT + WEEKS * (BOX + GAP) - GAP + RIGHT
    grid_height = 7 * (BOX + GAP) - GAP
    height = 184

    start = date(2025, 8, 10)
    start -= timedelta(days=(start.weekday() + 1) % 7)

    months, seen = [], set()
    for week in range(WEEKS):
        d = start + timedelta(days=week * 7)
        key = (d.year, d.month)
        if key not in seen:
            seen.add(key)
            months.append((week, calendar.month_abbr[d.month]))

    out = [
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        'xmlns="http://www.w3.org/2000/svg">',
        '<rect width="100%" height="100%" fill="#0d1117"/>',
        '<defs>',
        '<pattern id="cells" width="98" height="98" patternUnits="userSpaceOnUse">',
    ]

    for row in range(7):
        for col in range(7):
            shade = [2, 3, 3, 4, 2, 4, 1][
                int(hashlib.sha256(f"base:{col}:{row}".encode()).hexdigest()[:8], 16) % 7
            ]
            out.append(
                f'<rect x="{col * 14}" y="{row * 14}" width="11" height="11" '
                f'rx="2" fill="{PALETTE[shade]}"/>'
            )

    out += [
        '</pattern>',
        '<style>.hit{transform-box:fill-box;transform-origin:center}.ship{filter:drop-shadow(0 0 2px #39d353)}.shot{fill:#69f0a0}</style>',
        '</defs>',
    ]

    for week, month in months:
        x = LEFT + week * 14
        out.append(
            f'<text x="{x}" y="14" font-family="{FONT}" font-size="10" fill="#8b949e">{month}</text>'
        )

    grid_width = WEEKS * (BOX + GAP) - GAP
    out.append(
        f'<rect x="{LEFT}" y="{TOP}" width="{grid_width}" height="{grid_height}" fill="url(#cells)"/>'
    )

    gaps = set()
    for week in range(WEEKS):
        for row in range(7):
            h = int(hashlib.sha256(f"gap:{week}:{row}".encode()).hexdigest()[:8], 16)
            if h % 100 < 18:
                gaps.add((week, row))

    targets = [(6, 3), (11, 5), (16, 2), (22, 4), (28, 1), (34, 5), (40, 1), (46, 4), (51, 2)]

    for week, row in gaps:
        if (week, row) in targets:
            continue
        x, y = LEFT + week * 14, TOP + row * 14
        out.append(f'<rect x="{x}" y="{y}" width="11" height="11" rx="2" fill="#161b22"/>')

    for week, row in targets:
        x, y = LEFT + week * 14, TOP + row * 14
        begin = ((x + 5 - 30) / (748 - 30)) * 6
        out += [
            f'<rect x="{x}" y="{y}" width="11" height="11" rx="2" fill="#39d353" class="hit">',
            f'<animate attributeName="opacity" values="1;0.04;1" keyTimes="0;0.5;1" begin="{begin:.2f}s" dur="1.1s" repeatCount="indefinite"/>',
            '</rect>',
        ]

    out += [
        '<g class="ship">',
        '<path d="M0 8 L10 0 L20 8 L16 8 L13 13 L7 13 L4 8 Z" fill="#c9d1d9"/>',
        '<path d="M7 8 L10 2 L13 8 Z" fill="#39d353"/>',
        '<rect x="8" y="11" width="4" height="4" rx="1" fill="#69f0a0"/>',
        '<path d="M2 10 L0 14 L5 12 Z M18 10 L20 14 L15 12 Z" fill="#39d353"/>',
        f'<animateTransform attributeName="transform" type="translate" values="30 {PLANE_Y};748 {PLANE_Y};30 {PLANE_Y}" keyTimes="0;0.5;1" dur="12s" repeatCount="indefinite"/>',
        '</g>',
    ]

    for week, row in targets:
        x, y = LEFT + week * 14, TOP + row * 14
        tx, ty = x + 5, y + 5
        begin = ((tx - 30) / (748 - 30)) * 6
        out += [
            '<g class="shot">',
            f'<rect x="{tx - 1.5}" y="{PLANE_Y - 10}" width="3" height="7" rx="1.5">',
            f'<animate attributeName="y" values="{PLANE_Y - 10};{ty}" begin="{begin:.2f}s" dur="0.55s" repeatCount="indefinite"/>',
            f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.05;.9;1" begin="{begin:.2f}s" dur="0.65s" repeatCount="indefinite"/>',
            '</rect>',
            '</g>',
        ]

    out.append('</svg>')
    Path("contrib-heatmap.svg").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("[render_heatmap_svg] wrote arcade contrib-heatmap.svg")


if __name__ == "__main__":
    main()
