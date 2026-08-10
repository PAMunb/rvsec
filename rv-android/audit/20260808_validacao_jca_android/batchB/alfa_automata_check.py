#!/usr/bin/env python3
"""ALFA batch B — algorithmic dual-inclusion check, CrySL reference automaton vs
EFFECTIVE automaton parsed from the generated *RuntimeMonitor.java (D-piloto-3).

Method. For each spec we define a finite set of CONCRETE LETTERS. A letter is one
realizable Java call scenario and carries:
  - its CrySL projection (an event of the rule's alphabet, or None if the call is
    invisible to the oracle, e.g. flush());
  - its MOP projection (the monitor event actually dispatched, or None when the
    generated suppression prologue returns false before handleEvent — verified in
    the artifacts — or when no pointcut exists for the member);
  - oracle_tag: whether the RAW api30 oracle itself flags this single call
    (constraint / requires / forbidden), independent of ORDER;
  - mop_body_err(state): whether the event body emits an ErrorDescription when the
    event is dispatched (state-independent in all five specs);
The reference automaton encodes the rule's ORDER under reading A (D-piloto-1).
The effective automaton is the transition table parsed from the RuntimeMonitor.

Exact product reachability (no depth bound) over (ref_state, mop_state) flags any
reachable STEP where oracle emission != MOP emission:
  FP: MOP emits (body error or live @fail handler) while the oracle does not
      (ref transition stays live and the letter carries no oracle_tag);
  FN: the oracle emits (ref goes DEAD, or oracle_tag set) while MOP emits nothing.
Shortest witnesses via BFS; full state walk printed.
End-of-trace: reachable products where ref is live-but-not-accepting and MOP is
silent are reported as the incomplete-operation limitation (not a step mismatch).

Multi-instance models (dimension 5): CIS/COS use the verified static global
monitor (single shared table, `<Spec>__Map = new <Spec>Monitor()`); KPR uses the
verified empty-slice broadcast semantics of c1 (dispatch through KeyPairSpec__Map
Tuple2 + clone-from-empty on first bound event), reproduced from
KeyPairSpecRuntimeMonitor.java lines 324-354 (c1: FindOrCreateEntry on the empty
binding, then set-wide event) and 380-430 (gpu: defineTo clone from the empty
leaf). Reset semantics of @fail (__RESET -> state 0) applied per monitor.
"""
import re, sys, os
from collections import deque

ART = os.environ.get("BATCHB_ART",
  "/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/d2ed0fb6-e4be-4945-abb4-21d8af2acd28/scratchpad/batchB")

def parse_tables(path, expected_events):
    txt = open(path).read()
    tabs = {}
    for ev in expected_events:
        m = re.search(r"Prop_1_transition_%s\[\] = \{([0-9, ]+)\}" % ev, txt)
        assert m, (path, ev)
        tabs[ev] = [int(x) for x in m.group(1).split(",")]
    return tabs

# ---------- per-spec letter definitions ----------
# letter = (name, crysl_ev, mop_ev, oracle_tag, body_err)
# oracle_tag in {None,'constraint','requires','forbidden'}

SPECS = {}

# ===== CIS =====
cis_tabs = parse_tables(f"{ART}/gen_CipherInputStreamSpec/out/CipherInputStreamSpecRuntimeMonitor.java",
                        ["c1","r1","r2","cl1"])
SPECS["CIS"] = dict(
    tables=cis_tabs, fail_state=4, fail_handler=True, mop_acc={2}, mop_init=0,
    # reference: Constructs, Reads+, c   (Constructs := c1|c2, Reads := r1|r2|r3)
    ref_init=0, ref_acc={3},
    ref_delta={ (0,'c1O'):1, (0,'c2O'):1, (1,'rO'):2, (2,'rO'):2, (2,'cO'):3 },
    letters=[
      ("ctor2_marked",  'c2O','c1',None,False),
      ("ctor2_unmarked",'c2O','c1',None,True),   # body validate(GENERATED_CIPHER) fails -> addError; api30 rule has NO REQUIRES
      ("ctor1_subclass",'c1O',None ,None,False), # protected 1-arg ctor: rule models it, spec has no event
      ("read0_or_readB",'rO','r1',None,False),
      ("read3_lenOK",   'rO','r2',None,False),
      ("read3_lenLEoff",'rO','r2','constraint',False), # CONSTRAINTS len > off — no check anywhere in the spec
      ("close",         'cO','cl1',None,False),
    ],
    global_monitor=True,
)

