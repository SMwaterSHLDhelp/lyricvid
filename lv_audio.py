"""Audio analysis: Demucs vocal separation, beat grid, onset envelope."""
import os, subprocess, json, numpy as np

def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)

def duration(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", path]).decode().strip())

def load_mono(path, sr=16000):
    """Decode any audio file to float32 mono via ffmpeg (avoids broken av/torchaudio backends)."""
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).copy()

def separate(audio, work):
    """Demucs htdemucs two-stem split. Returns (vocals.wav, no_vocals.wav); cached in work/sep."""
    name = os.path.splitext(os.path.basename(audio))[0]
    d = os.path.join(work, "sep", "htdemucs", name)
    voc, inst = os.path.join(d, "vocals.wav"), os.path.join(d, "no_vocals.wav")
    if not os.path.exists(voc):
        import sys
        run([sys.executable, "-m", "demucs", "--two-stems", "vocals", "-n", "htdemucs", "-o", os.path.join(work, "sep"), audio])
    return voc, inst

def beats(audio, fps=30, bpm=None):
    """Beat grid + downbeat phase + per-frame onset strength.
    If bpm is given, a constant grid at that tempo is phase-fitted to the onset envelope
    (robust for AI-generated songs, which hold tempo); otherwise librosa's tracker is used."""
    import librosa
    y = load_mono(audio, 22050); sr = 22050; hop = 512
    onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    t = librosa.frames_to_time(np.arange(len(onset)), sr=sr, hop_length=hop)
    if not bpm:
        tempo, _ = librosa.beat.beat_track(onset_envelope=onset, sr=sr, hop_length=hop)
        bpm = float(np.atleast_1d(tempo)[0])
    period = 60.0 / bpm
    best = (-1, 0)
    for ph in np.linspace(0, period, 240, endpoint=False):
        idx = np.clip(((np.arange(ph, t[-1], period)) / (hop / sr)).astype(int), 0, len(onset) - 1)
        s = onset[idx].sum()
        if s > best[0]: best = (s, ph)
    grid = np.arange(best[1], t[-1] + period, period)
    # downbeat = beat phase (0..3) with the most low-frequency energy onset (kick)
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop))[:12]
    low = np.r_[0, np.maximum(np.diff(np.log1p(S), axis=1), 0).sum(0)]
    gi = np.clip((grid / (hop / sr)).astype(int), 0, len(low) - 1)
    down = int(np.argmax([low[gi[k::4]].sum() for k in range(4)]))
    on = onset / (np.percentile(onset, 99) + 1e-9)
    nfr = int(np.ceil(duration(audio) * fps)) + 1
    times = np.arange(nfr) / fps
    onf = np.interp(times, t, np.clip(on, 0, 1.5))
    env = frame_envelopes(y, sr, fps, nfr)
    return dict(bpm=bpm, beats=grid.tolist(), down=int(down), onset=onf.tolist(), **env)

def frame_envelopes(y, sr, fps, nfr, win=2048):
    """Per-frame RMS and bass/mid/high energy, each scaled so the 98th percentile is 1.

    Bass is 20–150 Hz, mid 150–2000 Hz, high 2000–8000 Hz. Values are clipped to 1.5
    so a single spike cannot dominate a preset."""
    y = np.asarray(y, np.float32)
    hop = max(1, int(round(sr / float(fps))))
    nfr = int(nfr)
    if nfr < 1: nfr = 1
    need = (nfr - 1) * hop + win
    if len(y) < need: y = np.pad(y, (0, need - len(y)))
    frames = np.lib.stride_tricks.as_strided(y, shape=(nfr, win), strides=(y.strides[0] * hop, y.strides[0]))
    window = np.hanning(win).astype(np.float32)
    mag = np.abs(np.fft.rfft(frames * window, axis=1))
    freqs = np.fft.rfftfreq(win, 1.0 / sr)
    def band(a, b):
        m = (freqs >= a) & (freqs < b)
        return mag[:, m].mean(axis=1) if m.any() else np.zeros(nfr, np.float32)
    def norm(a):
        a = np.asarray(a, np.float64)
        return np.clip(a / (np.percentile(a, 98) + 1e-9), 0, 1.5).astype(float)
    rms = np.sqrt((frames.astype(np.float64) ** 2).mean(axis=1) + 1e-12)
    return dict(rms=norm(rms).tolist(), bass=norm(band(20, 150)).tolist(),
                mid=norm(band(150, 2000)).tolist(), high=norm(band(2000, 8000)).tolist())

def synth_audio(seconds=3.2, bpm=108, sr=22050, seed=1):
    """A short sine-plus-click track for previews. No vocals, no Demucs, no MMS."""
    n = int(seconds * sr)
    t = np.arange(n, dtype=np.float64) / sr
    y = 0.18 * np.sin(2 * np.pi * 55 * t) + 0.05 * np.sin(2 * np.pi * 220 * t)
    y += 0.03 * np.sin(2 * np.pi * 880 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.25 * t))
    period = 60.0 / bpm
    click_n = int(0.045 * sr)
    env = np.exp(-np.linspace(0, 1, click_n) * 7)
    burst = np.random.RandomState(seed).uniform(-1, 1, click_n) * env
    for i in range(int(seconds / period) + 1):
        c = int(round(i * period * sr))
        if c + click_n < n:
            y[c:c + click_n] += burst * (0.85 if i % 4 == 0 else 0.4)
    return np.clip(y, -1, 1).astype(np.float32), sr

def write_wav(path, y, sr):
    import wave
    pcm = (np.clip(y, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(int(sr))
        w.writeframes(pcm.tobytes())
    return path

def analyze_signal(y, sr, fps, bpm, dur=None):
    """Beat grid at a known BPM plus RMS and spectral bands. Does not use librosa."""
    dur = float(dur if dur is not None else len(y) / sr)
    period = 60.0 / float(bpm)
    grid = np.arange(0.0, dur + period * 0.5, period)
    nfr = int(np.ceil(dur * fps)) + 1
    env = frame_envelopes(y, sr, fps, nfr)
    bass = np.asarray(env["bass"], np.float64)
    flux = np.clip(np.diff(bass, prepend=bass[0]), 0, None)
    onset = np.clip(flux / (np.percentile(flux, 99) + 1e-9), 0, 1.5)
    return dict(bpm=float(bpm), beats=[float(x) for x in grid], down=0, onset=onset.tolist(), **env)
