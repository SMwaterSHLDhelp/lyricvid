#!/usr/bin/env python3
"""lyricvid: song + lyrics -> beat-synced lyric/music video (1080p30 H.264/AAC).

  lyricvid.py run   --audio song.mp3 --lyrics song.txt --preset doompop --out out/Song.mp4 [--title T] [--bpm 132]
                    [--workers 4] [--test 30:60] [--stills 12,40.5,...]
  lyricvid.py align --audio song.mp3 --lyrics song.txt --work DIR      (Demucs + MMS_FA forced alignment + onset report)
  lyricvid.py stills --job DIR/job.json --times 10,20,30               (render single frames + contact sheet)
  lyricvid.py check --video out.mp4 --audio song.mp3                   (flash test + duration match)

Font lookup: repeatable --font-dir DIR and LYRICVID_FONT_DIRS (path-separator separated), then the
standard system and user font directories. Presets still select fonts by file-name substring.

Pipeline: Demucs vocal stem -> forced alignment of the KNOWN lyrics (wav2vec2 MMS_FA) -> onset check ->
beat grid (fixed-BPM phase fit or librosa) -> parallel frame rendering (preset) -> concat -> mux trimmed to
the exact audio duration -> WCAG flash check -> stills. Everything is cached in the work dir."""
import argparse, json, os, sys, math, subprocess, time
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import lv_audio, lv_align, lv_flash

def log(*a): print("[lyricvid]", *a, flush=True)

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
    pr = lambda sel: float(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", sel, "-show_entries",
                                                    "stream=duration", "-of", "csv=p=0", video]).decode().strip())
    res = dict(audio_src=lv_audio.duration(audio), video_stream=pr("v:0"), audio_stream=pr("a:0"),
               size_mb=round(os.path.getsize(video) / 1e6, 1))
    res["duration_ok"] = abs(res["video_stream"] - res["audio_src"]) <= 1 / 30 + 1e-3 and abs(res["audio_stream"] - res["audio_src"]) <= 0.03
    res["flash"] = lv_flash.check(video); return res

