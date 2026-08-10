#!/usr/bin/env python3
"""
render_heatmap_svg.py

Reads data/contributions.json (written by fetch_contributions.py) and
draws the classic 53-week x 7-day GitHub contribution calendar as
rounded, colored boxes. Reveals once with a diagonal line-after-line
slide-down (plays on load, then freezes - no looping), plus a
Less->More legend and a stats footer.

Usage:
    python scripts/render_heatmap_svg.py
"""

import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# none -> brightest. Level 5 here is a deliberate neon top end above
# GitHub's own level-4 cap, used only when a single day's count is in
# the very top percentile of this user's own activity (see
# level_for_count below) - makes truly exceptional days pop rather
# than clipping everything above "a lot" to the same green.
PALETTE = [
    "#161b22",  # 0 - no contributions
    "#0e4429",  # 1
    "#006d32",  # 2
    "#26a641",  # 3
    "#39d353",  # 4
    "#69f0a0",  # 5 - neon top end, exceptional days only
]

BOX_SIZE = 11
BOX_GAP = 3
BOX_RADIUS = 2

MARGIN_LEFT = 30   # room for day-of-week labels
MARGIN_TOP = 20    # room for month labels
MARGIN_RIGHT = 20
LEGEND_HEIGHT = 30
FOOTER_HEIGHT = 26

BG_COLOR = "#0d1117"
TEXT_COLOR = "#8b949e"
FONT_FAMILY = "'SF Mono','Fira Code','Consolas',monospace"

# Diagonal reveal timing: each week-column starts slightly after the
# previous, and within a column each day-row starts slightly after
# the one above - the combination produces a diagonal sweep.
COL_STAGGER = 0.035
ROW_STAGGER = 0.02
BOX_ANIM_DURATION = 0.35

MONTH_ABBR = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def level_for_count(count: int, sorted_nonzero: list[int]) -> int:
    """Map a day's count to a 0-5 palette index using quantiles of this
    user's own non-zero days, not a linear ratio of the single max.

    A linear ratio-of-max breaks down badly for real contribution data:
    one outlier day (e.g. a big merge commit day) stretches the scale
    so most ordinary days round down to the bottom bucket. Quantile
    bucketing (levels 1-4 at roughly the 25th/50th/75th/90th
    percentiles of non-zero days) keeps the four "normal activity"
    buckets meaningfully populated regardless of how skewed one
    person's activity happens to be. Level 5 is reserved for the
    top ~2% of non-zero days - an "exceptional day" callout.

    `sorted_nonzero` must be pre-sorted ascending and contain only
    counts > 0 (pass the same precomputed list for every call in a
    render - don't refilter/resort per day).
    """
    if count == 0:
        return 0
    if not sorted_nonzero:
        return 1

    def percentile(p: float) -> int:
        idx = min(len(sorted_nonzero) - 1, int(len(sorted_nonzero) * p))
        return sorted_nonzero[idx]

    p25, p50, p75, p90, p98 = (
        percentile(0.25), percentile(0.50), percentile(0.75),
        percentile(0.90), percentile(0.98),
    )

    if count >= p98 and count > p50:
        return 5
    elif count >= p90:
        return 4
    elif count >= p75:
        return 3
    elif count >= p50:
        return 2
    else:
        return 1


def build_week_grid(days: list[dict]) -> list[list[dict | None]]:
    """Arrange days into a list of weeks (columns), each a list of 7
    day-slots (Sun-Sat), matching GitHub's own calendar layout.

    Returns weeks in chronological order; each week is a 7-element
    list where index 0 = Sunday .. 6 = Saturday, and slots before the
    first real day or after the last are None (padding).
    """
    if not days:
        return []

    parsed = [
        {**d, "_date": datetime.strptime(d["date"], "%Y-%m-%d").date()}
        for d in days
    ]
    parsed.sort(key=lambda d: d["_date"])

    first_date = parsed[0]["_date"]
    last_date = parsed[-1]["_date"]

    # Back up to the Sunday on/before first_date so week columns align
    # to calendar weeks, matching GitHub's own grid.
    start = first_date - timedelta(days=(first_date.weekday() + 1) % 7)

    by_date = {d["_date"]: d for d in parsed}

    weeks = []
    current = start
    current_week = [None] * 7

    while current <= last_date:
        weekday_slot = (current.weekday() + 1) % 7  # Sun=0..Sat=6
        current_week[weekday_slot] = by_date.get(current)

        if weekday_slot == 6:
            weeks.append(current_week)
            current_week = [None] * 7

        current += timedelta(days=1)

    if any(slot is not None for slot in current_week):
        weeks.append(current_week)

    return weeks


def month_label_positions(weeks: list[list[dict | None]]) -> list[tuple[int, str]]:
    """Return (week_index, month_abbr) pairs for month labels, placed
    at the first week column where that month first appears.
    """
    labels = []
    seen_months = set()

    for week_idx, week in enumerate(weeks):
        for slot in week:
            if slot is None:
                continue
            d = datetime.strptime(slot["date"], "%Y-%m-%d").date()
            month_key = (d.year, d.month)
            if month_key not in seen_months:
                seen_months.add(month_key)
                labels.append((week_idx, MONTH_ABBR[d.month - 1]))
            break  # only need the first non-None slot per week

    return labels


