# Tasks: gh105-predicate-wiring

<!--
Subagent dispatch (docs/WORKFLOW.md §5):
- Group 1 (substrate) and Group 2 (gate layer) are the critical path: everything else closes
  against them. 1 before 3-6; 2.1-2.4 before 3; 2.5-2.8 may run parallel to 3 (2.5 lands with
  4.1). gh104's Group 10 runs in the joint experiment (`experimento-gh104/`) after BOTH changes
  land — its 10.1 checkpoint therefore reads the pytest 2.5 rewrites (INV-INS-141), which is
  the intended final state, not a conflict.
- Group 3 (orphans) is independent of the mechanism decision and of Group 4 — parallelizable
  per-spec across subagents once 2.1-2.4 exist.
- Group 4 (guard moves + store migration) is per-file parallelizable, but 4.1 (first migrated
  file + gate collateral, INV-INS-141) MUST land alone first.
- Group 5 (wiring) is sequential by chain (topological order); within a chain, tasks are small.
- Group 6 (pointwise + removals) is per-spec parallelizable after Group 4.
- Group 7 (records/retirement) after 5-6. Group 8 (verification) last, single session.
- Java-side tasks run in the sibling reactor (JDK 21 prefix, /home/pedro/... paths — the
  /pedro/... alias does not resolve in the JVM). Every generation task checks the artifact,
  never the exit code, and records the heap (INV-INS-145).
- Checkpoint rule: tick each box immediately on completion, before starting the next task.
-->

## 1. F0 — Substrate (rvsec-core)

- [ ] 1.1 Create `PredicateVerdict` enum (`SATISFIED`/`VIOLATED`/`NOT_OBSERVED`) in
      `rvsec/rvsec-core/src/main/java/br/unb/cic/mop/` (design.md API Design)
- [ ] 1.2 Create `PredicateStore`: holder singleton; identity-keyed weak object binding with
      `ReferenceQueue` purge; tracked-type (`String`/`int`/`Integer`) case-insensitive value
      positions; arity N; bound-first signatures `ensure/validate(Property p, Object bound,
      Object... values)` (a plain varargs head spreads reference arrays — measured);
      `negate` (object-scoped); `validateAbsent` (negated clauses, INV-INS-146); `reset`
      (test-only). Not offered: `hasEnsuredPredicate`, property-wide remove (INV-INS-131)
- [ ] 1.3 JUnit `PredicateStoreTest` in rvsec-core: identity vs `equals` (two equal
      `SecretKeySpec`s), tracked-type matching (case, mismatch), arity ≥ 2, verdict semantics
      (entry+match / entry+mismatch / no entry), inverted table for `validateAbsent`,
      array-argument lands in `bound` whole (never spread), `negate` scoping, weak purge,
      concurrent access (~17 tests)
- [ ] 1.4 Freeze hardening: `ExecutionContext.java` untouched — assert byte-identity
      (`git diff` empty for the file) and add it to the freeze gate's `FROZEN_PATHS`; add the
      `Property` constants a wired clause needs (at least `PREPARED_KEY_MATERIAL`) append-only,
      with `test_property_append_only` asserting the pre-change constants and their relative
      order survive (INV-INS-132; zero `ordinal()`/`values()` uses measured)
- [ ] 1.5 Build the reactor (`mvn clean install -DskipMopAgent -DskipTests`, JDK 21 prefix);
      run rvsec-core tests; confirm gh101/gh104 freeze gates still green (INV-INS-132)

## 2. Gate layer foundations (rv-android)

- [ ] 2.1 Write `scripts/gh105_predicate_graph.py`: structural `.mop` analyzer (comment/string
      neutralization, brace/paren matching, `fsm`/`ere` alphabet incl. reverse direction and
      multiset, `alias` resolution, `(Property` discriminator) emitting
      `data/jca_android/predicate_graph.csv` rows per INV-INS-137 and placement classes per
      INV-INS-133/134; skip-and-count contract over the 214 files (INV-INS-140)
