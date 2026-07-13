"""Repository rozhrani pro kratkodobou pamet a dlouhodoba rozhodnuti."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from threading import Lock

from backend.schemas import LongTermDecisionCreate, LongTermDecisionItem, ShortTermMemoryItem


SHORT_TERM_RETENTION_DAYS = 31


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MemoryRepository(ABC):
    """Rozhrani uloziste pameti nezavisle na konkretni databazi."""

    @abstractmethod
    async def save_short_term_turn(
        self,
        role: str,
        content: str,
        session_id: str,
        metadata: dict | None = None,
    ) -> int | None:
        raise NotImplementedError

    @abstractmethod
    async def recent_short_term_turns(
        self,
        limit: int = 20,
        session_id: str = "",
    ) -> list[ShortTermMemoryItem]:
        raise NotImplementedError

    @abstractmethod
    async def search_short_term_text(
        self,
        query: str,
        limit: int = 10,
    ) -> list[ShortTermMemoryItem]:
        raise NotImplementedError

    @abstractmethod
    async def purge_short_term(self, days: int = SHORT_TERM_RETENTION_DAYS) -> int:
        raise NotImplementedError

    @abstractmethod
    async def save_long_term_decision(
        self,
        item: LongTermDecisionCreate,
    ) -> int | None:
        raise NotImplementedError

    @abstractmethod
    async def list_long_term_decisions(self, limit: int = 50) -> list[LongTermDecisionItem]:
        raise NotImplementedError

    @abstractmethod
    async def import_short_term_turns(self, records: list[dict]) -> int:
        raise NotImplementedError

    @abstractmethod
    async def import_long_term_decisions(self, records: list[dict]) -> int:
        raise NotImplementedError


class InMemoryMemoryRepository(MemoryRepository):
    """In-memory fallback pro backend pamet."""

    def __init__(self) -> None:
        self._short_term: list[ShortTermMemoryItem] = []
        self._decisions: list[LongTermDecisionItem] = []
        self._next_short_id = 1
        self._next_decision_id = 1
        self._lock = Lock()

    async def save_short_term_turn(
        self,
        role: str,
        content: str,
        session_id: str,
        metadata: dict | None = None,
    ) -> int | None:
        role = str(role or "").strip()
        content = str(content or "").strip()
        session_id = str(session_id or "").strip()
        if not role or not content or not session_id:
            return None

        with self._lock:
            item = ShortTermMemoryItem(
                id=self._next_short_id,
                role=role,
                content=content,
                session_id=session_id,
                metadata=metadata or {},
                created_at=utc_now(),
            )
            self._next_short_id += 1
            self._short_term.append(item)
            return item.id

    async def recent_short_term_turns(
        self,
        limit: int = 20,
        session_id: str = "",
    ) -> list[ShortTermMemoryItem]:
        limit = max(1, min(200, int(limit or 20)))
        with self._lock:
            records = self._short_term
            if session_id:
                records = [item for item in records if item.session_id == session_id]
            return list(records[-limit:])

    async def search_short_term_text(
        self,
        query: str,
        limit: int = 10,
    ) -> list[ShortTermMemoryItem]:
        query = str(query or "").strip().casefold()
        if not query:
            return []
        limit = max(1, min(50, int(limit or 10)))
        with self._lock:
            records = [item for item in self._short_term if query in item.content.casefold()]
            return list(records[-limit:])

    async def purge_short_term(self, days: int = SHORT_TERM_RETENTION_DAYS) -> int:
        cutoff = utc_now() - timedelta(days=max(1, int(days or SHORT_TERM_RETENTION_DAYS)))
        with self._lock:
            before = len(self._short_term)
            self._short_term = [item for item in self._short_term if item.created_at >= cutoff]
            return before - len(self._short_term)

    async def save_long_term_decision(
        self,
        item: LongTermDecisionCreate,
    ) -> int | None:
        if not item.confirmed or not item.confirmation_text.strip():
            return None
        with self._lock:
            record = LongTermDecisionItem(
                id=self._next_decision_id,
                title=item.title.strip(),
                decision=item.decision.strip(),
                rationale=item.rationale.strip(),
                status="ACCEPTED",
                source=item.source.strip(),
                confirmed_by=item.confirmed_by.strip() or "user",
                confirmation_text=item.confirmation_text.strip(),
                metadata=item.metadata or {},
                created_at=utc_now(),
            )
            self._next_decision_id += 1
            self._decisions.append(record)
            return record.id

    async def list_long_term_decisions(self, limit: int = 50) -> list[LongTermDecisionItem]:
        limit = max(1, min(200, int(limit or 50)))
        with self._lock:
            return list(self._decisions[-limit:])

    async def import_short_term_turns(self, records: list[dict]) -> int:
        imported = 0
        with self._lock:
            existing = {
                (item.session_id, item.role, item.content, item.created_at.isoformat())
                for item in self._short_term
            }
            for record in records:
                created_at = _coerce_datetime(record.get("created_at"))
                key = (
                    str(record.get("session_id") or ""),
                    str(record.get("role") or ""),
                    str(record.get("content") or ""),
                    created_at.isoformat(),
                )
                if key in existing or not all(key[:3]):
                    continue
                item = ShortTermMemoryItem(
                    id=self._next_short_id,
                    session_id=key[0],
                    role=key[1],
                    content=key[2],
                    metadata=dict(record.get("metadata") or {}),
                    created_at=created_at,
                )
                self._next_short_id += 1
                self._short_term.append(item)
                existing.add(key)
                imported += 1
        return imported

    async def import_long_term_decisions(self, records: list[dict]) -> int:
        imported = 0
        with self._lock:
            existing = {
                (item.title, item.decision, item.created_at.isoformat())
                for item in self._decisions
            }
            for record in records:
                created_at = _coerce_datetime(record.get("created_at"))
                key = (
                    str(record.get("title") or ""),
                    str(record.get("decision") or ""),
                    created_at.isoformat(),
                )
                if key in existing or not key[0] or not key[1]:
                    continue
                item = LongTermDecisionItem(
                    id=self._next_decision_id,
                    title=key[0],
                    decision=key[1],
                    rationale=str(record.get("rationale") or ""),
                    status=str(record.get("status") or "ACCEPTED"),
                    source=str(record.get("source") or ""),
                    confirmed_by=str(record.get("confirmed_by") or "user"),
                    confirmation_text=str(record.get("confirmation_text") or ""),
                    metadata=dict(record.get("metadata") or {}),
                    created_at=created_at,
                )
                self._next_decision_id += 1
                self._decisions.append(item)
                existing.add(key)
                imported += 1
        return imported


class FallbackMemoryRepository(MemoryRepository):
    """Pouzije primarni repository, pri selhani prejde na in-memory fallback."""

    def __init__(
        self,
        primary: MemoryRepository,
        fallback: MemoryRepository | None = None,
    ) -> None:
        self._primary = primary
        self._fallback = fallback or InMemoryMemoryRepository()
        self._fallback_active = False
        self.last_error: str | None = None

    async def save_short_term_turn(
        self,
        role: str,
        content: str,
        session_id: str,
        metadata: dict | None = None,
    ) -> int | None:
        return await self._call("save_short_term_turn", role, content, session_id, metadata)

    async def recent_short_term_turns(
        self,
        limit: int = 20,
        session_id: str = "",
    ) -> list[ShortTermMemoryItem]:
        return await self._call("recent_short_term_turns", limit, session_id)

    async def search_short_term_text(
        self,
        query: str,
        limit: int = 10,
    ) -> list[ShortTermMemoryItem]:
        return await self._call("search_short_term_text", query, limit)

    async def purge_short_term(self, days: int = SHORT_TERM_RETENTION_DAYS) -> int:
        return await self._call("purge_short_term", days)

    async def save_long_term_decision(self, item: LongTermDecisionCreate) -> int | None:
        return await self._call("save_long_term_decision", item)

    async def list_long_term_decisions(self, limit: int = 50) -> list[LongTermDecisionItem]:
        return await self._call("list_long_term_decisions", limit)

    async def import_short_term_turns(self, records: list[dict]) -> int:
        return await self._call("import_short_term_turns", records)

    async def import_long_term_decisions(self, records: list[dict]) -> int:
        return await self._call("import_long_term_decisions", records)

    async def _call(self, method_name: str, *args):
        target = self._fallback if self._fallback_active else self._primary
        try:
            return await getattr(target, method_name)(*args)
        except Exception as exc:
            self._fallback_active = True
            self.last_error = str(exc)
            return await getattr(self._fallback, method_name)(*args)


def _coerce_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    raw = str(value or "").strip()
    if raw:
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return utc_now()
