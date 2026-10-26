"""Forced alignment of KNOWN lyrics to the vocal stem (torchaudio MMS_FA, wav2vec2 CTC).
Whisper word timestamps drift badly on fast/gang/sung vocals; forced alignment of the real
lyric text is far more reliable. Lines are then checked against vocal onset energy."""
import re, numpy as np
from lv_audio import load_mono

NUM = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six", "7": "seven",
       "8": "eight", "9": "nine"}

def parse_lyrics(path):
    """Lyric file with [section] tags. Returns [(section, line)]. Tags like [instrumental ...] are skipped."""
    out, sec = [], "intro"
    for raw in open(path):
        l = raw.strip()
        if not l: continue
        if l.startswith("["):
            sec = l.strip("[]").split()[0].lower(); continue
        out.append((sec, l))
    return out

def norm(w):
    w = w.lower().replace("’", "'")
    w = "".join(NUM.get(c, c) for c in w)
    return re.sub(r"[^a-z]", "", w)

def emission_chunks(n_samples, rate=16000, chunk_s=30, min_tail=None):
    """Chunk boundaries for MMS emissions.

    A final piece shorter than `min_tail` samples (default: 1 second) is merged into
    the previous chunk. A tail under a second used to be sent to the model on its own
    and the aligner crashed."""
    if n_samples <= 0: return []
    if min_tail is None: min_tail = rate
    C = int(rate * chunk_s)
    starts = list(range(0, int(n_samples), C))
    if len(starts) > 1 and int(n_samples) - starts[-1] < min_tail: starts.pop()
    ends = starts[1:] + [int(n_samples)]
    return list(zip(starts, ends))

def force_align(vocals, lyric_lines):
    import torch
    from torchaudio.pipelines import MMS_FA as bundle
    model = bundle.get_model(with_star=False).eval(); tok = bundle.get_tokenizer(); aligner = bundle.get_aligner()
    a = load_mono(vocals, 16000); wav = torch.from_numpy(a)[None]
    with torch.inference_mode():
        chunks = emission_chunks(wav.shape[1])
        em = torch.cat([model(wav[:, s0:s1])[0][0] for s0, s1 in chunks])
    ratio = wav.shape[1] / 16000 / em.shape[0]
    words, owner = [], []
    for li, (_, line) in enumerate(lyric_lines):
        for w in line.split():
            n = norm(w)
            if n: words.append(n); owner.append((li, w))
    spans = aligner(em, tok(words))
    lines = []
    for li, (sec, line) in enumerate(lyric_lines):
        ws = [[owner[i][1], round(spans[i][0].start * ratio, 3), round(spans[i][-1].end * ratio, 3)]
              for i in range(len(words)) if owner[i][0] == li]
        if ws: lines.append(dict(sec=sec, text=line, words=ws, s=ws[0][1], e=ws[-1][2]))
    return clean_silence(vocals, lines)

def clean_silence(vocals, lines, thr=-40.0, maxw=1.2):
    """CTC alignment can smear a word across a silent tail (e.g. the last word of a song stretched
    20s into an instrumental outro). Trim word ends to the last voiced 10ms frame, and move words
    that sit entirely in silence to just after the previous word."""
    import numpy as np
    from lv_audio import load_mono
    y = load_mono(vocals, 16000); h = 160
    db = 20 * np.log10(np.sqrt(np.convolve(y ** 2, np.ones(h) / h, "same")[::h]) + 1e-9)
    voiced = lambda a, b: np.nonzero(db[int(a * 100):max(int(a * 100) + 1, int(b * 100))] > thr)[0]
    prev = 0.0
    for L in lines:
        for w in L["words"]:
            v = voiced(w[1], w[2])
            if len(v) == 0:                       # entirely silent: relocate after previous word
                nv = voiced(prev, w[1]); s0 = prev + 0.05 if len(nv) == 0 else prev + nv[0] / 100 + 0.0
                w[1] = round(max(prev + 0.02, min(s0, w[1])), 3); w[2] = round(w[1] + 0.4, 3)
            else:
                w[1] = float(round(w[1] + v[0] / 100, 3)); w[2] = round(min(w[1] + maxw * 4, w[1] + (v[-1] - v[0]) / 100 + 0.05), 3)
            w[2] = float(max(w[2], w[1] + 0.12)); w[1] = float(w[1]); prev = w[2]
        L["s"], L["e"] = L["words"][0][1], L["words"][-1][2]
    return lines

def onset_check(vocals, lines):
    """For each line: strongest vocal energy rise within +-0.5 s of its start, and the level before/after.
    'gap' lines (quiet before) are verifiable; 'legato' lines follow continuous singing."""
    a = load_mono(vocals, 16000)
    e = 20 * np.log10(np.sqrt(np.convolve(a ** 2, np.ones(400) / 400, "same")[::160]) + 1e-5)  # 10 ms
    d = np.diff(np.convolve(e, np.ones(5) / 5, "same"), prepend=e[0])
    rep = []
    for L in lines:
        i = int(L["s"] * 100); w = slice(max(0, i - 50), i + 50)
        j = int(np.argmax(d[w])) + w.start
        pre = float(e[max(0, i - 30):max(1, i - 5)].mean()); post = float(e[i + 2:i + 30].mean())
        rep.append(dict(s=L["s"], onset=j / 100, delta=round(j / 100 - L["s"], 2), pre_db=round(pre, 1),
                        post_db=round(post, 1), kind="gap" if pre < -35 else "legato", text=L["text"]))
    return rep
