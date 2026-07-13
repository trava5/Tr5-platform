"""HTTP API pro serverovy backend JARVIS."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from .config import BackendSettings
from .database import check_database
from .schemas import (
    ConversationDetail,
    ConversationSummary,
    LongTermDecisionCreate,
    LongTermDecisionItem,
    MemoryImportResult,
    MessageRequest,
    MessageResponse,
    ShortTermMemoryCreate,
    ShortTermMemoryItem,
)
from .services.agent_runtime import AgentRuntime
from .services.conversations import ConversationRepository
from .services.memory import MemoryRepository
from .services.memory_migration import import_sqlite_memory
from .services.realtime import RealtimeEventHub
from .storage import create_conversation_repository, create_memory_repository


def create_api_router(
    settings: BackendSettings,
    conversations: ConversationRepository | None = None,
    memory: MemoryRepository | None = None,
    agent_runtime: AgentRuntime | None = None,
    realtime_events: RealtimeEventHub | None = None,
) -> APIRouter:
    router = APIRouter(prefix=settings.api_prefix)
    conversations = conversations or create_conversation_repository(settings)
    memory = memory or create_memory_repository(settings)
    realtime_events = realtime_events or RealtimeEventHub()
    agent_runtime = agent_runtime or AgentRuntime(conversations, realtime_events=realtime_events)

    @router.get("/health")
    async def health() -> dict:
        return {
            "status": "ok",
            "service": settings.app_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @router.get("/status")
    async def status() -> dict:
        database = await check_database(settings)
        return {
            "status": "ok",
            "service": settings.app_name,
            "api_prefix": settings.api_prefix,
            "agent_runtime": {
                "connected": agent_runtime.state.connected,
                "detail": agent_runtime.state.detail,
            },
            "realtime": {
                "schema_version": realtime_events.schema_version,
                "connected_clients": realtime_events.connected_count,
            },
            "database": {
                "configured": database.configured,
                "ok": database.ok,
                "detail": database.detail,
            },
        }

    @router.websocket("/realtime")
    async def realtime(websocket: WebSocket) -> None:
        await realtime_events.connect(websocket)
        try:
            while True:
                message = await websocket.receive_text()
                if message.strip().lower() == "ping":
                    await websocket.send_json(
                        realtime_events.serialize(
                            realtime_events.create_event(
                                "pong",
                                payload={"message": "pong"},
                            )
                        )
                    )
        except WebSocketDisconnect:
            pass
        finally:
            await realtime_events.disconnect(websocket)

    @router.post("/messages", response_model=MessageResponse)
    async def create_message(message: MessageRequest) -> MessageResponse:
        return await agent_runtime.handle_message(message)

    @router.get("/conversations", response_model=list[ConversationSummary])
    async def list_conversations() -> list[ConversationSummary]:
        return await conversations.list()

    @router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
    async def get_conversation(conversation_id: str) -> ConversationDetail:
        conversation = await conversations.get(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Konverzacni relace nebyla nalezena.")
        return conversation

    @router.post("/memory/short-term")
    async def save_short_term_memory(item: ShortTermMemoryCreate) -> dict:
        item_id = await memory.save_short_term_turn(
            role=item.role,
            content=item.content,
            session_id=item.session_id,
            metadata=item.metadata,
        )
        if item_id is None:
            raise HTTPException(status_code=400, detail="Kratkodoby zaznam pameti nebyl ulozen.")
        return {"id": item_id}

    @router.get("/memory/short-term", response_model=list[ShortTermMemoryItem])
    async def list_short_term_memory(
        limit: int = 20,
        session_id: str = "",
    ) -> list[ShortTermMemoryItem]:
        return await memory.recent_short_term_turns(limit=limit, session_id=session_id)

    @router.get("/memory/short-term/search", response_model=list[ShortTermMemoryItem])
    async def search_short_term_memory(
        query: str,
        limit: int = 10,
    ) -> list[ShortTermMemoryItem]:
        return await memory.search_short_term_text(query=query, limit=limit)

    @router.delete("/memory/short-term")
    async def purge_short_term_memory(days: int = 31) -> dict:
        return {"deleted": await memory.purge_short_term(days=days)}

    @router.post("/memory/decisions")
    async def save_long_term_decision(item: LongTermDecisionCreate) -> dict:
        item_id = await memory.save_long_term_decision(item)
        if item_id is None:
            raise HTTPException(
                status_code=400,
                detail="Dlouhodobe rozhodnuti nebylo ulozeno. Chybi potvrzeni.",
            )
        return {"id": item_id}

    @router.get("/memory/decisions", response_model=list[LongTermDecisionItem])
    async def list_long_term_decisions(limit: int = 50) -> list[LongTermDecisionItem]:
        return await memory.list_long_term_decisions(limit=limit)

    @router.post("/memory/import/sqlite", response_model=MemoryImportResult)
    async def import_sqlite_memory_endpoint() -> MemoryImportResult:
        return await import_sqlite_memory(memory)

    return router
