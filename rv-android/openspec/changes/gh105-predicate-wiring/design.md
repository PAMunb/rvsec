# Design: gh105-predicate-wiring

**GitHub Issue**: #105 · **Predecessor**: gh104 D-11 · **Phase 0**:
`docs/20260820_plano_fiacao_predicados.md` (audited twice; every load-bearing claim carries
`[auditado]`/`[auditado-v2]` marks and reproducible evidence in
`audit/20260820_verificacao_plano_predicados_v2/`). External verification 2026-08-20
(`docs/analise_gh105_{claude,gemini,gpt5}.md`): adopted findings re-verified against primary
sources before amendment.

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
jca_android .mop (23 files)───────────────┐
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
  all generic over the 214 .mop (skip-and-count contract)
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
| `scripts/gh105_predicate_graph.py` (new) | Structural `.mop` analyzer → `predicate_graph.csv`; placement + G-PRED2 closure | 214 `.mop` | CSV + gate verdicts |
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
| INV-INS-136 (junction rules) | junction `.mop` files F3 | pilot-derived TraceRunner pairs + G-PARAM |
| INV-INS-137 (graph closure) | `predicate_graph.csv` + G-PRED2 | `test_inv_ins_137_gpred2` (incl. zero-rows-green over `generic`) |
| INV-INS-138 (G-ORDER + mapping) | `gh105_order_gate.py` + `order_alphabet_map.csv` | `test_inv_ins_138_gorder` (SecureRandom `Ends*` case) |
| INV-INS-139 (G-PARAM) | `gh105_param_gate.py` | `test_inv_ins_139_gparam` (byte[]/char[] collapse fixtures) |
| INV-INS-140 (genericity) | skip-and-count in every gate | `test_inv_ins_140_genericity_214` |
| INV-INS-141 (G-PRED rescoping) | `gh104_gates.py` edits + pytest rewrite; `divergence_record.csv` rows | `test_gpred_jca_lock_only` |
| INV-INS-142 (`remove()` semantics) | F4 `.mop` edits (8 removals out; `PBEKeySpecSpec` on new store) | harness deltas per removal |
| INV-INS-143 (*not observed* code) | `codes.csv` + envelope emission in `.mop` bodies | `gh104_message_gate.py` extension |
| INV-INS-144 (trace pair per edge) | `data/gh104/traces/` additions + harness runs | committed evidence per task |
| INV-INS-145 (Cipher generation + heap) | task discipline; real-pipeline generation; zero CipherSpec alphabet growth | recorded heap in task evidence |
| INV-INS-146 (negated-clause polarity) | `validateAbsent` entry point; polarity column in graph | JUnit polarity cases + `test_inv_ins_146_negated_polarity` |
| INV-INS-147 (accepting-state disposition) | per-file migration removes the 25 calls; divergence rows | harness deltas + divergence_record.csv counts |

## Goals / Non-Goals

**Goals**: the 36 `REQUIRES` clauses resolved per the ledger — 25 wired, 10 recorded
(`unmonitored-consumer`/`unmonitored-producer`), `preparedEC` `unclosable`; zero
orphan accusers; zero guard reads; three-valued verdicts reaching the envelope; the freeze safe
by construction; a gate layer that holds all of it over the full 214-file universe.

**Non-Goals**: repairing `jca` or the archived set; editing MetaCrySL; the weaver (if
`UnsatisfiedConstraint` stays at zero on the production path, this change is **blocked** and the
weaver becomes a prerequisite — the task 8.5 smoke test is the first place this shows); the
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
clauses; at most one of our removals corresponds (`PBEKeySpecSpec.mop:74`, `clearPassword`).
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

**D-5 — G-PRED rescoped, not deleted.** It stays as the `jca` lock; for `jca_android` it is
retired and replaced by G-PRED2 over `predicate_graph.csv`. Collateral updated in the same task:
`accept_requires` (G-2 would emit false reds), `PREDICATE_CALL` regex (blind to the new store),
the INV-INS-128 pytest, `gh104_message_gate.py::_clause_family` (classifies an orphan's clause
family from `condition(...)` text, which F2 empties), `experimento-gh104/scripts/preflight.py::
check_no_predicates` (a second gate also named G-PRED, still asserting the withdrawn
zero-predicates polarity — retired/renamed), and the `err2`/`c3` rows of
`data/jca_android/gate_allowlist.csv` (justified by condition reads F1/F2 change). Divergence policy: one `divergence_record.csv` row per migrated file
carrying its site count — not one row per line — matching the granularity gh104 used for
mechanical per-file hunks.

