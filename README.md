# lyricvid

Turn a finished song (audio plus the known lyrics) into a beat-synced, word-accurate lyric video: 1080p30 H.264 + AAC. A preset draws the picture; the toolkit aligns the words, renders frames, muxes the audio, and checks the result for duration and photosensitivity.

`lyricvid.py` is the only command. Each stage is cached in a work directory, so a re-run only repeats what changed.

## Install

Linux is the expected host. A CPU PyTorch build is enough. Use `python -m pip` (some venvs have no `pip` script).

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
.venv/bin/python -m pip install -r requirements.txt
```

Install the CPU wheels first. `demucs` depends on PyTorch; if torch is already installed, pip will not replace it with a CUDA wheel from PyPI.

You also need `ffmpeg` and `ffprobe` on `PATH`, with libx264, AAC, and libmp3lame. Frame rendering, audio decode, stem export, and the flash check all call them.

The first alignment downloads htdemucs (about 80 MB) and the torchaudio MMS_FA bundle (about 1.2 GB) into `~/.cache/torch/hub/checkpoints`.

### Fonts

Presets select a face by file-name substring (`ArchivoBlack-Regular`, `IBMPlexMono-Medium`, and so on), not by a hard-coded path. Directories are searched in this order:

1. Each `--font-dir DIR` (repeatable; earlier flags win).
2. `LYRICVID_FONT_DIRS`, split on the OS path separator (`:` on Linux and macOS, `;` on Windows).
3. The standard system and user font directories:
   - Linux: `/usr/share/fonts`, `/usr/local/share/fonts`, `~/.fonts`, `~/.local/share/fonts`, plus `XDG_DATA_HOME/fonts` and `XDG_DATA_DIRS` entries when those variables are set.
   - macOS: `/System/Library/Fonts`, `/Library/Fonts`, `~/Library/Fonts`.
   - Windows: `%WINDIR%\Fonts`, `%LOCALAPPDATA%\Microsoft\Windows\Fonts`.

Segment workers inherit `LYRICVID_FONT_DIRS`, so the same directories apply to every parallel encode. Install the faces a preset names (Google Fonts is a common source for Archivo Black and IBM Plex Mono), point `--font-dir` at the folder you unpacked them into, or change the `fonts` entries in the preset.

## Lyrics format

Plain text. A section tag is a bracketed line; the first word becomes the section name. One sung line per row. Blank lines are ignored. A tag with no following lines (an instrumental) is kept as a marker and is not aligned.

```
[verse]
first line of the verse
second line

[chorus]
hook line

[instrumental fade out]
```

Only the known sung text belongs in the file: no stage directions. Write repeated sections out in full, in the order they are sung. See `examples/example.txt`.

## CLI

```bash
# full pipeline
.venv/bin/python lyricvid.py run --audio song.mp3 --lyrics song.txt --preset doompop \
    --title "Song Title" --bpm 132 --out videos/Song.mp4 --workers 4 \
    --font-dir "$HOME/.local/share/fonts" --font-dir /opt/fonts \
    --stills 5,30,60,90,120,150

# alignment only (read the onset report before spending a render)
.venv/bin/python lyricvid.py align --audio song.mp3 --lyrics song.txt --work /tmp/song_work

# re-render a few frames after editing a preset
.venv/bin/python lyricvid.py stills --job /tmp/song_work/job.json --times 12,40.5,95

# 30 second test clip (no flash or duration gate)
.venv/bin/python lyricvid.py run --audio song.mp3 --lyrics song.txt --preset minimal \
    --out videos/Song.mp4 --test 40:70

