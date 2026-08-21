# The G-ORDER gate reads the CrySL `ORDER` with inverted precedence (gh105, found before task 4.8)

The gate parses `,` and `|` the way a regular expression does — concatenation
binding tighter than alternation. The CrySL grammar binds them the other way
round. One rule in the api30 oracle is written in a way that tells the two apart,
and it is `Cipher`, so the `CipherSpec` row of G-ORDER has been reporting the
wrong witness, in the wrong direction, against the wrong side.

**Disposition: recorded here, repaired at task 7.1.** Nothing in Groups 4 to 6
edits the gate, and no `.mop` edit is warranted by this — the repair is to the
parser, to the test that pins it, and to the two records that quote the artifact
witness. Task 4.8 does not depend on it: `GCMParameterSpec` has no `,` in its
`ORDER`.

## Verified at three sites

### The grammar says `|` binds tighter

`/home/pedro/tmp/CryptSL/de.darmstadt.tu.crossing.CrySL/src/de/darmstadt/tu/crossing/CrySL.xtext`:

```
103  Order:      Sequence
107  Sequence returns Order:     Alternative ({Order.left=current} op=SequenceOperator right=Alternative)*
112      SEQUENCE = ','
115  Alternative returns Order:  Cardinality ({Order.left=current} op=AlternativeOperator right=Cardinality)*
120      ALTERNATIVE = '|'
```

`Sequence` is the outermost production, so it is the *weakest* operator: `a, b | c`
is `a , (b | c)`. This is the opposite of the regular-expression convention, and it
is the whole of the defect.

### The gate says `,` binds tighter

`scripts/gh105_order_gate.py`: `tokenize` (:136) drops the comma outright —
`if token != ","` (:152) — and `parse_expression` (:160) states its own grammar in
the docstring at :162, `alt := cat ('|' cat)*`, which makes alternation the
outermost production. With the comma gone, `a, b | c` becomes the juxtaposition
`a b | c` and parses as `(a b) | c`.

The parser is *correct for the `ere`* and wrong only for the `ORDER`. An `ere` has
no commas, and juxtaposition-tighter-than-`|` is right there. The defect is
one-sided: it entered by reusing one parser for two notations whose operators
happen to be written differently and ordered differently.

### The suite pins the defect, and names the hazard it is causing

`tests/parity/test_gh105_predicate_gates.py:1344`,
`test_the_order_grammar_is_read_with_alternation_weakest`, asserts that `a, b | c`
parses as `("alt", (("cat", (a, b)), c))`. Its docstring reasons about the Cipher
rule and warns that reading it with the wrong precedence would make "the gate
report a divergence that is an artifact of its own parser". That is exactly what
the gate is doing; the docstring has the sign inverted.

## Blast radius: one rule

Of the 33 rules in `MetaCrySL/generated/api30`, five write both operators:

| rule | `ORDER` | same paren level? |
|---|---|---|
| `Cipher` | `Gets, Inits+, w+ \| (FINWOU \| (updates+, DOFINALS))+` | **yes** |
| `KeyStore` | `Gets, Loads, ((gE?, gk) \| (sE, Stores))*` | no |
| `Mac` | `Gets, Inits, (Finals \| (Updates+, Finals))` | no |
| `MessageDigest` | `Gets, (DWOU \| (Updates+, Digests))+` | no |
| `Signature` | `Gets, ((InitSigns+, (Updates+, Signs+)+)+ \| (InitVerifies+, (Updates*, Verifies+)+)+)` | no |

The other four parenthesise every alternation, so both parsers build the same tree
for them. Only `Cipher` leaves a top-level `|` next to top-level commas, and only
`Cipher`'s language changes.

`order_alphabet_map.csv` carries no comma in any of its 120 `order_symbol` cells,
so the mapping side is untouched.

## What the two parses disagree about

`Cipher`'s `ORDER` over the expanded alphabet (23 symbols):

