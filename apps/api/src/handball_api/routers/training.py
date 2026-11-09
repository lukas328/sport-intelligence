from __future__ import annotations

import uuid

from fastapi import APIRouter

from handball_api.routers.deps import OrgDep
from handball_api.schemas.training import (
    AssignmentCreate,
    AssignmentOut,
    AssignmentStatusIn,
    NotificationList,
    NotificationsRead,
)
from handball_api.services import training as service

router = APIRouter(prefix="/v1/orgs/{org_id}", tags=["training"])


@router.post("/teams/{team_id}/assignments", response_model=AssignmentOut, status_code=201)
async def create_assignment(
    team_id: uuid.UUID, data: AssignmentCreate, scope: OrgDep
) -> AssignmentOut:
    """Give players a playlist, play, match or drill to study (notification and e-mail)."""
    a = await service.create_assignment(scope.ctx, team_id, data)
    return await service.assignment_detail(scope.ctx, a.id)


@router.get("/teams/{team_id}/assignments", response_model=list[AssignmentOut])
async def team_assignments(team_id: uuid.UUID, scope: OrgDep) -> list[AssignmentOut]:
    return await service.team_assignments(scope.ctx, team_id)


@router.get("/assignments/{assignment_id}", response_model=AssignmentOut)
async def assignment_detail(assignment_id: uuid.UUID, scope: OrgDep) -> AssignmentOut:
    """One assignment with every recipient's progress and who is still open (staff)."""
    return await service.assignment_detail(scope.ctx, assignment_id)


@router.delete("/assignments/{assignment_id}", status_code=204)
async def delete_assignment(assignment_id: uuid.UUID, scope: OrgDep) -> None:
    await service.delete_assignment(scope.ctx, assignment_id)


@router.get("/me/assignments", response_model=list[AssignmentOut])
async def my_assignments(scope: OrgDep) -> list[AssignmentOut]:
    return await service.my_assignments(scope.ctx)


@router.put("/assignments/{assignment_id}/status", response_model=AssignmentOut)
async def set_status(
    assignment_id: uuid.UUID, data: AssignmentStatusIn, scope: OrgDep
) -> AssignmentOut:
    return await service.set_status(scope.ctx, assignment_id, data.done)


@router.get("/me/notifications", response_model=NotificationList, tags=["notifications"])
async def notifications(scope: OrgDep) -> NotificationList:
    return await service.notifications(scope.ctx)


@router.post("/me/notifications/read", status_code=204, tags=["notifications"])
async def mark_read(data: NotificationsRead, scope: OrgDep) -> None:
    await service.mark_read(scope.ctx, data.ids)
