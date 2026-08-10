#!/usr/bin/env python3
"""ALFA pilot audit -- algorithmic language-inclusion check, CipherSpec/GCMParameterSpecSpec.

Reference automaton: normalized from the CrySL ORDER of
  MetaCrySL/generated/api30/Cipher.cryptsl (ORDER: Gets, Inits+, w+ | (FINWOU | (updates+, DOFINALS))+)
under the OFFICIAL CrySL precedence (',' outermost, '|' binds tighter), i.e. reading (A):
  Gets , Inits+ , ( w+ | (FINWOU | (updates+ , DOFINALS))+ )
The alternative reading (B) under MetaCrySL's own Rascal grammar
(src/lang/crysl/ConcreteSyntax.rsc:59-70, priority sequence > or) is also built, to show it
is degenerate (normal encrypt usage not in its language).

MOP automaton: transcribed from the fsm section of jca_android/CipherSpec.mop (lines 288-326).
SOURCE IS THE .mop SYNTAX, not the generated monitor -- declared limitation of this round;
the effective monitor automaton is another agent's task.

Abstraction alpha (constraint-satisfying projection: isValid==true so only g1 fires;
all condition(...) guards assumed true so every event fires -- REQUIRES suppression is
analysed separately in the report):
  g1        -> G   (CrySL Gets = g1|g2; MOP pointcut getInstance(String, ..) covers both)
  init2/3/4 -> I   (CrySL Inits = i1..i8; arity partition 2/3/4)
  u1        -> U   (CrySL u1,u2)   u3 -> U (CrySL u3,u4)   u5 -> U (CrySL u5)
  wkb1      -> W   (CrySL w)
  f2        -> Fw  (CrySL f2,f4 in FINWOU)   f5 -> Fw (f5,f6)   f7 -> Fw (f7)
  f1        -> F1  (DOFINALS minus FINWOU)   f3 -> F3 (DOFINALS minus FINWOU)

Semantics compared:
  match language  : words accepted (CrySL: full word in L; MOP: monitor in accepting state 'end')
  prefix/violation: CrySL violation = trace is not a prefix of any word of L;
                    MOP violation   = event with no transition from current state (@fail).
Both directions of inclusion are decided by product BFS; the shortest separating trace is printed.
Deterministic; single run (pre_registro section 5).
"""

from collections import deque
from itertools import product

ALPHABET = ["G", "I", "U", "W", "Fw", "F1", "F3"]

# ---------- tiny regex -> NFA (Thompson) -> DFA ----------

class N:  # regex AST node
    def __init__(self, kind, *kids, sym=None):
        self.kind, self.kids, self.sym = kind, kids, sym

def SYM(s):    return N("sym", sym=s)
def SEQ(*ks):  return N("seq", *ks)
def ALT(*ks):  return N("alt", *ks)
def PLUS(k):   return N("plus", k)
def STAR(k):   return N("star", k)

def thompson(ast):
    trans, eps = [], []
    def new():
        trans.append({}); eps.append(set()); return len(trans) - 1
    def build(a):
        s, f = new(), new()
        if a.kind == "sym":
            trans[s].setdefault(a.sym, set()).add(f)
        elif a.kind == "seq":
            cur = s
            for k in a.kids:
                ks, kf = build(k)
                eps[cur].add(ks); cur = kf
            eps[cur].add(f)
        elif a.kind == "alt":
            for k in a.kids:
                ks, kf = build(k)
                eps[s].add(ks); eps[kf].add(f)
        elif a.kind in ("plus", "star"):
            ks, kf = build(a.kids[0])
            eps[s].add(ks); eps[kf].add(f)
            eps[kf].add(ks)
            if a.kind == "star":
                eps[s].add(f)
        return s, f
    s0, f0 = build(ast)
    return trans, eps, s0, {f0}

def eclose(states, eps):
    st, stack = set(states), list(states)
    while stack:
        for t in eps[stack.pop()]:
            if t not in st:
                st.add(t); stack.append(t)
    return frozenset(st)

