"""Accès des relecteurs en production, santé du service, choix du stockage."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from app.config import Settings
from app.security.auth import hash_password
from app.services.clock import FixedClock
from app.stores import create_store
from tests.conftest import make_client

PASSWORD = "mot-de-passe-de-test-solide"  # secret-scan: ignore (mot de passe de test)


def _prod_settings(reviewers: str) -> Settings:
    return Settings(
        env="prod",
        store="memory",
        show_drafts=False,
        load_fixtures=False,
        ingest_live=False,
        reviewers=reviewers,
    )


def test_review_requires_valid_credentials_in_production(clock: FixedClock) -> None:
    with make_client(_prod_settings(f"aziz:{hash_password(PASSWORD)}"), clock) as client:
        anonymous = client.get("/relecture")
        assert anonymous.status_code == 401
        assert "Basic" in anonymous.headers["www-authenticate"]
        assert client.get("/relecture", auth=("aziz", "faux")).status_code == 401
        assert client.get("/relecture", auth=("inconnu", PASSWORD)).status_code == 401
        allowed = client.get("/relecture", auth=("aziz", PASSWORD))
        assert allowed.status_code == 200
        assert "aziz" in allowed.text


def test_healthz_reports_missing_database(client: TestClient) -> None:
    body = client.get("/healthz?db=1").json()
    assert body["status"] == "ok"
    assert body["database"] == "non configurée"


@pytest.mark.anyio
async def test_create_store_picks_memory_by_default() -> None:
    store = await create_store(Settings(env="test"))
    assert await store.list_fiches(include_drafts=True)
    await store.close()


@pytest.mark.anyio
async def test_create_store_postgres_requires_a_url() -> None:
    with pytest.raises(ValueError, match="DATABASE_URL"):
        await create_store(Settings(env="test", store="postgres"))
