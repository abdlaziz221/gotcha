"""Règles d'architecture : qui a le droit d'importer quoi (voir docs/ARCHITECTURE.md).

Ce test fait respecter la règle de dépendance entre couches : par exemple, le
web et le serveur MCP ne touchent jamais au stockage, ils passent par les services.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.config import ROOT_DIR

# Pour chaque dossier de app/ : les modules app.* qu'il a le droit d'importer.
ALLOWED: dict[str, tuple[str, ...]] = {
    "domain": ("app.domain",),
    "services": ("app.domain", "app.services", "app.security.secrets"),
    "stores": ("app.domain", "app.stores", "app.config"),
    "security": ("app.domain", "app.security"),
    "ingest": ("app.domain", "app.ingest", "app.config", "app.container"),
    "mcp": ("app.domain", "app.mcp", "app.services", "app.security", "app.container"),
    "web": ("app.domain", "app.web", "app.services", "app.security", "app.container", "app.config"),
}


def _imported_modules(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules += [(node.lineno, alias.name) for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.append((node.lineno, node.module))
    return modules


def _is_allowed(module: str, allowed: tuple[str, ...]) -> bool:
    return any(module == prefix or module.startswith(prefix + ".") for prefix in allowed)


@pytest.mark.parametrize("area", sorted(ALLOWED))
def test_layer_imports_only_what_it_is_allowed_to(area: str) -> None:
    violations = [
        f"{path.relative_to(ROOT_DIR)}:{line} importe {module}"
        for path in sorted((ROOT_DIR / "app" / area).rglob("*.py"))
        for line, module in _imported_modules(path)
        if (module == "app" or module.startswith(("app.", "tests")))
        and not _is_allowed(module, ALLOWED[area])
    ]
    assert not violations, (
        f"app/{area} n'a le droit d'importer que {', '.join(ALLOWED[area])} :\n"
        + "\n".join(violations)
    )


def test_every_app_folder_has_a_rule() -> None:
    folders = {p.name for p in (ROOT_DIR / "app").iterdir() if (p / "__init__.py").exists()}
    assert folders == set(ALLOWED), "nouveau dossier dans app/ : ajoutez sa règle ici"
