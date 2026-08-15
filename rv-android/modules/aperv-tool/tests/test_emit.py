"""Nothing leaves through ``emit`` that is not an envelope.

The refusal is the point of the module, so the first two tests are the whole
contract: a bare float raises, and the message names ``Envelope``. The rest
check that what does get written keeps the parts an envelope exists to carry —
both denominators in their own columns, the exclusions by identity, and the
convention beside the number.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from aperv_tool.analysis import emit
from aperv_tool.analysis.envelope import Denominator, Envelope, Exclusion


def an_envelope(**overrides) -> Envelope:
    """A complete envelope, with the given fields replaced."""
    fields = {
        "estimand": "detection_rate",
        "n": 40,
        "denominator": Denominator(
            reachable=162, analysed=40, reason="declared 40-application subset"
        ),
        "estimate": {"rate": 0.35},
        "ci": (0.21, 0.51),
        "convention": {"replica_rule": "majority"},
        "exclusions": (
            Exclusion(
                identity="com.ds.avare_404.apk__1__300__aperv:mop_on_llm_off",
                reason="dead identity, three retries",
            ),
        ),
        "provenance_ref": "run-2026-08-15-a",
    }
    fields.update(overrides)
    return Envelope(**fields)  # type: ignore[arg-type]


def read_table(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """The written CSV as a header and a list of row mappings."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def test_bare_float_rejected(tmp_path: Path) -> None:
    """The call that actually gets written — a naked number — is refused."""
    with pytest.raises(TypeError, match="Envelope"):
        emit.table(0.4472, tmp_path / "out.csv")  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="Envelope"):
        emit.table([0.4472], tmp_path / "out.csv")  # type: ignore[list-item]

    assert not (tmp_path / "out.csv").exists()


def test_bare_float_rejected_by_the_figure_emitter(tmp_path: Path) -> None:
    """The figure path performs the same refusal, and never reaches the renderer."""
    drawn: list[Path] = []

    with pytest.raises(TypeError, match="Envelope"):
        emit.figure(
            [0.4472],  # type: ignore[list-item]
            tmp_path / "out.png",
            render=lambda envelopes, dest: drawn.append(dest),
        )

    assert drawn == []


def test_single_envelope_is_not_a_sequence_of_them(tmp_path: Path) -> None:
    """A lone envelope is a common slip and gets a message that says what to do."""
    with pytest.raises(TypeError, match="wrap it in a list"):
        emit.table(an_envelope(), tmp_path / "out.csv")  # type: ignore[arg-type]


def test_table_carries_both_denominators(tmp_path: Path) -> None:
    """A fraction reaches the file beside the two counts it was computed against."""
    dest = emit.table([an_envelope()], tmp_path / "results" / "out.csv")

    header, rows = read_table(dest)
    assert "reachable" in header and "analysed" in header
    assert rows[0]["reachable"] == "162"
    assert rows[0]["analysed"] == "40"
    assert rows[0]["denominator_reason"] == "declared 40-application subset"
    assert rows[0]["estimate.rate"] == "0.35"


def test_table_lists_exclusions_by_identity(tmp_path: Path) -> None:
    """Attrition travels with the table, not in a log beside it."""
    dest = emit.table([an_envelope()], tmp_path / "out.csv")

    _, rows = read_table(dest)
    assert rows[0]["exclusions"] == (
        "com.ds.avare_404.apk__1__300__aperv:mop_on_llm_off: "
        "dead identity, three retries"
    )
    assert rows[0]["convention"] == "replica_rule=majority"
    assert rows[0]["provenance_ref"] == "run-2026-08-15-a"


def test_estimate_columns_are_prefixed_and_unioned(tmp_path: Path) -> None:
    """Mixed estimands share one stable column set, and cannot collide with ``n``."""
    paired = an_envelope(
        estimand="mcnemar_exact",
        estimate={"b": 3, "c": 1, "n_disc": 4, "n": 40, "direction": "b>c"},
        ci=None,
    )
    dest = emit.table([an_envelope(), paired], tmp_path / "out.csv")

    header, rows = read_table(dest)
    assert header.count("n") == 1
    assert "estimate.n" in header and "estimate.rate" in header
    assert rows[0]["estimate.n_disc"] == ""
    assert rows[1]["estimate.n_disc"] == "4"
    assert rows[1]["ci_low"] == "" and rows[1]["ci_high"] == ""
    assert rows[0]["ci_low"] == "0.21"


def test_figure_hands_the_envelopes_to_the_renderer(tmp_path: Path) -> None:
    """The renderer gets envelopes, so a caption can still name the convention."""
    seen: list[tuple[str, ...]] = []

    dest = emit.figure(
        [an_envelope()],
        tmp_path / "figures" / "out.png",
        render=lambda envelopes, path: seen.append(
            tuple(item.convention["replica_rule"] for item in envelopes)
        ),
    )

    assert seen == [("majority",)]
    assert dest.parent.is_dir()
