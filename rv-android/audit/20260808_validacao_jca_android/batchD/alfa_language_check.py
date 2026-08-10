#!/usr/bin/env python3
"""Batch D / Agent ALFA — algorithmic language verification (D-piloto-3).

Same method as batch C (audit/.../batchC/alfa_language_check.py), adapted to the
five batch D specs: MacSpec (MAC), MessageDigestSpec (MDG),
KeyPairGeneratorSpec (KPG), SecureRandomSpec (SRD), SignatureSpec (SIG).

Part 1 parses the EFFECTIVE automaton of each RuntimeMonitor.java artifact
(transition int-arrays + fail/match state ids from the Category_ assignments).
No hand transcription.

Part 2 encodes the reference automaton of each CrySL ORDER under reading A
(D-piloto-1: comma outermost, `|` tighter), over the CrySL event alphabet of
the raw api30 rule.

Part 3 lifts both machines to a common CALL-CLASS alphabet via alpha,
materialized from the generated MonitorAspect.aj files: each call class maps to
one CrySL event (or None when the raw rule declares no event for the member)
and to the ordered MOP event emission of the woven advice, including merged
advices (Mac g1;g3 one advice, MDG g1;g4 one advice) and per-monitor condition
guards (modeled on the artifact guard expressions). Environment-dependent
guards (ExecutionContext reads) are encoded as call-class variants (e.g. I1k =
init with GENERATED_KEY-marked key, I1u = unmarked), each realizable (marked:
via a monitored producer; unmarked: keys from unmonitored sources such as
KeyAgreement/KeyFactory/AndroidKeyStore).

Fail-handler semantics from the artifacts: MAC/MDG/SRD/SIG @fail call
this.reset() (state back to initial); KPG @fail has NO reset -> fail sink,
every later event fails again (KeyPairGeneratorSpecRuntimeMonitor.java:471-477).

Verification: exhaustive BFS over bounded-length call words (max_len covers the
product diameter; all products < 300 joint states). FP = monitor emits fail on
a word whose CrySL image is ORDER-conformant (still a valid prefix);
FN = CrySL image leaves the language at step t and the monitor emits nothing at
that step; acceptance divergence = CrySL-complete word ends outside the match
category. Constraint/predicate divergences are NOT decided here (harness).
"""
import re, os
from collections import deque

GEN = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

SPECS = {
    'MAC': 'MacSpec', 'MDG': 'MessageDigestSpec', 'KPG': 'KeyPairGeneratorSpec',
    'SRD': 'SecureRandomSpec', 'SIG': 'SignatureSpec',
}
RESETS = {'MAC': True, 'MDG': True, 'KPG': False, 'SRD': True, 'SIG': True}

# ---------- Part 1: parse effective automata ----------
def parse_monitor(spec):
    path = f'{GEN}/gen_{spec}/out/{spec}RuntimeMonitor.java'
    src = open(path).read()
    trans = {}
    for m in re.finditer(r'static final int Prop_1_transition_(\w+)\[\] = \{([0-9, ]+)\};', src):
        trans[m.group(1)] = [int(x) for x in m.group(2).split(',')]
    fail = set(int(x) for x in re.findall(
        r'Category_fail = (?:nextstate|Prop_1_state) == (\d+)', src))
    match = set()
    for mm in re.findall(r'Category_match1? = ((?:(?:nextstate|Prop_1_state) == \d+(?:\|\| )?)+);', src):
        for d in re.findall(r'== (\d+)', mm):
            match.add(int(d))
    assert len(fail) == 1, (spec, fail)
    assert match, (spec, match)
    n = max(len(v) for v in trans.values())
    return {'events': sorted(trans), 'n_states': n, 'initial': 0,
            'fail': fail.pop(), 'match': match, 'delta': trans, 'path': path}

EFF = {ab: parse_monitor(name) for ab, name in SPECS.items()}

