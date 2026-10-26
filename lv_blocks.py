"""Composable pieces for a lyric-video preset.

A preset is a class. `STYLE` describes type, layout and motion. `background(t, st)`
returns an RGBA picture at `STYLE["bg_size"]`. `camera` and `overlay` are optional.

`st` keys the renderer always fills:
  t, k (beat index), dt (seconds since the beat), down, bar, bar_phase (0..1),
  sec (section name), hook, pulse (decaying beat), on (onset 0..1.5),
  rms, bass, mid, high (each ~0..1, 98th percentile = 1).

Large colour and brightness changes should pass through `Slew` or `AudioFollow`
with `seconds` of at least 0.6. Small marks (a star, a meter bar, a 2 px wobble)
can follow the audio more closely. The safety clamp is the backstop, not the design.

Typical preset, about a page:

    from lv_blocks import AudioFollow, Field, aurora, camera_drift, vignette, word_hit
    class Preset:
        DESCRIPTION = "Deep water, slow light, one gold word."
        STYLE = dict(bg_size=(960, 540), layout="center", kinetic="wave",
                     fonts=dict(lyric="InstrumentSerif-Regular", title="InstrumentSerif-Regular",
                                mono="IBMPlexMono-Regular"),
                     text=(236, 230, 220), sung=(232, 186, 96), size=86, upper=False, glow=2)
        def __init__(self, ctx):
            self.c = ctx; self.audio = AudioFollow(); self.motes = Field(ctx.SW, ctx.SH, 40, seed=2)
        def camera(self, t, st):
            return camera_drift(t, drift=10, rot=0.3)
        def background(self, t, st):
            a = self.audio(st)
            im = aurora(self.c.SW, self.c.SH, t, [(8, 18, 32), (16, 40, 48), (24, 18, 40)], speed=0.06)
            self.motes.draw(im, t, color=(220, 210, 180), react=a["high"] * 0.4)
            if word_hit(self.c, "light", t):
                ...
            return vignette(im, 0.5)
"""
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageChops

def mix(a, b, u):
    u = min(max(float(u), 0.0), 1.0)
    return tuple(int(x + (y - x) * u) for x, y in zip(a, b))

def rgba(color, alpha=255):
    color = tuple(int(c) for c in color[:3])
    if len(color) == 4: return color
    return color + (int(alpha),)

def as_rgba(im):
    return im if im.mode == "RGBA" else im.convert("RGBA")

def fill(w, h, color):
    return Image.new("RGBA", (int(w), int(h)), rgba(color))

def linear_gradient(w, h, c0, c1, vertical=True):
    w, h = int(w), int(h)
    if vertical:
        col = np.linspace(0, 1, h, dtype=np.float32)[:, None]
        shape = (h, 1, 1)
    else:
        col = np.linspace(0, 1, w, dtype=np.float32)[None, :]
        shape = (1, w, 1)
    a = np.array(c0[:3], np.float32); b = np.array(c1[:3], np.float32)
    rgb = a + (b - a) * col.reshape(shape)
    arr = np.zeros((h, w, 4), np.uint8)
    arr[..., :3] = np.clip(np.broadcast_to(rgb, (h, w, 3)), 0, 255)
    arr[..., 3] = 255
    return Image.fromarray(arr, "RGBA")

def radial_gradient(w, h, c0, c1, cx=0.5, cy=0.45):
    w, h = int(w), int(h)
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt(((xx - cx * w) / (w * 0.7)) ** 2 + ((yy - cy * h) / (h * 0.7)) ** 2)
    r = np.clip(r, 0, 1)[..., None]
    a = np.array(c0[:3], np.float32); b = np.array(c1[:3], np.float32)
    rgb = a + (b - a) * r
    arr = np.zeros((h, w, 4), np.uint8)
    arr[..., :3] = np.clip(rgb, 0, 255); arr[..., 3] = 255
    return Image.fromarray(arr, "RGBA")

