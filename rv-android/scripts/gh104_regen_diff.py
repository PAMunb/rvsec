#!/usr/bin/env python3
"""Regenerate one specification set and classify its diff against a frozen control.

Why this exists (gh104, INV-INS-120 and INV-INS-129)
----------------------------------------------------
The `__EVENTNAME` group edits the monitor *generator* (`rv-monitor/rv-monitor`),
which serves every specification set in the tree.  The generator edit is global,
so the way to show that it changed nothing it was not meant to change is to
regenerate a set whose output is already recorded and to look at every line of
the difference.  One control is enough: `jca` exercises the same emitter paths
any set derived from it would.

The admissible differences are exactly three, and this script is what says so
out loud instead of leaving it to a human reading a 16 000-line diff:

  * ``table``        — the per-monitor-class ``static final String[] RVM_eventNames``
  * ``helper``       — the per-monitor-class ``RVM_eventName()`` decoder
  * ``lock-framing`` — ``try {`` after the lock acquisition and ``} finally { … }``
                       in place of the bare release, plus the one extra tab of
                       indentation that framing gives every dispatcher body line

Anything else is ``other`` and fails.  An unexpanded ``__EVENTNAME`` is its own
category and fails unconditionally, whatever ``--expect`` says: an unexpanded
macro reaches ``javac`` as an undefined identifier or, worse, is reported as
text and read as a fact.

Two things the diff is deliberately blind to
--------------------------------------------
Leading whitespace is stripped before comparison.  The lock framing adds one
brace level around every dispatcher body, and `Tool.changeIndentation` re-indents
the whole generated file from the brace structure, so a byte-level diff would
report several thousand lines that differ only by a tab.  Those are counted and
reported separately (``indent-only``) rather than classified line by line.

The control's ``Coverage.aj`` is outside the comparison.  It is not a generator
output: the Python pipeline copies it from the aspects directory into the
control directory after generation.  ``mop/MonitorWrappers.java`` is likewise
outside it — the instrumentation step produces it, not the generator.

Usage
-----
Regenerate and compare (needs RVSEC_HOME and a TMPDIR off tmpfs)::

    export TMPDIR=$HOME/tmp-gh104 && mkdir -p $TMPDIR
    python3 scripts/gh104_regen_diff.py \
        --specs-dir ../rvsec/rvsec-mop/src/main/resources/jca \
        --control results/gh101_group8_jca_frozen_control/monitors/ \
        --manifest data/gh104/jca_frozen_control.sha256 \
        --expect table,helper,lock-framing

Compare a directory that was generated elsewhere, without regenerating::

    python3 scripts/gh104_regen_diff.py --candidate <dir> --control <dir> \
        --manifest data/gh104/jca_frozen_control.sha256 --expect table,helper,lock-framing

Exit codes: 0 every difference was expected; 1 an unexpected difference (or an
unexpanded macro, or a lock-count mismatch); 2 the run could not be made (no
control directory, no toolchain, generation failed).  A missing control
directory *skips* with a named reason — ``results/`` is gitignored and the
directory can legitimately be absent — but a control directory that disagrees
with its manifest is a failure, not a skip.
"""

from __future__ import annotations

import argparse
import difflib
import glob
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

# The three generator outputs the manifest covers.  Coverage.aj and mop/ are not
# generator outputs and are excluded on purpose (see the module docstring).
MONITOR_JAVA = "MultiSpec_1RuntimeMonitor.java"
ASPECT_AJ = "MultiSpec_1MonitorAspect.aj"
DESCRIPTOR_JSON = "MultiSpec_1MonitorAspect.json"
MANIFEST_FILES = (MONITOR_JAVA, ASPECT_AJ, DESCRIPTOR_JSON)

EXIT_OK = 0
EXIT_UNEXPECTED = 1
EXIT_CANNOT_RUN = 2

# --- classification vocabulary -------------------------------------------------
#
# Each pattern names one admissible difference.  A line that matches none of them
# and is not a bare brace is `other`.

