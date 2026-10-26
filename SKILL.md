---
name: lyricvid
description: Turn a finished song (audio + known lyrics) into a beat-synced, word-accurate, photosensitive-safe lyric video. Invent a new visual style for each song, or illustrate each lyric line as its own scene. Use when asked for a lyric video, karaoke video, or music video for a generated or provided song.
---

# lyricvid

Single CLI: `lyricvid.py` in this folder. Stages are cached in a work dir.

The job is not "pick doompop". Read the song and invent the picture. The files in `presets/`, `scenes/`, and `styles/` are examples of the API. `docs/styles_log.md` lists looks that already exist. A new video has to be deliberately different from every row in that log, especially the ink / bone / orange HUD (`doompop`, `contextwindow`).

Two first-class modes:

1. **One style for the song** — a preset of about 50–150 lines, built from `lv_blocks.py`.
2. **One scene per lyric line** — a scene file. Each line gets a small illustration that acts the line out, crossfaded when the line changes. This is the mode to use when the lyrics are concrete (objects, numbers, places, machines). The reference shape is `scenes/normaltech.py`: near-black, amber and cyan line-art with bloom, bold all-caps karaoke in the bottom third, key words in the accent, glowing section titles, objects that draw on, a slow push-in, no full-frame flashes.

Read `docs/STYLE_GUIDE.md` and follow it. Record the finished look in `docs/styles_log.md`.

## Requirements

- ffmpeg + ffprobe on PATH (libx264, aac, libmp3lame).
- Full render: Python 3.11+ with torch, torchaudio, demucs, librosa, numpy, pillow. CPU torch is enough.
- Preview, lint, gallery, and `tests/test_lyricvid.py` need numpy, pillow, and ffmpeg only.
- Fonts: `python3 scripts/install_fonts.py`, or `--font-dir`. Search order is `--font-dir`, `LYRICVID_FONT_DIRS`, `fonts/`, then system fonts. Name a fallback in `STYLE["fonts"]`.

## Lyrics file

```
[verse]
first line
[chorus]
hook line
```

Known sung text only. Repeated sections written out in order.

## Commands

```
python3 lyricvid.py presets
python3 lyricvid.py lint --preset path/to/mystyle.py
python3 lyricvid.py preview --preset scenes/normaltech.py
python3 lyricvid.py gallery --out docs/gallery
python3 lyricvid.py run --audio song.mp3 --lyrics song.txt --preset path/to/mystyle.py \
    --title "Song Title" --bpm 132 --out videos/Song.mp4 --workers 4 --stills 8,24,40,70
python3 lyricvid.py run --audio song.mp3 --lyrics song.txt --preset lineart \
    --scenes path/to/scenes.py --title "Song Title" --out videos/Song.mp4
python3 lyricvid.py align --audio song.mp3 --lyrics song.txt --work /tmp/song_work
python3 lyricvid.py stills --job <work>/job.json --times 12,40,95
python3 lyricvid.py check --video Song.mp4 --audio song.mp3
```

`--preset` accepts a preset name, a `.py` path (`class Preset`, or a scene module), or a `.json` / `.yaml` spec. `--preset-opts key=value` overrides STYLE (repeatable, commas allowed). `--scenes` selects the scene file when the preset is `lineart`.

`lint` renders a synthetic clip and exits 1 on a flash or a contrast failure. Fix the preset until it passes. Do not deliver a video that fails `check`.

## Pipeline

1. Demucs htdemucs `--two-stems vocals`.
2. MMS_FA forced alignment of the known words to the vocal stem. 30 s emission chunks; a tail shorter than 1 s merges into the previous chunk.
3. Onset check. `gap` lines with |Δ| > 0.25 s are flagged `<-- check`.
4. Beat grid (fixed BPM phase-fit, or librosa) plus per-frame `rms`, `bass`, `mid`, `high`.
5. Parallel frame render. `lv_safety.Guard` clamps every frame.
6. Concat, AAC, trim to the audio duration.
7. Duration check and `lv_flash.py`. Goal: 0 flashes, 0 red-flash frames.

## How to design the video

Do this before writing pixels.

1. Read the lyrics, the BPM, and the mood. Note concrete nouns (a shelf, a year, a crowd, a lamp) and the section map.
2. Read `docs/styles_log.md`. Name the look you are refusing to repeat.
3. Choose a mode.
   - Concrete, line-by-line images, or the brief asks for illustrated scenes: write a scene file. For each lyric line, write down the object that line literally depicts, then a `draw` function. Match lines with `contains`, `section`, or `index`. List `keywords` (the words that should wear the accent) and `SECTION_TITLES`. Use `lv_art` primitives. Pass progress `u` into draw-on, trace, and count-up. Keep drawings in the upper two thirds (`safe_stage`). Crossfade stays ≥ 0.6 s. Camera is a slow push, already applied by `SceneShow`.
   - One atmosphere for the whole song: write a preset. Pick palette, type, layout, kinetic, and one motion idea. Use `lv_blocks`. Let audio move size or position through `AudioFollow` or `Slew` (0.6 s or slower on anything large). Bind one repeated lyric word to `word_hit` / `ctx.word_events`.
4. `python3 lyricvid.py lint --preset <path>`. Read the still it implies by running `stills` or `gallery` logic: open a frame and check that the sung line is readable and that the picture matches that line.
5. Iterate. Then append a row to `docs/styles_log.md` (palette, type, layout, motion, and what it must not be confused with).

