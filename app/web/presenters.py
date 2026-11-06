"""Traduction des objets du domaine en contextes de pages (app/web/viewmodels.py)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from datetime import datetime
from typing import Any

from markupsafe import Markup

from app.domain.countries import country_name
from app.domain.models import (
    Confirmation,
    Contribution,
    Fiche,
    GlossaryTerm,
    Gotcha,
    Incident,
    Publication,
    ServiceStatus,
    Source,
)
from app.domain.text import first_sentence
from app.services.status import counts_now
from app.web.labels import (
    CONFIDENCE_LABELS,
    CONTRIBUTION_KIND_LABELS,
    ENVIRONMENT_LABELS,
    INCIDENT_SOURCE_LABELS,
    SERVICE_KIND_LABELS,
    SEVERITY_LABELS,
    STATUS_LABELS,
)
from app.web.markdown import render_markdown
from app.web.viewmodels import (
    ConfirmationView,
    ContributionView,
    FicheCard,
    GotchaView,
    IncidentView,
    SourceView,
    StatusView,
    StepView,
)

UNATTRIBUTED_SERVICE = "Mobile Money (tous opérateurs)"


def fiche_url(slug: str) -> str:
    return f"/fiches/{slug}"


def step_url(slug: str, order: int) -> str:
    return f"/fiches/{slug}?mode=pas-a-pas&etape={order}"


def service_names(fiches: list[Fiche]) -> dict[str, str]:
    return {f.service.slug: f.service.name for f in fiches}


def source_view(source: Source) -> SourceView:
    return SourceView(
        title=source.title,
        url=str(source.url) if source.url else None,
        author=source.author,
        published_on=source.published_on,
        accessed_on=source.accessed_on,
    )


def incident_view(incident: Incident, names: Mapping[str, str], now: datetime) -> IncidentView:
    if incident.service_slug is None:
        service = UNATTRIBUTED_SERVICE
    else:
        service = names.get(incident.service_slug, incident.service_slug)
    return IncidentView(
        id=incident.id,
        title=incident.title,
        description=incident.description,
        service_name=service,
        country_name=country_name(incident.country),
        status=incident.status,
        status_label=STATUS_LABELS[incident.status],
        source_label=INCIDENT_SOURCE_LABELS[incident.source],
        started_at=incident.started_at,
        resolved_at=incident.resolved_at,
        url=str(incident.url) if incident.url else None,
        is_active=counts_now(incident, now),
    )


def status_view(status: ServiceStatus, names: Mapping[str, str]) -> StatusView:
    return StatusView(
        status=status.status,
        label=STATUS_LABELS[status.status],
        since=status.since,
        incidents=[incident_view(i, names, status.checked_at) for i in status.active_incidents],
    )


def fiche_card(
    fiche: Fiche, status: ServiceStatus, names: Mapping[str, str], *, needs_review: bool
) -> FicheCard:
    return FicheCard(
        slug=fiche.slug,
        url=fiche_url(fiche.slug),
        title=fiche.title,
        service_name=fiche.service.name,
        kind=fiche.service.kind,
        kind_label=SERVICE_KIND_LABELS[fiche.service.kind],
        country_name=country_name(fiche.country),
        summary=fiche.summary,
        gotcha_count=len(fiche.gotchas),
        status=status_view(status, names),
        needs_review=needs_review,
        is_draft=fiche.publication is not Publication.PUBLISHED,
        last_confirmed_on=fiche.last_confirmed_on,
    )


def step_views(fiche: Fiche, glossary: Mapping[str, GlossaryTerm]) -> list[StepView]:
    return [
        StepView(
            order=s.order,
            title=s.title,
            body_html=render_markdown(s.body_md, glossary),
            url=step_url(fiche.slug, s.order),
        )
        for s in fiche.steps
    ]


def gotcha_view(
    gotcha: Gotcha, glossary: Mapping[str, GlossaryTerm], *, needs_review: bool
) -> GotchaView:
    return GotchaView(
        id=gotcha.id,
        anchor=gotcha.anchor,
        title=gotcha.title,
        severity=gotcha.severity,
        severity_label=SEVERITY_LABELS[gotcha.severity],
        environment_labels=[ENVIRONMENT_LABELS[e] for e in gotcha.environments],
        api_version=gotcha.api_version,
        error_codes=gotcha.error_codes,
        symptom_html=render_markdown(gotcha.symptom_md, glossary),
        cause_html=render_markdown(gotcha.cause_md, glossary),
        fix_html=render_markdown(gotcha.fix_md, glossary),
        failed_attempts_html=(
            render_markdown(gotcha.failed_attempts_md, glossary)
            if gotcha.failed_attempts_md
            else None
        ),
        proof_html=render_markdown(gotcha.proof_md, glossary) if gotcha.proof_md else None,
        confidence=gotcha.confidence,
        # Un brouillon n'a pas encore été recoupé par un relecteur : son niveau reste à confirmer.
        confidence_label=CONFIDENCE_LABELS[gotcha.confidence]
        + ("" if gotcha.publication is Publication.PUBLISHED else ", à confirmer à la relecture"),
        sources=[source_view(s) for s in gotcha.sources],
        last_confirmed_on=gotcha.last_confirmed_on,
        confirmations=gotcha.confirmations,
        needs_review=needs_review,
        is_draft=gotcha.publication is not Publication.PUBLISHED,
        verified_by=gotcha.verified_by,
        **_audio_fields(gotcha, glossary),
    )


def _audio_fields(gotcha: Gotcha, glossary: Mapping[str, GlossaryTerm]) -> dict[str, Any]:
    audio = gotcha.audio
    if audio is None:
        return {}
    credit = f"Enregistré par {audio.recorded_by}"
    credit += f", relu par {audio.reviewed_by}" if audio.reviewed_by else ", pas encore relu"
    fiche, name = gotcha.id.split(".", 1)
    return {
        "audio_url": f"/fiches/{fiche}/audio/{name}",
        "audio_transcript_html": render_markdown(audio.transcript_md, glossary),
        "audio_credit": credit,
    }


def gotcha_preview(
    gotcha: Gotcha, glossary: Mapping[str, GlossaryTerm], *, needs_review: bool
) -> GotchaView:
    """Aperçu public : le symptôme, le début de la cause, le niveau et les sources.

    Le reste n'est pas caché par le gabarit : il n'est tout simplement pas envoyé.
    """
    view = gotcha_view(gotcha, glossary, needs_review=needs_review)
    return replace(
        view,
        cause_html=Markup("<p>{}</p>").format(first_sentence(gotcha.cause_md)),
        fix_html=Markup(""),
        failed_attempts_html=None,
        proof_html=None,
        audio_url=None,  # l'explication parle de la solution : réservée, comme elle
        audio_transcript_html=None,
        audio_credit=None,
        locked=True,
    )


def confirmation_view(confirmation: Confirmation) -> ConfirmationView:
    return ConfirmationView(
        target_id=confirmation.target_id,
        still_works=confirmation.still_works,
        api_version=confirmation.api_version,
        pseudo=confirmation.pseudo,
        proof=confirmation.proof,
        created_at=confirmation.created_at,
    )


def contribution_view(
    contribution: Contribution, fiche_titles: Mapping[str, str]
) -> ContributionView:
    return ContributionView(
        id=contribution.id,
        kind_label=CONTRIBUTION_KIND_LABELS[contribution.kind],
        fiche_title=fiche_titles.get(contribution.fiche_slug, contribution.fiche_slug),
        fiche_url=fiche_url(contribution.fiche_slug),
        title=contribution.title,
        body_html=render_markdown(contribution.body_md),
        source_url=str(contribution.source_url) if contribution.source_url else None,
        api_version=contribution.api_version,
        pseudo=contribution.pseudo,
        created_at=contribution.created_at,
    )
