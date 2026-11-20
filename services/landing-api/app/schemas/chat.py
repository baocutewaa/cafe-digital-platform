from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CreateChatSessionRequest(BaseModel):
    store_slug: str | None = Field(default=None, max_length=100)
    language: Literal["vi", "en"] = "vi"


class CreateChatSessionResponse(BaseModel):
    session_id: uuid.UUID
    session_token: str
    language: Literal["vi", "en"]
    expires_at: datetime
    ai_mode: Literal["online", "fast_lookup_only"]


class SendChatMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=1000)
    client_message_id: str | None = Field(default=None, max_length=64)


class ChatFeedbackRequest(BaseModel):
    rating: Literal[-1, 1]
    comment: str | None = Field(default=None, max_length=500)


class ChatFeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message_id: uuid.UUID
    rating: int
    comment: str | None = None
