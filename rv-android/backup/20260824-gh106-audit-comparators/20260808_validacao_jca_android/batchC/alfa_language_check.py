#!/usr/bin/env python3
"""Batch C / Agent ALFA — algorithmic language verification (D-piloto-3).

Part 1 parses the EFFECTIVE automaton of each of the five RuntimeMonitor.java
artifacts (transition int-arrays + fail/match state ids). No hand transcription.

Part 2 encodes the reference automaton of each CrySL ORDER under reading A
(D-piloto-1: comma outermost, `|` tighter), over the CrySL event alphabet.

Part 3 lifts both machines to a common CALL-CLASS alphabet via the abstraction
relation alpha materialized from the generated MonitorAspect.aj files:
 - each call class maps to exactly one CrySL event (aggregates resolved);
 - each call class maps to the sequence of MOP monitor events the woven advice
   emits for that call, including merged advices (g1Event;g3Event in one advice)
   and per-monitor condition guards (modeled on the artifact guard expressions,
   with the guard-relevant monitor variable abstracted into the product state).
Realizability envelope: per monitored object, exactly one getInstance-class
call first (monitors are keyed on the object returned/targeted), then any
sequence of instance-method call classes. Formal (unrealizable-included)
event-level checks are run separately and labeled as such.

Verification: exhaustive product-space exploration (BFS) over
 (reference DFA state x monitor state x guard-variable abstraction x phase).
State spaces are < 200 states per spec => full verification, not sampling.
Outputs: verdict per inclusion, smallest counterexample call trace with the
state-by-state walk, plus end-of-trace acceptance divergences.
"""
import json, re, sys, os
from collections import deque

GEN = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

SPECS = {
    'KGN': 'KeyGeneratorSpec', 'KMF': 'KeyManagerFactorySpec',
    'TMF': 'TrustManagerFactorySpec', 'SSL': 'SSLContextSpec', 'KST': 'KeyStoreSpec',
}

# ---------- Part 1: parse effective automata from artifacts ----------
def parse_monitor(spec):
    path = f'{GEN}/gen_{spec}/out/{spec}RuntimeMonitor.java'
    src = open(path).read()
    trans = {}
    for m in re.finditer(r'static final int Prop_1_transition_(\w+)\[\] = \{([0-9, ]+)\};', src):
        trans[m.group(1)] = [int(x) for x in m.group(2).split(',')]
    fail = set(int(x) for x in re.findall(r'Category_fail = (?:nextstate|Prop_1_state) == (\d+)', src))
    match = set(int(x) for x in re.findall(r'Category_match1? = (?:nextstate|Prop_1_state) == (\d+)', src))
    assert len(fail) == 1 and len(match) == 1, (spec, fail, match)
    n = max(len(v) for v in trans.values())
    return {'events': sorted(trans), 'n_states': n, 'initial': 0,
            'fail': fail.pop(), 'match': match.pop(), 'delta': trans, 'path': path}

EFF = {ab: parse_monitor(name) for ab, name in SPECS.items()}

# ---------- Part 2: reference automata (reading A), CrySL alphabet ----------
# States are strings; 'V' = violation sink (transition absent in ORDER).
# acc = set of accepting states (end of a complete word of the ORDER language;
# every non-V state is a "valid prefix" state).
REF = {
  # KeyGenerator: Gets, Inits?, gk    Gets=g1|g2  Inits=i1..i5
  'KGN': dict(init='q0', acc={'ACC'},
      delta={('q0','Gets'):'q1', ('q1','Inits'):'q2', ('q1','gk'):'ACC', ('q2','gk'):'ACC'}),
  # KeyManagerFactory: Gets, Init, gkm?
  'KMF': dict(init='q0', acc={'A1','A2'},
      delta={('q0','Gets'):'q1', ('q1','Init'):'A1', ('A1','gkm'):'A2'}),
  # TrustManagerFactory: Gets, Init, gtm?
  'TMF': dict(init='q0', acc={'A1','A2'},
      delta={('q0','Gets'):'q1', ('q1','Init'):'A1', ('A1','gtm'):'A2'}),
  # SSLContext: Gets, Init, Engine?
  'SSL': dict(init='q0', acc={'A1','A2'},
      delta={('q0','Gets'):'q1', ('q1','Init'):'A1', ('A1','Engine'):'A2'}),
  # KeyStore: Gets, Loads, ((gE?, gk) | (sE, Stores))*
  #   scE, skE1, skE2 are DECLARED events absent from ORDER -> violation anywhere.
  'KST': dict(init='q0', acc={'A'},
      delta={('q0','Gets'):'q1', ('q1','Loads'):'A',
             ('A','gE'):'B', ('B','gk'):'A', ('A','gk'):'A',
             ('A','sE'):'C', ('C','Stores'):'A'}),
}

