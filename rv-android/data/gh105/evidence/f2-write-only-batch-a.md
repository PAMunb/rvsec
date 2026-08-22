# F2 — the four write-only specifications (task 4.13): nine dead ends and one chain

**Date**: 2026-08-22 · **Change**: gh105-predicate-wiring · **Task**: 4.13
**Files**: `rvsec/rvsec-mop/src/main/resources/jca_android/{SignatureSpec,MessageDigestSpec,SSLContextSpec,KeyPairSpec}.mop`
**Oracle**: `MetaCrySL/generated/api30/{Signature,MessageDigest,SSLContext,KeyPair}.cryptsl`

The first pass of the group with **no read in any of its files**. That changes the question.
From 4.1 to 4.12 the pass opened by measuring what each site accuses today; here the answer is
always *nothing*, because a write does not accuse. What decides the pass instead is **who reads
the write, and in what store** — and the answer separates the eleven sites into nine that nobody
reads and two that close a chain.

## The count the task carried was wrong, and the artifact says so

Task 4.13 reads *"Seven of these eleven sites belong to `ENSURES`-only dead ends"*. Measured, it
is **nine of the eleven**. The seven is the `design.md` figure for **seven dead-end predicates
over eleven sites**, and those eleven span five files — `SignatureSpec` 4, `MessageDigestSpec` 3,
`SSLContextSpec` 2, `PBEParameterSpecSpec` 1 (task 4.7, already done) and `KeyPairGeneratorSpec`
1 (task 4.14). The task pinned that number to its own, different eleven. The two counts coincide
by accident.

Measured over the whole oracle and every specification set: no rule of api30 has a `REQUIRES` of
`signed`, `verified`, `digested`, `generatedSSLContext` or `generatedSSLEngine`. The
`digestedInputStream`/`digestedOutputStream` the two stream rules ensure are different predicates.
No `.mop` of `jca`, `jca_android`, `jse`, `generic` or the docker examples reads any of the five
`Property` constants; the only non-write occurrence anywhere is a one-shot audit driver from
2026-08-08 (`audit/20260808_validacao_jca_android/batchD/alfa_HarnessD.java:224`), which
INV-INS-147 already lists as not maintained. The grep also hit `jca_android_bug_predicate`, the
set the 2026-08-08 audit reproved 22/22 — it holds a copy of the same seed writes, and it counts
for nothing.

The other two sites, `KeyPairSpec.gpu` and `gpr`, have a live reader: `CipherSpec.i2`, on the new
store since task 4.1.

## The measurement

Probe over the whole `ErrorCollector`, **one process per configuration** — the generated monitor
set is static and `ExecutionContext.reset()` does not touch it, so a first version that ran the
five configurations in one JVM leaked automaton state between them and was thrown away. The
`body` and `@match` columns are written inline between the starting tree's own dispatchers
(learning 51); the last column was measured afterwards against the real migrated tree.

| configuration | pre-image | starting tree | write in **body** | write at **`@match`** | migrated tree (real) |
|---|---|---|---|---|---|
| **A** `new KeyPair(pub, priv)` → `getPublic()` → `Cipher.init` | 0 | 1 | **0** | **0** | **0** |
| **A2** pair from `KeyPairGenerator` → `getPublic()` → `Cipher.init` | 1 | 2 | **1** | **2** | **1** |
| **B** `new KeyPair(pub, priv)` → `getPrivate()` → `Cipher.init` | 0 | 1 | **0** | **0** | **0** |
| **C** control: a key of no observed origin | 0 | 1 | 1 | 1 | **1** |
| **D** control: a producer already on the new store (task 4.10) | 0 | 0 | 0 | 0 | **0** |

The probe is auditable in both directions the corollary of learning 27 asks for: **C** accuses in
every column from the starting tree on, **D** is silent in all of them, and **A** and **B** reach
zero in exactly the columns the pass claims. The last column reproduces the simulation
configuration by configuration, which audits learning 51 rather than trusting it (learning 57).

The nine dead-end sites have no column of their own, and that is the honest result: with no
reader anywhere, relocating them changes no report on any tree. What they buy is the record.

## The five decisions, and the number that decided each

### 1. Where the two `KeyPairSpec` writes go — the body, with a recorded reason

api30 states `generatedPubkey[retPub] after pu` and `generatedPrivkey[retPriv] after pr`, so
INV-INS-134's default sends both to the acceptance point. Read off the generated monitor, that
point exists — `gpu`/`gpr` have the transition row `{2, 1, 2}` and the match category is
`Prop_1_state == 1` — but it is **unreachable on the route by which a program obtains a KeyPair**:

```
api30 KeyPair.cryptsl   ORDER  co?, (pu*, pr*)*        <- the constructor is OPTIONAL
jca_android KeyPairSpec ere:   c1 (gpu | gpr)*         <- and here it is mandatory
```

