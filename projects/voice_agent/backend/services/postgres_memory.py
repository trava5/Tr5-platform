"""PostgreSQL repository pro kratkodobou pamet a dlouhodoba rozhodnuti."""

from __future__ import annotations

import asyncio
from datetime import timedelta

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from backend.db.models import LongTermDecision, ShortTermMemoryTurn
from backend.db.session import configure_schema, initialize_database
from backend.schemas import LongTermDecisionCreate, LongTermDecisionItem, ShortTermMemoryItem
from backend.services.memory import MemoryRepository, SHORT_TERM_RETENTION_DAYS, _coerce_datetime, utc_now


class PostgresMemoryRepository(MemoryRepository):
    """Trvale ulozeni kratkodobe pameti a dlouhodobych rozhodnuti."""

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

        await self._ensure_initialized()
        await self.purge_short_term()
        async with self._sessionmaker() as session:
            await self._configure(session)
            turn = ShortTermMemoryTurn(
                role=role,
                content=content,
                session_id=session_id,
                metadata_json=metadata or {},
            )
            session.add(turn)
            await session.commit()
            await session.refresh(turn)
            return int(turn.id)

    async def recent_short_term_turns(
        self,
        limit: int = 20,
        session_id: str = "",
    ) -> list[ShortTermMemoryItem]:
        await self._ensure_initialized()
        limit = max(1, min(200, int(limit or 20)))
        async with self._sessionmaker() as session:
            await self._configure(session)
            statement = select(ShortTermMemoryTurn)
            if session_id:
                statement = statement.where(ShortTermMemoryTurn.session_id == session_id)
            statement = statement.order_by(ShortTermMemoryTurn.id.desc()).limit(limit)
            result = await session.execute(statement)
            return [self._to_short_item(row) for row in reversed(result.scalars().all())]

    async def search_short_term_text(
        self,
        query: str,
        limit: int = 10,
    ) -> list[ShortTermMemoryItem]:
        await self._ensure_initialized()
        query = str(query or "").strip()
        if not query:
            return []
        limit = max(1, min(50, int(limit or 10)))
        async with self._sessionmaker() as session:
            await self._configure(session)
            terms = [term for term in query.split() if term]
            filters = [ShortTermMemoryTurn.content.ilike(f"%{term}%") for term in terms]
            statement = select(ShortTermMemoryTurn)
            if filters:
                statement = statement.where(or_(*filters))
            statement = statement.order_by(ShortTermMemoryTurn.id.desc()).limit(limit)
            result = await session.execute(statement)
            return [self._to_short_item(row) for row in result.scalars().all()]

    async def purge_short_term(self, days: int = SHORT_TERM_RETENTION_DAYS) -> int:
        await self._ensure_initialized()
        cutoff = utc_now() - timedelta(days=max(1, int(days or SHORT_TERM_RETENTION_DAYS)))
        async with self._sessionmaker() as session:
            await self._configure(session)
            result = await session.execute(
                delete(ShortTermMemoryTurn).where(ShortTermMemoryTurn.created_at < cutoff)
            )
            await session.commit()
            return int(result.rowcount or 0)

    async def save_long_term_decision(
        self,
        item: LongTermDecisionCreate,
    ) -> int | None:
        if not item.confirmed or not item.confirmation_text.strip():
            return None
        await self._ensure_initialized()
        async with self._sessionmaker() as session:
            await self._configure(session)
            decision = LongTermDecision(
                title=item.title.strip(),
                decision=item.decision.strip(),
                rationale=item.rationale.strip(),
                status="ACCEPTED",
                source=item.source.strip(),
                confirmed_by=item.confirmed_by.strip() or "user",
                confirmation_text=item.confirmation_text.strip(),
                metadata_json=item.metadata or {},
            )
            session.add(decision)
            await session.commit()
            await session.refresh(decision)
            return int(decision.id)

    async def list_long_term_decisions(self, limit: int = 50) -> list[LongTermDecisionItem]:
        await self._ensure_initialized()
        limit = max(1, min(200, int(limit or 50)))
        async with self._sessionmaker() as session:
            await self._configure(session)
            result = await session.execute(
                select(LongTermDecision).order_by(LongTermDecision.id.desc()).limit(limit)
            )
            return [self._to_decision_item(row) for row in reversed(result.scalars().all())]

    async def import_short_term_turns(self, records: list[dict]) -> int:
        await self._ensure_initialized()
        imported = 0
        async with self._sessionmaker() as session:
            await self._configure(session)
            for record in records:
                session_id = str(record.get("session_id") or "").strip()
                role = str(record.get("role") or "").strip()
                content = str(record.get("content") or "").strip()
                created_at = _coerce_datetime(record.get("created_at"))
                if not session_id or not role or not content:
                    continue

                exists = await session.execute(
                    select(func.count())
                    .select_from(ShortTermMemoryTurn)
                    .where(
                        ShortTermMemoryTurn.session_id == session_id,
                        ShortTermMemoryTurn.role == role,
                        ShortTermMemoryTurn.content == content,
                        ShortTermMemoryTurn.created_at == created_at,
                    )
                )
                if int(exists.scalar_one() or 0):
                    continue

                session.add(
                    ShortTermMemoryTurn(
                        session_id=session_id,
                        role=role,
                        content=content,
                        metadata_json=dict(record.get("metadata") or {}),
                        created_at=created_at,
                    )
                )
                imported += 1
            await session.commit()
        return imported

    async def import_long_term_decisions(self, records: list[dict]) -> int:
        await self._ensure_initialized()
        imported = 0
        async with self._sessionmaker() as session:
            await self._configure(session)
            for record in records:
                title = str(record.get("title") or "").strip()
                decision_text = str(record.get("decision") or "").strip()
                created_at = _coerce_datetime(record.get("created_at"))
                if not title or not decision_text:
                    continue

                exists = await session.execute(
                    select(func.count())
                    .select_from(LongTermDecision)
                    .where(
                        LongTermDecision.title == title,
                        LongTermDecision.decision == decision_text,
                        LongTermDecision.created_at == created_at,
                    )
                )
                if int(exists.scalar_one() or 0):
                    continue

                session.add(
                    LongTermDecision(
                        title=title,
                        decision=decision_text,
                        rationale=str(record.get("rationale") or ""),
                        status=str(record.get("status") or "ACCEPTED"),
                        source=str(record.get("source") or ""),
                        confirmed_by=str(record.get("confirmed_by") or "user"),
                        confirmation_text=str(record.get("confirmation_text") or ""),
                        metadata_json=dict(record.get("metadata") or {}),
                        created_at=created_at,
                    )
                )
                imported += 1
            await session.commit()
        return imported

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
    def _to_short_item(turn: ShortTermMemoryTurn) -> ShortTermMemoryItem:
        return ShortTermMemoryItem(
            id=int(turn.id),
            session_id=turn.session_id,
            role=turn.role,
            content=turn.content,
            metadata=turn.metadata_json or {},
            created_at=turn.created_at,
        )

    @staticmethod
    def _to_decision_item(decision: LongTermDecision) -> LongTermDecisionItem:
        return LongTermDecisionItem(
            id=int(decision.id),
            title=decision.title,
            decision=decision.decision,
            rationale=decision.rationale,
            status=decision.status,
            source=decision.source,
            confirmed_by=decision.confirmed_by,
            confirmation_text=decision.confirmation_text,
            metadata=decision.metadata_json or {},
            created_at=decision.created_at,
        )
