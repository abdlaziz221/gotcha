"""Accès des relecteurs : authentification HTTP Basic, mots de passe hachés avec scrypt.

GOTCHA_REVIEWERS="aziz:<empreinte>;loum:<empreinte>" ; empreinte générée par
scripts/hash_password.py. En dev et en test, sans relecteur configuré, l'accès est
ouvert sous le pseudo « dev ». En production sans relecteur, /relecture renvoie 404.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import secrets
from functools import cache

from fastapi import HTTPException, Request

from app.security.ratelimit import RateLimiter, client_ip

_N, _R, _P = 2**14, 8, 1

# Essais ratés par adresse IP et par pseudo avant blocage : freine la recherche du mot de
# passe, et chaque essai coûte un calcul scrypt au processeur. Par pseudo : un visiteur qui
# rate ses essais ne bloque pas les autres relecteurs. Un bon mot de passe reste refusé
# pendant le blocage, sinon le blocage n'empêcherait plus de deviner.
MAX_FAILURES = 10
FAILURE_WINDOW_SECONDS = 15 * 60


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P)
    return "$".join(
        [
            "scrypt",
            str(_N),
            str(_R),
            str(_P),
            base64.b64encode(salt).decode(),
            base64.b64encode(digest).decode(),
        ]
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, n, r, p, salt_b64, digest_b64 = encoded.split("$")
        if scheme != "scrypt":
            return False
        salt, expected = base64.b64decode(salt_b64), base64.b64decode(digest_b64)
        digest = hashlib.scrypt(password.encode(), salt=salt, n=int(n), r=int(r), p=int(p))
    except (ValueError, binascii.Error):
        return False
    return hmac.compare_digest(digest, expected)


def parse_reviewers(spec: str) -> dict[str, str]:
    reviewers: dict[str, str] = {}
    for item in spec.split(";"):
        pseudo, _, encoded = item.strip().partition(":")
        if pseudo and encoded:
            reviewers[pseudo] = encoded
    return reviewers


@cache
def _unknown_reviewer_hash() -> str:
    """Empreinte factice : un pseudo inconnu prend autant de temps qu'un mauvais mot de passe."""
    return hash_password(secrets.token_urlsafe(16))


def require_reviewer(request: Request) -> str:
    """Dépendance FastAPI : renvoie le pseudo du relecteur authentifié."""
    settings = request.app.state.settings
    reviewers = parse_reviewers(settings.reviewers)
    if not reviewers:
        if settings.env in ("dev", "test"):
            return "dev"
        raise HTTPException(status_code=404)

    challenge = {"WWW-Authenticate": 'Basic realm="Relecture Gotcha", charset="UTF-8"'}
    scheme, _, credentials = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "basic" or not credentials:
        raise HTTPException(status_code=401, headers=challenge)

    try:
        pseudo, _, password = base64.b64decode(credentials).decode().partition(":")
    except (ValueError, binascii.Error):
        pseudo, password = "", ""
    limiter: RateLimiter = request.app.state.rate_limiter
    peer = request.client.host if request.client else None
    ip = client_ip(request.headers, peer, proxy_hops=settings.proxy_hops)
    key = f"relecture-echec:{ip}:{pseudo[:64]}"
    # L'essai est réservé avant le calcul scrypt : des essais simultanés ne peuvent pas
    # tous passer le contrôle avant que le premier échec soit compté.
    if not limiter.hit(key, limit=MAX_FAILURES, window_seconds=FAILURE_WINDOW_SECONDS):
        raise HTTPException(status_code=429, detail="Trop d'essais : réessayez dans 15 minutes.")
    encoded = reviewers.get(pseudo)
    valid = verify_password(password, encoded or _unknown_reviewer_hash())
    if encoded is None or not valid:
        raise HTTPException(status_code=401, headers=challenge)
    # HTTP Basic renvoie le mot de passe à chaque page : un succès ne consomme pas d'essai.
    limiter.release(key)
    return pseudo
