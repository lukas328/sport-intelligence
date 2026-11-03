"""Push tokens of the native apps (addendum 01, 5.5)."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Response
from pydantic import Field

from handball_api.routers.deps import AuthedDep
from handball_api.schemas.common import ApiModel
from handball_api.services import push

router = APIRouter(prefix="/v1/me/devices", tags=["devices"])


class DeviceIn(ApiModel):
    token: str = Field(min_length=10, max_length=200)
    platform: Literal["ios", "android"]


@router.post("", status_code=204)
async def register(body: DeviceIn, auth: AuthedDep) -> Response:
    await push.register(auth.ctx, body.token, body.platform)
    return Response(status_code=204)


@router.delete("/{token}", status_code=204)
async def unregister(token: str, auth: AuthedDep) -> Response:
    """On sign-out the app removes its token, so pushes stop at once."""
    await push.unregister(auth.ctx, token)
    return Response(status_code=204)