def escape_xml(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_svg(data: dict) -> str:
    days = data["days"]
    stats = data["stats"]
    all_counts = [d["count"] for d in days]

    sorted_nonzero_counts = sorted(c for c in all_counts if c > 0)

    weeks = build_week_grid(days)
    num_weeks = len(weeks)

    grid_width = num_weeks * (BOX_SIZE + BOX_GAP) - BOX_GAP
    grid_height = 7 * (BOX_SIZE + BOX_GAP) - BOX_GAP

    total_width = MARGIN_LEFT + grid_width + MARGIN_RIGHT
    total_height = MARGIN_TOP + grid_height + LEGEND_HEIGHT + FOOTER_HEIGHT

    boxes_markup = []
    for week_idx, week in enumerate(weeks):
        for day_idx, slot in enumerate(week):
            if slot is None:
                continue

            level = level_for_count(slot["count"], sorted_nonzero_counts)
            color = PALETTE[level]

            x = MARGIN_LEFT + week_idx * (BOX_SIZE + BOX_GAP)
            y = MARGIN_TOP + day_idx * (BOX_SIZE + BOX_GAP)

            start_time = week_idx * COL_STAGGER + day_idx * ROW_STAGGER

            title = f"{slot['count']} contribution{'s' if slot['count'] != 1 else ''} on {slot['date']}"

            boxes_markup.append(f"""
      <rect x="{x}" y="{y}" width="{BOX_SIZE}" height="{BOX_SIZE}" rx="{BOX_RADIUS}"
            fill="{color}" opacity="0">
        <title>{escape_xml(title)}</title>
        <animate attributeName="opacity" from="0" to="1"
                 begin="{start_time:.3f}s" dur="{BOX_ANIM_DURATION}s" fill="freeze" />
        <animateTransform attributeName="transform" type="translate"
                           from="0 -6" to="0 0"
                           begin="{start_time:.3f}s" dur="{BOX_ANIM_DURATION}s"
                           fill="freeze" calcMode="spline"
                           keySplines="0.25 0.1 0.25 1" keyTimes="0;1" />
      </rect>""")

    month_labels = month_label_positions(weeks)
    month_labels_markup = []
    for week_idx, abbr in month_labels:
        x = MARGIN_LEFT + week_idx * (BOX_SIZE + BOX_GAP)
        month_labels_markup.append(
            f'<text x="{x}" y="{MARGIN_TOP - 6}" font-family="{FONT_FAMILY}" '
            f'font-size="10" fill="{TEXT_COLOR}">{abbr}</text>'
        )

    legend_y = MARGIN_TOP + grid_height + 20
    legend_markup = [
        f'<text x="{MARGIN_LEFT}" y="{legend_y}" font-family="{FONT_FAMILY}" '
        f'font-size="10" fill="{TEXT_COLOR}">Less</text>'
    ]
    legend_box_start_x = MARGIN_LEFT + 34
    for i, color in enumerate(PALETTE):
        x = legend_box_start_x + i * (BOX_SIZE + BOX_GAP)
        legend_markup.append(
            f'<rect x="{x}" y="{legend_y - 9}" width="{BOX_SIZE}" height="{BOX_SIZE}" '
            f'rx="{BOX_RADIUS}" fill="{color}" />'
        )
    more_x = legend_box_start_x + len(PALETTE) * (BOX_SIZE + BOX_GAP) + 4
    legend_markup.append(
        f'<text x="{more_x}" y="{legend_y}" font-family="{FONT_FAMILY}" '
        f'font-size="10" fill="{TEXT_COLOR}">More</text>'
    )

    footer_y = legend_y + FOOTER_HEIGHT
    total = stats["total_contributions"]
    streak = stats["current_streak"]
    footer_text = (
        f"{total:,} contributions in the last year"
        + (f"  \u2022  {streak} day streak" if streak > 0 else "")
    )
    footer_markup = (
        f'<text x="{MARGIN_LEFT}" y="{footer_y}" font-family="{FONT_FAMILY}" '
        f'font-size="11" fill="{TEXT_COLOR}">{escape_xml(footer_text)}</text>'
    )

    boxes_body = "".join(boxes_markup)
    months_body = "".join(month_labels_markup)
    legend_body = "".join(legend_markup)

    return f"""<svg viewBox="0 0 {total_width} {total_height:.0f}" width="{total_width}" height="{total_height:.0f}"
     xmlns="http://www.w3.org/2000/svg">
  <rect width="100%" height="100%" fill="{BG_COLOR}" />
  <g>{months_body}</g>
  <g>{boxes_body}
  </g>
  <g>{legend_body}</g>
  {footer_markup}
</svg>
"""


def main():
    data_path = Path("data/contributions.json")
    if not data_path.exists():
        print(
            f"[render_heatmap_svg] ERROR: {data_path} not found. "
            f"Run fetch_contributions.py first.",
            file=sys.stderr,
        )
        sys.exit(1)

    data = json.loads(data_path.read_text(encoding="utf-8"))
    svg = build_svg(data)

    out_path = Path("contrib-heatmap.svg")
    out_path.write_text(svg, encoding="utf-8")
    print(f"[render_heatmap_svg] wrote {out_path}")


if __name__ == "__main__":
    main()
