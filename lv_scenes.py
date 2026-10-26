"""Per-line scenes. One lyric line, one picture, crossfaded when the line changes.

A scene module is either:

  SCENES = [
      {"contains": "shelf", "draw": draw_shelf, "keywords": ["prize"], "title": "THE SHELF"},
      {"section": "chorus", "template": "robots", "keywords": ["robots"]},
      {"index": 0, "template": "rays"},
  ]

or a JSON spec (`"mode": "scenes"`) whose scenes name a template from `lv_art.TEMPLATES`.

`draw(board, ctx, line, u, st)` receives `u` in 0..1 across that line's aligned
start and end. Match priority is index, then contains, then section, then the
module default, then a quiet HUD.

The show crossfades for `crossfade` seconds (default 0.7, never under 0.6) so a
line change is a blend and not a cut.
"""
import math, os
import numpy as np
from PIL import Image
from lv_art import PALETTE, Board, TEMPLATES, template_hud
from lv_blocks import vignette

CROSSFADE = 0.7

def _norm(s):
    return str(s).lower()

def rules_from_module(mod):
    if hasattr(mod, "SCENES"):
        raw = mod.SCENES
        return list(raw() if callable(raw) else raw)
    if hasattr(mod, "scenes"):
        raw = mod.scenes
        return list(raw() if callable(raw) else raw)
    return []

def rules_from_spec(spec):
    return list(spec.get("scenes") or [])

def _draw_of(rule, default_palette):
    if rule.get("draw"): return rule["draw"]
    name = rule.get("template") or "hud"
    fn = TEMPLATES.get(name, template_hud)
    def draw(board, ctx, line, u, st, fn=fn):
        fn(board, ctx, line, u, st)
    return draw

def assign_scenes(lines, rules, default_draw=None):
    """Return a list of scene dicts, one per lyric line."""
    chosen = [None] * len(lines)
    for rule in rules:
        if "index" not in rule: continue
        i = int(rule["index"])
        if 0 <= i < len(lines) and chosen[i] is None:
            chosen[i] = rule
    for i, L in enumerate(lines):
        if chosen[i] is not None: continue
        text = _norm(L.get("text", ""))
        for rule in rules:
            needle = rule.get("contains")
            if needle and _norm(needle) in text:
                chosen[i] = rule
                break
    for i, L in enumerate(lines):
        if chosen[i] is not None: continue
        for rule in rules:
            if rule.get("section") and _norm(rule["section"]) == _norm(L.get("sec", "")):
                chosen[i] = rule
                break
    fallback = default_draw or template_hud
    out = []
    for i, L in enumerate(lines):
        rule = dict(chosen[i] or {"template": "hud"})
        if not rule.get("draw"):
            rule["draw"] = _draw_of(rule, None) if rule.get("template") else fallback
        rule["line"] = i
        out.append(rule)
    return out

def _keywords(rule, line):
    keys = []
    for src in (rule.get("keywords") or (),):
        keys.extend(src)
    return {str(k).lower().strip("!?,.\"'()…") for k in keys}

