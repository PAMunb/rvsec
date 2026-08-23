## Purpose

A CrySL rule states its cross-object obligations in three clauses: `ENSURES` (what a conforming
sequence establishes about an object), `REQUIRES` (what a consumer demands was established), and
`NEGATES` (what a later event withdraws). The `jca_android` set carries the machinery for this —
134 `ExecutionContext` lines preserved byte-for-byte from the frozen `jca` under gh104's G-PRED —
but the machinery is not wired: against the 33 api30 rules there are 19 connectable predicates
(35 connectable `REQUIRES` clauses, of which 25 have both ends monitored in the set), and the set
realizes 3 — three predicate links with both ends live, not 3 of the 35 clauses. Eighteen of the 21 written `Property`
values (35 of 49 write sites) have no reader anywhere — and the gap is bidirectional:
`GENERATED_PRIVATE_KEY` is read (`CipherSpec.mop:85`) and written nowhere in the set, its
intended write existing only as the private-key-as-public defect F4 repairs; the whole
`PREPARED_*` family is dead, so
the misuse class the rules most directly describe — a static IV, a reused GCM parameter — is a
false negative by construction.

Where the wiring does exist, its form makes reports wrong rather than merely incomplete. All 27
predicate reads sit inside `condition(...)`, which compiles to an early `return false` before the
transition: a `Cipher.init` whose key the monitor did not see generated disappears from the
automaton, and the next call is accused of `InvalidSequenceOfMethodCalls` — the developer looks
for a missing call that does not exist, when the truth was "we did not model this key's origin".
Seventeen events are declared outside their `fsm`/`ere` blocks, so the generator gives each an
all-`fail` transition row and they accuse unconditionally; measured on the published dataset,
the orphan family sustains at most 39,682 events = 56.1 % of the `InvalidSequenceOfMethodCalls`
category — a ceiling measured over the `jca` campaign, not a causal attribution (the frozen
`jca`'s ten-spec orphan family sums 49,817 = 70.4 %, but `MessageDigestSpec`'s 10,135-event
orphan exists only there).
Eight of the nine `remove()` sites sit in `@fail` and implement "undo the predicate when the
automaton fails", a semantics that exists in no generation of CrySL; four of them use the
`@Deprecated` overload that erases the property for every object in the process.

The substrate cannot host a correct wiring. `ExecutionContext` keys by `equals()` while the
monitors index by identity (`System.identityHashCode` + `==`), projects every clause to arity 1
when 31 of the 90 clauses need arity ≥ 2, returns a boolean `validate()` that conflates *violated*
with *not observed*, holds strong references it never purges, and synchronizes nothing. The oracle
itself compares by value only in positions whose declared type is `String`/`int`/`Integer`
(`trackedTypes`, `AnalysisSeedWithSpecification.java`), case-insensitively and with splitters
(`alg()`, `part(0,"/",t)`); every other position — the whole `byte[]` family — degenerates to
name-only matching. The correct model is therefore hybrid: identity on the object binding, tracked
-type value comparison on the value positions.

This delta wires the predicates on a substrate that can carry them, without touching the frozen
one. New store classes in `rvsec-core` serve `jca_android` alone; `ExecutionContext` stays
byte-identical — zero edits, not even an annotation — and keeps serving the frozen `jca`: the
freeze is protected by construction, not by vigilance, closing the path that failed once before
(`233df18a`, reverted `e204e2a4`, because the freeze gate checks `.mop` files, not the classes
they call). Where a predicate edge is a co-observable call chain, the wiring uses JavaMOP's own
parametric indexing — a junction specification per chain — so identity is guaranteed by the same
`CachedWeakReference` mechanism the monitors already use, with weak references, purge and
synchronization for free; the executed IV-chain pilot
(`audit/20260820_verificacao_plano_predicados_v2/agentI/`) validated this on the hard case and
produced the design rules this delta encodes, including the one the toolchain hides: an array of
primitive type in a specification's parameter list makes JavaMOP delete the entire list and emit
a global, unparameterized monitor with exit code 0 and the normal success message. The viable
idiom declares `Object` and fixes the overload in the `call(...)` signature; a new gate, G-PARAM,
asserts that the parameter list of every `.mop` survives intact into its `.rvm`, because in this
toolchain silence looks like success.

Verdicts become three-valued. A `REQUIRES` may only accuse when the monitor has evidence it would
have seen the corresponding `ENSURES`; absent that evidence the verdict is *not observed*, not
*violated* — the distinction reaches the gh104 envelope with its own code so downstream analysis
can separate instrumentation-reach artifacts from real violations. Reads move to event bodies
(a violated `REQUIRES` accuses itself, with `UnsatisfiedConstraint` and its code); `condition(...)`
may not contain a predicate read — overload discrimination, `ORDER` branching and `CONSTRAINTS`
checks remain legitimate guards — reflecting CrySL's own orthogonality: violating a `REQUIRES`
does not change the typestate. The oracle's clause forms are all carried: the 8 guarded clauses
(6 of the form `alg in {…} =>`; Cipher's two use `part(1,"/",transformation) in {…} =>`, one of
them also guarded by `&& encmode == 1`) evaluate their guard in the body before the read, and the 3 negated
clauses (`Cipher: !macced[_, plainText]`; `Mac: !encrypted[output1, _]`, `!encrypted[output2, _]`)
invert the three-valued table — absence satisfies (INV-INS-146).

The gate layer grows to hold the wiring honest, and it is generic by contract: the gates run over
every `.mop` of the five sets, a universe they enumerate rather than assume (214 files before
this change edits the tree; 214 plus the junction specifications it adds) — including the 17 event-only specifications of `generic_new`
that declare no automaton at all, the 12 `generic` files that do not compile (11
duplicate-parameter files plus the `FSM358.mop` import collision), and the two archived
files whose `ere` names an event that was never declared — skipping declaredly what does not
apply and counting what they skipped. gh104's G-PRED, which asserted byte-identity of the
predicate machinery, is retired for `jca_android` (it stays as the lock of the frozen `jca`) and
replaced by the closure gates over a versioned predicate graph. The `rvsec-mop-defsuses` module,
whose 2023 idea this closure realizes and whose implementation discards the object argument, the
negated reads, and the automaton, is retired to `backup/` and removed from the reactor.

## Data Contracts

### Input
- `workspace-rv/MetaCrySL/generated/api30/<Class>.cryptsl` — the 33 generated rules; the oracle
  for every predicate edge, read-only (defects become `data/jca_android/divergence_record.csv`
  rows). The MetaCrySL tree is its own git repository, sibling of `rvsec/` — the path resolves
  from `workspace-rv/`, not from either tree; `scripts/gh101_conformance_check.py:50` carries
  the precedent absolute default.
- `rvsec/rvsec-mop/src/main/resources/{jca,jca_android,jca_android_bug_predicate,generic,generic_new}/*.mop`
  — the specifications the gates run over, 214 of them before this change adds its junction
  specifications to `jca_android`; only `jca_android` is edited.
- `data/jca_android/{constraint_table.csv,alias_table.csv,divergence_record.csv,gate_allowlist.csv}`
  — the gh104 records the gates keep reading.
- `results/<run>/monitors/MultiSpec_1RuntimeMonitor.java` and the generated `.rvm` — the artifacts
  the structural gates and G-PARAM inspect; never the generator's exit code.
- `data/gh104/traces/` and `scripts/gh104_diff_harness.py` — the differential harness every wiring
  task answers to.

### Output
- `data/jca_android/predicate_graph.csv` — one row per predicate site, 15 columns: file, event,
  site kind (`condition`/`body`/`@match`/`@fail`), polarity, guard (the guard expression of a
  guarded clause, empty otherwise — INV-INS-133), arity, predicate, position types, splitter,
  CrySL clause (rule file and line), mechanism (A store / B junction, per chain — D-2), verdict,
  disposition (`wired`/`propagation`/`unmonitored-consumer`/`unmonitored-producer`/
  `unclosable`/`vacuous`/`omission` — INV-INS-137), reason (the recorded reason of a write kept
  off the acceptance point or of a deliberate omission, empty otherwise — INV-INS-134), and
  automaton membership. Zero rows over a predicate-free set is the correct, green result.
- `data/jca_android/order_alphabet_map.csv` — the versioned event-alphabet mapping G-ORDER
  consumes: one row per (`.mop` event → `ORDER` event) association, per specification.
