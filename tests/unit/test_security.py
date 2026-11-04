"""Détection des secrets, mots de passe des relecteurs, quotas, configuration."""

from __future__ import annotations

import time

import pytest

from app.config import Settings
from app.security.auth import hash_password, parse_reviewers, verify_password
from app.security.ratelimit import RateLimiter, client_ip
from app.security.secrets import RULES, scan_text

# Clés FICTIVES, au bon format. Elles sont coupées en morceaux pour que le texte de ce
# fichier ne déclenche pas lui-même scripts/scan_secrets.py.
FAKE = "Zx8Yw7Vu6Ts5Rq4P"
HEX_32 = "0123456789abcdef" * 2
SECRETS = {
    "clé privée": "-----BEGIN RSA " + "PRIVATE KEY-----",
    "jeton JWT": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0."
    + "dBjftJeZ4CVPmB92K27uhbUJU1p1r",
    "clé AWS": "AKIA" + "ABCDEFGHIJKLMNOP",
    "jeton GitHub": "ghp_" + "a1B2" * 9,
    "clé secrète Flutterwave": "FLWSECK_TEST-" + "abc123" * 5 + "-X",
    "clé secrète Paystack ou Stripe": "sk_live_" + "Ab12" * 6,
    "clé d'API Wave": "wave_sn_prod_" + "Xy9_" * 6,
    "secret de signature Wave": "wave_sn_AKS_" + "a1b2c3d4" * 5,
    "clé d'abonnement MTN MoMo": "Ocp-Apim-Subscription-Key: " + HEX_32,
    "clé marchand Orange Money": '"merchant_key": "' + "a1b2c3d4" + '"',
    "passkey Daraja": "passkey: " + "ab12cd34" * 8,
    "en-tête Authorization": "Authorization: Bearer " + "abcDEF123456" * 3,
    "secret dans une affectation": 'consumer_secret = "' + FAKE + '"',
    "secret sans guillemets": "curl https://api.example.com/v1?api_key=" + FAKE,
    "secret dans un fichier .env": "\nCONSUMER_SECRET=" + FAKE + "\n",
    "secret dans un fichier YAML": "\nconsumer_secret: " + FAKE + "\n",
}

# Pour chaque règle, un texte qui lui ressemble et qui ne doit pas la déclencher.
LOOKALIKES = {
    "clé privée": "-----BEGIN PUBLIC KEY-----",
    "jeton JWT": "eyJhbGciOiJIUzI1NiJ9 est l'en-tête d'un jeton",
    "clé AWS": "Le préfixe AKIA identifie une clé AWS.",
    "jeton GitHub": "Un jeton commence par ghp_ puis des caractères.",
    "clé secrète Flutterwave": "FLWPUBK_TEST-" + "abc123" * 5 + "-X",
    "clé secrète Paystack ou Stripe": "pk_live_" + "Ab12" * 6,
    # L'exemple tronqué de docs.wave.com.
    "clé d'API Wave": "Authorization: Bearer wave_sn_prod_YhUNb9d...i4bA6",
    "secret de signature Wave": "wave_sn_AKS_" + "X" * 40,
    "clé d'abonnement MTN MoMo": "Ocp-Apim-Subscription-Key: {{subscription_key}}",
    "clé marchand Orange Money": "merchant_key: process.env.OM_MERCHANT_KEY",
    "passkey Daraja": "La passkey Daraja compte 64 caractères.",
    "en-tête Authorization": "Authorization: Bearer <VOTRE_JETON>",
    "secret dans une affectation": "password = settings.reviewer_password",
    "secret sans guillemets": "password = get_reviewer_password_v2()",
    "secret dans un fichier .env": "CONSUMER_SECRET=<VOTRE_SECRET>",
    "secret dans un fichier YAML": "consumer_secret: {{ secret }}",
}

