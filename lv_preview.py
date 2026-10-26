"""Synthetic preview: a generated click track, fake alignment, no Demucs and no MMS.

Used by `lyricvid.py preview`, `lint`, and `gallery`, and by the flash tests.
"""
import json, os
from lv_align import parse_lyrics
from lv_audio import analyze_signal, synth_audio, write_wav
from lv_render import load_preset
from lv_safety import GUIDANCE, contrast_summary

def generic_lines(seconds=3.2):
    """Short lines, including the adjacent words NAME and UNTIL."""
    rows = [
        ("verse", "lights drift over the empty room", 0.28, 1.12),
        ("chorus", "say my NAME UNTIL the night", 1.22, 2.25),
        ("bridge", "fold a paper boat", 2.38, 3.05),
    ]
    out = []
    for sec, text, t0, t1 in rows:
        if t0 >= seconds - 0.05: continue
        t1 = min(t1, seconds - 0.02)
        words = text.split()
        step = max(0.12, (t1 - t0) / len(words))
        ws = []
        for i, w in enumerate(words):
            a = round(t0 + i * step, 3)
            b = round(min(t1, a + step * 0.9), 3)
            ws.append([w, a, max(a + 0.12, b)])
        out.append(dict(sec=sec, text=text, words=ws, s=ws[0][1], e=ws[-1][2]))
    return out

def pace_lyrics(path, seconds, lead=0.28, tail=0.18):
    rows = parse_lyrics(path)
    if not rows: return generic_lines(seconds)
    usable = max(0.8, seconds - lead - tail)
    slot = usable / len(rows)
    out = []
    for i, (sec, text) in enumerate(rows):
        t0 = lead + i * slot
        t1 = min(seconds - 0.02, t0 + slot * 0.9)
        words = text.split() or ["…"]
        step = max(0.08, (t1 - t0) / len(words))
        ws = []
        for j, w in enumerate(words):
            a = round(t0 + j * step, 3)
            b = round(min(t1, a + step * 0.88), 3)
            ws.append([w, a, max(a + 0.1, b)])
        out.append(dict(sec=sec, text=text, words=ws, s=ws[0][1], e=ws[-1][2]))
    return out

def lyric_source(preset):
    """A scene module can point at a lyric file via LYRICS. Otherwise the generic lines are used."""
    try:
        mod = load_preset(preset)
    except Exception:
        return None
    return getattr(mod, "LYRICS", None)

def lines_for(preset, seconds):
    src = lyric_source(preset)
    if src and os.path.exists(src):
        return pace_lyrics(src, seconds)
    return generic_lines(seconds)

def default_seconds(preset):
    src = lyric_source(preset)
    if src: return 8.0
    return 3.0

def make_job(preset, work, seconds=None, size=(960, 540), bpm=108, title="PREVIEW", opts=None, scenes=None, fps=30):
    os.makedirs(work, exist_ok=True)
    if seconds is None: seconds = default_seconds(preset)
    y, sr = synth_audio(seconds=seconds, bpm=bpm)
    wav = os.path.join(work, "synth.wav")
    write_wav(wav, y, sr)
    lines = lines_for(preset if not scenes else scenes, seconds)
    analysis = analyze_signal(y, sr, fps, bpm, dur=seconds)
    json.dump(lines, open(os.path.join(work, "lines.json"), "w"), indent=1)
    json.dump(analysis, open(os.path.join(work, "beats.json"), "w"))
    job = dict(audio=os.path.abspath(wav), lines=os.path.join(work, "lines.json"),
               beats=os.path.join(work, "beats.json"), preset=preset, title=title, work=work,
               width=int(size[0]), height=int(size[1]), fps=fps, crf=30, x264_preset="veryfast",
               preset_opts=opts or {}, maxrate="8M")
    if scenes: job["scenes"] = os.path.abspath(scenes)
    json.dump(job, open(os.path.join(work, "job.json"), "w"), indent=1)
    return job

def gallery_time(lines, lead=0.35, settle=0.0):
    """A moment inside one sung line, after the picture has settled.

    `lead` is how early the next line is cued (type-on hides words that have
    not started, so the still has to land before that cue). `settle` is how
    long a scene crossfade takes; the still waits that out so the frame is one
    picture, not a blend of two.
    """
    if not lines: return 0.4
    best_w, best_t = -1.0, float(lines[0]["s"]) + 0.2
    for i, L in enumerate(lines):
        s, e = float(L["s"]), float(L["e"])
        cue = float(lines[i + 1]["s"]) - lead - 0.04 if i + 1 < len(lines) else e - 0.04
        start = s + max(float(settle), 0.12)
        end = min(e - 0.04, cue)
        width = end - start
        if width > best_w:
            best_w = width
            best_t = start + max(0.0, width) * 0.7
    return round(best_t, 2)

def _type_snap(lines, t, lead, kinetic_time):
    """Land type-on just after a word has fully revealed, before the next one starts."""
    if not lines: return t
    for i, L in enumerate(lines):
        if not (float(L["s"]) - 0.05 <= t <= float(L["e"]) + 0.05): continue
        cue = float(lines[i + 1]["s"]) - lead - 0.04 if i + 1 < len(lines) else float(L["e"]) - 0.04
        end = min(float(L["e"]) - 0.04, cue)
        words = L.get("words") or []
        snapped = None
        for j, w in enumerate(words):
            st = float(w[1])
            done = st + max(0.08, kinetic_time) - 0.02
            nxt = float(words[j + 1][1]) - 0.04 if j + 1 < len(words) else end
            if done <= nxt and done <= end and done >= float(L["s"]):
                snapped = min(done, nxt - 0.01, end)
        if snapped is not None: return round(snapped, 2)
    return t

def gallery_time_for(job):
    """Read the preset's lead and scene crossfade, then pick a still time."""
    from lv_render import Ctx
    ctx = Ctx(job)
    lead = float(ctx.S.get("lead", 0.35))
    settle = float(getattr(ctx.preset, "crossfade", 0.0) or 0.0)
    t = gallery_time(ctx.lines, lead=lead, settle=settle)
    if ctx.S.get("kinetic") == "type":
        t = _type_snap(ctx.lines, t, lead, float(ctx.S.get("kinetic_time", 0.32)))
    return t

def evaluate(job):
    """Render the whole synthetic clip in-process and run the flash and contrast gates."""
    from lv_flash import check
    from lv_render import render_segment
    video = os.path.join(job["work"], "preview.mp4")
    ctx = render_segment(job, 0, 10 ** 9, video)
    flash = check(video)
    contrast = contrast_summary(ctx.contrast_samples)
    flash_ok = bool(flash.get("passed") and flash.get("flashes", 1) == 0 and flash.get("red_flash_frames", 1) == 0)
    ok = bool(flash_ok and contrast["ok"])
    return dict(preset=job["preset"], video=video, flash=flash, contrast=contrast,
                clamps=ctx.guard.clamps, red_limits=ctx.guard.red_limits,
                passed=ok, guidance=None if ok else GUIDANCE)
