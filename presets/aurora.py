"""Slow liquid colour. The field moves on a multi-second cycle."""
from lv_blocks import AudioFollow, aurora, camera_drift, soft_blob, vignette

class Preset:
    DESCRIPTION = "Aurora: dark flowing colour, centred type with a soft glow."
    STYLE = dict(
        bg_size=(960, 540),
        fonts=dict(lyric=["LibreBaskerville[wght]@Bold", "DejaVuSerif-Bold"],
                   title=["LibreBaskerville[wght]@Bold", "DejaVuSerif-Bold"],
                   mono=["IBMPlexMono-Regular", "DejaVuSansMono"]),
        text=(236, 234, 228), sung=(186, 230, 220),
        size=64, hook_size=76, upper=False, layout="center", kinetic="wave",
        text_y=0.48, glow=3, shadow=True, shadow_px=2,
        band=0.4, band_color=(6, 10, 18), unsung_alpha=0.4,
        punch=0.008, shake=0.4, wave=6, pop=0.05, hook_slam=0.08, fade_in=0.8,
    )

    def __init__(self, ctx):
        self.c = ctx
        self.audio = AudioFollow(0.8, ctx.FPS)

    def camera(self, t, st):
        return camera_drift(t, drift=12, rot=0.25, zoom=1.01)

    def background(self, t, st):
        a = self.audio(st)
        w, h = self.c.SW, self.c.SH
        # kept dark so the lyric band stays above 3:1
        im = aurora(w, h, t, [(8, 16, 36), (14, 36, 48), (28, 16, 42)], speed=0.05)
        soft_blob(im, w * (0.4 + 0.08 * a["mid"]), h * 0.38, 70 + 16 * a["bass"], (40, 80, 90), alpha=50)
        return vignette(im, 0.5)
