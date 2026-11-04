"""Retour de GitHub après la connexion d'un développeur (voir app/services/oauth.py)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from starlette.responses import RedirectResponse

from app.security.ratelimit import rate_limit
from app.web.deps import ServicesDep

router = APIRouter()


@router.get(
    "/github/callback",
    dependencies=[Depends(rate_limit("connexion", limit=60, window_seconds=3600))],
)
async def github_callback(
    services: ServicesDep, state: str = "", code: str | None = None, error: str | None = None
) -> RedirectResponse:
    if not services.settings.mcp_auth:
        raise HTTPException(status_code=404)
    return RedirectResponse(await services.oauth.finish_login(state, code, error), status_code=302)
