# Design: gh105-predicate-wiring

**GitHub Issue**: #105 · **Predecessor**: gh104 D-11 · **Phase 0**:
`docs/20260820_plano_fiacao_predicados.md` (audited twice; every load-bearing claim carries
`[auditado]`/`[auditado-v2]` marks and reproducible evidence in
`audit/20260820_verificacao_plano_predicados_v2/`). External verification 2026-08-20
(`docs/analise_gh105_{claude,gemini,gpt5}.md`, consolidated in `docs/20260820_validacao_gh105.md`
— the review whose eight blockers drove the amendments; untracked today, committed with this
change): adopted findings re-verified against primary sources before amendment. A six-front
readiness audit the same day (Java tree, gate layer, Phase-0 evidence, task executability, delta
format, cross-artifact arithmetic) produced D-11 to D-14 and INV-INS-148.

## Context

gh104 made violation reports legible — envelope, codes, event names — and preserved the predicate
machinery byte-for-byte (G-PRED) precisely so that wiring it correctly could be its own change.
This is that change. The current state is measured, twice: 3 of the 19 connectable predicates
realized as links with both ends live (per clause, 25 of the 35 are wireable in-set — the
ledger below); 27/27 reads in `condition(...)` (guard suppresses the transition — the
false-accusation mechanism proven in the generated monitor at `Prop_1_event_i2`, `return false`
before `handleEvent`); 17 orphan accusers sustaining at most 56.1 % (39,682) of the published
`InvalidSequenceOfMethodCalls` — the 70.4 %/49,817 figure is the frozen `jca`'s ten-spec family,
`MessageDigestSpec` included; 42/49 writes in event bodies instead of acceptance points; 8 of 9
`remove()` implementing a semantics no CrySL generation has; a substrate keyed by `equals` under
monitors keyed by identity, arity-1 under 31 binary clauses, boolean under a three-valued truth.

