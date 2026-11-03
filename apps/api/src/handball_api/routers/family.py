"""Own consents: adult players for themselves, parents for their children (addendum 01, P6)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter

from handball_api.models.enums import ConsentKind
from handball_api.routers.deps import OrgDep
from handball_api.schemas.family import ConsentSubject, ConsentToggle, SubjectTeam
from handball_api.schemas.roster import ConsentOut
from handball_api.services import family as service

router = APIRouter(prefix="/v1/orgs/{org_id}/me", tags=["consents"])


def _out(s: service.Subject) -> ConsentSubject:
    return ConsentSubject(
        player_id=s.player.id,
        first_name=s.player.first_name,
        last_name=s.player.last_name,
        birth_year=s.player.birth_year,
        relation=s.relation,
        minor=s.minor,
        teams=[SubjectTeam(id=t.id, name=t.name, is_youth=t.is_youth) for t in s.teams],
        active=sorted({c.kind for c in s.consents if c.revoked_at is None}),
        history=[ConsentOut.model_validate(c) for c in s.consents],
    )


@router.get("/consents", response_model=list[ConsentSubject])
async def my_consents(scope: OrgDep) -> list[ConsentSubject]:
    """Players I decide for: my own player profile (adults) and my children (parents)."""
    return [_out(s) for s in await service.subjects(scope.ctx)]


@router.post("/consents/{player_id}", response_model=ConsentOut, status_code=201)
async def give_consent(player_id: uuid.UUID, data: ConsentToggle, scope: OrgDep) -> ConsentOut:
    c = await service.give(scope.ctx, player_id, data.kind, scope.user.name)
    return ConsentOut.model_validate(c)


@router.delete("/consents/{player_id}/{kind}", status_code=204)
async def revoke_consent(player_id: uuid.UUID, kind: ConsentKind, scope: OrgDep) -> None:
    await service.revoke(scope.ctx, player_id, ConsentKind(kind))