def determinize(trans, eps, s0, finals, alphabet=None):
    alphabet = alphabet or ALPHABET
    start = eclose({s0}, eps)
    dfa, acc = {}, set()
    seen, todo = {start: 0}, deque([start])
    dtrans = {}
    while todo:
        S = todo.popleft(); i = seen[S]
        if S & finals: acc.add(i)
        for a in alphabet:
            T = set()
            for q in S: T |= trans[q].get(a, set())
            if not T: continue
            T = eclose(T, eps)
            if T not in seen:
                seen[T] = len(seen); todo.append(T)
            dtrans.setdefault(i, {})[a] = seen[T]
    return dtrans, 0, acc

# ---------- automata ----------

def crysl_cipher_A():
    """Reading (A): Gets, Inits+, ( w+ | (FINWOU | (updates+, DOFINALS))+ )."""
    DOF = ALT(SYM("Fw"), SYM("F1"), SYM("F3"))
    block = ALT(SYM("Fw"), SEQ(PLUS(SYM("U")), DOF))
    ast = SEQ(SYM("G"), PLUS(SYM("I")), ALT(PLUS(SYM("W")), PLUS(block)))
    return determinize(*thompson(ast))

def crysl_cipher_B():
    """Reading (B) under MetaCrySL Rascal precedence: (Gets, Inits+, w+) | (FINWOU|(updates+,DOFINALS))+."""
    DOF = ALT(SYM("Fw"), SYM("F1"), SYM("F3"))
    block = ALT(SYM("Fw"), SEQ(PLUS(SYM("U")), DOF))
    ast = ALT(SEQ(SYM("G"), PLUS(SYM("I")), PLUS(SYM("W"))), PLUS(block))
    return determinize(*thompson(ast))

def mop_cipher():
    """fsm of CipherSpec.mop lines 288-326, alpha-projected (g1->G etc.). Missing edge = @fail."""
    t = {
        "start": {"G": "s1"},              # g1 -> s1   (g3 branch excluded by valid-transformation projection)
        "s1":    {"I": "s2"},              # init2/3/4 -> s2
        "s2":    {"W": "end", "Fw": "end", "U": "s3"},
        "s3":    {"Fw": "end", "F1": "end", "F3": "end"},
        "end":   {"W": "end", "Fw": "end", "U": "s3"},
    }
    names = {n: i for i, n in enumerate(t)}
    dtrans = {names[s]: {a: names[d] for a, d in row.items()} for s, row in t.items()}
    return dtrans, names["start"], {names["end"]}

def crysl_gcm():
    return determinize(*thompson(SYM("Cons")), alphabet=["Cons"])

def mop_gcm():
    # ere: c1 | c2 with both declared events named c1 and no event named c2.
    # Hypothesis H-GCM (INCONCLUSIVE at syntax level): c2 never fires, both ctors fire c1;
    # alpha(c1) = Cons. Effective language {c1} ~ {Cons}.
    return {0: {"Cons": 1}}, 0, {1}

# ---------- comparison ----------

def viable(dtrans, acc):
    """States from which an accepting state is reachable (prefix-viability)."""
    rev = {}
    states = set(dtrans) | {d for row in dtrans.values() for d in row.values()} | set(acc)
    for s, row in dtrans.items():
        for a, d in row.items():
            rev.setdefault(d, set()).add(s)
    ok, todo = set(acc), deque(acc)
    while todo:
        for p in rev.get(todo.popleft(), ()):
            if p not in ok:
                ok.add(p); todo.append(p)
    return ok

