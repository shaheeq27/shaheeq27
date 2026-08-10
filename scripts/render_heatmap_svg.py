#!/usr/bin/env python3
"""Render a dense terminal-style contribution/activity heatmap.

The README artwork is intentionally more visually saturated than the
live GitHub contribution graph shown lower on the profile. Real
contribution data is used to seed the palette, while empty days get
deterministic decorative tiles so the banner has the dense visual
treatment of the reference design.
"""

import hashlib
import json
import calendar
from datetime import datetime, timedelta
from pathlib import Path

PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353", "#69f0a0"]
BOX_SIZE, BOX_GAP = 11, 3
MARGIN_LEFT, MARGIN_TOP, MARGIN_RIGHT = 30, 20, 20
WEEKS = 53
FONT = "'SF Mono','Fira Code','Consolas',monospace"


def decorative_level(day, count):
    if count > 0:
        return min(5, max(1, int(count)))
    h = int(hashlib.sha256(f"shaheeq27:{day}".encode()).hexdigest()[:8], 16)
    r = h % 100
    if r < 6:
        return 0
    if r < 28:
        return 1
    if r < 52:
        return 2
    if r < 76:
        return 3
    if r < 93:
        return 4
    return 5


def main():
    data = json.loads(Path("data/contributions.json").read_text())
    by_date = {d["date"]: d["count"] for d in data["days"]}

    start = datetime.strptime(data["days"][0]["date"], "%Y-%m-%d").date()
    start -= timedelta(days=(start.weekday() + 1) % 7)

    grid_width = WEEKS * (BOX_SIZE + BOX_GAP) - BOX_GAP
    grid_height = 7 * (BOX_SIZE + BOX_GAP) - BOX_GAP
    legend_y = MARGIN_TOP + grid_height + 20
    footer_y = legend_y + 26
    width = MARGIN_LEFT + grid_width + MARGIN_RIGHT
    height = footer_y + 12

    out = [
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        'xmlns="http://www.w3.org/2000/svg">',
        '<rect width="100%" height="100%" fill="#0d1117"/>',
    ]

    seen = set()
    for w in range(WEEKS):
        week_date = start + timedelta(days=w * 7)
        key = (week_date.year, week_date.month)
        if key not in seen:
            seen.add(key)
            x = MARGIN_LEFT + w * (BOX_SIZE + BOX_GAP)
            out.append(
                f'<text x="{x}" y="{MARGIN_TOP - 6}" font-family="{FONT}" '
                f'font-size="10" fill="#8b949e">{calendar.month_abbr[week_date.month]}</text>'
            )

        for d in range(7):
            day = start + timedelta(days=w * 7 + d)
            day_key = day.isoformat()
            level = decorative_level(day_key, by_date.get(day_key, 0))
            x = MARGIN_LEFT + w * (BOX_SIZE + BOX_GAP)
            y = MARGIN_TOP + d * (BOX_SIZE + BOX_GAP)
            out.append(
                f'<rect x="{x}" y="{y}" width="{BOX_SIZE}" height="{BOX_SIZE}" '
                f'rx="2" fill="{PALETTE[level]}"><title>Activity tile • {day_key}</title></rect>'
            )

    out.append(
        f'<text x="{MARGIN_LEFT}" y="{legend_y}" font-family="{FONT}" '
        'font-size="10" fill="#8b949e">Less</text>'
    )
    for i, color in enumerate(PALETTE):
        x = MARGIN_LEFT + 34 + i * (BOX_SIZE + BOX_GAP)
        out.append(
            f'<rect x="{x}" y="{legend_y - 9}" width="{BOX_SIZE}" height="{BOX_SIZE}" '
            f'rx="2" fill="{color}"/>'
        )
    more_x = MARGIN_LEFT + 34 + len(PALETTE) * (BOX_SIZE + BOX_GAP) + 4
    out.append(
        f'<text x="{more_x}" y="{legend_y}" font-family="{FONT}" '
        'font-size="10" fill="#8b949e">More</text>'
    )
    out.append(
        f'<text x="{MARGIN_LEFT}" y="{footer_y}" font-family="{FONT}" '
        'font-size="11" fill="#8b949e">activity matrix • live GitHub stats below</text>'
    )
    out.append("</svg>")

    Path("contrib-heatmap.svg").write_text("\n".join(out) + "\n", encoding="utf-8")
    print("[render_heatmap_svg] wrote dense contrib-heatmap.svg")


if __name__ == "__main__":
    main()
