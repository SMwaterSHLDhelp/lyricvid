"""Declarative presets.

A style file composes blocks (no Python). A scene file (`"mode": "scenes"`)
maps lyric lines to line-art templates.

    {
      "description": "Warm paper, centred handwriting",
      "style": {"layout": "center", "kinetic": "wave", "text": [40, 28, 22],
                "fonts": {"lyric": "PatrickHand-Regular", "title": "PatrickHand-Regular",
                          "mono": "IBMPlexMono-Regular"}},
      "background": {"block": "paper", "tint": [236, 220, 196]},
      "camera": {"block": "drift", "drift": 8},
      "overlay": [{"block": "vignette", "amount": 0.35}]
    }
"""
import json, os, types
from lv_blocks import (AudioFollow, Field, aurora, camera_drift, camera_still, draw_grid,
                       fill, grain, linear_gradient, paint_sun, paper, radial_gradient,
                       scanlines, vignette, wobble)
from lv_scenes import SceneShow

def _read(path):
    if str(path).lower().endswith(".json"):
        return json.load(open(path))
    try:
        import yaml
    except Exception as e:
        raise SystemExit(f"{path} is YAML. Install PyYAML, or save the spec as JSON.") from e
    return yaml.safe_load(open(path))

def _color(v, default):
    if v is None: return default
    return tuple(v)

class BlockPreset:
    def __init__(self, ctx, spec):
        self.c = ctx
        self.spec = spec
        self.audio = AudioFollow(0.6, ctx.FPS)
        style = dict(spec.get("style") or {})
        fonts = dict(style.get("fonts") or {})
        fonts.setdefault("lyric", "DejaVuSans-Bold")
        fonts.setdefault("title", fonts["lyric"])
        fonts.setdefault("mono", "DejaVuSansMono")
        style["fonts"] = fonts
        style.setdefault("bg_size", (960, 540))
        self.STYLE = style
        self.DESCRIPTION = spec.get("description", "declarative style")
        bg = spec.get("background") or {"block": "solid", "color": [10, 10, 14]}
        self._stars = None
        if bg.get("block") == "stars":
            self._stars = Field(ctx.SW if hasattr(ctx, "SW") else style["bg_size"][0],
                                ctx.SH if hasattr(ctx, "SW") else style["bg_size"][1],
                                int(bg.get("count", 80)), seed=int(bg.get("seed", 1)))

    def camera(self, t, st):
        cam = self.spec.get("camera") or {}
        kind = cam.get("block", "still")
        if kind == "drift":
            return camera_drift(t, drift=float(cam.get("drift", 10)), rot=float(cam.get("rot", 0.3)),
                                zoom=float(cam.get("zoom", 1.0)))
        return camera_still()

    def _paint(self, t, st):
        w, h = self.STYLE.get("bg_size", (self.c.SW, self.c.SH))
        # Ctx sets SW from STYLE after init. Use STYLE.
        w, h = int(self.STYLE["bg_size"][0]), int(self.STYLE["bg_size"][1])
        bg = self.spec.get("background") or {"block": "solid"}
        kind = bg.get("block", "solid")
        a = self.audio(st)
        if kind == "paper":
            im = paper(w, h, _color(bg.get("tint"), (236, 220, 196)), speckle=int(bg.get("speckle", 12)), seed=int(bg.get("seed", 1)))
        elif kind == "aurora":
            cols = [tuple(c) for c in bg.get("colors", [(12, 18, 36), (18, 32, 48), (24, 16, 40)])]
            im = aurora(w, h, t, cols, speed=float(bg.get("speed", 0.07)))
        elif kind == "gradient":
            im = linear_gradient(w, h, _color(bg.get("c0"), (10, 12, 20)), _color(bg.get("c1"), (20, 16, 28)),
                                vertical=bg.get("vertical", True))
        elif kind == "radial":
            im = radial_gradient(w, h, _color(bg.get("c0"), (20, 16, 28)), _color(bg.get("c1"), (6, 6, 10)))
        elif kind == "stars":
            im = fill(w, h, _color(bg.get("color"), (4, 6, 12)))
            if self._stars is None:
                self._stars = Field(w, h, int(bg.get("count", 80)), seed=1)
            self._stars.w, self._stars.h = w, h
            self._stars.draw(im, t, color=tuple(bg.get("star", (230, 230, 240))), react=a["high"] * 0.5)
        elif kind == "grid":
            im = linear_gradient(w, h, _color(bg.get("sky0"), (10, 0, 24)), _color(bg.get("sky1"), (28, 8, 36)))
            paint_sun(im, w * 0.5, h * float(bg.get("horizon", 0.42)) - 20, int(bg.get("sun", 70)),
                      _color(bg.get("sun_color"), (255, 170, 60)))
            draw_grid(im, t, _color(bg.get("line"), (255, 70, 160)), horizon=float(bg.get("horizon", 0.46)),
                      speed=float(bg.get("speed", 0.18)))
        else:
            im = fill(w, h, _color(bg.get("color"), (10, 10, 14)))
        for ov in self.spec.get("overlay") or []:
            k = ov.get("block")
            if k == "vignette": im = vignette(im, float(ov.get("amount", 0.5)))
            elif k == "grain": im = grain(im, int(ov.get("amount", 10)), seed=int(ov.get("seed", 2)))
            elif k == "scanlines": im = scanlines(im, alpha=int(ov.get("alpha", 30)), gap=int(ov.get("gap", 4)))
            elif k == "wobble": im = wobble(im, t, amp=float(ov.get("amp", 1.5)))
        return im

    def background(self, t, st):
        return self._paint(t, st)

def load_spec(path):
    data = _read(path)
    if not isinstance(data, dict):
        raise SystemExit(f"{path} should be a JSON object")
    if data.get("mode") == "scenes":
        class Preset(SceneShow):
            DESCRIPTION = data.get("description", os.path.basename(path))
            def __init__(self, ctx, data=data):
                SceneShow.__init__(self, ctx, spec=data)
    else:
        class Preset(BlockPreset):
            DESCRIPTION = data.get("description", os.path.basename(path))
            def __init__(self, ctx, data=data):
                BlockPreset.__init__(self, ctx, data)
    mod = types.ModuleType("lyricvid_spec_" + os.path.splitext(os.path.basename(path))[0])
    mod.Preset = Preset
    mod.DESCRIPTION = Preset.DESCRIPTION
    return mod