# ===== COS =====
cos_tabs = parse_tables(f"{ART}/gen_CipherOutputStreamSpec/out/CipherOutputStreamSpecRuntimeMonitor.java",
                        ["c1","w1","w2","fl","cl"])
SPECS["COS"] = dict(
    tables=cos_tabs, fail_state=4, fail_handler=True, mop_acc={3}, mop_init=0,
    ref_init=0, ref_acc={3},
    ref_delta={ (0,'c1O'):1, (0,'c2O'):1, (1,'wO'):2, (2,'wO'):2, (2,'cO'):3 },
    letters=[
      ("ctor2_marked",  'c2O','c1',None,False),
      ("ctor2_unmarked",'c2O','c1',None,True),
      ("ctor1_subclass",'c1O',None ,None,False),
      ("write_int_or_bytes",'wO','w1',None,False),
      ("write3_lenOK",  'wO','w2',None,False),
      ("write3_lenLEoff",'wO','w2','constraint',False),
      ("flush",         None ,'fl',None,False),  # not in the rule's alphabet: oracle-invisible
      ("close",         'cO','cl',None,False),
    ],
    global_monitor=True,
)

# ===== KPR =====
kpr_tabs = parse_tables(f"{ART}/gen_KeyPairSpec/out/KeyPairSpecRuntimeMonitor.java",
                        ["c1","gpu","gpr"])
SPECS["KPR"] = dict(
    tables=kpr_tabs, fail_state=2, fail_handler=True, mop_acc={1}, mop_init=0,
    # reference: co?, (pu*, pr*)*  == co? (pu|pr)* ; every live state accepting
    ref_init=0, ref_acc={0,1},
    ref_delta={ (0,'co'):1, (0,'pu'):1, (0,'pr'):1, (1,'pu'):1, (1,'pr'):1 },
    letters=[
      ("ctor_bothPredsHeld",'co','c1',None,False),
      ("ctor_pubUnmarked",  'co','c1','requires',True),  # body reports; oracle RequiredPredicateError: matched step
      ("getPublic",         'pu','gpu',None,False),
      ("getPrivate",        'pr','gpr',None,False),
    ],
    broadcast_c1=True,
)

# ===== SKY =====
sky_tabs = parse_tables(f"{ART}/gen_SecretKeySpec/out/SecretKeySpecRuntimeMonitor.java",
                        ["e1","d"])
SPECS["SKY"] = dict(
    tables=sky_tabs, fail_state=2, fail_handler=False,  # NO @fail handler: state 2 emits nothing
    mop_acc={0,1}, mop_init=0,
    ref_init=0, ref_acc={0,1},
    ref_delta={ (0,'ge'):0, (0,'d'):1 },
    letters=[
      ("getEncoded_keyMarked",  'ge','e1',None,False),
      ("getEncoded_keyUnmarked",'ge',None,None,False), # suppression prologue: validate(GENERATED_KEY) false -> return false
      ("destroy",               'd','d',None,False),
    ],
    # constraint: after 'destroy', GENERATED_KEY is removed, so getEncoded_keyMarked
    # becomes unavailable; encoded via letter guard below
    sky_guard=True,
)

# ===== PBK =====
pbk_tabs = parse_tables(f"{ART}/gen_PBEKeySpecSpec/out/PBEKeySpecSpecRuntimeMonitor.java",
                        ["f1","f2","c1","err1","err2","err3","c2"])
SPECS["PBK"] = dict(
    tables=pbk_tabs, fail_state=3, fail_handler=True, mop_acc={2}, mop_init=0,
    # reference: c1, cP   with FORBIDDEN(1-arg)=>c1, FORBIDDEN(3-arg)=>c1
    ref_init=0, ref_acc={2},
    ref_delta={ (0,'c1O'):1, (1,'cPO'):2 },
    letters=[
      # 4-arg ctor scenarios; MOP advice fires c1,err1,err2,err3 in this order (aspect verified)
      ("ctor4_iterOK_saltR_pwdR", 'c1O',['c1'],None,False),          # all conditions true
      ("ctor4_iterOK_saltR_pwdUser",'c1O',['err2'],None,True),       # oracle: NO error (only randomized[salt] required)
      ("ctor4_iterLow_saltR_pwdR",'c1O',['err1'],'constraint',True),
      ("ctor4_iterOK_saltU_pwdR", 'c1O',['err3'],'requires',True),
      ("ctor1_forbidden",         'c1O',['f1'],'forbidden',True),
      ("ctor3_forbidden",         'c1O',['f2'],'forbidden',True),
      ("clearPassword",           'cPO',['c2'],None,False),
    ],
)

