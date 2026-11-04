"""Modèle de données de Gotcha : le vocabulaire commun à tout le code.

CONTRAT PARTAGÉ. On peut ajouter un champ optionnel ; renommer ou supprimer un
champ demande l'accord des trois membres (voir app/domain/README.md).
"""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
GOTCHA_ID_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*\.[a-z0-9]+(?:-[a-z0-9]+)*$"
COUNTRY_PATTERN = r"^[A-Z]{2}$"


class Model(BaseModel):
    """Base commune : objets immuables, champs inconnus refusés."""

    model_config = ConfigDict(frozen=True, extra="forbid")


# --- Énumérations ------------------------------------------------------------


class ServiceKind(StrEnum):
    PAYMENT = "payment"
    HOSTING = "hosting"


class Environment(StrEnum):
    SANDBOX = "sandbox"
    PRODUCTION = "production"


class Severity(StrEnum):
    BLOCKING = "blocking"  # l'intégration ne marche pas du tout
    MAJOR = "major"  # un cas important casse (callbacks, doublons, remboursements…)
    MINOR = "minor"  # perte de temps, comportement surprenant


class Publication(StrEnum):
    DRAFT = "draft"  # visible en développement seulement, à vérifier
    PUBLISHED = "published"  # vérifié par un humain, visible en production


class Status(StrEnum):
    NORMAL = "normal"  # aucune panne connue
    DEGRADED = "degraded"
    DOWN = "down"
    UNKNOWN = "unknown"


class IncidentSource(StrEnum):
    FLUTTERWAVE = "flutterwave"  # flux public d'incidents de Flutterwave
    COMMUNITY = "community"  # signalé par un dev sur le site
    AGENT = "agent"  # signalé par un agent IA via le serveur MCP


class ContributionKind(StrEnum):
    GOTCHA = "gotcha"  # un nouveau piège
    STEP = "step"  # une étape nouvelle ou corrigée
    CORRECTION = "correction"  # quelque chose est faux ou dépassé


class ContributionStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class TargetKind(StrEnum):
    FICHE = "fiche"
    GOTCHA = "gotcha"


class SearchHitKind(StrEnum):
    FICHE = "fiche"
    GOTCHA = "gotcha"
    ERROR_CODE = "error_code"


# --- Contenu des fiches ------------------------------------------------------


class Source(Model):
    """D'où vient une information : une page publique ou un retour de terrain."""

    title: str = Field(min_length=3)
    url: HttpUrl | None = None
    author: str | None = None  # pseudo du dev, pour un retour de terrain
    accessed_on: date

    @model_validator(mode="after")
    def _url_or_author(self) -> Self:
        if self.url is None and not self.author:
            raise ValueError("une source a besoin d'une URL ou d'un auteur")
        return self


class Service(Model):
    """Un service suivi : un opérateur de paiement ou un hébergeur."""

    slug: str = Field(pattern=SLUG_PATTERN)  # "mtn-momo"
    name: str  # "MTN MoMo"
    kind: ServiceKind
    operator: str  # "MTN"
    docs_url: HttpUrl | None = None


class Step(Model):
    order: int = Field(ge=1)
    title: str
    body_md: str


class EnvDifference(Model):
    """Un écart entre le bac à sable et la production."""

    topic: str  # "Devise"
    sandbox: str
    production: str


class ErrorCode(Model):
    code: str  # "400", "INVALID_CURRENCY"…
    meaning: str
    action: str


class Gotcha(Model):
    """Un piège : ce que la documentation ne dit pas."""

    id: str = Field(pattern=GOTCHA_ID_PATTERN)  # "<slug de la fiche>.<nom du fichier>"
    fiche_slug: str = Field(pattern=SLUG_PATTERN)
    title: str = Field(min_length=5)
    symptom_md: str
    cause_md: str
    fix_md: str
    severity: Severity
    environments: list[Environment] = Field(min_length=1)
    api_version: str | None = None
    error_codes: list[str] = Field(default_factory=list)
    sources: list[Source] = Field(min_length=1)
    publication: Publication = Publication.DRAFT
    verified_by: str | None = None  # qui l'a vérifié ; obligatoire pour publier
    last_confirmed_on: date
    confirmations: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _published_is_verified(self) -> Self:
        if self.publication is Publication.PUBLISHED and not self.verified_by:
            raise ValueError(f"le piège {self.id} est publié sans verified_by")
        if not self.id.startswith(f"{self.fiche_slug}."):
            raise ValueError(f"l'id {self.id} doit commencer par '{self.fiche_slug}.'")
        return self

    @property
    def anchor(self) -> str:
        """Ancre HTML du piège dans la page de sa fiche."""
        return "piege-" + self.id.split(".", 1)[1]


