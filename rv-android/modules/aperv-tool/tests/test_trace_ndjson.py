"""Tests for the native stage-4 NDJSON trace reader.

Every rule the `aperv` delta states about the reader gets one named test, and
each is asserted against `tests/fixtures/trace_ndjson_golden.ndjson` — a fixture
written from the `event-sink` spec of `ape`'s `rearch-04-step-ndjson-telemetry`
*before* the reader existed, so these tests compare the reader against the wire
contract rather than against itself.

The two negative cases that would perturb the golden fixture's malformed count
(an undefined dictionary ID, a trace with no `RUN_START`) are built inline
instead, so the fixture keeps its exact count of 2.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from aperv_tool.analysis.trace_ndjson import (
    Counterfactual,
    StepRow,
    TraceReader,
    read_steps,
)

FIXTURES = Path(__file__).parent / "fixtures"
GOLDEN = FIXTURES / "trace_ndjson_golden.ndjson"

# The epoch base the golden fixture's RUN_START declares.
GOLDEN_T0_MS = 1750000000000

MAIN_ACTIVITY = "br.unb.cic.cryptoapp/.MainActivity"
ABOUT_ACTIVITY = "br.unb.cic.cryptoapp/.AboutActivity"


@pytest.fixture
def rows():
    return read_steps(GOLDEN)


@pytest.fixture
def by_step(rows):
    return {row.step: row for row in rows}


class TestJoinedRow:
    def test_reader_yields_joined_step_row(self, rows, by_step):
        """One row per well-formed StepRecord, with dec/llm[]/out already joined.

        The point of the reader is that the three-way join by `step=` the retired
        format forced on every consumer no longer exists: the decision, the LLM
        attempts and the outcome arrive on the same row.
        """
        assert [row.step for row in rows] == [42, 43, 44]

        step42 = by_step[42]
        assert isinstance(step42, StepRow)
        # Dictionary references resolved to strings, not left as integer IDs.
        assert step42.activity == MAIN_ACTIVITY
        assert step42.state_key == "S17a4f"
        assert step42.action == "model=CLICK@[0,0][100,50]"
        assert step42.decision_source == "MOP_WIDGET"
        assert step42.pick_channel == "roulette_greedy"
        assert step42.priority == 9
        assert step42.mop_exposure == (3, 23)
        # Decision, LLM calls and outcome all present on the one row.
        assert len(step42.llm) == 2
        assert step42.outcome is not None

    def test_epoch_expanded_from_run_start(self, by_step):
        """`t` is run-relative; the absolute clock comes from RUN_START.t0."""
        assert by_step[42].t_rel_ms == 8123
        assert by_step[42].t_epoch_ms == GOLDEN_T0_MS + 8123

    def test_escaped_newline_in_action_round_trips(self, by_step):
        """A raw newline inside an action string survives as data, not as a break.

        This is the failure class the jar's new serializer removes by
        construction: in the retired format the same value split the record over
        two physical lines and silently dropped `decision_source`.
        """
        assert "\n" in by_step[43].action
        assert by_step[43].action.endswith('text="Salvar\nopção"')


class TestDefaultMaterialization:
    def test_boost_defaults_materialized(self, by_step):
        """Absent boost fields come back as explicit zeros (INV-APV-49)."""
        step42 = by_step[42]
        assert (step42.mop, step42.mop_frontier, step42.wtg) == (0, 0, 0)
        assert (step42.coverage, step42.menu, step42.form) == (0, 0, 0)

    def test_present_boosts_are_not_overwritten(self, by_step):
        """Materializing defaults must not flatten the values that were emitted."""
        step43 = by_step[43]
        assert (step43.mop, step43.menu, step43.wtg) == (500, 250, 400)
        assert step43.wtg_source == "both"
        assert (step43.mop_frontier, step43.coverage, step43.form) == (0, 0, 0)

    def test_outcome_booleans_default_to_false(self, by_step):
        """`new_state` and `act_changed` are omitted when false."""
        outcome = by_step[42].outcome
        assert outcome.new_state is True
        assert outcome.activity_changed is False


class TestTriState:
    def test_tri_state_patched_not_defaulted(self, by_step):
        """`patched` distinguishes 0 from absent, so it is never defaulted.

        Absent means "no resolved target"; `0` means "natively clickable node".
        Defaulting the absent case to 0 would merge two different facts, which
        is why the jar emits both values explicitly.
        """
        assert by_step[42].patched == 0
        assert by_step[43].patched is None
        assert by_step[42].patched != by_step[43].patched

    def test_counterfactual_absent_stays_absent(self, by_step):
        """`cf` rides only the MOP-sensitive channels; elsewhere it is absent."""
        assert by_step[43].counterfactual == Counterfactual(
            changed=True, action="model=CLICK@[0,0][10,10]"
        )
        assert by_step[42].counterfactual is None
        assert by_step[44].counterfactual is None


class TestLlmSubEvents:
    def test_llm_calls_kept_in_occurrence_order(self, by_step):
        """`llm[]` is ordered, and a retry appends rather than replaces."""
        calls = by_step[42].llm
        assert [c.call for c in calls] == [3, 4]
        assert [c.mode for c in calls] == ["new_state", "stagnation"]

    def test_completed_call_fields(self, by_step):
        first = by_step[42].llm[0]
        assert first.result == "matched"
        assert first.tool == "click"
        assert first.qwen == (500, 861)
        assert first.px == (512, 884)
        assert first.tokens == (1841, 25)
        assert first.ms == 973
        assert first.matched_class == "android.widget.Button"
        assert first.nearest_dist == 4.2

    def test_abandoned_call_carries_cause_and_detail(self, by_step):
        """An error entry replaces the retired `[APE-LLM-ERROR]` line, attributed
        to its step by construction rather than by a `step=` key."""
        second = by_step[42].llm[1]
        assert second.result == "error"
        assert second.cause == "timeout"
        assert second.detail == "read timed out after 8000 ms"

    def test_step_without_llm_has_empty_tuple(self, by_step):
        assert by_step[43].llm == ()

    def test_prompt_and_response_dumps_survive_the_reader(self, by_step):
        """The dumps reach the caller, newlines and quotes intact.

        They are the bulk of the record and the jar writes them by default, so
        a reader that dropped them would leave the run paying their whole cost
        — escaping included, which the stage's throughput gate measures — for
        data no sanctioned consumer could reach. The successor of
        `decompose_nomatch.py` needs `resp` to decompose `no_match` causes.
        """
        first = by_step[42].llm[0]

        assert first.system_prompt == "You are a GUI testing agent."
        assert first.user_text.startswith('Screen "MainActivity":')
        assert "\n[2] Button" in first.user_text, "the widget list keeps its lines"
        assert first.response == "I will tap Encrypt."
        assert '"name":"click"' in first.tool_calls

    def test_dumps_are_absent_not_empty_when_the_flag_was_off(self, by_step):
        """A call written without dumps carries None, never an empty string.

        The difference is real: `""` would claim the model was sent an empty
        prompt, which is not what a disabled flag means.
        """
        second = by_step[42].llm[1]

        assert second.system_prompt is None
        assert second.user_text is None
        assert second.response is None
        assert second.tool_calls is None


class TestOutcome:
    def test_outcome_absent_differs_from_unresolved(self, by_step):
        """Three distinct outcome states, and the reader keeps them distinct.

        Resolved; legitimately absent (a restart, a non-model action, a
        refinement discard — no `out` member at all); and flushed at teardown
        while still in flight (`out:{"resolved":false}`).
        """
        assert by_step[42].outcome.resolved is True
        assert by_step[43].outcome is None
        assert by_step[44].outcome is not None
        assert by_step[44].outcome.resolved is False

    def test_activity_has_mop_rederived_on_both_sides(self, by_step):
        """The step side reads ACT.mop; the outcome side is a two-hop lookup.

        Neither value is on the step record — the jar records that static fact
        once, on the dictionary entry — so both are re-derived here.
        """
        step42 = by_step[42]
        assert step42.activity_has_mop is True  # act 17, mop:1
        # out.target 232 -> STATE.act 18 -> ACT 18, mop:0
        assert step42.outcome.target_state == "S18b7c"
        assert step42.outcome.target_activity == ABOUT_ACTIVITY
        assert step42.outcome.target_activity_has_mop is False

    def test_component_dispatch_result_recorded(self, by_step):
        """A refused launch and an accepted one differ only here."""
        assert by_step[44].component is not None
        assert by_step[44].component.result == 0
        assert by_step[44].component.error is None


class TestDiagnostics:
    def test_malformed_record_skipped_and_counted(self):
        """Exactly 2 malformed records in the fixture, and the read never raises.

        One syntactically invalid line and one final line truncated mid-write —
        a trace cut by SIGKILL ends that way by construction, and losing the
        whole run's analysis over its last line would be the worse failure.
        """
        reader = TraceReader(GOLDEN)
        rows = list(reader)

        assert reader.diagnostics.malformed == 2
        assert reader.diagnostics.steps_yielded == len(rows) == 3

    def test_free_text_lines_are_not_counted_as_malformed(self):
        """A sink record is a line beginning with `{` (INV-SNK-11).

        The jar interleaves free-text `[APE] ` diagnostics into the same stdout.
        Counting those as damage would report every healthy run as broken.
        """
        reader = TraceReader(GOLDEN)
        list(reader)
        assert "[APE] " in GOLDEN.read_text(encoding="utf-8")
        assert reader.diagnostics.malformed == 2

    def test_run_end_is_read_by_nothing_and_not_counted_as_malformed(self):
        """RUN_END is well-formed, skipped, and has no accessor at all.

        Write-only by owner decision D5: no code path reads, validates or acts
        on it (INV-APV-53). The absence of an accessor is the point — an
        attribute is the first step toward `if not run_end: ...`, which is the
        exit contract that decision refuses — so it is asserted rather than
        left to be noticed.
        """
        reader = TraceReader(GOLDEN)
        list(reader)

        assert reader.diagnostics.records_read == 14
        assert reader.diagnostics.activities == 2
        assert reader.diagnostics.states == 2
        assert reader.diagnostics.run_start_present is True
        assert not hasattr(reader, "run_end")
        assert "RUN_END" not in {
            name for name in dir(reader) if not name.startswith("_")
        }

    def test_undefined_dictionary_id_is_malformed(self, tmp_path):
        """A reference no earlier record defined is malformed, not a placeholder.

        Emitting an empty or invented activity string here would let a fabricated
        name flow into an analysis indistinguishable from a real one.
        """
        trace = tmp_path / "undefined.ndjson"
        trace.write_text(
            '{"type":"ACT","id":17,"name":"com.foo/.Main","mop":1}\n'
            '{"type":"STATE","id":231,"key":"S1","act":17}\n'
            '{"s":1,"t":10,"act":17,"st":99,'
            '"dec":{"a":"CLICK","src":"SATA","ch":"sata_other"}}\n'
            '{"s":2,"t":20,"act":17,"st":231,'
            '"dec":{"a":"CLICK","src":"SATA","ch":"sata_other"}}\n',
            encoding="utf-8",
        )

        reader = TraceReader(trace)
        rows = list(reader)

        assert [row.step for row in rows] == [2]
        assert reader.diagnostics.malformed == 1
        assert all(row.state_key for row in rows)

    def test_undefined_outcome_target_is_malformed(self, tmp_path):
        """The same rule applies to the outcome-side two-hop lookup."""
        trace = tmp_path / "undefined_target.ndjson"
        trace.write_text(
            '{"type":"ACT","id":17,"name":"com.foo/.Main","mop":1}\n'
            '{"type":"STATE","id":231,"key":"S1","act":17}\n'
            '{"s":1,"t":10,"act":17,"st":231,'
            '"dec":{"a":"CLICK","src":"SATA","ch":"sata_other"},'
            '"out":{"new_state":true,"target":404}}\n',
            encoding="utf-8",
        )

        reader = TraceReader(trace)
        assert list(reader) == []
        assert reader.diagnostics.malformed == 1

    def test_missing_run_start_reports_epoch_unavailable(self, tmp_path):
        """No RUN_START means no absolute clock — and none is invented.

        The run-relative `t` still stands. A base is not inferred from the
        file's mtime, from the logcat, or from anything else (INV-APV-51).
        """
        trace = tmp_path / "no_run_start.ndjson"
        trace.write_text(
            '{"type":"ACT","id":17,"name":"com.foo/.Main","mop":0}\n'
            '{"type":"STATE","id":231,"key":"S1","act":17}\n'
            '{"s":7,"t":4321,"act":17,"st":231,'
            '"dec":{"a":"CLICK","src":"SATA","ch":"sata_other"}}\n',
            encoding="utf-8",
        )

        reader = TraceReader(trace)
        rows = list(reader)

        assert reader.run_start is None
        assert reader.diagnostics.run_start_present is False
        assert rows[0].t_rel_ms == 4321
        assert rows[0].t_epoch_ms is None


class TestRunLevelRecords:
    """The census records reach the caller, because nothing else can reach them.

    This module is the sole mechanism for consuming a post-change trace, so a
    record it skips is a record no conformant analysis can read.
    """

    def test_mop_data_census_exposed(self):
        reader = TraceReader(GOLDEN)
        list(reader)

        assert reader.mop_data is not None
        assert reader.mop_data["status"] == "loaded"
        assert reader.mop_data["windows"] == 5
        assert reader.mop_data["widgets"] == 340
        assert reader.mop_data["wtgEdges"] == 7, (
            "the click-only view the frontier passes gate on, not the flat "
            "transitions list the retired line reported"
        )
        assert "type" not in reader.mop_data

    def test_pipeline_census_says_what_was_not_assembled(self):
        reader = TraceReader(GOLDEN)
        list(reader)

        assert reader.pipeline is not None
        assert reader.pipeline["passes"] == ["MopWidgetPass", "CoveragePass"]
        disabled = [
            candidate["name"]
            for candidate in reader.pipeline["candidates"]
            if not candidate["enabled"]
        ]
        assert disabled == ["WtgPass", "FrontierPass", "MopFrontierPass"], (
            "without the candidate census, 'the arm turned this off' and 'this "
            "application's data could not support it' are the same evidence"
        )

    def test_llm_ack_exposed(self):
        reader = TraceReader(GOLDEN)
        list(reader)

        assert reader.llm_ack is not None
        assert reader.llm_ack["server_model"] == "qwen3-vl-8b"

    def test_run_level_records_reset_between_iterations(self):
        """A second pass re-reads them rather than keeping the first pass's.

        The ID tables and the header already reset; a census that survived
        would make a reader used twice report the first trace's assembly for
        the second one.
        """
        reader = TraceReader(GOLDEN)
        list(reader)
        first = reader.pipeline
        list(reader)

        assert reader.pipeline == first
        assert reader.pipeline is not first, "re-read, not retained"

    def test_absent_run_level_records_are_none(self, tmp_path):
        """A trace with no census reports None, never an empty dict.

        An empty dict would read as "the load happened and found nothing",
        which is a different claim from "this trace does not say".
        """
        trace = tmp_path / "bare.trace"
        trace.write_text(
            '{"type":"ACT","id":0,"name":"com.foo/.Main","mop":0}\n'
            '{"type":"STATE","id":0,"key":"S1","act":0}\n'
            '{"s":1,"t":5,"act":0,"st":0,"dec":{"a":"x","src":"SATA","ch":"sata_other"}}\n',
            encoding="utf-8",
        )

        reader = TraceReader(trace)
        list(reader)

        assert reader.mop_data is None
        assert reader.pipeline is None
        assert reader.llm_ack is None


class TestCollectionPathIsolation:
    """INV-APV-48: the reader is analysis-time only and never on the run path."""

    def _imports_of(self, path: Path) -> set[str]:
        """Module names imported by one source file, however they are written."""
        tree = ast.parse(path.read_text(encoding="utf-8"))
        found: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    found.add(node.module)
                found.update(
                    f"{node.module}.{a.name}" for a in node.names if node.module
                )
        return found

    def test_reader_never_imported_by_collection_path(self):
        """`trace_ndjson` is unreachable from `tools/aperv/tool.py`'s import graph.

        Walked transitively across the package's own modules, because an
        indirect import would couple the collection path to the analysis path
        just as effectively as a direct one.
        """
        package_root = Path(__import__("aperv_tool").__file__).parent
        entry = package_root / "tools" / "aperv" / "tool.py"
        assert entry.exists()

        seen: set[Path] = set()
        pending = [entry]
        reachable: set[str] = set()

        while pending:
            current = pending.pop()
            if current in seen:
                continue
            seen.add(current)

            for name in self._imports_of(current):
                if not name.startswith("aperv_tool"):
                    continue
                reachable.add(name)
                relative = Path(*name.split(".")[1:])
                for candidate in (
                    package_root / relative.with_suffix(".py"),
                    package_root / relative / "__init__.py",
                ):
                    if candidate.exists():
                        pending.append(candidate)

        # Non-vacuity: a walk that reached nothing would satisfy the assertion
        # below while proving nothing at all. tool.py does import within the
        # package, so an empty result means the walk broke, not that the
        # collection path is clean.
        assert reachable, "import walk reached no aperv_tool module — test is vacuous"

        offenders = {name for name in reachable if "trace_ndjson" in name}
        assert offenders == set(), f"collection path reaches the reader: {offenders}"

    def test_import_walk_detects_a_reader_import(self, tmp_path):
        """Positive control for the walk above, so its silence means something.

        Runs the same traversal over a synthetic package where the collection
        path *does* import the reader, and asserts it is caught. Without this,
        a traversal bug would make the real assertion pass forever.
        """
        package = tmp_path / "aperv_tool"
        (package / "tools" / "aperv").mkdir(parents=True)
        (package / "analysis").mkdir()
        (package / "analysis" / "trace_ndjson.py").write_text("", encoding="utf-8")
        # The import is indirect, through a helper, exactly as a real leak would be.
        (package / "tools" / "aperv" / "helper.py").write_text(
            "from aperv_tool.analysis import trace_ndjson\n", encoding="utf-8"
        )
        entry = package / "tools" / "aperv" / "tool.py"
        entry.write_text(
            "from aperv_tool.tools.aperv import helper\n", encoding="utf-8"
        )

        seen: set[Path] = set()
        pending = [entry]
        reachable: set[str] = set()
        while pending:
            current = pending.pop()
            if current in seen:
                continue
            seen.add(current)
            for name in self._imports_of(current):
                if not name.startswith("aperv_tool"):
                    continue
                reachable.add(name)
                relative = Path(*name.split(".")[1:])
                for candidate in (
                    package / relative.with_suffix(".py"),
                    package / relative / "__init__.py",
                ):
                    if candidate.exists():
                        pending.append(candidate)

        assert {name for name in reachable if "trace_ndjson" in name}
