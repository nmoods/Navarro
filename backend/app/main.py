"""FastAPI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import account, auth, creative, jobs, media, planning, projects, scenes
from app.core.config import AppEnv, get_settings
from app.core.errors import install_error_handlers
from app.core.logging import configure_logging
from app.core.middleware import SecurityMiddleware

logger = logging.getLogger("reelforge")

BUILTIN_TEMPLATES = [
    ("History Mystery", "mystery", {"visual_style": "dark_mystery", "story_tone": "suspenseful", "voice_id": "am_michael",
                                     "caption_style": {"animation": "karaoke", "font": "Montserrat"}, "music": {"mood": "mystery"}}),
    ("Science Explainer", "education", {"visual_style": "minimalist_motion", "story_tone": "educational", "voice_id": "af_heart",
                                         "caption_style": {"animation": "word_pop", "font": "Inter"}, "music": {"mood": "uplifting"}}),
    ("Archival Documentary", "history", {"visual_style": "vintage_documentary", "story_tone": "documentary", "voice_id": "bm_george",
                                          "caption_style": {"animation": "sentence", "font": "Playfair Display", "uppercase": False},
                                          "music": {"mood": "melancholy"}}),
    ("Epic Battles", "history", {"visual_style": "historical_realism", "story_tone": "dramatic", "voice_id": "am_fenrir",
                                  "caption_style": {"animation": "bounce", "font": "Anton"}, "music": {"mood": "epic"}}),
    ("Geography Facts", "geography", {"visual_style": "cinematic_documentary", "story_tone": "educational", "voice_id": "bf_emma",
                                       "caption_style": {"animation": "karaoke", "font": "Oswald"}, "music": {"mood": "calm"}}),
]  # fmt: skip


def run_migrations() -> None:
    from alembic import command
    from alembic.config import Config

    from app.core.config import BACKEND_ROOT
    from app.infrastructure.database.session import get_engine

    get_engine()  # creates the SQLite folder if needed before Alembic connects
    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    command.upgrade(cfg, "head")


def seed_templates() -> None:
    from sqlalchemy import select

    from app.infrastructure.database.models import Template
    from app.infrastructure.database.session import session_scope

    with session_scope() as session:
        existing = set(session.scalars(select(Template.name).where(Template.is_builtin.is_(True))))
        for name, category, config in BUILTIN_TEMPLATES:
            if name not in existing:
                session.add(Template(name=name, category=category, config=config, is_builtin=True, is_public=True,
                                     description=f"Built-in {category} starting point"))  # fmt: skip


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    if settings.app_env is not AppEnv.TEST:
        run_migrations()
    seed_templates()
    worker = None
    if settings.embedded_worker:
        from app.infrastructure.database.session import get_session_factory
        from app.infrastructure.providers import get_providers
        from app.infrastructure.storage.base import get_storage
        from app.workers.runner import Worker

        worker = Worker(settings, get_session_factory(), get_providers(), get_storage(settings))
        worker.start_background()
    logger.info("ReelForge API started (env=%s, auth=%s)", settings.app_env.value, settings.auth_mode.value)
    yield
    if worker:
        worker.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    prod = settings.app_env is AppEnv.PRODUCTION
    app = FastAPI(
        title="ReelForge AI API", version="0.1.0", lifespan=lifespan,
        docs_url=None if prod else "/api/docs", redoc_url=None, openapi_url=None if prod else "/api/openapi.json",
    )  # fmt: skip
    install_error_handlers(app)
    app.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Requested-With", "X-Request-Id"],
        expose_headers=["X-Request-Id"], max_age=600,
    )  # fmt: skip
    app.add_middleware(SecurityMiddleware, max_body=settings.max_request_bytes, per_minute=settings.rate_limit_per_minute, hsts=prod)

    api = APIRouter(prefix="/api/v1")
    for module in (auth, projects, scenes, jobs, media, creative, planning, account):
        api.include_router(module.router)

    @api.get("/health", tags=["system"])
    def health() -> dict:
        return {"status": "ok", "service": "reelforge-api"}

    app.include_router(api)
    return app


app = create_app()
