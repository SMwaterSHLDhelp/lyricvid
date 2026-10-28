"""Skeleton Crew: a playful Halloween 'sticker-book' style. Flat cut-paper cartoon props with thick
plum outlines on a purple moonlit night, one acted-out scene per lyric line, characters bouncing
on the beat, fog that drifts, bats that glide. Luckiest Guy lyrics, Creepster titles.
Photosensitive-safe: no lightning, no flashes, scene changes are 0.8 s crossfades, sky tint drifts slowly."""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = (30, 12, 44); NIGHT0 = (20, 10, 42); NIGHT1 = (70, 30, 100); HILL = (36, 18, 54); HILL2 = (50, 26, 72)
PUMP = (255, 140, 36); PUMP2 = (220, 104, 20); SLIME = (130, 232, 84); MOON = (240, 238, 208); BONE = (244, 240, 226)
PURP = (150, 90, 210); STEM = (90, 140, 50); CANDY = (255, 214, 80); GREY = (150, 150, 170); BROWN = (120, 80, 60)
FUR = (110, 90, 80); CHERRY = (190, 50, 120); BLUE = (110, 170, 240); DARK = (14, 8, 22)

def ease(u): u = min(max(u, 0), 1); return u * u * (3 - 2 * u)
def back(u):  # ease-out-back for playful pop-ins
    u = min(max(u, 0), 1); c = 1.70158; return 1 + (c + 1) * (u - 1) ** 3 + c * (u - 1) ** 2

