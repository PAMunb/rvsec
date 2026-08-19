"""One record per step, with every logcat stream placed by the one rule.

The tests below defend three properties that are easy to lose and hard to notice
losing. **One placement rule**: the violation stream, the executed-method stream
and the diagnostic stream are placed by `clock_logcat_join.place_on_timeline`, and
a structural test greps the package to keep the loop in one file — a second copy
would pass every behavioural test here and disagree with the first on some run
nobody looks at. **The heartbeat gap is a number**: a step whose heartbeat never
reached the file is named, and its window's events are attributed to the previous
heartbeat with a flag rather than dropped or invented. **A run with no heartbeat
is reported, not repaired**: its lines come back counted as `UNALIGNED`.

The synthetic runs are written as the jar writes them, so the reader is exercised
on its real grammar. The campaign checks are gated on the pinned tree and assert
against the manifest's measured figures, never against a literal.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fixture_gate import MISSING_REAL

from aperv_tool.analysis import clock_logcat_join, step_bundle
from aperv_tool.analysis.step_bundle import DIAGNOSTIC_STREAM, bundle_run

MONITORED_OP_TAG = "RVSEC-COV"
VIOLATION_TAG = "RVSEC"

# Epoch base of the synthetic runs, and one step per second. Only differences
# between logcat stamps matter to placement, so the wall clock below and the
# epoch base agree by construction rather than by coincidence.
T0_MS = 1784850137964
STEP_INTERVAL_MS = 1000
BASE_SECOND = 17
BASE_MINUTE = 42
BASE_HOUR = 20

ACTIVITY = "com.example.MainActivity"

# One real payload of each stream, kept verbatim from the recorded corpus: the
# violation message contains commas, and the executed-method payload is a full
# Soot signature with an angle-bracketed method name.
VIOLATION_PAYLOAD = (
    "SSLContextSpec,okhttp3.internal.platform.Platform,Platform,"
    "newSslSocketFactory,Platform.kt:168,UnsafeProtocol,"
    "expecting one of {TLSv1.2, TLSv1.3} but found TLS."
)
SIGNATURE = "<io.keepalive.android.AppController: void <clinit>()>"


def _at(step_index: int, millis: int = 964) -> tuple[int, int, int, int]:
    """Wall clock inside the window of step `step_index` (zero-based).

    A heartbeat is written at `964` ms, so a line at a later millisecond of the
    same second belongs to that step and a line at an earlier one belongs to its
    predecessor. Several tests turn on exactly that ordering.
    """
    total = BASE_MINUTE * 60 + BASE_SECOND + step_index
    return (BASE_HOUR + total // 3600, (total % 3600) // 60, total % 60, millis)


def _line(
    clock: tuple[int, int, int, int], tag: str, payload: str, level: str = "V"
) -> str:
    hour, minute, second, millis = clock
    padded = tag if len(tag) >= 8 else tag.ljust(8)
    return (
        f"07-23 {hour:02d}:{minute:02d}:{second:02d}.{millis:03d}  "
        f"3035  3035 {level} {padded}: {payload}"
    )


def _heartbeat(step_index: int) -> str:
    return _line(
        _at(step_index),
        "ApeRvHb",
        f"s={step_index + 1} t={step_index * STEP_INTERVAL_MS}",
    )


def _step(step_index: int) -> str:
    return json.dumps(
        {
            "s": step_index + 1,
            "t": step_index * STEP_INTERVAL_MS,
            "act": 1,
            "st": 1,
            "dec": {
                "a": "g0a0@MODEL_CLICK class=android.view.View",
                "src": "Coverage",
                "ch": "roulette_greedy",
                "pri": 100,
            },
        },
        separators=(",", ":"),
    )


def _write_run(
    directory: Path,
    *,
    steps: int,
    heartbeat_steps: list[int] | None = None,
    logcat_lines: list[str] | None = None,
    dump_states: list[str] | None = None,
    name: str = "app.apk__1__300__aperv:mop_on_llm_off",
    ndjson: bool = True,
) -> Path:
    """Write a synthetic `(.trace, .logcat)` pair, as the jar writes them.

    `heartbeat_steps` defaults to every step; passing a shorter list is how a run
    with a heartbeat gap is produced. `ndjson=False` writes the free-text-only
    trace a baseline tool leaves behind.
    """
    directory.mkdir(parents=True, exist_ok=True)
    header = [
        json.dumps(
            {
                "type": "RUN_START",
                "v": 1,
                "run_id": name,
                "t0": T0_MS,
                "params": {},
            },
            separators=(",", ":"),
        ),
        "[APE] *** INFO *** Let's wait for activity loading...",
        json.dumps(
            {"type": "ACT", "id": 1, "name": ACTIVITY, "mop": 0}, separators=(",", ":")
        ),
        json.dumps(
            {"type": "STATE", "id": 1, "key": "S1", "act": 1}, separators=(",", ":")
        ),
    ]
    body = [_step(index) for index in range(steps)]
    dump = [
        f"[APE-RV] UICOV state={key} discovered=4 interacted=2 "
        "byType=MODEL_CLICK:2/4 mopReach=0"
        for key in (dump_states or [])
    ]
    trace = directory / f"{name}.trace"
    if ndjson:
        trace.write_text("\n".join([*header, *body, *dump]) + "\n")
    else:
        trace.write_text(
            "\n".join(["[APE] *** INFO *** SATA begin step [1]", *dump]) + "\n"
        )

    beats = range(steps) if heartbeat_steps is None else heartbeat_steps
    lines = [_heartbeat(index) for index in beats]
    lines.extend(logcat_lines or [])
    (directory / f"{name}.logcat").write_text(
        "--------- beginning of main\n" + "\n".join(sorted(lines)) + "\n"
    )
    return trace


def test_rvsec_cov_placed_same_rule(tmp_path: Path) -> None:
    """An executed-method line lands on the step that was executing, as a violation does.

    Both streams are placed by the same imported rule, so the check is that the
    two agree: an execution and a violation written between the same two
    heartbeats belong to the same step, and `clock_logcat_join`'s own output for
    the run is unchanged by any of this.
    """
    between_seven_and_eight = _at(6, 990)
    trace = _write_run(
        tmp_path,
        steps=10,
        logcat_lines=[
            _line(between_seven_and_eight, MONITORED_OP_TAG, SIGNATURE),
            _line(between_seven_and_eight, VIOLATION_TAG, VIOLATION_PAYLOAD),
        ],
    )

    bundles, report = bundle_run(trace)
    by_step = {bundle.row.step: bundle for bundle in bundles}

    assert [op.signature for op in by_step[7].monitored_ops] == [SIGNATURE]
    assert by_step[7].violations[0].violation_type == "UnsafeProtocol"
    assert report.placed_by_tag[MONITORED_OP_TAG] == 1
    assert sum(len(bundle.monitored_ops) for bundle in bundles) == 1

    # The shipped join reads the same file and must reach the same step.
    joined = clock_logcat_join.join_run(trace)
    assert [violation.step for violation in joined.violations] == [7]
    assert joined.violation_lines == 1


def test_heartbeat_gap_counted(tmp_path: Path) -> None:
    """262 steps against 261 heartbeats: the gap is named and its events are kept."""
    missing = 100
    heartbeats = [index for index in range(262) if index + 1 != missing]
    during_the_missing_step = _at(missing - 1, 990)
    trace = _write_run(
        tmp_path,
        steps=262,
        heartbeat_steps=heartbeats,
        logcat_lines=[
            _line(during_the_missing_step, VIOLATION_TAG, VIOLATION_PAYLOAD),
        ],
    )

    bundles, report = bundle_run(trace)

    assert report.steps == 262
    assert report.heartbeats == 261
    assert report.heartbeat_gap == 1
    assert report.steps_without_heartbeat == (missing,)

    by_step = {bundle.row.step: bundle for bundle in bundles}
    # The step with no heartbeat still has a bundle, flagged as having none, and
    # the events of its window are attributed to the preceding heartbeat — which
    # says so, so the attribution is readable rather than assumed.
    assert by_step[missing].heartbeat is False
    assert by_step[missing].violations == ()
    assert by_step[missing - 1].absorbs_steps == (missing,)
    assert len(by_step[missing - 1].violations) == 1
    assert report.placed_by_tag[VIOLATION_TAG] == 1
    assert report.unaligned_by_tag[VIOLATION_TAG] == 0


def test_unaligned_not_repaired(tmp_path: Path) -> None:
    """No heartbeat in the file means no placement, and the run is still reported."""
    trace = _write_run(
        tmp_path,
        steps=4,
        heartbeat_steps=[],
        logcat_lines=[
            _line(_at(2, 990), VIOLATION_TAG, VIOLATION_PAYLOAD),
            _line(_at(2, 990), MONITORED_OP_TAG, SIGNATURE),
        ],
    )

    bundles, report = bundle_run(trace)

    assert len(bundles) == 4
    assert all(bundle.violations == () for bundle in bundles)
    assert report.heartbeats == 0
    assert report.unaligned_by_tag[VIOLATION_TAG] == 1
    assert report.unaligned_by_tag[MONITORED_OP_TAG] == 1
    assert report.placed_by_tag[VIOLATION_TAG] == 0
    # Nothing is lost: every line read is in exactly one counter.
    for tag in step_bundle.STREAMS:
        assert report.lines_by_tag[tag] == (
            report.placed_by_tag[tag]
            + report.unaligned_by_tag[tag]
            + report.outside_window_by_tag[tag]
            + report.placed_without_row_by_tag[tag]
        )


def test_events_outside_the_window_are_counted_not_forced(tmp_path: Path) -> None:
    """A line before the first step is neither dropped nor pinned to step 1."""
    before = _at(0, 100)
    trace = _write_run(
        tmp_path,
        steps=3,
        logcat_lines=[_line(before, VIOLATION_TAG, VIOLATION_PAYLOAD)],
    )

    bundles, report = bundle_run(trace)

    assert sum(len(bundle.violations) for bundle in bundles) == 0
    assert report.outside_window_by_tag[VIOLATION_TAG] == 1
    assert report.lines_by_tag[VIOLATION_TAG] == 1


def test_uicov_payload_rides_the_bundle(tmp_path: Path) -> None:
    """The teardown dump reaches the step, flagged for the run-wide thing it is."""
    trace = _write_run(tmp_path, steps=3, dump_states=["S1"])

    bundles, report = bundle_run(trace)

    assert all(bundle.uicov is not None for bundle in bundles)
    assert bundles[0].uicov.discovered == 4
    assert report.uicov is not None and report.uicov.total
    frame = step_bundle.frame(bundles)
    assert set(frame["uicov_scope"]) == {"cumulative_per_run"}


def test_diagnostics_come_from_the_shared_parser(tmp_path: Path) -> None:
    """A crash block is assembled by `rv_coverage`'s parser and placed like the rest."""
    crash_clock = _at(1, 990)
    trace = _write_run(
        tmp_path,
        steps=4,
        logcat_lines=[
            _line(crash_clock, "AndroidRuntime", "FATAL EXCEPTION: main", "E"),
            _line(
                crash_clock, "AndroidRuntime", "Process: com.example, PID: 3035", "E"
            ),
            _line(
                crash_clock,
                "AndroidRuntime",
                "java.lang.NullPointerException: boom",
                "E",
            ),
            _line(
                crash_clock,
                "AndroidRuntime",
                "at com.example.Main.go(Main.java:9)",
                "E",
            ),
        ],
    )

    bundles, report = bundle_run(trace)

    assert report.diagnostics_read
    placed = [event for bundle in bundles for event in bundle.diagnostics]
    assert [event.category for event in placed] == ["crash"]
    assert placed[0].class_full_name == "java.lang.NullPointerException"
    assert report.placed_by_tag[DIAGNOSTIC_STREAM] == 1


