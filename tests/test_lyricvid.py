#!/usr/bin/env python3
"""Synthetic checks: alignment chunks, loudness normalization, the safety clamp, word spacing, and a flash/contrast pass per preset.

    python3 tests/test_lyricvid.py            # unit checks + every example preset
    python3 tests/test_lyricvid.py --quick    # unit checks and one frame of line-art
"""
import os, sys, tempfile, subprocess
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
os.chdir(HERE)

def test_chunks():
    from lv_align import emission_chunks
    rate = 16000
    # a tail under one second is merged into the previous chunk
    assert emission_chunks(rate * 30 + 8000) == [(0, rate * 30 + 8000)], emission_chunks(rate * 30 + 8000)
    # a tail of a full second stays its own chunk
    two = emission_chunks(rate * 30 + rate)
    assert len(two) == 2 and two[0] == (0, rate * 30) and two[1][1] - two[1][0] == rate
    assert emission_chunks(rate * 10) == [(0, rate * 10)]
    print("PASS chunks")

def test_guard():
    import numpy as np
    from PIL import Image
    from lv_flash import check
    from lv_safety import Guard
    w, h, n = 320, 180, 36
    raw = tempfile.mktemp(suffix=".mp4")
    clamped = tempfile.mktemp(suffix=".mp4")
    def encode(path, frames):
        ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                               "-s", f"{w}x{h}", "-r", "30", "-i", "-", "-an", "-c:v", "libx264", "-preset", "veryfast",
                               "-crf", "20", "-pix_fmt", "yuv420p", path], stdin=subprocess.PIPE)
        for im in frames: ff.stdin.write(im.tobytes())
        ff.stdin.close(); assert ff.wait() == 0, path
    strobe = [Image.new("RGB", (w, h), (255, 255, 255) if i % 2 == 0 else (0, 0, 0)) for i in range(n)]
    encode(raw, strobe)
    raw_flash = check(raw)
    assert raw_flash["flashes"] > 0, raw_flash
    guard = Guard()
    encode(clamped, [guard.apply(im) for im in strobe])
    safe = check(clamped)
    assert safe["flashes"] == 0 and safe["red_flash_frames"] == 0 and safe["passed"], safe
    assert guard.clamps > 0
    red = Guard()
    out = red.apply(Image.new("RGB", (w, h), (220, 10, 10)))
    arr = np.asarray(out).astype(np.float32) / 255.0
    s = arr.sum(2) + 1e-6
    frac = float(((arr[..., 0] / s >= 0.8) & (arr[..., 0] >= 0.3)).mean())
    assert frac <= 0.13, frac
    print("PASS guard", "raw_flashes", raw_flash["flashes"], "clamped", safe["flashes"], "clamps", guard.clamps)

def test_spacing():
    import numpy as np
    from PIL import Image
    from lv_preview import make_job
    from lv_render import Ctx
    work = tempfile.mkdtemp(prefix="lv-space-")
    job = make_job("minimal", work, seconds=3.2, size=(1280, 720),
                   opts={"hook_slam": 0.85, "pop": 0.55, "upper": True, "size": 90,
                         "hook_size": 120, "band": 0, "stroke": 4})
    ctx = Ctx(job)
    line = next(L for L in ctx.lines if "UNTIL" in L["text"].upper())
    until = next(w for w in line["words"] if w[0].upper() == "UNTIL")
    t = until[1] + 0.04
    li = ctx.lines.index(line)
    items, _sz, _hook, _mode = ctx.layout(li)
    fr = Image.new("RGBA", (ctx.W, ctx.H), (0, 0, 0, 0))
    ctx.draw_lyrics(fr, t, ctx.state(t), 0, 0)
    alpha = np.asarray(fr)[..., 3]
    bad = []
    for a, b in zip(items, items[1:]):
        if abs(a["y"] - b["y"]) > 10: continue
        # x-height band only, so a tall pop on the row above cannot fill the gap
        y0 = max(0, int(a["y"] - a["sz"] * 0.55))
        y1 = min(fr.height, int(a["y"] + max(8, a["sz"] * 0.12)))
        cols = [int(alpha[y0:y1, x].max()) for x in range(int(a["x"] + a["w"]) + 1, int(b["x"]))]
        clear = sum(1 for v in cols if v < 20)
        if clear < 4: bad.append((a["word"], b["word"], clear, cols))
    assert not bad, bad
    # the highlighted word is scaled vertically and the slot width is unchanged
    hi = next(it for it in items if it["word"].upper() == "UNTIL")
    kin = ctx._kinetic(hi, t, True, True)
    assert kin["sx"] == 1.0 and kin["sy"] > 1.05, kin
    print("PASS spacing", "sy", round(kin["sy"], 3))

