#!/usr/bin/env python3
"""lyricvid: song + lyrics -> a lyric video (1080p30 H.264/AAC).

Presets are examples. The agent that uses this repo writes a new one per song
(a Python preset, a JSON style, or a per-line scene file). See SKILL.md.

  lyricvid.py presets
  lyricvid.py run    --audio song.mp3 --lyrics song.txt --preset doompop --out out.mp4
                     [--title T] [--bpm 132] [--preset-opts layout=center] [--scenes scenes/x.py]
  lyricvid.py preview --preset synthwave [--seconds 3] [--preset-opts text=#fff]
  lyricvid.py lint   --preset scenes/normaltech.py          (preview + flash + contrast, exit 1 on failure)
  lyricvid.py gallery --out docs/gallery
  lyricvid.py align  --audio song.mp3 --lyrics song.txt --work DIR
  lyricvid.py stills --job DIR/job.json --times 10,20,30
  lyricvid.py check  --video out.mp4 --audio song.mp3

Font lookup: repeatable --font-dir, then LYRICVID_FONT_DIRS, then bundled fonts/,
then the system font directories. scripts/install_fonts.py fetches the faces
the examples name. Missing faces fall back to DejaVu or Liberation.
"""
import argparse, glob, json, math, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import lv_audio, lv_align, lv_flash
from lv_safety import GUIDANCE

def log(*a): print("[lyricvid]", *a, flush=True)

def parse_opts(items):
    """Repeatable --preset-opts key=value. Values are JSON when they parse, else strings. #rrggbb is a colour."""
    out = {}
    if not items: return out
    blobs = []
    for item in items:
        if item is None: continue
        blobs.extend(__import__("re").split(r",(?=[A-Za-z_][A-Za-z0-9_]*=)", str(item)))
    for blob in blobs:
        blob = blob.strip()
        if not blob: continue
        if blob.startswith("{"):
            out.update(json.loads(blob)); continue
        if "=" not in blob:
            raise SystemExit(f"--preset-opts expected key=value, got {blob!r}")
        k, v = blob.split("=", 1)
        v = v.strip()
        if v.startswith("#") and len(v) in (4, 7):
            h = v[1:]
            if len(h) == 3: h = "".join(c * 2 for c in h)
            out[k.strip()] = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
            continue
        try: out[k.strip()] = json.loads(v)
        except Exception: out[k.strip()] = v
    return out

def preset_catalog():
    """Example presets, scene files, and declarative specs."""
    rows = []
    for folder, kind in (("presets", "preset"), ("scenes", "scenes"), ("styles", "spec")):
        d = os.path.join(HERE, folder)
        if not os.path.isdir(d): continue
        for path in sorted(glob.glob(os.path.join(d, "*"))):
            base = os.path.basename(path)
            if base.startswith("_") or base.endswith(".pyc"): continue
            if folder == "presets" and not base.endswith(".py"): continue
            if folder == "scenes" and not base.endswith(".py"): continue
            if folder == "styles" and not base.lower().endswith((".json", ".yml", ".yaml")): continue
            name = os.path.splitext(base)[0]
            rel = os.path.relpath(path, HERE)
            desc = ""
            try:
                from lv_render import load_preset
                mod = load_preset(rel if folder != "presets" else name)
                desc = getattr(mod, "DESCRIPTION", "") or getattr(getattr(mod, "Preset", None), "DESCRIPTION", "")
            except Exception as e:
                desc = f"(failed to import: {e})"
            rows.append(dict(name=name, kind=kind, path=rel, description=desc))
    return rows

def do_align(audio, lyrics, work, force=False):
    os.makedirs(work, exist_ok=True); out = os.path.join(work, "lines.json")
    if os.path.exists(out) and not force: return json.load(open(out))
    voc, _ = lv_audio.separate(audio, work)
    lines = lv_align.force_align(voc, lv_align.parse_lyrics(lyrics))
    json.dump(lines, open(out, "w"), indent=1)
    rep = lv_align.onset_check(voc, lines); json.dump(rep, open(os.path.join(work, "onset_check.json"), "w"), indent=1)
    for r in rep:
        flag = "  <-- check" if r["kind"] == "gap" and abs(r["delta"]) > 0.25 else ""
        log(f"{r['s']:7.2f} onset {r['onset']:7.2f} ({r['delta']:+.2f}) {r['kind']:6s} {r['text'][:50]}{flag}")
    return lines

