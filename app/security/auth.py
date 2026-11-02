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

from fastapi import HTTPException, Request

_N, _R, _P = 2**14, 8, 1


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
        raise HTTPException(status_code=401, headers=challenge) from None
    encoded = reviewers.get(pseudo)
    if encoded is None or not verify_password(password, encoded):
        raise HTTPException(status_code=401, headers=challenge)
    return pseudo
