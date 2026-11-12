from __future__ import annotations

import json

from fastapi import APIRouter, Response, status
from pydantic import Field

from handball_api.routers.deps import AuthedDep, OrgDep, clear_session_cookies
from handball_api.schemas.common import ApiModel
from handball_api.services import privacy as service

router = APIRouter(prefix="/v1", tags=["privacy"])


class AccountDelete(ApiModel):
    confirm_email: str = Field(max_length=320)
    password: str | None = Field(default=None, max_length=200)


class OrgDelete(ApiModel):
    confirm_name: str = Field(max_length=200)


@router.get(
    "/me/export",
    response_class=Response,
    responses={200: {"content": {"application/json": {}}}},
)
async def export(auth: AuthedDep) -> Response:
    """Download of all personal data (JSON)."""
    data = await service.export(auth.ctx, auth.user)
    return Response(
        json.dumps(data, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"content-disposition": 'attachment; filename="handball-intelligence-daten.json"'},
    )


@router.post("/me/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(data: AccountDelete, auth: AuthedDep, response: Response) -> None:
    """Delete the own account (password and e-mail confirmation)."""
    await service.delete_account(auth.ctx, auth.user, data.password, data.confirm_email)
    clear_session_cookies(response, auth.ctx.settings)


@router.post("/orgs/{org_id}/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_org(data: OrgDelete, scope: OrgDep) -> None:
    """Delete the club with all teams, matches and videos (club admin, name confirmation)."""
    await service.delete_org(scope.ctx, data.confirm_name)