class SceneShow:
    """A preset. `module` is a Python scene file, or pass `spec` for JSON."""

    def __init__(self, ctx, module=None, spec=None):
        self.c = ctx
        self.module = module
        self.spec = spec or {}
        palette = dict(PALETTE)
        if module is not None and getattr(module, "PALETTE", None):
            palette.update(module.PALETTE)
        if self.spec.get("palette"):
            palette.update({k: tuple(v) for k, v in self.spec["palette"].items()})
        self.palette = palette
        rules = rules_from_module(module) if module is not None else rules_from_spec(self.spec)
        self.assigned = assign_scenes(ctx.lines, rules)
        ctx.line_keywords = {}
        for sc in self.assigned:
            ctx.line_keywords[sc["line"]] = _keywords(sc, ctx.lines[sc["line"]])
        titles = {}
        if module is not None and getattr(module, "SECTION_TITLES", None):
            titles.update(module.SECTION_TITLES)
        titles.update(self.spec.get("section_titles") or {})
        for sc in self.assigned:
            if sc.get("section_title"):
                titles.setdefault(ctx.lines[sc["line"]]["sec"], sc["section_title"])
        ctx.section_titles = {str(k).lower(): v for k, v in titles.items()}
        style = dict(
            bg_size=(960, 540),
            fonts=dict(lyric="ArchivoBlack-Regular", title="ArchivoBlack-Regular", mono="IBMPlexMono-Medium"),
            text=(236, 232, 220), sung=tuple(palette["amber"]), keyword=tuple(palette["cyan"]),
            keywords=(),
            size=54, hook_size=60, upper=True, layout="lower", kinetic="pop",
            pop=0.1, hook_slam=0.12, unsung_alpha=0.45,
            band=0.55, band_color=(4, 5, 8), band_radius=8,
            text_y=0.84, lead=0.08, stroke=0, shadow=True, shadow_px=3, glow=1,
            punch=0.012, shake=0.5, fade_in=0.8, fade_out=1.6,
            title_card=True, title_mode="top", title_size=64,
            section_card=True, section_hold=1.7, section_color=tuple(palette["amber"]),
            section_size=34,
        )
        if module is not None and getattr(module, "STYLE", None):
            extra = dict(module.STYLE)
            if "fonts" in extra: style["fonts"].update(extra.pop("fonts"))
            style.update(extra)
        if self.spec.get("style"):
            extra = dict(self.spec["style"])
            if "fonts" in extra: style["fonts"].update(extra.pop("fonts"))
            style.update(extra)
        self.STYLE = style
        self.crossfade = max(0.6, float(self.spec.get("crossfade") or getattr(module, "CROSSFADE", CROSSFADE) or CROSSFADE))
        desc = "Neon line-art scenes, one picture per lyric line."
        if module is not None and getattr(module, "DESCRIPTION", None): desc = module.DESCRIPTION
        if self.spec.get("description"): desc = self.spec["description"]
        self.DESCRIPTION = desc

    def line_at(self, t):
        lines = self.c.lines
        if not lines: return 0
        idx = 0
        for i, L in enumerate(lines):
            if t >= L["s"] - 0.05: idx = i
        return idx

    def _progress(self, li, t):
        L = self.c.lines[li]
        dur = max(0.35, float(L["e"]) - float(L["s"]))
        return min(1.0, max(0.0, (t - float(L["s"])) / dur))

    def _render(self, li, t, st):
        board = Board(self.c, self.palette)
        sc = self.assigned[li] if self.assigned else {"draw": template_hud}
        draw = sc.get("draw") or template_hud
        draw(board, self.c, self.c.lines[li], self._progress(li, t), st)
        im = board.finish(bloom=5)
        return vignette(im, 0.45)

    def camera(self, t, st):
        if not self.c.lines: return (0, 0, 1.0, 0)
        u = self._progress(self.line_at(t), t)
        # slow push-in across the line, no beat snap
        return (math.sin(t * 0.12) * 6, math.cos(t * 0.09) * 3, 1.0 + 0.05 * u, math.sin(t * 0.07) * 0.25)

    def background(self, t, st):
        if not self.c.lines:
            return self._render(0, t, st) if False else Board(self.c, self.palette).finish()
        li = self.line_at(t)
        cur = self._render(li, t, st)
        L = self.c.lines[li]
        age = t - float(L["s"])
        if li > 0 and 0 <= age < self.crossfade:
            prev = self._render(li - 1, t, st)
            u = age / self.crossfade
            a = np.asarray(prev, np.float32)
            b = np.asarray(cur, np.float32)
            return Image.fromarray(np.clip(a * (1 - u) + b * u, 0, 255).astype(np.uint8), "RGBA")
        return cur

def show_from_job(ctx):
    path = ctx.job.get("scenes")
    if not path:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scenes", "normaltech.py")
    from lv_render import load_preset
    # load_preset would wrap the scene module as a Preset and recurse. Load the module raw.
    mod = _load_module(path)
    if path.lower().endswith((".json", ".yml", ".yaml")):
        return SceneShow(ctx, spec=_read_spec(path))
    return SceneShow(ctx, module=mod)

def _load_module(path):
    import importlib.util
    path = os.path.abspath(path)
    name = "lyricvid_scenes_" + os.path.splitext(os.path.basename(path))[0]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def _read_spec(path):
    import json
    if str(path).lower().endswith(".json"):
        return json.load(open(path))
    try:
        import yaml
    except Exception as e:
        raise SystemExit("YAML scene specs need PyYAML, or use JSON") from e
    return yaml.safe_load(open(path))

def is_scene_module(mod):
    return any(hasattr(mod, name) for name in ("SCENES", "scenes", "PALETTE")) and not hasattr(mod, "Preset")
