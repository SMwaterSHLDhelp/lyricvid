"""Set For Years: a 'golden parachute' day-cycle diorama. Glossy soft-vector props (gradient fills, thick rounded
navy ink lines, soft blurred drop shadows) drawn SUPERSAMPLED (default 2x = 3840x2160, Lanczos-downscaled by the
engine) in front of a parallax glass-tower skyline. The sky slowly walks one workday through the song: hopeful
morning -> golden deal-closing noon -> coral layoff sunset -> navy night bridge -> teal dawn for the defiant last
chorus. One acted-out scene per lyric line (meeting, handshake, champagne, HR email, badge denied, boss on his
boat, the clock stopping), office paper drifting in the air. Bricolage Grotesque lyrics, Fraunces titles.
Photosensitive-safe: no flashes, sky changes take tens of seconds, scenes crossfade over 0.7 s."""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

INK = (22, 30, 58); CREAM = (255, 246, 228); GOLD = (255, 196, 72); GOLD2 = (230, 150, 40); TEAL = (40, 170, 170)
CORAL = (240, 120, 100); PAPER = (250, 248, 240); PAPER2 = (222, 218, 205); SKIN = (240, 196, 160); SKIN2 = (214, 160, 124)
SUIT = (52, 64, 110); SUIT2 = (34, 42, 80); SHIRT = (120, 170, 230); SHIRT2 = (80, 128, 196); GLASS = (180, 220, 240)
GREEN = (110, 200, 130); AMBER = (255, 170, 40); WOOD = (170, 116, 76); WOOD2 = (128, 82, 52); BOX = (210, 160, 100)
BOX2 = (170, 120, 70); WATER = (60, 140, 200); WATER2 = (30, 90, 160); WHITE = (255, 255, 255)

# sky keyframes: (time_s, top, bottom)
SKY = [(0, (120, 180, 230), (255, 214, 180)), (22, (110, 175, 235), (255, 226, 170)), (50, (255, 190, 110), (255, 236, 170)),
       (60, (250, 160, 110), (255, 210, 150)), (78, (200, 110, 130), (255, 170, 120)), (100, (90, 70, 130), (240, 140, 120)),
       (112, (24, 30, 70), (70, 60, 120)), (124, (30, 40, 90), (110, 90, 150)), (134, (40, 120, 160), (255, 190, 140)),
       (150, (90, 180, 210), (255, 224, 170)), (180, (110, 190, 220), (255, 230, 190))]

def ease(u): u = min(max(u, 0), 1); return u * u * (3 - 2 * u)
def back(u):
    u = min(max(u, 0), 1); c = 1.6; return 1 + (c + 1) * (u - 1) ** 3 + c * (u - 1) ** 2
def mix(a, b, u): u = min(max(u, 0), 1); return tuple(int(x + (y - x) * u) for x, y in zip(a, b))
def shade(c, f): return tuple(max(0, min(255, int(v * f))) for v in c[:3])

def sky_at(t):
    for (t0, a0, b0), (t1, a1, b1) in zip(SKY, SKY[1:]):
        if t <= t1:
            u = ease((t - t0) / (t1 - t0)); return mix(a0, a1, u), mix(b0, b1, u)
    return SKY[-1][1], SKY[-1][2]
def night_at(t):  # 0 day .. 1 night
    if t < 70: return 0.0
    if t < 112: return ease((t - 70) / 42)
    if t < 124: return 1.0
    return 1 - ease((t - 124) / 14)


class Pen:
    """Vector-ish drawing in 1920x1080 'units' onto a K-times supersampled RGBA layer.
    transform: X = (ox + x*s)*K. Gradients are vertical (c -> c2). Outlines are drawn as a fatter shape underneath,
    which anti-aliases better than PIL's outline= after the engine's Lanczos downscale."""
    def __init__(self, im, K, fonts):
        self.im = im; self.d = ImageDraw.Draw(im); self.K = K; self.ox = 0; self.oy = 0; self.s = 1; self.fonts = fonts
    def at(self, ox, oy, s=1): self.ox, self.oy, self.s = ox, oy, s; return self
    def P(self, x, y): return ((self.ox + x * self.s) * self.K, (self.oy + y * self.s) * self.K)
    def L(self, v): return max(1, v * self.s * self.K)
    def _grad(self, kind, x0, y0, x1, y1, c, c2, r=0, a=255):
        X0, Y0 = self.P(x0, y0); X1, Y1 = self.P(x1, y1)
        X0, X1 = sorted((X0, X1)); Y0, Y1 = sorted((Y0, Y1))
        w, h = int(X1 - X0) + 2, int(Y1 - Y0) + 2
        if w < 2 or h < 2: return
        m = Image.new("L", (w, h), 0); md = ImageDraw.Draw(m)
        fx, fy = X0 - int(X0), Y0 - int(Y0)
        bb = [fx, fy, fx + X1 - X0, fy + Y1 - Y0]
        if kind == "e": md.ellipse(bb, fill=a)
        else: md.rounded_rectangle(bb, radius=self.L(r), fill=a)
        g = np.linspace(0, 1, h)[:, None, None]
        arr = (np.array(c[:3]) * (1 - g) + np.array(c2[:3]) * g) * np.ones((1, w, 1))
        gi = Image.fromarray(arr.astype(np.uint8)).convert("RGBA"); gi.putalpha(m)
        self.im.alpha_composite(gi, (int(X0), int(Y0)))
    def rect(self, x0, y0, x1, y1, c, c2=None, r=0, ink=INK, w=5, a=255):
        if ink is not None and w:
            self.d.rounded_rectangle([*self.P(x0 - w, y0 - w), *self.P(x1 + w, y1 + w)], radius=self.L(r + w), fill=ink + (a,))
        if c2 is None: self.d.rounded_rectangle([*self.P(x0, y0), *self.P(x1, y1)], radius=self.L(r), fill=c[:3] + (a,))
        else: self._grad("r", x0, y0, x1, y1, c, c2, r, a)
    def ell(self, cx, cy, rx, ry, c, c2=None, ink=INK, w=5, a=255):
        if ink is not None and w:
            self.d.ellipse([*self.P(cx - rx - w, cy - ry - w), *self.P(cx + rx + w, cy + ry + w)], fill=ink + (a,))
        if c2 is None: self.d.ellipse([*self.P(cx - rx, cy - ry), *self.P(cx + rx, cy + ry)], fill=c[:3] + (a,))
        else: self._grad("e", cx - rx, cy - ry, cx + rx, cy + ry, c, c2, 0, a)
    def poly(self, pts, c, ink=INK, w=5, a=255):
        P = [self.P(x, y) for x, y in pts]
        if ink is not None and w:
            self.d.polygon(P, fill=ink + (a,))
            self.d.line(P + [P[0]], fill=ink + (a,), width=int(self.L(w * 2)), joint="curve")
            for p in P: r = self.L(w); self.d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=ink + (a,))
        self.d.polygon(P, fill=c[:3] + (a,))
    def line(self, pts, c=INK, w=6, a=255):
        P = [self.P(x, y) for x, y in pts]; W = self.L(w)
        self.d.line(P, fill=c[:3] + (a,), width=int(W), joint="curve")
        for p in (P[0], P[-1]): r = W / 2; self.d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=c[:3] + (a,))
    def arc(self, cx, cy, r, a0, a1, c=INK, w=6, n=24, a=255):
        self.line([(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)], c, w, a)
    def text(self, x, y, s, size, c=INK, font="b", anchor="mm", a=255, stroke=0, sc=INK):
        f = self.fonts(font, int(self.L(size)))
        self.d.text(self.P(x, y), s, font=f, fill=c[:3] + (a,), anchor=anchor,
                    stroke_width=int(self.L(stroke)), stroke_fill=sc[:3] + (a,))


