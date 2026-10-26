"""Line-art scenes for examples/normaltech.txt.

One function per line. `u` runs from 0 to 1 across that line's aligned times.
Drawings stay in the upper two thirds; lyrics are composited later, in the
bottom third, with the keywords listed here drawn in cyan.

This is the reference shape: near-black, amber and cyan line-art with bloom,
objects that draw themselves on, a slow camera push (handled by the scene
player), and a crossfade when the line changes.
"""
import os
from lv_art import (bar_chart, building, calendar, clock, crowd, diminish_curve,
                    hud_rings, medal, neon_sign, network, robot, safe_stage,
                    shelf, sun_rays, terminal)

DESCRIPTION = "Neon line-art, one illustrated scene per line. Amber and cyan on near-black."
LYRICS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples", "normaltech.txt")
CROSSFADE = 0.7
PALETTE = dict(bg=(6, 7, 11), line=(220, 226, 232), amber=(255, 176, 48), cyan=(72, 216, 226), dim=(86, 98, 114))
SECTION_TITLES = {
    "intro": "a tool",
    "verse": "the shelf",
    "chorus": "build",
    "bridge": "a million",
    "outro": "lamp",
}

def _stage(board):
    return safe_stage(board)

def draw_spread(board, ctx, line, u, st):
    x0, y0, x1, y1 = _stage(board)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    sun_rays(board, cx, cy, 22, u, n=18, ray=1.5)
    network(board, (x0 + 30, y0 + 20, x1 - 30, y1 - 10), u)
    board.label((x0, y0), "SPREAD", board.p["amber"])

def draw_shelf(board, ctx, line, u, st):
    x0, y0, x1, y1 = _stage(board)
    shelf(board, x0 + 10, y0 + 78, (x1 - x0) * 0.42, u)
    medal(board, x0 + 80, y0 + 42, 26, u)
    bar_chart(board, [3, 5, 8, 6, 9, 7], u, (x0 + (x1 - x0) * 0.48, y0 + 16, (x1 - x0) * 0.48, y1 - y0 - 36))
    board.label((x0, y1 - 8), "A PRIZE, AND THE BARS", board.p["dim"], 16)

def draw_year(board, ctx, line, u, st):
    x0, y0, x1, y1 = _stage(board)
    calendar(board, x0, y0 + 8, 230, 190, u, mark=(1, 5))
    clock(board, x1 - 110, y0 + 100, 62, u, hours=4.2)
    # a short run of towers, drawn on, standing in for the grid
    ground = y1 - 4
    for i, bw in enumerate((28, 36, 24)):
        building(board, x0 + 250 + i * 48, ground - 70 - i * 16, bw, 70 + i * 16, min(1, max(0, u - 0.05 * i)), floors=3, cols=2)
    board.label((x0, y0), "ONE YEAR", board.p["amber"])

def draw_robots(board, ctx, line, u, st):
    x0, y0, x1, y1 = _stage(board)
    ground = y1 - 6
    board.trace([(x0, ground), (x1, ground)], min(1, u * 2), board.p["dim"], 2)
    robot(board, (x0 + x1) * 0.38, ground, 130, u, board.p["cyan"], arm=0.8)
    robot(board, (x0 + x1) * 0.62, ground, 86, min(1, max(0, (u - 0.15) / 0.85)), board.p["line"], arm=-0.3)
    board.label((x0, y0), "ROBOTS, BUILDING", board.p["amber"])

def draw_curve(board, ctx, line, u, st):
    x0, y0, x1, y1 = _stage(board)
    diminish_curve(board, u, (x0, y0 + 8, x1 - x0, y1 - y0 - 24))
    board.label((x0, y1 - 6), "THE CURVE FLATTENS", board.p["dim"], 16)

def draw_minds(board, ctx, line, u, st):
    x0, y0, x1, y1 = _stage(board)
    crowd(board, (x0, y0 + 36, x1, y1), n=18, u=u, color=board.p["line"])
    board.count_up((x0, y0), 1000000, u, board.p["amber"], size=28)
    board.label((x0 + 220, y0 + 6), "MINDS", board.p["cyan"], 18)

def draw_log(board, ctx, line, u, st):
    x0, y0, x1, y1 = _stage(board)
    terminal(board, (x0, y0, x1 - x0, y1 - y0), [
        "$ tail -f /var/log/review",
        "queue: holding",
        "reader: present",
        "action: wait",
    ], u=u)
    hud_rings(board, x1 - 70, y0 + 56, 36, u * 0.8, t=st.get("t", 0))

def draw_lamp(board, ctx, line, u, st):
    x0, y0, x1, y1 = _stage(board)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 + 10
    sun_rays(board, cx, cy - 20, 26, u, n=12, ray=1.15, color=board.p["amber"])
    # a simple stand under the lamp
    board.trace([(cx, cy + 10), (cx, cy + 70), (cx - 36, cy + 70), (cx + 36, cy + 70)], min(1, u * 1.2), board.p["line"], 2)
    neon_sign(board, cx, y0 + 28, "STAYS LIT", u, color=board.p["amber"], swing=3.5, t=st.get("t", 0))

SCENES = [
    {"contains": "spread", "draw": draw_spread, "keywords": ["tool"]},
    {"contains": "shelf", "draw": draw_shelf, "keywords": ["prize", "bars"]},
    {"contains": "year", "draw": draw_year, "keywords": ["year"]},
    {"contains": "robots", "draw": draw_robots, "keywords": ["robots"]},
    {"contains": "curve", "draw": draw_curve, "keywords": ["curve"]},
    {"contains": "million", "draw": draw_minds, "keywords": ["million"]},
    {"contains": "log", "draw": draw_log, "keywords": ["log"]},
    {"contains": "lamp", "draw": draw_lamp, "keywords": ["lamp"]},
]
