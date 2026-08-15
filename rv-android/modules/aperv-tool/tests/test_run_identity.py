"""The run identity is parsed in one place, and an unknown arm is an error.

Two of these tests are ordinary unit tests and one is structural. The structural
one — ``test_regex_declared_once`` — is the point of the module: the pattern was
copied into two readers before ``run_identity`` existed, and nothing would have
reported the copies drifting apart. A grep over the package's own source is the
only check that survives a future author adding a third copy "just for now".
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fixture_gate import CMP162_MANIFEST

from aperv_tool.analysis import run_identity
from aperv_tool.analysis.run_identity import (
    RunKey,
    UnknownArm,
    arm_label,
    decompose_arm,
    parse_run_filename,
    try_parse_run_filename,
)

PACKAGE = Path(run_identity.__file__).resolve().parent

# cmp162's roster. Supplied as data everywhere it is used, including here.
CMP162_ARMS = {
    "ape": ("ape", ""),
    "aperv:mop_off_llm_off": ("aperv", "mop_off_llm_off"),
    "aperv:mop_on_llm_off": ("aperv", "mop_on_llm_off"),
}


def test_regex_declared_once() -> None:
    """The identity pattern occurs exactly once under ``analysis/`` (INV-CAN-01)."""
    needle = "__(?P<repetition>"
    holders = [
        path.relative_to(PACKAGE)
        for path in sorted(PACKAGE.rglob("*.py"))
        if needle in path.read_text()
    ]
    assert holders == [Path("run_identity.py")], (
        "the run-identity regex must exist only in run_identity.py; found in "
        f"{holders}"
    )


def test_arm_label_declared_once() -> None:
    """``arm_label`` is defined exactly once under ``analysis/``.

    It was written twice — ``tasks_record`` and ``liveness``, byte-equal, by two
    authors who could not see each other's file. Byte-equal is the harmless half of
    the failure; the harmful half is the day one of them learns about a new arm and
    the other does not, and the two halves of the analysis disagree about which runs
    exist without either raising.
    """
    needle = "def arm_label("
    holders = [
        path.relative_to(PACKAGE)
        for path in sorted(PACKAGE.rglob("*.py"))
        if needle in path.read_text()
    ]
    assert holders == [Path("run_identity.py")], (
        "arm_label must be defined only in run_identity.py; found in " f"{holders}"
    )


def test_arm_label_consumers_import_the_seat() -> None:
    """``tasks_record`` and ``liveness`` reach the label by import, not by copy."""
    for module in ("tasks_record.py", "liveness.py"):
        source = (PACKAGE / module).read_text()
        assert "arm_label" in source, f"{module} no longer uses arm_label"
        assert (
            "from aperv_tool.analysis.run_identity import" in source
        ), f"{module} does not import the run-identity seat"


def test_arm_label_collapses_the_builtin_ape() -> None:
    """``ape`` loses its ``default`` variant; every other arm keeps its pair.

    The collapse is not cosmetic: ``ape:default`` matches nothing in the ``tool``
    column of the consolidated CSVs, so the whole arm reads as never executed.
    """
    assert arm_label("ape", "default") == "ape"
    assert arm_label("ape", None) == "ape"
    assert arm_label("aperv", "mop_on_llm_off") == "aperv:mop_on_llm_off"
    assert arm_label("droidbot", "bfs_greedy") == "droidbot:bfs_greedy"


def test_arm_label_round_trips_through_decompose() -> None:
    """Composition and decomposition agree over the campaign's own roster."""
    for arm, (tool, variant) in CMP162_ARMS.items():
        assert decompose_arm(arm, CMP162_ARMS) == (tool, variant)
        assert arm_label(tool, variant or "default") == arm


def test_shipped_readers_resolve_through_the_single_seat() -> None:
    """``coverage_dump`` and ``clock_logcat_join`` import it rather than re-deriving."""
    for module in ("coverage_dump.py", "clock_logcat_join.py"):
        source = (PACKAGE / module).read_text()
        assert (
            "from aperv_tool.analysis.run_identity import" in source
        ), f"{module} does not import the run-identity seat"


def test_parses_a_run_artefact_name() -> None:
    """The four fields come back typed, with the arm kept whole."""
    key = parse_run_filename(
        Path(
            "/anywhere/app.eduroam.geteduroam_2685.apk__2__300__aperv:mop_on_llm_off.trace"
        )
    )
    assert key == RunKey(
        apk="app.eduroam.geteduroam_2685.apk",
        repetition=2,
        timeout_s=300,
        arm="aperv:mop_on_llm_off",
    )
    assert str(key) == "app.eduroam.geteduroam_2685.apk__2__300__aperv:mop_on_llm_off"


