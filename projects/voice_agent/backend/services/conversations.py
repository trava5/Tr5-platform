"""Repository rozhrani pro konverzacni relace."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

from backend.schemas import ConversationDetail, ConversationSummary, StoredMessage


@dataclass
class ConversationRecord:
    conversation_id: str
    channel: str
    client_id: str | None
    created_at: datetime
    updated_at: datetime
    messages: list[StoredMessage] = field(default_factory=list)


class ConversationRepository(ABC):
    """Rozhrani uloziste konverzacnich relaci."""

    @abstractmethod
    async def get_or_create(
        self,
        conversation_id: str | None,
        channel: str,
        client_id: str | None,
    ) -> ConversationRecord:
        raise NotImplementedError

    @abstractmethod
    async def append_message(
        self,
        conversation_id: str,
        role: str,
        text: str,
        channel: str,
        client_id: str | None,
        status: str | None = None,
    ) -> StoredMessage:
        raise NotImplementedError

    @abstractmethod
    async def get(self, conversation_id: str) -> ConversationDetail | None:
        raise NotImplementedError

    @abstractmethod
    async def list(self) -> list[ConversationSummary]:
        raise NotImplementedError


class InMemoryConversationRepository(ConversationRepository):
    """In-memory repository pro MIG-003 pred zapojenim PostgreSQL."""

    def __init__(self) -> None:
        self._records: dict[str, ConversationRecord] = {}
        self._lock = Lock()

    async def get_or_create(
        self,
        conversation_id: str | None,
        channel: str,
        client_id: str | None,
    ) -> ConversationRecord:
        now = datetime.now(timezone.utc)
        with self._lock:
            if conversation_id and conversation_id in self._records:
                record = self._records[conversation_id]
                record.updated_at = now
                return record

            new_id = conversation_id or f"conv_{uuid4().hex}"
            record = ConversationRecord(
                conversation_id=new_id,
                channel=channel,
                client_id=client_id,
                created_at=now,
                updated_at=now,
            )
            self._records[new_id] = record
            return record

    async def append_message(
        self,
        conversation_id: str,
        role: str,
        text: str,
        channel: str,
        client_id: str | None,
        status: str | None = None,
    ) -> StoredMessage:
        now = datetime.now(timezone.utc)
        message = StoredMessage(
            message_id=f"msg_{uuid4().hex}",
            role=role,
            text=text,
            channel=channel,
            client_id=client_id,
            created_at=now,
            status=status,
        )
        with self._lock:
            record = self._records.get(conversation_id)
            if record is None:
                record = ConversationRecord(
                    conversation_id=conversation_id,
                    channel=channel,
                    client_id=client_id,
                    created_at=now,
                    updated_at=now,
                )
                self._records[conversation_id] = record
            record.messages.append(message)
            record.updated_at = now
        return message

    async def get(self, conversation_id: str) -> ConversationDetail | None:
        with self._lock:
            record = self._records.get(conversation_id)
            if not record:
                return None
            return self._to_detail(record)

    async def list(self) -> list[ConversationSummary]:
        with self._lock:
            records = sorted(
                self._records.values(),
                key=lambda record: record.updated_at,
                reverse=True,
            )
            return [self._to_summary(record) for record in records]

    @staticmethod
    def _to_summary(record: ConversationRecord) -> ConversationSummary:
        return ConversationSummary(
            conversation_id=record.conversation_id,
            client_id=record.client_id,
            channel=record.channel,
            created_at=record.created_at,
            updated_at=record.updated_at,
            message_count=len(record.messages),
        )

    @classmethod
    def _to_detail(cls, record: ConversationRecord) -> ConversationDetail:
        summary = cls._to_summary(record)
        return ConversationDetail(
            **summary.model_dump(),
            messages=list(record.messages),
        )


class FallbackConversationRepository(ConversationRepository):
    """Pouzije primarni repository, pri selhani prejde na in-memory fallback."""

    def __init__(
        self,
        primary: ConversationRepository,
        fallback: ConversationRepository | None = None,
    ) -> None:
        self._primary = primary
        self._fallback = fallback or InMemoryConversationRepository()
        self._fallback_active = False
        self.last_error: str | None = None

    async def get_or_create(
        self,
        conversation_id: str | None,
        channel: str,
        client_id: str | None,
    ) -> ConversationRecord:
        return await self._call(
            "get_or_create",
            conversation_id,
            channel,
            client_id,
        )

    async def append_message(
        self,
        conversation_id: str,
        role: str,
        text: str,
        channel: str,
        client_id: str | None,
        status: str | None = None,
    ) -> StoredMessage:
        return await self._call(
            "append_message",
            conversation_id,
            role,
            text,
            channel,
            client_id,
            status,
        )

    async def get(self, conversation_id: str) -> ConversationDetail | None:
        return await self._call("get", conversation_id)

    async def list(self) -> list[ConversationSummary]:
        return await self._call("list")

    async def _call(self, method_name: str, *args):
        target = self._fallback if self._fallback_active else self._primary
        try:
            return await getattr(target, method_name)(*args)
        except Exception as exc:
            self._fallback_active = True
            self.last_error = str(exc)
            return await getattr(self._fallback, method_name)(*args)
