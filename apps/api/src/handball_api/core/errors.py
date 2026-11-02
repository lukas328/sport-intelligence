"""RFC 9457 problem details as the single error format of the API."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

PROBLEM_MEDIA_TYPE = "application/problem+json"
PROBLEM_BASE = "urn:handball-platform:problem:"


class Problem(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
    errors: list[dict[str, Any]] | None = None


class ProblemError(Exception):
    """Raise from domain or service code to return a typed problem response."""

    def __init__(self, status: int, code: str, detail: str | None = None) -> None:
        super().__init__(detail or code)
        self.status = status
        self.code = code
        self.detail = detail


def _response(problem: Problem) -> JSONResponse:
    return JSONResponse(
        problem.model_dump(exclude_none=True),
        status_code=problem.status,
        media_type=PROBLEM_MEDIA_TYPE,
    )


def _title(status: int) -> str:
    try:
        return HTTPStatus(status).phrase
    except ValueError:
        return "Error"


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ProblemError)
    async def _problem(request: Request, exc: ProblemError) -> JSONResponse:
        return _response(
            Problem(
                type=PROBLEM_BASE + exc.code,
                title=_title(exc.status),
                status=exc.status,
                detail=exc.detail,
                instance=request.url.path,
            )
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _response(
            Problem(
                title=_title(exc.status_code),
                status=exc.status_code,
                detail=str(exc.detail) if exc.detail else None,
                instance=request.url.path,
            )
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {"loc": list(e.get("loc", ())), "msg": e.get("msg"), "type": e.get("type")}
            for e in exc.errors()
        ]
        return _response(
            Problem(
                type=PROBLEM_BASE + "validation-error",
                title="Unprocessable Content",
                status=422,
                detail="Request validation failed",
                instance=request.url.path,
                errors=errors,
            )
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        return _response(
            Problem(
                title="Internal Server Error",
                status=500,
                detail="An unexpected error occurred",
                instance=request.url.path,
            )
        )
