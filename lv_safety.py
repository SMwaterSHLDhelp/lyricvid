"""Automatic photosensitivity clamp, applied to every frame a preset produces.

WCAG 2.3.1 counts a flash when a large area of the picture jumps in luminance and then
jumps back. The clamp slows those jumps. It also pulls saturated red off large areas.
It does not restyle a preset; it only refuses changes that would strobe.

The lint/check gate still runs afterwards. If a picture gets past the clamp and fails,
the render stops and prints GUIDANCE.
"""
import numpy as np
from PIL import Image

GUIDANCE = """\
Photosensitivity gate failed (WCAG 2.3.1). The video was not accepted.
- Do not flash, invert, or cut the whole frame on the beat.
- Crossfade any large colour change over at least 0.6s, and at most once per bar.
- Keep saturated red (R / (R+G+B) >= 0.8 and R >= 0.3) on small accents. Large red fields are pulled down automatically; if you needed that red, the look will be wrong, so pick another accent.
- Type that fills the screen has to ease in and out. Do not scale a full-frame word on every beat.
- The safety clamp already blended some frames (see "clamps" in the report). If the gate still failed, the moving area is too big or it reverses within a second: shrink it, or slow it down.
- Readability: lyric fill and the sung-word colour need contrast of at least 3:1 against the pixels behind them. Add a flat band, or darken the background and lighten the type.
"""

# Mean relative-luminance change allowed in one frame. A full black-to-white
# swing then takes about 0.75s at 30 fps, which stays past the 0.6s crossfade floor.
MAX_MEAN_DY = 0.045
# Fraction of the frame allowed to jump by more than DY at once. The WCAG area
# threshold is 25%; stay under it so a single cut is not already a transition.
MAX_AREA = 0.22
DY = 0.10
RED_MAX = 0.12
OPPOSE_WINDOW = 20  # frames; at 30 fps this is 0.67s


def _lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

def rel_luma(rgb):
    """rgb is float 0..1, shape (H, W, 3)."""
    lin = _lin(np.clip(rgb, 0, 1))
    return 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]

def contrast_ratio(c1, c2):
    def L(c):
        s = np.array([x / 255.0 for x in c[:3]], np.float64)
        lin = np.where(s <= 0.04045, s / 12.92, ((s + 0.055) / 1.055) ** 2.4)
        return float(0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2])
    a, b = L(c1), L(c2)
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


class Guard:
    """Stateful per render. One instance per segment; frames must be in order."""

    def __init__(self):
        self.prev = None
        self.clamps = 0
        self.red_limits = 0
        self.last_sign = 0
        self.last_sign_frame = -999
        self.frame_i = 0

    def apply(self, image):
        arr = np.asarray(image.convert("RGB")).astype(np.float32) / 255.0
        out = self.clamp_array(arr)
        return Image.fromarray(np.clip(out * 255.0 + 0.5, 0, 255).astype(np.uint8), "RGB")

    def _limit_red(self, rgb):
        s = rgb.sum(-1) + 1e-6
        red = (rgb[..., 0] / s >= 0.8) & (rgb[..., 0] >= 0.3)
        if float(red.mean()) <= RED_MAX: return rgb
        score = np.where(red, rgb[..., 0] / s, 0.0)
        flat = score.ravel()
        # Keep the least-red of the red pixels, fix the rest.
        k = int(flat.size * (1.0 - RED_MAX))
        if k <= 0: return rgb
        thresh = np.partition(flat, -k)[-k] if k < flat.size else 0.0
        fix = score >= max(float(thresh), 1e-6)
        out = rgb.copy()
        gb = out[..., 1] + out[..., 2]
        # R / (R+G+B) = 0.72  =>  R = 0.72/0.28 * (G+B)
        cap = (0.72 / 0.28) * gb
        out[..., 0] = np.where(fix, np.minimum(out[..., 0], cap), out[..., 0])
        self.red_limits += 1
        return out

    def clamp_array(self, rgb):
        rgb = self._limit_red(np.clip(rgb, 0.0, 1.0))
        if self.prev is None or self.prev.shape != rgb.shape:
            self.prev = rgb.copy()
            self.frame_i += 1
            return self.prev.copy()
        out = rgb.copy()
        blended = False
        sign = 0
        for _ in range(12):
            Y = rel_luma(out); pY = rel_luma(self.prev)
            dY = Y - pY
            dark = np.minimum(Y, pY) < 0.8
            up = float(((dY > DY) & dark).mean())
            dn = float(((dY < -DY) & dark).mean())
            mean_d = abs(float(Y.mean() - pY.mean()))
            sign = 1 if up > 0.08 and up >= dn else (-1 if dn > 0.08 and dn > up else 0)
            oppose = bool(sign and self.last_sign == -sign and (self.frame_i - self.last_sign_frame) <= OPPOSE_WINDOW)
            hot = up > MAX_AREA or dn > MAX_AREA or mean_d > MAX_MEAN_DY or (oppose and max(up, dn) > 0.05)
            if not hot:
                if sign:
                    self.last_sign = sign
                    self.last_sign_frame = self.frame_i
                break
            out = self.prev * 0.5 + out * 0.5
            blended = True
        else:
            out = self.prev * 0.8 + out * 0.2
            blended = True
        if blended: self.clamps += 1
        self.prev = np.clip(out, 0.0, 1.0).copy()
        self.frame_i += 1
        return self.prev.copy()


def contrast_summary(samples, minimum=3.0):
    """samples: list of (text_ratio, sung_ratio). Large lyric type, so the bar is 3:1."""
    if not samples:
        return dict(ok=False, n=0, median_sung=0.0, min_sung=0.0, median_text=0.0,
                    reason="no lyric pixels were sampled; the line never became visible")
    text = np.array([a for a, _ in samples], np.float64)
    sung = np.array([b for _, b in samples], np.float64)
    med = float(np.median(sung)); med_t = float(np.median(text))
    p10 = float(np.percentile(sung, 10)); p10t = float(np.percentile(text, 10))
    # Median is the look. The 10th percentile ignores a sample that landed on a spark or a glyph.
    ok = bool(med >= minimum and med_t >= minimum and p10 >= 2.5 and p10t >= 2.5)
    reason = "" if ok else "lyric contrast is below 3:1 against the background behind the words"
    return dict(ok=ok, n=int(len(samples)), median_sung=round(med, 2), min_sung=round(float(sung.min()), 2),
                p10_sung=round(p10, 2), median_text=round(med_t, 2), reason=reason)
