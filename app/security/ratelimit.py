"""Quotas par adresse IP, en mémoire (fenêtre glissante).

Limite connue : sur le Serverless, chaque instance a ses propres compteurs. Suffisant
pour le MVP ; à déplacer dans PostgreSQL si on constate des abus.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from collections.abc import Callable, Mapping

from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str, *, limit: int, window_seconds: float) -> bool:
        """Compte un appel ; renvoie False si le quota est dépassé."""
        now = self._clock()
        hits = self._hits[key]
        while hits and now - hits[0] > window_seconds:
            hits.popleft()
        if len(hits) >= limit:
            return False
        hits.append(now)
        return True

    def exceeded(self, key: str, *, limit: int, window_seconds: float) -> bool:
        """Le quota est-il déjà atteint ? (ne compte pas d'appel)"""
        now = self._clock()
        hits = self._hits[key]
        while hits and now - hits[0] > window_seconds:
            hits.popleft()
        return len(hits) >= limit

    def reset(self) -> None:
        self._hits.clear()


def client_ip(headers: Mapping[str, str], peer: str | None, *, proxy_hops: int) -> str:
    """Adresse du visiteur, pour les quotas.

    Chaque proxy de confiance ajoute à la fin de X-Forwarded-For l'adresse qu'il a vue :
    derrière `proxy_hops` proxys, la bonne valeur est la `proxy_hops`-ième en partant de
    la fin. Les valeurs plus à gauche viennent du visiteur, qui peut les inventer.
    """
    if proxy_hops > 0:
        forwarded = [v.strip() for v in headers.get("x-forwarded-for", "").split(",")]
        forwarded = [v for v in forwarded if v]
        if len(forwarded) >= proxy_hops:
            return forwarded[-proxy_hops]
    return peer or "inconnu"


def rate_limit(name: str, *, limit: int, window_seconds: float) -> Callable[[Request], None]:
    """Fabrique une dépendance FastAPI.

    Exemple : Depends(rate_limit("contribuer", limit=5, window_seconds=3600)).
    """

    def dependency(request: Request) -> None:
        settings = request.app.state.settings
        peer = request.client.host if request.client else None
        ip = client_ip(request.headers, peer, proxy_hops=settings.proxy_hops)
        limiter: RateLimiter = request.app.state.rate_limiter
        if not limiter.hit(f"{name}:{ip}", limit=limit, window_seconds=window_seconds):
            raise HTTPException(status_code=429, detail="Trop de demandes : réessayez plus tard.")

    return dependency
