#!/usr/bin/env python3
"""ALFA batch A -- algorithmic language-inclusion check over EFFECTIVE automata (D-piloto-3).

Specs: DHGenParameterSpecSpec, HMACParameterSpecSpec, PBEParameterSpecSpec,
       IvParameterSpec (spec IvParameterSpecSpec), SecretKeySpecSpec.

Effective automaton source: the Prop_1_transition_* arrays parsed DIRECTLY from the
generated <Spec>RuntimeMonitor.java of the round's common input
(batchA/generation_manifest.md hashes), not from the .mop syntax.
RV-Monitor state encoding for these five (verified by reading the categories in the
same files): state 0 = initial, category match = (state == 1), category fail =
(state == 2); a missing edge does not exist in this encoding -- rows are total.

Reference automaton: normalized from the CrySL ORDER of the api30 rule under
reading A (D-piloto-1; comma outermost -- no comma occurs in these five ORDERs):
  DHGenParameterSpec : ORDER c1          alphabet {Ctor}
  HMACParameterSpec  : ORDER c1          alphabet {Ctor}
  PBEParameterSpec   : ORDER Cons := c1|c2   alphabet {Ctor2, Ctor3}
  IvParameterSpec    : ORDER Cons := cons1|cons2  alphabet {Ctor1, Ctor3}
  SecretKeySpec      : ORDER Cons := c1|c2   alphabet {Ctor2, Ctor4}

Abstraction alpha (per-spec section of alfa_report.md): each Java constructor call
(after returning) is one CrySL Cons event; the MOP side splits it into a
conforming carrier (c1/c2) and a violating carrier (c3/c4) discriminated by the
condition(...) prologue. The guard-satisfying projection maps the Java call to the
conforming carrier; the guard-violating projection maps it to the violating
carrier. CrySL treats a REQUIRES/CONSTRAINT violation as a predicate/constraint
error, NOT as an ORDER violation, so on the violating projection the correct
ORDER-verdict is "no sequence violation" -- which is what state 0 self-loops give.

Realizability (dimension-5 fact used by the language argument): the monitor is
parametric on the returned object; a given object is constructed exactly once, so
every realizable per-instance trace has length exactly 1.  The checker therefore
reports (a) dual inclusion over realizable traces (length 1), and (b) the behavior
of the full table on unrealizable longer traces, to document vacuous transitions.

Deterministic; single run (pre_registro section 5).
"""

import re, sys, os
from collections import deque

SCRATCH = ("/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-"
           "workspace-rv-rvsec-rv-android/d2ed0fb6-e4be-4945-abb4-21d8af2acd28/"
           "scratchpad/batchA")

MONITORS = {
    "DHG": f"{SCRATCH}/gen_DHGenParameterSpecSpec/out/DHGenParameterSpecSpecRuntimeMonitor.java",
    "HMC": f"{SCRATCH}/gen_HMACParameterSpecSpec/out/HMACParameterSpecSpecRuntimeMonitor.java",
    "PBE": f"{SCRATCH}/gen_PBEParameterSpecSpec/out/PBEParameterSpecSpecRuntimeMonitor.java",
    "IVP": f"{SCRATCH}/gen_IvParameterSpec/out/IvParameterSpecRuntimeMonitor.java",
    "SKS": f"{SCRATCH}/gen_SecretKeySpecSpec/out/SecretKeySpecSpecRuntimeMonitor.java",
}

TR_RE = re.compile(r"Prop_1_transition_(\w+)\[\]\s*=\s*\{([0-9,\s]+)\}")

def parse_tables(path):
    src = open(path).read()
    tables = {}
    for name, body in TR_RE.findall(src):
        tables[name] = [int(x) for x in body.split(",")]
    # sanity: category encoding as stated in the docstring (class prefix = declared
    # spec name, which for IvParameterSpec.mop differs from the file name -- match
    # the pattern generically instead of rebuilding the identifier)
    flat = src.replace("this.", "")
    base = os.path.basename(path).replace("RuntimeMonitor.java", "")
    assert re.search(r"Category_fail = (nextstate|Prop_1_state) == 2", flat), \
        f"{base}: fail category is not state==2 -- encoding assumption broken"
    assert re.search(r"Category_match = (nextstate|Prop_1_state) == 1", flat), \
        f"{base}: match category is not state==1"
    return tables

