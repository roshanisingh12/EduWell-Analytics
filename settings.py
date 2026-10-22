"""
EduWell Analytics - runtime configuration.

Every setting can be overridden with an environment variable prefixed with
EDUWELL_ (see .env.example). Values are read once at startup.
"""

import os
import tempfile
from dataclasses import dataclass
from typing import Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _env(name: str, default: str) -> str:
    val = os.environ.get(f"EDUWELL_{name}")
    if val is None:
        val = os.environ.get(name, default)
    return str(val).strip()


def _env_bool(name: str, default: bool) -> bool:
    return _env(name, str(default)).lower() in ("1", "true", "yes", "on")


def _env_list(name: str) -> Tuple[str, ...]:
    return tuple(item.strip() for item in _env(name, "").split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    host: str
    port: int
    log_level: str
    max_upload_mb: float
    max_rows: int
    session_ttl_minutes: int
    max_sessions: int
    analysis_wait_seconds: float
    cors_origins: Tuple[str, ...]
    cookie_secure: bool
    enable_docs: bool
    work_dir: str
    sample_path: str

    @property
    def max_upload_bytes(self) -> int:
        return int(self.max_upload_mb * 1024 * 1024)


def load_settings() -> Settings:
    return Settings(
        host=_env("HOST", "127.0.0.1"),
        port=int(_env("PORT", "8000")),
        log_level=_env("LOG_LEVEL", "INFO").upper(),
        max_upload_mb=float(_env("MAX_UPLOAD_MB", "25")),
        max_rows=int(_env("MAX_ROWS", "100000")),
        session_ttl_minutes=int(_env("SESSION_TTL_MINUTES", "120")),
        max_sessions=int(_env("MAX_SESSIONS", "200")),
        analysis_wait_seconds=float(_env("ANALYSIS_WAIT_SECONDS", "60")),
        cors_origins=_env_list("CORS_ORIGINS"),
        cookie_secure=_env_bool("COOKIE_SECURE", False),
        enable_docs=_env_bool("ENABLE_DOCS", True),
        work_dir=_env("WORK_DIR", os.path.join(tempfile.gettempdir(), "eduwell")),
        sample_path=_env("SAMPLE_PATH", os.path.join(BASE_DIR, "student_lifestyle_dataset.csv")),
    )
