"""Détection des secrets, mots de passe des relecteurs, quotas, configuration."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.security.auth import hash_password, parse_reviewers, verify_password
from app.security.ratelimit import RateLimiter, client_ip
from app.security.secrets import scan_text

# Clés FICTIVES, au bon format. Elles sont coupées en morceaux pour que le texte de ce
# fichier ne déclenche pas lui-même scripts/scan_secrets.py.
FAKE = "Zx8Yw7Vu6Ts5Rq4P"
SECRETS = {
    "clé privée": "-----BEGIN RSA " + "PRIVATE KEY-----",
    "jeton JWT": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0."
    + "dBjftJeZ4CVPmB92K27uhbUJU1p1r",
    "clé AWS": "AKIA" + "ABCDEFGHIJKLMNOP",
    "jeton GitHub": "ghp_" + "a1B2" * 9,
    "clé secrète Flutterwave": "FLWSECK_TEST-" + "abc123" * 5 + "-X",
    "clé secrète Paystack ou Stripe": "sk_live_" + "Ab12" * 6,
    "clé d'API Wave": "wave_sn_prod_" + "Xy9_" * 6,
    "clé d'abonnement MTN MoMo": "Ocp-Apim-Subscription-Key: " + "0123456789abcdef" * 2,
    "en-tête Authorization": "Authorization: Bearer " + "abcDEF123456" * 3,
    "secret dans une affectation": 'consumer_secret = "' + FAKE + '"',
    "secret dans un fichier .env": "\nCONSUMER_SECRET=" + FAKE + "\n",
    "secret dans un fichier YAML": "\nconsumer_secret: " + FAKE + "\n",
}

NOT_SECRETS = [
    "Authorization: Bearer <VOTRE_JETON>",
    "api_key = xxxxxxxxxxxxxxxxxxxx",
    "consumer_secret: {{ secret }}",
    "CONSUMER_SECRET=<VOTRE_SECRET>",
    "Envoyez l'en-tête X-Target-Environment: sandbox",
    "Le jeton expire au bout de 3600 secondes.",
    # Du code qui manipule un secret sans le contenir :
    "password = base64.b64decode(credentials).decode()",
    "password = settings.reviewer_password",
    "api_key: str = Field(min_length=12)",
    "DATABASE_URL=postgresql://utilisateur:motdepasse@hote:5432/gotcha",
]


@pytest.mark.parametrize(("kind", "text"), list(SECRETS.items()))
def test_each_rule_detects_its_secret(kind: str, text: str) -> None:
    findings = scan_text(f"Voici mon code : {text} fin.")
    assert kind in {f.kind for f in findings}


@pytest.mark.parametrize("text", NOT_SECRETS)
def test_placeholders_code_and_normal_text_are_not_secrets(text: str) -> None:
    assert scan_text(text) == []


def test_reviewer_password_round_trip() -> None:
    encoded = hash_password("un mot de passe solide")
    assert verify_password("un mot de passe solide", encoded)
    assert not verify_password("mauvais", encoded)
    assert not verify_password("x", "pas-une-empreinte")
    assert parse_reviewers(f"aziz:{encoded}; loum:{encoded}") == {"aziz": encoded, "loum": encoded}


def test_rate_limiter_window() -> None:
    now = [0.0]
    limiter = RateLimiter(clock=lambda: now[0])
    assert limiter.hit("k", limit=2, window_seconds=60)
    assert limiter.hit("k", limit=2, window_seconds=60)
    assert not limiter.hit("k", limit=2, window_seconds=60)
    now[0] = 61
    assert limiter.hit("k", limit=2, window_seconds=60)


def test_rate_limiter_check_does_not_count() -> None:
    limiter = RateLimiter(clock=lambda: 0.0)
    assert not limiter.exceeded("k", limit=1, window_seconds=60)
    assert not limiter.exceeded("k", limit=1, window_seconds=60)
    assert limiter.hit("k", limit=1, window_seconds=60)
    assert limiter.exceeded("k", limit=1, window_seconds=60)


# Le visiteur a inventé 6.6.6.6 ; le proxy de confiance a ajouté l'adresse qu'il a vue.
FORWARDED = {"x-forwarded-for": "6.6.6.6, 41.82.1.2"}


@pytest.mark.parametrize(
    ("headers", "hops", "expected"),
    [
        (FORWARDED, 1, "41.82.1.2"),  # la dernière valeur, jamais la première
        (FORWARDED, 2, "6.6.6.6"),  # deux proxys : l'avant-dernière
        (FORWARDED, 0, "10.0.0.1"),  # aucun proxy de confiance : l'en-tête est ignoré
        ({"x-forwarded-for": "41.82.1.2"}, 2, "10.0.0.1"),  # moins de valeurs que de proxys
        ({"x-forwarded-for": " , "}, 1, "10.0.0.1"),
        ({}, 1, "10.0.0.1"),
    ],
)
def test_client_ip_reads_the_value_added_by_trusted_proxies(
    headers: dict[str, str], hops: int, expected: str
) -> None:
    assert client_ip(headers, "10.0.0.1", proxy_hops=hops) == expected
    assert client_ip({}, None, proxy_hops=hops) == "inconnu"


def test_proxy_hops_setting() -> None:
    assert Settings.from_env({}).proxy_hops == 0
    prod = {"GOTCHA_ENV": "prod", "DATABASE_URL": "postgresql://x", "GOTCHA_MCP_AUTH": "0"}
    assert Settings.from_env(prod).proxy_hops == 1
    assert Settings.from_env({**prod, "GOTCHA_PROXY_HOPS": "2"}).proxy_hops == 2
    with pytest.raises(ValueError, match="GOTCHA_PROXY_HOPS"):
        Settings.from_env({"GOTCHA_PROXY_HOPS": "-1"})


PROD_WITH_CONNECTION = {
    "GOTCHA_ENV": "prod",
    "DATABASE_URL": "postgresql://x",
    "GOTCHA_SITE_URL": "https://gotcha.test",
    "GOTCHA_GITHUB_CLIENT_ID": "identifiant",
    "GOTCHA_GITHUB_CLIENT_SECRET": "secret-a-cacher",
}


def test_production_requires_the_mcp_connection_by_default() -> None:
    settings = Settings.from_env(PROD_WITH_CONNECTION)
    assert settings.mcp_auth
    assert "secret-a-cacher" not in repr(settings)
    assert not Settings.from_env({}).mcp_auth


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"GOTCHA_GITHUB_CLIENT_SECRET": ""}, "GOTCHA_GITHUB_CLIENT_SECRET"),
        ({"GOTCHA_GITHUB_CLIENT_ID": ""}, "GOTCHA_GITHUB_CLIENT_ID"),
        ({"GOTCHA_STORE": "memory"}, "PostgreSQL"),
        ({"GOTCHA_SITE_URL": "http://gotcha.test"}, "https"),
    ],
)
def test_unsafe_mcp_connection_settings_are_refused(change: dict[str, str], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        Settings.from_env({**PROD_WITH_CONNECTION, **change})


def test_production_settings_are_safe() -> None:
    settings = Settings.from_env(
        {"GOTCHA_ENV": "prod", "DATABASE_URL": "postgresql://x", "GOTCHA_MCP_AUTH": "0"}
    )
    assert settings.store == "postgres"
    assert not settings.show_drafts
    assert not settings.load_fixtures
    assert settings.ingest_live
    with pytest.raises(ValueError, match="brouillons"):
        Settings.from_env(
            {
                "GOTCHA_ENV": "prod",
                "DATABASE_URL": "x",
                "GOTCHA_SHOW_DRAFTS": "1",
                "GOTCHA_MCP_AUTH": "0",
            }
        )
    with pytest.raises(ValueError, match="DATABASE_URL"):
        Settings.from_env({"GOTCHA_STORE": "postgres"})
