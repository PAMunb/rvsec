"""Gate — the distance-pair constants agree in three places (INV-ANA-88, INV-ANA-99).

GATOR's compact output keeps, per method, the `targetDistances` pairs at
`d <= weighedMax` and the `k` nearest by `(d, i)`. The same two numbers are
declared three times, each where its owner needs it:

    TargetDistances.COMPACT_WEIGHED_MAX / COMPACT_K   (Java, the producer)
    rv_static_analysis.compact.COMPACT_WEIGHED_MAX / COMPACT_K   (the converter)
    aperv_tool...derive_mop_artifact.DIST_WEIGHED_MAX / DIST_K   (the consumer)

The reduction is exact for the MOP derive only while the producer keeps at
least what the derive reads. If the derive's numbers grew while the producer's
stayed, compact documents would silently lose pairs the derive weighs. Java
cannot import Python and `aperv-tool` cannot be a dependency of
`rv-static-analysis`, so the values are pinned by this test instead of shared
code.

The default distance horizon is declared three times for the same reason:

    TargetDistances.DEFAULT_DIST_MAX   (Java, the horizon of a run given no distMax)
    rv_static_analysis.config.DEFAULT_DIST_MAX   (the reuse check, INV-ANA-102)
    aperv_tool...derive_mop_artifact.DEFAULT_DIST_MAX   (the derive's bound on the cut)

A document without the `distMax` member was computed with that horizon (INV-ANA-99).
If one reader's default drifted from the producer's, it would read such a document
under a horizon it was not computed with: the reuse check would regenerate or reuse
the wrong documents, and the derive would accept or refuse the wrong cuts.

The Java values are read from the source by regex. `test_json_keys.py` runs a
reflection dumper against the deployed jar because key values can be built by
concatenation; these are integer literals declared on one line each, and
reading the source also catches a source edit that was never rebuilt.
"""

from __future__ import annotations

import re
from pathlib import Path

from aperv_tool.tools.aperv.derive_mop_artifact import (
    DEFAULT_DIST_MAX as DERIVE_DEFAULT_DIST_MAX,
)
from aperv_tool.tools.aperv.derive_mop_artifact import (
    DIST_K,
    DIST_WEIGHED_MAX,
)
from rv_static_analysis.compact import COMPACT_K, COMPACT_WEIGHED_MAX
from rv_static_analysis.config import DEFAULT_DIST_MAX as CONFIG_DEFAULT_DIST_MAX

TARGET_DISTANCES_JAVA = (
    Path(__file__).resolve().parents[3]
    / "rvsec"
    / "rvsec-android"
    / "rvsec-gator"
    / "client"
    / "src"
    / "main"
    / "java"
    / "presto"
    / "android"
    / "gui"
    / "clients"
    / "reach"
    / "TargetDistances.java"
)


def _java_int_constant(source: str, name: str) -> int:
    match = re.search(rf"\bstatic\s+final\s+int\s+{name}\s*=\s*(\d+)\s*;", source)
    assert (
        match
    ), f"{name} not declared as a static final int in {TARGET_DISTANCES_JAVA}"
    return int(match.group(1))


def test_reduction_constants_are_equal_in_java_converter_and_derive() -> None:
    source = TARGET_DISTANCES_JAVA.read_text(encoding="utf-8")
    java = (
        _java_int_constant(source, "COMPACT_WEIGHED_MAX"),
        _java_int_constant(source, "COMPACT_K"),
    )
    converter = (COMPACT_WEIGHED_MAX, COMPACT_K)
    derive = (DIST_WEIGHED_MAX, DIST_K)

    assert java == converter == derive, (
        "distance-pair reduction constants drifted (weighedMax, k):\n"
        f"  Java TargetDistances.COMPACT_WEIGHED_MAX/COMPACT_K = {java}\n"
        f"  rv_static_analysis.compact COMPACT_WEIGHED_MAX/COMPACT_K = {converter}\n"
        f"  aperv-tool derive DIST_WEIGHED_MAX/DIST_K = {derive}"
    )


def test_default_horizon_is_equal_in_java_reuse_check_and_derive() -> None:
    source = TARGET_DISTANCES_JAVA.read_text(encoding="utf-8")
    java = _java_int_constant(source, "DEFAULT_DIST_MAX")

    assert java == CONFIG_DEFAULT_DIST_MAX == DERIVE_DEFAULT_DIST_MAX, (
        "default distance horizon drifted:\n"
        f"  Java TargetDistances.DEFAULT_DIST_MAX = {java}\n"
        f"  rv_static_analysis.config.DEFAULT_DIST_MAX = {CONFIG_DEFAULT_DIST_MAX}\n"
        f"  aperv-tool derive DEFAULT_DIST_MAX = {DERIVE_DEFAULT_DIST_MAX}"
    )