# ---------- Part 2: reference automata (reading A), raw api30 CrySL alphabet ----------
# 'V' = out of the language. acc = states ending a complete ORDER word.
REF = {
  # Mac: Gets, Inits, (Finals | (Updates+, Finals))
  #   Gets = g1|g2, BOTH getInstance(macAlg) 1-arg (Mac.cryptsl:33-37).
  'MAC': dict(init='q0', acc={'ACC'},
      delta={('q0','Gets'):'q1', ('q1','Inits'):'q2', ('q2','Finals'):'ACC',
             ('q2','Updates'):'q3', ('q3','Updates'):'q3', ('q3','Finals'):'ACC'}),
  # MessageDigest: Gets, (DWOU | (Updates+, Digests))+   DWOU=d2, Digests=d1|d2|d3
  'MDG': dict(init='q0', acc={'A'},
      delta={('q0','Gets'):'q1', ('q1','DWOU'):'A', ('q1','Updates'):'q2',
             ('q2','Updates'):'q2', ('q2','Digests'):'A', ('q2','DWOU'):'A',
             ('A','DWOU'):'A', ('A','Updates'):'q2'}),
  # KeyPairGenerator: Gets, Inits, Generators  (Inits mandatory, exactly one)
  'KPG': dict(init='q0', acc={'ACC'},
      delta={('q0','Gets'):'q1', ('q1','Inits'):'q2', ('q2','Generators'):'ACC'}),
  # SecureRandom: Ins, Seeds?, Ends*   Ins=Gets|Cons, Ends=gS|ne|nB
  'SRD': dict(init='q0', acc={'A1','A2','A3'},
      delta={('q0','Ins'):'A1', ('A1','Seeds'):'A2', ('A1','Ends'):'A3',
             ('A2','Ends'):'A3', ('A3','Ends'):'A3'}),
  # Signature: Gets, ((InitSigns+, (Updates+, Signs+)+)+ |
  #                   (InitVerifies+, (Updates*, Verifies+)+)+)
  'SIG': dict(init='q0', acc={'s3','r3'},
      delta={('q0','Gets'):'q1',
             ('q1','InitSigns'):'s1', ('s1','InitSigns'):'s1',
             ('s1','Updates'):'s2', ('s2','Updates'):'s2', ('s2','Signs'):'s3',
             ('s3','Signs'):'s3', ('s3','Updates'):'s2', ('s3','InitSigns'):'s1',
             ('q1','InitVerifies'):'r1', ('r1','InitVerifies'):'r1',
             ('r1','Updates'):'r2', ('r2','Updates'):'r2',
             ('r1','Verifies'):'r3', ('r2','Verifies'):'r3',
             ('r3','Verifies'):'r3', ('r3','Updates'):'r2', ('r3','InitVerifies'):'r1'}),
}

