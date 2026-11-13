"""Accès des relecteurs en production, santé du service, choix du stockage."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from app.config import Settings
from app.security.auth import MAX_FAILURES, hash_password
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


def test_review_blocks_an_address_after_repeated_failures(clock: FixedClock) -> None:
    with make_client(_prod_settings(f"aziz:{hash_password(PASSWORD)}"), clock) as client:
        for _ in range(3):  # sans identifiants : le navigateur demande, rien n'est compté
            assert client.get("/relecture").status_code == 401
        for _ in range(MAX_FAILURES):
            assert client.get("/relecture", auth=("aziz", "faux")).status_code == 401
        # Bloqué, même avec le bon mot de passe, sans calcul scrypt.
        assert client.get("/relecture", auth=("aziz", PASSWORD)).status_code == 429
        client.app.state.rate_limiter.reset()  # type: ignore[attr-defined]
        assert client.get("/relecture", auth=("aziz", PASSWORD)).status_code == 200


def test_review_treats_unknown_pseudo_and_garbage_as_failures(clock: FixedClock) -> None:
    with make_client(_prod_settings(f"aziz:{hash_password(PASSWORD)}"), clock) as client:
        assert client.get("/relecture", auth=("inconnu", PASSWORD)).status_code == 401
        garbage = {"Authorization": "Basic %%%"}
        assert client.get("/relecture", headers=garbage).status_code == 401


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


def test_failures_on_another_pseudo_do_not_block_a_reviewer(clock: FixedClock) -> None:
    with make_client(_prod_settings(f"aziz:{hash_password(PASSWORD)}"), clock) as client:
        for _ in range(MAX_FAILURES):
            assert client.get("/relecture", auth=("inconnu", "faux")).status_code == 401
        assert client.get("/relecture", auth=("inconnu", "faux")).status_code == 429
        assert client.get("/relecture", auth=("aziz", PASSWORD)).status_code == 200


def test_successful_pages_do_not_use_up_the_attempts(clock: FixedClock) -> None:
    # HTTP Basic renvoie le mot de passe à chaque page : seuls les échecs comptent.
    with make_client(_prod_settings(f"aziz:{hash_password(PASSWORD)}"), clock) as client:
        for _ in range(MAX_FAILURES + 2):
            assert client.get("/relecture", auth=("aziz", PASSWORD)).status_code == 200
        assert client.get("/relecture", auth=("aziz", "faux")).status_code == 401


def test_changing_pseudo_at_each_attempt_does_not_avoid_the_block(clock: FixedClock) -> None:
    with make_client(_prod_settings(f"aziz:{hash_password(PASSWORD)}"), clock) as client:
        codes = [client.get("/relecture", auth=(f"x{n}", "faux")).status_code for n in range(12)]
        assert codes[:MAX_FAILURES] == [401] * MAX_FAILURES
        assert codes[MAX_FAILURES:] == [429] * (12 - MAX_FAILURES)
        # Le vrai relecteur garde son propre compteur.
        assert client.get("/relecture", auth=("aziz", PASSWORD)).status_code == 200


def test_healthz_db_check_is_rate_limited(client: TestClient) -> None:
    from app.web.routes.health import DB_CHECK_LIMIT

    codes = [client.get("/healthz?db=1").status_code for _ in range(DB_CHECK_LIMIT + 1)]
    assert codes[:-1] == [200] * DB_CHECK_LIMIT
    assert codes[-1] == 429
    # Le contrôle simple, appelé par l'hébergeur, reste toujours libre.
    assert client.get("/healthz").status_code == 200


def test_healthz_does_not_tell_the_environment(client: TestClient) -> None:
    assert client.get("/healthz").json() == {"status": "ok"}
