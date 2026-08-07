#!/usr/bin/env python3
"""V2 — do the monitor events a fused advice carries reach the woven DEX?

This is the end-to-end half of gh100's acceptance criterion. V0 asserts that
each emitter *plans* N invokes for an advice carrying N monitor calls; V2
asserts that those invokes survive the whole pipeline and land as real
``invoke-static`` instructions in a real APK's DEX.

The two questions are genuinely different. An emitter can plan correctly and
still lose the invokes downstream — the mutator discards a site under register
pressure, the wrapper registry rebinds a key, the pointcut matches nothing. V2
reads the artefact the device would run.

What it checks
--------------
The dropped-event set is not hard-coded. It is recomputed from the descriptor
by ``census_truncated_advices.py``, so V2 and the census can never disagree
about which events are at stake, and V2 keeps working when the specification
set changes.

For each such event the script reports how many ``invoke-static`` sites target
it in application code. Call sites *inside the generated monitor itself* are
excluded: ``MultiSpec_1RuntimeMonitor`` declares every event method and calls
some of them from its own state machine, so counting them would report the
events as present in an APK where the weaver emitted nothing.

Each advice's *kept* event — the ``get(0)`` the truncating path does emit — is
counted the same way and reported as the positive control. Without it, absence
proves nothing: an advice whose pointcut matched no call site in this APK would
show zero for the dropped event and zero for the kept one, and that is a silent
APK, not a truncating weaver.

Verdict
-------
``pass`` when every dropped event whose advice actually wove (kept > 0) is
present. Against the unrepaired weaver this fails, which is the point: per
INV-INS-108 the failure is recorded as an artefact of the change before the
repair is integrated.

Usage
-----
    python3 scripts/v2_woven_dex_events.py --apk WOVEN.apk \\
        --descriptor MultiSpec_1MonitorAspect.json \\
        --monitor-src MultiSpec_1RuntimeMonitor.java \\
        [--instr-cli instr-cli.jar] [--json OUT]
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
from census_truncated_advices import run_census, sha256  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_INSTR_CLI = REPO_ROOT / "modules/rv-instrumentation-dexlib2/lib/instr-cli.jar"
DEFAULT_WEAVER_SRC = (
    REPO_ROOT.parent
    / "rvsec/rvsec-android/rvsec-instrumentation-dexlib2/advice-emitter/src/main/java"
)

# The generated monitor class. Call sites inside it are the state machine
# talking to itself, never a weave.
MONITOR_CLASS = "MultiSpec_1RuntimeMonitor"

# A smali invoke line: `invoke-static {v0, v1}, Lmop/X;->event(...)V`. Only the
# static forms matter — the weaver emits nothing else for a monitor event.
INVOKE = re.compile(
    r"^\s*invoke-static(?:/range)?\s*\{[^}]*\}\s*,\s*(L[^;]+;)->(\w+)\("
)

# `.class public final Lcom/foo/Bar;` — tracks which class a line belongs to.
CLASS_DECL = re.compile(r"^\.class\b.*?(L[^;]+;)\s*$")


def disassemble(apk: Path, instr_cli: Path, workdir: Path) -> List[Path]:
    """Baksmali every ``classes*.dex`` of ``apk`` into ``workdir``.

    ``instr-cli.jar`` is a fat jar that already bundles baksmali, so this needs
    no tool the weave itself does not need.
    """
    dex_dir = workdir / "dex"
    dex_dir.mkdir(parents=True, exist_ok=True)
    dex_files: List[Path] = []
    with zipfile.ZipFile(apk) as zf:
        for name in sorted(zf.namelist()):
            if re.fullmatch(r"classes\d*\.dex", name):
                target = dex_dir / name
                target.write_bytes(zf.read(name))
                dex_files.append(target)
    if not dex_files:
        raise SystemExit(f"no classes*.dex inside {apk}")

    smali_dirs: List[Path] = []
    for dex in dex_files:
        out = workdir / "smali" / dex.stem
        out.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["java", "-cp", str(instr_cli), "com.android.tools.smali.baksmali.Main",
             "disassemble", str(dex), "-o", str(out)],
            check=True, capture_output=True,
        )
        smali_dirs.append(out)
    return smali_dirs


def count_invokes(smali_dirs: List[Path], events: List[str]) -> Dict[str, Dict[str, int]]:
    """For each event name, the invoke-static sites targeting it, by caller class.

    Callers inside the generated monitor are dropped here rather than at the
    reporting stage, so no count can accidentally include them.
    """
    wanted = set(events)
    hits: Dict[str, Dict[str, int]] = {e: {} for e in events}
    for root in smali_dirs:
        for smali in root.rglob("*.smali"):
            current = ""
            for line in smali.read_text(encoding="utf-8", errors="replace").splitlines():
                declaration = CLASS_DECL.match(line)
                if declaration:
                    current = declaration.group(1)
                    continue
                invoke = INVOKE.match(line)
                if not invoke:
                    continue
                event = invoke.group(2)
                if event not in wanted:
                    continue
                if MONITOR_CLASS in current:
                    continue
                hits[event][current] = hits[event].get(current, 0) + 1
    return hits


def short_event(method: str) -> str:
    """``MultiSpec_1RuntimeMonitor.FooSpec_c3Event`` -> ``FooSpec_c3Event``."""
    return method.rsplit(".", 1)[-1]


def run(apk: Path, descriptor: Path, monitor_src: Path, weaver_src: Path,
        instr_cli: Path) -> Dict[str, object]:
    census = run_census(descriptor, monitor_src, weaver_src)

    advices = []
    for entry in census["inlineRouted"]:
        advices.append({
            "advice": entry["advice"],
            "spec": entry["spec"],
            "kept": short_event(entry["kept"]),
            "dropped": [
                {"event": short_event(d["method"]), "errorTypes": d["errorTypes"]}
                for d in entry["dropped"]
            ],
        })

    events = sorted({a["kept"] for a in advices}
                    | {d["event"] for a in advices for d in a["dropped"]})

    workdir = Path(tempfile.mkdtemp(prefix="v2-woven-"))
    try:
        hits = count_invokes(disassemble(apk, instr_cli, workdir), events)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    def total(event: str) -> int:
        return sum(hits[event].values())

    findings = []
    for advice in advices:
        kept = total(advice["kept"])
        for dropped in advice["dropped"]:
            present = total(dropped["event"])
            findings.append({
                "advice": advice["advice"],
                "spec": advice["spec"],
                "keptEvent": advice["kept"],
                "keptInvokes": kept,
                "droppedEvent": dropped["event"],
                "droppedInvokes": present,
                "errorTypes": dropped["errorTypes"],
                # The advice wove somewhere in this APK, so the dropped event's
                # absence is the weaver's doing and not an unmatched pointcut.
                "adviceWove": kept > 0,
                "present": present > 0,
                "callers": hits[dropped["event"]],
            })

    woven = [f for f in findings if f["adviceWove"]]
    missing = [f for f in woven if not f["present"]]

    return {
        "inputs": {
            "apk": str(apk),
            "apkSha256": sha256(apk),
            "descriptor": str(descriptor),
            "descriptorSha256": sha256(descriptor),
            "monitorSource": str(monitor_src),
            "monitorSourceSha256": sha256(monitor_src),
            "instrCli": str(instr_cli),
            "instrCliSha256": sha256(instr_cli),
        },
        "emissionModel": census["emissionModel"],
        "counts": {
            "droppedEventsInDescriptor": len(findings),
            "advicesThatWove": len({f["advice"] for f in woven}),
            "droppedEventsReachable": len(woven),
            "droppedEventsPresent": len([f for f in woven if f["present"]]),
            "droppedEventsAbsent": len(missing),
        },
        "verdict": "pass" if woven and not missing else "fail",
        "findings": findings,
    }


def render(report: Dict[str, object]) -> str:
    counts = report["counts"]
    out: List[str] = []
    out.append("V2 — do the truncated monitor events reach the woven DEX?")
    out.append("=" * 72)
    out.append("")
    for label, key in (("apk", "apk"), ("descriptor", "descriptor"),
                       ("monitor source", "monitorSource"), ("instr-cli", "instrCli")):
        out.append(f"{label:15s} {report['inputs'][key]}")
        out.append(f"{'':15s}   sha256 {report['inputs'][key + 'Sha256']}")
    out.append("")
    model = report["emissionModel"]
    out.append("INLINE PATH TRUNCATES" if model["truncating"] else "INLINE PATH ITERATES")
    out.append("")
    out.append("Per dropped event")
    out.append("-" * 72)
    for f in report["findings"]:
        types = ", ".join(f["errorTypes"]) or "no error emission"
        state = "PRESENT" if f["present"] else ("ABSENT " if f["adviceWove"] else "n/a    ")
        out.append(f"  [{state}] {f['droppedEvent']}  [{types}]")
        out.append(f"            advice {f['advice']}: kept {f['keptEvent']}"
                   f" x{f['keptInvokes']}, dropped x{f['droppedInvokes']}")
        if not f["adviceWove"]:
            out.append("            advice did not weave in this APK — inconclusive, not evidence")
    out.append("")
    out.append("Counts")
    out.append("-" * 72)
    for key, value in counts.items():
        out.append(f"  {key:28s} {value}")
    out.append("")
    out.append(f"VERDICT: {report['verdict'].upper()}")
    if report["verdict"] == "fail":
        out.append("  Every event above marked ABSENT was planned by the descriptor,")
        out.append("  belongs to an advice that demonstrably wove into this APK, and is")
        out.append("  not in the artefact. That is the truncation, observed end to end.")
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apk", type=Path, required=True, help="the WOVEN apk")
    parser.add_argument("--descriptor", type=Path, required=True)
    parser.add_argument("--monitor-src", type=Path, required=True)
    parser.add_argument("--weaver-src", type=Path, default=DEFAULT_WEAVER_SRC)
    parser.add_argument("--instr-cli", type=Path, default=DEFAULT_INSTR_CLI)
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args()

    for label, path in (("apk", args.apk), ("descriptor", args.descriptor),
                        ("monitor source", args.monitor_src),
                        ("instr-cli jar", args.instr_cli)):
        if not path.is_file():
            raise SystemExit(f"{label} not found at {path}")

    report = run(args.apk, args.descriptor, args.monitor_src,
                 args.weaver_src, args.instr_cli)
    print(render(report))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(f"\nJSON written to {args.json}")
    return 0 if report["verdict"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
