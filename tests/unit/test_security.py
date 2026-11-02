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


def test_client_ip_trusts_proxy_only_when_asked() -> None:
    headers = {"x-forwarded-for": "41.82.1.2, 10.0.0.1"}
    assert client_ip(headers, "10.0.0.1", trust_proxy=True) == "41.82.1.2"
    assert client_ip(headers, "10.0.0.1", trust_proxy=False) == "10.0.0.1"


def test_production_settings_are_safe() -> None:
    settings = Settings.from_env({"GOTCHA_ENV": "prod", "DATABASE_URL": "postgresql://x"})
    assert settings.store == "postgres"
    assert not settings.show_drafts
    assert not settings.load_fixtures
    assert settings.ingest_live
    with pytest.raises(ValueError, match="brouillons"):
        Settings.from_env({"GOTCHA_ENV": "prod", "DATABASE_URL": "x", "GOTCHA_SHOW_DRAFTS": "1"})
    with pytest.raises(ValueError, match="DATABASE_URL"):
        Settings.from_env({"GOTCHA_STORE": "postgres"})
