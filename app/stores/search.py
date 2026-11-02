"""Logique commune aux stockages : brouillons, tri, recherche, compteurs de confirmation.

MemoryStore et PostgresStore appliquent exactement ces fonctions : leurs résultats
sont identiques par construction (vérifié par tests/contract/, décision D17).
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from app.domain.models import (
    Fiche,
    GlossaryTerm,
    Gotcha,
    Publication,
    SearchHit,
    SearchHitKind,
    SearchQuery,
)
from app.domain.text import plain_snippet

_TOKEN_RE = re.compile(r"[\w-]+")


def normalize(text: str) -> str:
    """Minuscules, sans accents : « Sénégal » devient « senegal »."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def visible(fiche: Fiche, *, include_drafts: bool) -> Fiche | None:
    """Sans brouillons : seules les fiches publiées, avec leurs seuls pièges publiés."""
    if include_drafts:
        return fiche
    if fiche.publication is not Publication.PUBLISHED:
        return None
    published = [g for g in fiche.gotchas if g.publication is Publication.PUBLISHED]
    return fiche.model_copy(update={"gotchas": published})


def sort_fiches(fiches: Iterable[Fiche]) -> list[Fiche]:
    return sorted(fiches, key=lambda f: normalize(f.title))


def sort_glossary(terms: Iterable[GlossaryTerm]) -> list[GlossaryTerm]:
    return sorted(terms, key=lambda t: normalize(t.term))


def keep_confirmations(new: Fiche, old: Fiche | None) -> Fiche:
    """Recharger le contenu ne doit pas effacer les confirmations reçues sur le site.

    Les fichiers de content/ ne connaissent pas les compteurs : on garde ceux déjà
    enregistrés, et la date de dernière confirmation la plus récente des deux.
    """
    if old is None:
        return new
    old_gotchas = {g.id: g for g in old.gotchas}

    def merge(gotcha: Gotcha) -> Gotcha:
        previous = old_gotchas.get(gotcha.id)
        if previous is None:
            return gotcha
        return gotcha.model_copy(
            update={
                "confirmations": previous.confirmations,
                "last_confirmed_on": max(previous.last_confirmed_on, gotcha.last_confirmed_on),
            }
        )

    return new.model_copy(
        update={
            "confirmations": old.confirmations,
            "last_confirmed_on": max(old.last_confirmed_on, new.last_confirmed_on),
            "gotchas": [merge(g) for g in new.gotchas],
        }
    )


def _score(tokens: list[str], text: str, weight: float) -> float:
    haystack = normalize(text)
    return sum(weight for t in tokens if t in haystack)


def _gotcha_hits(fiche: Fiche, tokens: list[str]) -> list[SearchHit]:
    hits = []
    for gotcha in fiche.gotchas:
        score = (
            _score(tokens, gotcha.title, 3)
            + _score(tokens, f"{gotcha.symptom_md} {gotcha.cause_md} {gotcha.fix_md}", 1)
            + 5 * sum(1 for code in gotcha.error_codes if normalize(code) in tokens)
        )
        if score:
            hits.append(
                SearchHit(
                    kind=SearchHitKind.GOTCHA,
                    fiche_slug=fiche.slug,
                    title=gotcha.title,
                    snippet=plain_snippet(gotcha.symptom_md),
                    anchor=gotcha.anchor,
                    score=score,
                )
            )
    return hits


def search_fiches(fiches: Iterable[Fiche], query: SearchQuery) -> list[SearchHit]:
    """Recherche dans des fiches déjà filtrées (brouillons) et triées."""
    tokens = [t for t in _TOKEN_RE.findall(normalize(query.text)) if len(t) > 1]
    hits: list[SearchHit] = []
    for fiche in fiches:
        if query.service and fiche.service.slug != query.service:
            continue
        if query.country and fiche.country not in (None, query.country):
            continue
        if not tokens:
            hits.append(
                SearchHit(
                    kind=SearchHitKind.FICHE,
                    fiche_slug=fiche.slug,
                    title=fiche.title,
                    snippet=plain_snippet(fiche.summary),
                )
            )
            continue
        fiche_score = _score(tokens, fiche.title, 3) + _score(tokens, fiche.summary, 1)
        if fiche_score:
            hits.append(
                SearchHit(
                    kind=SearchHitKind.FICHE,
                    fiche_slug=fiche.slug,
                    title=fiche.title,
                    snippet=plain_snippet(fiche.summary),
                    score=fiche_score,
                )
            )
        hits.extend(_gotcha_hits(fiche, tokens))
        hits.extend(
            SearchHit(
                kind=SearchHitKind.ERROR_CODE,
                fiche_slug=fiche.slug,
                title=f"{fiche.title} : erreur {error.code}",
                snippet=plain_snippet(f"{error.meaning} {error.action}"),
                anchor="codes-erreur",
                score=5,
            )
            for error in fiche.error_codes
            if normalize(error.code) in tokens
        )
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[: query.limit]
