"""Détection des clés et jetons dans les contributions. Responsable : Khalifa.

Règles maison (expressions régulières) : detect-secrets est exclu, car il entraîne
certifi, sous licence MPL. Chaque règle doit avoir ses tests dans
tests/unit/test_security.py, avec un vrai format de clé (fictive) et un faux positif
à éviter. Ne jamais journaliser le secret trouvé.

Ce texte vient du public : pas de « \\s* » en début de motif, qui se rejoue sur chaque
ligne vide et bloque le serveur. On borne les répétitions et on reste sur la ligne.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Une valeur de substitution (xxxx, <VOTRE_CLE>, {{token}}, $VARIABLE, ****, your_key)
# n'est pas un secret.
_NOT_PLACEHOLDER = (
    r"(?![xX*]{6,}|<|\{|\$"
    r"|(?i:(?:your|votre|my|mon|ma)[_-]|example|exemple|change[_-]?me|placeholder))"
)
_SENSITIVE_FIELDS = (
    r"(?:api[_-]?key|secret[_-]?key|client[_-]?secret|consumer[_-]?(?:key|secret)"
    r"|subscription[_-]?key|pass[_-]?key|password|passwd|access[_-]?token)"
)
_FIELD_START = r"(?<![A-Za-z0-9])"
_ASSIGN = r"[\"']?[ \t]*[:=][ \t]*"
# Passkey du bac à sable Daraja : la même pour tous, publiée par Safaricom.
_PUBLIC_VALUES = ("bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919",)


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
    # Formats publiés sur docs.wave.com (clé d'API, signature des requêtes, webhooks).
    (
        "clé d'API Wave",
        re.compile(
            r"\bwave_[a-z]{2}_(?:prod|dev|test)_" + _NOT_PLACEHOLDER + r"[A-Za-z0-9_-]{16,}"
        ),
    ),
    (
        "secret de signature Wave",
        re.compile(r"\bwave_[a-z]{2}_(?:AKS|WHS)_" + _NOT_PLACEHOLDER + r"[A-Za-z0-9]{16,}"),
    ),
    # Longueur à confirmer sur un vrai compte (K1) : 32 caractères hexadécimaux, le format
    # par défaut d'Azure API Management, que MTN utilise.
    (
        "clé d'abonnement MTN MoMo",
        re.compile(r"(?i)ocp-apim-subscription-key[\"']?\s*[:=]\s*[\"']?[0-9a-f]{32}\b"),
    ),
    # Plus courte que les autres clés, d'où un seuil bas, compensé par l'exigence d'un
    # chiffre. Longueur à confirmer sur un vrai compte (K1).
    (
        "clé marchand Orange Money",
        re.compile(
            r"(?i)" + _FIELD_START + r"merchant[_-]?key" + _ASSIGN + r"[\"']?"
            + _NOT_PLACEHOLDER
            + r"(?=[A-Za-z]*[0-9])[A-Za-z0-9]{8,}\b"
        ),
    ),
    (
        "passkey Daraja",
        re.compile(
            r"(?i)" + _FIELD_START + r"pass[_-]?key" + _ASSIGN + r"[\"']?[0-9a-f]{64}\b"
        ),
    ),
    (
        "en-tête Authorization",
        re.compile(
            r"(?i)\bauthorization[\"']?\s*[:=]\s*[\"']?(?:bearer|basic)\s+"
            + _NOT_PLACEHOLDER
            # Une valeur tronquée (« wave_sn_prod_YhUNb9d...i4bA6 ») a déjà été masquée.
            + r"(?!\S*\.\.\.)[A-Za-z0-9+/=._-]{16,}"
        ),
    ),
    # Affectations. Une expression comme « password = base64.b64decode(...) » ou
    # « password = settings.reviewer_password » n'est pas un secret.
    (
        "secret dans une affectation",
        re.compile(
            r"(?i)" + _FIELD_START + _SENSITIVE_FIELDS + r"\b" + _ASSIGN + r"[\"']"
            + _NOT_PLACEHOLDER
            + r"[^\s\"'`]{16,}[\"']"
        ),
    ),
    # Sans guillemets, en plein texte : URL, curl, phrase. Un chiffre et une lettre, sans
    # point ni souligné : la valeur ne doit pas pouvoir être un nom de variable.
    (
        "secret sans guillemets",
        re.compile(
            r"(?i)" + _FIELD_START + _SENSITIVE_FIELDS + r"\b" + _ASSIGN
            + _NOT_PLACEHOLDER
            + r"(?=[A-Za-z/+=-]*[0-9])(?=[0-9/+=-]*[A-Za-z])[A-Za-z0-9/+=-]{16,}(?=$|[\s&\"',;#)])"
        ),
    ),
    (
        "secret dans un fichier .env",
        re.compile(
            r"(?<![A-Za-z0-9_])[A-Z0-9_]{0,64}"
            r"(?:API_KEY|SECRET|PASSKEY|PASSWORD|PASSWD|ACCESS_TOKEN|CONSUMER_KEY"
            r"|SUBSCRIPTION_KEY)[A-Z0-9_]{0,64}=[\"']?"
            + _NOT_PLACEHOLDER
            + r"[^\s\"'#()]{16,}"
        ),
    ),
    (
        "secret dans un fichier YAML",
        re.compile(
            r"(?im)^[ \t]*(?:-[ \t]+)?" + _SENSITIVE_FIELDS + r"[ \t]*:[ \t]*"
            + _NOT_PLACEHOLDER
            + r"[A-Za-z0-9/+_.=-]{16,}[ \t]*(?:#.*)?$"
        ),
    ),
]  # fmt: skip


def scan_text(text: str) -> list[SecretFinding]:
    """Liste les secrets probables du texte, dans l'ordre d'apparition."""
    findings = [
        SecretFinding(kind=kind, start=m.start(), end=m.end())
        for kind, pattern in RULES
        for m in pattern.finditer(text)
        if not any(public in m.group() for public in _PUBLIC_VALUES)
    ]
    return sorted(findings, key=lambda f: f.start)
