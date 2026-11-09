"""Small DSP toolkit shared by the procedural music and sound-effect generators."""

from __future__ import annotations

import numpy as np
from scipy import signal

SR = 48_000


def seconds(n: float) -> int:
    return max(1, int(n * SR))


def midi_hz(note: float) -> float:
    return 440.0 * 2 ** ((note - 69) / 12)


def adsr(n: int, attack: float, decay: float, sustain: float, release: float) -> np.ndarray:
    a, d, r = seconds(attack), seconds(decay), seconds(release)
    s = max(0, n - a - d - r)
    env = np.concatenate([
        np.linspace(0, 1, a, endpoint=False),
        np.linspace(1, sustain, d, endpoint=False),
        np.full(s, sustain),
        np.linspace(sustain, 0, r),
    ])  # fmt: skip
    return np.pad(env, (0, max(0, n - len(env))))[:n].astype(np.float32)


def additive(freq: float, n: int, harmonics: int = 8, detune_cents: float = 0.0, rolloff: float = 1.0,
             phase: float = 0.0) -> np.ndarray:  # fmt: skip
    t = np.arange(n, dtype=np.float32) / SR
    f = freq * 2 ** (detune_cents / 1200)
    out = np.zeros(n, np.float32)
    for k in range(1, harmonics + 1):
        if f * k > SR / 2.2:
            break
        out += np.sin(2 * np.pi * f * k * t + phase * k).astype(np.float32) / k**rolloff
    return out


def noise(n: int, rng: np.random.Generator) -> np.ndarray:
    return rng.uniform(-1, 1, n).astype(np.float32)


def lowpass(x: np.ndarray, cutoff: float, order: int = 2) -> np.ndarray:
    sos = signal.butter(order, min(cutoff, SR / 2.1), "low", fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=0).astype(np.float32)


def highpass(x: np.ndarray, cutoff: float, order: int = 2) -> np.ndarray:
    sos = signal.butter(order, cutoff, "high", fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=0).astype(np.float32)


def bandpass(x: np.ndarray, lo: float, hi: float, order: int = 2) -> np.ndarray:
    sos = signal.butter(order, [lo, min(hi, SR / 2.1)], "band", fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=0).astype(np.float32)


def reverb(x: np.ndarray, rng: np.random.Generator, seconds_: float = 2.4, wet: float = 0.3) -> np.ndarray:
    """Convolution reverb with a synthetic exponentially-decaying stereo-ish impulse response."""
    n = seconds(seconds_)
    ir = noise(n, rng) * np.exp(-np.linspace(0, 7, n)).astype(np.float32)
    ir = lowpass(ir, 6000)
    ir /= np.sqrt(np.sum(ir**2)) + 1e-9
    tail = signal.fftconvolve(x, ir)[: len(x)].astype(np.float32)
    return x * (1 - wet) + tail * wet


def place(buffer: np.ndarray, sound: np.ndarray, start: float, gain: float = 1.0) -> None:
    i = int(start * SR)
    if i >= len(buffer) or i + len(sound) <= 0:
        return
    s = sound[max(0, -i) :]
    i = max(0, i)
    end = min(len(buffer), i + len(s))
    buffer[i:end] += s[: end - i] * gain


def db(value: float) -> float:
    return float(10 ** (value / 20))
