import uuid
from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from app.schemas.base import BaseSchema


class AssistantChatRequest(BaseSchema):
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: uuid.UUID | None = None

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("message must not be blank")
        return cleaned


class AssistantMessageRead(BaseSchema):
    id: uuid.UUID
    role: str
    content: str
    citations: list[dict[str, Any]] | None = None
    created_at: datetime


class AssistantChatResponse(BaseSchema):
    conversation_id: uuid.UUID
    message: AssistantMessageRead


class AssistantConversationSummary(BaseSchema):
    id: uuid.UUID
    title: str | None = None
    created_at: datetime
    updated_at: datetime


class AssistantConversationDetail(AssistantConversationSummary):
    messages: list[AssistantMessageRead] = Field(default_factory=list)