A pair returned by `KeyPairGenerator.generateKeyPair()` was never constructed by a monitored
call, so `gpu` fires from the start state and goes to `fail`. Row **A2** is what an
acceptance-point write costs there: **2 reports instead of 1** — the `CIPHER-NOBS-00` this pass
exists to remove stays, on the common route.

The divergence is not new and not this pass's: gh104 task 8.12(f) already recorded it in
`conformance_record.csv` as measured-not-repaired, with the published-campaign mass —
**668 rows over 8 apps**, `TLSClientHandshakeKt.generateECKeys` 430 and `CryptoUtil.generateKeyPair`
218. Repairing the `ere` to `c1? (gpu | gpr)*` would give the best number of the three (A2 to 0),
and it is task 7.1's: `KeyPairSpec` is one of the specifications `order_alphabet_map.csv` does not
map, so G-ORDER skips it and would not have checked the change.

**The cost stated in full**: after a second `c1` — a sequence both the rule and the automaton
reject — the body write marks a key the automaton did not accept, where an acceptance-point write
would not. That is the whole of what the recorded reason buys back. When 7.1 lands, both writes
move to `@match`.

### 2. `KeyPairSpec.gpr` writes the predicate its clause names

The seed wrote the **private** key under `GENERATED_PUBLIC_KEY`. That is the defect task 6.1
names, and the reason `GENERATED_PRIVATE_KEY` was read at `CipherSpec.i2` and written nowhere.

Repaired here rather than recorded, and the argument is a measurement, not a preference. The
`preparedKeyMaterial` conflation stayed recorded at 4.10 and 4.12 because renaming it alone would
have reopened the chain the pass had just closed. Here it does not: `CipherSpec.i2` reads the
three key-origin predicates as one disjunction, so column **B** is 0 under either name. What the
seed's name costs is downstream, and **task 5.7 runs before task 6.1**:

```
seed naming   (ensure GENERATED_PUBLIC_KEY over a PrivateKey)
   5.7 initSign(priv)   reads generatedPrivkey[priv] -> NOT_OBSERVED   <- accuses a conforming program
   5.7 initVerify(priv) reads generatedPubkey[·]     -> SATISFIED      <- a private key answering the public clause
clause naming (ensure GENERATED_PRIVATE_KEY)
   5.7 initSign(priv)   -> SATISFIED
   5.7 initVerify(priv) -> NOT_OBSERVED
```

The repair also closes something the gate could see: `gh105_gate_baseline.py` reports
`[G-PRED2] repaired jca_android/CipherSpec.mop i2/GENERATED_PRIVATE_KEY`. The set's one read-only
property, which task 5.11 was going to have to close, is closed.

### 3. `SignatureSpec.v1/v2` write the object the clause names

api30 states `verified[sign]` over the **`byte[]` the call was given**; the seed wrote the
**boolean the call returned**. Measured, the two are indistinguishable in reports — no rule
requires `verified`, so nobody reads either — and measured on the store, the seed's form is not
about the program at all:

```
ensure(VERIFIED, true); validate(VERIFIED, <any other true>)  -> SATISFIED
```

`Boolean.valueOf` caches, so an identity-keyed store handed a boolean marks one JVM-wide object.
Writing the argument costs nothing, makes the site the literal transcription of the clause, and
leaves the omission record with one thing to say instead of two.

### 4. `generatedKeypair[this, _] after co` is not fabricated

api30 KeyPair states a third `ENSURES` and `KeyPairSpec.c1` has no write for it. None is added:
the predicate is required by no rule, its other producer is `KeyPairGeneratorSpec.mop:111` (task
4.14), and a clause with no site has no row in the site inventory to carry a record — the graph
is an inventory of sites. **Task 5.10 owns the record**, and this pass feeds it rather than
duplicating it, the way task 4.12 fed 6.5.

### 5. The `TraceRunner.produce()` repair enters this task

The harness could not build the object the pass needed to observe. Measured, not assumed:

```
KeyPairGenerator.getInstance("RSA")  ->  java.security.KeyPairGenerator$Delegate   (not public)
   setAccessible on Delegate.generateKeyPair()
   -> InaccessibleObjectException: module java.base does not "opens java.security" to unnamed module
   -> the call is refused and the binding silently becomes null
```

Silently, because `bind` lines are never recorded as unresolved. A trace naming a real key pair
replayed with a null key and measured something else.

The breadth was measured across the fourteen factories the corpus uses, and it is **one**:

| receiver | runtime class | public? | refused |
|---|---|---|---|
| `KeyPairGenerator` | `KeyPairGenerator$Delegate` | no | **`generateKeyPair`, `initialize`** |
| `MessageDigest` | `MessageDigest$Delegate$CloneableDelegate` | no | none — it overrides none of the methods the corpus calls |
| `Signature` | `Signature$Delegate` | no | none, same reason |
| `Cipher`, `Mac`, `KeyGenerator`, `SecureRandom`, `KeyFactory`, `SecretKeyFactory`, `KeyStore`, `SSLContext`, `TrustManagerFactory`, `KeyManagerFactory`, `KeyPair` | the class itself | yes | — |

The repair re-looks the same signature up on the nearest public supertype; virtual dispatch still
runs the delegate's body. Its effect was measured before it was accepted:

* **Zero of the 97 committed traces change** — the only three that change are the three this pass
  writes, and they change from measuring nothing to measuring the chain.
* `TraceRunnerTest` stays at **2 failures of 6**, the same two of finding 40, with the same text.
* The three new traces resolve on all **three** snapshots (learning 52), including the frozen
  control the test replays against.

This is the shape of decision 31, where task 4.11 took the `fitsPointcut` repair: without it the
pass's central chain has no committed witness.

## Where each write goes, read off the generated monitor

Learning 42, applied to four files at once. The `awk` costs nothing and closes the argument.

| file | clause | `after L` states | accepting states | handler |
|---|---|---|---|---|
| `SignatureSpec` | `signed[out, inpb] after Signs` (:87, with :89/:91) | `s1`/`s2` → `{1}` | `nextstate == 1 \|\| nextstate == 4` | `@match` |
| `SignatureSpec` | `verified[sign]` (:93) | — | `v1`/`v2` → `{4}` | `@match` |
| `MessageDigestSpec` | `digested[out, _]` (:73), `digested[out, inbytearr]` (:75) | — | `d1`/`d2`/`d3` → `{2}`, `nextstate == 2` | `@match` |
| `SSLContextSpec` | `generatedSSLContext[this] after Init` (:57) | `init` → `{1}` | `nextstate == 1` | `@match1` |
| `SSLContextSpec` | `generatedSSLEngine[eng]` (:59) | — | `engine` → `{1}` | `@match1` |
| `KeyPairSpec` | `generatedPubkey[retPub] after pu` (:41) | `gpu` → `{1}` | `Prop_1_state == 1` | body, recorded reason |
| `KeyPairSpec` | `generatedPrivkey[retPriv] after pr` (:43) | `gpr` → `{1}` | `Prop_1_state == 1` | body, recorded reason |

In the three files that move to a handler, the `after L` states and the accepting states are the
same states, so both routes INV-INS-134 admits name one handler. A handler sees no event
parameter (finding 43), so every object a handler cannot reach travels through a staged field
cleared on consumption — four of them: `stagedSigned`, `stagedVerified`, `stagedDigested`,
`stagedEngine`. `SSLContextSpec`'s context needs none: `g1`/`g2` bind the monitor field and state
1 is unreachable without them.

**Arity.** Three of the clauses are two-place and their sites write one place; the arity stays
where the seed had it, with the reason in `predicate_graph.csv` (decision 28, INV-INS-134's
recorded-reason clause). It costs nothing measurable here for a reason peculiar to dead ends:
there is no consumer whose arity the write has to meet. `digested[out, _]` is the one case where
the projection **is** the clause — the second place is anonymous, the same reading `MACED`
already carries for `macced[M, D]`.

## A finding this pass owes the record

**The `generatedSSLEngine` write is relocated onto an event with no execution path.**
`SSLContextSpec`'s `engine` pointcut declares `call(public void SSLContext.createSSLEngine(..))`
where the API returns `SSLEngine`, and both weavers gate the return type exactly, so the advice is
generated and never fires. The harness sees it from both sides: `SSLContextSpec.txt —
ctx.createSSLEngine()` appears under *Lines no pointcut resolved* on A and on B.

This is not new and not repaired here: gh104 task 8.7 recorded it in `conformance_record.csv` as
measured-not-repaired (researcher decision, 2026-08-18), on the ground that reviving it only adds
accusations the corpus cannot size. The pass relocates the write as the clause asks and leaves the
pointcut alone — the shape of decision 21. It is the fifteenth member of the family of finding 8.

## The harness

100 traces (97 committed plus the three this pass writes), against
`backup/gh105-preimage/jca_android`, cumulative:

```
unchanged 65 · moved 19 · introduced 10 · removed 6
```

`git diff --stat -- data/gh105/evidence/harness/` — **one report of the twenty-three changed**,
`f2-KeyPairSpec.md`, and it changed only by gaining the three new traces. Nothing else in the set
moved (learning 53).

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `KeyPairSpec-public-cipher.txt` | unchanged | — | — |
| `KeyPairSpec-private-cipher.txt` | unchanged | — | — |
| `KeyPairSpec-generated-cipher.txt` | unchanged | `KeyPairSpec.gpu` | `KeyPairSpec.gpu` |
| `KeyPairSpec.txt` | unchanged | — | — |