def check(video, audio):
    pr = lambda sel: float(subprocess_duration(video, sel))
    res = dict(audio_src=lv_audio.duration(audio), video_stream=pr("v:0"), audio_stream=pr("a:0"),
               size_mb=round(os.path.getsize(video) / 1e6, 1))
    res["duration_ok"] = abs(res["video_stream"] - res["audio_src"]) <= 1 / 30 + 1e-3 and abs(res["audio_stream"] - res["audio_src"]) <= 0.03
    res["flash"] = lv_flash.check(video)
    return res

def subprocess_duration(video, sel):
    import subprocess
    return subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", sel, "-show_entries",
                                    "stream=duration", "-of", "csv=p=0", video]).decode().strip()

def contact_sheet(paths, out, cols=3, w=640):
    from PIL import Image, ImageDraw
    ims = [Image.open(p).convert("RGB").resize((w, w * 9 // 16)) for p in paths]
    rows = math.ceil(len(ims) / cols) or 1
    sheet = Image.new("RGB", (cols * w, rows * w * 9 // 16), (0, 0, 0))
    for i, (im, p) in enumerate(zip(ims, paths)):
        ImageDraw.Draw(im).text((8, 6), os.path.basename(p).replace(".png", ""), fill=(255, 220, 80))
        sheet.paste(im, ((i % cols) * w, (i // cols) * w * 9 // 16))
    sheet.save(out); return out

def targets_for(preset, scenes, all_presets):
    if all_presets:
        rows = []
        for row in preset_catalog():
            if row["kind"] == "preset" and row["name"] == "lineart":
                continue  # same show as scenes/normaltech.py
            rows.append(row)
        return rows
    path = scenes or preset
    return [dict(name=os.path.splitext(os.path.basename(path))[0], kind="one", path=path, description="")]

def run_preview(row, outdir, seconds, opts, size, strict):
    from lv_preview import evaluate, make_job
    name = row["name"]
    work = os.path.join(outdir, name)
    preset = row["path"]
    scenes = None
    if row["kind"] == "preset":
        preset = name
    job = make_job(preset, work, seconds=seconds, size=size, opts=opts, scenes=scenes, title=name.upper())
    res = evaluate(job)
    res["name"] = name
    brief = dict(name=name, passed=res["passed"], flashes=res["flash"].get("flashes"),
                 red=res["flash"].get("red_flash_frames"), contrast=res["contrast"].get("median_sung"),
                 clamps=res["clamps"], video=res["video"])
    log(json.dumps(brief))
    if strict and not res["passed"]:
        log(res["contrast"].get("reason", ""))
        log(GUIDANCE)
    return res

def do_gallery(outdir, opts):
    from lv_preview import gallery_time_for, make_job
    from lv_render import stills
    os.makedirs(outdir, exist_ok=True)
    paths = []
    for row in targets_for(None, None, True):
        name = row["name"]
        work = os.path.join(outdir, "_work", name)
        preset = name if row["kind"] == "preset" else row["path"]
        job = make_job(preset, work, size=(1280, 720), opts=opts, title=name.upper(), fps=30)
        t = gallery_time_for(job)
        stills(job, [t], outdir, prefix=name)
        # stills names frame as prefix_time; rename to name.png
        src = os.path.join(outdir, f"{name}_{t:07.2f}.png")
        dst = os.path.join(outdir, f"{name}.png")
        if os.path.exists(src): os.replace(src, dst)
        paths.append(dst)
        log("still", dst)
    if paths:
        contact_sheet(paths, os.path.join(outdir, "sheet.png"), cols=4, w=480)
        log("sheet", os.path.join(outdir, "sheet.png"))
    return paths

def fail_flash(res):
    flash = res.get("flash") or {}
    if flash.get("passed") and flash.get("flashes", 0) == 0 and flash.get("red_flash_frames", 0) == 0:
        return False
    log("FLASH CHECK FAILED")
    log(GUIDANCE)
    return True

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    fonts = argparse.ArgumentParser(add_help=False)
    fonts.add_argument("--font-dir", action="append", default=None, metavar="DIR",
                       help="font directory to search (repeatable; before the defaults). Also LYRICVID_FONT_DIRS")
    opt = argparse.ArgumentParser(add_help=False)
    opt.add_argument("--preset-opts", action="append", default=[], metavar="KEY=VALUE",
                     help="override a STYLE key (repeatable). Colours as #rrggbb. Example: layout=center,kinetic=wave")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", parents=[fonts, opt]); r.add_argument("--audio", required=True); r.add_argument("--lyrics", required=True)
    r.add_argument("--preset", default="minimal"); r.add_argument("--out", required=True); r.add_argument("--title", default="")
    r.add_argument("--bpm", type=float); r.add_argument("--workers", type=int, default=4); r.add_argument("--work")
    r.add_argument("--test", help="render only START:END seconds (no flash/duration gate)"); r.add_argument("--stills", default="")
    r.add_argument("--crf", type=int, default=21); r.add_argument("--realign", action="store_true")
    r.add_argument("--scenes", help="per-line scene file (.py or .json) used by the lineart preset")
    a = sub.add_parser("align", parents=[fonts]); a.add_argument("--audio", required=True); a.add_argument("--lyrics", required=True); a.add_argument("--work", required=True)
    s = sub.add_parser("stills", parents=[fonts]); s.add_argument("--job", required=True); s.add_argument("--times", required=True); s.add_argument("--outdir")
    c = sub.add_parser("check", parents=[fonts]); c.add_argument("--video", required=True); c.add_argument("--audio", required=True)
    p = sub.add_parser("presets", parents=[fonts]); p.add_argument("--json", action="store_true")
    pv = sub.add_parser("preview", parents=[fonts, opt])
    pv.add_argument("--preset", default="minimal"); pv.add_argument("--all", action="store_true")
    pv.add_argument("--seconds", type=float); pv.add_argument("--out", default="")
    pv.add_argument("--width", type=int, default=960); pv.add_argument("--height", type=int, default=540)
    pv.add_argument("--scenes", default="")
    ln = sub.add_parser("lint", parents=[fonts, opt])
    ln.add_argument("--preset", default="minimal"); ln.add_argument("--all", action="store_true")
    ln.add_argument("--seconds", type=float); ln.add_argument("--out", default="")
    ln.add_argument("--width", type=int, default=960); ln.add_argument("--height", type=int, default=540)
    ln.add_argument("--scenes", default="")
    gal = sub.add_parser("gallery", parents=[fonts, opt]); gal.add_argument("--out", default=os.path.join(HERE, "docs", "gallery"))
    g = sub.add_parser("_segment", parents=[fonts]); g.add_argument("job"); g.add_argument("a", type=int); g.add_argument("b", type=int); g.add_argument("out")
    A = ap.parse_args()
    import lv_render
    lv_render.configure_font_dirs(getattr(A, "font_dir", None))

    if A.cmd == "_segment":
        lv_render.render_segment(json.load(open(A.job)), A.a, A.b, A.out); return
    if A.cmd == "align": do_align(A.audio, A.lyrics, A.work, True); return
    if A.cmd == "check":
        res = check(A.video, A.audio); print(json.dumps(res, indent=1))
        if fail_flash(res) or not res["duration_ok"]: sys.exit(1)
        return
    if A.cmd == "presets":
        rows = preset_catalog()
        if A.json: print(json.dumps(rows, indent=1))
        else:
            for row in rows:
                print(f"{row['name']:16} {row['kind']:7} {row['description']}")
        return
    if A.cmd == "stills":
        job = json.load(open(A.job)); od = A.outdir or os.path.join(job["work"], "stills")
        ps = lv_render.stills(job, [float(x) for x in A.times.split(",")], od)
        log("sheet", contact_sheet(ps, os.path.join(od, "sheet.png"))); return
    if A.cmd in ("preview", "lint"):
        outdir = A.out or os.path.join(os.getcwd(), "_preview")
        opts = parse_opts(A.preset_opts)
        rows = targets_for(A.preset, A.scenes or None, A.all)
        if A.scenes and not A.all:
            rows = [dict(name=os.path.splitext(os.path.basename(A.scenes))[0], kind="scenes", path=A.scenes, description="")]
        elif not A.all:
            rows = [dict(name=A.preset, kind="one", path=A.preset, description="")]
        bad = 0
        for row in rows:
            res = run_preview(row, outdir, A.seconds, opts, (A.width, A.height), strict=(A.cmd == "lint"))
            if not res["passed"]: bad += 1
        if bad:
            log(f"{bad} preset(s) failed the flash or contrast gate")
            sys.exit(1)
        return
    if A.cmd == "gallery":
        do_gallery(A.out, parse_opts(A.preset_opts)); return

    # ---- run ----
    import subprocess
    t0 = time.time(); name = os.path.splitext(os.path.basename(A.out))[0]
    work = A.work or os.path.join(os.path.dirname(os.path.abspath(A.out)), "_work_" + name); os.makedirs(work, exist_ok=True)
    audio = os.path.abspath(A.audio)
    do_align(audio, A.lyrics, work, A.realign)
    bj = os.path.join(work, "beats.json")
    if not os.path.exists(bj) or A.realign: json.dump(lv_audio.beats(audio, 30, A.bpm), open(bj, "w"))
    preset = A.scenes if A.scenes else A.preset
    job = dict(audio=audio, lines=os.path.join(work, "lines.json"), beats=bj, preset=preset, title=A.title,
               work=work, crf=A.crf, preset_opts=parse_opts(A.preset_opts))
    if A.scenes: job["scenes"] = os.path.abspath(A.scenes)
    jp = os.path.join(work, "job.json"); json.dump(job, open(jp, "w"), indent=1)
    dur = lv_audio.duration(audio); NF = int(math.ceil(dur * 30))
    a0, a1 = 0, NF
    if A.test: s0, s1 = map(float, A.test.split(":")); a0, a1 = int(s0 * 30), min(NF, int(s1 * 30))
    n = A.workers; step = math.ceil((a1 - a0) / max(1, n)); segs = []; procs = []
    for i in range(n):
        sa, sb = a0 + i * step, min(a1, a0 + (i + 1) * step)
        if sa >= sb: continue
        o = os.path.join(work, f"seg{i}.mp4"); segs.append(o)
        procs.append(subprocess.Popen([sys.executable, __file__, "_segment", jp, str(sa), str(sb), o]))
    for p_ in procs:
        if p_.wait() != 0: sys.exit("segment render failed")
    lst = os.path.join(work, "segs.txt"); open(lst, "w").write("".join(f"file '{s}'\n" for s in segs))
    out = A.out if not A.test else A.out.replace(".mp4", f"_test{int(a0/30)}-{int(a1/30)}.mp4")
    ss, tt = a0 / 30, (a1 - a0) / 30 if A.test else dur
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-ss", str(ss), "-t", str(tt), "-i", audio,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", str(tt), "-movflags", "+faststart", out], check=True)
    for s_ in segs: os.remove(s_)
    os.remove(lst)
    log("wrote", out, f"{time.time() - t0:.0f}s")
    if A.stills:
        ps = lv_render.stills(job, [float(x) for x in A.stills.split(",")], os.path.join(work, "stills"))
        log("sheet", contact_sheet(ps, os.path.join(work, "stills", "sheet.png")))
    if not A.test:
        res = check(out, audio); json.dump(res, open(os.path.join(work, "check.json"), "w"), indent=1)
        log(json.dumps(res))
        if fail_flash(res) or not res["duration_ok"]:
            if not res["duration_ok"]: log("DURATION MISMATCH")
            sys.exit(1)

if __name__ == "__main__": main()
