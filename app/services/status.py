"""Calcul de l'état d'un service (normal, dégradé, en panne) à partir des pannes connues.

Responsable : Khalifa. Fonctions pures, sans entrée/sortie, donc faciles à tester.
Les règles sont documentées dans app/services/README.md.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta

from app.domain.models import Incident, IncidentSource, ServiceStatus, Status

# Un signalement non confirmé (communauté ou agent) cesse de compter au bout de 6 heures.
REPORT_TTL = timedelta(hours=6)
# Autant de personnes différentes en si peu de temps : le service est considéré en panne.
CONFIRMING_REPORTERS = 3
CONFIRMATION_WINDOW = timedelta(hours=1)

_RANK = {Status.NORMAL: 0, Status.UNKNOWN: 0, Status.DEGRADED: 1, Status.DOWN: 2}


def _is_report(incident: Incident) -> bool:
    return incident.source in (IncidentSource.COMMUNITY, IncidentSource.AGENT)


def counts_now(incident: Incident, now: datetime) -> bool:
    """La panne pèse-t-elle encore sur l'état du service ?"""
    if not incident.is_active:
        return False
    return not (_is_report(incident) and now - incident.started_at > REPORT_TTL)


def confirmed_by_several(incidents: Iterable[Incident], now: datetime) -> bool:
    """Assez de personnes différentes ont-elles signalé la panne récemment ?

    Une personne compte une fois, quel que soit le nombre de ses signalements, et tous
    les signalements anonymes comptent ensemble pour une seule personne : personne ne
    peut faire passer un service en panne à lui seul.
    """
    reporters = {
        (i.reported_by or "").strip().casefold()
        for i in incidents
        if _is_report(i) and now - i.started_at <= CONFIRMATION_WINDOW
    }
    return len(reporters) >= CONFIRMING_REPORTERS


def concerns(
    incident: Incident, service_slug: str, country: str | None, *, is_payment: bool
) -> bool:
    """La panne concerne-t-elle ce service dans ce pays ?

    Une panne sans service concerne tous les services de paiement du pays.
    Une panne sans pays, ou une fiche sans pays, s'appliquent partout.
    """
    if incident.service_slug is None:
        service_ok = is_payment
    else:
        service_ok = incident.service_slug == service_slug
    country_ok = country is None or incident.country is None or incident.country == country
    return service_ok and country_ok


def compute_status(
    service_slug: str,
    country: str | None,
    incidents: Iterable[Incident],
    now: datetime,
    *,
    is_payment: bool = True,
) -> ServiceStatus:
    active = [
        i
        for i in incidents
        if counts_now(i, now) and concerns(i, service_slug, country, is_payment=is_payment)
    ]
    if not active:
        return ServiceStatus(
            service_slug=service_slug, country=country, status=Status.NORMAL, checked_at=now
        )
    worst = max(active, key=lambda i: _RANK[i.status]).status
    if confirmed_by_several(active, now):
        worst = Status.DOWN
    active.sort(key=lambda i: i.started_at, reverse=True)
    return ServiceStatus(
        service_slug=service_slug,
        country=country,
        status=worst,
        since=min(i.started_at for i in active),
        active_incidents=active,
        checked_at=now,
    )
