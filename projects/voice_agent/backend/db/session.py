"""Pomocne funkce pro SQLAlchemy async databazovou vrstvu."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from backend.config import BackendSettings
from backend.db.base import Base


def quote_identifier(identifier: str) -> str:
    """Vrati bezpecne citovany PostgreSQL identifikator."""

    return '"' + identifier.replace('"', '""') + '"'


def create_engine(settings: BackendSettings) -> AsyncEngine:
    candidate = (
        settings.database_url
        if "://" in settings.database_url
        else f"postgresql+asyncpg://{settings.database_url}"
    )
    url = make_url(candidate)
    drivername = (
        "postgresql+asyncpg"
        if url.drivername in {"postgresql", "postgres"}
        else url.drivername
    )
    url = url.set(drivername=drivername)
    if settings.database_user and not url.username:
        url = url.set(username=settings.database_user)
    if settings.database_password and not url.password:
        url = url.set(password=settings.database_password)
    if settings.database_name and not url.database:
        url = url.set(database=settings.database_name)
    return create_async_engine(url, pool_pre_ping=True)


def create_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def configure_schema(session: AsyncSession, schema: str) -> None:
    if not schema:
        return
    await session.execute(text(f"SET search_path TO {quote_identifier(schema)}"))


async def initialize_database(engine: AsyncEngine, schema: str = "") -> None:
    async with engine.begin() as connection:
        if schema:
            quoted_schema = quote_identifier(schema)
            await connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {quoted_schema}"))
            await connection.execute(text(f"SET search_path TO {quoted_schema}"))
        await connection.run_sync(Base.metadata.create_all)