# ---------- Part 3: alpha at call-class level ----------
# (name, crysl_event_or_None, [(mop_event, guard(var), var')])
# Guard var: MAC/MDG/KPG/SIG currentAlgorithmInstance-family abstraction where
# needed; environment marks encoded in the call-class choice itself.
TRUE = lambda v: True
def CALLS(ab):
    if ab == 'MAC':
        return [
          # merged advice MacSpecMonitorAspect.aj:45-51: g1Event then g3Event, both
          # guards argument-based (safeAlgorithms.contains(alg) / negation).
          ('G1s','Gets', [('g1', TRUE, 'SAFE'), ('g3', lambda v: False, None)]),
          ('G1u','Gets', [('g1', lambda v: False, None), ('g3', TRUE, 'UNSAFE')]),
          # 2-arg getInstance: NOT a raw-rule event (Mac.cryptsl g1=g2=1-arg).
          # Creation by an unmodeled member -> object UNTRACKED by the rule
          # (batch C convention for born-invisible objects: rule stays silent,
          # never accepts); assumption declared in the report.
          ('G2s','UNTRACK', [('g2', TRUE, 'SAFE')]),
          ('G2u','UNTRACK', []),                  # condition false; no counterpart
          ('GP', 'UNTRACK', []),                  # getInstance(String,Provider): no pointcut
          # init: i1/i2 condition = validate(GENERATED_KEY,key) -> suppression
          ('I1k','Inits', [('i1', TRUE, None)]),  # key marked
          ('I1u','Inits', []),                    # key unmarked: SUPPRESSED
          ('I2k','Inits', [('i2', TRUE, None)]),
          ('I2u','Inits', []),
          ('UA','Updates', [('uArr', TRUE, None)]),
          ('UB','Updates', [('uByte', TRUE, None)]),
          ('UBUF',None, [('uBuf', TRUE, None)]),  # ByteBuffer update: not a rule event
          ('F1','Finals', [('f1', TRUE, None)]),
          ('F2','Finals', [('f2', TRUE, None)]),
          ('F3','Finals', [('f3', TRUE, None)]),  # NB: unbound event, global dispatch
        ]
    if ab == 'MDG':
        return [
          # merged advice MessageDigestSpecMonitorAspect.aj:41-46: g1Event then
          # g4Event; g1 guard argument-based, g4 guard FIELD-based
          # (!algorithms.contains(currentAlgorithmInstance.toUpperCase())).
          ('G1s','Gets', [('g1', TRUE, 'SAFE'), ('g4', lambda v: v != 'SAFE', None)]),
          ('G1u','Gets', [('g1', lambda v: False, None), ('g4', lambda v: v != 'SAFE', 'UNSAFE')]),
          ('G2s','Gets', [('g2', TRUE, 'SAFE')]),
          ('G2u','Gets', []),                     # 2-arg unsafe: suppressed, no counterpart
          ('G3s','Gets', [('g3', TRUE, 'SAFE')]), # (String,Provider) captured (unlike MAC/KPG/SIG)
          ('G3u','Gets', []),
          ('U','Updates', [('update', TRUE, None)]),
          ('D1','Digests', [('d1', TRUE, None)]),
          ('D2','DWOU', [('d2', TRUE, None)]),
          ('D3','Digests', [('d3', TRUE, None)]),
        ]
    if ab == 'KPG':
        return [
          ('G1s','Gets', [('g1', TRUE, 'SAFE'), ('g3', lambda v: False, None)]),
          ('G1u','Gets', [('g1', lambda v: False, None), ('g3', TRUE, 'UNSAFE')]),
          ('G2s','Gets', [('g2', TRUE, 'SAFE')]),
          ('G2u','Gets', []),
          ('GP','Gets', []),                      # (String,Provider): no pointcut
          # initialize(int): init1 guard validate(keySize) / initError guard !validate;
          # both read the `algorithm` FIELD; with an invisible creation the field is
          # null and validate() throws NPE (measured in harness, KPG-T5/T8).
          ('I3good','Inits', [('init1', TRUE, None), ('initError', lambda v: False, None)]),
          ('I3bad','Inits', [('init1', lambda v: False, None), ('initError', TRUE, None)]),
          # initialize(int, SecureRandom): init2 guard validate; NO initError
          # counterpart (initError pointcut is initialize(int) only) -> suppressed.
          ('I4good','Inits', [('init2', TRUE, None)]),
          ('I4bad','Inits', []),
          ('IP','Inits', [('init3', TRUE, None)]),
          ('IPR','Inits', [('init4', TRUE, None)]),
          ('GEN','Generators', [('gen', TRUE, None)]),
          ('GEN2','Generators', [('gen', TRUE, None)]),   # genKeyPair, same advice
        ]
    if ab == 'SRD':
        return [
          ('C1','Ins', [('c1', TRUE, None)]),
          ('C2r','Ins', [('c2', TRUE, None)]),    # seed RANDOMIZED-marked
          ('C2u','Ins', [('c3', TRUE, None)]),    # unmarked -> violating branch c3
          ('G1s','Ins', [('g1', TRUE, None)]),
          ('G1u','Ins', [('g4', TRUE, None)]),
          ('G2s','Ins', [('g2', TRUE, None)]),    # 2-arg safe (String,String)/(String,Provider)/(String,SRParams)
          ('G2u','Ins', []),                      # 2-arg unsafe: g2 cond false, g4 args(alg) arity-1 -> invisible
          ('G3sp','UNTRACK', []),                 # 3-arg getInstance (API30): no rule event, no pointcut -> untracked object
          ('GIS','Ins', [('g3', TRUE, None)]),
          ('S1','Seeds', [('setSeed1', TRUE, None)]),
          ('S2r','Seeds', [('setSeed2', TRUE, None)]),
          ('S2u','Seeds', [('setSeed3', TRUE, None)]),
          ('GS','Ends', [('genSeed', TRUE, None)]),
          ('NB','Ends', [('next2', TRUE, None)]),
          # nextInt(int)/nextInt()/ints(): java.util.Random members; the raw rule's
          # ne is the protected SecureRandom.next(int) -> these are extra-alphabet.
          ('NI',None, [('next1', TRUE, None)]),
          ('NI0',None, [('next3', TRUE, None)]),
          ('INTS',None, [('ints', TRUE, None)]),
        ]
    if ab == 'SIG':
        return [
          ('G1s','Gets', [('g1', TRUE, 'SAFE'), ('g3', lambda v: False, None)]),
          ('G1u','Gets', [('g1', lambda v: False, None), ('g3', TRUE, 'UNSAFE')]),
          ('G2s','Gets', [('g2', TRUE, 'SAFE')]),
          ('G2u','Gets', []),
          ('GP','Gets', []),                      # (String,Provider): no pointcut
          ('IS1','InitSigns', [('i1', TRUE, None)]),   # no condition (gh101: reads in body)
          ('IS2','InitSigns', [('i2', TRUE, None)]),
          ('IV3','InitVerifies', [('i3', TRUE, None)]),
          ('IV4','InitVerifies', [('i4', TRUE, None)]),
          ('U','Updates', [('update', TRUE, None)]),
          # sign()/sign(byte[],int,int): pointcuts declare return type `byte`;
          # android-30 declares byte[] sign() and int sign(byte[],int,int)
          # (alfa_javap_android30_batchD.txt) -> ZERO-CAPTURE.
          ('SGN','Signs', []),
          ('SGN2','Signs', []),
          ('V1','Verifies', [('v1', TRUE, None)]),
          ('V2','Verifies', [('v2', TRUE, None)]),
        ]