- `rvsec/rvsec-mop/src/main/resources/jca_android/codes.csv` — extended with one code per new
  accuser and the *not observed* code family.
- Gate reports (pytest): G-ORDER, G-PRED2, G-ACC, G-PARAM, import discipline — each with
  `passed`/`failed`/`skipped` counts, skips named with reasons.
- Harness evidence per wired edge: before/after per-trace verdicts, committed.

### Side-Effects
- **[Java]**: new store classes under `rvsec/rvsec-core/src/main/java/br/unb/cic/mop/`
  (`jca_android` predicate store and its result type); `ExecutionContext.java` untouched — zero
  edits; `Property.java` gains constants append-only (never removed/renamed/reordered — measured
  safe: zero `ordinal()`/`values()` uses in the tree); JUnit tests for the store in `rvsec-core`.
- **[Filesystem]**: `rvsec/rvsec-mop-defsuses/` moved to `backup/` (rv-android tree; note the
  tracked state of `backup/` is what it is — the move is recorded by the retirement commit, not
  by an ignore rule) and removed from `rvsec/rvsec/pom.xml` `<modules>` (the mid-level
  aggregator; the root pom does not list the module).
- **[Generation]**: every task touching `CipherSpec` generates the monitor through the real
  pipeline (`rvj.Main` → logic-repository child) and records the heap used; `TMPDIR` off tmpfs.

### Error
- `pytest` failure — a predicate read inside `condition(...)`; a read without an accuser or
  without a `codes.csv` code; a read whose predicate no specification in the set writes (and no
  `unclosable` record names the absent producer); a write outside the rule's `ORDER` acceptance
  point without a recorded reason; an orphan accuser in `jca_android` (either direction: declared
  and unused, or used and undeclared); a `.mop` parameter list that does not survive into the
  `.rvm`; any occurrence of `ExecutionContext` in a `jca_android` `.mop`; an automaton not
  equivalent to its rule's `ORDER` under the versioned alphabet mapping; a wired edge closed
  without its trace pair; an unrecorded hunk against the seed (`divergence_record.csv`).
- `Logic Engine Error` / `StackOverflowError` — a generation failure; the artifact, not the exit
  code, decides success (the toolchain returns 0 on failure — measured live).

## Invariants

- **INV-INS-130**: Every predicate operation of a `jca_android` specification MUST go through the
  set's own store classes; no `.mop` of the set may mention `ExecutionContext` — checked as
  `grep -rlw 'ExecutionContext' jca_android/ --include='*.mop'` returning nothing, with `-w` so a
  fully-qualified use is caught as well as an import. `generic` and `generic_new` reference no
  predicate substrate (0 of 145 files) and are outside this invariant.
