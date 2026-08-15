"""The catalogue, the two example callers, and the hole the report must show.

The load-bearing test here is ``test_uncovered_entries_listed``. A catalogue is
written from the pre-registration before anything is wired, so an entry with no
caller is the normal early state — and indistinguishable, from outside, from a
question that was quietly dropped. The report is what tells the two apart, and a
report that silently omitted the hole would be worse than none.

The second theme is the freeze-item rule crossing the configuration boundary.
``E19`` is in the catalogue with three knobs deliberately absent because the
author has not fixed them; the tests assert it *raises* rather than running. A
catalogue that filled them with something plausible would produce a number under
parameters nobody decided, which is the whole failure the rule exists against.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from aperv_tool.analysis.callers import (
    NONE_IN_TOML,
    RQ_MAP,
    Entry,
    UnknownEntry,
    count_model,
    coverage,
    entry,
    load,
    paired_detection,
)
from aperv_tool.analysis.corpus import FreezeItemUnset
from aperv_tool.analysis.envelope import Envelope


def catalogue_entry(**overrides) -> Entry:
    """A minimal entry, with the fields under test overridden."""
    fields = {
        "entry_id": "E99",
        "question": "a question",
        "builder": "builder",
        "estimator": "estimator",
        "caller": None,
        "parameters": {},
    }
    fields.update(overrides)
    return Entry(**fields)


def paired_frame() -> pd.DataFrame:
    """Two arms over four applications, three replicas, one discordant pair."""
    rows = []
    # `only_guided` fires under the guided arm alone; `only_control` the reverse;
    # `both` and `neither` are concordant and carry no information about the
    # difference. One discordant pair each way is the smallest table that gives
    # every field of the envelope something to say.
    counts = {
        "only_guided.apk": {"aperv:mop_on_llm_off": 3, "aperv:mop_off_llm_off": 0},
        "only_control.apk": {"aperv:mop_on_llm_off": 0, "aperv:mop_off_llm_off": 2},
        "both.apk": {"aperv:mop_on_llm_off": 5, "aperv:mop_off_llm_off": 4},
        "neither.apk": {"aperv:mop_on_llm_off": 0, "aperv:mop_off_llm_off": 0},
    }
    for apk, per_arm in counts.items():
        for arm, value in per_arm.items():
            for replica in (1, 2, 3):
                rows.append(
                    {
                        "apk": apk,
                        "arm": arm,
                        "rep": replica,
                        "timeout_s": 300,
                        "mop_errors_unique": value,
                    }
                )
    return pd.DataFrame(rows)


def count_frame() -> pd.DataFrame:
    """A count frame with an arm factor, a cluster and a log-scale size column."""
    generator = np.random.default_rng(20260815)
    rows = []
    for index in range(24):
        apk = f"app_{index}.apk"
        log_size = float(np.log(1_000 + 500 * index))
        for arm, rate in (
            ("aperv:mop_off_llm_off", 1.0),
            ("aperv:mop_on_llm_off", 1.4),
        ):
            rows.append(
                {
                    "apk": apk,
                    "arm": arm,
                    "log_apk_size": log_size,
                    "distinct_signatures": int(
                        generator.poisson(rate * np.exp(log_size) / 400.0)
                    ),
                }
            )
    return pd.DataFrame(rows)


class TestCatalogue:
    """The file is data, and reading it must not require running it."""

    def test_shipped_catalogue_loads(self) -> None:
        """Every shipped entry carries the three fields that make it readable."""
        entries = load()

        assert entries, "the shipped catalogue is empty"
        for row in entries.values():
            assert row.question.strip(), f"{row.entry_id} has no question"
            assert row.builder.strip(), f"{row.entry_id} names no builder"
            assert row.estimator.strip(), f"{row.entry_id} names no estimator"

    def test_unknown_entry_names_the_known_ones(self) -> None:
        """A typo is the usual cause, and the list is what resolves it."""
        with pytest.raises(UnknownEntry) as raised:
            entry("E00")

        assert "E01" in str(raised.value)

    def test_an_entry_missing_a_readable_field_is_refused(self, tmp_path) -> None:
        """An entry that cannot be read without running it is not an entry."""
        catalogue = tmp_path / "rq_map.toml"
        catalogue.write_text('[entry.E77]\nquestion = "q"\n', encoding="utf-8")

        with pytest.raises(ValueError, match="builder, estimator"):
            load(catalogue)

    def test_a_missing_parameter_raises_naming_what_is_declared(self) -> None:
        """No defaults: an omitted knob stops the run instead of being invented."""
        row = catalogue_entry(parameters={"alpha": 0.025})

        with pytest.raises(FreezeItemUnset) as raised:
            row.parameter("threshold")

        assert "threshold" in str(raised.value)
        assert "alpha" in str(raised.value), "the message does not say what IS declared"

    def test_saying_none_and_saying_nothing_are_different(self) -> None:
        """``optional`` reads the empty string as a decision, absence as an error."""
        declared = catalogue_entry(parameters={"offset_column": NONE_IN_TOML})
        assert declared.optional("offset_column") is None

        with pytest.raises(FreezeItemUnset):
            catalogue_entry(parameters={}).optional("offset_column")


class TestCoverage:
    """An entry with no working caller is a hole, and holes are printed."""

    def test_uncovered_entries_listed(self) -> None:
        """The shipped catalogue's unwired entry is named by the report.

        ``E14`` declares a builder that ships and an estimator that does not —
        there is no survival model in this library. It is in the catalogue so the
        gap is legible; this test is what keeps it legible.
        """
        holes = coverage.uncovered()
        ids = [hole.entry_id for hole in holes]

        assert "E14" in ids, "the unwired entry vanished from the coverage report"
        assert coverage.uncovered() != coverage.survey(), "nothing is covered at all"

        report = coverage.report()
        assert "E14" in report
        assert "uncovered" in report
        for hole in holes:
            assert hole.detail, f"{hole.entry_id} is reported with no reason"

    def test_a_declared_caller_that_does_not_resolve_is_not_undeclared(
        self, tmp_path
    ) -> None:
        """A broken reference and an absent one need different actions.

        The catalogue claiming a caller that is not there is the more urgent of
        the two, so the report must not fold it into "no caller declared".
        """
        catalogue = tmp_path / "rq_map.toml"
        catalogue.write_text(
            "[entry.E88]\n"
            'question = "q"\n'
            'builder = "b"\n'
            'estimator = "e"\n'
            'caller = "no_such_module:run"\n',
            encoding="utf-8",
        )

        (state,) = coverage.survey(catalogue)

        assert state.state == "unresolved"
        assert "ModuleNotFoundError" in state.detail

    def test_a_malformed_caller_string_is_reported_not_raised(self, tmp_path) -> None:
        """``module.function`` instead of ``module:function`` is a common slip."""
        catalogue = tmp_path / "rq_map.toml"
        catalogue.write_text(
            "[entry.E89]\n"
            'question = "q"\n'
            'builder = "b"\n'
            'estimator = "e"\n'
            'caller = "paired_detection.run"\n',
            encoding="utf-8",
        )

        (state,) = coverage.survey(catalogue)

        assert state.state == "unresolved"
        assert "module:function" in state.detail

    def test_every_shipped_caller_resolves_to_something_callable(self) -> None:
        """A caller that resolved to a module or a constant would satisfy hasattr."""
        for row in load().values():
            if row.caller:
                assert callable(coverage.resolve(row)), row.entry_id


class TestPairedDetectionCaller:
    """The paired-binary example, driven entirely by the catalogue."""

    def test_runs_the_shipped_entry_end_to_end(self) -> None:
        """One discordant pair each way, and the envelope says which arm holds it."""
        envelope = paired_detection.run(entry("E01"), paired_frame())

        assert isinstance(envelope, Envelope)
        assert envelope.estimand == "mcnemar_exact"
        assert envelope.n == 4
        assert envelope.estimate["b"] == 1
        assert envelope.estimate["c"] == 1
        assert envelope.estimate["n_disc"] == 2
        assert envelope.estimate["direction"] == "none"

    def test_the_envelope_carries_the_decisions_the_caller_made(self) -> None:
        """The entry, the pairing unit and the arms, in the order direction reads."""
        envelope = paired_detection.run(entry("E01"), paired_frame())

        assert envelope.convention["entry"] == "E01"
        assert "apk" in envelope.convention["pairing_unit"]
        assert "first=aperv:mop_on_llm_off" in envelope.convention["arms"]
        assert "mop_errors_unique >= 1" in envelope.convention["outcome"]
        assert "majority" in envelope.convention["outcome"]

    def test_below_the_power_floor_is_said_in_the_envelope(self) -> None:
        """Two discordant pairs cannot reach alpha=0.025, and the envelope says so."""
        envelope = paired_detection.run(entry("E01"), paired_frame())

        assert envelope.estimate["power_floor_n_disc"] == 7
        assert envelope.estimate["below_floor"] is True
        assert "not evidence" in envelope.convention["below_floor"]

    def test_an_absent_arm_raises_rather_than_pairing_with_nothing(self) -> None:
        """An empty side would report a well-formed comparison of zero pairs."""
        frame = paired_frame()
        frame = frame.loc[frame["arm"] != "aperv:mop_on_llm_off"]

        with pytest.raises(ValueError, match="has no runs in the frame"):
            paired_detection.run(entry("E01"), frame)

    def test_an_absent_count_column_names_what_is_there(self) -> None:
        """The usual cause is a frame built by a different loader version."""
        frame = paired_frame().drop(columns=["mop_errors_unique"])

        with pytest.raises(ValueError, match="is not in the frame"):
            paired_detection.run(entry("E01"), frame)

    def test_the_caller_takes_nothing_from_its_own_source(self) -> None:
        """Change a knob in the catalogue and the result changes with it.

        This is the property that makes the TOML the readable record of the
        pre-registration: a parameter the caller could override from its own
        source would be invisible to anyone diffing the catalogue.
        """
        declared = entry("E01")
        unanimity = Entry(
            entry_id=declared.entry_id,
            question=declared.question,
            builder=declared.builder,
            estimator=declared.estimator,
            caller=declared.caller,
            parameters={**declared.parameters, "replica_rule": "unanimity"},
        )

        frame = paired_frame()
        # One replica of the guided arm on `both.apk` drops to zero: under
        # majority the cell stays positive, under unanimity it flips.
        mask = (
            (frame["apk"] == "both.apk")
            & (frame["arm"] == "aperv:mop_on_llm_off")
            & (frame["rep"] == 1)
        )
        frame.loc[mask, "mop_errors_unique"] = 0

        by_majority = paired_detection.run(declared, frame)
        by_unanimity = paired_detection.run(unanimity, frame)

        assert by_majority.estimate["n_disc"] != by_unanimity.estimate["n_disc"]
        assert "unanimity" in by_unanimity.convention["outcome"]


class TestCountModelCaller:
    """The count-GLM example, and the two freeze items crossing the TOML boundary."""

    def test_runs_the_shipped_entry_end_to_end(self) -> None:
        """The whole regression table arrives as one envelope."""
        envelope = count_model.run(entry("E15"), count_frame())

        assert isinstance(envelope, Envelope)
        assert envelope.n == 48
        assert any(key.startswith("irr__") for key in envelope.estimate)
        assert envelope.ci is None, "a regression has one interval per term"

    def test_the_envelope_records_the_offset_and_the_reference(self) -> None:
        """Both are what every rate ratio in the table is read against."""
        envelope = count_model.run(entry("E15"), count_frame())

        assert envelope.convention["entry"] == "E15"
        assert "log_apk_size" in envelope.convention["offset"]
        assert "verbatim" in envelope.convention["offset"]
        assert envelope.convention["reference_level"] == "aperv:mop_off_llm_off"

    def test_an_open_freeze_item_stops_the_run(self) -> None:
        """``E19`` omits the offset by decision; running it must raise, not guess.

        The author recorded the application-size offset as an open specification
        choice, and it is load-bearing. An entry that filled it here would emit a
        perfectly plausible table under a specification nobody chose.
        """
        with pytest.raises(FreezeItemUnset, match="offset_column"):
            count_model.run(entry("E19"), count_frame())

    def test_the_open_entry_is_still_a_readable_catalogue_row(self) -> None:
        """Unrunnable is not the same as unwired: it resolves, and it is covered."""
        row = entry("E19")

        assert row.caller == "count_model:run"
        assert callable(coverage.resolve(row))
        assert "E19" not in [hole.entry_id for hole in coverage.uncovered()]

    def test_an_absent_offset_column_names_what_is_there(self) -> None:
        """A declared offset that the frame does not carry is refused."""
        with pytest.raises(ValueError, match="is not in the frame"):
            count_model.run(entry("E15"), count_frame().drop(columns=["log_apk_size"]))

    def test_a_non_finite_offset_is_refused_not_absorbed(self) -> None:
        """A NaN offset fits to a table of NaN rate ratios and raises nowhere.

        patsy never sees the offset, so its dropped-rows check cannot catch it,
        and the result emits as a perfectly well-formed row. The refusal names
        the rows because the usual cause is a join that did not match.
        """
        frame = count_frame()
        frame.loc[3, "log_apk_size"] = np.nan

        with pytest.raises(ValueError, match="non-finite value"):
            count_model.run(entry("E15"), frame)


def test_the_catalogue_is_the_only_file_naming_a_question() -> None:
    """Non-vacuity check for INV-CAN-22's exception.

    ``test_no_rq_identifier`` proves the library is clean by scanning everything
    except this package. That proof is only worth something if the exception is
    actually being used — an empty ``callers/`` would make the scan pass while
    the coupling lived somewhere else entirely.
    """
    assert RQ_MAP.exists(), "the catalogue is missing"
    assert "E01" in RQ_MAP.read_text(encoding="utf-8")
