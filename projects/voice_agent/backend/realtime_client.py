"""Synchronous WebSocket client for backend realtime events."""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urlparse, urlunparse

from websockets.sync.client import connect


DEFAULT_API_PREFIX = "/api/v1"
RealtimeEventHandler = Callable[[dict], None]
RealtimeLogger = Callable[[str], None]


@dataclass(frozen=True)
class BackendRealtimeClientConfig:
    enabled: bool = True
    base_url: str = "http://127.0.0.1:8000"
    api_prefix: str = DEFAULT_API_PREFIX
    realtime_url: str = ""
    reconnect_seconds: float = 3.0
    open_timeout_seconds: float = 2.5


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


def _default_realtime_url(base_url: str, api_prefix: str) -> str:
    explicit = (
        os.getenv("JARVIS_BACKEND_REALTIME_URL")
        or os.getenv("JARVIS_BACKEND_WS_URL")
        or ""
    ).strip()
    if explicit:
        return explicit

    parsed = urlparse(base_url if "://" in base_url else f"http://{base_url}")
    scheme = "wss" if parsed.scheme == "https" else "ws"
    path = f"{api_prefix.rstrip('/')}/realtime"
    return urlunparse((scheme, parsed.netloc, path, "", "", ""))


def load_config() -> BackendRealtimeClientConfig:
    base_url = _default_base_url()
    api_prefix = _normalize_api_prefix(os.getenv("JARVIS_BACKEND_API_PREFIX"))
    return BackendRealtimeClientConfig(
        enabled=_parse_bool(os.getenv("JARVIS_BACKEND_REALTIME_ENABLED"), default=True),
        base_url=base_url,
        api_prefix=api_prefix,
        realtime_url=_default_realtime_url(base_url, api_prefix),
        reconnect_seconds=_parse_float(
            os.getenv("JARVIS_BACKEND_REALTIME_RECONNECT_SECONDS"),
            3.0,
        ),
        open_timeout_seconds=_parse_float(
            os.getenv("JARVIS_BACKEND_REALTIME_OPEN_TIMEOUT_SECONDS"),
            2.5,
        ),
    )


class BackendRealtimeClient:
    def __init__(self, config: BackendRealtimeClientConfig | None = None) -> None:
        self.config = config or load_config()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(
        self,
        on_event: RealtimeEventHandler,
        logger: RealtimeLogger | None = None,
    ) -> bool:
        if not self.config.enabled:
            return False
        if self.is_running:
            return True
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            args=(on_event, logger),
            name="JarvisBackendRealtimeClient",
            daemon=True,
        )
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop.set()

    def _run(
        self,
        on_event: RealtimeEventHandler,
        logger: RealtimeLogger | None,
    ) -> None:
        while not self._stop.is_set():
            try:
                with connect(
                    self.config.realtime_url,
                    open_timeout=self.config.open_timeout_seconds,
                    close_timeout=1,
                ) as websocket:
                    self._log(logger, "Backend realtime klient je připojený.")
                    for message in websocket:
                        if self._stop.is_set():
                            break
                        event = self._parse_event(message)
                        if event is not None:
                            on_event(event)
            except Exception as exc:
                if not self._stop.is_set():
                    self._log(logger, f"Backend realtime reconnect: {exc}")
                    self._sleep_until_stop(self.config.reconnect_seconds)

    def _sleep_until_stop(self, seconds: float) -> None:
        self._stop.wait(max(0.2, seconds))

    @staticmethod
    def _parse_event(message: str | bytes) -> dict | None:
        if isinstance(message, bytes):
            message = message.decode("utf-8", errors="replace")
        try:
            data = json.loads(message)
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
        return data if isinstance(data, dict) else None

    @staticmethod
    def _log(logger: RealtimeLogger | None, message: str) -> None:
        if logger:
            logger(message)
