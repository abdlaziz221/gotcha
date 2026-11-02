"""Pages d'erreur (404, 400, 401, 403, 429, 500), ou JSON pour /mcp et /healthz."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse, Response

from app.domain.errors import InvalidInputError, NotFoundError
from app.web.templating import render
from app.web.viewmodels import ErrorPage, PageMeta

log = logging.getLogger(__name__)

MESSAGES = {
    400: "La demande est invalide.",
    401: "Identifiez-vous pour accéder à la relecture.",
    403: "Accès refusé.",
    404: "Cette page n'existe pas, ou plus.",
    429: "Trop de demandes : réessayez dans quelques minutes.",
    500: "Une erreur inattendue s'est produite. Réessayez dans un instant.",
}
TITLES = {404: "Page introuvable", 429: "Trop de demandes", 500: "Erreur du serveur"}


def _error_response(
    request: Request, status_code: int, message: str | None, headers: dict[str, str] | None = None
) -> Response:
    if request.url.path.startswith(("/mcp", "/healthz")):
        return JSONResponse({"detail": message}, status_code=status_code, headers=headers)
    page = ErrorPage(
        meta=PageMeta(title=TITLES.get(status_code, "Erreur"), path=request.url.path, noindex=True),
        status_code=status_code,
        message=message or MESSAGES.get(status_code, "Erreur."),
    )
    response = render(request, "pages/error.html", page, status_code=status_code)
    if headers:
        response.headers.update(headers)
    return response


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> Response:
        detail = exc.detail if isinstance(exc.detail, str) and exc.status_code != 404 else None
        if detail and detail == "Not Found":
            detail = None
        return _error_response(request, exc.status_code, detail, exc.headers)

    @app.exception_handler(NotFoundError)
    async def not_found(request: Request, exc: NotFoundError) -> Response:
        return _error_response(request, 404, None)

    @app.exception_handler(InvalidInputError)
    async def invalid_input(request: Request, exc: InvalidInputError) -> Response:
        return _error_response(request, 400, str(exc))

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, exc: RequestValidationError) -> Response:
        return _error_response(request, 400, None)

    @app.exception_handler(Exception)
    async def server_error(request: Request, exc: Exception) -> Response:
        log.exception("erreur inattendue sur %s", request.url.path)
        return _error_response(request, 500, None)
