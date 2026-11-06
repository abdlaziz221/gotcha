"""Lecture (et écriture des brouillons) du dossier content/ : fiches, étapes, pièges, glossaire.

Utilisé par le stockage mémoire, par scripts/seed.py (content/ vers PostgreSQL) et par
scripts/export_contributions.py (contributions approuvées vers content/). Le format est
décrit dans content/README.md. Toute erreur indique le fichier fautif.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from app.domain.models import (
    SLUG_PATTERN,
    Contribution,
    ContributionKind,
    ContributionStatus,
    Fiche,
    GlossaryTerm,
    Gotcha,
    Step,
)

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)
_SECTION_FIELDS = {"symptome": "symptom_md", "cause": "cause_md", "solution": "fix_md"}
# Début ou fin d'un bloc de code Markdown : ses lignes « ## » ne sont pas des titres.
_FENCE_RE = re.compile(r"^ {0,3}(```|~~~)")


class ContentError(ValueError):
    """Contenu mal formé ; le message commence par le chemin du fichier."""


def load_fiches(content_dir: Path) -> list[Fiche]:
    fiches_dir = content_dir / "fiches"
    if not fiches_dir.is_dir():
        raise ContentError(f"{fiches_dir} : dossier introuvable")
    return [load_fiche(d) for d in sorted(fiches_dir.iterdir()) if d.is_dir()]


def load_fiche(fiche_dir: Path) -> Fiche:
    slug = fiche_dir.name
    meta = _read_yaml(fiche_dir / "fiche.yml")
    steps_file = fiche_dir / "etapes.md"
    steps = _parse_steps(steps_file.read_text(encoding="utf-8")) if steps_file.exists() else []
    gotchas_dir = fiche_dir / "pieges"
    gotchas = (
        [_load_gotcha(slug, f) for f in sorted(gotchas_dir.glob("*.md"))]
        if gotchas_dir.is_dir()
        else []
    )
    try:
        fiche = Fiche(slug=slug, steps=steps, gotchas=gotchas, **meta)
    except (ValidationError, TypeError) as exc:
        raise ContentError(f"{fiche_dir / 'fiche.yml'} : {exc}") from exc
    _refuse_future_date(fiche_dir / "fiche.yml", fiche.last_confirmed_on)
    return fiche


def load_glossary(content_dir: Path) -> list[GlossaryTerm]:
    path = content_dir / "glossaire.yml"
    if not path.exists():
        return []
    data = _read_yaml(path)
    terms = data.get("termes")
    if not isinstance(terms, list) or not terms:
        # Sinon le chargement remplacerait tout le glossaire par une liste vide.
        raise ContentError(f"{path} : la liste « termes » est absente ou vide")
    try:
        return [GlossaryTerm(**item) for item in terms]
    except (ValidationError, TypeError) as exc:
        raise ContentError(f"{path} : {exc}") from exc


EXPORT_LEDGER = Path("a-integrer") / "contributions-exportees.txt"


def export_contributions(contributions: list[Contribution], content_dir: Path) -> list[Path]:
    """Écrit les contributions approuvées dans content/, en brouillons à relire (tâche A7).

    Un piège devient content/fiches/<fiche>/pieges/contribution-<id>.md, chargé comme
    brouillon ; une étape ou une correction devient une note dans content/a-integrer/,
    à reporter à la main. L'e-mail du contributeur n'est jamais écrit. Renvoie les
    fichiers créés.

    Chaque contribution exportée est notée dans content/a-integrer/contributions-exportees.txt,
    versionné avec le reste : on peut relancer le script sans risque, même après avoir
    intégré, renommé ou supprimé un brouillon, ou depuis une autre branche.
    """
    ledger = content_dir / EXPORT_LEDGER
    done = _exported_ids(ledger)
    written = []
    for contribution in contributions:
        if contribution.status is not ContributionStatus.APPROVED or contribution.id in done:
            continue
        short_id = re.sub(r"[^a-z0-9]", "", contribution.id.lower())[:8] or "sans-id"
        # Le slug sert à bâtir un chemin : jamais « ../ » ni autre chose qu'un slug.
        slug = (
            contribution.fiche_slug if re.fullmatch(SLUG_PATTERN, contribution.fiche_slug) else ""
        )
        fiche_dir = content_dir / "fiches" / slug if slug else None
        if contribution.kind is ContributionKind.GOTCHA and fiche_dir and fiche_dir.is_dir():
            path = fiche_dir / "pieges" / f"contribution-{short_id}.md"
            text = _gotcha_draft(contribution)
        else:
            name = f"{slug}-{short_id}.md" if slug else f"contribution-{short_id}.md"
            path = content_dir / "a-integrer" / name
            text = _integration_note(contribution)
        if not path.resolve().is_relative_to(content_dir.resolve()) or path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        written.append(path)
        done.add(contribution.id)
        _note_export(ledger, contribution.id)
    return written


def _exported_ids(ledger: Path) -> set[str]:
    if not ledger.exists():
        return set()
    lines = ledger.read_text(encoding="utf-8").splitlines()
    return {line.strip() for line in lines if line.strip() and not line.startswith("#")}


def _note_export(ledger: Path, contribution_id: str) -> None:
    ledger.parent.mkdir(parents=True, exist_ok=True)
    header = (
        ""
        if ledger.exists()
        else (
            "# Contributions déjà exportées par scripts/export_contributions.py, une par ligne.\n"
            "# Ne pas retirer de ligne : la contribution serait exportée de nouveau.\n"
        )
    )
    with ledger.open("a", encoding="utf-8", newline="\n") as file:
        file.write(f"{header}{contribution_id}\n")


def _contribution_day(contribution: Contribution) -> date:
    return (contribution.reviewed_at or contribution.created_at).date()


def _contributed_markdown(markdown: str) -> str:
    """Prépare le texte d'un contributeur pour un brouillon qui doit toujours se charger.

    - Fins de ligne normalisées comme le chargeur les lit (\r, \f, \x85,  …) : un
      « ## » caché derrière l'une d'elles créerait une section.
    - Hors des blocs de code, « ## » devient « ### » : il casserait le découpage
      Symptôme / Cause / Solution. Dans un bloc de code, le texte reste intact.
    - « [[ » est échappé : il serait lu comme un lien de glossaire (« if [[ -z $X ]] »).
    - Un bloc de code laissé ouvert est refermé, sinon il avalerait les sections suivantes.
    """
    lines = []
    in_fence = False
    for line in markdown.splitlines():
        if _FENCE_RE.match(line):
            in_fence = not in_fence
        elif not in_fence and line.startswith("## "):
            line = "#" + line
        lines.append(line.replace("[[", r"\[\["))
    if in_fence:
        lines.append("```")
    return "\n".join(lines).strip()


def _gotcha_draft(contribution: Contribution) -> str:
    day = _contribution_day(contribution)
    source: dict[str, Any] = {
        "title": f"Contribution de {contribution.pseudo} sur Gotcha",
        "author": contribution.pseudo,
        "accessed_on": day,
    }
    if contribution.source_url:
        source["url"] = str(contribution.source_url)
    meta = {
        "title": contribution.title,
        "severity": "major",
        "environments": ["sandbox", "production"],
        "api_version": contribution.api_version,
        "error_codes": [],
        "publication": "draft",
        "verified_by": None,
        "last_confirmed_on": day,
        "sources": [source],
    }
    header = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()
    reviewer = contribution.reviewer or "un relecteur"
    return (
        f"---\n{header}\n---\n\n"
        f"<!-- Contribution {contribution.id}, approuvée par {reviewer} le {day.isoformat()}.\n"
        "À faire avant publication : répartir le texte entre Symptôme, Cause et Solution,\n"
        "ajuster la gravité et les environnements, recouper la source, puis publier\n"
        "Les « [[ » du texte sont échappés : dans un bloc de code, retirer les barres obliques.\n"
        "(publication: published, verified_by: <pseudo>). -->\n\n"
        f"## Symptôme\n\n{_contributed_markdown(contribution.body_md)}\n\n"
        "## Cause\n\nÀ compléter à partir du texte de la contribution.\n\n"
        "## Solution\n\nÀ compléter à partir du texte de la contribution.\n"
    )


def _integration_note(contribution: Contribution) -> str:
    day = _contribution_day(contribution)
    lines = [
        f"# À intégrer : {contribution.title}",
        "",
        f"- Fiche : `{contribution.fiche_slug}`",
        f"- Type : {contribution.kind.value}",
        f"- Proposé par : {contribution.pseudo}, approuvé le {day.isoformat()}",
        f"- Source : {contribution.source_url or 'aucune'}",
        f"- Version de l'API : {contribution.api_version or 'non précisée'}",
        "",
        "Reporter ce changement dans les fichiers de la fiche, puis supprimer cette note.",
        "",
        "## Texte de la contribution",
        "",
        _contributed_markdown(contribution.body_md),
        "",
    ]
    return "\n".join(lines)


def _load_gotcha(fiche_slug: str, path: Path) -> Gotcha:
    match = _FRONTMATTER_RE.match(path.read_text(encoding="utf-8"))
    if not match:
        raise ContentError(f"{path} : en-tête YAML (entre deux lignes ---) introuvable")
    meta = yaml.safe_load(match.group(1)) or {}
    sections = _split_sections(match.group(2))
    fields: dict[str, Any] = {}
    for heading, body in sections.items():
        key = _SECTION_FIELDS.get(_normalize(heading))
        if key is None:
            raise ContentError(
                f"{path} : section inconnue « {heading} » (Symptôme, Cause, Solution)"
            )
        fields[key] = body
    missing = [h for h, key in _SECTION_FIELDS.items() if key not in fields]
    if missing:
        raise ContentError(f"{path} : sections manquantes : {', '.join(missing)}")
    try:
        gotcha = Gotcha(id=f"{fiche_slug}.{path.stem}", fiche_slug=fiche_slug, **meta, **fields)
    except (ValidationError, TypeError) as exc:
        raise ContentError(f"{path} : {exc}") from exc
    _refuse_future_date(path, gotcha.last_confirmed_on)
    return gotcha


def _refuse_future_date(path: Path, day: date) -> None:
    """Une date future ne se corrigerait plus en base : le stockage garde la plus récente."""
    if day > datetime.now(UTC).date():
        raise ContentError(f"{path} : last_confirmed_on {day} est dans le futur")


def _parse_steps(markdown: str) -> list[Step]:
    return [
        Step(order=i, title=title, body_md=body)
        for i, (title, body) in enumerate(_split_sections(markdown).items(), start=1)
    ]


def _split_sections(markdown: str) -> dict[str, str]:
    """Découpe un texte Markdown sur ses titres de niveau 2 (« ## Titre »).

    Une ligne « ## » dans un bloc de code (commentaire, exemple) n'est pas un titre.
    """
    sections: dict[str, list[str]] = {}
    current: list[str] | None = None
    in_fence = False
    for line in markdown.splitlines():
        if _FENCE_RE.match(line):
            in_fence = not in_fence
        if not in_fence and line.startswith("## "):
            current = sections.setdefault(line[3:].strip(), [])
        elif current is not None:
            current.append(line)
    return {title: "\n".join(lines).strip() for title, lines in sections.items()}


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ContentError(f"{path} : fichier introuvable")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ContentError(f"{path} : YAML invalide : {exc}") from exc
    if not isinstance(data, dict):
        raise ContentError(f"{path} : le fichier doit contenir un dictionnaire YAML")
    return data


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).strip().lower()
