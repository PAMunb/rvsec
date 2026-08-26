# Tasks: gh105-predicate-wiring

**What "complete" means here.** This change lands when tasks 8.1 to 8.7 are green. Tasks 8.8 and
8.9 are gated on gh104's archive, which follows the joint experiment in `experimento-gh104/`,
which in turn runs only after *both* changes land — so they cannot close inside this change's own
execution window, by construction and not by delay. Do not read an unchecked 8.8/8.9 as unfinished
work here.

**The change can be stopped at task 4.3.** The reach probe (design D-12) asks the one question
that voids this change: if `UnsatisfiedConstraint` stays at zero on the production path, the
weaver is a prerequisite and the wiring groups must not be started. It runs immediately after the
first migrated file, not at the end, so the kill switch fires before the expensive half.

<!--
Subagent dispatch (docs/WORKFLOW.md §5):
- Group 1 (substrate) and Group 2 (gate layer) are the critical path: everything else closes
  against them. 1 before 3-6; 2.1-2.6 AND 2.8 before Group 3 (3.x closes against the 2.8
  mapping); 2.11 MUST land before any `.mop` edit of Groups 3-6 — it snapshots the unmodified
  universe and archives the pre-change *specification-set directory* that task 8.4 diffs against;
  2.7 lands with 3.1 — the first migrated file is the trigger INV-INS-141 names, and it is
  a Group-3 file, not 4.1 (rescheduled 2026-08-20, ratified by the researcher: leaving the
  INV-INS-128 pytest red from 3.1 to 4.1 is the state D-13 exists to avoid);
  2.12 may run parallel to Group 3.
  gh104's Group 10 runs in the joint experiment (`experimento-gh104/`) after BOTH changes
  land — its 10.1 checkpoint therefore reads the pytest 2.7 rewrites (INV-INS-141), which is
  the intended final state, not a conflict.
- Group 3 (orphans) is independent of the mechanism decision and of Group 4 — parallelizable
  per-spec across subagents once 2.1-2.6, 2.8 and 2.11 exist. "Absorb" = the event enters the
  automaton's declared alphabet and keeps accusing, in whichever of the two forms INV-INS-135
  defines: self-loops at every state where the call is legal plus an ORDER-unmapped mapping row
  (erased before the G-ORDER comparison — INV-INS-138) when the rule's ORDER has no symbol for
  that call, or entry at the position the ORDER does name plus a `mapped` row to that symbol
  when it has one (`KeyPairGeneratorSpec.initError` → `i3`, ratified 2026-08-21 during task 3.6);
  "fuse" per INV-INS-135. The `gate_allowlist.csv` rows are owned by
  named tasks (`c3` by 3.1, `err2` by 3.5) so two parallel subagents cannot both claim the file.
- Group 4 is ONE PASS PER FILE, not four sequential sweeps: each file's reads, writes,
  accepting-state calls, divergence hunks and trace pair move together, because they are the same
  edit. 4.1+4.2 land as ONE atomic commit, before any other Group-4 file. 4.3 (reach probe)
  gates entry into Group 5. Files 4.4-4.14 are per-file parallelizable across subagents.
- Group 5 (wiring) is sequential by chain (topological order) and runs after Group 4 — 5.2/5.3
  consume the `ENCRYPTED` writes that the Cipher file pass relocates. Coupling exceptions: 5.10
  and 6.1 land in the same commit (ledger #32); 6.2's pointcut repair pairs with 5.9 (ledger #36).
- Group 6 (pointwise + removals) is per-spec parallelizable after Group 4, except the couplings
  above.
- Group 7 (records/retirement) after 5-6. Group 8 (verification) last, single session.
- EVERY `.mop` edit in Groups 3-6 produces divergence hunks against the frozen seed. Each task
  writes its own `divergence_record.csv` rows, KEYED BY HUNK (INV-INS-141 / design D-11), under a
  kind the recorder's `KINDS` whitelist admits — 2.7 adds the four new kinds. A task that edits a
  `.mop` and records nothing turns `test_jca_android_hunks_all_recorded` red.
- Java-side tasks run in the sibling reactor (JDK 21 prefix, /home/pedro/... paths — the
  /pedro/... alias does not resolve in the JVM). Every generation task checks the artifact,
  never the exit code, and records the heap (INV-INS-145).
- Commit messages NEVER carry `Co-Authored-By` or any co-author trailer (CLAUDE.md, Git
  Commits) — repeated here because subagents commit.
- Checkpoint rule: tick each box immediately on completion, before starting the next task.
-->

## 1. F0 — Substrate (rvsec-core)

- [x] 1.1 Create `PredicateVerdict` enum (`SATISFIED`/`VIOLATED`/`NOT_OBSERVED`) in
      `rvsec/rvsec-core/src/main/java/br/unb/cic/mop/` (design.md API Design). Done when the
      reactor compiles it and 1.3 can import it
- [x] 1.2 Create `PredicateStore` in the same package: holder singleton; identity-keyed weak
      object binding with `ReferenceQueue` purge; tracked-type (`String`/`int`/`Integer`)
      case-insensitive value positions; arity N; bound-first signatures
      `ensure/validate(Property p, Object bound, Object... values)` (a plain varargs head spreads
      reference arrays — measured); `negate` (object-scoped); `validateAbsent` (negated clauses,
      INV-INS-146); `reset` (test-only, the entry point INV-INS-148 requires). Not offered:
      `hasEnsuredPredicate`, property-wide remove (INV-INS-131)
- [x] 1.3 JUnit `PredicateStoreTest` in rvsec-core (JUnit 4, matching the module's existing test
      corpus): identity vs `equals` (two equal `SecretKeySpec`s), tracked-type matching (case,
      mismatch), arity ≥ 2, verdict semantics (entry+match / entry+mismatch / no entry),
      inverted table for `validateAbsent`, array-argument lands in `bound` whole (never spread),
      `negate` scoping, weak purge, concurrent access (~17 tests)
- [x] 1.4 Harness isolation (INV-INS-148, design D-14): `TraceRunner.replay()`
      (`rvsec/rvsec-mop/src/test/java/br/unb/cic/mop/harness/TraceRunner.java:227-230`) resets
      only `ErrorCollector` — the predicate singleton resolves through the parent class loader
      and survives every trace of a directory replay. Add `PredicateStore.instance().reset()`
      and `ExecutionContext.instance().reset()` beside the existing sink reset, and prove it with
      a cross-trace case in `TraceRunnerTest`: a satisfy trace followed by a violate trace in one
      replay, asserting the violation is still accused. Without this task every INV-INS-144 pair
      in Groups 3-6 is unsound evidence
- [x] 1.5 Freeze hardening: `ExecutionContext.java` untouched — assert byte-identity
      (`git diff` empty for the file) and add it to the freeze gate's `FROZEN_PATHS`
      (`tests/parity/test_gh101_specset_gates.py:50`, which holds two entries today); add the
      `Property` constants a wired clause needs (at least `PREPARED_KEY_MATERIAL`) append-only,
      with `test_property_append_only` asserting the pre-change constants and their **relative
      order** survive (INV-INS-132; zero `ordinal()`/`values()` uses measured — note the tree's
      precedent inserts mid-enum, so relative order of the pre-change set is the checkable claim)
- [x] 1.6 Build the reactor (`mvn clean install -DskipMopAgent -DskipTests`, JDK 21 prefix);
      run rvsec-core and rvsec-mop tests; confirm gh101/gh104 freeze gates still green
      (`uv run pytest tests/parity --import-mode=importlib -o "addopts="`, INV-INS-132)

## 2. Gate layer foundations (rv-android)

<!-- 2.1-2.3 build one analyzer in three passes; each is independently runnable and testable.
     Every gate script takes `--sets all|jca_android [--json]`, exits 0 iff no failure, and
     always reports passed/failed/skipped(reason). The universe is ENUMERATED, never a literal
     (INV-INS-140): 214 `.mop` today, 214 + junction specifications after Group 5. -->

- [x] 2.1 `scripts/gh105_predicate_graph.py`, pass 1 — the reader: comment/string
      neutralization, brace/paren matching, `alias` resolution, and the `(Property`
      discriminator that separates predicate sites from helper methods shadowing API names
      (`validate(int)` in `KeyPairGeneratorSpec`; collection `.remove(`). Unit fixtures for each
      neutralization case
- [x] 2.2 Pass 2 — the alphabet: `fsm`/`ere` event extraction including the reverse direction
      (events named in states but not declared, and declared but never named) and multiset
      handling. Fixtures: the two archived files whose `ere` names an undeclared event; the 17
      event-only `generic_new` files (no automaton at all)
- [x] 2.3 Pass 3 — the emitter: `data/jca_android/predicate_graph.csv` with the full 15-column
      schema of the delta's Output contract (incl. `guard`, `mechanism`, `polarity`,
      `disposition`, `reason` — the columns Groups 4-6 write into), placement classes per
      INV-INS-133/134, and the skip-and-count contract over the enumerated universe
      (INV-INS-140). Done when the CSV round-trips: re-running the analyzer over an unedited
      tree reproduces it byte-for-byte
- [x] 2.4 G-ACC (orphans, both directions) + placement checks + G-PRED2 closure + the junction
      rules (a)(b)(d) of INV-INS-136 — (a) `creation` on a consumer event declaration, (d)
      handler state outside the monitor's field block, (b) benign self-loop reachability over the
      declared automaton (design D-6: these are gated, not reviewed). Negative fixtures in
      `tests/parity/fixtures/`: `jca/GCMParameterSpecSpec.mop` (dup `c1`, undeclared `c2` —
      allowlisted, never repaired), event-only `generic_new` files (skipped), `generic` FSM246
      orphan (informative)
- [x] 2.5 `scripts/gh105_param_gate.py` (G-PARAM): `.mop` header vs generated `.rvm` header,
      artifact-only, never exit codes (INV-INS-139); fixtures for `byte[]`/`int[]`/`char[]`
      collapse and the `Object`-idiom pass, checked in as `.rvm` samples so the gate is testable
      before the first real generation
- [x] 2.6 Import-discipline gate (`grep -rlw 'ExecutionContext'` over `jca_android/*.mop` empty
      — INV-INS-130) and wire 2.1-2.5 into `tests/parity/test_gh105_predicate_gates.py` under
      the CI contract (`--import-mode=importlib -o "addopts="`), each gate registered against
      the 2.10 baseline — a forward dependency inside the group: the pytest wiring lands
      here, and the baseline registration closes only when 2.10 exists. Test names: `test_inv_ins_130_import_discipline`,
      `test_inv_ins_133_no_condition_reads`, `test_inv_ins_134_write_placement`,
      `test_inv_ins_135_gacc`, `test_inv_ins_136_junction_rules`, `test_inv_ins_137_gpred2`,
      `test_inv_ins_139_gparam`, `test_inv_ins_140_genericity` (no literal in the name — the
      universe grows in Group 5)
- [x] 2.7 Rescope G-PRED to the `jca` lock (INV-INS-141) — lands in the same commit as task
      3.1, the first migrated file, which is the trigger the invariant states. Collateral, all
      in the same commit: `gh104_gates.py` (`predicate_divergences` wiring,
      the `accept_requires` flag computed at `:1189-1190`, the `PREDICATE_CALL` regex at `:516`
      — both hardcoded to `ExecutionContext`); the INV-INS-128 pytest
      (`test_gh104_specset_gates.py:91`) and the census constants above it at `:41-52`
      (`PREDICATE`, `EXPECTED_CONSTRUCTS`, `EXPECTED_PREDICATE_LINES = 134`,
      `EXPECTED_SPECS = 23`); `test_gh104_structural_gates.py:229` (a third, `jca`-only G-PRED
      assertion — verify it survives the rescoping, do not delete);
      `gh104_message_gate.py::_clause_family:153` (classifies via `condition(...)` text, which F2
      empties); `experimento-gh104/scripts/preflight.py::check_no_predicates:158-179` (a second
      gate named G-PRED, opposite polarity, warn-only — retire it); and
      **`scripts/gh104_divergence_record.py`: add the four kinds this change produces
      (`predicate-store`, `placement`, `junction`, `predicate-removal`) to `KINDS:46-55`**, or
      every Group 3-6 row fails `check()` with `unknown kind` (design D-11). The `err2`/`c3`
      allowlist rows are NOT here: they are owned by 3.1 and 3.5
- [x] 2.8 Create `data/jca_android/order_alphabet_map.csv` (schema + rows for the specs Groups 3
      and 5 touch first, enumerated in the file's header comment so completeness is checkable
      before 7.1 closes it)
- [x] 2.9 `scripts/gh105_order_gate.py` (G-ORDER): DFA equivalence under the 2.8 mapping,
      `skipped` without rule or mapping, never inferred (INV-INS-138); SecureRandom
      `Ins, Seeds?, Ends*` as the first anchored case; wire `test_inv_ins_138_gorder` into
      `test_gh105_predicate_gates.py` (it is written after 2.6, so it registers itself)
- [x] 2.10 Expected-baseline mechanism (design D-13): the new gates are written before the edits
      that make them green, so each pytest wrapper asserts *no regression against the recorded
      baseline* at `data/jca_android/gate_baseline.json`, not *zero findings*. A spec's rows
      leave the baseline as its group lands. This is scaffolding with a demolition date (7.6),
      and it is NOT `gate_allowlist.csv`, which records permanent, justified findings
- [x] 2.11 Run the full gate suite over the unmodified universe; commit the baseline report at
      `data/jca_android/evidence/gate_baseline_report.md` (passed/failed/skipped counts — the
      genericity evidence for INV-INS-140, exercised by `test_inv_ins_140_genericity`) and the
      machine baseline at `data/jca_android/gate_baseline.json`; archive the pre-change
      **specification-set directory** to `backup/gh105-preimage/jca_android/` — that is the
      `--a` side task 8.4 feeds to `gh104_diff_harness.py`, which takes `.mop` set directories
      and regenerates the monitors itself
- [x] 2.12 Run `/rv-doc-code scripts/gh105_predicate_graph.py`,
      `/rv-doc-code scripts/gh105_order_gate.py` and `/rv-doc-code scripts/gh105_param_gate.py`

## 3. F1 — The 17 orphan accusers (9 specs): fuse the twins, absorb the rest

<!-- Per task: automaton edit + trace pair (satisfy/violate) + harness before/after delta +
     divergence_record.csv rows KEYED BY HUNK + order_alphabet_map.csv row for every absorbed
     event. 17 = 12 twin fusions (11 arrows) + PBEKeySpecSpec.err1 + 4 plain absorptions.
     What tells the two treatments apart is the orphan's body, not its guard: a body that
     accuses on its own is absorbed, a body that only rebinds a monitor field is a negated twin
     and is fused (design.md census, corrected and ratified 2026-08-20 during task 3.2). -->

- [x] 3.1 `SecureRandomSpec`: fuse `c3`→`c2` and `setSeed3`→`setSeed2` (twins; note `c3` accuses
      nothing today — its body only rebinds); absorb `g4`. Owns the `c3` row of
      `data/jca_android/gate_allowlist.csv:3` (`SecretKeySpecSpec.c3` justification cites a
      condition read this group removes — re-justify or drop it in this commit)
- [x] 3.2 `TrustManagerFactorySpec`: fuse `g3`→`g1` (negated twin over the same
      `call(getInstance(String)) && args(alg)`; its body only rebinds `currentAlgorithmInstance`,
      and the `-x509` harness snapshot shows the seed accusing `InvalidSequenceOfMethodCalls`
      twice — the published co-emission signature 9,015/9,014). Record the fusion residue (a
      rejected algorithm never followed by an `init` goes unaccused) as a `divergence_record.csv`
      row; do NOT move the algorithm check into `g1` — that is a behavioural change, deferred
