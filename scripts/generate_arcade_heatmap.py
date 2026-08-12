#!/usr/bin/env python3
"""Generate a crisp, looping arcade-style GitHub contribution heatmap GIF."""

import argparse
import datetime
import random
from PIL import Image, ImageDraw, ImageFont

WEEKS = 53
DAYS = 7
CELL = 11
GAP = 3
PITCH = CELL + GAP
LEFT_MARGIN = 14
RIGHT_MARGIN = 14
TOP_MARGIN = 24
SHIP_LANE_H = 34
GRID_W = WEEKS * PITCH - GAP
GRID_H = DAYS * PITCH - GAP
CANVAS_W = LEFT_MARGIN + GRID_W + RIGHT_MARGIN
CANVAS_H = TOP_MARGIN + GRID_H + SHIP_LANE_H

BG = (13, 17, 23)
GRID_EMPTY = (22, 27, 34)
LEVEL_COLORS = [
    GRID_EMPTY,
    (14, 68, 41),
    (0, 109, 50),
    (38, 166, 65),
    (57, 211, 83),
]
TEXT_COLOR = (139, 148, 158)
SHIP_COLOR = (88, 166, 255)
SHIP_ACCENT = (240, 246, 252)
BULLET_COLOR = (255, 214, 102)
EXPLOSION_COLORS = [(255, 245, 170), (255, 190, 70), (255, 100, 60)]

FIRE_INTERVAL = 3
BULLET_SPEED = 9
EXPLOSION_LIFE = 5
ATTACK_FRAMES = 90
REBUILD_FRAMES = 24
TOTAL_FRAMES = ATTACK_FRAMES + REBUILD_FRAMES
FRAME_MS = 55

SHIP_BITMAP = [
    "....#....",
    "...###...",
    "..#####..",
    ".##.#.##.",
    "#########",
]


def make_grid(seed=42):
    rng = random.Random(seed)
    grid = [[0] * DAYS for _ in range(WEEKS)]
    for w in range(WEEKS):
        base = rng.random()
        for d in range(DAYS):
            r = rng.random()
            if base < 0.15:
                lvl = 0 if r < 0.7 else rng.choice([1, 2])
            elif base < 0.6:
                lvl = 0 if r < 0.35 else rng.choice([1, 1, 2, 3])
            else:
                lvl = 0 if r < 0.15 else rng.choice([1, 2, 3, 3, 4])
            grid[w][d] = lvl
    return grid


def month_labels(weeks):
    today = datetime.date.today()
    start = today - datetime.timedelta(weeks=weeks - 1)
    start -= datetime.timedelta(days=(start.weekday() + 1) % 7)
    labels = {}
    last_month = None
    for w in range(weeks):
        col_date = start + datetime.timedelta(weeks=w)
        if col_date.month != last_month:
            labels[w] = col_date.strftime("%b")
            last_month = col_date.month
    return labels


def cell_xy(week, day):
    return LEFT_MARGIN + week * PITCH, TOP_MARGIN + day * PITCH


def draw_grid(draw, grid, font, labels):
    for w, label in labels.items():
        x, _ = cell_xy(w, 0)
        draw.text((x, 3), label, fill=TEXT_COLOR, font=font)
    for w in range(WEEKS):
        for d in range(DAYS):
            x, y = cell_xy(w, d)
            draw.rounded_rectangle(
                [x, y, x + CELL - 1, y + CELL - 1], radius=2,
                fill=LEVEL_COLORS[grid[w][d]]
            )


def draw_ship(draw, cx, base_y, scale=2):
    x0 = int(cx - len(SHIP_BITMAP[0]) * scale / 2)
    y0 = base_y - len(SHIP_BITMAP) * scale
    for j, row in enumerate(SHIP_BITMAP):
        for i, ch in enumerate(row):
            if ch == "#":
                fill = SHIP_ACCENT if j == 0 else SHIP_COLOR
                draw.rectangle(
                    [x0 + i * scale, y0 + j * scale,
                     x0 + (i + 1) * scale - 1, y0 + (j + 1) * scale - 1],
                    fill=fill,
                )