* CrySL: `Gets , Inits+ , ( w+ | (FINWOU | (updates+, DOFINALS))+ )` — a
  `getInstance` and at least one `init` are **mandatory**, and then either wrapping
  or finalising.
* gate: `( Gets Inits+ w+ ) | ( (FINWOU | (updates+ DOFINALS))+ )` — the right-hand
  branch stands alone, so a program may finalise having never called `getInstance`
  or `init`.

| call sequence | CrySL | gate |
|---|---|---|
| `g1 i2 f2` — getInstance, init, doFinal | **accepts** | **rejects** |
| `g1 i2 w` — getInstance, init, wrap | accepts | accepts |
| `f2` — a bare doFinal | **rejects** | **accepts** |
| `u1 f2` — update, doFinal, nothing before | rejects | accepts |

Over all words of length ≤ 3 the two languages disagree on **795**: 715 the gate
accepts and CrySL does not, 80 the reverse. The gate rejecting the canonical
`getInstance → init → doFinal` is the measure of how far off it is.

## The delta, measured on the gate itself

Substituting a grammar-faithful parser and running G-ORDER over `jca_android`:

| | current parser | faithful parser |
|---|---|---|
| passed / findings / skipped | 6 / 4 / 13 | 6 / 4 / 13 |
| `CipherSpec` | `` `f2` `` accepted by **the api30 ORDER**, rejected by the specification | `` `g1 i1 u1` `` accepted by **the specification**, rejected by the api30 ORDER |
| `SSLContextSpec` | `g1 Init se1 se1`, by the specification | unchanged |
| `SecureRandomSpec` | `c1 c1`, by the specification | unchanged |
| `TrustManagerFactorySpec` | `g1 i1 gtm`, by the api30 ORDER | unchanged |

Exactly one finding moves, and it inverts. The counts do not move, so no
specification crosses between `passed` and `findings`: the repair changes what the
`CipherSpec` row *says*, not how many rows there are.

**The real divergence, for whoever repairs it.** The `CipherSpec` `ere` accepts
`getInstance → init → update` terminating with no `doFinal`; the api30 `ORDER` does
not, because `updates+` is only accepting when `DOFINALS` follows. That is a
specification that lets an unfinalised Cipher pass. The witness on record today
says the reverse — that the rule permits a bare `doFinal` and the specification is
too strict — and a repair driven by it would have loosened the `ere` in the wrong
direction.

## What does not change

* `data/jca_android/gate_baseline.json` keys its G-ORDER entries by
  `(set, file, "order")` and stores no witness, so the repair needs no `--write`.
  All four rows stay, `order_failed` stays 4.
* The `counts` block, the other three witnesses, and every G-PRED2 / INV-INS-130 /
  INV-INS-133 / INV-INS-134 finding.
* Every `.mop`. No specification is wrong because of this.

## The mis-attribution, which is the part worth remembering

This was seen once and explained away. `docs/handoff/20260820_gh105_apply_prompt_v2.md:124`
records the witness with its mechanism attached:

> `CipherSpec`: `f2` aceito pelo ORDER, rejeitado pela especificação (precedência
> do `|` no ORDER da regra deixa `doFinal` sozinho legal).

The precedence was named correctly and attributed to **the rule** — read as a
quirk of how CrySL writes `Cipher` — when it is a property of **the reader**. A
gate's own parse is the one thing a gate cannot use itself to check, so an
oddity in a witness is evidence about the gate before it is evidence about the
oracle. **When a gate reports something surprising about its input, verify the
gate's parse against the input's grammar before recording the surprise as a fact
about the input.**

`data/gh105/evidence/f2-CipherSpec.md:96` cites the divergence in passing, while
disposing of the `unsafeAlg` sink: "G-ORDER already reports `CipherSpec` as
divergent (on a different witness, `f2` alone)". The disposition does not rest on
it — the point being made is only that the sink is a separate matter — and it
survives the repair, since `g1 i1 u1` is a different witness from the sink too.
The parenthetical becomes stale and is listed below.

## Task 7.1 checklist

