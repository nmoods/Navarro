"""Master audio mix: narration + ducked music + sound effects -> 48 kHz stereo WAV."""

from __future__ import annotations

from math import gcd
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal

from app.media.audio.music import generate_music
from app.media.audio.sfx import generate_sfx
from app.media.audio.synth import SR, db, place, seconds
from app.media.spec import TimelineSpec


def load_audio(path: Path) -> np.ndarray:
    """Load any WAV/FLAC/OGG to mono float32 at 48 kHz."""
    data, rate = sf.read(str(path), dtype="float32", always_2d=True)
    mono = data.mean(axis=1)
    if rate != SR:
        g = gcd(int(rate), SR)
        mono = signal.resample_poly(mono, SR // g, int(rate) // g).astype(np.float32)
    return mono


def load_stereo(path: Path) -> np.ndarray:
    data, rate = sf.read(str(path), dtype="float32", always_2d=True)
    if data.shape[1] == 1:
        data = np.repeat(data, 2, axis=1)
    data = data[:, :2]
    if rate != SR:
        g = gcd(int(rate), SR)
        data = signal.resample_poly(data, SR // g, int(rate) // g, axis=0).astype(np.float32)
    return data


def _envelope(x: np.ndarray, attack: float = 0.02, release: float = 0.35) -> np.ndarray:
    """Smoothed amplitude envelope used for side-chain ducking."""
    rect = np.abs(x)
    win = seconds(0.05)
    smooth = np.convolve(rect, np.ones(win, np.float32) / win, mode="same")
    b, a = signal.butter(1, 1 / (release * SR) * 4, "low")
    return signal.lfilter(b, a, smooth).astype(np.float32)


def mix_timeline(spec: TimelineSpec, total: float, out_path: Path) -> Path:
    n = seconds(total)
    voice = np.zeros(n, np.float32)
    for cue in spec.narration:
        place(voice, load_audio(cue.path), cue.start, db(cue.gain_db))
    rms = float(np.sqrt(np.mean(voice[np.abs(voice) > 1e-4] ** 2))) if np.any(np.abs(voice) > 1e-4) else 0.0
    if rms > 0:
        voice *= db(-17.0) / rms  # narration at about -17 dBFS RMS

    music = np.zeros((n, 2), np.float32)
    if spec.music_path is not None:
        track = load_stereo(spec.music_path)
        reps = int(np.ceil(n / max(1, len(track))))
        music = np.tile(track, (reps, 1))[:n]
    elif spec.music_mood and spec.music_mood != "none":
        generated = generate_music(spec.music_mood, total, spec.music_cues, spec.seed)
        music[: len(generated)] = generated[:n]
    if np.any(music):
        music *= db(spec.music_volume_db + 6) / (float(np.max(np.abs(music))) or 1.0)
        env = _envelope(voice)
        duck = 1.0 - 0.55 * np.clip(env / (float(np.percentile(env, 95)) + 1e-6), 0, 1)
        music *= duck[:, None]

    sfx = np.zeros(n, np.float32)
    for i, cue in enumerate(spec.sfx):
        place(sfx, generate_sfx(cue.kind, cue.duration, spec.seed + i), cue.start, db(cue.gain_db))

    master = music + (voice + sfx)[:, None]
    peak = float(np.max(np.abs(master))) or 1.0
    if peak > 0.98:
        master = np.tanh(master / peak * 1.2) / np.tanh(1.2) * 0.98
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out_path), master, SR, subtype="PCM_16")
    return out_path
