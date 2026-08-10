#!/usr/bin/env python3
"""JUDGE standard test J1 (batch A): programmatic walk over the transition tables
parsed directly from the round-input *RuntimeMonitor.java artifacts. Usage: juiz_walk.py [dir containing gen_<Spec>/out] — regenerate the gen_* dirs with the commands in generation_manifest.md and verify hashes first (pilot judge
adjustment 1). States: 0=start, 1=match(accepting), 2=fail. Category flags per the
generated dispatch: match iff nextstate==1, fail iff nextstate==2."""
import re, pathlib, sys

BASE = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent.parent
MON = {
    "DHG": BASE / "gen_DHGenParameterSpecSpec/out/DHGenParameterSpecSpecRuntimeMonitor.java",
    "HMC": BASE / "gen_HMACParameterSpecSpec/out/HMACParameterSpecSpecRuntimeMonitor.java",
    "PBE": BASE / "gen_PBEParameterSpecSpec/out/PBEParameterSpecSpecRuntimeMonitor.java",
    "IVP": BASE / "gen_IvParameterSpec/out/IvParameterSpecRuntimeMonitor.java",
    "SKS": BASE / "gen_SecretKeySpecSpec/out/SecretKeySpecSpecRuntimeMonitor.java",
}
RX = re.compile(r"Prop_1_transition_(\w+)\[\]\s*=\s*\{([0-9,\s]+)\}")

def tables(path):
    t = {}
    for m in RX.finditer(path.read_text()):
        t[m.group(1)] = [int(x) for x in m.group(2).split(",")]
    return t

def walk(t, trace, start=0):
    s = start
    for ev in trace:
        s = t[ev][s]
    return s

ok = True
def check(cond, msg):
    global ok
    print(("PASS " if cond else "FAIL ") + msg)
    ok = ok and cond

for spec, path in MON.items():
    t = tables(path)
    print(f"== {spec} tables: " + ", ".join(f"{k}={v}" for k, v in sorted(t.items())))
    conf = [k for k, v in t.items() if v == [1, 2, 2]]
    viol = [k for k, v in t.items() if v == [0, 2, 2]]
    check(len(conf) + len(viol) == len(t), f"{spec}: every event is {{1,2,2}} or {{0,2,2}}")
    for c in conf:
        check(walk(t, [c]) == 1, f"{spec}: single {c} -> state 1 (match/accepting)")
        check(walk(t, [c, c]) == 2, f"{spec}: second event on SAME monitor -> state 2 (fail)")
    for v in viol:
        check(walk(t, [v]) == 0, f"{spec}: single {v} -> state 0 (loop, no match, no fail)")
        if conf:
            check(walk(t, [v, conf[0]]) == 1, f"{spec}: {v} then {conf[0]} -> 1 (Kleene prefix)")
    # fail unreachable with <=1 event delivered to a monitor
    reach1 = {walk(t, [e]) for e in t}
    check(2 not in reach1, f"{spec}: fail UNREACHABLE with a single event per monitor")

print("\n-- parametrization walk (indexing read from the artifacts §0) --")
print("DHG/PBE/IVP/SKS: MapOfMonitor keyed on the returned object -> one event per monitor")
print("  => fail dead in realizable traces for these four (confirmed above: needs 2nd event).")
print("HMC: single static Tuple2 (global monitor) -> ALL constructions share one monitor")
t = tables(MON["HMC"])
check(walk(t, ["c", "c"]) == 2,
      "HMC(global): two CrySL-LEGAL constructions in one process -> fail state 2 "
      "(separating trace: L(CrySL) accepts, artifact fires InvalidSequenceOfMethodCalls)")
print("\nALL PASS" if ok else "\nSOME CHECK FAILED")
sys.exit(0 if ok else 1)