class Preset:
    DESCRIPTION = "Halloween sticker-book: flat cut-paper cartoons on a purple moonlit night, one scene per line."
    STYLE = dict(bg_size=(960, 540),
                 fonts=dict(lyric=["LuckiestGuy-Regular", "DejaVuSans-Bold"], title=["Creepster-Regular", "DejaVuSans-Bold"],
                            mono=["IBMPlexMono-Medium", "DejaVuSansMono"]),
                 text=MOON, sung=SLIME, keyword=PUMP,
                 keywords=("skeleton", "crew", "boo", "bones", "pumpkin", "moonlight", "fog", "vampire", "werewolf",
                           "mummy", "mummy's", "vampire's", "doorbell's", "graveyard's", "witches", "graveyard", "midnight", "ghost", "costume", "doorbell"),
                 size=70, hook_size=80, upper=True, layout="lower", kinetic="pop", pop=0.16, hook_slam=0.2,
                 kinetic_time=0.3, unsung_alpha=0.42, band=0.6, band_color=(22, 10, 34), band_radius=22,
                 text_y=0.84, lead=0.12, stroke=4, stroke_color=OUT, shadow=True, shadow_px=4, glow=0,
                 punch=0.018, shake=0.9, fade_in=0.8, fade_out=4.0,
                 title_card=True, title_mode="center", title_size=120, subtitle="a spooky little dance song",
                 section_card=True, section_hold=1.6, section_color=PUMP, section_size=40)
    TITLES = {"intro": "knock knock", "verse": "who's at the door?", "pre-chorus": "lights down",
              "chorus": "skeleton crew!", "bridge": "midnight", "outro": "see you next year"}

    def __init__(self, ctx):
        self.c = ctx; W, H = self.STYLE["bg_size"]; self.W, self.H = W, H
        ctx.section_titles = self.TITLES
        from lv_render import find_font
        from PIL import ImageFont
        self.fb = lambda s: ImageFont.truetype(find_font("LuckiestGuy-Regular"), s)
        self.fc = lambda s: ImageFont.truetype(find_font("Creepster-Regular"), s)
        self.f40, self.f90, self.f28 = self.fb(40), self.fb(120), self.fc(34)
        rnd = random.Random(31)
        # static plate: sky gradient, stars, moon, hills with tombstones (seeded once)
        y = np.linspace(0, 1, H)[:, None, None]
        sky = (np.array(NIGHT0) * (1 - y) + np.array(NIGHT1) * y) * np.ones((1, W, 1))
        self.sky = Image.fromarray(sky.astype(np.uint8)).convert("RGBA")
        d = ImageDraw.Draw(self.sky)
        for _ in range(70):
            x, yy = rnd.uniform(0, W), rnd.uniform(0, H * 0.55); r = rnd.choice((1, 1, 1.5, 2))
            d.ellipse([x - r, yy - r, x + r, yy + r], fill=MOON + (rnd.randint(90, 200),))
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
        mx, my = W * 0.82, H * 0.2
        gd.ellipse([mx - 90, my - 90, mx + 90, my + 90], fill=(200, 190, 255, 70))
        self.sky.alpha_composite(glow.filter(ImageFilter.GaussianBlur(30)))
        d.ellipse([mx - 48, my - 48, mx + 48, my + 48], fill=MOON)
        for cx, cy, r in ((-14, -10, 9), (16, 12, 6), (8, -22, 5)): d.ellipse([mx + cx - r, my + cy - r, mx + cx + r, my + cy + r], fill=(220, 218, 190))
        pts = [(0, H)] + [(x, H * 0.66 + 22 * math.sin(x / 120) + 10 * math.sin(x / 47)) for x in range(0, W + 20, 20)] + [(W, H)]
        d.polygon(pts, fill=HILL2)
        pts = [(0, H)] + [(x, H * 0.74 + 16 * math.sin(x / 90 + 2)) for x in range(0, W + 20, 20)] + [(W, H)]
        d.polygon(pts, fill=HILL)
        for x in (60, 140, 820, 900):
            gy = H * 0.72; d.rounded_rectangle([x - 16, gy - 34, x + 16, gy + 10], radius=14, fill=(80, 64, 104), outline=OUT, width=3)
        # fog sprite (soft, static), drifted horizontally
        fog = Image.new("RGBA", (W * 2, 160), (0, 0, 0, 0)); fd = ImageDraw.Draw(fog)
        for i in range(26):
            x = rnd.uniform(0, W * 2); r = rnd.uniform(50, 110)
            fd.ellipse([x - r * 1.6, 80 - r * 0.5, x + r * 1.6, 80 + r * 0.5], fill=(200, 190, 230, 40))
        self.fog = fog.filter(ImageFilter.GaussianBlur(18))
        self.bats = [(rnd.uniform(0, 6.28), rnd.uniform(0.04, 0.08), rnd.uniform(0.15, 0.4)) for _ in range(5)]
        self.cache = {}

    # ---------------- helpers ----------------
    def bounce(self, st, amt=14):
        return -amt * math.exp(-st["dt"] * 7) * (1.0 if st["down"] else 0.7)
    def line_at(self, t):
        idx = -1
        for i, L in enumerate(self.c.lines):
            if t >= L["s"] - 0.15: idx = i
        return idx
    def prog(self, li, t):
        L = self.c.lines[li]; return min(1, max(0, (t - L["s"]) / max(0.4, L["e"] - L["s"])))

    def skeleton(self, d, x, y, s, t, st, phase=0.0, wave=False):
        b = self.bounce(st, s * 0.12); sw = math.sin(t * 2 * math.pi * self.c.bpm / 120 + phase)
        y = y + b; w = max(2, int(s * 0.07))
        hx = x + sw * s * 0.08
        d.ellipse([hx - s * 0.2, y - s * 1.15, hx + s * 0.2, y - s * 0.75], fill=BONE, outline=OUT, width=3)
        for ex in (-0.08, 0.08): d.ellipse([hx + s * ex - s * 0.05, y - s * 1.0, hx + s * ex + s * 0.05, y - s * 0.9], fill=OUT)
        d.line([(hx - s * 0.07, y - s * 0.82), (hx + s * 0.07, y - s * 0.82)], fill=OUT, width=2)
        d.line([(hx, y - s * 0.75), (x, y - s * 0.3)], fill=BONE, width=w)
        for k in range(3):
            yy = y - s * (0.68 - k * 0.1); d.line([(x - s * 0.15, yy), (x + s * 0.15, yy)], fill=BONE, width=max(2, w - 2))
        sh = y - s * 0.68
        la = -0.6 - 0.9 * max(0, sw) if not wave else -2.2 + 0.5 * math.sin(t * 6)
        ra = -0.6 - 0.9 * max(0, -sw)
        for side, a in ((-1, la), (1, ra)):
            ex, ey = x + side * s * 0.22, sh + s * 0.18
            hx2, hy2 = ex + side * s * 0.25 * math.cos(a), ey + s * 0.25 * math.sin(a)
            d.line([(x + side * s * 0.12, sh), (ex, ey), (hx2, hy2)], fill=BONE, width=w, joint="curve")
            d.ellipse([hx2 - w, hy2 - w, hx2 + w, hy2 + w], fill=BONE)
        for side in (-1, 1):
            kx = x + side * s * (0.12 + 0.06 * sw * side)
            d.line([(x, y - s * 0.3), (kx, y - s * 0.02), (x + side * s * 0.14, y + s * 0.28)], fill=BONE, width=w, joint="curve")

    def pumpkin(self, d, x, y, r, st, grin=1.0):
        sq = 1 + 0.06 * math.exp(-st["dt"] * 7); rx, ry = r * sq, r / sq * 0.85
        for k, dx in enumerate((-0.5, 0.5, 0)):
            d.ellipse([x + dx * r - rx * 0.6, y - ry, x + dx * r + rx * 0.6, y + ry], fill=PUMP2 if k < 2 else PUMP, outline=OUT, width=4)
        d.rectangle([x - r * 0.08, y - ry - r * 0.25, x + r * 0.08, y - ry + 4], fill=STEM, outline=OUT, width=3)
        for sx in (-1, 1):
            d.polygon([(x + sx * r * 0.45, y - r * 0.1), (x + sx * r * 0.15, y - r * 0.1), (x + sx * r * 0.3, y - r * 0.38)], fill=CANDY, outline=OUT)
        gw = r * 0.6 * grin
        pts = [(x - gw, y + r * 0.12)] + [(x + gw * (i / 4 - 1) * -1 if False else x - gw + gw * i / 4, y + r * 0.12 + (r * 0.12 if i % 2 else 0) + r * 0.25 * math.sin(math.pi * i / 8)) for i in range(9)]
        bot = [(x + gw - gw * i / 4, y + r * 0.2 + r * 0.32 * math.sin(math.pi * (8 - i) / 8)) for i in range(9)]
        d.polygon(pts + bot, fill=CANDY, outline=OUT)

    def ghost(self, d, x, y, s, t, alpha=255):
        y += 6 * math.sin(t * 2.2)
        pts = [(x - s * 0.5, y + s * 0.6)]
        for i in range(7): pts.append((x - s * 0.5 + s * i / 6, y + s * 0.6 + (8 if i % 2 else -2) + 4 * math.sin(t * 5 + i)))
        pts += [(x + s * 0.5, y + s * 0.6), (x + s * 0.5, y)]
        d.polygon(pts, fill=(236, 236, 250, alpha), outline=OUT)
        d.pieslice([x - s * 0.5, y - s * 0.5, x + s * 0.5, y + s * 0.5], 180, 360, fill=(236, 236, 250, alpha), outline=OUT, width=3)
        d.rectangle([x - s * 0.5 + 2, y - 2, x + s * 0.5 - 2, y + s * 0.6], fill=(236, 236, 250, alpha))
        for ex in (-0.16, 0.16): d.ellipse([x + s * ex - s * 0.06, y - s * 0.12, x + s * ex + s * 0.06, y + s * 0.04], fill=OUT)
        d.ellipse([x - s * 0.08, y + s * 0.1, x + s * 0.08, y + s * 0.28], fill=OUT)

    def door(self, d, x, y, w, h, open_=0.0, shake=0.0):
        x += shake
        d.rectangle([x - w / 2 - 10, y - h - 10, x + w / 2 + 10, y], fill=BROWN, outline=OUT, width=4)
        d.rectangle([x - w / 2, y - h, x + w / 2, y], fill=DARK)
        ww = w * (1 - 0.7 * open_)
        d.rectangle([x - w / 2, y - h, x - w / 2 + ww, y], fill=(160, 70, 140), outline=OUT, width=4)
        d.ellipse([x - w / 2 + ww - 22, y - h * 0.5 - 6, x - w / 2 + ww - 10, y - h * 0.5 + 6], fill=CANDY, outline=OUT)
        d.polygon([(x - w / 2 - 24, y - h - 10), (x, y - h - 50), (x + w / 2 + 24, y - h - 10)], fill=(90, 50, 120), outline=OUT)

    def big_text(self, d, x, y, s, txt, col, u=1.0):
        f = self.fb(max(10, int(s * back(u))))
        d.text((x, y), txt, font=f, anchor="mm", fill=col, stroke_width=5, stroke_fill=OUT)

    # ---------------- per-line scenes ----------------
    def scene(self, li, t, st, d):
        L = self.c.lines[li]; txt = L["text"].lower(); u = self.prog(li, t); W, H = self.W, self.H; cx = W / 2; gy = H * 0.62
        if "knock" in txt:
            hits = [e for e in self.c.word_events.get("knock", []) if e <= t]
            sh = 6 * math.sin(t * 40) * math.exp(-(t - hits[-1]) * 6) if hits else 0
            self.door(d, cx, gy, 150, 230, 0, sh)
            if "who's" in txt or "who" in txt: self.big_text(d, cx + 190, gy - 200, 60, "?", CANDY, (t - L["s"]) * 2)
            for i, e in enumerate(hits[-2:]):
                a = max(0, 1 - (t - e) / 1.2)
                if a: self.big_text(d, cx - 190 + i * 40, gy - 170 - i * 50, 46, "KNOCK!", PUMP + (int(255 * a),), 1)
        elif "doorbell" in txt:
            self.door(d, cx - 120, gy, 140, 220)
            bx, by = cx + 110, gy - 150; rock = 0.35 * math.sin(t * 14) * (1 if u < 0.9 else 0)
            d.pieslice([bx - 40, by - 40, bx + 40, by + 40], 180, 360, fill=CANDY, outline=OUT, width=4)
            d.rectangle([bx - 40, by - 2, bx + 40, by + 8], fill=CANDY, outline=OUT, width=3)
            for k in range(3):
                r = 55 + k * 18 + 10 * ((t * 2) % 1)
                d.arc([bx - r, by - r, bx + r, by + r], 200 + rock * 20, 340 + rock * 20, fill=MOON + (150 - k * 40,), width=3)
            ox, oy, r = cx + 300, gy - 150, 50
            d.ellipse([ox - r, oy - r, ox + r, oy + r], fill=MOON, outline=OUT, width=4)
            a8 = math.radians(240 * ease(u * 1.5)) - math.pi / 2  # hour hand swings to 8
            d.line([(ox, oy), (ox + 28 * math.cos(math.radians(150) * ease(u) - math.pi / 2 + 0), oy + 28 * math.sin(math.radians(240) * ease(u) - math.pi / 2))], fill=OUT, width=5)
            d.line([(ox, oy), (ox, oy - 40)], fill=OUT, width=3)
        elif "pumpkin" in txt:
            self.pumpkin(d, cx, gy - 110 + self.bounce(st, 18), 120 * back(min(1, u * 3)), st, grin=0.6 + 0.4 * ease(u))
            self.c_porch(d, gy)
        elif "grandma" in txt:
            x = cx - 120 + self.bounce(st, 0)
            cape = 30 * math.sin(t * 3)
            d.polygon([(x - 30, gy - 160), (x + 30, gy - 160), (x + 80 + cape, gy), (x - 80 - cape * 0.5, gy)], fill=PURP, outline=OUT)
            d.rectangle([x - 26, gy - 150, x + 26, gy - 20], fill=(120, 170, 200), outline=OUT, width=3)
            d.ellipse([x - 32, gy - 222, x + 32, gy - 158], fill=(250, 214, 190), outline=OUT, width=3)
            d.ellipse([x - 34, gy - 236, x + 34, gy - 196], fill=GREY, outline=OUT, width=3)
            for ex in (-12, 12): d.ellipse([x + ex - 9, gy - 196, x + ex + 9, gy - 182], outline=OUT, width=2)
            d.arc([x - 12, gy - 184, x + 12, gy - 168], 20, 160, fill=OUT, width=3)
            k = cx + 150; ky = gy + self.bounce(st, 16)
            d.ellipse([k - 50, ky - 80, k + 50, ky], fill=DARK, outline=PURP, width=3)
            d.ellipse([k - 34, ky - 130, k + 34, ky - 66], fill=DARK, outline=PURP, width=3)
            for sx in (-1, 1): d.polygon([(k + sx * 30, ky - 110), (k + sx * 12, ky - 124), (k + sx * 30, ky - 140)], fill=DARK, outline=PURP)
            for ex in (-12, 12): d.ellipse([k + ex - 6, ky - 108, k + ex + 6, ky - 96], fill=SLIME)
            hy = ky - 128 - 10 * back(min(1, u * 2.5))
            d.polygon([(k - 50, hy), (k + 50, hy), (k + 6, hy - 80), (k + 30, hy - 60)], fill=(40, 20, 60), outline=OUT)
            d.rectangle([k - 30, hy - 14, k + 26, hy - 4], fill=SLIME)
            tail = [(k + 50 + i * 8, ky - 20 - 30 * math.sin(i / 3 + t * 3) * i / 6) for i in range(7)]
            d.line(tail, fill=DARK, width=8, joint="curve")
        elif "closet" in txt:
            x0, x1, top = cx - 140, cx + 140, gy - 260
            d.rectangle([x0 - 10, top - 10, x1 + 10, gy], fill=BROWN, outline=OUT, width=4)
            d.rectangle([x0, top, x1, gy], fill=DARK)
            for i in range(3):
                bt = (t * 0.7 + i * 0.33) % 2
                if bt < 1.1:
                    ex, ey = cx - 40 + i * 40, top + 70 + i * 50; o = min(1, bt * 3, (1.1 - bt) * 3)
                    for sx in (-10, 10): d.ellipse([ex + sx - 7, ey - 7 * o, ex + sx + 7, ey + 7 * o], fill=CANDY)
            ajar = 0.15 + 0.1 * math.sin(t * 4)
            d.rectangle([x0, top, cx - 140 * ajar * 2 + 0, gy], fill=(160, 70, 140), outline=OUT, width=4)
            d.rectangle([cx + 140 * ajar * 2, top, x1, gy], fill=(160, 70, 140), outline=OUT, width=4)
            self.big_text(d, cx + 230, top + 30, 70, "?", SLIME, u * 3)
        elif "lights go down" in txt:
            lx = cx; dim = 1 - ease(u)
            d.line([(lx, 0), (lx, 120)], fill=OUT, width=4)
            d.ellipse([lx - 40 - 120 * dim, 140 - 60 - 60 * dim, lx + 40 + 120 * dim, 140 + 60 + 60 * dim], fill=CANDY + (int(50 * dim),))
            d.polygon([(lx - 50, 150), (lx + 50, 150), (lx + 26, 110), (lx - 26, 110)], fill=PURP, outline=OUT)
            d.ellipse([lx - 16, 140, lx + 16, 172], fill=tuple(int(c * (0.35 + 0.65 * dim)) for c in CANDY), outline=OUT, width=3)
        elif "fun begins" in txt:
            op = ease(u)
            for side in (-1, 1):
                x = cx + side * (40 + 360 * op)
                d.rectangle([min(x, x - side * 480), 30, max(x, x - side * 480), gy + 30], fill=(130, 40, 110), outline=OUT, width=4)
                for k in range(5): d.line([(x - side * (40 + k * 90), 30), (x - side * (40 + k * 90), gy + 30)], fill=(100, 30, 90), width=4)
            for i in range(14):
                rr = random.Random(i); px = cx + rr.uniform(-300, 300) * op; py = 60 + ((t * 80 + rr.uniform(0, 300)) % 320)
                d.polygon([(px, py), (px + 14, py), (px + 7, py + 22)], fill=[CANDY, PUMP, MOON][i % 3], outline=OUT)
        elif "spin around" in txt:
            ang = t * 5; w = abs(math.cos(ang))
            d.ellipse([cx - 110 * w - 4, gy - 260, cx + 110 * w + 4, gy - 40], fill=PURP if math.cos(ang) > 0 else (90, 50, 140), outline=OUT, width=4)
            if math.cos(ang) > 0:
                for ex in (-40, 40): d.ellipse([cx + ex * w - 14 * w, gy - 180, cx + ex * w + 14 * w, gy - 150], fill=SLIME)
                d.arc([cx - 50 * w, gy - 150, cx + 50 * w, gy - 90], 20, 160, fill=OUT, width=5)
            for k in range(3): d.arc([cx - 170 - k * 20, gy - 200 - k * 10, cx + 170 + k * 20, gy - 20 + k * 10], 200 + k * 30 + t * 120 % 360, 260 + k * 30 + t * 120 % 360, fill=MOON + (160,), width=4)
        elif "costume reveal" in txt:
            words = L["words"]; tw = {w[0].lower().strip(".,!?"): w[1] for w in words}
            seq = [("3", tw.get("three", L["s"] + 1)), ("2", tw.get("two...", tw.get("two", L["s"] + 2))), ("WAIT!", tw.get("wait!", tw.get("wait", L["e"] - 0.5)))]
            cur = None
            for s, ts in seq:
                if t >= ts: cur = (s, ts)
            if cur:
                col = SLIME if cur[0] != "WAIT!" else PUMP
                self.big_text(d, cx, gy - 140, 170 if cur[0] != "WAIT!" else 130, cur[0], col, (t - cur[1]) * 3.5)
            else:
                d.rectangle([cx - 120, gy - 260, cx + 120, gy - 30], fill=(130, 40, 110), outline=OUT, width=4)
                self.big_text(d, cx, gy - 145, 60, "?", CANDY, 1)
        elif "vampire" in txt:
            x = cx - 60; y = gy + self.bounce(st, 10)
            d.polygon([(x - 80, y), (x + 80, y), (x + 40, y - 170), (x - 40, y - 170)], fill=DARK, outline=PURP, width=3)
            d.polygon([(x - 70, y - 170), (x - 20, y - 150), (x - 60, y - 215)], fill=(140, 30, 90), outline=OUT)
            d.polygon([(x + 70, y - 170), (x + 20, y - 150), (x + 60, y - 215)], fill=(140, 30, 90), outline=OUT)
            d.ellipse([x - 36, y - 250, x + 36, y - 170], fill=(200, 220, 210), outline=OUT, width=3)
            d.polygon([(x - 36, y - 222), (x, y - 252), (x + 36, y - 222), (x, y - 236)], fill=DARK)
            for ex in (-14, 14): d.ellipse([x + ex - 6, y - 218, x + ex + 6, y - 206], fill=PURP)
            d.arc([x - 14, y - 200, x + 14, y - 182], 20, 160, fill=OUT, width=3)
            for fx in (-6, 6): d.polygon([(x + fx - 3, y - 186), (x + fx + 3, y - 186), (x + fx, y - 178)], fill=BONE)
            bx, by = x + 110, y - 170; lvl = 1 - 0.8 * ease(u)
            d.rounded_rectangle([bx - 24, by - 10, bx + 24, by + 100], radius=10, fill=(60, 30, 70), outline=OUT, width=3)
            d.rectangle([bx - 21, by + 100 - 87 * lvl, bx + 21, by + 97], fill=CHERRY)
            d.rectangle([bx - 24, by + 30, bx + 24, by + 55], fill=MOON, outline=OUT, width=2)
            d.text((bx, by + 42), "POP", font=self.fb(18), anchor="mm", fill=OUT)
            d.line([(bx, by - 10), (bx - 10, by - 50), (x + 14, y - 190)], fill=SLIME, width=4)
            for i in range(4):
                by2 = by + 80 - ((t * 60 + i * 25) % 90); d.ellipse([bx - 10 + i * 6, by2, bx - 4 + i * 6, by2 + 6], outline=MOON)
        elif "werewolf" in txt:
            d.rectangle([cx + 140, gy - 250, cx + 260, gy], fill=(200, 210, 220), outline=OUT, width=4)
            d.line([(cx + 140, gy - 160), (cx + 260, gy - 160)], fill=OUT, width=3)
            d.rectangle([cx - 320, gy - 70, cx + 120, gy], fill=BROWN, outline=OUT, width=4)
            x = cx - 100; y = gy - 70 + self.bounce(st, 16)
            d.ellipse([x - 60, y - 150, x + 60, y], fill=FUR, outline=OUT, width=4)
            d.ellipse([x - 50, y - 230, x + 50, y - 130], fill=FUR, outline=OUT, width=4)
            for sx in (-1, 1): d.polygon([(x + sx * 46, y - 200), (x + sx * 20, y - 222), (x + sx * 44, y - 262)], fill=FUR, outline=OUT)
            d.ellipse([x - 26, y - 176, x + 26, y - 140], fill=(170, 150, 130), outline=OUT, width=3)
            d.ellipse([x - 8, y - 180, x + 8, y - 168], fill=OUT)
            for ex in (-20, 20): d.ellipse([x + ex - 7, y - 206, x + ex + 7, y - 192], fill=CANDY)
            ang = math.sin(t * 2 * math.pi * self.c.bpm / 60 / 2) * 0.6
            px, py = x + 110, y - 100
            d.line([(x + 50, y - 90), (px, py)], fill=FUR, width=14)
            ex2, ey2 = px + 80 * math.cos(ang), py - 20 + 30 * math.sin(ang)
            d.line([(px, py), (ex2, ey2)], fill=OUT, width=8)
            d.ellipse([ex2 - 30, ey2 - 12, ex2 + 50, ey2 + 12], fill=(70, 70, 80), outline=OUT, width=3)
            fl = max(0, math.sin(t * 6)); d.ellipse([ex2, ey2 - 40 * fl - 14, ex2 + 24, ey2 - 40 * fl + 10], fill=CANDY, outline=OUT, width=2)
        elif "mummy" in txt:
            x = cx - 160 + 40 * math.sin(t * 1.5); y = gy + self.bounce(st, 10)
            d.rounded_rectangle([x - 45, y - 230, x + 45, y], radius=36, fill=(230, 222, 196), outline=OUT, width=4)
            for k in range(8): d.line([(x - 45, y - 210 + k * 26), (x + 45, y - 196 + k * 26)], fill=(190, 180, 150), width=3)
            for ex in (-16, 16): d.ellipse([x + ex - 8, y - 196, x + ex + 8, y - 180], fill=SLIME)
            d.line([(x - 40, y - 140), (x - 110, y - 150)], fill=(230, 222, 196), width=22)
            n = int(4 + 18 * ease(u)); trail = [(x + 40 + i * 22, y - 120 + i * 8 + 10 * math.sin(i * 0.8 + t * 3)) for i in range(n)]
            if len(trail) > 1: d.line(trail, fill=(250, 248, 240), width=14, joint="curve"); d.line(trail, fill=OUT, width=1)
            rx, ry = trail[-1]; d.ellipse([rx - 22, ry - 22, rx + 22, ry + 22], fill=(250, 248, 240), outline=OUT, width=3); d.ellipse([rx - 6, ry - 6, rx + 6, ry + 6], fill=GREY)
        elif "witches" in txt:
            for i in range(2):
                ph = t * 0.35 + i * 0.5; x = (ph % 1.3) / 1.3 * (W + 300) - 150; y = 170 + i * 120 + 25 * math.sin(t * 2 + i)
                d.line([(x - 90, y + 20), (x + 70, y)], fill=BROWN, width=8)
                d.polygon([(x - 90, y + 20), (x - 130, y), (x - 130, y + 44)], fill=CANDY, outline=OUT)
                d.polygon([(x - 30, y + 14), (x + 20, y + 10), (x, y - 50)], fill=(60, 30, 90), outline=OUT)
                d.ellipse([x - 16, y - 76, x + 16, y - 44], fill=SLIME, outline=OUT, width=3)
                d.polygon([(x - 30, y - 64), (x + 30, y - 64), (x - 4, y - 124)], fill=DARK, outline=PURP)
                d.rounded_rectangle([x + 22, y - 74, x + 42, y - 40], radius=4, fill=(30, 30, 40), outline=MOON, width=2)
                d.text((x + 50, y - 96), "♪", font=self.fb(28), fill=SLIME)
            d.ellipse([cx - 90, gy - 40, cx + 90, gy + 20], fill=(70, 40, 90), outline=OUT, width=4)
            d.ellipse([cx - 80, gy - 40, cx + 80, gy - 10], fill=SLIME)
        elif "left hand" in txt:
            self.skeleton(d, cx, gy, 230, t, st, wave=True)
            wl = L["words"]
            for w in wl:
                if w[1] <= t <= w[2] + 0.4:
                    self.big_text(d, cx + 250, gy - 230, 44, w[0].upper().strip(","), SLIME, (t - w[1]) * 4)
        elif "graveyard" in txt:
            for i, x in enumerate((cx - 260, cx - 90, cx + 90, cx + 260)):
                d.rounded_rectangle([x - 40, gy - 120, x + 40, gy], radius=36, fill=(110, 100, 130), outline=OUT, width=4)
                d.text((x, gy - 70), "RIP", font=self.fb(24), anchor="mm", fill=OUT)
                if ease(u * 1.6 - i * 0.15) > 0.2: self.skeleton(d, x, gy - 125 - 40 * ease(u * 1.6 - i * 0.15), 90, t, st, phase=i)
        elif "midnight" in txt:
            ox, oy, r = cx - 220, gy - 170, 70
            d.ellipse([ox - r, oy - r, ox + r, oy + r], fill=MOON, outline=OUT, width=4)
            d.line([(ox, oy), (ox, oy - 50)], fill=OUT, width=6); d.line([(ox, oy), (ox + 2, oy - 60)], fill=OUT, width=3)
            d.text((ox, oy - r + 16), "12", font=self.fb(20), anchor="mm", fill=OUT)
            for k in range(5): d.rectangle([cx - 20 + k * 60, gy - k * 40, cx + 300, gy - k * 40 + 40], fill=(90, 60, 110), outline=OUT, width=3)
            self.ghost(d, cx + 60 + 180 * ease(u), gy - 80 - 140 * ease(u), 90, t)
            for i, x in enumerate((cx - 340, cx - 120)):
                d.rectangle([x - 10, gy - 70, x + 10, gy], fill=MOON, outline=OUT, width=2)
                fl = 1 + 0.1 * math.sin(t * 9 + i)
                d.ellipse([x - 8 * fl, gy - 98 * fl + 0, x + 8 * fl, gy - 70], fill=CANDY, outline=OUT, width=2)
        elif "dancing" in txt or "next year" in txt or "always here" in txt:
            for i, x in enumerate((cx - 300, cx - 150, cx + 150, cx + 300)):
                self.skeleton(d, x, gy, 120, t, st, phase=i * 1.5, wave="here" in txt or "year" in txt)
            self.pumpkin(d, cx, gy - 60, 64, st, grin=1)
            if "next year" in txt: self.big_text(d, cx, 90, 52, "SEE YOU 2027!", CANDY, u * 3)
        elif "boo" in txt:
            self.ghost(d, cx - 220, gy - 180, 110, t); self.ghost(d, cx + 240, gy - 210, 90, t + 1)
            b = [e for e in self.c.word_events.get("boo", []) + self.c.word_events.get("boo!", []) if L["s"] <= e <= t]
            self.big_text(d, cx, gy - 170, 140, "BOO!", SLIME, (t - b[-1]) * 3 if b else 0.0001)
            for i in range(6):
                rr = random.Random(i + 9); px = cx + rr.uniform(-380, 380); py = gy - 20 - abs(math.sin(t * 4 + i)) * 60
                d.rounded_rectangle([px - 14, py - 8, px + 14, py + 8], radius=6, fill=[PUMP, CANDY, SLIME, PURP][i % 4], outline=OUT, width=2)
        elif "no body" in txt:
            x, y = cx, gy - 160 + 12 * math.sin(t * 3) + self.bounce(st, 14)
            d.ellipse([x - 90, y - 100, x + 90, y + 60], fill=BONE, outline=OUT, width=5)
            d.rounded_rectangle([x - 50, y + 30, x + 50, y + 90], radius=14, fill=BONE, outline=OUT, width=5)
            for ex in (-38, 38): d.ellipse([x + ex - 26, y - 40, x + ex + 26, y + 10], fill=OUT)
            for ex in (-38, 38): d.ellipse([x + ex - 6, y - 24, x + ex + 6, y - 12], fill=SLIME)
            d.polygon([(x, y + 14), (x - 12, y + 34), (x + 12, y + 34)], fill=OUT)
            for k in range(5): d.line([(x - 40 + k * 20, y + 60), (x - 40 + k * 20, y + 88)], fill=OUT, width=3)
            self.big_text(d, x + 220, y - 60, 40, "NO PROBLEM!", CANDY, u * 3)
        elif "moonlight" in txt:
            for i in range(5):
                x = cx - 320 + i * 160 + 30 * math.sin(t * 2 * math.pi * self.c.bpm / 120 + i)
                self.skeleton(d, x, gy, 130, t, st, phase=i)
        elif "trick" in txt:
            pass
        else:  # 'we're the skeleton crew' / rattle lines / intro 'skeleton crew!'
            n = 3 if "rattle" not in txt else 5
            for i in range(n):
                x = cx + (i - (n - 1) / 2) * (180 if n == 3 else 150)
                self.skeleton(d, x, gy, 150 if n == 3 else 120, t, st, phase=i * 2.1, wave=(i % 2 == 0 and "ooh" in txt))
            if "rattle" in txt:
                for i in range(8):
                    rr = random.Random(i); a = (t * 2 + rr.uniform(0, 6)) % 6.28; bx = cx + 360 * math.cos(a + i); by = 120 + 40 * math.sin(a * 2)
                    d.line([(bx - 14, by), (bx + 14, by)], fill=BONE, width=6)
                    for ex in (-14, 14): d.ellipse([bx + ex - 6, by - 7, bx + ex + 6, by + 7], fill=BONE, outline=OUT)

    def c_porch(self, d, gy):
        d.rectangle([self.W / 2 - 260, gy, self.W / 2 + 260, gy + 24], fill=BROWN, outline=OUT, width=4)

    def layer(self, li, t, st):
        im = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        if li >= 0:
            txt = self.c.lines[li]["text"].lower()
            d = ImageDraw.Draw(im)
            if "trick" in txt:  # trick-or-treat bucket scene
                cx, gy = self.W / 2, self.H * 0.62; b = self.bounce(st, 20)
                d.ellipse([cx - 110, gy - 190 + b, cx + 110, gy - 10 + b], fill=PUMP, outline=OUT, width=5)
                d.arc([cx - 90, gy - 260 + b, cx + 90, gy - 110 + b], 180, 360, fill=OUT, width=6)
                for ex in (-40, 40): d.polygon([(cx + ex - 18, gy - 120 + b), (cx + ex + 18, gy - 120 + b), (cx + ex, gy - 150 + b)], fill=DARK)
                d.chord([cx - 50, gy - 110 + b, cx + 50, gy - 50 + b], 0, 180, fill=DARK)
                for i in range(9):
                    rr = random.Random(i); ph = (t * 1.2 + rr.uniform(0, 1)) % 1
                    px = cx + rr.uniform(-1, 1) * 260 * ph; py = gy - 190 - 220 * ph * (1 - ph) * 2.2 + b
                    d.rounded_rectangle([px - 16, py - 9, px + 16, py + 9], radius=6, fill=[CANDY, SLIME, PURP, MOON][i % 4], outline=OUT, width=2)
                for i in range(4):
                    x = 120 + i * 240 if i < 2 else self.W - 120 - (i - 2) * 0
                for side in (-1, 1):
                    x = cx + side * 300; y = self.H * 0.62
                    for k, sgn in enumerate((-1, 1)):
                        lift = max(0, math.sin(t * math.pi * self.c.bpm / 60 + k * math.pi + side)) * 22
                        d.rounded_rectangle([x + sgn * 30 - 28, y - 30 - lift, x + sgn * 30 + 28, y - lift], radius=12, fill=PURP, outline=OUT, width=4)
            else:
                self.scene(li, t, st, d)
        return im

    # ---------------- preset hooks ----------------
    def camera(self, t, st):
        sway = math.sin(t * 2 * math.pi * self.c.bpm / 60 / 4)  # one sway per bar
        hk = 1.4 if st["hook"] else 1.0
        return (8 * sway * hk, 3 * math.sin(t * 0.7), 1.03 + 0.012 * math.sin(t * 0.21), 0.9 * sway * hk)

    def background(self, t, st):
        W, H = self.W, self.H
        im = self.sky.copy()
        # slow tint drift (period 40 s) instead of beat colour changes
        tint = Image.new("RGBA", (W, H), (60, 200, 120, int(18 + 14 * math.sin(t * 2 * math.pi / 40))))
        im.alpha_composite(tint)
        d = ImageDraw.Draw(im)
        for ph, sp, yy in self.bats:
            x = (t * sp * W + ph * 200) % (W + 100) - 50; y = H * yy + 14 * math.sin(t * 3 + ph)
            fl = 10 * math.sin(t * 14 + ph)
            d.polygon([(x, y), (x - 22, y - fl), (x - 12, y + 4), (x, y + 6), (x + 12, y + 4), (x + 22, y - fl)], fill=DARK)
        li = self.line_at(t)
        cur = self.layer(li, t, st)
        if li >= 0:
            age = t - (self.c.lines[li]["s"] - 0.15); cf = 0.8
            if age < cf and li > 0:
                prev = self.layer(li - 1, t, st)
                a = ease(age / cf)
                cur = Image.blend(prev, cur, a)
        im.alpha_composite(cur)
        # fog: thicker in pre-chorus, always drifting
        fog_a = 1.0 if st["sec"] == "pre-chorus" else 0.55
        off = int((t * 18) % W)
        fl = self.fog.crop((off, 0, off + W, 160))
        if fog_a < 1: fl.putalpha(fl.getchannel("A").point(lambda v: int(v * fog_a)))
        im.alpha_composite(fl, (0, int(H * 0.56)))
        # the song starts on the vocal, so the title rides the intro's instrumental gap
        if 4.6 < t < 11.3:
            a = min(1, (t - 4.6) / 0.8, (11.3 - t) / 0.8); dt = ImageDraw.Draw(im)
            f = self.fc(int(96 * (0.9 + 0.1 * back(min(1, (t - 4.6) / 0.8)))))
            dt.text((W / 2, 86 + 4 * math.sin(t * 2)), "SKELETON CREW", font=f, anchor="mm", fill=SLIME + (int(255 * a),), stroke_width=5, stroke_fill=OUT + (int(255 * a),))
        return im
