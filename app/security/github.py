"""Identification des développeurs par GitHub. Responsable : Abdoul Aziz.

Aucune permission n'est demandée : GitHub ne donne alors que le profil public. Le jeton
GitHub sert à lire ce profil, puis il est oublié. Lecture réseau avec urllib (bibliothèque
standard) : ni requests ni httpx, qui entraînent certifi (licence MPL).
"""

from __future__ import annotations

import asyncio
import json
import urllib.parse
import urllib.request

from app.domain.errors import IdentityError
from app.domain.models import ExternalIdentity

AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
TOKEN_URL = "https://github.com/login/oauth/access_token"  # noqa: S105 (adresse, pas un secret)
PROFILE_URL = "https://api.github.com/user"


class GitHubIdentity:
    def __init__(self, client_id: str, client_secret: str, *, timeout: float = 5.0) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._timeout = timeout

    def authorize_url(self, *, state: str, redirect_uri: str) -> str:
        query = {"client_id": self._client_id, "redirect_uri": redirect_uri, "state": state}
        return f"{AUTHORIZE_URL}?{urllib.parse.urlencode(query)}"

    async def fetch_identity(self, code: str, redirect_uri: str) -> ExternalIdentity:
        return await asyncio.to_thread(self._fetch_identity, code, redirect_uri)

    def _fetch_identity(self, code: str, redirect_uri: str) -> ExternalIdentity:
        try:
            token = self._exchange_code(code, redirect_uri)
            profile = self._read_json(
                urllib.request.Request(
                    PROFILE_URL,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github+json",
                        "User-Agent": "gotcha",
                    },
                )
            )
            return ExternalIdentity(id=f"github:{profile['id']}", pseudo=str(profile["login"]))
        # Message fixe : ni le code, ni le jeton, ni le secret ne doivent finir dans un journal.
        except (OSError, ValueError, KeyError):
            raise IdentityError("GitHub n'a pas pu identifier ce compte.") from None

    def _exchange_code(self, code: str, redirect_uri: str) -> str:
        form = {
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        }
        answer = self._read_json(
            urllib.request.Request(
                TOKEN_URL,
                data=urllib.parse.urlencode(form).encode(),
                headers={"Accept": "application/json", "User-Agent": "gotcha"},
            )
        )
        return str(answer["access_token"])

    def _read_json(self, request: urllib.request.Request) -> dict[str, object]:
        with urllib.request.urlopen(request, timeout=self._timeout) as response:  # noqa: S310
            data = json.load(response)
        if not isinstance(data, dict):
            raise ValueError("réponse inattendue")
        return data
