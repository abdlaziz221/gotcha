"""Rendu Markdown : sûr (pas de HTML ni de script) et liens du glossaire."""

from __future__ import annotations

from app.domain.models import GlossaryTerm
from app.web.markdown import render_markdown

GLOSSARY = {
    "webhook": GlossaryTerm(slug="webhook", term="Webhook", definition='Une "adresse" appelée.')
}


def test_raw_html_and_scripts_are_neutralized() -> None:
    html = render_markdown("<script>alert(1)</script> <img src=x onerror=alert(1)>")
    assert "<script" not in html
    assert "<img" not in html


def test_dangerous_link_schemes_are_removed() -> None:
    html = render_markdown("[clic](javascript:alert(1))")
    assert "href" not in html  # le lien n'est pas créé, le texte reste inoffensif


def test_links_get_safe_rel() -> None:
    html = render_markdown("[doc](https://example.com)")
    assert 'rel="noopener noreferrer nofollow"' in html


def test_glossary_terms_become_links() -> None:
    html = render_markdown("Configurez le [[webhook]] puis le [[webhook|point d'appel]].", GLOSSARY)
    assert 'href="/glossaire#webhook"' in html
    assert "point d'appel" in html or "point d&#39;appel" in html
    assert "[[" not in html


def test_unknown_glossary_term_stays_plain_text() -> None:
    html = render_markdown("Un [[terme-inconnu|mot]] ici.", GLOSSARY)
    assert "mot" in html
    assert "<a" not in html
