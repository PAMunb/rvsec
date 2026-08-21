# SecretKeySpecSpec — the pass that closes the last open window (gh105 task 4.10)

One read, one write, one bookkeeping call. Nothing moves placement: the read was already in its
body (task 3.4 put it there when it fused the twins) and the write was already at the acceptance
point. What moves is the **store** under both, and that is the whole of the pass — the placement
census cannot see it and INV-INS-130 can.

It closes **two** windows, not one. A window here is the F2 hazard the migration creates by
construction: a producer moves store before its consumer, and until the consumer follows, a
chain that used to close silently is broken. This file's read is the last consumer whose producer
had already moved; and its write, once on the new store, closes a second window at a consumer
that moved four tasks ago and has been answering *not observed* to every key since.

The second window is why this pass has a decision at all: closing it correctly required the write
to stay **below the rule's arity**, and the measurement says so plainly.

## What the rule says, and where each site landed

api30 `SecretKeySpec.cryptsl`:

```
EVENTS       c1: SecretKeySpec(keyMaterial, alg);            :17
             c2: SecretKeySpec(keyMaterial, off, len, alg);  :19
             Cons := c1 | c2;                                :21
ORDER        Cons                                            :25
CONSTRAINTS  length(keyMaterial) >= off + len;               :29
REQUIRES     preparedKeyMaterial[keyMaterial];               :34
ENSURES      speccedKey[this, _];                            :39
             generatedKey[this, alg];                        :41
```

| site | before | after | placed by |
|---|---|---|---|
| `c1` read of the key material | `read:body`, boolean, one code | `read:body`, three-valued, two codes, on the new store | this task |
| `c2` CONSTRAINTS check | body, unreachable, kept | unchanged | task 3.4 |
| `@match` write of the key origin | `write:acceptance`, old store, arity 1 | `write:acceptance`, **new store, still arity 1**, reason recorded | this task |
| `@match` accepting-state bookkeeping | present | **deleted** (INV-INS-147) | this task |
| `speccedKey[this, _]` | no site | **still no site**, recorded | ledger #31 → 5.10 |

The read keeps asking about `randomized` where the rule requires `preparedKeyMaterial`. That
conflation is the seed's, it is ledger clause **#32**, and it is undone at task 5.10 together with
6.1 — recorded here, not repaired. This pass changed the store and the verdict shape, not which
predicate the read names.

## The two windows, measured before the edit

The corpus could measure the first and **not** the second: every Cipher trace binds its key
silently (`bind k = new SecretKeySpec(...)`), so `SecretKeySpecSpec`'s construction event never
fires in them and no committed trace observed both ends of the chain. So the chain was measured by
probe first, and a trace was written for it (finding 18).

Probe over the whole `ErrorCollector`, both ends observed, before the edit:

| configuration | before |
|---|---|
| randomised material → `new SecretKeySpec(km, "AES")` | **1 — `SECRETKEYSPEC-CONSTR-00`** |
| `Cipher.init(1, that key)` | 1 — `CIPHER-NOBS-00` |
| `Cipher.init(1, a key of no observed origin)` | 1 — `CIPHER-NOBS-00`, **indistinguishable from the row above** |

Row 1 is window one: `randomized` is produced by `SecureRandom`, which moved store at task 4.5,
and this consumer was still reading the old one — so key material an observed `SecureRandom` had
just filled was accused of not having been observed to come from a randomized source. Row 2 is
window two, and rows 2 and 3 being the same report is the sharp statement of it: the read that
task 4.1 migrated has not been able to tell an observed key origin from an unobserved one since,
because no producer had reached its store.

## The two decisions, and what measured each one

### 1. The write moves store and does **not** move arity

api30 states `ENSURES generatedKey[this, alg]` — **two places**, the key and its algorithm — and
INV-INS-134 requires a write at the rule's arity. The write went to the new store at **arity 1**.

What decided it is a property of the store, measured directly rather than argued:

```
write arity 1, read arity 1 -> SATISFIED
write arity 1, read arity 2 -> VIOLATED
write arity 2, read arity 1 -> VIOLATED        <- the case that matters
write arity 2, read arity 2 -> SATISFIED
write arity 2 with null, read arity 1 -> VIOLATED
never written, read arity 1 -> NOT_OBSERVED
```

`validate` compares the value tuple, so an arity mismatch is **VIOLATED, not NOT_OBSERVED**. The
one migrated reader of this predicate is `CipherSpec.i2`, which reads at arity 1 until task 5.6.
Raising the arity here alone would therefore have turned every `SecretKeySpec`-created key given
to `Cipher.init` into `CIPHER-CONSTR-00` — *"the key given to Cipher.init carries a key-origin
predicate the rule does not admit"* — a **positive accusation about a conforming program**, and
strictly worse than the `NOT_OBSERVED` it replaces. The window would have opened in its accusing
form, in the pass whose job is to close the last one.

