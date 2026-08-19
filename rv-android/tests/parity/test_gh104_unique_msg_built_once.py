"""`unique_msg` has one constructor, and a grep is what keeps it that way.

The key is `__hash__` and `__eq__` of `RvErrorLog`, so a second place that assembles
it from the fields does not merely duplicate a formula — it forks the identity of a
violation the moment the domain formula changes, which is exactly what gh104 does by
growing the key from five parts to seven. Before this change the tree carried four
such copies (`result_processor.py` ×3, `regenerate_container.py` ×1); each would have
gone on writing five-part keys into files whose other rows carried seven, and nothing
would have raised.

The search is for the f-string fragment `:::{`, not for the bare separator: every
composer is an f-string interpolating a field right after a separator, while every
*reader* splits on the literal `":::"` and never writes that fragment. A grep for
`:::` alone returns the readers too and is therefore useless as a gate.

Two composers are permitted, both in `rv_android_core/domain/log.py`:
`RvErrorLog.unique_msg` (the seven-part violation identity) and
`RvDiagnosticEvent.unique_msg` (the four-part diagnostic-event identity — a different
record type, a different key, untouched by gh104).
"""

from __future__ import annotations

import re
from pathlib import Path

#: What an f-string composing the key looks like: a separator immediately followed by
#: an interpolation.
COMPOSER = re.compile(r":::\{")

REPO_ROOT = Path(__file__).resolve().parents[2]
SCANNED_ROOTS = (REPO_ROOT / "modules", REPO_ROOT / "scripts")

#: The one file allowed to compose. Its two composers are the two permitted ones.
DOMAIN_LOG = REPO_ROOT / "modules/rv-android-core/src/rv_android_core/domain/log.py"

EXCLUDED_PARTS = (".venv", "backup", "__pycache__", "site-packages")


def _scanned_files() -> list[Path]:
    """Every non-test `.py` under `modules/` and `scripts/`.

    Tests are excluded because a test may legitimately spell a key out to assert on
    it; the gate is about production code composing one at runtime.
    """
    files: list[Path] = []
    for root in SCANNED_ROOTS:
        for path in sorted(root.rglob("*.py")):
            parts = set(path.parts)
            if parts & set(EXCLUDED_PARTS):
                continue
            if "tests" in parts or path.name.startswith("test_"):
                continue
            files.append(path)
    return files


def test_only_the_domain_model_composes_the_key() -> None:
    offenders: list[str] = []
    for path in _scanned_files():
        if path == DOMAIN_LOG:
            continue
        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if COMPOSER.search(line):
                offenders.append(
                    f"{path.relative_to(REPO_ROOT)}:{number}: {line.strip()}"
                )

    assert offenders == [], (
        "`unique_msg` is composed outside rv_android_core/domain/log.py; read it from "
        "the domain object instead (core INV-CORE-25):\n" + "\n".join(offenders)
    )


def test_the_domain_model_carries_exactly_the_two_permitted_composers() -> None:
    """A third composer inside `log.py` would fail here rather than pass unseen: the
    file is the gate's blind spot, so the count is pinned instead of trusted."""
    lines = DOMAIN_LOG.read_text(encoding="utf-8").splitlines()
    composing = [
        f"{number}: {line.strip()}"
        for number, line in enumerate(lines, start=1)
        if COMPOSER.search(line)
    ]

    # Two lines for the seven-part violation key (it wraps), one for the four-part
    # diagnostic key.
    assert len(composing) == 3, "\n".join(composing)
    assert "class_full_name" in composing[0]
    assert "self.code or 'UNSPECIFIED'" in composing[1]
    assert "category" in composing[2]


def test_the_violation_key_has_seven_parts_and_the_diagnostic_key_four() -> None:
    """The two permitted composers are permitted for different records, and the gate
    would be vacuous if it did not say which is which."""
    from rv_android_core.domain.log import RvDiagnosticEvent, RvErrorLog

    violation = RvErrorLog(
        spec="CipherSpec",
        error_type="UnsafeAlgorithm",
        class_full_name="com.example.C",
        method="enc",
        source="C.java:9",
        message="unknown",
    )
    diagnostic = RvDiagnosticEvent(
        category="crash",
        class_full_name="java.lang.NullPointerException",
        method="onClick",
        message="FATAL EXCEPTION: main",
    )

    assert len(violation.unique_msg.split(":::")) == 7
    assert len(diagnostic.unique_msg.split(":::")) == 4