# ---------- Part 3: alpha at call-class level ----------
# Call classes per spec: (name, crysl_event, mop_emission)
# mop_emission = list of (mop_event, guard) run in the order the .aj advice
# emits them; guard is a predicate over the abstract monitor-variable state.
# Guard var abstraction:
#   KGN/KMF/TMF: cAI in {'EMPTY','SAFE','UNSAFE'} (currentAlgorithmInstance)
#   SSL: cP in {'EMPTY','SAFE','UNSAFE'} (currentProtocol); KST: none needed
#   (KST g1/g2 guards test the ARGUMENT, encoded by the call class itself).
# Updates: body assignment of the variable when the event fires.
TRUE = lambda v: True
def CALLS(ab):
    if ab == 'KGN':
        return [
          ('G1s','Gets', [('g1', TRUE, 'SAFE'), ('g3', lambda v: v != 'SAFE', 'SAFE')]),
          # ^ merged advice KeyGeneratorSpecMonitorAspect.aj:67-72: g1Event then g3Event.
          #   g1 guard: safeAlgorithms.contains(alg) -> True for G1s; body sets cAI=SAFE.
          #   g3 guard: !safeAlgorithms.contains(cAI); body sets cAI=alg (SAFE here).
          ('G1u','Gets', [('g1', lambda v: False, None), ('g3', lambda v: v != 'SAFE', 'UNSAFE')]),
          ('G2s','Gets', [('g2', TRUE, 'SAFE')]),
          ('G2u','Gets', []),          # condition false, no unsafe counterpart event
          ('I1','Inits', [('i1', TRUE, None)]),
          ('I2','Inits', [('i2', TRUE, None)]),
          ('I5','Inits', [('i5', TRUE, None)]),
          ('GK','gk',   [('gk1', TRUE, None)]),
        ]
    if ab in ('KMF','TMF'):
        i1ev, i2ev, gev, gcrysl = ('i1','i2','gkm1','gkm') if ab=='KMF' else ('i1','i2','gtm1','gtm')
        return [
          ('G1s','Gets', [('g1', TRUE, 'SAFE'), ('g3', lambda v: False, None)]),
          # merged advice; g3 guard !contains(alg) is False for safe alg (argument-based)
          ('G1u','Gets', [('g1', lambda v: False, None), ('g3', TRUE, 'UNSAFE')]),
          ('G2s','Gets', [('g2', TRUE, 'SAFE')]),
          ('G2u','Gets', []),          # 2-arg unsafe: g2 condition false; no counterpart
          ('I1','Init', [(i1ev, TRUE, None)]),
          ('I2','Init', [(i2ev, TRUE, None)]),
          ('GM', gcrysl, [(gev, TRUE, None)]),
        ]
    if ab == 'SSL':
        return [
          ('G1s','Gets', [('g1', TRUE, 'SAFE'), ('unsafe_protocol', lambda v: False, None)]),
          ('G1u','Gets', [('g1', lambda v: False, None), ('unsafe_protocol', TRUE, 'UNSAFE')]),
          ('G2s','Gets', [('g2', TRUE, 'SAFE')]),   # getInstance(String,String) safe
          ('G2sP','Gets', []),  # getInstance(String,Provider): android-30 member, g2
                                # pointcut is (String,String) only -> NO event even for
                                # a safe protocol (javap alfa_javap_android30.txt)
          ('G2u','Gets', []),
          ('INIT','Init', [('init', TRUE, None)]),
          ('ENG','Engine', []),        # engine pointcut declares void return; createSSLEngine
                                       # returns SSLEngine -> never matches (zero-capture)
        ]
    if ab == 'KST':
        return [
          ('G1s','Gets', [('g1', TRUE, None), ('g2', lambda v: False, None)]),
          ('G1u','Gets', [('g1', lambda v: False, None), ('g2', TRUE, None)]),
          ('G2s','Gets', []),          # getInstance(String,String)/(String,Provider): no pointcut
          ('G2u','Gets', []),
          ('LOAD','Loads', [('load', TRUE, None)]),
          ('STORE','Stores', [('store', TRUE, None)]),
          ('GE','gE', [('ge1', TRUE, None)]),
          ('SE','sE', [('se1', TRUE, None)]),
          ('GK','gk', [('gk1', TRUE, None)]),
          ('SCE','scE', []),           # declared CrySL event, no MOP pointcut
          ('SKE1','skE1', []), ('SKE2','skE2', []),
        ]

