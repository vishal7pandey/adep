"""Guards for the paddleocr major version (ADE-70).

Dependabot PR #28 raised paddleocr from 2.10.0 to 3.7.0. The provider (`src/providers/ocr_paddle.py`) speaks the 2.x
API (`show_log`, `use_angle_cls`, `ocr(..., cls=True)`), which 3.x rejects at runtime (`ValueError: Unknown argument:
show_log`). Every other test mocks the engine, so CI stayed green. These tests do not mock it:

* the version guards fail on a 3.x resolution (installed package, `uv.lock`, `pyproject.toml`);
* the contract test reads the arguments the provider passes and checks them against the installed paddleocr package's own
  definitions. It reads the package source instead of importing it, because 2.x imports `paddle` (paddlepaddle, not a
  dependency of this project) at import time and constructing `PaddleOCR` downloads model files; neither belongs in a
  unit test.

Lifted only by a deliberate migration of the provider to the 3.x API, or by retiring the engine (ADE-33).
"""

from __future__ import annotations

import ast
import importlib.metadata
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PROVIDER = REPO_ROOT / "src" / "providers" / "ocr_paddle.py"


def _major(version: str) -> int:
    match = re.match(r"(\d+)\.", version)
    assert match, f"not a plain version: {version}"
    return int(match.group(1))


def _installed_package_dir() -> Path:
    try:
        dist = importlib.metadata.distribution("paddleocr")
    except importlib.metadata.PackageNotFoundError:
        pytest.skip("paddleocr is not installed")
    return Path(str(dist.locate_file("paddleocr")))


def _lock_paddleocr_version(lock_text: str) -> str:
    match = re.search(r'^name = "paddleocr"\r?\nversion = "([^"]+)"', lock_text, re.MULTILINE)
    assert match, "paddleocr is not resolved in uv.lock"
    return match.group(1)


def _paddle_calls(tree: ast.AST) -> tuple[set[str], set[str]]:
    """Keyword names the provider passes to `PaddleOCR(...)` and to `<engine>.ocr(...)`."""
    constructor: set[str] = set()
    ocr: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        names = {kw.arg for kw in node.keywords if kw.arg}
        if isinstance(func, ast.Name) and func.id == "PaddleOCR":
            constructor |= names
        elif isinstance(func, ast.Attribute) and func.attr == "ocr":
            ocr |= names
    return constructor, ocr


def _option_names(source: str) -> set[str]:
    """Names declared with `parser.add_argument("--name", ...)` in a 2.x argument definition."""
    return set(re.findall(r'add_argument\(\s*"--([A-Za-z0-9_]+)"', source))


def _ocr_method_args(source: str) -> set[str]:
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ClassDef) and node.name == "PaddleOCR":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "ocr":
                    return {a.arg for a in item.args.args + item.args.kwonlyargs}
    return set()


class TestVersionGuard:
    def test_major_helper(self):
        assert _major("2.10.0") == 2
        assert _major("3.7.0") == 3
        assert _major("10.0.0") == 10

    def test_installed_paddleocr_is_2x(self):
        installed = importlib.metadata.version("paddleocr")
        assert _major(installed) == 2, (
            f"paddleocr {installed} is installed; the provider needs 2.x (ADE-70)"
        )

    def test_lockfile_resolves_paddleocr_2x(self):
        version = _lock_paddleocr_version((REPO_ROOT / "uv.lock").read_text(encoding="utf-8"))
        assert _major(version) == 2, (
            f"uv.lock resolves paddleocr {version}; the provider needs 2.x (ADE-70)"
        )

    def test_lock_helper_reads_the_entry(self):
        text = 'name = "other"\nversion = "9.0.0"\n\n[[package]]\nname = "paddleocr"\r\nversion = "3.7.0"\n'
        assert _lock_paddleocr_version(text) == "3.7.0"

    def test_pyproject_caps_paddleocr_below_3(self):
        text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        match = re.search(r'^\s*"paddleocr([^"]*)"', text, re.MULTILINE)
        assert match, "paddleocr is not a dependency in pyproject.toml"
        assert re.search(r"<\s*3(\.0)*\s*(,|$)", match.group(1)), (
            f"paddleocr{match.group(1)} has no '<3' cap (ADE-70)"
        )


class TestProviderMatchesInstalledPackage:
    """Not mocked: the provider's arguments are checked against the installed paddleocr's own definitions."""

    def test_provider_arguments_are_what_the_helper_expects(self):
        constructor, ocr = _paddle_calls(ast.parse(PROVIDER.read_text(encoding="utf-8")))
        # If the provider is migrated, this fails first and points here: update the contract together with it.
        assert constructor == {"use_angle_cls", "lang", "show_log"}
        assert ocr == {"cls"}

    def test_constructor_options_are_accepted_by_the_installed_package(self):
        package = _installed_package_dir()
        constructor, _ = _paddle_calls(ast.parse(PROVIDER.read_text(encoding="utf-8")))

        known: set[str] = set()
        for relative in ("tools/infer/utility.py", "paddleocr.py"):
            path = package / relative
            if path.is_file():
                known |= _option_names(path.read_text(encoding="utf-8"))

        unknown = constructor - known
        assert not unknown, (
            f"the installed paddleocr does not define {sorted(unknown)} (the provider passes them to PaddleOCR()); "
            "3.x raises 'ValueError: Unknown argument' for these (ADE-70)"
        )

    def test_ocr_method_takes_the_keywords_the_provider_passes(self):
        package = _installed_package_dir()
        _, ocr = _paddle_calls(ast.parse(PROVIDER.read_text(encoding="utf-8")))
        main = package / "paddleocr.py"
        accepted = _ocr_method_args(main.read_text(encoding="utf-8")) if main.is_file() else set()
        missing = ocr - accepted
        assert not missing, (
            f"PaddleOCR.ocr() of the installed paddleocr has no argument {sorted(missing)} (ADE-70)"
        )