- **INV-INS-131**: The `jca_android` predicate store MUST key hybridly — identity
  (`IdentityHashMap` semantics) on the object binding; value comparison, case-insensitive and
  with the oracle's splitters, only on positions whose declared type is `String`/`int`/`Integer`
  — MUST support arity N (the oracle's measured maximum is 2), MUST return a three-valued verdict
  (`SATISFIED`/`VIOLATED`/`NOT_OBSERVED`), MUST hold object keys weakly with purge, and MUST be
  thread-safe. The API MUST separate the bound object from the value positions —
  `ensure/validate(Property p, Object bound, Object... values)` — because a plain varargs head
  (`Object... args`) silently spreads a reference-array argument (`KeyManager[]`, `TrustManager[]`
  — exactly the TLS-chain bindings) into separate arguments, and an empty array yields zero
  arguments (measured under JDK 21; javac emits only an easily missed warning). It MUST NOT
  offer `hasEnsuredPredicate` (zero `.mop` sites in any set) nor a property-wide removal that
  ignores the object (the deprecated `remove(Property)` semantics of the old store).
- **INV-INS-132**: `ExecutionContext.java` MUST remain byte-identical — zero edits, not even an
  annotation (WORKFLOW.md P3 bans deprecation annotations, and byte-identity without exception is
  the stronger freeze claim) — and MUST keep serving the frozen `jca` and the archived
  `jca_android_bug_predicate` unchanged; it joins the freeze gate's `FROZEN_PATHS`. The shared
  `Property` enum MAY gain constants **append-only** — never removed, renamed or reordered
  (measured safe: zero `ordinal()`/`values()` uses anywhere in the tree) — under a dedicated
  test that asserts the pre-change constants and their relative order survive. Every other class
  the frozen set calls is untouched. The freeze gates of gh101/gh104 MUST stay green throughout.
  This narrows nothing the main spec grants: its scenario "Shared runtime code the frozen set
  references is repaired" opens a repair path for `rvsec-core` code that specifications of
  **both** sets call, and after this migration no `jca_android` specification calls
  `ExecutionContext` at all (INV-INS-130), so that scenario has no subject in this file and its
  WHEN is vacuous here. The class serves one set, and a one-set class is frozen with that set.
- **INV-INS-133**: A predicate read (`REQUIRES` translation) MUST be placed in the event body,
  never inside `condition(...)`; a failed read MUST accuse at that event with
  `UnsatisfiedConstraint` and a `codes.csv` code, and a read whose verdict is `NOT_OBSERVED`
  MUST emit the *not observed* code, not the violation code. `condition(...)` MUST NOT contain a
  predicate read; overload discrimination, `ORDER` branching and `CONSTRAINTS` checks remain
  legitimate guard uses. A guarded clause (`X => pred[…]` — 8 of the 36) evaluates its guard in
  the event body **before** the read: a false guard suppresses the read and any report, never
  the transition, and the guard expression is recorded in the `guard` column of
  `predicate_graph.csv` — wiring the clause unconditionally would accuse every non-matching
  `Cipher.init` of a missing IV. A composite read site (a disjunction or conjunction of probes
  translating one clause, `CipherSpec.i2`'s key-origin trichotomy being the live case) keeps its
  boolean structure in the body and emits at most **one** report per violated clause, not one
  per probe.
- **INV-INS-134**: A predicate write (`ENSURES` translation) MUST be placed at the rule's
  acceptance point — the `@match` handler, or the states of an `after L` clause — never in an
  arbitrary event body; each write names the object the rule's clause binds, at the rule's arity.
  A write kept elsewhere, or kept below the rule's arity, MUST carry a recorded reason in
  `predicate_graph.csv`. The arity exception exists because producer and consumer must move
  together: `PredicateStore.validate` compares the value tuple, so a write at arity 2 read by a
  not-yet-migrated consumer at arity 1 returns `VIOLATED` — a positive accusation about a
  conforming program — where the unmigrated pair returned `NOT_OBSERVED`. A write MUST NOT stay
  below the rule's arity past the task that migrates its last consumer.
- **INV-INS-135**: `jca_android` MUST have zero orphan accusers in both directions: every
  declared event appears in the `fsm`/`ere`, and every symbol the `fsm`/`ere` uses is declared
  exactly once (the alphabet is a multiset — a duplicate declaration is a defect; the archived
  `GCMParameterSpecSpec` carries both defects at `jca/…:23,34,48` and stays as the gate's
  negative fixture). The gate is G-ACC, and on specification forms without an automaton
  (event-only) it MUST skip declaredly, never report "all events orphan". An orphan that is the
  **negated twin** of a conforming sibling — identical `call`/`args` pointcut, condition
  differing only in polarity; 12 of the 17 measured orphans are this, and `PBEKeySpecSpec.err1`
  rides the same fusion as a thirteenth — MUST be **fused** into the
  sibling (one event, the accusation moved into the body), never absorbed as a second event:
  two events matching the same call is itself the defect the automaton scenarios name. The two
  treatments are told apart by the orphan's body, not by the shape of its guard: an orphan whose
  body carries an accusation of its own MUST be absorbed, because absorbing preserves a report
  the set would otherwise lose; an orphan whose body only rebinds a monitor field accuses nothing
  of its own — the only report it emits is the spurious `InvalidSequenceOfMethodCalls` that its
  absence from the automaton produces — and MUST be fused. Such a twin can suppress the very
  finding its file exists to make: on `TrustManagerFactorySpec-sunx509.txt` the unfused set
  emits `TRUSTMANAGERFACTORY-ORDER-00` twice and never accuses the algorithm, because the
  orphan's `__RESET` leaves the monitor in a state where the next event's transition fails and
  the `@fail` path replaces the body that carries the check; the fusion produces exactly one
  report, the `TRUSTMANAGERFACTORY-ALG-00` the rule states. Where the
  twin is not an exact complement (`IvParameterSpec.c4` ignores its sibling's offset/length
  constraints; the three `PBEKeySpecSpec` accusers overlap, so one bad call fires up to three),
  the fusion decomposes the accusation per clause, one report each. To **absorb** the remaining
  4 is defined operationally by where the rule's ORDER puts the call the orphan matches, and it
  takes one of two forms. Where the ORDER has no symbol for that call — `SecureRandomSpec.g4`
  and the two `PBEKeySpecSpec` FORBIDDEN constructors, three calls the rule turns down rather
  than sequences — the event enters the automaton's declared alphabet with benign self-loops at
  every state where its call is legal, and its `order_alphabet_map.csv` row records it as
  ORDER-unmapped. Where the ORDER does name the call — `KeyPairGeneratorSpec.initError` matches
  `initialize(int)`, which api30 states as `i3: initialize(keySize)` with the size bound under
  CONSTRAINTS — the event enters at that position, as one more alternative of the group its
  sibling belongs to, and its row is `mapped` to the same symbol; two events standing for one
  symbol is the non-bijection the mapping already models. G-ACC holds by membership either way,
  and so does G-ORDER: the first form because the comparison erases unmapped events first
  (INV-INS-138), the second because the erased languages are then literally unchanged. Without
  this definition the two gates could only be satisfied by mutually exclusive automata. The
  second form is not a convenience, and the first is not always available: a self-loop does not
  satisfy the position the following event needs, so absorbing `initError` as a loop would have
  left `getInstance("RSA"); initialize(3072); generateKeyPair()` drawing a
  KEYPAIRGENERATOR-ORDER-00 on top of its KEYPAIRGENERATOR-KEYSIZE-00, about an ordering the
  rule accepts. Measured 2 → 1 against the pre-image, task 3.6
  (`data/gh105/evidence/harness/f1-KeyPairGeneratorSpec.md`, trace `-rsa3072`).
- **INV-INS-136**: A junction specification (mechanism B) MUST obey four rules: (a) the consumer
  event is never `creation` — a consumer-created partial instance cannot see the chain and
  accuses the conforming trace; (b) every state reachable by a disconnected join (an instance
  combination whose parameters never met in one event) carries a benign self-loop, so
  cross-product instances stay silent instead of failing spuriously; (c) a chain position whose
  runtime type is a primitive array is declared `Object` and the overload is fixed in the
  `call(...)` signature — `args(x)` with `Object` alone matches any single argument, including
  autoboxed primitives; (d) state needed by `@match`/`@fail` handlers lives in monitor fields —
  specification parameters are not visible inside handlers. All four rules MUST be checked
  structurally, not by per-chain review: (c) by G-PARAM, and (a), (b), (d) by
  `gh105_predicate_graph.py`, because each is decidable from the `.mop` alone — (a) is the
  `creation` keyword on the consumer event declaration, (d) is handler state declared outside the
  monitor's field block, (b) is a reachability question over the declared automaton. A rule
  enforced only by a review that runs once per chain is not protected against the next edit.
- **INV-INS-137**: `data/jca_android/predicate_graph.csv` is the versioned inventory of every
  predicate site, and the closure gate G-PRED2 MUST hold over it: every read has at least one
  producer in the set or an `unclosable` record naming the absent producing rule; every write has
  a reader or a deliberate-omission record; every `ENSURES`/`REQUIRES` clause of a rule with a
  specification in the set maps to exactly its sites. Zero rows over a set without predicates is
  green. The closure target is measured, not aspirational: of the 35 connectable clauses,
  **25 are wireable** (consumer and at least one producer rule both have a `.mop` in the set) —
  of which **24 are wired** and the vacuous #30 is recorded, never wired —
  and **10 are not** — recorded under a second category beside `unclosable`:
  `unmonitored-consumer` / `unmonitored-producer` (or both), naming the absent specification.
  `preparedEC` stays the single `unclosable` (no producing rule exists), and
  `SSLContext randomized[sr]` is recorded as **vacuous** — the rule's own `Init: init(kms, tms, _)`
  binds `sr` in no event, so not even the oracle can check it. This inventory realizes
  INV-INS-111 for the successor set.
- **INV-INS-138**: G-ORDER MUST decide language equivalence between a specification's `fsm`/`ere`
  and its rule's `ORDER` by DFA equivalence, under the event-alphabet mapping of
  `data/jca_android/order_alphabet_map.csv` — a versioned artifact, one row per association,
  revised with the specification that uses it. The gate MUST report `skipped` (with the reason)
  for a specification with no CrySL rule or no mapping, and MUST NOT infer a mapping
  heuristically. An event with no `ORDER` counterpart (an absorbed accuser such as `initError`
  or `g4`) maps to no `ORDER` symbol: its mapping row records the exemption, and
  the gate erases unmapped events from both languages before deciding equivalence — this is
  what lets an absorbed accuser satisfy G-ACC without breaking G-ORDER. A wrong mapping is a
  wrong verdict in both directions. The gate MUST parse an `ORDER` under the CrySL grammar's own
  precedence — `Sequence` (`,`) is the outermost production and therefore the *weakest* operator,
  so `a, b | c` is `a, (b | c)` (`CrySL.xtext:103-120`) — and MUST NOT reuse the juxtaposition
  precedence an `ere` needs, where concatenation binds tighter. The two readings agree on every
  rule that parenthesises its alternations and disagree only on the one that does not, so the
  defect presents as a single plausible witness rather than as a parse failure: it cost the
  `CipherSpec` row a wrong witness, a wrong direction and a wrong accuser
  (`data/gh105/evidence/f1-order-gate-precedence.md`, repaired at task 7.1).
- **INV-INS-139**: The parameter list of every `.mop` MUST survive intact into its generated
  `.rvm` (G-PARAM), checked over every file of the enumerated universe by comparing the two headers. The check MUST read
  the generated artifact and MUST NOT trust exit codes: JavaMOP deletes the entire list for a
  primitive-array parameter and returns 0 with the success message, and returns 0 even on hard
  pointcut parse errors.
- **INV-INS-140**: Every gate of this contract MUST degrade declaredly over the full
  specification universe, which each gate MUST **enumerate** rather than assert as a literal —
  214 `.mop` over the five sets before this change edits the tree, and 214 plus the junction
  specifications Group 5 adds to `jca_android` afterwards, so a gate that hard-codes the count
  turns its own deliverable into a failure: event-only specifications (17 in `generic_new`) are a legitimate form and are
  skipped by automaton gates; files that do not compile (11 duplicate-parameter files and the
  `FSM358.mop` import collision in `generic`) are skipped and counted, never crash the gate;
  specifications without a CrySL rule are `skipped`, never green-by-vacuity nor red-by-absence;
  helper methods that shadow API names (`validate(int)` in `KeyPairGeneratorSpec`; collection
  `.remove(`) MUST NOT be counted as predicate sites — the discriminator is the `(Property`
  argument; `@match1`-style handlers reached through `alias` MUST be resolved to their states.
- **INV-INS-141**: INV-INS-128 (G-PRED byte-identity of the predicate machinery) is superseded
  **for `jca_android`** by INV-INS-130/131/137; it remains in force verbatim for the frozen
  `jca`. The supersession extends to the rest of gh104's predicate-preservation contract: the
  requirement "The Successor Set Carries the Predicates of Its Seed Unchanged" (its per-file
  count equality summing to 134, and its "neither pure propagator receives a report site"
  scenario) stops applying to `jca_android` when the first migrated file lands, and INV-INS-123's
  premise that the set "encodes no `REQUIRES` by construction" is falsified by this change —
  constraint provenance (G-CONF) continues to hold, and the `REQUIRES` the set now encodes are
  governed by INV-INS-133/137/146. Every hunk the migration writes against the gh104 seed MUST
  appear as a `divergence_record.csv` entry **keyed by that hunk**, so the departure from the seed
  stays enumerable. The granularity is not a choice: `scripts/gh104_divergence_record.py` keys
  each row by a 12-hex sha1 of the diff hunk and its `check()` fails both ways — `unrecorded
  divergence` for a live hunk with no row, `stale entry` for a row whose hunk no longer exists —
  with an empty hunk key admitted only for the three narrative kinds. The recorder is therefore
  collateral of this change, not a bystander: its `KINDS` whitelist MUST gain the species this
  migration produces (`predicate-store`, `placement`, `junction`, `predicate-removal`), because
  an unlisted kind makes `check()` report `unknown kind`, and
  `tests/parity/test_gh104_specset_gates.py::test_jca_android_hunks_all_recorded` (INV-INS-118)
  MUST stay green through every `.mop` edit of this change, including the junction
  specifications and the wiring edges. Per-site accounting lives in `predicate_graph.csv`, which
  is keyed for it; the divergence record answers a different question — what changed against the
  seed, and why. The collateral sites MUST be updated in the same task
  that migrates the first specification, or they produce false verdicts: in `gh104_gates.py`,
  `accept_requires` and the `PREDICATE_CALL` regex; in `gh104_message_gate.py`, `_clause_family`
  (it classifies an orphan's clause family from the `condition(...)` text, which F2 empties); in
  `experimento-gh104/scripts/preflight.py`, `check_no_predicates` — a **second** gate also named
  G-PRED that still asserts the withdrawn opposite polarity (zero predicates in the successor);
  it is warn-only (it never fails a run) and MUST be retired; in
  `tests/parity/test_gh104_structural_gates.py`, the third G-PRED assertion
  (`test_jca_g_pred_counts_the_sites_the_successor_must_carry`), which is already `jca`-only and
  therefore survives the rescoping — listed so the record shows it was read, not overlooked; in
  `tests/parity/test_gh104_specset_gates.py`, the census constants (`PREDICATE` regex,
  `EXPECTED_CONSTRUCTS`, `EXPECTED_PREDICATE_LINES = 134`, `EXPECTED_SPECS = 23`) that encode the
  frozen census this migration invalidates for the successor set; and in
  `data/jca_android/gate_allowlist.csv`, the `err2` and
  `c3` rows, whose justifications cite condition reads that F1/F2 change — their update lands
  with the first F1 fusion that deletes a cited event. The supersession also covers gh104's
  INV-INS-118 arithmetic: it counts the successor set at 21 specifications (seed minus the two
  files INV-INS-128 removes), while the tree holds 23 — both files present — and this change
  wires sites in one of the two (`SecretKeySpec.e1` as a `propagation` record and
  `SecretKeySpec.mop` as the #32 producer) while `RandomStringPassword.mop` stays in the set and
  ends this change with no predicate site at all, its four deleted by task 4.11; the 23-file count
  is the operative one for `jca_android`.
- **INV-INS-142**: A predicate removal MUST translate a `NEGATES` clause of the rule, MUST name
  the object, and MUST occur at the clause's `after` event. The oracle has exactly two `NEGATES`
  clauses (`SecretKey: generatedKey[this,_] after d`; `PBEKeySpec: speccedKey[this,_] after cP`);
  only the second has a corresponding event in the set. The eight `@fail` removals — "undo the
  predicate when the automaton fails", a semantics no CrySL generation has — MUST be removed,
  each with its harness-measured delta, and each MUST leave with the file pass that migrates or
  deletes the write it withdraws, by the precedent of the `clearPassword` removal at task 4.6.
  One of the eight (`MacSpec.mop:99`) went with the writes it withdrew at task 4.9; the
  remaining seven went at task 4.14 with the seven writes that pass migrated, because
  `PredicateStore` offers no removal at all (INV-INS-131 forbids it the object-blind
  `remove(Property)`) — so a removal left behind is a no-op on a store nothing writes, which is
  dead code and holds INV-INS-130 off zero for its file. Task 6.4 therefore **verifies** the
  count is zero rather than performing any deletion, the shape task 6.5 already has.
- **INV-INS-143**: The *not observed* verdict MUST reach the violation-report envelope with its
  own `codes.csv` code family, distinct from the violation codes, in the same task that
  introduces the first three-valued read — so no intermediate state exists where the third value
  is computed but indistinguishable downstream.
- **INV-INS-144**: No wiring task (an edge of F3, a guard move of F2, an orphan absorption of F1,
  a removal of INV-INS-142) MAY close without a satisfy/violate trace pair replayed by the
  differential harness through the before and after monitors, verdicts committed — the per-edge
  refinement of INV-INS-124. A repair that moves which call is accused without changing whether
  the trace is accused is a moved defect, recorded as such.
- **INV-INS-145**: Every task that changes the `Cipher` alphabet MUST generate the monitor
  through the real pipeline before the alphabet is accepted and MUST record the heap used.
  Seventeen events generate under `-Xmx1g` (~53 s); eighteen raise `StackOverflowError` in the
  parent's enable-set parser at any heap — the ceiling is the parser, not memory, and no flag
  lifts it (INV-INS-115 carries the same numbers). `CipherSpec` already declares exactly 17
  events, so its headroom is **zero**: no task of this change may add an event to the
  `CipherSpec` alphabet — every new `Cipher` binding routes through a junction specification or
  the store, both of which cost nothing there. The enduring, re-checkable form of this
  invariant is the ceiling itself: the `CipherSpec` alphabet MUST NOT exceed 17 events
  (countable in the `.mop`); the generate-and-record-heap discipline is this change's task
  evidence, not a post-archive check.
- **INV-INS-146**: A negated `REQUIRES` clause (`!pred[…]` — the oracle has exactly three:
  `Cipher: !macced[_, plainText]` at `Cipher.cryptsl:180`; `Mac: !encrypted[output1, _]` and
  `!encrypted[output2, _]` at `Mac.cryptsl:82,84`) inverts the three-valued table: **no entry is
  the conforming case** and MUST stay silent — for `!macced`, `NOT_OBSERVED` is conformance, not
  a reach artifact — while an entry for a same-name predicate is the violation (the old oracle's
  name-only branch fails on any same-name ensured predicate, regardless of argument values). The
  read API MUST carry the polarity explicitly (a distinct `validateAbsent(...)` entry point or
  equivalent), and `predicate_graph.csv` records the clause polarity. The three clauses are
  **wired** in this change (researcher decision 2026-08-20 — tasks 5.3/5.7, with the `MACED`
  producer write added at Mac's acceptance point); wiring a negated clause through the positive
  table would emit *not observed* on every conforming `Mac.doFinal()`.
- **INV-INS-147**: The 25 accepting-state bookkeeping calls of the current set
  (19 `setObjectAsInAcceptingState` / 6 `unsetObjectAsInAcceptingState`) MUST receive an explicit
  disposition in the migration: the new store does not offer the bookkeeping, each removed call
  falls inside a recorded `divergence_record.csv` hunk (INV-INS-141), and the behavioral delta is measured
  by the differential harness like any other hunk. Production has zero readers of that
  bookkeeping; the maintained readers (`Assertions.mustBe…InAcceptingState`) live in the
  `rvsec-agent` test corpus, which weaves the frozen `jca` and is untouched, and 11 disposable
  audit drivers under `audit/20260808_validacao_jca_android/` call `isInAcceptingState`
  directly (73 sites) — one-shot harnesses against the pre-change set, not updated. The
  enduring, re-checkable form after the migration: `jca_android` MUST contain zero
  `setObjectAsInAcceptingState`/`unsetObjectAsInAcceptingState` calls.
- **INV-INS-148**: The differential harness MUST isolate the predicate substrate between traces.
  `TraceRunner.replay()` rebuilds a fresh class loader per trace and resets `ErrorCollector`, but
  the predicate singleton resolves through the **parent** loader — it sits on `java.class.path` —
  so its state survives every trace of a directory replay unless it is reset explicitly, exactly
  as the error sink already is. Without the reset a satisfy trace's `ensure` silently satisfies
  the violate trace that follows it, and the pair evidence of INV-INS-144 reports a pass it did
  not earn. `replay()` MUST therefore reset the predicate store beside the error sink, and the
  isolation MUST be proved by a cross-trace test — a satisfy trace followed by a violate trace in
  one replay, asserting the violation is still accused — never assumed from the class-loader
  construction. This is the operational reason the store offers `reset()` despite having zero
  production callers.
- **INV-INS-128** (restated, replacing the entry of the same number): every `ExecutionContext`
  site of the frozen `jca` — 134 lines over its 23 files — MUST be present at the same event and
  unrewritten **in the frozen set itself**. The successor set `jca_android` is outside this
  invariant: it carries no `ExecutionContext` site at all (INV-INS-130), and its predicate
  machinery is governed by INV-INS-131/133/137. G-PRED is the `jca` lock and nothing else.
- **INV-INS-123** (restated, replacing the entry of the same number): G-2 accepts an accuser
  whose clause family is `CONSTRAINTS` or `FORBIDDEN`, and — for `jca_android` — `REQUIRES` as
  well, because the set now encodes `REQUIRES` clauses as body reads with accusers
  (INV-INS-133/137/146). Constraint provenance (G-CONF) is unaffected: every allow-list value
  still traces to its api30 rule. The `jca` branch of G-2 is unchanged.
- **INV-INS-118** (restated, replacing the entry of the same number): every hunk between the
  frozen `jca` and the successor `jca_android` MUST carry a `divergence_record.csv` row keyed by
  that hunk, and the successor set holds **24** specifications — the tree's count, both
  `RandomStringPassword.mop` and `SecretKeySpec.mop` present, and `IvChainJunction.mop` added by
  Group 5. `SecretKeySpec.mop` carries a wired
  site after this change and `RandomStringPassword.mop` carries none, its four deleted at task
  4.11; membership is what the count asserts, not predicate sites. The 21-specification arithmetic
  of the original entry counted a removal that the tree does not show.

## MODIFIED Requirements

### Requirement: Predicate Contract Between Specifications

A `Property` predicate written by one specification and read by another SHALL be treated as a
contract with two enforced properties: every constant written is read somewhere or recorded as a
deliberate omission with its reason, and the inventory of writes and reads is a versioned
artefact — `data/jca_android/predicate_graph.csv` — rather than an ad-hoc derivation. The
inventory carries what earlier tooling discarded: the site kind (`condition`/body/`@match`/
`@fail`), the polarity, the arity, the static type of each position, the splitter of value
positions, the CrySL clause translated (rule file and line), and the automaton membership of the
carrying event.

Nothing links the constant written to the constant read. Both sides are enum members, so a
specification that writes a neighbouring specification's constant compiles and runs and reports
nothing; two specifications do this today. A read of an absent key is quiet in both directions —
a missing write turns a guarded accusation into an unconditional one, and a wrong write turns a
real accusation into silence.

The store serving `jca_android` SHALL be the set's own classes in `rvsec-core`, and SHALL
identify objects the way the monitor index identifies them — **by identity** — while comparing
**value positions** the way the oracle does: only positions whose declared type is
`String`/`int`/`Integer` are compared, case-insensitively and with the oracle's splitters
(`alg()`, `part(0,"/",transformation)`); every other position participates by identity or not at
all. JavaMOP keys a monitor by `System.identityHashCode` confirmed with `==`, so it never
conflates two alike instances; a predicate store keyed by `equals` does, and the two halves of
one mechanism then disagree about what "the same object" means. The consequence is not academic
and runs in all three directions: a write over an object equal to a stored one adds nothing, so
two monitors share a mark; a `REQUIRES` succeeds for an object that no monitored sequence
produced, provided an equal one was; and a removal in one monitor's `@fail` takes another
monitor's mark. It bites wherever `equals` is value-based — `Key` implementations, `String`,
boxed primitives — and is invisible wherever it is not, which is why it survived a translation
that is otherwise careful. The store SHALL support the rule's arity (31 of the 90
`ENSURES`/`REQUIRES` clauses are binary; the maximum arity in the api30 oracle is 2 — the
apparent quaternary `generatedKey` was an artifact of counting commas inside a splitter),
SHALL separate the bound object from the value positions in its API
(`ensure/validate(Property p, Object bound, Object... values)` — a plain varargs head spreads a
reference-array argument, so the TLS chain's `KeyManager[]`/`TrustManager[]` bindings would
silently arrive element-by-element), SHALL hold object keys weakly and purge them, and SHALL be
thread-safe — cryptography on Android rarely runs on the main thread, and the previous substrate
synchronized nothing.

`validate` SHALL return three values, not two: **satisfied**, **violated**, and **not observed**.
A `REQUIRES` may only accuse when the monitor has evidence it would have seen the corresponding
`ENSURES`; in the absence of that evidence — the producer outside the instrumentation reach being
the measured case, 88 % of published violations sitting in third-party code — the verdict is
*not observed*, reported under its own code so downstream analysis can separate reach artifacts
from violations. Because `condition(...)` compiles to a boolean guard, the three-valued verdict
is consumable only in event bodies — which is where reads live under this contract. Polarity
inverts the table (INV-INS-146): for a negated clause, no entry is the conforming case and stays
silent, while a same-name entry violates — the read side of a negated clause goes through its
own explicit entry point, never through the positive `validate`.

The frozen substrate is not repaired: `ExecutionContext` stays byte-identical — zero edits — and
keeps serving the frozen `jca` and the archived set. This is what makes the
freeze safe by construction — the path that failed before (`233df18a` → `e204e2a4`) changed the
shared class believing the `.mop` freeze gate covered it. After the migration, the only
consumers of the frozen class are the two read-only sets; `generic` and `generic_new` call
no predicate substrate at all.

Predicates that cannot be expressed by this mechanism SHALL be recorded rather than approximated.
A predicate asserting **provenance** over a primitive remains inexpressible under identity
keying: a boxed primitive has no stable identity across boxing operations, so `randomized[lSeed]`
— that a `long` came from a CSPRNG — is asserted of a box that the next autoboxing of the same
value does not reproduce; the residual write-side unsoundness narrows to the `Integer` cache,
where equal small values genuinely are one object. A `REQUIRES` whose producing rule has no specification in the set MUST NOT be given
a reader on the strength of the rule alone: the rule names a producer this set does not model,
and transcribing only the consumer half turns every conforming execution into a reported misuse
(`preparedEC` is the one such predicate in the api30 oracle). Such an edge SHALL be recorded as
`unclosable` in the predicate graph, naming the rule that would have produced it.

#### Scenario: Constant written and never read

- **WHEN** `predicate_graph.csv` shows a `Property` predicate written by at least one
  specification and read by none
- **THEN** G-PRED2 MUST fail
- **AND** the predicate MUST either gain its reader (the rule's consuming clause, wired) or be
  recorded as a deliberate omission with its reason

#### Scenario: Specification writes a neighbouring specification's constant

- **WHEN** a specification writes a predicate that does not correspond to the clause its CrySL
  rule ensures (`KeyPairSpec` writing the private key under `GENERATED_PUBLIC_KEY` is the
  measured case)
- **THEN** G-PRED2 MUST detect the mismatch from the clause column of the inventory
- **AND** the defect MUST NOT depend on code review to be caught

#### Scenario: Two equal objects are monitored separately

- **WHEN** an application constructs two `SecretKeySpec` instances with the same key material and
  algorithm, one through a conforming sequence and one through a violating branch
- **THEN** the store MUST mark only the instance the conforming sequence produced
- **AND** a later `Cipher.init` over the other instance MUST NOT be validated by the first
- **AND** a removal naming either MUST leave the other's mark untouched

#### Scenario: A predicate's whole set is deleted

- **WHEN** a specification's handler would remove a `Property` without naming the object it
  wrote — the semantics of the old store's one-argument `remove(Property)`, which the frozen
  `jca` still calls at four sites
- **THEN** every other monitor's mark for that predicate would be erased as well
- **AND** the migrated set MUST NOT reproduce this: the new store offers no property-wide
  removal (INV-INS-131), and a removal names the object, which requires the specification to
  hold it in a monitor field

#### Scenario: Value position compared the way the oracle compares

- **WHEN** a rule's clause is `generatedKey[key, alg]` and the store holds the predicate for the
  identical `key` object with value `"AES"` at the algorithm position
- **THEN** a read passing the same `key` and `"aes"` MUST be satisfied (case-insensitive)
- **AND** a read passing the same `key` and `"DES"` MUST be violated
- **AND** a read passing an equal-but-distinct key object MUST NOT be satisfied by identity

#### Scenario: Consumer without observed producer reports "not observed"

- **WHEN** a `Cipher.init(mode, key, spec)` fires and no `ENSURES` for that `key` was observed
  (the generating call sits outside the woven code)
- **THEN** the read's verdict MUST be `NOT_OBSERVED`
- **AND** the emitted envelope MUST carry the *not observed* code, not the violation code
- **AND** the event MUST still take its automaton transition

#### Scenario: Required predicate has no producer in the set

- **WHEN** a rule's `REQUIRES` names a predicate whose producing rule has no specification in
  the set
- **THEN** the edge MUST be recorded as `unclosable` in `predicate_graph.csv`, naming the absent
  producing rule
- **AND** a reader MUST NOT be added for it

#### Scenario: Inexpressible predicate is recorded, not approximated

- **WHEN** a CrySL predicate asserts provenance over a primitive value
- **THEN** it MUST be recorded as inexpressible with the reason
- **AND** it MUST NOT be approximated by a value-keyed entry that would conflate unrelated equal
  values

#### Scenario: The frozen substrate is untouched

- **WHEN** the migration of `jca_android` to the new store is complete
- **THEN** `ExecutionContext.java` MUST be byte-identical to its pre-change state
- **AND** the `jca` freeze gates MUST be green
- **AND** `grep -rlw 'ExecutionContext'` over `jca_android/*.mop` MUST return nothing

### Requirement: Event Membership in the Specification Automaton

Every event declared in a specification SHALL appear in that specification's `fsm` or `ere`, and
every symbol the `fsm` or `ere` uses SHALL be a declared event — membership is checked in both
directions, and the declared alphabet is a multiset: a duplicate declaration is a defect. The
monitor generator assigns an event absent from the automaton a transition row that moves every
state to `fail`, so such an event does not merely go unmodelled — it makes the specification
accuse unconditionally; a symbol used but never declared is dropped by the generator silently. In
`jca_android` this SHALL hold with zero exceptions after this change: the 17 orphan accusers (9
specifications) are absorbed into their automata or fused into their conforming siblings, each
change measured by the differential
harness, rescuing the structural bucket of the archived attempt under fresh evidence rather than
by copying its hunks. The gate is G-ACC, and it runs generically: on event-only specification
forms (no `fsm`/`ere` block — 17 files in `generic_new`) it skips declaredly instead of calling
every event an orphan, and on sets without predicates it reports an orphan as informative rather
than as an accuser defect.

The reverse direction and the multiset rule have a live negative fixture: the frozen
`jca/GCMParameterSpecSpec.mop` declares `event c1` twice (lines 23 and 34) and its `ere` (line
48) names a `c2` that is never declared — identical in the archived set; `jca_android` already
carries the correction. The frozen file is not repaired (INV-INS-109); it anchors the gate's
negative test.

This makes automaton membership part of any binding correction rather than a follow-up:
repairing the binding of an event that is absent from the automaton converts a dead event into
an unconditional accuser. Kleene-star residue is declared where it exists: absorbing an orphan
by a Kleene prefix resolves the `@fail` at the violating event but does not absorb obligatory
calls that must follow it (`PBEKeySpec.cP` is the recorded case — the Kleene-prefix residue
record, labeled `FEN-PBK-RESIDUO` in the Phase-0 plan).

#### Scenario: Bound event absent from the automaton

- **WHEN** a `jca_android` specification declares an event that appears in no row of its `fsm`
  or `ere`
- **THEN** G-ACC MUST fail
- **AND** the correction MUST add the event to the automaton in the same change that repairs its
  binding, with the satisfy/violate trace pair committed

#### Scenario: Automaton symbol never declared

- **WHEN** a specification's `fsm` or `ere` names a symbol that matches no declared event
- **THEN** G-ACC MUST fail in the reverse direction
- **AND** the frozen `GCMParameterSpecSpec` fixture MUST be reported and allowlisted with its
  reason, never repaired

#### Scenario: Event-only specification form

- **WHEN** G-ACC runs over a specification with no `fsm`/`ere` block
- **THEN** it MUST classify the file as event-only and skip it declaredly, counting the skip
- **AND** it MUST NOT report its events as orphans

#### Scenario: Binding repaired without automaton membership

- **WHEN** an event's binding is corrected while the event remains absent from the automaton
- **THEN** every call outside the allow-list MUST be expected to emit a spurious
  `InvalidSequenceOfMethodCalls`
- **AND** the change MUST NOT be accepted in that state

#### Scenario: A fused pointcut leaves a required argument unbound

- **WHEN** a specification collapses several of its rule's events into one pointcut, and a
  `REQUIRES`, `ENSURES`, `NEGATES` or `CONSTRAINTS` clause quantifies over an argument the
  fusion leaves unbound
- **THEN** the fusion MUST be replaced by one event per distinct binding profile — the set of
  arguments the clauses mentioning that event need bound — each taking exactly the transitions
  of the fused event it replaces
- **AND** the automaton's accepted language MUST be unchanged, only its alphabet refined
- **AND** signatures that share a binding profile and a body MUST stay fused, since the weaver
  resolves overloads on owner, name, return type and parameter types, so splitting them binds
  nothing new and spends alphabet that INV-INS-115 makes scarce
- **AND** where a fusion binds the varying argument as `Object+` and discriminates by type in
  the body, the fused signatures MUST share an arity, because `args(a, b, third, ..)` requires
  arity ≥ 3 and drops a shorter overload out of the automaton entirely, and none of the varying
  positions may be primitive, because `Object+` rejects primitives — a static type-pattern fact
  about the `call(...)` signature, distinct from INV-INS-136(c)'s `args(x)` with `Object`, a
  dynamic test that autoboxing satisfies; the two constructs are not in contradiction
- **AND** each resulting pointcut MUST be verified against the target API's real overload set,
  showing that the candidates jointly cover every signature the rule names and are pairwise
  disjoint

#### Scenario: Two events match the same call

- **WHEN** two pointcuts in one specification both match a single call, as an argument-less
  signature and the same signature with `(..)` do
- **THEN** the specification MUST be treated as defective, because one call takes two transitions
- **AND** the **wider** pointcut MUST be made disjoint from the narrower one, which is the only
  side that can move: the narrow one is an exact signature and admits no further narrowing.
  `CipherSpec.f2` was made `doFinal(byte[], ..)` this way, leaving the argument-less call to `f1`
- **AND** the repair MUST NOT spend alphabet: splitting the wider event into one per overload is
  what INV-INS-145 makes unavailable, and restricting its signature is what does not

## ADDED Requirements

### Requirement: Predicate Read and Write Placement

A predicate read SHALL live in the event body, never inside `condition(...)`, and a predicate
write SHALL live at the rule's acceptance point — the `@match` handler or the states of an
`after L` clause — never in an arbitrary event body. The two placements are the same lesson from
opposite sides. A guard read compiles to `return false` before the transition: the event leaves
the automaton, the next call is accused of order, and the report names a defect the program does
not have — today 27 of 27 reads are on the wrong side. A body write fires before the sequence is
accepted: 42 of 49 writes today establish `ENSURES` facts for sequences the rule has not
accepted, so a consumer downstream validates against a predicate the producer never earned.
`condition(...)` may not contain a predicate read — overload discrimination, `ORDER` branching
and `CONSTRAINTS` checks remain legitimate guards; violating a `REQUIRES` does not change the
typestate, exactly as `ORDER` and `REQUIRES` are distinct sections of the rule.

Every clause-translating read carries its accuser: a failed read reports `UnsatisfiedConstraint`
at that event with its own `codes.csv` code, and a `NOT_OBSERVED` verdict reports the
*not observed* code (INV-INS-143). Nine read events today have no accuser at all
(`CipherSpec.i2`, `GCMParameterSpecSpec.c1/c2`, `MacSpec.i1/i2`, `PBEParameterSpecSpec.c2` —
its would-be accuser `c3` binds only the 2-argument constructor while `c2` binds the 3-argument
one — `RandomStringPassword.vo/gb`, `SecretKeySpec.e1`). Of the nine, the reads that translate a
clause of their rule gain their accuser in the same task that moves them; the reads that
translate **no clause** MUST NOT gain one — `MacSpec.i1/i2` read `generatedKey`, which the Mac
rule does not require (it requires `preparedHMAC` and `!encrypted`); `RandomStringPassword.vo/gb`
have no rule at all; `SecretKeySpec.e1` governs a propagation write — from its body since task
4.12 — and the SecretKey rule has no `REQUIRES` section. Arming a propagation read fabricates a misuse class no rule describes.

Of those that translate no clause, a read is propagation only when it **feeds a write** and that
write **carries the predicate across**, and only then is it recorded as `propagation` in
`predicate_graph.csv`. `SecretKeySpec.e1` is the one that meets both: `SecretKey.getEncoded()`
returns the key's own bytes, so `RANDOMIZED` on the key is `RANDOMIZED` on what it returns.
Measured at task 4.12, the carrying is not incidental but the whole reason the event exists:
`getEncoded()` returns a fresh clone on every call, so a store keyed on object identity cannot
see the material through the copy, and no other site of the set writes about the returned array.
The same measurement bounds what the read may do — it governs the write and reports nothing, so
`NOT_OBSERVED` and `VIOLATED` are indistinguishable there, and the write stays conditional
because an unconditional one was measured to hand a hard-coded key's encoding on as randomised.

A read that translates no clause **and feeds no write** propagates nothing — it computes a
verdict no site consumes, and its only remaining effect is the transition its guard suppresses —
so it MUST be deleted rather than recorded: `MacSpec.i1/i2` are deleted by task 4.9 (researcher,
2026-08-21), which measured that guard turning a program that breaks no clause into an
`InvalidSequenceOfMethodCalls`.

A read whose write does **not** carry the predicate across MUST be deleted with that write, for
the same reason and a sharper one: recording it as `propagation` would put the set's name on a
fact the conversion does not support. `RandomStringPassword.vo/gb` are deleted with their two
writes by task 4.11 (researcher, 2026-08-21) — this reverses the instruction that task carried.
The file spans `Object` → `String` → `char[]` through `String.valueOf(Object)` and
`String.toCharArray()`, and `String.valueOf(Object)` calls `Object.toString()`, which was measured
over each of the three source types the set can hand it: a `byte[]` becomes its identity string
(`[B@726f3b58`), the `SecureRandom` itself becomes the constant `SecureRandom`, and only an
`Integer` becomes its own digits — and that one does not survive the new store, whose bound key is
identity, because the box at the `ensure` and the box at the read are the same object only inside
the `Integer` cache. So the two source types that propagate carry no randomness and the one that
carries randomness does not propagate. Its only consumer is `PBEKeySpecSpec.c1`'s password read,
which stands behind no clause either: api30 `PBEKeySpec.cryptsl` REQUIRES `randomized[salt]`, and
its clause about the password is `neverTypeOf(password, java.lang.String)`. Measured on the frozen
seed, the bridge is a false *negative* — a `PBEKeySpec` built from the `char[]` of `[B@6ae40994`
is accepted as having a randomised password and nothing is reported. Deleting the four sites
leaves the migrated tree's observable behaviour unchanged, because the bridge is already inert
there: its reads are still on the old substrate while its producers moved at task 4.5. The file
leaves `predicate_graph.csv` entirely, as `MacSpec` did at task 4.9.

The real clauses are wired where they belong (F3).

#### Scenario: Read moved from guard to body

- **WHEN** a `Cipher.init` event fires with a key for which `GENERATED_KEY` was established
- **THEN** the event MUST take its automaton transition
- **AND** no report is emitted
- **WHEN** the same event fires with a key for which the predicate was observed absent
- **THEN** the event MUST still take its transition
- **AND** an `UnsatisfiedConstraint` report MUST be emitted at that event, with its code and the
  envelope naming the event

#### Scenario: Guard read detected by the graph

- **WHEN** `predicate_graph.csv` classifies any `jca_android` read site as `condition`
- **THEN** the placement gate MUST fail naming the file, event and line

#### Scenario: Write at the acceptance point only

- **WHEN** a specification's rule ensures `preparedIV[this]` at the accepting state
- **THEN** the write MUST sit in the `@match` handler (or the `after L` state's handler), naming
  the object the clause binds
- **AND** a write found in an event body without a recorded reason MUST fail the placement gate

### Requirement: Junction Specifications for Co-Observable Predicate Chains

Where a predicate edge is realized by a chain of calls that hand an object from producer to
consumer — `SecureRandom.nextBytes(iv)` → `new IvParameterSpec(iv)` → `Cipher.init(…, spec)` —
the wiring SHALL use a junction specification: one multi-parameter JavaMOP specification per
chain, whose events bind overlapping parameter subsets so the runtime's own parametric indexing
(`CachedWeakReference`, identity, weak references, `TerminatedMonitorCleaner`, synchronized
monitors) carries the identity the store would otherwise have to reimplement. Two separate
specifications sharing an object have no channel in JavaMOP — each has its own maps and
monitors — so "specifications communicating" is by definition the store mechanism, not a
junction. The executed pilot validated the mechanism on the hard case: with two `byte[]` in one
process, the conforming chain matched silently and the violating chain failed at `mk` and at
`use`, on the right instance with the right bindings.

Four design rules are binding (INV-INS-136), each with a measured failure mode behind it: the
consumer is never the `creation` event (a consumer-created partial instance cannot see the chain
and accuses the conforming trace — the pilot reproduced this false positive); disconnected joins
get benign self-loops (without them, the randomized `iv` of another chain produced a spurious
fail); a primitive-array position is declared `Object` with the overload fixed in the
`call(...)` signature (declaring `byte[]` deletes the whole parameter list silently — G-PARAM
exists because of this); handler state lives in monitor fields. The silence of a consumer-only
trace under rule (a) is the structural form of the *not observed* verdict: no monitor exists, so
nothing accuses, and the reach limitation is not converted into a false violation.

A junction coexists with the typestate specification at shared joinpoints — the pilot chain's
consumer event fires on `Cipher.init`, inside `CipherSpec.i2`'s pointcut — and its reports
SHALL be counted as their own accuser: a junction `@fail` carries its own specification name,
code and event, so it never merges with the typestate specification's reports under the report
dedup identity (spec, error, class, method, location, code, event) nor under the
`(apk, class, method, spec)` unique-misuse key — a junction opens a new bucket at the same
`(class, method)` by construction. The ledger routes each clause to exactly one accuser, so the
same clause is never accused twice; downstream counting MUST NOT fold junction reports into the
typestate specification's bucket, and MUST NOT read them as duplicates.

#### Scenario: Junction and typestate specification fire at the same joinpoint

- **WHEN** a junction's `@fail` and the typestate specification both emit at one `Cipher.init`
  call on the same trace
- **THEN** the two reports carry distinct spec/code/event identities and both reach the envelope
- **AND** the accounting reads them as two accusers of distinct clauses, never as a duplicate
  to suppress (the task 8.5 smoke run commits the observed co-fire counts)

#### Scenario: The IV chain distinguishes instances

- **WHEN** two `byte[]` arrays exist in one process, one filled by `SecureRandom.nextBytes` and
  one not, and each is wrapped and used in a `Cipher.init`
- **THEN** the chain over the randomized array MUST NOT be accused
- **AND** the chain over the other array MUST be accused at the wrapping event (`randomized`
  required) and at the consuming event (`preparedIV` required), on that instance only

#### Scenario: Consumer-only trace stays silent

- **WHEN** the first observed event of a chain is the consumer (`Cipher.init`) and no earlier
  chain event was observed
- **THEN** no junction monitor exists and no accusation is emitted
- **AND** the *not observed* accounting of that consumer is carried by the store-side read, not
  by the junction

#### Scenario: A junction declares a primitive-array parameter

- **WHEN** a junction specification declares `byte[]`, `int[]` or `char[]` in its parameter list
- **THEN** G-PARAM MUST fail on the generated `.rvm` (empty parameter list)
- **AND** the specification MUST be rewritten with the `Object` idiom, the overload fixed in the
  `call(...)` signature

### Requirement: Predicate Graph Record and Closure Gate (G-PRED2)

`data/jca_android/predicate_graph.csv` SHALL be the versioned record of every predicate site of
the set, one row per site, carrying the 15 columns of the Output contract: file, event, site
kind, polarity, guard, arity, predicate, position types, splitter, the CrySL clause translated
(rule file and line), the mechanism (A/B per chain), the verdict, the disposition, the reason,
and the automaton membership of the carrying event. The closure gate G-PRED2 runs over it (INV-INS-137): every
read has a producer or an `unclosable` record; every write has a reader or a deliberate
omission; every clause of a rule with a specification in the set maps to exactly its sites. The
graph is diagrammable (Graphviz/Mermaid from the CSV, dead edges in red), which retires the
`rvsec-mop-defsuses` idea into an instrument that actually carries the object argument, the
negated reads and the automaton — everything the 2023 module discarded.

The record is generic: over a set without predicates, zero rows is the correct content and the
gate is green; helper methods shadowing API names are excluded by the `(Property` discriminator
(the set's own `KeyPairGeneratorSpec` carries a private `validate(int)` that a name-based count
miscounts as 4 extra reads).

#### Scenario: Closure over the wired set

- **WHEN** F3 completes and G-PRED2 runs over `jca_android`
- **THEN** each of the 21 wired `REQUIRES` clauses (the 25 wireable minus the two vacuous, #30
  and #23, which can have no read site, and the two whose composition the platform refuses,
  #17 and #21) MUST map to a read site with an accuser
- **AND** each of the 10 non-wireable clauses MUST map to an `unmonitored-consumer`/
  `unmonitored-producer` record naming the absent specification
- **AND** the one predicate with no producer in any rule (`preparedEC`) MUST appear as
  `unclosable`, and `SSLContext randomized[sr]` as `vacuous` (the rule binds `sr` in no event)
- **AND** each written `Property` value with no reader MUST carry a write-side disposition —
  `omission` or `propagation`, never a read-side one: `unmonitored-consumer` categorises the
  clause and closes a read, and a write with no reader is closed by the record of the omission

#### Scenario: Zero rows on a predicate-free set

- **WHEN** G-PRED2 runs over `generic` (118 files, no predicates)
- **THEN** the graph has zero rows and the gate MUST be green
- **AND** the report MUST say the set was covered, not skipped

### Requirement: Automaton–Order Equivalence Gate (G-ORDER)

For every `jca_android` specification with a CrySL rule, the language accepted by its
`fsm`/`ere` SHALL be equivalent to the language of the rule's `ORDER` clause, decided by DFA
equivalence — both languages are regular: the `Order` grammar is sequence, alternative,
cardinality (`*`, `+`, `?`) and grouping only, and event aggregates (`Gets := g1 | g2`) are
regular too. The comparison runs under the event-alphabet mapping of
`data/jca_android/order_alphabet_map.csv` (INV-INS-138): the `.mop` separates overloads to bind
arguments, so the mapping is not a bijection, and it is the gate's real work — versioned,
revised with its specification, never inferred. Specifications without a rule (`generic/*`,
`generic_new/*`, `RandomStringPassword.mop`) are skipped declaredly.

This gate would have caught the measured false positive on its own: the api30 `SecureRandom`
rule's `ORDER` is `Ins, Seeds?, Ends*` — Kleene star — while the specification's `end` state
omits `next2`, so calling `nextBytes()` twice is accused; 12,400 events, 99.98 % in libraries.

#### Scenario: SecureRandom order equivalence

- **WHEN** G-ORDER compares the repaired `SecureRandomSpec` automaton with `Ins, Seeds?, Ends*`
  under its mapping
- **THEN** the two DFAs MUST accept the same language
- **AND** a `nextBytes(); nextBytes()` trace MUST be accepted by both

#### Scenario: Specification without a rule

- **WHEN** G-ORDER reaches a specification with no api30 rule
- **THEN** it MUST report `skipped` with the reason
- **AND** it MUST NOT synthesize a mapping

### Requirement: Parameter-List Survival Gate (G-PARAM)

For every `.mop` of the five sets whose generation succeeds, the parameter list declared by the
specification SHALL survive intact into the generated `.rvm` header, and the gate that asserts
it SHALL read the artifacts, never the exit codes (INV-INS-139). The toolchain's failure is
silent twice over — measured: a primitive-array parameter makes JavaMOP delete the entire list
(not just the offending parameter) and return 0 with the success message, and rv-monitor then
emits a global monitor with zero `CachedWeakReference`; even a hard pointcut parse error returns
0. Today zero of the 215 specifications declares a primitive-array parameter, so G-PARAM
protects the work F3 introduces (junction specifications) rather than repairing a present
defect. The root cause is located and recorded (`javamop.jj:1456` `SimpleTypePattern` versus
`:1470` `TypePattern`, silent `catch` in both translators' `JavaParserAdapter`); an upstream
double patch is a recorded option outside this change's scope — the `Object` idiom does not
depend on it.

#### Scenario: Collapse detected from the artifact

- **WHEN** a specification declaring `byte[] iv` in its parameter list is generated
- **THEN** the generator exits 0 with the success message
- **AND** G-PARAM MUST fail by comparing the `.mop` header's parameter list with the empty list
  of the generated `.rvm`

#### Scenario: The Object idiom passes

- **WHEN** the same chain is declared with `Object iv` and the overload fixed in the
  `call(...)` signature
- **THEN** the `.rvm` header MUST carry the full parameter list
- **AND** the generated monitor MUST slice by `CachedWeakReference` on that parameter

### Requirement: Reformulated Scope of G-PRED and Retirement of `rvsec-mop-defsuses`

G-PRED (gh104) SHALL remain the byte-identity lock of the frozen `jca` predicate machinery and
SHALL stop applying to `jca_android`, whose predicate contract is carried by INV-INS-130/131/137
instead (INV-INS-141). The reformulation updates, in the same task, the collateral sites in
`gh104_gates.py` that assume the old substrate (`accept_requires`, which decides G-2 by grepping
`ExecutionContext`; the `PREDICATE_CALL` regex, blind to the new store and to arity N) and the
INV-INS-128 pytest; every hunk the rewrite produces lands in `divergence_record.csv` under a
kind its `KINDS` whitelist admits.

`rvsec-mop-defsuses` SHALL be retired: moved to `backup/` and removed from the reactor
`<modules>` (P3 — the module is dead: its `main()` points at an absolute path under an alias the
JVM cannot resolve, `DefsUsesGraph.java:65-66`, its extractor discards the object argument and
every negated read, and it knows nothing of the automaton). Its idea — def/use closure over
predicates — is exactly G-PRED2 over `predicate_graph.csv`, which carries everything the module
discards.

#### Scenario: The jca lock is untouched

- **WHEN** the migration completes and the gh104 gates run
- **THEN** G-PRED over `jca` MUST be green, byte for byte
- **AND** G-PRED MUST NOT run over `jca_android`
- **AND** G-2's `accept_requires` MUST recognize the new store's read sites

#### Scenario: The dead module is retired completely

- **WHEN** the retirement task completes
- **THEN** `rvsec/rvsec-mop-defsuses/` MUST be in `backup/` and absent from
  `rvsec/rvsec/pom.xml` `<modules>` (the only pom that lists it)
- **AND** `grep -r "defsuses"` over the reactor MUST return no reference outside documentation
  and the historical record (the measured survivors, updated or exempted declaredly: module
  CLAUDE.md rows, `docs/`, archived changes, the `check_no_legacy_mop.py` skip list, the
  retired copy under `backup/` — which the move itself creates inside the grepped tree, since
  `backup/` is tracked, not gitignored — and the active `gh48-project-finalization` artifacts,
  whose `defsuses` rows are that change's own to update)
- **AND** the reactor MUST build

#### Scenario: The gh104 successor-predicate requirement is superseded for the migrated set

- **WHEN** the first migrated specification lands (task 4.1) and the gh104 requirement "The
  Successor Set Carries the Predicates of Its Seed Unchanged" is evaluated against `jca_android`
- **THEN** its per-file count equality (summing to 134) MUST NOT be asserted any more — the
  departure is enumerated by `divergence_record.csv` (INV-INS-141) instead
- **AND** its "neither pure propagator receives a report site" scenario yields to the
  propagation-read rule of this delta (a propagation read is recorded, never armed)
- **AND** before this change archives, that requirement MUST receive its formal `MODIFIED`
  entry in this delta once gh104 has archived it into the main specification

## REMOVED Requirements

(none — no requirement of the main specification is removed. The `@fail` predicate removals in
the `jca_android` `.mop` files are code-level deletions governed by INV-INS-142. Nothing is
deleted from the old store: `ExecutionContext` stays byte-identical (INV-INS-132) and the frozen
`jca` still calls its one-argument `remove(Property)` overload at four sites — the new store
simply never offers those operations (INV-INS-131, absence not removal). `rvsec-mop-defsuses`
was never covered by a spec requirement.)