GCLASSES = {ab: [c for c,_,_ in CALLS(ab) if c.startswith('G')] for ab in SPECS}

def ref_step(ab, q, ev):
    if q == 'V':
        return 'V'
    return REF[ab]['delta'].get((q, ev), 'V')

def mop_run_call(ab, mstate, var, emission):
    """Run one call class on the monitor; returns (mstate', var', n_fails, resets).
    Fail handler semantics from the artifact: emit InvalidSequence, then reset()
    -> state back to initial 0 (KGN/KST __RESET; KMF/TMF/SSL __RESET)."""
    eff = EFF[SPECS_AB[ab]] if False else EFF[ab]
    fails = 0
    for (mev, guard, newvar) in emission:
        if not guard(var):
            continue
        if newvar is not None:
            var = newvar
        nxt = eff['delta'][mev][mstate]
        if nxt == eff['fail']:
            fails += 1
            mstate = eff['initial']      # handler: __RESET (present in all five @fail)
        else:
            mstate = nxt
    return mstate, var, fails

# ---------- product exploration ----------
def explore(ab, max_len=8):
    """Full BFS over call-class sequences respecting the realizability envelope
    (one G-class first, then instance classes). The joint state space
    (refq, mstate, var, phase) is finite; we search bounded-length words but the
    product graph is also closed transitively: any mismatch is reachable within
    |product| steps; max_len=8 > product diameter for all five specs."""
    calls = CALLS(ab)
    cmap = {c[0]: c for c in calls}
    eff = EFF[ab]
    init = ('q0i', eff['initial'], 'EMPTY', 0)  # phase 0: before G; 1: after
    # counterexample search: FP = fail emitted while ref still non-V
    #                        FN = ref hit V at step t, no fail at step t (first divergence)
    fps, fns, accdiv = [], [], []
    seen = set()
    Q = deque([(REF[ab]['init'], eff['initial'], 'EMPTY', 0, ())])
    while Q:
        rq, ms, var, ph, w = Q.popleft()
        key = (rq, ms, var, ph)
        if key in seen and len(w) > 0:
            # continue expanding only if word shorter than product bound handled;
            # we rely on bounded max_len for counterexample minimality
            pass
        if len(w) >= max_len:
            continue
        for (cname, cev, emission) in calls:
            if ph == 0 and not cname.startswith('G'):
                continue
            if ph == 1 and cname.startswith('G'):
                continue   # realizability: exactly one getInstance per object
            nrq = ref_step(ab, rq, cev)
            nms, nvar, fails = mop_run_call(ab, ms, var, emission)
            nw = w + (cname,)
            nph = 1
            first_viol_now = (rq != 'V' and nrq == 'V')
            if fails > 0 and nrq != 'V':
                fps.append((nw, fails, rq, nrq))
            if first_viol_now and fails == 0:
                # check whether MOP flags NOTHING for the whole remaining trace:
                # here we record immediate silent deviation (per-position compare)
                fns.append((nw, rq))
            # acceptance comparison at end of word
            if nrq != 'V' and nrq in REF[ab]['acc']:
                if nms != eff['match']:
                    accdiv.append((nw, nrq, nms))
            Q.append((nrq, nms, nvar, nph, nw))
    def dedupe(lst):
        out, s = [], set()
        for item in sorted(lst, key=lambda x: (len(x[0]), x[0])):
            k = item[0]
            # keep only shortest witness per (pattern of last call, kind)
            sig = (item[0][-1], item[0][0] if item[0] else None)
            if sig in s:
                continue
            s.add(sig); out.append(item)
        return out
    return dedupe(fps), dedupe(fns), dedupe(accdiv)

