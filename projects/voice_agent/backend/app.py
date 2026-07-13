"""FastAPI aplikace pro JARVIS backend."""

from __future__ import annotations

from fastapi import FastAPI

from .api import create_api_router
from .config import BackendSettings, load_settings
from .services.agent_runtime import AgentRuntime
from .services.realtime import RealtimeEventHub
from .storage import create_conversation_repository, create_memory_repository


def create_app(settings: BackendSettings | None = None) -> FastAPI:
    settings = settings or load_settings()
    conversations = create_conversation_repository(settings)
    memory = create_memory_repository(settings)
    realtime_events = RealtimeEventHub()
    agent_runtime = AgentRuntime(conversations, realtime_events=realtime_events)
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


app = create_app()