def aurora(w, h, t, colors, speed=0.08):
    """Smooth flowing field. `colors` is 2–4 RGB triples. `speed` is cycles-ish per second; keep it under 0.15."""
    w, h = int(w), int(h)
    cols = [tuple(c[:3]) for c in list(colors)[:4]]
    while len(cols) < 3: cols.append(cols[-1])
    ys, xs = np.mgrid[0:h, 0:w]
    xs = xs / max(w, 1); ys = ys / max(h, 1)
    f1 = np.sin((xs * 2.4 + t * speed) * math.tau + ys * 2.1)
    f2 = np.sin((ys * 1.8 - t * speed * 0.7) * math.tau + xs * 3.3)
    f3 = np.sin(((xs + ys) * 1.5 + t * speed * 0.45) * math.tau)
    wts = np.stack(((f1 + 1) * 0.5, (f2 + 1) * 0.5, (f3 + 1) * 0.5), axis=-1)
    wts = wts / (wts.sum(-1, keepdims=True) + 1e-6)
    rgb = wts @ np.array(cols[:3], np.float32)
    arr = np.zeros((h, w, 4), np.uint8)
    arr[..., :3] = np.clip(rgb, 0, 255); arr[..., 3] = 255
    return Image.fromarray(arr, "RGBA")

def paper(w, h, tint=(232, 216, 190), speckle=12, seed=1):
    """Warm sheet with a fixed speckle. Speckle does not change per frame, so it cannot strobe."""
    w, h = int(w), int(h)
    rng = np.random.RandomState(seed)
    base = np.array(tint[:3], np.int16)
    n = rng.randint(-int(speckle), int(speckle) + 1, size=(h, w, 1), dtype=np.int16)
    # a broad fixed stain so the sheet is not a flat fill
    yy, xx = np.mgrid[0:h, 0:w]
    stain = (6 * np.sin(xx / 180.0) + 5 * np.cos(yy / 140.0)).astype(np.int16)
    rgb = np.clip(base + n + stain[..., None], 0, 255).astype(np.uint8)
    arr = np.zeros((h, w, 4), np.uint8); arr[..., :3] = rgb; arr[..., 3] = 255
    return Image.fromarray(arr, "RGBA")