def test_diagnostics_off_is_reported_not_silent(tmp_path: Path) -> None:
    """An empty diagnostic stream must never read as 'the run had none'."""
    trace = _write_run(tmp_path, steps=2)

    _, report = bundle_run(trace, diagnostics=False)

    assert report.diagnostics_read is False
    assert report.lines_by_tag[DIAGNOSTIC_STREAM] == 0


def test_missing_logcat_keeps_the_run(tmp_path: Path) -> None:
    """A run whose log was not retained still yields its steps."""
    trace = _write_run(tmp_path, steps=3)
    trace.with_suffix(".logcat").unlink()

    bundles, report = bundle_run(trace)

    assert len(bundles) == 3
    assert report.logcat_present is False
    assert report.heartbeats == 0


def test_a_trace_with_no_ndjson_yields_no_bundles(tmp_path: Path) -> None:
    """The synthetic form of the baseline case: no step records, no bundles."""
    trace = _write_run(tmp_path, steps=0, ndjson=False, name="app.apk__1__300__ape")

    bundles, report = bundle_run(trace)

    assert bundles == []
    assert report.steps == 0


def test_placement_exists_once() -> None:
    """The heartbeat placement loop lives in one file, and this module imports it."""
    analysis = Path(clock_logcat_join.__file__).parent
    carriers = sorted(
        path.name
        for path in analysis.rglob("*.py")
        if "last heartbeat at or before" in path.read_text(encoding="utf-8")
    )

    assert carriers == ["clock_logcat_join.py"]

    source = (analysis / "step_bundle.py").read_text(encoding="utf-8")
    assert "place_on_timeline" in source
    assert "from aperv_tool.analysis.clock_logcat_join import" in source


