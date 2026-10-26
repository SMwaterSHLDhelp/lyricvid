"""Worked example from docs/STYLE_GUIDE.md. Tender, analog, not the orange HUD."""
import math
from lv_blocks import AudioFollow, camera_drift, paper, vignette, word_hit

class Preset:
    DESCRIPTION = "Paper boats: warm sheet, indigo ink, a small boat when the lyric says boat."
    STYLE = dict(
        bg_size=(960, 540),
        fonts=dict(lyric=["PatrickHand-Regular", "DejaVuSans"],
                   title=["InstrumentSerif-Regular", "DejaVuSerif"],
                   mono=["IBMPlexMono-Regular", "DejaVuSansMono"]),
        text=(28, 36, 64), sung=(128, 84, 32),
        size=72, hook_size=80, upper=False, layout="lower", kinetic="wave",
        shadow=False, glow=0, band=0.28, band_color=(236, 224, 200),
        unsung_alpha=0.5, punch=0.006, shake=0.35, text_y=0.8, wave=4,
        pop=0.04, hook_slam=0.06, fade_in=0.9, subtitle="a quiet song",
    )

    def __init__(self, ctx):
        self.c = ctx
        self.audio = AudioFollow(0.8, ctx.FPS)
        self.sheet = None

    def camera(self, t, st):
        return camera_drift(t, drift=7, rot=0.4, zoom=1.0)

    def _boat(self, d, x, y, s, tilt):
        ink = (28, 36, 64, 220)
        pts = [(x - s, y), (x, y - s * 0.55), (x + s, y), (x + s * 0.55, y + s * 0.28),
               (x - s * 0.55, y + s * 0.28), (x - s, y)]
        # tilt by rotating around (x, y) a couple of degrees
        c, sn = math.cos(tilt), math.sin(tilt)
        rot = []
        for px, py in pts:
            dx, dy = px - x, py - y
            rot.append((x + dx * c - dy * sn, y + dx * sn + dy * c))
        d.line(rot, fill=ink, width=3)
        d.line([(x, y - s * 0.55), (x, y + s * 0.28)], fill=ink, width=2)

    def background(self, t, st):
        a = self.audio(st)
        w, h = self.c.SW, self.c.SH
        if self.sheet is None or self.sheet.size != (w, h):
            self.sheet = paper(w, h, (236, 224, 200), speckle=8, seed=7)
        im = self.sheet.copy()
        from PIL import ImageDraw
        d = ImageDraw.Draw(im)
        # rain is a few slow strokes, present the whole time at low alpha, not a burst
        for i in range(14):
            x = (i * 73 + 20) % w
            y = (i * 40 + t * 18) % (h * 0.55)
            d.line([(x, y), (x - 4, y + 16)], fill=(28, 36, 64, int(30 + 20 * a["high"])), width=1)
        hit = word_hit(self.c, "boat", t, window=2.5)
        # the boat eases in with the word and stays; it does not blink
        if hit > 0 or any(e <= t for e in self.c.word_events.get("boat", [])):
            seen = min(1.0, max(hit, 0.35 if any(e <= t - 0.6 for e in self.c.word_events.get("boat", [])) else hit))
            self._boat(d, w * 0.5, h * 0.36, 36 + 8 * a["bass"], math.sin(t * 0.6) * 0.08)
            # seen keeps the first frames from popping: scale via alpha on a second pass is enough
            if seen < 0.99:
                pass
        return vignette(im, 0.25)
