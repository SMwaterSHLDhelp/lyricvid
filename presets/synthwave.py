"""Neon sunset, perspective grid, outlined type. Slow scroll, no beat flash."""
from lv_blocks import AudioFollow, camera_drift, draw_grid, linear_gradient, paint_sun, vignette

class Preset:
    DESCRIPTION = "Synthwave: magenta grid, amber sun, cyan outline type on a night sky."
    STYLE = dict(
        bg_size=(960, 540),
        fonts=dict(lyric=["Orbitron[wght]@Bold", "DejaVuSans-Bold"],
                   title=["Orbitron[wght]@Bold", "DejaVuSans-Bold"],
                   mono=["IBMPlexMono-Medium", "DejaVuSansMono"]),
        text=(170, 250, 255), sung=(255, 70, 170),
        size=58, hook_size=68, upper=True, layout="lower", kinetic="slide",
        stroke=2, stroke_color=(20, 0, 40), shadow=False, glow=2,
        band=0.45, band_color=(8, 0, 20), unsung_alpha=0.45,
        punch=0.012, shake=0.6, text_y=0.84, slide=22, pop=0.08, hook_slam=0.1,
        fade_in=0.8,
    )

    def __init__(self, ctx):
        self.c = ctx
        self.audio = AudioFollow(0.8, ctx.FPS)

    def camera(self, t, st):
        return camera_drift(t, drift=10, rot=0.15, zoom=1.02)

    def background(self, t, st):
        a = self.audio(st)
        w, h = self.c.SW, self.c.SH
        im = linear_gradient(w, h, (18, 0, 40), (40, 8, 48))
        horizon = 0.46
        # sun radius follows slewed bass by a few pixels, not a pulse
        paint_sun(im, w * 0.5, h * horizon - 8, 78 + 10 * a["bass"], (255, 168, 64), stripe=(28, 0, 48), bands=6)
        draw_grid(im, t, (255, 64, 170), horizon=horizon, speed=0.16)
        # the lyric band sits on night, not on the sun
        from PIL import Image
        shade = Image.new("RGBA", im.size, (0, 0, 0, 0))
        shade.paste((6, 0, 16, 150), (0, int(h * 0.68), w, h))
        im.alpha_composite(shade)
        return vignette(im, 0.42)
