"""Planted-violation tests for `scripts/check_env_vars_drift.py` (gh55).

Each test writes a temporary fixture containing exactly one form of violation
(or one form of allowed pattern), runs the lint via the same matchers, and
asserts the expected outcome. We import the lint module's matchers directly
rather than spawning a subprocess so the fixtures can target individual regexes
without scanning the whole repo.

Five forbidden forms (must each be flagged outside the L1 allow-list):
    1. os.environ.get("RV_X")
    2. os.environ["RV_X"]
    3. os.getenv("RV_X")
    4. dict(os.environ)             — outside rv-experiment
    5. os.environ.copy()            — outside rv-experiment

Allowed (L1 cross-layer infra family) inside `rv-android-core/util/validation/config.py`,
`rv-android-core/util/jar_resolver.py`, and `rv-android-core/util/android/android.py`:
    RV_PYDANTIC, RV_PYDANTIC_STRICT, RV_PYDANTIC_LOG, RVSEC_HOME, ANDROID_HOME, TOOLS_DIR.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

LINT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "check_env_vars_drift.py"


def _load_lint_module():
    spec = importlib.util.spec_from_file_location("_check_env_vars_drift", LINT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["_check_env_vars_drift"] = module
    spec.loader.exec_module(module)
    return module


lint = _load_lint_module()


def test_form_1_environ_get_rv_literal_matches():
    """Form 1: `os.environ.get("RV_X")` MUST be detected."""
    code = 'value = os.environ.get("RV_TOOLS")'
    assert lint.RX_ENVIRON_GET.search(code) is not None


def test_form_2_environ_subscript_rv_literal_matches():
    """Form 2: `os.environ["RV_X"]` MUST be detected."""
    code = 'value = os.environ["RV_TOOLS"]'
    assert lint.RX_ENVIRON_SUB.search(code) is not None


def test_form_3_getenv_rv_literal_matches():
    """Form 3: `os.getenv("RV_X")` MUST be detected."""
    code = 'value = os.getenv("RV_TOOLS")'
    assert lint.RX_GETENV.search(code) is not None


def test_form_4_dict_environ_matches():
    """Form 4: `dict(os.environ)` MUST be detected."""
    code = "env = dict(os.environ)"
    assert lint.RX_DICT_ENVIRON.search(code) is not None


def test_form_4_patch_dict_is_not_a_violation():
    """`patch.dict(os.environ, ...)` (test mock idiom) MUST NOT be flagged."""
    code = "with patch.dict(os.environ, {'X': 'Y'}):"
    assert lint.RX_DICT_ENVIRON.search(code) is None


def test_form_5_environ_copy_matches():
    """Form 5: `os.environ.copy()` MUST be detected."""
    code = "env = os.environ.copy()"
    assert lint.RX_ENVIRON_COPY.search(code) is not None


def test_l1_infra_family_allowed_via_allowlist():
    """The 9-name L1 cross-layer infra family is recognized as allow-listed.

    The three device timeout budgets belong here for the same reason the
    Pydantic toggles do: they are read by `rv-android-core` at the point of
    use, because their correct value follows from the host and its
    concurrency level rather than from the experiment definition.
    """
    expected = {
        "RV_PYDANTIC",
        "RV_PYDANTIC_STRICT",
        "RV_PYDANTIC_LOG",
        "RVSEC_HOME",
        "ANDROID_HOME",
        "TOOLS_DIR",
        "RV_EMULATOR_BOOT_TIMEOUT",
        "RV_ADB_CMD_TIMEOUT",
        "RV_APK_INSTALL_TIMEOUT",
    }
    assert lint.L1_INFRA_NAMES == expected


def test_l1_allowlist_files_are_realistic():
    """The L1 allow-list points at files that exist in the repo (lint cannot
    silently allow violations in non-existent paths)."""
    for path in lint.L1_ALLOWLIST_FILES:
        assert path.exists(), f"L1 allow-list file missing: {path}"


def test_constant_registry_loads_non_empty():
    """Cross-check (c) requires a populated registry; this guards against an
    empty file shadowing the lint."""
    registry = lint._load_registry()
    assert registry, "registry parse returned empty"
    assert "ENV_PYDANTIC" in registry
    assert registry["ENV_PYDANTIC"] == "RV_PYDANTIC"


def test_l1_infra_literal_at_non_l1_is_flagged():
    """L1 infra literals (e.g., `RVSEC_HOME`) outside the allow-list are flagged."""
    code = 'value = os.environ.get("RVSEC_HOME")'
    assert lint.RX_ENVIRON_GET_INFRA.search(code) is not None


# ---------------------------------------------------------------------------
# INV-EXP-34 — RV_PACKAGE_DETECTOR is read at the entry points and nowhere else
# ---------------------------------------------------------------------------

_MODULES_DIR = Path(__file__).resolve().parents[2] / "modules"

# The two entry points allowed to resolve the variable: rv-experiment, which owns
# the CLI surface of an experiment, and the rv-static-analysis command, which is
# a run in its own right when invoked standalone (design D4).
_ENTRY_POINT_READERS = {
    _MODULES_DIR / "rv-experiment" / "src" / "rv_experiment" / "config.py",
    _MODULES_DIR / "rv-static-analysis" / "src" / "rv_static_analysis" / "__main__.py",
}


def _production_sources() -> list[Path]:
    return [
        path
        for path in _MODULES_DIR.rglob("*.py")
        if "__pycache__" not in path.parts and "tests" not in path.parts
    ]


def test_package_detector_env_read_only_at_entry_points():
    """No layer between an entry point and `App` looks the variable up.

    `rv-platform`, `rv-instrumentation-*` and `rv-android-core` receive the
    resolved boolean by value; `domain/app.py` reads nothing at all
    (INV-CORE-55). A read appearing anywhere else means the decision acquired a
    second, invisible source.
    """
    readers = []
    for path in _production_sources():
        text = path.read_text(encoding="utf-8")
        if "ENV_PACKAGE_DETECTOR" not in text:
            continue
        # Both idioms count: `os.getenv(ENV_*)` is as much a read as
        # `os.environ.get(ENV_*)`, and both slip past check_env_vars_drift.py,
        # which only matches string literals.
        if any(form in text for form in ("os.environ", "os.getenv")):
            readers.append(path)

    assert set(readers) == _ENTRY_POINT_READERS, (
        "RV_PACKAGE_DETECTOR must be resolved at the two entry points only "
        f"(INV-EXP-34). Found readers: {sorted(str(p) for p in readers)}"
    )


def test_package_detector_never_appears_as_a_literal_at_a_read_site():
    """Every read goes through the registry constant, never the raw string."""
    registry_file = (
        _MODULES_DIR / "rv-android-core" / "src" / "rv_android_core" / "constants.py"
    )

    offenders = [
        path
        for path in _production_sources()
        if path != registry_file
        and any(
            quoted in path.read_text(encoding="utf-8")
            for quoted in ('"RV_PACKAGE_DETECTOR"', "'RV_PACKAGE_DETECTOR'")
        )
    ]

    assert offenders == [], (
        "The literal belongs only in constants.py; every other site must import "
        f"ENV_PACKAGE_DETECTOR. Found: {sorted(str(p) for p in offenders)}"
    )


def test_l1_allowlist_did_not_grow_for_the_package_policy():
    """`domain/app.py` is not an environment reader and must not become one."""
    assert len(lint.L1_ALLOWLIST_FILES) == 3
    assert not any("domain" in str(path) for path in lint.L1_ALLOWLIST_FILES)
    assert "RV_PACKAGE_DETECTOR" not in lint.L1_INFRA_NAMES
