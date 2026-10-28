"""Frame engine. A preset supplies the picture; this module supplies typography, camera and safety.

Preset module (`presets/<name>.py`, a path ending in `.py`, or a `.json` style spec):

    class Preset:
        DESCRIPTION = "one line"
        STYLE = { ... }          # merged over DEFAULT_STYLE, then --preset-opts
        def __init__(self, ctx): ...
        def background(self, t, st) -> RGBA image at STYLE["bg_size"]
        def camera(self, t, st) -> (dx, dy, zoom, rot)     # optional
        def overlay(self, img, t, st)                       # optional, full-frame RGBA

Layout (`STYLE["layout"]`): lower, center, karaoke, scatter, stack.
Kinetic (`STYLE["kinetic"]`): pop, none, slide, type, scale, rotate, wave.

Word slots keep their unscaled advance. Scale never grows a glyph past that slot
(horizontal scale stays <= 1), and pop only stretches vertically, so a highlighted
word cannot swallow the gap before the next word.

Every delivered frame passes through lv_safety.Guard.
"""
import os, sys, math, json, random, subprocess, importlib, importlib.util, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from lv_audio import duration
from lv_safety import Guard, contrast_ratio

DEFAULT_STYLE = dict(
    bg_size=(1280, 720),
    text=(240, 236, 228), sung=(255, 210, 80),
    size=80, hook_size=112, upper=False,
    layout="lower", kinetic="pop",
    unsung_alpha=0.38, band=0.5, band_color=(0, 0, 0), band_radius=16,
    pop=0.16, hook_slam=0.22, punch=0.02, shake=1.4,
    text_y=0.78, lead=0.35, stroke=0, stroke_color=(0, 0, 0),
    shadow=True, shadow_px=5, glow=0,
    title_card=True, title_size=110, title_mode="center", subtitle="",
    fade_in=0.6, fade_out=2.0, safety=True,
    hook_sections=("chorus",),
    slide=28, wave=7, rotate=8, kinetic_time=0.32, line_fade=0.24,
    jitter_rot=0, ransom=False, karaoke_ahead=True,
    keyword=(255, 176, 48), keywords=(),
    section_card=False, section_hold=1.8, section_color=None,
)

def default_font_dirs():
    """Bundled fonts first, then the standard system and user font directories."""
    home = os.path.expanduser("~")
    bundled = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
    if sys.platform == "win32":
        windir = os.environ.get("WINDIR", r"C:\Windows")
        local = os.environ.get("LOCALAPPDATA", "")
        dirs = [bundled, os.path.join(windir, "Fonts")]
        if local: dirs.append(os.path.join(local, "Microsoft", "Windows", "Fonts"))
        return dirs
    if sys.platform == "darwin":
        return [bundled, "/System/Library/Fonts", "/Library/Fonts", os.path.join(home, "Library", "Fonts")]
    dirs = [
        bundled,
        "/usr/share/fonts",
        "/usr/local/share/fonts",
        os.path.join(home, ".fonts"),
        os.path.join(home, ".local", "share", "fonts"),
    ]
    xdg = os.environ.get("XDG_DATA_HOME", "")
    if xdg: dirs.append(os.path.join(xdg, "fonts"))
    for data in os.environ.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(os.pathsep):
        if data.strip(): dirs.append(os.path.join(data.strip(), "fonts"))
    return dirs

def _dedupe_dirs(paths):
    out, seen = [], set()
    for p in paths:
        if p is None: continue
        p = os.path.expanduser(str(p).strip())
        if not p: continue
        key = os.path.normcase(os.path.normpath(p))
        if key in seen: continue
        seen.add(key); out.append(p)
    return out

def configure_font_dirs(extra):
    """Prepend --font-dir entries onto LYRICVID_FONT_DIRS so segment workers inherit them."""
    if not extra: return
    current = os.environ.get("LYRICVID_FONT_DIRS", "").split(os.pathsep)
    os.environ["LYRICVID_FONT_DIRS"] = os.pathsep.join(_dedupe_dirs(list(extra) + current))

def font_search_dirs():
    env = os.environ.get("LYRICVID_FONT_DIRS", "")
    extra = env.split(os.pathsep) if env else []
    return _dedupe_dirs(list(extra) + default_font_dirs())

_FONT_CACHE = {}
_FONT_WARNED = set()

