"""
Tests for the offline coverage-dump parser (gh90 group 5, INV-APV-36/37).

The corpus tests run against the recorded iter0 traces as READ-ONLY fixtures —
3.5 GB of real runs, never modified, never regenerated. They are skipped when
that tree is absent (a checkout without the campaign data) rather than failing,
but they are the actual validation gate of the change: the recorded per-arm dump
presence, 462/800 overall, must reproduce exactly.
"""

import hashlib
from pathlib import Path

import pytest

from aperv_tool.analysis.coverage_dump import (
    DUMP_SCHEMA_VERSION,
    ActivityCoverage,
    DumpPresence,
    DumpStatus,
    StateCoverage,
    aggregate_activities,
    dump_presence,
    main,
    parse_run,
    parse_tree,
    presence_by_arm,
)

CORPUS = Path(__file__).resolve().parents[3] / "experimento-cal" / "iter0" / "results"

# A run whose teardown completed: one Activity, 31 states, dump intact.
COMPLETE_RUN = (
    CORPUS
    / "cala_04/cala_04/com.kin.easynotes_14.apk"
    / "com.kin.easynotes_14.apk__2__300__aperv:cal_a7.trace"
)
# A run killed before the dump — 47% of the corpus looks like this, which is the
# reason the parser reports absence instead of dropping the run.
ABSENT_RUN = (
    CORPUS
    / "cala_00/cala_00/at.linuxtage.Eventfahrplan_1700028.apk"
    / "at.linuxtage.Eventfahrplan_1700028.apk__1__300__aperv:cal_a1.trace"
)
# Two replicas of the same (APK, arm), both dumping: the pair that demonstrates
# why cross-run joins are Activity-grain only.
REPLICA_RUNS = [
    CORPUS
    / "cala_00/cala_00/at.linuxtage.Eventfahrplan_1700028.apk"
    / f"at.linuxtage.Eventfahrplan_1700028.apk__{rep}__300__aperv:cal_a4.trace"
    for rep in (1, 2)
]

requires_corpus = pytest.mark.skipif(
    not CORPUS.is_dir(), reason="recorded iter0 corpus not present in this checkout"
)

# Real dump lines, copied verbatim from the corpus. Note what they do NOT have:
# the `*** INFO *** ` infix that most APE output carries. They come from
# Logger.format, so a pattern anchored at the start of the line matches nothing.
STATE_LINE = (
    "[APE] [APE-RV] UICOV state=com.kin.easynotes.presentation.MainActivity"
    "@-1421630281@Naming[0]@[W=3] discovered=5 interacted=5 gap=0.0 "
    "byType=MODEL_BACK:1/1,MODEL_MENU:1/1,MODEL_CLICK:2/2,MODEL_LONG_CLICK:1/1 "
    "mopReach=1"
)
ACTIVITY_LINE = (
    "[APE] [APE-RV] UICOV-ACT activity=com.kin.easynotes.presentation.MainActivity "
    "discovered=42 interacted=32 gap=0.2 "
    "byType=MODEL_BACK:1/1,MODEL_MENU:1/1,MODEL_CLICK:24/33 liveStates=31"
)


