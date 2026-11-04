"""Détection des clés et jetons dans les contributions. Responsable : Khalifa.

Règles maison (expressions régulières) : detect-secrets est exclu, car il entraîne
certifi, sous licence MPL. Chaque règle doit avoir ses tests dans
tests/unit/test_secrets.py, avec un vrai format de clé (fictive) et un faux positif
à éviter. Ne jamais journaliser le secret trouvé.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Une valeur de substitution (xxxx, <VOTRE_CLE>, {{token}}, ****) n'est pas un secret.
_NOT_PLACEHOLDER = r"(?![xX*]{6,}|<|\{|\$\{)"
_SENSITIVE_FIELDS = (
    r"(?:api[_-]?key|secret[_-]?key|client[_-]?secret|consumer[_-]?(?:key|secret)"
    r"|pass[_-]?key|password|passwd|access[_-]?token)"
)


@dataclass(frozen=True)
class SecretFinding:
    kind: str  # libellé affichable, ex. « clé secrète Flutterwave »
    start: int
    end: int


RULES: list[tuple[str, re.Pattern[str]]] = [
    ("clé privée", re.compile(r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----")),
    (
        "jeton JWT",
        re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
    ),
    ("clé AWS", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("jeton GitHub", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("clé secrète Flutterwave", re.compile(r"\bFLWSECK(?:_TEST)?-[A-Za-z0-9]{20,}(?:-X)?")),
    ("clé secrète Paystack ou Stripe", re.compile(r"\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{16,}")),
    # Format à confirmer sur un vrai compte Wave Business (tâche K7).
    ("clé d'API Wave", re.compile(r"\bwave_[a-z]{2}_(?:prod|dev|test)_[A-Za-z0-9_-]{16,}")),
    (
        "clé d'abonnement MTN MoMo",
        re.compile(r"(?i)ocp-apim-subscription-key[\"']?\s*[:=]\s*[\"']?[0-9a-f]{32}\b"),
    ),
    (
        "en-tête Authorization",
        re.compile(
            r"(?i)\bauthorization[\"']?\s*[:=]\s*[\"']?(?:bearer|basic)\s+"
            + _NOT_PLACEHOLDER
            + r"[A-Za-z0-9+/=._-]{16,}"
        ),
    ),
    # Affectations : la valeur doit être une chaîne entre guillemets (code), une ligne
    # NOM=valeur (fichier .env) ou une valeur seule sur sa ligne (YAML). Une expression
    # comme « password = base64.b64decode(...) » n'est pas un secret.
    (
        "secret dans une affectation",
        re.compile(
            r"(?i)\b" + _SENSITIVE_FIELDS + r"\b[\"']?\s*[:=]\s*[\"']"
            + _NOT_PLACEHOLDER
            + r"[A-Za-z0-9/+_.=-]{16,}[\"']"
        ),
    ),
    (
        "secret dans un fichier .env",
        re.compile(
            r"(?m)^\s*(?:export\s+)?[A-Z0-9_]*"
            r"(?:API_KEY|SECRET|PASSKEY|PASSWORD|ACCESS_TOKEN|CONSUMER_KEY)[A-Z0-9_]*="
            + _NOT_PLACEHOLDER
            + r"[^\s\"'#]{16,}"
        ),
    ),
    (
        "secret dans un fichier YAML",
        re.compile(
            r"(?im)^\s*" + _SENSITIVE_FIELDS + r"\s*:\s*"
            + _NOT_PLACEHOLDER
            + r"[A-Za-z0-9/+_.=-]{16,}\s*$"
        ),
    ),
]  # fmt: skip


def scan_text(text: str) -> list[SecretFinding]:
    """Liste les secrets probables du texte, dans l'ordre d'apparition."""
    findings = [
        SecretFinding(kind=kind, start=m.start(), end=m.end())
        for kind, pattern in RULES
        for m in pattern.finditer(text)
    ]
    return sorted(findings, key=lambda f: f.start)