TABLE_RE = re.compile(r"static\s+final\s+String\s*\[\]\s*RVM_eventNames\b")
HELPER_DECL_RE = re.compile(r"\bString\s+RVM_eventName\s*\(\s*\)")
HELPER_BODY_RE = re.compile(
    r"(RVM_eventNames\s*\[|RVM_eventNames\s*\.\s*length|this\.getLastEvent\s*\(\s*\)"
    r"|^\s*return\s+\"none\"\s*;|^\s*int\s+idx\s*=|^\s*idx\s*=)"
)
HELPER_CALL_RE = re.compile(r"\bRVM_eventName\s*\(\s*\)")
FRAMING_TRY_RE = re.compile(r"^try\s*\{$")
FRAMING_FINALLY_RE = re.compile(r"^\}\s*finally\s*\{$")
BRACE_RE = re.compile(r"^[{}();\s]*$")
MACRO_RE = re.compile(r"__EVENTNAME")

ACQUIRE_RE = re.compile(r"while\s*\(\s*!\s*\w+\.tryLock\(\)\s*\)")
RELEASE_RE = re.compile(r"\w+\.unlock\(\)\s*;")
FINALLY_RE = re.compile(r"\bfinally\b")

CATEGORY_MACRO = "macro"
CATEGORY_TABLE = "table"
CATEGORY_HELPER = "helper"
CATEGORY_FRAMING = "lock-framing"
CATEGORY_BRACE = "brace"
CATEGORY_OTHER = "other"


@dataclass
class Difference:
    """One classified line of the diff."""

    sign: str  # '+' (only in candidate) or '-' (only in control)
    category: str
    text: str


@dataclass
class Report:
    """
    What one regeneration comparison found: differences, indent-only lines, notes.

    `indent_only` is a count and not a list on purpose. The lock framing adds a
    brace level to every dispatcher body and the generator re-indents the whole
    file from the brace structure, so those lines number in the thousands and
    carry no information beyond how many they are.
    """

    differences: list[Difference] = field(default_factory=list)
    indent_only: int = 0
    notes: list[str] = field(default_factory=list)

    def by_category(self) -> dict[str, int]:
        """Count the differences by category, for the summary line."""
        counts: dict[str, int] = {}
        for d in self.differences:
            counts[d.category] = counts.get(d.category, 0) + 1
        return counts


# The two places a state number is written into the generated monitor: the
# transition rows and the category tests. A difference confined to these is a
# relabelling — the automaton is the same, its states are numbered differently.
STATE_LABEL_RE = re.compile(
    r"Prop_\d+_transition_\w+\[\]"
    r"|_Category_\w+\s*=\s*(?:nextstate|Prop_\d+_state)\s*=="
)

RELABELLING_DIAGNOSIS = """
All {count} substantive differences are state labels — transition rows and category tests — and
everything else is a pure reordering. That is the signature of a state relabelling rather than of
a changed automaton, and its known cause is the JDK: the state numbering a generated monitor
carries depends on the JDK that ran the generation, because the ERE-to-FSM conversion of the
logic repository returns its states in a different order. The control under results/ was
generated under JDK 25; you are running {jdk}.

Re-run with JAVA_HOME=$HOME/.sdkman/candidates/java/25.0.3-tem before reading this as a defect.
The automata are isomorphic across JDKs and no verdict moves, so this is a constraint on
byte-comparison, not on correctness. Measured in data/gh104/evidence/g_regeneration.md.
"""


def running_jdk() -> str:
    """The JDK that would run the generation, for the relabelling diagnosis."""
    home = os.environ.get("JAVA_HOME")
    return Path(home).name if home else "an unnamed JDK (JAVA_HOME unset)"


def classify(line: str) -> str:
    """Name the one admissible difference this line belongs to, or `other`.

    Bare braces are their own category: the framing and the helper both add
    them, and a brace on its own carries no evidence either way.  A brace is
    only tolerated in a hunk that also carries a classified, non-brace line —
    `resolve_braces` enforces that after the whole hunk has been seen.
    """
    if MACRO_RE.search(line):
        return CATEGORY_MACRO
    if TABLE_RE.search(line):
        return CATEGORY_TABLE
    if HELPER_DECL_RE.search(line) or HELPER_BODY_RE.search(line):
        return CATEGORY_HELPER
    if HELPER_CALL_RE.search(line):
        return CATEGORY_HELPER
    if FRAMING_TRY_RE.match(line) or FRAMING_FINALLY_RE.match(line):
        return CATEGORY_FRAMING
    if RELEASE_RE.search(line):
        # The release itself moves into the `finally`; the line is unchanged in
        # substance, only in position, so it shows up as an add/remove pair.
        return CATEGORY_FRAMING
    if BRACE_RE.match(line):
        return CATEGORY_BRACE
    return CATEGORY_OTHER


