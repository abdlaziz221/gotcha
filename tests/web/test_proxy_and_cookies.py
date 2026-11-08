"""Cookies voisins mal formés, jeton CSRF non ASCII, protocole d'origine derrière le proxy."""

from __future__ import annotations

import re
from dataclasses import replace

from starlette.datastructures import Headers
from starlette.testclient import TestClient

from app.config import Settings
from app.security.csrf import COOKIE_NAME
from app.security.ratelimit import client_ip
from app.services.clock import FixedClock
from tests.conftest import make_client


def _token(client: TestClient) -> str:
    match = re.search(r'name="csrf_token" value="([^"]+)"', client.get("/contribuer").text)
    assert match
    return match.group(1)


def test_a_malformed_neighbour_cookie_breaks_nothing(client: TestClient) -> None:
    # Un sous-domaine voisin peut poser ces cookies : ni erreur 500, ni jeton perdu.
    assert client.get("/", headers={"Cookie": "a/b=1"}).status_code == 200
    token = _token(client)
    cookie = f"foo=bar baz; {COOKIE_NAME}={token}"
    client.cookies.clear()
    reply = client.post(
        "/contribuer",
        data={"csrf_token": token, "licence": "non"},
        headers={"Cookie": cookie},
    )
    assert reply.status_code == 422  # formulaire refusé pour ses champs, pas pour le jeton


def test_a_non_ascii_csrf_token_is_refused_not_a_crash(client: TestClient) -> None:
    _token(client)
    assert client.post("/contribuer", data={"csrf_token": "é"}).status_code == 403


def test_redirects_keep_https_behind_the_proxy(settings: Settings, clock: FixedClock) -> None:
    with make_client(replace(settings, proxy_hops=1), clock) as client:
        reply = client.get(
            "/pannes/", headers={"X-Forwarded-Proto": "https"}, follow_redirects=False
        )
        assert reply.status_code in (307, 308)
        assert reply.headers["location"].startswith("https://")
    # Sans proxy de confiance, l'en-tête envoyé par le visiteur est ignoré.
    with make_client(settings, clock) as client:
        reply = client.get(
            "/pannes/", headers={"X-Forwarded-Proto": "https"}, follow_redirects=False
        )
        assert reply.headers["location"].startswith("http://")


def test_client_ip_reads_every_forwarded_for_line() -> None:
    # Le proxy ajoute sa propre ligne : la première, posée par le visiteur, ne compte pas.
    headers = Headers(
        raw=[(b"x-forwarded-for", b"203.0.113.7"), (b"x-forwarded-for", b"198.51.100.2")]
    )
    assert client_ip(headers, "10.0.0.1", proxy_hops=1) == "198.51.100.2"
