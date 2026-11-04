"""Réponses des outils MCP : CONTRAT avec les agents (voir docs/CONTRACTS.md, section 4).

Textes destinés aux agents, en anglais pour les champs techniques ; le contenu
des fiches reste en français. Ne jamais exposer l'e-mail d'un contributeur.
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class FicheRef(BaseModel):
    slug: str
    title: str
    country: str | None


class ServiceOut(BaseModel):
    slug: str
    name: str
    kind: str
    fiches: list[FicheRef]


class StepOut(BaseModel):
    order: int
    title: str
    body: str


class GotchaOut(BaseModel):
    id: str
    title: str
    severity: str
    environments: list[str]
    symptom: str
    cause: str
    fix: str
    failed_attempts: str | None
    proof: str | None
    confidence: str  # sourced, reproduced ou production
    error_codes: list[str]
    api_version: str | None
    sources: list[str]
    last_confirmed_on: date
    confirmations: int
    verified: bool
    needs_review: bool
    url: str


class IncidentOut(BaseModel):
    title: str
    status: str
    country: str | None
    started_at: datetime
    source: str
    url: str | None


class StatusOut(BaseModel):
    service: str
    country: str | None
    status: str
    since: datetime | None
    checked_at: datetime
    incidents: list[IncidentOut]
    advice: str


class EnvDifferenceOut(BaseModel):
    topic: str
    sandbox: str
    production: str


class ErrorCodeOut(BaseModel):
    code: str
    meaning: str
    action: str


class FicheOut(BaseModel):
    slug: str
    url: str
    title: str
    service: str
    country: str | None
    summary: str
    api_version: str | None
    prerequisites: list[str]
    steps: list[StepOut]
    gotchas: list[GotchaOut]
    sandbox_vs_production: list[EnvDifferenceOut]
    error_codes: list[ErrorCodeOut]
    status: StatusOut
    last_confirmed_on: date
    needs_review: bool
    warning: str | None


class SearchResultOut(BaseModel):
    kind: str
    fiche_slug: str
    title: str
    snippet: str
    url: str


class OutageReportOut(BaseModel):
    incident_id: str
    status: str
    message: str