**All three new traces are `unchanged`, and that is finding 46 again.** The chain works on the
pre-image, where both ends are on the old store, and works on the migrated tree, where both are on
the new one. It was broken only on the **starting tree**, which the harness does not contain — the
producer had not moved and the consumer had, since task 4.1. Do not read `unchanged` as "nothing
happened": say what it is unchanged against. The closure is column B of the probe table, not here.

`KeyPairSpec-generated-cipher.txt` keeps its `KEYPAIR-ORDER-00` on both sides. That is the
automaton divergence of decision 1, and it is deliberately left in the trace: the report the pass
removes from that program is the `CIPHER-NOBS-00` beside it, which the harness cannot show for the
same reason as above.

The three specifications whose sites are dead ends are `unchanged` throughout, in all nineteen of
their traces, and their reports are byte-identical to the starting tree's. A relocation nobody
reads changes nothing, which is the expected result and the reason the record is the product.

## Gates

| gate | before | after |
|---|---|---|
| `read:condition-guard` (INV-INS-133) | 0 | 0 (no file of this pass declares a read) |
| `read:body` | 14 | 14 |
| `write:body` | 22 | **13** |
| `write:acceptance` | 12 | **17** |
| bookkeeping (INV-INS-147) | 17 | **11** |
| `remove:fail` / `negate:body` | 7 / 1 | 7 / 1 |
| INV-INS-130 files | 13 | **9** |
| gh105 structural findings | 55 | **30** (G-PRED2 13, INV-INS-130 9, INV-INS-134 8) |
| graph rows | 73 | **63** |
| `disposition=omission` rows | 1 | **6** |
| G-ORDER divergences | 4 | 4 (unchanged; the `SSLContextSpec` one is task 7.1's) |

`gh105_gate_baseline.py` reports **25 repairs** and no finding outside the recorded baseline:
ten G-PRED2 (including `CipherSpec.i2/GENERATED_PRIVATE_KEY`, the read-only property that closes
as a side effect of decision 2), four INV-INS-130 and eleven INV-INS-134. `gh104_mop_lint.py` and
`gh104_message_gate.py` green. `gh104_gates.py` over the generated monitor:
`G-2 0 · G-2a 4 · G-2b' 11 · G-2c 1 · G-2d 2 · G-6' 0 · G-ERE 0 · G-CONF 0 · G-PRED 14` — every
gate identical to the starting tree's except G-PRED, which goes 10 → 14 by construction: it counts
the seed's predicate sites a migrated file no longer has, one per migrated file, and is the mirror
of INV-INS-130 going 13 → 9.

`codes.csv` gains and loses nothing: not one of the eleven sites is an accuser. Eleven rows had
their `file_line` relocated by the edit, in place, with the file order preserved.

**42 divergence hunks recorded, 14 retired.** The retired ones are re-keyings, not withdrawals:
the edit merged each of them into an adjacent hunk, and every reason is absorbed into its
successor with the `task` column accumulating. One splits into two (`MessageDigestSpec
e731f09c6821` → `dec2110e981a` + `3b228032511e`, learning 49) and one absorbs two
(`SignatureSpec adc3c0a29ea3` takes `c526a03ca2c2` and `f5b107015238`). 240 hunks, all recorded;
the file grew +42/−14 rather than being rewritten, and the CRLF terminator is preserved.

The 94 assertions of the four gate suites pass.

## What this pass did not touch

The `fsm`/`ere` of any of the four files, and therefore `order_alphabet_map.csv`. Two of the four
are ORDER-unmapped (`MessageDigestSpec`, `KeyPairSpec`) and task 7.1 owns the mapping; the
`SSLContextSpec` divergence `g1 Init se1 se1` is one of the four open G-ORDER findings and is also
7.1's. The `MessageDigestSpec.reset` deletion, the `SignatureSpec` fusion of `g3` and the two
allow-list transcriptions are earlier tasks' hunks that this pass only re-keyed.

The `@match` of `KeyPairSpec` is left **empty** rather than deleted: an `ere` names its accepting
category whether or not a handler uses it, the JavaMOP grammar requires the handler after the
`ere`, and the write returns there at task 7.1. The precedent is `RandomStringPassword` at task
4.11.

Three fields the accepting-state bookkeeping orphaned are deleted with it — `Signature signature`,
`MessageDigest md`, `KeyPair keyPair` — following task 4.1, which deleted `Cipher cipher` and its
two assignments the same way. `SSLContextSpec`'s `context` stays, because the write reads it;
`SSLEngine engine`, which nothing ever assigned, is replaced by the staging field.