class Preset:
    DESCRIPTION = "Golden-parachute day-cycle diorama: glossy supersampled vector props, parallax towers, one scene per line."
    STYLE = dict(bg_size=(3840, 2160),
                 fonts=dict(lyric=["BricolageGrotesque-VariableFont@ExtraBold", "Outfit[wght]@Bold", "DejaVuSans-Bold"],
                            title=["Fraunces-VariableFont@Black", "DejaVuSerif-Bold"], mono=["IBMPlexMono-Medium"]),
                 text=CREAM, sung=GOLD, keyword=(140, 230, 220),
                 keywords=("years", "boss", "contract", "deal", "word", "family", "champagne", "hr", "badge", "boat",
                           "clock", "lock", "synergy", "empire", "mine", "own", "alive", "hey!", "hey"),
                 size=72, hook_size=86, upper=False, layout="lower", kinetic="pop", pop=0.12, hook_slam=0.14,
                 kinetic_time=0.28, unsung_alpha=0.45, band=0.62, band_color=(20, 26, 52), band_radius=36,
                 text_y=0.86, lead=0.12, stroke=3, stroke_color=INK, shadow=True, shadow_px=4, glow=0,
                 punch=0.012, shake=0.5, fade_in=1.0, fade_out=6.0,
                 title_card=True, title_mode="center", title_size=124, subtitle="part two of Chained to the Clock",
                 section_card=True, section_hold=1.6, section_color=GOLD, section_size=40)
    TITLES = {"verse": "monday, 9:00 a.m.", "pre-chorus": "overtime", "chorus": "set for years",
              "bridge": "after hours", "outro": "clock out"}

    def __init__(self, ctx):
        self.c = ctx
        self.K = float(ctx.opts.get("k", 2.0))
        self.W, self.H = int(1920 * self.K), int(1080 * self.K)
        self.STYLE = dict(self.STYLE, bg_size=(self.W, self.H))
        ctx.section_titles = self.TITLES
        from lv_render import find_font, resolve_font
        self._fc = {}
        paths = {"b": resolve_font("BricolageGrotesque-VariableFont@ExtraBold"), "t": resolve_font("Fraunces-VariableFont@Black"),
                 "m": resolve_font("IBMPlexMono-Medium")}
        def fonts(key, size):
            size = max(4, int(round(size / 4.0)) * 4)
            k = (key, size)
            if len(self._fc) > 60: self._fc.clear()
            if k not in self._fc:
                p, var = paths[key]; f = ImageFont.truetype(p, size)
                if var:
                    try: f.set_variation_by_name(var)
                    except Exception: pass
                self._fc[k] = f
            return self._fc[k]
        self.fonts = fonts
        rnd = random.Random(7)
        K = self.K
        # skyline plates (2 parallax depths), lit-window overlays
        self.city = []
        for depth, (col, hmin, hmax, y0) in enumerate((((150, 170, 200), 260, 560, 820), ((90, 110, 150), 200, 440, 900))):
            Wp = int(2600 * K); base = Image.new("RGBA", (Wp, self.H), (0, 0, 0, 0)); lit = Image.new("RGBA", (Wp, self.H), (0, 0, 0, 0))
            pen = Pen(base, K, fonts); lp = Pen(lit, K, fonts); x = 0
            while x < 2600:
                bw = rnd.uniform(90, 190); bh = rnd.uniform(hmin, hmax); top = y0 - bh
                pen.rect(x, top, x + bw, 1080, shade(col, 1.08), shade(col, 0.85), r=6, ink=None)
                if rnd.random() < 0.35: pen.rect(x + bw * 0.4, top - 40, x + bw * 0.46, top, shade(col, 0.9), ink=None)
                for wy in np.arange(top + 22, min(1080, y0 + 200), 34):
                    for wx in np.arange(x + 14, x + bw - 18, 26):
                        pen.rect(wx, wy, wx + 12, wy + 18, shade(col, 1.2), ink=None, r=2)
                        if rnd.random() < 0.55: lp.rect(wx, wy, wx + 12, wy + 18, (255, 220, 140), ink=None, r=2)
                x += bw + rnd.uniform(6, 30)
            self.city.append((base, lit, 0.25 + 0.2 * depth))
        self.papers = [(rnd.uniform(0, 1920), rnd.uniform(0, 1), rnd.uniform(18, 34), rnd.uniform(0, 6.28), rnd.uniform(0.012, 0.03)) for _ in range(7)]
        self.conf = [(rnd.uniform(-1, 1), rnd.uniform(0.3, 1), rnd.choice((GOLD, TEAL, CORAL, CREAM, SHIRT)), rnd.uniform(0, 6.28)) for _ in range(40)]
        self.scene_for = [self.pick(i, L) for i, L in enumerate(ctx.lines)]
        self.chorus_n = {}
        n = 0
        for i, L in enumerate(ctx.lines):
            if L["text"].lower().startswith("set for years, set"):
                n += 1
            self.chorus_n[i] = n

    # ---------------- scene table ----------------
    def pick(self, i, L):
        t = L["text"].lower()
        table = [("coffee", "coffee"), ("land this contract", "family"), ("shook my hand", "handshake"), ("close this deal", "promise"),
                 ("clocked in", "clock"), ("weekends", "calendar"), ("set for years, set", "chart"), ("out of here", "exit"),
                 ("gave our nights", "nights"), ("still alive", "alive"), ("ink is dry", "lights"), ("crying", "toast"),
                 ("frontier", "toast"), ("champagne", "champagne"), ("hr email", "email"), ("badge", "badge"), ("boat", "boat"),
                 ("alarm", "alarm"), ("tick tock", "clockstop"), ("clock out", "clockout"), ("the lock", "lock"), ("best thing", "shrug"), ("chain right off", "chain"),
                 ("empire", "empire"), ("build my own", "own"), ("tick tock", "clockstop"), ("clock out", "clockout"),
                 ("hey", "hey"), ("set for years", "sunrise")]
        for k, v in table:
            if k in t: return v
        return "chart"

    def active(self, t):
        out = []; lines = self.c.lines
        for i, L in enumerate(lines):
            s = L["s"] - 0.35
            e = lines[i + 1]["s"] - 0.35 if i + 1 < len(lines) else self.c.dur
            if i == 0: s = -1
            if s - 0.7 <= t < e:
                a = ease((t - (s - 0.7)) / 0.7) if i > 0 else 1.0
                out.append((i, a, (t - s), max(0.5, e - s)))
        return out[-2:]

    # ---------------- characters ----------------
    def worker(self, p, x, y, s=1, shirt=SHIRT, arm=0.0, box=False, hair=INK, face=1, bob=0):
        p.at(p.ox, p.oy, p.s)
        X = lambda v: x + v * s; Y = lambda v: y + bob + v * s
        p.rect(X(-38), Y(-40), X(38), Y(70), shirt, shade(shirt, 0.75), r=34 * s, w=5)
        p.rect(X(-30), Y(66), X(-6), Y(120), SUIT2, w=5, r=8); p.rect(X(6), Y(66), X(30), Y(120), SUIT2, w=5, r=8)
        p.ell(X(0), Y(-82), 40 * s, 42 * s, SKIN, SKIN2)
        p.d.chord([*p.P(X(-42), Y(-126)), *p.P(X(42), Y(-52))], 180, 360, fill=hair + (255,))
        ex = 12 * s * face
        p.ell(X(-14 + ex * 0.3), Y(-80), 4.5 * s, 6 * s, INK, ink=None); p.ell(X(14 + ex * 0.3), Y(-80), 4.5 * s, 6 * s, INK, ink=None)
        if box:
            p.rect(X(-52), Y(-10), X(52), Y(60), BOX, BOX2, r=6, w=5); p.line([(X(-52), Y(8)), (X(52), Y(8))], BOX2, 4)
            p.rect(X(-20), Y(-34), X(4), Y(-10), GREEN, w=4, r=4)  # plant
        else:
            a = math.radians(-90 * arm)
            p.line([(X(34), Y(-20)), (X(34 + 64 * math.cos(a + 1.2)), Y(-20 + 64 * math.sin(a + 1.2)))], shade(shirt, 0.7), 18 * s)
            p.line([(X(-34), Y(-20)), (X(-48), Y(36))], shade(shirt, 0.7), 18 * s)

    def boss(self, p, x, y, s=1, arm=0.0, glasses=False, mug=False, crown=False, bob=0):
        X = lambda v: x + v * s; Y = lambda v: y + bob + v * s
        p.rect(X(-58), Y(-50), X(58), Y(90), SUIT, SUIT2, r=46 * s, w=6)
        p.poly([(X(-16), Y(-50)), (X(16), Y(-50)), (X(0), Y(-8))], WHITE, w=0, ink=None)
        p.poly([(X(-7), Y(-42)), (X(7), Y(-42)), (X(10), Y(30)), (X(0), Y(42)), (X(-10), Y(30))], GOLD, w=3)
        p.ell(X(0), Y(-100), 48 * s, 50 * s, SKIN, SKIN2, w=6)
        p.d.chord([*p.P(X(-50), Y(-156)), *p.P(X(50), Y(-96))], 180, 360, fill=(200, 200, 210, 255))
        if glasses:
            p.rect(X(-38), Y(-112), X(-4), Y(-92), INK, r=8, ink=None); p.rect(X(4), Y(-112), X(38), Y(-92), INK, r=8, ink=None)
            p.line([(X(-4), Y(-104)), (X(4), Y(-104))], INK, 4)
        else:
            p.ell(X(-16), Y(-102), 5 * s, 6 * s, INK, ink=None); p.ell(X(16), Y(-102), 5 * s, 6 * s, INK, ink=None)
        p.arc(X(0), Y(-84), 18 * s, 20, 160, INK, 5)
        if crown: p.poly([(X(-34), Y(-150)), (X(-34), Y(-186)), (X(-17), Y(-166)), (X(0), Y(-192)), (X(17), Y(-166)), (X(34), Y(-186)), (X(34), Y(-150))], GOLD, w=4)
        a = math.radians(-90 * arm)
        hx, hy = X(56 + 80 * math.cos(a + 1.1)), Y(-30 + 80 * math.sin(a + 1.1))
        p.line([(X(52), Y(-26)), (hx, hy)], SUIT2, 24 * s)
        p.ell(hx, hy, 14 * s, 14 * s, SKIN, w=4)
        if mug:
            p.rect(hx - 22 * s, hy - 56 * s, hx + 22 * s, hy - 6 * s, WHITE, PAPER2, r=8, w=5)
            p.arc(hx + 26 * s, hy - 32 * s, 13 * s, -90, 90, INK, 6)
        p.line([(X(-52), Y(-26)), (X(-70), Y(40))], SUIT2, 24 * s)

    def paper(self, p, x, y, w, h, rot, lines=5, sig=0.0):
        c, s_ = math.cos(rot), math.sin(rot)
        R = lambda dx, dy: (x + dx * c - dy * s_, y + dx * s_ + dy * c)
        p.poly([R(-w / 2, -h / 2), R(w / 2, -h / 2), R(w / 2, h / 2), R(-w / 2, h / 2)], PAPER, w=4)
        for k in range(lines):
            yy = -h / 2 + h * (0.18 + 0.12 * k)
            p.line([R(-w * 0.36, yy), R(w * (0.36 if k % 3 else 0.2), yy)], PAPER2, max(2, h * 0.025))
        if sig > 0:
            pts = [R(-w * 0.32 + w * 0.6 * j / 20, h * 0.36 + h * 0.04 * math.sin(j * 1.3)) for j in range(int(20 * sig) + 1)]
            if len(pts) > 1: p.line(pts, (30, 60, 160), max(2, h * 0.02))

    def clock(self, p, x, y, r, hm, mm):
        p.ell(x, y, r, r, WHITE, PAPER2, w=8)
        for k in range(12):
            a = k * math.pi / 6; p.line([(x + r * 0.78 * math.cos(a), y + r * 0.78 * math.sin(a)), (x + r * 0.88 * math.cos(a), y + r * 0.88 * math.sin(a))], INK, 6)
        p.line([(x, y), (x + r * 0.5 * math.sin(hm), y - r * 0.5 * math.cos(hm))], INK, 12)
        p.line([(x, y), (x + r * 0.75 * math.sin(mm), y - r * 0.75 * math.cos(mm))], INK, 8)
        p.ell(x, y, 10, 10, GOLD, w=4)

    # ---------------- scenes (units: 1920x1080, stage centre ~ (960, 470)) ----------------
    def scene(self, name, p, u, lt, dur, t, st, i):
        b = -10 * math.exp(-st["dt"] * 6) if st["down"] else -6 * math.exp(-st["dt"] * 6)
        sway = math.sin(t * 1.3)
        if name == "coffee":
            p.rect(520, 560, 1400, 600, WOOD, WOOD2, r=10)
            for k, x in enumerate((640, 1280)): self.worker(p, x, 520, 0.9, shirt=(SHIRT, GREEN)[k], bob=b * 0.5)
            self.boss(p, 960, 470, 1.1, arm=ease(lt / 0.8) * 1.0, mug=True, bob=b)
            for k in range(3):
                ph = (t * 0.6 + k / 3) % 1
                p.line([(1060 + 14 * math.sin(ph * 6 + k + j * 0.5), 300 - ph * 120 - j * 8) for j in range(6)], (255, 255, 255), 6, a=int(200 * math.sin(ph * math.pi)))
        elif name == "family":
            self.boss(p, 760, 480, 1.15, arm=0.6 + 0.2 * sway, bob=b)
            p.rect(980, 230, 1380, 360, WHITE, r=40, w=6); p.poly([(1010, 350), (1060, 352), (990, 400)], WHITE, w=0, ink=None)
            p.text(1180, 295, "we're family!", 52, INK, "t")
            self.paper(p, 1220, 520, 220, 280, 0.08 * sway, sig=0)
            p.text(1220, 420, "CONTRACT", 26, INK, "m")
        elif name == "handshake":
            g = ease(lt / 0.8)
            for side in (-1, 1):
                x0 = 960 + side * (520 - 445 * g)
                p.line([(960 + side * 900, 520), (x0 + side * 60, 500)], SUIT if side < 0 else SHIRT2, 90)
                p.ell(x0, 500 + 8 * math.sin(t * 8) * g, 70, 56, SKIN, SKIN2, w=6)
            for k in range(5):
                a = k * 1.25 + t * 0.5; r = 150 + 10 * math.sin(t * 2 + k)
                sx_, sy_ = 960 + r * math.cos(a), 470 + r * 0.6 * math.sin(a); q = 16 + 4 * math.sin(t * 3 + k)
                p.poly([(sx_, sy_ - q), (sx_ + q * 0.4, sy_), (sx_, sy_ + q), (sx_ - q * 0.4, sy_)], GOLD, w=3, a=int(230 * g))
        elif name == "promise":
            self.boss(p, 640, 490, 1.0, arm=0.4, bob=b)
            self.worker(p, 1320, 520, 1.0, bob=b * 0.5, face=-1)
            g = back(lt / 0.7)
            p.at(960, 260, max(0.01, g)); p.rect(-260, -70, 260, 70, GOLD, GOLD2, r=60, w=6); p.text(0, 0, "SET FOR YEARS", 60, INK, "b"); p.at(0, 0, 1)
            for k in range(min(6, int(lt / 0.4) + 1)):
                self.paper(p, 900 + k * 24, 600 - k * 14, 110, 80, -0.1 + k * 0.04, lines=2)
                p.text(900 + k * 24, 600 - k * 14, str(2027 + k), 22, INK, "m")
        elif name == "clock":
            sp = 1.2 + 0.6 * (i % 2)
            self.clock(p, 960, 400, 220, t * sp * 0.25, t * sp * 3)
            for side in (-1, 1):
                self.worker(p, 960 + side * 420, 560, 0.9, shirt=(SHIRT if side < 0 else GREEN), bob=b, arm=0.3)
            p.rect(1240, 300, 1380, 480, PAPER, r=8); p.text(1310, 330, "TIME", 22, INK, "m")
            for k in range(4): p.rect(1260, 350 + k * 30, 1360, 368 + k * 30, PAPER2 if k > (lt * 2) % 4 else GOLD, ink=None, r=3)
        elif name == "calendar":
            p.rect(700, 200, 1220, 640, WHITE, PAPER2, r=24, w=7); p.rect(700, 200, 1220, 280, CORAL, shade(CORAL, 0.85), r=24, w=7)
            p.text(960, 240, "WEEKENDS", 40, WHITE, "b")
            days = "MTWTFSS"
            for k in range(7):
                x = 740 + k * 68; p.text(x + 30, 310, days[k], 26, INK, "b")
                for r_ in range(4):
                    y = 350 + r_ * 66; p.rect(x, y, x + 60, y + 54, (250, 250, 250) if k < 5 else (255, 236, 200), r=8, w=3)
                    if k >= 5 and lt > 0.3 + (r_ * 2 + k - 5) * 0.25:
                        p.line([(x + 8, y + 8), (x + 52, y + 46)], (60, 80, 180), 7); p.line([(x + 52, y + 8), (x + 8, y + 46)], (60, 80, 180), 7)
            px = 1260 + 30 * math.sin(t * 3); p.line([(px, 380), (px + 80, 260)], GOLD2, 22); p.ell(px, 380, 10, 10, INK, ink=None)
        elif name == "chart":
            n = self.chorus_n.get(i, 1)
            p.rect(560, 640, 1360, 652, INK, ink=None)
            hs = [120, 190, 260, 340, 430]
            for k, h in enumerate(hs):
                g = ease((lt - k * 0.15) / 0.6)
                if n == 2 and k >= 3: h = h * (1 - 0.7 * ease((lt - 1.2) / 1.0))
                p.rect(600 + k * 150, 640 - h * g, 700 + k * 150, 640, GOLD if k % 2 == 0 else TEAL, shade(GOLD if k % 2 == 0 else TEAL, 0.7), r=10, w=6)
            if n != 2 or lt < 1.2:
                pts = [(620 + k * 150, 600 - hs[k] - 30) for k in range(5)]
                g = ease(lt / 1.2); m = max(2, int(len(pts) * g) + 1)
                p.line(pts[:m], CORAL, 12)
            else:
                p.line([(620, 470), (920, 300), (1220, 560 + 40 * ease(lt - 1.2))], CORAL, 12)
            if n >= 3: self.worker(p, 1420, 520, 0.9, arm=0.9 + 0.1 * sway, bob=b)
        elif name == "exit":
            p.rect(1220, 180, 1500, 640, (170, 200, 210), (120, 150, 170), r=10, w=7)
            p.rect(1260, 130, 1460, 180, GREEN, r=10, w=5); p.text(1360, 155, "EXIT", 34, WHITE, "b")
            wx = 500 + 700 * ease(lt / max(1, dur))
            self.worker(p, wx, 520 + abs(math.sin(t * 6)) * -10, 1.0, box=True)
        elif name == "nights":
            p.rect(700, 140, 1220, 700, (70, 80, 120), (40, 46, 80), r=8, w=7)
            for r_ in range(7):
                for k in range(5):
                    on = (r_ * 5 + k + int(t * 0.8)) % 4 != 0
                    p.rect(735 + k * 96, 170 + r_ * 74, 805 + k * 96, 225 + r_ * 74, (255, 214, 130) if on else (60, 70, 110), r=4, w=3)
            p.ell(1440, 230, 70, 70, CREAM, (230, 225, 200), w=0, ink=None)
            p.ell(1470, 210, 60, 60, sky_at(t)[0], w=0, ink=None)
        elif name == "lights":
            self.paper(p, 820, 470, 300, 380, -0.06, sig=ease(lt / 1.5))
            g = 1 - ease((lt - 1.4) / 1.6)
            p.line([(1260, 640), (1300, 400), (1420, 330)], INK, 14)
            p.poly([(1380, 300), (1500, 280), (1520, 380), (1400, 400)], GOLD, w=5)
            p.ell(1450, 395, 120, 40, (255, 230, 160), w=0, ink=None, a=int(140 * g))
            p.line([(1060, 600), (1160, 420)], (40, 50, 90), 18); p.ell(1060, 600, 8, 8, (30, 60, 160), ink=None)
        elif name == "alive":
            self.worker(p, 960, 520, 1.2, arm=1.0, bob=b, shirt=GREEN)
            for k in range(8):
                a = k * math.pi / 4 + t * 0.2
                p.line([(960 + 220 * math.cos(a), 420 + 220 * math.sin(a)), (960 + 270 * math.cos(a), 420 + 270 * math.sin(a))], GOLD, 10)
        elif name == "toast":
            p.rect(0, 610, 1920, 700, WATER, WATER2, ink=None)
            bx = 1500 + 40 * math.sin(t * 0.4)
            p.poly([(bx - 90, 600), (bx + 90, 600), (bx + 60, 625), (bx - 70, 625)], WHITE, w=4)
            p.rect(bx - 40, 572, bx + 30, 600, WHITE, w=4, r=6)
            for k, x in enumerate((760, 960, 1160)):
                g = ease((lt - k * 0.2) / 0.6)
                gx, gy = x, 480 - 60 * g + b
                p.poly([(gx - 46, gy - 110), (gx + 46, gy - 110), (gx + 14, gy - 10), (gx - 14, gy - 10)], (255, 236, 170), w=6)
                p.line([(gx, gy - 10), (gx, gy + 70)], INK, 8); p.line([(gx - 36, gy + 72), (gx + 36, gy + 72)], INK, 10)
                for j in range(3):
                    ph = (t * 0.8 + j / 3 + k * 0.2) % 1
                    p.ell(gx - 16 + j * 14, gy - 30 - ph * 70, 5, 5, WHITE, ink=None, a=int(220 * (1 - ph)))
        elif name == "champagne":
            g = ease(lt / 0.5)
            p.at(820, 470, 1)
            ang = -0.5
            c, s_ = math.cos(ang), math.sin(ang)
            R = lambda dx, dy: (dx * c - dy * s_, dx * s_ + dy * c)
            p.poly([R(-60, 200), R(60, 200), R(60, -20), R(20, -110), R(20, -170), R(-20, -170), R(-20, -110), R(-60, -20)], (40, 110, 80), w=6)
            p.poly([R(-60, 0), R(60, 0), R(60, 80), R(-60, 80)], GOLD, w=0, ink=None)
            cx, cy = R(0, -180)
            fl = ease(lt / 1.2); p.ell(cx + 420 * fl, cy - 260 * math.sin(fl * math.pi) - 60 * fl, 18, 14, WOOD, w=4)
            for k in range(16):
                ph = (lt * 0.7 + k / 16) % 1
                p.ell(cx + 300 * ph * (0.6 + 0.4 * math.sin(k)), cy - 200 * ph + 30 * math.sin(k * 3), 7 + 4 * (k % 3), 7 + 4 * (k % 3), (255, 240, 190), ink=None, a=int(220 * (1 - ph)))
            p.at(0, 0, 1)
            self.paper(p, 1300, 500, 240, 300, 0.05, sig=1.0)
            p.ell(1300, 360, 40, 26, CORAL, w=4); p.poly([(1290, 370), (1250, 440), (1280, 430)], CORAL, w=4); p.poly([(1310, 370), (1350, 440), (1320, 430)], CORAL, w=4)
        elif name == "email":
            p.rect(560, 170, 1360, 640, (60, 70, 100), (36, 42, 70), r=26, w=7)
            p.rect(590, 200, 1330, 610, WHITE, (236, 240, 248), r=10, w=0, ink=None)
            p.rect(590, 200, 1330, 250, (220, 228, 244), r=10, ink=None)
            for k, c in enumerate((CORAL, GOLD, GREEN)): p.ell(620 + k * 30, 225, 9, 9, c, ink=None)
            p.text(620, 290, "From: HR <people@company>", 28, INK, "m", anchor="lm")
            p.text(620, 335, "Subject: Exciting changes!", 28, INK, "m", anchor="lm")
            msg = "Please don't take it personal :)"
            n = int(len(msg) * ease(lt / 1.8)); p.text(620, 410, msg[:n] + ("|" if int(t * 2) % 2 else ""), 34, INK, "b", anchor="lm")
            p.rect(620, 480, 860, 540, TEAL, r=12, w=4); p.text(740, 510, "OK", 30, WHITE, "b")
            p.rect(560, 640, 1360, 670, (90, 100, 130), r=10, w=6)
        elif name == "badge":
            p.rect(1060, 140, 1420, 660, GLASS + (0,), (150, 190, 215), r=8, w=8, a=200)
            p.line([(1240, 140), (1240, 660)], INK, 6)
            p.rect(980, 330, 1040, 430, (60, 70, 90), r=10, w=5)
            ok = int(lt * 1.5) % 2
            p.ell(1010, 360, 14, 14, AMBER if lt > 0.5 else (90, 100, 120), w=3)
            if lt > 0.5: p.line([(998, 390), (1022, 414)], AMBER, 6); p.line([(1022, 390), (998, 414)], AMBER, 6)
            g = ease(lt / 0.6); bx = 820 + 120 * g
            self.worker(p, 700, 520, 1.0, box=True, face=1)
            p.line([(760, 480), (bx, 380)], SHIRT2, 16)
            p.rect(bx - 34, 350, bx + 34, 410, WHITE, r=6, w=4); p.ell(bx, 372, 12, 12, SHIRT, w=3)
        elif name == "boat":
            p.rect(0, 600, 1920, 700, WATER, WATER2, ink=None)
            for k in range(10):
                x = (k * 220 + t * 30) % 2100 - 90
                p.arc(x, 640 + 20 * (k % 2), 40, 200, 340, (200, 230, 250), 5)
            bob = 10 * math.sin(t * 1.6); bx = 700 + 300 * ease(lt / max(1, dur))
            p.at(bx, 560 + bob, 1)
            p.poly([(-280, 0), (300, 0), (230, 90), (-220, 90)], WHITE, w=7)
            p.rect(-160, -80, 140, 0, (240, 244, 250), PAPER2, r=16, w=6)
            for k in range(4): p.rect(-130 + k * 66, -60, -90 + k * 66, -30, GLASS, r=6, w=3)
            p.line([(0, -80), (0, -280)], INK, 8)
            p.poly([(0, -280), (150, -240), (0, -200)], GOLD, w=5)
            p.text(-20, 45, "SET 4 YEARS", 34, SUIT, "b")
            p.at(0, 0, 1)
            self.boss(p, bx + 200, 470 + bob, 0.75, arm=0.9 + 0.25 * math.sin(t * 5), glasses=True, crown=True)
        elif name == "alarm":
            self.clock(p, 960, 410, 190, math.radians(180), 0)
            for side in (-1, 1): p.ell(960 + side * 120, 220, 54, 36, GOLD, GOLD2, w=6)
            p.line([(880, 590), (840, 650)], INK, 12); p.line([(1040, 590), (1080, 650)], INK, 12)
            g = ease((lt - 0.8) / 1.2)
            for k in range(5):
                side = -1 if k % 2 else 1
                x = 960 + side * (260 + 60 * k + 140 * g); y = 420 + 20 * k + 220 * g * g
                p.ell(x, y, 34, 22, (170, 175, 190), ink=INK, w=6); p.ell(x, y, 18, 8, sky_at(t)[1], ink=None)
        elif name == "lock":
            p.rect(760, 150, 1160, 680, WOOD, WOOD2, r=10, w=7)
            p.arc(960, 380, 70, 180, 360, (170, 175, 190), 26)
            p.rect(870, 370, 1050, 510, GOLD, GOLD2, r=18, w=7); p.ell(960, 430, 16, 16, INK, ink=None)
            p.rect(1200, 340, 1430, 420, PAPER, r=40, w=5); p.text(1315, 380, "FREE", 40, TEAL, "b")
            p.line([(1050, 400), (1200, 380)], INK, 4)
        elif name == "shrug":
            p.ell(960, 900, 900, 300, (90, 160, 110), (60, 120, 80), ink=None)
            p.ell(1400, 480, 90, 90, GOLD, w=0, ink=None, a=200)
            self.worker(p, 900, 500, 1.1, arm=0.5 + 0.2 * sway, bob=b * 0.5)
            p.text(1080, 330, "?", 90, CREAM, "t")
        elif name == "chain":
            p.line([(380, 520), (900, 470)], SKIN2, 120); p.ell(930, 465, 80, 70, SKIN, SKIN2, w=6)
            g = ease((lt - 0.6) / 1.4)
            for k in range(7):
                x = 780 + 0 * k; y = 470
                ox = (k - 3) * 46
                yy = y + ox * 0.1 + g * (120 + 40 * k) ** 1.05 * g
                p.ell(760 + ox + g * 30 * k, yy, 30, 20, (170, 175, 190), ink=INK, w=6)
                p.ell(760 + ox + g * 30 * k, yy, 14, 7, sky_at(t)[1], ink=None)
            p.rect(1150, 260, 1550, 380, WHITE, r=50, w=6); p.text(1350, 320, "“synergy”", 56, INK, "t")
        elif name == "empire":
            n = min(9, int(lt / 0.4) + 1)
            for k in range(n):
                g = ease((lt - k * 0.4) / 0.4)
                y = 640 - (k + 1) * 52 - 60 * (1 - g)
                p.rect(1040, y, 1300, y + 50, (90, 100, 140), (60, 66, 100), r=4, w=5, a=int(255 * g))
                for j in range(5): p.rect(1060 + j * 48, y + 14, 1084 + j * 48, y + 36, (255, 214, 130), ink=None, r=2, a=int(255 * g))
            self.worker(p, 860, 520, 1.0, arm=0.8, bob=b)
            self.clock(p, 620, 260, 70, t * 0.2, t * 2.4)
        elif name == "own":
            cols = [TEAL, GOLD, CORAL, GREEN, SHIRT, GOLD]
            for k in range(min(6, int(lt / 0.45) + 1)):
                g = back((lt - k * 0.45) / 0.5)
                x = 1000 + (k % 3) * 120; y = 640 - (k // 3 + 1) * 110
                p.at(x + 55, y + 55, max(0.01, g)); p.rect(-55, -55, 55, 55, cols[k], shade(cols[k], 0.8), r=12, w=6); p.at(0, 0, 1)
            if lt > 2.6:
                g = back((lt - 2.6) / 0.6)
                p.line([(1180, 420), (1180, 420 - 160 * g)], INK, 8); p.poly([(1180, 420 - 160 * g), (1300, 440 - 160 * g), (1180, 470 - 160 * g)], GOLD, w=5)
                p.text(1230, 450 - 160 * g, "MINE", 20, INK, "b")
            self.worker(p, 780, 520, 1.1, arm=0.9, bob=b, shirt=GREEN)
        elif name == "clockstop":
            sp = max(0.0, 1 - lt / 2.4)
            ang = 2.0 + (1 - (1 - min(1, lt / 2.4)) ** 2) * 2.4 * 3
            self.clock(p, 960, 420, 250, 2.2, ang)
            if lt > 2.4: p.text(960, 740 - 60, "", 10)
        elif name == "clockout":
            p.rect(1180, 160, 1480, 650, sky_at(t)[1], (255, 236, 190), r=8, w=8)
            g = ease(lt / 1.5); p.poly([(1180, 160), (1180 + 300 * (1 - g * 0.8), 190), (1180 + 300 * (1 - g * 0.8), 620), (1180, 650)], WOOD, w=6)
            p.rect(560, 270, 760, 520, PAPER, PAPER2, r=10, w=6); p.text(660, 300, "TIME", 26, INK, "m")
            p.rect(600, 420, 720, 450, GOLD if lt > 0.6 else PAPER2, ink=None, r=4); p.text(660, 480, "OUT", 26, INK, "b")
            self.worker(p, 900 + 220 * ease((lt - 1) / 2), 520, 1.0, bob=b, face=1)
        elif name == "sunrise":
            p.ell(960, 640, 260, 260, (255, 210, 120), (255, 170, 90), ink=None, a=230)
            p.rect(0, 640, 1920, 700, (70, 90, 120), ink=None)
            self.worker(p, 960 + 140 * ease(lt / 2), 520, 1.0, arm=0.3)
        elif name == "hey":
            for k, (x, sh) in enumerate(((620, SHIRT), (820, GREEN), (1100, CORAL), (1300, TEAL))):
                j = abs(math.sin((t * 2.03 + k * 0.4) * math.pi / 1)) * 40
                self.worker(p, x, 520 - j, 1.0, shirt=sh, arm=1.0)
            for k, (ux, uy, c, ph) in enumerate(self.conf):
                yy = (uy * 900 + lt * 120 * (0.6 + uy)) % 900 - 100
                xx = 960 + ux * 900 + 30 * math.sin(t + ph)
                a = ph + t * 2; w_, h_ = 12, 20 * abs(math.cos(a))
                p.rect(xx - w_, yy - h_ - 1, xx + w_, yy + h_ + 1, c, ink=None, r=3)

    # ---------------- frame ----------------
    def background(self, t, st):
        K, W, H = self.K, self.W, self.H
        top, bot = sky_at(t)
        g = np.linspace(0, 1, 270)[:, None, None]
        sky = (np.array(top) * (1 - g) + np.array(bot) * g).astype(np.uint8)
        im = Image.fromarray(sky).resize((W, H), Image.BICUBIC).convert("RGBA")
        nt = night_at(t)
        d = ImageDraw.Draw(im)
        # sun/moon arc across the day
        su = min(1, t / 112); sx = (300 + 1320 * su) * K; sy = (140 + 260 * (2 * su - 1) ** 2) * K
        sc = mix((255, 236, 170), (255, 170, 120), su)
        glow = Image.new("RGBA", (W // 8, H // 8), (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
        gd.ellipse([sx / 8 - 30 * K, sy / 8 - 30 * K, sx / 8 + 30 * K, sy / 8 + 30 * K], fill=sc + (int(110 * (1 - nt)),))
        im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(10 * K)).resize((W, H), Image.BICUBIC))
        if nt < 0.99: d.ellipse([sx - 70 * K, sy - 70 * K, sx + 70 * K, sy + 70 * K], fill=sc + (int(255 * (1 - nt)),))
        if nt > 0.01:
            rnd = random.Random(3)
            for _ in range(80):
                x, y = rnd.uniform(0, W), rnd.uniform(0, H * 0.5); r = rnd.choice((1.5, 2, 3)) * K
                tw = 0.75 + 0.25 * math.sin(t * 0.7 + x)
                d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 250, 230, int(220 * nt * tw)))
        # parallax skyline
        for base, lit, spd in self.city:
            off = int((t * 14 * spd * K) % (base.width - W))
            im.alpha_composite(base.crop((off, 0, off + W, H)))
            if nt > 0.02:
                L = lit.crop((off, 0, off + W, H)); a = L.getchannel("A").point(lambda v, f=nt: int(v * f)); L.putalpha(a)
                im.alpha_composite(L)
        # dim haze so props pop
        im.alpha_composite(Image.new("RGBA", (W, H), (20, 26, 52, int(40 + 50 * nt))))
        # drifting office paper
        pen = Pen(im, K, self.fonts)
        for x0, y0, sz, ph, spd in self.papers:
            y = ((y0 - t * spd) % 1.2 - 0.1) * 1080; x = x0 + 40 * math.sin(t * 0.5 + ph)
            self.paper(pen, x, y, sz * 1.3, sz * 1.65, math.sin(t * 0.4 + ph) * 0.6, lines=3)
        # scene layer(s) with soft drop shadow
        props = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        for i, a, lt, dur in self.active(t):
            lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)) if a < 0.999 else props
            pen = Pen(lay, K, self.fonts)
            ent = back(min(1, lt / 0.6 + 0.0)) if lt > 0 else 0
            # gentle slide-in drift so every scene moves
            pen.at(30 * (1 - ease(lt / 0.8)) + 8 * math.sin(t * 0.35), 30 * (1 - ent) - 30, 1)
            self._scene_xform(pen)
            self.scene(self.scene_for[i], pen, min(1, lt / dur), lt, dur, t, st, i)
            if lay is not props:
                al = lay.getchannel("A").point(lambda v, f=a: int(v * f)); lay.putalpha(al); props.alpha_composite(lay)
        sm = props.getchannel("A").resize((W // 8, H // 8), Image.BOX).filter(ImageFilter.GaussianBlur(3))
        sh = Image.new("RGBA", sm.size, INK + (0,)); sh.putalpha(sm.point(lambda v: int(v * 0.42)))
        sh = sh.resize((W, H), Image.BICUBIC)
        im.alpha_composite(sh, (int(10 * K), int(16 * K)))
        im.alpha_composite(props)
        return im

    def _scene_xform(self, pen):
        # wrap P so the pen's own at() calls inside scenes compose with the scene drift offset
        bx, by = pen.ox, pen.oy
        orig_at = pen.at
        def at(ox, oy, s=1):
            pen.ox, pen.oy, pen.s = bx + ox, by + oy, s; return pen
        pen.at = at; pen.at(0, 0, 1)

    def camera(self, t, st):
        return (14 * self.K * math.sin(t * 2 * math.pi / 23), 8 * self.K * math.sin(t * 2 * math.pi / 31), 1.0 + 0.012 * math.sin(t * 2 * math.pi / 17), 0)
