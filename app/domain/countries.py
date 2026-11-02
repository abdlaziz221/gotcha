"""Pays suivis (codes ISO 3166-1 alpha-2) et leurs noms en français."""

from __future__ import annotations

COUNTRY_NAMES: dict[str, str] = {
    "BF": "Burkina Faso",
    "BJ": "Bénin",
    "CI": "Côte d'Ivoire",
    "CM": "Cameroun",
    "GH": "Ghana",
    "KE": "Kenya",
    "ML": "Mali",
    "NE": "Niger",
    "NG": "Nigeria",
    "RW": "Rwanda",
    "SN": "Sénégal",
    "TG": "Togo",
    "TZ": "Tanzanie",
    "UG": "Ouganda",
    "ZA": "Afrique du Sud",
    "ZM": "Zambie",
}


def country_name(code: str | None) -> str:
    """Nom affichable d'un pays ; « Tous les pays » si le code est vide."""
    if not code:
        return "Tous les pays"
    return COUNTRY_NAMES.get(code.upper(), code.upper())
