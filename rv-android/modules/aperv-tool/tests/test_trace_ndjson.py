"""Tests for the native stage-4 NDJSON trace reader.

Every rule the `aperv` delta states about the reader gets one named test, each
asserted against a hand-written fixture rather than against the reader itself:

- `trace_ndjson_golden.ndjson`, a trace of the `eea2b1a9` jar (`v: 1`), written
  from the `event-sink` spec of `ape`'s `rearch-04-step-ndjson-telemetry`
  *before* the reader existed;
- `trace_ndjson_groups.ndjson`, a trace of the group-isolation jar (`v: 2`),
  written from the `event-sink` spec of `ape`'s `isolate-guidance-groups`;
- `trace_ndjson_v3_header.ndjson`, a header declaring a version the reader does
  not implement.

The negative cases that would perturb the golden fixture's malformed count (an
undefined dictionary ID, a trace with no `RUN_START`, a wrongly shaped member)
are built inline instead, so the fixture keeps its exact count of 2.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from fixture_gate import MISSING_REAL

from aperv_tool.analysis.trace_ndjson import (
    SUPPORTED_VERSIONS,
    BuildStamp,
    ComponentTrigger,
    Counterfactual,
    NavTie,
    Ownership,
    SchemaVersionMismatch,
    StepRow,
    TraceReader,
    read_steps,
)

FIXTURES = Path(__file__).parent / "fixtures"
GOLDEN = FIXTURES / "trace_ndjson_golden.ndjson"
GROUPS = FIXTURES / "trace_ndjson_groups.ndjson"
V3_HEADER = FIXTURES / "trace_ndjson_v3_header.ndjson"

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
        assert step42.nav_frontier == 0
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

    def test_run_end_is_a_census_record_not_counted_as_malformed(self):
        """RUN_END is well-formed, carried verbatim, and interpreted by nothing.

        The reader exposes it beside the other run-level records and derives
        nothing from it (INV-APV-53): the public surface is pinned, so a
        completeness flag or an "ended normally" property cannot appear
        unnoticed. The collection path still never reads it, which
        `test_aperv_tool.py` asserts over `tools/aperv/*`.
        """
        reader = TraceReader(GOLDEN)
        list(reader)

        assert reader.diagnostics.records_read == 14
        assert reader.diagnostics.malformed == 2
        assert reader.diagnostics.activities == 2
        assert reader.diagnostics.states == 2
        assert reader.diagnostics.run_start_present is True
        assert reader.run_end == {
            "reason": "timeout",
            "steps": 4,
            "t_first_step": 8123,
            "t_last_step": 9500,
            "counters": {"calls": 2, "matched": 1},
        }
        assert {name for name in dir(reader) if not name.startswith("_")} == {
            "path",
            "run_start",
            "diagnostics",
            "mop_data",
            "pipeline",
            "llm_ack",
            "run_end",
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

    @pytest.mark.parametrize(
        "damaged",
        [
            '"dec":{"a":"CLICK","src":"SATA","ch":"sata_other","cf":"wrong"}',
            '"dec":{"a":"CLICK","src":"SATA","ch":"sata_other","cf":[1,2]}',
            '"dec":{"a":"CLICK","src":"SATA","ch":"sata_other"},"llm":["wrong"]',
            '"dec":{"a":"CLICK","src":"SATA","ch":"sata_other"},"llm":[7]',
        ],
        ids=["cf_is_str", "cf_is_list", "llm_entry_is_str", "llm_entry_is_int"],
    )
    def test_a_wrongly_shaped_section_is_malformed_not_an_abort(
        self, tmp_path, damaged
    ):
        """A `cf` or `llm[]` entry that is not an object joins the malformed count.

        These two are the sections read through `.get()` without the record having said
        they are objects, so a damaged one would raise `AttributeError` rather than
        the `TypeError` the envelope catches. The whole read is a generator consumed
        inside `join_tree`, so an escape here would abort the join of every run in
        the tree over one damaged record — the opposite of INV-APV-50, and exactly
        the schema drift the malformed path exists to absorb.
        """
        trace = tmp_path / "damaged.ndjson"
        trace.write_text(
            '{"type":"ACT","id":17,"name":"com.foo/.Main","mop":1}\n'
            '{"type":"STATE","id":231,"key":"S1","act":17}\n'
            '{"s":1,"t":10,"act":17,"st":231,' + damaged + "}\n"
            '{"s":2,"t":20,"act":17,"st":231,'
            '"dec":{"a":"CLICK","src":"SATA","ch":"sata_other"}}\n',
            encoding="utf-8",
        )

        reader = TraceReader(trace)
        rows = list(reader)

        assert [row.step for row in rows] == [2]
        assert reader.diagnostics.malformed == 1

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


class TestRunStartHeader:
    """The header is read whole, and the schema it declares is checked.

    A trace that cannot say which jar, which arm and which parameters produced
    it is only interpretable next to the code that produced it — the position
    that made a whole campaign unreadable when a stale jar shipped. These tests
    hold the reader to carrying the record the jar writes to end that, rather
    than the three fields the earliest analyses happened to need.
    """

    def test_run_start_thirteen_members(self):
        """All thirteen members of an `eea2b1a9` header arrive, `build` nested."""
        reader = TraceReader(GOLDEN)
        list(reader)
        run_start = reader.run_start

        assert run_start is not None
        assert run_start.v == 1
        assert run_start.variant is None, "the eea2b1a9 jar writes no variant"
        assert run_start.run_id == "cryptoapp.apk__1__1800__aperv:mop_on_llm_70"
        assert run_start.t0_ms == GOLDEN_T0_MS
        assert run_start.seed == 1750000000001
        assert run_start.agent == "sata"
        assert run_start.preset == "mop_llm"
        assert run_start.features == (
            "ACTIVITY_TRIGGER",
            "LLM_ROUTING",
            "MOP",
            "MOP_FRONTIER",
        )
        assert run_start.params["ape.llmPercentage"] == "0.7"
        assert run_start.inert == ("ape.componentPercentage",)
        assert run_start.corpus_basis.startswith("selected162:")
        assert run_start.digest == "ad537a816a19f154"
        assert run_start.props_digest.startswith("81feabbc")
        assert run_start.build == BuildStamp(
            sha="9e948102", time="2026-08-05T17:22:00Z"
        )

    def test_params_absence_means_the_jar_default(self):
        """`params` is what someone chose, so an absent key is not an unset one.

        The jar omits a parameter sitting at its own default because the default
        is recoverable from the jar `build.sha` names. Reading absence as "unset"
        would turn every default into a claim the record never made.
        """
        reader = TraceReader(GOLDEN)
        list(reader)

        assert "ape.mopWeightDirect" in reader.run_start.params
        assert "ape.mopWeightWtg" not in reader.run_start.params

    def test_inert_absent_is_none(self, tmp_path):
        """An absent member is None; an empty list is an empty tuple.

        The two are different facts — "the record did not say" against "the jar
        declared no inert key" — and an inert key outside an arm's expected set
        is how a feature silently leaving the plan announces itself. Defaulting
        the first case to the second would answer that provenance question with
        the reader's own guess.
        """
        trace = tmp_path / "no_inert.trace"
        trace.write_text(
            '{"type":"RUN_START","v":1,"run_id":"r","t0":10,"preset":"mop"}\n'
            '{"type":"ACT","id":1,"name":"com.foo/.Main","mop":0}\n'
            '{"type":"STATE","id":1,"key":"S1","act":1}\n'
            '{"s":1,"t":5,"act":1,"st":1,'
            '"dec":{"a":"CLICK","src":"SATA","ch":"sata_other"}}\n',
            encoding="utf-8",
        )

        reader = TraceReader(trace)
        list(reader)

        assert reader.run_start.inert is None
        assert reader.run_start.features is None
        assert reader.run_start.build is None
        assert reader.run_start.seed is None
        assert reader.run_start.preset == "mop"

        v3 = TraceReader(V3_HEADER)
        list(v3)
        assert v3.run_start.inert == (), "an empty list is not an absent member"
        assert v3.run_start.corpus_basis is None

    def test_missing_t0_leaves_the_epoch_unavailable(self, tmp_path):
        """A header without `t0` is a header, not a malformed record.

        It says everything else it says, and only the absolute clock is lost —
        which is reported unavailable rather than based on a guess (INV-APV-51).
        """
        trace = tmp_path / "no_t0.trace"
        trace.write_text(
            '{"type":"RUN_START","v":1,"run_id":"r","preset":"mop"}\n'
            '{"type":"ACT","id":1,"name":"com.foo/.Main","mop":0}\n'
            '{"type":"STATE","id":1,"key":"S1","act":1}\n'
            '{"s":1,"t":5,"act":1,"st":1,'
            '"dec":{"a":"CLICK","src":"SATA","ch":"sata_other"}}\n',
            encoding="utf-8",
        )

        reader = TraceReader(trace)
        rows = list(reader)

        assert reader.diagnostics.malformed == 0
        assert reader.run_start.t0_ms is None
        assert rows[0].t_rel_ms == 5
        assert rows[0].t_epoch_ms is None

    def test_v_mismatch_strict_raises(self):
        """Strict mode fails loudly, and before a single row is handed over.

        A caller comparing fields across traces is asking the one question a
        schema change invalidates, so it gets the exception rather than rows it
        would go on to average against rows of another schema.
        """
        reader = TraceReader(V3_HEADER, strict=True)

        with pytest.raises(SchemaVersionMismatch) as raised:
            list(reader)

        assert raised.value.found == 3
        assert raised.value.supported == SUPPORTED_VERSIONS == frozenset({1, 2})
        assert "v=3" in str(raised.value)
        assert "implements 1, 2" in str(raised.value)
        assert reader.diagnostics.steps_yielded == 0, "raised before any row"

    def test_v_mismatch_counted(self):
        """Non-strict, the same trace yields its rows and counts the mismatch.

        A survey over a mixed tree should report the tree's composition, not
        stop at its first foreign trace.
        """
        reader = TraceReader(V3_HEADER)
        rows = list(reader)

        assert len(rows) == 1
        assert reader.diagnostics.schema_version_mismatch == 1
        assert reader.run_start.v == 3

    @pytest.mark.parametrize(
        ("trace", "version"), [(GOLDEN, 1), (GROUPS, 2)], ids=["eea2b1a9", "groups"]
    )
    def test_both_jar_generations_read_in_strict_mode(self, trace, version):
        """Version 1 (`eea2b1a9`) and version 2 (group isolation) both pass.

        The group-isolation jar bumped the version because `dec.src` changed
        meaning, not because the reader cannot read it; the version is carried
        so a consumer can tell the two meanings apart (INV-APV-67).
        """
        reader = TraceReader(trace, strict=True)
        rows = list(reader)

        assert rows
        assert reader.run_start.v == version
        assert reader.diagnostics.schema_version_mismatch == 0

    def test_absent_version_is_unknown_not_mismatched(self, tmp_path):
        """No `v` means the schema is unknown, and unknown is never inferred.

        Counting it as a mismatch would claim the record said something it did
        not; assuming it matches would claim the opposite. Both are the reader
        answering for the trace.
        """
        trace = tmp_path / "no_v.trace"
        trace.write_text(
            '{"type":"RUN_START","run_id":"r","t0":10}\n'
            '{"type":"ACT","id":1,"name":"com.foo/.Main","mop":0}\n'
            '{"type":"STATE","id":1,"key":"S1","act":1}\n'
            '{"s":1,"t":5,"act":1,"st":1,'
            '"dec":{"a":"CLICK","src":"SATA","ch":"sata_other"}}\n',
            encoding="utf-8",
        )

        reader = TraceReader(trace, strict=True)
        rows = list(reader)

        assert len(rows) == 1
        assert reader.run_start.v is None
        assert reader.diagnostics.schema_version_mismatch == 0

    def test_first_brace_line_is_header(self, tmp_path):
        """The header is the first sink record, whatever text precedes it.

        The jar prints its AOSP banners to the same stdout the trace is captured
        from, so requiring line 1 would lose the header on a healthy run. The
        rule is positional in records, not in lines: a `RUN_START` reached after
        another sink record is not this trace's header — that is two runs'
        output concatenated, and adopting the second header would attribute
        these steps to that run's specification.
        """
        preamble = tmp_path / "banners_first.trace"
        preamble.write_text(
            "--------- beginning of main\n"
            "[APE] *** INFO *** InputMethod ID: com.google.android.inputmethod\n"
            '{"type":"RUN_START","v":1,"run_id":"r","t0":1000,"preset":"mop"}\n'
            '{"type":"ACT","id":1,"name":"com.foo/.Main","mop":0}\n'
            '{"type":"STATE","id":1,"key":"S1","act":1}\n'
            '{"s":1,"t":5,"act":1,"st":1,'
            '"dec":{"a":"CLICK","src":"SATA","ch":"sata_other"}}\n',
            encoding="utf-8",
        )

        reader = TraceReader(preamble)
        rows = list(reader)

        assert reader.run_start is not None
        assert reader.run_start.run_id == "r"
        assert rows[0].t_epoch_ms == 1005

        late = tmp_path / "header_not_first.trace"
        late.write_text(
            '{"type":"ACT","id":1,"name":"com.foo/.Main","mop":0}\n'
            '{"type":"RUN_START","v":1,"run_id":"other-run","t0":1000}\n'
            '{"type":"STATE","id":1,"key":"S1","act":1}\n'
            '{"s":1,"t":5,"act":1,"st":1,'
            '"dec":{"a":"CLICK","src":"SATA","ch":"sata_other"}}\n',
            encoding="utf-8",
        )

        reader = TraceReader(late)
        rows = list(reader)

        assert reader.run_start is None
        assert reader.diagnostics.run_start_present is False
        assert reader.diagnostics.malformed == 0, "well-formed, just not the header"
        assert rows[0].t_epoch_ms is None

    def test_damaged_first_record_does_not_consume_the_header_slot(self, tmp_path):
        """A truncated first line says nothing about which record is the header.

        Letting it take the slot would turn one damaged line into a whole run
        with no provenance, which is the failure the header exists to prevent.
        """
        trace = tmp_path / "damaged_first.trace"
        trace.write_text(
            '{"type":"MOP_DA\n'
            '{"type":"RUN_START","v":1,"run_id":"r","t0":1000}\n'
            '{"type":"ACT","id":1,"name":"com.foo/.Main","mop":0}\n'
            '{"type":"STATE","id":1,"key":"S1","act":1}\n'
            '{"s":1,"t":5,"act":1,"st":1,'
            '"dec":{"a":"CLICK","src":"SATA","ch":"sata_other"}}\n',
            encoding="utf-8",
        )

        reader = TraceReader(trace)
        rows = list(reader)

        assert reader.diagnostics.malformed == 1
        assert reader.run_start is not None
        assert rows[0].t_epoch_ms == 1005


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
        assert reader.run_end is None

    def test_groups_run_level_records_with_the_routing_counters(self):
        """The four run-level records of a group-isolation trace are reachable.

        `RUN_END.counters` is the per-run census of the mechanisms the cell
        mounts, so an analysis of the cells needs the eight routing counters
        exactly as the jar wrote them.
        """
        reader = TraceReader(GROUPS)
        list(reader)

        assert reader.mop_data["targets"] == 4
        assert "NavFrontierPass" in reader.pipeline["passes"]
        assert reader.llm_ack["server_model"] == "Qwen/Qwen3-VL-4B-Instruct"
        assert "type" not in reader.run_end
        counters = reader.run_end["counters"]
        assert counters["coinMop"] == 37
        assert counters["coinLlm"] == 120
        assert counters["launches"] == 4
        assert {
            key: counters[key]
            for key in (
                "gateMinActions",
                "gateBreaker",
                "guardBacks",
                "bufAbandoned",
                "restarts",
            )
        } == {
            "gateMinActions": 3,
            "gateBreaker": 0,
            "guardBacks": 2,
            "bufAbandoned": 1,
            "restarts": 1,
        }
        assert reader.diagnostics.malformed == 0


# Fields that only the group-isolation jar writes, absent on every older trace.
GROUP_ONLY_FIELDS = (
    "owner",
    "scorer_cf",
    "draw",
    "nav",
    "input_source",
    "restart_kind",
    "back_menu_capped",
    "sata_path",
    "rotation",
    "buffer_abandoned_by",
    "component_trigger",
)


@pytest.fixture
def groups_by_step():
    return {row.step: row for row in read_steps(GROUPS)}


def _one_step_trace(tmp_path: Path, dec: str) -> TraceReader:
    """A minimal trace whose step 1 carries `dec` and whose step 2 is clean.

    The clean second step is the control: it proves a malformed first record
    was skipped rather than taking the read down with it.
    """
    trace = tmp_path / "one_step.ndjson"
    trace.write_text(
        '{"type":"RUN_START","v":2,"run_id":"r","t0":10}\n'
        '{"type":"ACT","id":1,"name":"com.foo/.Main"}\n'
        '{"type":"STATE","id":1,"key":"S1","act":1}\n'
        '{"s":1,"t":5,"act":1,"st":1,"dec":' + dec + "}\n"
        '{"s":2,"t":6,"act":1,"st":1,'
        '"dec":{"a":"CLICK","src":"sata","ch":"sata_other","own":{"i":"sata"}}}\n',
        encoding="utf-8",
    )
    return TraceReader(trace)


class TestMopStampMembers:
    def test_mop_stamp_members_reach_the_row(self, by_step):
        """`mopd`, `mops` and `ret` reach typed fields instead of being dropped."""
        step43 = by_step[43]
        assert step43.mop_distance == 2
        assert step43.mop_stamp == "s"
        assert step43.retired_targets == (0, 3)

        step42 = by_step[42]
        assert (
            step42.mop_distance,
            step42.mop_stamp,
            step42.retired_targets,
        ) == (None, None, None)


class TestGroupIsolationMembers:
    """The decision record of the group-isolation jar reaches the row.

    `trace_ndjson_groups.ndjson` is hand-written from the `event-sink` spec of
    `ape`'s `isolate-guidance-groups`. Two of its records deliberately go beyond
    what one real step writes, so that every rule has an input that reaches it:
    step 5 carries every new member at once (a real step carries `restart` only
    when the RESTART guard owns it, and `buf` only when a preempting owner took
    it), and `ACT` 2 carries no `mop` although the cell mounts MOP.
    """

    def test_owner_record_reaches_the_row(self, groups_by_step):
        """`src` is carried as written, beside the owner that was intended."""
        step4 = groups_by_step[4]

        assert step4.decision_source == "sata"
        assert step4.owner == Ownership(
            intended="llm",
            trigger="coin",
            u_llm=0.42,
            u_mop=0.17,
            gate="min_actions",
            fallback="gate",
        )
        assert step4.sata_path == "greedy_path"
        assert step4.rotation == 1

    def test_one_step_per_owner(self, groups_by_step):
        """Steps owned by `llm`, `mop`, `restart` and `sata` each read whole."""
        assert {
            step: (row.decision_source, row.pick_channel, row.owner.intended)
            for step, row in groups_by_step.items()
        } == {
            1: ("llm", "llm", "llm"),
            2: ("mop", "mop_coin", "mop"),
            3: ("restart", "restart", "restart"),
            4: ("sata", "sata_other", "llm"),
            5: ("sata", "roulette_greedy", "sata"),
        }
        assert groups_by_step[1].owner.trigger == "new_state"
        assert groups_by_step[1].owner.u_mop == 0.88
        assert groups_by_step[2].mop_distance == 2
        assert groups_by_step[2].mop_stamp == "s"
        assert groups_by_step[3].restart_kind == "activity"
        assert groups_by_step[3].sata_path is None

    def test_every_new_member_reaches_its_field(self, groups_by_step):
        """Each member of step 5 lands in its typed `StepRow` field."""
        step5 = groups_by_step[5]

        assert step5.scorer_cf == {"mop": True, "navf": False, "cov": False}
        assert step5.draw == (731, 1290)
        assert step5.nav == NavTie(
            point="X3", component="mop", alternative=True, drew=False
        )
        assert step5.input_source == "typed"
        assert step5.restart_kind == "periodic"
        assert step5.back_menu_capped == 1
        assert step5.sata_path == "eps_roulette"
        assert step5.rotation == 0, "rot:0 is a reading, not an absence"
        assert step5.buffer_abandoned_by == "budget"
        assert step5.component_trigger == ComponentTrigger(
            kind="broadcast", component_class="com.example.BootReceiver"
        )
        assert step5.nav_frontier == 150
        assert (step5.mop, step5.coverage) == (400, 50)
        assert step5.mop_distance == 1
        assert step5.mop_stamp == "i"
        assert step5.retired_targets == (0, 3)
        assert step5.patched == 0
        assert step5.mop_exposure == (2, 9)

    def test_group_isolation_trace_has_no_v1_members(self, groups_by_step):
        """`cf` and `wtgsrc` exist only on `v == 1`, so they are None here."""
        for row in groups_by_step.values():
            assert row.counterfactual is None
            assert row.wtg_source is None

    def test_eea2b1a9_trace_reports_the_new_members_absent(self, rows):
        """No default for a mechanism the older jar did not have (INV-APV-49)."""
        for row in rows:
            for name in GROUP_ONLY_FIELDS:
                assert getattr(row, name) is None, f"step {row.step}: {name}"
            assert row.nav_frontier == 0

        reader = TraceReader(GOLDEN)
        list(reader)
        assert reader.run_start.variant is None

    def test_run_start_carries_every_member_variant_included(self):
        """All fourteen members of the group-isolation header reach the caller."""
        reader = TraceReader(GROUPS)
        list(reader)
        run_start = reader.run_start

        assert run_start.v == 2
        assert run_start.variant == "as_mop_llm"
        assert run_start.preset == "as_mop_llm"
        assert run_start.run_id == "cryptoapp.apk__1__900__aperv:as_mop_llm"
        assert run_start.t0_ms == 1790000000000
        assert run_start.seed == 1790000000001
        assert run_start.agent == "sata"
        assert "MOP_LAUNCHER" in run_start.features
        assert run_start.params["ape.variant"] == "as_mop_llm"
        assert run_start.inert == ()
        assert run_start.corpus_basis == "e6-corpus:5b1f0c2d"
        assert run_start.digest == "c0ffee0123456789"
        assert run_start.props_digest.startswith("9a8b7c6d")
        assert run_start.build == BuildStamp(
            sha="16b185f4", time="2026-10-17T09:00:00Z"
        )

    def test_activity_without_the_mop_fact_reports_it_absent(
        self, groups_by_step, by_step
    ):
        """An `ACT` with no `mop` gives None on both sides (INV-APV-68).

        The group-isolation jar writes the member only when MOP is mounted, so
        its absence says the fact was not computed; False would claim it was.
        """
        assert groups_by_step[3].activity_has_mop is None
        assert groups_by_step[1].activity_has_mop is True
        assert groups_by_step[1].outcome.target_activity == (
            "br.unb.cic.cryptoapp/.SettingsActivity"
        )
        assert groups_by_step[1].outcome.target_activity_has_mop is None

        # ACT 18 of the golden fixture carries mop:0, which still reads False.
        assert by_step[43].activity == ABOUT_ACTIVITY
        assert by_step[43].activity_has_mop is False

    def test_unknown_enumerated_value_is_carried(self, tmp_path):
        """A SATA path the contract does not list is data, not damage."""
        reader = _one_step_trace(
            tmp_path,
            '{"a":"CLICK","src":"sata","ch":"sata_other",'
            '"own":{"i":"sata","fb":"novel"},"strat":"lookahead",'
            '"nav":{"x":"X9","c":"other","alt":0,"drew":1}}',
        )
        rows = list(reader)

        assert rows[0].sata_path == "lookahead"
        assert rows[0].owner.fallback == "novel"
        assert rows[0].nav == NavTie(
            point="X9", component="other", alternative=False, drew=True
        )
        assert reader.diagnostics.malformed == 0

    @pytest.mark.parametrize(
        "member",
        [
            '"own":"llm"',
            '"own":{"trg":"coin"}',
            '"draw":[731]',
            '"draw":731',
            '"nav":"X3"',
            '"nav":{"x":"X3","c":"mop","alt":1}',
            '"trig":"broadcast"',
            '"trig":{"k":"broadcast"}',
            '"cfc":["mop"]',
            '"ret":3',
        ],
        ids=[
            "own_is_str",
            "own_without_i",
            "draw_is_short",
            "draw_is_int",
            "nav_is_str",
            "nav_without_drew",
            "trig_is_str",
            "trig_without_c",
            "cfc_is_list",
            "ret_is_int",
        ],
    )
    def test_wrongly_shaped_member_is_malformed(self, tmp_path, member):
        """A structured member of the wrong shape drops its record, not the read."""
        reader = _one_step_trace(
            tmp_path, '{"a":"CLICK","src":"sata","ch":"sata_other",' + member + "}"
        )
        rows = list(reader)

        assert [row.step for row in rows] == [2]
        assert reader.diagnostics.malformed == 1


class TestRunStartOnRecordedTraces:
    """The header rules hold on captured output, not only on a hand-written one.

    The golden fixture was written from the wire spec before the reader existed,
    which is what makes it an independent check of the reader; what it cannot
    check is whether the jar actually writes what the spec says. These tests
    read the pinned cmp162 traces for that, and skip — never pass — when the
    campaign tree is not on this machine.
    """

    def _aperv_traces(self, manifest: dict) -> list[str]:
        return sorted(
            path
            for path in manifest["files"]
            if path.endswith(".trace") and "aperv" in path
        )

    def test_cmp162_aperv_headers_carry_every_member(
        self, cmp162_manifest: dict, cmp162_root: Path
    ) -> None:
        """Every pinned `aperv` header carries all thirteen members, `v` at 1.

        The campaign holds 972 `aperv` traces; the manifest pins the 105 that
        belong to its twelve-application raw subset, and this asserts over those
        — the pin is the denominator, so a wider claim would be one the fixture
        cannot support. Each read stops at the first step row, so the assertion
        costs the head of each file rather than its whole length.
        """
        traces = self._aperv_traces(cmp162_manifest)
        assert traces, "the manifest pins no aperv traces"

        checked = 0
        for relative in traces:
            path = cmp162_root / relative
            if not path.exists():
                pytest.skip(f"{MISSING_REAL}: {relative}")

            reader = TraceReader(path)
            next(iter(reader), None)
            run_start = reader.run_start

            assert run_start is not None, f"{relative}: no RUN_START header"
            absent = [
                name
                for name in (
                    "v",
                    "run_id",
                    "t0_ms",
                    "seed",
                    "agent",
                    "preset",
                    "features",
                    "params",
                    "inert",
                    "corpus_basis",
                    "digest",
                    "props_digest",
                    "build",
                )
                if getattr(run_start, name) is None
            ]
            assert not absent, f"{relative}: header lacks {absent}"
            assert run_start.v == 1
            assert run_start.build.sha, f"{relative}: build carries no sha"
            assert reader.diagnostics.schema_version_mismatch == 0
            checked += 1

        assert checked == len(traces)

    def test_cmp162_headers_identify_the_arm_they_are_labelled_with(
        self, cmp162_manifest: dict, cmp162_root: Path
    ) -> None:
        """`preset` and `features` corroborate the arm the filename claims.

        The filename is written by the orchestrator — the code that was supposed
        to apply the configuration — so it is the claim, not the evidence. The
        header is the jar answering for itself, and this is the join that makes
        arm attribution checkable at all.
        """
        by_arm: dict[str, set[str]] = {}
        for relative in self._aperv_traces(cmp162_manifest):
            path = cmp162_root / relative
            if not path.exists():
                pytest.skip(f"{MISSING_REAL}: {relative}")

            reader = TraceReader(path)
            next(iter(reader), None)
            arm = path.name.rsplit("__", 1)[-1].removesuffix(".trace")
            by_arm.setdefault(arm, set()).update(reader.run_start.features)

            assert reader.run_start.preset, f"{relative}: no preset"

        assert set(by_arm) == {"aperv:mop_off_llm_off", "aperv:mop_on_llm_off"}
        for arm, features in by_arm.items():
            assert not any(
                name.startswith("LLM") for name in features
            ), f"{arm} is an llm_off arm, yet its headers declare {sorted(features)}"
        assert "MOP_FRONTIER" in by_arm["aperv:mop_on_llm_off"]
        assert "MOP_FRONTIER" not in by_arm["aperv:mop_off_llm_off"]


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