Chosen (researcher, 2026-08-21): **arity 1 now, with the reason recorded** in
`predicate_graph.csv` and in the file, rising at task 5.6 in the same commit as its consumer.
Precedent: decision 7 of task 4.4 — a behavioural change with no measurement to decide it does not
travel inside a substrate migration.

Two things follow, and both are recorded rather than left to be re-derived. INV-INS-134's escape
hatch covered *placement* only ("a write kept elsewhere"); it now covers arity too, with the
reason above, and with the bound that a write MUST NOT stay below the rule's arity past the task
that migrates its last consumer. And `tasks.md` 5.6 lists four producers whose arity rises there
and did not list this one — the same staleness the 4.9 pass found in 6.4's site list, and fixed
the same way (finding 25: the record goes in two artefacts, not one).

The third option was to raise both ends here, closing ledger #5 in a Group-4 pass — four Group-4
passes have already closed an edge routed to Group 5. Measured in its favour: `SecretKeySpec`'s
`alg` and Cipher's `part(0,"/",transformation)` agree on `"AES"` for the corpus traces. Declined
because it touches `CipherSpec`, which is at 17/17 events with zero headroom (INV-INS-145), and
takes the splitter decision the ledger routes to 5.6.

### 2. `speccedKey[this, _]` is not written

The rule's other `ENSURES` has **no site in the file**, before this pass or after it. It is not
created here. Its consumer is `SecretKeyFactory`, which has no specification in the set; ledger
#31 already disposes the chain as `unmonitored-consumer` at task 5.10; and `PBEKeySpecSpec`
already produces the predicate. A second producer for a chain with no consumer at all is a site
with no purpose, and this change's rule is that no read is fabricated to give a write one.

Chosen (researcher, 2026-08-21): **leave it, record it**. The alternative had a precedent —
`preparedPBE` at task 4.7 kept its write and carried a deliberate-omission record for the absent
reader (INV-INS-137) — but that write already existed; this one would have to be invented. The
ledger row was corrected while checking: it credited only `PBEKeySpec` as a producer of
`speccedKey`, and `SecretKeySpec.cryptsl:39` makes two.

### And one that was not a decision: which branch keeps the code number

The boolean read becomes three-valued, so one code becomes two. The set's convention is already
fixed by the three files migrated before this one: `-CONSTR-NN` for the VIOLATED branch,
`-NOBS-NN` for NOT_OBSERVED, in body order. So `SECRETKEYSPEC-CONSTR-00` stays where it is and
names the VIOLATED branch, and the accusation a program can actually reach moves to the new
`SECRETKEYSPEC-NOBS-00`. Task 4.7 re-pointed an existing number the same way when it decomposed
`PBEPARAMETERSPEC-CONSTR-00` from a composite into the iteration-count clause.

The one thing that could have made this a decision was measured and does not apply: the published
corpus predates the v=1 envelope, and this specification's **820 rows in it are mute** — they
carry no code at all — so no external reading of `SECRETKEYSPEC-CONSTR-00` changes meaning.

The VIOLATED branch it now names has **no execution path**: nothing in api30 withdraws
`randomized`, and at arity 1 with no value positions that verdict can only come from `negate`. It
is written anyway, for the reason finding 29 records — a code may be written knowing nothing
executes it, as long as the reason is on the record. That makes three codes without a path in this
one file: this branch, `SECRETKEYSPEC-CONSTR-01`, and `SECRETKEYSPEC-ORDER-00`.

## The `@fail` that cannot fire

Measured in the generated monitor, not inferred: `Prop_1_transition_c1 = {1, 2, 2}` and
`Prop_1_transition_c2 = {1, 2, 2}`, and the monitor is keyed on the constructed `SecretKeySpec`.
A monitor of this specification therefore receives **at most one event**, state 2 is never
entered, and `SECRETKEYSPEC-ORDER-00` has no execution path.

This is finding 29's criterion applied to a second file, and it confirms what task 4.8 predicted
when it generalised from `GCMParameterSpecSpec`: **every constructor-only specification of this
set is in the same position**. Unlike `GCMParameterSpecSpec`, this file is not mute — its `c1`
body speaks, because task 3.4 took the read out of the guard — so the unreachable handler costs a
code rather than the whole specification. Recorded, not repaired: the repair is to the automaton,
this pass moves no symbol, and the file is one of the thirteen still absent from
`order_alphabet_map.csv`, so G-ORDER skips it in both directions (task 7.1).

## What the harness measured

92 traces (the 91 committed plus the chain trace this pass wrote), `--a
backup/gh105-preimage/jca_android`, cumulative against the pre-image:

| | before this task | after |
|---|---|---|
| unchanged | 59 | **61** |
| moved | 18 | 18 |
| introduced | 8 | **7** |
| removed | 6 | 6 |

