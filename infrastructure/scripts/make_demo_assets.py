"""Copy a finished NaRRAVO export into the landing page (frontend/public/demo).

Usage (from backend/):  uv run python ../infrastructure/scripts/make_demo_assets.py <project_id>

Writes reel.mp4 (the export, re-encoded small for the web), poster.jpg and one still per visual type,
taken from the middle of the first scene of that type, so every image on the landing page is a real frame
of the real video.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

from sqlalchemy import select

from app.application.story_service import current_storyboard
from app.core.config import get_settings
from app.infrastructure.database.models import MediaAsset, VideoExport
from app.infrastructure.database.session import session_scope
from app.infrastructure.storage.base import get_storage
from app.media.assembler import plan_timeline
from app.media.ffmpeg import run_ffmpeg

OUT = Path(__file__).resolve().parents[2] / "frontend" / "public" / "demo"
STILL_NAMES = {
    "historical_map": "still-map", "timeline": "still-timeline", "parallax": "still-parallax",
    "newspaper": "still-newspaper", "infographic": "still-infographic", "kinetic_typography": "still-kinetic",
    "cinematic_image": "still-cinematic", "character_portrait": "still-portrait", "comparison": "still-comparison",
}  # fmt: skip


def main(project_id: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    storage = get_storage(get_settings())
    with session_scope() as session:
        export = session.scalar(select(VideoExport).where(VideoExport.project_id == uuid.UUID(project_id),
                                                          VideoExport.quality == "final").order_by(VideoExport.created_at.desc()))  # fmt: skip
        if export is None:
            raise SystemExit("No final export for that project")
        video = storage.local_path(session.get(MediaAsset, export.video_asset_id).storage_key)
        board = current_storyboard(session, export.project_id)
        scenes = sorted(board.scenes, key=lambda s: s.position)
        from app.application.production import current_asset

        lengths = [current_asset(session, s.id, "narration")[1].duration_seconds for s in scenes]
        timings, _ = plan_timeline(lengths, [s.transition for s in scenes], [s.duration_override for s in scenes])
        moments = {}
        for scene, t in zip(scenes, timings, strict=True):
            moments.setdefault(scene.visual_type, t.start + t.duration * 0.62)
    run_ffmpeg(["-i", video, "-vf", "scale=540:-2", "-c:v", "libx264", "-crf", "30", "-preset", "slow", "-c:a", "aac",
                "-b:a", "96k", "-movflags", "+faststart", OUT / "reel.mp4"], timeout=600)  # fmt: skip
    run_ffmpeg(["-ss", "2.0", "-i", video, "-frames:v", "1", "-vf", "scale=540:-2", "-q:v", "4", OUT / "poster.jpg"], timeout=60)
    for vtype, at in moments.items():
        name = STILL_NAMES.get(vtype)
        if name:
            run_ffmpeg(["-ss", f"{at:.2f}", "-i", video, "-frames:v", "1", "-vf", "scale=360:-2", "-q:v", "4",
                        OUT / f"{name}.jpg"], timeout=60)  # fmt: skip
    print("Wrote", sorted(p.name for p in OUT.iterdir()))


if __name__ == "__main__":
    main(sys.argv[1])
