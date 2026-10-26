"""Smallest preset, built from blocks. Copy this file to start a new style."""
from lv_blocks import AudioFollow, camera_drift, fill, vignette

class Preset:
    DESCRIPTION = "Dark field, a slow ring, centred-lower karaoke. The template."
    STYLE = dict(
        bg_size=(960, 540),
        fonts=dict(lyric=["DejaVuSans-Bold"], title=["DejaVuSans-Bold"], mono=["DejaVuSansMono"]),
        text=(236, 232, 224), sung=(255, 196, 72),
        size=72, hook_size=84, upper=False, layout="lower", kinetic="pop",
        band=0.5, band_color=(6, 8, 14), unsung_alpha=0.4,
        punch=0.015, shake=1.0, text_y=0.78, pop=0.12, hook_slam=0.16, glow=0,
    )

    def __init__(self, ctx):
        self.c = ctx
        self.audio = AudioFollow(0.6, ctx.FPS)

    def camera(self, t, st):
        return camera_drift(t, drift=8, rot=0.2, zoom=1.0)

    def background(self, t, st):
        a = self.audio(st)
        w, h = self.c.SW, self.c.SH
        im = fill(w, h, (8, 10, 18))
        # ring radius follows the bar, not a per-frame strobe
        r = 30 + (min(w, h) * 0.28) * (0.35 + 0.65 * st["bar_phase"])
        from PIL import ImageDraw
        ImageDraw.Draw(im).ellipse([w / 2 - r, h / 2 - r * 0.7, w / 2 + r, h / 2 + r * 0.7],
                                   outline=(90, 110, 160, 180), width=2)
        # a dim core that breathes with slewed bass
        core = 18 + 10 * a["bass"]
        ImageDraw.Draw(im).ellipse([w / 2 - core, h * 0.42 - core, w / 2 + core, h * 0.42 + core],
                                   fill=(40, 50, 80, int(40 + 30 * a["bass"])))
        return vignette(im, 0.5)
