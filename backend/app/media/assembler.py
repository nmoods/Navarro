"""Timeline maths and final assembly: scene clips + FFmpeg ``xfade`` transitions + mixed audio -> MP4."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.media.ffmpeg import run_ffmpeg
from app.media.spec import RenderSettings

XFADE_NAMES = {
    "crossfade": "fade",
    "fade_black": "fadeblack",
    "fade_white": "fadewhite",
    "slide_left": "slideleft",
    "slide_up": "slideup",
    "wipe": "wipeleft",
    "zoom": "zoomin",
    "circle_open": "circleopen",
    "dissolve": "dissolve",
    "pixelize": "pixelize",
    "radial": "radial",
}

TRANSITION_SECONDS = {"cut": 0.0, "fade_black": 0.7, "fade_white": 0.6, "zoom": 0.45, "pixelize": 0.5}
DEFAULT_TRANSITION_SECONDS = 0.55
PRE_ROLL = 0.18  # silence before narration inside a scene (after the incoming transition settles)
POST_ROLL = 0.3  # breathing room after the last word of a scene
MIN_SCENE_SECONDS = 2.0


def transition_seconds(name: str) -> float:
    return TRANSITION_SECONDS.get(name, DEFAULT_TRANSITION_SECONDS) if name in XFADE_NAMES or name == "cut" else 0.0


@dataclass(frozen=True)
class SceneTiming:
    start: float  # where the clip starts on the master timeline
    duration: float  # clip length
    narration_offset: float  # narration start inside the clip
    transition_in: float


def plan_timeline(
    narration_lengths: list[float],
    transitions: list[str],
    overrides: list[float | None] | None = None,
) -> tuple[list[SceneTiming], float]:
    """Compute clip lengths/positions so narration never overlaps across xfade transitions."""
    overrides = overrides or [None] * len(narration_lengths)
    timings: list[SceneTiming] = []
    cursor = 0.0
    for i, (audio_len, override) in enumerate(zip(narration_lengths, overrides, strict=True)):
        trans = transition_seconds(transitions[i]) if i > 0 else 0.0
        offset = trans + PRE_ROLL
        natural = offset + audio_len + POST_ROLL
        duration = max(MIN_SCENE_SECONDS, natural, override or 0.0)
        start = cursor - trans
        timings.append(SceneTiming(start=max(0.0, start), duration=duration, narration_offset=offset, transition_in=trans))
        cursor = max(0.0, start) + duration
    return timings, cursor


def assemble(
    clips: list[Path],
    timings: list[SceneTiming],
    transitions: list[str],
    audio_path: Path | None,
    out_path: Path,
    settings: RenderSettings,
    total_duration: float,
    *,
    timeout: float,
    threads: int = 4,
    cancel_check: Callable[[], bool] | None = None,
) -> Path:
    args: list[str | Path] = []
    for clip in clips:
        args += ["-i", clip]
    if audio_path:
        args += ["-i", audio_path]
    fps = settings.fps
    graph = [f"[{i}:v]settb=AVTB,fps={fps},format=yuv420p,setsar=1[s{i}]" for i in range(len(clips))]
    current, length = "s0", timings[0].duration
    for i in range(1, len(clips)):
        out = f"v{i}"
        name = transitions[i]
        trans = timings[i].transition_in
        if name == "cut" or trans <= 0 or name not in XFADE_NAMES:
            graph.append(f"[{current}][s{i}]concat=n=2:v=1:a=0[{out}]")
            length += timings[i].duration
        else:
            offset = max(0.0, length - trans)
            graph.append(f"[{current}][s{i}]xfade=transition={XFADE_NAMES[name]}:duration={trans:.3f}:offset={offset:.3f}[{out}]")
            length = offset + timings[i].duration
        current = out
    args += ["-filter_complex", ";".join(graph), "-map", f"[{current}]"]
    if audio_path:
        args += ["-map", f"{len(clips)}:a", "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
    args += [
        "-c:v", "libx264", "-preset", settings.preset, "-crf", str(settings.crf), "-pix_fmt", "yuv420p",
        "-r", str(fps), "-threads", str(threads), "-t", f"{total_duration:.3f}", "-movflags", "+faststart", out_path,
    ]  # fmt: skip
    out_path.parent.mkdir(parents=True, exist_ok=True)
    run_ffmpeg(args, timeout=timeout, cancel_check=cancel_check)
    return out_path