`scenes/normaltech.py` is the line-art worked example. `presets/paperboats.py` is the whole-song worked example. `styles/desk.json` and `styles/postcard.json` are the no-Python versions.

## Preset API

```python
class Preset:
    DESCRIPTION = "one line"
    STYLE = dict(
        bg_size=(960, 540),
        fonts=dict(lyric=["Outfit[wght]@Bold", "DejaVuSans-Bold"],
                   title=["Outfit[wght]@Bold", "DejaVuSans-Bold"],
                   mono=["IBMPlexMono-Regular", "DejaVuSansMono"]),
        text=(230, 234, 240), sung=(255, 214, 120),
        layout="lower",   # lower, center, karaoke, scatter, stack
        kinetic="wave",   # pop, none, slide, type, scale, rotate, wave
        text_y=0.8, size=64, hook_size=76,
        band=0.4, unsung_alpha=0.4,
        punch=0.01, shake=0.6, fade_in=0.8,
    )
    def __init__(self, ctx): ...
    def background(self, t, st): ...   # RGBA at bg_size
    def camera(self, t, st): ...       # (dx, dy, zoom, rot)
    def overlay(self, img, t, st): ... # optional
```

`st` includes `t`, `k`, `dt`, `down`, `bar`, `bar_phase`, `sec`, `hook`, `pulse`, `on`, `rms`, `bass`, `mid`, `high`.

Pop only scales vertically. Horizontal scale is clamped to ≤ 1. Slots use unscaled widths. A highlighted word must not touch the next word.

Useful STYLE keys: `keyword`, `keywords`, `glow`, `stroke`, `shadow`, `section_card`, `section_hold`, `section_color`, `ransom` with `lyric_b` / `lyric_c`, `karaoke_ahead`, `lead`, `line_fade`, `title_card`, `title_mode`.

## Scene API

```python
DESCRIPTION = "..."
LYRICS = "examples/song.txt"   # optional, used by preview and gallery
CROSSFADE = 0.7
PALETTE = dict(bg=(6, 7, 11), line=(220, 226, 232), amber=(255, 176, 48), cyan=(72, 216, 226))
SECTION_TITLES = {"verse": "the shelf", "chorus": "build"}

def draw_shelf(board, ctx, line, u, st):
    x0, y0, x1, y1 = safe_stage(board)
    shelf(board, x0, y0 + 80, 280, u)
    medal(board, x0 + 80, y0 + 40, 26, u)

SCENES = [
    {"contains": "shelf", "draw": draw_shelf, "keywords": ["prize", "shelf"]},
    {"contains": "year", "template": "calendar", "keywords": ["year"]},
]
```

Match priority: `index`, then `contains`, then `section`, otherwise the HUD template. JSON `"mode": "scenes"` uses the same fields with `template` names from `lv_art.TEMPLATES` (`rays`, `medal_bars`, `calendar`, `robots`, `curve`, `crowd`, `terminal`, `hud`, `sign`, `buildings`).

The lyric band is drawn by the renderer, in the bottom third, all caps for this style. Do not also draw the lyric line inside the scene. Key words listed on the scene are drawn in `keyword` (cyan in the example). Section titles ease in and out; only the current section is shown.

Primitives (each takes a progress `u` for draw-on / trace / count-up): `arrow`, `sun_rays`, `building`, `person`, `crowd`, `robot`, `shelf`, `medal`, `bar_chart`, `line_chart`, `diminish_curve`, `clock`, `calendar`, `hud_rings`, `terminal`, `neon_sign`, `network`, plus `board.line`, `board.circle`, `board.rect`, `board.text`, `board.label`, `board.count_up`. `Board.finish` blooms the glow layer.

## Blocks

`lv_blocks.py`: `fill`, `linear_gradient`, `radial_gradient`, `aurora`, `paper`, `vignette`, `grain`, `scanlines`, `wobble`, `halftone`, `draw_grid`, `paint_sun`, `boxes`, `meters`, `Field`, `Slew`, `AudioFollow`, `word_hit`, `camera_still`, `camera_drift`, `soft_blob`.

Grain, halftone, and speckle should be static (seeded once), not a new random field every frame. Large colour or size changes go through a slew of at least 0.6 s.

## Photosensitivity

- Goal: 0 flashes and 0 red-flash frames. `lint` is the gate.
- No beat flashes, no full-frame inversion, no strobing opacity.
- Colour crossfades ≥ 0.6 s. Scene crossfade is forced to at least 0.6 s.
- Saturated red only as a small static mark. The guard clamps the red fraction and blends an opposing transition inside 20 frames.
- Light presets need `fade_in` ≥ 0.8 so the opening is not a white flash.
- Shake stays small. Zoom punches stay around 1–2%.

## Before delivering

- `onset_check.json`: listen to flagged lines. Fricatives (f, s, sh) often look 0.3–0.4 s "late" when the alignment is right.
- Last sung line sits on real vocal energy, not a silent tail.
- `check.json`: `duration_ok`, `flashes` 0, `red_flash_frames` 0.
- Stills: the lyric line is readable, words are separated, the picture matches the line, the section title does not cover the lyric.
- Ending fades. Do not cut mid-phrase.
- `docs/styles_log.md` has a new row.
