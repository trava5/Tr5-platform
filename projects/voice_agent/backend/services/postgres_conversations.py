"""PostgreSQL implementace repository pro konverzacni relace."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from backend.db.models import Client, Conversation, Message
from backend.db.session import configure_schema, initialize_database
from backend.schemas import ConversationDetail, ConversationSummary, StoredMessage
from backend.services.conversations import ConversationRecord, ConversationRepository


class PostgresConversationRepository(ConversationRepository):
    """Repository pro trvale ulozeni konverzaci v PostgreSQL."""

    def __init__(
        self,
        engine: AsyncEngine,
        sessionmaker: async_sessionmaker[AsyncSession],
        schema: str = "",
    ) -> None:
        self._engine = engine
        self._sessionmaker = sessionmaker
        self._schema = schema
        self._initialized = False
        self._init_lock = asyncio.Lock()

    async def get_or_create(
        self,
        conversation_id: str | None,
        channel: str,
        client_id: str | None,
    ) -> ConversationRecord:
        await self._ensure_initialized()
        async with self._sessionmaker() as session:
            await self._configure(session)
            if client_id:
                await self._ensure_client(session, client_id, channel)

            record_id = conversation_id or f"conv_{uuid4().hex}"
            conversation = await session.get(Conversation, record_id)
            if conversation is None:
                conversation = Conversation(
                    id=record_id,
                    client_id=client_id,
                    channel=channel,
                )
                session.add(conversation)
            else:
                conversation.updated_at = datetime.now(timezone.utc)

            await session.commit()
            await session.refresh(conversation)
            return self._to_record(conversation)

    async def append_message(
        self,
        conversation_id: str,
        role: str,
        text: str,
        channel: str,
        client_id: str | None,
        status: str | None = None,
    ) -> StoredMessage:
        await self._ensure_initialized()
        async with self._sessionmaker() as session:
            await self._configure(session)
            if client_id:
                await self._ensure_client(session, client_id, channel)

            conversation = await session.get(Conversation, conversation_id)
            if conversation is None:
                conversation = Conversation(
                    id=conversation_id,
                    client_id=client_id,
                    channel=channel,
                )
                session.add(conversation)
                await session.flush()

            message = Message(
                id=f"msg_{uuid4().hex}",
                conversation_id=conversation_id,
                client_id=client_id,
                role=role,
                text=text,
                channel=channel,
                status=status,
            )
            conversation.updated_at = datetime.now(timezone.utc)
            session.add(message)
            await session.commit()
            await session.refresh(message)
            return self._to_message(message)

    async def get(self, conversation_id: str) -> ConversationDetail | None:
        await self._ensure_initialized()
        async with self._sessionmaker() as session:
            await self._configure(session)
            result = await session.execute(
                select(Conversation)
                .options(selectinload(Conversation.messages))
                .where(Conversation.id == conversation_id)
            )
            conversation = result.scalar_one_or_none()
            if conversation is None:
                return None
            return self._to_detail(conversation)

    async def list(self) -> list[ConversationSummary]:
        await self._ensure_initialized()
        async with self._sessionmaker() as session:
            await self._configure(session)
            result = await session.execute(
                select(Conversation)
                .options(selectinload(Conversation.messages))
                .order_by(Conversation.updated_at.desc())
            )
            return [self._to_summary(conversation) for conversation in result.scalars()]

    async def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        async with self._init_lock:
            if self._initialized:
                return
            await initialize_database(self._engine, self._schema)
            self._initialized = True

    async def _configure(self, session: AsyncSession) -> None:
        await configure_schema(session, self._schema)

    @staticmethod
    async def _ensure_client(session: AsyncSession, client_id: str, channel: str) -> None:
        client = await session.get(Client, client_id)
        if client is None:
            session.add(Client(id=client_id, default_channel=channel))
        elif not client.default_channel:
            client.default_channel = channel

    @staticmethod
    def _to_record(conversation: Conversation) -> ConversationRecord:
        return ConversationRecord(
            conversation_id=conversation.id,
            channel=conversation.channel,
            client_id=conversation.client_id,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )

    @staticmethod
    def _to_message(message: Message) -> StoredMessage:
        return StoredMessage(
            message_id=message.id,
            role=message.role,
            text=message.text,
            channel=message.channel,
            client_id=message.client_id,
            created_at=message.created_at,
            status=message.status,
        )

    @classmethod
    def _to_summary(cls, conversation: Conversation) -> ConversationSummary:
        return ConversationSummary(
            conversation_id=conversation.id,
            client_id=conversation.client_id,
            channel=conversation.channel,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            message_count=len(conversation.messages),
        )

    @classmethod
    def _to_detail(cls, conversation: Conversation) -> ConversationDetail:
        summary = cls._to_summary(conversation)
        messages = [cls._to_message(message) for message in conversation.messages]
        return ConversationDetail(
            **summary.model_dump(),
            messages=messages,
        )
