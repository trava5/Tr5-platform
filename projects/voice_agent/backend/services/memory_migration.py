"""Migrace lokalni SQLite pameti do backend storage vrstvy."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from backend.schemas import MemoryImportResult
from backend.services.memory import MemoryRepository


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SQLITE_MEMORY_PATH = BASE_DIR / "memory" / "jarvis_memory.sqlite3"


def read_sqlite_memory_records(
    sqlite_path: Path = DEFAULT_SQLITE_MEMORY_PATH,
) -> tuple[list[dict], list[dict]]:
    if not sqlite_path.exists():
        return [], []

    connection = sqlite3.connect(sqlite_path)
    connection.row_factory = sqlite3.Row
    try:
        short_term = _read_short_term_turns(connection)
        decisions = _read_long_term_decisions(connection)
    finally:
        connection.close()
    return short_term, decisions


async def import_sqlite_memory(
    repository: MemoryRepository,
    sqlite_path: Path = DEFAULT_SQLITE_MEMORY_PATH,
) -> MemoryImportResult:
    short_term, decisions = read_sqlite_memory_records(sqlite_path)
    return MemoryImportResult(
        short_term_imported=await repository.import_short_term_turns(short_term),
        long_term_imported=await repository.import_long_term_decisions(decisions),
    )


def _read_short_term_turns(connection: sqlite3.Connection) -> list[dict]:
    if not _table_exists(connection, "short_term_conversation_turns"):
        return []
    rows = connection.execute(
        """
        SELECT session_id, role, content, metadata_json, created_at
        FROM short_term_conversation_turns
        ORDER BY id
        """
    ).fetchall()
    return [
        {
            "session_id": row["session_id"],
            "role": row["role"],
            "content": row["content"],
            "metadata": _load_metadata(row["metadata_json"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def _read_long_term_decisions(connection: sqlite3.Connection) -> list[dict]:
    if not _table_exists(connection, "long_term_decisions"):
        return []
    rows = connection.execute(
        """
        SELECT title, decision, rationale, status, source, confirmed_by,
               confirmation_text, metadata_json, created_at
        FROM long_term_decisions
        ORDER BY id
        """
    ).fetchall()
    return [
        {
            "title": row["title"],
            "decision": row["decision"],
            "rationale": row["rationale"],
            "status": row["status"],
            "source": row["source"],
            "confirmed_by": row["confirmed_by"],
            "confirmation_text": row["confirmation_text"],
            "metadata": _load_metadata(row["metadata_json"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def _load_metadata(raw: str | None) -> dict:
    try:
        value = json.loads(raw or "{}")
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}
