"""Giant stacked words, paper white, one static red block. Type eases, it does not slam."""
from lv_blocks import camera_still, fill

class Preset:
    DESCRIPTION = "Brutalist type: off-white field, black stacked words, one small red block."
    STYLE = dict(
        bg_size=(960, 540),
        fonts=dict(lyric=["Anton-Regular", "DejaVuSans-Bold"],
                   title=["Anton-Regular", "DejaVuSans-Bold"],
                   mono=["IBMPlexMono-Medium", "DejaVuSansMono"]),
        text=(12, 12, 12), sung=(12, 12, 12),
        size=92, stack_size=100, upper=True, layout="stack", kinetic="slide",
        shadow=False, glow=0, band=0, unsung_alpha=0.28,
        punch=0.0, shake=0.0, text_y=0.48, slide=18,
        pop=0.0, hook_slam=0.0, line_fade=0.6, fade_in=0.9, kinetic_time=0.45,
    )

    def __init__(self, ctx):
        self.c = ctx

    def camera(self, t, st):
        return camera_still()

    def background(self, t, st):
        w, h = self.c.SW, self.c.SH
        im = fill(w, h, (244, 241, 234))
        from PIL import ImageDraw
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, w, 18], fill=(12, 12, 12, 255))
        # small accent, static, well under the red-area cap
        d.rectangle([w - 64, 36, w - 28, 72], fill=(176, 48, 36, 255))
        return im
