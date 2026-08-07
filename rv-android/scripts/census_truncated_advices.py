#!/usr/bin/env python3
"""Census of monitor calls the DEX weaver drops when it emits a fused advice.

JavaMOP fuses advices whose position and pointcut coincide, so one advice can
carry several ``monitorCalls``. The weaver has two emission paths. The wrapper
path iterates the list. The inline path reduces it to ``get(0)`` and drops the
rest, and it is the inline path that every fused advice in the production
descriptor reaches — see the routing rule below.

This script answers three questions mechanically, so that the post-repair count
has a pre-repair baseline computed by the same code rather than by a different
method (gh100 decision D-A3):

  1. How many advices carry more than one monitor call?
  2. How many of those are routed to the inline path, and therefore truncated?
  3. Which events are dropped, and are they error emitters?

Question 3 is the one that matters. The defect's observable signature is an
entire ``ErrorType`` category reading zero across the corpus, and that only
follows if the dropped events are the ones that call ``addError``.

The answer to question 2 depends on the weaver's source, not on the descriptor:
the script reads the emitter sources and reports whether the inline path still
truncates. That is what makes the same script give a different answer before and
after the repair, rather than restating the descriptor twice.

Usage
-----
    python3 scripts/census_truncated_advices.py \\
        [--descriptor PATH] [--monitor-src PATH] [--weaver-src DIR] \\
        [--json OUT]

Defaults point at the committed production descriptor from the gh92 campaign,
which is insulated from the specification edits happening in parallel.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_DESCRIPTOR = REPO_ROOT / "results/gh92_e2e2/monitors/MultiSpec_1MonitorAspect.json"
DEFAULT_MONITOR_SRC = REPO_ROOT / "results/gh92_e2e2/monitors/MultiSpec_1RuntimeMonitor.java"
DEFAULT_WEAVER_SRC = (
    REPO_ROOT.parent
    / "rvsec/rvsec-android/rvsec-instrumentation-dexlib2/advice-emitter/src/main/java"
)

# A constructor pointcut is written ``call(<modifiers> Type.new(<params>))``.
# ``.new(`` cannot occur in any other pointcut form, so it identifies the
# constructor targets exactly without re-implementing the pointcut parser.
CONSTRUCTOR_MARKER = ".new("

# The wrapper path is entered only for after-advice — WrapperEmitter.shouldWrap
# is literally ``"after".equals(a.getPosition())``.
WRAPPED_POSITION = "after"


# --- emission model -------------------------------------------------------


def find_truncation_sites(weaver_src: Path) -> List[Dict[str, object]]:
    """Report every emitter site that reduces ``monitorCalls`` to its first entry.

    Two spellings occur in the tree: the direct ``getMonitorCalls().get(0)``
    and the indirect one, where a local is assigned from ``getMonitorCalls()``
    and then read with ``.get(0)``. Both are truncation; the accessors that
    wrap them are named ``primaryMonitorCall`` / ``primaryCall``.

    The presence of any such site is what this script treats as "the inline
    path still truncates". After the repair there are none, which is also what
    the INV-INS-106 contract test enforces independently.
    """
    sites: List[Dict[str, object]] = []
    if not weaver_src.is_dir():
        raise SystemExit(f"weaver sources not found at {weaver_src}")

    direct = re.compile(r"getMonitorCalls\(\)\s*\.\s*get\(\s*0\s*\)")
    assigned = re.compile(r"(\w+)\s*=\s*[\w.]*\bgetMonitorCalls\(\)")

    for java in sorted(weaver_src.rglob("*.java")):
        text = java.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        locals_from_calls = set(assigned.findall(text))
        indirect = (
            re.compile(
                r"\b(" + "|".join(re.escape(n) for n in locals_from_calls) + r")\s*\.\s*get\(\s*0\s*\)"
            )
            if locals_from_calls
            else None
        )
        for idx, line in enumerate(lines, start=1):
            if direct.search(line):
                sites.append({"file": java.name, "line": idx, "form": "direct", "text": line.strip()})
            elif indirect is not None and indirect.search(line):
                sites.append({"file": java.name, "line": idx, "form": "indirect", "text": line.strip()})
    return sites


# --- monitor source -------------------------------------------------------


def error_emitting_events(monitor_src: Path) -> Dict[str, List[str]]:
    """Map ``<SpecName>/<eventId>`` to the ``ErrorType``s its handler raises.

    rv-monitor emits one ``Prop_<n>_event_<eventId>`` method per event inside
    the spec's monitor class. An event is an error emitter when that method's
    own body calls ``ErrorCollector.addError`` — the guard that fires the error
    lives in the event method, not in the state machine's fail handler, so this
    is a local property and can be read without following transitions.
    """
    text = monitor_src.read_text(encoding="utf-8", errors="replace")
    emitters: Dict[str, List[str]] = {}

    # Monitor classes are named ``<SpecName>Monitor``. Track which one we are
    # inside so the same event id under two specs cannot be confused.
    class_pattern = re.compile(r"\bclass\s+(\w+?)Monitor\b")
    event_pattern = re.compile(r"\bProp_\d+_event_(\w+)\s*\(")
    error_pattern = re.compile(r"addError\(new ErrorDescription\(ErrorType\.(\w+)")

    boundaries = [(m.start(), m.group(1)) for m in class_pattern.finditer(text)]

    def spec_at(pos: int) -> Optional[str]:
        current = None
        for start, name in boundaries:
            if start <= pos:
                current = name
            else:
                break
        return current

    for match in event_pattern.finditer(text):
        # Brace-match the method body. Delimiting on the next member instead
        # would swallow the `Prop_<n>_handler_fail` that follows the last event
        # of each class, and that handler raises InvalidSequenceOfMethodCalls
        # for every spec — every last event would be misreported as raising it.
        body = brace_matched_body(text, match.end() - 1)
        types = error_pattern.findall(body)
        if types:
            spec = spec_at(match.start())
            emitters[f"{spec}/{match.group(1)}"] = sorted(set(types))
    return emitters


def brace_matched_body(text: str, from_index: int) -> str:
    """Return the ``{...}`` block that opens at or after ``from_index``."""
    start = text.find("{", from_index)
    if start < 0:
        return ""
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return text[start:]


# --- census ---------------------------------------------------------------


def run_census(descriptor: Path, monitor_src: Path, weaver_src: Path) -> Dict[str, object]:
    doc = json.loads(descriptor.read_text(encoding="utf-8"))
    advices = doc["advices"]
    emitters = error_emitting_events(monitor_src)
    sites = find_truncation_sites(weaver_src)
    truncating = bool(sites)

    fused = [a for a in advices if len(a.get("monitorCalls") or []) > 1]
    inline_routed: List[Dict[str, object]] = []
    wrapper_routed: List[str] = []
    unclassified: List[str] = []

    for advice in fused:
        expression = advice.get("expression") or ""
        if advice.get("position") != WRAPPED_POSITION:
            # Before-advice never reaches the wrapper path at all.
            unclassified.append(advice["name"])
            continue
        if CONSTRUCTOR_MARKER not in expression:
            wrapper_routed.append(advice["name"])
            continue

        dropped = []
        for call in advice["monitorCalls"][1:]:
            key = f"{call['specName']}/{call['eventId']}"
            dropped.append(
                {
                    "method": call["method"],
                    "spec": call["specName"],
                    "event": call["eventId"],
                    "errorTypes": emitters.get(key, []),
                }
            )
        inline_routed.append(
            {
                "advice": advice["name"],
                "spec": advice["specName"],
                "monitorCalls": len(advice["monitorCalls"]),
                "kept": advice["monitorCalls"][0]["method"],
                "dropped": dropped,
            }
        )

    dropped_events = [d for a in inline_routed for d in a["dropped"]]
    error_emitting = [d for d in dropped_events if d["errorTypes"]]
    by_type: Dict[str, int] = {}
    for event in error_emitting:
        for kind in event["errorTypes"]:
            by_type[kind] = by_type.get(kind, 0) + 1

    return {
        "inputs": {
            "descriptor": str(descriptor),
            "descriptorSha256": sha256(descriptor),
            "monitorSource": str(monitor_src),
            "monitorSourceSha256": sha256(monitor_src),
            "weaverSource": str(weaver_src),
        },
        "emissionModel": {
            "truncating": truncating,
            "truncationSites": sites,
        },
        "counts": {
            "advices": len(advices),
            "fusedAdvices": len(fused),
            "inlineRoutedAdvices": len(inline_routed),
            "wrapperRoutedAdvices": len(wrapper_routed),
            "unclassifiedAdvices": len(unclassified),
            # Under an iterating inline path nothing is dropped, so the census
            # reports zero without the descriptor having changed.
            "eventsDropped": len(dropped_events) if truncating else 0,
            "errorEmittersDropped": len(error_emitting) if truncating else 0,
        },
        "errorTypesDropped": by_type if truncating else {},
        "inlineRouted": inline_routed,
        "wrapperRouted": sorted(wrapper_routed),
        "unclassified": sorted(unclassified),
    }


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render(census: Dict[str, object]) -> str:
    counts = census["counts"]
    model = census["emissionModel"]
    out: List[str] = []
    out.append("Truncation census — fused advices on the dexlib2 inline emission path")
    out.append("=" * 72)
    out.append("")
    out.append(f"descriptor      {census['inputs']['descriptor']}")
    out.append(f"  sha256        {census['inputs']['descriptorSha256']}")
    out.append(f"monitor source  {census['inputs']['monitorSource']}")
    out.append(f"  sha256        {census['inputs']['monitorSourceSha256']}")
    out.append("")
    out.append("Emission model read from the weaver sources")
    out.append("-" * 72)
    if model["truncating"]:
        out.append("INLINE PATH TRUNCATES — it emits only the first monitor call.")
        for site in model["truncationSites"]:
            out.append(f"  {site['file']}:{site['line']}  [{site['form']}]  {site['text']}")
    else:
        out.append("INLINE PATH ITERATES — no site reduces monitorCalls to its first entry.")
    out.append("")
    out.append("Descriptor census")
    out.append("-" * 72)
    out.append(f"  advices total                 {counts['advices']}")
    out.append(f"  advices with >1 monitor call  {counts['fusedAdvices']}")
    out.append(f"    routed to the wrapper path  {counts['wrapperRoutedAdvices']}  (iterates correctly)")
    out.append(f"    routed to the inline path   {counts['inlineRoutedAdvices']}  (constructor targets)")
    if counts["unclassifiedAdvices"]:
        out.append(f"    unclassified                {counts['unclassifiedAdvices']}  {census['unclassified']}")
    out.append("")
    out.append(f"  events dropped                {counts['eventsDropped']}")
    out.append(f"    of which error emitters     {counts['errorEmittersDropped']}")
    for kind, n in sorted(census["errorTypesDropped"].items()):
        out.append(f"      {kind:34s}{n}")
    out.append("")
    out.append("Advices routed inline, and what each one loses")
    out.append("-" * 72)
    for advice in census["inlineRouted"]:
        out.append(f"  {advice['advice']}  (N={advice['monitorCalls']})")
        out.append(f"    kept    {advice['kept']}")
        for dropped in advice["dropped"]:
            types = ", ".join(dropped["errorTypes"]) or "no error emission"
            verb = "dropped" if model["truncating"] else "emitted"
            out.append(f"    {verb} {dropped['method']}  [{types}]")
    out.append("")
    out.append("Routing rule, for the reader")
    out.append("-" * 72)
    out.append(
        "  WrapperEmitter.shouldWrap is `\"after\".equals(position)`, and every fused\n"
        "  advice in this descriptor is after-advice. What still falls to the inline\n"
        "  path is the explicit constructor `continue` in WrapperEmitter.generate:\n"
        "  constructors do not flow through wrappers because the weaver already has\n"
        "  the allocated instance in the invoke site's first register.\n"
        "\n"
        "  This census assumes the non-constructor targets do reach the wrapper path,\n"
        "  which holds when the weave resolves android.jar — without the platform\n"
        "  index, overload expansion falls back to static-only targets and more\n"
        "  advices would drop to inline. The resolved android.jar is logged per APK\n"
        "  by the weaver, so that assumption is checkable against any real run."
    )
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--descriptor", type=Path, default=DEFAULT_DESCRIPTOR)
    parser.add_argument("--monitor-src", type=Path, default=DEFAULT_MONITOR_SRC)
    parser.add_argument("--weaver-src", type=Path, default=DEFAULT_WEAVER_SRC)
    parser.add_argument("--json", type=Path, default=None, help="also write the census as JSON")
    args = parser.parse_args()

    for label, path in (
        ("descriptor", args.descriptor),
        ("monitor source", args.monitor_src),
    ):
        if not path.is_file():
            raise SystemExit(f"{label} not found at {path}")

    census = run_census(args.descriptor, args.monitor_src, args.weaver_src)
    print(render(census))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(census, indent=2) + "\n", encoding="utf-8")
        print(f"\nJSON written to {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
