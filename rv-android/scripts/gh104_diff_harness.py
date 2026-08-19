#!/usr/bin/env python3
"""Replay a file of traces through two specification-set snapshots and classify the difference.

    unchanged   neither snapshot accuses the trace, or both accuse it at the same event
    moved       both accuse it, at different events
    removed     the first accuses it and the second does not
    introduced  the second accuses it and the first does not

A static gate measures the artefact. This measures what the artefact does, which is the only
way to see the two failures the lineage shipped as successes: gh100's wrapper merge, which
removed twelve silently discarded wrappers and reported `wrappersGenerated 96 -> 84`; and
gh101's automaton repairs, which removed eighteen all-`fail` rows and moved the accusation to
the call that follows. Both are invisible to a gate that counts rows.

The report also flags, per trace and on either side, an envelope whose observed value appears in
the expected list it is accused of missing -- the `self-contradicting envelope` the message gate
finds statically. That is what makes the guard-on-field sites visible before they are repaired:
a site whose guard reads a monitor field and whose message reports the object's own algorithm
can accuse `SHA-256` of not being one of `{SHA-256, SHA-384, SHA-512}`.

Usage:
    gh104_diff_harness.py --a <set A> --b <set B> --traces data/gh104/traces \\
                          --out data/gh104/evidence/harness --group s
    gh104_diff_harness.py --selftest        # writes a mutant of `jca` in scratch and runs it

Both sides are generated in scratch by `rv-monitor-generator`, so neither call touches a
committed monitor; `TraceRunner` (rvsec-mop, test scope) compiles and replays each.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REACTOR = REPO.parent
RVSEC_MOP = REACTOR / "rvsec/rvsec-mop"
TEST_CLASSES = RVSEC_MOP / "target/test-classes"
CLASSPATH_FILE = RVSEC_MOP / "target/gh104-classpath.txt"

# `val` inside `exp`: `expecting one of A,B,C but found B.`
ENVELOPE = re.compile(r"expecting (?:one of|at least)?\s*\{?([^}]*?)\}?\s*but found\s+(.*?)\.?\s*$")


def scratch_root() -> Path:
    """Off tmpfs: monitor generation writes hundreds of megabytes of intermediates."""
    root = Path(os.environ.get("TMPDIR", Path.home() / "tmp-gh104"))
    root.mkdir(parents=True, exist_ok=True)
    return root


# --------------------------------------------------------------------------
# generation and replay
# --------------------------------------------------------------------------


def generate(set_dir: Path, out_dir: Path) -> Path:
    """Generates the monitor of a specification set into a scratch directory."""
    out_dir.mkdir(parents=True, exist_ok=True)
    command = [
        "uv",
        "run",
        "rv-monitor-generator",
        "generate",
        "--specs-dir",
        str(set_dir),
        "--output",
        str(out_dir),
    ]
    monitor = out_dir / "MultiSpec_1RuntimeMonitor.java"
    # The generator probes the javamop launcher with a ten-second budget before it starts, and
    # a cold JVM on a loaded machine misses it. One retry costs a few seconds and removes a
    # failure that says nothing about the specifications.
    for attempt in range(2):
        result = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
        if monitor.is_file():
            break
    if not monitor.is_file():
        raise RuntimeError(
            f"monitor generation from {set_dir} produced no MultiSpec_1RuntimeMonitor.java\n"
            f"{result.stdout[-4000:]}\n{result.stderr[-4000:]}"
        )
    # The gates derive the `.mop` directory from the monitor rather than taking it on the
    # command line, so a scratch generation leaves the marker they read.
    (out_dir / "gh104_set.txt").write_text(str(set_dir), encoding="utf-8")
    return monitor


def classpath() -> str:
    """The rvsec-mop test classpath, built once and cached beside the module's target."""
    if not TEST_CLASSES.is_dir() or not CLASSPATH_FILE.is_file():
        subprocess.run(
            [
                "mvn",
                "-o",
                "-q",
                "test-compile",
                "dependency:build-classpath",
                "-pl",
                "rvsec/rvsec-mop",
                f"-Dmdep.outputFile={CLASSPATH_FILE}",
                "-Dmdep.includeScope=test",
            ],
            cwd=REACTOR,
            check=True,
        )
    return f"{TEST_CLASSES}:{CLASSPATH_FILE.read_text(encoding='utf-8').strip()}"


