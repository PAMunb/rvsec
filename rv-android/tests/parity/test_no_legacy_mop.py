"""Planted-violation tests for `scripts/check_no_legacy_mop.py` (gh60 INV-ANA-37).

Each test exercises a single regex from FORBIDDEN_PATTERNS by writing a
temporary fixture into a fake `modules/` subtree under `tmp_path`, pointing
the scanner at that root, and asserting the expected outcome. Importing
the scanner module directly (rather than spawning a subprocess) lets the
fixtures isolate one matcher at a time.

The end-to-end "the real repo is clean" assertion lives in `test_repo_is_clean`
at the bottom — that one runs the scanner against the actual repo root.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "check_no_legacy_mop.py"


def _load_scanner():
    spec = importlib.util.spec_from_file_location("_check_no_legacy_mop", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["_check_no_legacy_mop"] = module
    spec.loader.exec_module(module)
    return module


scanner = _load_scanner()


def _fake_root(tmp_path: Path) -> Path:
    """Build the directory layout the scanner expects under tmp_path.

    Mirrors the three SCAN_ROOTS (modules/, scripts/, ../rvsec/.../rvsec-gator)
    so a fixture can plant a violation in any of them and the scanner sees
    it through the same code path the real repo would hit.
    """
    (tmp_path / "modules").mkdir()
    (tmp_path / "scripts").mkdir()
    gator = tmp_path.parent / "rvsec" / "rvsec-android" / "rvsec-gator"
    gator.mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture
def root(tmp_path: Path) -> Path:
    # tmp_path resolves to a fresh directory per test, so the sibling
    # `../rvsec/.../rvsec-gator` walk lands inside the pytest tmpdir tree.
    yield _fake_root(tmp_path)


# ── positive: each forbidden token is detected ──────────────────────────

@pytest.mark.parametrize(
    "token",
    [
        "reaches_mop",
        "reachesMop",
        "directly_reaches_mop",
        "directlyReachesMop",
        "mop_methods",
        "mopMethods",
        "MopReachability",
        "findDirectMopCallersByBytecodeScan",
        "NReachesMop",
        "ReachesMopNode",
    ],
)
def test_each_forbidden_token_is_detected(root: Path, token: str) -> None:
    """Each FORBIDDEN_PATTERNS entry must flag a planted violation."""
    target = root / "modules" / "violation.py"
    target.write_text(f"value = obj.{token}\n", encoding="utf-8")

    findings = scanner.scan(root)

    assert any(f.token == token for f in findings), (
        f"expected the scanner to detect {token!r} in modules/violation.py; "
        f"got {findings!r}"
    )


# ── negative: allowlisted contexts must NOT flag ────────────────────────

def test_backup_dir_under_module_is_allowlisted(root: Path) -> None:
    """`/backup/` substring must shield historical archives at any depth."""
    p = root / "modules" / "rv-android-core" / "backup" / "old.py"
    p.parent.mkdir(parents=True)
    p.write_text("reaches_mop = True\n", encoding="utf-8")

    assert scanner.scan(root) == []


def test_rv_agent_module_is_allowlisted(root: Path) -> None:
    """rv-agent is deprecated — its legacy MOP names are out of scope."""
    p = root / "modules" / "rv-agent" / "src" / "leftover.py"
    p.parent.mkdir(parents=True)
    p.write_text("def reachesMop(self): ...\n", encoding="utf-8")

    assert scanner.scan(root) == []


def test_mopspecstargetsource_filename_is_allowlisted(root: Path) -> None:
    """The MOP→Target adapter legitimately references upstream types."""
    p = root / "modules" / "src" / "MopSpecsTargetSource.java"
    p.parent.mkdir(parents=True)
    p.write_text("Set<MopMethod> mopMethods = facade.listUsedMethods(...);\n", encoding="utf-8")

    assert scanner.scan(root) == []


def test_upstream_rvsec_mop_module_is_allowlisted(root: Path) -> None:
    """Upstream rvsec-mop modules keep their original names."""
    p = root.parent / "rvsec" / "rvsec-mop" / "Foo.java"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("class MopReachability { }\n", encoding="utf-8")

    assert scanner.scan(root) == []


def test_word_boundary_protects_target_substring(root: Path) -> None:
    """`MopSpecsTargetSource` contains "Mop" but must not match `\\bMop…\\b`.

    Regression guard: an earlier draft tried `re.compile(r"Mop")` which
    flagged every MopSpecsTargetSource reference. The whole-word patterns
    in FORBIDDEN_PATTERNS sidestep this; the test plants a legitimate
    reference to MopSpecsTargetSource and asserts it stays unflagged.
    """
    p = root / "modules" / "client.py"
    p.write_text("from rvsec import MopSpecsTargetSource  # adapter import\n", encoding="utf-8")

    assert scanner.scan(root) == []


def test_pycache_is_skipped(root: Path) -> None:
    """`__pycache__` substring path must be skipped (binary noise)."""
    p = root / "modules" / "pkg" / "__pycache__" / "stale.cpython-313.pyc"
    p.parent.mkdir(parents=True)
    # Write text so the scanner can read it; the real .pyc would be binary
    # and the SOURCE_EXTENSIONS filter would also skip it. This test guards
    # the substring rule (defence in depth).
    p.write_text("reaches_mop garbage\n", encoding="utf-8")

    # SOURCE_EXTENSIONS filters out .pyc anyway, so this is doubly safe.
    assert scanner.scan(root) == []


# ── extension filter ────────────────────────────────────────────────────

def test_binary_extension_is_ignored(root: Path) -> None:
    """A .jar / .png / .json file must not be scanned."""
    p = root / "modules" / "blob.jar"
    p.write_bytes(b"reaches_mop\x00binary-garbage")

    assert scanner.scan(root) == []


# ── end-to-end: the real repo is clean ──────────────────────────────────

def test_repo_is_clean() -> None:
    """Live invariant — the actual rv-android repo passes G_no_legacy_mop.

    Skips if the rvsec-gator sibling tree is missing (avoids flaking the
    test on a checkout that only includes rv-android).
    """
    rv_android_root = Path(__file__).resolve().parents[2]
    gator_root = rv_android_root.parent / "rvsec" / "rvsec-android" / "rvsec-gator"
    if not gator_root.exists():
        pytest.skip(f"rvsec-gator sibling tree missing at {gator_root}")

    findings = scanner.scan(rv_android_root)
    assert findings == [], "\n".join(
        f"{f.path}:{f.line}: {f.token}  |  {f.snippet}" for f in findings
    )
