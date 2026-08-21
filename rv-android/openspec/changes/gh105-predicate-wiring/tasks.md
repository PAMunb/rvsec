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
  automaton's declared alphabet with benign self-loops at every state where its call is legal,
  and its `order_alphabet_map.csv` row records it as ORDER-unmapped (erased before the G-ORDER
  comparison — INV-INS-138); "fuse" per INV-INS-135. The `gate_allowlist.csv` rows are owned by
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
- [ ] 3.6 `PBEParameterSpecSpec`: fuse `c3`→`c1` (2-arg twin; the 3-arg `c2` read stays
      accuser-less until its Group-4 file pass); `KeyPairGeneratorSpec`: absorb `initError` (it
      accuses `InvalidKeySize` on its own); `SSLContextSpec`: fuse `unsafe_protocol`→`g1` and
      `SignatureSpec`: fuse `g3`→`g1` — both negated twins whose bodies only rebind a field,
      same treatment and same recorded residue as 3.2
- [ ] 3.7 G-ACC green over `jca_android` (zero orphans, both directions), its baseline rows
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

- [ ] 4.1 `CipherSpec` (3 reads / 12 writes / 1 accepting-state call), the first migrated file:
      `i2`'s key-origin trichotomy stays ONE composite site emitting at most one report per
      violated clause (INV-INS-133); the `ENCRYPTED` writes relocate here (5.3's `validateAbsent`
      pair consumes them). Lands with 4.2 in one commit
- [ ] 4.2 Add the *not observed* code family to `jca_android/codes.csv` and emit it from the
      first three-valued read; extend `gh104_message_gate.py` (INV-INS-143) — same commit as 4.1
- [ ] 4.3 **REACH PROBE — the change's blocking condition (design D-12), gates Group 5.** One
      `rv-experiment`/`rv-platform` run over a sample APK instrumented with the 4.1 monitors (the
      platform owns the emulator lifecycle; never a manual emulator command). One question: does
      any predicate-derived report reach `errors.csv` — a `VIOLATED` or a *not observed* code
      through the gh104 envelope? Commit the verdict either way. **If `UnsatisfiedConstraint`
      stays at zero on the production path, STOP: the change is blocked and the weaver becomes a
      prerequisite (proposal Out of scope, design Non-Goals).** Do not start Group 5 on an
      unanswered probe
- [ ] 4.4 `IvParameterSpec` (4 reads / 1 write / 1 call)
- [ ] 4.5 `SecureRandomSpec` (4 reads / 6 writes / 1 call); the `end`-state `next2` omission is
      repaired here (6.3 carries the rest of the pointwise `Signature` work, this one rides its
      own file)
- [ ] 4.6 `PBEKeySpecSpec` (4 reads / 1 write / 1 call); its `remove()` at `:74` is NOT touched
      here — 6.4 translates it to `PredicateStore.negate`
- [ ] 4.7 `PBEParameterSpecSpec` (3 reads / 1 write / 1 call); the 3-arg `c2` read gains its
      accuser here (`randomized[salt]`)
- [ ] 4.8 `GCMParameterSpecSpec` (2 reads / 1 write / 1 call); `c1`/`c2` gain their accusers
      (`randomized[src]`)
- [ ] 4.9 `MacSpec` (2 reads / 2 writes / 1 call); `i1`/`i2` read `generatedKey`, which the Mac
      rule does not require — they are **propagation**, MUST NOT gain an accuser, and are
      recorded as `propagation` in the graph; the rule's real clause is re-derived at 5.2
- [ ] 4.10 `SecretKeySpecSpec` (2 reads / 1 write / 1 call)
- [ ] 4.11 `RandomStringPassword` (2 reads / 2 writes / 0 calls); both reads are **propagation**
      (no rule) — no accuser, recorded as such
- [ ] 4.12 `SecretKeySpec` (1 read / 1 write / 0 calls); `e1` is **propagation** (no `REQUIRES`
      section) — no accuser
- [ ] 4.13 Write-only specs, batch A (11 writes / 6 calls): `SignatureSpec` (4 writes),
      `MessageDigestSpec` (3), `SSLContextSpec` (2), `KeyPairSpec` (2). Seven of these eleven
      sites belong to `ENSURES`-only dead ends and carry a deliberate-omission record for their
      absent reader (INV-INS-137); no read is fabricated for any of them
- [ ] 4.14 Write-only specs, batch B (10 writes / 11 calls): `KeyStoreSpec` (2),
      `KeyManagerFactorySpec` (2), `TrustManagerFactorySpec` (2), `KeyGeneratorSpec` (1),
      `KeyPairGeneratorSpec` (1), `DHGenParameterSpecSpec` (1), `HMACParameterSpecSpec` (1).
      Their `@fail` removals are NOT touched here — 6.4 owns all eight
