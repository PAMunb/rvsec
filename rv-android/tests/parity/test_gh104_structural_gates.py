"""The gate family of gh104, parametrised by specification set.

Nine structural and semantic gates (`scripts/gh104_gates.py`), the `.mop` lint
(`scripts/gh104_mop_lint.py`) and the message-property gate
(`scripts/gh104_message_gate.py`) run over each set of the change.

Two sets, two roles:

`jca` is the **fixture with known answers**. It is frozen, it produced the
published measurements, and every one of its hits was measured on 2026-08-16 and
recorded in `data/jca/gate_allowlist.csv` with a reason. A gate that reports
*fewer* hits on `jca` than the baseline is broken, not clean -- so the baseline
is asserted exactly rather than as an upper bound.

`jca_android` is the **subject**. Its expectations are computed from the set
rather than hard-coded: four of the frozen baseline's hits belong to
specifications the successor set does not carry, and writing a second constant
list would encode today's answer as tomorrow's requirement. Until Group 2 has
landed the set, the cases skip with a named reason and never pass silently.

Both cases read the generated monitor. The `jca` one reads the frozen control
snapshot of 2026-08-08 -- not `results/gh56-smoke/`, which predates the freeze by
three months and two source fixes -- and the `jca_android` one generates in
scratch.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "scripts"
CONTROL = REPO / "results/gh101_group8_jca_frozen_control/monitors"
MANIFEST = REPO / "data/gh104/jca_frozen_control.sha256"
# The oracle, singular since D-16 (2026-08-25, task 11.3). D-15 had split it in
# two -- the generated api30 rules for ORDER, alphabets and predicates, the pinned
# expert copy for values through a `--value-crysl` flag of its own -- after
# measuring that the generated value lists admitted MD5, SHA-1 and AES/ECB. D-16
# withdrew the generated catalogue from the remaining dimensions for the reason
# the design states, so the two flags collapsed into `--crysl` and this fixture
# loads one directory. The pin is by sha256, recorded as a freeze item of
# `data/jca_android/README.md` (INV-INS-125/127).
CRYSL = REPO.parent.parent / "RVSec-replication-package/tools/rules"

# Measured on 2026-08-16 against the frozen control monitor, and reproduced by
# every gate of `scripts/gh104_gates.py`. `G-2` is the count of
# `orphan-without-clause` verdicts, not of raw orphans: the raw count is 18, which
# does not move, and 16 of those carry a CrySL clause that accounts for them.
#
# `G-2` is 3 in the 2026-08-16 measurement and 2 here, and the difference is the
# substitution of oracle that task 11.3 made, not a gate that stopped looking. The
# orphan that moved is `SecretKeySpecSpec.c3`, whose `condition()` tests
# `keyAlgorithm` and `keyMaterial`: `MetaCrySL/generated/api30/SecretKeySpec.cryptsl`
# states no clause over either -- it dropped the algorithm membership its source had,
# which is the D-15 finding in its clearest form -- so no clause accounted for the
# event and G-2 called it a failure. `RVSec-replication-package/tools/rules/
# SecretKeySpec.crysl:18,20` states `keyAlgorithm in {"AES", "HmacSHA256",
# "HmacSHA384", "HmacSHA512"}` and `neverTypeOf[keyMaterial, java.lang.String]`, so
# the event is `orphan-with-clause` and moves from the hits to the notes. Nothing in
# the frozen set was touched: 3 + 15 and 2 + 16 are the same 18 raw orphans, which is
# why `JCA_RAW_ORPHANS` is asserted beside the split.
JCA_BASELINE = {
    "G-2": 2,
    "G-2a": 1,
    "G-2b'": 8,
    "G-2c": 1,
    "G-2d": 2,
    "G-6'": 1,
    "G-ERE": 1,
}
JCA_RAW_ORPHANS = 18
JCA_EXECUTION_CONTEXT = 134
JCA_LINT = {
    "three-argument-site": 25,
    "duplicate-event": 1,
    "undeclared-symbol": 1,
    "unbalanced": 1,
}
# `wrong-error-type` is 3 in the 2026-08-16 measurement and 4 here, for the same
# reason `G-2` is 2 rather than 3: the message gate classifies a report site by the
# clause family behind its event, through the same classifier G-2 uses. Under the
# withdrawn catalogue `SecretKeySpecSpec.mop:48` had no clause behind it at all and
# no family, so the gate had nothing to compare its `ErrorType` against; under the
# oracle it has `CONSTRAINTS-value`, and the site raises `UnsatisfiedConstraint`
# where a value clause asks for `UnsafeAlgorithm`. The finding is the frozen set's
# and predates this change -- `jca` may not be edited (task 8.2) -- so it is pinned
# here rather than repaired, exactly as the other three are.
JCA_MESSAGE = {"literal-mismatch": 2, "wrong-error-type": 4}


def _rvsec_home() -> Path:
    home = os.environ.get("RVSEC_HOME")
    if not home or not (Path(home) / "rvsec/rvsec-mop/src/main/resources/jca").is_dir():
        pytest.skip("RVSEC_HOME not set or the sibling Java reactor is absent")
    return Path(home)


def _set_dir(name: str) -> Path:
    path = _rvsec_home() / "rvsec/rvsec-mop/src/main/resources" / name
    if not path.is_dir():
        pytest.skip(f"the specification set {name} does not exist yet at {path}")
    return path


def _crysl() -> Path:
    if not CRYSL.is_dir():
        pytest.skip(f"the pinned expert rules are absent: {CRYSL}")
    return CRYSL


def _control_monitor() -> Path:
    """The frozen control snapshot, checked against Group 3's manifest when it exists.

    The order matters. An absent directory is a skip with its reason, because a
    developer without the artefact should be told how to get it. A directory that
    disagrees with the committed manifest is a *failure*, because a gate suite
    whose fixture moved is measuring something else and reporting the old name
    for it. Before the manifest lands there is nothing to disagree with, so the
    check is the skip and never a traceback.
    """
    monitor = CONTROL / "MultiSpec_1RuntimeMonitor.java"
    if not monitor.is_file():
        pytest.skip(
            "control directory absent: results/gh101_group8_jca_frozen_control/monitors; "
            "regenerate per data/gh104/README.md"
        )
    if MANIFEST.is_file():
        recorded = {}
        for line in MANIFEST.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            digest, name = line.split(maxsplit=1)
            recorded[name.strip().lstrip("*")] = digest.strip()
        mismatched = []
        for name, digest in sorted(recorded.items()):
            path = CONTROL / Path(name).name
            if not path.is_file():
                mismatched.append(f"{name}: absent")
                continue
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != digest:
                mismatched.append(f"{name}: {actual} != {digest}")
        assert not mismatched, (
            "the frozen control snapshot disagrees with "
            f"{MANIFEST.relative_to(REPO)}; the gate baselines below were measured against the "
            "recorded one:\n" + "\n".join(mismatched)
        )
    return monitor


# Generation costs about ninety seconds per set, and five cases of this file read
# the same monitor. Generating once per session is the difference between a gate
# suite that runs in the loop and one that nobody runs.
_GENERATED: dict[str, Path] = {}


def _generated_monitor(set_name: str) -> Path:
    """Generates a set's monitor into scratch, off tmpfs, and returns its path."""
    if set_name in _GENERATED:
        return _GENERATED[set_name]
    set_dir = _set_dir(set_name)
    scratch = Path(os.environ.get("TMPDIR", Path.home() / "tmp-gh104"))
    scratch.mkdir(parents=True, exist_ok=True)
    out = Path(tempfile.mkdtemp(prefix=f"gh104-{set_name}-", dir=scratch)) / "monitors"
    out.mkdir(parents=True)
    result = subprocess.run(
        [
            "uv",
            "run",
            "rv-monitor-generator",
            "generate",
            "--specs-dir",
            str(set_dir),
            "--output",
            str(out),
        ],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    monitor = out / "MultiSpec_1RuntimeMonitor.java"
    if not monitor.is_file():
        pytest.skip(f"monitor generation for {set_name} failed: {result.stderr[-500:]}")
    (out / "gh104_set.txt").write_text(str(set_dir), encoding="utf-8")
    _GENERATED[set_name] = monitor
    return monitor


def _gates_command(monitor: Path, allowlist: Path | None) -> list[str]:
    """The CLI invocation, built once so the report and the exit code agree.

    Two cases read this: the ones that parse the report, and the one that reads the
    exit code the CLI returns. They have to be the same invocation -- a suite that
    asserted green on a report built differently from the command a reader runs
    would be measuring an artefact of its own construction.
    """
    command = [
        sys.executable,
        str(SCRIPTS / "gh104_gates.py"),
        "--monitor",
        str(monitor),
        "--crysl",
        str(_crysl()),
        "--alias",
        str(REPO / "data/jca_android/alias_table.csv"),
        "--constraint-table",
        str(REPO / "data/jca_android/constraint_table.csv"),
    ]
    if allowlist and allowlist.is_file():
        command += ["--allowlist", str(allowlist)]
    return command


def _gates(monitor: Path, allowlist: Path | None) -> dict:
    result = subprocess.run(
        _gates_command(monitor, allowlist), capture_output=True, text=True, check=False
    )
    assert result.stdout, result.stderr
    return json.loads(result.stdout)


def _lint(set_name: str) -> dict:
    command = [
        sys.executable,
        str(SCRIPTS / "gh104_mop_lint.py"),
        str(_set_dir(set_name)),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    assert result.stdout, result.stderr
    return json.loads(result.stdout)


def _message_gate(set_name: str) -> dict:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "gh104_message_gate.py"),
            str(_set_dir(set_name)),
            "--crysl",
            str(_crysl()),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.stdout, result.stderr
    return json.loads(result.stdout)


# --------------------------------------------------------------------------
# jca -- the fixture with known answers
# --------------------------------------------------------------------------


def test_jca_gates_reproduce_the_measured_baseline():
    """Exactly the 2026-08-16 counts. Fewer means the gate stopped looking."""
    report = _gates(_control_monitor(), None)
    counts = {name: gate["count"] for name, gate in report["gates"].items()}
    for gate, expected in JCA_BASELINE.items():
        assert counts[gate] == expected, (
            f"{gate} reported {counts[gate]} on the frozen `jca`, and the measured baseline is "
            f"{expected}: {report['gates'][gate]['hits']}"
        )


def test_jca_g2_splits_eighteen_orphans_into_sixteen_notes_and_two_failures():
    """The correction G-2 exists for: 16 of the 18 are correct encodings.

    `CONSTRAINTS`, `REQUIRES` and `FORBIDDEN` are per-call predicates and name no
    position in the `ORDER`, so an event that encodes one has no place in the
    automaton and the generator gives it an all-`fail` row. Reading those as
    defects buries the one hit that is real.

    The split was 15/3 while the generated api30 catalogue was the oracle, and the
    raw 18 is asserted beside it so that the substitution task 11.3 made reads as a
    re-classification and not as a gate that stopped counting.
    `SecretKeySpecSpec.c3` crossed the line because the expert rule states the two
    clauses the generated one had lost; the comment on `JCA_BASELINE` carries the
    lines.
    """
    report = _gates(_control_monitor(), None)
    gate = report["gates"]["G-2"]
    assert gate["orphans_raw"] == JCA_RAW_ORPHANS
    assert len(gate["notes"]) == 16, [note["event"] for note in gate["notes"]]
    assert {(hit["spec"], hit["event"]) for hit in gate["hits"]} == {
        ("MessageDigestSpec", "reset"),
        ("PBEKeySpecSpec", "err2"),
    }
    for note in gate["notes"]:
        assert note[
            "clause"
        ], f"{note['spec']}.{note['event']} cleared without naming a clause"


def test_jca_g_ere_finds_the_gcm_symbol_and_nothing_else():
    report = _gates(_control_monitor(), None)
    hits = report["gates"]["G-ERE"]["hits"]
    assert [(hit["spec"], hit["event"], hit["line"]) for hit in hits] == [
        ("GCMParameterSpecSpec", "c2", 48)
    ]


def test_jca_g_pred_counts_the_sites_the_successor_must_carry():
    """134 `ExecutionContext` sites: what the successor set is checked against.

    The seed is its own oracle here, so the gate reports no failure; what the test
    pins is the census behind it. If this number ever moves, the frozen `jca` has
    been edited and every measurement published from it is in question.
    """
    report = _gates(_control_monitor(), None)
    assert report["gates"]["G-PRED"]["predicate_sites"] == JCA_EXECUTION_CONTEXT
    assert report["gates"]["G-PRED"]["failures"] == []
    # And the gate still governs the seed. It withdraws from a set that has migrated
    # off `ExecutionContext` onto the store, which is `jca_android` and never this
    # one; a supersession here would mean the lock had been lifted from the frozen
    # control by a scoping rule written for its successor.
    assert report["superseded"] == []


def test_no_file_of_the_frozen_set_names_the_alias_class():
    """INV-INS-112: the frozen set's verdicts stay under its own control.

    A shared alias class named by both sets would put the published `jca`
    measurements under the control of a table edited for Android, and no
    reproduction of them would be possible afterwards.
    """
    report = _gates(_control_monitor(), None)
    assert report["gates"]["G-CONF"]["names_alias_class_in_jca"] == []


def test_jca_gates_pass_with_the_allowlist():
    report = _gates(_control_monitor(), REPO / "data/jca/gate_allowlist.csv")
    failures = {
        name: gate["failures"]
        for name, gate in report["gates"].items()
        if gate["failures"]
    }
    assert report["ok"], failures


def test_jca_lint_reports_the_measured_baseline():
    counts = _lint("jca")["counts"]
    assert counts == JCA_LINT, counts


def test_jca_carries_no_hand_written_event_name_bookkeeping():
    """INV-INS-120: the seed has none, and it must keep none.

    The generator emits the event name now. A hand-written index table beside it
    is a second source of truth that desynchronises under any edit of the
    alphabet, and the failure is silent because the wrong name is still a name.
    """
    findings = _lint("jca")["findings"]
    assert [hit for hit in findings if hit["kind"] == "hand-written-name"] == []


def test_jca_message_gate_reports_the_measured_baseline():
    """The frozen set's four wrong `ErrorType`s and two literal mismatches.

    The sites are pinned and not only the counts, because a count that stayed at
    four while one finding closed and another opened would report the same number
    for a different set of defects. `SecretKeySpecSpec.mop:48` is the fourth from
    task 11.3 and the comment on `JCA_MESSAGE` says why; the other three are the
    2026-08-16 measurement unchanged.
    """
    report = _message_gate("jca")
    assert report["counts"] == JCA_MESSAGE, report["counts"]

    sites = {
        (hit["file"], hit["line"])
        for hit in report["findings"]
        if hit["kind"] == "literal-mismatch"
    }
    assert sites == {
        ("PBEKeySpecSpec.mop", 49),
        ("PBEParameterSpecSpec.mop", 49),
    }, sites

    wrong = {
        (hit["file"], hit["line"])
        for hit in report["findings"]
        if hit["kind"] == "wrong-error-type"
    }
    assert wrong == {
        ("PBEKeySpecSpec.mop", 24),
        ("PBEKeySpecSpec.mop", 30),
        ("PBEParameterSpecSpec.mop", 49),
        ("SecretKeySpecSpec.mop", 48),
    }, wrong


def test_jca_declares_the_guard_on_field_sites():
    """The nine specifications E1 changes, and the reason the envelope flag is zero here.

    Every guard-on-field site of the frozen set reports the same field it guards,
    so the envelope reads `but found .` rather than a value inside its own
    expected list. The flag fires on `jca_android` once E1 makes the message
    report the object's algorithm, and goes to zero again when E4 task 8.16 moves
    the guard with it.
    """
    report = _message_gate("jca")
    specs = {
        note["spec"] for note in report["notes"] if note["kind"] == "guard-on-field"
    }
    assert specs == {
        "CipherSpec",
        "KeyGeneratorSpec",
        "KeyManagerFactorySpec",
        "KeyStoreSpec",
        "MacSpec",
        "MessageDigestSpec",
        "SSLContextSpec",
        "SignatureSpec",
        "TrustManagerFactorySpec",
    }, specs
    assert [
        hit
        for hit in report["findings"]
        if hit["kind"] == "self-contradicting envelope"
    ] == []


# --------------------------------------------------------------------------
# jca_android -- the subject, with expectations computed from the set
# --------------------------------------------------------------------------


def test_jca_android_has_no_orphan_without_a_clause():
    """The target of E4. Skipped, never passed, while the set is not in the tree."""
    report = _gates(
        _generated_monitor("jca_android"), REPO / "data/jca_android/gate_allowlist.csv"
    )
    assert report["gates"]["G-2"]["failures"] == []


def test_jca_android_has_no_inert_event_without_a_row():
    """G-2a over the successor, the assertion whose absence let the CLI stay red.

    The suite asserted G-2, G-ERE, G-6', the lint, the message gate and G-CONF for
    this set and never G-2a, so four hits with no covering row -- `PBEKeySpecSpec`'s
    two forbidden constructors, `SSLContextSpec.getDefault` and `SecureRandomSpec.g4`,
    every one of them an accuser absorbed into the automaton as a self-loop by a task
    of this change -- lived in the CLI's exit code and nowhere else. Every inert event
    of this set is a decision, and a decision that is not in `gate_allowlist.csv` with
    a reason is indistinguishable from an oversight: that is what this asserts, and it
    is what keeps the two instruments from diverging again.
    """
    report = _gates(
        _generated_monitor("jca_android"), REPO / "data/jca_android/gate_allowlist.csv"
    )
    assert report["gates"]["G-2a"]["failures"] == []


def test_jca_android_has_no_undeclared_ere_symbol():
    report = _gates(
        _generated_monitor("jca_android"), REPO / "data/jca_android/gate_allowlist.csv"
    )
    assert report["gates"]["G-ERE"]["failures"] == []


def test_jca_android_event_names_survive_generation():
    """G-6': one generated event method per transition row."""
    report = _gates(
        _generated_monitor("jca_android"), REPO / "data/jca_android/gate_allowlist.csv"
    )
    assert report["gates"]["G-6'"]["failures"] == []


def test_jca_android_lint_is_clean():
    report = _lint("jca_android")
    assert report["counts"] == {}, report["counts"]


def test_jca_android_message_gate_is_clean():
    report = _message_gate("jca_android")
    assert report["counts"] == {}, report["counts"]


def test_jca_android_allow_lists_conform_to_the_expert_rules():
    """G-CONF: INV-INS-127, with every difference backed by a recorded row.

    From D-15 the oracle is the pinned expert copy, not the generated api30
    rules. The assertion is unchanged -- no unbacked difference -- but what
    counts as a difference moved: the api30 lists admitted MD5, SHA-1, ARC4,
    NONEwithRSA and AES/ECB, and the expert lists do not. D-16 extended that copy
    to every other dimension, so from task 11.3 the invocation above passes it
    once, as `--crysl`, and this gate reads what every other gate reads.
    """
    report = _gates(
        _generated_monitor("jca_android"), REPO / "data/jca_android/gate_allowlist.csv"
    )
    assert report["gates"]["G-CONF"]["failures"] == []


def test_jca_android_gates_exit_zero_and_say_which_gate_withdrew():
    """The CLI's own verdict over the successor, which no case read before.

    Every assertion above reads one gate's failure list out of the report, and the
    exit code -- the thing a reader, a hook or a CI step actually consults -- was
    covered by none of them. It had been 1 for the whole of this change: G-PRED
    compares each file against the frozen seed's `ExecutionContext` lines, the set
    has none left by construction (INV-INS-130), and its 23 structural failures were
    summed into `ok` all the same. A red that cannot go green is not a gate, and the
    reader who learns to ignore one learns to ignore the others with it.

    So this asserts the whole verdict and the shape behind it: exit 0, nothing
    skipped -- a missing input is still not a pass -- and G-PRED reported as
    withdrawn from this set with the successor named in writing, rather than quietly
    absent from the report.
    """
    result = subprocess.run(
        _gates_command(
            _generated_monitor("jca_android"),
            REPO / "data/jca_android/gate_allowlist.csv",
        ),
        capture_output=True,
        text=True,
        check=False,
    )
    report = json.loads(result.stdout)
    failures = {
        name: gate["failures"]
        for name, gate in report["gates"].items()
        if gate["failures"]
    }
    assert result.returncode == 0, (failures, report["skipped"])
    assert report["skipped"] == []
    assert "predicate_graph.csv" in report["gates"]["G-PRED"]["superseded"]
    assert report["superseded"] == [report["gates"]["G-PRED"]["superseded"]]
