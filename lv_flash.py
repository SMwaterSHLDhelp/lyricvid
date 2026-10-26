"""Photosensitivity check (WCAG 2.3.1 general + red flash, simplified area method).
A transition = >25% of the frame changes relative luminance by >0.1 (darker state <0.8).
A flash = a pair of opposing transitions. Fail if >3 flashes in any 1 s window.
Red: >25% of the frame toggling to/from saturated red (R/(R+G+B) >= 0.8)."""
import subprocess, numpy as np, json, sys

def check(path, w=320, h=180, fps=30):
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-i", path, "-vf", f"scale={w}:{h}", "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
    lin = lambda c: np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    prev = prevred = None; ev = []; red = []; md = []
    while True:
        b = p.stdout.read(w * h * 3)
        if len(b) < w * h * 3: break
        a = np.frombuffer(b, np.uint8).reshape(h, w, 3).astype(np.float32) / 255
        Y = 0.2126 * lin(a[..., 0]) + 0.7152 * lin(a[..., 1]) + 0.0722 * lin(a[..., 2])
        s = a.sum(2) + 1e-3; rd = (a[..., 0] / s >= 0.8) & (a[..., 0] >= 0.3)
        if prev is not None:
            dY = Y - prev; dark = np.minimum(Y, prev) < 0.8
            up, dn = ((dY > 0.1) & dark).mean(), ((dY < -0.1) & dark).mean()
            ev.append(1 if up > 0.25 else (-1 if dn > 0.25 else 0))
            red.append(bool((rd != prevred).mean() > 0.25)); md.append(float(abs(Y.mean() - prev.mean())))
        prev, prevred = Y, rd
    ev = np.array(ev); idx = np.nonzero(ev)[0] if len(ev) else np.array([], dtype=int); sg = ev[idx] if len(ev) else ev
    fl = [int(idx[i]) for i in range(1, len(idx)) if sg[i] != sg[i - 1]]
    mx = max([sum(1 for x in fl if s <= x < s + fps) for s in range(len(ev))] + [0])
    r = dict(frames=int(len(ev) + 1), transitions=int(len(idx)), flashes=len(fl), max_flashes_per_s=mx,
             red_flash_frames=int(sum(red)), mean_dY=round(float(np.mean(md)) if md else 0.0, 5),
             max_dY=round(float(np.max(md)) if md else 0.0, 4),
             passed=bool(mx <= 3 and sum(red) == 0))
    return r

if __name__ == "__main__":
    print(json.dumps(check(sys.argv[1]), indent=1))