def mop_step(spec, state, mop_ev):
    """apply one MOP event to the table; returns (next_state, fail_fired)"""
    t = spec["tables"][mop_ev]
    nxt = t[state]
    fail = (nxt == spec["fail_state"]) and spec["fail_handler"]
    if fail:
        nxt = spec["mop_init"]   # __RESET in @fail
    return nxt, fail

def run_product(name, spec):
    print(f"\n================ {name} ================")
    DEAD = "DEAD"
    init = (spec["ref_init"], spec["mop_init"])
    # BFS over product; record predecessor for shortest witness
    seen = {init: None}
    q = deque([init])
    fp_wit = fn_wit = None
    while q:
        cur = q.popleft()
        ref, mop = cur
        for L in spec["letters"]:
            lname, cev, mev, otag, berr = L
            if spec.get("sky_guard") and lname == "getEncoded_keyMarked" and ref == 1:
                continue  # after destroy the mark is removed; gate can no longer be true
            # oracle side
            if cev is None:
                nref, oerr = ref, False
            elif ref == DEAD:
                nref, oerr = DEAD, False   # oracle already reported; stop comparing further steps
            else:
                nref = spec["ref_delta"].get((ref, cev), DEAD)
                oerr = (nref == DEAD)
            if otag: oerr = True
            # mop side
            memits = berr
            nmop = mop
            evs = mev if isinstance(mev, list) else ([mev] if mev else [])
            for e in evs:
                nmop, f = mop_step(spec, nmop, e)
                memits = memits or f
            step = (cur, lname)
            if memits and not oerr and fp_wit is None:
                fp_wit = (step, "FP: MOP emits, oracle silent")
            if oerr and not memits and fn_wit is None:
                fn_wit = (step, "FN: oracle flags, MOP silent")
            nxt = (nref, nmop)
            if nxt not in seen:
                seen[nxt] = (cur, lname)
                q.append(nxt)
    for wit, kind in [(fp_wit, "FP"), (fn_wit, "FN")]:
        if wit:
            (state, lname), desc = wit
            path = []
            cur = state
            while seen[cur] is not None:
                prev, ln = seen[cur]
                path.append(ln); cur = prev
            path.reverse(); path.append(lname)
            print(f"  {desc}")
            print(f"    shortest witness: {path}")
            walk(spec, path)
        else:
            print(f"  no {kind} step mismatch reachable (single-instance product)")
    # end-of-trace limitation: live non-accepting ref with silent mop
    eot = sorted(set((r) for (r,m) in seen if r not in (DEAD,) and r not in spec["ref_acc"]))
    if eot:
        print(f"  end-of-trace: ref states {eot} reachable and non-accepting; a trace ending there is a CrySL incomplete operation the monitor never reports (no end-of-trace channel).")
    return fp_wit, fn_wit

def walk(spec, path):
    ref, mop = spec["ref_init"], spec["mop_init"]
    for lname in path:
        L = next(l for l in spec["letters"] if l[0]==lname)
        _, cev, mev, otag, berr = L
        nref = ref if cev is None or ref=="DEAD" else spec["ref_delta"].get((ref,cev),"DEAD")
        oerr = (nref=="DEAD" and cev is not None and ref!="DEAD") or bool(otag)
        evs = mev if isinstance(mev, list) else ([mev] if mev else [])
        memits = berr; nmop = mop
        for e in evs:
            nmop, f = mop_step(spec, nmop, e); memits = memits or f
        print(f"      {lname}: ref {ref}->{nref} (oracle_err={oerr}) | mop {mop}->{nmop} (mop_emits={memits})")
        ref, mop = nref, nmop

def two_instance_global(name, spec, seq):
    """CIS/COS: one static monitor shared by all instances (artifact-verified).
    seq = list of (instance, letter_name); each instance's CrySL projection must be legal."""
    print(f"\n  [{name}] two-instance drive over the GLOBAL monitor: {seq}")
    refs = {}
    mop = spec["mop_init"]; spurious = []
    for inst, lname in seq:
        L = next(l for l in spec["letters"] if l[0]==lname)
        _, cev, mev, otag, berr = L
        r = refs.get(inst, spec["ref_init"])
        if cev is not None:
            nr = spec["ref_delta"].get((r,cev), "DEAD")
            assert nr != "DEAD", f"per-instance projection must stay legal: {inst},{lname}"
            refs[inst] = nr
        assert not otag and not berr
        if mev:
            nmop, f = mop_step(spec, mop, mev)
            print(f"      inst{inst} {lname}: mop {mop}->{nmop}{' FAIL->handler+RESET' if f else ''}")
            if f: spurious.append((inst,lname))
            mop = nmop
    ok = all(r in spec["ref_acc"] for r in refs.values())
    print(f"      per-instance CrySL projections all accepted: {ok}; spurious monitor emissions: {len(spurious)} {spurious}")
    return spurious

