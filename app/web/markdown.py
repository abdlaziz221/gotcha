"""Rendu sûr du Markdown des fiches et des contributions.

markdown-it-py (MIT) sans HTML brut, puis nettoyage par nh3 (MIT) avec une liste
blanche de balises. Les termes du glossaire s'écrivent [[webhook]] ou
[[jeton-acces|jeton]] et deviennent des liens vers /glossaire.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

import nh3
from markdown_it import MarkdownIt
from markupsafe import Markup

from app.domain.models import GlossaryTerm
from app.domain.text import TERM_LINK_RE

_md = MarkdownIt("commonmark", {"html": False, "linkify": False}).enable("table")

ALLOWED_TAGS = {
    "p", "br", "strong", "em", "code", "pre", "ul", "ol", "li", "a", "blockquote",
    "h3", "h4", "table", "thead", "tbody", "tr", "th", "td", "hr",
}  # fmt: skip
ALLOWED_ATTRIBUTES = {"a": {"href", "title"}, "code": {"class"}, "th": {"align"}, "td": {"align"}}


def link_glossary_terms(text: str, glossary: Mapping[str, GlossaryTerm]) -> str:
    """Remplace [[terme]] par un lien Markdown vers sa définition ; terme inconnu : texte simple."""

    def replace(match: re.Match[str]) -> str:
        key = match.group(1).strip()
        label = (match.group(2) or key).strip()
        term = glossary.get(key) or next(
            (t for t in glossary.values() if t.term.lower() == key.lower()), None
        )
        if term is None:
            return label
        title = term.definition.replace('"', "'").replace("\n", " ")
        return f'[{label}](/glossaire#{term.slug} "{title}")'

    return TERM_LINK_RE.sub(replace, text)


def render_markdown(text: str, glossary: Mapping[str, GlossaryTerm] | None = None) -> Markup:
    if glossary:
        text = link_glossary_terms(text, glossary)
    html = _md.render(text)
    clean = nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes={"http", "https", "mailto"},
        link_rel="noopener noreferrer nofollow",
    )
    return Markup(clean)  # noqa: S704 (nettoyé par nh3 juste au-dessus)
