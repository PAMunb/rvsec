#!/usr/bin/env python3
"""G-PARAM: the specification's parameter list survives into the generated monitor.

JavaMOP deletes a parameter whose declared type is a primitive array. Not warns
about it, not fails on it -- deletes it, writes the `.rvm` without it, and exits
0. The root cause is a grammar branch (`javamop.jj:1456` versus `:1470`) with a
silent `catch` on either side of it, and it is not patched here: the generators
are shared with the frozen set, and the `Object` idiom bypasses the collapse
entirely. What is needed instead is a gate, because the failure is invisible in
every place an operator would look.

The consequence is worse than a lost parameter. A specification whose header
loses its `byte[]` position stops slicing by that object: every instance of the
chain collapses into one monitor, so a randomised IV in one part of the program
satisfies a constructor in another. The generated monitor compiles, runs, and
reports plausible nonsense.

**The gate reads artifacts, never exit codes.** The toolchain returns 0 on this
failure, on an out-of-memory logic engine, and on a monitor it never wrote. A
gate that trusted the return code would be green for all three.

Usage:
    uv run python scripts/gh105_param_gate.py --sets jca_android --monitors <dir>
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gh105_predicate_graph import SPECIFICATION_SETS, neutralize  # noqa: E402

# `SpecName(Type name, Type name) {` at the start of a line. The `.mop` and the
# generated `.rvm` carry the same construct, which is what makes the comparison a
# comparison rather than a reconstruction.
_HEADER = re.compile(r"^(?P<name>\w+)\s*\((?P<parameters>[^)]*)\)\s*\{", re.MULTILINE)

# The types the generator drops. `Object` is the idiom that bypasses it: the
# overload is pinned in the `call(...)` signature instead, and `args(x)` with
# `Object` matches any single argument, autoboxed primitives included.
_PRIMITIVE_ARRAY = re.compile(r"\b(?:byte|char|int|long|short|float|double|boolean)\s*\[\s*\]")


@dataclass(frozen=True)
class ParamFinding:
    spec_set: str
    spec: str
    message: str

    @property
    def key(self) -> tuple[str, str]:
        return (self.spec_set, self.spec)


@dataclass
class ParamRun:
    passed: list[str] = field(default_factory=list)
    findings: list[ParamFinding] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.passed) + len(self.findings) + len(self.skipped)


def read_header(path: Path) -> tuple[str, list[str]] | None:
    """The specification name and its parameter list, comments and strings removed.

    Neutralising first matters here for a reason specific to this file: a `.rvm`
    keeps the specification's Javadoc, and a rule name inside a comment can look
    exactly like a header at the start of a line.
    """
    text = neutralize(path.read_text(encoding="utf-8"))
    for match in _HEADER.finditer(text):
        name = match.group("name")
        if name in {"if", "for", "while", "switch", "catch", "import", "package", "return"}:
            continue
        raw = match.group("parameters").strip()
        parameters = [re.sub(r"\s+", " ", part.strip()) for part in raw.split(",") if part.strip()]
        return name, parameters
    return None


def compare(spec_set: str, mop: Path, rvm: Path) -> ParamFinding | None:
    """One specification's `.mop` header against the header the generator wrote."""
    source = read_header(mop)
    generated = read_header(rvm)
    if source is None or generated is None:
        return None

    _, declared = source
    _, survived = generated
    if declared == survived:
        return None

    lost = [parameter for parameter in declared if parameter not in survived]
    collapsed = [parameter for parameter in lost if _PRIMITIVE_ARRAY.search(parameter)]
    if collapsed:
        detail = (
            f"the generator dropped {collapsed} -- a primitive-array parameter is deleted "
            "silently, with return code 0. Declare the position `Object` and pin the overload "
            "in the `call(...)` signature."
        )
    else:
        detail = f"declared {declared}, generated {survived}"
    return ParamFinding(spec_set, mop.stem, detail)


def run(specs_root: Path, monitors: Path, selection: str = "all") -> ParamRun:
    """G-PARAM over the enumerated universe, skipping what was never generated.

    A specification with no generated monitor beside it is skipped and counted,
    never passed: the whole point of this gate is that a missing artifact is a
    finding about the generation, and the shape a missing artifact takes here is a
    skip with a reason rather than a silent success.
    """
    names = SPECIFICATION_SETS if selection == "all" else (selection,)
    result = ParamRun()
    for name in names:
        set_dir = specs_root / name
        if not set_dir.is_dir():
            continue
        for mop in sorted(set_dir.glob("*.mop")):
            rvm = monitors / f"{mop.stem}.rvm"
            if not rvm.is_file():
                result.skipped.append((f"{name}/{mop.stem}", f"no generated monitor at {rvm}"))
                continue
            if read_header(mop) is None:
                result.skipped.append((f"{name}/{mop.stem}", "no specification header: event declarations only"))
                continue
            finding = compare(name, mop, rvm)
            if finding:
                result.findings.append(finding)
            else:
                result.passed.append(f"{name}/{mop.stem}")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--specs-root",
        type=Path,
        default=Path("../rvsec/rvsec-mop/src/main/resources"),
        help="directory holding the specification sets",
    )
    parser.add_argument("--sets", default="all", help="`all` or the name of one set")
    parser.add_argument("--monitors", type=Path, required=True, help="directory of generated `.rvm`")
    parser.add_argument("--json", action="store_true", help="machine-readable report")
    arguments = parser.parse_args(argv)

    result = run(arguments.specs_root, arguments.monitors, arguments.sets)

    payload = {
        "passed": len(result.passed),
        "failed": len(result.findings),
        "skipped": [{"spec": spec, "reason": reason} for spec, reason in result.skipped],
        "findings": [
            {"set": finding.spec_set, "spec": finding.spec, "message": finding.message}
            for finding in result.findings
        ],
    }

    if arguments.json:
        print(json.dumps(payload, indent=2))
    else:
        print(
            f"G-PARAM: {len(result.passed)} passed, {len(result.findings)} failed, "
            f"{len(result.skipped)} skipped (of {result.total})"
        )
        for spec, reason in result.skipped:
            print(f"  skipped {spec}: {reason}")
        for finding in result.findings:
            print(f"  [G-PARAM] {finding.spec_set}/{finding.spec}: {finding.message}")

    return 1 if result.findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
