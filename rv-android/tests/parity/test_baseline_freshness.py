"""Tripwires that catch the two failure modes that hid for 2 months pre-2026-05-26.

Background — see ``openspec/changes/gh60-targets-core/design.md`` §D12 for
the incident. The short version: the in-tree cryptoapp baseline at
``modules/rv-static-analysis/tests/resources/cryptoapp.apk.json`` had its
content frozen at ``4a8a6342 feat(gh45)`` (2026-03-31). It was last touched
by ``4f06e3a9 refactor(gh60): C1f rename MOP→Target``, but that commit
*only renamed JSON keys* — content stayed pre-gh51 (cha CG algorithm) +
pre-gh57 (no ``components``, no ``complete`` sentinel). Production was
already running spark + the new schema. The mismatch was invisible because
the reachability parity gate compared this stale baseline against an
equally-stale ``/tmp/gh60_g_subset/lenient.json`` cache.

These two tests pin the two invariants the previous regime was missing:

1. **Schema currency** — the baseline JSON MUST carry the current schema's
   load-bearing keys (``components`` from gh57, ``complete`` sentinel from
   ADR-6, ``targetMethods`` from C1f and the renamed per-method
   ``reachesTarget`` / ``directlyReachesTarget``). A future revert that
   pulls in a legacy fixture fails this test immediately.

2. **Producer-vs-baseline freshness** — when both the deployed jar and the
   baseline exist locally, ``mtime(baseline) >= mtime(jar)``. A
   ``mvn install`` that produces a new jar without regenerating the
   baseline trips this tripwire so the operator sees the divergence at
   PR-review time rather than months later via a phantom-passing gate.

Skip semantics follow the same ``RV_GATOR_REQUIRED`` contract documented in
the other parity gates: prerequisites missing → ``pytest.skip`` by default,
``pytest.fail`` when the env var is set (so CI / Pedro's local runs cannot
silently miss the test).
"""

from __future__ import annotations

import json
import os
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
JAR_PATH = ROOT / "lib" / "gator" / "rvsec-analysis-client.jar"


def _required_or_skip(reason: str) -> None:
    """Skip-or-fail dispatcher honoring the ``RV_GATOR_REQUIRED`` contract.

    The previous regime treated missing prerequisites as silent success
    (pytest.skip). When ``RV_GATOR_REQUIRED=1`` the gate is meant to
    actually run, so missing prereqs become a hard failure instead.
    """
    if os.environ.get("RV_GATOR_REQUIRED") == "1":
        pytest.fail(f"RV_GATOR_REQUIRED=1 but {reason}")
    pytest.skip(reason)


def test_baseline_has_current_schema() -> None:
    """Baseline JSON must carry the current schema (gh57 + gh60).

    The four invariants checked here are the load-bearing schema markers
    each anchored to a specific change in the schema's history:

    - top-level ``components`` key — gh57 added the components section
      (Activity/Service/Receiver/Provider classification).
    - top-level ``complete: bool`` — gh60 ADR-6 sentinel (the writer
      emits this as the final field on a successful run; absence means
      the file is truncated or a pre-gh60 fixture leaked back in).
    - per-method ``reachesTarget`` + ``directlyReachesTarget`` — gh60 C1f
      rename (legacy: ``reachesMop`` / ``directlyReachesMop``). Pinned
      against the first method of the first reachability entry to keep
      the assertion cheap.

    The top-level ``targetMethods`` key is *defined* in JsonSchema.Keys
    (tasks.md 5.1) but the writer does not emit it yet — that field is
    reserved for the C2/C3 enrichment changes. So this test does NOT
    require ``targetMethods`` to be present; it only enforces that the
    legacy ``mopMethods`` key is absent.
    """
    if not BASELINE_PATH.exists():
        pytest.fail(f"baseline missing at {BASELINE_PATH}")

    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))

    assert "components" in data, (
        "baseline missing top-level 'components' (gh57). Likely a pre-gh57 "
        "fixture leaked back in — regenerate per tasks.md 11.8."
    )
    assert "complete" in data, (
        "baseline missing top-level 'complete' sentinel (gh60 ADR-6). "
        "Either truncated or a pre-gh60 fixture leaked in."
    )
    assert isinstance(data["complete"], bool), (
        f"baseline 'complete' must be boolean, got {type(data['complete']).__name__}"
    )
    assert "mopMethods" not in data, (
        "baseline still carries legacy 'mopMethods' key — C1f rename "
        "incomplete."
    )

    # Sample one method to pin the per-method key rename
    reachability = data.get("reachability") or []
    sample_method = next(
        (m for cls in reachability for m in cls.get("methods", [])),
        None,
    )
    assert sample_method is not None, (
        "baseline 'reachability' has no methods to sample — empty fixture?"
    )
    method_keys = set(sample_method.keys())
    assert "reachesTarget" in method_keys, (
        f"per-method 'reachesTarget' (gh60 C1f) missing — got {sorted(method_keys)}"
    )
    assert "directlyReachesTarget" in method_keys, (
        f"per-method 'directlyReachesTarget' (gh60 C1f) missing — got {sorted(method_keys)}"
    )
    assert "reachesMop" not in method_keys, (
        "per-method legacy 'reachesMop' still present — C1f rename incomplete"
    )


def test_baseline_not_older_than_jar() -> None:
    """Baseline mtime must be ≥ jar mtime when both exist locally.

    The two-month bug this test catches: someone runs ``mvn install`` in
    ``rvsec-gator``, the jar is overwritten with new behavior (e.g., the
    gh51 cha→spark switch), but the in-tree baseline is not regenerated.
    The parity gates then compare a fresh-spark cache against a stale-cha
    baseline; under a normal test run those differ wildly, but if the
    cache itself is also stale (pre-gh51 .m2 snapshot path) both sides
    collapse onto the same legacy era and the gate passes silently.

    Catching the mtime divergence is the cheapest defense — no
    regeneration runs here, the test just looks at filesystem timestamps.
    """
    if not JAR_PATH.exists():
        _required_or_skip(f"jar absent at {JAR_PATH}; nothing to compare against")
        return  # unreachable when _required_or_skip raises, but keeps mypy happy

    if not BASELINE_PATH.exists():
        pytest.fail(f"baseline missing at {BASELINE_PATH}")

    baseline_mtime = BASELINE_PATH.stat().st_mtime
    jar_mtime = JAR_PATH.stat().st_mtime

    assert baseline_mtime >= jar_mtime, (
        f"baseline is older than the deployed jar — likely the jar was rebuilt "
        f"without regenerating the baseline.\n"
        f"  baseline mtime: {baseline_mtime} ({BASELINE_PATH})\n"
        f"  jar      mtime: {jar_mtime} ({JAR_PATH})\n"
        f"  delta: {jar_mtime - baseline_mtime:.1f} s\n"
        f"Regenerate the baseline per gh60 tasks.md 11.8."
    )
