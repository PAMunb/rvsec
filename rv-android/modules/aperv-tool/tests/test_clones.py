"""Nothing collapses silently, and nothing collapses that was not declared.

Two properties are worth a test each. The first is that a fold happens at all and
is attributed — member, survivor, family, reason. The second is its complement,
and the one a clone rule usually gets wrong: an application the map never mentions
must come out of the collapse byte-identical, including its rows, because a fold
rule that touches the unmapped is a scoping decision nobody declared.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from aperv_tool.analysis.clones import CloneFamily, collapse, read_clone_map

SURVIVOR = "com.ds.avare_404.apk"
FOLDED = "com.ds.avare_405.apk"
UNMAPPED = "io.keepalive.android_133.apk"

FAMILY = CloneFamily(
    name="avare",
    survivor=SURVIVOR,
    members=frozenset({SURVIVOR, FOLDED}),
    reason="same upstream program, version bump only; the lower build is kept",
)


def frame() -> pd.DataFrame:
    """Two runs each of the survivor, the folded member and an unmapped app."""
    return pd.DataFrame(
        [
            {"apk": application, "repetition": repetition, "steps": 10 + repetition}
            for application in (SURVIVOR, FOLDED, UNMAPPED)
            for repetition in range(2)
        ]
    )


def test_clone_collapse() -> None:
    """The folded member is relabelled and its survival is attributed."""
    collapsed, report = collapse(frame(), [FAMILY])

    assert set(collapsed["apk"]) == {SURVIVOR, UNMAPPED}
    assert report.before.cardinality == 3
    assert report.after.cardinality == 2

    (record,) = report.collapses
    assert (record.member, record.survivor, record.family) == (
        FOLDED,
        SURVIVOR,
        "avare",
    )
    assert record.reason == FAMILY.reason

    text = report.report()
    assert FOLDED in text and SURVIVOR in text and FAMILY.reason in text
    assert "|3∖2| = 1" in text


def test_collapse_is_counted() -> None:
    """The number of folded applications and of moved rows is reported."""
    collapsed, report = collapse(frame(), [FAMILY])

    assert report.collapsed == 1
    assert report.rows_relabelled == 2
    assert len(collapsed) == len(frame())
    assert int((collapsed["apk"] == SURVIVOR).sum()) == 4

    empty_map: list[CloneFamily] = []
    _, untouched = collapse(frame(), empty_map)
    assert untouched.collapsed == 0
    assert untouched.rows_relabelled == 0
    assert untouched.before.members == untouched.after.members


def test_unmapped_application_survives_unchanged() -> None:
    """An application outside the map keeps its id and all of its rows."""
    original = frame()
    collapsed, report = collapse(original, [FAMILY])

    kept = collapsed[collapsed["apk"] == UNMAPPED].reset_index(drop=True)
    expected = original[original["apk"] == UNMAPPED].reset_index(drop=True)
    pd.testing.assert_frame_equal(kept, expected)

    assert UNMAPPED not in {record.member for record in report.collapses}
    assert list(original["apk"]) == [SURVIVOR] * 2 + [FOLDED] * 2 + [UNMAPPED] * 2


def test_clone_map_is_read_from_a_file(tmp_path: Path) -> None:
    """The declaration round-trips through the JSON form callers supply."""
    path = tmp_path / "clone_map.json"
    path.write_text(
        json.dumps(
            [
                {
                    "family": FAMILY.name,
                    "survivor": FAMILY.survivor,
                    "members": sorted(FAMILY.members),
                    "reason": FAMILY.reason,
                }
            ]
        ),
        encoding="utf-8",
    )

    assert read_clone_map(path) == (FAMILY,)

    _, report = collapse(frame(), path)
    assert report.collapsed == 1


def test_a_family_cannot_claim_a_member_twice() -> None:
    """Overlapping families would make the fold order decide the result."""
    other = CloneFamily(
        name="avare-fork",
        survivor=FOLDED,
        members=frozenset({FOLDED, UNMAPPED}),
        reason="fork of the same program",
    )

    with pytest.raises(ValueError, match="claimed by families"):
        collapse(frame(), [FAMILY, other])

    with pytest.raises(ValueError, match="not one of its members"):
        CloneFamily(
            name="stray",
            survivor=UNMAPPED,
            members=frozenset({SURVIVOR}),
            reason="declared wrongly",
        )