def contact_sheet(paths, out, cols=3, w=640):
    from PIL import Image, ImageDraw, ImageFont
    ims = [Image.open(p).convert("RGB").resize((w, w * 9 // 16)) for p in paths]
    rows = math.ceil(len(ims) / cols); sheet = Image.new("RGB", (cols * w, rows * w * 9 // 16), (0, 0, 0))
    for i, (im, p) in enumerate(zip(ims, paths)):
        ImageDraw.Draw(im).text((8, 6), os.path.basename(p).split("_")[-1][:-4] + "s", fill=(255, 255, 0))
        sheet.paste(im, ((i % cols) * w, (i // cols) * w * 9 // 16))
    sheet.save(out); return out

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    fonts = argparse.ArgumentParser(add_help=False)
    fonts.add_argument("--font-dir", action="append", default=None, metavar="DIR",
                       help="font directory to search (repeatable; before the defaults). Also LYRICVID_FONT_DIRS")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", parents=[fonts]); r.add_argument("--audio", required=True); r.add_argument("--lyrics", required=True)
    r.add_argument("--preset", default="minimal"); r.add_argument("--out", required=True); r.add_argument("--title", default="")
    r.add_argument("--bpm", type=float); r.add_argument("--workers", type=int, default=4); r.add_argument("--work")
    r.add_argument("--test", help="render only START:END seconds (no flash/duration gate)"); r.add_argument("--stills", default="")
    r.add_argument("--crf", type=int, default=21); r.add_argument("--realign", action="store_true")
    a = sub.add_parser("align", parents=[fonts]); a.add_argument("--audio", required=True); a.add_argument("--lyrics", required=True); a.add_argument("--work", required=True)
    s = sub.add_parser("stills", parents=[fonts]); s.add_argument("--job", required=True); s.add_argument("--times", required=True); s.add_argument("--outdir")
    c = sub.add_parser("check", parents=[fonts]); c.add_argument("--video", required=True); c.add_argument("--audio", required=True)
    g = sub.add_parser("_segment", parents=[fonts]); g.add_argument("job"); g.add_argument("a", type=int); g.add_argument("b", type=int); g.add_argument("out")
    A = ap.parse_args()
    import lv_render
    lv_render.configure_font_dirs(A.font_dir)

    if A.cmd == "_segment":
        lv_render.render_segment(json.load(open(A.job)), A.a, A.b, A.out); return
    if A.cmd == "align": do_align(A.audio, A.lyrics, A.work, True); return
    if A.cmd == "check": print(json.dumps(check(A.video, A.audio), indent=1)); return
    if A.cmd == "stills":
        job = json.load(open(A.job)); od = A.outdir or os.path.join(job["work"], "stills")
        ps = lv_render.stills(job, [float(x) for x in A.times.split(",")], od)
        log("sheet", contact_sheet(ps, os.path.join(od, "sheet.png"))); return

    # ---- run ----
    t0 = time.time(); name = os.path.splitext(os.path.basename(A.out))[0]
    work = A.work or os.path.join(os.path.dirname(os.path.abspath(A.out)), "_work_" + name); os.makedirs(work, exist_ok=True)
    audio = os.path.abspath(A.audio)
    do_align(audio, A.lyrics, work, A.realign)
    bj = os.path.join(work, "beats.json")
    if not os.path.exists(bj) or A.realign: json.dump(lv_audio.beats(audio, 30, A.bpm), open(bj, "w"))
    job = dict(audio=audio, lines=os.path.join(work, "lines.json"), beats=bj, preset=A.preset, title=A.title, work=work, crf=A.crf)
    jp = os.path.join(work, "job.json"); json.dump(job, open(jp, "w"), indent=1)
    dur = lv_audio.duration(audio); NF = int(math.ceil(dur * 30))
    a0, a1 = 0, NF
    if A.test: s0, s1 = map(float, A.test.split(":")); a0, a1 = int(s0 * 30), min(NF, int(s1 * 30))
    n = A.workers; step = math.ceil((a1 - a0) / n); segs = []; procs = []
    for i in range(n):
        sa, sb = a0 + i * step, min(a1, a0 + (i + 1) * step)
        if sa >= sb: continue
        o = os.path.join(work, f"seg{i}.mp4"); segs.append(o)
        procs.append(subprocess.Popen([sys.executable, __file__, "_segment", jp, str(sa), str(sb), o]))
    for p in procs:
        if p.wait() != 0: sys.exit("segment render failed")
    lst = os.path.join(work, "segs.txt"); open(lst, "w").write("".join(f"file '{s}'\n" for s in segs))
    out = A.out if not A.test else A.out.replace(".mp4", f"_test{int(a0/30)}-{int(a1/30)}.mp4")
    ss, tt = a0 / 30, (a1 - a0) / 30 if A.test else dur
    # exact duration: video has ceil(dur*fps) frames; -t trims both streams to the audio length
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-ss", str(ss), "-t", str(tt), "-i", audio,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", str(tt), "-movflags", "+faststart", out], check=True)
    for s in segs: os.remove(s)
    os.remove(lst)
    log("wrote", out, f"{time.time() - t0:.0f}s")
    if A.stills:
        ps = lv_render.stills(job, [float(x) for x in A.stills.split(",")], os.path.join(work, "stills"))
        log("sheet", contact_sheet(ps, os.path.join(work, "stills", "sheet.png")))
    if not A.test:
        res = check(out, audio); json.dump(res, open(os.path.join(work, "check.json"), "w"), indent=1)
        log(json.dumps(res))
        if not res["flash"]["passed"]: log("FLASH CHECK FAILED")
        if not res["duration_ok"]: log("DURATION MISMATCH")

if __name__ == "__main__": main()
