"""Sonde des limites de l'hébergeur (/_sonde/…, tâche A2)."""

from __future__ import annotations

import os
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from starlette.testclient import TestClient

from app.config import PROBE_TOKEN_MIN_LENGTH, Settings
from app.services.clock import FixedClock
from tests.conftest import make_client

# Rien n'écoute sur le port 9 : la connexion est refusée tout de suite, sans réseau.
UNREACHABLE = "http://127.0.0.1:9/"


TOKEN = "jeton-de-test-de-la-sonde-0123"


@contextmanager
def probe_client(settings: Settings, clock: FixedClock) -> Iterator[TestClient]:
    """Client qui envoie le jeton partagé, comme scripts/probe_platform.py."""
    with make_client(settings, clock) as client:
        client.headers["X-Sonde-Jeton"] = TOKEN
        yield client


@pytest.fixture
def probe_settings() -> Settings:
    return Settings(env="test", probe=True, probe_token=TOKEN, proxy_hops=1)


@pytest.fixture
def probe(probe_settings: Settings, clock: FixedClock) -> Iterator[TestClient]:
    with probe_client(probe_settings, clock) as client:
        yield client


def test_probe_needs_the_shared_token(probe_settings: Settings, clock: FixedClock) -> None:
    with make_client(probe_settings, clock) as client:
        assert client.get("/_sonde/requete").status_code == 404
        reply = client.get("/_sonde/requete", headers={"X-Sonde-Jeton": "x" * len(TOKEN)})
        assert reply.status_code == 404
        # Octets non ASCII : compare_digest sur des str lèverait TypeError (erreur 500).
        accented = ("é" * len(TOKEN)).encode("latin-1")
        assert (
            client.get("/_sonde/requete", headers={b"X-Sonde-Jeton": accented}).status_code == 404
        )
        reply = client.get("/_sonde/requete", headers={"X-Sonde-Jeton": TOKEN})
        assert reply.status_code == 200


def test_probe_cannot_be_enabled_without_a_long_token() -> None:
    with pytest.raises(ValueError, match="GOTCHA_PROBE_TOKEN"):
        Settings.from_env({"GOTCHA_PROBE": "1"})
    with pytest.raises(ValueError, match="GOTCHA_PROBE_TOKEN"):
        Settings.from_env({"GOTCHA_PROBE": "1", "GOTCHA_PROBE_TOKEN": "court"})
    token = "t" * PROBE_TOKEN_MIN_LENGTH
    assert Settings.from_env({"GOTCHA_PROBE": "1", "GOTCHA_PROBE_TOKEN": token}).probe


def test_probe_calls_are_rate_limited(probe: TestClient) -> None:
    codes = [probe.get("/_sonde/attente?secondes=0").status_code for _ in range(61)]
    assert codes[:60] == [200] * 60
    assert codes[60] == 429


def test_probe_is_hidden_unless_enabled(client: TestClient, prod_client: TestClient) -> None:
    for c in (client, prod_client):
        assert c.get("/_sonde/requete").status_code == 404
    assert not Settings.from_env({}).probe


def test_request_shows_what_the_proxy_sends(probe: TestClient) -> None:
    body = probe.get("/_sonde/requete", headers={"X-Forwarded-For": "203.0.113.7, 10.0.0.2"}).json()
    assert body["x_forwarded_for"] == "203.0.113.7, 10.0.0.2"
    # Un proxy de confiance : la dernière valeur, ajoutée par lui ; la première est inventable.
    assert body["ip_retenue_pour_les_quotas"] == "10.0.0.2"
    assert body["protocole"] == "http"
    assert "x-forwarded-for" in body["en_tetes"]
    assert body["instance"].endswith(f":{os.getpid()}")


def test_wait_is_bounded(probe: TestClient) -> None:
    assert probe.get("/_sonde/attente?secondes=0").json()["attente_s"] == 0
    assert probe.get("/_sonde/attente?secondes=301").status_code == 400


def test_background_task_finishes_after_the_response(probe: TestClient) -> None:
    assert probe.get("/_sonde/tache-de-fond").json()["tache"] is None
    started = probe.get("/_sonde/tache-de-fond?lancer=0.05").json()["tache"]
    assert started["terminee_le"] is None
    deadline = time.monotonic() + 5
    finished = None
    while finished is None and time.monotonic() < deadline:
        time.sleep(0.05)
        finished = probe.get("/_sonde/tache-de-fond").json()["tache"]["terminee_le"]
    assert finished is not None


def test_database_without_url(probe: TestClient) -> None:
    assert probe.get("/_sonde/base").json()["base"] == "non configurée"


def test_errors_name_the_problem_without_leaking_the_address(
    probe_settings: Settings, clock: FixedClock
) -> None:
    settings = replace(
        probe_settings,
        database_url="postgresql://gotcha:motdepasse@127.0.0.1:9/gotcha",  # secret-scan: ignore
        flutterwave_feed_url=UNREACHABLE,
    )
    with probe_client(settings, clock) as client:
        database = client.get("/_sonde/base")
        outbound = client.get("/_sonde/sortie").json()
    assert database.json()["base"].startswith("erreur : ")
    assert "motdepasse" not in database.text
    assert outbound["sortie"].startswith("erreur : ")


def test_outbound_reaches_the_feed(probe_settings: Settings, clock: FixedClock) -> None:
    class Feed(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Feed)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        feed = f"http://127.0.0.1:{server.server_port}/incidents.json"
        with probe_client(replace(probe_settings, flutterwave_feed_url=feed), clock) as client:
            body = client.get("/_sonde/sortie").json()
    finally:
        server.shutdown()
    assert body["sortie"] == "ok"
    assert body["code"] == 200


@pytest.mark.postgres
def test_database_reports_latency_and_ssl(probe_settings: Settings, clock: FixedClock) -> None:
    url = os.environ.get("GOTCHA_TEST_DATABASE_URL")
    if not url:
        pytest.skip("GOTCHA_TEST_DATABASE_URL non défini")
    with probe_client(replace(probe_settings, database_url=url), clock) as client:
        body = client.get("/_sonde/base").json()
    assert body["base"] == "ok"
    assert body["connexion_ms"] >= 0
    assert body["ssl"] in (True, False)
    assert "PostgreSQL" in body["version"]