def test_logcat_and_bare_identity_parse_the_same() -> None:
    """A run's three names are one identity — that is what makes them joinable."""
    stem = "com.ds.avare_404.apk__1__300__aperv:mop_on_llm_off"
    assert (
        parse_run_filename(f"{stem}.trace")
        == parse_run_filename(f"{stem}.logcat")
        == parse_run_filename(stem)
    )


def test_timeout_keeps_two_budgets_disjoint() -> None:
    """The same application and arm at two budgets are two identities, not one."""
    at_60 = parse_run_filename("app.pachli_50.apk__1__60__ape.trace")
    at_300 = parse_run_filename("app.pachli_50.apk__1__300__ape.trace")
    assert at_60 != at_300
    assert (at_60.timeout_s, at_300.timeout_s) == (60, 300)


def test_foreign_name_raises_naming_the_basename() -> None:
    """A hand-named file is an error the caller can act on, not a silent None."""
    with pytest.raises(ValueError, match="notes.txt"):
        parse_run_filename("/tmp/notes.txt")


def test_try_parse_returns_none_for_a_foreign_name() -> None:
    """The readers' form: unattributable, still readable, never dropped (INV-APV-37)."""
    assert try_parse_run_filename("/tmp/notes.txt") is None


def test_unknown_arm_raises() -> None:
    """``decompose_arm`` refuses to guess, and names what it knows (INV-CAN-02)."""
    with pytest.raises(UnknownArm) as caught:
        decompose_arm("droidbot:bfs_greedy", CMP162_ARMS)
    message = str(caught.value)
    assert "droidbot:bfs_greedy" in message
    assert "aperv:mop_on_llm_off" in message


def test_unknown_arm_is_not_split_on_the_colon() -> None:
    """The plausible wrong answer is the one this must not return.

    Splitting on the first colon yields ``("droidbot", "bfs_greedy")`` for the
    string above — correct today, and correct-looking for every typo ever passed
    to it, which is how an arm disappears from an analysis while the counts still
    look reasonable.
    """
    with pytest.raises(UnknownArm):
        decompose_arm("droidbot:bfs_greedy", CMP162_ARMS)

    table = dict(CMP162_ARMS, **{"droidbot:bfs_greedy": ("droidbot", "bfs_greedy")})
    assert decompose_arm("droidbot:bfs_greedy", table) == ("droidbot", "bfs_greedy")


def test_arm_without_variant_decomposes_to_an_empty_variant() -> None:
    """``ape`` carries no variant; the pair stays two strings so a groupby has no null."""
    assert decompose_arm("ape", CMP162_ARMS) == ("ape", "")


def test_cmp162_arm_strings_with_colon() -> None:
    """Every arm cmp162 wrote round-trips, colon and underscores intact.

    The naive ``split('_')`` that this module exists to prevent fails visibly here:
    ``aperv:mop_on_llm_off`` would decompose into six fragments, and the paired
    columns are named ``{arm}__{metric}``, so the damage would land in the column
    labels rather than raising.
    """
    manifest = (
        json.loads(CMP162_MANIFEST.read_text()) if CMP162_MANIFEST.exists() else None
    )
    arms = manifest["facts"]["arms"] if manifest else sorted(CMP162_ARMS)
    assert set(arms) == set(CMP162_ARMS)

    for arm in arms:
        key = parse_run_filename(f"some.app_1.apk__3__300__{arm}.trace")
        assert key.arm == arm, f"arm mangled: {arm} -> {key.arm}"
        assert decompose_arm(key.arm, CMP162_ARMS)[0] in {"ape", "aperv"}


def test_ndjson_gz_is_not_treated_as_a_run_artefact() -> None:
    """``.trace.ndjson.gz`` is a gzip of its sibling, never a second stream.

    Stripping only ``.trace`` and ``.logcat`` means the gz name does not parse as
    an identity, so a directory walk that collects identities cannot count a run
    twice — about 1.5 GB of a campaign is this redundancy.
    """
    gz = parse_run_filename(
        "app.pachli_50.apk__1__300__aperv:mop_on_llm_off.trace.ndjson.gz"
    )
    trace = parse_run_filename("app.pachli_50.apk__1__300__aperv:mop_on_llm_off.trace")
    assert gz.arm == "aperv:mop_on_llm_off.trace.ndjson.gz"
    assert gz != trace, "the gzip sibling must not resolve to the run's identity"
