"""Factory pro backendova uloziste."""

from __future__ import annotations

from .config import BackendSettings
from .db.session import create_engine, create_sessionmaker
from .services.conversations import (
    ConversationRepository,
    FallbackConversationRepository,
    InMemoryConversationRepository,
)
from .services.memory import FallbackMemoryRepository, InMemoryMemoryRepository, MemoryRepository
from .services.postgres_conversations import PostgresConversationRepository
from .services.postgres_memory import PostgresMemoryRepository


def create_conversation_repository(settings: BackendSettings) -> ConversationRepository:
    """Vrati repository pro konverzace.

    Bez DATABASE_URL se pouziva in-memory fallback, aby API zustalo funkcni i v
    lokalnim vyvojovem rezimu bez databaze.
    """

    if settings.database_configured:
        engine = create_engine(settings)
        postgres_repository = PostgresConversationRepository(
            engine=engine,
            sessionmaker=create_sessionmaker(engine),
            schema=settings.database_schema,
        )
        return FallbackConversationRepository(postgres_repository)

    return InMemoryConversationRepository()


def create_memory_repository(settings: BackendSettings) -> MemoryRepository:
    """Vrati repository pro kratkodobou pamet a dlouhodoba rozhodnuti."""

    if settings.database_configured:
        engine = create_engine(settings)
        postgres_repository = PostgresMemoryRepository(
            engine=engine,
            sessionmaker=create_sessionmaker(engine),
            schema=settings.database_schema,
        )
        return FallbackMemoryRepository(postgres_repository)

    return InMemoryMemoryRepository()