- [ ] 2.2 Write G-ACC + placement + G-PRED2 closure checks over the graph; negative fixtures:
      `jca/GCMParameterSpecSpec.mop` (dup `c1`, undeclared `c2` — allowlisted, never repaired),
      event-only `generic_new` files (skipped), `generic` FSM246 orphan (informative)
- [ ] 2.3 Write `scripts/gh105_param_gate.py` (G-PARAM): `.mop` header vs generated `.rvm`
      header, artifact-only (INV-INS-139); fixtures for `byte[]`/`int[]`/`char[]` collapse and
      the `Object`-idiom pass
- [ ] 2.4 Write the import-discipline gate (`grep -rlw 'ExecutionContext'` over
      `jca_android/*.mop` empty — INV-INS-130) and wire 2.1-2.4 into
      `tests/parity/test_gh105_predicate_gates.py` (CI contract:
      `--import-mode=importlib -o "addopts="`)
- [ ] 2.5 Rescope G-PRED to the `jca` lock (INV-INS-141) — lands in the same commit as task
      4.1. Collateral, all in the same commit: `gh104_gates.py`
      (`predicate_divergences` wiring, `accept_requires`, `PREDICATE_CALL` recognize the new
      store), the INV-INS-128 pytest rewrite, `gh104_message_gate.py::_clause_family` (classifies
      via `condition(...)` text, which F2 empties), `experimento-gh104/scripts/preflight.py::
      check_no_predicates` (second gate named G-PRED, opposite polarity — retire/rename), and the
      `err2`/`c3` rows of `data/jca_android/gate_allowlist.csv` (re-justify or drop)
- [ ] 2.6 Create `data/jca_android/order_alphabet_map.csv` (schema + rows for the specs F1/F3
      touch first) and write `scripts/gh105_order_gate.py` (G-ORDER): DFA equivalence under the
      mapping, `skipped` without rule or mapping (INV-INS-138); SecureRandom `Ins, Seeds?, Ends*`
      as the first anchored case
- [ ] 2.7 Run the full gate suite over the unmodified 214 files; commit the baseline report
      (passed/failed/skipped counts — the genericity evidence for INV-INS-140, exercised by
      `test_inv_ins_140_genericity_214`); generate and archive the pre-change `jca_android`
      monitor set — the "before" side task 8.4's differential needs
- [ ] 2.8 Run `/rv-doc-code scripts/gh105_predicate_graph.py` and
      `/rv-doc-code scripts/gh105_order_gate.py`

## 3. F1 — The 17 orphan accusers (9 specs): fuse the twins, absorb the rest

<!-- Per-spec tasks from the measured census (design.md "17-Orphan Census"); each = automaton
     edit + satisfy/violate trace pair + harness before/after (INV-INS-144) +
     `divergence_record.csv` row + G-ORDER mapping row when the rule exists. A twin orphan
     (identical pointcut to a conforming sibling) is FUSED into the sibling's body, never added
     as a second event (INV-INS-135). Rescue material: the archived set's structural hunks,
     reimplemented under fresh evidence, never copied (Non-Goal). Kleene residue declared where
     it applies (the FEN-PBK-RESIDUO record). Magnitudes are jca-campaign ceilings. -->

- [ ] 3.1 `SecureRandomSpec`: fuse `c3`→`c2` and `setSeed3`→`setSeed2` (twins; note `c3`
      accuses nothing today — its body only rebinds); absorb `g4`; add `next2` to the `end`
      state (the `Ends*` false positive, 12,400 events); G-ORDER green under the 2.6 mapping
- [ ] 3.2 `TrustManagerFactorySpec`: absorb `g3` (co-emission signature 9,015/9,014);
      `SSLContextSpec`: absorb `unsafe_protocol` (6,835 — its only orphan; `newSslSocketFactory`
      is an okhttp3 method, not an event of the spec)
- [ ] 3.3 `IvParameterSpec`: fuse `c3`→`c1` and `c4`→`c2` (twins; `c4` is not an exact
      complement — it ignores `c2`'s offset/length constraints; decompose the accusation per
      clause); `PBEParameterSpecSpec`: fuse `c3`→`c1` (2-arg twin; the 3-arg `c2` read stays
      accuser-less until 4.3)