def resolve_braces(hunk: list[Difference], context: list[str]) -> list[Difference]:
    """Attribute the bare braces of a hunk to whatever else explains them.

    Two cases.  A hunk that carries a classified line as well as braces gives
    its braces to that line's category — the framing wins when both appear,
    because the framing is what adds braces.  A hunk that is *only* braces
    (the `}` that closes a `finally`, for instance, which the diff aligns on
    its own) is read from the lines around it: if the neighbouring lines are
    the release or the framing keywords, the brace belongs to the framing.
    Otherwise it stays `other` and fails, which is the safe direction.
    """
    real = [d.category for d in hunk if d.category != CATEGORY_BRACE]
    if real:
        owner = CATEGORY_FRAMING if CATEGORY_FRAMING in real else real[0]
    else:
        owner = CATEGORY_OTHER
        for line in context:
            cat = classify(line)
            if cat in (CATEGORY_FRAMING, CATEGORY_HELPER, CATEGORY_TABLE):
                owner = cat
                break
    return [
        Difference(
            d.sign, owner if d.category == CATEGORY_BRACE else d.category, d.text
        )
        for d in hunk
    ]


def strip_lines(path: Path) -> list[str]:
    """
    The file's lines with leading and trailing whitespace removed.

    This is what the monitor comparison reads, so that the framing's extra tab on
    every dispatcher body line does not read as thousands of changed lines. The
    raw text is still available through `raw_lines` for the indentation count.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    return [ln.strip() for ln in text.splitlines()]


def raw_lines(path: Path) -> list[str]:
    """
    The file's lines exactly as written, indentation included.

    Used only to tell an indent-only difference from a substantive one: two lines
    equal after stripping and unequal before it differ by whitespace alone.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    return text.splitlines()


def diff_monitor(control: Path, candidate: Path, report: Report) -> None:
    """Classify the monitor file's diff, ignoring pure indentation changes."""
    a = strip_lines(control)
    b = strip_lines(candidate)

    raw_a, raw_b = raw_lines(control), raw_lines(candidate)

    matcher = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            # Same line, possibly at a different indent: the framing adds one
            # brace level around every dispatcher body, and the whole file is
            # re-indented from the brace structure.
            for k in range(i2 - i1):
                if raw_a[i1 + k] != raw_b[j1 + k]:
                    report.indent_only += 1
            continue
        hunk: list[Difference] = []
        for line in a[i1:i2]:
            hunk.append(Difference("-", classify(line), line))
        for line in b[j1:j2]:
            hunk.append(Difference("+", classify(line), line))
        # Two lines either side, on both files, are enough to say what a
        # brace-only hunk closes.
        context = b[max(0, j1 - 2) : j1] + b[j2 : j2 + 2]
        context += a[max(0, i1 - 2) : i1] + a[i2 : i2 + 2]
        report.differences.extend(resolve_braces(hunk, context))


def diff_exact(control: Path, candidate: Path, report: Report, label: str) -> None:
    """`.aj` and `.json` come from javamop, which this change does not touch."""
    if control.read_bytes() == candidate.read_bytes():
        return
    report.differences.append(
        Difference(
            "!", CATEGORY_OTHER, f"{label} differs from the control byte for byte"
        )
    )


def check_lock_balance(candidate: Path, report: Report) -> bool:
    """Acquisitions = releases = `finally` blocks, and every acquisition framed.

    INV-INS-129's arithmetic check.  It is run on the *regenerated* file, so it
    reads 134/134/134 for `jca` after the framing lands and 134/134/0 before.
    """
    lines = strip_lines(candidate)
    acquires = [i for i, ln in enumerate(lines) if ACQUIRE_RE.search(ln)]
    releases = sum(1 for ln in lines if RELEASE_RE.search(ln))
    finallys = sum(1 for ln in lines if FINALLY_RE.search(ln))

    report.notes.append(
        f"lock accounting: {len(acquires)} acquisitions, {releases} releases, "
        f"{finallys} finally blocks"
    )

    ok = len(acquires) == releases == finallys
    if not ok:
        report.notes.append(
            "FAIL: acquisitions, releases and finally blocks disagree (INV-INS-129)"
        )
        return False

    # Every acquisition must be followed, within the spin loop's three lines plus
    # a little slack, by the `try {` that opens its guarded region.
    unframed = []
    for i in acquires:
        window = lines[i : i + 6]
        if not any(FRAMING_TRY_RE.match(w) for w in window):
            unframed.append(i + 1)
    if unframed:
        report.notes.append(
            f"FAIL: {len(unframed)} acquisition(s) not inside a try, first at line "
            f"{unframed[0]} (INV-INS-129)"
        )
        return False
    return True


