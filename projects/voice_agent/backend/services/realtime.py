"""Realtime WebSocket event hub for backend clients."""

from __future__ import annotations

import asyncio
import threading
import uuid
from datetime import datetime, timezone

from fastapi import WebSocket

from backend.schemas import RealtimeEvent


SCHEMA_VERSION = "realtime.v1"
SUPPORTED_EVENT_TYPES = ("hello", "pong", "runtime_state", "message", "audio")


def _event_payload(event: RealtimeEvent) -> dict:
    if hasattr(event, "model_dump"):
        return event.model_dump(mode="json")
    payload = event.dict()
    timestamp = payload.get("timestamp")
    if isinstance(timestamp, datetime):
        payload["timestamp"] = timestamp.isoformat()
    return payload


class RealtimeEventHub:
    """Tracks WebSocket clients and broadcasts realtime events."""

    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_lock = threading.RLock()

    @property
    def schema_version(self) -> str:
        return SCHEMA_VERSION

    @property
    def connected_count(self) -> int:
        return len(self._clients)

    async def connect(self, websocket: WebSocket) -> None:
        with self._loop_lock:
            self._loop = asyncio.get_running_loop()
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)
        await websocket.send_json(
            _event_payload(
                self.create_event(
                    "hello",
                    payload={
                        "schema_version": SCHEMA_VERSION,
                        "supported_event_types": list(SUPPORTED_EVENT_TYPES),
                    },
                )
            )
        )

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(websocket)

    def create_event(
        self,
        event_type: str,
        *,
        channel: str = "backend",
        client_id: str | None = None,
        conversation_id: str | None = None,
        role: str | None = None,
        text: str | None = None,
        audio_mime_type: str | None = None,
        audio_base64: str | None = None,
        payload: dict[str, object] | None = None,
    ) -> RealtimeEvent:
        return RealtimeEvent(
            event_id=uuid.uuid4().hex,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            channel=channel,
            client_id=client_id,
            conversation_id=conversation_id,
            role=role,
            text=text,
            audio_mime_type=audio_mime_type,
            audio_base64=audio_base64,
            payload=payload or {},
        )

    def serialize(self, event: RealtimeEvent) -> dict:
        return _event_payload(event)

    async def publish(
        self,
        event_type: str,
        *,
        channel: str = "backend",
        client_id: str | None = None,
        conversation_id: str | None = None,
        role: str | None = None,
        text: str | None = None,
        audio_mime_type: str | None = None,
        audio_base64: str | None = None,
        payload: dict[str, object] | None = None,
    ) -> RealtimeEvent:
        event = self.create_event(
            event_type,
            channel=channel,
            client_id=client_id,
            conversation_id=conversation_id,
            role=role,
            text=text,
            audio_mime_type=audio_mime_type,
            audio_base64=audio_base64,
            payload=payload,
        )
        await self.broadcast(event)
        return event

    def publish_nowait(
        self,
        event_type: str,
        *,
        channel: str = "backend",
        client_id: str | None = None,
        conversation_id: str | None = None,
        role: str | None = None,
        text: str | None = None,
        audio_mime_type: str | None = None,
        audio_base64: str | None = None,
        payload: dict[str, object] | None = None,
    ) -> bool:
        with self._loop_lock:
            loop = self._loop
        if loop is None or not loop.is_running():
            return False

        coroutine = self.publish(
            event_type,
            channel=channel,
            client_id=client_id,
            conversation_id=conversation_id,
            role=role,
            text=text,
            audio_mime_type=audio_mime_type,
            audio_base64=audio_base64,
            payload=payload,
        )
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None
        if running_loop is loop:
            loop.create_task(coroutine)
        else:
            asyncio.run_coroutine_threadsafe(coroutine, loop)
        return True

    async def broadcast(self, event: RealtimeEvent) -> None:
        payload = _event_payload(event)
        async with self._lock:
            clients = list(self._clients)

        stale: list[WebSocket] = []
        for websocket in clients:
            try:
                await websocket.send_json(payload)
            except Exception:
                stale.append(websocket)

        if stale:
            async with self._lock:
                for websocket in stale:
                    self._clients.discard(websocket)
