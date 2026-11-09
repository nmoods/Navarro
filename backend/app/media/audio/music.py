"""Procedural, royalty-free underscore music.

A mood selects key, tempo, chord progression and instrumentation (pad, bass, plucked arpeggio, low drums,
drone). An intensity curve derived from the storyboard's music cues (build / steady / tension / drop /
resolve) gates the layers so the score follows the story. Output: stereo float32 at 48 kHz.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.media.audio.synth import (
    SR,
    additive,
    adsr,
    highpass,
    lowpass,
    midi_hz,
    noise,
    place,
    reverb,
    seconds,
)


@dataclass(frozen=True)
class Mood:
    root: int
    minor: bool
    bpm: float
    progression: tuple[int, ...]  # scale-degree roots in semitones from the key root
    pad: float
    bass: float
    pluck: float
    drums: float
    drone: float
    brightness: float


MOODS: dict[str, Mood] = {
    "mystery": Mood(57, True, 68, (0, 8, 3, 10), 0.5, 0.35, 0.28, 0.0, 0.35, 2200),
    "epic": Mood(50, True, 88, (0, 8, 3, 10), 0.55, 0.5, 0.2, 0.6, 0.2, 3200),
    "calm": Mood(60, False, 72, (0, 7, 9, 5), 0.5, 0.25, 0.35, 0.0, 0.0, 3000),
    "tension": Mood(52, True, 100, (0, 1, 0, 6), 0.35, 0.55, 0.25, 0.3, 0.5, 1800),
    "uplifting": Mood(55, False, 100, (0, 7, 9, 5), 0.5, 0.35, 0.4, 0.35, 0.0, 4200),
    "melancholy": Mood(50, True, 60, (0, 5, 8, 7), 0.55, 0.25, 0.4, 0.0, 0.1, 2400),
}

_CUE_INTENSITY = {"build": (0.45, 0.95), "steady": (0.55, 0.55), "tension": (0.8, 0.85), "drop": (1.0, 1.0),
                  "resolve": (0.6, 0.3), "calm": (0.35, 0.35)}  # fmt: skip


def intensity_curve(cues: list[tuple[float, str]], total: float) -> np.ndarray:
    """Per-0.1s intensity in [0, 1] built from (start_time, cue) pairs."""
    steps = int(total * 10) + 1
    curve = np.full(steps, 0.55, np.float32)
    if not cues:
        curve[:] = np.linspace(0.45, 0.8, steps)
        return curve
    ordered = sorted(cues)
    for i, (start, cue) in enumerate(ordered):
        end = ordered[i + 1][0] if i + 1 < len(ordered) else total
        a, b = int(start * 10), max(int(start * 10) + 1, int(end * 10))
        lo, hi = _CUE_INTENSITY.get(cue, (0.55, 0.55))
        curve[a:b] = np.linspace(lo, hi, b - a)[: max(0, min(b, steps) - a)]
        if cue == "drop":
            curve[a : min(b, a + 6)] = 0.0
    kernel = np.ones(15, np.float32) / 15
    return np.convolve(curve, kernel, mode="same")


def _chord(root: int, minor_key: bool, degree: int) -> list[int]:
    minor_degrees = {0, 5, 7} if minor_key else {9, 2, 4}
    third = 3 if (degree % 12) in minor_degrees else 4
    if degree % 12 in (1, 6):
        third = 4
    return [root + degree, root + degree + third, root + degree + 7]


def generate_music(mood_name: str, total: float, cues: list[tuple[float, str]], seed: int = 0) -> np.ndarray:
    mood = MOODS.get(mood_name, MOODS["mystery"])
    rng = np.random.default_rng(seed)
    n = seconds(total + 1.0)
    left, right = np.zeros(n, np.float32), np.zeros(n, np.float32)
    beat = 60.0 / mood.bpm
    bar = beat * 4
    intensity = intensity_curve(cues, total + 1.0)
    level = lambda t: float(intensity[min(len(intensity) - 1, int(t * 10))])  # noqa: E731
    t, bar_index = 0.0, 0
    while t < total + 0.5:
        degree = mood.progression[bar_index % len(mood.progression)]
        chord = _chord(mood.root, mood.minor, degree)
        lv = level(t)
        # pad: wide detuned voices, long attack, slight stereo spread
        pad_len = seconds(bar * 1.25)
        for j, note in enumerate(chord + [chord[0] + 12]):
            env = adsr(pad_len, bar * 0.35, 0.3, 0.8, bar * 0.4)
            for side, cents in ((left, -7), (right, 7)):
                voice = additive(midi_hz(note), pad_len, harmonics=7, detune_cents=cents + j, rolloff=1.3)
                place(side, voice * env, t, mood.pad * 0.07 * (0.6 + 0.4 * lv))
        # bass: root pulses, busier when intense
        hits = 2 if lv < 0.6 else 4 if lv < 0.85 else 8
        for k in range(hits):
            bt = t + k * bar / hits
            ln = seconds(bar / hits * 0.95)
            tone = additive(midi_hz(chord[0] - 12), ln, harmonics=3, rolloff=1.8)
            tone = np.tanh(tone * 1.6) * adsr(ln, 0.01, 0.15, 0.6, 0.12)
            gain = mood.bass * 0.22 * (0.5 + 0.5 * lv)
            place(left, tone, bt, gain)
            place(right, tone, bt, gain)
        # plucked arpeggio
        if mood.pluck and lv > 0.3:
            steps = 8 if lv > 0.6 else 4
            pattern = [chord[0], chord[1], chord[2], chord[1] + 12, chord[2], chord[0] + 12, chord[1], chord[2] + 12]
            for k in range(steps):
                note = pattern[k % len(pattern)] + 12
                ln = seconds(beat * 1.6)
                tone = additive(midi_hz(note), ln, harmonics=4, rolloff=2.2) * np.exp(-np.linspace(0, 6, ln)).astype(np.float32)
                pan = 0.5 + 0.35 * np.sin(k * 1.7 + bar_index)
                gain = mood.pluck * 0.12 * min(1.0, lv * 1.3)
                place(left, tone, t + k * bar / steps, gain * (1 - pan) * 2)
                place(right, tone, t + k * bar / steps, gain * pan * 2)
        # low drums for epic/tension/uplifting moments
        if mood.drums and lv > 0.65:
            for k in range(4):
                if k % 2 and lv < 0.85:
                    continue
                ln = seconds(0.6)
                tt = np.arange(ln) / SR
                freq = 45 + 80 * np.exp(-tt * 18)
                body = np.sin(2 * np.pi * np.cumsum(freq) / SR).astype(np.float32) * np.exp(-tt * 6).astype(np.float32)
                hit = body + lowpass(noise(ln, rng), 900) * np.exp(-tt * 30).astype(np.float32) * 0.4
                g = mood.drums * 0.35 * lv
                place(left, hit, t + k * beat, g)
                place(right, hit, t + k * beat, g)
        t += bar
        bar_index += 1
    if mood.drone:
        tt = np.arange(n, dtype=np.float32) / SR
        lfo = 0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * tt)
        drone = (additive(midi_hz(mood.root - 24), n, 4, rolloff=1.5) + 0.6 * additive(midi_hz(mood.root - 17), n, 3)) * lfo
        left += drone * mood.drone * 0.05
        right += drone * mood.drone * 0.05
    stereo = np.stack([left, right], axis=1)
    stereo = lowpass(stereo, mood.brightness)
    stereo = highpass(stereo, 35)
    stereo = np.stack([reverb(stereo[:, 0], rng, 2.8, 0.35), reverb(stereo[:, 1], rng, 2.9, 0.35)], axis=1)
    fade = min(len(stereo), seconds(1.5))
    stereo[:fade] *= np.linspace(0, 1, fade)[:, None]
    stereo[-fade:] *= np.linspace(1, 0, fade)[:, None]
    peak = float(np.max(np.abs(stereo))) or 1.0
    return (stereo / peak * 0.7)[: seconds(total)].astype(np.float32)
