"""Obecný HTTP klient pro backend API JARVIS."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import requests


DEFAULT_API_PREFIX = "/api/v1"
DEFAULT_FALLBACK_STATUSES = frozenset(
    {"runtime_unavailable", "not_implemented", "runtime_error"}
)


class BackendClientError(RuntimeError):
    """Očekávaná chyba backend klienta, při které má volající použít fallback."""


@dataclass(frozen=True)
class BackendClientConfig:
    enabled: bool = True
    base_url: str = "http://127.0.0.1:8000"
    api_prefix: str = DEFAULT_API_PREFIX
    connect_timeout_seconds: float = 2.5
    timeout_seconds: float = 95.0
    fallback_statuses: frozenset[str] = field(default_factory=lambda: DEFAULT_FALLBACK_STATUSES)


@dataclass(frozen=True)
class BackendMessageResult:
    status: str
    text: str
    conversation_id: str | None = None
    message_id: str | None = None
    detail: str | None = None
    fallback_statuses: frozenset[str] = field(default_factory=lambda: DEFAULT_FALLBACK_STATUSES)

    @property
    def should_fallback(self) -> bool:
        return self.status in self.fallback_statuses or not self.text.strip()


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on", "enabled", "ano"}


def _parse_float(value: str | None, default: float) -> float:
    if value is None or not str(value).strip():
        return default
    try:
        return float(str(value).strip())
    except ValueError:
        return default


def _normalize_api_prefix(value: str | None) -> str:
    raw = str(value or DEFAULT_API_PREFIX).strip() or DEFAULT_API_PREFIX
    return raw if raw.startswith("/") else f"/{raw}"


def _default_base_url() -> str:
    explicit = (
        os.getenv("JARVIS_BACKEND_BASE_URL")
        or os.getenv("JARVIS_BACKEND_URL")
        or ""
    ).strip()
    if explicit:
        return explicit.rstrip("/")
    host = os.getenv("JARVIS_BACKEND_HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = os.getenv("JARVIS_BACKEND_PORT", "8000").strip() or "8000"
    return f"http://{host}:{port}"


def load_config() -> BackendClientConfig:
    return BackendClientConfig(
        enabled=_parse_bool(os.getenv("JARVIS_BACKEND_CLIENT_ENABLED"), default=True),
        base_url=_default_base_url(),
        api_prefix=_normalize_api_prefix(os.getenv("JARVIS_BACKEND_API_PREFIX")),
        connect_timeout_seconds=_parse_float(
            os.getenv("JARVIS_BACKEND_CONNECT_TIMEOUT_SECONDS"),
            2.5,
        ),
        timeout_seconds=_parse_float(os.getenv("JARVIS_BACKEND_TIMEOUT_SECONDS"), 95.0),
    )


class BackendClient:
    def __init__(self, config: BackendClientConfig | None = None) -> None:
        self.config = config or load_config()

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    @property
    def messages_url(self) -> str:
        return f"{self.config.base_url.rstrip('/')}{self.config.api_prefix}/messages"

    def send_message(
        self,
        text: str,
        *,
        client_id: str,
        channel: str,
        conversation_id: str | None = None,
        want_audio: bool = False,
    ) -> BackendMessageResult:
        if not self.config.enabled:
            raise BackendClientError("Backend klient je vypnutý.")

        payload = {
            "text": str(text or "").strip(),
            "channel": str(channel or "api").strip() or "api",
            "client_id": client_id,
            "conversation_id": conversation_id,
            "want_audio": bool(want_audio),
        }
        if not payload["text"]:
            raise BackendClientError("Nelze odeslat prázdnou zprávu do backendu.")

        try:
            response = requests.post(
                self.messages_url,
                json=payload,
                timeout=(self.config.connect_timeout_seconds, self.config.timeout_seconds),
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            raise BackendClientError(f"Backend není dostupný: {exc}") from exc
        except ValueError as exc:
            raise BackendClientError("Backend vrátil neplatnou JSON odpověď.") from exc

        status = str(data.get("status", "") or "").strip()
        if not status:
            raise BackendClientError("Backend nevrátil stav odpovědi.")

        return BackendMessageResult(
            status=status,
            text=str(data.get("text", "") or ""),
            conversation_id=str(data.get("conversation_id", "") or "") or None,
            message_id=str(data.get("message_id", "") or "") or None,
            detail=str(data.get("detail", "") or "") or None,
            fallback_statuses=self.config.fallback_statuses,
        )
