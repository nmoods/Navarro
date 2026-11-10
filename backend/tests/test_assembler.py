"""Final assembly with mixed hard cuts and crossfades (regression: xfade after concat failed on timebases)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.media.assembler import assemble, plan_timeline
from app.media.ffmpeg import media_duration, run_ffmpeg
from app.media.spec import RenderSettings


def _clip(path: Path, seconds: float, hue: int) -> Path:
    # Same container timescale as the scene renderer's clips (15360), as in the failing real export.
    run_ffmpeg(["-f", "lavfi", "-i", f"color=c=0x{hue:02x}4080:s=160x288:r=30:d={seconds}", "-c:v", "libx264",
                "-pix_fmt", "yuv420p", "-video_track_timescale", "15360", path], timeout=60)  # fmt: skip
    return path


@pytest.mark.slow
@pytest.mark.parametrize("transitions", [
    ["cut", "cut", "crossfade", "fade_black"],
    ["cut", "crossfade", "cut", "crossfade"],
    ["cut", "zoom", "cut", "cut"],
])  # fmt: skip
def test_assemble_mixes_cuts_and_crossfades(tmp_path: Path, transitions: list[str]) -> None:
    timings, total = plan_timeline([2.0, 2.2, 1.8, 2.1], transitions)
    clips = [_clip(tmp_path / f"c{i}.mp4", t.duration, 40 * i) for i, t in enumerate(timings)]
    out = assemble(clips, timings, transitions, None, tmp_path / "out.mp4", RenderSettings(160, 288, 30, "draft"), total,
                   timeout=120)  # fmt: skip
    assert abs(media_duration(out) - total) < 0.2