1. Give `parse_expression` the comma: `seq := alt (',' alt)*`, `alt := juxta ('|' juxta)*`,
   `juxta := card+`, `card := primary [*+?]*`. `tokenize` stops dropping `,`. The
   `ere` path is unaffected — it never emits a `,` token — so one parser still
   reads both notations, which was the right instinct with the wrong grammar.
2. Invert `test_the_order_grammar_is_read_with_alternation_weakest`
   (`tests/parity/test_gh105_predicate_gates.py:1344`): rename it to say sequence
   is weakest, assert `("cat", (a, ("alt", (b, c))))`, and keep the Cipher
   reasoning in the docstring with the sign fixed. Add the `g1 i2 f2` case — the
   canonical use the old parse rejected is the regression this test exists to
   catch.
3. Update the two records that quote the artifact witness:
   `data/jca_android/evidence/gate_baseline_report.md:68` and the stale
   parenthetical at `data/gh105/evidence/f2-CipherSpec.md:96`.
4. Re-run G-ORDER and confirm 6 / 4 / 13 with the new `CipherSpec` witness. No
   baseline `--write` is required; if one is run anyway it must preserve `retired`.
5. Hand the real divergence — the `ere` accepting an unfinalised Cipher — to
   whichever Group 6 task takes the `CipherSpec` automaton, or record it as
   deliberately unrepaired the way the `unsafeAlg` sink was.

## Reproduction

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
python3 - <<'PY'
import sys, re
from pathlib import Path
sys.path.insert(0, 'scripts')
import gh105_order_gate as g

def parse_crysl(text):
    """Faithful to CrySL.xtext:103-120 -- Sequence(`,`) outermost, Alternative(`|`)
    tighter. Juxtaposition (the `ere`) is concatenation inside Alternative, where
    an `ere` never carries a `,`."""
    ts = [m.group(0) for m in re.finditer(r"[A-Za-z_$][\w$]*|[()|*+?,]", text)]
    pos = 0
    def peek(): return ts[pos] if pos < len(ts) else None
    def seq():
        nonlocal pos
        items = [alt()]
        while peek() == ',':
            pos += 1; items.append(alt())
        return items[0] if len(items) == 1 else ("cat", tuple(items))
    def alt():
        nonlocal pos
        branches = [juxta()]
        while peek() == '|':
            pos += 1; branches.append(juxta())
        return branches[0] if len(branches) == 1 else ("alt", tuple(branches))
    def juxta():
        items = []
        while peek() is not None and peek() not in ('|', ')', ','):
            items.append(card())
        if not items: return ("eps",)
        return items[0] if len(items) == 1 else ("cat", tuple(items))
    def card():
        nonlocal pos
        node = prim()
        while peek() in ('*', '+', '?'):
            node = ({'*': 'star', '+': 'plus', '?': 'opt'}[ts[pos]], node); pos += 1
        return node
    def prim():
        nonlocal pos
        t = peek()
        if t is None: raise g.ParseError("the expression ends where a symbol was expected")
        if t == '(':
            pos += 1; node = seq()
            if peek() != ')': raise g.ParseError("an unclosed `(`")
            pos += 1; return node
        if t in ('|', '*', '+', '?', ')', ','): raise g.ParseError(f"`{t}` where a symbol was expected")
        pos += 1
        return ("eps",) if t in g._ERE_EMPTY else ("sym", t)
    node = seq()
    if pos != len(ts): raise g.ParseError(f"`{ts[pos]}` left over")
    return node

SPECS = Path('/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv'
             '/rvsec/rvsec/rvsec-mop/src/main/resources')
for label, parser in (("current", g.parse_expression), ("faithful", parse_crysl)):
    g.parse_expression = parser
    r = g.run(SPECS, "jca_android")
    print(f"== {label}: passed={len(r.passed)} findings={len(r.findings)} skipped={len(r.skipped)}")
    for f in r.findings:
        print(f"   [{f.spec_set}/{f.spec}] {f.message}")
PY
```