def draw_bullet(draw, x, y):
    draw.rounded_rectangle([x - 2, y - 6, x + 1, y], radius=1, fill=BULLET_COLOR)


def draw_explosion(draw, x, y, age):
    color = EXPLOSION_COLORS[min(age // 2, len(EXPLOSION_COLORS) - 1)]
    r = 2 + age * 2
    draw.line((x, y - r, x, y + r), fill=color, width=2)
    draw.line((x - r, y, x + r, y), fill=color, width=2)
    draw.point((x, y), fill=(255, 255, 220))


def col_center_x(week):
    x, _ = cell_xy(week, 0)
    return x + CELL / 2


def load_font(size=11):
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def build_frames():
    original = make_grid()
    grid = [row[:] for row in original]
    labels = month_labels(WEEKS)
    font = load_font(10)

    ship_min_x = LEFT_MARGIN + CELL
    ship_max_x = LEFT_MARGIN + GRID_W - CELL
    ship_y = CANVAS_H - 7
    bullets = []
    explosions = []
    frames = []
    destroyed_order = []

    for f in range(TOTAL_FRAMES):
        img = Image.new("RGB", (CANVAS_W, CANVAS_H), BG)
        draw = ImageDraw.Draw(img)

        half = ATTACK_FRAMES / 2
        if f < ATTACK_FRAMES:
            if f < half:
                t = f / max(1, half - 1)
                ship_x = ship_min_x + t * (ship_max_x - ship_min_x)
            else:
                t = (f - half) / max(1, half - 1)
                ship_x = ship_max_x - t * (ship_max_x - ship_min_x)

            if f > 0 and f % FIRE_INTERVAL == 0:
                col = min(WEEKS - 1, max(0, round((ship_x - LEFT_MARGIN) / PITCH)))
                bullets.append({"week": col, "x": col_center_x(col), "y": ship_y - 10})

            alive = []
            for b in bullets:
                b["y"] -= BULLET_SPEED
                row = int((b["y"] - TOP_MARGIN) / PITCH)
                if 0 <= row < DAYS and grid[b["week"]][row] != 0:
                    grid[b["week"]][row] = 0
                    destroyed_order.append((b["week"], row))
                    ex, ey = cell_xy(b["week"], row)
                    explosions.append({"x": ex + CELL // 2, "y": ey + CELL // 2, "age": 0})
                    continue
                if b["y"] >= TOP_MARGIN - 8:
                    alive.append(b)
            bullets = alive
        else:
            rt = (f - ATTACK_FRAMES) / max(1, REBUILD_FRAMES - 1)
            ship_x = ship_min_x + (ship_max_x - ship_min_x) * (0.15 + 0.2 * rt)
            bullets = []
            n_restore = int(round(rt * len(destroyed_order)))
            for w, d in destroyed_order[:n_restore]:
                grid[w][d] = original[w][d]
            if f == TOTAL_FRAMES - 1:
                grid = [row[:] for row in original]

        active_explosions = []
        for e in explosions:
            e["age"] += 1
            if e["age"] <= EXPLOSION_LIFE:
                active_explosions.append(e)
        explosions = active_explosions

        draw_grid(draw, grid, font, labels)
        for b in bullets:
            draw_bullet(draw, int(b["x"]), int(b["y"]))
        for e in explosions:
            draw_explosion(draw, e["x"], e["y"], e["age"])
        draw_ship(draw, ship_x, ship_y)
        frames.append(img)

    return frames


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="contrib-heatmap-arcade.gif")
    args = ap.parse_args()
    frames = build_frames()

    # Keep the full palette large enough for crisp greens, text and effects.
    palette = frames[0].quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    quantized = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    quantized[0].save(
        args.out,
        save_all=True,
        append_images=quantized[1:],
        duration=FRAME_MS,
        loop=0,
        optimize=False,
        disposal=2,
    )
    print(f"Wrote {args.out}: {len(frames)} frames, canvas {CANVAS_W}x{CANVAS_H}")


if __name__ == "__main__":
    main()
