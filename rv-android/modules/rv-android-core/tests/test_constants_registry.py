"""Verify ENV_* registry well-formedness (gh55, INV-CORE-30).

The `rv-android-core/constants.py` registry MUST contain ENV_* names that match a
fixed regex: every entry is either an `RV_*` user-facing variable, or one of the
three legacy non-`RV_*`-prefixed L1 cross-layer infra paths (`RVSEC_HOME`,
`ANDROID_HOME`, `TOOLS_DIR`). Any ENV_* added in the future MUST satisfy this
predicate.
"""

from __future__ import annotations

import re

from rv_android_core import constants

ENV_NAME_RE = re.compile(r"^(RV_[A-Z_]+|RVSEC_HOME|ANDROID_HOME|TOOLS_DIR)$")


def _env_constants() -> list[tuple[str, str]]:
    """Return list of (constant_name, value) pairs for every ENV_* in the module."""
    return [
        (name, getattr(constants, name))
        for name in dir(constants)
        if name.startswith("ENV_")
    ]


def test_registry_is_non_empty():
    pairs = _env_constants()
    assert pairs, "ENV_* registry is empty — constants.py is missing the env block"


def test_every_env_constant_matches_regex():
    pairs = _env_constants()
    bad = [(n, v) for n, v in pairs if not ENV_NAME_RE.match(v)]
    assert not bad, (
        "ENV_* values must match ^(RV_[A-Z_]+|RVSEC_HOME|ANDROID_HOME|TOOLS_DIR)$; "
        f"violators: {bad}"
    )


def test_every_env_constant_is_string():
    pairs = _env_constants()
    bad = [(n, type(v).__name__) for n, v in pairs if not isinstance(v, str)]
    assert not bad, f"ENV_* values must be strings; violators: {bad}"


def test_dead_constants_removed():
    """Removed by gh55 task 1.3."""
    for dead in (
        "ENV_MEMORY_FILE",
        "ENV_RVANDROID_URL",
        "ENV_SKIP_EXPERIMENT",
        "ENV_JCA_SPEC",
    ):
        assert not hasattr(
            constants, dead
        ), f"{dead} should have been removed (gh55 task 1.3) but still present"


def test_l1_infra_family_present():
    """The 6-name L1 cross-layer infra family MUST be in the registry (gh55 D10)."""
    expected = {
        "ENV_RVSEC_HOME": "RVSEC_HOME",
        "ENV_ANDROID_HOME": "ANDROID_HOME",
        "ENV_TOOLS_DIR": "TOOLS_DIR",
        "ENV_PYDANTIC": "RV_PYDANTIC",
        "ENV_PYDANTIC_STRICT": "RV_PYDANTIC_STRICT",
        "ENV_PYDANTIC_LOG": "RV_PYDANTIC_LOG",
    }
    for name, value in expected.items():
        assert hasattr(constants, name), f"L1 infra family missing: {name}"
        assert (
            getattr(constants, name) == value
        ), f"{name} value mismatch: got {getattr(constants, name)!r}, expected {value!r}"
