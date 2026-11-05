"""Sonde des limites de l'hébergeur (tâche A2) : active avec GOTCHA_PROBE=1, sinon introuvable.

À activer le temps des mesures, puis à désactiver. scripts/probe_platform.py interroge ces
adresses et rédige le compte rendu : durée maximale d'une requête, tâches de fond après la
réponse, accès à la base, sortie vers Internet, en-têtes du proxy, démarrage à froid.
Chaque réponse indique l'instance qui a répondu (nom de machine et processus).
"""

from __future__ import annotations

import asyncio
import hmac
import os
import socket
import time
import urllib.request
from datetime import UTC, datetime
from typing import Annotated, Any

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from starlette.responses import JSONResponse

from app.security.ratelimit import client_ip, rate_limit
from app.web.deps import ServicesDep

TOKEN_HEADER = "x-sonde-jeton"  # noqa: S105 (nom d'en-tête, pas un secret)


def require_token(request: Request) -> None:
    """Sans le jeton partagé (GOTCHA_PROBE_TOKEN), la sonde n'existe pas : 404."""
    expected = request.app.state.settings.probe_token
    sent = request.headers.get(TOKEN_HEADER, "")
    # Comparaison en octets : compare_digest refuse les chaînes non ASCII.
    if not expected or not hmac.compare_digest(sent.encode(), expected.encode()):
        raise HTTPException(status_code=404)


# Quota d'abord : les essais de jeton comptent aussi. Une mesure complète fait ~20 appels,
# et /base ouvre une connexion par appel : le quota protège une petite base managée.
router = APIRouter(
    prefix="/_sonde",
    dependencies=[
        Depends(rate_limit("sonde", limit=60, window_seconds=3600)),
        Depends(require_token),
    ],
)

MAX_WAIT_SECONDS = 300
Seconds = Annotated[float, Query(ge=0, le=MAX_WAIT_SECONDS)]

# Module importé au démarrage du processus : sert à repérer un démarrage à froid.
_STARTED = time.monotonic()


def _instance() -> dict[str, Any]:
    return {
        "instance": f"{socket.gethostname()}:{os.getpid()}",
        "en_service_depuis_s": round(time.monotonic() - _STARTED, 1),
    }


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _ms(start: float) -> int:
    return round((time.monotonic() - start) * 1000)


@router.get("/requete")
async def request_info(request: Request, services: ServicesDep) -> JSONResponse:
    """Ce que le proxy transmet : adresse du client, protocole, en-têtes (noms seulement)."""
    headers = request.headers
    peer = request.client.host if request.client else None
    return JSONResponse(
        {
            **_instance(),
            "pair": peer,
            "protocole": request.url.scheme,
            "host": headers.get("host"),
            "x_forwarded_for": headers.get("x-forwarded-for"),
            "x_forwarded_proto": headers.get("x-forwarded-proto"),
            "x_real_ip": headers.get("x-real-ip"),
            "ip_retenue_pour_les_quotas": client_ip(
                headers, peer, trust_proxy=services.settings.trust_proxy
            ),
            "en_tetes": sorted(headers.keys()),
        }
    )


@router.get("/attente")
async def wait(secondes: Seconds = 0) -> JSONResponse:
    """Répond après `secondes` : la plus longue attente qui aboutit est la durée maximale."""
    start = time.monotonic()
    await asyncio.sleep(secondes)
    return JSONResponse({**_instance(), "attente_s": secondes, "duree_ms": _ms(start)})


async def _finish_later(record: dict[str, Any], seconds: float) -> None:
    await asyncio.sleep(seconds)
    record["terminee_le"] = _now()


@router.get("/tache-de-fond")
async def background(request: Request, lancer: Seconds | None = None) -> JSONResponse:
    """?lancer=N démarre une tâche qui se termine N secondes après la réponse ; sans
    paramètre, indique si elle s'est terminée (sur cette instance)."""
    state = request.app.state
    if lancer is not None:
        record: dict[str, Any] = {"lancee_le": _now(), "duree_s": lancer, "terminee_le": None}
        state.probe_background = record
        task = asyncio.create_task(_finish_later(record, lancer))
        tasks: set[asyncio.Task[None]] = getattr(state, "probe_tasks", set())
        state.probe_tasks = tasks
        tasks.add(task)  # garder une référence : sinon la tâche peut être ramassée
        task.add_done_callback(tasks.discard)
    return JSONResponse({**_instance(), "tache": getattr(state, "probe_background", None)})


@router.get("/base")
async def database(services: ServicesDep) -> JSONResponse:
    """Durée d'une connexion neuve à la base et d'une requête, chiffrement SSL, version."""
    url = services.settings.database_url
    if not url:
        return JSONResponse({**_instance(), "base": "non configurée"})
    start = time.monotonic()
    try:
        conn = await asyncio.wait_for(asyncpg.connect(url), timeout=10)
        connect_ms = _ms(start)
        try:
            query_start = time.monotonic()
            row = await conn.fetchrow(
                "SELECT version() AS version,"
                " coalesce((SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()), false)"
                " AS ssl"
            )
            query_ms = _ms(query_start)
        finally:
            await conn.close()
    except Exception as exc:  # on ne renvoie que le type d'erreur, jamais l'URL de connexion
        return JSONResponse(
            {**_instance(), "base": f"erreur : {type(exc).__name__}", "duree_ms": _ms(start)}
        )
    return JSONResponse(
        {
            **_instance(),
            "base": "ok",
            "connexion_ms": connect_ms,
            "requete_ms": query_ms,
            "ssl": bool(row["ssl"]) if row else None,
            "version": row["version"] if row else None,
        }
    )


def _fetch_status(url: str) -> int:
    request = urllib.request.Request(url, headers={"User-Agent": "gotcha-sonde/0.1"})  # noqa: S310
    # Adresse fixe, lue dans la configuration : aucune adresse ne vient de la requête.
    with urllib.request.urlopen(request, timeout=10) as response:  # noqa: S310
        return response.status


@router.get("/sortie")
async def outbound(services: ServicesDep) -> JSONResponse:
    """L'instance joint-elle Internet ? (le flux de pannes Flutterwave, lu par l'import)."""
    url = services.settings.flutterwave_feed_url
    start = time.monotonic()
    try:
        status = await asyncio.to_thread(_fetch_status, url)
    except Exception as exc:
        return JSONResponse(
            {**_instance(), "sortie": f"erreur : {type(exc).__name__}", "duree_ms": _ms(start)}
        )
    return JSONResponse({**_instance(), "sortie": "ok", "code": status, "duree_ms": _ms(start)})
