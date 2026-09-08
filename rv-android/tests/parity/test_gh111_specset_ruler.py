"""The `jca` / `jca_android` sanity ruler stays measured (gh111, task 7.1).

`modules/rv-static-analysis/CLAUDE.md` offers a pair of numbers per specification
set — the `Loaded N MOP signatures` line GATOR prints, and the distinct
`(class, method)` target count behind it — for one purpose: confirming *which
set* a run loaded. It carried the pre-gh105 figures for `jca_android` (119/67)
long after the set had grown from 23 to 48 `.mop` files, an error of 74%. A ruler
that names the wrong set is worse than no ruler, because it is consulted precisely
when something looks wrong. Re-measured on 2026-09-08 through the same
`MopSpecsTargetSource.load()` the GATOR run calls: `jca` 122/70 and `jca_android`
212/115, the latter at 47 files since a599be6b removed `RandomStringPassword.mop`
and with it the two STRICT signatures over `java.lang.String`.

The signature counts themselves need the extractor's own owner resolution to
reproduce exactly, so what is pinned here is the half that moves for free and
moves first: the **file count** of each set. Every historical change to these
numbers came with a change to that count, and a set that gains or loses a `.mop`
is a set whose ruler is stale until someone re-measures it.

The check is conditional on `RVSEC_HOME`: the specification sets live in the
sibling Java reactor, not in this repository, so CI without it skips loudly
rather than failing for the absence of a tree it never checked out.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

# What the ruler in modules/rv-static-analysis/CLAUDE.md is anchored to.
EXPECTED_MOP_FILES = {"jca": 23, "jca_android": 47}

CLAUDE_MD = (
    Path(__file__).resolve().parents[2]
    / "modules/rv-static-analysis/CLAUDE.md"
)


def _spec_dir(spec_set: str) -> Path:
    root = os.environ.get("RVSEC_HOME")
    if not root:
        pytest.skip("RVSEC_HOME is unset — the specification sets are not checked out")
    return Path(root) / "rvsec/rvsec-mop/src/main/resources" / spec_set


@pytest.mark.parametrize("spec_set,expected", sorted(EXPECTED_MOP_FILES.items()))
def test_the_set_still_has_the_size_the_ruler_assumes(spec_set, expected):
    directory = _spec_dir(spec_set)
    if not directory.is_dir():
        pytest.skip(f"{directory} is absent")

    actual = len(list(directory.glob("*.mop")))

    assert actual == expected, (
        f"'{spec_set}' now holds {actual} .mop files, not {expected}. The "
        "sanity ruler in modules/rv-static-analysis/CLAUDE.md is stale until "
        "someone re-measures 'Loaded N MOP signatures' and the distinct "
        "(class, method) count for this set."
    )


def test_the_ruler_carries_the_measured_figures():
    """The exact pair the ruler must carry, so a revert to a stale one is visible.

    Both stale pairs this file has replaced are named negatively below: 119/67 was
    pre-gh105 and 207/113 was pre-a599be6b. Asserting their absence as well as the
    current pair's presence is what makes a revert fail here rather than pass by
    matching nothing.
    """
    text = CLAUDE_MD.read_text(encoding="utf-8")

    assert "`jca_android` prints **212** and seeds **115**" in text
    assert "119 and seeds 67" not in text
    assert "prints **207** and seeds **113**" not in text