- [ ] 3.4 `SecretKeySpecSpec`: fuse `c3`→`c1` and `c4`→`c2` (`c4` is the length complement);
      `KeyPairGeneratorSpec`: absorb `initError`; `SignatureSpec`: absorb `g3`
- [ ] 3.5 `PBEKeySpecSpec`: absorb `f1`, `f2`; fuse `err2`/`err3` into the `c1` body alongside
      `err1`'s iteration-count check (the three overlap today — one bad call fires up to three
      accusers; the fusion decomposes per clause, one report each); declare the Kleene-prefix
      residue
- [ ] 3.6 G-ACC green over `jca_android` (zero orphans, both directions); harness evidence
      committed for all 17

## 4. F2 — Guard moves + store migration (27 reads)

- [ ] 4.1 First migrated file (`CipherSpec`, 3 of the 27 reads — `i2`'s key-origin trichotomy
      stays one composite site emitting at most one report per violated clause, INV-INS-133):
      rewrite its reads onto `PredicateStore` in the event body with accuser + code; land
      together with 2.5 (gate collateral) in one commit; `divergence_record.csv` row (site count
      per file — D-5)
- [ ] 4.2 Add the *not observed* code family to `codes.csv` and emit it from the first
      three-valued read; extend `gh104_message_gate.py` (INV-INS-143) — same task as 4.1
- [ ] 4.3 Migrate the remaining 9 reading specs' 24 reads (27 − 3) to body placement on the new
      store. Of the 9 accuser-less read events, the clause-translating ones gain their accuser
      (`GCMParameterSpecSpec.c1/c2` — `randomized[src]`; `PBEParameterSpecSpec.c2` —
      `randomized[salt]`; `CipherSpec.i2` handled in 4.1); the propagation reads MUST NOT gain
      one (`MacSpec.i1/i2` read `generatedKey`, which the Mac rule does not require — re-derived
      in 5.2 from `preparedHMAC`; `RandomStringPassword.vo/gb` — no rule; `SecretKeySpec.e1` —
      no `REQUIRES` section) and are recorded as `propagation` in the graph
- [ ] 4.4 Placement gate green: zero `condition` reads in `jca_android` (INV-INS-133);
      import-discipline gate green (INV-INS-130); trace pair per moved read committed — F2
      window rule: pairs assert `NOT_OBSERVED` for reads whose producer lands in F3 (the satisfy
      side is impossible inside the window); `SATISFIED`/`VIOLATED` pairs land per chain in
      Group 5
- [ ] 4.5 Disposition of the 25 accepting-state calls (19 set / 6 unset, INV-INS-147): removed
      with each file's store migration (the new store offers no bookkeeping); counted in the
      file's `divergence_record.csv` row; harness delta measured per file
- [ ] 4.6 Run `/rv-test-run tests/parity` (gh104 + gh105 gates together)

## 5. F3 — Wire the 25 wireable REQUIRES clauses, record the rest (topological)

<!-- Sequential by chain; every task resolves against design.md's 36-clause ledger, never
     against family names. Every edge task = producer write at the acceptance point
     (INV-INS-134) + consumer read (or junction spec per INV-INS-136) + accuser + trace pair +
     predicate_graph.csv row with the clause pointer. Mechanism per D-2, recorded per chain.
     CipherSpec is at 17/17 events — ZERO headroom (INV-INS-145): no task may add a CipherSpec
     event; every new Cipher binding routes through a junction spec or the store. Cipher
     alphabet: generate in the real pipeline, record heap. -->

- [ ] 5.1 Pilot chain in production: IV junction spec (`SecureRandom → byte[](Object idiom) →
      IvParameterSpec → Cipher`), ledger #9/#12; rules INV-INS-136(a-d); G-PARAM green; the
      pilot's four fixture traces become committed pairs, including the rule-violating negative
      fixtures for (a), (b), (d)
- [ ] 5.2 `Mac` chain: `preparedHMAC[params]` (ledger #21 — the rule's real clause; Mac does
      not require `generatedKey`, so the `i1`/`i2` propagation reads are re-derived here); the
      negated `!encrypted` pair (#22/#23) wired via `validateAbsent` (researcher decision
      2026-08-20; producer: the Cipher `ENCRYPTED` writes, repositioned to acceptance by F2/F4)
