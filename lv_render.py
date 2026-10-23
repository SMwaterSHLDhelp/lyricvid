"""Frame engine: beat/section context, camera, karaoke typography, title card, fade-out,
parallel segment encoding and exact-duration muxing. Visuals come from a preset module
(presets/<name>.py) that implements `class Preset(ctx)` with `background(t, st) -> RGBA (SW,SH)`
and a STYLE dict (see presets/minimal.py for the smallest working example)."""
import os, sys, math, json, random, subprocess, importlib, numpy as np
from PIL import Image, ImageDraw, ImageFont
from lv_audio import duration

def default_font_dirs():
    """Standard system and user font directories. Search order keeps /usr/share/fonts ahead of
    ~/.fonts, matching the historical lookup, then other platform defaults."""
    home = os.path.expanduser("~")
    if sys.platform == "win32":
        windir = os.environ.get("WINDIR", r"C:\Windows")
        local = os.environ.get("LOCALAPPDATA", "")
        dirs = [os.path.join(windir, "Fonts")]
        if local:
            dirs.append(os.path.join(local, "Microsoft", "Windows", "Fonts"))
        return dirs
    if sys.platform == "darwin":
        return ["/System/Library/Fonts", "/Library/Fonts", os.path.join(home, "Library", "Fonts")]
    dirs = [
        "/usr/share/fonts",
        "/usr/local/share/fonts",
        os.path.join(home, ".fonts"),
        os.path.join(home, ".local", "share", "fonts"),
    ]
    xdg = os.environ.get("XDG_DATA_HOME", "")
    if xdg:
        dirs.append(os.path.join(xdg, "fonts"))
    for data in os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(os.pathsep):
        if data.strip():
            dirs.append(os.path.join(data.strip(), "fonts"))
    return dirs

def _dedupe_dirs(paths):
    out, seen = [], set()
    for p in paths:
        if p is None:
            continue
        p = os.path.expanduser(str(p).strip())
        if not p:
            continue
        key = os.path.normcase(os.path.normpath(p))
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out

def configure_font_dirs(extra):
    """Prepend --font-dir entries onto LYRICVID_FONT_DIRS so segment workers inherit them."""
    if not extra:
        return
    current = os.environ.get("LYRICVID_FONT_DIRS", "").split(os.pathsep)
    merged = _dedupe_dirs(list(extra) + current)
    os.environ["LYRICVID_FONT_DIRS"] = os.pathsep.join(merged)

def font_search_dirs():
    """--font-dir / LYRICVID_FONT_DIRS first, then standard system and user font directories."""
    env = os.environ.get("LYRICVID_FONT_DIRS", "")
    extra = env.split(os.pathsep) if env else []
    return _dedupe_dirs(list(extra) + default_font_dirs())

def find_font(name):
    """Find a .ttf/.otf by file-name substring (e.g. 'ArchivoBlack-Regular')."""
    for d in font_search_dirs():
        if not os.path.isdir(d):
            continue
        for root, _, fs in os.walk(d):
            for f in fs:
                if name.lower() in f.lower() and f.lower().endswith((".ttf", ".otf")): return os.path.join(root, f)
    raise FileNotFoundError(name)

def ease_out(u): u = min(max(u, 0), 1); return 1 - (1 - u) ** 3
def ease_expo(u): u = min(max(u, 0), 1); return 1 if u >= 1 else 1 - 2 ** (-10 * u)
def smooth(u): u = min(max(u, 0), 1); return u * u * (3 - 2 * u)

