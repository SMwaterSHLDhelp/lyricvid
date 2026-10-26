"""A slow starfield. Audio only changes star size through a 0.6s slew."""
from lv_blocks import AudioFollow, Field, camera_drift, fill, soft_blob, vignette

class Preset:
    DESCRIPTION = "Starfield: navy space, audio-slewed dust, two-line karaoke."
    STYLE = dict(
        bg_size=(960, 540),
        fonts=dict(lyric=["Outfit[wght]@Bold", "DejaVuSans-Bold"],
                   title=["Outfit[wght]@Bold", "DejaVuSans-Bold"],
                   mono=["IBMPlexMono-Regular", "DejaVuSansMono"]),
        text=(230, 234, 240), sung=(255, 214, 120),
        size=60, hook_size=70, upper=False, layout="karaoke", kinetic="pop",
        glow=2, shadow=True, band=0.4, band_color=(2, 4, 12),
        unsung_alpha=0.42, punch=0.012, shake=0.5, text_y=0.74,
        pop=0.1, hook_slam=0.12, fade_in=0.8,
    )

    def __init__(self, ctx):
        self.c = ctx
        self.audio = AudioFollow(0.6, ctx.FPS)
        self.stars = Field(ctx.SW if hasattr(ctx, "SW") else 960, ctx.SH if hasattr(ctx, "SH") else 540, 110, seed=5, kind="stars")
        self.dust = Field(self.stars.w, self.stars.h, 30, seed=6, kind="dust")

    def camera(self, t, st):
        return camera_drift(t, drift=8, rot=0.15, zoom=1.03)

    def background(self, t, st):
        a = self.audio(st)
        w, h = self.c.SW, self.c.SH
        self.stars.w = self.dust.w = w
        self.stars.h = self.dust.h = h
        im = fill(w, h, (3, 6, 16))
        soft_blob(im, w * 0.5, h * 0.4, 80 + 30 * a["bass"], (24, 36, 80), alpha=55)
        self.stars.draw(im, t, color=(235, 236, 245), react=a["high"] * 0.6)
        self.dust.draw(im, t, color=(140, 160, 200), react=a["mid"] * 0.3, alpha=0.7)
        return vignette(im, 0.55)
