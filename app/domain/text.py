"""Outils de texte liés au format du contenu (syntaxe [[terme]] du glossaire)."""

from __future__ import annotations

import re

TERM_LINK_RE = re.compile(r"\[\[([^\[\]|]{1,60})(?:\|([^\[\]]{1,60}))?\]\]")
_MARKDOWN_NOISE_RE = re.compile(r"[`*_>#]+")


def strip_term_links(text: str) -> str:
    """[[jeton-acces|jeton]] devient « jeton », [[webhook]] devient « webhook »."""
    return TERM_LINK_RE.sub(lambda m: (m.group(2) or m.group(1)).strip(), text)


def plain_snippet(markdown: str, length: int = 180) -> str:
    """Extrait en texte brut, sans syntaxe Markdown ni liens du glossaire."""
    flat = " ".join(_MARKDOWN_NOISE_RE.sub("", strip_term_links(markdown)).split())
    return flat if len(flat) <= length else flat[: length - 1].rstrip() + "…"
