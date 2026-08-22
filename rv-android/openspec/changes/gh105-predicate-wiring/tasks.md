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

## 5. F3 — Wire the 24 wired REQUIRES clauses, record the rest (topological)

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
- [ ] 5.4 `randomized` hub A (ledger #11, #24, #25): `GCMParameterSpec` `randomized[src]`,
      `PBEKeySpec` and `PBEParameterSpec` salts; junction where co-observable, store where not,
      mechanism recorded per chain in `predicate_graph.csv`
- [ ] 5.5 `randomized` hub B (ledger #13, #33, #6, #30): `KeyGenerator` (**not**
      KeyPairGenerator), `SecureRandom` self-chain, `Cipher.init` `ranGen` (store-side — zero
      CipherSpec events); `SSLContext randomized[sr]` (#30) recorded `vacuous` — `Init:
      init(kms, tms, _)` binds `sr` in no event, so it can have no read site; drop the autoboxed
      argument writes (`SecureRandomSpec.next1/next3` mark the int argument today)
- [ ] 5.6 `generated*key` family A (ledger #5, #15, #16): producers at acceptance
      (`KeyGenerator`, `KeyPairGenerator`, `SecretKeyFactory`, `KeyStore`); consumer
      `Cipher.init` `generatedKey[key, part(0,"/",transformation)]` (arity-2, splitter applied
      by the caller, store read replacing the `i2` guard — zero new events); `KeyPair`
      `generatedPrivkey`/`generatedPubkey`. The producer list includes `SecretKeySpecSpec`'s
      `@match` write, which task 4.10 migrated to the new store at arity 1 with a recorded reason:
      it rises to the rule's `generatedKey[this, alg]` here, in the same commit as the consumer,
      because the two arities must move together or the read returns `VIOLATED` on a conforming key
- [ ] 5.7 `generated*key` family B (ledger #34, #35, #8): `Signature`
      `generatedPrivkey[priv]`/`generatedPubkey[pub]` (Signature's own clauses — not
      `generatedKey`); the Cipher negated `!macced` (#8) via `validateAbsent`, with the `MACED`
      producer write added at the Mac rule's acceptance point (zero sites today)
- [ ] 5.8 `prepared*` guarded clauses (ledger #10, #17, #20): `preparedGCM` (`{GCM} =>`, guard
      evaluated in the body before the read) and `preparedDH` (`KeyPairGenerator {DH} =>`);
      `preparedEC` (#20) recorded `unclosable` — no producing rule exists; deliberate-omission
      records for the **9 in-set ENSURES-only dead ends** (`preparedPBE`, `generatedSSLContext`,
      `generatedSSLEngine`, `signed`, `verified`, `digested`, `generatedKeypair`,
      `cipheredInputStream`, `cipheredOutputStream`): no fabricated read for any, no fabricated
      write for the two stream predicates that have none, and the eleven existing write sites of
      the other seven were already placed by Group 4 — ten by 4.13/4.14, and
      `PBEParameterSpecSpec.mop:62` by its own file pass 4.7
- [ ] 5.9 TLS chain (ledger #14, #36, #28, #29): `generatedKeyStore` →
      `KeyManagerFactory`/`TrustManagerFactory`; `generatedKeyManager[kms]` /
      `generatedTrustManager[tms]` → `SSLContext.init` (bound-first API — `kms`/`tms` are
      reference arrays a varargs head would spread). Pairs with 6.2's pointcut repair
- [ ] 5.10 Leaf clause and the record pass: `preparedKeyMaterial[keyMaterial]` (#32 — consumer
      `SecretKeySpecSpec`, producer `SecretKeySpec.mop` `getEncoded`), un-conflated with 6.1 in
      the same commit; then the 10 non-wireable clauses recorded with their category, each
      exactly once, here (ledger #1, #2, #3, #4, #7, #18, #19, #26, #27, #31 — the ledger's task
      column is the single source). Task 4.13 also feeds this task a record it measured and
      deliberately did not duplicate: api30 `KeyPair.cryptsl:39` states
      `generatedKeypair[this, _] after co` and `KeyPairSpec.c1` has no write for it. None was
      fabricated (researcher decision, 2026-08-22) — the predicate is required by no rule of the
      oracle, its other producing site is `KeyPairGeneratorSpec.mop:111` (task 4.14), and a
      clause with no site has no row in `predicate_graph.csv` to carry the record, because that
      inventory is of sites. Record it here, the way task 4.12 fed task 6.5
- [ ] 5.11 Closure sweep over **all 21 written `Property` values**, not only the named ones:
      every write has its reader or its deliberate-omission record, and the read-only gap
      (`GENERATED_PRIVATE_KEY`, resolved by 6.1's producer repair) closes. G-PRED2 green — 24
      wired + 11 recorded (10 non-wireable + the vacuous #30) + `preparedEC` `unclosable` in the
      graph. Run `/rv-verify` on the gate layer; harness evidence for every 5.x chain committed

## 6. F4 — Pointwise defects and the nine remove() (8 deleted + 1 migrated)

<!-- Per task: the repair + trace pair + harness delta + divergence_record.csv hunks. -->

- [ ] 6.1 The `KeyPairSpec.mop:38` half of this task is **done, by task 4.13**: the private key
      now writes `GENERATED_PRIVATE_KEY` as `generatedPrivkey[retPriv] after pr` names it, and
      the set's one read-only property is closed — `gh105_gate_baseline.py` reports
      `[G-PRED2] repaired jca_android/CipherSpec.mop i2/GENERATED_PRIVATE_KEY`. It was repaired
      with the store move rather than deferred here because task **5.7 runs before this one** and
      wires Signature's `generatedPrivkey[priv]`, which would otherwise be measured against a
      producer known to be wrong: a private key marked as public answers NOT_OBSERVED to
      `initSign(priv)` about a conforming program, and SATISFIED to `generatedPubkey`. What
      remains here is `SecretKeySpec.mop:26`
      `preparedKeyMaterial ≡ RANDOMIZED` conflation — producer AND consumer halves in the same
      commit: the reads at `SecretKeySpecSpec.mop:25,42` (`validate(RANDOMIZED, keyMaterial)`)
      move to `PREPARED_KEY_MATERIAL` together with the write, or the repaired producer leaves
      the consumer reading a never-written predicate. Lands with 5.10
- [ ] 6.2 `TrustManagerFactorySpec.mop:74-78` wrong property + `KeyManager[]` return pointcut +
      `TrustManager[][]` parameter; the `remove(GENERATED_TRUST_MANAGERS)` of a never-written
      property goes with it. Pairs with 5.9
- [ ] 6.3 `SignatureSpec`: `verified` marked on the `boolean` instead of the `byte[]`; `sign()`
      pointcuts declaring `public byte`
- [ ] 6.4 **Verify** the 8 `@fail` removals of INV-INS-142 are gone; this task performs none of
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
      Verify the count is zero and that each deletion carries its `divergence_record.csv` hunk
- [ ] 6.5 Record the `SecretKey generatedKey[this,_] after d` NEGATES as `unclosable` — the set
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
      7.1 still owns: `SecretKeySpec` is one of the thirteen unmapped specifications
- [ ] 6.6 `CipherSpec` `f1`/`f2` (pointcuts at `:135` and `:141`; the `event` declarations sit at
      `:134`/`:140`): both match the argument-less call — one call, two transitions; make the
      wider pointcut disjoint (two-events-same-call scenario)
- [ ] 6.7 Trace pairs, harness deltas and `divergence_record.csv` hunks for all of Group 6

## 7. F5 — Records, retirement, hardening

- [ ] 7.1 Complete `order_alphabet_map.csv` for every spec Groups 1-6 touched; G-ORDER green or
      declaredly skipped across `jca_android`. **Repair the gate's `ORDER` parser first**: it
      reads `,` as binding tighter than `|`, and `CrySL.xtext:103-120` binds them the other way
      round (`Sequence` is the outermost production, so it is the weakest operator). `Cipher` is
      the one api30 rule that tells the two parses apart, so the `CipherSpec` row is an artifact
      of the gate: it reports `f2` accepted by the ORDER, where the faithful parse rejects a bare
      `doFinal` and accepts `g1 i2 f2`, which the gate rejects. Measured delta: one witness,
      inverted; counts unchanged at 6 passed / 4 findings / 13 skipped; no baseline `--write`
      needed, since `gate_baseline.json` keys G-ORDER by `(set, file, "order")` and stores no
      witness. The five-step checklist, the reproduction, and the real `CipherSpec` divergence
      the repair uncovers (the `ere` accepts an unfinalised Cipher) are in
      `data/gh105/evidence/f1-order-gate-precedence.md`.
      **Task 4.14 feeds this task a divergence the gate cannot currently see.**
      `KeyManagerFactorySpec` has no rows in `order_alphabet_map.csv`, so G-ORDER skips it
      declaredly — and `g1 init gkm1` is accepted by the api30 ORDER (`Gets, Init, gkm?`) and
      rejected by the `fsm`, whose `gkm1` row {3, 3, 0, 3} leaves the accepting state (2) for
      `start` (0) against a match category of `nextstate == 2`. It is the exact mirror of the
      `g1 i1 gtm` divergence the gate already reports against `TrustManagerFactorySpec`, and
      `conformance_record.csv` was read before calling it new: its three `KeyManagerFactorySpec`
      rows are about the algorithm allow-list, the deferred `neverTypeOf` constant and the 8.16
      guard-on-field repair. Mapping the file here will raise it. Two writes move to their
      acceptance point when the two automata are repaired — `KeyManagerFactorySpec.gkm1` and
      `TrustManagerFactorySpec.gtm1`, both kept in the event body by task 4.14 with the reason
      recorded in `predicate_graph.csv` precisely because these rows make the acceptance point
      unreachable
- [ ] 7.2 `codes.csv` completeness pass: every accuser introduced in Groups 3-6 has its code;
      message gate green
- [ ] 7.3 Retire `rvsec-mop-defsuses`: move to `backup/`, remove from `rvsec/rvsec/pom.xml:27`
      `<modules>` (the only pom that lists it), grep for dangling references (documentation
      survivors updated or exempted declaredly — module CLAUDE.md rows,
      `scripts/check_no_legacy_mop.py` skip list, the retired copy under `backup/` that the move
      itself creates inside the grepped tree, and the active gh48-project-finalization
      artifacts, whose `defsuses` rows are that change's to update), reactor builds (P3)
- [ ] 7.4 Regenerate the full `jca_android` monitor through the real pipeline; record heap;
      inspect the artifact, never the exit code (INV-INS-145); update
      `data/jca_android/README.md` to the new machinery census **and** the new file count — the
      set is no longer 23 specifications and the universe is no longer 214, because Group 5
      added junction specifications; verify no gate, test name or record holds the stale literal
- [ ] 7.5 Run `/rv-qa-lint-fix scripts` and `/rv-doc-code` on any script not covered by 2.12 —
      enumerate them from `git status` at this point, so "any script" is decidable
- [ ] 7.6 Delete the expected-baseline mechanism of 2.10: every gate now asserts zero findings
      on its own, `data/jca_android/gate_baseline.json` is removed, and the pytest wrappers stop
      reading it. A baseline that outlives its groups is an allow-list nobody voted for

## 8. Verification

- [ ] 8.1 Full gate suite over the enumerated universe: G-ORDER, G-PRED2, G-ACC, G-PARAM,
      junction rules, import discipline, genericity (skip-and-count report committed); gh104
      gates still green, `test_jca_android_hunks_all_recorded` included
- [ ] 8.2 Freeze proof: `jca/` and `ExecutionContext.java` byte-identical (zero-diff — no
      annotation, no whitespace), `FROZEN_PATHS` covers the file, `test_property_append_only`
      green. Run it with `RVSEC_HOME` set — the gh101 freeze gate `pytest.skip`s without it
      (`test_gh101_specset_gates.py:59-60`), and a skipped freeze gate is not a freeze proof
- [ ] 8.3 C5 ground truth, as an **oracle comparison, not a replay**: the corpus at
      `../../ase-journal/dataset/results/errors_unit_tests.csv` (sibling repository, read-only
      per gh89) is a 299-row aggregate of already-reported errors — columns
      `apk,rep,timeout,tool,time,spec,class,method,message,unique_msg` — not traces the harness
      can consume. Use it to answer one question per row family: does the corrected set still
      accuse the misuse this row records, and does it stop accusing what the repairs declared
      spurious? The replayable bench is `rvsec/rvsec-agent/src/test`, which weaves the **frozen
      `jca`** (`rvsec-agent/pom.xml:106`) — so it validates the seed, not the successor, and is
      cited here to say why it is not the instrument. Commit the verdict table
- [ ] 8.4 Full harness differential over `data/gh104/traces/`: `--a
      backup/gh105-preimage/jca_android/` (the specification-set directory 2.11 archived) versus
      the edited set; `gh104_diff_harness.py` regenerates both monitor trees itself. Every
      `introduced`/`removed`/`moved` classification traces to a task
- [ ] 8.5 Device smoke test (one mini run, before the joint experiment; via
      `rv-experiment`/`rv-platform` only — the platform manages the entire emulator lifecycle,
      never a manually managed emulator): a sample APK instrumented with the wired set — (a) R4
      probe: record whether `OpenSSLRSAPublicKey`/`BCRSAPublicKey` `equals` is value- or
      identity-based (design Open Question 1); (b) the woven `Object`-idiom junction fires on a
      real device trace through the dexlib2 host path (Open Question 2); (c) the junction ×
      `CipherSpec` co-fire on the same `Cipher.init` joinpoint is observed and its report counts
      committed — the junction's own spec name opens a new unique-misuse bucket at the same
      `(class, method)` (design Risks; the Phase-0 pilot's third untested item). The blocking
      condition was already answered at 4.3; this run measures what only a wired chain can show
- [ ] 8.6 Run `/rv-qa-lint-fix` over everything the change touched since 7.5 (the rv-sdd
      schema's final sequence: lint-fix → verify → code-reviewer), then `/rv-verify` (tests +
      lint + types) and `uv run pytest tests/parity --import-mode=importlib -o "addopts="`
- [ ] 8.7 Run `/rv-code-reviewer` on the change ("Review gh105-predicate-wiring implementation")
- [ ] 8.8 [BLOCKED — external: gh104 archive, which follows the joint experiment] Reconcile
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
- [ ] 8.9 [final commit BLOCKED on 8.8] `openspec status` complete; commits use `refs #105`;
      final commit `closes #105` after the researcher signs off completion (D-9 single-change
      scope ratified 2026-08-20; Group 10 of gh104 and campaign validation stay with the joint
      experiment in `experimento-gh104/`, which validates both changes at once)
