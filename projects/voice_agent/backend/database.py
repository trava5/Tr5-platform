"""PostgreSQL pripojeni pro serverovy backend."""

from __future__ import annotations

from dataclasses import dataclass

from .config import BackendSettings


@dataclass(frozen=True)
class DatabaseHealth:
    configured: bool
    ok: bool
    detail: str


async def check_database(settings: BackendSettings) -> DatabaseHealth:
    if not settings.database_configured:
        return DatabaseHealth(
            configured=False,
            ok=False,
            detail="DATABASE_URL neni nastaveno.",
        )

    try:
        from sqlalchemy import text

        from .db.session import create_engine
    except ImportError as exc:
        return DatabaseHealth(
            configured=True,
            ok=False,
            detail=f"Chybi databazova zavislost: {exc.name}.",
        )

    engine = create_engine(settings)
    try:
        async with engine.connect() as connection:
            if settings.database_schema:
                from .db.session import quote_identifier

                schema_status = await connection.execute(
                    text(
                        """
                        SELECT
                            EXISTS(
                                SELECT 1
                                FROM information_schema.schemata
                                WHERE schema_name = :schema_name
                            ) AS schema_exists,
                            has_database_privilege(
                                current_user,
                                current_database(),
                                'CREATE'
                            ) AS can_create_schema
                        """
                    ),
                    {"schema_name": settings.database_schema},
                )
                schema_row = schema_status.one()
                if not schema_row.schema_exists and not schema_row.can_create_schema:
                    return DatabaseHealth(
                        configured=True,
                        ok=False,
                        detail=(
                            "PostgreSQL odpovida, ale cilove schema neexistuje "
                            "a databazovy uzivatel ho nemuze vytvorit."
                        ),
                    )
                if schema_row.schema_exists:
                    await connection.execute(
                        text(f"SET search_path TO {quote_identifier(settings.database_schema)}")
                    )
            await connection.execute(text("SELECT 1"))
        detail = "PostgreSQL odpovida."
        if settings.database_schema:
            detail = "PostgreSQL odpovida a schema je dostupne."
        return DatabaseHealth(configured=True, ok=True, detail=detail)
    except Exception as exc:
        return DatabaseHealth(
            configured=True,
            ok=False,
            detail=f"PostgreSQL kontrola selhala: {exc}",
        )
    finally:
        await engine.dispose()
