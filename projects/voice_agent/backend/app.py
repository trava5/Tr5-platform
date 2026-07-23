"""FastAPI aplikace pro JARVIS backend."""

from __future__ import annotations

from fastapi import FastAPI

from .api import create_api_router
from .config import BASE_DIR, BackendSettings, load_settings
from .services.agent_runtime import AgentRuntime
from .services.gemini_chat_handler import build_handler
from .services.realtime import RealtimeEventHub
from .storage import create_conversation_repository, create_memory_repository


def create_app(settings: BackendSettings | None = None) -> FastAPI:
    settings = settings or load_settings()
    conversations = create_conversation_repository(settings)
    memory = create_memory_repository(settings)
    realtime_events = RealtimeEventHub()
    agent_runtime = AgentRuntime(conversations, realtime_events=realtime_events)

    if settings.gemini_api_key:
        handler = build_handler(
            api_key=settings.gemini_api_key,
            model=settings.gemini_text_model,
            profiles_root=BASE_DIR / "profiles",
            memory=memory,
        )
        agent_runtime.connect(handler, detail="Gemini generate_content runtime je pripojen.")

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Serverovy backend pro viceklientskou architekturu JARVIS.",
    )
    app.state.agent_runtime = agent_runtime
    app.state.realtime_events = realtime_events
    app.include_router(
        create_api_router(
            settings,
            conversations=conversations,
            memory=memory,
            agent_runtime=agent_runtime,
            realtime_events=realtime_events,
        )
    )
    return app
