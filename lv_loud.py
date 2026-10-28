"""Two-pass EBU R128 loudness normalization (ffmpeg loudnorm) for YouTube delivery.

YouTube plays back at about -14 LUFS integrated; louder uploads are turned down.
Pass 1 measures the source, pass 2 applies loudnorm with the measured values
(linear=true when the target is reachable without limiting), then resamples to 48 kHz.
The source file is only read, never written.
"""
import json, re, subprocess

DEFAULT_I, DEFAULT_TP, DEFAULT_LRA = -14.0, -1.0, 11.0

def _loudnorm_json(stderr):
    m = re.findall(r"\{[^{}]*\"input_i\"[^{}]*\}", stderr)
    if not m: raise RuntimeError("loudnorm produced no measurement")
    return json.loads(m[-1])

def measure(path, stream="a:0", I=DEFAULT_I, TP=DEFAULT_TP, LRA=DEFAULT_LRA, ss=None, t=None):
    """Return dict(I, TP, LRA, thresh, offset) of the audio in `path` (LUFS / dBTP / LU)."""
    cmd = ["ffmpeg", "-hide_banner", "-nostats"]
    if ss is not None: cmd += ["-ss", str(ss)]
    if t is not None: cmd += ["-t", str(t)]
    cmd += ["-i", path, "-map", f"0:{stream}", "-af", f"loudnorm=I={I}:TP={TP}:LRA={LRA}:print_format=json", "-f", "null", "-"]
    j = _loudnorm_json(subprocess.run(cmd, capture_output=True, text=True).stderr)
    return dict(I=float(j["input_i"]), TP=float(j["input_tp"]), LRA=float(j["input_lra"]),
                thresh=float(j["input_thresh"]), offset=float(j["target_offset"]))

def linear_ok(m, I=DEFAULT_I, TP=DEFAULT_TP):
    """loudnorm only stays linear if the gain needed doesn't push the peak over TP."""
    return m["TP"] + (I - m["I"]) <= TP

def filter_for(m, I=DEFAULT_I, TP=DEFAULT_TP, LRA=DEFAULT_LRA, sr=48000):
    """Second-pass filter string. LRA is raised to the measured LRA so linear mode is kept."""
    lra = max(LRA, min(50.0, round(m["LRA"] + 0.1, 1)))
    return (f"loudnorm=I={I}:TP={TP}:LRA={lra}:measured_I={m['I']}:measured_TP={m['TP']}:"
            f"measured_LRA={m['LRA']}:measured_thresh={m['thresh']}:offset={m['offset']}:"
            f"linear=true:print_format=summary,aresample={sr}:resampler=soxr")

def evaluate(final, I=DEFAULT_I, TP=DEFAULT_TP):
    """Warnings for a measured final mix: >1 LU off target, or true peak above TP."""
    w = []
    if abs(final["I"] - I) > 1.0: w.append(f"integrated {final['I']:.1f} LUFS is more than 1 LU from {I:g}")
    if final["TP"] > TP + 0.05: w.append(f"true peak {final['TP']:.1f} dBTP is above {TP:g}")
    return w

def parse_target(v):
    if v is None or str(v).lower() in ("off", "none", "false", "0"): return None
    x = float(v)
    if not -70 <= x <= -5: raise ValueError("--loudness must be between -70 and -5 LUFS, or 'off'")
    return x
