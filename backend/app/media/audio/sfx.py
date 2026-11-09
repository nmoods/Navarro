"""Procedural sound effects (license-free by construction). Each returns mono float32 at 48 kHz."""

from __future__ import annotations

import numpy as np

from app.media.audio.synth import SR, additive, bandpass, highpass, lowpass, midi_hz, noise, reverb, seconds


def _t(n: int) -> np.ndarray:
    return np.arange(n, dtype=np.float32) / SR


def whoosh(duration: float, rng: np.random.Generator) -> np.ndarray:
    n = seconds(min(duration, 1.2))
    x = noise(n, rng)
    out = np.zeros(n, np.float32)
    chunks = 24
    size = n // chunks
    for i in range(chunks):
        centre = 300 + 3500 * np.sin(np.pi * i / chunks) ** 2
        seg = bandpass(x[i * size : (i + 1) * size + 256], centre * 0.6, centre * 1.6)
        out[i * size : i * size + len(seg)] += seg[: n - i * size]
    env = np.sin(np.linspace(0, np.pi, n)) ** 2
    return out * env.astype(np.float32) * 1.8


def impact(duration: float, rng: np.random.Generator) -> np.ndarray:
    n = seconds(2.0)
    t = _t(n)
    freq = 38 + 90 * np.exp(-t * 14)
    boom = np.sin(2 * np.pi * np.cumsum(freq) / SR).astype(np.float32) * np.exp(-t * 2.4)
    crack = highpass(noise(n, rng), 1500) * np.exp(-t * 40)
    return reverb(np.tanh((boom + crack * 0.5) * 1.5).astype(np.float32), rng, 2.0, 0.3)


def riser(duration: float, rng: np.random.Generator) -> np.ndarray:
    n = seconds(min(max(duration, 1.0), 3.0))
    t = _t(n)
    p = t / t[-1]
    freq = 180 + 1800 * p**2
    tone = np.sin(2 * np.pi * np.cumsum(freq) / SR).astype(np.float32) * 0.4
    hiss = bandpass(noise(n, rng), 1500, 9000) * p
    return (tone + hiss) * (p**1.5).astype(np.float32)


def wind(duration: float, rng: np.random.Generator) -> np.ndarray:
    n = seconds(duration)
    t = _t(n)
    gust = 0.55 + 0.45 * np.sin(2 * np.pi * 0.13 * t) * np.sin(2 * np.pi * 0.051 * t + 1)
    return bandpass(noise(n, rng), 200, 1200) * gust.astype(np.float32) * 1.6


def rain(duration: float, rng: np.random.Generator) -> np.ndarray:
    n = seconds(duration)
    bed = highpass(lowpass(noise(n, rng), 7000), 800) * 0.5
    drops = np.zeros(n, np.float32)
    for pos in rng.integers(0, n, int(duration * 40)):
        ln = min(400, n - pos)
        drops[pos : pos + ln] += np.exp(-np.arange(ln) / 60).astype(np.float32) * rng.uniform(0.1, 0.4)
    return bed + highpass(drops * noise(n, rng), 2000)


def thunder(duration: float, rng: np.random.Generator) -> np.ndarray:
    n = seconds(max(3.0, min(duration, 5.0)))
    t = _t(n)
    rumble = lowpass(noise(n, rng), 180, 4) * 6 * np.exp(-t * 0.9) * (1 - np.exp(-t * 6))
    crack = bandpass(noise(n, rng), 300, 4000) * np.exp(-t * 9) * 0.8
    return reverb((rumble + crack).astype(np.float32), rng, 3.0, 0.4)


def fire(duration: float, rng: np.random.Generator) -> np.ndarray:
    n = seconds(duration)
    bed = lowpass(noise(n, rng), 600) * 0.6
    crackle = np.zeros(n, np.float32)
    for pos in rng.integers(0, n, int(duration * 18)):
        ln = min(220, n - pos)
        crackle[pos : pos + ln] += rng.uniform(-1, 1, ln).astype(np.float32) * np.exp(-np.arange(ln) / 30) * rng.uniform(0.3, 1.0)
    return bed + highpass(crackle, 1200)