- [x] 3.3 `IvParameterSpec`: fuse `c3`→`c1` and `c4`→`c2` (twins; `c4` is not an exact
      complement — it ignores `c2`'s offset/length constraints, so the fused body keeps both)
- [x] 3.4 `SecretKeySpecSpec`: fuse `c3`→`c1` and `c4`→`c2` (`c4` is the length complement)
- [x] 3.5 `PBEKeySpecSpec`: absorb `f1`, `f2`; fuse `err2` AND `err3` into `c1` (one arrow, two
      orphans) and `err1` as the tenth fused orphan, its iteration-count check decomposed per
      clause into the `c1` body — the three overlap today (one bad call fires up to three
      accusers; the fusion emits one report per violated clause). Declare the Kleene-prefix
      residue. Owns the `err2` row of `data/jca_android/gate_allowlist.csv:2`
- [x] 3.6 `PBEParameterSpecSpec`: fuse `c3`→`c1` (2-arg twin; the 3-arg `c2` read stays
      accuser-less until its Group-4 file pass); `KeyPairGeneratorSpec`: absorb `initError` (it
      accuses `InvalidKeySize` on its own); `SSLContextSpec`: fuse `unsafe_protocol`→`g1` and
      `SignatureSpec`: fuse `g3`→`g1` — both negated twins whose bodies only rebind a field,
      same treatment and same recorded residue as 3.2
- [x] 3.7 G-ACC green over `jca_android` (zero orphans, both directions), its baseline rows
      retired; harness evidence committed for all 17

## 4. F2 — One pass per file: reads to body, writes to acceptance, bookkeeping out

<!-- 27 reads over 10 specs, 49 writes over 21 specs, 25 accepting-state calls. These are ONE
     edit per file, not four sweeps: 4.4-4.14 each carry {reads to event bodies on the new store
     with accuser + code | writes relocated to the rule's ORDER acceptance point | accepting-state
     calls deleted | divergence_record.csv hunks | trace pair}. F2-window rule: until a read's
     producer lands in Group 5, the read is NOT_OBSERVED on every trace, so F2 pairs assert
     NOT_OBSERVED — the satisfy side is impossible inside the window, and the SATISFIED/VIOLATED
     pairs land per chain in Group 5. Per-file census (reads/writes/accepting-state) is stated in
     each task so completeness is checkable by a third party. -->

- [x] 4.1 `CipherSpec` (3 reads / 12 writes / 1 accepting-state call), the first migrated file:
      `i2`'s key-origin trichotomy stays ONE composite site emitting at most one report per
      violated clause (INV-INS-133); the `ENCRYPTED` writes relocate here (5.3's `validateAbsent`
      pair consumes them). Lands with 4.2 in one commit
- [x] 4.2 Add the *not observed* code family to `jca_android/codes.csv` and emit it from the
      first three-valued read; extend `gh104_message_gate.py` (INV-INS-143) — same commit as 4.1
- [x] 4.3 **REACH PROBE — the change's blocking condition (design D-12), gates Group 5.** One
      `rv-experiment`/`rv-platform` run over a sample APK instrumented with the 4.1 monitors (the
      platform owns the emulator lifecycle; never a manual emulator command). One question: does
      any predicate-derived report reach `errors.csv` — a `VIOLATED` or a *not observed* code
      through the gh104 envelope? Commit the verdict either way. **If `UnsatisfiedConstraint`
      stays at zero on the production path, STOP: the change is blocked and the weaver becomes a
      prerequisite (proposal Out of scope, design Non-Goals).** Do not start Group 5 on an
      unanswered probe
- [x] 4.4 `IvParameterSpec` (4 reads / 1 write / 1 call)
- [x] 4.5 `SecureRandomSpec` (4 reads / 6 writes / 1 call); the `end`-state `next2` omission is
      repaired here (6.3 carries the rest of the pointwise `Signature` work, this one rides its
      own file)
- [x] 4.6 `PBEKeySpecSpec` (measured census after task 3.5: 2 body reads / 1 write / 1 call /
      1 removal). Its `remove()` — the `clearPassword` withdrawal, the set's one real `NEGATES`
      translation — IS translated here to `PredicateStore.negate`, brought forward from 6.5
      (researcher, 2026-08-21): the write it withdraws changes substrate in this pass, so
      splitting the two would leave the predicate ensured on one store and withdrawn from the
      other in between, and INV-INS-130 asks the migrated file to name no other substrate. The
      `ENSURES` write stays in `c1`'s body with a recorded reason — api30 qualifies the clause
      `after c1`, and an `ere` has no way to name the state after an event (its only alias is
      `match`, over the accepting states, which here is the state after `c2`) — and rises to the
      rule's arity
- [x] 4.7 `PBEParameterSpecSpec` (3 reads / 1 write / 1 call); the 3-arg `c2` read gains its
      accuser here (`randomized[salt]`)
- [x] 4.8 `GCMParameterSpecSpec` (2 reads / 1 write / 1 call); `c1`/`c2` gain their accusers
      (`randomized[src]`)
- [x] 4.9 `MacSpec` (2 reads / 2 writes / 1 call / 1 removal). Three researcher decisions,
      2026-08-21, each measured before it was taken; after this pass the file names no predicate
      at all and loses all six of its `predicate_graph.csv` rows. **The `i1`/`i2` reads are
      deleted, not recorded as `propagation`** — this reverses the instruction this task carried.
      The Mac rule does not require `generatedKey` (its REQUIRES are `preparedHMAC[params]` and
      the two `!encrypted`), and unlike the three reads that earn the label, `i1`/`i2` feed no
      write, so deleting them and moving them to the body without an accuser are behaviourally
      indistinguishable; the difference is dead code and two graph rows. The guard is not inert:
      measured, it turns a program that breaks no clause into a `MAC-ORDER-00` and hides
      `MAC-ALG-00` behind the same suppressed transition. The rule's real clauses arrive at 5.2
      and 5.3. **The two `GENERATED_MAC` writes are deleted** — the property is written in three
      sets and read in none, and it does not translate `macced[output1, inp]`, which is arity 2
      where `GENERATED_MAC` holds only the output; the real producer is ledger #8 at 5.7, and
      migrating the write would hand that edge a second producer (precedents: `WRAPPED_KEY` at
      4.1, the `ints` write at 4.5). The `remove(GENERATED_MAC)` in `@fail` goes with the write it
      withdraws (precedent 4.6), which is why 6.4 performs seven of INV-INS-142's eight.
      **The `@match` handler and the `mac` field are deleted whole** — the handler carried only
      `setObjectAsInAcceptingState(mac)` (INV-INS-147) and the field served only it; 5.7 recreates
      a handler when it has something to write, at arity 2 over `output` and the data, not over
      `mac`. What stays: the `MAC-ALG-00`/`-01` bodies, `q(...)`, `ConscryptAliasTable`, and the
      `g3*` order defect, which belongs to the automaton and is recorded, not repaired
- [x] 4.10 `SecretKeySpecSpec` (1 body read / 1 acceptance write / 1 call; the pre-change census
      of 2 reads counted the twin `c3`'s guard, which task 3.4 removed when it fused the pair).
      The pass that closes the **last open F2 window**: the `c1` read of `randomized[keyMaterial]`
      moves to the new store and becomes three-valued, and its producer `SecureRandom` moved at
      task 4.5, so a construction over genuinely randomised material stops being accused of not
      being randomised (measured: one report becomes none). The read keeps testing `RANDOMIZED`
      where the rule requires `preparedKeyMaterial`; that conflation is ledger #32, undone at
      5.10+6.1, and is recorded here rather than repaired.
      Two researcher decisions, 2026-08-21, each measured before it was taken. **The `@match`
      write moves store but NOT arity**: api30 states `generatedKey[this, alg]` at arity 2, and
      the write stays at arity 1 with a recorded reason, rising at 5.6 with its consumer.
      Measured on `PredicateStore` itself — an `ensure` at arity 2 read by a `validate` at arity 1
      returns `VIOLATED`, not `NOT_OBSERVED` — so raising it alone would make every
      `SecretKeySpec`-created key given to `Cipher.init` draw `CIPHER-CONSTR-00`, a positive
      accusation about a conforming program, until 5.6 lands. At arity 1 it instead closes a
      **second** window: `CipherSpec.i2` goes from `NOT_OBSERVED` to `SATISFIED` for such keys,
      the first time that read can tell an observed key origin from an unobserved one.
      **The rule's other `ENSURES`, `speccedKey[this, _]`, is not written here**: its consumer
      `SecretKeyFactory` has no `.mop` in the set, ledger #31 already disposes the chain as
      `unmonitored-consumer` at 5.10, and `PBEKeySpecSpec` already produces the predicate, so a
      second producer for a chain with no consumer at all would be a site with no purpose
- [x] 4.11 `RandomStringPassword` (2 reads / 2 writes / 0 calls). **All four sites are deleted,
      not migrated** — this reverses the instruction this task carried, which was to record the
      two reads as `propagation`. Two researcher decisions, 2026-08-21, both measured before the
      edit (finding 47). The file is the set's only dataflow bridge: it exists to carry
      `RANDOMIZED` across `Object` → `String` → `char[]`, because `PBEKeySpecSpec.c1` is the only
      read of that predicate over a `char[]` and nothing else in the set produces one.
      **The bridge does not carry what it stamps.** `String.valueOf(Object)` calls
      `Object.toString()`, measured over each of the three source types the set can hand it: a
      `byte[]` becomes its identity string (`[B@726f3b58`), the `SecureRandom` itself becomes the
      constant `SecureRandom`, and only an `Integer` becomes its own digits — and that one dies on
      the new store, whose bound key is identity, since the box at the `ensure` and the box at the
      read coincide only inside the `Integer` cache (−128..127), where `next1`'s value is the
      *bound argument* rather than the random result. The two types that propagate carry no
      randomness; the one that carries randomness does not propagate. On the frozen seed this is a
      false **negative**, measured: a `PBEKeySpec` built from the `char[]` of `[B@6ae40994` draws
      nothing at all. Deleting the four sites moves no observable behaviour of the migrated tree —
      the bridge is already inert there, its reads on the old substrate while its producers moved
      at 4.5 — so the pass costs the set nothing and stops it asserting a fact the conversion does
      not support. The file keeps its two events, its `ere` and its empty `@match`, and leaves
      `predicate_graph.csv` whole, as `MacSpec` did at 4.9. **The `@match` is NOT deleted**,
      unlike 4.6 and 4.9: measured, the JavaMOP grammar requires at least one handler after the
      `ere` (`RVParser.propertyHandler`; generation fails with `ParseException: Encountered
      "<EOF>"`), so an empty handler is the only legal way to state an automaton with nothing to
      report. No `codes.csv` line is added or moved: this file has none, and gains none, because
      a propagation site never earns an accuser. The pass also repairs the harness it needed:
      `TraceRunner.fitsPointcut` refused an `Integer` against every declared reference type, which
      the assignability test below it already decides for the `initialize` case the docstring
      cites, and which blocked the one pointcut of the set's 112 that declares `Object` — the
      bridge's own. Measured inert: 0 outcome changes over the 92 committed traces on both
      snapshots, with a new test pinning both directions
- [x] 4.12 `SecretKeySpec` (1 read / 1 write / 0 calls); `e1` is **propagation** (no `REQUIRES`
      section) — no accuser. The set's **last** `condition(...)` read, so INV-INS-133 reaches zero
      here. Three researcher decisions, 2026-08-21, each measured before the edit over the whole
      `ErrorCollector` across six trees — three real and three written inline between the starting
      tree's own dispatchers (learning 51), a simulation afterwards confirmed configuration by
      configuration against the real migrated tree. **The read stays, governing the write.** api30
      SecretKey states `ENSURES preparedKeyMaterial[keyMaterial] after ge` and no `REQUIRES`
      section at all, so the literal shape would delete the read and make the write
      unconditional; measured, that does close the `KeyGenerator` chain immediately and **loses a
      true accusation** — a hard-coded key's encoding is handed on as randomised and the IV built
      from it stops being accused. Deleting both sites, the disposition of 4.9 and 4.11, was
      measured too: nothing closes, and the set loses its only bridge from a key to its encoding.
      **What the pass buys** is the chain from `SecretKeySpecSpec`: `getEncoded()` returns a fresh
      clone on every call, measured, so no identity-keyed store can see the material through the
      copy and this event is the only thing in the set that bridges it — key material an observed
      `SecureRandom` filled now reaches `IvParameterSpec` as randomised for the first time, one
      report to none. **What it costs** is a window against the other two producers of
      `generatedKey` (`KeyGeneratorSpec.mop:80`, `KeyStoreSpec.mop:83`), which task 4.14 owns —
      and that window is measured to change no report at all, because the write it suppresses went
      to a store no reader of `randomized` has used since task 4.4. It is the tenth `introduced`
      row of the harness and the first that is a window rather than a repair, and the report says
      so. The write sits in `@match`: the clause's `after ge` states and the `ere`'s accepting
      states are the same single state here, read off the generated monitor's transition row
      `{0, 1}`, so both routes INV-INS-134 admits name the same handler, reached through a staged
      field because a handler sees no event parameter. The `randomized` × `preparedKeyMaterial`
      conflation is ledger #32, recorded and not repaired — 5.10 with 6.1 owns it, exactly as task
      4.10 recorded it at the reading end, and renaming it here alone would leave this producer
      writing what none of the seven migrated readers of `randomized` over a `byte[]` ask for.
      Arity needs no exception: the clause is one-place and the readers read one-place. Three
      traces committed — `-encoded-iv` is the chain that closes, `-keygen-iv` the window,
      `-hardcoded-iv` the violating control that decided the disposition — each replayed on all
      three snapshots. `codes.csv` gains nothing: a propagation site never earns an accuser
- [x] 4.13 Write-only specs, batch A (11 writes / 6 calls): `SignatureSpec` (4 writes),
      `MessageDigestSpec` (3), `SSLContextSpec` (2), `KeyPairSpec` (2). **Nine** of these eleven
      sites belong to `ENSURES`-only dead ends and carry a deliberate-omission record for their
      absent reader (INV-INS-137); no read is fabricated for any of them. The "seven" this task
      carried was `design.md`'s count of seven dead-end **predicates** over eleven **sites**
      spanning five files (`SignatureSpec` 4, `MessageDigestSpec` 3, `SSLContextSpec` 2,
      `PBEParameterSpecSpec` 1 at task 4.7, `KeyPairGeneratorSpec` 1 at task 4.14), pinned by
      mistake to this task's own, different eleven; the design is right and the task was wrong.
      Measured: no rule of api30 requires `signed`, `verified`, `digested`, `generatedSSLContext`
      or `generatedSSLEngine`, and no `.mop` of any set reads the five `Property` constants —
      the only non-write occurrence anywhere is an unmaintained 2026-08-08 audit driver. The
      other two sites, `KeyPairSpec.gpu`/`gpr`, have a live reader (`CipherSpec.i2`, on the new
      store since 4.1) and close a chain: measured over the whole `ErrorCollector`, one
      `CIPHER-NOBS-00` to none. Three researcher decisions (2026-08-22). The two `KeyPairSpec`
      writes stay in the **event body** with a recorded reason, because the `ere` demands the
      constructor api30 marks optional (`co?, (pu*, pr*)*`) and the accepting state is therefore
      unreachable on the route by which a program obtains a KeyPair — measured, an
      acceptance-point write leaves that program at 2 reports instead of 1; the automaton repair
      is task 7.1's and is already recorded as measured-not-repaired at 668 corpus rows over 8
      apps (gh104 8.12(f)), and the writes move to `@match` when it lands. `gpr` writes
      `GENERATED_PRIVATE_KEY` as its clause names, taking the first half of task 6.1 with it.
      `v1`/`v2` write the `byte[]` that `verified[sign]` names instead of the returned boolean,
      which an identity-keyed store would have recorded against the JVM-wide `Boolean.TRUE`.
      The `TraceRunner.produce()` repair rides with this task, in the shape of decision 31: a
      non-public `KeyPairGenerator$Delegate` made every `generateKeyPair()` binding silently
      null, so the chain had no committed witness — measured, zero of the 97 committed traces
      change and `TraceRunnerTest` stays at its two pre-existing failures. Evidence:
      `data/gh105/evidence/f2-write-only-batch-a.md`
- [x] 4.14 Write-only specs, batch B (10 writes / 11 calls): `KeyStoreSpec` (2),
      `KeyManagerFactorySpec` (2), `TrustManagerFactorySpec` (2), `KeyGeneratorSpec` (1),
      `KeyPairGeneratorSpec` (1), `DHGenParameterSpecSpec` (1), `HMACParameterSpecSpec` (1).
      The last seven files of the group, and the pass that takes three counters to zero: the
      accepting-state calls (INV-INS-147, the last 11 of 25), the `ExecutionContext` mentions
      (INV-INS-130, these seven plus two dangling imports in `CipherInputStreamSpec` and
      `CipherOutputStreamSpec` that no 4.x task covered), and the `@fail` removals. Like task
      4.13 no file declares a read, so the question is again who reads the write; unlike 4.13
      the answer is rarely nobody — two writes have a live reader (`CipherSpec.i2`,
      `SecretKeySpec.e1`), five have one scheduled (ledger #14/#36 and #28/#29 at 5.9, #17 at
      5.8, #21 at 5.2), and three are dead ends. Eight writes go to the acceptance point; the
      three `after L` clauses land on the same state as their `@match`, so the handler is both
      routes at once. **Two stay in the event body with a recorded reason** —
      `KeyManagerFactorySpec.gkm1` and `TrustManagerFactorySpec.gtm1`, whose transition rows
      ({3,3,0,3} and {3,0,3,3}) leave the accepting state for `start`, so an acceptance-point
      write would not merely be worse, it would never run: measured, `validate` answers
      NOT_OBSERVED under that placement and SATISFIED under this one, and it is exactly what
      ledger #28 reads at 5.9. Task 7.1 owns the automaton and both writes move with it. The
      probe row that decided the other eight points the opposite way from task 4.13's: the
      acceptance point is reachable on the common route (rows A and B both reach zero reports),
      and the one program the placements separate is one the rule itself rejects — two
      `generateKey()` on one generator — where the acceptance point is what CrySL states and
      the extra report is true. **The F2 window task 4.12 opened is closed and witnessed at both
      producers**: `SecretKeySpec-keygen-iv.txt` leaves `introduced` for `unchanged` and the
      harness goes 10 `introduced` to 9, while `KeyStore.getKey()` — which had no witness —
      gains `KeyStoreSpec-getkey-iv.txt`, measured on the seed before the edit and replayed on
      all three snapshots. Six researcher decisions (2026-08-22). The seven `@fail` removals
      travel here instead of 6.4 by decision 11's criterion (each undoes a write this task
      migrates, as at 4.6 and 4.9): `PredicateStore` offers no removal, no reader of any
      predicate remains on the old substrate so deleting them changes no report, and leaving
      them would keep INV-INS-130 off zero and block 4.15. `gtm1` writes `GENERATED_TRUST_MANAGER`
      as its clause names instead of the neighbouring rule's constant, which costs nothing
      measured — no set reads either, and the advice has no execution path at all, its pointcut
      declaring `getTrustManagers()` returning `KeyManager[]` (gh104 8.7, task 6.2's). Three
      deliberate-omission records, per site: `generatedKeypair` — the eleventh and last of the
      sites `design.md` lists for its seven dead-end predicates, after which every one is
      disposed of — and the two `[this] after Init` halves the oracle ensures on the factory and
      no rule asks for there. Evidence:
      `data/gh105/evidence/f2-write-only-batch-b.md`
- [x] 4.15 Placement gates green, baselines retired: zero `condition` reads in `jca_android`
      (INV-INS-133), `test_inv_ins_134_write_placement` green — every write at acceptance or
      carrying its recorded `reason` in `predicate_graph.csv`, import-discipline green
      (INV-INS-130), zero `set/unsetObjectAsInAcceptingState` in the set (INV-INS-147, all 25
      gone), trace pair committed per moved read.
      Every one of the five was already satisfied when the task opened, by tasks 4.12 and 4.14
      and not by this one, and each was re-derived from the tree rather than read off a gate:
      the guards and the accepting-state calls by `grep` over the 23 `.mop` files beside the
      gate that counts them, the seven surviving `write:body` rows by checking each carries a
      non-empty `reason`, and the trace pairs by naming, per moved read, the committed trace
      that satisfies it and the one where it is not observed. Thirteen of the fourteen reads
      have such a pair; the fourteenth is `PBEKeySpecSpec.c1`'s `randomized[password]`, whose
      satisfying side no trace can express — the `String.valueOf(Object)` → `toCharArray()`
      chain the `TraceRunner` cannot replay, measured at task 3.5, and whose only producer task
      4.11 then deleted. That is a recorded absence, not an unchecked item.
      What the checking found to *do* was the second half of the title. Three gates had reached
      zero and their keys had simply vanished from `gate_baseline.json`, because `--write`
      records what a gate reports; none of them had entered `retired`. Measured by handing
      `retire()` a payload that pretends each gate found something, a regeneration on a drifted
      tree would have silently re-recorded INV-INS-133, INV-INS-134 and INV-INS-130 while
      refusing G-ACC — the one failure the mechanism exists to prevent (`8fdf73fd`). All three
      are now retired with `task: "4.15"`, `was:` the count each reported on the unmodified tree
      (27, 42, 23) and a note naming the pass that closed it. G-PRED2 is deliberately left in
      `gates`: its rows are Group 5's live expectation and task 5.11 closes them. (The count
      written here as "ten" was wrong when 4.15 wrote it — the baseline and the gate both held
      **nine** — and tasks 5.2 and 5.3 took it to **six**, so no literal is recorded in its place.)
      Collateral: `test_a_retired_gate_leaves_the_baseline_and_stays_out` now asserts all four
      retirements plus the negative half; three wrapper docstrings that stated numbers the tree
      contradicts were corrected; the three censuses gained the line saying this task moved no
      counter. No `.mop` was edited, so there is no divergence hunk, no new trace and no graph
      row. Evidence: `data/gh105/evidence/f2-placement-gates-retired.md`
- [x] 4.16 Run `/rv-test-run tests/parity` (gh104 + gh105 gates together).
      152 passed, 3 failed over the 155 tests the directory collects — the four gate suites are
      only 94 of them. The three reds are pre-existing and none is this change's, which was
      measured and not argued: the four files task 4.15 edits were reverted to `HEAD`, the same
      selection re-run, and the same three failed with the same messages.
      `test_baseline_freshness` (the GATOR jar is newer than the `cryptoapp.apk.json` baseline —
      gh60 task 11.8), `test_no_legacy_mop` (six `reachesMop` occurrences in
      `modules/aperv-tool/`) and `test_sentinel_emission` (`StaticAnalysisParser.parse_file()`
      takes 2 positional arguments and the test passes 3).
      The run also measures defect D1 of
      `docs/20260821_relatorio_analise_estatica_defeitos.md` from a new angle: **without**
      `ANDROID_SDK_HOME` exported the same suite reads *3 failed, 145 passed, 7 errors*, the
      extra eight being `KeyError: 'ANDROID_SDK_HOME'` in `test_reachability_parity`,
      `test_sentinel_emission` and `test_signature_file_subset`. Exporting it turns eight of the
      nine green. The default reading of `tests/parity` is therefore the harsher one, and that is
      worth knowing before anyone reads a red as a regression

## 5. F3 — Wire the 21 wired REQUIRES clauses, record the rest (topological)

<!-- Sequential by chain; every task resolves against design.md's 36-clause ledger, never
     against family names. Every edge task = producer write at the acceptance point
     (INV-INS-134) + consumer read (or junction spec per INV-INS-136) + accuser + trace pair
     (SATISFIED and VIOLATED) + predicate_graph.csv row with the clause pointer + divergence
     hunks. Junction specifications are new `.mop` files in
     `rvsec/rvsec-mop/src/main/resources/jca_android/`, named `<Chain>Junction.mop`; each one
     grows the enumerated universe, which is why no gate may hold a literal count.
     CipherSpec is at 17/17 events — ZERO headroom (INV-INS-145): no task may add a CipherSpec
     event; every new Cipher binding routes through a junction spec or the store. Cipher
     alphabet: generate in the real pipeline, record heap. -->

- [x] 5.1 Pilot chain in production: `IvChainJunction.mop` (`SecureRandom → byte[](Object idiom)
      → IvParameterSpec → Cipher`), ledger #9/#12; rules INV-INS-136(a-d) green under 2.4;
      G-PARAM green; the pilot's four fixture traces become committed pairs, including the
      rule-violating negative fixtures for (a), (b), (d).
      **Executed as mechanism A (the store), not B**, on three measurements and four ratified
      decisions (2026-08-22). Ledger #12 (`randomized[iv]`) was already wired store-side by task
      4.4 with its producer at 4.5, so a junction accuser at the wrapping event would be a second
      accuser of one clause, which the ledger forbids; only #9 had a producer and no reader. The
      pilot's `fsm` draws six INV-INS-136(b) findings under the gate as written — the gate demands
      totality over the alphabet where the invariant asks only for the states a disconnected join
      can reach — and made total its fail state is unreachable in the generated transition table
      (`Prop_1_transition_use` sends state 0 to state 0), so a gate-conformant junction cannot
      accuse through `@fail` at all. And a junction with no store call yields no
      `predicate_graph.csv` row, because rows are derived from the `PredicateStore` call text, so
      it closes no G-PRED2 line. The file is separate from `CipherSpec` because the clause binds
      `params`, `i2` stands for the rule's i3–i8 under `args(mode, key, ..)` and binds no third
      argument, narrowing it would drop the two-argument initialisations out of the automaton, and
      the alphabet is at 17 of 17 (INV-INS-145). It states no ORDER of its own, so `ere : use*`
      never fails and no ORDER code exists; the four gh104 structural findings that follow from
      that are allow-listed on the `SecretKeySpec` precedent, with the difference recorded — those
      are legacy artefacts, these are the design.
      **The pilot's fixtures do not transfer, and the count in this task was wrong**: the pilot
      has three drivers of three scenarios each and four spec variants (E1–E4), not four traces;
      rule (c) fails at generation and rule (d) at monitor-compile time, so neither has a trace
      fixture at all; and with #9 wired store-side, (a) and (b) have no subject in this pass.
      What is committed instead is a satisfy/violate pair plus a guard-false control, all three
      replaying whole against the pre-image, the edited tree and the frozen snapshot: the
      unprepared trace goes from 1 report to 2, the decrypt trace stays at 1, and the conforming
      trace stays silent. The guarded clause's antecedent is evaluated in the event body ahead of
      the read, which makes this the first row of `predicate_graph.csv` to carry a `guard`.
      Cost declared: the cascade `IvParameterSpec.mop` named at task 4.4 as its open question —
      `@match` there prepares only on SATISFIED, so one reach limit on the iv is now reported
      twice, at the construction and at the init. The alternative, preparing on NOT_OBSERVED, was
      put to the researcher and refused as a behavioural change to a ratified decision.
      Evidence: `data/gh105/evidence/f3-IvChainJunction.md`
- [x] 5.2 `Mac` chain, positive: `preparedHMAC[params]` (ledger #21 — the rule's real clause;
      Mac does not require `generatedKey`, confirmed against `Mac.cryptsl`: it appears in no
      REQUIRES, no CONSTRAINTS and no ENSURES).
      **Recorded, not wired** (researcher decision, 2026-08-22), on three measurements. The site
      exists — `MacSpec.i2` binds `params` directly, so the separate-file question task 5.1 had to
      answer does not recur — but no program can compose the clause's two ends. The producing
      class is `javax.xml.crypto.dsig.spec.HMACParameterSpec`, of the `java.xml.crypto` module,
      and the api30 `android.jar` carries `javax/crypto/Mac` and `javax/crypto/spec/PBEParameterSpec`
      and **no entry whatever under `javax/xml/crypto`**: on the platform this set targets the
      producer cannot be loaded. On a JVM, where it can, no `Mac` accepts it — measured over the
      twelve algorithms of the rule's own allow-list on Temurin 21, the six `Hmac*` answer "HMAC
      does not use parameters" to every parameter object, the five `PBEwithHmac*` take
      `PBEParameterSpec` only, and `PBEwithHmacSHA`, which the allow-list names, does not exist.
      `i2` is an `after` advice, which is after-finally, so the only program that could reach a
      read with the predicate present is one raising `InvalidAlgorithmParameterException` at that
      call. A read would answer `NOT_OBSERVED` on every conforming two-argument `init`, the shape
      of the seventeen orphan accusers Group 3 removed. The record is carried by the producer's own
      row in `predicate_graph.csv` at `disposition=omission`, which is how its G-PRED2 line closes
      **without a reader** — the first time in this change that a recorded clause retires a gate
      line. This task adds no graph row and no code.
      **The task statement was wrong in two labels**: it calls 4.9's deleted reads "propagation
      reads", which 4.9's own evidence had already corrected, and "re-derived" suggests
      restoration; nothing was restored, and the pass reads a different predicate at a different
      event on a different object — or rather, reads nothing at all.
      **Found and recorded, not repaired**: `HMACParameterSpecSpec.mop` instruments a class absent
      from Android, so one of the set's 24 specifications cannot fire in any APK. Recorded in
      `conformance_record.csv`; whether it should leave the set is a change of scope.
      Evidence: `data/gh105/evidence/f3-MacChain.md` (with task 5.3, one commit)
- [x] 5.3 `Mac` chain, negated: `!encrypted[output1,_]` and `!encrypted[output2,_]` (ledger
      #22/#23) via `validateAbsent` (INV-INS-146); producer = the Cipher `ENCRYPTED` writes 4.1
      relocated to acceptance.
      **"Two sites, one predicate" was the wrong count**: the two clauses have one realisable site
      between them, and the `.mop` alphabet does not map to the rule's by name. `MacSpec.f1` merges
      api30's `f1: output1 = doFinal()` and `f2: output2 = doFinal(input)` under one pointcut
      disjunction and binds the array the call **returns**, which the JCA allocates fresh every
      time — measured on Temurin 21 over HmacSHA1, HmacSHA256 and HmacSHA512, a returned tag is
      never the ciphertext object beside it. Since `validateAbsent` never answers `NOT_OBSERVED`
      (absence is conformance), a read there could answer only `SATISFIED`: a site with no path to
      an accusation, which decision 19 deletes rather than writes. So **#23 is recorded vacuous in
      full, with the returned half of #22**, and #22 keeps its second site: `MacSpec.f2`, which is
      api30's **`f3: doFinal(output1, outOffset)`** — the one event of the rule whose `byte[]` the
      caller owns.
      **The site did not match, and the repair travels with the clause** (researcher decision,
      2026-08-22, on the 6.2↔5.9 precedent). The event declared `target(m)` while naming no `m`
      among its formals — the empty-binding broadcast of `conformance_record.csv:67` item (c) — so
      the generator gave it the specification's parameterless map and it landed on a root monitor
      that had seen no `getInstance`, which the `ere` rejects. **It was therefore a false accuser**:
      measured on the three traces this task adds, against the pre-image, this tree and the frozen
      control alike, all three drew `MAC-ORDER-00` at this event, the conforming one included.
      After the repair `MacSpec__Map` is gone from the generated monitor, `MacSpec_f2Event` takes
      `Mac m`, and the conforming trace is silent. No trace of the existing corpus reaches this
      event, so the repair moves nothing already measured.
      Delivered: the set's **first `validateAbsent`** and first `polarity=negated` row, with
      `MAC-CONSTR-00`. The verdict is two-valued by construction, so no NOBS code stands beside it
      and its absence is not an omission under INV-INS-143.
      **Cost declared**: `Cipher.cryptsl` states `encrypted[cipherText, plainText]` with no guard
      on `encmode`, so a decrypting Cipher marks its output the same way and a Mac writing into it
      is accused although nothing was destroyed. `MacSpec-decrypt-buffer.txt` witnesses it. The
      imprecision is the oracle's; the rule's third clause, `encrypted[cipherBuffer, plainBuffer]`,
      has no write in the set, so a Mac over that buffer is not caught.
      Evidence: `data/gh105/evidence/f3-MacChain.md` (with task 5.2, one commit)
- [x] 5.4 `randomized` hub A (ledger #11, #24, #25): `GCMParameterSpec` `randomized[src]`,
      `PBEKeySpec` and `PBEParameterSpec` salts; junction where co-observable, store where not,
      mechanism recorded per chain in `predicate_graph.csv`.
      **All three were already wired, and the task's work turned out to be elsewhere.**
      `GCMParameterSpecSpec.c1/c2`, `PBEKeySpecSpec.c1` and `PBEParameterSpecSpec.c1/c2` have read
      `RANDOMIZED` off the store since the Group 4 file passes (4.6, 4.7, 4.8), all by mechanism A;
      the identity that closes the chains was measured rather than assumed — `nextBytes` fills the
      caller's array, so the object the constructor receives is the one `SecureRandomSpec.@match2`
      marked (achado 73).
      What the pass did instead was **delete a read**: `PBEKeySpecSpec.c1` also read `randomized`
      over the `password`, a clause api30 does not state. Measured against the oracle, `randomized`
      is ENSURED over four objects only (`this` at SecureRandom, `genSeed`, `next`, `numB`), none of
      them a `char[]`, and none of the set's six writes binds one either — so the read could answer
      only NOT_OBSERVED, and `PBEKEYSPEC-NOBS-00` fired at every construction of a PBEKeySpec, the
      conforming ones included. It also cleared the flag gating the `speccedKey` write, so that
      write had never run for any program in any set. The read and its two codes are gone
      (researcher decision, 2026-08-22); the sibling codes keep their numbers, because a code is an
      identifier in measurements already published. Measured: `PBEKeySpecSpec-conforming.txt` and
      `-salt-only.txt` both go silent, and the two `RandomStringPasswordSpec` traces leave the
      harness's `introduced` class, taking it from 9 to 8.
      Evidence: `data/gh105/evidence/f3-RandomizedHubAndGuardedPrepared.md` (with 5.5 and 5.8, one commit)
- [x] 5.5 `randomized` hub B (ledger #13, #33, #6, #30): `KeyGenerator` (**not**
      KeyPairGenerator), `SecureRandom` self-chain, `Cipher.init` `ranGen` (store-side — zero
      CipherSpec events); `SSLContext randomized[sr]` (#30) recorded `vacuous` — `Init:
      init(kms, tms, _)` binds `sr` in no event, so it can have no read site; drop the autoboxed
      argument writes (`SecureRandomSpec.next1/next3` mark the int argument today).
      **Zero CipherSpec events held, and the site count did not.** #6 and #13 cost seven events
      between them, and the number is the measurement's rather than the clause's: api30 binds
      `ranGen` in four `Cipher.init` overloads and three `KeyGenerator.init` overloads, and all
      three shorter statements of the pointcut fail. A disjunction of the signatures makes javamop
      write `null` to stderr and emit no aspect at all, though every `.rvm` of the set generates
      first — bisected against the HEAD set and the pre-image, which generate clean. The one-event
      `args(.., ranGen)` form generates and, measured on three probe traces against the monitor it
      produces, matches every `init` whatever the last argument's type, binds no SecureRandom and
      answers NOT_OBSERVED for all of them, including an `init` whose SecureRandom had just been
      observed — an accuser of everything that passes through it. And a wildcard in a middle
      position generates a correct aspect, since AspectJ resolves the signature statically, but
      defeats `TraceRunner.fitsPointcut`, which accepts any call from the first wildcard onward:
      measured on the corpus, task 5.1's conforming traces drew a report they must not draw. A
      wildcard is safe only after every discriminating type. The four Cipher reads live in
      `IvChainJunction.mop`, which gains no `CipherSpec` event; the three KeyGenerator reads are a
      **split** of the merged `init`, which stood for all five overloads and bound none of their
      arguments, so the clause had no site at all — the `ere` accepts any of the four symbols
      wherever it accepted the merged one, and no ordering claim moves.
      #33's constructor half went to `SecureRandomSpec.c2`, the site task 3.1 named as this task's
      in the file itself, and needed no new trace: `SecureRandomSpec-seeded-constructor.txt` and
      `-unrandomised-constructor.txt` were already in the corpus and separate the verdicts.
      Evidence: `data/gh105/evidence/f3-RandomizedHubAndGuardedPrepared.md` (with 5.4 and 5.8, one commit)
- [x] 5.6 `generated*key` family A (ledger #5, #15, #16): producers at acceptance; consumer
      `Cipher.init` `generatedKey[key, part(0,"/",transformation)]` (arity-2, splitter applied
      by the caller, store read replacing the `i2` guard — zero new events); `KeyPair`
      `generatedPrivkey`/`generatedPubkey`. **Two of the four producers this task named do not
      exist as it named them, and the tree wins.** There is no `SecretKeyFactorySpec.mop` — the
      set has 24 files and none is that one, which task 4.10 had already recorded — and
      `KeyPairGenerator` produces `generatedKeypair[kp, alg]`, a different predicate that #5, #15
      and #16 do not read; its write has been at the acceptance point since 4.14 and is a dead
      end. The producers of `GENERATED_KEY` are **three**: `KeyGeneratorSpec`, `SecretKeySpecSpec`
      and `KeyStoreSpec`, and all three rise to the rule's arity in this commit with **both**
      readers — `CipherSpec.i2` and, the one this task did not name, `SecretKeySpec.e1`. That
      second reader translates no clause and governs a write instead of a report, so left at
      arity 1 it would answer `VIOLATED` for every observed key, stage nothing, and break the
      set's only dataflow bridge **in silence**. `KeyStore` writes `generatedKey[key, _]`, whose
      second place is the oracle's anonymous variable; the store has no wildcard, so the site
      writes the key's own algorithm and the departure is recorded (researcher decision,
      2026-08-22). What licenses it is measured: the JCA itself refuses with `InvalidKeyException`
      every key whose algorithm differs from the Cipher's, so no execution distinguishes the two,
      and the same measurement says the arity's `VIOLATED` branch has no execution path the
      platform lets a program complete — what the second place protects is the `SATISFIED` one.
      Measured too, and the reason `KeyStoreSpec` must write at all: `getKey` returns a *fresh*
      key object, so an identity-keyed store cannot carry a predicate through a key store.
      #15 and #16 are the constructor's own REQUIRES and `KeyPairSpec.c1` carried no site for
      them; it gains two reads and four codes. `KeyStore`'s `generatedPrivkey[key]` gains its
      first site in the set, guarded by `instanceof PrivateKey`; its `generatedPubkey[key]` gains
      none and is recorded — `getKey` never returns a `PublicKey`.
      Evidence: `data/gh105/evidence/f3-GeneratedKeyFamily.md` (with 5.7, one commit)
- [x] 5.7 `generated*key` family B (ledger #34, #35, #8): `Signature`
      `generatedPrivkey[priv]`/`generatedPubkey[pub]` (Signature's own clauses — not
      `generatedKey`); the Cipher negated `!macced` (#8) via `validateAbsent`, with the `MACED`
      producer write added at the Mac rule's acceptance point (zero sites today).
      #34 and #35 take three sites, not two: the rule binds `priv` in both `i1` and `i2` and
      `pub` in `i4`. `i3` gains none — it binds a `Certificate`, which api30 states no clause
      over, and that asymmetry is the oracle's and is recorded.
      #8 takes **four** sites and needed a producer built from nothing. On the consuming side
      `CipherSpec.f5` and `f6` bind the rule's `plainText` and read it there, while the two
      overloads almost every program uses fall into `CipherSpec.f2`, which is
      `call(public byte[] Cipher.doFinal(..))` over three overloads and binds no argument;
      splitting it is not available at 17 of 17 events (INV-INS-145), so they became two events
      of `IvChainJunction.mop` — no new `.mop`, the universe stays at 215. `f7` binds a
      `ByteBuffer` and gains no read: no site of the set can mark one, and `validateAbsent` never
      answers `NOT_OBSERVED`, so it could answer only `SATISFIED`.
      On the producing side `MacSpec` had zero sites **and no `@match`** — task 4.9 deleted the
      handler whole — so it comes back with a clause to write, and the events that bind the data
      had to be created: the aggregate `update(..)` and the merged `doFinal` bound no argument,
      which is finding 74. One event per overload with types written out (finding 79), plus an
      `update(ByteBuffer)` sibling that carries no clause and exists so the split narrows no
      alphabet the aggregate covered. The rule's third clause, `macced[output1, inp]`, gains no
      site: `inp` is a primitive `byte`, a write would box it, the store is keyed by identity,
      and no `Cipher` takes a `byte` as its plaintext.
      Evidence: `data/gh105/evidence/f3-GeneratedKeyFamily.md` (with 5.6, one commit)
- [x] 5.8 `prepared*` guarded clauses (ledger #10, #17, #20): `preparedGCM` (`{GCM} =>`, guard
      evaluated in the body before the read) and `preparedDH` (`KeyPairGenerator {DH} =>`);
      `preparedEC` (#20) recorded `unclosable` — no producing rule exists; deliberate-omission
      records for the **9 in-set ENSURES-only dead ends** (`preparedPBE`, `generatedSSLContext`,
      `generatedSSLEngine`, `signed`, `verified`, `digested`, `generatedKeypair`,
      `cipheredInputStream`, `cipheredOutputStream`): no fabricated read for any, no fabricated
      write for the two stream predicates that have none, and the eleven existing write sites of
      the other seven were already placed by Group 4 — ten by 4.13/4.14, and
      `PBEParameterSpecSpec.mop:62` by its own file pass 4.7.
      **#10 was wired and #17 was not, and the ledger had #17 in the wrong column.** `preparedGCM`
      binds the same `params` at the same join point as clause #9, so it is a second read in
      `IvChainJunction`'s `use` body rather than a file of its own — a second specification over that
      call would put a second monitor on it to ask about the same object — and the universe of
      enumerated `.mop` stays at 215. Its G-PRED2 line closes by that read, which is what
      `GCMParameterSpecSpec.mop` predicted in a comment at task 4.8.
      `preparedDH` (#17) is the ledger's second `unreachable-composition`, after clause #21: both
      ends have a `.mop` and no program can compose them. `DHGenParameterSpec` is the only producer
      of the predicate in the whole api30 oracle — `AlgorithmParameters` requires it and ensures
      `preparedAlg` instead — and measured on Temurin 21,
      `KeyPairGenerator.getInstance("DH").initialize(new DHGenParameterSpec(2048, 0))` raises
      `InvalidAlgorithmParameterException: Inappropriate parameter type`, while the same object into
      `AlgorithmParameterGenerator.getInstance("DH").init(...)` — the consumer the class exists for,
      with no `.mop` in this set — runs. A DH key pair is initialised from a `DHParameterSpec`, which
      no rule ensures. A read at `KeyPairGeneratorSpec.init3/init4` would accuse every conforming DH
      program of a preparation it has no way to obtain, so the producer's write carries a
      deliberate-omission record instead and its G-PRED2 line closes the way `PREPARED_HMAC`'s did
      (researcher decision, 2026-08-22). The gate goes from six findings to four.
      The **nine ENSURES-only dead ends were already disposed of**: the seven with writes carry
      `disposition=omission` from tasks 4.13 and 4.14, and the two stream predicates have no write
      and need none. This task measured that and states it rather than adding a row.
      Evidence: `data/gh105/evidence/f3-RandomizedHubAndGuardedPrepared.md` (with 5.4 and 5.5, one commit)
- [x] 5.9 TLS chain (ledger #14, #36, #28, #29): `generatedKeyStore` →
      `KeyManagerFactory`/`TrustManagerFactory`; `generatedKeyManager[kms]` /
      `generatedTrustManager[tms]` → `SSLContext.init` (bound-first API — `kms`/`tms` are
      reference arrays a varargs head would spread). Pairs with 6.2's pointcut repair.
      **Four reads, no new event and no new file**, which is the batch's strongest structural
      claim: each read binds its argument by adding an `args(...)` clause to a pointcut that was
      already there, so no alphabet grows, no `fsm` changes, `order_alphabet_map.csv` needs no
      row, `gate_allowlist.csv` stays at 14, the universe stays at 215 and every `gh104_gates.py`
      counter is identical before and after. `KeyStoreSpec.mop` is not edited at all — its
      G-PRED2 finding closes because a reader appeared elsewhere, which is what the closure gate
      measures. The `init` of both factories is one event standing for the rule's `i1` and `i2`
      at once and bound nothing; the position the fused overloads share is the zeroth, so
      `args(arg, ..)` (KeyManagerFactory, arities 2 and 1) and `args(arg)` (TrustManagerFactory,
      both 1) bind it as `Object` and the body discriminates by `instanceof`. Splitting into the
      rule's own `i1`/`i2` and adding a separate consumer specification were both triaged with
      `javamop` and both generate; they were rejected on collateral — the split moves the `ev=`
      of a published ORDER code and rewrites an ordering map, and a separate specification is
      the last resort this set takes only where an alphabet has no headroom.
      **The measurements decided three things and dissolved nothing.** The chain composes end to
      end on Temurin 21, and unlike clause #5 the platform does *not* already refuse what these
      clauses accuse: `ctx.init(null, null, null)` runs, and so does the trust-all manager. A
      null argument is therefore read and not exempted (researcher decision), which is why six
      previously silent corpus traces gain a `NOBS` report and four new traces were written so
      the conforming chain is witnessed silent and the accusing case — `tmf.init(unloadedStore)`,
      which this platform *runs* where its `KeyManagerFactory` counterpart throws — is witnessed
      accusing. Both factories allocate a fresh array per call, so the predicate travels with the
      array the call returned and a copy loses it; that reach limit is named, not hidden.
      **The baseline moves for the first time since Group 5 began**: three `repaired` G-PRED2
      lines, findings 4 → 1. The `omission` records on the two `[this] after Init` halves are
      kept and extended rather than retired — the gate accumulates by predicate name over the
      whole set and stops asking, but what they state is still true, since `SSLContext` reads the
      array and never the factory. Ledger #30 (`randomized[sr]`) stays `vacuous`: `Init` binds
      `sr` in no event. Evidence: `data/gh105/evidence/f3-TLSChain.md` (with 6.2, one commit)
- [x] 5.10 Leaf clause and the record pass: `preparedKeyMaterial[keyMaterial]` (#32 — consumer
      `SecretKeySpecSpec`, producer `SecretKeySpec.mop` `getEncoded`), un-conflated with 6.1 in
      the same commit; then the 10 non-wireable clauses recorded with their category, each
      exactly once, here (ledger #1, #2, #3, #4, #7, #18, #19, #26, #27, #31 — the ledger's task
      column is the single source). Task 4.13 also feeds this task a record it measured and
      deliberately did not duplicate: api30 `KeyPair.cryptsl:39` states
      `generatedKeypair[this, _] after co` and `KeyPairSpec.c1` has no write for it. None was
      fabricated (researcher decision, 2026-08-22) — the predicate is required by no rule of the
      oracle, its other producing site is `KeyPairGeneratorSpec.mop:111` (task 4.14), and a
      clause with no site has no row in `predicate_graph.csv` to carry the record, because that
      inventory is of sites. Record it here, the way task 4.12 fed task 6.5.
      **The wiring cost no symbol and the collateral is the whole of what this task bought.**
      Both sites already bound the `byte[]` and `PREPARED_KEY_MATERIAL` already existed in the
      enum, so no alphabet, no `fsm`, no allow-list row and no file moved. What moved is what the
      set accuses: `preparedKeyMaterial` is ENSURED by `Key.getEncoded()` and
      `SecretKey.getEncoded()` and by nothing else in the oracle, so the idiom the corpus is
      built on — a `byte[]` an observed `SecureRandom` filled, handed to the constructor — does
      not satisfy the clause, and the one that does is `generateKey()` then `getEncoded()` then
      the constructor. Measured against the tree before the batch: **18 of 128 traces change** —
      15 draw `SECRETKEYSPEC-NOBS-00`, 11 draw `CIPHER-NOBS-00` downstream because a construction
      that breaks the clause ensures no `generatedKey`, 4 draw `IVPARAMETERSPEC-NOBS-00` because
      an encoding is no longer randomised bytes, and 1 draws the new `c2` site. Every one is what
      api30 states; eight trace headers that claimed conformance were corrected rather than the
      traces changed, and `SecretKeySpecSpec-prepared-material.txt` was written as the conforming
      chain the corpus lacked (silent on both sides). Three alternatives were measured and
      declined: moving half trades one G-PRED2 finding for another; suppressing the downstream
      cascade changes the same 18 traces and costs the conditional ENSURES that CrySL states;
      deferring leaves this change's own object unrepaired (researcher decision, 2026-08-22).
      **The four-argument overload gains the read task 4.10 deferred here** (decision above):
      api30 binds `keyMaterial` in both events of `Cons := c1 | c2` under one REQUIRES, so the
      obligation is the constructor's; two new codes, `SECRETKEYSPEC-CONSTR-02` and
      `SECRETKEYSPEC-NOBS-01`, new numbers because a code names a site.
      **The G-PRED2 line does not close here, by decision.** `unmonitored-consumer` is a *read*
      disposition (`gh105_predicate_graph.py:1189`); the write-side `omission` that would close
      `PBEKeySpecSpec c1/SPECCED_KEY` is task 5.11's, and it has to travel with the gate's
      retirement, because `gh105_gate_baseline.py:75-84` builds `gates` from findings alone — a
      gate driven to zero loses its baseline key and turns
      `test_a_retired_gate_leaves_the_baseline_and_stays_out` red. #31's *clause* is recorded here
      (`PBEKeySpecSpec.mop` `c2` comment, `predicate_graph.csv` `reason`, evidence).
      Evidence: `data/gh105/evidence/f3-PreparedKeyMaterial.md` (with 6.1 and 6.5, one commit)
- [x] 5.11 Closure sweep over **all 22 written `Property` values**, not only the named ones:
      every write has its reader or its deliberate-omission record, and the read-only gap
      (`GENERATED_PRIVATE_KEY`, resolved by 6.1's producer repair) closes. G-PRED2 green — 21
      wired + 14 recorded (10 non-wireable + the vacuous #30 and #23 + the
      `unreachable-composition` #17 and #21) + `preparedEC` `unclosable` in the graph.
      **The sweep corrected two numbers this task's own statement carried.** It says 21 written
      values and there are **22**: task 5.10 renamed `SecretKeySpec.mop:125` from `RANDOMIZED` to
      `PREPARED_KEY_MATERIAL` while `RANDOMIZED` stayed written at three other sites, so the
      distinct set grew by one without moving any census of operations. And it said 24 wired,
      the `design.md` totals said 22, and the tree says **21** — #17 (`{DH} => preparedDH`) was
      recorded `unreachable-composition` by task 5.8 and never subtracted; measured, `PREPARED_DH`
      has one write (`DHGenParameterSpecSpec.mop:37`) and no read in the set. Of the 22 written
      values, 12 have a reader, 9 carry an `omission`, and `SPECCED_KEY` was the last open row.
      **It closes with `omission`, not with the category its clause has.** Ledger #31 is an
      `unmonitored-consumer` — `SecretKeyFactory`, the one rule of api30 that requires
      `speccedKey`, has no `.mop` in the set — but that is a *read* disposition
      (`gh105_predicate_graph.py:1179`); a write with no reader closes with `omission` or
      `propagation` and nothing else (`:1189`). The ledger categorises the clause, the graph
      column categorises the site.
      **The gate retires in the same commit that closes it**, because
      `gh105_gate_baseline.py:75-84` builds `gates` from findings alone: at zero the key leaves
      the baseline and any assertion that names it turns red. So the disposition, the `retired`
      entry (`was` 36 — what the gate reported on the unmodified tree, the same rule the four
      earlier retirements used) and the removal of
      `test_a_retired_gate_leaves_the_baseline_and_stays_out`'s `"G-PRED2" in recorded["gates"]`
      travelled together, plus one nobody had recorded: the frozen-set test asserted the origin
      of findings with a set *equality*, which needed a finding to exist, and became a subset.
      No `.mop` changed, so no trace changed and no census moved — stated in both censuses rather
      than assumed. `/rv-verify` on the gate layer green: 94 assertions, `structural_findings` 0.
      Evidence: `data/gh105/evidence/f3-ClosureSweep.md` (with 6.4, one commit)

## 6. F4 — Pointwise defects and the nine remove() (8 deleted + 1 migrated)

<!-- Per task: the repair + trace pair + harness delta + divergence_record.csv hunks. -->

- [x] 6.1 The `KeyPairSpec.mop:38` half of this task is **done, by task 4.13**: the private key
      now writes `GENERATED_PRIVATE_KEY` as `generatedPrivkey[retPriv] after pr` names it, and
      the set's one read-only property is closed — `gh105_gate_baseline.py` reports
      `[G-PRED2] repaired jca_android/CipherSpec.mop i2/GENERATED_PRIVATE_KEY`. It was repaired
      with the store move rather than deferred here because task **5.7 runs before this one** and
      wires Signature's `generatedPrivkey[priv]`, which would otherwise be measured against a
      producer known to be wrong: a private key marked as public answers NOT_OBSERVED to
      `initSign(priv)` about a conforming program, and SATISFIED to `generatedPubkey`. What
      remains here is `SecretKeySpec.mop:26`
      `preparedKeyMaterial ≡ RANDOMIZED` conflation — producer AND consumer halves in the same
      commit: the read moves to `PREPARED_KEY_MATERIAL` together with the write, or the repaired
      producer leaves the consumer reading a never-written predicate. Landed with 5.10.
      **The task statement named two reads and the tree had one.** `SecretKeySpecSpec.mop:25,42`
      are seed anchors; after the fusion of task 3.4 and the store move of task 4.10 there is a
      single `validate(RANDOMIZED, keyMaterial)`, in `c1`. The second site the statement was
      reaching for is the four-argument `c2`, which had no read at all and gains one here under
      task 5.10's decision, so the arithmetic comes out at two reads either way — for a different
      reason than the statement gave.
      **A second thing the batch discharged and this statement did not foresee**: the guard at
      `SecretKeySpec.e1` kept its read, but not for the reason task 4.12 recorded. That reason
      was about `randomized` and is spent once the write names `preparedKeyMaterial`; measured
      over 128 traces, guarded and unguarded are indistinguishable everywhere but on the one
      trace written to tell them apart. The reason it stays is now laundering — without it, a key
      the set never observed hands its encoding on as prepared material and a second
      `SecretKeySpec` built from it goes silent (`SecretKeySpec-laundered-material.txt`;
      researcher decision, 2026-08-22).
      Evidence: `data/gh105/evidence/f3-PreparedKeyMaterial.md` (with 5.10 and 6.5, one commit)
- [x] 6.2 `TrustManagerFactorySpec.mop` `gtm1`: `KeyManager[]` return pointcut +
      `TrustManager[][]` parameter + a target bound to a name the specification does not declare.
      Pairs with 5.9. Two of the four defects the task named had already travelled with task
      4.14 under decision 11's criterion — the wrong property (the seed wrote the neighbouring
      rule's `GENERATED_KEY_MANAGERS`) and the `remove(GENERATED_TRUST_MANAGERS)` of a property
      no site of any set writes — so what remained here is the pointcut, and the three remaining
      defects were three faces of one fact: **the advice had no execution path at all**.
      It had to be repaired in this commit and not the next, because ledger #29 is wired in this
      commit: measured against a producer that never runs, every read would have answered
      `NOT_OBSERVED` for a reason that has nothing to do with the wiring.
      **What the repair makes live, stated in full rather than discovered later**: the write
      happens, so an `SSLContext.init` receiving this array reads `SATISFIED`; and a second
      `getTrustManagers()` on one factory now draws `TRUSTMANAGERFACTORY-ORDER-00`, because the
      transition row sends `gtm1` from the accepting state to `start`, where the event is not
      declared. That accusation is faithful — api30 orders `Gets, Init, gtm?` and the `?` refuses
      the repetition too — and symmetric, since `KeyManagerFactorySpec.gkm1` declares the right
      return type, has always been live and has always behaved this way; the repair restores two
      mirror specifications to being mirrors (researcher decision, 2026-08-22).
      **The harness proves the repair from the trace side, in the column that recorded the
      defect**: `tmf.getTrustManagers()` used to resolve to no pointcut on either snapshot and
      now resolves on this one, so `TrustManagerFactorySpec.txt` goes from two unresolved lines
      to one. The `g1 i1 gtm` ordering divergence and the placement of the body write are
      untouched and stay with task 7.1; this batch edits no `fsm`. The `order_alphabet_map.csv`
      row keeps its symbol, its reason rewritten to say the repair changed what the event binds
      and whether it runs, never which rule event it is.
      Evidence: `data/gh105/evidence/f3-TLSChain.md` (with 5.9, one commit)
- [x] 6.3 `SignatureSpec`: `verified` marked on the `boolean` instead of the `byte[]`; `sign()`
      pointcuts declaring `public byte`. **Both halves were already repaired when this task was
      reached, each by the pass that owned the file at the time, and this task verifies rather
      than performs — the same shape tasks 6.4 and 6.5 took, by the same criterion (decision
      11).** The `sign()` return types left in `bc5e3e09`, a gh104 structural pass that predates
      this change: `public byte Signature.sign()` became `public byte[]` and
      `public byte Signature.sign(byte[], int, int)` became `public int`. The `verified` argument
      left in `bd25a3aa`, the Group 4 file pass, and `predicate_graph.csv` already credits it in
      writing on the `VERIFIED` row — "the clause names the signature the call was given and the
      seed wrote the boolean it returned … (researcher decision, task 4.13)".
      **The three verifications are measured, not read**: zero `public byte ` without brackets
      across the 24 `.mop` of `jca_android`; `stagedVerified = sign` at `SignatureSpec.mop:242`
      and `:250`, with the `boolean signed` of `:238`/`:246` used in no body; and the graph row
      carrying `position_types=byte[]` with `disposition=omission`, which is why neither form
      ever moved a gate finding — no api30 rule requires `verified`.
      **One correction to this statement, the same one task 6.4 carries**: the anchors it names
      resolve in the frozen `jca` (`jca/SignatureSpec.mop:99,106`) and in the archived
      `jca_android_bug_predicate` (`:120,127`), not in the tree. Worth recording, because nobody
      had: in the frozen set `call(public byte Signature.sign())` matches no call at all —
      `Signature.sign()` returns `byte[]` — so `s1` and `s2` are non-existent producers there
      (finding 95). `jca` is frozen against its published measurements and this change does not
      touch it. Evidence: `data/gh105/evidence/f3-DoFinalDisjoint.md` (with 6.6 and 6.7, one commit)
- [x] 6.4 **Verify** the 8 `@fail` removals of INV-INS-142 are gone; this task performs none of
      them. They implement "undo the predicate when the automaton fails", a semantics no CrySL
      generation has, and couple typestate to predicate against the rule's own orthogonality —
      and every one of them left with the file pass that migrated the write it withdrew, which
      is decision 11's criterion and the shape task 6.5 already has for tasks 4.6 and 4.9. Task
      4.9 took `MacSpec.mop:99`; task 4.14 took the remaining seven
      (`TrustManagerFactorySpec.mop:124,125`, `KeyStoreSpec.mop:92,93`,
      `KeyManagerFactorySpec.mop:104`, `KeyPairGeneratorSpec.mop:133`,
      `KeyGeneratorSpec.mop:89`) because `PredicateStore` offers no removal at all — INV-INS-131
      forbids it the object-blind `remove(Property)` — so leaving them would have made them
      no-ops on a store nothing writes and would have kept INV-INS-130 off zero, blocking task
      4.15. Measured there: no reader of any predicate remains on the old substrate in
      `jca_android`, so their deletion changed no report (researcher decision, 2026-08-22).
      Verify the count is zero and that each deletion carries its `divergence_record.csv` hunk.
      **Both halves are green, measured over the whole set rather than over the named files**:
      zero `remove(` in any `.mop` of `jca_android`, zero predicate operations inside any `@fail`
      block (scanned by brace depth, not by grep), zero `ExecutionContext`, and exactly one
      `negate(` — `PBEKeySpecSpec.mop:167`, the ninth removal, which is a translation and task
      6.5's to verify. The censuses say the same from the other side: `remove:fail == 0` and
      `negate:body == 1`. The eight deletions carry six `divergence_record.csv` hunks, two of
      which cover two removals each: `3667658f9cf7` (`MacSpec`, task 4.9), `0fd4fb92f7f3`
      (`TrustManagerFactorySpec`, both `GENERATED_TRUST_MANAGER` and the `GENERATED_TRUST_MANAGERS`
      that named a `Property` no site of any set writes), `a92ed5c42e2d` (`KeyStoreSpec`, both),
      `eaa0801a5e33` (`KeyManagerFactorySpec`), `ee86d177e08f` (`KeyPairGeneratorSpec`) and
      `b22fbfe58fb8` (`KeyGeneratorSpec`); `--check` reports 278 hunks all recorded, none stale.
      **One correction to this statement**: the eight line anchors it names resolve in the
      archived `jca_android_bug_predicate` set, where the defect is preserved — not in the tree
      and not in the frozen `jca`. What is verifiable here is the count and the hunks, and both
      are. Evidence: `data/gh105/evidence/f3-ClosureSweep.md` (with 5.11, one commit)
- [x] 6.5 Record the `SecretKey generatedKey[this,_] after d` NEGATES as `unclosable` — the set
      has no `destroy` event, and inventing one would fabricate the evidence this change exists
      to remove. The ninth removal (`PBEKeySpecSpec`, `clearPassword`, the one real `NEGATES`
      clause) was translated to `PredicateStore.negate`, object-scoped, by task 4.6 — it moved
      with the file pass that migrated the write it withdraws, so this task verifies it rather
      than performing it. By the same criterion task 4.9 deleted the `@fail` removal at
      `MacSpec.mop:99` together with the two `GENERATED_MAC` writes it withdrew, leaving 6.4 with
      seven of the eight; verify that one here as well. Task 4.12 measured what this record should
      state about the absent `destroy` event, and deliberately did not write it here: `destroy()`
      throws `DestroyFailedException` on both `SecretKey` implementations the set can observe —
      the `SecretKeySpec` its own file constructs and the one `KeyGenerator.generateKey()`
      returns, which is the same class — so an `after ... returning` advice over it would have no
      execution path even if the event were declared, the position `SECRETKEYSPEC-CONSTR-01` is
      already in. Declaring it would also add a symbol to an automaton whose `ORDER` mapping task
      7.1 still owns: `SecretKeySpec` is one of the thirteen unmapped specifications.
      **All three verifications are green, and each was measured rather than read.** The ninth
      removal is `PredicateStore.negate(Property.SPECCED_KEY, s)` at the `c2` the rule names,
      object-scoped, put there by task 4.6 — and the assertion that verifies it is that the
      number did not move: `negate:body == 1` in the graph census and `remove + negate == 1` in
      the reader census, both unchanged across this batch. The `MacSpec.mop:99` removal is gone:
      `grep -c "remove(" MacSpec.mop` is zero and the file's `@fail` carries no withdrawal. The
      `unclosable` record for the absent `destroy` event is written in `SecretKeySpec.mop:67-75`
      and in `data/gh105/evidence/f3-PreparedKeyMaterial.md` §6, carrying task 4.12's measurement
      rather than re-deriving it.
      Evidence: `data/gh105/evidence/f3-PreparedKeyMaterial.md` (with 5.10 and 6.1, one commit)
- [x] 6.6 `CipherSpec` `f1`/`f2` (pointcuts at `:135` and `:141`; the `event` declarations sit at
      `:134`/`:140`): both match the argument-less call — one call, two transitions; make the
      wider pointcut disjoint (two-events-same-call scenario).
      **The line anchors are the pre-image's**; in the tree the declarations sit at `:220`/`:227`
      and the pointcuts at `:221`/`:228`. **The repair is `doFinal(byte[], ..)` on `f2`**, and
      what decides that form is `order_alphabet_map.csv`, which already attributed `f1` to the
      rule's `f1` (`Cipher.cryptsl:93`, the argument-less overload) and `f2` to its `f2` and `f4`
      (`:95`, `:99`, the two that take one) and whose note already said "both of the rule's
      returning overloads" while the pointcut covered three. Coverage is preserved, the two are
      disjoint, and **no alphabet is spent**: 17 events before and after, which matters because
      splitting `f2` into one event per overload stays unavailable (INV-INS-145).
      **Measured over the corpus: 128 of 128 traces unchanged**, including the only one with an
      argument-less `doFinal` — `CipherSpec-update-chain.txt`, where the call follows an `update`,
      so the monitor sits in `s3`, `f1` runs first and `s3 -> end -> end` is accepted at both
      steps. The defect was silent everywhere the corpus went. It is audible only on the path
      without an `update`, which the corpus did not cover: `s2` has a transition for `f2` and none
      for `f1`. The probe written for it, run against the control first, goes from three accusers
      (`i2` NOBS, `f1` ORDER, `f2` ORDER — the second from the start state its own `__RESET` left
      the monitor in) to two. **Both snapshots are right to accuse**: `FINWOU := f2 | f4 | f5 | f6
      | f7` excludes the rule's `f1`, so a bare `doFinal()` after an init is outside the `ORDER`
      and the `fsm` states that faithfully; the repair trades two reports for one, not one for
      none. The probe entered the corpus as `data/gh104/traces/CipherSpec-nofinal-arg.txt`
      (researcher decision, 2026-08-22), on the B5 precedent and after measuring that no assertion
      of the four suites counts trace files. This batch edits no `fsm`: the G-ORDER `f2`
      divergence stays with task 7.1, and `gate_baseline.json` does not move.
      **The repair unblocks something a neighbouring file recorded as impossible, and that is
      recorded rather than taken**: `IvChainJunction.mop` justified carrying the two clause-#8
      reads by saying `CipherSpec.f2` binds no argument "and narrowing it would drop `doFinal()`
      out of the automaton". Measured, the second half is imprecise — narrowing removes `doFinal()`
      from `s2` only, a transition the `ORDER` never granted — and the first stops holding, since
      the two remaining overloads share a `byte[]` in the first position and `args(plainText, ..)`
      would bind it. Moving those reads would retire `IVCHAINJUNCTION-CONSTR-06` and `-07` and is
      behavioural change this batch does not measure, so both comments were rewritten to say the
      placement is a choice and not an impossibility (researcher decision, 2026-08-22).
      Evidence: `data/gh105/evidence/f3-DoFinalDisjoint.md` (with 6.3 and 6.7, one commit)
- [x] 6.7 Trace pairs, harness deltas and `divergence_record.csv` hunks for all of Group 6.
      **The accounting for 6.3 and 6.6, which is why the three are one batch and one commit.**
      Harness against the pre-image over 129 traces: **60 unchanged · 31 moved · 31 introduced ·
      7 removed** — `moved` rises by exactly the new probe and no earlier trace changes class;
      `git diff --stat -- data/gh105/evidence/harness/` names one file, `f2-CipherSpec.md`; and
      `unresolved` stays at six lines in four files, all pre-existing. `codes.csv` reanchored by
      script over the whole file: **5 of 112** rows moved, all by displacement from this batch's
      comments (`CIPHER-CONSTR-01` `:272→:293`, `CIPHER-CONSTR-02` `:284→:305`, `CIPHER-ORDER-00`
      `:355→:376`, `IVCHAINJUNCTION-CONSTR-06` `:337→:342`, `-07` `:347→:352`) and **no
      pre-existing drift**, the B6 sweep having taken it. `divergence_record.csv`: **278 hunks,
      all recorded, zero stale**, 283 rows before and after — three hunks re-keyed and three left,
      one for one (`465872e781b7` absorbs `91c25b291fdb`; `f535aef55279` absorbs `95a6e30dc89e`;
      `f44aff070792` absorbs `a42232d095f8`), appended at the end rather than reordered.
      `predicate_graph.csv` does not move — neither `f1` nor `f2` has a row, since they stage into
      a field and the write stands at `@match1` — and the round-trip was taken (copy, `--emit`,
      `diff`) and is identical at 70 rows. `order_alphabet_map.csv` changes one note and no
      symbol. Both per-batch census paragraphs are written and both say nothing moved, which is
      what rule 16 asks for. Evidence: `data/gh105/evidence/f3-DoFinalDisjoint.md`

## 7. F5 — Records, retirement, hardening

- [x] 7.1 Complete `order_alphabet_map.csv` for every spec Groups 1-6 touched; G-ORDER green or
      declaredly skipped across `jca_android`. **Repair the gate's `ORDER` parser first**: it
      reads `,` as binding tighter than `|`, and `CrySL.xtext:103-120` binds them the other way
      round (`Sequence` is the outermost production, so it is the weakest operator). `Cipher` is
      the one api30 rule that tells the two parses apart, so the `CipherSpec` row is an artifact
      of the gate: it reports `f2` accepted by the ORDER, where the faithful parse rejects a bare
      `doFinal` and accepts `g1 i2 f2`, which the gate rejects. Measured delta: one witness,
      inverted; counts unchanged at 6 passed / 4 findings / 14 skipped (the evidence says 13,
      having been written before Group 5 added `IvChainJunction`). The five-step checklist, the
      reproduction, and the real `CipherSpec` divergence the repair uncovers (the `ere` accepts
      an unfinalised Cipher) are in `data/gh105/evidence/f1-order-gate-precedence.md`.
      **Measured, and it decided the mapping:** completing the file takes G-ORDER from
      6/4/14 to 13 passed / 9 findings / 2 declared skips. Twelve specifications translate an
      api30 rule and were mapped (61 rows); two translate none and can never gain a row, so the
      skip is prose in the file's header. Five pass at once; seven divergences the skips had
      been hiding are raised and recorded in `gate_baseline.json`, which grows from 4 rows to 9
      after the two repairs below — so a `--write` *is* run, preserving `retired`.
      **The oracle is not unanimous, and the researcher decided it (2026-08-23):** the gate
      follows `CrySL.xtext`, while `MetaCrySL/src/lang/crysl/ConcreteSyntax.rsc:67-68` — the
      Rascal grammar of the generator that produced `generated/api30/` — binds `,` the other
      way. Cipher is the only rule where the choice changes the language. Recorded in
      `data/gh105/evidence/f3-OrderMapComplete.md` §1.
      **Task 4.14 feeds this task a divergence the gate cannot currently see.**
      `KeyManagerFactorySpec` has no rows in `order_alphabet_map.csv`, so G-ORDER skips it
      declaredly — and `g1 init gkm1` is accepted by the api30 ORDER (`Gets, Init, gkm?`) and
      rejected by the `fsm`, whose `gkm1` row {3, 3, 0, 3} leaves the accepting state (2) for
      `start` (0) against a match category of `nextstate == 2`. It is the exact mirror of the
      `g1 i1 gtm` divergence the gate already reports against `TrustManagerFactorySpec`, and
      `conformance_record.csv` was read before calling it new: its three `KeyManagerFactorySpec`
      rows are about the algorithm allow-list, the deferred `neverTypeOf` constant and the 8.16
      guard-on-field repair. Mapping the file here will raise it. Two writes reach their
      acceptance point when the two automata are repaired — `KeyManagerFactorySpec.gkm1` and
      `TrustManagerFactorySpec.gtm1`, both kept in the event body by task 4.14 with the reason
      recorded in `predicate_graph.csv` precisely because these rows make the acceptance point
      unreachable.
      **Measured: they reach it without moving.** The repair is `gkm1 -> taken` and
      `gtm1 -> taken`, a second accepting state that declares no event, which is what the rule's
      `gkm?` states — optional and terminal at once. `-> final`, the self-loop this task's
      wording implies, was measured first and rejected: it closes the reported witness and opens
      `g1 i1 g1 i1`, and it makes the set accept `g1 i1 gkm gkm`, which the `?` refuses, so it
      would have silenced an accusation the file's own comment had already called faithful. With
      the edge repaired the event's transition lands on the accepting state, so the body write
      runs where the clause asks and nothing moves; what keeps it out of the `@match2` handler
      is the array, since a handler sees no parameter of the event it follows. Over the
      131-trace corpus the repair moves nothing, and `gh104_gates.py` is unchanged in all nine
      counts
- [x] 7.2 `codes.csv` completeness pass: every accuser introduced in Groups 3-6 has its code;
      message gate green.
      **Measured satisfied before it was executed** (batch B8): 112 accusers against 112 codes,
      zero accuser without a code, zero orphan code, zero derived `file_line` anchor, message
      gate green. What the task delivered instead is the gate the anchors never had: a
      `code-anchor` check in `gh104_message_gate.py`, asked for by batches B6 and B7, which found
      six drifted anchors and moved five respectively — both times only because someone
      re-anchored the whole file by script. It caught its first drift on the pass that added it:
      task 7.1's edits moved two `@fail` sites, and the two `codes.csv` rows were re-anchored
- [x] 7.3 Retire `rvsec-mop-defsuses`: move to `backup/`, remove from `rvsec/rvsec/pom.xml:27`
      `<modules>` (the only pom that lists it), grep for dangling references (documentation
      survivors updated or exempted declaredly — module CLAUDE.md rows,
      `scripts/check_no_legacy_mop.py` skip list, the retired copy under `backup/` that the move
      itself creates inside the grepped tree, and the active gh48-project-finalization
      artifacts, whose `defsuses` rows are that change's to update), reactor builds (P3)
- [x] 7.4 Regenerate the full `jca_android` monitor through the real pipeline; record heap;
      inspect the artifact, never the exit code (INV-INS-145); update
      `data/jca_android/README.md` to the new machinery census **and** the new file count — the
      set is no longer 23 specifications and the universe is no longer 214, because Group 5
      added junction specifications; verify no gate, test name or record holds the stale literal.
      **Measured (batch B9):** two full runs, 79 s and 77 s, peak RSS 5.4 GB and 4.5 GB across
      the process tree, producing a byte-identical `MultiSpec_1RuntimeMonitor.java` of 17,087
      lines — the generation is deterministic. **No launcher passes `-Xmx`**: javamop's invokes a
      bare `java`, rv-monitor's and the child at `LogicRepositoryConnector.java:149-154` pass
      `-Xss1g` and nothing else, so both JVMs run at the default ergonomic heap. **And there is
      no environment lever, measured**: `_JAVA_OPTIONS=-Xmx4g` reaches both JVMs but aborts the
      run, because the JVM prints `Picked up _JAVA_OPTIONS:` on stderr and
      `utils.execute_command` raises on any stderr even at `code=0` — INV-INS-145 turned around,
      the exit code falsely red instead of falsely green. Recorded rather than repaired
      (researcher decision 2026-08-23): widening `execute_command` would blind the generator to
      the masked child OOM the invariant exists for. A side effect nobody had recorded: the
      failed run leaves 24 gitignored `.rvm` inside the specification directory, which silently
      changes the harness's cache fingerprint until a successful run moves them out.
      **Artifact inspection** found the monitor differs from the one the harness had cached — a
      state renumbering, `{2,3}` transposed, `fail` unmoved — traced in four measurements: two
      real-pipeline runs agree, a cold-cache harness leg is byte-identical to the real pipeline,
      the old cache differs, and the reports are identical either way (61/31/32/7 over 131
      traces, 0 files differing). The cache is keyed on the specification set and not on the
      toolchain, so it is stale and provably harmless — **and that excludes the monitor as the
      cause of the ten-report evidence drift**. `CipherSpec` declares exactly 17 events, the
      ceiling, headroom zero; next largest is `SecureRandomSpec` at 13. **Literals corrected**:
      set 23 → **24**, universe 214 → **215**, report sites 50 → **112** (all four-argument, zero
      commented), `codes.csv` 50 → **112**, `ExecutionContext`/`setProperty(`/`.remove(` all
      **0**, `validate(` **38** (the handoff said 39; `f010cb92` commented one out). The README's
      four `21`s are **not** stale: they count the rule-paired specifications of
      `conformance_record.csv`, not the set, and the ambiguous sentence was reworded instead. No
      gate holds a count literal — all 18 `scripts/gh10*.py` enumerate
- [x] 7.5 Run `/rv-qa-lint-fix scripts` and `/rv-doc-code` on any script not covered by 2.12 —
      enumerate them from `git status` at this point, so "any script" is decidable.
      **`git status` does not decide it**: this tree carries ~180 untracked files from another
      campaign, so the decidable criterion is by path — every `scripts/gh10*.py` less the three
      2.12 covered. Measured before executing: **14 scripts, 7,096 lines, 92 functions and 6
      classes without a docstring = 98 items**, two files accounting for 59 of them.
      **Lint**: `autoflake` changed nothing, `isort` two files, `black` **13 of 14, 96 hunks**
      (plus three files on a second pass — a `@dataclass` docstring wants a blank line before
      the first field). The handoff's trap did not materialise: `codes.csv` anchors point at
      `.mop` files, not at scripts, so `code-anchor` never moved and no row was re-anchored.
      `flake8` fell **505 → 353**, all of them `E501` inside strings `black` will not break.
      Outside `E501` three remained, **the same three as `HEAD`** (verified by running flake8
      over `git show` copies, not assumed): two dead imports in `gh104_message_gate.py` that
      `autoflake` skips because the block carries a `# noqa: E402` written for the
      `sys.path.insert` above it, and a `nonlocal buffer_line` in a `flush()` that only ever
      assigns `buffer`. Both removed; residue outside `E501` is now **0**.
      **Docs**: all 98 written item by item after reading the code, each saying why the
      function decides as it does rather than restating its signature. Insertion went through a
      purpose-built inserter, not `edit.py`: it locates the target structurally in the AST and
      then **reparses and compares the AST with every docstring stripped against the one from
      before**, so an insertion that touched anything else fails loudly — a text substitution
      could not assert that, and `def main() -> int:` appears in fourteen files.
      **Behaviour proved unchanged by artefact, not by suite**: `gh104_baseline.py` reproduces
      `baseline.json`/`baseline.md`/`definitions.md` byte-for-byte,
      `gh104_identity_discontinuity.py` reproduces both of its documents, the gh101 inventory
      and conformance records reproduce, the harness over 131 traces yields reports identical to
      the pre-edit pass (61/31/32/7), and the nine `gh104_gates.py` counters are unmoved since
      B4. `data/gh101/predicate_edges.csv` does **not** reproduce — 44 rows this change's Groups
      3–5 closed — and the `HEAD` copy of the script produces byte-identical output, so the
      drift is in the historical record and not in this pass. `gh104_regen_diff.py` was **not**
      exercised end to end: its control lives under gitignored `results/` and pointing
      `generate` there would destroy the G-PARAM oracle, so it was covered by `--help`, its
      three pure functions and the absent-control path only. Evidence:
      `data/gh105/evidence/f5-ScriptsDocumented.md`
- [x] 7.6 Delete the expected-baseline mechanism of 2.10: every gate now asserts zero findings
      on its own, `data/jca_android/gate_baseline.json` is removed, and the pytest wrappers stop
      reading it. A baseline that outlives its groups is an allow-list nobody voted for.
      **Measured before it was executed (batch B9):** the file held **one** gate — G-ORDER, nine
      rows — and five `retired` entries. The other eight gates were already at zero and their
      `_no_regression` calls already compared against the empty set, which the wrappers' own
      docstrings said in as many words. The mechanism was dead for eight of nine, and deleting it
      unchanged would have turned nine records into nine failures.
      **Researcher decision (2026-08-23): move the nine to `gate_allowlist.csv` and teach
      `gh105_order_gate.py` to read it.** The task's accusation is about *provenance* — the nine
      baseline rows were three anonymous fields elected by whatever a `--write` measured, while
      every allow-list row carries the witness, the measurement, the reason and the owning task.
      Moving them is taking them to a vote, which is obeying 7.6 rather than dodging it. Repairing
      the nine automata was measured and rejected: two (`CipherInputStreamSpec`, `SecretKeySpec`)
      have the excess on the **rule's** side — the api30 orders a symbol no monitored program can
      produce — and `order_alphabet_map.csv` has no disposition for that, so repair would end at
      the allow-list anyway after a whole group; two more are inherited from the frozen `jca`.
      Narrowing 7.6 to the gates already at zero would have removed no row at all and left
      `DEMOLITION_TASK` pointing at a task that no longer existed.
      **Delivered:** `gh105_order_gate.py` gained an `allowed` list beside `findings`, an
      `--allowlist` flag and its own 20-line reader — deliberately not the shared
      `read_allowlist`, because **a row with an empty `reason` must allow nothing**, and the
      shared reader ignores that column. Two key widths, not three: the subject of a G-ORDER row
      is the constant `order`. Audited by mutation, as finding 100 asks: emptying a reason,
      dropping a row and renaming the gate each produce exactly one finding. The gate now reports
      `13 passed, 0 failed, 9 allow-listed, 2 skipped of 24` and exits 0.
      The script, the JSON and the report moved to `backup/gh105-retired/gate-baseline/` with a
      `RETIREMENT.md` that **preserves the five retirement records verbatim** — they are decisions
      rather than measurements, each saying what a future finding from that gate would mean, and
      they died with the file. Without that, 7.6 would have traded nine unprovenanced expectations
      for five unprovenanced retirements. In the suite four mechanism tests died whole (14
      assertions) with the `BASELINE`/`_recorded`/`_no_regression` helpers and the `measured`
      fixture; six wrappers became `_no_findings`, five of them a rename. The sixth,
      `test_inv_ins_138_gorder`, asserts **both** halves — zero findings *and* a non-empty
      allow-list — because a run reporting neither would mean the gate stopped comparing.
      Suite 71 → 67 passing; no `.mop` edited, and the harness footprint against `HEAD` is zero
      files. **Found along the way and worth its own line:** `tests/parity/` does not run in CI —
      `.github/workflows/ci.yml:79-97` iterates `modules/*/tests` only — so D-13's "CI contract"
      is `/rv-verify` and task 8.1 in practice

## 8. Verification

- [x] 8.1 Full gate suite over the enumerated universe: G-ORDER, G-PRED2, G-ACC, G-PARAM,
      junction rules, import discipline, genericity (skip-and-count report committed); gh104
      gates still green, `test_jca_android_hunks_all_recorded` included.
      Measured over 215 `.mop` in five sets: G-ORDER 13/0/9 allow-listed/193 skipped, every skip
      with a written reason; the graph gate 213 read, 2 skipped, 0 failing, 21 informative G-ACC
      findings **none of which is in `jca_android`**; the four migrated-set-only gates declare
      16 skips over the four sets they do not govern. G-PARAM closes over **24 of 24** rather
      than the suite's 23, by preserving the `.rvm` between the javamop and rv-monitor steps —
      the suite's single skip is an artefact of the pre-change fixture under
      `results/gh51_e2e_test/monitors`, not of the specification.
      Evidence: `data/gh105/evidence/f5-GateSuiteOverTheUniverse.md`
- [x] 8.2 Freeze proof: `jca/` and `ExecutionContext.java` byte-identical (zero-diff — no
      annotation, no whitespace), `FROZEN_PATHS` covers the file, `test_property_append_only`
      green. Run it with `RVSEC_HOME` set — the gh101 freeze gate `pytest.skip`s without it
      (`test_gh101_specset_gates.py:59-60`), and a skipped freeze gate is not a freeze proof.
      `git diff 7e7acb69` is empty on all three frozen paths and the working tree is clean on
      them; the suite runs 6 passed, **0 skipped**. One measured gap is recorded and, by
      researcher decision (2026-08-23), not gated: the 23 frozen `.mop` import
      `br.unb.cic.mop.eh.*`, which changed since the base commit and is covered by neither
      `FROZEN_PATHS` nor an append-only test — it is observationally neutral for the frozen set
      because 0 of its 23 files write the `v=1` envelope marker (against 22 of `jca_android`'s
      24), so `ErrorSummary`'s new `code`/`event` fields are a constant for every `jca` report.
      Evidence: `data/gh105/evidence/f5-FreezeProof.md`
- [x] 8.3 C5 ground truth, as an **oracle comparison, not a replay**: the corpus at
      `../../ase-journal/dataset/results/errors_unit_tests.csv` (sibling repository, read-only
      per gh89) is a 299-row aggregate of already-reported errors — columns
      `apk,rep,timeout,tool,time,spec,class,method,message,unique_msg` — not traces the harness
      can consume. Use it to answer one question per row family: does the corrected set still
      accuse the misuse this row records, and does it stop accusing what the repairs declared
      spurious? The replayable bench is `rvsec/rvsec-agent/src/test`, which weaves the **frozen
      `jca`** (`rvsec-agent/pom.xml:106`) — so it validates the seed, not the successor, and is
      cited here to say why it is not the instrument. Commit the verdict table.
      298 data rows, 32 APKs, 23 message families, **212 (71.1 %) carrying the word `unknown`**.
      The instrument is the corrected set's accusing code interrogated directly — the `.mop`, the
      `codes.csv`, and a Java probe on the harness's own classpath — because 8.4 measured that the
      harness reports one envelope per accusing event and would undercount. Of the 86 legible
      rows: 56 are no longer accused (each against a recorded api30 clause), 6 still are, 19 keep
      the half the rule states, and 1 inverts. All 13 specifications keep an `ORDER` code, so the
      212 `unknown` rows stay accusable — and can no longer say `unknown`, since every accusation
      carries the `v=1` envelope (G-CONF 0). One widening is recorded and not repaired:
      `AES/ECB/PKCS5Padding` is admitted by the api30 rule and was not by the seed.
      Evidence: `data/gh105/evidence/f5-GroundTruthC5.md`
- [x] 8.4 Full harness differential over `data/gh104/traces/`: `--a
      backup/gh105-preimage/jca_android/` (the specification-set directory 2.11 archived) versus
      the edited set; `gh104_diff_harness.py` regenerates both monitor trees itself. Every
      `introduced`/`removed`/`moved` classification traces to a task.
      131 traces, 61 unchanged / 31 moved / 32 introduced / 7 removed; the 70 non-`unchanged`
      classifications carry 130 accusation deltas and **all 130 are attributed**, none of them to
      a gh104 task — checked against the sources, because the shared `divergence_record.csv`
      task column mixes both changes. Three of the 70 are knock-on effects and are named as
      such. Determinism was measured (two cached runs plus one full regeneration, byte-identical),
      which also surfaced that ten committed `f2-*.md` reports carried 17 envelope lines the tree
      does not produce; they are regenerated here.
      Evidence: `data/gh105/evidence/f5-HarnessDifferential.md`
- [x] 8.5 Device smoke test (one mini run, before the joint experiment; via
      `rv-experiment`/`rv-platform` only — the platform manages the entire emulator lifecycle,
      never a manually managed emulator): a sample APK instrumented with the wired set — (a) R4
      probe: record whether `OpenSSLRSAPublicKey`/`BCRSAPublicKey` `equals` is value- or
      identity-based (design Open Question 1); (b) the woven `Object`-idiom junction fires on a
      real device trace through the dexlib2 host path (Open Question 2); (c) the junction ×
      `CipherSpec` co-fire on the same `Cipher.init` joinpoint is observed and its report counts
      committed — the junction's own spec name opens a new unique-misuse bucket at the same
      `(class, method)` (design Risks; the Phase-0 pilot's third untested item). The blocking
      condition was already answered at 4.3; this run measures what only a wired chain can show.
      Four passes over `cryptoapp.apk` through the dexlib2 host path (monkey 120 s, ape 300 s,
      monkey 2×300 s, droidbot dfs_greedy 300 s), 126 advices woven, 0 plans skipped, **12
      violations, seven of them predicate reads on the new store** (`*-NOBS-*`), every one
      carrying the `v=1` envelope. (a) is answered more strongly than the probe would have:
      `AndroidKeyStorePublicKey.equals` **is** value-based, and `PredicateStore` never consults
      `equals` on the bound object — `BoundKey` hashes with `System.identityHashCode` and
      compares with `==` — so the R4 answer cannot change a verdict. (b) and (c) are proved
      structurally in the woven bytecode: 4 `invoke-static IvChainJunctionSpec_useEvent(I,
      AlgorithmParameterSpec, Cipher)` in application classes with the parameter list intact (the
      D-10 collapse does not occur on the host path), each immediately followed by
      `CipherSpec_i2Event` before the same `Cipher.init` call. The dynamic firing was not reached:
      the junction sits on the CBC/IV branch of `encryptWithSecretKey`, the method ran (pass 1
      covered it and `CipherSpec` accused there) but through its two-argument branch, and no tool
      flipped the app's mode radio group. Recorded as a reach limit of random exploration over
      this APK, not as a result.
      Evidence: `data/gh105/evidence/f5-DeviceSmokeTest.md`, logcats under
      `data/gh105/evidence/smoke/`
- [x] 8.6 Run `/rv-qa-lint-fix` over everything the change touched since 7.5 (the rv-sdd
      schema's final sequence: lint-fix → verify → code-reviewer), then `/rv-verify` (tests +
      lint + types) and `uv run pytest tests/parity --import-mode=importlib -o "addopts="`.
      Nothing but documents changed since 7.5 literally, so the scope was read as the change's
      own code — and two pockets were not clean: the three `gh105_*` gate scripts 7.5 excluded
      (2.12 was assumed to cover them; `012f9dbe` had edited one since) and the four
      `tests/parity` gate suites, one of which carried a dead `import json`. Fixed: 7 files,
      54 + 4 hunks, one redundant `nonlocal` (the same defect B10 found in `gh104_gates.py`) and
      one `W391`. Residue outside `E501`: **0**. The reformat is proved inert by regenerating the
      five gate outputs before and after (`diff -r` clean) and by the four suites still at
      **91 passed**. `tests/parity` whole: **149 passed, 3 failed**, all three pre-existing and
      outside this change (a gator jar rebuilt without regenerating its baseline; `reachesMop`
      tokens in `modules/aperv-tool/`; and `StaticAnalysisParser.parse_file()` losing its
      `package` parameter in `bd10fb0f` without the gh60 test following). Also measured: without
      `ANDROID_SDK_HOME` exported, seven parity tests error inside `lib/gator/gator` instead of
      running.
      Evidence: `data/gh105/evidence/f5-FinalVerification.md`
- [x] 8.7 Run `/rv-code-reviewer` on the change ("Review gh105-predicate-wiring implementation").
      Verdict **REQUEST CHANGES**: three criticals, ten warnings, a handful of suggestions. Every
      finding was reproduced before being accepted or refused, and two of the three criticals only
      appear outside the repository root — a reviewer trusting the root's green suite would have
      refused both. Repaired: **C1** (relative data defaults let three gates exit 0 having compared
      **0 of 24**, blaming the specification for a missing CSV — paths now anchored on `__file__`
      and the gates exit **2** when they compared nothing), **C2** (`_order_run` pinned the map and
      left the allow-list relative, so `test_inv_ins_138_gorder` was red outside the root: 91 from
      the root, **67** from `/tmp`), **C3** (`PredicateStore` held two truths in two fields and a
      reader could sample a pair that never existed — the one direction that *suppresses* an
      accusation; the concurrency test the decision ordered **refuted the review's proposed
      repair**, measuring 18 leaks with the writes already inverted, so the fix is an immutable
      `State` behind an `AtomicReference` and every read is a snapshot — `rvsec-core` **72 tests,
      0 failures**), **W1** (the allow-list matched on `(set, spec)` and ignored the witness, so one
      forgiven counterexample forgave every future one — nine of twenty-two compared specifications
      unguarded; `gate_allowlist.csv` gains a `witness` column filled from the gate's own output)
      and **W7** (`_is_allowed`, `read_allowlist`, `OrderRun` and `main()` were called by no test,
      and INV-INS-133/130 had no negative fixture: six tests and two fixtures added, each of the
      five red paths proved by mutating the gate, running, and reverting). Registered and **not**
      repaired under decision 7: **W2** — the set's only `@fail` without `__RESET` (20 of 21 reset;
      a rejected sequence re-raises `KEYPAIRGENERATOR-ORDER-00` at every later event) gets a
      `behavioural` narrative row in `divergence_record.csv`, now **288** rows (282 hunks + 6
      narratives), `check()` exit 0 — plus W3, W5, W6, W9, W10 and the 🟢 suggestions in prose.
      Four suites **97 passed** (was 91); the four gate outputs byte-identical before and after.
      Evidence: `data/gh105/evidence/f5-FinalVerification.md`
- [ ] 8.8 [BLOCKED — external: gh104 archive, which follows the joint experiment; and internal:
      groups 9, 10 and 11, whose repairs land before this change reconciles] Reconcile
      with gh104 before archive: once gh104 has archived, add the formal `MODIFIED` entry for
      its requirement "The Successor Set Carries the Predicates of Its Seed Unchanged" to this
      delta (the supersession scenario already carries the content) and delete that scenario's
      closing sentence about "this delta", which reads as process history once synced. In the
      same reconciliation window, sync this delta's `## Invariants` (INV-INS-130–148, plus the
      three restated entries for INV-INS-118/123/128) and Data Contracts to `openspec/specs/`
      with a **P4 rewrite** — migration narrative ("is superseded", "in the migration", "MUST
      remain byte-identical") restated as current state, extended to the requirement
      "Reformulated Scope of G-PRED and Retirement of `rvsec-mop-defsuses`", which describes
      events rather than steady state — and verify the 19 IDs by grep (the gh104 task-10.8
      pattern; `openspec-sync-specs` only processes the ADDED/MODIFIED headers)
- [ ] 8.9 [final commit BLOCKED on 8.8 and on groups 9, 10 and 11] `openspec status` complete; commits use
      `refs #105`;
      final commit `closes #105` after the researcher signs off completion (D-9 single-change
      scope ratified 2026-08-20; Group 10 of gh104 and campaign validation stay with the joint
      experiment in `experimento-gh104/`, which validates both changes at once)

## 9. F6 — Repairs adjudicated from the external audit of 2026-08-25

<!-- Source: four independent external audits (docs/analise_gh105_{gemini3,gpt5,mimo-v2-7b-free,
     opus5}.md), adjudicated in docs/20260825_adjudicacao_analises_specs_jca_android.md. No claim
     entered on agreement between models: each was re-verified against the .mop of today, the
     pinned expert rule, the api30 rule, `javap -cp $ANDROID_HOME/platforms/android-30/android.jar`,
     and the project's own records. Three convergent claims were REFUTED in verification and carry
     no task — the AES keysize clause (deferred-constant, and `init(64)` throws inside the JCA
     before `generateKey()` is reached), the `SecretKey.destroy()` NEGATES (INV-INS-137; the
     default always throws, so an `after returning` advice is dead code and the variant that would
     fire is semantically inverted), and six allegedly missing `Signature` OID aliases (all 61 are
     present; the six absent Conscrypt rows are `KeyFactory` and `CertificateFactory`).

     The group is split by whether a task changes the set of programs the specification accuses.
     9.A does not and may proceed; 9.B does, and each of its tasks carries the harness delta and
     the researcher's decision, per the standing rule that a probable repair and a behavioural
     change are never bundled. Tasks 8.8 and 8.9 depend on this group.

     Verified task by task on 2026-08-25 (second session) against the four oracles, with the
     monitor regenerated from the current set, three independent sweeps re-run from scratch, and
     two differential harness pairs executed — docs/20260825_verificacao_grupo9_gh105.md carries
     the 18 verdicts with sources. What that pass changed here: 9.1 moved to 9.B (the revived
     event is a creation event and start->fail — the repair changes what is accused, as its own
     conformance_record row already said); 9.6 and 9.12 fell as redundant (the first was applied
     in the previous session, the second was repaired by task 4.5); 9.5 lost its deletion branch
     (INV-INS-132 and frozen-jca readers); 9.2's harness criterion was unsatisfiable as written
     (measured: 159/159 unchanged — the TraceRunner dedups by call site); and 9.19 was added for
     the two record-hygiene findings the adjudication had excluded (OPUS5-15/16). Implementing
     9.A then refuted one of those two in turn: 9.19(a) read `constraint_table.csv` as an oracle
     for the successor when the register speaks about the seed, and the gate that recomputes it
     measured the flip as introducing two disagreements where there are none — the task now
     records the refutation instead of ordering the edit. Two levels of review missed it because
     both read `KeyStoreSpec.mop:23` in the set being repaired; the register itself says which
     set it describes, and the habit of checking that is the group's own lesson. -->

### 9.A — Repairs that do not change what is accused

<!-- 9.1 lived here until the 2026-08-25 verification read the generated monitor: `engine` is a
     creation event and its row is {3,1,3,3} — start->fail — so reviving it accuses programs that
     are silent today. It is now the first task of 9.B, number unchanged. -->

- [x] 9.2 `KeyPairGeneratorSpec.mop:167-171`: add `__RESET;` to the `@fail` handler. It is the
      set's only `@fail` without one (20 of 21 reset), the fail state is a sink, and
      `Category_fail` holds again at every later dispatch — condition-false dispatches included,
      which neither transition nor recompute the flag (the case
      `data/gh104/traces/KeyPairGeneratorSpec-sticky-fail.txt` replays). Registered under
      decision 7 as W2 with a `behavioural` narrative row; that row is replaced by the repair.
      Two bounds the 2026-08-25 verification measured, so the record says what the repair can
      and cannot show: (a) `ErrorCollector.addError` dedups on
      (spec, code, event, class, method, location), so the re-raise is observable only at a
      **distinct call site** — the delta is at most one row per extra site, and condition-true
      events keep re-raising even after the reset (start->fail->reset each time); (b) **the
      differential harness cannot prove this repair**: measured A/B with the reset mutant,
      159/159 traces class `unchanged`, sticky-fail included — in the TraceRunner every dispatch
      shares one synthetic call site, so the side-A repeat lands in the dedup. Evidence for the
      pair is therefore the generated monitor's `reset()` clearing the category flag plus the W2
      row, not a harness class; do not gate this task on `removed`
- [x] 9.3 `PBEKeySpecSpec.mop:33-45`: `f1` and `f2` bind `char[] password` and no `PBEKeySpec` —
      no `returning`, no `target` — so the generator hands them the parameterless map and each
      runs its body on the root monitor and every live monitor of the specification
      (`PBEKeySpecSpec__Map`, `stateTransitionedSet`). Add `returning(PBEKeySpec s)` to both.
      Exact precedent: `MacSpec.f2`, task 5.3. The automaton does not move — `(f1 | f2)*` is
      already the benign loop task 3.5 installed. Stated so the harness expectation is honest:
      the fan-out multiplies **emissions**, not recorded rows — all copies share one
      (spec, code, event, site) and the ErrorCollector dedups them — so the expected harness
      class is `unchanged`, and what the repair buys is per-object trace semantics, the end of
      the set-wide dispatch, and the site class 9.7's G-BIND then locks (the 2026-08-25 sweep
      found exactly these two events with no binding, none other). The file's comment already
      states the dispatch in the present tense and only the all-`fail` row in the past; after
      the repair the paragraph is rewritten for the new binding, not corrected for tense.
      Closes the last two of the `empty-binding broadcast` sites of `conformance_record.csv`
      item (c) (`MacSpec.f2` repaired at 5.3, `SSLContextSpec.unsafe_protocol` removed at 3.6,
      `TrustManagerFactorySpec.g3/gtm1` repaired since)
- [x] 9.4 `KeyGeneratorSpec.mop:76` and `MessageDigestSpec.mop:73`: the two negated twins whose
      `condition(!ConscryptAliasTable.matches(...))` reads the monitor field
      `currentAlgorithmInstance` instead of the bound argument `alg`. The other
      six negated twins of the set read the argument (`KeyStoreSpec:63`, `MacSpec:81`,
      `KeyManagerFactorySpec:64`, `KeyPairGeneratorSpec:77`, `SecureRandomSpec:135`, and
      `CipherSpec:100` over `transformation`). The field is initialised `""` and the positive twin
      `g1` writes it only when the algorithm is admitted, so on a fresh monitor the guard is
      correct **only because** the generator emits `g1Event` ahead of `g4Event`/`g3Event` on the
      shared pointcut (`MultiSpec_1MonitorAspect.aj:366-371`, `:524-529`), and nothing in the
      tree asserts that order. Were it to invert, every safe `MessageDigest.getInstance(String)`
      would accuse through `g4`'s body with the self-contradicting envelope `expecting one of
      SHA-256,… but found SHA-256` — the `but found .` signature task 8.16 repaired in the body
      `if` guards (conformance_record.csv:53-61) and did not reach in these two `condition()`
      clauses. `KeyGeneratorSpec.g3` emits no envelope of its own — its body only rebinds the
      field and the accusation lives downstream in `gk1` — so for that file the inversion would
      be automaton-silent and the repair is hygiene against the same latent order dependence.
      Read `alg` in both. Behaviour today is unchanged by construction; measured on the pair in
      the 2026-08-25 verification: 159/159 traces `unchanged`, accusations identical event by
      event
- [x] 9.5 `rvsec-core/.../Property.java`: `GENERATED_CIPHER`, `GENERATED_MAC`,
      `GENERATED_TRUST_MANAGERS` and `WRAPPED_KEY` have zero sites across the 24 `.mop` of
      `jca_android`, and the javadoc of `GENERATED_CIPHER` states the mark is written at the
      `init` events, describing a program no live set contains — the inverse of P4. **The repair
      is the javadoc alone.** Deletion, which an earlier draft of this task offered, fails two
      checks the 2026-08-25 verification ran: all four constants are in
      `PROPERTY_CONSTANTS_AT_FREEZE` and `test_property_append_only` fails any removal
      (INV-INS-132 — the `ordinal()`/`values()` measurement licensed order-insensitivity, never
      removal); and three of the four are read outside this set — `GENERATED_MAC` by
      `jca/MacSpec.mop` and by `rvsec-crysl-mop` (`PredicateSite`, `PredicateIdioms`, tests),
      `GENERATED_TRUST_MANAGERS` by `jca/TrustManagerFactorySpec.mop` and `PredicateStoreTest`,
      `WRAPPED_KEY` by `jca/CipherSpec.mop` — so deleting them breaks the frozen set's monitor
      compilation, which is the harness's own side A. Rewrite the four javadocs to what is true:
      which frozen or archived set reads each constant, and that no live set writes it
- [x] 9.6 `proposal.md:17` said "24 of those are wired" against `design.md:490`'s "Of the 25
      wireable, **21 are wired**" — two artefacts of one change contradicting each other, and the
      wrong one the artefact an external reader cites. **Applied in the 2026-08-25 adjudication
      session**: the proposal now reads 21 and derives the four clauses left out (#30 and #23
      `vacuous`, #21 and #17 `unreachable-composition`), matching the design ledger. Verified
      against the working tree in the same day's verification pass; the edit rides the group's
      commit (uncommitted until then)
- [x] 9.7 Three gates for the three classes this audit walked through, each written so it fails
      before it passes (the task-8 discipline: prove the red path by mutating, running, reverting):
      **G-SIG** cross-checks every `call(...)` signature of the set against
      `$ANDROID_HOME/platforms/android-30/android.jar` and fails on a return-type or arity
      mismatch — this is the gate whose absence let 9.1 survive nine task groups. Its design
      carries three guards the 2026-08-25 verification proved necessary: class presence is read
      from the **jar's own zip entries, never via `javap`** — `javap` resolves `java.*`/`javax.*`
      from the running JDK's modules regardless of `-cp`, `--system none` or `-bootclasspath`
      (demonstrated on `javax.xml.crypto.dsig.spec.HMACParameterSpec`, which javap reports
      present while android-30.jar has zero entries under `javax/xml/crypto`), so a naive sweep
      greenlights exactly the class the record knows is absent; members declared on supertypes
      resolve through the hierarchy or land as notes (`SecretKey.getEncoded` is `Key`'s,
      `SecureRandom.nextInt`/`ints` are `Random`'s — the recorded DEX-residue family,
      conformance_record.csv:73); and nested types compare on binary names
      (`KeyStore$ProtectionParameter`). Two further guards the implementation discovered and
      this text did not foresee: **(iv)** `javap` prints a **constructor under the class's
      qualified name** (`public javax.crypto.spec.PBEKeySpec(char[]);`) and a method under the
      bare name, so treating the two alike reported **15** constructor pointcuts as unweavable,
      every one of them correct code; and **(v)** the gate is **scoped by platform**, because it
      compares a signature against a jar and a set written against another platform is outside
      its reach. `generic` (118 `.mop`) and `generic_new` (27) are JSE specifications — Swing,
      JMX, `java.util` — whose platform is the JDK, and this gate deliberately carries **no JDK
      oracle**, since `javap` resolving from the JDK's own modules is precisely the fallback
      guard (i) exists to refuse. They are declared, counted skips, the same discipline the F5
      gates' genericity contract states (`proposal.md:20`); unscoped, the gate produced **275**
      findings that are not defects, and the one real finding surfaced only behind them.
      **G-FORB** asserts that every `FORBIDDEN` clause of a rule **with a `.mop` in the set** has
      an accusing event — the scope matters, because the oracles carry **four** FORBIDDEN rules
      each, not two: besides `PBEKeySpec` (implemented) and `SSLContext.getDefault()` (not),
      `DigestInputStream` and `DigestOutputStream` state `FORBIDDEN on(...)` and have no `.mop`
      (they are among the 27 out-of-scope rules); unscoped, the gate is born red on rules no task
      owns. Within scope it is decidable and cheap, and the out-of-scope clauses are declared
      skips, counted.
      **G-BIND** fails when an event of a parametric specification binds no monitored object
      (no `returning`, no `target`) — the class 9.3 closes, and the one a three-line check would
      have caught at `MacSpec.f2` time; the 2026-08-25 sweep found exactly the two 9.3 sites and
      no other. Register G-SIG's inalcançabilidade findings as notes, not failures
      (`HMACParameterSpec` is absent from android-30 and is already recorded).
      Measured over the universe (`scripts/gh105_spec_gates.py --sets all`): **G-SIG** 416
      checked / 1 failed / 7 allow-listed / 7 skipped / 16 notes; **G-FORB** 18 / 2 / 12 / 14 /
      0; **G-BIND** 843 / 0 / 3 / 24 / 0. Each of the three live findings is a 9.B task awaiting
      the researcher's decision — G-SIG's single failure is 9.1, G-FORB's two are 9.9, one per
      oracle — so those two gates stay red until the tasks are approved or their deferral earns
      a `gate_allowlist.csv` row, exactly as the nine ordering divergences this change already
      keeps on purpose. 9.18 requires all four suites green, so the group cannot close around
      them. The red path was proven by mutation for each gate, and G-SIG over the frozen `jca`
      rediscovered **on its own** three defects this change had already repaired — `byte` for
      `byte[]` in `Signature.sign()` twice, `KeyManager[]` for `TrustManager[]` in
      `getTrustManagers()` — allow-listed by freeze with the successor's repair named in the
      reason. Evidence: `data/gh105/evidence/f6-three-gates.md`
- [x] 9.8 `ConscryptAliasTable` registry hygiene, no verdict effect: the file states that services
      without a specification enter the table anyway so the extraction is complete, and six
      Conscrypt `Alg.Alias` rows are missing — five `KeyFactory` OIDs and
      `CertificateFactory X.509 -> X509` — while `AlgorithmParameters` and `SecretKeyFactory` are
      in. 175 rows in the pinned `backup/gh104-analise/OpenSSLProvider.java` (KeyFactory :195,
      :196, :197, :200, :201; CertificateFactory :500 — relocated in the 2026-08-25
      verification), 169 in the table. Add the six to **both** registries — the Java table and
      `data/jca_android/alias_table.csv`, which `ConscryptAliasTableTest` asserts equal row for
      row — and update the header count, or narrow the completeness claim to what the table
      actually holds. No specification calls `matches` with those services, so no verdict moves
- [x] 9.12 **Record hygiene only — the spec defect is already repaired, and the task no longer
      changes what is accused, which is why it sits here and not in 9.B** (reclassified with the
      researcher's decision of 2026-08-25). The `end`-state `next2` omission this task originally
      rescheduled was repaired by task 4.5 of this same change (commit `a7e97294`): today's `fsm`
      lists `next2 -> end` and the regenerated monitor reads
      `Prop_1_transition_next2 = {3,1,1,3}` — a second `nextBytes()` is a self-loop, conforming
      to api30's `Ins, Seeds?, Ends*` (verified 2026-08-25; the previous adjudication copied
      item (d) from the record without checking the tree). What remains is the stale record:
      `conformance_record.csv:68` still says "Recorded, not repaired", contradicting the tree.
      Rewrite that row to name the 4.5 repair, and keep the 12,400-rows-over-43-apps mass with
      its provenance stated — it was measured on the published `jca` campaign, whose frozen set
      still carries the omission, so the row must say which set each half of it describes

- [x] 9.19 Record recompute over the two registries the 2026-08-25 verification flagged as stale
      — no `.mop` text and no verdict moves in either half. One half was applied; the other was
      **refuted by measurement**, and the refutation is what the task records:
      **(a) Refuted — `constraint_table.csv:51` (`KeyStoreSpec | KeyStore.crysl:52`) and `:72`
      (`SSLContextSpec | SSLContext.crysl:29`) are correct as they stand**, and flipping them to
      `MOP-MAIS-PERMISSIVO`, as this task originally ordered, would have *introduced* the
      divergence it claimed to fix. The premise read the wrong set: the `mop_line` column of
      those rows names the **seed**, not the successor. `jca/KeyStoreSpec.mop:23` is literally
      the expert's five store types (`JCEKS, JKS, DKS, PKCS11, PKCS12`) and
      `jca/SSLContextSpec.mop:23` the expert's two protocols (`TLSV1.2, TLSV1.3`); the 9-type
      and 3-protocol lists are `jca_android`'s (`:41-42`, `:43`). The gate says so itself —
      `gh104_gates.py:1798-1802`: the table "records the clause-by-clause comparison of the
      api30 rules against the **seed**, so it is an oracle for `jca` and for nothing else" — and
      the code loads it only when `set_name == "jca"`. **Measured**: G-CONF derives the verdicts
      independently from the `jca` set plus the expert rules and reproduces the register at
      `{"agree": 66, "disagree": 0, "not-derived": 14, "unrecorded": 0}`; with the two rows
      flipped, `{"agree": 64, "disagree": 2}`. The successor's deliberate permissivity is
      already recorded where it belongs — the `platform-value` rows of `divergence_record.csv`
      and, since (b), the two re-anchored `transcription` rows. The sweep this task asked for is
      done and is stronger than the sampling it proposed: `agree 66 / disagree 0` **is** the gate
      recomputing all 80 rows against the source, so there is no third wrong row to find.
      **(b) Applied.** The 15 `transcription` rows of `conformance_record.csv` carried the
      withdrawn anchor: `rule` pointed at `generated/api30/` and `mop_literals` described the
      pre-D-15 lists (CipherSpec citing `Api30CipherTransformationUtil`, today without a caller;
      MessageDigest listing `MD5, SHA-224, SHA-1…` where today's list is SHA-256/384/512;
      SSLContext listing api30's 7 protocols where today's list is 3; KeyGenerator listing
      ChaCha20/ARC4/…; KeyPairGenerator missing the restored 3072). All 15 re-anchored to the
      expert rule and today's literals per D-15, keeping the historical text under a
      `D-15 (2026-08-24):` paragraph — the convention `divergence_record.csv` already uses.
      Three substantive corrections came out of the row-by-row pass: `SecretKeySpecSpec`'s
      `MOP-SEM-BASE` was true of api30 and **false of the expert** (`SecretKeySpec.crysl:18`
      does declare the algorithm list), so the allow-list is back and byte-identical to the
      frozen set; `MessageDigestSpec` and `SignatureSpec` **withdrew their declared cost**,
      because the expert admits neither MD5 nor SHA-1; and nine of the fifteen move
      `changed_from_jca` from `yes` to `no`, the no-narrowing rule having reverted their
      narrowings. Only `KeyStoreSpec` and `SSLContextSpec` stay changed against the frozen set —
      the same pair (a) is about, which is why (a)'s premise looked plausible for as long as it
      did. Evidence: `data/gh105/evidence/f6-record-hygiene.md`

### 9.B — Changes to what is accused [researcher decision per task]

<!-- Each task here needs the differential harness pair, a divergence_record.csv row, and an
     explicit go/no-go. Several carry measured corpus mass from the published jca campaign; that
     mass is a ceiling on what the repair could move, never a causal attribution, and the weaver
     was repaired between that campaign and today.

     DECIDED 2026-08-25 (researcher, against docs/20260825_dossie_decisao_9b_gh105.md): every
     task of this block is GO, with two scoped exclusions and one reclassification — 9.13's third
     transition (re-`init` at `end`) is NO, no oracle licences it; 9.1 and 9.9 take the
     `PBEKeySpecSpec` idiom rather than silencing `engine` at `start`; and 9.12, which no longer
     changes what is accused, moved to 9.A.

     The order is not preference. Four tasks touch `SSLContextSpec`, and 9.1 revives an event
     whose dispatcher runs `FindOrCreateEntry` — so it accuses every origin of an `SSLContext`
     the set does not observe being born. There are three such origins today: the
     `getInstance(String, Provider)` overload with no pointcut (9.16 closes it), the `g2` context
     whose protocol guard suppresses the event while the dispatcher still creates the monitor
     (9.17 closes it), and `getDefault()` (9.9, which by design keeps accusing it — with the
     right code). Landing 9.1 ahead of 9.16 and 9.17 would buy an ordering false positive in two
     populations that have nothing to do with the defect it repairs. Execution order:
     **9.17 -> 9.14 -> 9.16 -> 9.9 -> 9.1 -> 9.13 -> 9.11 -> 9.15 -> 9.10**. -->

- [x] 9.1 `SSLContextSpec.mop:171`: the `engine` pointcut declares
      `call(public void SSLContext.createSSLEngine(..))` where android-30 declares
      `public final SSLEngine createSSLEngine()` / `(String, int)`; both weavers gate the return
      type exactly (conformance_record.csv:62, :73), so the advice is generated and has never
      fired. Change `void` to `SSLEngine`. Adds no event (the 17-event ceiling is untouched) and
      the `fsm` text does not change — but the behaviour does, which is why this task sits in
      9.B: read off the regenerated monitor, `engine`'s row is `{3,1,3,3}` (start->fail,
      s1->fail, end->end) and `SSLContextSpec_engineEvent` creates a monitor when none exists,
      so a revived event makes `SSLContext.getDefault().createSSLEngine()` — a context no
      g1/g2 ever observed — draw SSLCONTEXT-ORDER-00 where today there is silence. The row this
      task retires said exactly that ("reviving it would accuse every createSSLEngine outside
      the accepting state") and its non-repair was a researcher decision (2026-08-18), so the
      revival needs the harness pair and a go/no-go, not a hygiene pass. The s1->fail path is
      unreachable in practice (`createSSLEngine()` before `init` throws `IllegalStateException`
      and an `after returning` advice never runs). On the accepted route the only effect is
      `@match1` bookkeeping: `generatedSSLEngine[eng]` written for the first time, no reader
      (INV-INS-137). **Decide jointly with 9.9**: after both repairs, `getDefault()`'s monitor
      sits wherever 9.9's new event leaves it, and `engine` from that state must not re-create
      the ordering false positive 9.9 exists to avoid — either give `engine` a transition there
      or record the residue deliberately. **A signature sweep closed this class**: every
      `call(...)` signature of the set was re-checked against android-30 in the 2026-08-25
      verification (143 sites, class presence read from the jar's own entries) and this is the
      only return-type mismatch — which is what 9.7's G-SIG then locks
      **GO, decided 2026-08-25.** The joint design question is settled by this change's own precedent: `getDefault` enters the `fsm` as a self-loop at every state, the `PBEKeySpecSpec` idiom (`ere: (f1 | f2)* c1 (f1 | f2)* c2 (f1 | f2)*`), and **`engine` is NOT given a loop at `start`**. So `getDefault().createSSLEngine()` draws FORB-00 *and* ORDER-00, which is byte-for-byte the residue `PBEKeySpecSpec.mop:183-189` already records and the change already ratified — silencing it would mean modelling a forbidden event as an alternative opening of the ordering, the opposite of what FORBIDDEN says. The rejected alternative (`engine -> start`) would have made this task accusation-neutral at the price of a **new** G-ORDER divergence, in a file that already carries one open (task 7.1). Lands **after 9.17 and 9.16**, which close two of the three unobserved-birth origins.

- [x] 9.9 `SSLContextSpec`: `getDefault()` is FORBIDDEN in **both** oracles (`SSLContext.crysl:10-11`,
      api30 `SSLContext.cryptsl`) and the set has no event for it —
      `SSLContext.getDefault().createSSLEngine()` is silent. The omission appears in no record:
      not `divergence_record.csv`, `conformance_record.csv`, `constraint_table.csv`,
      `gate_allowlist.csv`, nor any gh105 artefact. It is an inconsistency and not a decision,
      because the only other FORBIDDEN clause of the set — `PBEKeySpec`'s two constructors — **is**
      implemented, with `ErrorType.ForbiddenMethod` and its own `PBEKEYSPEC-FORB-00/01` codes
      ("of the set" is load-bearing: the oracles carry two further FORBIDDEN rules,
      `DigestInputStream`/`DigestOutputStream`, but neither has a `.mop` here — see 9.7's
      G-FORB scope). Add the event with a `FORB` code of its own. **The event must enter the
      `fsm` with self-loops**: an event absent from the automaton gets a transition row that
      moves every state to `fail`, and the repair would trade a false negative for an ordering
      false positive — the exact defect tasks 3.2/3.6 spent a group removing. **Decide jointly
      with 9.1**: once `engine` fires, a `getDefault()` context's monitor sits in whatever state
      this task's event leaves it, and `engine` from that state is `fail` unless given a
      transition — without the joint decision, `getDefault().createSSLEngine()` draws the FORB
      code *and* the ordering false positive this task exists to avoid. `SSLContextSpec` has
      4 events of 17
      **GO, decided 2026-08-25.** Design as recorded in 9.1: self-loop at `start`, `s1` and `end`, FORB code raised in the event body. Closes G-FORB's two findings.

- [x] 9.10 `CipherSpec` is the one value-carrying specification that does not normalise: its five
      `isValid(...)` sites (`:85`, `:92`, `:100`, `:108`, `:181`) call the statically imported
      frozen `CipherTransformationUtil`, while the other eleven value specs compare through
      `ConscryptAliasTable.matches`, which folds case and resolves aliases. In `isValid`,
      `alg(t).equals("AES")` and `modes.contains(mode(t))` are case-sensitive (`:44`, `:45`; only
      the padding calls `toUpperCase()`, `:46`); the CBC padding list is `[PKCS5PADDING,
      ISO10126PADDING, PKCS5PADDING]` (`:35` — a duplicate, no `PKCS7Padding`); and the RSA
      branch admits only `mode == ""` and `mode == "ECB"` (`:64-65`), so the `RSA/None/...`
      spelling falls out. Derivable false positives: `AES/CBC/PKCS7Padding`,
      `aes/cbc/pkcs5padding`, `AES/cbc/PKCS5Padding`, `RSA/None/PKCS1Padding`.
      **This does not reopen D-15, and the licence is the mechanism, not the word "spelling"**:
      the expert clause (`Cipher.crysl:113`) does not list PKCS7, but the mappings are pinned
      Conscrypt `Alg.Alias` registrations the project already extracted —
      `alias_table.csv` `Cipher,AES/CBC/PKCS7Padding,AES/CBC/PKCS5Padding,380` and
      `Cipher,RSA/None/PKCS1Padding,RSA/ECB/PKCS1Padding,334`, today without a reader — and
      alias-resolution-then-compare against the expert value is exactly what D-15 ratified for
      the other eleven. Add a normaliser in `rvsec-core` that resolves the `Cipher` alias rows
      and folds case, then compares to the expert values; migrate the five `isValid` sites; do
      not touch the frozen `CipherTransformationUtil` and do not revive
      `Api30CipherTransformationUtil` — read in full on 2026-08-25, it transcribes the api30
      catalogue (admits `AES/ECB`, `ARC4`, `BLOWFISH`...) and its own doc closes "It is not to
      be given a caller again".
      **`IvChainJunction` is a different, second exposure**: it never calls `isValid` and
      already folds case at both mode tests (`:139`, `:173`, `Locale.ROOT`) — but it extracts
      `mode()` from the **unresolved** transformation (`:136`), so an alias spelling such as
      `PBEWithHmacSHA1AndAES_128` (canonical `AES_128/CBC/PKCS5PADDING`, alias_table:394-398)
      yields `mode() == ""` and silently skips the IV and GCM clauses. The normaliser resolves
      the alias before the parse, and both files consume it.
      Corpus mass zero for the spelling class is the external audit's estimate, not a record of
      this tree (the consolidated campaign corpus is not here) — the harness pair is the
      evidence, labelled as such
      **GO, decided 2026-08-25.** **Both halves**: the five `isValid` sites (which remove spelling false positives) and `IvChainJunction`'s unresolved `mode()` (which adds true accusations by closing the silent IV/GCM skip). Last in the execution order — it is the only task of the block that touches Java and needs the reactor build.

- [x] 9.11 `KeyPairSpec.mop:130`: `ere: c1 (gpu | gpr)*` makes the `KeyPair(PublicKey, PrivateKey)`
      constructor mandatory, but api30 `KeyPair.cryptsl:27` orders `co?, (pu*, pr*)*` and on
      Android practically every `KeyPair` comes from `generateKeyPair()`, which never fires `c1`.
      Every `getPublic()`/`getPrivate()` then draws `KEYPAIR-ORDER-00`. Measured: **668 rows over
      8 apps** (`conformance_record.csv` item (f); the audit's "100 % of this specification's
      rows" is its own corpus estimate, not derivable from the record). Repair is
      `ere: (c1 | epsilon) (gpu | gpr)*` — **not `c1?`**: the rv-monitor ERE grammar
      (`EREParser.jj`) has `~ | * +` and `epsilon` and no `?`, so the shorthand does not parse.
      Record with the repair that the oracles split here: the expert `KeyPair.crysl:20` orders
      `Con, (GetPubl | GetPriv)*` — constructor mandatory — so today's `ere` is a faithful
      expert translation, and the repair follows the project convention that ORDER answers to
      api30; the divergence goes in the row, not left implicit
      **GO, decided 2026-08-25.** The oracle split goes in the repair's own divergence row, not left implicit.

- [x] 9.13 `CipherSpec.mop:339+`: two divergences from the oracles' ORDER, both repairable by
      transitions over existing events — the `fsm` gains no event, the 17-event ceiling is not
      touched (which corrects item (e)'s remark that repairing "would need new events"), and
      that is what made this repairable at all. **Licensed by both oracles**: `s3` has no
      `update` loop, so `init; update; update` fails where api30's `updates+`
      (`Cipher.cryptsl:117`) and the expert's `Update+` (`Cipher.crysl:85`) admit it — add the
      `u*` loop at `s3`; and `s2` has no `init` loop, so `init; init` fails where both orders
      state `Inits+`/`Init+` — add `i1`/`i2 -> s2` at `s2`. **Not licensed by either oracle**:
      re-`init` at `end` (the "reused Cipher") — neither ORDER returns from the finals group to
      `Inits`, so that transition would make the `.mop` more permissive than both oracles; if
      wanted, it is a separate decision with its own divergence row, not part of this
      conformance repair. Measured: **10.814 rows over 21 apps** (a ceiling across both defect
      classes; the record does not split them). `conformance_record.csv` item (e)
      **GO, decided 2026-08-25.** **Scoped to the two licensed transitions; the third is NO.** Re-`init` at `end` stays unrepaired: neither ORDER returns from the finals group to `Inits`, so it is a project decision with its own divergence row, not conformance, and it was not taken.

- [x] 9.14 `KeyStoreSpec.mop`: the specification declares `ks` and every event binds `k`, so the
      generator emits one process-wide monitor instead of one per key store; a second `getInstance`
      before the first `load` fails. Measured: **8.655 InvalidSequenceOfMethodCalls over 22 apps
      plus 2.005 InvalidKeyStoreType**. Parametrise it. This and 9.16 touch the same file and the
      same corpus mass; sequence them as one decision. `conformance_record.csv` item (a)
      **GO, decided 2026-08-25.** Sequenced with 9.16 as one decision, 9.14 first. Second-order effect declared with the harness pair: today's single process-wide monitor, once in the `fail` sink, absorbs everything that follows into one accusation — parametrised, each store accuses for itself, so the raw row count can rise while the set of accused programs shrinks. The rows are correct; the raw count is not the metric.

- [x] 9.15 `CipherInputStreamSpec` and `CipherOutputStreamSpec` declare no parameter, so each is a
      single process-wide instance and two interleaved streams fail on the second constructor.
      Measured: **0 rows of 97.018** — the repair is free of corpus consequence and is the cheapest
      way to retire item (b), or the clearest candidate to leave recorded. Researcher's call
      **GO, decided 2026-08-25.** Repair rather than record, for consistency with 9.14 — repairing one non-parametric specification while leaving two is the inconsistency this change exists to remove. The pair will read `unchanged` by construction (0 rows of 97,018); the evidence says so and does not claim a delta.

- [x] 9.16 `getInstance(String, Provider)` has no pointcut in `KeyStoreSpec`, `SignatureSpec`,
      `MacSpec`, `KeyPairGeneratorSpec` or `SSLContextSpec`, though android-30 declares the overload
      on all five; an object obtained through it reaches its next event with the monitor at state 0,
      where every row is fail (`Signature i1[0]=8`, `Mac i1[0]=4`, `KeyStore load[0]=5`,
      `KeyPairGenerator init1[0]=4`, `SSLContext init[0]=3`). In four of the five the repair widens
      the existing two-argument pointcut and **adds no event**; only `KeyStoreSpec` lacks
      `(String, String)` as well and needs one (it has 7 of 17). Prefer `Object+` over `..` where
      the arity is known: a wildcard in the `call` signature stops the harness resolver at the
      first wildcard type (`KeyManagerFactorySpec.mop:88-90`). `conformance_record.csv` items (g)
      and (a), `gate_allowlist.csv:21` (witness `g2 l1`). `KeyStoreSpec`'s share of the mass is the
      10.660 published rows of 9.14
      **GO, decided 2026-08-25.** Sequenced after 9.14 on the shared file. Precondition of 9.1: it closes the `getInstance(String, Provider)` birth the set does not observe.

- [x] 9.17 `SSLContextSpec.mop:97`: `g2` still carries the positive protocol guard that task 3.6
      removed from `g1`, so `getInstance("TLSv1", provider)` fires no event — the dispatcher
      still **creates** the monitor (`FindOrCreateEntry` runs before the condition), which then
      sits at state 0, and the `init` that follows falls into `fail` from there (`init[0] = 3`):
      reported as a wrong call sequence instead of a rejected protocol. The api30 rule orders
      `Gets, Init, Engine?` (`SSLContext.cryptsl:39`) with the protocol under CONSTRAINTS
      (`:43`), so `getInstance` is a `Gets` whatever it was asked for. Drop the guard, exactly
      as 3.6 did, and let the `init` body accuse once with `SSLCONTEXT-PROTO-00`. The deferral
      is recorded in the file's own comment (`SSLContextSpec.mop:81-86`) and inside the 3.6 hunk
      rows — there is no standalone `behavioural` row for it (verified 2026-08-25 against the
      nine behavioural rows); the repair writes that row when it lands. Deferred at 3.6 because
      `g2` is not an orphan — this is the task that reaches it
      **GO, decided 2026-08-25.** **First of the block.** Precondition of 9.1: it closes the `g2`-suppressed birth, where the dispatcher creates the monitor at state 0 and the event never fires.

- [x] 9.18 Verification for the group: the four gate suites green over the repaired set (including
      the three new gates of 9.7, with G-FORB's scope and G-SIG's jar-entry guard as specified
      there), `gh104_divergence_record.py --check` exit 0 with every hunk of 9.A and 9.B keyed,
      the parity suites passing, and one harness pair committed per **spec-text task** under
      `data/gh105/evidence/f6-*.md` — 9.5 (javadoc), 9.6 (OpenSpec artefact, applied), 9.8
      (registry without verdict effect), 9.12 (record hygiene) and 9.19 (record recompute) carry
      no pair; 9.2's pair is committed with its measured `unchanged` verdict and the
      monitor-inspection evidence the task specifies, never as a `removed` gate. No task of this
      group is closed on a gate exit code alone — artifact inspection, per R5/R6

## 10. F7 — Repairs adjudicated from the internal conformance validation of 2026-08-25

<!-- Source: the internal validation docs/20260825_validacao_conformidade_jca_android.md — six
     independent audits over the tree at 14dd8093 (four spec families clause-by-clause against
     both oracles, one mechanical pass that re-ran every gate and the gh106 conformance CLI
     M0–M4, one methodological), consolidated the same day. No external model's analysis was
     read. Every finding ordered below was re-verified against the primary sources during this
     adjudication, and the pass refuted one claim on its way in: the audit's case-variant
     mechanism for the splitter finding ("aes" vs "AES" → VIOLATED) is wrong — the store's
     `ValueKey` folds `String` values to lower case (`PredicateStore.java:171`), so pure case
     variants already match and the exposed class is alias/composite spellings only (see 10.10).
     The group was also checked task by task against group 9 so nothing is ordered twice:
     9.10 covered the five `isValid` sites and the junction's `mode()` — the `i2` splitter is a
     third exposure it did not reach; 9.19(a)'s refutation governs `constraint_table.csv`
     (`mop_line` names the seed, the register is an oracle for `jca` and nothing else), so no
     task here flips or re-anchors any of its rows — the two audit claims against the GCM and
     Iv rows are re-read under that ruling as anchor ambiguity, already answered by the
     register's own contract.

     Split as group 9: 10.A does not change the set of programs the specifications accuse and
     may proceed; 10.B does, and carries the harness pair, the divergence row and the
     researcher's decision per the standing rule. Tasks 8.8 and 8.9 depend on this group.
     Ordering: 10.1 and 10.2 first (they turn the successor's CLI verdict from a structural
     false red into a measurement); the record tasks 10.3–10.9 in any order; 10.10 last — like
     9.10, it is the group's only Java-touching task and needs the reactor build.

     D-16 (researcher, 2026-08-25) landed after this group was drafted: the api30 oracle is
     withdrawn entirely. Citations to `*.cryptsl` inside this group describe the records as
     they stand today; group 11 re-anchors them to the expert rules where the record
     survives, and a group-10 task that edits such a record coordinates with the group-11
     task that re-anchors it rather than writing the api30 citation back. -->

### 10.A — Repairs that do not change what is accused

- [x] 10.1 `data/jca_android/gate_allowlist.csv`: four G-2a hits with no covering row make
      `gh104_gates.py` exit 1 over `jca_android` (measured 2026-08-25): `PBEKeySpecSpec.f1`,
      `PBEKeySpecSpec.f2` (identity transition rows since 3.5's benign loop, bound since 9.3),
      `SSLContextSpec.getDefault` (self-loop at every state by 9.9's design) and
      `SecureRandomSpec.g4` (self-loop absorption, F1). All four are the same idiom the
      existing G-2b'/G-2a rows already allow for eight other events — accuser in the body,
      no state change — so the repair is four allowlist rows with per-event reasons citing the
      task that created each shape, never a gate edit. A row with an empty reason allows
      nothing (the register's own rule)
- [x] 10.2 `scripts/gh104_gates.py`: G-PRED is superseded for `jca_android` (README, G-PRED2 +
      `predicate_graph.csv` are the successor's accounting) but the CLI still sums its 23
      structural failures into the global `ok`, so every invocation over the successor exits 1
      by construction — a false red that trains readers to ignore the tool (R5/R6 class).
      Scope G-PRED to the sets it still governs (`jca`'s byte-identity lock, untouched);
      the CLI must exit 0 over `jca_android` when every applicable gate passes. Close the
      coverage gap that let this live: the parity suite asserts G-2, G-ERE, G-6', lint,
      message and G-CONF for `jca_android` but not G-2a
      (`tests/parity/test_gh104_structural_gates.py:388-431`), which is how the pytest suite
      stayed green while the CLI was red — add the G-2a assertion so the two instruments
      cannot diverge silently again
- [x] 10.3 `data/jca_android/README.md` refresh — the census is the register the message gate
      proves, and the prose fell three edits behind it: the five "112" mentions (site census
      §, codes.csv §) become 115, with the evolution stated (112 → 114 at `5bc5c893`,
      `SECRETKEYSPEC-ALG-00/01`; → 115 at `cc6d64bc`, `SSLCONTEXT-FORB-00`, task 9.9); the
      "five purely predicate-guarded accusers … are likewise all alive" paragraph is false
      against the tree (IvParameterSpec c3/c4 and PBEKeySpecSpec err2/err3 fused by F1/F2,
      SecureRandomSpec setSeed3 fused into setSeed2) and is rewritten for the successor's
      actual shape; the propagator paragraph ("each exists only to write a Property another
      specification's condition() reads … removing either would silently disarm a
      condition()") is rewritten for RandomStringPassword's post-`5f64c8de` role — it writes
      nothing and no `condition()` reads it; the file exists as the negative record of the
      measured laundering ponte, and the paragraph must say that instead; and the "nine
      ordering divergences the set keeps on purpose" sentence (README:459) counts a state 7.6
      left behind — 9.11 repaired KeyPairSpec's and 9.16 replaced KeyStoreSpec's witness, so
      the allowlist holds eight G-ORDER rows today and the sentence restates the current count
      with the two repairs named
- [x] 10.4 `data/jca_android/predicate_graph.csv` refresh — the register is one generation
      behind the tree (23/08 vs the 7.1 map and the 9.x repairs of 25/08): the KeyGenerator
      rows and the KeyPairSpec rows claim "`order_alphabet_map.csv` has no row for this file
      at all" while the completed map carries both (`:163-171`, `:177-179`); the KeyPairSpec
      rows justify the body write with the pre-9.11 automaton ("transition row {2,1,2} sends
      it to the fail state") which `(c1 | epsilon)` made false; and three records cite
      `KeyGenerator.cryptsl:60` for `randomized[ranGen]` where the clause sits at `:52` (the
      file has 60 lines; `:60` is blank). Regenerate or hand-correct, and re-run the graph
      gate to confirm 0 failing after the refresh
- [x] 10.5 `divergence_record.csv` and sibling-register hygiene: (a) rows 91, 134, 210 and 288
      — the four ConscryptAliasTable-import hunks of KMF, KeyStore, SSLContext and TMF —
      carry the KeyGeneratorSpec reason verbatim ("KeyGenerator.cryptsl:45 … ChaCha20, ARC4,
      DESede…"), which describes none of the four files; rewrite each for its own list.
      (b) rows 95/96 still state KMF's list as `{PKIX}` with "SunX509 leaves as a narrowing"
      — reversed by D-15; add the `D-15 (2026-08-24):` adendum the register's convention
      already uses (the conformance row 11 got it, these did not). (c) add the residue row
      `TrustManagerFactorySpec.mop:74-78` promises ("a rejected algorithm whose factory is
      never `init`ed is now accused by nothing") — the comment says "recorded … 
      (divergence_record.csv)" and no TMF row records it; the harness evidence
      (`f1-TrustManagerFactorySpec.md`, trace `sunx509-no-init`, class `removed`) is the
      row's citation. (d) `conformance_record.csv:74` concludes the KPG `@fail` `__RESET`
      edit "is reverted" — superseded by 9.2, which reimplemented it; add the supersession
      adendum (the row-19 pattern). (e) `conformance_record.csv:4` still claims the DHGen
      value test is registered as MOP-SEM-BASE in the constraint table; the 80-row table says
      IGUAL — correct the way row 19 was corrected. (f) `gate_allowlist.csv:34` (jca, G-FORB,
      getDefault) still reads "adding the event is task 9.9 … until it lands" — 9.9 landed;
      restate for the current state (the jca omission stands, the successor's row is closed).
      (g) `KeyStore.cryptsl` declares `scE`/`skE1`/`skE2` (`:67-71`) that no `.mop` event
      covers and **no register records** — the omission is a consequence of the rule's own
      ORDER (`:79` uses only `gE`/`sE`, so there is no G-ORDER divergence to record and the
      map format has no disposition for a rule-side symbol), but a reader auditing alphabet
      coverage should find that reasoning written down rather than re-derive it; add the
      register entry where the `iv`/`d` precedents live. (h) erratum: design.md D-3 and the
      proposal cite the kept `remove()` at `PBEKeySpecSpec.mop:74`; in the frozen seed it is
      `:72` (the `:74` offset belongs to the migrated copy) — one-line citation fix
- [x] 10.6 Stale in-file comments, P4 pass — prose only, zero behaviour, and where a comment
      states a withdrawn justification the task restates the current decision rather than
      deleting the trace: `PBEKeySpecSpec.mop:80-91` (block asserts the `randomized[password]`
      read "is kept unchanged" and PBEKEYSPEC-CONSTR-01 lives — contradicted by `:116-135` of
      the same file and by `codes.csv`; rewrite for the post-5.4 state); `MacSpec.mop:329-332`,
      `GCMParameterSpecSpec` and `SecretKeySpec.mop:84-85` ("one of the thirteen still absent
      from order_alphabet_map.csv" — the 7.1 map carries all three); `KeyPairSpec.mop:100-113`
      (the body-write justification describes the pre-9.11 automaton and promises "this write
      moves to `@match` when 7.1 lands" — 7.1 landed and the write correctly stayed, because
      with `(c1 | epsilon)` the body IS the acceptance point on both routes; the comment must
      state that decision, and any actual move of the write would be a 10.B task, which this
      task explicitly is not); `IvChainJunction.mop:310-311` ("both symbols" for a seven-symbol
      alphabet); `PBEParameterSpecSpec.mop:12` (file title says "GCMParameterSpec" — the
      row-289 class of defect, never corrected here); `KeyPairGeneratorSpec.mop:151` (the
      envelope's `exp='the key size api30 KeyPairGenerator.cryptsl declares…'` attributes the
      implemented list to the withdrawn anchor — the list is the expert's, 3072 included;
      this one edits an emitted message text: code and event unchanged, so the harness class
      is `unchanged` under the (event, code) comparison, and the pair is committed to prove it)
- [x] 10.7 `GCMParameterSpecSpec.mop` names `List` and `Arrays` (`:22`) and imports neither —
      it compiles only because the merged monitor inherits the imports another file
      contributes, the exact dedupe fragility that broke 11.9 twice and that the README's
      set-wide import rule exists to prevent. Add the imports in the set's uniform style;
      expected monitor delta is import-lines-only and the committed byte-diff proves it
- [x] 10.8 Register-only rows for the four behavioural findings the validation surfaced and
      this change defers (the standing rule: a probable repair and a behavioural change are
      never bundled, and none of these carries a researcher decision): (a) the 2-arg-overload
      guard family — `KeyManagerFactorySpec.g1/g2` plus its `g3→unsafeAlg` route (the one
      mirror 3.2/3.6/9.17 did not reach: `unsafeAlg` rejects the `init`, so a rejected
      algorithm draws ORDER-00 **and** ALG-00), `TrustManagerFactorySpec.g2`,
      `MessageDigestSpec.g2/g3`, `SignatureSpec.g2`, `SecureRandomSpec.g2` — same misuse,
      different answer per file; (b) `KeyStoreSpec`: constraint governs transition (`g2` makes
      the following `load` fail) and the type accusation lives only in `gk1`, so a rejected
      type that is loaded but never asked for a key draws ORDER and never KSTYPE; (c)
      `CipherSpec` fsm `:402-412`: the `end` state accepts `wkb1` after `f2` and `f2` after
      `wkb1`, where both oracles make `w+` and the finals group alternatives — more
      permissive than either oracle, false-negative only, inherited from the seed byte for
      byte; (d) predicate writes in event bodies execute even when the dispatched transition
      fails (`TrustManagerFactorySpec.gtm1`, `KeyManagerFactorySpec.gkm1`) — an
      over-approximation only reachable in traces already carrying ORDER. Each becomes a
      narrative/`behavioural` row with the mechanism and the deferral, no spec text moves
- [x] 10.9 Evidence hygiene: the 8.4 differential (131 traces, "130/130 attributed") ran on
      2026-08-23 under the pre-11.11 harness, whose `classify()` compared accusing event
      names — an accusation added at an already-accused event was invisible by construction,
      so the attribution is a claim of the pre-repair instrument. Re-run the full 8.4 sweep
      under the (event, code) harness (seconds, per its own evidence) and refresh
      `f5-HarnessDifferential.md`; if any trace moves class, attribute it before this group
      closes — and if none does, the evidence says so under the repaired instrument instead
      of the broken one

### 10.B — Changes to what is accused [researcher decision per task]

- [x] 10.10 `CipherSpec.mop:166-167`: the `GENERATED_KEY` tuple splitter is the third exposure
      of the defect 9.10 repaired — `validate(Property.GENERATED_KEY, key,
      alg(c.getAlgorithm()))` calls the statically imported frozen
      `CipherTransformationUtil.alg` (split on `/`, no alias resolution) while every other
      value site of the same event goes through `CipherTransformationNormalizer` (its `alg`
      is `:101`). The mechanism, verified this adjudication: the store folds `String` value
      positions to lower case (`PredicateStore.java:171`), so pure case variants already
      match and the audit's "aes vs AES" scenario is refuted — the exposed class is
      **alias/composite spellings**: `Cipher.getInstance("AES_128/CBC/PKCS5Padding")` with a
      `KeyGenerator("AES")` key forms the tuple `("aes_128")` against the producer's
      `("aes")` → VIOLATED → a false `CIPHER-CONSTR-00` the envelope presents as positive
      misuse evidence. Route the splitter through the 9.10 normaliser. **Two questions the
      harness pair must answer before the researcher decides, because the repair may be
      incomplete as stated**: (i) `CipherTransformationNormalizer.alg("AES_128/CBC/…")`
      plausibly yields `AES_128`, which still mismatches the producer's `AES` — if so, the
      comparison target needs a decision (fold the `AES_128/192/256` service family into
      `AES`, or record the family as a deliberate mismatch) and that decision is recorded
      before any edit; (ii) whether any affected program is accused **only** by the false
      CONSTR (a new-silence risk) or every affected spelling also draws `CIPHER-ALG-0x` from
      the value check, making the repair pure category hygiene. Divergence row + satisfy/
      violate pair per the 9.B discipline; like 9.10, needs nothing from the reactor unless
      the normaliser API itself moves
- [x] 10.11 Verification for the group, the 9.18 mirror: `gh104_gates.py` exit 0 over
      `jca_android` (post-10.1/10.2, G-2a green with the four rows, G-PRED scoped); the
      G-2a parity assertion of 10.2 in place and red-green tested; the predicate-graph gate
      0 failing after 10.4; README counts re-derived by the census parser, never asserted as
      literals; harness pairs committed for 10.6's message-text edit (`unchanged`), 10.7
      (import-only byte-diff) and 10.10 (researcher-decided); `gh104_divergence_record.py
      --check` exit 0 with every 10.5/10.8 row keyed. No task of this group closes on a gate
      exit code alone — artifact inspection, per R5/R6

## 11. F8 — Sole oracle: total withdrawal of MetaCrySL (D-16)

<!-- Source: researcher decision of 2026-08-25 (design.md D-16), superseding D-15's "the scope
     is values only". The sole oracle of `jca_android`, for values, ORDER, alphabets and
     predicates alike, is the pinned expert copy `RVSec-replication-package/tools/rules/`
     (49 rules, sha256 `d7bcc019…`). `MetaCrySL/generated/api30/` keeps no oracle role: it is
     the historical input of the pre-D-16 records, named only inside supersession adenda.

     Discipline: 11.1 and 11.2 are pure derivation — they produce the expert ledger and the
     expert alphabet map plus the delta against the api30-derived records, and NOTHING moves
     on their strength alone. Every behavioural consequence they surface (a read that
     returns, a wiring that opens, an ORDER tightening) enters 11.5/11.6 with the 9.B
     discipline: harness pair, divergence row, researcher go/no-go per clause. Platform-limit
     records (protected constructors, the absent javax.xml.crypto class, destroy() throwing,
     the Integer cache) were measured on android-30, not derived from api30 — they carry over
     as records against the expert rule, re-cited, never re-litigated. "No new accusation
     classes" stands: the 28 expert rules without a `.mop` gain no specification here.
     Ordering: 11.1 → 11.2 → 11.3 (the instruments must point at the expert rules before any
     record claims conformity to them) → 11.4 (records) → 11.8 (spec text) → 11.9 (the two
     dispositions D-17 re-derives) → 11.5/11.6 (researcher-decided) → 11.7. Tasks 11.8 and
     11.9 were added on 2026-08-26, after 11.2 and 11.1 measured what the group had not:
     they carry numbers out of sequence because task ids are keys in
     `divergence_record.csv` and in committed evidence, and are never renumbered.
     Tasks 8.8 and 8.9 depend on this group. -->

- [x] 11.1 [record] Re-derive the predicate ledger from the 49 expert rules: sweep every
      `REQUIRES`/`ENSURES`/`NEGATES` of `RVSec-replication-package/tools/rules/*.crysl`,
      produce the expert ledger (the D-16 sibling of design.md's 36-clause table) and the
      delta table against the api30 ledger — clause by clause: appears only in expert /
      only in api30 / in both with different binding or arity. Known deltas, each verified
      against the rule text on 2026-08-25 and named in D-16: `Mac.crysl:54`
      `generatedKey[key,_]`; `SSLContext.crysl:18,34` (`i1` binds `random`; #30's `vacuous`
      falls — it was an api30 artifact); `TrustManagerFactory.crysl:29`
      `generatedManagerFactoryParameters[params]`; `SecureRandom.crysl:46`
      `randomized[lSeed]`, `:52` `randomized[randInt] after nI`;
      `KeyPair.crysl:27` `generatedKeypair[this,_] after Con`; `SSLContext.crysl:32` names
      `generatedKeyManagers[km]` (plural) where the wired read consumes the singular-named
      property — resolve the pairing in the ledger, not in code. Re-classify every clause
      with the established dispositions (wired / unmonitored-* / vacuous /
      unreachable-composition / unclosable), each against the expert text; a disposition
      that only held under api30 is re-derived, not copied
- [x] 11.2 [record] Re-derive `order_alphabet_map.csv` against the expert `EVENTS`/`ORDER`
      for the 21 paired specifications: every map row re-keyed to the expert rule's symbols
      and line numbers; the aggregate labels differ (expert `Get, Load, GetEntry…` vs api30
      `Gets, Loads, gE…` — the KeyStore pair was diffed on 2026-08-25 and is structurally
      identical), so most rows re-anchor mechanically, and the task lists the specs where
      the two rules' alphabets genuinely differ (SecureRandom's `nI`/`randInt` family, the
      Mac/Signature event splits) rather than assuming zero. The two no-rule files
      (IvChainJunction, RandomStringPassword) keep their declared prose skips, restated
      against the expert catalogue ("the expert rules enunciate no such rule")
- [x] 11.3 [gates] Point every instrument at the sole oracle: `gh105_order_gate.py` and the
      `gh104_gates.py` `--crysl` input read `RVSec-replication-package/tools/rules/`
      (G-CONF's `--value-crysl expert` is already there — the two flags collapse into one);
      the parity fixtures that load api30 rules re-anchor; no CLI keeps an api30 code path.
      Genericity contract holds: gates still derive their universe by enumeration, skip
      declaredly, and count what they skipped
- [x] 11.4 [records] Single-oracle records: `conformance_record.csv` stops naming two rules
      per specification — one `rule` column meaning (the expert rule), with the api30
      citation preserved inside a `D-16 (2026-08-25):` supersession adendum on every row
      that was derived against it; `divergence_record.csv` rows whose reason cites a
      `*.cryptsl` gain the same adendum; `data/jca_android/README.md` replaces "The scope
      is values only" with the sole-oracle statement and re-states which records were
      re-derived (11.1/11.2) and which carry adenda; `gate_allowlist.csv` G-ORDER rows
      re-justified against the expert ORDER — a divergence that only existed against api30
      closes, one that persists against the expert rule is re-cited. Grep gate for the
      group: outside supersession adenda and the archived set, nothing names api30 as an
      authority — no artifact of `data/jca_android/`, no `.mop` comment, **and no emitted
      message**. The third clause is not a widening for tidiness: written as "no `.mop`
      comment" the gate reads over the five report strings task 11.8 repairs, because a
      string handed to `ErrorDescription` is not a comment. The gate is what proves 11.8
      complete, so it has to be able to see what 11.8 fixes
- [x] 11.8 [spec text] The five emitted messages that still name the withdrawn oracle as
      their authority. Measured 2026-08-26, by sweeping the report strings of the set rather
      than reading a list: `SSLCONTEXT-FORB-00` (`SSLContextSpec.mop:125`, `msg='...
      is forbidden by api30 SSLContext.cryptsl'`), `GCMPARAMETERSPEC-CONSTR-00` and
      `-CONSTR-02` (`GCMParameterSpecSpec.mop:66,110`, `exp='a tag length api30
      GCMParameterSpec.cryptsl admits'`), and `PBEKEYSPEC-FORB-00` and `-FORB-01`
      (`PBEKeySpecSpec.mop:45,52`, `msg='... is forbidden by api30 PBEKeySpec.cryptsl'`).
      This is text the tool shows a person reading a violation report: under D-16 it cites an
      authority that no longer exists. Task 10.6 made this exact repair for the sixth
      (`KeyPairGeneratorSpec.mop:151`, now `exp='the key size the expert
      KeyPairGenerator.crysl declares for RSA'`) and reached only that one, because it worked
      from the internal validation's findings and not from a sweep — which is the reason this
      task states its own method. Each message is re-anchored on the expert clause it
      implements, cited by line: `GCMParameterSpec.crysl:18`, `PBEKeySpec.crysl:10-11`,
      `SSLContext.crysl:11`.

      **The task must prove it is label and not verdict, not assert it.** The three clauses
      say the same thing in both catalogues — `{96, 104, 112, 120, 128}` is the tag-length
      list of the expert rule and of the api30 one alike, both FORBID the same two
      `PBEKeySpec` constructors, and both FORBID `getDefault()` — so no program changes class
      and the committed harness pair reads **`unchanged`** under the `(event, code)`
      comparison, as 10.6's did (`data/gh105/evidence/harness/f7-KeyPairGeneratorSpec.md`).
      A pair that reads anything else is this task getting it wrong, not the measurement
      surprising: it means a message was re-anchored onto a clause the set does not implement,
      and the edit comes back out.

      Two consequences the precedents already name and this task inherits: editing a message
      re-keys its hunk, so `divergence_record.csv` rows come back as `unrecorded`/`stale`
      pairs to re-key by `(file, summary)` (task 10.6); and any line added above a report site
      moves the `codes.csv` anchors of that file, which the message gate's `code-anchor` check
      accuses with the right line to use (tasks 7.2, 10.7). Both are part of the task, not
      surprises after it

- [x] 11.9 [record] The two dispositions D-17 re-derives, and the census that comes with
      them. **No `.mop` changes, no accusation changes class, no harness pair is owed**: the
      whole task is `predicate_ledger.csv`, `predicate_graph.csv` and the prose that cites
      them. It exists because 11.1 asked for every disposition to be re-derived rather than
      copied, and one came through with the right conclusion and a reason that had changed
      class — which is the failure mode a re-derivation is for, and the one a green ledger
      cannot show.

      (a) **Ledger clause #34** (`KeyPairGenerator`, `algorithm in {"DiffieHellman","DH"} =>
      preparedDH[params]`, `KeyPairGenerator.crysl:37`) moves from `unreachable-composition`
      to `unmonitored-producer`. Task 5.8's measurement stands and is re-cited, not repeated:
      the JCA raises `InvalidAlgorithmParameterException: Inappropriate parameter type` for
      `KeyPairGenerator.getInstance("DH").initialize(new DHGenParameterSpec(2048, 0))` on
      Temurin 21. What falls is the sentence it rested on — "a DH key pair is initialised
      from a `DHParameterSpec`, which no rule ensures". The generated catalogue states no
      `DHParameterSpec.cryptsl`; the oracle states `DHParameterSpec.crysl:21 ENSURES
      preparedDH[this]`, and that is the type `initialize` accepts. The row already carries
      the evidence — `counterparts` reads `DHGenParameterSpec|DHParameterSpec` and
      `counterparts_with_mop` reads `DHGenParameterSpec` alone. Still not wired, and the
      reason is now the honest one: a read at `KeyPairGeneratorSpec.init3/init4` answers
      `NOT_OBSERVED` for every conforming DH program because the producer it uses is
      unmonitored, not because no producer could exist. The new reason must say what would
      close the clause — a `.mop` for `DHParameterSpec` — and say in the same breath that
      writing one is a new accusation class, which D-16 keeps out.

      (b) **Ledger clause #38** (`Mac preparedHMAC[params]`, `Mac.crysl:53`) is re-derived
      and survives verbatim, which is what makes (a) a finding rather than a hunch. Its
      producer is `javax.xml.crypto.dsig.spec.HMACParameterSpec` (`HMACParameterSpec.crysl:14`),
      of the `java.xml.crypto` module, and the api30 `android.jar` carries no entry whatever
      under `javax/xml/crypto` — a fact about the platform, not about a catalogue, so the
      substitution of oracle cannot touch it. The row is re-cited against the expert lines
      and its disposition is left where it is. **The task closes only if both halves are
      derived**: one row that moved and one that did not is the shape of a re-derivation;
      two rows that moved, or none, means the sweep was answering a different question.

      (c) **The census of what the set requires and cannot observe**, stated as a record and
      never as a backlog. Six predicates the set's own specifications require have no
      producer it can observe: `preparedRSA` (#19), `preparedDSA` (#18), `preparedEC` (#20,
      `unclosable` — no rule of the catalogue ensures it), `preparedOAEP`, `preparedAlg` (#7)
      and `generatedManagerFactoryParameters`. `preparedOAEP` is the one the oracle *adds*:
      `Cipher.crysl:140` states `mode(transformation) in {"OAEPWith…"} => preparedOAEP[paramSpec]`
      and the generated catalogue stated no such clause, so it enters the record for the
      first time here, at `unmonitored-producer`, as 11.1's delta already derived. The census
      is derived by enumeration from `predicate_ledger.csv`, never listed by hand, and it
      carries the standing conclusion: closing any of the six means a specification for a
      rule the set does not have, which D-16 keeps out of this change.

      (d) **The reciprocal half, so the census cannot be read as one-sided**: every
      `Property` the set writes and nobody reads already carries a write-side disposition
      (`omission`/`propagation`), and the sweep re-states which of them the oracle could ever
      give a reader — `preparedPBE` and `speccedKey` are required only by rules with no
      `.mop`, while `digested`, `signed`, `verified` and `generatedKeypair` are required by
      **no rule of the 49 at all**. Those four are dead ends of the oracle and not of this
      set, and saying so is what keeps a future reader from proposing a wiring for them

- [x] 11.5 [researcher decision per clause — behavioural] The wirings the expert oracle
      restores or opens, each through the 9.B discipline (harness pair, divergence row,
      go/no-go): (a) `Mac generatedKey[key,_]` — the read returns on the new store, in the
      `init` event bodies, three-valued with its own CONSTR/NOBS codes; the 4.9 deletion is
      superseded (its rationale was "the api30 rule does not declare the clause", which
      D-16 voids); the seed's measured failure mode (guard in `condition()` masking
      MAC-ALG-00 under MAC-ORDER-00) is exactly what the body placement avoids;
      (b) `SSLContext randomized[random]` — `i1: init(km, tm, random)` binds it, so the
      event gains the binding and the read, producer = the RANDOMIZED hub; #30's row and
      `SSLContextSpec.mop`'s vacuous comment fall with it; (c)
      `TrustManagerFactory generatedManagerFactoryParameters[params]` — both ends checked
      against the set: the producer rules (`CertPathTrustManagerParameters`,
      `KeyStoreBuilderParameters`) have no `.mop`, so the expected disposition is
      `unmonitored-producer`, recorded not wired — the task exists so that conclusion is
      derived under the expert oracle, not assumed; (d) `SecureRandom randomized[lSeed]` —
      the `long` position boxes fresh (the Integer-cache measurement extends to `Long`);
      expected disposition platform-limit record, derived not assumed; (e) any further
      clause 11.1's delta surfaces, one task-line each, same discipline
- [x] 11.6 [researcher decision per spec — behavioural] ORDER deltas against the expert
      rules, from the re-anchored G-ORDER sweep (11.2+11.3): every hit either allow-listed
      with an expert-anchored reason or repaired under a decision. The named case:
      `KeyPair.crysl:20` orders the constructor **mandatory** and the 9.11 automaton is
      `(c1 | epsilon)` — the adjudication weighs the 668-line measurement (the platform
      constructs the pair inside `generateKeyPair()`; the app never calls `c1`) and, if the
      automaton stands, writes the divergence record against the expert rule saying exactly
      that; obedience to `co?` is no longer a reason that exists. Same treatment for every
      divergence the sweep finds that the api30 anchor was silently absorbing
- [ ] 11.7 Verification for the group, the 9.18/10.11 mirror: all gates green over the
      re-anchored inputs; the 11.4 grep gate clean (no api30 authority outside adenda); the
      expert ledger's arithmetic closed (wired + recorded + unclosable = total, derived by
      enumeration, never asserted) and **unmoved by 11.9** — D-17 renames one disposition and
      must shift no count, which is the cheapest check that a re-derivation stayed a
      re-derivation; harness pairs committed for every 11.5/11.6 task that
      moved an accusation, `unchanged` proofs for the record-only ones and for 11.8's five
      messages;
      `gh104_divergence_record.py --check` exit 0 with every new row keyed. No task of this
      group closes on a gate exit code alone — artifact inspection, per R5/R6