def _search(name):
    key = name.lower()
    if key in _FONT_CACHE: return _FONT_CACHE[key]
    hits = []
    for d in font_search_dirs():
        if not os.path.isdir(d): continue
        for root, _, fs in os.walk(d):
            for f in fs:
                if key in f.lower() and f.lower().endswith((".ttf", ".otf")):
                    hits.append(os.path.join(root, f))
    if not hits:
        _FONT_CACHE[key] = None; return None
    def rank(p):
        stem = os.path.splitext(os.path.basename(p))[0].lower()
        return (0 if stem == key else 1, len(stem), p)
    found = sorted(hits, key=rank)[0]
    _FONT_CACHE[key] = found
    return found

def split_font(spec):
    """'Orbitron[wght]@Bold' -> ('Orbitron[wght]', 'Bold')."""
    spec = str(spec)
    if "@" in spec:
        name, var = spec.split("@", 1)
        return name, var or None
    return spec, None

def resolve_font(spec):
    """Return (path, variation). Tries each candidate, then DejaVu / Liberation."""
    items = list(spec) if isinstance(spec, (list, tuple)) else [spec]
    tried = []
    for item in items:
        name, var = split_font(item)
        tried.append(name)
        path = _search(name)
        if path: return path, var
    for name in ("DejaVuSans-Bold", "DejaVuSans", "LiberationSans-Bold", "LiberationSans"):
        path = _search(name)
        if path:
            label = ",".join(tried) or "font"
            if label not in _FONT_WARNED:
                _FONT_WARNED.add(label)
                print(f"[lyricvid] font {label!r} not found; using {os.path.basename(path)}. "
                      f"Run scripts/install_fonts.py or pass --font-dir.", flush=True)
            return path, None
    raise FileNotFoundError(tried[0] if tried else "font")

def find_font(name):
    """Path to a .ttf/.otf whose file name contains `name`. Falls back rather than crashing."""
    path, _var = resolve_font(name)
    return path

def ease_out(u): u = min(max(u, 0), 1); return 1 - (1 - u) ** 3
def ease_expo(u): u = min(max(u, 0), 1); return 1 if u >= 1 else 1 - 2 ** (-10 * u)
def smooth(u): u = min(max(u, 0), 1); return u * u * (3 - 2 * u)

