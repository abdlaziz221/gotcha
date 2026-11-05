"""Libellés affichés pour les valeurs du modèle (un seul endroit pour les textes)."""

from __future__ import annotations

from app.domain.models import (
    ConfidenceLevel,
    ContributionKind,
    Environment,
    IncidentSource,
    SearchHitKind,
    ServiceKind,
    Severity,
    Status,
    UsageEvent,
)

STATUS_LABELS = {
    Status.NORMAL: "Aucune panne signalée",
    Status.DEGRADED: "Dégradé",
    Status.DOWN: "En panne",
    Status.UNKNOWN: "État inconnu",
}

SEVERITY_LABELS = {
    Severity.BLOCKING: "Bloquant",
    Severity.MAJOR: "Important",
    Severity.MINOR: "Mineur",
}

ENVIRONMENT_LABELS = {
    Environment.SANDBOX: "Bac à sable",
    Environment.PRODUCTION: "Production",
}

SERVICE_KIND_LABELS = {
    ServiceKind.PAYMENT: "Paiement",
    ServiceKind.HOSTING: "Hébergement",
}

CONTRIBUTION_KIND_LABELS = {
    ContributionKind.GOTCHA: "Un nouveau piège",
    ContributionKind.STEP: "Une étape à ajouter ou corriger",
    ContributionKind.CORRECTION: "Une information fausse ou dépassée",
}

INCIDENT_SOURCE_LABELS = {
    IncidentSource.FLUTTERWAVE: "Flux d'incidents Flutterwave",
    IncidentSource.COMMUNITY: "Signalé par un dev",
    IncidentSource.AGENT: "Signalé par un agent IA",
}

SEARCH_HIT_LABELS = {
    SearchHitKind.FICHE: "Fiche",
    SearchHitKind.GOTCHA: "Piège",
    SearchHitKind.ERROR_CODE: "Code d'erreur",
}

# Messages affichés après une redirection (?ok=<clé>). Seules ces clés sont acceptées.
FLASH_MESSAGES = {
    "confirmation": "Merci ! Votre confirmation est enregistrée.",
    "signalement": "Merci, la panne est signalée : elle apparaît sur la fiche concernée.",
    "relecture": "Contribution relue.",
}

_MONTHS = [
    "janv.",
    "févr.",
    "mars",
    "avr.",
    "mai",
    "juin",
    "juil.",
    "août",
    "sept.",
    "oct.",
    "nov.",
    "déc.",
]


def date_fr(value: object) -> str:
    """28 oct. 2026"""
    day = getattr(value, "day", None)
    if day is None:
        return ""
    return f"{day} {_MONTHS[value.month - 1]} {value.year}"  # type: ignore[attr-defined]


def datetime_fr(value: object) -> str:
    """28 oct. 2026 à 14 h 05 (heure de Dakar, GMT)"""
    hour = getattr(value, "hour", None)
    if hour is None:
        return date_fr(value)
    return f"{date_fr(value)} à {hour} h {value.minute:02d}"  # type: ignore[attr-defined]


CONFIDENCE_LABELS = {
    ConfidenceLevel.SOURCED: "Sourcé",
    ConfidenceLevel.REPRODUCED: "Reproduit",
    ConfidenceLevel.PRODUCTION: "Confirmé en production",
}

USAGE_LABELS = {
    UsageEvent.READ_FICHE: "Fiches consultées",
    UsageEvent.SEARCH_HIT: "Recherches avec résultat",
    UsageEvent.SEARCH_MISS: "Recherches sans résultat",
    UsageEvent.READ_STATUS: "États de service consultés",
    UsageEvent.REPORT_OUTAGE: "Pannes signalées",
    UsageEvent.PROPOSE: "Contributions reçues",
    UsageEvent.CONFIRM: "Confirmations reçues",
}
