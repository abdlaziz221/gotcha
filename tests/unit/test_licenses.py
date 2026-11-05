"""Liste des composants à déclarer (scripts/check_licenses.py --markdown, docs/LICENCES.md)."""

from __future__ import annotations

import importlib.util
import re
from types import ModuleType

import pytest

from app.config import ROOT_DIR


@pytest.fixture(scope="module")
def licenses() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "check_licenses", ROOT_DIR / "scripts" / "check_licenses.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical(name: str) -> str:
    """Nom normalisé (PEP 503) : « pydantic-core » et « pydantic_core » sont le même paquet."""
    return re.sub(r"[-_.]+", "-", name).lower()


def direct_requirements(file: str = "requirements.txt") -> dict[str, str]:
    lines = (ROOT_DIR / file).read_text("utf-8").splitlines()
    pins = (re.match(r"([\w.-]+)==([\w.]+)", line.strip()) for line in lines)
    return {canonical(m.group(1)): m.group(2) for m in pins if m}


def table_rows(text: str) -> dict[str, str]:
    rows = (re.match(r"\| ([^|]+) \| ([^|]+) \|", line) for line in text.splitlines())
    return {canonical(m.group(1).strip()): m.group(2).strip() for m in rows if m}


def test_production_environment_follows_the_dockerfile(licenses: ModuleType) -> None:
    dockerfile = (ROOT_DIR / "Dockerfile").read_text("utf-8")
    image = re.search(r"^FROM python:(\d+\.\d+)", dockerfile, re.M)
    assert image is not None
    environment = licenses.production_environment()
    assert environment["python_version"] == image.group(1)
    assert environment["sys_platform"] == "linux"


def test_shipped_follows_dependencies_and_extras(licenses: ModuleType) -> None:
    shipped = licenses.shipped()
    assert set(direct_requirements()) <= shipped
    assert "starlette" in shipped  # dépendance de fastapi
    assert "cryptography" in shipped  # demandée par mcp avec « pyjwt[crypto] »
    assert "pytest" not in shipped  # outil de développement
    assert "pywin32" not in shipped  # réservé à Windows, absent de l'image


def test_markdown_separates_shipped_from_tools(licenses: ModuleType) -> None:
    text = licenses.markdown()
    shipped_part, tools_part = text.split("## Outils de développement")
    assert "| fastapi |" in shipped_part
    assert "| pytest |" in tools_part
    assert "| pytest |" not in shipped_part


def test_licences_file_is_up_to_date() -> None:
    """Versions figées de requirements.txt et de requirements-dev.txt, noms normalisés.

    Les dépendances indirectes ne sont pas figées : la liste de référence est l'artefact
    du job « licences » de la CI (voir docs/SUBMISSION.md).
    """
    text = (ROOT_DIR / "docs" / "LICENCES.md").read_text("utf-8")
    shipped_part, tools_part = text.split("## Outils de développement")
    for part, file in ((shipped_part, "requirements.txt"), (tools_part, "requirements-dev.txt")):
        listed = table_rows(part)
        for name, version in direct_requirements(file).items():
            if file == "requirements-dev.txt" and name in direct_requirements():
                continue
            assert listed.get(name) == version, (
                f"{name}=={version} absent de docs/LICENCES.md : "
                "lancer python scripts/check_licenses.py --markdown"
            )


def test_pip_is_removed_from_the_image() -> None:
    dockerfile = (ROOT_DIR / "Dockerfile").read_text("utf-8")
    assert "pip uninstall -y pip setuptools wheel" in dockerfile
    assert "ensurepip" in dockerfile
