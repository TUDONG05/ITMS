import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.assistant import (
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantConversationDetail,
    AssistantConversationSummary,
)
from app.services.assistant import AssistantService

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/chat", response_model=AssistantChatResponse)
def chat(
    payload: AssistantChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AssistantChatResponse:
    return AssistantService().chat(db, current_user, payload)


@router.get("/conversations", response_model=list[AssistantConversationSummary])
def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AssistantConversationSummary]:
    return AssistantService.list_conversations(db, current_user)


@router.get(
    "/conversations/{conversation_id}",
    response_model=AssistantConversationDetail,
)
def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AssistantConversationDetail:
    return AssistantService.get_conversation(db, current_user, conversation_id)