Two prior attempts failed. gh101's identity re-keying of the shared `ExecutionContext`
(`233df18a`) was reverted in three days because the `jca` freeze gate checks `.mop` files, not
the classes they call. The `jca_android_bug_predicate` set wired predicates without the
instrument and was failed 22/22 by the 2026-08-08 audit — but its structural bucket (51 automaton
hunks, the audit's `PROVADO`/`PASS` verdicts — "proven") is rescue material under fresh evidence.

Constraints: `jca` frozen (INV-INS-109); the archived set is a record, not a seed; MetaCrySL
rules are a read-only oracle; the weaver is out of scope; gh104 Group 10 is not run (joint
validation in `experimento-gh104/`). FR01-FR03 (monitor generation), NFR06 (measurement
integrity), NFR07 (reproducibility).

## Architecture

```
MetaCrySL api30 rules (oracle, read-only)
        │  clauses (ENSURES/REQUIRES/NEGATES, ORDER)
        ▼
jca_android .mop (24 files)───────────────┐
  │ store calls (body/@match)             │ junction specs (per co-observable chain)
  ▼                                       ▼
rvsec-core: PredicateStore/PredicateVerdict   JavaMOP parametric indexing
  (new classes; ExecutionContext untouched    (CachedWeakReference identity,
   — byte-identical, serves frozen jca only)   weak refs, sync — for free)
        │ verdict + code                        │ @fail with code
        └──────────────► ErrorCollector envelope (gh104) ◄──────────┘
                              │
                              ▼
rv-android gate layer (scripts/, tests/parity/):
  predicate_graph.csv ── G-PRED2 (closure)      order_alphabet_map.csv ── G-ORDER (DFA equiv)
  G-ACC (orphans, both directions)              G-PARAM (.mop list survives in .rvm)
  import-discipline (no ExecutionContext)       G-PRED (jca lock only — reformulated scope)
  all generic over the enumerated .mop universe (215 today; skip-and-count contract)
        │ before/after monitors
        ▼
scripts/gh104_diff_harness.py + TraceRunner: satisfy/violate trace pair per wired edge
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `rvsec-core …/mop/PredicateStore` (new) | Hybrid-keyed, arity-N, three-valued predicate store for `jca_android` | `ensure/negate/validate` calls from `.mop` bodies | `PredicateVerdict` |
| `rvsec-core …/mop/PredicateVerdict` (new) | The three-valued result type | — | `SATISFIED`/`VIOLATED`/`NOT_OBSERVED` |
| `rvsec-core …/mop/ExecutionContext` | Frozen legacy store; zero edits (byte-identical) | (unchanged) | (unchanged) |
| `jca_android/*.mop` + `codes.csv` | The wired set: automata, placements, junction specs, codes | api30 clauses | monitors + envelopes |
| `scripts/gh105_predicate_graph.py` (new) | Structural `.mop` analyzer → `predicate_graph.csv`; placement, G-PRED2 closure, junction rules (a)(b)(d) | the enumerated `.mop` universe | CSV + gate verdicts |
| `scripts/gh105_order_gate.py` (new) | G-ORDER: DFA equivalence under versioned alphabet map | `.mop`, `.cryptsl`, `order_alphabet_map.csv` | verdict/skip per spec |
| `scripts/gh105_param_gate.py` (new) | G-PARAM: `.mop` header vs `.rvm` header | generated artifacts | verdict per spec |
| `scripts/gh104_gates.py` (edited) | G-PRED scoped to `jca`; `accept_requires`/`PREDICATE_CALL` recognize the new store | monitors, records | gate verdicts |
| `tests/parity/test_gh105_predicate_gates.py` (new) | pytest home of the new gates | gate scripts | CI verdicts |
| `rvsec-mop` test scope (`TraceRunner`) + `gh104_diff_harness.py` | Per-edge satisfy/violate trace pairs, before/after | traces | committed verdicts |

## Mapping: Spec → Implementation → Test

| Requirement / Invariant | Implementation | Test |
|---|---|---|
| INV-INS-130 (no `ExecutionContext` in set) | import-discipline gate in `test_gh105_predicate_gates.py` | `test_inv_ins_130_import_discipline` |
| INV-INS-131 (store contract) | `PredicateStore.java`, `PredicateVerdict.java` | JUnit `PredicateStoreTest` (identity, tracked-type value, arity, 3 values, weak keys, threads) |
| INV-INS-132 (frozen substrate) | zero-diff on `ExecutionContext.java` (joins `FROZEN_PATHS`); `Property` append-only | gh101/gh104 freeze gates + `git diff` assertion + `test_property_append_only` |
| INV-INS-133/134 (placements) | `.mop` edits F2; placement checks in `gh105_predicate_graph.py` | `test_inv_ins_133_no_condition_reads`, `test_inv_ins_134_write_placement` |
| INV-INS-135 (orphans, both directions) | `.mop` edits F1; G-ACC | `test_inv_ins_135_gacc` (+ `GCMParameterSpecSpec` negative fixture) |
| INV-INS-136 (junction rules) | junction `.mop` files F3; (a)(b)(d) checked structurally in `gh105_predicate_graph.py` | `test_inv_ins_136_junction_rules` + G-PARAM + pilot-derived TraceRunner pairs |
| INV-INS-137 (graph closure) | `predicate_graph.csv` + G-PRED2 | `test_inv_ins_137_gpred2` (incl. zero-rows-green over `generic`) |
| INV-INS-138 (G-ORDER + mapping) | `gh105_order_gate.py` + `order_alphabet_map.csv` | `test_inv_ins_138_gorder` (SecureRandom `Ends*` case) |
| INV-INS-139 (G-PARAM) | `gh105_param_gate.py` | `test_inv_ins_139_gparam` (byte[]/char[] collapse fixtures) |
| INV-INS-140 (genericity) | skip-and-count in every gate; the universe is enumerated, never a literal | `test_inv_ins_140_genericity` |
| INV-INS-141 (G-PRED rescoping) | `gh104_gates.py` edits + pytest rewrite; `divergence_record.csv` rows | `test_gpred_jca_lock_only` |
| INV-INS-142 (`remove()` semantics) | F4 `.mop` edits (8 removals out; `PBEKeySpecSpec` on new store) | harness deltas per removal |
| INV-INS-143 (*not observed* code) | `codes.csv` + envelope emission in `.mop` bodies | `gh104_message_gate.py` extension |
| INV-INS-144 (trace pair per edge) | `data/gh104/traces/` additions + harness runs | committed evidence per task |
| INV-INS-145 (Cipher generation + heap) | task discipline; real-pipeline generation; zero CipherSpec alphabet growth | recorded heap in task evidence |
| INV-INS-146 (negated-clause polarity) | `validateAbsent` entry point; polarity column in graph | JUnit polarity cases + `test_inv_ins_146_negated_polarity` |
| INV-INS-147 (accepting-state disposition) | per-file migration removes the 25 calls; divergence rows | harness deltas + divergence_record.csv counts |
| INV-INS-148 (harness isolation) | `TraceRunner.replay()` resets the predicate substrate beside `ErrorCollector` | `TraceRunnerTest` cross-trace case (satisfy then violate in one replay) |

## Goals / Non-Goals

**Goals**: the 36 `REQUIRES` clauses resolved per the ledger — 21 wired, 14 recorded
(10 `unmonitored-consumer`/`unmonitored-producer`, the vacuous #30 and #23, the
`unreachable-composition` #17 and #21), `preparedEC` `unclosable`; zero
orphan accusers; zero guard reads; three-valued verdicts reaching the envelope; the freeze safe
by construction; a gate layer that holds all of it over the full enumerated universe (215 files
today, the junction specifications this change adds included).

**Non-Goals**: repairing `jca` or the archived set; editing MetaCrySL; the weaver (if
`UnsatisfiedConstraint` stays at zero on the production path, this change is **blocked** and the
weaver becomes a prerequisite — the early reach probe of D-12 is the first place this shows,
before any F3 edge); the
article (untouched — the corrected numbers serve the next experiments); the upstream
javamop/rv-monitor grammar patch (documentation only, D-10); gh104 Group 10; re-running
campaigns (joint experiment does that).

## Decisions

**D-1 — New store classes beside the old one (researcher, 2026-08-20).** Alternatives: repair
the shared class (failed once — `233df18a`/`e204e2a4`; the freeze gate does not see Java);
per-set implementations selected by import with both maintained (superseded — more surface, same
risk). Chosen: new classes used only by `jca_android`; `ExecutionContext` **byte-identical,
zero edits**. The originally planned `@Deprecated` annotation was dropped by the 2026-08-20
external verification and **ratified by the researcher the same day** (§3.1-bis revision):
WORKFLOW.md P3 literally
bans deprecation annotations, the annotation was measured inert in every build path
(`showWarnings`/`showDeprecation` false, no `-Werror` anywhere), and byte-identity without
exception is the stronger freeze claim — the file joins `FROZEN_PATHS`. Cheap because
`generic`/`generic_new` call no predicate substrate (0/145 files); after migration the old class
serves only read-only sets. P3 is not violated: the old class is alive, serving `jca`.
The main spec's freeze requirement carries a scenario — *"Shared runtime code the frozen set
references is repaired"* — that grants a repair path for `rvsec-core` code **specifications of
both sets call**. Freezing `ExecutionContext.java` byte-identically does not contradict it: after
migration no `jca_android` specification calls the class, so that scenario's WHEN is vacuous for
this file and the repair path it grants has no subject left. INV-INS-132 states this, so the
narrowing is carried by the delta and not left to a reader's inference.

**D-2 — Hybrid wiring mechanism, partitioned by chain type (pilot-validated).** Alternatives:
store-only (A — reimplements identity the runtime already has; leaks and races were the measured
result last time), junction-by-default (B — dies on the `byte[]` family: a primitive-array
parameter silently deletes the spec's parameter list, and 17 of the 27 live reads bind `byte[]`,
19 counting `char[]`).
Chosen: B for co-observable chains — including `byte[]` via the `Object` idiom with the overload
fixed in the `call(...)` signature — A (the new store) for value positions, non-co-observable
edges, and whatever the topology leaves. The executed pilot decided this with evidence, not on
paper: B distinguished instances correctly on the hard case, and its failure modes became the
four binding rules of INV-INS-136. Per-chain choice is recorded in `predicate_graph.csv`.

**D-3 — The nine `remove()` (plan D3, reformulated by audit).** The oracle has two `NEGATES`
clauses; at most one of our removals corresponds (`PBEKeySpecSpec.mop:72`, `clearPassword`).
Decision: the 8 `@fail` removals are deleted (semantics foreign to both CrySL generations;
couples typestate to predicate against the rule's own orthogonality), each with its harness
delta; the `PBEKeySpec` removal is kept, translated to the new store, object-scoped. The
`SecretKey generatedKey[this,_] after d` clause has no `destroy` event in the set — recorded as
`unclosable` rather than invented.

**D-4 — Three-valued verdict, confined by construction.** `VIOLATED` requires positive evidence
(an entry for the object exists with mismatched value positions, or the predicate was negated);
no entry at all is `NOT_OBSERVED`; a matching entry is `SATISFIED`. Polarity inverts the table
(INV-INS-146): for the oracle's three negated clauses, no entry is the conforming case and stays
silent, while a same-name entry violates — read through `validateAbsent`, never the positive
`validate`. Guarded clauses (8 of 36) evaluate their guard in the body before the read; a false
guard suppresses the read and any report, never the transition. The signature change cannot
touch the frozen 27 `jca` sites because it is born in the new class (D-1). Because
`condition(...)` compiles to a boolean guard, three-valued reads are body-only — which F2
mandates anyway. The *not observed* code lands in `codes.csv`/envelope in the same task as the
first three-valued read (INV-INS-143), so no window exists where the third value is computed but
invisible.
**Deliberate strengthening against the static oracle (external finding gpt5 F-04, disposed
2026-08-20).** CogniCrypt's `AnalysisSeedWithSpecification.java:475-513` leaves `predEval=true`
when the statically extracted tracked values come back empty — imprecise extraction degrades to
silence, because a static analysis that cannot see a value must not accuse on it. The runtime has
no analogue of that failure: a woven event either observed the value or the event did not fire,
and the second case is exactly `NOT_OBSERVED`, which carries its own code and is never reported
as a violation. So this change accuses where the static oracle stayed silent, deliberately, and
the two are not comparable on that axis — a `VIOLATED` here means positive runtime evidence of a
mismatch, not an extraction gap. Recorded so that a later comparison against CogniCrypt numbers
reads the difference as design, not drift.

**D-5 — G-PRED rescoped, not deleted.** It stays as the `jca` lock; for `jca_android` it is
retired and replaced by G-PRED2 over `predicate_graph.csv`. Collateral updated in the same task:
`accept_requires` (G-2 would emit false reds), `PREDICATE_CALL` regex (blind to the new store),
the INV-INS-128 pytest, `gh104_message_gate.py::_clause_family` (classifies an orphan's clause
family from `condition(...)` text, which F2 empties), `experimento-gh104/scripts/preflight.py::
check_no_predicates` (a second gate also named G-PRED, still asserting the withdrawn
zero-predicates polarity; warn-only — it never fails a run — so it is retired, not renamed),
`tests/parity/test_gh104_structural_gates.py:229::test_jca_g_pred_counts_the_sites_the_successor_must_carry`
(a **third** G-PRED assertion, already `jca`-only, so it survives the rescoping and is listed to
prove it was read, not overlooked), and the census constants at
`tests/parity/test_gh104_specset_gates.py:41-52` (`PREDICATE` regex, `EXPECTED_CONSTRUCTS`,
`EXPECTED_PREDICATE_LINES = 134`, `EXPECTED_SPECS = 23`), which encode the frozen census the
migration invalidates for the successor set.
The `err2`/`c3` rows of `data/jca_android/gate_allowlist.csv` are justified by condition reads
that **F1** removes first: their re-justification lands with the first Group-3 fusion that
deletes a cited event, not with this task's commit. Divergence policy: **one row per diff hunk**, which is what
the instrument actually enforces — see D-11.

**D-6 — Junction design rules are enforced, each by its own instrument.** (a) consumer never
`creation`; (b) benign self-loops for disconnected joins; (c) `Object` idiom + fixed overload
for primitive arrays; (d) monitor fields for handler state. Each rule exists because the pilot
measured its violation: (a) accused the conforming trace; (b) produced spurious cross-chain
fails; (c) is the silent-collapse contour; (d) is a compile-time visibility fact. All four are
gated, not reviewed: (c) by G-PARAM, and (a), (b), (d) by structural checks in
`gh105_predicate_graph.py`, because each is decidable from the `.mop` alone — (a) is the
`creation` keyword on the consumer event declaration, (d) is handler state declared outside the
monitor's field block, and (b) is a reachability question over the declared automaton (every
state a disconnected join can reach carries the benign self-loop). Leaving them to per-chain
review was the plan's weakest point: a review that runs once per chain cannot protect a rule a
later edit can break silently. The pilot-derived negative fixture traces stay — they prove the
failure mode is real, the gate proves it stays absent — so each chain still commits the
rule-violating fixture inside the trace pair of INV-INS-144.

**D-7 — Gates are generic by contract (skip-and-count).** The seven measured gaps of plan §8-bis
define the contract; `generic`'s 118 files (82 % multi-parameter, 12 non-compiling counting the
`FSM358.mop` import collision) and `generic_new`'s 27 files (17 of them event-only) are the
standing test bed — 118 + 27 = the 145 predicate-free files of INV-INS-130. A gate that cannot classify a
file skips it, counts it, and says why — never green by vacuity, red by absence, or crash.

**D-8 — Order of work: substrate and gates first, then automata, then guards, then edges.**
F0 (store) and the gate skeletons come first because every later task closes against them; F1
(orphans) is independent of the mechanism decision and lands early for its measured payoff
(≤ 56.1 % of the published ISoMC category, a ceiling); F2 (guard moves + the write relocation of
INV-INS-134 — 42 of 49 writes sit in event bodies today) before F3 because every
F3 consumer read presupposes body placement and every F3 producer presupposes acceptance-point
writes — and the F2→F3 window is declared: until a read's
producer lands in F3, the read evaluates to `NOT_OBSERVED` on every trace, so F2 trace pairs
assert `NOT_OBSERVED` (the satisfy side is impossible inside the window) and the
`SATISFIED`/`VIOLATED` pairs of INV-INS-144 land per chain in F3;
F3 wires topologically (the `randomized` hub first as the pilot's chain, then `generatedKey`,
then `prepared*` closing `Cipher`, then the TLS chain); F4 pointwise fixes ride alongside; F5
gates harden continuously, not at the end. **The reach probe splits from the smoke test and moves
to the front (D-12)**: the first migrated file plus the *not observed* code are already enough to
ask the one question that can void the change, so it is asked there — before any F3 edge — and
its verdict gates entry into F3.

**D-9 — Scope: this change carries F0–F5 as a single change (ratified by the researcher,
2026-08-20; supersedes the plan's D2 split recommendation).**
Issue #105 was created with the full wiring as acceptance criteria and the researcher directed
artifact creation on that basis. The task order (D-8) preserves the split's virtue: F0+F1+F2
form a complete, verifiable stage before any F3 edge lands, so the change can pause at a
coherent boundary if capacity demands it.

**D-10 — No upstream toolchain patch, now or later in this line of work (researcher,
2026-08-20).** The parameter-collapse root cause is located (`javamop.jj:1456` vs `:1470`;
silent `catch` in both `JavaParserAdapter`s; a fix would need a double patch because rv-monitor
re-parses the `.rvm`) and stays recorded as **documentation only**. The `Object` idiom bypasses
the collapse entirely, G-PARAM guards the gap, and the two generators are also used by the
frozen set — javamop/rv-monitor are not touched.

**D-11 — Divergence records stay per hunk (readiness audit, 2026-08-20).** The plan wrote "one
row per migrated file, matching the granularity gh104 used". That is false against the
instrument: `scripts/gh104_divergence_record.py` keys every row by a 12-hex sha1 of the diff
hunk between the frozen `jca` and `jca_android` (`digest_row`), and `check()` fails twice over —
`unrecorded divergence` for a live hunk with no row, `stale entry` for a row whose hunk no longer
exists. Only `NARRATIVE_KINDS = {set-archived, api30-omits, behavioural}` may carry an empty hunk
key, and 131 of the 134 existing rows carry a digest. A per-file row would therefore fail
`tests/parity/test_gh104_specset_gates.py::test_jca_android_hunks_all_recorded` (INV-INS-118) on
both counts, on the first migrated `.mop`. Decision: this change records **one row per hunk**,
like gh104 did, and treats the recorder as first-class collateral — `KINDS` gains the four
species this change actually produces (`predicate-store`, `placement`, `junction`,
`predicate-removal`), because an unlisted kind makes `check()` report `unknown kind`. The site
count a per-file row would have carried lives in `predicate_graph.csv`, which is keyed for it;
the divergence record answers a different question ("what changed against the seed, and why"),
and conflating the two was what produced the wrong granularity.

**D-12 — The reach probe runs at the front; the smoke test stays at the end (readiness audit,
2026-08-20).** The change declares its own blocking condition: if `UnsatisfiedConstraint` stays
at zero on the production path, the weaver is a prerequisite and this work stops. The plan asked
that question in the last task group, after every wiring edge had landed — which means the
blocking condition could void the wiring groups *after* they were finished. It is split in two.
The **reach probe** runs immediately after the first migrated file and its *not observed* code:
one instrumented APK through `rv-experiment`/`rv-platform` (the platform owns the emulator
lifecycle; no manual emulator command, ever), one question — *does any predicate-derived report
reach `errors.csv`?* One migrated read with a three-valued verdict and a code is sufficient
evidence to answer it, and its verdict gates entry into the wiring groups. The **full smoke
test** stays at the end, where it belongs, carrying what only a wired chain can show: the R4
`equals` probe, the woven `Object`-idiom junction, the junction × `CipherSpec` co-fire counts.
Cost of the split: one extra device run. What it buys: the kill switch fires before the
expensive half of the change instead of after it.

**D-13 — New gates enter CI behind a declared expected-baseline (readiness audit, 2026-08-20).**
The import-discipline gate, G-ACC and the placement gate are written before the edits that make
them green: G-ACC cannot pass until the orphans are absorbed, the placement gate not until the
reads move. Wiring them into `tests/parity/` on arrival would leave the suite red across most of
this change, and a suite that is expected to be red stops being read — `/rv-verify` and every
intermediate checkpoint would be noise. So each new gate is registered against the **baseline
report** its first run commits: the pytest wrapper asserts *no regression against the recorded
baseline*, not *zero findings*, and each spec's row leaves the baseline as its group lands. A
final task deletes the baseline mechanism outright once the gates are green on their own —
it is scaffolding with a demolition date, not a permanent allowance, and it is a different
instrument from `gate_allowlist.csv`, which records findings that are *deliberately* permanent.

**D-14 — Pair evidence has a precondition: the harness must isolate the substrate (readiness
audit, 2026-08-20).** `TraceRunner.replay()` rebuilds a fresh `URLClassLoader` per trace and
resets `ErrorCollector` explicitly — and nothing else. `ExecutionContext` (and any new
`PredicateStore`) sits on `java.class.path`, so parent-first delegation resolves the singleton in
the **parent** loader and its state survives every trace in a directory replay. That is exactly
why `ErrorCollector` needed its own reset line. Untouched, the consequence lands on the one thing
this change uses as evidence: a satisfy trace's `ensure` silently satisfies the violate trace
that follows it, and the INV-INS-144 pair reports a pass it did not earn. `replay()` therefore
resets the predicate substrate beside the error sink, and the reset is proved by a cross-trace
test, not assumed (INV-INS-148). This is why `reset()` exists on the store despite having zero
production callers — the design already said "test-only"; D-14 names the test.

**D-16 — The MetaCrySL oracle is withdrawn entirely; the sole oracle is the pinned expert copy
(researcher, 2026-08-25).** D-15 (2026-08-24) withdrew the api30 anchor for **value clauses**
and kept it for `ORDER`, event alphabets and predicates ("the scope is values only"). That
limitation is superseded: the researcher's decision is that `jca_android` answers to the
expert-validated rules and to nothing generated — a chain that measurably inverted value
semantics (MD5/SHA-1/AES-ECB admitted) does not earn oracle status for any dimension. From this
decision on, the **only** oracle of the set, for every clause kind, is
`RVSec-replication-package/tools/rules/` (49 rules, sha256 `d7bcc019…`, the existing freeze
item). `MetaCrySL/generated/api30/` loses oracle status entirely: it stays on disk as the
historical input the pre-D-16 records were derived against, cited only inside supersession
adenda, and no gate, register, `.mop` comment or emitted message may name it as the
authority for anything.

What this does **not** reopen: (a) platform-limit divergences were justified by measurement on
android-30, never by api30 — protected constructors (CipherStreams), the absent
`javax.xml.crypto` class (HMACParameterSpec), `destroy()` throwing (SecretKey), the `Integer`
cache (SecureRandom autoboxing) — they survive unchanged as records **against the expert
rule**; (b) "no new accusation classes" stands — the 28 expert rules without a `.mop` gain no
specification in this change; (c) the frozen `jca`, the archived `jca_android_bug_predicate`
and the published numbers are untouched.

What it does change, ordered by tasks group 11: the 36-clause predicate ledger was derived from
the 33 api30 rules and must be re-derived from the 49 expert rules — the known deltas, each
verified against the rule text on 2026-08-25: `Mac.crysl:54` REQUIRES `generatedKey[key,_]`
(the read task 4.9 deleted returns, on the new store, in the event body); `SSLContext.crysl:18`
binds `random` in `i1: init(km, tm, random)` and `:34` REQUIRES `randomized[random]` — clause
#30's `vacuous` disposition was an api30 artifact and falls; `TrustManagerFactory.crysl:29`
REQUIRES `generatedManagerFactoryParameters[params]`; `SecureRandom.crysl:46` REQUIRES
`randomized[lSeed]` and `:52` ENSURES `randomized[randInt] after nI`; `KeyPair.crysl:20` orders
`Con, (GetPubl | GetPriv)*` with the constructor **mandatory** and `:27` ENSURES
`generatedKeypair[this,_] after Con`. `order_alphabet_map.csv` and G-ORDER re-anchor on the
expert `EVENTS`/`ORDER`; the gates CLI drops its api30 input; `conformance_record.csv` stops
naming two rules per specification. Where the current set deliberately stays away from the
expert text on measurement — the 9.11 `(c1 | epsilon)` automaton against `KeyPair.crysl:20`'s
mandatory constructor being the named case (668 corpus lines measured: the platform constructs
the pair internally, the app never calls the constructor) — the disposition becomes a
**divergence record against the expert rule**, adjudicated by the researcher, never obedience
to a generated rule. Behavioural consequences (the Mac read, the SSLContext `sr` wiring, ORDER
deltas) go through the 9.B discipline: harness pair, divergence row, researcher go/no-go per
task.

**D-17 — A disposition is re-derived from its reason, not from its conclusion (researcher,
2026-08-26).** Task 11.1 required that "a disposition that only held under api30 is re-derived,
not copied", and the expert ledger it produced carried one disposition whose *conclusion* was
right and whose *reason* had changed class. Ledger clause #34 (`KeyPairGenerator`, `algorithm in
{"DiffieHellman","DH"} => preparedDH[params]`, `KeyPairGenerator.crysl:37`) reads
`unreachable-composition`, on the measurement task 5.8 made: the JCA raises
`InvalidAlgorithmParameterException: Inappropriate parameter type` for
`KeyPairGenerator.getInstance("DH").initialize(new DHGenParameterSpec(2048, 0))`. That
measurement stands. What no longer stands is the sentence it rested on -- *"a DH key pair is
initialised from a `DHParameterSpec`, which no rule ensures"*. It was true of the generated
catalogue, which states no `DHParameterSpec.cryptsl` at all, and it is false of the oracle:
`DHParameterSpec.crysl:21` ENSURES `preparedDH[this]`, and `DHParameterSpec` is precisely the
type `initialize` accepts. The clause's own ledger row already shows it -- its `counterparts`
column reads `DHGenParameterSpec|DHParameterSpec` while `counterparts_with_mop` reads
`DHGenParameterSpec` alone.

So the disposition becomes `unmonitored-producer`, the same as #18 and #19, and the difference
is not cosmetic: `unreachable-composition` says no specification could ever close the clause,
and `unmonitored-producer` says a `.mop` for `DHParameterSpec` would. Nothing is wired either
way -- a read at `KeyPairGeneratorSpec.init3/init4` would still answer `NOT_OBSERVED` for every
conforming DH program, because the producer it uses is unmonitored -- so no `.mop` changes, no
accusation changes class, and no harness pair is owed. What changes is what the record says is
possible.

Clause #38 (`Mac preparedHMAC[params]`, `Mac.crysl:53`) is the control, and it survives verbatim:
its producer is `javax.xml.crypto.dsig.spec.HMACParameterSpec` (`HMACParameterSpec.crysl:14`),
of the `java.xml.crypto` module, and the api30 `android.jar` carries no entry whatever under
`javax/xml/crypto`. That is a fact about the platform and not about a catalogue, so the
substitution of oracle leaves it untouched. The two together are why this decision is stated as
a rule rather than as a correction to one row: **under a substitution of oracle, a disposition
is re-checked against the sentence that justified it, even when the verdict does not move** --
the reason is what a later task acts on, and a reason that has quietly changed class is a wrong
premise waiting to be reused.

Two consequences for the census, both records and neither work: the oracle *adds* a REQUIRES
clause the generated catalogue never stated -- `Cipher.crysl:140`, `mode(transformation) in
{"OAEPWith…"} => preparedOAEP[paramSpec]`, whose only producer `OAEPParameterSpec` has no `.mop`
(`unmonitored-producer`, already in 11.1's delta) -- and six of the predicates the set's own
specifications require have no producer it can observe at all: `preparedRSA` (#19),
`preparedDSA` (#18), `preparedEC` (#20, `unclosable`), `preparedOAEP`, `preparedAlg` (#7) and
`generatedManagerFactoryParameters`. Closing any of them means a specification for a rule the
set does not have, which is a new accusation class, which D-16 keeps out of this change.


## API Design

### `PredicateStore` (Java, `rvsec-core`, package `br.unb.cic.mop`)

```java
public enum PredicateVerdict { SATISFIED, VIOLATED, NOT_OBSERVED }

public final class PredicateStore {
    public static PredicateStore instance();          // holder-idiom singleton, thread-safe

    /** ENSURES: record predicate p for the bound object, plus value positions.
     *  bound is a separate parameter: a plain varargs head would spread a
     *  reference-array argument (KeyManager[], TrustManager[]) into elements. */
    public void ensure(Property p, Object bound, Object... values);

    /** NEGATES: withdraw p for exactly this object (never property-wide). */
    public void negate(Property p, Object bound);

    /** REQUIRES (positive clause): three-valued check. bound identity-matched;
     *  value positions of declared type String/int/Integer matched
     *  case-insensitively (splitters applied by the caller, which holds the
     *  rule's clause). */
    public PredicateVerdict validate(Property p, Object bound, Object... values);

    /** REQUIRES (negated clause, INV-INS-146): inverted table — no entry is
     *  SATISFIED (absence conforms); a same-name entry is VIOLATED (the old
     *  oracle's name-only branch). Never NOT_OBSERVED. */
    public PredicateVerdict validateAbsent(Property p, Object bound, Object... values);

    /** Test-only: clears all state. Production never calls it (measured: reset() had
     *  zero production callers on the old substrate too). */
    public void reset();
}
```

- **Keying**: object binding in a synchronized identity-keyed weak map
  (`WeakHashMap`-with-identity semantics — implementation uses identity boxes over
  `ConcurrentHashMap`, purged via a `ReferenceQueue`); value positions stored as normalized
  strings for tracked types.
- **Preconditions**: `bound` non-null. **Postconditions**: `ensure` is idempotent per
  (p, identity, values); `negate` affects only the named object; `validate`/`validateAbsent`
  never mutate.
- **Not offered** (absence, not removal): `hasEnsuredPredicate`, property-wide `remove`,
  accepting-state bookkeeping — its 25 call sites receive the INV-INS-147 disposition.
  Production has zero readers; the maintained readers (`Assertions.mustBe…InAcceptingState`)
  live in the `rvsec-agent` test corpus, which weaves the frozen `jca` and is untouched. Eleven
  disposable audit drivers under `audit/20260808_validacao_jca_android/` also call
  `isInAcceptingState` (73 sites) — one-shot harnesses against the pre-change set, not
  maintained consumers; they are not updated. Junction monitors carry state where needed.

### Gate CLI contract (Python, `scripts/`)

Each gate script: `uv run python scripts/gh105_<gate>.py --sets all|jca_android [--json]` →
exit 0 iff no failure; report always lists `passed/failed/skipped(reason)`. pytest wrappers in
`tests/parity/test_gh105_predicate_gates.py` under the CI contract
(`--import-mode=importlib -o "addopts="`).

## Data Flow

Write path: woven event fires → `@match`/`after L` handler calls
`PredicateStore.ensure(P, obj, values…)` → store records under identity + normalized values.
Read path: consumer event body calls `validate` → verdict → `SATISFIED`: silence;
`VIOLATED`: `ErrorDescription` four-arg with `UnsatisfiedConstraint` code; `NOT_OBSERVED`:
four-arg with the *not observed* code — all through the gh104 envelope, then
`ErrorCollector` → logcat → `errors.csv`. Junction path: chain events bind overlapping parameter
sets → JavaMOP slices by identity → `@fail` of the junction reports with its own code.
Gate path: `.mop` sources + generated `.rvm`/monitor → analyzers → `predicate_graph.csv` /
verdicts → pytest. Evidence path: every wiring task → trace pair → `TraceRunner` →
`gh104_diff_harness.py` before/after → committed verdicts. The harness's two sides are
**specification-set directories** (`--a`/`--b`), not monitor trees: it regenerates the monitors
itself, so what the baseline task archives is the pre-change `.mop` set, and what task 8.4 diffs
is that directory against the edited one.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| Generation "success" with empty parameter list | JavaMOP silent collapse (rc=0) | G-PARAM reads the `.rvm` header; never trust rc | rewrite with `Object` idiom |
| `Logic Engine Error: null`, exit 0, no monitor | child OOM masked by `LogicRepositoryConnector` | artifact-existence check after every generation; heap recorded (INV-INS-145) | re-run with `-Xmx2g` on the child |
| `StackOverflowError` in `EnableSet.parseSets` | parent parser at n=18 | hard ceiling — alphabet stays ≤ 17 per spec | re-budget alphabet; no flag helps |
| False G-2 reds after store migration | `accept_requires` greps old class | updated in the same task as the first migrated spec (INV-INS-141) | — |
| Spurious junction FAIL on cross-chain instances | missing benign loop | INV-INS-136(b) + pilot fixture trace | add loop, re-run pair |
| Conforming trace accused by junction | consumer declared `creation` | INV-INS-136(a) gate check | restructure spec |
| Read of never-written predicate | wiring order violation | G-PRED2 closure + task discipline (producer+consumer+accuser same task) | wire producer or record `unclosable` |

## Risks / Trade-offs

- **[R1 freeze]** → by construction (D-1) + import gate (INV-INS-130). Residual: G-PRED
  collateral, handled by INV-INS-141.
- **[R2 generator]** → 17 events generate under 1 GB; 18 is a parser ceiling no flag lifts.
  Mitigation: INV-INS-145 discipline; alphabet re-budget only as a performance lever.
- **[R3 instrumentation reach]** → the `NOT_OBSERVED` verdict is the mitigation, and the D-12
  reach probe measures it on a device before the first F3 edge rather than after the last;
  full-scale measurement still rides on the joint experiment.
- **[R4 concrete key `equals`]** → open; device test via `rv-experiment`/`rv-platform` (never a
  manually managed emulator). Affects `GENERATED_KEY`/`GENERATED_PUBLIC_KEY` verdicts only.
- **[R5/R6 silent toolchain]** → artifact inspection everywhere; G-PARAM; stderr byte poisons
  the XML parse (measured) — generation wrappers keep stderr clean.
- **[R7 alphabet mapping]** → versioned `order_alphabet_map.csv`, budgeted as its own F5 task;
  gate skips without a mapping, never infers.
- **[Published magnitudes measured over `jca`]** → every event count quoted from the published
  dataset (12,400 / 9,015 / 6,835 / 39,682) was measured on the `jca` campaign; the `jca_android`
  constraint lists differ in several specs, so these are sizing ceilings, not predictions for the
  target set. The joint experiment re-measures on-target.
- **[Junction memory at scale]** → O(#producers × #consumers) silent monitors on disconnected
  joins; not measured beyond the pilot. Mitigation: weak refs + `TerminatedMonitorCleaner` are
  free in path B; scale measurement lands in the joint experiment.
- **[Junction coexistence with `CipherSpec` at the same joinpoint]** → the pilot chain's
  junction fires on `Cipher.init` — a strict subset of `CipherSpec.i2`'s pointcut. A junction
  `@fail` carries its own spec name, code and event, so its reports never merge with
  `CipherSpec`'s under the gh104 dedup identity (7-field `ErrorSummary`, `bd61abea`) nor under
  the thesis's `(apk, class, method, spec)` unique-misuse key: a junction opens a **new bucket
  at the same `(class, method)` by construction**. This is a measurement disposition, not a
  runtime defect — the ledger routes each clause to exactly one accuser, so a double accusation
  of the *same* clause cannot arise; but the joint experiment MUST count junction reports as
  their own accuser (never fold them into the typestate spec's bucket, never read them as
  duplicates). Task 8.5 observes the co-fire on a real trace and commits the counts — the third
  untested item of the Phase-0 pilot (`docs/20260820_plano_fiacao_predicados.md:1196-1198`).
- **[Two stores in one process]** → the standard sets cannot mix (identical `.mop` filenames —
  one directory cannot hold both), but `--custom-specs-dir` accepts an arbitrary directory that
  could mix files from the two import families. Recorded as an **open risk**, no validation
  added here (P1); INV-INS-09 forbids mixed runs for the named sets.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit (Java) | `PredicateStore`: identity vs equals, tracked-type matching, arity, 3 verdicts, negate scoping, weak purge, thread-safety | JUnit in `rvsec-core` | ~17 |
| Unit (Python) | analyzers/gates: placement classes, orphan directions, alias/shadowing, skip-and-count | pytest fixtures incl. negative (`GCMParameterSpecSpec`, byte[]-collapse spec) | ~20 |
| Trace (per edge) | satisfy + violate pair per wired edge / guard move / orphan / removal (F2-window pairs assert `NOT_OBSERVED`); the replay's substrate reset proved by a cross-trace case (INV-INS-148) | `TraceRunner` + `gh104_diff_harness.py` over specification-set directories, verdicts committed | 2 × 77 (24 F3 edges + 27 F2 moves + 17 F1 orphans (fusions and absorptions) + 8 `@fail` removals + the `PBEKeySpec` translation) ≈ 154 files — a **floor**: the Group-6 closing task adds pairs for the pointwise fixes; the current corpus holds 63 files (~40 %) |
| Gates (CI) | G-ORDER, G-PRED2, G-ACC, G-PARAM, junction rules, import, genericity over the enumerated universe; gh104 gates still green, the recorder included | `tests/parity/` under the CI contract, each new gate reading its expected-baseline until its group lands (D-13) | the 12 pytest functions named in the mapping table |
| Ground truth | C5: `errors_unit_tests.csv` misuse corpus — corrected specs keep accusing planted misuse, stop accusing conforming use | harness replay of `../../ase-journal/dataset/results/errors_unit_tests.csv` (sibling repository, read-only per gh89) | 1 suite |
| Reach probe (device) | does any predicate-derived report reach `errors.csv` at all — the change's blocking condition, asked before any F3 edge (D-12) | one `rv-experiment`/`rv-platform` run over a sample APK instrumented with the first migrated file | 1 run |
| Smoke (device) | R4 `equals` probe + woven `Object`-idiom junction fires on a real trace + junction × `CipherSpec` co-fire counts | one mini `rv-experiment`/`rv-platform` run over a sample APK, end of change | 1 run |

## The 36-Clause Ledger (REQUIRES, api30)

**Superseded as an oracle by D-16 (2026-08-25); kept as the record it was computed on.** This
table was derived from the 33 generated api30 rules. Task 11.1 re-derived it from the 49 expert
rules into `data/jca_android/predicate_ledger.csv`, with the row-by-row account in
`predicate_ledger_delta.csv`; that pair is the live ledger, and the numbering below survives in
it because task ids and clause numbers are keys in committed evidence and are never renumbered.
D-17 (2026-08-26) corrects one disposition the re-derivation had copied -- see row 17.

Re-derived from the oracle and the set on 2026-08-20 (external verification, arbitrated by
re-measurement). **Wireable** = the consuming rule *and* at least one producing rule have a
`.mop` in `jca_android`. Neg = negated clause; Grd = implication guard evaluated in the body.
Every F3/record task resolves against this table, not against family names.

| # | consumer rule | clause | Neg | Grd | wireable? | disposition | task |
|---|---|---|---|---|---|---|---|
| 1 | AlgorithmParameters | `preparedAlg[parAr]` | | | no (neither end) | record `unmonitored-consumer`+`producer` | 5.10 |
| 2 | AlgorithmParameters | `{AES,DESede} => preparedIV[params]` | | G | no (no consumer .mop) | record `unmonitored-consumer` | 5.10 |
| 3 | AlgorithmParameters | `{DiffieHellman} => preparedDH[params]` | | G | no (no consumer .mop) | record `unmonitored-consumer` | 5.10 |
| 4 | CertPathTrustManagerParameters | `generatedCertPathParameters[params]` | | | no (neither end) | record | 5.10 |
| 5 | Cipher | `generatedKey[key, part(0,"/",transformation)]` | | | yes | wire — store, arity 2, splitter by caller | 5.6 |
| 6 | Cipher | `randomized[ranGen]` | | | yes | wire — store (zero CipherSpec events) | 5.5 |
| 7 | Cipher | `preparedAlg[param, part(0,"/",transformation)]` | | | no (no producer .mop) | record `unmonitored-producer` | 5.10 |
| 8 | Cipher | `!macced[_, plainText]` | N | | yes | wire — `validateAbsent` (researcher 2026-08-20); add the `MACED` producer write at Mac's acceptance (zero sites today) | 5.7 |
| 9 | Cipher | `{CBC,…} && encmode==1 => preparedIV[params]` | | G | yes | wire — junction (pilot chain) | 5.1 |
| 10 | Cipher | `{GCM} => preparedGCM[params]` | | G | yes | wire | 5.8 |
| 11 | GCMParameterSpec | `randomized[src]` | | | yes | wire | 5.4 |
| 12 | IvParameterSpec | `randomized[iv]` | | | yes | wire — junction (pilot chain) | 5.1 |
| 13 | KeyGenerator | `randomized[ranGen]` | | | yes | wire (KeyGenerator, **not** KeyPairGenerator) | 5.5 |
| 14 | KeyManagerFactory | `generatedKeyStore[keyStore]` | | | yes | wire | 5.9 |
| 15 | KeyPair | `generatedPrivkey[consPriv]` | | | yes | wire | 5.6 |
| 16 | KeyPair | `generatedPubkey[consPub]` | | | yes | wire | 5.6 |
| 17 | KeyPairGenerator | `{DH} => preparedDH[params]` | | G | wireable, producer unmonitored | record `unmonitored-producer` (D-17, 2026-08-26; was `unreachable-composition`) — the JCA refuses `DHGenParameterSpec` here, and the type it accepts, `DHParameterSpec`, is ensured by `DHParameterSpec.crysl:21` and has no `.mop` | 5.8; 11.9 |
| 18 | KeyPairGenerator | `{DSA} => preparedDSA[params]` | | G | no (no producer .mop) | record `unmonitored-producer` | 5.10 |
| 19 | KeyPairGenerator | `{RSA} => preparedRSA[params]` | | G | no (no producer .mop) | record `unmonitored-producer` | 5.10 |
| 20 | KeyPairGenerator | `{EC} => preparedEC[params]` | | G | non-connectable | record `unclosable` (no producing rule) | 5.8 |
| 21 | Mac | `preparedHMAC[params]` | | | wireable, **not composable** | record `unreachable-composition` — the site exists and no program can reach it (5.2); re-derived unchanged under the oracle at 11.9, the producer class being absent from `android.jar` whatever the catalogue | 5.2; 11.9 |
| 22 | Mac | `!encrypted[output1, _]` | N | | yes | wired — `validateAbsent` at `MacSpec.f2` (api30's `f3`), with the binding repair; the returned half recorded vacuous | 5.3 |
| 23 | Mac | `!encrypted[output2, _]` | N | | yes (vacuous) | record `vacuous` — `output2` is bound only as a returned array, which the JCA allocates fresh | 5.3 |
| 24 | PBEKeySpec | `randomized[salt]` | | | yes | wire | 5.4 |
| 25 | PBEParameterSpec | `randomized[salt]` | | | yes | wire | 5.4 |
| 26 | PKIXBuilderParameters | `generatedKeyStore[keyStore]` | | | no (no consumer .mop) | record `unmonitored-consumer` | 5.10 |
| 27 | PKIXParameters | `generatedKeyStore[keyStore]` | | | no (no consumer .mop) | record `unmonitored-consumer` | 5.10 |
| 28 | SSLContext | `generatedKeyManager[kms]` | | | yes | wire (bound-first API — `kms` is `KeyManager[]`) | 5.9 |
| 29 | SSLContext | `generatedTrustManager[tms]` | | | yes | wire (bound-first API) | 5.9 |
| 30 | SSLContext | `randomized[sr]` | | | yes (vacuous) | record `vacuous` — `Init: init(kms, tms, _)` binds `sr` in no event | 5.5 |
| 31 | SecretKeyFactory | `speccedKey[keySpec, _]` | | | no (no consumer .mop) | record `unmonitored-consumer` (PBEKeySpec and SecretKeySpec are its producers) | 5.10 |
| 32 | SecretKeySpec | `preparedKeyMaterial[keyMaterial]` | | | yes | **wired** — un-conflated from `RANDOMIZED`, producer and consumer in one commit, plus the read the four-argument overload lacked | 5.10+6.1 |
| 33 | SecureRandom | `randomized[seed]` | | | yes | wire (self-chain) | 5.5 |
| 34 | Signature | `generatedPrivkey[priv]` | | | yes | wire (Signature's clauses — not `generatedKey`) | 5.7 |
| 35 | Signature | `generatedPubkey[pub]` | | | yes | wire | 5.7 |
| 36 | TrustManagerFactory | `generatedKeyStore[keyStore]` | | | yes | wire | 5.9 |

Totals: 25 wireable (incl. the 3 negated and the 1 vacuous), 10 non-wireable records,
1 `unclosable` (`preparedEC`). Of the 25 wireable, **21 are wired**; the vacuous #30 is
**recorded**, never wired — no event binds `sr`, so it can have no read site — and tasks 5.2, 5.3
and 5.8 moved three more out of the wired column on measurement (2026-08-22): #23 joins #30 as
`vacuous`, because `output2` is bound only as an array the JCA allocates fresh and
`validateAbsent` never answers `NOT_OBSERVED`, so a read there could answer only `SATISFIED`; and
#21 is a **third kind of record**, which this ledger did not have a column for. Its producer and
its consumer both have a `.mop` in the set — the ledger's own wireability test — and the platform
still refuses the composition: the producing class is absent from the api30 `android.jar`, and on
a JVM no `Mac` of the rule's twelve-algorithm allow-list accepts its type. **Having a `.mop` at
both ends is necessary and not sufficient**, and every remaining task of Group 5 should measure the
composition rather than the two ends. The measurements are in
`data/gh105/evidence/f3-MacChain.md`.
Task 5.8 (2026-08-22) found the third such clause, which is why that rule is now stated as a rule rather
than as an observation about `Mac`. **#17 leaves the wired column for the same record**:
`DHGenParameterSpec` is the only rule of the whole api30 oracle that ENSURES `preparedDH` --
`AlgorithmParameters` requires the predicate and ensures `preparedAlg` instead -- and the JCA will not put
that object into the consuming call. Measured on Temurin 21,
`KeyPairGenerator.getInstance("DH").initialize(new DHGenParameterSpec(2048, 0))` raises
`InvalidAlgorithmParameterException: Inappropriate parameter type`, while the same object into
`AlgorithmParameterGenerator.getInstance("DH").init(...)` -- the consumer the class exists for, and one
with no `.mop` in this set -- runs; a DH key pair is initialised from a `DHParameterSpec`, which no rule
ensures. A read at `KeyPairGeneratorSpec.init3/init4` would therefore answer NOT_OBSERVED for every
conforming DH program, of a preparation the program has no way to obtain. Recorded, not wired (researcher
decision, 2026-08-22), which retires the producer's G-PRED2 line the way #21's did. The measurements are in
`data/gh105/evidence/f3-RandomizedHubAndGuardedPrepared.md`.

Task 5.10 (2026-08-22) wired the last of them, #32, and the ledger owes one correction its
wireability column could not carry. **A clause can be wireable, composable and still change what
the set accuses at scale**, because a predicate the oracle ensures at exactly two events is
narrower than the idiom the corpus was written in. `preparedKeyMaterial` is ENSURED by
`Key.getEncoded()` and `SecretKey.getEncoded()` and by nothing else in the whole of api30, so a
`SecretKeySpec` built from a `SecureRandom`'s output does not satisfy its own REQUIRES, and — the
ENSURES being conditional on the rule holding — it ensures no `generatedKey` either, so every
`Cipher.init` downstream of it is accused too. Measured: 18 of the 128 corpus traces change, 11 of
them through that cascade. Every report is one api30 states, and the three ways of not paying the
cost were measured and declined (evidence: `data/gh105/evidence/f3-PreparedKeyMaterial.md`).
The lesson for the tasks still open is the third face of "necessary and not sufficient": having a
`.mop` at both ends and a program that composes still does not tell you **how much** the wiring
moves — measure the corpus before deciding, not the two ends.

Task 5.11 (2026-08-22) swept the closure and found the totals above had been carrying #17 in the
wired column after task 5.8 recorded it. **The arithmetic that closes is 21 + 14 + 1**: 21 clauses
with a read site, 14 recorded (the 10 `unmonitored-*`, the vacuous #30 and #23, and #17 and #21,
which no conforming program can satisfy a read of), and `preparedEC` `unclosable`. D-17 moves
#17's *reason* from `unreachable-composition` to `unmonitored-producer` and moves none of these
counts: the clause is recorded either way, and what changes is whether the record says a
specification could ever close it. Measured against the tree
rather than against this table: `PREPARED_DH` has one write (`DHGenParameterSpecSpec.mop:37`) and
no read anywhere in the set. The same sweep counts **22** distinct `Property` values written where
the change opened with 21 — task 5.10 renamed a write rather than adding one, and a census of
operations cannot see a rename. Evidence: `data/gh105/evidence/f3-ClosureSweep.md`.

Dead-end `ENSURES`-only predicates are never required by any rule. The oracle has 12; **9 have
their producing rule's `.mop` in the set** and are the ones this change must dispose of:
`preparedPBE`, `generatedSSLContext`, `generatedSSLEngine`, `signed`, `verified`, `digested`,
`generatedKeypair`, `cipheredInputStream`, `cipheredOutputStream` (the other three —
`digestedInputStream`, `digestedOutputStream`, `generatedManagerFactoryParameters` — have no
producing `.mop` and need nothing). Seven of the nine have write sites in the set today —
**seven predicates over eleven sites**, a distinction worth keeping because the relocation pass
moves sites, not predicates (`SignatureSpec.mop:116,124,131,139`;
`MessageDigestSpec.mop:90,104,111`; `SSLContextSpec.mop:73,79`; `PBEParameterSpecSpec.mop:62`;
`KeyPairGeneratorSpec.mop:111`); each of the eleven is placed at the acceptance point by the F2
write-relocation pass and carries a deliberate-omission record for its absent reader
(INV-INS-137); no read is fabricated
for any of them, and no write is fabricated for the two stream predicates that have none.

## The 17-Orphan Census (F1)

`IvParameterSpec{c3,c4}` · `KeyPairGeneratorSpec{initError}` · `PBEKeySpecSpec{f1,f2,err1,err2,err3}`
· `PBEParameterSpecSpec{c3}` · `SSLContextSpec{unsafe_protocol}` · `SecretKeySpecSpec{c3,c4}` ·
`SecureRandomSpec{c3,g4,setSeed3}` · `SignatureSpec{g3}` · `TrustManagerFactorySpec{g3}`.
**What separates a fusion from an absorption is the orphan's own body, not the shape of its
guard.** An orphan whose body carries an accusation of its own — an algorithm the CONSTRAINTS
reject, a key size the rule bounds, a constructor it forbids — is a report the set would lose if
the event went away, so it is **absorbed**: it enters the automaton with benign self-loops and
keeps accusing. An orphan whose body only rebinds a monitor field accuses nothing of its own;
whatever it appears to detect is emitted somewhere else, and the single report it does produce is
the spurious `InvalidSequenceOfMethodCalls` the generator hands every event absent from the
automaton. That one is a **negated twin** and is fused into its sibling, per INV-INS-135.

Twin fusions (identical `call`/`args`, condition differing only in polarity — INV-INS-135):
`IvParameterSpec.c3→c1`, `c4→c2` (c4 is not an
exact complement — it ignores c2's offset/length constraints), `SecureRandomSpec.c3→c2` (c3
accuses nothing today — body only rebinds), `setSeed3→setSeed2`, `SecretKeySpecSpec.c3→c1`,
`c4→c2` (length complement), `PBEParameterSpecSpec.c3→c1` (2-arg twin; the 3-arg `c2` read stays
accuser-less until that file's F2 pass), `PBEKeySpecSpec.err2/err3→c1` (one arrow, two orphans),
`TrustManagerFactorySpec.g3→g1`, `SignatureSpec.g3→g1`, `SSLContextSpec.unsafe_protocol→g1`.
That is 11 arrows fusing **12 twin orphans**. `PBEKeySpecSpec.err1` is the **thirteenth fused
orphan**: it rides
the same `c1` fusion, its iteration-count check decomposed per clause — the three overlap (one
bad call fires up to three accusers today; the fusion decomposes per clause, one report each).
Plain absorptions — the remaining **4**, each one an accusation of its own:
`KeyPairGeneratorSpec.initError` (`InvalidKeySize`), `SecureRandomSpec.g4` (`UnsafeAlgorithm`),
`PBEKeySpecSpec.f1` and `f2` (`ForbiddenMethod`). Partition: 12 twins + `err1` + 4
absorptions = 17.

**Refinement of 2026-08-21, ratified by the researcher at the start of task 3.6.** Absorption has
two forms, and which one applies is decided by the rule, not by taste: where the ORDER has no
symbol for the call the orphan matches, the event self-loops and its mapping row is ORDER-unmapped
(`g4`, `f1`, `f2` — the rule turns those calls down rather than sequencing them); where the ORDER
*does* name the call, the event enters at that position and its row is `mapped` to the same symbol
as its sibling. `initError` is the second kind: it matches `initialize(int)`, which api30 states as
`i3: initialize(keySize)`, and the size bound is a CONSTRAINTS clause, so the size may no more
govern the transition than the algorithm may in the three `getInstance` fusions above. Absorbing it
as a self-loop was measured and rejected: a loop does not satisfy the `Inits` the following `gen`
needs, so `getInstance("RSA"); initialize(3072); generateKeyPair()` would have kept drawing a
KEYPAIRGENERATOR-ORDER-00 on top of its KEYPAIRGENERATOR-KEYSIZE-00, about an ordering the rule
accepts. As an `Inits` alternative the same trace goes 2 reports → 1
(`data/gh105/evidence/harness/f1-KeyPairGeneratorSpec.md`). The partition is unchanged: the event
is still absorbed, still keeps its own accusation, and is still one of the 4.

**Correction of 2026-08-20, ratified by the researcher at the start of task 3.2.** The three
`getInstance` accusers — `TrustManagerFactorySpec.g3`, `SignatureSpec.g3`,
`SSLContextSpec.unsafe_protocol` — were listed here as plain absorptions until the 3.2 file pass
read their bodies: each only assigns `currentAlgorithmInstance` or `currentProtocol`, and each is
the polarity-negated twin of its file's `g1` over the same
`call(getInstance(String)) && args(...)`. Three independent oracles agree they are fusions. The
api30 rules order `Gets, Init, …` with `Gets := g1 | g2` and put the algorithm in CONSTRAINTS, so
the algorithm must not govern a transition. INV-INS-135's own definition of a negated twin
matches all three literally. And the differential harness measured the fusion against the
pre-change set: on `TrustManagerFactorySpec-sunx509.txt` the pre-image emits
`TRUSTMANAGERFACTORY-ORDER-00` **twice** — once at `g3`, once at the `init` that follows it — and
accuses the algorithm **not at all**, because `g3`'s `__RESET` leaves the monitor at `start`,
where `init` is not declared, and the failing transition takes the `@fail` path instead of the
event body that carries the check. After the fusion the same trace produces exactly one report,
`TRUSTMANAGERFACTORY-ALG-00 val='SunX509' exp='PKIX'`. The orphan was therefore not merely adding
noise to a finding: it was **suppressing** the finding. (`SunX509` is the algorithm that still
reaches the orphan in `jca_android` — the corpus's older `-x509` trace no longer does, because
gh104's alias table resolves `X509` to `PKIX`, `alias_table.csv:2` / OpenSSLProvider.java:90.)
Absorption was never needed to preserve a report, because `g3` carried none of its own.

**The residue the fusion leaves is recorded, not repaired.** After fusion, a `getInstance` whose
algorithm the rule rejects and which is never followed by an `init` is accused by nothing: today
it draws the spurious ordering report, and the real accusation lives in the `init` body. Moving
the algorithm check up into the fused `g1` would close that hole, but it creates an accusation
where none exists today and would need deduplication against the `init` one — a behavioural
change, not a structural repair. Decision (researcher, 2026-08-20): each of the three tasks
records the residue as a `divergence_record.csv` row and leaves the check where it is. It is
measured, not asserted: `TrustManagerFactorySpec-sunx509-no-init.txt` classifies `removed` — the
pre-image's one spurious `TRUSTMANAGERFACTORY-ORDER-00` at `g3` becomes silence.

## Open Questions

1. **R4** — do `OpenSSLRSAPublicKey`/`BCRSAPublicKey` override `equals` by value? Device-only;
   changes the identity-vs-value analysis for `GENERATED_KEY` reads. Open until measured; does
   not block F0–F2. **Measurement path**: the Group 8 device smoke test (task 8.5) probes it in
   a mini run before the joint experiment.
2. **End-to-end weaving of the `Object` idiom** — the pilot validated through the generated
   monitor; open until the woven path runs. **Measurement path**: the same smoke test (task 8.5)
   weaves the junction spec over a sample APK through the dexlib2 host path — one run answers
   both this and R4 ahead of the joint experiment.

**Disposed by the readiness audit (2026-08-20)**: the divergence-record granularity (D-11), the
position of the reach probe (D-12), the CI baseline for gates written before their edits (D-13),
the harness's substrate isolation (D-14, INV-INS-148), the gating of junction rules (a)(b)(d)
(D-6), and the static-oracle asymmetry raised as gpt5 F-04 (D-4, recorded as a deliberate
strengthening).

**Decided by the researcher (2026-08-20)**:
- The three negated clauses are **wired** via `validateAbsent` (former OQ5 → tasks 5.3/5.7).
- The `@Deprecated` removal is **ratified** (former OQ6 → D-1); `ExecutionContext.java` is
  zero-diff.
- The scope is a **single change**, F0–F5 (D-9 ratified).
- **No upstream javamop/rv-monitor patch**, now or later as part of this line of work: the
  `Object` idiom bypasses the collapse entirely and G-PARAM guards the gap; the root cause
  stays recorded in D-10 as documentation only.
- **The article is not touched.** The corrected numbers (39,682 = 56.1 % orphan ceiling, the
  venn readings) exist for the **next experiments**, not for a revision of the published text.

Resolved, not open: gh104's Group 10 has no ordering question — the joint experiment
(`experimento-gh104/`) validates **both** changes at once, after both land, so its 10.1
checkpoint reads the 2.7-rewritten pytest (INV-INS-141) and 10.5 measures the specs in their
post-gh105 state; that is the intended final contract, recorded here so the checkpoint
expectations are read against it.
