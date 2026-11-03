"""Data assistant (addendum 01, 5.1)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Request, Response

from handball_api.models import AssistantConversation, AssistantMessage
from handball_api.routers.deps import OrgDep
from handball_api.schemas.assistant import (
    AskIn,
    ConversationDetail,
    ConversationOut,
    MessageOut,
    RateIn,
)
from handball_api.services import assistant as service

router = APIRouter(prefix="/v1/orgs/{org_id}", tags=["assistant"])


@router.post("/teams/{team_id}/assistant", response_model=MessageOut, status_code=201)
async def ask(team_id: uuid.UUID, body: AskIn, scope: OrgDep, request: Request) -> AssistantMessage:
    """Answers a question about the team's data with typed queries; numbers are validated."""
    return await service.ask(
        scope.ctx,
        request.app.state.assistant,
        team_id,
        body.question,
        body.conversation_id,
        body.lang,
    )


@router.get("/teams/{team_id}/assistant", response_model=list[ConversationOut])
async def conversations(team_id: uuid.UUID, scope: OrgDep) -> list[AssistantConversation]:
    return await service.conversations(scope.ctx, team_id)


@router.get("/assistant/{conversation_id}", response_model=ConversationDetail)
async def conversation(conversation_id: uuid.UUID, scope: OrgDep) -> ConversationDetail:
    conv, msgs = await service.conversation(scope.ctx, conversation_id)
    return ConversationDetail(
        id=conv.id,
        team_id=conv.team_id,
        title=conv.title,
        created_at=conv.created_at,
        messages=[MessageOut.model_validate(m) for m in msgs],
    )


@router.post("/assistant/messages/{message_id}/rating", status_code=204)
async def rate(message_id: uuid.UUID, body: RateIn, scope: OrgDep) -> Response:
    await service.rate(scope.ctx, message_id, body.rating)
    return Response(status_code=204)
