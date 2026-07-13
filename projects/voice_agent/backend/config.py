"""Konfigurace serveroveho backendu."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]


def _load_env_file(path: Path = BASE_DIR / ".env") -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = value.strip().strip('"').strip("'")


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "enabled", "ano"}


@dataclass(frozen=True)
class BackendSettings:
    app_name: str
    host: str
    port: int
    reload: bool
    database_url: str
    database_name: str
    database_user: str
    database_password: str
    database_schema: str
    api_prefix: str = "/api/v1"

    @property
    def database_configured(self) -> bool:
        return bool(self.database_url.strip())


def load_settings() -> BackendSettings:
    _load_env_file()
    return BackendSettings(
        app_name=os.getenv("JARVIS_BACKEND_APP_NAME", "JARVIS Backend"),
        host=os.getenv("JARVIS_BACKEND_HOST", "127.0.0.1"),
        port=int(os.getenv("JARVIS_BACKEND_PORT", "8000")),
        reload=_env_bool("JARVIS_BACKEND_RELOAD", default=False),
        database_url=os.getenv("DATABASE_URL", "").strip(),
        database_name=os.getenv("DATABASE_NAME", "postgres").strip(),
        database_user=os.getenv("DATABASE_USER", "").strip(),
        database_password=os.getenv("DATABASE_PASS", "").strip(),
        database_schema=os.getenv("DATABASE_SCHEMA", "").strip(),
    )
