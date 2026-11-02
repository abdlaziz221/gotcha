"""Lecture des formulaires et messages d'erreur en français."""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import ValidationError
from starlette.datastructures import FormData

FIELD_ERRORS = {
    "kind": "Choisissez le type de contribution.",
    "fiche_slug": "Choisissez une fiche.",
    "title": "Le titre doit faire entre 5 et 160 caractères.",
    "body_md": "Le texte doit faire entre 20 et 10 000 caractères.",
    "source_url": "L'adresse de la source doit commencer par http:// ou https://.",
    "api_version": "La version de l'API fait 40 caractères au plus.",
    "pseudo": "Le pseudo doit faire entre 2 et 40 caractères.",
    "email": "Adresse e-mail invalide.",
    "description": "Décrivez la panne en 10 à 1 000 caractères.",
    "service_slug": "Choisissez un service.",
    "country": "Pays invalide.",
    "licence": "Acceptez la publication sous licence CC BY 4.0 pour envoyer.",
}


def form_values(form: FormData, fields: Iterable[str]) -> dict[str, str]:
    values = {}
    for name in fields:
        raw = form.get(name)
        values[name] = raw.strip() if isinstance(raw, str) else ""
    return values


def field_errors(exc: ValidationError) -> dict[str, str]:
    errors: dict[str, str] = {}
    for error in exc.errors():
        name = str(error["loc"][0]) if error["loc"] else "form"
        errors.setdefault(name, FIELD_ERRORS.get(name, "Valeur invalide."))
    return errors