def check_no_macro(directory: Path, report: Report) -> bool:
    """INV-INS-120's fail-closed check, applied to the regenerated tree."""
    offenders = []
    for path in sorted(directory.rglob("*.java")) + sorted(directory.rglob("*.aj")):
        for n, line in enumerate(raw_lines(path), start=1):
            if MACRO_RE.search(line):
                offenders.append(f"{path}:{n}")
    if offenders:
        report.notes.append(
            f"FAIL: the literal __EVENTNAME survived in {len(offenders)} place(s); "
            f"first at {offenders[0]} (INV-INS-120)"
        )
        return False
    report.notes.append("no unexpanded __EVENTNAME in the regenerated output")
    return True


def verify_manifest(control: Path, manifest: Path) -> tuple[bool, str]:
    """The manifest is the versioned artefact; `results/` is gitignored.

    Absent control directory -> skip with a named reason.  Present but
    disagreeing -> failure: a control that has drifted is worse than none.
    """
    if not control.is_dir():
        return False, f"control directory {control} is absent (results/ is gitignored)"
    expected: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        digest, name = line.split(None, 1)
        expected[name.strip()] = digest
    problems = []
    for name, digest in expected.items():
        path = control / name
        if not path.is_file():
            problems.append(f"{name}: missing from the control directory")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != digest:
            problems.append(f"{name}: sha256 {actual} != recorded {digest}")
    if problems:
        return False, "control disagrees with its manifest: " + "; ".join(problems)
    return True, f"control verified against {manifest} ({len(expected)} files)"


def regenerate(specs_dir: Path, aspects_dir: Path, rvsec_home: Path, out: Path) -> None:
    """Reproduce the pipeline that produced the control, into a scratch directory.

    This mirrors `rv_monitor_generator.runtime_verification_generator`: javamop
    with `-merge` (and `--emit-descriptor`) writes the `.aj` and the descriptor
    into `out` but leaves the `.rvm` files beside the sources, so they are moved;
    then rv-monitor turns them into the monitor class.  The `.rvm` files are
    removed from the source directory whatever happens, so a failed run never
    leaves the frozen specification set dirty.
    """
    javamop = rvsec_home / "javamop" / "bin" / "javamop"
    rvmonitor = rvsec_home / "rv-monitor" / "bin" / "rv-monitor"
    for tool in (javamop, rvmonitor):
        if not tool.is_file():
            raise FileNotFoundError(f"toolchain missing: {tool}")

    out.mkdir(parents=True, exist_ok=True)
    strays: list[str] = []
    try:
        subprocess.run(
            [
                str(javamop),
                "-d",
                str(out),
                "-merge",
                "--emit-descriptor",
                str(specs_dir / "*.mop"),
            ],
            check=True,
        )
        strays = glob.glob(str(specs_dir / "*.rvm"))
        for rvm in strays:
            shutil.move(rvm, str(out / Path(rvm).name))
        strays = []
        for aj in glob.glob(str(aspects_dir / "*.aj")):
            shutil.copy2(aj, str(out / Path(aj).name))
        subprocess.run(
            [str(rvmonitor), "-d", str(out), "-merge", str(out / "*.rvm")],
            check=True,
        )
    finally:
        for rvm in glob.glob(str(specs_dir / "*.rvm")):
            os.remove(rvm)


