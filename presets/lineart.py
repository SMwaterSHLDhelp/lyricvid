"""Loader for the neon line-art show. The pictures live in a scenes file.

    lyricvid.py run --preset lineart --scenes scenes/normaltech.py ...
    lyricvid.py preview --preset scenes/normaltech.py

`scenes/normaltech.py` is the worked example: one illustrated scene per line.
"""
import os
LYRICS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples", "normaltech.txt")

class Preset:
    DESCRIPTION = "Neon line-art scenes (amber + cyan). Use --scenes to swap the scene file. Default: scenes/normaltech.py."

    def __new__(cls, ctx):
        from lv_scenes import show_from_job
        return show_from_job(ctx)