def test_keywords_and_scenes():
    from lv_scenes import assign_scenes
    from lv_preview import make_job, lines_for
    lines = lines_for("scenes/normaltech.py", 8.0)
    rules = [
        {"contains": "shelf", "keywords": ["prize"], "template": "medal_bars"},
        {"contains": "robots", "keywords": ["robots"], "template": "robots"},
    ]
    # use the real module
    from lv_render import load_preset
    mod = load_preset("scenes/normaltech.py")
    assert mod.LYRICS and os.path.exists(mod.LYRICS)
    texts = [L["text"] for L in lines]
    assert any("shelf" in t for t in texts), texts
    assert len(lines) >= 8
    work = tempfile.mkdtemp(prefix="lv-scene-")
    job = make_job("scenes/normaltech.py", work, seconds=8.0, size=(640, 360))
    from lv_render import Ctx
    ctx = Ctx(job)
    assert ctx.S.get("section_card") is True
    # keyword image exists on the shelf line
    shelf = next(i for i, L in enumerate(ctx.lines) if "shelf" in L["text"])
    items, *_ = ctx.layout(shelf)
    assert any(it["is_kw"] and it["kw"] is not None for it in items), [it["word"] for it in items]
    # one frame renders
    ctx.frame(int(ctx.lines[shelf]["s"] * ctx.FPS) + 2)
    print("PASS scenes", "lines", len(lines), "keywords", sorted(ctx.line_keywords.get(shelf, [])))

def _one(name, kind, path):
    from lv_preview import evaluate, make_job
    work = os.path.join(tempfile.gettempdir(), "lyricvid-lint", name.replace("/", "_"))
    preset = name if kind == "preset" else path
    job = make_job(preset, work, size=(960, 540), title=name.upper())
    res = evaluate(job)
    return dict(name=name, passed=res["passed"], flashes=res["flash"].get("flashes"),
                red=res["flash"].get("red_flash_frames"), contrast=res["contrast"],
                clamps=res["clamps"], reason=res["contrast"].get("reason", ""))

def test_all_presets():
    from concurrent.futures import ProcessPoolExecutor, as_completed
    from lyricvid import preset_catalog
    rows = [r for r in preset_catalog() if not (r["kind"] == "preset" and r["name"] == "lineart")]
    print(f"lint {len(rows)} presets")
    fails = []
    with ProcessPoolExecutor(max_workers=min(4, len(rows))) as ex:
        futs = {ex.submit(_one, r["name"], r["kind"], r["path"]): r for r in rows}
        for fut in as_completed(futs):
            r = futs[fut]
            try:
                res = fut.result()
            except Exception as e:
                print("FAIL", r["name"], type(e).__name__, e)
                fails.append(r["name"]); continue
            flag = "PASS" if res["passed"] else "FAIL"
            print(f"{flag} {res['name']:16} flashes={res['flashes']} red={res['red']} "
                  f"contrast={res['contrast'].get('median_sung')} clamps={res['clamps']} {res['reason']}")
            if not res["passed"]: fails.append(res["name"])
    assert not fails, fails
    print("PASS all presets", len(rows))

def test_loudness():
    """Quiet synthetic song -> remux at -14 LUFS: source untouched, sync kept, target and peak met."""
    import hashlib, json, lv_loud
    d = tempfile.mkdtemp()
    wav, vid, out = (os.path.join(d, n) for n in ("song.wav", "v.mp4", "out.mp4"))
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "sine=f=220:d=12:sample_rate=44100",
                    "-f", "lavfi", "-i", "anoisesrc=d=12:a=0.05:r=44100", "-filter_complex", "[0][1]amix=2,volume=0.3",
                    "-c:a", "pcm_s24le", wav], check=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "color=c=gray:s=160x90:r=30:d=12",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", vid], check=True)
    md5 = hashlib.md5(open(wav, "rb").read()).hexdigest()
    assert lv_loud.parse_target("off") is None and lv_loud.parse_target("-16") == -16.0
    assert lv_loud.evaluate(dict(I=-14.4, TP=-1.2)) == [] and len(lv_loud.evaluate(dict(I=-16.0, TP=-0.5))) == 2
    r = subprocess.run([sys.executable, "lyricvid.py", "remux", "--video", vid, "--audio", wav, "--out", out, "--no-flash"])
    assert r.returncode == 0
    assert hashlib.md5(open(wav, "rb").read()).hexdigest() == md5, "source audio modified"
    res = json.load(open(os.path.join(d, "out_check.json")))
    L = res["loudness"]
    assert res["duration_ok"], res
    assert L["source"]["I"] < -20 and abs(L["final"]["I"] + 14) <= 1 and L["final"]["TP"] <= -0.95 and not L["warnings"], L
    sr = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=sample_rate,codec_name",
                                  "-of", "csv=p=0", out]).decode().strip()
    assert sr == "aac,48000", sr
    off = os.path.join(d, "off.mp4")
    subprocess.run([sys.executable, "lyricvid.py", "remux", "--video", vid, "--audio", wav, "--out", off, "--no-flash", "--loudness", "off"], check=True)
    Lo = json.load(open(os.path.join(d, "off_check.json")))["loudness"]
    assert Lo["target"] is None and abs(Lo["final"]["I"] - Lo["source"]["I"]) < 0.5, Lo
    print("PASS loudness", L["source"]["I"], "->", L["final"]["I"], "LUFS, TP", L["final"]["TP"])

def main():
    test_chunks(); test_guard(); test_spacing(); test_keywords_and_scenes(); test_loudness()
    if "--quick" not in sys.argv:
        test_all_presets()
    print("OK")

if __name__ == "__main__":
    main()
