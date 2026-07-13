"""Datove modely backend API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=12000)
    channel: str = Field(default="api", max_length=64)
    client_id: str | None = Field(default=None, max_length=128)
    conversation_id: str | None = Field(default=None, max_length=128)
    want_audio: bool = False


class MessageResponse(BaseModel):
    status: str
    message_id: str
    conversation_id: str
    text: str
    audio_url: str | None = None
    detail: str | None = None


class StoredMessage(BaseModel):
    message_id: str
    role: str
    text: str
    channel: str
    client_id: str | None = None
    created_at: datetime
    status: str | None = None


class ConversationSummary(BaseModel):
    conversation_id: str
    client_id: str | None = None
    channel: str
    created_at: datetime
    updated_at: datetime
    message_count: int


class ConversationDetail(ConversationSummary):
    messages: list[StoredMessage]


class ShortTermMemoryCreate(BaseModel):
    role: str = Field(min_length=1, max_length=32)
    content: str = Field(min_length=1, max_length=12000)
    session_id: str = Field(min_length=1, max_length=128)
    metadata: dict | None = None


class ShortTermMemoryItem(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    metadata: dict
    created_at: datetime


class LongTermDecisionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    decision: str = Field(min_length=1, max_length=12000)
    rationale: str = ""
    source: str = ""
    confirmed: bool = False
    confirmed_by: str = Field(default="user", max_length=128)
    confirmation_text: str = ""
    metadata: dict | None = None


class LongTermDecisionItem(BaseModel):
    id: int
    title: str
    decision: str
    rationale: str
    status: str
    source: str
    confirmed_by: str
    confirmation_text: str
    metadata: dict
    created_at: datetime


class MemoryImportResult(BaseModel):
    short_term_imported: int
    long_term_imported: int


class RealtimeEvent(BaseModel):
    event_id: str
    event_type: str = Field(max_length=64)
    timestamp: datetime
    channel: str = Field(default="backend", max_length=64)
    client_id: str | None = Field(default=None, max_length=128)
    conversation_id: str | None = Field(default=None, max_length=128)
    role: str | None = Field(default=None, max_length=32)
    text: str | None = None
    audio_mime_type: str | None = None
    audio_base64: str | None = None
    payload: dict[str, object] = Field(default_factory=dict)
