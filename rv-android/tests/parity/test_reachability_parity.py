"""Gates G_paridade_reachability + G_paridade_targets on cryptoapp.

Background
----------
The C1f rename touched 90 files / 1609 insertions and the C1g extraction
shipped a new utility class — both changes risk perturbing the analyser's
output set, even when no signature comparison logic was modified
(class iteration order, hash seeding, JSON section delimiters). The
gates lock the *content* of the reachability set against a baseline
fixture so any future change that silently grows or shrinks the set
trips at PR time, not in the 380-APK sweep weeks later.

Why set equality, not byte equality
-----------------------------------
Per design.md line 414: "Set iteration order changes JSON byte-order
cosmetically → gates compare `set ==` per section, not byte-equivalent
diff." A class count of 27 vs 16 is acceptable noise (GATOR's set
implementation reorganises between builds) as long as the *reachable*
and *reachesTarget* method-signature sets agree exactly.

Baseline fixture
----------------
`modules/rv-static-analysis/tests/resources/cryptoapp.apk.json` —
already in tree, used by the parser unit suite, captures the post-rename
key schema (`reachable`, `reachesTarget`, `directlyReachesTarget`). The
parser-test maintainer keeps it current; this gate piggybacks on that
invariant.

Gates
-----
    G_paridade_reachability — set of method signatures where reachable=True
                              must equal the baseline.
    G_paridade_targets       — set of method signatures where reachesTarget=True
                              must equal the baseline. Implicitly anchors
                              `directlyReachesTarget` too, since it's a
                              strict subset.

Skipped when GATOR can't be invoked (no RVSEC_HOME, no cryptoapp.apk,
jar not deployed).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = (
    ROOT
    / "modules"
    / "rv-static-analysis"
    / "tests"
    / "resources"
    / "cryptoapp.apk.json"
)
GATE_SCRIPT = ROOT / "scripts" / "check_signature_file_subset.py"
JAR_PATH = ROOT / "lib" / "gator" / "rvsec-analysis-client.jar"

# Cache path + freshness check live in the shared helper so the four
# call sites in tests/parity/ + scripts/ cannot drift. See
# `tests/parity/_lenient_cache.py` for the rationale (and
# `openspec/changes/gh60-targets-core/design.md` §D12 for the incident
# that motivated this).
from ._lenient_cache import LENIENT_OUTPUT, ensure_fresh_lenient, required_or_skip


def _signature_set(json_path: Path, flag: str) -> set[str]:
    """Collect method signatures where ``flag`` is True in the JSON file."""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    out: set[str] = set()
    for cls in data.get("reachability", []):
        for m in cls.get("methods", []):
            if m.get(flag):
                out.add(m["signature"])
    return out


def _ensure_fresh_lenient_output() -> Path | None:
    # Cache freshness check is centralised; if the cache predates the
    # deployed jar (or is missing/empty), the helper deletes it and
    # returns None — forcing the fall-through subprocess regeneration
    # below to actually run. This is what protects the gate from the
    # silently-stale-cache failure mode documented in design.md §D12.
    cached = ensure_fresh_lenient(JAR_PATH)
    if cached is not None:
        return cached
    if not os.environ.get("RVSEC_HOME"):
        return None
    proc = subprocess.run(
        [sys.executable, str(GATE_SCRIPT)],
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
    if proc.returncode == 77:
        return None
    if proc.returncode != 0:
        pytest.fail(
            f"gate script exited {proc.returncode}\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return LENIENT_OUTPUT if LENIENT_OUTPUT.exists() else None


@pytest.fixture(scope="module")
def fresh_output() -> Path:
    out = _ensure_fresh_lenient_output()
    if out is None:
        required_or_skip("GATOR prerequisites missing — set RVSEC_HOME + deploy the jar")
    return out


@pytest.fixture(scope="module")
def baseline() -> Path:
    if not BASELINE_PATH.exists():
        # Baseline is a tracked file — its absence is always a real
        # problem, not a missing-environment issue. Fail unconditionally.
        pytest.fail(f"baseline fixture missing at {BASELINE_PATH}")
    return BASELINE_PATH


def _assert_set_equal(fresh: set[str], base: set[str], gate: str) -> None:
    """Symmetric diff with a structured failure message.

    The two sides of the diff (`only_in_fresh`, `only_in_base`) name
    different failure modes:
        - only_in_fresh ≠ ∅ → analyser grew the set (false positives, or
          a legitimate new call site previously missed)
        - only_in_base ≠ ∅ → analyser shrunk the set (false negatives —
          almost always a bug; the rename changed pointer semantics
          somewhere upstream of the matcher)
    """
    only_in_fresh = sorted(fresh - base)
    only_in_base = sorted(base - fresh)
    assert not only_in_fresh and not only_in_base, (
        f"{gate}: cryptoapp set drift\n"
        f"  size: fresh={len(fresh)} baseline={len(base)}\n"
        f"  only in fresh ({len(only_in_fresh)}): {only_in_fresh}\n"
        f"  only in base  ({len(only_in_base)}): {only_in_base}"
    )


def test_reachability_set_matches_baseline(fresh_output: Path, baseline: Path) -> None:
    """G_paridade_reachability — set of `reachable=True` signatures is stable."""
    fresh = _signature_set(fresh_output, "reachable")
    base = _signature_set(baseline, "reachable")
    _assert_set_equal(fresh, base, "G_paridade_reachability")


def test_targets_set_matches_baseline(fresh_output: Path, baseline: Path) -> None:
    """G_paridade_targets — set of `reachesTarget=True` signatures is stable."""
    fresh = _signature_set(fresh_output, "reachesTarget")
    base = _signature_set(baseline, "reachesTarget")
    _assert_set_equal(fresh, base, "G_paridade_targets")


def test_directly_reaches_target_is_subset_of_reaches_target(fresh_output: Path) -> None:
    """Invariant by construction: directly⊆reaches. Tripwire if not."""
    direct = _signature_set(fresh_output, "directlyReachesTarget")
    reaches = _signature_set(fresh_output, "reachesTarget")
    leak = direct - reaches
    assert not leak, (
        "directlyReachesTarget MUST be a subset of reachesTarget — a method "
        "that directly calls a target trivially reaches one. Leak:\n"
        f"  {sorted(leak)}"
    )


def test_baseline_carries_renamed_keys() -> None:
    """Sanity — baseline already uses the gh60 renamed keys.

    Catches a regression where someone reverts the baseline to a pre-gh60
    schema (with `reachesMop` etc); the parity gates would then spuriously
    pass against a stale fixture without exercising the renamed keys.
    """
    if not BASELINE_PATH.exists():
        pytest.skip(f"baseline missing at {BASELINE_PATH}")
    data = json.loads(BASELINE_PATH.read_text())
    sample_method = None
    for cls in data.get("reachability", []):
        if cls.get("methods"):
            sample_method = cls["methods"][0]
            break
    assert sample_method is not None, "baseline has no methods to inspect"
    keys = set(sample_method.keys())
    assert "reachesTarget" in keys, (
        f"baseline missing renamed key 'reachesTarget' (gh60); observed: {sorted(keys)}"
    )
    assert "reachesMop" not in keys, (
        f"baseline still carries legacy key 'reachesMop' — re-export with current GATOR"
    )