def compare(name, A, B, alphabet=None):
    """Product BFS over total-ized automata A=(reference) B=(candidate).
    Reports shortest word where match-acceptance differs and where violation verdict differs."""
    alphabet = alphabet or ALPHABET
    (ta, sa, aa), (tb, sb, ab) = A, B
    va, vb = viable(ta, aa), viable(tb, ab)
    DEAD = -1
    def step(t, s, a):
        return t.get(s, {}).get(a, DEAD) if s != DEAD else DEAD
    seen = {(sa, sb)}
    q = deque([(sa, sb, [])])
    diffs = {"match_only_ref": None, "match_only_cand": None,
             "viol_only_cand": None, "viol_only_ref": None}
    while q and not all(diffs.values()):
        xa, xb, w = q.popleft()
        acc_a, acc_b = xa in aa, xb in ab
        via_a = xa != DEAD and xa in va
        via_b = xb != DEAD and xb in vb
        if acc_a and not acc_b and not diffs["match_only_ref"]:
            diffs["match_only_ref"] = list(w)
        if acc_b and not acc_a and not diffs["match_only_cand"]:
            diffs["match_only_cand"] = list(w)
        # violation semantics: candidate(MOP) fails (dead) while reference still prefix-viable -> FP
        if xb == DEAD and via_a and not diffs["viol_only_cand"]:
            diffs["viol_only_cand"] = list(w)
        # reference violated (dead or non-viable) while candidate alive (no @fail) -> FN
        if not via_a and xb != DEAD and w and not diffs["viol_only_ref"]:
            diffs["viol_only_ref"] = list(w)
        if xa == DEAD and xb == DEAD:
            continue
        for a in alphabet:
            na, nb = step(ta, xa, a), step(tb, xb, a)
            if (na, nb) not in seen and len(w) < 12:
                seen.add((na, nb))
                q.append((na, nb, w + [a]))
    print(f"== {name} ==")
    label = {
        "match_only_ref":  "L(CrySL) word REJECTED by MOP  (inclusion CrySL<=MOP fails; FP side)",
        "match_only_cand": "MOP-accepted word NOT in L(CrySL) (inclusion MOP<=CrySL fails; FN side)",
        "viol_only_cand":  "MOP @fail on CrySL-viable prefix   (FP verdict)",
        "viol_only_ref":   "CrySL violation, MOP takes no @fail (FN verdict)",
    }
    ok = True
    for k, v in diffs.items():
        if v is not None:
            ok = False
            print(f"  {label[k]}: {' '.join(v) if v else '<empty>'}")
    if ok:
        print("  no separating trace up to length 12 -- dual inclusion HOLDS on this model")
    print()
    return diffs

def walk(name, mop, trace):
    """State-by-state walk of a trace through the MOP fsm (named states)."""
    states = ["start", "s1", "s2", "s3", "end"]
    t, s, acc = mop
    inv = {v: k for k, v in {n: i for i, n in enumerate(states)}.items()}
    cur = s
    print(f"  walk [{name}]: {' '.join(trace)}")
    for ev in trace:
        nxt = t.get(cur, {}).get(ev)
        if nxt is None:
            print(f"    {inv[cur]} --{ev}--> @FAIL (no transition)")
            return
        print(f"    {inv[cur]} --{ev}--> {inv[nxt]}")
        cur = nxt
    print(f"    end of trace in state {inv[cur]}; accepting={cur in acc}")

if __name__ == "__main__":
    A = crysl_cipher_A()
    Bdeg = crysl_cipher_B()
    M = mop_cipher()

    print("MetaCrySL-precedence reading (B) sanity: is the normal usage G I Fw in L(B)?")
    t, s, acc = Bdeg
    cur, okB = s, True
    for ev in ["G", "I", "Fw"]:
        cur = t.get(cur, {}).get(ev, -1)
        if cur == -1: okB = False; break
    print(f"  G I Fw in L(reading B): {okB and cur in acc}  -> reading (B) is degenerate; (A) adopted\n")

    d = compare("CipherSpec.mop fsm  vs  Cipher.cryptsl ORDER (reading A)", A, M)
    print("state-by-state walks of the separating traces (MOP fsm):")
    for k in ("viol_only_cand", "match_only_cand", "match_only_ref", "viol_only_ref"):
        if d[k]:
            walk(k, M, d[k])
    # hand-chosen minimal realizable counterexamples, verified by walk:
    print("\nhand-verified counterexamples:")
    for tr in (["G", "I", "I"], ["G", "I", "U", "U"], ["G", "I", "W", "Fw"], ["G", "I", "Fw", "W"]):
        walk("candidate", M, tr)

    print()
    compare("GCMParameterSpecSpec.mop (hypothesis H-GCM)  vs  GCMParameterSpec.cryptsl ORDER",
            crysl_gcm(), mop_gcm(), alphabet=["Cons"])
