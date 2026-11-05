"""Lecture du dossier content/ : fiches, étapes, pièges et glossaire.

Utilisé par le stockage mémoire et par scripts/seed.py (content/ vers PostgreSQL).
Le format est décrit dans content/README.md. Toute erreur indique le fichier fautif.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from app.domain.models import Fiche, GlossaryTerm, Gotcha, Step

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)
_SECTION_FIELDS = {"symptome": "symptom_md", "cause": "cause_md", "solution": "fix_md"}


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
    """Découpe un texte Markdown sur ses titres de niveau 2 (« ## Titre »)."""
    sections: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in markdown.splitlines():
        if line.startswith("## "):
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
