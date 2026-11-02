"""Import du flux public d'incidents de Flutterwave (format Statuspage v2). Responsable : Khalifa.

Le flux ne donne ni opérateur ni pays sous forme structurée : on les déduit du
texte (titre et messages). Les règles ci-dessous sont un point de départ, testées
sur un extrait réel enregistré dans fixtures/flutterwave_incidents.json.

Lecture réseau avec urllib (bibliothèque standard) : ni requests ni httpx, qui
entraînent certifi (licence MPL).
"""

from __future__ import annotations

import asyncio
import html
import json
import re
import unicodedata
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from app.domain.models import Incident, IncidentSource, Status

# Mots repérés dans le texte -> service suivi. None : opérateur connu mais non suivi.
OPERATORS: dict[str, str | None] = {
    "orange": "orange-money",
    "mtn": "mtn-momo",
    "m-pesa": "mpesa",
    "mpesa": "mpesa",
    "safaricom": "mpesa",
    "wave": "wave",
    "airtel": None,
    "telecel": None,
    "vodafone": None,
    "moov": None,
    "free money": None,
    "intouch": None,  # agrégateur
    "jambopay": None,
}

COUNTRY_WORDS: dict[str, str] = {
    "senegal": "SN",
    "cote d'ivoire": "CI",
    "ivory coast": "CI",
    "cameroon": "CM",
    "cameroun": "CM",
    "burkina faso": "BF",
    "mali": "ML",
    "benin": "BJ",
    "togo": "TG",
    "niger": "NE",
    "nigeria": "NG",
    "ghana": "GH",
    "kenya": "KE",
    "uganda": "UG",
    "tanzania": "TZ",
    "rwanda": "RW",
    "zambia": "ZM",
}

# Devises d'un seul pays. XOF et XAF couvrent plusieurs pays : on n'en déduit rien.
CURRENCY_COUNTRIES: dict[str, str] = {
    "GHS": "GH",
    "KES": "KE",
    "UGX": "UG",
    "TZS": "TZ",
    "RWF": "RW",
    "ZMW": "ZM",
    "NGN": "NG",
}

MOBILE_MONEY_WORDS = ("mobile money", "momo")


def _norm(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", html.unescape(text))
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def _contains_word(text: str, word: str) -> bool:
    return re.search(rf"\b{re.escape(word)}\b", text) is not None


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def map_incident(raw: dict[str, Any]) -> list[Incident]:
    """Traduit un incident Statuspage en zéro, une ou plusieurs pannes Gotcha.

    Une panne par couple (service, pays). Rien si l'incident ne concerne pas le
    Mobile Money, ou seulement des opérateurs que Gotcha ne suit pas.
    """
    updates = raw.get("incident_updates") or []
    text = _norm(" ".join([raw.get("name", "")] + [u.get("body", "") for u in updates]))

    operators = {op for word, op in OPERATORS.items() if _contains_word(text, word)}
    tracked = sorted(op for op in operators if op)
    if operators and not tracked:
        return []
    if not operators and not any(w in text for w in MOBILE_MONEY_WORDS):
        return []

    countries = sorted({c for w, c in COUNTRY_WORDS.items() if _contains_word(text, w)})
    if not countries:
        countries = sorted(
            {c for cur, c in CURRENCY_COUNTRIES.items() if _contains_word(text, cur.lower())}
        )

    resolved_at = _parse_dt(raw["resolved_at"]) if raw.get("resolved_at") else None
    if resolved_at is None and raw.get("status") in ("resolved", "postmortem"):
        resolved_at = _parse_dt(raw["updated_at"])
    latest = html.unescape(updates[0]["body"]).strip() if updates else None

    return [
        Incident(
            id=f"flutterwave:{raw['id']}:{country or 'all'}:{service or 'all'}",
            source=IncidentSource.FLUTTERWAVE,
            external_id=raw["id"],
            service_slug=service,
            country=country,
            status=Status.DOWN if raw.get("impact") == "critical" else Status.DEGRADED,
            title=html.unescape(raw.get("name", "")).strip(),
            description=latest[:600] if latest else None,
            url=raw.get("shortlink") or None,
            started_at=_parse_dt(raw.get("started_at") or raw["created_at"]),
            resolved_at=resolved_at,
        )
        for service in (tracked or [None])
        for country in (countries or [None])
    ]


def parse_incidents(payload: dict[str, Any]) -> list[Incident]:
    return [incident for raw in payload.get("incidents", []) for incident in map_incident(raw)]


class FlutterwaveFeed:
    """Flux Flutterwave : en direct (live) ou depuis l'extrait enregistré (développement)."""

    source = IncidentSource.FLUTTERWAVE

    def __init__(self, *, url: str, live: bool, fixture_path: Path, timeout: float = 5.0) -> None:
        self.url = url
        self.live = live
        self.fixture_path = fixture_path
        self.timeout = timeout

    async def fetch(self) -> list[Incident]:
        if self.live:
            payload = await asyncio.to_thread(self._read_live)
        else:
            payload = json.loads(self.fixture_path.read_text(encoding="utf-8"))
        return parse_incidents(payload)

    def _read_live(self) -> dict[str, Any]:
        if not self.url.startswith("https://"):
            raise ValueError(f"URL de flux non HTTPS refusée : {self.url}")
        request = urllib.request.Request(  # noqa: S310 (schéma https vérifié ci-dessus)
            self.url,
            headers={"User-Agent": "gotcha-status-reader/0.1", "Accept": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:  # noqa: S310
            return json.loads(response.read(2_000_000))
