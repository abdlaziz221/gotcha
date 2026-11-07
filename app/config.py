"""Configuration, lue dans les variables d'environnement (voir .env.example)."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast

ROOT_DIR = Path(__file__).resolve().parent.parent
PROBE_TOKEN_MIN_LENGTH = 24

Env = Literal["dev", "test", "prod"]
StoreKind = Literal["memory", "postgres"]


def _bool(value: str | None, default: bool) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "oui", "on"}


@dataclass(frozen=True)
class Settings:
    env: Env = "dev"
    store: StoreKind = "memory"
    database_url: str | None = None
    content_dir: Path = ROOT_DIR / "content"
    fixtures_dir: Path = ROOT_DIR / "fixtures"
    # Affiche les fiches et pièges en brouillon (jamais en production).
    show_drafts: bool = True
    # Charge les pannes et contributions fictives de fixtures/ (stockage mémoire uniquement).
    load_fixtures: bool = True
    # Lit le vrai flux Flutterwave ; sinon l'extrait enregistré dans fixtures/.
    ingest_live: bool = False
    flutterwave_feed_url: str = "https://status.flutterwave.com/api/v2/incidents.json"
    ingest_min_interval_minutes: int = 10
    # Relecteurs : "pseudo:empreinte;pseudo2:empreinte2" (voir scripts/hash_password.py).
    reviewers: str = ""
    # Valeurs autorisées pour l'en-tête Host du serveur MCP (protection DNS rebinding).
    allowed_hosts: tuple[str, ...] = ("localhost:*", "127.0.0.1:*", "testserver")
    # Derrière le proxy de Datacloud : lire l'adresse du client dans X-Forwarded-For.
    trust_proxy: bool = False
    site_url: str = "http://localhost:8000"
    # Sonde des limites de l'hébergeur (/_sonde/…), le temps du test A2 seulement.
    probe: bool = False
    # Jeton partagé qu'envoie scripts/probe_platform.py (en-tête X-Sonde-Jeton).
    probe_token: str = ""

    @property
    def is_prod(self) -> bool:
        return self.env == "prod"

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        e = os.environ if environ is None else environ
        env = cast(Env, e.get("GOTCHA_ENV", "dev"))
        if env not in ("dev", "test", "prod"):
            raise ValueError(f"GOTCHA_ENV invalide : {env!r} (dev, test ou prod)")
        prod = env == "prod"
        store = cast(StoreKind, e.get("GOTCHA_STORE", "postgres" if prod else "memory"))
        if store not in ("memory", "postgres"):
            raise ValueError(f"GOTCHA_STORE invalide : {store!r} (memory ou postgres)")

        hosts = e.get("GOTCHA_ALLOWED_HOSTS")
        settings = cls(
            env=env,
            store=store,
            database_url=e.get("DATABASE_URL") or None,
            content_dir=Path(e.get("GOTCHA_CONTENT_DIR", str(ROOT_DIR / "content"))),
            fixtures_dir=Path(e.get("GOTCHA_FIXTURES_DIR", str(ROOT_DIR / "fixtures"))),
            show_drafts=_bool(e.get("GOTCHA_SHOW_DRAFTS"), default=not prod),
            load_fixtures=_bool(e.get("GOTCHA_LOAD_FIXTURES"), default=not prod),
            ingest_live=_bool(e.get("GOTCHA_INGEST_LIVE"), default=prod),
            flutterwave_feed_url=e.get("GOTCHA_FLUTTERWAVE_FEED_URL", cls.flutterwave_feed_url),
            ingest_min_interval_minutes=int(e.get("GOTCHA_INGEST_MIN_INTERVAL_MINUTES", "10")),
            reviewers=e.get("GOTCHA_REVIEWERS", ""),
            allowed_hosts=(
                tuple(h.strip() for h in hosts.split(",") if h.strip())
                if hosts
                else cls.allowed_hosts
            ),
            trust_proxy=_bool(e.get("GOTCHA_TRUST_PROXY"), default=prod),
            site_url=e.get("GOTCHA_SITE_URL", cls.site_url).rstrip("/"),
            probe=_bool(e.get("GOTCHA_PROBE"), default=False),
            probe_token=e.get("GOTCHA_PROBE_TOKEN", ""),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.store == "postgres" and not self.database_url:
            raise ValueError("GOTCHA_STORE=postgres demande DATABASE_URL")
        if self.is_prod and self.show_drafts:
            raise ValueError("les brouillons ne doivent jamais être affichés en production")
        if self.probe and len(self.probe_token) < PROBE_TOKEN_MIN_LENGTH:
            raise ValueError(
                f"GOTCHA_PROBE demande GOTCHA_PROBE_TOKEN ({PROBE_TOKEN_MIN_LENGTH} caractères"
                " au moins) : la sonde n'est jamais ouverte à tous"
            )
