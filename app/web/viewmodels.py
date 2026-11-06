"""Contextes des pages : le CONTRAT entre les routes (Abdoul Aziz) et les gabarits (Loum).

Chaque gabarit de templates/pages/ reçoit :
- `page` : un objet d'une des classes ci-dessous (une classe par page) ;
- `csrf_token` : à recopier dans chaque formulaire POST ;
- `viewer` : qui regarde la page (voir Viewer) ;
- `site` : nom, slogan, mentions du pied de page ;
- `request` : la requête (pour request.url.path, par exemple).

Les champs *_html sont déjà nettoyés : on les affiche tels quels ({{ g.fix_html }}),
jamais avec |safe. Ajouter un champ : PR relue par Loum et Abdoul Aziz.
Renommer ou supprimer : accord des trois (voir docs/CONTRACTS.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal

from markupsafe import Markup

from app.domain.models import (
    ConfidenceLevel,
    EnvDifference,
    ErrorCode,
    GlossaryTerm,
    SearchHitKind,
    ServiceKind,
    Severity,
    Status,
)

# D21 : mémoire opérationnelle ; D22 : niveau de confiance affiché, rien de plus promis.
DEFAULT_DESCRIPTION = (
    "La mémoire opérationnelle du paiement mobile et du déploiement en Afrique : "
    "chaque piège cite ses sources et affiche son niveau de confiance."
)


# --- Briques communes --------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Viewer:
    """Le visiteur : `pseudo` s'il est connecté, et ce qu'il peut faire."""

    pseudo: str | None
    site_auth: bool  # la connexion est-elle proposée sur ce site ?
    can_write: bool  # peut-il envoyer un formulaire maintenant ?


@dataclass(frozen=True, slots=True)
class PageMeta:
    title: str  # contenu de <title> et du <h1> par défaut
    path: str = "/"
    description: str = DEFAULT_DESCRIPTION
    noindex: bool = False  # pages de formulaires, relecture, guide de style


@dataclass(frozen=True, slots=True)
class Flash:
    kind: Literal["success", "error", "info"]
    message: str


@dataclass(frozen=True, slots=True)
class Option:
    """Une option de <select>."""

    value: str
    label: str
    selected: bool = False


@dataclass(frozen=True, slots=True)
class FormState:
    """Valeurs saisies et erreurs, par nom de champ, pour réafficher un formulaire."""

    values: dict[str, str] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SourceView:
    title: str
    url: str | None
    author: str | None
    accessed_on: date
    published_on: date | None = None


@dataclass(frozen=True, slots=True)
class IncidentView:
    id: str
    title: str
    description: str | None
    service_name: str  # « Mobile Money (tous opérateurs) » si non attribuée
    country_name: str
    status: Status
    status_label: str
    source_label: str
    started_at: datetime
    resolved_at: datetime | None
    url: str | None
    is_active: bool  # compte encore dans l'état du service


@dataclass(frozen=True, slots=True)
class StatusView:
    status: Status  # normal | degraded | down | unknown : à utiliser comme classe CSS
    label: str
    since: datetime | None
    incidents: list[IncidentView] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class FicheCard:
    """Une fiche dans une liste (accueil, styleguide)."""

    slug: str
    url: str
    title: str
    service_name: str
    kind: ServiceKind
    kind_label: str
    country_name: str
    summary: str
    gotcha_count: int
    status: StatusView
    needs_review: bool
    is_draft: bool
    last_confirmed_on: date


@dataclass(frozen=True, slots=True)
class StepView:
    order: int
    title: str
    body_html: Markup
    url: str  # lien vers cette étape en mode pas à pas


@dataclass(frozen=True, slots=True)
class GotchaView:
    id: str
    anchor: str  # id HTML de la carte du piège
    title: str
    severity: Severity
    severity_label: str
    environment_labels: list[str]
    api_version: str | None
    error_codes: list[str]
    symptom_html: Markup
    cause_html: Markup
    fix_html: Markup
    failed_attempts_html: Markup | None
    proof_html: Markup | None
    confidence: ConfidenceLevel
    confidence_label: str
    sources: list[SourceView]
    last_confirmed_on: date
    confirmations: int
    needs_review: bool
    is_draft: bool
    locked: bool = False  # aperçu public : ni solution, ni pistes, ni preuve
    # Explication en wolof (D26) : adresse de la route protégée, jamais /static.
    audio_url: str | None = None
    audio_transcript_html: Markup | None = None
    audio_credit: str | None = None  # « Enregistré par X, relu par Y »
    verified_by: str | None = None  # relecteur affiché « Relu par » (L15) ; jamais d'auteur inventé


@dataclass(frozen=True, slots=True)
class StepMode:
    """Mode « pas à pas » : une étape à la fois, pour les débutants."""

    current: StepView
    index: int  # 1 pour la première étape
    total: int
    prev_url: str | None
    next_url: str | None
    exit_url: str


# --- Pages -------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HomePage:
    meta: PageMeta
    cards: list[FicheCard]
    active_incidents: list[IncidentView]
    gotcha_total: int
    flash: Flash | None = None


@dataclass(frozen=True, slots=True)
class SearchHitView:
    kind: SearchHitKind
    kind_label: str
    title: str
    snippet: str
    url: str


@dataclass(frozen=True, slots=True)
class SearchPage:
    meta: PageMeta
    query: str
    hits: list[SearchHitView]
    service_options: list[Option]
    country_options: list[Option]


@dataclass(frozen=True, slots=True)
class FichePage:
    meta: PageMeta
    slug: str
    title: str
    service_name: str
    service_docs_url: str | None
    kind: ServiceKind
    country_name: str
    summary: str
    api_version: str | None
    status: StatusView
    prerequisites: list[str]
    steps: list[StepView]
    gotchas: list[GotchaView]
    differences: list[EnvDifference]
    error_codes: list[ErrorCode]
    sources: list[SourceView]
    needs_review: bool
    is_draft: bool
    last_confirmed_on: date
    confirmations: int
    contribute_url: str
    report_url: str
    step_mode: StepMode | None = None  # renseigné si ?mode=pas-a-pas
    flash: Flash | None = None
    locked: bool = False  # aperçu public : étapes et solutions réservées aux membres
    login_url: str = ""


@dataclass(frozen=True, slots=True)
class ContributePage:
    meta: PageMeta
    form: FormState
    fiche_options: list[Option]
    kind_options: list[Option]


@dataclass(frozen=True, slots=True)
class MessagePage:
    """Page simple : remerciement, confirmation."""

    meta: PageMeta
    heading: str
    message: str
    back_url: str
    back_label: str


@dataclass(frozen=True, slots=True)
class ToolConsentPage:
    """Écran de consentement avant de connecter un outil MCP (app/web/routes/auth.py)."""

    meta: PageMeta
    client_name: str
    redirect_uri: str  # affichée telle quelle : le développeur voit où partira le code
    request_id: str


@dataclass(frozen=True, slots=True)
class IncidentsPage:
    meta: PageMeta
    active: list[IncidentView]
    recent: list[IncidentView]
    flash: Flash | None = None


@dataclass(frozen=True, slots=True)
class ReportOutagePage:
    meta: PageMeta
    form: FormState
    fiche_options: list[Option]
    country_options: list[Option]


@dataclass(frozen=True, slots=True)
class ContributionView:
    id: str  # jamais d'e-mail ici : il reste privé
    kind_label: str
    fiche_title: str
    fiche_url: str
    title: str
    body_html: Markup
    source_url: str | None
    api_version: str | None
    pseudo: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class ConfirmationView:
    target_id: str
    still_works: bool
    api_version: str | None
    pseudo: str | None
    proof: str | None
    created_at: datetime


@dataclass(frozen=True, slots=True)
class UsageView:
    label: str
    count: int
    accounts: int


@dataclass(frozen=True, slots=True)
class ReviewPage:
    meta: PageMeta
    reviewer: str
    pending: list[ContributionView]
    flash: Flash | None = None
    confirmations: list[ConfirmationView] = field(default_factory=list)
    usage: list[UsageView] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class LoginPage:
    meta: PageMeta
    github_url: str
    retour: str
    jury_enabled: bool
    form: FormState


@dataclass(frozen=True, slots=True)
class GlossaryPage:
    meta: PageMeta
    terms: list[GlossaryTerm]


@dataclass(frozen=True, slots=True)
class StaticPage:
    meta: PageMeta


@dataclass(frozen=True, slots=True)
class ErrorPage:
    meta: PageMeta
    status_code: int
    message: str


@dataclass(frozen=True, slots=True)
class StyleguidePage:
    """Atelier de Loum : chaque composant avec des données d'exemple (dev seulement)."""

    meta: PageMeta
    statuses: list[StatusView]
    cards: list[FicheCard]
    gotcha: GotchaView | None
    flashes: list[Flash]
    form: FormState
    options: list[Option]
