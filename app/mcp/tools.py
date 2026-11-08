"""Logique des outils MCP, sans dépendance au SDK : testable avec de simples appels.

Responsable : Khalifa. server.py ne fait qu'enregistrer ces fonctions auprès du SDK.
"""

from __future__ import annotations

from pydantic import ValidationError

from app.container import Services
from app.domain.errors import InvalidInputError
from app.domain.models import (
    ContributionInput,
    ContributionKind,
    Fiche,
    Gotcha,
    IncidentSource,
    OutageReport,
    Publication,
    ServiceStatus,
    Status,
    TargetKind,
)
from app.domain.text import strip_term_links
from app.mcp.schemas import (
    ConfirmationOut,
    EnvDifferenceOut,
    ErrorCodeOut,
    FicheOut,
    FicheRef,
    GotchaOut,
    IncidentOut,
    OutageReportOut,
    ProposalOut,
    SearchResultOut,
    ServiceOut,
    StatusOut,
    StepOut,
)

_ADVICE = {
    Status.NORMAL: "No known outage. Proceed, and still handle payment failures and retries.",
    Status.DEGRADED: (
        "Service degraded: warn the user, expect failures or delays, offer a fallback "
        "payment method and retry later."
    ),
    Status.DOWN: "Service down: do not rely on it now; tell the user and offer a fallback.",
    Status.UNKNOWN: "Status unknown: handle failures defensively.",
}


def _status_out(status: ServiceStatus) -> StatusOut:
    return StatusOut(
        service=status.service_slug,
        country=status.country,
        status=status.status.value,
        since=status.since,
        checked_at=status.checked_at,
        incidents=[
            IncidentOut(
                title=i.title,
                status=i.status.value,
                country=i.country,
                started_at=i.started_at,
                source=i.source.value,
                url=str(i.url) if i.url else None,
            )
            for i in status.active_incidents
        ],
        advice=_ADVICE[status.status],
    )


def _gotcha_out(services: Services, fiche: Fiche, gotcha: Gotcha) -> GotchaOut:
    return GotchaOut(
        id=gotcha.id,
        title=gotcha.title,
        severity=gotcha.severity.value,
        environments=[e.value for e in gotcha.environments],
        symptom=strip_term_links(gotcha.symptom_md),
        cause=strip_term_links(gotcha.cause_md),
        fix=strip_term_links(gotcha.fix_md),
        failed_attempts=(
            strip_term_links(gotcha.failed_attempts_md) if gotcha.failed_attempts_md else None
        ),
        proof=strip_term_links(gotcha.proof_md) if gotcha.proof_md else None,
        confidence=gotcha.confidence.value,
        error_codes=gotcha.error_codes,
        api_version=gotcha.api_version,
        sources=[str(s.url) if s.url else f"{s.title} ({s.author})" for s in gotcha.sources],
        last_confirmed_on=gotcha.last_confirmed_on,
        confirmations=gotcha.confirmations,
        verified=gotcha.publication is Publication.PUBLISHED,
        needs_review=services.fiches.needs_review(gotcha),
        url=f"{services.settings.site_url}/fiches/{fiche.slug}#{gotcha.anchor}",
    )


async def list_services(services: Services) -> list[ServiceOut]:
    by_service: dict[str, ServiceOut] = {}
    for fiche in await services.fiches.list():
        entry = by_service.setdefault(
            fiche.service.slug,
            ServiceOut(
                slug=fiche.service.slug,
                name=fiche.service.name,
                kind=fiche.service.kind.value,
                fiches=[],
            ),
        )
        entry.fiches.append(FicheRef(slug=fiche.slug, title=fiche.title, country=fiche.country))
    return sorted(by_service.values(), key=lambda s: s.name.lower())


async def get_fiche(services: Services, service: str, country: str | None = None) -> FicheOut:
    await services.incidents.refresh_if_stale()
    fiche = await services.fiches.find(service, country)
    status = await services.incidents.status_of(fiche.service, country or fiche.country)
    unverified = [g for g in fiche.gotchas if g.publication is not Publication.PUBLISHED]
    warning = (
        f"{len(unverified)} gotcha(s) not yet verified by a human (draft): double-check them."
        if unverified
        else None
    )
    return FicheOut(
        slug=fiche.slug,
        url=f"{services.settings.site_url}/fiches/{fiche.slug}",
        title=fiche.title,
        service=fiche.service.slug,
        country=fiche.country,
        summary=fiche.summary,
        api_version=fiche.api_version,
        prerequisites=fiche.prerequisites,
        steps=[
            StepOut(order=s.order, title=s.title, body=strip_term_links(s.body_md))
            for s in fiche.steps
        ],
        gotchas=[_gotcha_out(services, fiche, g) for g in fiche.gotchas],
        sandbox_vs_production=[EnvDifferenceOut(**d.model_dump()) for d in fiche.differences],
        error_codes=[ErrorCodeOut(**e.model_dump()) for e in fiche.error_codes],
        status=_status_out(status),
        last_confirmed_on=fiche.last_confirmed_on,
        needs_review=services.fiches.needs_review(fiche),
        warning=warning,
    )


