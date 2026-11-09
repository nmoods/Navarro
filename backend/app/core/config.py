"""Application settings, loaded from environment variables (prefix ``REELFORGE_``) and ``.env``."""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class AppEnv(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class AuthMode(StrEnum):
    LOCAL = "local"
    SUPABASE = "supabase"


class StorageBackendKind(StrEnum):
    LOCAL = "local"
    R2 = "r2"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="REELFORGE_",
        env_file=(BACKEND_ROOT.parent / ".env", BACKEND_ROOT / ".env"),
        extra="ignore",
    )

    app_env: AppEnv = AppEnv.DEVELOPMENT
    app_name: str = "ReelForge AI"
    public_api_url: str = "http://127.0.0.1:8000"
    log_level: str = "INFO"

    database_url: str = f"sqlite:///{(BACKEND_ROOT / 'var' / 'reelforge.db').as_posix()}"

    auth_mode: AuthMode = AuthMode.LOCAL
    jwt_secret: SecretStr = SecretStr("dev-only-insecure-secret-change-me-0123456789")
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    supabase_url: str | None = None
    supabase_jwt_audience: str = "authenticated"

    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    storage_backend: StorageBackendKind = StorageBackendKind.LOCAL
    storage_root: Path = BACKEND_ROOT / "var" / "storage"
    work_root: Path = BACKEND_ROOT / "var" / "work"
    media_url_ttl_seconds: int = 3600
    r2_account_id: str | None = None
    r2_bucket: str | None = None
    r2_access_key_id: SecretStr | None = None
    r2_secret_access_key: SecretStr | None = None

    llm_provider: str = "ollama"
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:4b"
    llm_timeout_seconds: float = 600.0

    image_provider: str = "auto"
    comfyui_url: str = "http://127.0.0.1:8188"
    comfyui_checkpoint: str = "dreamshaper_8.safetensors"
    comfyui_lcm_lora: str | None = "lcm-lora-sdv1-5.safetensors"
    comfyui_steps: int = 6
    comfyui_cfg: float = 1.5
    comfyui_timeout_seconds: float = 600.0

    tts_provider: str = "kokoro"
    kokoro_model_path: Path = BACKEND_ROOT.parent / ".runtime" / "models" / "kokoro" / "kokoro-v1.0.onnx"
    kokoro_voices_path: Path = BACKEND_ROOT.parent / ".runtime" / "models" / "kokoro" / "voices-v1.0.bin"

    stt_provider: str = "faster_whisper"
    whisper_model: str = "base.en"
    whisper_compute_type: str = "int8"

    research_enabled: bool = True
    research_user_agent: str = "ReelForgeAI/0.1 (self-hosted; fact-check module)"

    embedded_worker: bool = True
    worker_concurrency: int = 1
    job_timeout_seconds: int = 3600
    job_max_attempts: int = 2
    job_stale_after_seconds: int = 300

    max_request_bytes: int = 30 * 1024 * 1024
    max_upload_bytes: int = 25 * 1024 * 1024
    rate_limit_per_minute: int = 120
    generation_rate_limit_per_hour: int = 30
    max_active_jobs_per_user: int = 3
    render_timeout_seconds: int = 1800
    ffmpeg_threads: int = 4

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def _guard_production(self) -> Settings:
        if self.app_env is AppEnv.PRODUCTION:
            secret = self.jwt_secret.get_secret_value()
            if secret.startswith("dev-only") or len(secret) < 32:
                raise ValueError("REELFORGE_JWT_SECRET must be set to a random value of 32+ characters")
            if any(p.startswith("fixture") for p in (self.llm_provider, self.image_provider, self.tts_provider)):
                raise ValueError("Fixture (test) providers cannot be used in production")
            if "*" in self.cors_origins:
                raise ValueError("Wildcard CORS origins are not allowed in production")
        if self.auth_mode is AuthMode.SUPABASE and not self.supabase_url:
            raise ValueError("REELFORGE_SUPABASE_URL is required when auth_mode=supabase")
        return self

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