class Fiche(Model):
    """Une fiche : un service dans un pays (ou dans tous les pays si country est vide)."""

    slug: str = Field(pattern=SLUG_PATTERN)  # "orange-money-sn"
    service: Service
    country: str | None = Field(default=None, pattern=COUNTRY_PATTERN)  # code ISO, ex. "SN"
    title: str  # "Orange Money Sénégal"
    summary: str
    api_version: str | None = None
    prerequisites: list[str] = Field(default_factory=list)
    steps: list[Step] = Field(default_factory=list)
    gotchas: list[Gotcha] = Field(default_factory=list)
    differences: list[EnvDifference] = Field(default_factory=list)
    error_codes: list[ErrorCode] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    publication: Publication = Publication.DRAFT
    last_confirmed_on: date
    confirmations: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        orders = [s.order for s in self.steps]
        if orders != list(range(1, len(orders) + 1)):
            raise ValueError(f"fiche {self.slug} : les étapes doivent être numérotées 1, 2, 3…")
        for gotcha in self.gotchas:
            if gotcha.fiche_slug != self.slug:
                raise ValueError(f"le piège {gotcha.id} n'appartient pas à la fiche {self.slug}")
        return self

    def find_gotcha(self, gotcha_id: str) -> Gotcha | None:
        return next((g for g in self.gotchas if g.id == gotcha_id), None)


class GlossaryTerm(Model):
    """Un terme technique expliqué aux débutants."""

    slug: str = Field(pattern=SLUG_PATTERN)
    term: str
    definition: str


# --- Contributions -----------------------------------------------------------


class ContributionInput(Model):
    """Ce qu'envoie le formulaire « Contribuer » (ou, plus tard, un agent)."""

    kind: ContributionKind
    fiche_slug: str = Field(pattern=SLUG_PATTERN)
    title: str = Field(min_length=5, max_length=160)
    body_md: str = Field(min_length=20, max_length=10_000)
    source_url: HttpUrl | None = None
    api_version: str | None = Field(default=None, max_length=40)
    pseudo: str = Field(min_length=2, max_length=40)
    email: str = Field(min_length=5, max_length=254)  # PRIVÉ : jamais affiché ni exposé


class Contribution(Model):
    id: str  # uuid4 en hexadécimal
    kind: ContributionKind
    fiche_slug: str
    title: str
    body_md: str
    source_url: HttpUrl | None = None
    api_version: str | None = None
    pseudo: str
    email: str  # PRIVÉ : jamais affiché, jamais renvoyé par le serveur MCP
    status: ContributionStatus = ContributionStatus.PENDING
    created_at: datetime
    reviewed_at: datetime | None = None
    reviewer: str | None = None
    review_note: str | None = None


class Confirmation(Model):
    """Un clic sur « ça marche encore » (still_works) ou « ça ne marche plus »."""

    target_kind: TargetKind
    target_id: str  # slug de la fiche ou id du piège
    still_works: bool = True
    api_version: str | None = Field(default=None, max_length=40)
    pseudo: str | None = Field(default=None, max_length=40)
    created_at: datetime


# --- Pannes ------------------------------------------------------------------


class Incident(Model):
    """Une panne connue, importée ou signalée.

    service_slug vide : panne Mobile Money non attribuée à un opérateur, qui
    concerne tous les services de paiement du pays. country vide : pays inconnu
    ou tous les pays.
    """

    id: str  # "flutterwave:<id externe>:<pays>:<service>" ou "community:<uuid>"
    source: IncidentSource
    external_id: str | None = None
    service_slug: str | None = None
    country: str | None = Field(default=None, pattern=COUNTRY_PATTERN)
    status: Status
    title: str
    description: str | None = None
    url: HttpUrl | None = None
    started_at: datetime
    resolved_at: datetime | None = None
    reported_by: str | None = None

    @property
    def is_active(self) -> bool:
        return self.resolved_at is None


class OutageReport(Model):
    """Signalement d'une panne par un dev (site) ou un agent (MCP)."""

    service_slug: str = Field(pattern=SLUG_PATTERN)
    country: str | None = Field(default=None, pattern=COUNTRY_PATTERN)
    description: str = Field(min_length=10, max_length=1_000)
    reported_by: str | None = Field(default=None, max_length=40)
    source: IncidentSource = IncidentSource.COMMUNITY


class ServiceStatus(Model):
    """État calculé d'un service dans un pays, à un instant donné."""

    service_slug: str
    country: str | None
    status: Status
    since: datetime | None = None
    active_incidents: list[Incident] = Field(default_factory=list)
    checked_at: datetime


# --- Recherche ---------------------------------------------------------------


class SearchQuery(Model):
    text: str = Field(default="", max_length=200)
    service: str | None = None
    country: str | None = None
    limit: int = Field(default=20, ge=1, le=100)


class SearchHit(Model):
    kind: SearchHitKind
    fiche_slug: str
    title: str
    snippet: str
    anchor: str | None = None  # ancre dans la page de la fiche, ex. "piege-sandbox-eur"
    score: float = 0.0


# --- Comptes -----------------------------------------------------------------


class OAuthGrantKind(StrEnum):
    LOGIN = "login"  # connexion en cours chez GitHub
    CODE = "code"  # code d'autorisation, à usage unique
    ACCESS = "access"  # jeton d'accès au serveur MCP
    REFRESH = "refresh"  # jeton de renouvellement, remplacé à chaque usage


class ExternalIdentity(Model):
    """Ce que le fournisseur d'identité nous apprend sur le développeur."""

    id: str = Field(min_length=3)  # "github:<identifiant numérique>"
    pseudo: str = Field(min_length=1, max_length=100)


class Account(Model):
    """Un développeur connecté. Aucun mot de passe ni jeton GitHub n'est conservé."""

    id: str = Field(min_length=3)
    pseudo: str = Field(min_length=1, max_length=100)
    created_at: datetime
    last_login_at: datetime
    blocked: bool = False
