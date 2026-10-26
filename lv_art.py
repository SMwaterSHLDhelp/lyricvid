"""Neon line-art for per-line scenes.

Draw on a `Board`. Strokes are a crisp core plus a blurred copy, so the picture
reads as line-art with bloom and not as filled shapes. Pass `u` (0..1, the
fraction of the current lyric line) into the helpers to trace, draw on, or count.

Keep drawings in the upper two thirds. The lyric band owns the bottom.

    board = Board(ctx, palette)
    stage = safe_stage(board)          # x0, y0, x1, y1 above the lyrics
    medal(board, x, y, 36, u)
    bar_chart(board, [2, 5, 8, 6], u, (x, y, w, h))
    board.label((x, y - 20), "A PRIZE")
    return board.finish()
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

PALETTE = dict(
    bg=(6, 7, 11),
    line=(220, 226, 232),
    amber=(255, 176, 48),
    cyan=(72, 216, 226),
    dim=(86, 98, 114),
)

def _col(color, alpha=255):
    return tuple(int(c) for c in color[:3]) + (int(max(0, min(255, alpha))),)

def partial(pts, u):
    """Polyline trimmed to fraction u along its length. u=1 returns every point."""
    pts = [(float(x), float(y)) for x, y in pts]
    if len(pts) < 2 or u >= 0.999: return pts
    if u <= 0: return pts[:1]
    segs = []
    total = 0.0
    for a, b in zip(pts, pts[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        segs.append((a, b, L)); total += L
    if total < 1e-6: return pts[:1]
    need = total * float(u)
    out = [pts[0]]; acc = 0.0
    for a, b, L in segs:
        if acc + L >= need - 1e-6:
            f = 0 if L <= 1e-6 else (need - acc) / L
            f = min(max(f, 0.0), 1.0)
            out.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
            return out
        out.append(b); acc += L
    return out

def _arc(cx, cy, r, u, a0=-math.pi / 2, sweep=math.tau):
    steps = max(8, int(40 * max(u, 0.05)))
    n = max(2, int(steps * min(max(u, 0.0), 1.0)))
    return [(cx + r * math.cos(a0 + sweep * i / steps), cy + r * math.sin(a0 + sweep * i / steps)) for i in range(n + 1)]

class Board:
    """RGBA canvas at the preset background size. `finish` composites the bloom."""

    def __init__(self, ctx, palette=None):
        self.ctx = ctx
        self.w, self.h = int(ctx.SW), int(ctx.SH)
        self.p = dict(PALETTE)
        if palette: self.p.update(palette)
        self.im = Image.new("RGBA", (self.w, self.h), _col(self.p["bg"]))
        self.ink = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        self.glow = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))

    def stroke(self, pts, color=None, width=2, alpha=255):
        pts = list(pts)
        if len(pts) < 2: return
        color = self.p["line"] if color is None else color
        ImageDraw.Draw(self.ink).line(pts, fill=_col(color, alpha), width=max(1, int(width)))
        ImageDraw.Draw(self.glow).line(pts, fill=_col(color, min(alpha, 150)), width=max(1, int(width) + 6))

    def trace(self, pts, u, color=None, width=2, alpha=255):
        self.stroke(partial(pts, u), color, width, alpha)

    def circle(self, cx, cy, r, color=None, width=2, u=1.0, alpha=255):
        self.stroke(_arc(cx, cy, r, u), color, width, alpha)

    def rect(self, box, color=None, width=2, u=1.0, alpha=255):
        x, y, w, h = box
        pts = [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]
        self.trace(pts, u, color, width, alpha)

    def round_rect(self, box, radius=12, color=None, width=2, u=1.0):
        x, y, w, h = box
        r = min(radius, w / 3, h / 3)
        pts = []
        def corner(cx, cy, a0):
            for i in range(7):
                a = a0 + i / 6 * (math.pi / 2)
                pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        corner(x + w - r, y + r, -math.pi / 2)
        corner(x + w - r, y + h - r, 0)
        corner(x + r, y + h - r, math.pi / 2)
        corner(x + r, y + r, math.pi)
        pts.append(pts[0])
        self.trace(pts, u, color, width)

    def text(self, xy, s, size=22, color=None, anchor="lt", alpha=255):
        color = self.p["line"] if color is None else color
        f = self.ctx.font("mono", int(size))
        ImageDraw.Draw(self.ink).text(xy, str(s), font=f, anchor=anchor, fill=_col(color, alpha))
        ImageDraw.Draw(self.glow).text(xy, str(s), font=f, anchor=anchor, fill=_col(color, min(int(alpha), 140)))

    def label(self, xy, s, color=None, size=18):
        self.text(xy, s, size=size, color=self.p["dim"] if color is None else color, anchor="lt")

    def count_up(self, xy, target, u, color=None, size=28, suffix="", anchor="lt"):
        n = int(round(float(target) * min(1.0, max(0.0, u))))
        self.text(xy, f"{n:,}{suffix}", size=size, color=color or self.p["amber"], anchor=anchor)

    def finish(self, bloom=5):
        if bloom:
            self.im.alpha_composite(self.glow.filter(ImageFilter.GaussianBlur(radius=bloom)))
        self.im.alpha_composite(self.ink)
        return self.im

def safe_stage(board, top=0.14, bottom=0.64):
    """Rectangle above the lyric band: (x0, y0, x1, y1)."""
    return (board.w * 0.08, board.h * top, board.w * 0.92, board.h * bottom)

def arrow(board, a, b, u=1, color=None, width=2):
    ax, ay = a; bx, by = b
    x = ax + (bx - ax) * u; y = ay + (by - ay) * u
    board.stroke([(ax, ay), (x, y)], color, width)
    if u > 0.35:
        ang = math.atan2(by - ay, bx - ax)
        ah = 10 + width
        p1 = (x - ah * math.cos(ang - 0.45), y - ah * math.sin(ang - 0.45))
        p2 = (x - ah * math.cos(ang + 0.45), y - ah * math.sin(ang + 0.45))
        board.stroke([p1, (x, y), p2], color, width)

def sun_rays(board, cx, cy, r, u=1, n=14, color=None, ray=2.4):
    color = color or board.p["amber"]
    board.circle(cx, cy, r * min(1, u * 1.4), color, width=2, u=min(1, u * 1.3))
    for i in range(n):
        # each ray starts a little later so they draw on, they do not blink
        lu = min(1.0, max(0.0, u * n - i) / 1.2) if False else min(1.0, max(0.0, (u - i / n) / 0.45))
        if lu <= 0: continue
        a = -math.pi / 2 + i / n * math.tau
        x0, y0 = cx + math.cos(a) * (r + 6), cy + math.sin(a) * (r + 6)
        x1, y1 = cx + math.cos(a) * (r + 6 + r * ray * lu), cy + math.sin(a) * (r + 6 + r * ray * lu)
        board.stroke([(x0, y0), (x1, y1)], color, width=2)

def building(board, x, y, w, h, u=1, color=None, floors=4, cols=3):
    color = color or board.p["line"]
    board.rect((x, y, w, h), color, 2, u)
    if u < 0.45: return
    wu = min(1.0, (u - 0.45) / 0.55)
    fw, fh = w / cols, h / floors
    drawn = 0
    total = floors * cols
    for r in range(floors):
        for c in range(cols):
            drawn += 1
            if drawn / total > wu: return
            pad = min(fw, fh) * 0.22
            board.rect((x + c * fw + pad, y + r * fh + pad, fw - 2 * pad, fh - 2 * pad), color, 1, 1)

def person(board, x, y, s=40, u=1, color=None):
    """Outline figure. (x, y) is the feet."""
    color = color or board.p["line"]
    head_r = s * 0.16
    hy = y - s * 0.78
    board.circle(x, hy, head_r, color, 2, u=min(1, u * 2))
    if u < 0.25: return
    body = partial([(x, hy + head_r), (x, y - s * 0.28)], min(1, (u - 0.25) / 0.3))
    board.stroke(body, color, 2)
    if u < 0.5: return
    arm_u = min(1, (u - 0.5) / 0.25)
    board.trace([(x, hy + head_r + s * 0.12), (x - s * 0.28, hy + s * 0.28), (x + s * 0.28, hy + s * 0.22)], arm_u, color, 2)
    if u < 0.7: return
    leg_u = min(1, (u - 0.7) / 0.3)
    board.trace([(x, y - s * 0.28), (x - s * 0.16, y), (x, y - s * 0.28), (x + s * 0.16, y)], leg_u, color, 2)

def crowd(board, box, n=16, u=1, color=None):
    x0, y0, x1, y1 = box
    cols = max(4, int(math.sqrt(n) * 1.6))
    rows = int(math.ceil(n / cols))
    cw, rh = (x1 - x0) / cols, (y1 - y0) / rows
    show = max(1, int(round(n * min(1, max(0, u)))))
    k = 0
    for r in range(rows):
        for c in range(cols):
            if k >= show: return
            person(board, x0 + cw * (c + 0.5), y0 + rh * (r + 0.92), s=min(cw, rh) * 0.85, u=1, color=color)
            k += 1

def robot(board, x, y, s=70, u=1, color=None, arm=0.0):
    """Box robot. `arm` -1..1 reaches sideways. (x, y) is the feet."""
    color = color or board.p["cyan"]
    head = s * 0.28
    body_h = s * 0.38
    hy = y - s * 0.78
    board.rect((x - head / 2, hy - head / 2, head, head), color, 2, min(1, u * 2))
    if u > 0.2:
        board.circle(x - head * 0.18, hy, 2.2, color, 2, u=1)
        board.circle(x + head * 0.18, hy, 2.2, color, 2, u=1)
        board.stroke([(x, hy - head / 2), (x, hy - head / 2 - s * 0.12)], color, 2)
        board.circle(x, hy - head / 2 - s * 0.14, 3, board.p["amber"], 2, u=1)
    if u < 0.35: return
    board.rect((x - s * 0.22, hy + head / 2 + 4, s * 0.44, body_h), color, 2, min(1, (u - 0.35) / 0.3))
    if u < 0.65: return
    au = min(1, (u - 0.65) / 0.35)
    shoulder_y = hy + head / 2 + 14
    reach = s * 0.34 * arm
    board.trace([(x - s * 0.22, shoulder_y), (x - s * 0.42, shoulder_y + 8)], au, color, 2)
    board.trace([(x + s * 0.22, shoulder_y), (x + s * 0.42 + reach, shoulder_y + 6 + reach * 0.1)], au, color, 2)
    board.trace([(x - s * 0.1, hy + head / 2 + 4 + body_h), (x - s * 0.14, y),
                 (x + s * 0.1, hy + head / 2 + 4 + body_h), (x + s * 0.14, y)], au, color, 2)

def shelf(board, x, y, w, u=1, color=None):
    color = color or board.p["line"]
    board.trace([(x, y), (x + w, y)], u, color, 2)
    board.trace([(x + 8, y), (x + 8, y + 16), (x + w - 8, y), (x + w - 8, y + 16)], min(1, u * 1.2), color, 2)

def medal(board, x, y, r=28, u=1, color=None):
    color = color or board.p["amber"]
    board.circle(x, y, r, color, 2, u=min(1, u * 1.3))
    if u < 0.35: return
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.tau / 10
        rad = r * (0.45 if i % 2 else 0.2)
        pts.append((x + rad * math.cos(a), y + rad * math.sin(a)))
    pts.append(pts[0])
    board.trace(pts, min(1, (u - 0.35) / 0.45), color, 2)
    if u > 0.75:
        board.stroke([(x - 8, y + r), (x - 14, y + r + 18), (x, y + r + 8), (x + 14, y + r + 18), (x + 8, y + r)], color, 2)

def _axes(board, box, color, u):
    x, y, w, h = box
    board.trace([(x, y), (x, y + h), (x + w, y + h)], min(1, u * 1.5), color, 2)
    return x, y, w, h

def bar_chart(board, values, u, box, color=None, accent=None):
    color = color or board.p["cyan"]
    accent = accent or board.p["amber"]
    x, y, w, h = _axes(board, box, board.p["dim"], u)
    if u < 0.25 or not values: return
    bu = min(1, (u - 0.25) / 0.75)
    vals = [max(0.0, float(v)) for v in values]
    peak = max(vals) or 1
    gap = w / len(vals)
    bw = gap * 0.55
    for i, v in enumerate(vals):
        bh = (h - 8) * (v / peak) * bu
        board.rect((x + 8 + i * gap, y + h - bh, bw, bh), accent if i == len(vals) - 1 else color, 2, 1)

def line_chart(board, values, u, box, color=None):
    color = color or board.p["amber"]
    x, y, w, h = _axes(board, box, board.p["dim"], u)
    if u < 0.3 or len(values) < 2: return
    vals = [float(v) for v in values]
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    pts = []
    for i, v in enumerate(vals):
        px = x + 6 + (w - 12) * i / (len(vals) - 1)
        py = y + h - 6 - (h - 14) * (v - lo) / span
        pts.append((px, py))
    board.trace(pts, min(1, (u - 0.3) / 0.7), color, 2)

def diminish_curve(board, u, box, color=None):
    """A curve that rises fast and flattens. Traced with u."""
    color = color or board.p["amber"]
    x, y, w, h = _axes(board, box, board.p["dim"], u)
    pts = []
    for i in range(24):
        t = i / 23
        # fast start, flat finish
        val = 1 - math.exp(-3.2 * t)
        pts.append((x + 8 + (w - 16) * t, y + h - 8 - (h - 20) * val))
    board.trace(pts, min(1, max(0, (u - 0.25) / 0.75)), color, 3)
    if u > 0.4:
        board.label((x + 8, y + 4), "returns", board.p["dim"], 16)

def clock(board, cx, cy, r, u=1, color=None, hours=10.2):
    color = color or board.p["line"]
    board.circle(cx, cy, r, color, 2, u=min(1, u * 1.4))
    if u < 0.35: return
    for i in range(12):
        a = -math.pi / 2 + i / 12 * math.tau
        board.stroke([(cx + math.cos(a) * r * 0.82, cy + math.sin(a) * r * 0.82),
                      (cx + math.cos(a) * r * 0.94, cy + math.sin(a) * r * 0.94)], color, 2)
    # hands move a small amount across the line; they do not spin
    hu = min(1, max(0, (u - 0.35) / 0.65))
    ha = (-math.pi / 2) + (hours % 12) / 12 * math.tau + hu * 0.15
    ma = (-math.pi / 2) + (hours % 1) * math.tau + hu * 0.4
    board.stroke([(cx, cy), (cx + math.cos(ha) * r * 0.48, cy + math.sin(ha) * r * 0.48)], board.p["amber"], 3)
    board.stroke([(cx, cy), (cx + math.cos(ma) * r * 0.72, cy + math.sin(ma) * r * 0.72)], board.p["cyan"], 2)

def calendar(board, x, y, w, h, u=1, mark=(2, 3), color=None):
    color = color or board.p["line"]
    board.rect((x, y, w, h), color, 2, min(1, u * 1.6))
    board.stroke([(x, y + h * 0.18), (x + w, y + h * 0.18)], color, 2)
    if u < 0.3: return
    gu = min(1, (u - 0.3) / 0.7)
    cols, rows = 7, 5
    gw, gh = w * 0.9, h * 0.72
    x0, y0 = x + w * 0.05, y + h * 0.24
    cells = cols * rows
    show = max(1, int(gu * cells))
    for i in range(show):
        r, c = divmod(i, cols)
        board.rect((x0 + c * gw / cols + 2, y0 + r * gh / rows + 2, gw / cols - 4, gh / rows - 4),
                   board.p["amber"] if (r, c) == tuple(mark) else board.p["dim"], 1, 1)

def hud_rings(board, cx, cy, r, u=1, color=None, t=0):
    color = color or board.p["cyan"]
    for i, scale in enumerate((0.45, 0.7, 1.0)):
        lu = min(1.0, max(0.0, u * 3 - i))
        # slow rotation, continuous, a few degrees per second
        shift = t * 0.25 + i
        pts = _arc(cx, cy, r * scale, lu, a0=shift, sweep=math.tau * 0.82)
        board.stroke(pts, color if i == 2 else board.p["line"], 2)
    if u > 0.4:
        board.circle(cx, cy, 3, board.p["amber"], 2, u=1)

def terminal(board, box, lines, u=1, color=None):
    color = color or board.p["cyan"]
    x, y, w, h = box
    board.round_rect((x, y, w, h), 12, color, 2, min(1, u * 1.5))
    if u < 0.25: return
    board.circle(x + 16, y + 16, 4, board.p["amber"], 2, u=1)
    board.circle(x + 30, y + 16, 4, board.p["dim"], 2, u=1)
    board.circle(x + 44, y + 16, 4, board.p["dim"], 2, u=1)
    tu = min(1, (u - 0.25) / 0.75)
    body = list(lines)
    budget = tu * max(1, sum(len(s) for s in body))
    yy = y + 36
    for s in body:
        if budget <= 0 or yy > y + h - 16: break
        take = int(min(len(s), budget))
        board.text((x + 16, yy), s[:take], size=18, color=board.p["line"])
        budget -= len(s); yy += 24

def neon_sign(board, cx, cy, text, u=1, color=None, swing=0.0, t=0):
    """A hanging sign. `swing` is degrees of slow rock; keep it under about 6."""
    color = color or board.p["amber"]
    f = board.ctx.font("title", 36)
    tw = f.getlength(text)
    w, h = tw + 48, 64
    ang = math.radians(swing) * math.sin(t * 0.7)
    # draw upright into a tile, then rotate the tile slowly
    tile = Image.new("RGBA", (int(w + 20), int(h + 20)), (0, 0, 0, 0))
    d = ImageDraw.Draw(tile)
    d.rounded_rectangle([8, 8, w + 8, h + 8], radius=10, outline=_col(color), width=3)
    if u > 0.35:
        shown = text if u > 0.9 else text[:max(1, int(len(text) * (u - 0.2) / 0.7))]
        d.text((tile.width / 2, tile.height / 2), shown, font=f, anchor="mm", fill=_col(color))
    if abs(ang) > 0.001:
        tile = tile.rotate(math.degrees(ang), resample=Image.BICUBIC, expand=True, fillcolor=(0, 0, 0, 0))
    _stamp(board.glow, tile, (cx - tile.width / 2, cy - tile.height / 2))
    _stamp(board.ink, tile, (cx - tile.width / 2, cy - tile.height / 2))

def _stamp(base, tile, xy):
    x, y = int(xy[0]), int(xy[1])
    if x >= base.width or y >= base.height or x + tile.width <= 0 or y + tile.height <= 0: return
    if x < 0 or y < 0 or x + tile.width > base.width or y + tile.height > base.height:
        l, t = max(0, -x), max(0, -y)
        r, b = min(tile.width, base.width - x), min(tile.height, base.height - y)
        if r <= l or b <= t: return
        tile = tile.crop((l, t, r, b)); x, y = max(0, x), max(0, y)
    base.alpha_composite(tile, (x, y))

def network(board, box, u=1, nodes=7, color=None):
    color = color or board.p["cyan"]
    x0, y0, x1, y1 = box
    rng_pts = []
    for i in range(nodes):
        px = x0 + (x1 - x0) * ((i * 0.37) % 1)
        py = y0 + (y1 - y0) * ((i * 0.53 + 0.1) % 1)
        rng_pts.append((px, py))
    show = max(1, int(round(nodes * min(1, u * 1.2))))
    for i in range(show):
        board.circle(rng_pts[i][0], rng_pts[i][1], 5, board.p["amber"] if i == 0 else color, 2, u=1)
        if i:
            board.trace([rng_pts[i - 1], rng_pts[i]], min(1, u * 1.3), color, 2)

# ---- whole-scene templates used by JSON specs ----

def _box_center(board):
    x0, y0, x1, y1 = safe_stage(board)
    return x0, y0, x1, y1

def template_rays(board, ctx, line, u, st):
    x0, y0, x1, y1 = _box_center(board)
    sun_rays(board, (x0 + x1) / 2, (y0 + y1) / 2 + 10, 28, u, n=16, ray=1.6)
    board.label((x0, y0), "SPREAD", board.p["amber"])

def template_medal_bars(board, ctx, line, u, st):
    x0, y0, x1, y1 = _box_center(board)
    shelf(board, x0 + 20, y0 + 70, x1 - x0 - 40, u)
    medal(board, x0 + 90, y0 + 36, 26, u)
    bar_chart(board, [2, 4, 7, 5, 9, 8], u, (x0 + 180, y0 + 20, x1 - x0 - 220, y1 - y0 - 40))
    board.label((x0, y1 - 18), "ON THE SHELF", board.p["dim"])

def template_calendar(board, ctx, line, u, st):
    x0, y0, x1, y1 = _box_center(board)
    calendar(board, x0 + 30, y0 + 10, 220, 180, u, mark=(2, 4))
    clock(board, x1 - 120, y0 + 100, 58, u)
    board.label((x0, y1 - 16), "A YEAR", board.p["amber"])

def template_robots(board, ctx, line, u, st):
    x0, y0, x1, y1 = _box_center(board)
    ground = y1 - 8
    board.trace([(x0, ground), (x1, ground)], min(1, u * 2), board.p["dim"], 2)
    robot(board, x0 + 140, ground, 120, u, board.p["cyan"], arm=0.6)
    robot(board, x0 + 300, ground, 78, min(1, max(0, (u - 0.2) / 0.8)), board.p["line"], arm=-0.2)
    board.label((x0, y0), "BUILDING", board.p["amber"])

def template_curve(board, ctx, line, u, st):
    x0, y0, x1, y1 = _box_center(board)
    diminish_curve(board, u, (x0 + 10, y0 + 10, x1 - x0 - 20, y1 - y0 - 30))

def template_crowd(board, ctx, line, u, st):
    x0, y0, x1, y1 = _box_center(board)
    crowd(board, (x0, y0 + 30, x1, y1), n=18, u=u, color=board.p["line"])
    board.count_up((x0, y0), 1000000, u, board.p["amber"], size=26)

def template_terminal(board, ctx, line, u, st):
    x0, y0, x1, y1 = _box_center(board)
    terminal(board, (x0 + 20, y0, (x1 - x0) - 40, y1 - y0 - 10), u=u, lines=[
        "$ tail -f decisions.log",
        "review: queued",
        "status: hold",
        "next: ask a person",
    ])

def template_hud(board, ctx, line, u, st):
    x0, y0, x1, y1 = _box_center(board)
    hud_rings(board, (x0 + x1) / 2, (y0 + y1) / 2, min(x1 - x0, y1 - y0) * 0.28, u, t=st.get("t", 0))
    board.label((x0, y0), "SIGNAL", board.p["cyan"])

def template_sign(board, ctx, line, u, st):
    x0, y0, x1, y1 = _box_center(board)
    neon_sign(board, (x0 + x1) / 2, (y0 + y1) / 2, "WAIT", u, swing=4, t=st.get("t", 0))

def template_buildings(board, ctx, line, u, st):
    x0, y0, x1, y1 = _box_center(board)
    ground = y1 - 6
    board.trace([(x0, ground), (x1, ground)], min(1, u * 2), board.p["dim"], 2)
    building(board, x0 + 20, ground - 120, 70, 120, u, floors=4, cols=3)
    building(board, x0 + 110, ground - 170, 90, 170, min(1, u * 1.1), floors=5, cols=3)
    building(board, x0 + 220, ground - 90, 60, 90, min(1, max(0, u - 0.1)), floors=3, cols=2)
    sun_rays(board, x1 - 80, y0 + 40, 16, u, n=10, ray=1.1)

TEMPLATES = {
    "rays": template_rays,
    "medal_bars": template_medal_bars,
    "calendar": template_calendar,
    "robots": template_robots,
    "curve": template_curve,
    "crowd": template_crowd,
    "terminal": template_terminal,
    "hud": template_hud,
    "sign": template_sign,
    "buildings": template_buildings,
}
