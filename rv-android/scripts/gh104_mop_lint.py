#!/usr/bin/env python3
"""Lint a specification-set directory before a monitor is generated from it.

It fails closed, and it is a gate rather than a hook inside the generator
because the generator's response to most of these is silence: an `ere` symbol
with no event behind it is dropped without a word, and the specification ships
with an automaton nobody wrote.

What it reports:

    undeclared-symbol   an `ere`/`fsm` symbol with no event declaration -- this
                        is G-ERE, shared with `gh104_gates.py` so the two can
                        never drift apart
    duplicate-event     two events with one name; the generator keeps one
    unbalanced          parentheses that do not close inside one event
    three-argument-site a `new ErrorDescription(` with three arguments
                        (INV-INS-119): the third positional argument is the
                        location, and a message passed there is read as one
    hand-written-name   an event-name field or assignment written by hand
                        (INV-INS-120). The generator emits the name now, and a
                        hand-written index table desynchronises silently under
                        any edit of the alphabet -- the failure is invisible
                        because the wrong name is still a name
    reserved-name       a declaration that collides with a name the generator
                        writes into the monitor

Predicates are not a lint subject: the successor set carries the seed's
`ExecutionContext` machinery byte-for-byte (design D-11) and G-PRED, in
`gh104_gates.py`, is what checks that it is still all there.

Usage:
    gh104_mop_lint.py <set directory> [--json report.json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from gh104_gates import (  # noqa: E402  (the path insert above is what makes it importable)
    MopSpec,
    _match_delimiters,
    _split_top_level,
    parse_mop,
)

# Names the generator writes into every monitor. A declaration that reuses one
# is not a name clash the compiler will catch -- the generated field shadows or
# is shadowed depending on where it lands, and the monitor still compiles.
RESERVED = (
    "pairValue",
    "RVM_lastevent",
    "RVM_eventName",
    "RVM_eventNames",
    "reset",
    "getState",
    "getLastEvent",
    "handleEvent",
    "clone",
)
RESERVED_PREFIXES = ("Prop_",)

# INV-INS-120: the generator emits the event name, so a specification that keeps
# its own copy holds two sources of truth for one fact.
EVENT_NAME_FIELD = re.compile(
    r"^\s*(?:private|protected|public|static|final|\s)*"
    r"(?:String|int)\s+(\w*(?:[eE]vent[nN]ame|EVENT_NAME|lastEvent|last_event)\w*)\s*[=;]",
    re.MULTILINE,
)
EVENT_NAME_ASSIGN = re.compile(
    r"^\s*(\w*(?:[eE]vent[nN]ame|EVENT_NAME|lastEvent)\w*)\s*=\s*\"", re.MULTILINE
)
ERROR_SITE = re.compile(r"new\s+ErrorDescription\s*\(")
DECLARATION = re.compile(
    r"^\s*(?:private|protected|public|static|final|\s)*"
    r"(?:[\w.<>\[\], ]+?)\s+(\w+)\s*(?:=|;|\()",
    re.MULTILINE,
)


def error_sites(mop: MopSpec) -> list[dict]:
    """Every `new ErrorDescription(...)` with its argument list and line."""
    sites: list[dict] = []
    for match in ERROR_SITE.finditer(mop.text):
        start, end = _match_delimiters(mop.text, match.end() - 1, "(", ")")
        arguments = _split_top_level(mop.text[start + 1 : end])
        sites.append(
            {
                "file": mop.path.name,
                "line": mop.text[: match.start()].count("\n") + 1,
                "arity": len(arguments),
                "arguments": arguments,
                "text": mop.text[match.start() : end + 1],
            }
        )
    return sites


def lint(directory: Path) -> dict:
    findings: list[dict] = []
    notes: list[dict] = []

    for path in sorted(directory.glob("*.mop")):
        try:
            mop = parse_mop(path)
        except ValueError as error:  # an unbalanced group the parser walked into
            findings.append(
                {"kind": "unbalanced", "file": path.name, "line": 0, "detail": str(error)}
            )
            continue

        seen: set[str] = set()
        for event in mop.events:
            if event.name in seen:
                findings.append(
                    {
                        "kind": "duplicate-event",
                        "file": path.name,
                        "line": event.line,
                        "detail": f"a second `event {event.name}`; the generator keeps one of them",
                    }
                )
            seen.add(event.name)

        for symbol, line in mop.formula_symbols():
            if symbol not in seen:
                findings.append(
                    {
                        "kind": "undeclared-symbol",
                        "file": path.name,
                        "line": line,
                        "detail": f"`{symbol}` is named in the {mop.formula_kind} and declared nowhere "
                        f"(declared: {', '.join(sorted(seen)) or 'nothing'})",
                    }
                )

        for opener, closer in (("(", ")"), ("{", "}")):
            depth = 0
            for number, text in enumerate(mop.text.splitlines(), start=1):
                depth += text.count(opener) - text.count(closer)
                if depth < 0:
                    findings.append(
                        {
                            "kind": "unbalanced",
                            "file": path.name,
                            "line": number,
                            "detail": f"`{closer}` with no matching `{opener}`",
                        }
                    )
                    break
            else:
                if depth != 0:
                    findings.append(
                        {
                            "kind": "unbalanced",
                            "file": path.name,
                            "line": 0,
                            "detail": f"{depth} unclosed `{opener}` in the file",
                        }
                    )

        for site in error_sites(mop):
            if site["arity"] == 3:
                findings.append(
                    {
                        "kind": "three-argument-site",
                        "file": path.name,
                        "line": site["line"],
                        "detail": "new ErrorDescription(type, spec, location) -- "
                        "the report carries no message",
                    }
                )

        for pattern in (EVENT_NAME_FIELD, EVENT_NAME_ASSIGN):
            for match in pattern.finditer(mop.text):
                findings.append(
                    {
                        "kind": "hand-written-name",
                        "file": path.name,
                        "line": mop.text[: match.start()].count("\n") + 1,
                        "detail": f"`{match.group(1)}` keeps an event name by hand (INV-INS-120)",
                    }
                )

        for match in DECLARATION.finditer(mop.declarations):
            name = match.group(1)
            if name in RESERVED or name.startswith(RESERVED_PREFIXES):
                findings.append(
                    {
                        "kind": "reserved-name",
                        "file": path.name,
                        "line": mop.text[: mop.text.index(match.group(0))].count("\n") + 1,
                        "detail": f"`{name}` is a name the generator writes into the monitor",
                    }
                )
        # Only `declarations` are checked, not event names: an event named
        # `reset` becomes `Prop_1_event_reset` and collides with nothing, while a
        # *field* named `reset` shadows a member of the generated monitor.

    counts: dict[str, int] = {}
    for finding in findings:
        counts[finding["kind"]] = counts.get(finding["kind"], 0) + 1

    return {
        "directory": str(directory),
        "files": len(list(directory.glob("*.mop"))),
        "findings": findings,
        "notes": notes,
        "counts": counts,
        "ok": not findings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("directory", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()

    if not args.directory.is_dir():
        print(f"not a specification-set directory: {args.directory}", file=sys.stderr)
        return 2

    report = lint(args.directory)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