def kpr_broadcast(seq):
    """Faithful model of the verified dispatch: c1 hits the empty-binding monitor and
    every monitor in the set; gpu/gpr on an unseen object clone from the empty leaf."""
    spec = SPECS["KPR"]
    print(f"\n  [KPR] broadcast drive (artifact semantics): {seq}")
    empty = None            # empty-binding monitor state or None
    mons = {}               # obj -> state
    refs = {}
    emissions = []
    def apply(mstate, ev, who):
        nxt, f = mop_step(spec, mstate, ev)
        if f: emissions.append((who, ev))
        return nxt
    for inst, lname in seq:
        L = next(l for l in spec["letters"] if l[0]==lname)
        _, cev, mev, otag, berr = L
        r = refs.get(inst, spec["ref_init"])
        nr = spec["ref_delta"].get((r,cev), "DEAD")
        assert nr != "DEAD" and not otag and not berr
        refs[inst] = nr
        if mev == 'c1':
            if empty is None: empty = spec["mop_init"]
            empty = apply(empty, 'c1', 'empty-binding')
            for o in list(mons): mons[o] = apply(mons[o], 'c1', f'monitor[{o}]')
        else:
            if inst not in mons:
                mons[inst] = empty if empty is not None else spec["mop_init"]  # clone (defineTo:6) or fresh
            mons[inst] = apply(mons[inst], mev, f'monitor[{inst}]')
    print(f"      per-instance CrySL projections: all legal (asserted); spurious @fail emissions: {len(emissions)} {emissions}")
    return emissions

NAMED = [
    # distinct phenomena shadowed by the shortest witness of the same class
    ("COS", "flush alone satisfies (w1|w2|fl)+ -> FN at close (oracle: Writes+ unmet)",
        ["ctor2_marked","flush","close"]),
    ("COS", "flush after close -> spurious @fail (oracle-invisible call changes state)",
        ["ctor2_marked","write_int_or_bytes","close","flush"]),
    ("CIS", "constraint len>off dropped: violating read flagged by oracle, silent in MOP",
        ["ctor2_marked","read3_lenLEoff"]),
    ("COS", "constraint len>off dropped (same class)",
        ["ctor2_marked","write3_lenLEoff"]),
    ("PBK", "residue: violating carrier loops at 0, later LEGAL clearPassword -> spurious @fail",
        ["ctor4_iterLow_saltR_pwdR","clearPassword"]),
    ("PBK", "FORBIDDEN => c1 mapping not honored: f1 loops at 0, legal cP -> spurious @fail",
        ["ctor1_forbidden","clearPassword"]),
    ("SKY", "double destroy: oracle rejects (d?), monitor reaches dead state 2 with NO handler",
        ["destroy","destroy"]),
    ("KPR", "generator-obtained pair: getPublic first (co? optional in rule) -> spurious @fail",
        ["getPublic"]),
]

if __name__ == "__main__":
    results = {}
    for name in ["CIS","COS","KPR","SKY","PBK"]:
        results[name] = run_product(name, SPECS[name])
    print("\n======== named witnesses (distinct phenomena, full walks) ========")
    for spec_name, desc, path in NAMED:
        print(f"\n  [{spec_name}] {desc}")
        walk(SPECS[spec_name], path)
    print("\n======== multi-instance / lifecycle models (dimension 5) ========")
    s1 = two_instance_global("CIS", SPECS["CIS"],
        [(1,"ctor2_marked"),(1,"read0_or_readB"),(1,"close"),
         (2,"ctor2_marked"),(2,"read0_or_readB"),(2,"close")])
    s2 = two_instance_global("COS", SPECS["COS"],
        [(1,"ctor2_marked"),(1,"write_int_or_bytes"),(1,"close"),
         (2,"ctor2_marked"),(2,"write_int_or_bytes"),(2,"close")])
    s3 = kpr_broadcast([(1,"ctor_bothPredsHeld"),(2,"ctor_bothPredsHeld")])
    s4 = kpr_broadcast([(1,"ctor_bothPredsHeld"),(1,"getPublic"),(2,"ctor_bothPredsHeld"),(1,"getPublic")])
    print("\nSummary: two sequential legal CIS streams ->", len(s1), "spurious emissions;",
          "COS:", len(s2), "; KPR two ctors:", len(s3), "; KPR interleaved:", len(s4))
