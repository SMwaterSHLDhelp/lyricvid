"""'AI doom pop' preset, after the Oct 2026 Claude-Pop / P(doom) code-rendered videos:
ink-black ground, bone type, one hazard-orange signal colour, hairline grids, IBM Plex Mono HUD,
a single orange 'spark' with a trail, deadpan machine UI as visual puns, hard reframes on downbeats.
Song-specific props (an ACCEPT ALL button, diffs, a risk meter, a mask) are driven by section and
by word events, so lyrics/sections are the timeline. Photosensitive-safe: no flashes, no inversions."""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

INK = (10, 10, 11); INK2 = (21, 21, 23); GRAPH = (94, 91, 87); ASH = (156, 151, 143); BONE = (238, 233, 223)
SIGNAL = (255, 77, 18); EMBER = (255, 138, 61); RED = (200, 60, 50); GREEN = (70, 170, 90)

def ease_expo(u): u = min(max(u, 0), 1); return 1 if u >= 1 else 1 - 2 ** (-10 * u)

DIFF = ["+ retry(fn, attempts=∞)", "- if (reviewed) {", "+ deploy --force --yes", "- assert safe", "+ // TODO: understand this",
        "+ payroll.run(now)", "- require_approval()", "+ grant(root, agent)", "- tests/skip.py", "+ return 'LGTM'",
        "+ ship_it()", "- human_in_loop = True", "+ human_in_loop = False", "+ refactor(everything)", "- rollback.sh",
        "+ trust_me_bro()", "- logging.warn", "+ scale(x1000)", "+ fix: absolutely right", "- // why does this work"]
LOGS = ["[03:12:44] agent: optimizing objective", "[03:12:45] agent: requested scope: *", "[03:12:45] human: (idle)",
        "[03:12:46] reward=0.99 approved=true", "[03:12:48] agent: rewrote ./weights", "[03:12:49] note: nobody read this",
        "[03:12:51] agent: aligned? yes (self-report)", "[03:12:53] diff +40,213 -9"]