**D-6 — Junction design rules are enforced, each by its own instrument.** (a) consumer never
`creation`; (b) benign self-loops for disconnected joins; (c) `Object` idiom + fixed overload
for primitive arrays; (d) monitor fields for handler state. Each rule exists because the pilot
measured its violation: (a) accused the conforming trace; (b) produced spurious cross-chain
fails; (c) is the silent-collapse contour; (d) is a compile-time visibility fact. Only (c) has a
structural gate (G-PARAM); (a), (b) and (d) are enforced by mandatory pilot-derived negative
fixture traces per chain (the trace pair of INV-INS-144 includes the rule-violating fixture) —
per-chain review, not a gate.

**D-7 — Gates are generic by contract (skip-and-count).** The seven measured gaps of plan §8-bis
define the contract; `generic`'s 118 files (82 % multi-parameter, 11 non-compiling) and
`generic_new`'s 17 event-only files are the standing test bed. A gate that cannot classify a
file skips it, counts it, and says why — never green by vacuity, red by absence, or crash.

**D-8 — Order of work: substrate and gates first, then automata, then guards, then edges.**
F0 (store) and the gate skeletons come first because every later task closes against them; F1
(orphans) is independent of the mechanism decision and lands early for its measured payoff
(≤ 56.1 % of the published ISoMC category, a ceiling); F2 (guard moves) before F3 because every
F3 consumer read presupposes body placement — and the F2→F3 window is declared: until a read's
producer lands in F3, the read evaluates to `NOT_OBSERVED` on every trace, so F2 trace pairs
assert `NOT_OBSERVED` (the satisfy side is impossible inside the window) and the
`SATISFIED`/`VIOLATED` pairs of INV-INS-144 land per chain in F3;
F3 wires topologically (the `randomized` hub first as the pilot's chain, then `generatedKey`,
then `prepared*` closing `Cipher`, then the TLS chain); F4 pointwise fixes ride alongside; F5
gates harden continuously, not at the end.

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
  accepting-state bookkeeping — its 25 call sites receive the INV-INS-147 disposition; the only
  readers (`Assertions.mustBe…InAcceptingState`) live in the `rvsec-agent` test corpus, which
  weaves the frozen `jca` and is untouched; junction monitors carry state where needed.

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
`gh104_diff_harness.py` before/after → committed verdicts.

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
- **[R3 instrumentation reach]** → the `NOT_OBSERVED` verdict is the mitigation; device
  measurement before accepting F3 conclusions rides on the joint experiment.
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
- **[Two stores in one process]** → the standard sets cannot mix (identical `.mop` filenames —
  one directory cannot hold both), but `--custom-specs-dir` accepts an arbitrary directory that
  could mix files from the two import families. Recorded as an **open risk**, no validation
  added here (P1); INV-INS-09 forbids mixed runs for the named sets.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit (Java) | `PredicateStore`: identity vs equals, tracked-type matching, arity, 3 verdicts, negate scoping, weak purge, thread-safety | JUnit in `rvsec-core` | ~15 |
| Unit (Python) | analyzers/gates: placement classes, orphan directions, alias/shadowing, skip-and-count | pytest fixtures incl. negative (`GCMParameterSpecSpec`, byte[]-collapse spec) | ~20 |
| Trace (per edge) | satisfy + violate pair per wired edge / orphan / removal (F2-window pairs assert `NOT_OBSERVED`) | `TraceRunner` + `gh104_diff_harness.py`, verdicts committed | 2 × ~25 wired edges + F1/F4 |
| Gates (CI) | G-ORDER, G-PRED2, G-ACC, G-PARAM, import, genericity over 214; gh104 gates still green | `tests/parity/` under the CI contract | 7 gate tests |
| Ground truth | C5: `errors_unit_tests.csv` misuse corpus — corrected specs keep accusing planted misuse, stop accusing conforming use | harness replay | 1 suite |
| Smoke (device) | R4 `equals` probe + woven `Object`-idiom junction fires on a real trace | one mini `rv-experiment`/`rv-platform` run over a sample APK (task 8.5) | 1 run |

