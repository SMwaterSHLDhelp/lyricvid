---
name: lyricvid
description: Turn a finished song (audio + known lyrics) into a beat-synced, word-accurate, photosensitive-safe lyric/music video (1080p30 H.264+AAC). Use when asked for a lyric video, karaoke video or music video for a generated or provided song.
---

# lyricvid: audio + lyrics + style preset → music video

Single CLI: `lyricvid.py` (in this folder). Every stage is cached in a work dir, so re-runs only redo what changed.

## Requirements / installs (Linux box, CPU is fine)
- ffmpeg + ffprobe on PATH (libx264, aac, libmp3lame).
- Python 3.11+ venv with: `torch torchaudio` (CPU builds OK), `demucs`, `librosa`, `numpy`, `pillow`.
  ```
  python -m venv dm && dm/bin/python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
  dm/bin/python -m pip install demucs librosa pillow numpy
  ```
  (Some venvs have no `bin/pip`; always use `python -m pip`.)
- First run downloads htdemucs (~80 MB) and torchaudio MMS_FA (~1.2 GB, cached in `~/.cache/torch/hub/checkpoints`).
- Fonts: presets look up TTFs/OTFs by file name (e.g. ArchivoBlack-Regular, IBMPlexMono-Medium). Search order is each `--font-dir` (repeatable), then `LYRICVID_FONT_DIRS` (path-separator separated), then the standard system and user font directories (`/usr/share/fonts`, `/usr/local/share/fonts`, `~/.fonts`, `~/.local/share/fonts` on Linux; the usual Library/Fonts and Windows Fonts dirs elsewhere). Install the faces a preset names, or edit the preset.

## Lyrics file format
Plain text, section tags in brackets, one sung line per row, blank lines ignored:
```
[verse]
first line
[chorus]
...
[instrumental fade out]   <- tags with no lines are fine
```
Only the KNOWN sung text belongs here: no stage directions, and repeated sections written out in full in sung order.

## Usage
```
# full pipeline
dm/bin/python lyricvid.py run --audio song.mp3 --lyrics song.txt --preset doompop \
    --title "Song Title" --bpm 132 --out /path/videos/Song.mp4 --workers 4 \
    --stills 5,30,60,90,120,150
# only alignment (inspect onset report before rendering)
dm/bin/python lyricvid.py align --audio song.mp3 --lyrics song.txt --work /tmp/song_work
# re-render a few frames after editing a preset (fast iteration)
dm/bin/python lyricvid.py stills --job <work>/job.json --times 12,40,95
# render a 30s test clip
... run ... --test 40:70
# gate an existing video
dm/bin/python lyricvid.py check --video Song.mp4 --audio song.mp3
```
Work dir defaults to `<out dir>/_work_<name>/` and holds `sep/` (stems), `lines.json` (word timings), `onset_check.json`, `beats.json`, `job.json`, `stills/sheet.png` and `check.json`.
`--realign` forces alignment and beats to be redone.

## Pipeline steps
1. **Separate**: Demucs htdemucs `--two-stems vocals` → `vocals.wav`, `no_vocals.wav`.
2. **Align**: torchaudio MMS_FA (wav2vec2 CTC) forced alignment of the normalised known lyric words to the vocal stem (emissions in 30s chunks). Output is per-word `[word, start, end]` and per-line `s/e`.
3. **Onset check**: per line, the strongest 10ms RMS rise within ±0.5s of the aligned start. `gap` lines (silence before) are verifiable, `legato` lines are not. Lines flagged `<-- check` (gap and |Δ|>0.25s) need a listen.
4. **Beats**: librosa onset envelope. With `--bpm`, a fixed grid is phase-fitted (best for generated music with a known tempo); otherwise librosa beat_track. Downbeat phase comes from the low-band (kick) flux. A per-frame onset curve is included for reactive motion.
5. **Render**: `lv_render.Ctx` renders `ceil(dur*fps)` frames (so the video is never short). Parallel segments, each piped to libx264 (CRF 21, yuv420p).
6. **Mux**: concat segments, add the audio as AAC 192k, `-t <audio duration>` on both, `+faststart`.
7. **Check**: video and audio stream durations vs. the source (±1 frame), WCAG flash analysis (`lv_flash.py`), file size, and a contact sheet of stills.

