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


def direct_requirements() -> dict[str, str]:
    lines = (ROOT_DIR / "requirements.txt").read_text("utf-8").splitlines()
    pins = (re.match(r"([\w.-]+)==([\w.]+)", line.strip()) for line in lines)
    return {m.group(1).lower(): m.group(2) for m in pins if m}


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
    text = (ROOT_DIR / "docs" / "LICENCES.md").read_text("utf-8")
    shipped_part = text.split("## Outils de développement")[0]
    for name, version in direct_requirements().items():
        assert f"| {name} | {version} |" in shipped_part, (
            f"{name}=={version} absent de docs/LICENCES.md : "
            "lancer python scripts/check_licenses.py --markdown"
        )
