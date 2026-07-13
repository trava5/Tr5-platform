"""SQLAlchemy declarative base pro backend modely."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Zaklad pro SQLAlchemy 2.0 ORM modely."""
