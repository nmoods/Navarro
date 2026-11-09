"""SRT / WebVTT subtitle export built from aligned word timings and the same timeline maths as the renderer."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.application.production import current_asset
from app.application.story_service import current_storyboard
from app.core.errors import ConflictError
from app.infrastructure.database.models import Project
from app.media.assembler import plan_timeline
from app.media.captions import chunk_words
from app.media.spec import CaptionWord


def _stamp(seconds: float, sep: str) -> str:
    ms = max(0, round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def build_cues(session: Session, project: Project, max_words: int = 7) -> list[tuple[float, float, str]]:
    board = current_storyboard(session, project.id)
    if board is None:
        raise ConflictError("Generate a storyboard first")
    scenes = sorted(board.scenes, key=lambda s: s.position)
    words_per_scene, lengths = [], []
    for scene in scenes:
        narration = current_asset(session, scene.id, "narration")
        transcript = current_asset(session, scene.id, "transcript")
        if not narration or not transcript:
            raise ConflictError("Render a preview or export first so the voiceover is timed")
        lengths.append(narration[1].duration_seconds or 0.0)
        words_per_scene.append(transcript[0].details.get("words", []))
    timings, _ = plan_timeline(lengths, [s.transition for s in scenes], [s.duration_override for s in scenes])
    cues = []
    for scene, timing, words in zip(scenes, timings, words_per_scene, strict=True):
        offset = timing.start + timing.narration_offset + (scene.caption_override or {}).get("offset_ms", 0) / 1000
        caption_words = tuple(CaptionWord(w["text"], w["start"] + offset, w["end"] + offset) for w in words)
        for chunk in chunk_words(caption_words, max_words):
            cues.append((chunk.start, chunk.words[-1].end, " ".join(w.text for w in chunk.words)))
    return cues


def to_srt(cues: list[tuple[float, float, str]]) -> str:
    return "\n".join(f"{i}\n{_stamp(a, ',')} --> {_stamp(b, ',')}\n{text}\n" for i, (a, b, text) in enumerate(cues, start=1))


def to_vtt(cues: list[tuple[float, float, str]]) -> str:
    return "WEBVTT\n\n" + "\n".join(f"{_stamp(a, '.')} --> {_stamp(b, '.')}\n{text}\n" for a, b, text in cues)
