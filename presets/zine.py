"""Cut paper, halftone, mixed faces, words scattered and tilted. The collage does not move."""
import random
from lv_blocks import boxes, camera_still, halftone, paper

class Preset:
    DESCRIPTION = "Punk zine: newsprint, halftone, cut-out blocks, ransom-note words."
    STYLE = dict(
        bg_size=(960, 540),
        fonts=dict(lyric=["Syne[wght]@ExtraBold", "DejaVuSans-Bold"],
                   lyric_b=["Anton-Regular", "DejaVuSans-Bold"],
                   lyric_c=["BebasNeue-Regular", "DejaVuSans-Bold"],
                   title=["Syne[wght]@ExtraBold", "DejaVuSans-Bold"],
                   mono=["IBMPlexMono-Medium", "DejaVuSansMono"]),
        text=(16, 16, 16), sung=(20, 48, 140),
        size=64, hook_size=72, upper=True, layout="scatter", kinetic="none",
        ransom=True, jitter_rot=7, shadow=False, glow=0,
        band=0.72, band_color=(236, 230, 210), band_radius=2,
        unsung_alpha=0.85, punch=0.0, shake=0.3, pop=0.0, hook_slam=0.0,
        fade_in=0.8, line_fade=0.4,
    )

    def __init__(self, ctx):
        self.c = ctx
        rng = random.Random(9)
        w, h = 960, 540
        self.rects = []
        inks = [(236, 230, 210), (250, 214, 64), (210, 214, 206), (20, 20, 20)]
        for i in range(7):
            self.rects.append((rng.uniform(40, w - 80), rng.uniform(40, h * 0.62),
                               rng.uniform(80, 220), rng.uniform(36, 90),
                               inks[i % len(inks)], rng.uniform(-8, 8)))
        self.base = None

    def camera(self, t, st):
        return camera_still()

    def background(self, t, st):
        w, h = self.c.SW, self.c.SH
        if self.base is None or self.base.size != (w, h):
            im = paper(w, h, (214, 206, 188), speckle=8, seed=2)
            # scale the seeded rects if the background size is not 960x540
            sx, sy = w / 960, h / 540
            rects = [(x * sx, y * sy, rw * sx, rh * sy, c, rot) for x, y, rw, rh, c, rot in self.rects]
            boxes(im, rects)
            self.base = halftone(im, step=6, strength=0.16)
        return self.base.copy()
