"""Secure upload validation: size limits, extension allow-list, magic-byte sniffing, full decode and
re-encode (strips metadata and neutralises polyglot files)."""

from __future__ import annotations

import io
import tempfile
from dataclasses import dataclass
from pathlib import Path

import soundfile as sf
from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError

from app.core.errors import PayloadTooLargeError, ValidationFailedError

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}
AUDIO_EXT = {".wav", ".mp3", ".ogg", ".flac"}
_MAGIC = {
    b"\x89PNG\r\n\x1a\n": "image", b"\xff\xd8\xff": "image", b"RIFF": "riff", b"ID3": "audio", b"\xff\xfb": "audio",
    b"\xff\xf3": "audio", b"\xff\xf2": "audio", b"OggS": "audio", b"fLaC": "audio",
}  # fmt: skip
MAX_PIXELS = 40_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS  # decompression-bomb guard


@dataclass(frozen=True)
class CleanImage:
    data: bytes
    width: int
    height: int
    mime: str


async def read_limited(upload: UploadFile, max_bytes: int) -> bytes:
    data = await upload.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise PayloadTooLargeError(f"File exceeds {max_bytes // (1024 * 1024)} MB")
    if not data:
        raise ValidationFailedError("Empty file")
    return data


def _sniff(data: bytes) -> str | None:
    for magic, kind in _MAGIC.items():
        if data.startswith(magic):
            if kind == "riff":
                return "image" if data[8:12] == b"WEBP" else "audio" if data[8:12] == b"WAVE" else None
            return kind
    return None


def _ext(name: str | None) -> str:
    return Path(name or "").suffix.lower()


def validate_image(data: bytes, filename: str | None) -> CleanImage:
    if _ext(filename) not in IMAGE_EXT or _sniff(data) != "image":
        raise ValidationFailedError("Only PNG, JPEG or WebP images are accepted")
    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()
        with Image.open(io.BytesIO(data)) as img:
            if img.width * img.height > MAX_PIXELS or min(img.width, img.height) < 64:
                raise ValidationFailedError("Image dimensions out of range")
            img = img.convert("RGB")
            img.thumbnail((4096, 4096))
            out = io.BytesIO()
            img.save(out, format="PNG", optimize=True)
            return CleanImage(out.getvalue(), img.width, img.height, "image/png")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValidationFailedError("The image could not be decoded") from exc


def validate_audio(data: bytes, filename: str | None, work_dir: Path) -> tuple[Path, float, str]:
    ext = _ext(filename)
    if ext not in AUDIO_EXT or _sniff(data) != "audio":
        raise ValidationFailedError("Only WAV, MP3, OGG or FLAC audio is accepted")
    work_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=work_dir, suffix=ext, delete=False) as fh:
        fh.write(data)
        path = Path(fh.name)
    try:
        info = sf.info(str(path))
    except RuntimeError as exc:
        path.unlink(missing_ok=True)
        raise ValidationFailedError("The audio file could not be decoded") from exc
    if not (0.2 <= info.duration <= 900):
        path.unlink(missing_ok=True)
        raise ValidationFailedError("Audio must be between 0.2 seconds and 15 minutes")
    mime = {".wav": "audio/wav", ".mp3": "audio/mpeg", ".ogg": "audio/ogg", ".flac": "audio/flac"}[ext]
    return path, float(info.duration), mime
