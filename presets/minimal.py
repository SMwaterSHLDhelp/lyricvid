"""Smallest preset: dark gradient + beat-pulsed rings. Copy this to start a new style."""
import math
from PIL import Image, ImageDraw

class Preset:
    STYLE = dict(bg_size=(960, 540), fonts=dict(lyric="ArchivoBlack-Regular", title="ArchivoBlack-Regular", mono="IBMPlexMono-Regular"),
                 text=(240, 236, 228), sung=(255, 200, 60), size=86, hook_size=120, upper=False, band=0.55,
                 unsung_alpha=0.4, hook_sections=("chorus",), punch=0.02, shake=1.5, text_y=0.8)
    def __init__(self, ctx):
        self.c = ctx
        g = Image.linear_gradient("L").resize((ctx.SW if hasattr(ctx, "SW") else 960, 540))
        self.base = Image.merge("RGB", (g.point(lambda v: 10 + v // 10), g.point(lambda v: 10 + v // 14), g.point(lambda v: 22 + v // 6))).convert("RGBA")
    def background(self, t, st):
        im = self.base.copy(); d = ImageDraw.Draw(im); W, H = im.size
        r = 40 + 300 * st["bar_phase"]
        d.ellipse([W / 2 - r, H / 2 - r, W / 2 + r, H / 2 + r], outline=(90, 90, 140), width=2)
        return im
