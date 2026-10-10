"""Gate — the distance-pair reduction constants agree in three places (INV-ANA-88).

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

The Java values are read from the source by regex. `test_json_keys.py` runs a
reflection dumper against the deployed jar because key values can be built by
concatenation; these are two integer literals declared on one line each, and
reading the source also catches a source edit that was never rebuilt.
"""

from __future__ import annotations

import re
from pathlib import Path

from aperv_tool.tools.aperv.derive_mop_artifact import DIST_K, DIST_WEIGHED_MAX
from rv_static_analysis.compact import COMPACT_K, COMPACT_WEIGHED_MAX

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
