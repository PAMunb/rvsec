"""Containment gate over a golden fixture that once violated it.

Why this file exists
--------------------
`test_reachability_parity.py::test_directly_reaches_target_is_subset_of_reaches_target`
asserts the same invariant (INV-ANA-64: a method that directly calls a
target trivially reaches one, so `directlyReachesTarget ⊆ reachesTarget`)
by running GATOR fresh over `cryptoapp.apk`. That APK has **zero**
violations and always had — so the tripwire passes by luck and is blind
to the very defect gh69 repairs. It would keep passing if the repair
were reverted.

`app.notesr_59.apk` is the counter-example. Before the D8 repair
(seeding the reverse BFS with the direct set instead of unioning the two
sets after the fact), GATOR's output for this APK recorded

    app.notesr.core.security.crypto.AesCryptor.generatePasswordBasedKey
        directlyReachesMop=true, reachesMop=false, reachable=false

— a direct caller of a target that the transitive axis did not mark.
Those are the **pre-gh60 key names**; the run predates the
`reachesMop` → `reachesTarget` rename, which is why a sweep for the
current names finds nothing and why the evidence is easy to miss. The
recorded copies are under `results/gh56-smoke6/app.notesr_59.apk/`,
`results/gh56-smoke6/instrumented_apks/` and `results/gh56-smoke6-ext-v2/`.

The APK itself is 35.4 MB against the 4.0 MB tracked `cryptoapp.apk`, so
committing it to run GATOR fresh is not an option. The fixture here is
the **post-repair** output of a real spark run over it, committed as a
golden.

What this proves, and what it does not
--------------------------------------
It proves the recorded output satisfies containment on an APK that
demonstrably did not before. It does **not** prove a fresh run on an
arbitrary APK does — a golden fixture cannot. The end-to-end half of the
invariant stays with `cryptoapp` and the Java ITs; this file covers the
half `cryptoapp` cannot reach.

Generated with the spark call graph (production's algorithm, and the one
`scripts/check_signature_file_subset.py` uses) via

    uv run python scripts/check_signature_file_subset.py \
        --apk <corpus>/app.notesr_59.apk --workdir /tmp/gh69_notesr

after the phase-4 rebuild. Regenerate the same way if the schema moves.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
GOLDEN_PATH = (
    ROOT
    / "modules"
    / "rv-static-analysis"
    / "tests"
    / "resources"
    / "app.notesr_59.apk.json"
)

# The method the pre-repair run recorded as a containment violation. It is
# named rather than merely counted: a gate that only asserts "zero
# violations" would still pass if this method vanished from the output
# entirely, which would be a different defect wearing the same green.
WITNESS = (
    "<app.notesr.core.security.crypto.AesCryptor: "
    "javax.crypto.SecretKey generatePasswordBasedKey(char[],byte[])>"
)


@pytest.fixture(scope="module")
def methods() -> list[dict]:
    data = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    return [m for cls in data.get("reachability", []) for m in cls.get("methods", [])]


def test_golden_uses_current_key_names(methods: list[dict]) -> None:
    """The fixture must speak the post-gh60 schema, not the legacy one.

    Guards the trap that hid this defect for a year: a fixture written
    with `reachesMop`/`directlyReachesMop` would make every assertion
    below vacuous, since `.get()` on an absent key is falsy.
    """
    assert methods, f"{GOLDEN_PATH.name}: no methods parsed"
    keys = set(methods[0])
    assert {"reachable", "reachesTarget", "directlyReachesTarget"} <= keys, (
        f"{GOLDEN_PATH.name} carries {sorted(keys)}; expected the gh60 key names. "
        "A fixture using reachesMop/directlyReachesMop makes this gate vacuous."
    )
    assert not {"reachesMop", "directlyReachesMop"} & keys


def test_witness_method_is_present_and_contained(methods: list[dict]) -> None:
    """The method that violated containment pre-repair now satisfies it."""
    rows = [m for m in methods if m.get("signature") == WITNESS]
    assert len(rows) == 1, (
        f"expected exactly one row for the witness method, found {len(rows)}. "
        "If it disappeared from the output, that is a regression in its own "
        "right — this gate deliberately fails rather than passing vacuously."
    )
    m = rows[0]
    assert m["directlyReachesTarget"] is True, (
        "the witness must still be a direct caller of a target; if it is not, "
        "the fixture no longer witnesses anything"
    )
    assert m["reachesTarget"] is True, (
        "containment violated on the exact method the pre-repair run reported: "
        "directlyReachesTarget=True with reachesTarget=False"
    )
    # Recorded deliberately: this is the D8 case where the reverse BFS reaches
    # a method SPARK never processed. `reachable=False` alongside
    # `reachesTarget=True` is correct here, not a contradiction.
    assert m["reachable"] is False


def test_containment_holds_over_the_whole_fixture(methods: list[dict]) -> None:
    """INV-ANA-64 over every method in the golden, not just the witness."""
    leak = sorted(
        m["signature"]
        for m in methods
        if m.get("directlyReachesTarget") and not m.get("reachesTarget")
    )
    assert not leak, (
        "directlyReachesTarget MUST be a subset of reachesTarget (INV-ANA-64). "
        f"{len(leak)} method(s) violate it:\n  " + "\n  ".join(leak)
    )