def main(argv: list[str] | None = None) -> int:
    """
    Regenerate (or accept) a candidate set, classify the diff, and return an exit code.

    Three outcomes rather than two. `EXIT_CANNOT_RUN` is for everything that
    prevents the comparison from being made at all -- a control that is not on
    this disk, an unset `RVSEC_HOME`, a regeneration that failed -- and it is kept
    apart from `EXIT_UNEXPECTED` so that "not measured" can never be read as
    "measured and clean".

    The manifest is verified before anything is generated, since a control that
    does not match its own digests is not a control.

    When the unexpected differences are all state labels and the rest is a pure
    permutation, `RELABELLING_DIAGNOSIS` is printed. That combination has one
    known cause -- the JDK that ran the generation orders the ERE-to-FSM states
    differently -- and printing the diagnosis is cheaper than a reader
    rediscovering it from a 16 000-line diff. It is a note, not a pass: the exit
    code still says the diff was not what `--expect` admitted.
    """
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--specs-dir", type=Path, help="the .mop set to regenerate")
    p.add_argument("--aspects-dir", type=Path, help="defaults to <specs-dir>/../aspect")
    p.add_argument("--control", type=Path, required=True, help="recorded control dir")
    p.add_argument("--manifest", type=Path, required=True, help="sha256 of the control")
    p.add_argument(
        "--candidate",
        type=Path,
        help="a directory already generated; skips regeneration",
    )
    p.add_argument(
        "--expect",
        default="table,helper,lock-framing",
        help="comma-separated admissible categories",
    )
    p.add_argument("--rvsec-home", type=Path, default=os.environ.get("RVSEC_HOME"))
    p.add_argument("--keep", action="store_true", help="keep the scratch directory")
    p.add_argument("--out", type=Path, help="scratch directory (default: a temp dir)")
    args = p.parse_args(argv)

    expected = {c.strip() for c in args.expect.split(",") if c.strip()}
    report = Report()

    ok, why = verify_manifest(args.control, args.manifest)
    print(why)
    if not ok:
        if not args.control.is_dir():
            return EXIT_CANNOT_RUN  # skip: the control is simply not on this disk
        return EXIT_UNEXPECTED

    scratch: Path | None = None
    if args.candidate:
        candidate = args.candidate
    else:
        if not args.specs_dir:
            print("--specs-dir is required unless --candidate is given")
            return EXIT_CANNOT_RUN
        if not args.rvsec_home:
            print("RVSEC_HOME is unset and --rvsec-home was not given")
            return EXIT_CANNOT_RUN
        scratch = args.out or Path(tempfile.mkdtemp(prefix="gh104-regen-"))
        aspects = args.aspects_dir or (args.specs_dir.parent / "aspect")
        try:
            regenerate(args.specs_dir, aspects, Path(args.rvsec_home), scratch)
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            print(f"regeneration failed: {exc}")
            return EXIT_CANNOT_RUN
        candidate = scratch
        print(f"regenerated into {scratch}")

    for name in MANIFEST_FILES:
        c, k = args.control / name, candidate / name
        if not k.is_file():
            report.differences.append(
                Difference("!", CATEGORY_OTHER, f"{name} was not generated")
            )
            continue
        if name == MONITOR_JAVA:
            diff_monitor(c, k, report)
        else:
            diff_exact(c, k, report, name)

    passed = True
    monitor = candidate / MONITOR_JAVA
    if monitor.is_file():
        passed &= check_lock_balance(monitor, report)
    passed &= check_no_macro(candidate, report)

    counts = report.by_category()
    print(f"indent-only lines (framing re-indentation): {report.indent_only}")
    print("classified differences:")
    for cat in sorted(counts):
        print(f"  {cat}: {counts[cat]}")
    for note in report.notes:
        print(f"note: {note}")

    unexpected = [d for d in report.differences if d.category not in expected]
    if unexpected:
        passed = False
        print(f"\n{len(unexpected)} unexpected difference(s); first 40:")
        for d in unexpected[:40]:
            print(f"  {d.sign} [{d.category}] {d.text}")
        substantive = [
            d for d in unexpected if d.text.strip() not in ("", "}", "{", "};")
        ]
        rows = [d for d in substantive if STATE_LABEL_RE.search(d.text)]
        rest = [d for d in substantive if not STATE_LABEL_RE.search(d.text)]
        # A line that is removed and added with identical text was reordered, not
        # changed; only a residue that is not a pure permutation carries evidence.
        removed = Counter(d.text.strip() for d in rest if d.sign == "-")
        added = Counter(d.text.strip() for d in rest if d.sign == "+")
        residue = (removed - added) + (added - removed)
        print(
            f"\nshape of the {len(unexpected)} unexpected: {len(rows)} state-label lines, "
            f"{len(rest)} reordered or changed lines ({sum(residue.values())} not a pure "
            f"reordering), {len(unexpected) - len(substantive)} braces or blanks"
        )
        for text, n in list(residue.items())[:10]:
            print(f"  not a reordering (x{n}): {text}")
        if rows and not residue:
            print(RELABELLING_DIAGNOSIS.format(count=len(rows), jdk=running_jdk()))

    if scratch and not args.keep:
        shutil.rmtree(scratch, ignore_errors=True)

    print("\nRESULT:", "OK" if passed else "FAIL")
    return EXIT_OK if passed else EXIT_UNEXPECTED


if __name__ == "__main__":
    sys.exit(main())
