"""Outils de texte liés au format du contenu (syntaxe [[terme]] du glossaire)."""

from __future__ import annotations

import re

TERM_LINK_RE = re.compile(r"\[\[([^\[\]|]{1,60})(?:\|([^\[\]]{1,60}))?\]\]")
_MARKDOWN_NOISE_RE = re.compile(r"[`*_>#]+")
_SENTENCE_END_RE = re.compile(r"(?<=[.!?…])\s")


def strip_term_links(text: str) -> str:
    """[[jeton-acces|jeton]] devient « jeton », [[webhook]] devient « webhook »."""
    return TERM_LINK_RE.sub(lambda m: (m.group(2) or m.group(1)).strip(), text)


def plain_snippet(markdown: str, length: int = 180) -> str:
    """Extrait en texte brut, sans syntaxe Markdown ni liens du glossaire."""
    flat = " ".join(_MARKDOWN_NOISE_RE.sub("", strip_term_links(markdown)).split())
    return flat if len(flat) <= length else flat[: length - 1].rstrip() + "…"


def first_sentence(markdown: str, length: int = 180) -> str:
    """La première phrase, en texte brut : le début de la cause dans l'aperçu public."""
    paragraph = markdown.strip().split("\n\n", 1)[0]
    return _SENTENCE_END_RE.split(plain_snippet(paragraph, length), maxsplit=1)[0]
