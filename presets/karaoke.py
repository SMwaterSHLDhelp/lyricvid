"""Clean two-line karaoke. High contrast, almost no camera."""
from lv_blocks import AudioFollow, camera_still, fill, meters

class Preset:
    DESCRIPTION = "Clean karaoke: two lines, white on navy, a small slewed meter."
    STYLE = dict(
        bg_size=(960, 540),
        fonts=dict(lyric=["Outfit[wght]@Bold", "DejaVuSans-Bold"],
                   title=["Outfit[wght]@Bold", "DejaVuSans-Bold"],
                   mono=["IBMPlexMono-Medium", "DejaVuSansMono"]),
        text=(245, 246, 248), sung=(255, 214, 64),
        size=64, hook_size=72, upper=False, layout="karaoke", kinetic="type",
        shadow=False, glow=0, band=0, unsung_alpha=0.4,
        punch=0.0, shake=0.2, text_y=0.62, kinetic_time=0.12,
        pop=0.0, hook_slam=0.0, fade_in=0.6,
    )

    def __init__(self, ctx):
        self.c = ctx
        self.audio = AudioFollow(0.6, ctx.FPS)

    def camera(self, t, st):
        return camera_still()

    def background(self, t, st):
        a = self.audio(st)
        w, h = self.c.SW, self.c.SH
        im = fill(w, h, (10, 14, 22))
        from PIL import ImageDraw
        d = ImageDraw.Draw(im)
        d.rectangle([0, int(h * 0.5), w, h], fill=(6, 8, 14, 255))
        meters(d, (48, 36, 180, 28), [a["bass"], a["mid"], a["high"]], (255, 214, 64))
        return im