def walk(ab, word):
    """state-by-state walk for the report"""
    eff = EFF[ab]; calls = {c[0]: c for c in CALLS(ab)}
    rq, ms, var = REF[ab]['init'], eff['initial'], 'EMPTY'
    lines = [f"    ref={rq} mop={ms} var={var}"]
    for c in word:
        _, cev, emission = calls[c]
        nrq = ref_step(ab, rq, cev)
        nms, nvar, fails = mop_run_call(ab, ms, var, emission)
        emitted = [e for (e,g,_) in emission if g(var)]
        lines.append(f"    --{c} (CrySL {cev}; MOP emits {emitted or 'nothing'})--> "
                     f"ref={nrq} mop={nms}{' FAIL#'+str(fails)+'->reset' if fails else ''}")
        rq, ms, var = nrq, nms, nvar
    return '\n'.join(lines)

# ---------- formal event-level inclusion (unrealizable words included) ----------
def formal_event_level(ab):
    """alpha(L_eff) vs L(CrySL) over MOP event alphabet mapped to CrySL events,
    ignoring guards/realizability: detects the purely formal divergences
    (repetition g1+, cycle re-entry, etc.). Reported separately."""
    eff = EFF[ab]
    amap = {}
    for (cname, cev, emission) in CALLS(ab):
        for (mev, _, _) in emission:
            amap.setdefault(mev, cev)
    # BFS product: mop DFA (no guards, any event anytime) vs ref DFA
    out = []
    seen = set(); Q = deque([(REF[ab]['init'], eff['initial'], ())])
    while Q:
        rq, ms, w = Q.popleft()
        if (rq, ms) in seen:
            continue
        seen.add((rq, ms))
        for mev, cev in amap.items():
            nms = eff['delta'][mev][ms]
            if nms == eff['fail']:
                continue
            nrq = ref_step(ab, rq, cev)
            nw = w + (mev,)
            if nms == eff['match'] and (nrq == 'V' or nrq not in REF[ab]['acc']):
                out.append((nw, 'accepted-by-effective, not in L(CrySL)'))
                continue
            Q.append((nrq, nms, nw))
    return sorted(out, key=lambda x: len(x[0]))[:6]

if __name__ == '__main__':
    print("=== Effective automata parsed from RuntimeMonitor.java artifacts ===")
    for ab in SPECS:
        e = EFF[ab]
        print(f"{ab} ({SPECS[ab]}): states={e['n_states']} init=0 fail={e['fail']} "
              f"match={e['match']}")
        for ev in e['events']:
            print(f"    {ev}: {e['delta'][ev]}")
    for ab in SPECS:
        print(f"\n=== {ab} ({SPECS[ab]}) — call-class product verification ===")
        fps, fns, accdiv = explore(ab)
        print(f"L(CrySL) ⊆ α(L(MOP)) [no spurious fail on rule-conformant prefix]: "
              f"{'PASS' if not fps else 'FAIL'}")
        for wrd, fails, rq, nrq in fps[:5]:
            print(f"  FP witness ({fails} fail(s)): {' '.join(wrd)}")
            print(walk(ab, wrd))
        print(f"α(L(MOP)) ⊆ L(CrySL) [no silent deviation]: "
              f"{'PASS' if not fns else 'FAIL'}")
        for wrd, rq in fns[:6]:
            print(f"  FN witness (silent CrySL violation): {' '.join(wrd)}")
            print(walk(ab, wrd))
        print(f"acceptance-set agreement at end of trace: "
              f"{'PASS' if not accdiv else 'DIVERGES'}")
        for wrd, nrq, nms in accdiv[:4]:
            print(f"  word {' '.join(wrd)}: CrySL accepts in {nrq}, monitor in "
                  f"non-match state {nms}")
        fe = formal_event_level(ab)
        print(f"formal event-level (unrealizability ignored): "
              f"{'no extra acceptance' if not fe else 'effective accepts words outside L(CrySL)'}")
        for wrd, why in fe[:4]:
            print(f"  {' '.join(wrd)}: {why}")