def ref_step(ab, q, ev):
    if ev is None:
        return q          # member not modeled by the raw rule: no CrySL step
    if ev == 'UNTRACK' or q == 'U':
        return 'U'        # object created by an unmodeled member: rule silent forever
    if q == 'V':
        return 'V'
    return REF[ab]['delta'].get((q, ev), 'V')

def mop_run_call(ab, mstate, var, emission):
    eff = EFF[ab]
    fails = 0
    for (mev, guard, newvar) in emission:
        if not guard(var):
            continue
        if newvar is not None:
            var = newvar
        nxt = eff['delta'][mev][mstate]
        if nxt == eff['fail']:
            fails += 1
            mstate = eff['initial'] if RESETS[ab] else nxt   # KPG: sink, no reset
        else:
            mstate = nxt
    return mstate, var, fails

CREATION = {  # call classes only possible as the object's first observable call
  'MAC': {'G1s','G1u','G2s','G2u','GP'},
  'MDG': {'G1s','G1u','G2s','G2u','G3s','G3u'},
  'KPG': {'G1s','G1u','G2s','G2u','GP'},
  'SRD': {'C1','C2r','C2u','G1s','G1u','G2s','G2u','G3sp','GIS'},
  'SIG': {'G1s','G1u','G2s','G2u','GP'},
}

def explore(ab, max_len=7):
    calls = CALLS(ab)
    eff = EFF[ab]
    fps, fns, accdiv = [], [], []
    Q = deque([(REF[ab]['init'], eff['initial'], 'EMPTY', 0, ())])
    while Q:
        rq, ms, var, ph, w = Q.popleft()
        if len(w) >= max_len:
            continue
        for (cname, cev, emission) in calls:
            is_creation = cname in CREATION[ab]
            if ph == 0 and not is_creation:
                # invisible-creation route: object may enter observation at an
                # instance call ONLY when a zero-emission creation preceded it;
                # modeled by the explicit G2u/GP/G3sp classes, so skip here.
                continue
            if ph == 1 and is_creation:
                continue      # one creation call per object (reference identity)
            nrq = ref_step(ab, rq, cev)
            nms, nvar, fails = mop_run_call(ab, ms, var, emission)
            nw = w + (cname,)
            first_viol_now = (rq not in ('V','U') and nrq == 'V')
            if fails > 0 and nrq != 'V':
                fps.append((nw, fails, rq, nrq))
            if first_viol_now and fails == 0:
                fns.append((nw, rq))
            if nrq != 'V' and nrq in REF[ab]['acc']:
                if nms not in eff['match']:
                    accdiv.append((nw, nrq, nms))
            Q.append((nrq, nms, nvar, 1, nw))
    def dedupe(lst):
        out, s = [], set()
        for item in sorted(lst, key=lambda x: (len(x[0]), x[0])):
            sig = (item[0][-1], item[0][0] if item[0] else None)
            if sig in s:
                continue
            s.add(sig); out.append(item)
        return out
    return dedupe(fps), dedupe(fns), dedupe(accdiv)