- [ ] 5.3 `randomized` hub (ledger #6, #11, #24, #25, #13, #33): consumers `GCMParameterSpec`,
      `PBEKeySpec`/`PBEParameterSpec` salts, `KeyGenerator` (not KeyPairGenerator),
      `Cipher.init` ranGen (store-side — zero CipherSpec events), `SecureRandom` self-chain;
      junction where co-observable, store where not; `SSLContext randomized[sr]` (#30) recorded
      `vacuous` — the rule binds `sr` in no event; drop the autoboxed-argument writes
      (`SecureRandomSpec.next1/next3` mark the int argument today)
- [ ] 5.4 `generated*key` family (ledger #5, #15, #16, #34, #35): producers at acceptance
      (`KeyGenerator`, `KeyPairGenerator`, `SecretKeyFactory`, `KeyStore`), consumers
      `Cipher.init` `generatedKey[key, part(0,"/",transformation)]` (arity-2, splitter by
      caller, store read replacing the i2 guard — zero new events), `KeyPair`
      `generatedPrivkey`/`generatedPubkey`, `Signature` `generatedPrivkey[priv]`/
      `generatedPubkey[pub]` (Signature's own clauses — not `generatedKey`); the Cipher negated
      `!macced` (#8) wired via `validateAbsent` (researcher decision 2026-08-20), with the
      `MACED` producer write added at the Mac rule's acceptance point (zero sites today)
- [ ] 5.5 `prepared*` guarded clauses (ledger #10, #17): `preparedGCM` (`{GCM} =>`, guard in
      body) and `preparedDH` (`KeyPairGenerator {DH} =>`); `preparedEC` (#20) recorded
      `unclosable`; `preparedDSA`/`preparedRSA` (#18/#19) recorded `unmonitored-producer`;
      `preparedPBE` and `generatedSSLContext` are ENSURES-only dead ends — deliberate-omission
      records, no fabricated read
- [ ] 5.6 TLS chain (ledger #14, #36, #28, #29): `generatedKeyStore` → `KeyManagerFactory`/
      `TrustManagerFactory`; `generatedKeyManager[kms]`/`generatedTrustManager[tms]` →
      `SSLContext.init` (bound-first API — `kms`/`tms` are reference arrays that a varargs head
      would spread); PKIX* `generatedKeyStore` (#26/#27) and `CertPathTrustManagerParameters`
      (#4) recorded `unmonitored-consumer`
- [ ] 5.7 Leaf clauses and the record pass: `preparedKeyMaterial[keyMaterial]` (#32 — consumer
      `SecretKeySpecSpec`, producer `SecretKeySpec.mop` `getEncoded`; un-conflated with 6.1 in
      the same commit); `speccedKey` (#31) and the remaining non-wireable clauses (#1, #2, #3,
      #4, #7, #18, #19, #26, #27) recorded with their category; G-PRED2 closure green — 25
      wired + 10 recorded + `preparedEC` `unclosable` in the graph
- [ ] 5.8 Run `/rv-verify` on the gate layer; harness evidence for every 5.x chain committed

## 6. F4 — Pointwise defects and the nine remove()

- [ ] 6.1 `KeyPairSpec.mop:38` private key written under `GENERATED_PUBLIC_KEY`;
      `SecretKeySpec.mop:26` `preparedKeyMaterial ≡ RANDOMIZED` conflation — producer AND
      consumer halves in the same commit: the reads at `SecretKeySpecSpec.mop:25,42`
      (`validate(RANDOMIZED, keyMaterial)`) move to `PREPARED_KEY_MATERIAL` together with the
      write, or the repaired producer leaves the consumer reading a never-written predicate
- [ ] 6.2 `TrustManagerFactorySpec.mop:74-78` wrong property + `KeyManager[]` return pointcut +
      `TrustManager[][]` parameter; the `remove(GENERATED_TRUST_MANAGERS)` of a never-written
      property goes with it
- [ ] 6.3 `SignatureSpec`: `verified` marked on the `boolean` instead of the `byte[]`; `sign()`
      pointcuts declaring `public byte`
- [ ] 6.4 Delete the 8 `@fail` removals (INV-INS-142), one harness delta each; translate
      `PBEKeySpecSpec.mop:74` (`clearPassword` NEGATES) to `PredicateStore.negate`,
      object-scoped; record the `SecretKey after d` NEGATES as `unclosable` (no `destroy` event)
- [ ] 6.5 `CipherSpec` `f1`/`f2` (`doFinal()` at :134, `doFinal(..)` at :140): both match the
      argument-less call — one call, two transitions; make the wider pointcut disjoint
      (two-events-same-call scenario)
- [ ] 6.6 Trace pairs + `divergence_record.csv` rows for all of Group 6

## 7. F5 — Records, retirement, hardening

- [ ] 7.1 Complete `order_alphabet_map.csv` for all specs F0–F5 touched; G-ORDER green or
      declaredly skipped across `jca_android`
- [ ] 7.2 `codes.csv` completeness pass: every accuser introduced in 3-6 has its code; message
      gate green
- [ ] 7.3 Retire `rvsec-mop-defsuses`: move to `backup/`, remove from `rvsec/rvsec/pom.xml:27`
      `<modules>` (the only pom that lists it), grep for dangling references (documentation
      survivors updated or exempted declaredly — module CLAUDE.md rows, `check_no_legacy_mop.py`
      skip list), reactor builds (P3)
- [ ] 7.4 Regenerate the full `jca_android` monitor through the real pipeline; record heap;
      inspect the artifact (INV-INS-145); `data/jca_android/README.md` updated to the new
      machinery census
- [ ] 7.5 Run `/rv-qa-lint-fix scripts` and `/rv-doc-code` on any script not covered in 2.8

## 8. Verification

- [ ] 8.1 Full gate suite over the 214 files: G-ORDER, G-PRED2, G-ACC, G-PARAM, import
      discipline, placement — green with declared skips; gh104 gates (G-2 family, G-CONF,
      G-ERE, message gate) green; G-PRED green over `jca` (the lock)
- [ ] 8.2 Freeze proof: `jca/` and `ExecutionContext.java` byte-identical (zero-diff — no
      annotation hunk); `Property` append-only test green; archived set untouched
- [ ] 8.3 C5 ground truth: replay the misuse corpus (`errors_unit_tests.csv` traces) — corrected
      specs still accuse planted misuse, stop accusing conforming use; verdict table committed
- [ ] 8.4 Full harness differential over `data/gh104/traces/` (before = pre-change monitors):
      classify `unchanged`/`moved`/`removed`/`introduced`; every `moved` justified
- [ ] 8.5 Device smoke test (one mini run, before the joint experiment; via
      `rv-experiment`/`rv-platform` only — the platform manages the entire emulator lifecycle,
      never a manually managed emulator): a sample APK instrumented with the `Object`-idiom
      junction spec — (a) R4 probe: record whether `OpenSSLRSAPublicKey`/`BCRSAPublicKey`
      `equals` is value- or identity-based (design Open Question 1); (b) the woven junction
      fires on a real device trace through the dexlib2 host path (Open Question 2); verdicts
      committed as change evidence
- [ ] 8.6 Run `/rv-verify` (tests + lint + types) and `uv run pytest tests/parity
      --import-mode=importlib -o "addopts="`
- [ ] 8.7 Run `/rv-code-reviewer` on the change ("Review gh105-predicate-wiring implementation")
- [ ] 8.8 Reconcile with gh104 before archive: once gh104 has archived, add the formal
      `MODIFIED` entry for its requirement "The Successor Set Carries the Predicates of Its
      Seed Unchanged" to this delta (the supersession scenario already carries the content);
      verify INV-INS-123's restated form landed
- [ ] 8.9 `openspec status` complete; commits use `refs #105`; final commit `closes #105` after
      the researcher signs off completion (D-9 single-change scope ratified 2026-08-20; Group 10
      of gh104 and campaign validation stay with the joint experiment in `experimento-gh104/`,
      which validates both changes at once)
