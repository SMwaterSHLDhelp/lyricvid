# Designing a lyric video

The toolkit will render whatever you describe. The design work is choosing a picture that belongs to this song and to no earlier video.

Open `docs/styles_log.md` first. If the new look could be mistaken for a row already there, change it. The ink / bone / orange HUD (`doompop`, `contextwindow`) is the look that already exists in the wild. Do not ship another one.

## Read the song

Write five lines before any code:

- Mood and genre, in concrete words (tender, harsh, nocturnal, civic, comic).
- Tempo, and whether the picture should feel slower than the beat.
- Three lyric images a stranger could draw (a prize on a shelf, a year on a calendar, a crowd).
- Where the words should sit: lower band, centre, two-line karaoke, stacked, or scattered.
- One motion idea (a line drawing itself, a slow drift, type sliding into a stack).

Then pick a mode.

## Mode A — one style for the whole song

Use this when the song is a mood more than a list of objects.

1. Palette. Two or three colours. One of them is the sung word. Check that the sung colour and the resting colour both clear roughly 3:1 on the background you actually draw. Sample the plate behind the word, not a spark on top of it.
2. Type. One lyric face, one title face, one mono face, each with a DejaVu or Liberation fallback. `upper`, `size`, `text_y`, `band`.
3. Layout and kinetic. `lower` + `wave` reads as a song. `stack` + `slide` reads as a poster. `karaoke` + `type` reads as a lyric video. `scatter` needs `jitter_rot` kept small and `ransom` only when the collage is the point.
4. Motion. `AudioFollow(0.6)` or `Slew` on anything that covers a lot of the frame. `punch` and `shake` stay small. `fade_in` is at least 0.8 on a light ground.
5. One word event. `word_hit(ctx, "boat", t)` or `ctx.word_events["boat"]` so a motif arrives with the lyric and then stays. It should not blink on every beat.

`presets/minimal.py` is the shortest legal preset. `presets/paperboats.py` is a finished one.

### Worked example: a quiet song about paper boats

Brief: slow, analog, indoor. The word "boat" is the motif. Not a HUD, not neon, not a grid.

Decisions: warm paper `(236, 224, 200)`, indigo ink `(28, 36, 64)`, sung word a dull bronze. Patrick Hand for the lyric, Instrument Serif for the title. Lower band, a small wave, almost no punch. Speckle is generated once and copied. Rain is a few slow strokes. When "boat" is sung, a small boat eases in and remains.

That preset is `presets/paperboats.py`. The same idea as data, with no drawing code, is `styles/postcard.json`.

Lint it:

```bash
python3 lyricvid.py lint --preset presets/paperboats.py
```

## Mode B — one scene per lyric line

Use this when each line can be acted out. This is the gold-standard shape: clean neon line-art with bloom on near-black, one warm accent and one cool accent, bold all-caps karaoke in the bottom third, key words in the accent, a glowing section title, objects that draw themselves on, a slow camera push, and a crossfade at every line change. No full-frame flash.

Workflow, in order:

1. Read the lyric file line by line. For each line, write the literal picture in a few words. "permits take a year" is a calendar and a clock, not an abstract texture. "a million minds" is a crowd and a count-up, not a particle field that merely feels large.
2. Create `scenes/<song>.py` (or a JSON spec with `"mode": "scenes"`).
3. Set `PALETTE`, `CROSSFADE` (0.7 is the default; the player will not go under 0.6), and `SECTION_TITLES` (short glowing labels, one per section).
4. Write a `draw(board, ctx, line, u, st)` per line, or name a `template`. `u` is 0 at the aligned start of the line and 1 at the end. Pass it to every primitive so the picture traces on, counts up, or swings in. Do not cut the drawing on a beat.
5. Stay inside `safe_stage` (about y 0.14–0.64). The renderer paints the lyric band underneath. Drawing the lyric line again inside the scene double-prints it.
6. On each rule, set `keywords` to the words that should wear the cool accent while they are part of the line. The active word still uses the warm sung colour.
7. Match rules with `contains` (a distinctive word), `section`, or `index`. Index wins, then contains, then section. An unmatched line falls through to the HUD template, which is a sign that a line was skipped.
8. Preview. The still for a line should show that line's objects and that line's words, after the crossfade has finished.

### Worked example: a civic, technical lyric

`examples/normaltech.txt` is original demo copy (do not paste someone else's lyric). The pictures:

| line | picture | keywords |
| --- | --- | --- |
| a tool spreads through the dark | rays and a node network | tool |
| a prize sits on the shelf by the bars | a medal on a shelf, a bar chart | prize, bars |
| permits take a year on the grid | a calendar, a clock, a short row of buildings | year |
| robots building robots | two robots, the smaller one drawing on later | robots |
| the curve bends and flattens | a diminishing-returns curve tracing itself | curve |
| a million minds stand in rows | silhouettes and a count-up to 1,000,000 | million |
| the log scrolls then holds | a terminal and HUD rings | log |
| one warm lamp stays lit | a lamp, rays, a swinging neon sign | lamp |

The file is `scenes/normaltech.py`. Section titles are "a tool", "the shelf", "build", "a million", "lamp". The lyric band is Archivo Black, bone type, amber for the sung word, cyan for keywords.

```bash
python3 lyricvid.py lint --preset scenes/normaltech.py
python3 lyricvid.py preview --preset lineart --scenes scenes/mysong.py
```

A scene file with no `class Preset` is wrapped automatically. `presets/lineart.py` is the loader for `--preset lineart --scenes ...`.

### Declarative scenes

`styles/desk.json` maps substrings of the lyric to template names. Templates: `rays`, `medal_bars`, `calendar`, `robots`, `curve`, `crowd`, `terminal`, `hud`, `sign`, `buildings`. Write Python when the line needs a composition the template does not have.

### Primitives

All of these live in `lv_art.py` and bloom through `Board`:

- marks: `arrow`, `sun_rays`, `network`, `board.label`, `board.text`, `board.count_up`
- figures: `person`, `crowd`, `robot`
- charts: `bar_chart`, `line_chart`, `diminish_curve`
- objects: `clock`, `calendar`, `shelf`, `medal`, `building`, `hud_rings`, `terminal`, `neon_sign`

`u` trims polylines (`partial`), reveals bars, and interpolates counters. A sign can take `swing` and `t` so it rocks slowly instead of popping.

## Shared rules

- Colour changes that cover the frame take at least 0.6 s. Scene changes already crossfade.
- Do not flash, invert, or cut to white or red on a beat.
- Grain, halftone, and paper speckle are static. A new noise field every frame flickers.
- Keep a margin. The camera pushes in; zoom is at least 1.02 so the crop stays inside the background.
- Words stay in their slots. Pop is vertical. Scale does not exceed 1 on x. If two words touch, the gap is too small or a glyph is scaled the wrong way.
- `python3 lyricvid.py lint --preset <path>` must pass (0 flashes, 0 red frames, contrast ok) before a full render.
- After the video is accepted, add a row to `docs/styles_log.md`: name, palette, type, layout, motion, and the lyric idea it was built for.

## Iteration loop

```bash
python3 lyricvid.py lint --preset path/to/style.py
python3 lyricvid.py stills --job <lint-work>/job.json --times 1.2,2.4
```

Look at the PNG. If the picture and the lyric disagree, the still landed in a crossfade or the rule matched the wrong line. If the words collide, the kinetic is scaling horizontally. If lint prints the safety guidance, the change it names is the one to make (slower fade, less red, higher contrast), not a second effect on top.
