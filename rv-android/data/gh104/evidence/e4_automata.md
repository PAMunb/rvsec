# E4 — structural repairs in `jca_android` (Group 8)

What this records: the run of tasks 8.1–8.16, what each instrument returned, the harness verdict of
every item that changes what is accused, and the three instrument repairs the group needed. The
per-specification before/after evidence is in `evidence/harness/e4-<Spec>.md` (the six structural
repairs), `e4-8.14-<Spec>.md`, `e4-8.15-<Spec>.md` and `e4-8.16-<Spec>.md`, 23 files each.

## What changed in the set

Six structural repairs over five files, each proved against the api30 rule, the `javap` signature on
`android-30` or the frozen-control monitor — never against the lineage's word:

| task | file | the repair |
|---|---|---|
| 8.1 | `GCMParameterSpecSpec` | the second `event c1` (the four-argument constructor) becomes `c2`, which is what `ere : c1 \| c2` always referenced and what `GCMParameterSpec.cryptsl:17,19,21` declares |
| 8.2 | `SecretKeySpecSpec` | the surplus `)` in `c1`'s condition leaves |
| 8.3 | `MessageDigestSpec` | the `reset` event is deleted |
| 8.4 | `KeyPairGeneratorSpec` | `init1`, `init2` and `initError` guard on `algorithm != null` |
| 8.5 | `SignatureSpec` | `sign()` returns `byte[]` and `sign(byte[], int, int)` returns `int` |
| 8.6 | `KeyPairGeneratorSpec` | the unreachable `UnsafeAlgorithm` branch inside `init1` leaves |

Two sites were measured without an edit (8.7), one item was withdrawn as a checked non-defect (8.8)
and nine inherited structural divergences were recorded as measured and not repaired (8.12) — all
three in `data/jca_android/conformance_record.csv`, which now carries **73** rows. Of the three
measured items inherited from E1, **8.14 landed** (the `g4` report of `MessageDigestSpec` is live
again), **8.16 landed** (fifteen guards over nine specifications now test the getter their message
already names) and **8.15 was applied, measured and reverted** — the reason is below and in the
conformance record.

`codes.csv` stays bijective with the census at **50 rows**: `KEYPAIRGENERATOR-ALG-00` leaves with
8.6's unreachable branch and `MESSAGEDIGEST-ALG-02` arrives with 8.14's revived report. 8.3 removes
an event with no report site, so it moves no row.

`data/jca_android/gate_allowlist.csv` no longer carries the temporary G-ERE row task 7.6 wrote
"until 8.1"; it carries seven rows instead, one per surviving gate hit family, each with its reason.

## What the instruments said

| instrument | result |
|---|---|
| `gh104_mop_lint.py` on `jca_android` | **clean** — `duplicate-event` 1 → 0 and `undeclared-symbol` 1 → 0 (8.1), `unbalanced` 1 → 0 (8.2) |
| `gh104_message_gate.py` on `jca_android` | **clean** — `self-contradicting envelope` 15 → **0** (8.16); `code-bijection` 0 across the removal of 8.6 and the addition of 8.14 |
| `gh104_gates.py` on the regenerated monitor | **ok** — G-6′ 1 → **0** (8.1), G-ERE **0** without the temporary allowlist row, G-2 `orphan-without-clause` 3 → **2** (8.3), G-CONF **0** failures (55 notes), G-PRED **0**; G-2a 1, G-2b′ 8, G-2c 1, G-2d 2 unchanged from the frozen baseline. Every remaining hit is allowlisted with a reason, so the gate report is `ok: true` |
| `gh104_divergence_record.py --check` | green: **130 hunks, all recorded**, 4 narrative entries; kinds now include `automaton` |
| generation | 1 min 21 s, peak RSS 4.4 GiB, `MultiSpec_1RuntimeMonitor.java` 17,098 lines, **zero** unexpanded `__EVENTNAME` in any generated Java or `.aj` |
| compilation | `javac` clean, 63 classes |
| `CipherSpec` | 17 events — at the INV-INS-115 ceiling, unchanged; still generates |
| `tests/parity` | 74 passed, 3 failed, 7 errors — **all four `test_gh104_structural_gates.py` failures closed**, and the survivors are the environmental ones the handoff names (`test_no_legacy_mop`, `test_baseline_freshness`, and the `ANDROID_SDK_HOME` group) |

A number the plan asked to be measured rather than repeated: the set carries **143** `call(`
pointcuts over its 23 files, counted with `grep -o 'call *(' | wc -l`, which counts occurrences and
not lines. The plan's 141 was a count over a 21-file seed that D-11 withdrew.

## The harness verdicts

Four before/after runs, each against the snapshot immediately preceding its own edit, over the
**63** traces of `data/gh104/traces`.