def heartbeat(duration: float, rng: np.random.Generator) -> np.ndarray:
    n = seconds(duration)
    out = np.zeros(n, np.float32)
    beat = seconds(0.18)
    t = _t(beat)
    thump = (np.sin(2 * np.pi * 55 * t) * np.exp(-t * 22)).astype(np.float32)
    period = 0.95
    k = 0.0
    while k < duration:
        for offset, g in ((0.0, 1.0), (0.24, 0.7)):
            i = int((k + offset) * SR)
            end = min(n, i + beat)
            if i < n:
                out[i:end] += thump[: end - i] * g
        k += period
    return lowpass(out, 400) * 2.2


def clock_tick(duration: float, rng: np.random.Generator) -> np.ndarray:
    n = seconds(duration)
    out = np.zeros(n, np.float32)
    tick = bandpass(noise(seconds(0.02), rng), 2500, 6000) * np.exp(-np.linspace(0, 8, seconds(0.02))).astype(np.float32)
    for k in np.arange(0, duration, 0.5):
        i = int(k * SR)
        out[i : i + len(tick)] += tick[: max(0, min(len(tick), n - i))] * (1.0 if int(k * 2) % 2 == 0 else 0.6)
    return out * 1.5


def paper(duration: float, rng: np.random.Generator) -> np.ndarray:
    n = seconds(0.7)
    env = np.zeros(n, np.float32)
    for pos in rng.integers(0, n - 4000, 5):
        env[pos : pos + 4000] += np.hanning(4000).astype(np.float32) * rng.uniform(0.3, 1)
    return bandpass(noise(n, rng), 1200, 8000) * env


def shimmer(duration: float, rng: np.random.Generator) -> np.ndarray:
    n = seconds(min(3.0, max(1.5, duration)))
    out = np.zeros(n, np.float32)
    for i, note in enumerate((84, 88, 91, 96, 100)):
        start = int(i * 0.09 * SR)
        ln = n - start
        out[start:] += additive(midi_hz(note), ln, 2) * np.exp(-np.linspace(0, 5, ln)).astype(np.float32) * 0.25
    return reverb(out, rng, 2.5, 0.45)


def drone(duration: float, rng: np.random.Generator) -> np.ndarray:
    n = seconds(duration)
    t = _t(n)
    body = additive(midi_hz(33), n, 5, rolloff=1.4) + additive(midi_hz(33.15), n, 5, rolloff=1.4)
    return lowpass(body * (0.7 + 0.3 * np.sin(2 * np.pi * 0.1 * t)).astype(np.float32), 500) * 0.5


GENERATORS = {
    "whoosh": whoosh, "impact": impact, "riser": riser, "wind": wind, "rain": rain, "thunder": thunder,
    "fire": fire, "heartbeat": heartbeat, "clock_tick": clock_tick, "paper": paper, "shimmer": shimmer,
    "drone": drone,
}  # fmt: skip

ONE_SHOTS = {"whoosh", "impact", "riser", "paper", "shimmer", "thunder"}


def generate_sfx(kind: str, duration: float, seed: int = 0) -> np.ndarray:
    fn = GENERATORS.get(kind)
    if fn is None:
        raise ValueError(f"Unknown sound effect '{kind}'")
    x = fn(duration, np.random.default_rng(seed))
    if kind not in ONE_SHOTS:  # fade ambient beds in/out
        f = min(len(x) // 3, seconds(0.6))
        x[:f] *= np.linspace(0, 1, f)
        x[-f:] *= np.linspace(1, 0, f)
    peak = float(np.max(np.abs(x))) or 1.0
    return (x / peak * 0.8).astype(np.float32)
