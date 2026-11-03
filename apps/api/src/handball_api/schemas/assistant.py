"""Data assistant (addendum 01, 5.1)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AskIn(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    conversation_id: uuid.UUID | None = None
    lang: Literal["de-CH", "fr", "en"] = "de-CH"


class Clip(BaseModel):
    event_id: str
    match_id: str
    t_ms: int | None = None
    label: str = ""


class Chart(BaseModel):
    title: str
    labels: list[str]
    values: list[float]


class Answer(BaseModel):
    answerable: bool
    text: str
    values: list[float] = []
    sample_size: int | None = None
    clips: list[Clip] = []
    chart: Chart | None = None
    suggestion: str | None = None


class ToolCall(BaseModel):
    name: str
    input: dict[str, Any]
    ms: int | None = None
    summary: dict[str, Any] | None = None
    error: str | None = None


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    question: str
    answer: Answer
    tool_calls: list[ToolCall]
    validated: bool
    status: str
    latency_ms: int
    rating: int | None
    created_at: datetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    team_id: uuid.UUID
    title: str
    created_at: datetime


class ConversationDetail(ConversationOut):
    messages: list[MessageOut]


class RateIn(BaseModel):
    rating: Literal[-1, 1]
