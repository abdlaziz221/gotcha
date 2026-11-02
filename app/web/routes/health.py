"""Santé du service : /healthz (et /healthz?db=1 pour tester la base PostgreSQL)."""

from __future__ import annotations

import asyncio

import asyncpg
from fastapi import APIRouter
from starlette.responses import JSONResponse

from app.web.deps import ServicesDep

router = APIRouter()


@router.get("/healthz")
async def healthz(services: ServicesDep, db: bool = False) -> JSONResponse:
    settings = services.settings
    body: dict[str, str] = {"status": "ok", "env": settings.env, "store": settings.store}
    if not db:
        return JSONResponse(body)
    if not settings.database_url:
        body["database"] = "non configurée"
        return JSONResponse(body)
    try:
        conn = await asyncio.wait_for(asyncpg.connect(settings.database_url), timeout=5)
        try:
            await conn.fetchval("SELECT 1")
        finally:
            await conn.close()
        body["database"] = "ok"
    except Exception as exc:  # on ne renvoie que le type d'erreur, jamais l'URL de connexion
        body.update(status="degraded", database=f"erreur : {type(exc).__name__}")
        return JSONResponse(body, status_code=503)
    return JSONResponse(body)
