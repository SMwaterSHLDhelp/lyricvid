# Styles log

Every shipped or example look goes here so the next video can be chosen against it. Add a row when a new preset or scene file is rendered for a song. "Different" means a stranger could tell the stills apart with the sound off: palette, type, layout, and motion, not a renamed colour.

## Do not repeat

The ink / bone / signal-orange family is already the default people reach for. New work uses a different palette, a different type, and a different layout.

| name | palette | type | layout | motion | notes |
| --- | --- | --- | --- | --- | --- |
| doompop | ink `#0A0A0B`, bone `#EEE9DF`, orange `#FF4D12` | Archivo Black, IBM Plex Mono | lower band | grid, spark trail, HUD, beat punch | machine-UI scenes. The look to avoid. |
| contextwindow | same family | same | lower band | token meter, scrollback | a variant of doompop, not a new style |

## Examples already in the gallery

These are demos of the API. A song may reuse a *block*, not the whole row.

| name | palette | type | layout | motion | notes |
| --- | --- | --- | --- | --- | --- |
| minimal | near-black, bone, gold | DejaVu / system | lower | slow ring, small punch | smallest preset; a starting shape |
| synthwave | night blue, magenta grid, amber sun, cyan type | Orbitron | lower | perspective grid, striped sun | outlined lyric |
| lofi | warm paper, dark brown ink, dull red sung word | Caveat | lower | static speckle, scanlines, 2 px wobble, meter | handwriting |
| brutalist | off-white, black, one small red square | Anton, stacked | stack | words slide in, long fade-in | poster, almost still |
| aurora | very dark blue-green, white type | Outfit | center | slow colour drift, wave | keep the field dark so type stays readable |
| zine | newsprint, black, spot red | Syne / Anton / Bebas ransom | scatter | static halftone, small rotation | collage |
| starfield | navy, dust, gold sung word | Outfit | karaoke | slewed star size, slow drift | two lines |
| karaoke | navy, white, gold | Outfit | karaoke | type-on, small meter | clean lyric video |
| paperboats | warm sheet, indigo, bronze | Patrick Hand, Instrument Serif | lower | drift, a boat on the word "boat" | style-guide worked example |
| postcard | warm sheet, brown ink | Patrick Hand | center | drift, wave | JSON twin of the paper idea |
| normaltech | near-black, bone, amber, cyan | Archivo Black | lower third | line-art draw-on, 0.7 s crossfade, slow push-in | one scene per line; section cards; keyword accent |
| desk | same line-art palette | Archivo Black | lower third | template scenes | JSON scene spec |

## Shipped songs

| name | palette | type | layout | motion | notes |
| --- | --- | --- | --- | --- | --- |
| skeletoncrew | night purple gradient `#140A2A→#461E64`, pumpkin `#FF8C24`, slime `#82E854` (sung), moonlight `#F0EED0`, plum outlines `#1E0C2C` | Luckiest Guy (lyrics, plum stroke), Creepster (title, section cards) | lower band, rounded plum pill | flat cut-paper "sticker-book" cartoons, one acted-out scene per line, 0.8 s scene crossfade, characters bounce on beats, bar-length camera sway, drifting fog, gliding bats, ease-out-back pop-ins | `presets/skeletoncrew.py`, Skeleton Crew (Halloween house dance-pop, 124 BPM). Filled shapes, not line-art; not the doompop HUD. |