def _write_trace(tmp_path, *lines, trailing_newline=True):
    """Write a synthetic trace file with APE-shaped surrounding noise."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "app.apk__1__300__aperv:cal_a1.trace"
    body = "[APE] *** INFO *** Let's wait for activity loading...\n" + "\n".join(lines)
    path.write_text(body + ("\n" if trailing_newline else ""))
    return path


class TestLineParsing:
    """Line shape, including the traps that make a plausible parser wrong."""

    def test_dump_lines_are_matched_without_the_info_infix(self, tmp_path):
        # The trap: every line is prefixed `[APE] `, and the dump lines lack the
        # `*** INFO *** ` the neighbouring lines carry. Matching the tag as a
        # substring is what makes both shapes reachable.
        run = parse_run(_write_trace(tmp_path, STATE_LINE, ACTIVITY_LINE))

        assert run.status is DumpStatus.COMPLETE
        assert len(run.states) == 1
        assert len(run.activities) == 1

    def test_activity_tag_is_not_swallowed_by_the_state_tag(self, tmp_path):
        # `UICOV` is a prefix of `UICOV-ACT`: testing the state tag first would
        # classify every Activity line as a malformed state line.
        run = parse_run(_write_trace(tmp_path, ACTIVITY_LINE))

        assert run.activities[0].activity.endswith("MainActivity")
        assert run.states == ()
        assert run.unparsed_lines == 0

    def test_state_key_with_embedded_equals_survives(self, tmp_path):
        # State keys carry `@[W=3]`, so tokenizing on `=` instead of partitioning
        # would truncate the key.
        run = parse_run(_write_trace(tmp_path, STATE_LINE))

        assert run.states[0].state_key.endswith("@Naming[0]@[W=3]")

    def test_by_type_is_interacted_over_discovered(self, tmp_path):
        # The field is TYPE:interacted/discovered, and reading it backwards would
        # silently invert every per-type figure.
        run = parse_run(_write_trace(tmp_path, ACTIVITY_LINE))

        activity = run.activities[0]
        assert activity.by_type["MODEL_CLICK"] == (24, 33)
        assert sum(i for i, _ in activity.by_type.values()) <= activity.interacted
        assert sum(d for _, d in activity.by_type.values()) <= activity.discovered

    def test_gap_is_not_a_computation_source(self):
        # `gap` carries one decimal under Locale.ROOT; discovered/interacted are
        # integers and are authoritative. The rounded field is not even stored.
        assert not hasattr(ActivityCoverage, "gap")
        assert "gap" not in ActivityCoverage.__dataclass_fields__
        assert "gap" not in StateCoverage.__dataclass_fields__

    def test_mop_reach_is_absent_at_activity_grain(self, tmp_path):
        # Task 5.4: mopReach is emitted on UICOV and not on UICOV-ACT. The
        # Activity row reports the absence as None instead of inferring a value.
        run = parse_run(_write_trace(tmp_path, STATE_LINE, ACTIVITY_LINE))

        assert run.states[0].mop_reach == 1
        assert run.activities[0].mop_reach is None

    def test_rows_carry_the_schema_version(self, tmp_path):
        run = parse_run(_write_trace(tmp_path, ACTIVITY_LINE))

        assert run.schema_version == DUMP_SCHEMA_VERSION


class TestDumpStatus:
    """INV-APV-37: every run reported, with an explicit status."""

    def test_truncated_tail_is_partial_and_keeps_earlier_lines(self, tmp_path):
        # Synthetic because the recorded corpus contains no truncated dump (see
        # the module's test report): the process was killed either before the
        # dump or after it, never mid-line.
        truncated = ACTIVITY_LINE[: ACTIVITY_LINE.index(" liveStates=")]
        path = _write_trace(
            tmp_path, STATE_LINE, ACTIVITY_LINE, truncated, trailing_newline=False
        )

        run = parse_run(path)

        assert run.status is DumpStatus.PARTIAL
        assert run.unparsed_lines == 1
        # Everything before the cut survives — discarding the run would throw
        # away complete measurements to punish an incomplete one.
        assert len(run.activities) == 1
        assert len(run.states) == 1

    def test_run_without_dump_is_reported_not_dropped(self, tmp_path):
        path = _write_trace(tmp_path, "[APE] *** INFO *** nothing to see here")

        run = parse_run(path)

        assert run.status is DumpStatus.ABSENT
        assert run.has_dump is False
        assert run.activities == () and run.states == ()

    def test_rate_carries_its_denominator(self):
        # A bare float is exactly how "coverage over the runs that dumped" became
        # "coverage over all runs" in the retracted 165/880 figure.
        presence = DumpPresence(runs_with_dump=462, runs_total=880)

        assert presence.runs_total == 880
        assert "462/880" in str(presence)
        assert presence.rate == pytest.approx(0.525, abs=0.001)

    def test_empty_input_rate_does_not_divide_by_zero(self):
        assert dump_presence([]).rate == 0.0


class TestActivityGrainOnly:
    """INV-APV-36: cross-run aggregation joins on Activity, never on state keys."""

    def test_aggregate_joins_on_activity_names(self, tmp_path):
        first = parse_run(_write_trace(tmp_path / "a", ACTIVITY_LINE))
        second = parse_run(_write_trace(tmp_path / "b", ACTIVITY_LINE))

        totals = aggregate_activities([first, second])

        assert list(totals) == ["com.kin.easynotes.presentation.MainActivity"]
        discovered, interacted, contributing = totals[
            "com.kin.easynotes.presentation.MainActivity"
        ]
        assert (discovered, interacted, contributing) == (84, 64, 2)

    def test_module_offers_no_cross_run_state_aggregation(self):
        # Structural, not documentary: there is no state-level counterpart to
        # aggregate_activities() for a caller to reach for by mistake.
        import aperv_tool.analysis.coverage_dump as module

        aggregators = {
            name
            for name in dir(module)
            if name.startswith("aggregate") and callable(getattr(module, name))
        }
        assert aggregators == {"aggregate_activities"}


@requires_corpus
class TestRecordedCorpus:
    """The validation gate: recorded iter0 traces, read-only."""

    def setup_method(self):
        self._digests = {}

    def _remember(self, path):
        self._digests[path] = hashlib.sha256(path.read_bytes()).hexdigest()

    def _assert_unchanged(self):
        for path, digest in self._digests.items():
            assert (
                hashlib.sha256(path.read_bytes()).hexdigest() == digest
            ), f"fixture modified: {path}"

    def test_complete_dump_from_a_recorded_run(self):
        self._remember(COMPLETE_RUN)

        run = parse_run(COMPLETE_RUN)

        assert run.status is DumpStatus.COMPLETE
        assert (run.apk, run.repetition, run.timeout_seconds, run.arm) == (
            "com.kin.easynotes_14.apk",
            2,
            300,
            "aperv:cal_a7",
        )
        assert len(run.states) == 31
        activity = run.activities[0]
        assert activity.activity == "com.kin.easynotes.presentation.MainActivity"
        assert (activity.discovered, activity.interacted) == (42, 32)
        assert activity.live_states == 31
        # byType decomposes the totals exactly on a complete line.
        assert sum(i for i, _ in activity.by_type.values()) == activity.interacted
        assert sum(d for _, d in activity.by_type.values()) == activity.discovered
        self._assert_unchanged()

    def test_recorded_run_without_a_dump_is_reported(self):
        self._remember(ABSENT_RUN)

        run = parse_run(ABSENT_RUN)

        assert run.status is DumpStatus.ABSENT
        assert run.arm == "aperv:cal_a1"
        self._assert_unchanged()

    def test_state_keys_never_pair_across_replicas(self):
        # The measured fact behind INV-APV-36: two replicas of the same (APK,
        # arm) share every Activity and not one state key, because the state key
        # embeds a JVM identity hash.
        for path in REPLICA_RUNS:
            self._remember(path)
        first, second = (parse_run(path) for path in REPLICA_RUNS)

        state_keys = [
            {state.state_key for state in run.states} for run in (first, second)
        ]
        activities = [{a.activity for a in run.activities} for run in (first, second)]

        assert state_keys[0] and state_keys[1]
        assert not (
            state_keys[0] & state_keys[1]
        ), "state keys must not pair across runs"
        assert activities[0] == activities[1]
        assert len(aggregate_activities([first, second])) == len(activities[0])
        self._assert_unchanged()

    def test_per_arm_presence_reproduces_iter0(self):
        # THE gate (task 5.6). The 12 cala_smoke_* runs are excluded: they ran at
        # timeout=90, so the denominator of the campaign is 880, of which the ten
        # aperv arms hold 800 (the `ape` arm emits no dump at all).
        runs = [run for run in parse_tree(CORPUS) if "smoke" not in str(run.trace_path)]
        assert len(runs) == 880

        aperv_runs = [run for run in runs if run.arm and run.arm.startswith("aperv:")]
        overall = dump_presence(aperv_runs)
        assert (overall.runs_with_dump, overall.runs_total) == (462, 800)

        per_arm = presence_by_arm(aperv_runs)
        assert len(per_arm) == 10
        assert all(presence.runs_total == 80 for presence in per_arm.values())
        rates = [presence.rate for presence in per_arm.values()]
        assert min(rates) == pytest.approx(0.438, abs=0.001)
        assert max(rates) == pytest.approx(0.650, abs=0.001)
        # The `ape` arm is the reason the step-level denominator is 800, not 880.
        assert dump_presence([run for run in runs if run.arm == "ape"]) == DumpPresence(
            runs_with_dump=0, runs_total=80
        )


class TestCli:
    """Usage errors are exit status 2, naming the path."""

    def test_missing_directory_is_usage_error(self, tmp_path, capsys):
        missing = tmp_path / "nope"

        with pytest.raises(SystemExit) as exit_info:
            main([str(missing)])

        assert exit_info.value.code == 2
        assert str(missing) in capsys.readouterr().err

    def test_wrong_argument_count_is_usage_error(self):
        with pytest.raises(SystemExit) as exit_info:
            main([])

        assert exit_info.value.code == 2

    def test_csv_row_per_run_including_the_ones_without_a_dump(self, tmp_path, capsys):
        _write_trace(tmp_path, ACTIVITY_LINE)
        (tmp_path / "other.apk__1__300__ape.trace").write_text("[APE] nothing\n")

        assert main([str(tmp_path)]) == 0

        stdout = capsys.readouterr().out.splitlines()
        assert stdout[0].startswith("apk,repetition,timeout,arm,status")
        assert len(stdout) == 3
        assert any(",absent," in row for row in stdout[1:])
        assert any(",complete," in row for row in stdout[1:])