| trace | A accuses | B accuses | class |
|---|---|---|---|
| `SecretKeySpecSpec.txt` | — | — | **unchanged** (was `introduced`) |
| `SecretKeySpecSpec-badalg.txt` | `c3` `SECRETKEYSPEC-CONSTR-00` | `c1` `SECRETKEYSPEC-NOBS-00` | moved |
| `SecretKeySpecSpec-offset.txt` | — | — | unchanged |
| `SecretKeySpecSpec-cipher-chain.txt` | — | — | unchanged |

`SecretKeySpecSpec.txt` leaving `introduced` **is** the window closing, and it is the last one: the
`introduced` count reaches 7, all of which are repairs the earlier passes made deliberately (four
from task 4.8's end of a mute specification, two from 4.7's three-argument `c2`, one from 4.9).

`-badalg` shows the renumbering doing its job: the same program, the same words, a code that now
says which of the three values the read returned.

## The window the harness cannot see, and the correction it forces

The chain trace came out **unchanged**, and the prediction written into it said `removed`. The
prediction was wrong, and the reason is worth more than the prediction was.

Measured on three trees, same probe, whole `ErrorCollector`:

| configuration | pre-image | the tree this pass started from | after |
|---|---|---|---|
| randomised material → `new SecretKeySpec(km, "AES")` | 0 | **1 — `SECRETKEYSPEC-CONSTR-00`** | **0** |
| `Cipher.init(1, that key)` | 0 | **1 — `CIPHER-NOBS-00`** | **0** |
| `Cipher.init(1, a key of no observed origin)` | **0** | 1 — `CIPHER-NOBS-00` | 1 — `CIPHER-NOBS-00` |

Both windows are real, and neither is visible in the harness's two sides. The pre-image is
internally consistent — every end of both chains on the old store — and so is the migrated tree.
A window exists only in the trees the migration *walks through*, and this trace's A side is the
pre-image, not the tree the pass started from.

Finding 18 says: when the corpus has no trace of the site, write the trace and measure the seed.
This pass wrote the trace before the harness ran but **after** the edit, which is one step too
late — the trace's A side became the pre-image and the state it was written to demonstrate had
already gone. The correction, for the passes that remain: **"write the trace first" means before
the edit, not before the harness run.** The measurement survived here only because the probe had
already been run against the starting tree, for the arity decision.

Row 3 of the pre-image column is worth reading twice. A key that came from nowhere at all drew
**nothing** before this change: `CipherSpec.i2`'s read sat in `condition(...)`, so an unknown key
origin suppressed the `init` transition instead of accusing it. Task 4.1 made that read speak, and
what this pass adds is the other half — the read can now tell the key it *did* see from the key it
did not, which is the difference between rows 2 and 3 in the last column.

## Gate state after the task

| gate | before | after |
|---|---|---|
| G-PRED2 | 23 | 23 |
| INV-INS-130 | 16 | **15** |
| INV-INS-133 | 3 | 3 |
| INV-INS-134 | 22 | 22 |
| **total structural findings** | **64** | **63** |

One finding repaired, and it is the whole of the pass in the gates' terms: this file no longer
names the old substrate. `gh105_gate_baseline.py` reports no finding outside the recorded
baseline; the baseline was rewritten and its `retired` block (G-ACC, 17) preserved. G-ORDER is
unchanged — the same four known divergences, this file still skipped. `gh104_mop_lint.py` and
`gh104_message_gate.py` are green over the 23 files. `gh104_divergence_record.py --check`: 202
hunks, all recorded — 7 new rows for this file, 4 stale ones retired with their reasons absorbed.

Censuses: the set's accepting-state calls go 18 → **17** and the graph's bookkeeping 18 → **17**;
every other number holds, because this pass moved a store and not a placement. The graph stays at
77 rows, and two of them gain judgments instead of verdicts — the read's `clause` records the
`randomized`/`preparedKeyMaterial` conflation, and the write's `reason` records the arity.

## Reproducing

```bash
cd .../rvsec/rv-android
export RVSEC_HOME=.../rvsec; SPECS=$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources
CP=$(cat $RVSEC_HOME/rvsec/rvsec-mop/target/gh104-classpath.txt)

# the rule
cat .../MetaCrySL/generated/api30/SecretKeySpec.cryptsl

# the store's arity matching, which decided the write (ArityProbe: ensure/validate at 1 and 2)
javac -nowarn -cp "$CP" -d <dir> ArityProbe.java && java -cp "<dir>:$CP" ArityProbe

# the chain, both ends observed, one process per tree (ChainProbe)
#   SecureRandomSpec_g1Event/next2Event -> SecretKeySpecSpec_c1Event/3
#   -> CipherSpec_g1Event -> CipherSpec_i2Event/3, reading getExpecting() and
#   resetting the collector between configurations
java -cp "<dir>:<scratch>/<side>/work/classes/classes:$CP" ChainProbe <label>

# the transition table that makes @fail unreachable
grep -A2 "class SecretKeySpecSpecMonitor" <scratch>/b/monitors/MultiSpec_1RuntimeMonitor.java
```

**To see a window at all, run the probe against the tree the pass starts from.** Neither side of
the differential harness holds one, and neither does the pre-image.
