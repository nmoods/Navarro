"""Import every model so ``Base.metadata`` is complete for Alembic and tests."""

from app.infrastructure.database.models.creative import (
    MusicTrack,
    SoundEffectAsset,
    StoryDnaProfile,
    Template,
    VoiceProfile,
)
from app.infrastructure.database.models.identity import AuditLog, Profile, RefreshToken, User
from app.infrastructure.database.models.jobs import GenerationJob, GenerationJobLog
from app.infrastructure.database.models.media import MediaAsset, VideoExport
from app.infrastructure.database.models.planning import ContentIdea, ContentSeries, SeriesEpisode
from app.infrastructure.database.models.projects import (
    Project,
    ProjectSettings,
    Scene,
    SceneAsset,
    ScriptVersion,
    Storyboard,
)

__all__ = [
    "AuditLog",
    "ContentIdea",
    "ContentSeries",
    "GenerationJob",
    "GenerationJobLog",
    "MediaAsset",
    "MusicTrack",
    "Profile",
    "Project",
    "ProjectSettings",
    "RefreshToken",
    "Scene",
    "SceneAsset",
    "ScriptVersion",
    "SeriesEpisode",
    "SoundEffectAsset",
    "Storyboard",
    "StoryDnaProfile",
    "Template",
    "User",
    "VideoExport",
    "VoiceProfile",
]