## Presets (`presets/<name>.py`)
A preset exposes `class Preset(ctx)` with `STYLE` (fonts, colours, sizes, `unsung_alpha`, `punch`, `shake`, `text_y`, `fade_out`, `bg_size`) and hooks: `background(t, st)`, `camera(t, st) -> (dx, dy, zoom, rot)`, optional `overlay(img, t, st)`.
`st` = beat state (beat index, time since beat, downbeat, bar, section, hook flag, pulse, onset).
`ctx.word_events[word]` lists the sung start times of every word, so visuals can bind to words ("click", "accept").
- `minimal`: dark background, centred karaoke lines, gentle beat zoom. A template.
- `doompop`: "AI doom pop / Claude-pop" code-rendered look. Ink #0A0A0B, bone #EEE9DF type, a single signal orange #FF4D12. Archivo Black lyrics, IBM Plex Mono HUD. Hairline grid, orange spark with trail, HUD (BPM/BAR/BEAT + a rising risk meter), downbeat reframes. Section scenes: prompt typing (intro), scrolling diffs (verse), accumulating diff blocks (pre-chorus), giant button pressed on beats with rings (chorus), logs plus a smiley mask (bridge), idle UI (outro).
To make a new style, copy `minimal.py` and edit. Keep text in the lower band (`text_y`) and leave the centre for the scene.

## Quality checks (do all before delivering)
- Read `onset_check.json` and listen to or spot-check flagged lines. Make a table of ≥10 timestamps: lyric, aligned time, onset.
- Verify the last sung line is aligned to real vocal energy (1s RMS of the vocal stem). If the aligner pushes lines into a silent tail, the take dropped lyrics: pick another take.
- `check.json`: `duration_ok` true, `flash.passed` true with 0 flashes and 0 red-flash frames, size under budget.
- Look at `stills/sheet.png`: readable lyrics, nothing off-frame, title not overlapping lyrics.
- Ending: audio fades naturally (last 5s RMS well below the body), and the video fades to black over `fade_out` s.

## Photosensitivity (WCAG 2.3.1 / Harding)
- `lv_flash.py` counts a transition when >25% of the frame changes relative luminance by >0.1 and the darker state is <0.8. A flash is a pair of opposing transitions. Limit: ≤3/s. The goal is 0.
- Never flash or invert on beats. Do colour changes as ≥0.6s crossfades, at most once per bar.
- Avoid saturated full-screen red. Keep shake moderate (≤2px at 720p bg) and zoom punches ≤3%.

## Pitfalls learned
- Whisper word timestamps are unreliable on sung/generated vocals. Use forced alignment of the known lyrics to the Demucs vocal stem.
- Fricative onsets (f/s/sh) make the energy check read ~0.3–0.4s "late" even when alignment is right. Verify by ear before moving lines.
- A frame count of `round(dur*fps)` or a beat array one frame short gives a video 0.03–0.04s shorter than the audio. Render `ceil(dur*fps)` frames, clamp beat indices, mux with `-t`.
- Shake and zoom can produce negative crop boxes. Clamp them and keep a base zoom (~1.06).
- Word "pop" scaling collides with neighbours: pop vertically only, and anchor glyphs on a shared baseline (`anchor="ls"`, font metrics).
- Light/cream backgrounds hurt lyric readability. Put a dark band behind the text.
- Show unsung words dimmed (30–40%) so lines don't jump off-centre while being revealed.
- For generated songs: render longer than the target (e.g. +10s) and trim with a 5–7s fade so the song never cuts off. Reject takes whose vocals end early or whose lyrics run past the trim point.
- Large file copies to a remote laptop can fail. Keep outputs on the build machine unless asked.