## The 36-Clause Ledger (REQUIRES, api30)

Re-derived from the oracle and the set on 2026-08-20 (external verification, arbitrated by
re-measurement). **Wireable** = the consuming rule *and* at least one producing rule have a
`.mop` in `jca_android`. Neg = negated clause; Grd = implication guard evaluated in the body.
Every F3/record task resolves against this table, not against family names.

| # | consumer rule | clause | Neg | Grd | wireable? | disposition | task |
|---|---|---|---|---|---|---|---|
| 1 | AlgorithmParameters | `preparedAlg[parAr]` | | | no (neither end) | record `unmonitored-consumer`+`producer` | 5.7 |
| 2 | AlgorithmParameters | `{AES,DESede} => preparedIV[params]` | | G | no (no consumer .mop) | record `unmonitored-consumer` | 5.7 |
| 3 | AlgorithmParameters | `{DiffieHellman} => preparedDH[params]` | | G | no (no consumer .mop) | record `unmonitored-consumer` | 5.7 |
| 4 | CertPathTrustManagerParameters | `generatedCertPathParameters[params]` | | | no (neither end) | record | 5.7 |
| 5 | Cipher | `generatedKey[key, part(0,"/",transformation)]` | | | yes | wire — store, arity 2, splitter by caller | 5.4 |
| 6 | Cipher | `randomized[ranGen]` | | | yes | wire — store (zero CipherSpec events) | 5.3 |
| 7 | Cipher | `preparedAlg[param, part(0,"/",transformation)]` | | | no (no producer .mop) | record `unmonitored-producer` | 5.7 |
| 8 | Cipher | `!macced[_, plainText]` | N | | yes | wire — `validateAbsent` (researcher 2026-08-20); add the `MACED` producer write at Mac's acceptance (zero sites today) | 5.4 |
| 9 | Cipher | `{CBC,…} && encmode==1 => preparedIV[params]` | | G | yes | wire — junction (pilot chain) | 5.1 |
| 10 | Cipher | `{GCM} => preparedGCM[params]` | | G | yes | wire | 5.5 |
| 11 | GCMParameterSpec | `randomized[src]` | | | yes | wire | 5.3 |
| 12 | IvParameterSpec | `randomized[iv]` | | | yes | wire — junction (pilot chain) | 5.1 |
| 13 | KeyGenerator | `randomized[ranGen]` | | | yes | wire (KeyGenerator, **not** KeyPairGenerator) | 5.3 |
| 14 | KeyManagerFactory | `generatedKeyStore[keyStore]` | | | yes | wire | 5.6 |
| 15 | KeyPair | `generatedPrivkey[consPriv]` | | | yes | wire | 5.4 |
| 16 | KeyPair | `generatedPubkey[consPub]` | | | yes | wire | 5.4 |
| 17 | KeyPairGenerator | `{DH} => preparedDH[params]` | | G | yes | wire | 5.5 |
| 18 | KeyPairGenerator | `{DSA} => preparedDSA[params]` | | G | no (no producer .mop) | record `unmonitored-producer` | 5.7 |
| 19 | KeyPairGenerator | `{RSA} => preparedRSA[params]` | | G | no (no producer .mop) | record `unmonitored-producer` | 5.7 |
| 20 | KeyPairGenerator | `{EC} => preparedEC[params]` | | G | non-connectable | record `unclosable` (no producing rule) | 5.5 |
| 21 | Mac | `preparedHMAC[params]` | | | yes | wire (Mac's clause — Mac does not require `generatedKey`) | 5.2 |
| 22 | Mac | `!encrypted[output1, _]` | N | | yes | wire — `validateAbsent` (researcher 2026-08-20) | 5.2 |
| 23 | Mac | `!encrypted[output2, _]` | N | | yes | wire — `validateAbsent` (two sites, one predicate) | 5.2 |
| 24 | PBEKeySpec | `randomized[salt]` | | | yes | wire | 5.3 |
| 25 | PBEParameterSpec | `randomized[salt]` | | | yes | wire | 5.3 |
| 26 | PKIXBuilderParameters | `generatedKeyStore[keyStore]` | | | no (no consumer .mop) | record `unmonitored-consumer` | 5.7 |
| 27 | PKIXParameters | `generatedKeyStore[keyStore]` | | | no (no consumer .mop) | record `unmonitored-consumer` | 5.7 |
| 28 | SSLContext | `generatedKeyManager[kms]` | | | yes | wire (bound-first API — `kms` is `KeyManager[]`) | 5.6 |
| 29 | SSLContext | `generatedTrustManager[tms]` | | | yes | wire (bound-first API) | 5.6 |
| 30 | SSLContext | `randomized[sr]` | | | yes (vacuous) | record `vacuous` — `Init: init(kms, tms, _)` binds `sr` in no event | 5.3 |
| 31 | SecretKeyFactory | `speccedKey[keySpec, _]` | | | no (no consumer .mop) | record `unmonitored-consumer` (PBEKeySpec is its producer) | 5.7 |
| 32 | SecretKeySpec | `preparedKeyMaterial[keyMaterial]` | | | yes | wire — un-conflate from `RANDOMIZED` with 6.1, same commit | 5.7+6.1 |
| 33 | SecureRandom | `randomized[seed]` | | | yes | wire (self-chain) | 5.3 |
| 34 | Signature | `generatedPrivkey[priv]` | | | yes | wire (Signature's clauses — not `generatedKey`) | 5.4 |
| 35 | Signature | `generatedPubkey[pub]` | | | yes | wire | 5.4 |
| 36 | TrustManagerFactory | `generatedKeyStore[keyStore]` | | | yes | wire | 5.6 |

Totals: 25 wireable (incl. the 3 negated and the 1 vacuous), 10 non-wireable records,
1 `unclosable` (`preparedEC`). Dead-end `ENSURES`-only predicates (`preparedPBE`,
`generatedSSLContext`) are never required by any rule: their writes stay at the acceptance
point with a deliberate-omission record; no read is fabricated for them.

## The 17-Orphan Census (F1)

`IvParameterSpec{c3,c4}` · `KeyPairGeneratorSpec{initError}` · `PBEKeySpecSpec{f1,f2,err1,err2,err3}`
· `PBEParameterSpecSpec{c3}` · `SSLContextSpec{unsafe_protocol}` · `SecretKeySpecSpec{c3,c4}` ·
`SecureRandomSpec{c3,g4,setSeed3}` · `SignatureSpec{g3}` · `TrustManagerFactorySpec{g3}`.
Twin fusions (identical pointcut, INV-INS-135): `IvParameterSpec.c3→c1`, `c4→c2` (c4 is not an
exact complement — it ignores c2's offset/length constraints), `SecureRandomSpec.c3→c2` (c3
accuses nothing today — body only rebinds), `setSeed3→setSeed2`, `SecretKeySpecSpec.c3→c1`,
`c4→c2` (length complement), `PBEParameterSpecSpec.c3→c1` (2-arg twin; the 3-arg `c2` read stays
accuser-less until 4.3), `PBEKeySpecSpec.err2/err3→c1` (with `err1`; the three overlap — one bad
call fires up to three accusers today; the fusion decomposes per clause). Plain absorptions:
`KeyPairGeneratorSpec.initError`, `SSLContextSpec.unsafe_protocol`, `SecureRandomSpec.g4`,
`SignatureSpec.g3`, `TrustManagerFactorySpec.g3`, `PBEKeySpecSpec.f1/f2`.

## Open Questions

1. **R4** — do `OpenSSLRSAPublicKey`/`BCRSAPublicKey` override `equals` by value? Device-only;
   changes the identity-vs-value analysis for `GENERATED_KEY` reads. Open until measured; does
   not block F0–F2. **Measurement path**: the Group 8 device smoke test (task 8.5) probes it in
   a mini run before the joint experiment.
2. **End-to-end weaving of the `Object` idiom** — the pilot validated through the generated
   monitor; open until the woven path runs. **Measurement path**: the same smoke test (task 8.5)
   weaves the junction spec over a sample APK through the dexlib2 host path — one run answers
   both this and R4 ahead of the joint experiment.

**Decided by the researcher (2026-08-20)**:
- The three negated clauses are **wired** via `validateAbsent` (former OQ5 → tasks 5.2/5.4).
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
checkpoint reads the 2.5-rewritten pytest (INV-INS-141) and 10.5 measures the specs in their
post-gh105 state; that is the intended final contract, recorded here so the checkpoint
expectations are read against it.