NOT_SECRETS = [
    "api_key = xxxxxxxxxxxxxxxxxxxx",
    "Envoyez l'en-tête X-Target-Environment: sandbox",
    "X-Reference-Id: 0f8fad5b-d9cb-469f-a165-70867728950e",
    "Le jeton expire au bout de 3600 secondes.",
    # Du code qui manipule un secret sans le contenir :
    "password = base64.b64decode(credentials).decode()",
    "api_key: str = Field(min_length=12)",
    "DATABASE_URL=postgresql://utilisateur:motdepasse@hote:5432/gotcha",
    # Des références à une variable, pas sa valeur :
    "API_KEY=$MY_LONG_ENV_VARIABLE_NAME",
    "API_KEY=$(get_secret_from_vault)",
    "MPESA_CONSUMER_SECRET=$MPESA_CONSUMER_SECRET",
    "CONSUMER_KEY=os.environ.get('CONSUMER_KEY')",
    'consumer_secret = "YOUR_CONSUMER_SECRET_HERE"',
    # La passkey du bac à sable Daraja est la même pour tous et publiée par Safaricom.
    "passkey: " + "bfb279f9aa9bdbcf158e97dd71a467cd" + "2e0c893059b10f78e6b72ada1ed2c919",
]

# Formes vues dans de vraies intégrations, qui doivent toutes être refusées.
REAL_WORLD_LEAKS = [
    "Mon api_key=" + FAKE,
    "mon password: " + FAKE,
    "api_key: " + FAKE + " # prod",
    "- password: " + FAKE,
    'password = "' + FAKE + '!x"',
    "PASSWD=" + FAKE,
    'curl -d "client_id=a&client_secret=' + FAKE + '"',
    "docker run -e MPESA_CONSUMER_SECRET=" + FAKE + " image",
    'MPESA_API_KEY="' + FAKE + '"',
    "export MOMO_SUBSCRIPTION_KEY=" + HEX_32,
    "Authorization: Basic " + "QWxhZGRpbjpvcGVuIHNlc2FtZQ==",
    'curl -H "Ocp-Apim-Subscription-Key: ' + HEX_32 + '"',
    "consumer_key=" + "aB3dE6gH9jK2mN5pQ8sT" * 2,
    "wave_sn_WHS_" + "x4m6g8rj" * 6,
    "mpesa_consumer_secret = '" + FAKE + "'",
]


@pytest.mark.parametrize(("kind", "text"), list(SECRETS.items()))
def test_each_rule_detects_its_secret(kind: str, text: str) -> None:
    findings = scan_text(f"Voici mon code : {text} fin.")
    assert kind in {f.kind for f in findings}


@pytest.mark.parametrize(("kind", "text"), list(LOOKALIKES.items()))
def test_each_rule_ignores_its_lookalike(kind: str, text: str) -> None:
    assert kind not in {f.kind for f in scan_text(text)}


def test_every_rule_has_a_secret_and_a_lookalike() -> None:
    kinds = {kind for kind, _ in RULES}
    assert set(SECRETS) == kinds
    assert set(LOOKALIKES) == kinds


@pytest.mark.parametrize("text", NOT_SECRETS + list(LOOKALIKES.values()))
def test_placeholders_code_and_normal_text_are_not_secrets(text: str) -> None:
    assert scan_text(text) == []


@pytest.mark.parametrize("text", REAL_WORLD_LEAKS)
def test_real_world_leaks_are_detected(text: str) -> None:
    assert scan_text(text) != []


def test_finding_starts_on_the_line_of_the_secret() -> None:
    text = "A=1\n\n\nCONSUMER_SECRET=" + FAKE + "\n"
    finding = scan_text(text)[0]
    assert text.count("\n", 0, finding.start) == 3


@pytest.mark.parametrize(
    "text",
    ["\n" * 100_000, " " * 100_000, "API_KEY" * 15_000, "password " * 12_000, "a=" * 50_000],
)
def test_scan_stays_fast_on_hostile_text(text: str) -> None:
    started = time.perf_counter()
    scan_text(text)
    assert time.perf_counter() - started < 0.5


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
