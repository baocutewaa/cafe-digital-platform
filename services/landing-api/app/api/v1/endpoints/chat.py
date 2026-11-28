from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.chat import (
    ChatFeedbackRequest,
    ChatFeedbackResponse,
    CreateChatSessionRequest,
    CreateChatSessionResponse,
    SendChatMessageRequest,
)
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["Bean AI Chat"])


@router.post("/sessions", response_model=CreateChatSessionResponse, status_code=201)
async def create_chat_session(
    payload: CreateChatSessionRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> CreateChatSessionResponse:
    """Tạo phiên chat ẩn danh với Bean AI và trả về session_id + session_token."""
    service = ChatService(db)
    return await service.create_session(payload or CreateChatSessionRequest())


@router.post("/sessions/{session_id}/messages")
async def send_chat_message(
    session_id: uuid.UUID,
    payload: SendChatMessageRequest,
    request: Request,
    x_session_token: str | None = Header(default=None, alias="X-Session-Token"),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Gửi tin nhắn và nhận phản hồi SSE streaming (meta, status, products, token, done)."""
    service = ChatService(db)
    chat_session = await service.verify_session(session_id, x_session_token)
    client_ip = request.client.host if request.client else "unknown"
    replayed = await service.prepare_stream(
        chat_session=chat_session,
        client_message_id=payload.client_message_id,
        client_ip=client_ip,
    )

    return StreamingResponse(
        service.stream_message(
            chat_session=chat_session,
            content=payload.content,
            client_message_id=payload.client_message_id,
            client_ip=client_ip,
            replayed=replayed,
            rate_limit_checked=True,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/messages/{message_id}/feedback", response_model=ChatFeedbackResponse)
async def submit_chat_feedback(
    message_id: uuid.UUID,
    payload: ChatFeedbackRequest,
    x_session_token: str | None = Header(default=None, alias="X-Session-Token"),
    db: AsyncSession = Depends(get_db),
) -> ChatFeedbackResponse:
    """Gửi đánh giá 👍 (1) / 👎 (-1) và góp ý cho câu trả lời Bean AI."""
    service = ChatService(db)
    return await service.submit_feedback(message_id, x_session_token, payload)