# gate an existing video against the source audio
.venv/bin/python lyricvid.py check --video videos/Song.mp4 --audio song.mp3
```

`--font-dir` is accepted on `run`, `align`, `stills`, `check`, and the internal `_segment` worker. `run` and `stills` are the commands that open font files.

The work directory defaults to `<output dir>/_work_<name>/`. It holds `sep/` (Demucs stems), `lines.json` (word timings), `onset_check.json`, `beats.json`, `job.json`, `stills/sheet.png`, and `check.json`. `--realign` rebuilds alignment and beats. `--test START:END` writes `<name>_test<start>-<end>.mp4` and skips the flash and duration gate.

### What `run` does

1. **Separate.** Demucs `htdemucs --two-stems vocals` writes `vocals.wav` and `no_vocals.wav`.
2. **Align.** torchaudio MMS_FA (wav2vec2 CTC) force-aligns the normalised lyric words to the vocal stem, in 30 second emission chunks. Each word is `[word, start, end]`; each line has `s` / `e`.
3. **Onset check.** For each line, the strongest 10 ms RMS rise within ±0.5 s of the aligned start. `gap` lines (quiet before the line) are verifiable; `legato` lines follow continuous singing. A `gap` whose delta is larger than 0.25 s is printed with `<-- check`.
4. **Beats.** librosa onset envelope. With `--bpm`, a fixed grid is phase-fitted to that envelope (the right choice for generated music with a known tempo). Without it, librosa’s beat tracker estimates the tempo. Downbeat phase comes from low-band (kick) flux. A per-frame onset curve drives reactive motion.
5. **Render.** `lv_render.Ctx` draws `ceil(duration * fps)` frames so the picture is never short. Workers render segments and pipe raw frames to libx264 (CRF 21, yuv420p, by default).
6. **Mux.** Segments are concatenated, the source audio is encoded as AAC at 192 kbps, and `-t <audio duration>` trims both streams. `+faststart` is set.
7. **Check.** Stream durations against the source (±1 frame of video, 30 ms of audio), the WCAG flash analysis, file size, and a contact sheet when `--stills` is set.

## Presets

A preset is `presets/<name>.py` exporting `class Preset`. `STYLE` carries fonts, colours, sizes, `unsung_alpha`, `punch`, `shake`, `text_y`, `fade_out`, and `bg_size`. Hooks:

- `background(t, st)` returns an RGBA image at `bg_size`.
- `camera(t, st)` returns `(dx, dy, zoom, rot)`.
- `overlay(img, t, st)` is optional.

`st` is the beat state: beat index, time since the beat, downbeat flag, bar, section, hook flag, pulse, and onset. `ctx.word_events[word]` lists every sung start time of that word, so a scene can bind to words such as "click" or "accept".

- `minimal` is a dark field, centred karaoke, and a small beat zoom. Copy this to start a style.
- `doompop` is the "AI doom pop" look: ink `#0A0A0B`, bone `#EEE9DF` type, one signal orange `#FF4D12`. Archivo Black lyrics, IBM Plex Mono HUD, a hairline grid, an orange spark with a trail, and a BPM / bar / beat HUD with a rising risk meter. Sections are a prompt (intro), scrolling diffs (verse), accumulating diff blocks (pre-chorus), a button pressed on the beat (chorus), logs and a mask (bridge), and an idle UI (outro).

To make a preset, copy `presets/minimal.py` to `presets/<name>.py`, edit `STYLE` and `background`, and pass `--preset <name>`. Keep lyrics in the lower band (`text_y`) and leave the centre of the frame for the scene.

## Quality checks

Before calling a video done:

- Read `onset_check.json` and listen to lines flagged `<-- check`. A useful review is a table of at least ten timestamps: lyric, aligned time, onset.
- Confirm the last sung line sits on real vocal energy (about 1 s RMS of the vocal stem). If the aligner pushes words into a silent tail, that take dropped lyrics.
- `check.json`: `duration_ok` true, `flash.passed` true, `flashes` 0, `red_flash_frames` 0, and the file size inside the delivery budget.
- `stills/sheet.png`: lyrics readable, nothing clipped, title not sitting on the lyric line.
- The ending: the last few seconds of audio should sit well below the body of the song, and the picture fades to black over `fade_out` seconds.

`check` prints the same duration and flash report for a video you already rendered.

## Photosensitivity

`lv_flash.py` implements a simplified WCAG 2.3.1 / Harding area test. General and red flashes are both counted.

- A **transition** is a frame where more than 25% of the pixels change relative luminance by more than 0.1, and the darker of the two states is below 0.8.
- A **flash** is a pair of opposing transitions. More than 3 flashes in any 1 second window fails. The goal is 0.
- A **red flash** is more than 25% of the frame toggling into or out of saturated red (`R / (R+G+B) >= 0.8` and `R >= 0.3`). Any such frame fails.

Build presets so they never flash or invert on the beat. Colour changes should be crossfades of at least 0.6 s, at most once per bar. Avoid full-screen saturated red. Keep shake small (about 2 px at a 720p background) and zoom punches around 3% or less.

## Pitfalls

- Whisper word timestamps drift on sung and generated vocals. Align the known lyrics to the Demucs vocal stem instead.
- Fricative onsets (f, s, sh) make the energy check look about 0.3–0.4 s late when the alignment is actually right. Listen before moving a line.
- `round(duration * fps)`, or a beat array one frame short, yields a video about 0.03–0.04 s shorter than the audio. The renderer uses `ceil(duration * fps)`, clamps beat indices, and muxes with `-t`.
- Shake and zoom can produce a negative crop. The camera clamps the crop and keeps a base zoom.
- A uniform word "pop" collides with neighbouring words. Pop vertically only, and anchor every glyph to one baseline (`anchor="ls"` plus font metrics).
- Cream or light backgrounds make the lyric line hard to read. Put a dark band behind the text.
- Leave unsung words visible at about 30–40% opacity so a line does not jump as words appear. Layout is centred on the full line, not on the words sung so far.
- For generated songs, render longer than the target (about 10 s) and trim with a 5–7 s fade so the song never stops mid-phrase. Reject a take whose vocals end early or whose lyrics run past the trim.
- Copying a large finished file to a remote machine is the usual failure at the end. Leave outputs on the machine that built them unless someone asked for a copy.