def walk(ab, word):
    eff = EFF[ab]; calls = {c[0]: c for c in CALLS(ab)}
    rq, ms, var = REF[ab]['init'], eff['initial'], 'EMPTY'
    lines = [f"    ref={rq} mop={ms}"]
    for c in word:
        _, cev, emission = calls[c]
        nrq = ref_step(ab, rq, cev)
        nms, nvar, fails = mop_run_call(ab, ms, var, emission)
        emitted = [e for (e,g,_) in emission if g(var)]
        lines.append(f"    --{c} (CrySL {cev}; MOP emits {emitted or 'nothing'})--> "
                     f"ref={nrq} mop={nms}"
                     f"{' FAIL#'+str(fails)+('->reset' if RESETS[ab] else '->SINK') if fails else ''}")
        rq, ms, var = nrq, nms, nvar
    return '\n'.join(lines)

def formal_event_level(ab):
    """alpha(L_eff) vs L(CrySL) over the MOP event alphabet, guards/realizability
    ignored; words the effective machine ACCEPTS (match) whose CrySL image is
    outside the language. Reported separately (most need one object to pass two
    creation calls -> unrealizable by reference identity)."""
    eff = EFF[ab]
    amap = {}
    for (cname, cev, emission) in CALLS(ab):
        for (mev, _, _) in emission:
            amap.setdefault(mev, cev)
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
            if nms in eff['match'] and (nrq == 'V' or nrq not in REF[ab]['acc']):
                out.append((nw, 'accepted-by-effective, CrySL image outside L or non-final'))
                continue
            Q.append((nrq, nms, nw))
    return sorted(out, key=lambda x: len(x[0]))[:6]

if __name__ == '__main__':
    print("=== Effective automata parsed from RuntimeMonitor.java artifacts ===")
    for ab in SPECS:
        e = EFF[ab]
        print(f"{ab} ({SPECS[ab]}): states={e['n_states']} init=0 fail={e['fail']} "
              f"match={sorted(e['match'])} fail_resets={RESETS[ab]}")
        for ev in e['events']:
            print(f"    {ev}: {e['delta'][ev]}")
    for ab in SPECS:
        print(f"\n=== {ab} ({SPECS[ab]}) — call-class product verification ===")
        fps, fns, accdiv = explore(ab)
        print(f"L(CrySL) subset alpha(L(MOP)) [no spurious fail on conformant prefix]: "
              f"{'PASS' if not fps else 'FAIL'}")
        for wrd, fails, rq, nrq in fps[:12]:
            print(f"  FP witness ({fails} fail(s)): {' '.join(wrd)}")
            print(walk(ab, wrd))
        print(f"alpha(L(MOP)) subset L(CrySL) [no silent deviation]: "
              f"{'PASS' if not fns else 'FAIL'}")
        for wrd, rq in fns[:8]:
            print(f"  FN witness (silent CrySL violation): {' '.join(wrd)}")
            print(walk(ab, wrd))
        print(f"acceptance-set agreement at end of trace: "
              f"{'PASS' if not accdiv else 'DIVERGES'}")
        for wrd, nrq, nms in accdiv[:5]:
            print(f"  word {' '.join(wrd)}: CrySL accepts in {nrq}, monitor in "
                  f"non-match state {nms}")
        fe = formal_event_level(ab)
        print(f"formal event-level (realizability ignored): "
              f"{'no extra acceptance' if not fe else 'effective accepts words outside L(CrySL)'}")
        for wrd, why in fe[:4]:
            print(f"  {' '.join(wrd)}: {why}")
