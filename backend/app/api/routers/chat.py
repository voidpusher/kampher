"""AI chat search endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import ChatDep
from app.core.rate_limit import enforce_chat_rate_limit
from app.schemas.api import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse, dependencies=[Depends(enforce_chat_rate_limit)])
async def ask(request: ChatRequest, service: ChatDep) -> ChatResponse:
    result = await service.ask(request.question)
    return ChatResponse(**result)
