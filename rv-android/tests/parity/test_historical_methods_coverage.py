"""Tripwires anchored to an independent 2025-01-09 static-analysis run.

The historical evidence lives at::

    /home/pedro/desenvolvimento/RV_ANDROID/ALL_METHODS/cryptoapp.apk.methods

That CSV was produced by a separate toolchain that predates the gh27
GATOR unification — an entirely different code path. Using it here gives
us *independent* evidence that the regenerated cryptoapp baseline is not
silently missing structural app coverage.

Two invariants the manual cross-check on 2026-05-26 surfaced:

1. **All 8 classes the historical analyzer saw are still present.** The
   current pipeline may legitimately *add* classes (e.g.
   ``CryptographyActivity`` was added to the cryptoapp source after
   2025-01-09; the ``databinding.*Binding`` family arrived with the
   ViewBinding migration) but it MUST NOT *lose* a class. Class-level
   loss would indicate a filter regression (e.g. accidentally extending
   the gh57 R$* exclusion to real app code).

2. **All 3 methods the historical analyzer marked ``use_jca=True``
   are ``directlyReachesTarget=True`` in the current baseline.** This is
   the load-bearing crypto-detection invariant. The bytecode-scan path
   (D7) was specifically designed to be CG-independent, so any future
   change that re-routes JCA detection through a less reliable path
   would surface here. The three methods are
   ``MessageDigestUtil.hash``, ``CipherUtil.aes``, ``CipherUtil.des``.

Out of scope (registered but not enforced):
- Method-by-method reachable agreement — diverges by design (10 spark
  improvements, 5 spark precision-related losses; documented in design
  D12). Encoding this as a hard assertion would create churn whenever
  the call-graph algorithm or callback complement legitimately evolves.
- Constructor / SDK-callsite coverage — old toolchain flattened
  ``(class, method)`` differently; cannot be compared without semantic
  translation.

If the historical file ever disappears (e.g. machine reprovisioning),
this test SKIPs with a clear message — it is anchored to a specific
machine path because the original artifact is not in the repo.
"""

from __future__ import annotations

import csv
import json
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
HISTORICAL_PATH = Path(
    "/home/pedro/desenvolvimento/RV_ANDROID/ALL_METHODS/cryptoapp.apk.methods"
)


def _load_historical() -> list[dict[str, str]]:
    if not HISTORICAL_PATH.exists():
        pytest.skip(
            f"historical static-analysis file missing at {HISTORICAL_PATH} "
            "(this gate anchors to an off-repo artifact; cannot run on a "
            "machine without the 2025-01-09 evidence)"
        )
    with open(HISTORICAL_PATH, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _load_baseline() -> dict:
    if not BASELINE_PATH.exists():
        pytest.fail(f"baseline missing at {BASELINE_PATH}")
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def test_all_historical_classes_present_in_baseline() -> None:
    """Every class the 2025-01-09 toolchain saw MUST still be in the baseline.

    The current pipeline may add classes (legitimate evolution of the
    cryptoapp source between 2025-01-09 and today) but it MUST NOT lose
    one. Loss would flag a filter regression.
    """
    historical = _load_historical()
    baseline = _load_baseline()

    historical_classes = {row["class"] for row in historical}
    baseline_classes = {cls["className"] for cls in baseline["reachability"]}

    missing = historical_classes - baseline_classes
    assert not missing, (
        "structural regression — the 2025-01-09 historical analyzer saw "
        "these classes that the current pipeline does not:\n  "
        + "\n  ".join(sorted(missing))
    )


def test_historical_jca_usage_maps_to_directly_reaches_target() -> None:
    """The 3 historical ``use_jca=True`` methods MUST be ``directlyReachesTarget=True``.

    Crypto detection is the load-bearing invariant of the whole pipeline.
    This is independent confirmation from a tool that predates GATOR
    unification — if it disagrees with the current pipeline on these
    three methods, the current pipeline is wrong (the historical tool
    had cryptoapp's JCA usage right; cryptoapp's source for these
    methods has not changed).
    """
    historical = _load_historical()
    baseline = _load_baseline()

    jca_methods = [
        (row["class"], row["method"])
        for row in historical
        if row["use_jca"].lower() == "true"
    ]
    assert jca_methods, (
        "historical file has no use_jca=True rows — either the file is "
        "corrupted or its schema changed since 2026-05-26"
    )

    # Index current baseline by (class, name); a method MAY have multiple
    # overloads, so collect the disjunction (any overload directlyReaches → True).
    current: dict[tuple[str, str], bool] = {}
    for cls in baseline["reachability"]:
        for m in cls.get("methods", []):
            key = (cls["className"], m["name"])
            current[key] = current.get(key, False) or bool(
                m.get("directlyReachesTarget")
            )

    failures: list[str] = []
    for cls, name in jca_methods:
        observed = current.get((cls, name))
        if observed is None:
            failures.append(f"  {cls}.{name}: MISSING in current baseline")
        elif not observed:
            failures.append(
                f"  {cls}.{name}: historical use_jca=True but current "
                f"directlyReachesTarget=False — JCA detection regression"
            )

    assert not failures, (
        "JCA-usage detection regression vs 2025-01-09 toolchain:\n"
        + "\n".join(failures)
    )
