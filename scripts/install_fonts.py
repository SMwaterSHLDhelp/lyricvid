#!/usr/bin/env python3
"""Download the Google Fonts the example presets ask for.

    python3 scripts/install_fonts.py            # into ./fonts
    python3 scripts/install_fonts.py --dir DIR

The renderer also searches --font-dir, LYRICVID_FONT_DIRS, and the system font
folders. Every preset names a fallback (DejaVu Sans, DejaVu Serif, Liberation)
so a missing download still renders.

Files are the SIL Open Font License releases from github.com/google/fonts.
Upstream OFL.txt sits next to each family in that repo. Variable fonts are
loaded by Pillow; a name like Orbitron[wght]@Bold picks the Bold instance.
"""
import argparse, os, urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://github.com/google/fonts/raw/main/"

# (filename, repo path). Filename is what presets search for.
FONTS = [
    ("ArchivoBlack-Regular.ttf", "ofl/archivoblack/ArchivoBlack-Regular.ttf"),
    ("IBMPlexMono-Regular.ttf", "ofl/ibmplexmono/IBMPlexMono-Regular.ttf"),
    ("IBMPlexMono-Medium.ttf", "ofl/ibmplexmono/IBMPlexMono-Medium.ttf"),
    ("Anton-Regular.ttf", "ofl/anton/Anton-Regular.ttf"),
    ("BebasNeue-Regular.ttf", "ofl/bebasneue/BebasNeue-Regular.ttf"),
    ("Monoton-Regular.ttf", "ofl/monoton/Monoton-Regular.ttf"),
    ("PatrickHand-Regular.ttf", "ofl/patrickhand/PatrickHand-Regular.ttf"),
    ("InstrumentSerif-Regular.ttf", "ofl/instrumentserif/InstrumentSerif-Regular.ttf"),
    ("Orbitron[wght].ttf", "ofl/orbitron/Orbitron[wght].ttf"),
    ("Caveat[wght].ttf", "ofl/caveat/Caveat[wght].ttf"),
    ("Syne[wght].ttf", "ofl/syne/Syne[wght].ttf"),
    ("Outfit[wght].ttf", "ofl/outfit/Outfit[wght].ttf"),
    ("LibreBaskerville[wght].ttf", "ofl/librebaskerville/LibreBaskerville[wght].ttf"),
]

FALLBACKS = """
Preferred file                  Used by            Fallback if missing
ArchivoBlack-Regular            doompop, line-art  DejaVuSans-Bold
IBMPlexMono-Medium              HUD / mono         DejaVuSansMono
Orbitron[wght]@Bold             synthwave          DejaVuSans-Bold
Caveat[wght]@Bold               lofi               DejaVuSans
Anton-Regular                   brutalist          DejaVuSans-Bold
LibreBaskerville[wght]@Bold     aurora             DejaVuSerif-Bold
Syne[wght]@ExtraBold            zine               DejaVuSans-Bold
BebasNeue-Regular               zine (alt)         DejaVuSans-Bold
Outfit[wght]@Bold               karaoke, starfield DejaVuSans-Bold
PatrickHand-Regular             paperboats         DejaVuSans
InstrumentSerif-Regular         paperboats titles  DejaVuSerif
Monoton-Regular                 optional display   DejaVuSans-Bold
"""

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=os.path.join(HERE, "fonts"))
    A = ap.parse_args()
    os.makedirs(A.dir, exist_ok=True)
    print(FALLBACKS)
    for name, rel in FONTS:
        dest = os.path.join(A.dir, name)
        if os.path.exists(dest) and os.path.getsize(dest) > 1000:
            print("keep", name); continue
        url = BASE + urllib.request.quote(rel)
        print("get ", name)
        urllib.request.urlretrieve(url, dest)
    print("fonts in", A.dir)

if __name__ == "__main__":
    main()