| run | traces | verdicts | expected? |
|---|---|---|---|
| `e4` (8.1–8.6) | 62 | 59 `unchanged`, 2 `removed`, 1 `introduced` | yes |
| `e4-8.14` | 63 | 62 `unchanged`, 1 `introduced` | yes |
| `e4-8.15` | 62 | 62 `unchanged` | **no** — reverted |
| `e4-8.16` | 63 | 61 `unchanged`, 2 `moved` | see below |

Item by item:

- **8.1, 8.2, 8.4, 8.6 — `unchanged`**, as required. 8.4 earned a second piece of evidence the plan
  did not anticipate: on the A side `kpg.initialize(2048)` raises
  `NullPointerException: Cannot invoke "String.toUpperCase()" because … canonical(String, String) is
  null` at **both** the `init1` and the `initError` dispatchers, and on the B side it does not. That
  is the exact failure task 8.4 argues from, reproduced rather than inferred, and it accuses nothing
  on either side — which is what makes the verdict `unchanged` and the repair accusation-neutral.
- **8.3 — `removed`**, on `MessageDigestSpec-reset.txt`: A accuses at `MessageDigestSpec.reset`, B
  accuses nothing and records `md.reset()` as a line no pointcut resolves. This is the one repair of
  the group that removes accusations.
- **8.5 — `introduced` and `removed`, one trace each**, which is what the task demands and what the
  set had no trace for. `SignatureSpec-sign-unobserved.txt`: A accuses nothing, B accuses at `s1`
  (`sign()` on a `Signature` whose `getInstance` was never dispatched starts at state 0, where
  `s1[0] = 8`). `SignatureSpec-initsign-after-sign.txt`: A accuses at `i1`, B accuses nothing (once
  `s1` fires, state 7 → 6, and `i1[6] = 1` where `i1[7] = 8`). On the A side of both, `s.sign()` is
  recorded as a line no pointcut resolves — the dead pointcut, visible.
- **8.14 — `introduced`** on `MessageDigestSpec-unlisted-only.txt` (B accuses at `g4` with
  `val='SHA3-256'`), `unchanged` on the other 62.
- **8.16 — no accusation introduced anywhere.** Across all nine `guard-on-field` traces the B side's
  accusations are a strict subset of the A side's, and every `self-contradicting envelope` flag the
  harness raises sits on the A side, none on B.

## Two labels that read oddly, and why

The classifier compares the **list of accusing event names**, so it can only say `removed` when the
B side accuses nothing at all. Task 8.16 removes one accusation from traces that carry a second,
unrelated ORDER accusation, so:

- where the removed value accusation shared its event with the surviving one, the label is
  `unchanged` even though the error type and code changed — `MessageDigestSpec` A `MESSAGEDIGEST-ALG-00
  val='SHA-256'` → B `MESSAGEDIGEST-ORDER-00` at the same `update`; likewise `SSLContextSpec`
  (`val='TLSv1.2'`), `TrustManagerFactorySpec` (`val='PKIX'`) and `CipherSpec`
  (`val='AES/CBC/PKCS5Padding'`);
- where it sat at a different event, the label is `moved` even though B accuses strictly less —
  `KeyGeneratorSpec` (A `init` + `gk1`, B `init`) and `KeyStoreSpec` (A `load` + `gk1`, B `load`).

Both are the removal the task asked for, so neither was treated as the revert-triggering class. The
raw label is recorded per specification in the conformance record beside what actually moved.

Four of the nine traces never reach their value site at all, and E1 had already recorded why:
`KeyStoreSpec`, `KeyManagerFactorySpec`, `MacSpec` and `SignatureSpec` send the monitor to `fail` on
the first call of an object whose `getInstance` was never dispatched, so the event body holding the
guarded site never runs. The case needs an object that skipped `getInstance` *and* reaches the value
event legally, and those two are contradictory in those automata.

## Why 8.15 was reverted

Adding `__RESET;` to `KeyPairGeneratorSpec`'s `@fail` handler is correct by construction — the other
20 handlers of the set reset, and `Category_fail` is sticky, so the dispatcher re-runs
`Prop_1_handler_fail` on every later dispatch while the flag holds. It was applied, measured and
taken out again, because the harness classifies `unchanged` on all 62 traces, including
`KeyPairGeneratorSpec-sticky-fail.txt`, which was written for this measurement alone.

The reason is not harness infidelity, it is the production write path. `__LOC` expands to
`ViolationRecorder.getLineOfCode()`, a stack walk, and `ErrorCollector.addError` writes a row **only
when `errors.add(err)` succeeds**, over an `ErrorSummary` of `(spec, error, class, method,
location)`. A handler re-running at the same location is therefore already suppressed before it
reaches `errors.csv`, and `TraceRunner` replays every event through one reflective frame, so every
location is the same one. What 8.15 removes in production is the repeat at each **subsequent call
site**, which a single-site replay cannot stage. The task's rule is that a verdict outside the
expected class reverts the edit and records why, so it is reverted and recorded. Measuring it needs
either a replay that gives each trace line its own call site, or a device run.

## Where G-2 did not reach zero, and what carries it

