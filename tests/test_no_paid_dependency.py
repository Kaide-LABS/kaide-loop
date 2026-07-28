"""Guard G-12 / acceptance A-3, A-8: no paid dependency, no network client, no required API key."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src" / "loopr"

_FORBIDDEN_IMPORTS = (
    "nia",
    "nia_sdk",
    "context7",
    "anthropic",
    "openai",
    "google.generativeai",
    "vertexai",
    "langchain",
    "httpx",
    "requests",
    "aiohttp",
)

_FORBIDDEN_ENV_KEYS = ("ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY")


def test_runtime_dependency_set_is_exactly_pydantic() -> None:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    deps = pyproject["project"]["dependencies"]
    names = {re.split(r"[<>=\[]", dep)[0].strip() for dep in deps}
    assert names == {"pydantic"}


def test_no_forbidden_imports() -> None:
    for path in SRC_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for forbidden in _FORBIDDEN_IMPORTS:
            pattern = rf"^\s*(import|from)\s+{re.escape(forbidden)}\b"
            assert not re.search(pattern, text, re.MULTILINE), f"{path} imports forbidden {forbidden}"


def test_no_api_key_env_reads() -> None:
    for path in SRC_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for key in _FORBIDDEN_ENV_KEYS:
            assert key not in text, f"{path} references forbidden env var {key}"


def test_no_environ_getenv_usage_at_all() -> None:
    """loopr makes no outbound network call and needs no environment-sourced credentials at all."""
    for path in SRC_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "os.environ" not in text, f"{path} reads os.environ"
        assert "getenv(" not in text, f"{path} calls getenv"