def test_ape_arm_yields_zero_bundles(cmp162_root: Path, cmp162_manifest: dict) -> None:
    """A recorded baseline run produces no bundles — a measurement, not a failure."""
    relative = next(
        (
            name
            for name in sorted(cmp162_manifest["files"])
            if name.endswith("__ape.trace")
        ),
        None,
    )
    if relative is None:
        pytest.skip(f"{MISSING_REAL}: no baseline trace pinned in the manifest")
    trace = cmp162_root / relative
    if not trace.is_file():
        pytest.skip(f"{MISSING_REAL}: {relative}")

    bundles, report = bundle_run(trace, diagnostics=False)

    assert bundles == []
    assert report.steps == 0
    # The baseline jar writes no heartbeat either, so whatever the monitors did
    # log is counted as unplaceable rather than attached to a step that does not
    # exist.
    assert report.heartbeats == 0
    assert (
        report.unaligned_by_tag[MONITORED_OP_TAG]
        == report.lines_by_tag[MONITORED_OP_TAG]
    )


def test_cmp162_heartbeat_gap(cmp162_root: Path, cmp162_manifest: dict) -> None:
    """The campaign's own step⇄heartbeat arithmetic, from the manifest.

    The measured basis carries one more step than it does heartbeats. The
    expectation is the manifest's; this test only checks that the reader recovers
    it, and it names the run and step that lack one instead of reporting a total.
    """
    figures = cmp162_manifest["measured_figures"]
    steps = 0
    heartbeats = 0
    gaps: list[tuple[str, tuple[int, ...]]] = []
    for relative in figures["traces"]:
        trace = cmp162_root / relative
        if not trace.is_file():
            pytest.skip(f"{MISSING_REAL}: {relative}")
        _, report = bundle_run(trace, diagnostics=False)
        steps += report.steps
        heartbeats += report.heartbeats
        if report.steps_without_heartbeat:
            gaps.append((trace.name, report.steps_without_heartbeat))

    assert steps == figures["steps"]
    assert heartbeats == figures["heartbeats"]
    assert steps - heartbeats == figures["heartbeat_gap"]
    assert len(gaps) == figures["heartbeat_gap"]


