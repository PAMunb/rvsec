#!/usr/bin/env python3
"""Lint script enforcing the env-var contract for gh55 (INV-CORE-31, INV-EXP-30).

Three cross-checks, each fatal:

1. **Read-form scan** — every `RV_*` env access in `modules/` MUST go through an
   `ENV_*` constant from `rv-android-core/constants.py`. Five forms are covered:
   `os.environ.get("RV_X")`, `os.environ["RV_X"]`, `os.getenv("RV_X")`,
   `dict(os.environ)`, `os.environ.copy()`. The last two are flagged outside
   `modules/rv-experiment/` because they leak the entire environment past Layer
   Purity boundaries. The L1 cross-layer infra family (six names) is allow-listed
   in `rv-android-core` only.

2. **README/.env.example coverage** — every `RV_*` documented in `README.md` or
   `.env.example` MUST have a corresponding `ENV_*` constant in the registry.

3. **Registry coverage** — every `ENV_*` constant MUST be documented in `README.md`
   and `.env.example`.

Exit codes:
    0 — all checks pass
    1 — one or more checks failed

Run from repo root: ``uv run python scripts/check_env_vars_drift.py``
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONSTANTS_FILE = (
    REPO_ROOT
    / "modules"
    / "rv-android-core"
    / "src"
    / "rv_android_core"
    / "constants.py"
)
README_FILE = REPO_ROOT / "README.md"
ENV_EXAMPLE_FILE = REPO_ROOT / ".env.example"

# Files containing planted-violation fixtures (test data) — skipped by the lint.
LINT_TEST_PATHS = (
    "tests/lint/",
    "/tests/lint/",
)

# L1 cross-layer infra family — six canonical readers allow-listed at L1.
L1_ALLOWLIST_FILES = (
    REPO_ROOT
    / "modules"
    / "rv-android-core"
    / "src"
    / "rv_android_core"
    / "util"
    / "validation"
    / "config.py",
    REPO_ROOT
    / "modules"
    / "rv-android-core"
    / "src"
    / "rv_android_core"
    / "util"
    / "jar_resolver.py",
    REPO_ROOT
    / "modules"
    / "rv-android-core"
    / "src"
    / "rv_android_core"
    / "util"
    / "android"
    / "android.py",
)
L1_INFRA_NAMES = frozenset(
    {
        "RV_PYDANTIC",
        "RV_PYDANTIC_STRICT",
        "RV_PYDANTIC_LOG",
        "RVSEC_HOME",
        "ANDROID_HOME",
        "TOOLS_DIR",
        # Device timeout budgets read by util/android/android.py. Their value is a
        # property of the host and its concurrency level, not of the experiment.
        "RV_EMULATOR_BOOT_TIMEOUT",
        "RV_ADB_CMD_TIMEOUT",
        "RV_APK_INSTALL_TIMEOUT",
    }
)

# Entry points may read user-facing RV_* env vars through ENV_* constants; the
# layers between an entry point and the domain model may not. Only rv-experiment
# may take the whole environment at once, which is what this path gates — the
# wholesale forms below leak every variable past the Layer Purity boundary.
L5_DIR = REPO_ROOT / "modules" / "rv-experiment" / "src"

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# Five read forms; the regex captures the variable name where applicable.
RX_ENVIRON_GET = re.compile(r'os\.environ\.get\(\s*["\'](RV_[A-Z0-9_]+)["\']')
RX_ENVIRON_GET_INFRA = re.compile(
    r'os\.environ\.get\(\s*["\']((?:RVSEC_HOME|ANDROID_HOME|TOOLS_DIR))["\']'
)
RX_ENVIRON_SUB = re.compile(r'os\.environ\[\s*["\'](RV_[A-Z0-9_]+)["\']')
RX_ENVIRON_SUB_INFRA = re.compile(
    r'os\.environ\[\s*["\']((?:RVSEC_HOME|ANDROID_HOME|TOOLS_DIR))["\']'
)
RX_GETENV = re.compile(r'os\.getenv\(\s*["\'](RV_[A-Z0-9_]+)["\']')
RX_GETENV_INFRA = re.compile(
    r'os\.getenv\(\s*["\']((?:RVSEC_HOME|ANDROID_HOME|TOOLS_DIR))["\']'
)
RX_DICT_ENVIRON = re.compile(
    r"(?<!\.)\bdict\(\s*os\.environ\b"
)  # exclude patch.dict(os.environ, ...)
RX_ENVIRON_COPY = re.compile(r"\bos\.environ\.copy\(\s*\)")

# Documentation patterns for cross-checks (b) and (c)
RX_RV_NAME_DOC = re.compile(r"\bRV_[A-Z0-9_]+\b")

# Constants registry parser — captures `ENV_NAME = "VALUE"` lines.
RX_ENV_CONSTANT = re.compile(r'^(ENV_[A-Z0-9_]+)\s*=\s*["\']([^"\']+)["\']', re.M)


def _iter_python_files(root: Path) -> list[Path]:
    """Walk a directory tree returning production .py files only.

    Skips: __pycache__, .hypothesis caches, planted-violation fixtures, and any
    `tests/` tree (test files manipulate env via `patch.dict(os.environ, ...)`,
    which is the idiomatic mock pattern and is out of scope for Layer Purity).
    """
    return [
        p
        for p in root.rglob("*.py")
        if "__pycache__" not in p.parts
        and ".hypothesis" not in p.parts
        and "tests" not in p.parts
    ]


def _load_registry() -> dict[str, str]:
    """Return mapping `ENV_NAME -> "RV_NAME"` from constants.py."""
    text = CONSTANTS_FILE.read_text(encoding="utf-8")
    return dict(RX_ENV_CONSTANT.findall(text))


def _check_read_forms(violations: list[str]) -> None:
    """Cross-check (a): every env read goes through ENV_* constants."""
    modules_dir = REPO_ROOT / "modules"
    files = _iter_python_files(modules_dir)

    for path in files:
        is_l5 = str(path).startswith(str(L5_DIR))
        is_l1_allowed = path in L1_ALLOWLIST_FILES
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(REPO_ROOT)

        for line_no, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue

            # Five literal-read forms (RV_*) — never allowed.
            for rx, form in (
                (RX_ENVIRON_GET, "os.environ.get"),
                (RX_ENVIRON_SUB, "os.environ["),
                (RX_GETENV, "os.getenv"),
            ):
                m = rx.search(line)
                if m:
                    var = m.group(1)
                    violations.append(
                        f'{rel}:{line_no}: literal {form}("{var}") — use ENV_* constant from rv_android_core.constants'
                    )

            # L1 infra literals — allowed only inside L1_ALLOWLIST_FILES.
            for rx, form in (
                (RX_ENVIRON_GET_INFRA, "os.environ.get"),
                (RX_ENVIRON_SUB_INFRA, "os.environ["),
                (RX_GETENV_INFRA, "os.getenv"),
            ):
                m = rx.search(line)
                if m and not is_l1_allowed:
                    var = m.group(1)
                    violations.append(
                        f'{rel}:{line_no}: literal {form}("{var}") at non-L1 location — use the appropriate L1 utility (JarResolver, ValidationConfig)'
                    )

            # Wholesale env leak — never allowed outside L5.
            for rx, form in (
                (RX_DICT_ENVIRON, "dict(os.environ)"),
                (RX_ENVIRON_COPY, "os.environ.copy()"),
            ):
                if rx.search(line) and not is_l5:
                    violations.append(
                        f"{rel}:{line_no}: {form} leaks the entire environment past Layer Purity; build an explicit subprocess env instead"
                    )


def _check_doc_to_registry(registry: dict[str, str], violations: list[str]) -> None:
    """Cross-check (b): every RV_* in README/.env.example exists in registry.

    Lines explicitly noting a deprecated/removed/superseded variable
    (e.g., README's "Removed by gh55" list) are skipped — they document
    intentional historical names so operators recognize migration messages.
    """
    rv_in_registry = {value for value in registry.values() if value.startswith("RV_")}
    deprecation_markers = ("removed", "deprecated", "superseded", "supersede")

    for doc_file in (README_FILE, ENV_EXAMPLE_FILE):
        if not doc_file.exists():
            continue  # creation is scheduled in tasks 7.1/7.2; lint is permissive until then
        text = doc_file.read_text(encoding="utf-8")
        # Strip lines that explicitly mark deprecation context before extracting names.
        kept_lines = []
        for line in text.splitlines():
            lower = line.lower()
            if any(marker in lower for marker in deprecation_markers):
                continue
            kept_lines.append(line)
        scan_text = "\n".join(kept_lines)
        for name in set(RX_RV_NAME_DOC.findall(scan_text)):
            if name not in rv_in_registry:
                violations.append(
                    f"{doc_file.relative_to(REPO_ROOT)}: documents `{name}` which has no ENV_* constant in registry"
                )


def _check_registry_to_doc(registry: dict[str, str], violations: list[str]) -> None:
    """Cross-check (c): every ENV_* constant is documented somewhere."""
    docs_text = ""
    for doc_file in (README_FILE, ENV_EXAMPLE_FILE):
        if doc_file.exists():
            docs_text += "\n" + doc_file.read_text(encoding="utf-8")
    if not docs_text.strip():
        # Both docs absent — skip (creation is scheduled in tasks 7.1/7.2).
        return
    for env_name, value in registry.items():
        if value not in docs_text:
            violations.append(
                f'constants.py: {env_name}="{value}" — value not documented in README.md or .env.example'
            )


def main() -> int:
    if not CONSTANTS_FILE.exists():
        print(f"FATAL: registry not found at {CONSTANTS_FILE}", file=sys.stderr)
        return 2

    registry = _load_registry()
    if not registry:
        print(f"FATAL: registry parsed from {CONSTANTS_FILE} is empty", file=sys.stderr)
        return 2

    violations: list[str] = []

    _check_read_forms(violations)
    _check_doc_to_registry(registry, violations)
    _check_registry_to_doc(registry, violations)

    if violations:
        print(f"check_env_vars_drift.py: {len(violations)} violation(s) found:")
        for v in violations:
            print(f"  {v}")
        return 1

    print(f"check_env_vars_drift.py: clean ({len(registry)} ENV_* constants verified)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
