"""Closed vocabularies shared by the API, the AI layer and the render engine."""

from __future__ import annotations

from enum import StrEnum


class JobStatus(StrEnum):
    PENDING = "pending"
    SCRIPT_GENERATION = "script_generation"
    STORYBOARD_GENERATION = "storyboard_generation"
    IMAGE_GENERATION = "image_generation"
    VOICE_GENERATION = "voice_generation"
    ANIMATION = "animation"
    RENDERING = "rendering"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED)


ACTIVE_JOB_STATUSES = tuple(s for s in JobStatus if not s.is_terminal)


class JobType(StrEnum):
    STORY = "story"  # director brief + hooks + script + storyboard
    PRODUCTION = "production"  # ensure assets (cached) + render final video
    PREVIEW = "preview"  # same as production at draft quality
    SCENE_REGENERATION = "scene_regeneration"
    SERIES_PLAN = "series_plan"
    SERIES_PRODUCTION = "series_production"  # fan-out parent for episodes


class ProjectStatus(StrEnum):
    DRAFT = "draft"
    GENERATING_STORY = "generating_story"
    STORYBOARD_READY = "storyboard_ready"
    PRODUCING = "producing"
    READY = "ready"
    FAILED = "failed"


class AspectRatio(StrEnum):
    VERTICAL = "9:16"
    LANDSCAPE = "16:9"
    SQUARE = "1:1"

    @property
    def resolution(self) -> tuple[int, int]:
        return {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080)}[self.value]


class Platform(StrEnum):
    TIKTOK = "tiktok"
    INSTAGRAM_REELS = "instagram_reels"
    YOUTUBE_SHORTS = "youtube_shorts"
    YOUTUBE = "youtube"
    GENERIC = "generic"


class VisualStyle(StrEnum):
    CINEMATIC_DOCUMENTARY = "cinematic_documentary"
    HISTORICAL_REALISM = "historical_realism"
    DARK_MYSTERY = "dark_mystery"
    ANIMATION_3D = "animation_3d"
    ANIME = "anime"
    VINTAGE_DOCUMENTARY = "vintage_documentary"
    MINIMALIST_MOTION = "minimalist_motion"
    ARCHIVAL_NEWSPAPER = "archival_newspaper"
    PHOTOREALISTIC = "photorealistic"
    ILLUSTRATED = "illustrated"


class StoryTone(StrEnum):
    DOCUMENTARY = "documentary"
    SUSPENSEFUL = "suspenseful"
    EDUCATIONAL = "educational"
    DRAMATIC = "dramatic"
    LIGHTHEARTED = "lighthearted"
    INSPIRATIONAL = "inspirational"


class VisualType(StrEnum):
    CINEMATIC_IMAGE = "cinematic_image"
    PARALLAX = "parallax"
    CHARACTER_PORTRAIT = "character_portrait"
    HISTORICAL_MAP = "historical_map"
    TIMELINE = "timeline"
    INFOGRAPHIC = "infographic"
    COMPARISON = "comparison"
    NEWSPAPER = "newspaper"
    KINETIC_TYPOGRAPHY = "kinetic_typography"

    @property
    def needs_ai_image(self) -> bool:
        return self in (
            VisualType.CINEMATIC_IMAGE,
            VisualType.PARALLAX,
            VisualType.CHARACTER_PORTRAIT,
            VisualType.NEWSPAPER,
            VisualType.COMPARISON,
        )


class CameraMove(StrEnum):
    STATIC = "static"
    SLOW_ZOOM_IN = "slow_zoom_in"
    SLOW_ZOOM_OUT = "slow_zoom_out"
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    TILT_UP = "tilt_up"
    TILT_DOWN = "tilt_down"
    DRAMATIC_PUSH_IN = "dramatic_push_in"
    KEN_BURNS = "ken_burns"
    PARALLAX_DRIFT = "parallax_drift"
    HANDHELD = "handheld"
    CRASH_ZOOM = "crash_zoom"


class Effect(StrEnum):
    FOG = "fog"
    SMOKE = "smoke"
    DUST = "dust"
    EMBERS = "embers"
    RAIN = "rain"
    SNOW = "snow"
    BOKEH = "bokeh"
    LIGHT_RAYS = "light_rays"
    FLICKER = "flicker"
    LIGHTNING = "lightning"
    FILM_GRAIN = "film_grain"
    VIGNETTE_PULSE = "vignette_pulse"


class Transition(StrEnum):
    CUT = "cut"
    CROSSFADE = "crossfade"
    FADE_BLACK = "fade_black"
    FADE_WHITE = "fade_white"
    SLIDE_LEFT = "slide_left"
    SLIDE_UP = "slide_up"
    WIPE = "wipe"
    ZOOM = "zoom"
    CIRCLE_OPEN = "circle_open"
    DISSOLVE = "dissolve"
    PIXELIZE = "pixelize"
    RADIAL = "radial"


class CaptionAnimation(StrEnum):
    WORD_POP = "word_pop"
    KARAOKE = "karaoke"
    BOUNCE = "bounce"
    TYPEWRITER = "typewriter"
    SENTENCE = "sentence"


class CaptionPosition(StrEnum):
    TOP = "top"
    MIDDLE = "middle"
    BOTTOM = "bottom"


class SoundEffect(StrEnum):
    WHOOSH = "whoosh"
    IMPACT = "impact"
    RISER = "riser"
    WIND = "wind"
    RAIN = "rain"
    THUNDER = "thunder"
    FIRE = "fire"
    HEARTBEAT = "heartbeat"
    CLOCK_TICK = "clock_tick"
    PAPER = "paper"
    SHIMMER = "shimmer"
    DRONE = "drone"


class MusicMood(StrEnum):
    MYSTERY = "mystery"
    EPIC = "epic"
    CALM = "calm"
    TENSION = "tension"
    UPLIFTING = "uplifting"
    MELANCHOLY = "melancholy"
    NONE = "none"


class HookStyle(StrEnum):
    SHOCKING = "shocking"
    MYSTERIOUS = "mysterious"
    QUESTION = "question"
    CONTROVERSIAL = "controversial"
    EMOTIONAL = "emotional"
    CURIOSITY = "curiosity"


class ClaimConfidence(StrEnum):
    WELL_ESTABLISHED = "well_established"
    DEBATED = "debated"
    UNCERTAIN = "uncertain"


class ClaimVerdict(StrEnum):
    UNVERIFIED = "unverified"
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    NOT_FOUND = "not_found"


class AssetKind(StrEnum):
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    THUMBNAIL = "thumbnail"
    TRANSCRIPT = "transcript"


class AssetSource(StrEnum):
    GENERATED = "generated"
    PROCEDURAL = "procedural"
    UPLOADED = "uploaded"
    FIXTURE = "fixture"


class SceneAssetRole(StrEnum):
    IMAGE = "image"
    NARRATION = "narration"
    TRANSCRIPT = "transcript"
    CLIP = "clip"


class SeriesStatus(StrEnum):
    PLANNING = "planning"
    PLANNED = "planned"
    PRODUCING = "producing"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class IdeaStatus(StrEnum):
    IDEA = "idea"
    PLANNED = "planned"
    IN_PRODUCTION = "in_production"
    PUBLISHED = "published"
    ARCHIVED = "archived"