def _load_py(path):
    path = os.path.abspath(path)
    mod_name = "lyricvid_preset_" + os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(mod_name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def _wrap_scene_module(mod):
    """A scenes file with no Preset class becomes a line-art show."""
    import types
    from lv_scenes import SceneShow
    class Preset(SceneShow):
        DESCRIPTION = getattr(mod, "DESCRIPTION", "line-art scenes")
        def __init__(self, ctx, _mod=mod):
            SceneShow.__init__(self, ctx, module=_mod)
    out = types.ModuleType(getattr(mod, "__name__", "lyricvid_scenes"))
    out.Preset = Preset
    out.DESCRIPTION = Preset.DESCRIPTION
    out.LYRICS = getattr(mod, "LYRICS", None)
    return out

def load_preset(spec):
    """Import a preset name, a .py path, a scene file, or a JSON/YAML spec."""
    spec = str(spec)
    low = spec.lower()
    if low.endswith((".json", ".yml", ".yaml")):
        from lv_spec import load_spec
        return load_spec(spec)
    if low.endswith(".py") or os.path.sep in spec or os.path.exists(spec):
        path = spec if os.path.isabs(spec) else spec
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        module = _load_py(path)
        if hasattr(module, "Preset"): return module
        from lv_scenes import is_scene_module
        if is_scene_module(module): return _wrap_scene_module(module)
        raise ImportError(f"{path} has no Preset class and no SCENES list")
    return importlib.import_module("presets." + spec)

def _coerce_style_value(v):
    if isinstance(v, str) and v.startswith("#") and len(v) in (4, 7):
        h = v[1:]
        if len(h) == 3: h = "".join(c * 2 for c in h)
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    return v

class Ctx:
    def __init__(self, job):
        self.job = job
        self.W, self.H, self.FPS = int(job.get("width", 1920)), int(job.get("height", 1080)), int(job.get("fps", 30))
        self.audio = job["audio"]; self.dur = duration(self.audio)
        self.NF = int(math.ceil(self.dur * self.FPS))
        B = json.load(open(job["beats"]))
        self.beats = np.array(B["beats"], dtype=float)
        if len(self.beats) == 0: self.beats = np.array([0.0])
        self.down = int(B.get("down", 0)); self.onset = np.array(B["onset"], dtype=float)
        self.bpm = float(B["bpm"]); self.period = 60.0 / self.bpm
        self.rms = np.array(B.get("rms", B["onset"]), dtype=float)
        self.bass = np.array(B.get("bass", B["onset"]), dtype=float)
        self.mid = np.array(B.get("mid", B["onset"]), dtype=float)
        self.high = np.array(B.get("high", B["onset"]), dtype=float)
        self.lines = json.load(open(job["lines"]))
        self.fonts = {}; self.layouts = {}
        self.title = job.get("title", "")
        self.first = self.lines[0]["s"] if self.lines else 3.0
        self.word_events = {}
        for L in self.lines:
            for w in L["words"]:
                self.word_events.setdefault(str(w[0]).lower().strip("!?,.\"'()…"), []).append(w[1])
        self.opts = {}
        for k, v in (job.get("preset_opts") or {}).items():
            self.opts[k] = _coerce_style_value(v)
        # Presets (and scene files) fill these before the first frame.
        self.line_keywords = {}   # line index -> set of lowercase words drawn in the keyword colour
        self.section_titles = {}  # section name -> card label
        self.preset = load_preset(job["preset"]).Preset(self)
        style = dict(DEFAULT_STYLE)
        style.update(getattr(self.preset, "STYLE", {}) or {})
        style.update(self.opts)
        fonts = dict(style.get("fonts") or {})
        fonts.setdefault("lyric", "DejaVuSans-Bold")
        fonts.setdefault("title", fonts["lyric"])
        fonts.setdefault("mono", "DejaVuSansMono")
        style["fonts"] = fonts
        self.preset.STYLE = style
        self.S = style
        self.SW, self.SH = style.get("bg_size", (1280, 720))
        self.guard = Guard()
        self.contrast_samples = []

    def _env(self, arr, t):
        if arr is None or len(arr) == 0: return 0.0
        i = min(max(int(t * self.FPS), 0), len(arr) - 1)
        return float(arr[i])

    def font(self, key, size):
        spec = self.S["fonts"].get(key) or self.S["fonts"]["lyric"]
        path, var = resolve_font(spec)
        k = (path, var, int(size))
        if k not in self.fonts:
            f = ImageFont.truetype(path, int(size))
            if var and hasattr(f, "set_variation_by_name"):
                try: f.set_variation_by_name(var)
                except Exception: pass
            self.fonts[k] = f
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
        dt = t - float(self.beats[k]) if k >= 0 else 1.0; k = max(k, 0)
        down = (k - self.down) % 4 == 0
        bar = (k - self.down) // 4
        sec = self.section(t); hook = sec in self.S.get("hook_sections", ("chorus",))
        pulse = math.exp(-dt * 9) * (1.0 if down else 0.6)
        on = self._env(self.onset, t)
        return dict(t=t, k=k, dt=dt, down=down, bar=bar, sec=sec, hook=hook, pulse=pulse, on=on,
                    bar_phase=((k - self.down) % 4 + dt / self.period) / 4,
                    rms=self._env(self.rms, t), bass=self._env(self.bass, t),
                    mid=self._env(self.mid, t), high=self._env(self.high, t))

    # ---------------- typography ----------------
    def _font_key(self, i):
        if not self.S.get("ransom"): return "lyric"
        fonts = self.S["fonts"]
        if i % 3 == 2 and "lyric_c" in fonts: return "lyric_c"
        if i % 2 == 1 and "lyric_b" in fonts: return "lyric_b"
        return "lyric"

    def word_img(self, w, size, col, font_key="lyric"):
        S = self.S
        f = self.font(font_key, size); asc, desc = f.getmetrics()
        glow = int(S.get("glow", 0) or 0)
        sw = int(S.get("stroke", 0) or 0)
        shadow = bool(S.get("shadow", True))
        sh = int(S.get("shadow_px", 5) or 0) if shadow else 0
        pad = 18 + sw + glow * 3 + sh
        width = int(f.getlength(w)) + 2 * pad + 8
        im = Image.new("RGBA", (max(1, width), asc + desc + 2 * pad), (0, 0, 0, 0))
        stroke_col = tuple(S.get("stroke_color", (0, 0, 0)))[:3]
        xy = (pad, pad + asc)
        if glow > 0:
            g = Image.new("RGBA", im.size, (0, 0, 0, 0))
            ImageDraw.Draw(g).text(xy, w, font=f, anchor="ls", fill=tuple(col) + (170,))
            g = g.filter(ImageFilter.GaussianBlur(radius=max(1, glow)))
            im.alpha_composite(g)
        d = ImageDraw.Draw(im)
        if shadow and sh:
            d.text((xy[0] + sh, xy[1] + int(sh * 0.75)), w, font=f, anchor="ls", fill=(0, 0, 0, 150),
                   stroke_width=sw, stroke_fill=(0, 0, 0, 120))
        d.text(xy, w, font=f, anchor="ls", fill=tuple(col) + (255,),
               stroke_width=sw, stroke_fill=stroke_col + (255,))
        return im, pad, asc

    def layout(self, li):
        if li in self.layouts: return self.layouts[li]
        S = self.S; L = self.lines[li]
        mode = S.get("layout", "lower")
        hook = L["sec"] in S.get("hook_sections", ("chorus",))
        ws = [w[0].upper() if S.get("upper") else w[0] for w in L["words"]]
        sz = int(S["hook_size"] if hook else S["size"])
        if mode == "center": sz = int(S.get("center_size", sz + 8))
        if mode == "stack": sz = int(S.get("stack_size", max(sz, 96)))
        max_frac = 0.9 if mode in ("center", "stack", "karaoke") else 0.88
        sw = int(S.get("stroke", 0) or 0)
        rows = wd = gap = None
        f = self.font("lyric", sz)
        while sz >= 28:
            f = self.font("lyric", sz)
            space = f.getlength(" ")
            gap = space + sw * 2 + 6
            if S.get("kinetic") == "rotate" or S.get("jitter_rot"): gap += sz * 0.1
            wd = [f.getlength(ws[i] if not S.get("ransom") else ws[i]) for i in range(len(ws))]
            # ransom fonts differ in width; measure with the font that will draw
            if S.get("ransom"):
                wd = [self.font(self._font_key(i), sz).getlength(ws[i]) for i in range(len(ws))]
            def row_w(idxs):
                if not idxs: return 0
                return sum(wd[i] for i in idxs) + gap * (len(idxs) - 1)
            limit = self.W * max_frac
            if mode == "stack":
                if max(wd or [0]) <= limit and len(ws) * sz * 1.08 <= self.H * 0.82: break
            elif mode == "scatter":
                if max(wd or [0]) <= self.W * 0.42: break
            else:
                if row_w(range(len(ws))) <= limit or len(ws) <= 1:
                    rows = [list(range(len(ws)))]; break
                c = min(range(1, len(ws)), key=lambda c: abs(sum(wd[:c]) - sum(wd[c:])))
                if max(row_w(range(c)), row_w(range(c, len(ws)))) <= limit:
                    rows = [list(range(c)), list(range(c, len(ws)))]; break
                # greedy wrap, capped later by giving up size
                rows, cur = [], []
                for i in range(len(ws)):
                    trial = cur + [i]
                    if cur and row_w(trial) > limit:
                        rows.append(cur); cur = [i]
                    else: cur = trial
                if cur: rows.append(cur)
                if len(rows) <= 3: break
            sz -= 4
        if rows is None:
            rows = [[i] for i in range(len(ws))] if mode == "stack" else [list(range(len(ws)))]
        text_y = float(S.get("text_y", 0.5 if mode in ("center", "stack", "scatter") else 0.78))
        if mode == "center" and "text_y" not in getattr(self.preset, "STYLE", {}) and "text_y" not in self.opts:
            text_y = 0.5
        items = []
        rng = random.Random(1009 + li * 17)
        if mode == "scatter":
            placed = []
            for i in range(len(ws)):
                width = wd[i]
                x = y = 0
                for _try in range(24):
                    x = rng.uniform(self.W * 0.06, max(self.W * 0.08, self.W * 0.94 - width))
                    y = rng.uniform(self.H * 0.18, self.H * 0.82)
                    if all(abs(x - px) > (width + pw) * 0.45 or abs(y - py) > sz * 0.9 for px, py, pw in placed):
                        break
                placed.append((x, y, width))
                jrot = rng.uniform(-S.get("jitter_rot", 0), S.get("jitter_rot", 0)) if S.get("jitter_rot") else 0
                items.append(self._item(ws[i], i, x, y, width, sz, L, jrot, li))
        elif mode == "stack":
            block = len(ws) * sz * 1.06
            y0 = self.H * text_y - block / 2 + sz * 0.75
            for i in range(len(ws)):
                x = (self.W - wd[i]) / 2
                jrot = rng.uniform(-S.get("jitter_rot", 0), S.get("jitter_rot", 0)) if S.get("jitter_rot") else 0
                items.append(self._item(ws[i], i, x, y0 + i * sz * 1.06, wd[i], sz, L, jrot, li))
        else:
            for ri, row in enumerate(rows):
                tot = sum(wd[i] for i in row) + gap * (len(row) - 1)
                x = (self.W - tot) / 2
                y = self.H * text_y + (ri - (len(rows) - 1) / 2) * sz * 1.12
                for i in row:
                    jrot = rng.uniform(-S.get("jitter_rot", 0), S.get("jitter_rot", 0)) if S.get("jitter_rot") else 0
                    items.append(self._item(ws[i], i, x, y, wd[i], sz, L, jrot, li))
                    x += wd[i] + gap
        self.layouts[li] = (items, sz, hook, mode)
        return self.layouts[li]

    def _norm_word(self, word):
        return str(word).lower().strip("!?,.\"'()…")

    def _is_keyword(self, li, word):
        keys = {self._norm_word(k) for k in (self.S.get("keywords") or ())}
        keys |= {self._norm_word(k) for k in self.line_keywords.get(li, ())}
        return self._norm_word(word) in keys

    def _item(self, word, i, x, y, width, sz, L, jrot, li):
        key = self._font_key(i)
        im, pad, asc = self.word_img(word, sz, self.S["text"], key)
        hi, _, _ = self.word_img(word, sz, self.S["sung"], key)
        is_kw = self._is_keyword(li, word)
        kw = None
        if is_kw:
            kw, _, _ = self.word_img(word, sz, self.S.get("keyword", self.S["sung"]), key)
        ww = L["words"][i]
        return dict(x=x, y=y, w=width, word=word, im=im, hi=hi, kw=kw, is_kw=is_kw,
                    pad=pad, asc=asc, s=ww[1], e=ww[2], i=i, jrot=jrot, key=key, sz=sz, li=li)

    def _kinetic(self, it, t, hook, allow_highlight):
        S = self.S
        kind = S.get("kinetic", "pop") or "none"
        if not allow_highlight: kind = "none"
        st0, en = it["s"], it["e"]
        unsung = float(S.get("unsung_alpha", 0.38))
        dur = float(S.get("kinetic_time", 0.32))
        out = dict(alpha=unsung, sx=1.0, sy=1.0, rot=it["jrot"], ox=0.0, oy=0.0, clip=1.0, hi=False)
        if t < st0 - 0.03:
            if kind == "type": out["alpha"] = 0.0
            return out
        u = ease_out(min(1.0, (t - st0 + 0.03) / max(0.12, dur)))
        hi = t <= en + 0.12
        out.update(alpha=1.0, hi=hi)
        if kind == "pop":
            pop = float(S.get("hook_slam", 0.22) if hook else S.get("pop", 0.16))
            out["sy"] = 1.0 + pop * (1 - u)   # vertical only; the slot width does not change
        elif kind == "slide":
            out["oy"] = (1 - u) * float(S.get("slide", 28))
        elif kind == "type":
            out["clip"] = max(0.04, u)
        elif kind == "scale":
            # Grow into the slot. sx stays <= 1 so the glyph cannot cross the gap.
            sc = 0.78 + 0.22 * u
            out["sx"] = sc; out["sy"] = sc; out["alpha"] = 0.35 + 0.65 * u
        elif kind == "rotate":
            out["rot"] = it["jrot"] + (1 - u) * float(S.get("rotate", 8))
        elif kind == "wave":
            out["oy"] = math.sin(t * 2.1 + it["i"] * 0.75) * float(S.get("wave", 7))
        elif kind == "none":
            out["rot"] = it["jrot"]
        return out

    def _blit_word(self, fr, it, kin, fade):
        # Active word uses the sung colour. A keyword keeps the accent once it has started,
        # including while it is dim, so the highlight is not only a one-frame pop.
        if kin["hi"]: im = it["hi"]
        elif it.get("is_kw") and it.get("kw") is not None: im = it["kw"]
        else: im = it["im"]
        a = kin["alpha"] * fade
        if a < 0.03: return
        sx, sy = kin["sx"], kin["sy"]
        if sx > 1: sx = 1  # hard guard: horizontal growth collides with the next word
        if abs(sx - 1) > 0.01 or abs(sy - 1) > 0.01:
            im = im.resize((max(1, int(im.width * sx)), max(1, int(im.height * sy))), Image.BICUBIC)
        if kin["clip"] < 0.999:
            reveal = int(it["pad"] * sx + it["w"] * kin["clip"] + int(self.S.get("stroke", 0) or 0))
            shown = Image.new("RGBA", im.size, (0, 0, 0, 0))
            reveal = max(1, min(im.width, reveal))
            shown.paste(im.crop((0, 0, reveal, im.height)), (0, 0))
            im = shown
        if a < 0.99:
            im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v, a=a: int(v * a)))
        rot = kin["rot"]
        cx = it["x"] + it["w"] / 2 + kin["ox"]
        if abs(rot) > 0.4:
            im = im.rotate(rot, resample=Image.BICUBIC, expand=True, fillcolor=(0, 0, 0, 0))
            cy = it["y"] - it["asc"] * 0.45 * sy + kin["oy"]
            self._paste(fr, im, (cx - im.width / 2, cy - im.height / 2))
            return
        bx = it["x"] + it["w"] / 2 - (it["pad"] + it["w"] / 2) * sx + kin["ox"]
        by = it["y"] - (it["pad"] + it["asc"]) * sy + kin["oy"]
        self._paste(fr, im, (bx, by))

    def _paste(self, base, im, xy):
        x, y = int(xy[0]), int(xy[1])
        if x >= base.width or y >= base.height or x + im.width <= 0 or y + im.height <= 0: return
        if x < 0 or y < 0 or x + im.width > base.width or y + im.height > base.height:
            l, t = max(0, -x), max(0, -y)
            r, b = min(im.width, base.width - x), min(im.height, base.height - y)
            if r <= l or b <= t: return
            im = im.crop((l, t, r, b)); x, y = max(0, x), max(0, y)
        base.alpha_composite(im, (x, y))

    def _sample_contrast(self, fr, it):
        # Just left of the glyph, inside the plate, so the sample is the plate and not a neighbour's ink.
        x = int(min(max(it["x"] - 12, 0), fr.width - 1))
        y = int(min(max(it["y"] - it["sz"] * 0.2, 0), fr.height - 1))
        bg = fr.getpixel((x, y))[:3]
        sung = self.S["sung"]
        if it.get("is_kw"): sung = self.S.get("keyword", sung)
        self.contrast_samples.append((contrast_ratio(self.S["text"], bg), contrast_ratio(sung, bg)))

    def _band(self, fr, items, sz, fade, sx, sy):
        S = self.S
        if fade < 0.02 or not items: return
        mode = S.get("layout", "lower")
        f = self.font("lyric", sz); asc, desc = f.getmetrics()
        if mode in ("scatter", "stack"):
            band = Image.new("RGBA", fr.size, (0, 0, 0, 0)); d = ImageDraw.Draw(band)
            a = int(255 * S.get("band", 0) * fade)
            col = tuple(S.get("band_color", (0, 0, 0))) + (a,)
            for it in items:
                d.rounded_rectangle([it["x"] - 18, it["y"] - asc * 0.95, it["x"] + it["w"] + 18, it["y"] + desc + 10],
                                    radius=S.get("band_radius", 12), fill=col)
            fr.alpha_composite(band)
            return
        x0 = min(it["x"] for it in items) - 28; x1 = max(it["x"] + it["w"] for it in items) + 28
        y0 = min(it["y"] for it in items) - asc * 0.85 - 12
        y1 = max(it["y"] for it in items) + desc + 16
        band = Image.new("RGBA", fr.size, (0, 0, 0, 0))
        ImageDraw.Draw(band).rounded_rectangle(
            [x0 + sx * 0.5, y0 + sy * 0.5, x1 + sx * 0.5, y1 + sy * 0.5],
            radius=S.get("band_radius", 16),
            fill=tuple(S.get("band_color", (0, 0, 0))) + (int(255 * S.get("band", 0) * fade),))
        fr.alpha_composite(band)

    def draw_line(self, fr, t, li, y_shift, fade, allow_highlight, hook, sx, sy):
        items, sz, line_hook, _mode = self.layout(li)
        if y_shift:
            # draw a shifted copy without touching the cached coordinates
            items = [dict(it, y=it["y"] + y_shift) for it in items]
        use_hook = hook or line_hook
        if S_band := self.S.get("band", 0):
            if S_band > 0 and allow_highlight:
                self._band(fr, items, sz, fade, sx, sy)
        for it in items:
            if allow_highlight: self._sample_contrast(fr, it)
            kin = self._kinetic(it, t, use_hook and allow_highlight, allow_highlight)
            kin["ox"] += sx * 0.5; kin["oy"] += sy * 0.5
            self._blit_word(fr, it, kin, fade)

    def draw_lyrics(self, fr, t, st, sx, sy):
        S = self.S
        if not self.lines: return
        act = [i for i, L in enumerate(self.lines) if L["s"] - S.get("lead", 0.35) <= t <= L["e"] + 0.5]
        if not act: return
        li = act[-1]; L = self.lines[li]
        items, sz, hook, mode = self.layout(li)
        fade = 1 if t <= L["e"] + 0.2 else max(0, 1 - (t - L["e"] - 0.2) / 0.3)
        fin = min(1, max(0, (t - (L["s"] - S.get("lead", 0.35))) / max(0.05, float(S.get("line_fade", 0.24)))))
        fade *= fin
        if mode == "karaoke" and S.get("karaoke_ahead", True) and li + 1 < len(self.lines):
            self.draw_line(fr, t, li + 1, sz * 1.2, fade * 0.55, False, False, sx, sy)
        self.draw_line(fr, t, li, 0, fade, True, hook, sx, sy)

    def draw_title(self, fr, t, st):
        S = self.S
        if not S.get("title_card", True) or not self.title: return
        end = self.first - 0.9
        if t >= end: return
        a = min(1, t / 0.45) * min(1, max(0, (end - t) / 0.4))
        if a < 0.02: return
        mode = S.get("title_mode", "center")
        f = self.font("title", int(S.get("title_size", 110)))
        f2 = self.font("mono", 32)
        im = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        if mode == "lower": cy = self.H * 0.72
        elif mode == "top": cy = self.H * 0.22
        else: cy = self.H * 0.42
        panel = S.get("title_panel")
        if panel:
            tw = f.getlength(self.title)
            d.rounded_rectangle([self.W / 2 - tw / 2 - 48, cy - 80, self.W / 2 + tw / 2 + 48, cy + (120 if S.get("subtitle") else 70)],
                                radius=18, fill=tuple(panel) + (int(180 * a),))
        d.text((self.W / 2, cy), self.title, font=f, anchor="mm", fill=tuple(S["text"]) + (int(255 * a),))
        if S.get("subtitle"):
            d.text((self.W / 2, cy + 78), S["subtitle"], font=f2, anchor="mm", fill=tuple(S["sung"]) + (int(255 * a),))
        fr.alpha_composite(im)

    def _section_spans(self):
        spans = []
        for L in self.lines:
            if not spans or spans[-1][0] != L["sec"]:
                spans.append([L["sec"], L["s"], L["e"]])
            else:
                spans[-1][2] = L["e"]
        return spans

    def draw_section_card(self, fr, t, st):
        """Glowing section title. Alpha eases in and out over 0.6s; it never cuts on a beat."""
        S = self.S
        if not S.get("section_card"): return
        hold = float(S.get("section_hold", 1.8)); fade = 0.6
        col = tuple(S.get("section_color") or S.get("keyword") or S["sung"])
        f = self.font("title", int(S.get("section_size", 40)))
        # Only the section that has started most recently. Two titles on the same
        # spot read as one smashed word ("THE" over "SHELF").
        current = None
        for sec, s, e in self._section_spans():
            if s <= t: current = (sec, s)
        if current is None: return
        sec, s = current
        local = t - s
        if local < 0 or local > hold: return
        if local < fade: a = local / fade
        elif local > hold - fade: a = max(0.0, (hold - local) / fade)
        else: a = 1.0
        if a < 0.03: return
        label = str(self.section_titles.get(sec, sec)).upper()
        y = int(fr.height * 0.1)
        layer = Image.new("RGBA", fr.size, (0, 0, 0, 0))
        glow = Image.new("RGBA", fr.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((fr.width / 2, y), label, font=f, anchor="mm", fill=col + (int(230 * a),))
        ImageDraw.Draw(glow).text((fr.width / 2, y), label, font=f, anchor="mm", fill=col + (int(150 * a),))
        fr.alpha_composite(glow.filter(ImageFilter.GaussianBlur(radius=7)))
        fr.alpha_composite(layer)

    def frame(self, k):
        S = self.S; t = k / self.FPS; st = self.state(t)
        bg = self.preset.background(t, st)
        if not isinstance(bg, Image.Image):
            raise TypeError("Preset.background must return a PIL image")
        if bg.mode != "RGBA": bg = bg.convert("RGBA")
        if bg.size != (self.SW, self.SH): bg = bg.resize((self.SW, self.SH), Image.LANCZOS)
        cam = self.preset.camera(t, st) if hasattr(self.preset, "camera") else (0, 0, 1, 0)
        if cam is None: cam = (0, 0, 1, 0)
        z = cam[2] * (1 + S.get("punch", 0.02) * st["pulse"] * (1.35 if st["hook"] else 1) + 0.006 * st["on"]) * 1.04
        z = max(1.02, z)
        amp = S.get("shake", 1.4) * (min(st["on"], 1.2) + st["pulse"]) * (1.25 if st["hook"] else 1)
        rnd = random.Random(k); sx, sy = rnd.uniform(-1, 1) * amp, rnd.uniform(-1, 1) * amp
        if cam[3]: bg = bg.rotate(cam[3], resample=Image.BICUBIC, center=(self.SW / 2, self.SH / 2))
        cw, ch = self.SW / z, self.SH / z
        cx = min(max(self.SW / 2 + cam[0] + sx, cw / 2), self.SW - cw / 2)
        cy = min(max(self.SH / 2 + cam[1] + sy, ch / 2), self.SH - ch / 2)
        # Lanczos: when bg_size is larger than the output (supersampled presets) this is a proper
        # anti-aliased downscale; a bilinear resize of a low-res plate was the old "jaggy/blurry" look.
        fr = bg.convert("RGB").resize((self.W, self.H), Image.LANCZOS, reducing_gap=3.0 if cw > self.W * 1.5 else None,
                                      box=(cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)).convert("RGBA")
        if hasattr(self.preset, "overlay"): self.preset.overlay(fr, t, st)
        if self.title: self.draw_title(fr, t, st)
        self.draw_section_card(fr, t, st)
        self.draw_lyrics(fr, t, st, sx * self.W / self.SW, sy * self.H / self.SH)
        fo = S.get("fade_out", 2.0)
        if t > self.dur - fo:
            a = int(255 * min(1, (t - (self.dur - fo)) / max(0.05, fo)))
            fr.alpha_composite(Image.new("RGBA", fr.size, (0, 0, 0, a)))
        fi = float(S.get("fade_in", 0.6))
        if fi > 0 and t < fi:
            fr.alpha_composite(Image.new("RGBA", fr.size, (0, 0, 0, int(255 * (1 - t / fi)))))
        rgb = fr.convert("RGB")
        if S.get("safety", True): rgb = self.guard.apply(rgb)
        return rgb

def render_segment(job, a, b, out):
    ctx = Ctx(job); b = min(b, ctx.NF)
    enc = ["-c:v", "libx264", "-preset", job.get("x264_preset", "slow"), "-crf", str(job.get("crf", 16)),
           "-profile:v", "high", "-tune", job.get("x264_tune", "animation"), "-pix_fmt", "yuv420p",
           "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]
    if job.get("maxrate"): enc += ["-maxrate", job["maxrate"], "-bufsize", job.get("bufsize", job["maxrate"])]
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{ctx.W}x{ctx.H}", "-r", str(ctx.FPS), "-i", "-", "-an",
                           "-vf", "scale=out_color_matrix=bt709:flags=lanczos+accurate_rnd+full_chroma_int"] + enc + [out],
                          stdin=subprocess.PIPE)
    for k in range(a, b): ff.stdin.write(ctx.frame(k).tobytes())
    ff.stdin.close(); rc = ff.wait()
    if rc != 0: raise RuntimeError(f"ffmpeg segment exited {rc}")
    return ctx

def stills(job, times, outdir, prefix="frame"):
    ctx = Ctx(job); os.makedirs(outdir, exist_ok=True); paths = []
    for t in times:
        p = os.path.join(outdir, f"{prefix}_{t:07.2f}.png")
        ctx.guard = Guard()  # each still is independent; do not blend with the previous still
        ctx.frame(int(round(t * ctx.FPS))).save(p); paths.append(p)
    return paths