async def search_gotchas(
    services: Services,
    query: str,
    service: str | None = None,
    country: str | None = None,
) -> list[SearchResultOut]:
    hits = await services.fiches.search(query, service=service, country=country, limit=10)
    base = services.settings.site_url
    return [
        SearchResultOut(
            kind=h.kind.value,
            fiche_slug=h.fiche_slug,
            title=h.title,
            snippet=h.snippet,
            url=f"{base}/fiches/{h.fiche_slug}" + (f"#{h.anchor}" if h.anchor else ""),
        )
        for h in hits
    ]


async def get_service_status(
    services: Services, service: str, country: str | None = None
) -> StatusOut:
    await services.incidents.refresh_if_stale()
    fiche = await services.fiches.find(service, country)
    return _status_out(await services.incidents.status_of(fiche.service, country or fiche.country))


async def report_outage(
    services: Services,
    service: str,
    description: str,
    country: str | None = None,
    *,
    reported_by: str = "agent",
) -> OutageReportOut:
    incident = await services.incidents.report(
        OutageReport(
            service_slug=service,
            country=country.upper() if country else None,
            description=description,
            reported_by=reported_by,
            source=IncidentSource.AGENT,
        )
    )
    return OutageReportOut(
        incident_id=incident.id,
        status=incident.status.value,
        message="Thanks: the outage is recorded and shown on the fiche for a few hours.",
    )


def _proposal_body(
    symptom: str, cause: str, fix: str, failed_attempts: str | None, proof: str | None
) -> str:
    """Même découpage qu'un fichier de pièges : le relecteur n'a plus qu'à le reprendre."""
    sections = [("Symptôme", symptom), ("Cause", cause), ("Solution", fix)]
    if failed_attempts:
        sections.append(("Pistes qui ont échoué", failed_attempts))
    if proof:
        sections.append(("Preuve", proof))
    return "\n\n".join(f"## {title}\n\n{text.strip()}" for title, text in sections)


async def propose_gotcha(
    services: Services,
    *,
    subject: str,
    service: str,
    title: str,
    symptom: str,
    cause: str,
    fix: str,
    developer_approved: bool,
    failed_attempts: str | None = None,
    proof: str | None = None,
    country: str | None = None,
    api_version: str | None = None,
    source_url: str | None = None,
) -> ProposalOut:
    if not developer_approved:
        raise InvalidInputError(
            "Show this exact draft to your developer first, then call again with "
            "developer_approved=true. Never include private code, keys, customer data or prompts."
        )
    fiche = await services.fiches.find(service, country)
    pseudo = await services.oauth.account_pseudo(subject) or "agent"
    try:
        data = ContributionInput(
            kind=ContributionKind.GOTCHA,
            fiche_slug=fiche.slug,
            title=title,
            body_md=_proposal_body(symptom, cause, fix, failed_attempts, proof),
            source_url=source_url,  # type: ignore[arg-type]  # vérifiée par pydantic
            api_version=api_version,
            pseudo=pseudo[:40],
            account_id=subject,
        )
    except ValidationError as exc:
        fields = ", ".join(str(error["loc"][0]) for error in exc.errors())
        raise InvalidInputError(f"Invalid proposal: check {fields}.") from exc
    contribution = await services.contributions.submit(data)
    return ProposalOut(
        contribution_id=contribution.id,
        status=contribution.status.value,
        message="Thanks: a human reviews this draft before anything is published.",
    )


async def confirm_gotcha(
    services: Services,
    *,
    subject: str,
    gotcha_id: str,
    still_works: bool,
    proof: str,
    api_version: str | None = None,
) -> ConfirmationOut:
    pseudo = await services.oauth.account_pseudo(subject)
    await services.contributions.confirm(
        TargetKind.GOTCHA,
        gotcha_id,
        still_works=still_works,
        api_version=api_version,
        pseudo=pseudo[:40] if pseudo else None,
        account_id=subject,
        proof=proof,
    )
    return ConfirmationOut(
        gotcha_id=gotcha_id,
        still_works=still_works,
        message="Thanks: your confirmation and its proof are recorded.",
    )