- [ ] 4.15 Placement gates green, baselines retired: zero `condition` reads in `jca_android`
      (INV-INS-133), `test_inv_ins_134_write_placement` green — every write at acceptance or
      carrying its recorded `reason` in `predicate_graph.csv`, import-discipline green
      (INV-INS-130), zero `set/unsetObjectAsInAcceptingState` in the set (INV-INS-147, all 25
      gone), trace pair committed per moved read
- [ ] 4.16 Run `/rv-test-run tests/parity` (gh104 + gh105 gates together)

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

- [ ] 5.1 Pilot chain in production: `IvChainJunction.mop` (`SecureRandom → byte[](Object idiom)
      → IvParameterSpec → Cipher`), ledger #9/#12; rules INV-INS-136(a-d) green under 2.4;
      G-PARAM green; the pilot's four fixture traces become committed pairs, including the
      rule-violating negative fixtures for (a), (b), (d)
- [ ] 5.2 `Mac` chain, positive: `preparedHMAC[params]` (ledger #21 — the rule's real clause;
      Mac does not require `generatedKey`, so 4.9's propagation reads are re-derived here)
- [ ] 5.3 `Mac` chain, negated: `!encrypted[output1,_]` and `!encrypted[output2,_]` (ledger
      #22/#23 — two sites, one predicate) via `validateAbsent` (INV-INS-146); producer = the
      Cipher `ENCRYPTED` writes 4.1 relocated to acceptance
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
      `generatedPrivkey`/`generatedPubkey`
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
      column is the single source)
- [ ] 5.11 Closure sweep over **all 21 written `Property` values**, not only the named ones:
      every write has its reader or its deliberate-omission record, and the read-only gap
      (`GENERATED_PRIVATE_KEY`, resolved by 6.1's producer repair) closes. G-PRED2 green — 24
      wired + 11 recorded (10 non-wireable + the vacuous #30) + `preparedEC` `unclosable` in the
      graph. Run `/rv-verify` on the gate layer; harness evidence for every 5.x chain committed

## 6. F4 — Pointwise defects and the nine remove() (8 deleted + 1 migrated)

<!-- Per task: the repair + trace pair + harness delta + divergence_record.csv hunks. -->

- [ ] 6.1 `KeyPairSpec.mop:38` writes the private key under `GENERATED_PUBLIC_KEY` (this defect
      is why `GENERATED_PRIVATE_KEY` is read at `CipherSpec.mop:85` and written nowhere — the
      repair closes the set's one read-only property); `SecretKeySpec.mop:26`
      `preparedKeyMaterial ≡ RANDOMIZED` conflation — producer AND consumer halves in the same
      commit: the reads at `SecretKeySpecSpec.mop:25,42` (`validate(RANDOMIZED, keyMaterial)`)
      move to `PREPARED_KEY_MATERIAL` together with the write, or the repaired producer leaves
      the consumer reading a never-written predicate. Lands with 5.10
- [ ] 6.2 `TrustManagerFactorySpec.mop:74-78` wrong property + `KeyManager[]` return pointcut +
      `TrustManager[][]` parameter; the `remove(GENERATED_TRUST_MANAGERS)` of a never-written
      property goes with it. Pairs with 5.9
- [ ] 6.3 `SignatureSpec`: `verified` marked on the `boolean` instead of the `byte[]`; `sign()`
      pointcuts declaring `public byte`
- [ ] 6.4 Delete the 8 `@fail` removals (INV-INS-142), one harness delta each — the sites are
      `TrustManagerFactorySpec.mop:100,101`, `KeyStoreSpec.mop:92,93`,
      `KeyManagerFactorySpec.mop:104`, `KeyPairGeneratorSpec.mop:119`, `MacSpec.mop:99`,
      `KeyGeneratorSpec.mop:89`. They implement "undo the predicate when the automaton fails", a
      semantics no CrySL generation has, and couple typestate to predicate against the rule's
      own orthogonality
- [ ] 6.5 Translate the ninth removal, `PBEKeySpecSpec.mop:74` (`clearPassword`, the one real
      `NEGATES` clause), to `PredicateStore.negate`, object-scoped; record the
      `SecretKey generatedKey[this,_] after d` NEGATES as `unclosable` — the set has no `destroy`
      event, and inventing one would fabricate the evidence this change exists to remove
- [ ] 6.6 `CipherSpec` `f1`/`f2` (pointcuts at `:135` and `:141`; the `event` declarations sit at
      `:134`/`:140`): both match the argument-less call — one call, two transitions; make the
      wider pointcut disjoint (two-events-same-call scenario)
- [ ] 6.7 Trace pairs, harness deltas and `divergence_record.csv` hunks for all of Group 6

## 7. F5 — Records, retirement, hardening

- [ ] 7.1 Complete `order_alphabet_map.csv` for every spec Groups 1-6 touched; G-ORDER green or
      declaredly skipped across `jca_android`
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