Task 8.10 asks for G-2 `orphan-without-clause` = 0. It is **2**: `PBEKeySpecSpec.err2` and
`SecretKeySpecSpec.c3`, both allowlisted with reasons.

Design D-7 predicted all three of the frozen set's clause-less orphans would be "absent from
`jca_android` by construction", because Group 2 was to remove the predicate machinery that carries
two of them. **D-11 withdrew that removal** and keeps the seed's predicates unchanged, so `err2` and
`c3` survive with their guards. Both are real orphans under the mechanical mapping — `err2` tests
`RANDOMIZED[password]` where `PBEKeySpec.cryptsl:40` requires `randomized[salt]` and nothing about
the password; `c3`, after task 2.4 removed its algorithm half, tests `RANDOMIZED[keyMaterial]` where
`SecretKeySpec.cryptsl:34` requires `preparedKeyMaterial[keyMaterial]`, a different predicate. Both
repairs remove accusations on a predicate the rule does not state, which is the class of item task
8.12 records rather than repairs. `reset`, the third and the only one no `FORBIDDEN` clause
justified, is the one this group deleted.

The same D-7/D-11 tension explains four more allowlisted hits: G-2a 1, G-2c 1 and G-2d 2 all sit on
`SecretKeySpec.mop` and `RandomStringPassword.mop`, which D-7 measured as having no successor
because they were to be deleted, and which D-11 keeps.

## Three instrument repairs, and the traces they needed

The differential harness was written before any of this group's items were measured, and two of its
rules could not see the defects it was asked to measure. Each was repaired rather than allowlisted,
and neither changes any verdict already recorded, because both sides of every comparison are
replayed by the same instrument.

1. **`TraceRunner`: the return-type gate.** `Pointcut` discarded the declared return type —
   `readAll` took the last word of the signature as the method name and `matchesShape` compared name
   and arity only — so `call(public byte Signature.sign())` resolved `s.sign()` exactly as
   `byte[]` does. Both weavers gate the return type exactly (AspectJ by construction; the dexlib2
   engine in code, `PointcutMatcher.java:361-363` with `PointcutMatcherTest.java:603-612`, "concrete
   return-type gate MUST be exact"), so replaying such an advice reports that a specification
   accuses where the woven application is silent. Measured before the repair: task 8.5's before/after
   classified `unchanged` because both sides fired `s1`. After it, the A side records `s.sign()` as
   unresolved and the two verdicts are `introduced` and `removed`. The gate consults this JVM's
   platform, which agrees with android-30 on every signature the set names, and a type the harness
   cannot resolve carries no gate rather than a false negative.
2. **`TraceRunner`: a raised exception is a result, not the end of the run.** A guard or a handler
   can throw — `KeyPairGeneratorSpec`'s `validate()` switched on a null field until task 8.4 — and
   the replay died with the first one, so the side that throws produced no verdict at all and the
   side that does not could never be compared with it. The exception is now recorded against its
   trace line, naming the specification, the event and the cause, and the replay continues. This is
   how 8.4's `NullPointerException` became evidence instead of a crash.
3. **`gh104_divergence_record.py`: the `automaton` kind.** The record had no species for a structural
   repair; Group 7 added `message` for the same reason. Every hunk of this group carries it.

Three traces were added for measurements the set could not stage:
`SignatureSpec-sign-unobserved.txt` and `SignatureSpec-initsign-after-sign.txt` (8.5's two
directions) and `MessageDigestSpec-unlisted-only.txt` (8.14). A fourth,
`KeyPairGeneratorSpec-sticky-fail.txt`, was written for 8.15 and is kept: it is the trace that
demonstrates why that measurement cannot be made this way, and it is what reproduces 8.4's
exception. `MessageDigestSpec-md5-only.txt` no longer reaches `g4`, because task 2.4's transcription
admits MD5 — the api30 single oracle doing its job, not a defect — which is why 8.14 needed a trace
naming an algorithm the rule genuinely omits.

## Hunks that fused, and the rows that replaced them

The divergence record keys a hunk by the digest of its changed lines with zero context, so editing a
line adjacent to an already-recorded hunk merges the two and changes the key. It happened three
times, and each time one row replaced the pair and named both tasks:
`KeyPairGeneratorSpec` `init1` (tasks 2.4, 7.5, 8.4 and 8.6 in one hunk), and the nine
`guard-on-field` guards, whose Group 2 allow-list rewrite and this group's 8.16 edit sit on the same
lines (tasks 2.4 and 8.16).

Task 8.2 was written twice for the same reason. Rebalancing the parenthesis on the line that carries
the predicate call would have left `INV-INS-128` reporting a rewritten predicate site — that gate
compares the seed's `ExecutionContext` lines to the successor's verbatim — even though the predicate
call is untouched. The surplus parenthesis is dropped from the line that carried it and the brace is
left alone on its own line, so the predicate line is byte-identical to the seed and the lint is
clean.
