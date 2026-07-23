"""Agentni runtime kontrakt pro backend."""

from __future__ import annotations

import inspect
import threading
from dataclasses import dataclass
from typing import Awaitable, Callable

from backend.schemas import MessageRequest, MessageResponse
from backend.services.conversations import ConversationRepository
from backend.services.realtime import RealtimeEventHub


@dataclass(frozen=True)
class RuntimeState:
    connected: bool = False
    detail: str = "Zivy agentni runtime zatim neni pripojeny k backendu."


LiveMessageHandler = Callable[
    [MessageRequest, str], str | MessageResponse | Awaitable[str | MessageResponse]
]


class AgentRuntime:
    """Prvni backendova mezivrstva pro budouci sdileny agentni runtime."""

    def __init__(
        self,
        conversations: ConversationRepository,
        realtime_events: RealtimeEventHub | None = None,
    ) -> None:
        self._state = RuntimeState()
        self._conversations = conversations
        self._realtime_events = realtime_events
        self._handler: LiveMessageHandler | None = None
        self._lock = threading.RLock()

    @property
    def state(self) -> RuntimeState:
        with self._lock:
            return self._state

    def connect(self, handler: LiveMessageHandler, detail: str = "Zivy runtime je pripojen.") -> None:
        with self._lock:
            self._handler = handler
            self._state = RuntimeState(connected=True, detail=detail)
            state = self._state
        self._publish_runtime_state(state)

    def disconnect(
        self,
        detail: str = "Zivy agentni runtime zatim neni pripojeny k backendu.",
    ) -> None:
        with self._lock:
            self._handler = None
            self._state = RuntimeState(connected=False, detail=detail)
            state = self._state
        self._publish_runtime_state(state)

    async def handle_message(self, request: MessageRequest) -> MessageResponse:
        conversation = await self._conversations.get_or_create(
            conversation_id=request.conversation_id,
            channel=request.channel,
            client_id=request.client_id,
        )
        user_message = await self._conversations.append_message(
            conversation_id=conversation.conversation_id,
            role="user",
            text=request.text,
            channel=request.channel,
            client_id=request.client_id,
            status="received",
        )
        await self._publish_message(
            role="user",
            text=request.text,
            channel=request.channel,
            client_id=request.client_id,
            conversation_id=conversation.conversation_id,
            message_id=user_message.message_id,
            status="received",
        )

        with self._lock:
            handler = self._handler
            state = self._state

        if not handler or not state.connected:
            text = (
                "Backend zpravu prijal, ale zivy agentni runtime je zatim "
                "spusteny jen v desktopove aplikaci."
            )
            assistant_message = await self._conversations.append_message(
                conversation_id=conversation.conversation_id,
                role="assistant",
                text=text,
                channel=request.channel,
                client_id=request.client_id,
                status="runtime_unavailable",
            )
            await self._publish_message(
                role="assistant",
                text=text,
                channel=request.channel,
                client_id=request.client_id,
                conversation_id=conversation.conversation_id,
                message_id=assistant_message.message_id,
                status="runtime_unavailable",
            )
            return MessageResponse(
                status="runtime_unavailable",
                message_id=user_message.message_id,
                conversation_id=conversation.conversation_id,
                text=text,
                detail=state.detail,
            )

        try:
            response = handler(request, conversation.conversation_id)
            if inspect.isawaitable(response):
                response = await response
            text = self._extract_text(response)
        except Exception as exc:
            text = f"Zivy agentni runtime selhal: {exc}"
            assistant_message = await self._conversations.append_message(
                conversation_id=conversation.conversation_id,
                role="assistant",
                text=text,
                channel=request.channel,
                client_id=request.client_id,
                status="runtime_error",
            )
            await self._publish_message(
                role="assistant",
                text=text,
                channel=request.channel,
                client_id=request.client_id,
                conversation_id=conversation.conversation_id,
                message_id=assistant_message.message_id,
                status="runtime_error",
            )
            return MessageResponse(
                status="runtime_error",
                message_id=user_message.message_id,
                conversation_id=conversation.conversation_id,
                text=text,
                detail=str(exc),
            )

        if not text:
            text = "Zivy agentni runtime nevratil zadnou odpoved."
            status = "runtime_error"
        else:
            status = "ok"

        assistant_message = await self._conversations.append_message(
            conversation_id=conversation.conversation_id,
            role="assistant",
            text=text,
            channel=request.channel,
            client_id=request.client_id,
            status=status,
        )
        await self._publish_message(
            role="assistant",
            text=text,
            channel=request.channel,
            client_id=request.client_id,
            conversation_id=conversation.conversation_id,
            message_id=assistant_message.message_id,
            status=status,
        )
        return MessageResponse(
            status=status,
            message_id=user_message.message_id,
            conversation_id=conversation.conversation_id,
            text=text,
            detail=state.detail,
        )

    @staticmethod
    def _extract_text(response: str | MessageResponse) -> str:
        if isinstance(response, MessageResponse):
            return str(response.text or "").strip()
        return str(response or "").strip()

    def _publish_runtime_state(self, state: RuntimeState) -> None:
        if not self._realtime_events:
            return
        self._realtime_events.publish_nowait(
            "runtime_state",
            payload={
                "connected": state.connected,
                "detail": state.detail,
            },
        )

    async def _publish_message(
        self,
        *,
        role: str,
        text: str,
        channel: str,
        client_id: str | None,
        conversation_id: str,
        message_id: str,
        status: str,
    ) -> None:
        if not self._realtime_events:
            return
        await self._realtime_events.publish(
            "message",
            channel=channel,
            client_id=client_id,
            conversation_id=conversation_id,
            role=role,
            text=text,
            payload={
                "message_id": message_id,
                "status": status,
            },
        )