class Ctx:
    def __init__(self, job):
        self.job = job
        self.W, self.H, self.FPS = job.get("width", 1920), job.get("height", 1080), job.get("fps", 30)
        self.audio = job["audio"]; self.dur = duration(self.audio)
        self.NF = int(math.ceil(self.dur * self.FPS))          # cover the whole song; mux trims to exact audio length
        B = json.load(open(job["beats"])); self.beats = np.array(B["beats"]); self.down = B["down"]
        self.onset = np.array(B["onset"]); self.bpm = B["bpm"]; self.period = 60 / self.bpm
        self.lines = json.load(open(job["lines"]))
        self.fonts = {}
        self.layouts = {}
        self.title = job.get("title", "")
        self.first = self.lines[0]["s"] if self.lines else 3.0
        self.word_events = {}  # word -> [start times], for presets binding events to words
        for L in self.lines:
            for w in L["words"]:
                self.word_events.setdefault(w[0].lower().strip("!?,.\"'()…"), []).append(w[1])
        self.preset = importlib.import_module("presets." + job["preset"]).Preset(self)
        self.S = self.preset.STYLE
        self.SW, self.SH = self.S.get("bg_size", (1280, 720))
    def font(self, key, size):
        k = (key, size)
        if k not in self.fonts: self.fonts[k] = ImageFont.truetype(find_font(self.S["fonts"][key]), size)
        return self.fonts[k]
    def section(self, t):
        prev = None
        for i, L in enumerate(self.lines):
            if L["s"] - 0.4 <= t: prev = i
        if prev is None: return "intro"
        L = self.lines[prev]
        nxt = self.lines[prev + 1]["s"] if prev + 1 < len(self.lines) else self.dur
        if t > L["e"] + 2.5 and nxt - L["e"] > 5:
            return "end" if prev == len(self.lines) - 1 else "inst"
        return L["sec"]
    def state(self, t):
        k = int(np.searchsorted(self.beats, t)) - 1
        dt = t - self.beats[k] if k >= 0 else 1.0; k = max(k, 0)
        down = (k - self.down) % 4 == 0
        bar = (k - self.down) // 4
        sec = self.section(t); hook = sec in self.S.get("hook_sections", ("chorus",))
        pulse = math.exp(-dt * 9) * (1.0 if down else 0.6)
        on = float(self.onset[min(int(t * self.FPS), len(self.onset) - 1)])
        return dict(t=t, k=k, dt=dt, down=down, bar=bar, sec=sec, hook=hook, pulse=pulse, on=on,
                    bar_phase=((k - self.down) % 4 + dt / self.period) / 4)

    # ---------------- typography ----------------
    def word_img(self, w, size, col, shadow=True):
        f = self.font("lyric", size); asc, desc = f.getmetrics(); pad = 16
        im = Image.new("RGBA", (int(f.getlength(w)) + 2 * pad + 8, asc + desc + 2 * pad), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        sw = self.S.get("stroke", 0)
        if shadow: d.text((pad + 5, pad + asc + 6), w, font=f, anchor="ls", fill=(0, 0, 0, 170), stroke_width=sw, stroke_fill=(0, 0, 0, 170))
        d.text((pad, pad + asc), w, font=f, anchor="ls", fill=col + (255,), stroke_width=sw, stroke_fill=(0, 0, 0, 255))
        return im
    def layout(self, li):
        """Full-line layout, centred on the FULL line width (never re-centre as words appear).
        Words share one baseline (anchor 'ls'), wrap to 2 rows if wider than 88% of the frame."""
        if li in self.layouts: return self.layouts[li]
        S = self.S; L = self.lines[li]; hook = L["sec"] in S.get("hook_sections", ("chorus",))
        ws = [w[0].upper() if S.get("upper") else w[0] for w in L["words"]]
        sz = S["hook_size"] if hook else S["size"]
        while True:
            f = self.font("lyric", sz); sp = f.getlength(" "); wd = [f.getlength(w) for w in ws]
            tot = sum(wd) + sp * (len(ws) - 1); rows = None
            if tot < self.W * 0.88: rows = [list(range(len(ws)))]
            elif len(ws) > 1:
                c = min(range(1, len(ws)), key=lambda c: abs(sum(wd[:c]) - sum(wd[c:])))
                if max(sum(wd[:c]) + sp * (c - 1), sum(wd[c:]) + sp * (len(ws) - c - 1)) < self.W * 0.88:
                    rows = [list(range(c)), list(range(c, len(ws)))]
            if rows or sz < 40: break
            sz -= 6
        rows = rows or [list(range(len(ws)))]
        items = []
        for ri, row in enumerate(rows):
            tot = sum(wd[i] for i in row) + sp * (len(row) - 1); x = (self.W - tot) / 2
            dy = (ri - (len(rows) - 1) / 2) * sz * 1.08
            for i in row:
                items.append(dict(x=x, dy=dy, w=wd[i], im=self.word_img(ws[i], sz, S["text"]),
                                  hi=self.word_img(ws[i], sz, S["sung"]), s=L["words"][i][1], e=L["words"][i][2]))
                x += wd[i] + sp
        self.layouts[li] = (items, sz, hook); return self.layouts[li]
    def draw_lyrics(self, fr, t, st, sx, sy):
        S = self.S
        act = [i for i, L in enumerate(self.lines) if L["s"] - S.get("lead", 0.4) <= t <= L["e"] + 0.5]
        if not act: return
        li = act[-1]; L = self.lines[li]; items, sz, hook = self.layout(li)
        yb = self.H * S.get("text_y", 0.8)
        fade = 1 if t <= L["e"] + 0.25 else max(0, 1 - (t - L["e"] - 0.25) / 0.25)
        fin = min(1, (t - L["s"] + S.get("lead", 0.4)) / 0.15)
        fade *= fin
        if S.get("band", 0) > 0:
            f = self.font("lyric", sz); asc, desc = f.getmetrics()
            x0 = min(it["x"] for it in items) - 36; x1 = max(it["x"] + it["w"] for it in items) + 36
            y0 = yb + min(it["dy"] for it in items) - asc * 0.62 - 20; y1 = yb + max(it["dy"] for it in items) + asc * 0.62 + 20
            band = Image.new("RGBA", fr.size, (0, 0, 0, 0))
            ImageDraw.Draw(band).rounded_rectangle([x0 + sx * .5, y0 + sy * .5, x1 + sx * .5, y1 + sy * .5], radius=S.get("band_radius", 18),
                                                   fill=S.get("band_color", (0, 0, 0)) + (int(255 * S["band"] * fade),))
            fr.alpha_composite(band)
        for j, it in enumerate(items):
            st0 = it["s"]
            if t < st0 - 0.03:
                im = it["im"]; a = S.get("unsung_alpha", 0.38); sc = 1.0
            else:
                u = (t - st0 + 0.03) / 0.14; a = 1.0
                sc = 1 + (S.get("hook_slam", 0.6) if hook else S.get("pop", 0.18)) * (1 - ease_out(u))
                im = it["hi"] if t <= it["e"] + 0.12 else it["im"]
            a *= fade
            if a < 0.03: continue
            if sc != 1:
                im = im.resize((int(im.width * sc), int(im.height * sc)) if hook else (im.width, int(im.height * sc)), Image.BILINEAR)
            if a < 0.99:
                im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v, a=a: int(v * a)))
            pad = 16; asc = self.font("lyric", sz).getmetrics()[0]
            scx, scy = im.width / it["im"].width, im.height / it["im"].height
            base = yb + it["dy"] + asc * 0.35
            bx = it["x"] + it["w"] / 2 - (pad + it["w"] / 2) * scx
            by = base - (pad + asc) * scy
            bounce = -int(8 * st["pulse"]) if hook else 0
            fr.alpha_composite(im, (int(bx + sx * .5), int(by + bounce + sy * .5)))

    # ---------------- frame ----------------
    def frame(self, k):
        S = self.S; t = k / self.FPS; st = self.state(t)
        bg = self.preset.background(t, st)
        # camera: beat zoom punch + moderate shake + preset reframing (dx, dy, zoom, rot)
        cam = self.preset.camera(t, st) if hasattr(self.preset, "camera") else (0, 0, 1, 0)
        z = cam[2] * (1 + S.get("punch", 0.02) * st["pulse"] * (1.5 if st["hook"] else 1) + 0.008 * st["on"]) * 1.04
        amp = S.get("shake", 2.0) * (st["on"] + st["pulse"]) * (1.4 if st["hook"] else 1)
        rnd = random.Random(k); sx, sy = rnd.uniform(-1, 1) * amp, rnd.uniform(-1, 1) * amp
        if cam[3]: bg = bg.rotate(cam[3], resample=Image.BILINEAR, center=(self.SW / 2, self.SH / 2))
        cw, ch = self.SW / z, self.SH / z
        cx = min(max(self.SW / 2 + cam[0] + sx, cw / 2), self.SW - cw / 2)
        cy = min(max(self.SH / 2 + cam[1] + sy, ch / 2), self.SH - ch / 2)
        fr = bg.convert("RGB").resize((self.W, self.H), Image.BILINEAR, box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)).convert("RGBA")
        if hasattr(self.preset, "overlay"): self.preset.overlay(fr, t, st)
        if t < self.first - 0.9 and self.title: self.draw_title(fr, t, st)
        self.draw_lyrics(fr, t, st, sx * self.W / self.SW, sy * self.H / self.SH)
        fo = S.get("fade_out", 2.5)
        if t > self.dur - fo:  # fade to black at the end
            a = int(255 * min(1, (t - (self.dur - fo)) / fo))
            fr.alpha_composite(Image.new("RGBA", fr.size, (0, 0, 0, a)))
        fi = S.get("fade_in", 0.6)
        if t < fi: fr.alpha_composite(Image.new("RGBA", fr.size, (0, 0, 0, int(255 * (1 - t / fi)))))
        return fr.convert("RGB")
    def draw_title(self, fr, t, st):
        S = self.S; end = self.first - 0.9
        f = self.font("title", S.get("title_size", 130)); f2 = self.font("mono", 34)
        a = min(1, t / 0.5) * min(1, (end - t) / 0.4)
        sc = 1 + 0.5 * (1 - ease_expo(t / 0.6))
        im = Image.new("RGBA", (self.W, 400), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.text((self.W / 2, 170), self.title, font=f, anchor="mm", fill=S["text"])
        if S.get("subtitle"): d.text((self.W / 2, 290), S["subtitle"], font=f2, anchor="mm", fill=S["sung"])
        if sc != 1: im = im.resize((int(im.width * sc), int(im.height * sc)), Image.BILINEAR)
        im.putalpha(im.getchannel("A").point(lambda v: int(v * max(0, a))))
        fr.alpha_composite(im, (int(self.W / 2 - im.width / 2), int(self.H * S.get("text_y", 0.8) - im.height / 2 - 40)))

def render_segment(job, a, b, out):
    ctx = Ctx(job); b = min(b, ctx.NF)
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{ctx.W}x{ctx.H}",
                           "-r", str(ctx.FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", str(job.get("crf", 21)),
                           "-maxrate", job.get("maxrate", "4M"), "-bufsize", "8M", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for k in range(a, b): ff.stdin.write(ctx.frame(k).tobytes())
    ff.stdin.close(); ff.wait()

def stills(job, times, outdir, prefix="frame"):
    ctx = Ctx(job); os.makedirs(outdir, exist_ok=True); paths = []
    for t in times:
        p = os.path.join(outdir, f"{prefix}_{t:07.2f}.png"); ctx.frame(int(round(t * ctx.FPS))).save(p); paths.append(p)
    return paths
