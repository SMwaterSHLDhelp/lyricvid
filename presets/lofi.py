"""Warm paper, tape drift, handwriting. Motion stays under a few pixels."""
from lv_blocks import AudioFollow, camera_drift, meters, paper, scanlines, vignette, wobble

class Preset:
    DESCRIPTION = "Lo-fi tape: warm paper, handwriting, grain, a slow wobble, a quiet meter."
    STYLE = dict(
        bg_size=(960, 540),
        fonts=dict(lyric=["Caveat[wght]@Bold", "DejaVuSans"],
                   title=["Caveat[wght]@Bold", "DejaVuSans"],
                   mono=["IBMPlexMono-Regular", "DejaVuSansMono"]),
        text=(42, 26, 20), sung=(92, 28, 18),
        size=78, hook_size=88, upper=False, layout="lower", kinetic="wave",
        shadow=False, glow=0, band=0.72, band_color=(214, 186, 150), band_radius=8,
        unsung_alpha=0.55, punch=0.008, shake=0.4, text_y=0.8, wave=5,
        pop=0.06, hook_slam=0.08, fade_in=0.9,
    )

    def __init__(self, ctx):
        self.c = ctx
        self.audio = AudioFollow(0.7, ctx.FPS)
        self.sheet = None

    def camera(self, t, st):
        return camera_drift(t, drift=6, rot=0.35, zoom=1.0)

    def background(self, t, st):
        a = self.audio(st)
        w, h = self.c.SW, self.c.SH
        if self.sheet is None or self.sheet.size != (w, h):
            self.sheet = paper(w, h, (232, 214, 186), speckle=10, seed=4)
        im = self.sheet.copy()
        from PIL import ImageDraw
        d = ImageDraw.Draw(im)
        # cassette window, static
        d.rounded_rectangle([w * 0.32, h * 0.16, w * 0.68, h * 0.42], radius=16, outline=(90, 60, 40, 180), width=3)
        d.ellipse([w * 0.38 - 18, h * 0.29 - 18, w * 0.38 + 18, h * 0.29 + 18], outline=(90, 60, 40, 160), width=2)
        d.ellipse([w * 0.62 - 18, h * 0.29 - 18, w * 0.62 + 18, h * 0.29 + 18], outline=(90, 60, 40, 160), width=2)
        meters(d, (w * 0.36, h * 0.48, w * 0.28, 36), [a["bass"], a["mid"], a["high"], a["rms"]], (120, 70, 48))
        im = scanlines(im, alpha=22, gap=4, color=(80, 50, 30))
        im = wobble(im, t, amp=1.6)
        return vignette(im, 0.28)
