"""Dependency wiring for the API layer."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.services.chat import ChatService
from app.services.search import SearchService

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_search_service(session: SessionDep) -> SearchService:
    return SearchService(session)


def get_chat_service(session: SessionDep) -> ChatService:
    return ChatService(session)


SearchDep = Annotated[SearchService, Depends(get_search_service)]
ChatDep = Annotated[ChatService, Depends(get_chat_service)]
