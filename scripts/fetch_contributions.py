#!/usr/bin/env python3
"""
fetch_contributions.py

Scrapes the public, no-auth contribution calendar fragment GitHub
serves at:

    https://github.com/users/shaheeq27/contributions

This is the same HTML fragment the profile page itself renders - no
GraphQL API, no personal access token needed. Writes data/contributions.json
with per-day data plus derived stats (streaks, best day, monthly totals).

Usage:
    python scripts/fetch_contributions.py

Reads GITHUB_USERNAME from the environment (falls back to the
constant below for local runs). In CI, set it via the workflow env
or repository variable.
"""

import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Fallback for local runs - the GitHub Actions workflow sets this via env.
DEFAULT_USERNAME = "shaheeq27"

USER_AGENT = "Mozilla/5.0 (compatible; profile-readme-bot/1.0)"

# Matches both tooltip wordings actually served by GitHub:
#   "No contributions on September 1st."      -> 0
#   "3 contributions on February 25th."        -> 3
#   "1 contribution on February 25th."         -> 1  (singular, no 's')
COUNT_PATTERN = re.compile(r"^(No|\d+)\s+contributions?\s+on", re.IGNORECASE)


def fetch_html(username: str) -> str:
    url = f"https://github.com/users/{username}/contributions"
    resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=15)
    resp.raise_for_status()
    return resp.text


def parse_count_from_tooltip(tooltip_text: str) -> int:
    """Extract the integer contribution count from tooltip text.

    Returns 0 for the "No contributions" wording, otherwise the parsed
    integer. Raises ValueError if the text doesn't match either known
    pattern, so a future GitHub markup change surfaces loudly instead
    of silently writing wrong data.
    """
    match = COUNT_PATTERN.match(tooltip_text.strip())
    if not match:
        raise ValueError(f"Unrecognized tooltip format: {tooltip_text!r}")
    token = match.group(1)
    return 0 if token.lower() == "no" else int(token)


def parse_contributions(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    cells = soup.select("td.ContributionCalendar-day")

    if not cells:
        raise RuntimeError(
            "No td.ContributionCalendar-day cells found - GitHub may have "
            "changed their markup, or the request was blocked/redirected "
            "(e.g. to a login page). Check the raw HTML."
        )

    days = []
    fallback_used = 0

    for cell in cells:
        date_str = cell.get("data-date")
        level_str = cell.get("data-level")
        if date_str is None or level_str is None:
            continue

        cell_id = cell.get("id")
        tooltip = soup.find("tool-tip", attrs={"for": cell_id}) if cell_id else None

        count = None
        if tooltip is not None:
            try:
                count = parse_count_from_tooltip(tooltip.get_text())
            except ValueError:
                count = None

        if count is None:
            # Fallback: no tooltip found or it didn't match expected
            # wording. Level is a coarse 0-4 bucket, not an exact count -
            # better than crashing the whole fetch over one malformed cell.
            fallback_used += 1
            count = int(level_str) if level_str.isdigit() else 0

        days.append({
            "date": date_str,
            "count": count,
            "level": int(level_str) if level_str.isdigit() else 0,
        })

    if fallback_used:
        print(
            f"[fetch_contributions] WARNING: {fallback_used}/{len(days)} days "
            f"fell back to level-based estimate (no matching tooltip found).",
            file=sys.stderr,
        )

    days.sort(key=lambda d: d["date"])
    return days


def compute_stats(days: list[dict]) -> dict:
    total = sum(d["count"] for d in days)

    # Longest streak + current streak (current = trailing streak ending
    # on the most recent day with count > 0, allowing today to be 0 if
    # the day isn't over yet - so we check from the end backwards and
    # stop at the first zero *after* we've seen the most recent data).
    longest_streak = 0
    running_streak = 0
    for d in days:
        if d["count"] > 0:
            running_streak += 1
            longest_streak = max(longest_streak, running_streak)
        else:
            running_streak = 0

    current_streak = 0
    for d in reversed(days):
        if d["count"] > 0:
            current_streak += 1
        else:
            break

    best_day = max(days, key=lambda d: d["count"]) if days else None

    monthly_totals = defaultdict(int)
    for d in days:
        month_key = d["date"][:7]  # YYYY-MM
        monthly_totals[d["date"][:7]] += d["count"]

    return {
        "total_contributions": total,
        "longest_streak": longest_streak,
        "current_streak": current_streak,
        "best_day": best_day,
        "monthly_totals": dict(sorted(monthly_totals.items())),
    }


def main():
    username = os.environ.get("GITHUB_USERNAME", DEFAULT_USERNAME)
    if username == DEFAULT_USERNAME:
        print(
            f"[fetch_contributions] WARNING: using placeholder username "
            f"'{DEFAULT_USERNAME}'. Set GITHUB_USERNAME env var to your "
            f"real username.",
            file=sys.stderr,
        )

    html = fetch_html(username)
    days = parse_contributions(html)
    stats = compute_stats(days)

    output = {
        "username": username,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "days": days,
        "stats": stats,
    }

    out_path = Path("data/contributions.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")

    print(
        f"[fetch_contributions] wrote {out_path} "
        f"({len(days)} days, {stats['total_contributions']} total contributions)"
    )


if __name__ == "__main__":
    main()