def replay(monitor_dir: Path, traces: Path, work: Path) -> list[dict]:
    """Runs `TraceRunner` over every trace of a directory against one snapshot."""
    out = work / "outcomes.json"
    work.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "java",
            "-cp",
            classpath(),
            "br.unb.cic.mop.harness.TraceRunner",
            str(monitor_dir),
            str(traces),
            str(work / "classes"),
            str(out),
        ],
        cwd=work,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(out.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# classification
# --------------------------------------------------------------------------


def self_contradicting(envelope: str) -> str | None:
    """`val ∈ exp`: the observed value is inside the list it is accused of missing."""
    match = ENVELOPE.search(envelope)
    if not match:
        return None
    expected = {item.strip().strip("{}").lower() for item in re.split(r"[,;]", match.group(1))}
    observed = match.group(2).strip().lower()
    if observed and observed in expected:
        return f"val ∈ exp: observed {observed!r} is listed in {sorted(expected)}"
    return None


def classify(left: dict, right: dict) -> str:
    if not left["accused"] and not right["accused"]:
        return "unchanged"
    if left["accused"] and not right["accused"]:
        return "removed"
    if right["accused"] and not left["accused"]:
        return "introduced"
    return "unchanged" if left["accusingEvents"] == right["accusingEvents"] else "moved"


def compare(left: list[dict], right: list[dict]) -> list[dict]:
    by_left = {outcome["trace"]: outcome for outcome in left}
    by_right = {outcome["trace"]: outcome for outcome in right}
    rows: list[dict] = []
    for trace in sorted(set(by_left) | set(by_right)):
        one = by_left.get(trace)
        two = by_right.get(trace)
        if one is None or two is None:
            rows.append(
                {
                    "trace": trace,
                    "class": "unreplayed",
                    "note": "the trace ran on one snapshot only; a comparison with no trace on "
                    "one side classifies nothing",
                }
            )
            continue
        flags = []
        for side, outcome in (("a", one), ("b", two)):
            for envelope in outcome["envelopes"]:
                if reason := self_contradicting(envelope):
                    flags.append(f"{side}: self-contradicting envelope -- {reason}")
        rows.append(
            {
                "trace": trace,
                "class": classify(one, two),
                "a_accused": one["accused"],
                "b_accused": two["accused"],
                "a_events": one["accusingEvents"],
                "b_events": two["accusingEvents"],
                "a_envelopes": one["envelopes"],
                "b_envelopes": two["envelopes"],
                "unresolved": one["unresolved"] + two["unresolved"],
                "flags": flags,
            }
        )
    return rows


def specification_of(trace: str) -> str:
    name = trace.replace(".txt", "")
    return name.split("-", 1)[0]


def write_reports(rows: list[dict], out: Path, group: str, set_a: Path, set_b: Path) -> list[Path]:
    """One markdown report per specification, at `evidence/harness/<group>-<Spec>.md`."""
    out.mkdir(parents=True, exist_ok=True)
    by_spec: dict[str, list[dict]] = {}
    for row in rows:
        by_spec.setdefault(specification_of(row["trace"]), []).append(row)

    written: list[Path] = []
    for spec, entries in sorted(by_spec.items()):
        path = out / f"{group}-{spec}.md"
        lines = [
            f"# {spec} — differential harness",
            "",
            f"- **A** `{set_a}`",
            f"- **B** `{set_b}`",
            f"- traces: {len(entries)}",
            "",
            "| trace | class | A accuses | B accuses |",
            "|---|---|---|---|",
        ]
        for row in entries:
            if row["class"] == "unreplayed":
                lines.append(f"| `{row['trace']}` | unreplayed | — | — |")
                continue
            lines.append(
                f"| `{row['trace']}` | {row['class']} | "
                f"{', '.join(row['a_events']) or '—'} | "
                f"{', '.join(row['b_events']) or '—'} |"
            )
        flagged = [row for row in entries if row.get("flags")]
        if flagged:
            lines += ["", "## Self-contradicting envelopes", ""]
            for row in flagged:
                for flag in row["flags"]:
                    lines.append(f"- `{row['trace']}` — {flag}")
        unresolved = [row for row in entries if row.get("unresolved")]
        if unresolved:
            lines += ["", "## Lines no pointcut resolved", ""]
            for row in unresolved:
                for line in row["unresolved"]:
                    lines.append(f"- `{row['trace']}` — `{line}`")
        lines += ["", "## Envelopes", ""]
        for row in entries:
            for side in ("a", "b"):
                for envelope in row.get(f"{side}_envelopes", []):
                    lines.append(f"- `{row['trace']}` ({side.upper()}) `{envelope}`")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        written.append(path)
    return written


# --------------------------------------------------------------------------
# the self-test mutant
# --------------------------------------------------------------------------


def write_mutant(seed: Path, target: Path) -> dict[str, str]:
    """A synthetic mutant of the seed with one authored difference per verdict.

    It is authored rather than borrowed so that every verdict of the classifier is covered by a
    difference whose direction is known in advance. Borrowing a real derived set would supply
    one accidental difference, cover one verdict, and put a specification set nobody controls on
    the critical path of a test. The mutant is scratch and is never committed.
    """
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(seed, target)
    applied: dict[str, str] = {}

    # `moved`: TrustManagerFactorySpec's accusation leaves `g3` and lands on `init`. The seed
    # keeps `g3` orphaned with an all-`fail` row; the mutant gives it the identity at the start
    # state, so the sequence reaches `init` and is accused there instead.
    tmf = target / "TrustManagerFactorySpec.mop"
    text = tmf.read_text(encoding="utf-8")
    text = text.replace(
        "      && condition(!algorithms.contains(alg))  {\n        currentAlgorithmInstance = alg;",
        "      && condition(!algorithms.contains(alg))  {\n        currentAlgorithmInstance = alg;\n        // gh104 self-test mutant: the accusation moves to `init`",
    )
    text = text.replace(
        "      start [\n        g1 -> waitingInit\n        g2 -> waitingInit\n      ]",
        "      start [\n        g1 -> waitingInit\n        g2 -> waitingInit\n        g3 -> start\n      ]",
    )
    tmf.write_text(text, encoding="utf-8")
    applied["moved"] = "TrustManagerFactorySpec: g3 loops at start, so the accusation lands on init"

    # `removed`: IvParameterSpecSpec's violating branch `c3` is closed off. Deleting its report
    # site alone would not do it -- `c3` carries an all-`fail` row, so firing it still runs the
    # `@fail` handler and the trace comes back accused at the same event. What removes the
    # accusation is the event never firing.
    iv = target / "IvParameterSpec.mop"
    text = iv.read_text(encoding="utf-8")
    text = text.replace(
        "       condition(\n         !ExecutionContext.instance().validate(Property.RANDOMIZED, iv)\n       ) {",
        "       condition(\n         // gh104 self-test mutant: c3 can no longer fire\n"
        "         false && !ExecutionContext.instance().validate(Property.RANDOMIZED, iv)\n       ) {",
    )
    iv.write_text(text, encoding="utf-8")
    applied["removed"] = "IvParameterSpecSpec: c3's condition is closed off, so the branch never fires"

    # `introduced`: MessageDigestSpec's commented-out `g4` report is revived, so a digest
    # obtained under an unsafe algorithm is accused at `getInstance` as well.
    md = target / "MessageDigestSpec.mop"
    text = md.read_text(encoding="utf-8")
    text = text.replace(
        '//          ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsafeAlgorithm, "MessageDigestSpec", "" + __LOC,\n'
        '//             "expecting one of {SHA-256, SHA-384, SHA-512} but found " + alg + "."));',
        '          ErrorCollector.instance().addError(new ErrorDescription(ErrorType.UnsafeAlgorithm, "MessageDigestSpec", "" + __LOC,\n'
        '             "expecting one of {SHA-256, SHA-384, SHA-512} but found " + alg + "."));',
    )
    md.write_text(text, encoding="utf-8")
    applied["introduced"] = (
        "MessageDigestSpec: the commented-out g4 report at :57-58 is revived, so a bare "
        "getInstance(\"MD5\") is accused where the seed accuses only the call that consumes it"
    )

    applied["unchanged"] = "KeyStoreSpec and every other file: not mutated"
    return applied


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------


def run(set_a: Path, set_b: Path, traces: Path, out: Path, group: str) -> dict:
    root = Path(tempfile.mkdtemp(prefix="gh104-harness-", dir=scratch_root()))
    monitors_a = generate(set_a, root / "a" / "monitors")
    monitors_b = generate(set_b, root / "b" / "monitors")
    left = replay(monitors_a.parent, traces, root / "a" / "work")
    right = replay(monitors_b.parent, traces, root / "b" / "work")
    rows = compare(left, right)
    written = write_reports(rows, out, group, set_a, set_b)
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["class"]] = counts.get(row["class"], 0) + 1
    return {
        "a": str(set_a),
        "b": str(set_b),
        "traces": len(rows),
        "counts": counts,
        "reports": [str(path) for path in written],
        "rows": rows,
        "scratch": str(root),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--a", type=Path, help="the first specification-set directory")
    parser.add_argument("--b", type=Path, help="the second specification-set directory")
    parser.add_argument("--traces", type=Path, default=REPO / "data/gh104/traces")
    parser.add_argument("--out", type=Path, default=REPO / "data/gh104/evidence/harness")
    parser.add_argument(
        "--group",
        default="s",
        help="the report prefix: `s` (seed), `e1` (messages), `e4` (automata), `selftest`",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="compare `jca` against a synthetic mutant of itself written in scratch",
    )
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()

    set_a, set_b = args.a, args.b
    mutations: dict[str, str] = {}
    if args.selftest:
        home = os.environ.get("RVSEC_HOME")
        if not home:
            print("RVSEC_HOME is not set", file=sys.stderr)
            return 2
        set_a = Path(home) / "rvsec/rvsec-mop/src/main/resources/jca"
        set_b = scratch_root() / "jca_mutant"
        mutations = write_mutant(set_a, set_b)
        args.group = "selftest"

    if set_a is None or set_b is None:
        parser.error("--a and --b are required unless --selftest is given")

    report = run(set_a, set_b, args.traces, args.out, args.group)
    report["mutations"] = mutations

    if args.selftest:
        # One file, not one per specification: the self-test's subject is the classifier.
        summary = args.out / "selftest.md"
        summary.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Differential harness — self-test",
            "",
            "`jca` against a synthetic mutant of `jca`, written into scratch by",
            "`scripts/gh104_diff_harness.py --selftest` and never committed. One authored",
            "mutation per verdict the classifier must produce, so a single run covers all four",
            "and the direction of every difference is known before the run rather than after.",
            "",
            f"- **A** `{report['a']}`",
            f"- **B** `{report['b']}` (scratch)",
            f"- traces replayed: {report['traces']}",
            "",
            "## Mutations",
            "",
        ]
        for verdict, description in sorted(mutations.items()):
            lines.append(f"- **{verdict}** — {description}")
        lines += ["", "## Verdict counts", ""]
        for verdict, count in sorted(report["counts"].items()):
            lines.append(f"- `{verdict}`: {count}")
        lines += [
            "",
            "## Traces that differ",
            "",
            "| trace | class | A accuses | B accuses |",
            "|---|---|---|---|",
        ]
        for row in report["rows"]:
            if row["class"] in ("unchanged", "unreplayed"):
                continue
            lines.append(
                f"| `{row['trace']}` | {row['class']} | "
                f"{', '.join(row['a_events']) or '—'} | "
                f"{', '.join(row['b_events']) or '—'} |"
            )
        flagged = [row for row in report["rows"] if row.get("flags")]
        lines += ["", "## Self-contradicting envelopes", ""]
        if flagged:
            for row in flagged:
                for flag in row["flags"]:
                    lines.append(f"- `{row['trace']}` — {flag}")
        else:
            lines.append(
                "None. On the frozen `jca` every guard-on-field site reports the same field it "
                "guards, so the envelope reads `but found .` rather than a value inside its own "
                "expected list; the flag fires once E1 makes the message report the object's "
                "algorithm, and goes to zero again when E4 task 8.16 moves the guard with it."
            )
        summary.write_text("\n".join(lines) + "\n", encoding="utf-8")
        report["reports"].append(str(summary))

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps({key: value for key, value in report.items() if key != "rows"}, indent=2))
    missing = {"unchanged", "moved", "removed", "introduced"} - set(report["counts"])
    if args.selftest and missing:
        print(f"the self-test produced no {sorted(missing)} verdict", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