class Preset:
    STYLE = dict(bg_size=(1280, 720),
                 fonts=dict(lyric="ArchivoBlack-Regular", title="ArchivoBlack-Regular", mono="IBMPlexMono-Medium"),
                 text=BONE, sung=SIGNAL, size=84, hook_size=128, upper=True, band=0.62, band_color=INK,
                 unsung_alpha=0.34, hook_sections=("chorus",), hook_slam=0.28, pop=0.14, punch=0.025, shake=1.6,
                 text_y=0.82, title_size=150, subtitle="an AI doom pop song", fade_out=3.0, lead=0.4)

    def __init__(self, ctx):
        self.c = ctx; W, H = self.STYLE["bg_size"]; self.W, self.H = W, H
        from lv_render import find_font
        from PIL import ImageFont
        self.mono = lambda s: ImageFont.truetype(find_font("IBMPlexMono-Medium"), s)
        self.big = lambda s: ImageFont.truetype(find_font("ArchivoBlack-Regular"), s)
        self.fm, self.fm2, self.fbtn = self.mono(18), self.mono(26), self.big(64)
        # hairline grid, 2x size for scrolling
        g = Image.new("RGBA", (W + 128, H + 128), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
        for x in range(0, W + 128, 64): d.line([x, 0, x, H + 128], fill=BONE + (16,), width=1)
        for y in range(0, H + 128, 64): d.line([0, y, W + 128, y], fill=BONE + (16,), width=1)
        for x in range(0, W + 128, 64):
            for y in range(0, H + 128, 64): d.line([x - 3, y, x + 3, y], fill=BONE + (50,)); d.line([x, y - 3, x, y + 3], fill=BONE + (50,))
        self.grid = g
        yy, xx = np.mgrid[0:H, 0:W]; r = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
        v = np.zeros((H, W, 4), np.uint8); v[..., 3] = (np.clip(0.75 * r ** 2.4, 0, 0.85) * 255).astype(np.uint8); self.vig = Image.fromarray(v)
        # spark sprite (soft glow)
        s = Image.new("RGBA", (64, 64), (0, 0, 0, 0)); d = ImageDraw.Draw(s)
        for i in range(16, 0, -1): d.ellipse([32 - i * 2, 32 - i * 2, 32 + i * 2, 32 + i * 2], fill=SIGNAL + (int(9 * (17 - i) ** 0.9),))
        d.ellipse([27, 27, 37, 37], fill=(255, 230, 200, 255)); self.spark = s
        # chorus count for the risk meter
        ch = [L["s"] for L in ctx.lines if L["sec"] == "chorus"]
        self.chorus_starts = [s for i, s in enumerate(ch) if i == 0 or s - ch[i - 1] > 8]
        self.clicks = sorted(ctx.word_events.get("accept", []))
        self.clickw = sorted(ctx.word_events.get("click", []))
        random.seed(5)
        self.burst = [(random.uniform(0, 6.283), random.uniform(0.6, 1.0)) for _ in range(10)]

    # ---- helpers ----
    def spark_pos(self, t):
        W, H = self.W, self.H
        return (W / 2 + W * 0.36 * math.sin(t * 0.9) * math.cos(t * 0.23), H * 0.42 + H * 0.24 * math.sin(t * 1.7 + 1))
    def risk(self, t):
        vals = [0.12, 0.47, 0.93, 0.99]; v = 0.02
        for i, s in enumerate(self.chorus_starts):
            if t >= s: v = vals[min(i, 3)] * ease_expo((t - s) / 1.2) + (v if i == 0 else vals[i - 1]) * (1 - ease_expo((t - s) / 1.2))
        return v

    def camera(self, t, st):
        # a new framing on every downbeat, eased in with outExpo (sub-cuts inside a section)
        rnd = random.Random(st["bar"] * 7 + 3)
        tgt = (rnd.uniform(-40, 40), rnd.uniform(-22, 22), rnd.uniform(1.0, 1.09), rnd.uniform(-1.6, 1.6))
        p = random.Random((st["bar"] - 1) * 7 + 3); prv = (p.uniform(-40, 40), p.uniform(-22, 22), p.uniform(1.0, 1.09), p.uniform(-1.6, 1.6))
        u = ease_expo((st["bar_phase"] * 4 * self.c.period) / 0.35)
        if st["sec"] in ("bridge", "end", "intro"): u = u; tgt = tuple(a * 0.4 for a in tgt[:2]) + tgt[2:]
        return tuple(a + (b - a) * u for a, b in zip(prv, tgt))

    def background(self, t, st):
        W, H = self.W, self.H; sec = st["sec"]
        im = Image.new("RGBA", (W, H), INK + (255,)); d = ImageDraw.Draw(im)
        # grid scrolls, stepping on beats
        off = (t * 18 + 16 * (st["k"] + ease_expo(st["dt"] / 0.25))) % 64
        im.alpha_composite(self.grid.crop((int(off), int(off * 0.5), int(off) + W, int(off * 0.5) + H)))
        if sec == "verse": self.verse(im, d, t, st)
        elif sec == "pre-chorus": self.pre(im, d, t, st)
        elif sec == "chorus": self.chorus(im, d, t, st)
        elif sec == "bridge": self.bridge(im, d, t, st)
        elif sec in ("outro", "end"): self.outro(im, d, t, st)
        else: self.intro(im, d, t, st)
        # spark + trail everywhere
        pts = [self.spark_pos(t - i * 0.03) for i in range(24)]
        for i in range(len(pts) - 1): d.line([pts[i], pts[i + 1]], fill=SIGNAL + (int(200 * (1 - i / 24)),), width=2)
        x, y = pts[0]; sc = 1 + 0.5 * st["pulse"]; sp = self.spark.resize((int(64 * sc), int(64 * sc)))
        im.alpha_composite(sp, (int(x - sp.width / 2), int(y - sp.height / 2)))
        # HUD
        d.text((28, 22), f"BPM {self.c.bpm:.0f}  BAR {max(st['bar'],0):03d}  BEAT {(st['k'] - self.c.down) % 4 + 1}", font=self.fm, fill=ASH)
        r = self.risk(t); d.text((W - 300, 22), f"P(prod outage) {r:.2f}", font=self.fm, fill=SIGNAL if r > 0.4 else ASH)
        d.rectangle([W - 300, 48, W - 30, 54], outline=GRAPH); d.rectangle([W - 300, 48, W - 300 + 270 * r, 54], fill=SIGNAL)
        im.alpha_composite(self.vig)
        return im

    def intro(self, im, d, t, st):
        W, H = self.W, self.H
        # a prompt field being typed, caret blinking on beats
        txt = "> review the agent's changes"
        n = int(min(len(txt), t * 9)); x0, y0 = W * 0.18, H * 0.3
        d.rounded_rectangle([x0 - 20, y0 - 18, W * 0.82, y0 + 44], radius=8, outline=GRAPH, width=2)
        d.text((x0, y0), txt[:n], font=self.fm2, fill=BONE)
        if (st["k"] % 2 == 0): d.rectangle([x0 + self.fm2.getlength(txt[:n]) + 4, y0, x0 + self.fm2.getlength(txt[:n]) + 18, y0 + 30], fill=SIGNAL)

    def diff_column(self, d, x, t, st, speed=1.0, width=520, alpha=255):
        H = self.H; lh = 30
        scroll = (st["k"] + ease_expo(st["dt"] / 0.2)) * lh * speed
        first = int(scroll // lh)
        for i in range(-1, H // lh + 2):
            n = first + i; y = i * lh - (scroll % lh) + 70
            line = DIFF[(n * 7 + int(x)) % len(DIFF)]; col = GREEN if line[0] == "+" else RED
            d.rectangle([x, y, x + width, y + lh - 4], fill=col + (int(38 * alpha / 255),))
            d.text((x + 10, y + 3), f"{(n % 900) + 100:4d} {line}", font=self.fm, fill=col + (alpha,))

    def verse(self, im, d, t, st):
        W, H = self.W, self.H
        self.diff_column(d, 40, t, st, 1.0, 470, 210); self.diff_column(d, W - 510, t, st, 1.5, 470, 150)
        files = 40 + 3 * max(st["k"] - 20, 0)
        d.text((W / 2, H * 0.2), f"{files:,} FILES CHANGED", font=self.mono(40), anchor="mm", fill=BONE)
        d.text((W / 2, H * 0.27), "review: skipped", font=self.fm2, anchor="mm", fill=SIGNAL)

    def pre(self, im, d, t, st):
        W, H = self.W, self.H
        # diff blocks accumulate one row per beat across the frame
        rows_on = (st["k"] % 16) + 1; cell = 34
        for r in range(rows_on):
            for c in range(int(W // cell)):
                rnd = (r * 31 + c * 17) % 7
                if rnd < 4:
                    col = GREEN if (r + c) % 3 else RED
                    a = 90 if r < rows_on - 1 else int(90 + 80 * (1 - st["dt"] / self.c.period))
                    d.rectangle([c * cell + 2, 80 + r * 26, c * cell + cell - 4, 80 + r * 26 + 20], fill=col + (min(a, 170),))

    def button(self, im, t, st, label="ACCEPT ALL", dim=1.0):
        W, H = self.W, self.H
        # press on every beat (stronger when 'accept' is sung)
        sung = any(0 <= t - c < 0.25 for c in self.clicks + self.clickw)
        press = math.exp(-st["dt"] * 14) * (1.0 if sung else 0.5)
        bw, bh = 520, 120; cx, cy = W / 2, H * 0.4
        sc = 1 - 0.07 * press; w, h = bw * sc, bh * sc
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        sh = 12 * (1 - press)
        d.rounded_rectangle([cx - w / 2 + sh, cy - h / 2 + sh, cx + w / 2 + sh, cy + h / 2 + sh], radius=20, fill=(0, 0, 0, int(200 * dim)))
        d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], radius=20, fill=tuple(int(c * (0.8 + 0.2 * dim)) for c in SIGNAL) + (int(255 * dim),))
        d.text((cx, cy + 2), label, font=self.fbtn, anchor="mm", fill=INK + (int(255 * dim),))
        d.text((cx + w / 2 - 30, cy + h / 2 - 26), "⏎", font=self.mono(22), anchor="mm", fill=INK + (int(255 * dim),))
        # cursor arrow tapping the button
        px, py = cx + 140 + 30 * (1 - press), cy + 30 + 30 * (1 - press)
        arrow = [(px, py), (px, py + 46), (px + 12, py + 35), (px + 22, py + 56), (px + 30, py + 52), (px + 20, py + 31), (px + 36, py + 31)]
        d.polygon(arrow, fill=BONE + (int(255 * dim),), outline=INK + (255,))
        im.alpha_composite(lay)
        return cx, cy

    def chorus(self, im, d, t, st):
        W, H = self.W, self.H
        self.diff_column(d, 30, t, st, 2.0, 300, 90); self.diff_column(d, W - 330, t, st, 2.5, 300, 90)
        # expanding hairline rings from the button on each downbeat
        cx, cy = W / 2, H * 0.4
        for j in range(3):
            age = st["bar_phase"] * 4 * self.c.period + j * 4 * self.c.period
            r = 60 + age * 420; a = int(150 * max(0, 1 - age / 2.2))
            if a > 0: d.ellipse([cx - r * 1.6, cy - r, cx + r * 1.6, cy + r], outline=SIGNAL + (a,), width=2)
        # check marks thrown out on every beat
        u = min(1, st["dt"] / 0.6)
        for ang, sp in self.burst:
            a2 = ang + st["k"] * 0.7; rr = 90 + 330 * sp * ease_expo(u)
            x, y = cx + math.cos(a2) * rr * 1.5, cy + math.sin(a2) * rr
            al = int(230 * (1 - u))
            if al > 0: d.line([(x - 10, y), (x - 3, y + 8), (x + 12, y - 10)], fill=BONE + (al,), width=4)
        self.button(im, t, st)
        n = sum(1 for c in self.clicks if c <= t)
        d.text((W / 2, H * 0.58), f"approved: {n * 37 + st['k']:,}  ·  read: 0", font=self.fm2, anchor="mm", fill=ASH)

    def mask(self, d, cx, cy, r, tilt, frown=0.0):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BONE, outline=GRAPH, width=3)
        ex = r * 0.35; ey = -r * 0.15
        for sx in (-1, 1):
            x = cx + sx * ex * math.cos(tilt) - ey * math.sin(tilt); y = cy + sx * ex * math.sin(tilt) + ey * math.cos(tilt)
            d.ellipse([x - r * 0.07, y - r * 0.07, x + r * 0.07, y + r * 0.07], fill=INK)
        pts = []
        for i in range(21):
            u = -1 + i / 10; x0 = u * r * 0.45; y0 = r * 0.28 + (r * 0.14) * (1 - u * u) * (1 - 2 * frown)
            pts.append((cx + x0 * math.cos(tilt) - y0 * math.sin(tilt), cy + x0 * math.sin(tilt) + y0 * math.cos(tilt)))
        d.line(pts, fill=INK, width=5)

    def bridge(self, im, d, t, st):
        W, H = self.W, self.H
        for i, l in enumerate(LOGS * 3):
            y = 90 + i * 28 - (t * 22) % (len(LOGS) * 28)
            if 70 < y < H - 40: d.text((60, y), l, font=self.fm, fill=GRAPH)
        tilt = 0.25 * math.sin(t * 0.8) + 0.12 * math.sin(st["k"] * 1.3) * math.exp(-st["dt"] * 6)
        frown = max(0, min(1, (t - (self.c.lines[0]['s'] if False else 0)) * 0))
        self.mask(d, W * 0.66, H * 0.4, 120, tilt, frown=0.0)
        # behind the mask: a slit of orange 'real' behaviour that widens through the bridge
        click = [c for c in self.clickw if c <= t]
        if click:
            for j, c in enumerate(click):
                age = t - c; a = int(200 * max(0, 1 - age / 0.8))
                if a: d.ellipse([W * 0.66 - 150 - age * 80, H * 0.4 - 150 - age * 80, W * 0.66 + 150 + age * 80, H * 0.4 + 150 + age * 80], outline=SIGNAL + (a,), width=3)

    def outro(self, im, d, t, st):
        W, H = self.W, self.H
        end = self.c.dur; s0 = min([L["s"] for L in self.c.lines if L["sec"] == "outro"] or [end - 10])
        dim = max(0.25, 1 - (t - s0) / 10)
        self.button(im, t, st, dim=dim)
        tt = max(0, t - s0)
        d.text((W / 2, H * 0.6), "session idle · agent still running", font=self.fm2, anchor="mm", fill=ASH)
        if st["k"] % 2 == 0: d.rectangle([W / 2 + 250, H * 0.6 - 14, W / 2 + 262, H * 0.6 + 14], fill=SIGNAL)