# ---- per-spec model ----------------------------------------------------------
# conforming[e] / violating[e]: MOP event names per Java constructor arity.
SPECS = {
    "DHG": dict(ctors=["Ctor2i"], conforming={"Ctor2i": "c1"}, violating={"Ctor2i": None}),
    "HMC": dict(ctors=["Ctor1i"], conforming={"Ctor1i": "c"},  violating={"Ctor1i": None}),
    "PBE": dict(ctors=["Ctor2", "Ctor3"],
                conforming={"Ctor2": "c1", "Ctor3": "c2"},
                violating={"Ctor2": "c3", "Ctor3": None}),      # <-- no violating carrier for 3-arg
    "IVP": dict(ctors=["Ctor1", "Ctor3"],
                conforming={"Ctor1": "c1", "Ctor3": "c2"},
                violating={"Ctor1": "c3", "Ctor3": "c4"}),
    "SKS": dict(ctors=["Ctor2", "Ctor4"],
                conforming={"Ctor2": "c1", "Ctor4": "c2"},
                violating={"Ctor2": "c3", "Ctor4": "c4"}),
}

def run_spec(tag):
    spec = SPECS[tag]
    tables = parse_tables(MONITORS[tag])
    print(f"== {tag} ==")
    print(f"   parsed transition tables: " +
          ", ".join(f"{k}={v}" for k, v in sorted(tables.items())))

    # (a) realizable traces: length exactly 1, one Java ctor call.
    #     CrySL reference: word of length 1 over the Cons alternatives -> ACCEPT.
    #     MOP verdicts per projection:
    ok = True
    for ctor in spec["ctors"]:
        # guard-satisfying projection -> conforming carrier
        ev = spec["conforming"][ctor]
        st = tables[ev][0]
        match, fail = st == 1, st == 2
        verdict = "MATCH" if match else ("FAIL" if fail else f"state{st}")
        good = match and not fail
        ok &= good
        print(f"   [satisfying] {ctor} -> {ev}: 0 --{ev}--> {st}  ({verdict})  "
              f"CrySL: word in L(Cons) => {'OK' if good else 'COUNTEREXAMPLE'}")
        # guard-violating projection -> violating carrier (or silent suppression)
        vev = spec["violating"][ctor]
        if vev is None:
            print(f"   [violating ] {ctor} -> NO CARRIER: event suppressed before "
                  f"handleEvent (silent).  CrySL: predicate/constraint error expected "
                  f"=> report emitted only if a body exists: NONE  (documented as "
                  f"suppression; see claims)")
        else:
            st = tables[vev][0]
            spurious = st == 2
            ok &= not spurious
            print(f"   [violating ] {ctor} -> {vev}: 0 --{vev}--> {st}  "
                  f"(match={st==1}, fail={st==2})  CrySL: NOT an ORDER violation => "
                  f"{'OK: no @fail, no match' if not spurious and st != 1 else 'COUNTEREXAMPLE'}")

    # (b) full-table behavior on unrealizable traces (documentation of vacuity)
    evs = sorted(tables)
    from_accept = {e: tables[e][1] for e in evs}
    print(f"   [vacuous   ] from accepting state 1: " +
          ", ".join(f"{e}->{s}" for e, s in from_accept.items()) +
          "   (reachable only by a second construction of the SAME object -- impossible)")
    print(f"   [vacuous   ] @fail reachable only from state>=1 => dead per instance; "
          f"handler (ErrorCollector InvalidSequenceOfMethodCalls + __RESET) is dead code")

    # (c) dual inclusion statement over realizable traces
    #     L(CrySL) = { [ctor] : ctor in ctors }  (all length-1 words)
    #     alpha(L(MOP)) accepted = { [ctor] whose conforming carrier reached state 1 }
    incl1 = all(tables[spec["conforming"][c]][0] == 1 for c in spec["ctors"])
    #     MOP accepts nothing else of length 1 (violating carriers reach 0, not 1),
    #     and nothing longer is realizable.
    incl2 = all(spec["violating"][c] is None or tables[spec["violating"][c]][0] != 1
                for c in spec["ctors"])
    print(f"   L(CrySL) [satisfying proj.] subset of alpha(L(MOP)): "
          f"{'HOLDS' if incl1 else 'FAILS'}")
    print(f"   alpha(L(MOP)) subset of L(CrySL): {'HOLDS' if incl2 else 'FAILS'}")
    print(f"   dual inclusion on realizable traces: {'HOLDS' if incl1 and incl2 else 'FAILS'}\n")
    return incl1 and incl2

if __name__ == "__main__":
    allok = True
    for tag in ["DHG", "HMC", "PBE", "IVP", "SKS"]:
        allok &= run_spec(tag)
    print(f"OVERALL (language dimension only, guard projections as stated): "
          f"{'ALL DUAL INCLUSIONS HOLD' if allok else 'AT LEAST ONE FAILS'}")
    print("NOTE: suppression findings (PBE 3-arg, DHG) are NOT language-dimension "
          "counterexamples -- they are binding/predicate findings, filed separately.")
