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
    onf = np.interp(np.arange(nfr) / fps, t, np.clip(on, 0, 1.5))
    return dict(bpm=bpm, beats=grid.tolist(), down=down, onset=onf.tolist())
