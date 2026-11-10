"""Safe FFmpeg invocation: argument arrays only, never a shell, always with timeouts."""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from collections.abc import Callable, Sequence
from functools import lru_cache
from pathlib import Path

import numpy as np

logger = logging.getLogger("narravo.ffmpeg")


class FfmpegError(RuntimeError):
    pass


@lru_cache
def ffmpeg_exe() -> str:
    system = shutil.which("ffmpeg")
    if system:
        return system
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def run_ffmpeg(args: Sequence[str | Path], *, timeout: float, cancel_check: Callable[[], bool] | None = None) -> None:
    cmd = [ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-nostdin", "-y", *map(str, args)]
    logger.debug("ffmpeg %s", " ".join(cmd[1:]))
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)  # noqa: S603
    try:
        _, stderr = _wait(proc, timeout, cancel_check)
    except BaseException:
        proc.kill()
        proc.wait()
        raise
    if proc.returncode != 0:
        raise FfmpegError(f"ffmpeg failed ({proc.returncode}): {stderr.decode(errors='replace')[-800:]}")


def _wait(proc: subprocess.Popen, timeout: float, cancel_check: Callable[[], bool] | None) -> tuple[bytes, bytes]:
    from app.core.errors import JobCancelledError

    elapsed = 0.0
    while True:
        try:
            return proc.communicate(timeout=1.0)
        except subprocess.TimeoutExpired:
            elapsed += 1.0
            if cancel_check and cancel_check():
                raise JobCancelledError() from None
            if elapsed >= timeout:
                raise FfmpegError(f"ffmpeg timed out after {timeout:.0f}s") from None


def media_duration(path: Path) -> float:
    """Duration in seconds, parsed from ffmpeg's stream header (imageio-ffmpeg ships no ffprobe)."""
    cmd = [ffmpeg_exe(), "-hide_banner", "-nostdin", "-i", str(path)]
    proc = subprocess.run(cmd, capture_output=True, timeout=60, check=False)  # noqa: S603
    match = re.search(rb"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", proc.stderr)
    if not match:
        raise FfmpegError(f"Could not read duration of {path.name}")
    h, m, s = match.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


class FrameWriter:
    """Streams raw BGR frames to an FFmpeg H.264 encoder through a pipe."""

    def __init__(
        self,
        path: Path,
        width: int,
        height: int,
        fps: int,
        *,
        crf: int = 16,
        preset: str = "veryfast",
        threads: int = 4,
    ) -> None:
        self.width, self.height = width, height
        cmd = [
            ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
            "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{width}x{height}", "-r", str(fps), "-i", "pipe:0",
            "-an", "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p",
            "-threads", str(threads), "-movflags", "+faststart", str(path),
        ]  # fmt: skip
        self._proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)  # noqa: S603

    def write(self, frame: np.ndarray) -> None:
        if frame.shape != (self.height, self.width, 3) or frame.dtype != np.uint8:
            raise ValueError(f"Bad frame {frame.shape} {frame.dtype}")
        assert self._proc.stdin is not None
        try:
            self._proc.stdin.write(np.ascontiguousarray(frame).tobytes())
        except BrokenPipeError as exc:
            raise FfmpegError(self._stderr()) from exc

    def close(self, timeout: float = 300) -> None:
        assert self._proc.stdin is not None
        self._proc.stdin.close()
        try:
            self._proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            self._proc.kill()
            raise FfmpegError("Encoder timed out") from exc
        if self._proc.returncode != 0:
            raise FfmpegError(self._stderr())

    def abort(self) -> None:
        if self._proc.poll() is None:
            self._proc.kill()
            self._proc.wait()

    def _stderr(self) -> str:
        data = self._proc.stderr.read() if self._proc.stderr else b""
        return f"encoder failed: {data.decode(errors='replace')[-800:]}"

    def __enter__(self) -> FrameWriter:
        return self

    def __exit__(self, exc_type, *_exc) -> None:  # type: ignore[no-untyped-def]
        if exc_type is None:
            self.close()
        else:
            self.abort()