def vignette(im, amount=0.55):
    im = as_rgba(im); arr = np.array(im).astype(np.float32)
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    v = np.clip(amount * (r ** 2.1), 0, 0.85)
    arr[..., :3] *= (1 - v)[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")

def grain(im, amount=12, seed=2):
    """Fixed low-amplitude grain. Keep `amount` under ~16 so pixels stay inside the 0.1 luminance step."""
    im = as_rgba(im); arr = np.array(im).astype(np.int16)
    rng = np.random.RandomState(seed)
    n = rng.randint(-int(amount), int(amount) + 1, size=arr.shape[:2], dtype=np.int16)
    arr[..., :3] = np.clip(arr[..., :3] + n[..., None], 0, 255)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")

def scanlines(im, alpha=36, gap=4, color=(0, 0, 0)):
    im = as_rgba(im); d = ImageDraw.Draw(im)
    w, h = im.size
    col = rgba(color, alpha)
    for y in range(0, h, gap): d.line([(0, y), (w, y)], fill=col)
    return im

def wobble(im, t, amp=2.0):
    """Slow horizontal tape drift of a few pixels. Not a per-frame random shift."""
    im = as_rgba(im); arr = np.array(im)
    h, w = arr.shape[:2]
    ys = np.arange(h)
    shift = (float(amp) * np.sin(ys * 0.035 + t * 0.7)).astype(np.int32)
    idx = (np.arange(w)[None, :] - shift[:, None]) % w
    out = arr[np.arange(h)[:, None], idx]
    return Image.fromarray(out, "RGBA")

def halftone(im, step=7, strength=0.2):
    """Static dot screen. Safe because the dots do not move."""
    im = as_rgba(im); arr = np.array(im).astype(np.float32)
    h, w = arr.shape[:2]
    ys, xs = np.ogrid[0:h, 0:w]
    dots = (np.sin(xs * (math.tau / step)) ** 2) * (np.sin(ys * (math.tau / step)) ** 2)
    arr[..., :3] *= (1 - strength * (1 - dots))[..., None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")

def draw_grid(im, t, color=(255, 80, 170), horizon=0.48, speed=0.22, width=2):
    """Perspective floor. One thin line recycles from the horizon each cycle; that is a few pixels, not a flash."""
    im = as_rgba(im); d = ImageDraw.Draw(im)
    w, h = im.size
    hy = h * float(horizon); cx = w / 2.0
    col = tuple(int(c) for c in color[:3])
    for i in range(-14, 15):
        spread = i / 14.0
        d.line([(cx + spread * w * 0.12, hy), (cx + spread * w * 1.05, h + 4)], fill=col + (150,), width=width)
    for i in range(16):
        z = (i / 16.0 + (t * speed) % 1.0) % 1.0
        y = hy + (h - hy) * (0.05 + 0.95 * (z ** 1.65))
        d.line([(0, y), (w, y)], fill=col + (int(40 + 180 * z),), width=width)
    return im

def paint_sun(im, cx, cy, r, color, stripe=(12, 0, 24), bands=6):
    im = as_rgba(im)
    disc = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(disc).ellipse([cx - r, cy - r, cx + r, cy + r], fill=rgba(color))
    stripes = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ds = ImageDraw.Draw(stripes)
    for i in range(int(bands)):
        y0 = cy + r * 0.02 + i * (r * 0.13)
        ds.rectangle([0, y0, im.size[0], y0 + 3 + i], fill=rgba(stripe))
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    stripes.putalpha(ImageChops.multiply(stripes.getchannel("A"), mask))
    disc.alpha_composite(stripes)
    im.alpha_composite(disc)
    return im

def boxes(im, rects):
    """Paste flat cut-outs. Each rect is (x, y, w, h, color, rotation_degrees). Rotation is static."""
    im = as_rgba(im)
    for x, y, w, h, color, rot in rects:
        w, h = max(1, int(w)), max(1, int(h))
        tile = Image.new("RGBA", (w, h), rgba(color))
        if abs(rot) > 0.2:
            tile = tile.rotate(rot, expand=True, resample=Image.BILINEAR, fillcolor=(0, 0, 0, 0))
        _paste(im, tile, (int(x - tile.width / 2), int(y - tile.height / 2)))
    return im

def meters(draw, box, levels, color, gap=0.28):
    """Equaliser bars. `levels` is a list of 0..1 values, already slewed by the caller."""
    x, y, w, h = box
    n = max(1, len(levels))
    bw = w / n
    col = rgba(color)
    for i, lv in enumerate(levels):
        lv = min(max(float(lv), 0.0), 1.0)
        bh = h * (0.08 + 0.92 * lv)
        x0 = x + i * bw
        draw.rectangle([x0, y + h - bh, x0 + bw * (1 - gap), y + h], fill=col)

def _paste(base, im, xy):
    x, y = int(xy[0]), int(xy[1])
    if im.mode != "RGBA": im = im.convert("RGBA")
    if x >= base.width or y >= base.height or x + im.width <= 0 or y + im.height <= 0: return
    if x < 0 or y < 0 or x + im.width > base.width or y + im.height > base.height:
        l, t = max(0, -x), max(0, -y)
        r, b = min(im.width, base.width - x), min(im.height, base.height - y)
        if r <= l or b <= t: return
        im = im.crop((l, t, r, b)); x, y = max(0, x), max(0, y)
    base.alpha_composite(im, (x, y))

class Field:
    """A seeded particle field. `kind` is stars, dust, or rise.

    Motion is continuous. `react` (0..1) only changes the radius a little; slew it
    if you drive it from raw bass and the particles cover a lot of the frame.
    """
    def __init__(self, w, h, n=80, seed=0, kind="stars"):
        rng = random.Random(seed)
        self.w, self.h, self.kind = int(w), int(h), kind
        self.p = [(rng.random(), rng.random(), rng.uniform(0.35, 1.0), rng.uniform(0, math.tau)) for _ in range(int(n))]

    def draw(self, im, t, color=(255, 255, 255), react=0.0, alpha=1.0):
        im = as_rgba(im); d = ImageDraw.Draw(im)
        col = tuple(int(c) for c in color[:3])
        react = min(max(float(react), 0.0), 1.5)
        for x, y, s, ph in self.p:
            if self.kind == "rise":
                px, py = (x + 0.015 * math.sin(t * 0.4 + ph)) % 1.0, (y - t * 0.025 * (0.4 + s)) % 1.0
            elif self.kind == "dust":
                px = (x + t * 0.008 * s + 0.01 * math.sin(t * 0.3 + ph)) % 1.0
                py = (y + 0.02 * math.sin(t * 0.2 + ph)) % 1.0
            else:
                px = (x * 0.15 + (ph / math.tau) + t * 0.004 * (0.4 + s)) % 1.0
                py = y
            # stars drift sideways slowly; y is depth-ish via size
            r = (0.8 + s * 1.6) * (1 + 0.35 * react)
            a = int(max(0, min(255, (120 + 110 * s) * alpha)))
            cx, cy = px * self.w, (py if self.kind != "stars" else (0.08 + y * 0.84)) * self.h
            if self.kind == "stars":
                cy = y * self.h
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=col + (a,))
        return im

class Slew:
    """Limit how fast a float (0..1) or an RGB triple (0..255) may change."""
    def __init__(self, seconds=0.6, fps=30):
        self.step = 1.0 / max(1.0, float(seconds) * float(fps))
        self.v = None
    def __call__(self, value):
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            target = float(value)
            if self.v is None:
                self.v = target; return self.v
            d = max(-self.step, min(self.step, target - self.v))
            self.v = self.v + d
            return self.v
        target = tuple(int(x) for x in value[:3])
        if self.v is None:
            self.v = target; return self.v
        step = 255.0 * self.step
        out = []
        for a, b in zip(self.v, target):
            d = max(-step, min(step, b - a))
            out.append(a + d)
        self.v = tuple(out)
        return tuple(int(round(x)) for x in self.v)

class AudioFollow:
    """Slewed rms / bass / mid / high / on / pulse. Default window is 0.6s."""
    KEYS = ("rms", "bass", "mid", "high", "on", "pulse")
    def __init__(self, seconds=0.6, fps=30):
        self.s = {k: Slew(seconds, fps) for k in self.KEYS}
    def __call__(self, st):
        return {k: self.s[k](float(st.get(k, 0.0))) for k in self.KEYS}

def word_hit(ctx, word, t, window=1.0):
    """1 at the moment `word` is sung, falling to 0 across `window` seconds. 0 if it is not in the song."""
    key = str(word).lower().strip("!?,.\"'()…")
    best = 0.0
    for e in ctx.word_events.get(key, []):
        age = t - e
        if 0 <= age < window: best = max(best, 1.0 - age / window)
    return best

def camera_still():
    return (0, 0, 1.0, 0)

def camera_drift(t, drift=12, rot=0.4, zoom=1.0):
    """Slow reframing. No beat snap."""
    return (math.sin(t * 0.17) * drift, math.cos(t * 0.13) * drift * 0.45,
            zoom + 0.012 * math.sin(t * 0.11), math.sin(t * 0.09) * rot)

def soft_blob(im, cx, cy, r, color, alpha=90):
    """A cheap glow: a few nested ellipses, no blur kernel."""
    im = as_rgba(im); layer = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    col = tuple(int(c) for c in color[:3])
    for i in range(6, 0, -1):
        rr = r * (i / 6)
        a = int(alpha * (0.25 + 0.12 * (6 - i)))
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=col + (a,))
    im.alpha_composite(layer)
    return im