ENVELOPE_PAYLOAD = (
    "MessageDigestSpec,okio.ByteString,ByteString,digest$okio,ByteString.kt:12,"
    "UnsafeAlgorithm,v=1 code=MESSAGEDIGEST-ALG-01 ev=update obj=MessageDigest "
    "val='MD2' exp='MD5,SHA-224,SHA-256,SHA-1,SHA-512,SHA-384' "
    "msg='expecting one of MD5,SHA-224,SHA-256,SHA-1,SHA-512,SHA-384 but found MD2'"
)

TRUNCATED_PAYLOAD = (
    "CipherSpec,com.example.Crypto,Crypto,doEncrypt,Crypto.java:15,UnsafeAlgorithm,"
    "v=1 code=CIPHER-ALG-02 ev=c1 obj=Cipher val='AES/ECB/PKCS5Padding' "
    "exp='AES/GCM/NoPadding,AES/CBC/PKCS7Pad"
)


def test_one_payload_parser_on_the_step_timeline_and_in_the_run_join(
    tmp_path: Path,
) -> None:
    """The envelope's fields reach the bundle, and the shipped join reports the same
    event at the same step: both decompose the payload through
    `violations.parse_payload`, so they cannot disagree about what a line said."""
    between_three_and_four = _at(2, 990)
    trace = _write_run(
        tmp_path,
        steps=10,
        logcat_lines=[_line(between_three_and_four, VIOLATION_TAG, ENVELOPE_PAYLOAD)],
    )

    bundles, report = bundle_run(trace)
    by_step = {bundle.row.step: bundle for bundle in bundles}
    (event,) = by_step[3].violations

    assert event.code == "MESSAGEDIGEST-ALG-01"
    assert event.event == "update"
    assert event.obj == "MessageDigest"
    assert event.exp == "MD5,SHA-224,SHA-256,SHA-1,SHA-512,SHA-384"
    assert event.shape_ok is True
    assert report.violations.envelope_malformed == 0
    assert report.violations.envelope_truncated == 0

    joined = clock_logcat_join.join_run(trace)
    assert [violation.step for violation in joined.violations] == [3]
    assert joined.violations[0].violation_type == "UnsafeAlgorithm"
    assert joined.violations[0].message.startswith("v=1 ")


def test_a_discarded_line_is_a_number_on_the_bundle(tmp_path: Path) -> None:
    """A step whose lines were cut short must not read as a step that had none
    (INV-CAN-04/25/26): the run's reader counters ride on the report."""
    trace = _write_run(
        tmp_path,
        steps=10,
        logcat_lines=[
            _line(_at(2, 990), VIOLATION_TAG, TRUNCATED_PAYLOAD),
            _line(_at(4, 990), VIOLATION_TAG, "SomeSpec,went into an error state"),
        ],
    )

    bundles, report = bundle_run(trace)
    by_step = {bundle.row.step: bundle for bundle in bundles}

    assert report.violations is not None
    assert report.violations.lines == 2
    assert report.violations.envelope_truncated == 1
    assert report.violations.shape_bad == 1
    assert report.violations.envelope_malformed == 0
    # Both lines are still violations and still on the timeline.
    assert len(by_step[3].violations) == 1
    assert by_step[3].violations[0].code == "CIPHER-ALG-02"
    assert len(by_step[5].violations) == 1
