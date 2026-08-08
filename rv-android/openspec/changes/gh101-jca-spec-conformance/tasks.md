<!-- Execution notes:
     - The `jca` set is FROZEN (D-S0). Nothing under $MOP/jca and nothing in
       $CORE/jca/util/CipherTransformationUtil.java changes in this change, however visibly
       defective. Every correction lands in jca_android alone. Base commit for the freeze: 7e7acb69.
     - Groups run in order. Group 1 produces the records everything downstream depends on
       (the conformance verdicts, the two inventories, the freeze baseline); nothing else starts
       before it.
     - Groups 3 to 5 edit the jca_android .mop files one file at a time, applying every defect that
       file carries. Each edit is entered in the divergence record as it lands.
     - Group 3b was added after Group 3 had been implemented, when task 3.4's check showed the
       all-`fail` pattern covers eighteen events and not two (D-S9). It is inserted rather than
       numbered 4, so every group number already cited elsewhere — in issue #101, in design.md and
       in the coordination with issue #100 — keeps pointing at the same work. It runs between
       Groups 3 and 4, in order, like every other group.
     - Two checks run at the end of every group, not once at the end (INV-INS-109): the freeze check
       (the frozen paths are byte-identical to the base commit) and the divergence-record check
       (every non-allow-list hunk of the set diff is named by an entry, and no entry is stale).
     - Group 8 is the only part that depends on issue #100 (its task 5.3, the wrapper-collision
       fix). If that has not landed, task 8.1 is recorded as blocked citing the artefact — the
       criterion is not relaxed and no weaker check is substituted.
     - Source files, all but one in the sibling Java reactor:
       $MOP  = $RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/{jca,jca_android}
       $CORE = $RVSEC_HOME/rvsec/rvsec-core/src/main/java/br/unb/cic/mop
       Reference rules are read-only at MetaCrySL/generated/api30/ — that tree is not modified.
       The exception is Group 6, which touches rv-experiment's config.py.
     - 23 .mop files are touched, all in jca_android. Per-file edit counts come from Group 1's
       inventory, so each task is checked by counting rather than by reading. -->

## 1. Records that everything else depends on

- [x] 1.1 Regenerate the predicate inventory over `jca_android` — every `ExecutionContext` write, read and removal with property, file, line, spec, event and snippet — and commit it together with the script that produced it (D-S2)
- [x] 1.2 Generate the same inventory over the frozen `jca` set and commit it as the freeze baseline; it must be identical to 1.1 modulo the directory prefix, since no edit has landed yet, and it must still be identical to itself at the end of the change
- [x] 1.3 Derive the per-file expected edge counts from the inventory, so each editing task in Groups 3 to 5 carries the number of edges it must close
- [x] 1.4 Produce the conformance verdict for all 23 `jca_android` specifications against the generated API 30 rules: anchored to a named rule, uncontradicted with the rule that was checked, or no anchor with the reason (D-S4, INV-INS-113). Commit the record with the script
- [x] 1.5 List, in the conformance record, the aliases the 2022 translation added outside upstream — dashless and case variants carried over as declared translation artefacts — so each can receive a verdict. Bring the list to the user: it is one of the two open questions design.md leaves to them
- [x] 1.6 Write the freeze check: `git diff` from the base commit over `$MOP/jca` and `$CORE/jca/util/CipherTransformationUtil.java` must be empty (INV-INS-109 a)
- [x] 1.7 Write the divergence-record check: every hunk of the `jca` vs `jca_android` diff that is not allow-list content must be named by an entry in the record, and every entry must name a hunk that exists (INV-INS-109 b)
- [x] 1.8 Create the divergence record with its current content — the allow-list differences of the ten files that already diverge — and run both checks against the current tree to establish the baseline. The freeze check must pass trivially; the record must have no non-allow-list hunks yet

## 2. Transformation tables for the derived set

- [x] 2.1 Add `br.unb.cic.mop.jca.util.AndroidCipherTransformationUtil` with `isValid(String)` — beside the frozen class, in the package that already exists — transcribing the eight algorithms of the generated API 30 `Cipher` rule with their per-algorithm mode tables and per-mode padding tables, held as immutable class-level data (D-S3, INV-INS-112)
- [x] 2.2 Delegate parsing to the frozen utility's `alg`, `mode` and `pad` rather than restating the split, so a transformation string is decomposed in one place for both sets; being in the same package, the calls need no import. Fold case on all three components, which the frozen class does for padding only and which one corpus call site (`AES/CBC/PKCS5PADDING`) depends on
- [x] 2.3 Point `jca_android/CipherSpec.mop` at the new utility by redirecting its **static wildcard import** at `:15` only; the call sites read bare `isValid(...)`, so all five keep their current form byte for byte
- [x] 2.4 Table-driven test over the derived utility: each of the eight algorithms admitted with a conforming transformation, and rejected with a non-conforming mode or padding. Cover the two transformations the corpus contains where the derived verdict differs from the frozen one — `AES/ECB/NoPadding`, which the rule leaves unconstrained and the frozen class rejects, and `AES/CBC/PKCS5PADDING`, which only the case fold admits
- [x] 2.5 Assert the specific contradiction this closes: `ChaCha20`, `DESede`, `BLOWFISH` and `ARC4` are accepted by `KeyGeneratorSpec` and are now also accepted by `CipherSpec` in the derived set
- [x] 2.6 Record in the divergence record that `jca_android/CipherSpec.mop` diverges from `jca` by its import, with the reason
- [x] 2.7 Record as knowingly retained, in the frozen set's debt list, the two hygiene defects inside the freeze: `PKCS5PADDING` duplicated for `CBC` and `PCBC`, and the commented `rsaECBPaddings` block
- [x] 2.8 Run the freeze check and the divergence-record check

## 3. The two hot specifications

- [x] 3.1 `jca_android/TrustManagerFactorySpec.mop`: rename the `g3` binding at `:44`, add `g3` to the `fsm`, and correct the three `gtm1` defects at `:62-65` — the wrong `Property` constant at `:65`, the `TrustManager[][]` binding at `:62`, and the `KeyManager[]` return type at `:63` — plus the **2** predicate-graph edges the map assigns to this file at this stage (`ENSURES generatedTrustManagers`, which is the `:65` defect itself, and `REQUIRES generatedKeyStore`). Its third edge, `REQUIRES generatedManagerFactoryParameters`, needs new vocabulary and belongs to Group 5
- [x] 3.2 `jca_android/SSLContextSpec.mop`: add `returning(SSLContext ctx)` at `:46`, add `unsafe_protocol` to the `fsm`, and close the **3** unread `REQUIRES` the map assigns to this file — `generatedKeyManagers`, `generatedTrustManagers`, `randomized`
- [x] 3.3 Enter every hunk from 3.1 and 3.2 in the divergence record, each with its reason and this task
- [x] 3.4 Generate monitors from the derived set and assert that no bound event has an all-`fail` transition row (INV-INS-110) — this is what proves the `fsm` half of the correction landed. The invariant is set-wide, and writing this check is what surfaced the sixteen further events of Group 3b, so the assertion is run once, at task 3b.10, and closes both groups
- [x] 3.5 Record in the frozen set's debt list that `jca` retains both defects and the spurious `InvalidSequenceOfMethodCalls` they produce
- [x] 3.6 Run the freeze check and the divergence-record check

## 3b. The sixteen remaining all-`fail` events

<!-- The two events of Group 3 were the visible tip of a pattern of eighteen. The check written
     for task 3.4 reports 18 all-`fail` events in the frozen set, of which sixteen remain in the
     derived set, spread over eight further specifications. Fifteen are of one shape: the
     violating branch of an event the CrySL rule states once, reporting in its body and never
     added to the automaton. Most bind the monitored object, so each firing produces the report
     its author intended *and* an InvalidSequenceOfMethodCalls on top of it.
     The repair form is the one Group 3 established and is not stricter than it (D-S9): a Kleene
     prefix on the violating branch where the automaton is an `ere` -- the shape MacSpec,
     KeyGeneratorSpec, KeyStoreSpec and MessageDigestSpec already use -- and new rows where it
     is an `fsm`. No automaton is re-derived. The sixteenth, MessageDigestSpec.reset, is removed
     rather than placed: no generated rule models it and its body is empty.
     INV-INS-110 is not weakened; repairing all sixteen is what makes it true as written.
     One task per file, naming the events it closes, so completion is arithmetic:
     2 + 1 + 1 + 5 + 1 + 2 + 3 + 1 = 16. -->

- [x] 3b.1 `jca_android/IvParameterSpec.mop` (specification `IvParameterSpecSpec`): prefix the `ere` with the violating constructors — `(c3 | c4)* (c1 | c2)` — **2** events
- [x] 3b.2 `jca_android/KeyPairGeneratorSpec.mop`: admit `initError` in both positions where an `initialize` may occur — **1**
- [x] 3b.3 `jca_android/MessageDigestSpec.mop`: **remove** the `reset` event — the generated API 30 rule declares `getInstance`, `update` and `digest` and models no `reset`, the event body is empty, and the all-`fail` row is the whole of its effect — **1**
- [x] 3b.4 `jca_android/PBEKeySpecSpec.mop`: prefix the `ere` with `(f1 | f2 | err1 | err2 | err3)*` — **5**. `f1` and `f2` also carry the binding defect Group 3 met: neither has a `returning` clause, so both land in the empty parameter slice and need both halves, the binding and the automaton. The prefix must be a star and not an option, because one construction can fire `err1` and `err2` together
- [x] 3b.5 `jca_android/PBEParameterSpecSpec.mop`: `c3* (c1 | c2)` — **1**
- [x] 3b.6 `jca_android/SecretKeySpecSpec.mop`: `(c3 | c4)* (c1 | c2)` — **2**
- [x] 3b.7 `jca_android/SecureRandomSpec.mop`: rows in the existing `fsm` — `c3` and `g4` into a state that is not the accepting one, `setSeed3` where `setSeed2` already goes — **3**
- [x] 3b.8 `jca_android/SignatureSpec.mop`: `(g3* g1 | g3* g2) (...)`, the shape `MacSpec` uses — **1**
- [x] 3b.9 Enter each file's hunks in the divergence record as that file is completed, not in a batch at the end, each with its reason and its task
- [x] 3b.10 Generate monitors from the derived set and run `scripts/gh101_monitor_transition_check.py`: it must report no bound event with an all-`fail` transition row (INV-INS-110). Run it against the frozen set in the same session first, where the answer is known to be **18**, so a check that has quietly stopped seeing a monitor kind is caught before it is trusted. This closes task 3.4 and Group 3b together
- [x] 3b.11 Record in the frozen set's debt list that `jca` retains all eighteen events, with the share of the published dataset the ten specifications carrying them account for — 49,817 of 70,760 `InvalidSequenceOfMethodCalls` (70.4%) and 51.3% of all 97,018 reported errors — stated as a **ceiling on what the eighteen can explain**, not as a measurement of what they caused, since `@fail` records no message naming the event that triggered it
- [x] 3b.11b Record in the frozen set's debt list the residue this repair form deliberately leaves: in every specification of the set the state reached by a violating branch does not admit the calls that legitimately follow it, so the accusation moves from the violating call to the next one. It predates this change, it is present in `CipherSpec`, `KeyManagerFactorySpec`, `MacSpec`, `KeyGeneratorSpec`, `KeyStoreSpec` and in the two files Group 3 repaired, and Group 3b neither widens nor narrows it (D-S9)
- [x] 3b.12 Run the freeze check and the divergence-record check

## 4. Predicate graph — `.mop` only

- [x] 4.1 Correct the remaining translation defects in `jca_android`, one file at a time, applying every edge the map assigns to that file — including the wrong constant at `KeyPairSpec.mop:38`. **20 edges** over ten files: `KeyPairSpec` 4, `CipherSpec` 4, `MacSpec` 3, `KeyStoreSpec` 2, `SignatureSpec` 2, and one each in `KeyGeneratorSpec`, `KeyManagerFactorySpec`, `KeyPairGeneratorSpec`, `SecretKeySpec` and `SecretKeySpecSpec` (see `data/gh101/edge_counts_per_file.csv`). Four of the twenty — the `CipherSpec` reads and the `KeyGeneratorSpec` one — fall on arguments no pointcut binds and are closed by tasks 4.6 to 4.9, not here. `SecretKeySpec.mop` has no `destroy` event at all, so `NEGATES generatedKey[this] after d` needs the event added and placed in the automaton in the same edit — `ere : e1* (d | epsilon)`, which is the rule's `ORDER ge*, d?`. The `ere` grammar has no `?` operator: `EREParser.jj` accepts `*`, `+`, `~`, `&`, `|`, `^<digit>`, `epsilon` and `empty` and nothing else, so `(d | epsilon)` is how the same language is written
- [x] 4.2 Enter each file's hunks in the divergence record as that file is completed, not in a batch at the end
- [x] 4.3 Record the two deliberate omissions with their reason, including that the accepting-state mechanism they were replaced by is never read from any `.mop` and is therefore inert at runtime
- [x] 4.4 Record `randomized[lSeed]` as inexpressible — a provenance predicate over a primitive cannot be represented by a map keyed on `equals` — together with the matching unsoundness on the write side, where marking small `int` values as randomised marks every equal literal in the process through the boxed-integer cache
- [x] 4.5 Run the freeze check and the divergence-record check

<!-- 4.6 to 4.10 were added when Group 4's reads met the fused pointcuts. Six of the change's
     edges fall on arguments no pointcut binds, because the translation kept CrySL's aggregate
     (Inits := ...) and dropped the events it aggregates. The fusion is lossless for the ORDER,
     which names only the aggregate, and lossy for every clause that names an individual event.
     D-S11 as revised has the decision: one event per distinct BINDING PROFILE, not one per rule
     signature, because the weaver resolves overloads itself and the alphabet is scarce — the
     generator's ceiling is 17 events (INV-INS-115). Three of the four files land at the rule's
     own counts anyway and are done: KeyGenerator.init 5, KeyManagerFactory.init 2,
     TrustManagerFactory.init 2. CipherSpec is the exception and is budgeted, not transcribed:
     its literal 24-event form cannot be generated at all. -->

- [x] 4.6 `jca_android/CipherSpec.mop`: re-budget the alphabet from 17 events to the **14** verified in D-S11, binding `ranGen`, `params` (`AlgorithmParameterSpec`), `param` (`AlgorithmParameters`) and `plainText` — every argument the rule's clauses quantify over. Three `init` events grouped by arity (`init(int, Object+)`, `init(int, Object+, Object+)`, `init(int, Key, Object+, SecureRandom)`) partition all eight overloads, with `instanceof` in the body selecting the predicate each position carries; three `update` and five `doFinal` events partition those; `getInstance(String, ..)` replaces the arity-1 pair. Do **not** transcribe the rule's eight `init` and seven `doFinal` 1:1 — that is 24 events and the coenable string would exceed Java's maximum `String` length. Before editing, re-run `PointcutBudget` from the `rv-analyze-spec` skill over the API 30 `Cipher` members to confirm coverage and disjointness against the current tree; after editing, generate the file alone and record wall-clock and peak RSS (expected ≈ 6 s, ≈ 1 GB, against 53 s and 3.3 GB today)
- [x] 4.6a Two defects the re-budget closes at no cost in slots, each recorded in the divergence record with its own reason: `byte[] doFinal(..)` today matches `f1`, `f2` **and** `f4`, so a plain `doFinal()` takes two transitions and the rule's `f4` has no event — the replacement candidates are disjoint; and the invalid-transformation event is `getInstance(String)`, arity 1, so `getInstance(transformation, provider)` over an unsafe algorithm fires nothing and is misreported later as `InvalidSequenceOfMethodCalls` instead of `UnsafeAlgorithm`
- [x] 4.7 `jca_android/KeyGeneratorSpec.mop`: init 1 → **5**, the rule's `i1` to `i5`, which is what binds the `ranGen` of `randomized[ranGen]`. `args(Object)` does not match the `int` of `init(int)`, so the `Object`-and-`instanceof` form is not available here
- [x] 4.8 `jca_android/KeyManagerFactorySpec.mop`: init 1 → **2**, the rule's `i1: init(keyStore, password)` and `i2: init(params)`, which is what binds `keyStore` for `generatedKeyStore[keyStore]`. The overloads differ in arity, so the fused form cannot bind either argument
- [x] 4.9 `jca_android/TrustManagerFactorySpec.mop`: replace task 3.1's fused init and its `instanceof` with the rule's two events, so the set is 1:1 with its rules throughout rather than carrying one file's special case. Rewrite that file's divergence-record entries, whose digests change with their content
- [x] 4.10 Regenerate the monitors and re-run `scripts/gh101_monitor_transition_check.py`: every new event must have a row, and the accepted language must be unchanged — the re-budget changes the alphabet only (INV-INS-110, INV-INS-114). Record the whole-set generation time as evidence for INV-INS-115, and confirm no specification in the derived set exceeds the 17-event ceiling
- [x] 4.11 Record as out of scope, with the reason, the clauses the fusion also destroyed and this change does not restore: `noCallTo(IWOIV)` and `callTo(iv)` in the `Cipher` rule, the latter needing a `getIV()` event the specification does not declare at all, and the `neverTypeOf(password, java.lang.String)` constraints of `KeyManagerFactory` and `KeyStore`. They are `CONSTRAINTS`, not predicate-graph edges. Note with them that task 4.6's arity-3 `init` event spans members of both `IWOIV` and `IWIV`, so `noCallTo(IWOIV)` would need the same `instanceof` that selects the predicate — recoverable, but only if whoever picks it up knows it needs recovering
- [x] 4.12 Record what the re-budget does **not** fix, so it is not read as having solved more than it did: `preparedAlg[param, …]` still needs a new `Property` constant and a reader (Group 5) — a capability gap, not a granularity one; and `!macced[_, plainText]` stays unreadable even with `plainText` bound, because `MacSpec` writes `GENERATED_MAC` over the **output** only while the clause quantifies over the data that was MACed. The three ways out were put to the user with the rule text, the store's shape and the measured cost, and the user chose to **transcribe** it: D-S13 records the decision, why the one-place projection is faithful here rather than an approximation, and the two residues it leaves. The work itself is tasks 5.1b and 5.1c — this task records only that the re-budget did not close it and that closing it needs new vocabulary
- [x] 4.13 Record the generator ceiling as a measured constraint (INV-INS-115, D-S12) with the reproducing commands: `n × (2ⁿ − 1)` coenable sets for the `fail` category, exact at 17 and 18; 53 s / 3.3 GB at 17, `StackOverflowError` in `EnableSet.parseSets` at 18, beyond Java's `String` limit at 24; unchanged across `fsm` and `ere` because `EREPlugin` rewrites into `fsm`; `-Xss` not raisable above the launcher's `1g`. State that `rv-monitor` is deliberately not repaired, and that the method and harnesses live in `.claude/skills/rv-analyze-spec/` (commit `3d093592`)

## 4b. The predicate store agrees with the monitor index

<!-- Found while writing Group 4's reads. The two halves of the mechanism identify objects by
     different criteria: JavaMOP keys a monitor by System.identityHashCode confirmed with `==`
     (CachedWeakReference, BucketNode.findByStrongRef), and ExecutionContext keys its three
     stores by `equals` (HashSet). So a per-instance monitor records what it observed in a store
     that cannot tell two equal instances apart -- a shared mark on write, a REQUIRES satisfied
     by an object no monitored sequence produced, and a @fail that takes another monitor's mark.
     Closing Group 4's edges without this would connect them to a store that answers wrongly.
     D-S10 has the decision, the eight frozen-set reads it moves, and why a sibling class in the
     shape of D-S3 was rejected: the defect is identical in both sets, so duplicating the store
     would rename ~85 call sites to isolate a repair neither set benefits from missing.
     Inserted rather than numbered 5, so every group number already cited elsewhere keeps
     pointing at the same work. -->

- [x] 4b.1 Re-key `ExecutionContext`'s three stores by object identity — the per-`Property` sets, `acceptingState`, and the set `hasEnsuredPredicate` scans. Every method signature stays as it is, so no `.mop` in either set moves. `IdentityHashMap` is Java 1.4 and Android API 1; use it directly rather than `Collections.newSetFromMap` (Java 6 / API 9) if the lower floor is wanted
- [x] 4b.2 Java test over the store: two `SecretKeySpec` with the same material and algorithm — marking one leaves the other unmarked, reading the other returns false, and removing one leaves the first's mark standing. The same for `setObjectAsInAcceptingState`
- [x] 4b.3 Enumerate in the change's records the frozen set's reads whose answer changes, with the direction: three in `CipherSpec.i2`, two in `MacSpec`, one in `SecretKeySpec.e1`, the `SecureRandomSpec` seed reads over a boxed `long`, and the two `RandomStringPasswordSpec` reads over a `String` — eight of 27, all towards reporting more. State that no shared code branches on the active specification set, which is what makes the repair admissible (D-S10)
- [x] 4b.4 Record that the freeze check and task 5.2's monitor comparison both still pass after 4b.1, and that this is the limit of what they establish rather than evidence the frozen set is unchanged (INV-INS-109)
- [x] 4b.5 Repair the four one-argument `remove(Property)` calls in `jca_android` — `KeyManagerFactorySpec:91`, `MacSpec:87`, `TrustManagerFactorySpec:117-118` — which delete a predicate's whole set globally, so one monitor's `@fail` erases every other monitor's mark. Identity keying does not touch this. Three of the four need a monitor field to hold the object being unmarked, because it is a local of the event that wrote it. This one is specification content, so it lands in the derived set alone
- [x] 4b.6 Enter the 4b.5 hunks in the divergence record, each with its reason and this task
- [x] 4b.7 Run the freeze check and the divergence-record check

## 5. Predicate graph — new vocabulary

- [x] 5.1 Add the **one** `Property` constant this set can actually close, `GENERATED_CIPHER`, **together with both the write that produces it and the two reads that consume it**, in the same task. D-S14 records why it is one and not nine: of the bucket's nine predicates it is the only one whose producing rule (`Cipher`) and consuming rules (`CipherInputStream`, `CipherOutputStream`) are all modelled by a specification here. The write replaces the inert `setObjectAsInAcceptingState(cipher)` at `CipherSpec.mop:323` — this **reopens task 4.3's deliberate omission for this predicate**, and must, because reading against that substitute would fail on every execution exactly as the six producer-less predicates would. The reads go in `CipherInputStreamSpec` and `CipherOutputStreamSpec`, whose constructor events bind nothing today: `event c1 after(): call(public CipherInputStream.new(InputStream, Cipher))` needs `args(is, ciph)` and the same for the output stream. That is a binding change, not a new event — both alphabets stay at 4 and 5 events, far under the ceiling of 17 (INV-INS-115). Put the read in the event body, not in a `condition(...)`, so an unsatisfied requirement reports rather than vanishing (D-S9)

- [x] 5.1d Record the **eight** predicates of the capability-absent bucket that gain no constant, each with the mechanical reason, for the deliberate-omission list of task 7.2. Six — `preparedAlg`, `preparedRSA`, `preparedDSA`, `generatedManagerFactoryParameters`, `preparedEC`, `preparedOAEP` — have a consumer in this set and **no producer**: name the absent rule for each (`AlgorithmParameters`, `RSAKeyGenParameterSpec`, `DSAGenParameterSpec`, `CertPathTrustManagerParameters`/`KeyStoreBuilderParameters`, `ECGenParameterSpec`, `OAEPParameterSpec`), and record that closing them needs seven further specifications, which is a change of its own. Two — `cipheredInputStream`, `cipheredOutputStream` — have a producer here and **no consumer in any rule of either anchor**, so they would be writes with no reader. Record with them that this leaves **9 of the bucket's 11 edges open**, and that the CrySL anchor decides none of it: `preparedOAEP` is excluded for want of a producer whichever anchor is used, so the anchor bears only on `generatedCipher`. Note also that task 4.3's omission list keeps `generatedMessageDigest` under the identical criterion — its consumers would be `DigestInputStream` and `DigestOutputStream`, and neither is modelled here — so the same test yields opposite verdicts for the two predicates, which is the test working rather than an inconsistency
<!-- 5.1b and 5.1c were added after task 4.12 put the `!macced` question to the user and the
     user chose to transcribe it (D-S13). They are inserted rather than numbered 5.2, so every
     task number already cited elsewhere keeps pointing at the same work. Their constant's edge
     belongs to Group 4's twenty rather than to this group's eleven — it is done here because it
     is new vocabulary and lands under this group's rule. With D-S14 cutting 5.1 to a single
     constant, `macced` and `generatedCipher` are the only two the change adds. -->

- [x] 5.1b Add the `MACED` `Property` constant **together with its reader**, in one task, as 5.1 requires of every other constant. The write side needs `MacSpec`'s data-entry points to bind the input, which they do not today: `event update` is `call(public void Mac.update(..))` with no `args` at all, and `event f1` fuses `doFinal(byte[])` with `doFinal()`. Budget it the way task 4.6 budgeted `CipherSpec` — `update(byte[], ..)` covers the rule's `u2`, `u3` and `u4`, `update(byte)` needs an event of its own because `Object+` rejects a primitive, and `doFinal(byte[])` splits out of `f1` — which takes `MacSpec` from 8 events to about 11, against a ceiling of 17. Verify the candidates with `PointcutBudget` over the API 30 `javax.crypto.Mac` members before editing, as 4.6 did. The read side is `CipherSpec`'s `f2` and `f5`, where task 4.6 already bound `plainText`: the clause is negated, so it reports when the predicate **does** hold
- [x] 5.1c Record the two residues of that transcription, with the reason each is a residue and not an oversight: `Mac.update(java.nio.ByteBuffer)` is not among the rule's events, so data entering through it is never marked and the clause is silent about it; and `update(byte)` marks a boxed primitive, which carries the same unsoundness task 4.4 records for `randomized` — inside the `Byte` cache identity and equality coincide, so one MACed byte marks every equal literal in the process. Record with them that the one-place projection is faithful **for this clause only**, because its first place is anonymous, and that a clause naming both places would still be inexpressible

- [x] 5.2 Confirm the additions are invisible to the frozen set: no `jca` specification references any new constant, and the monitor generated from `jca` is unchanged against the one generated at the base commit. This establishes that the *constants* are invisible and nothing more — task 4b.4 records why an unchanged generated monitor is not evidence of unchanged behaviour
- [x] 5.3 Enter the specification-side hunks in the divergence record
- [x] 5.4 Regenerate the `jca_android` inventory and confirm every new constant has both a writer and a reader — and, the converse the inventory cannot see on its own, that no reader was added for a predicate this set never writes. Confirm too that the eight predicates of task 5.1d appear in the omission list rather than in the enum, so INV-INS-111 and the new unclosable-edge scenario both hold
- [x] 5.5 Run the freeze check and the divergence-record check

## 6. The derived set becomes selectable by name

- [ ] 6.1 Add `"jca_android"` to `valid_spec_sets` in `ExperimentConfig.validate()` and to the directory mapping in `get_monitored_operations_config()`, resolving to `{mop_base_dir}/jca_android/` (D-S8)
- [ ] 6.2 Test that `specification_set = "jca_android"` resolves to the derived directory and does not require `custom_specs_dir`
- [ ] 6.3 Check whether any documentation enumerates the accepted values — `CLAUDE.md`, `docs/PRD.md`, `.claude/project-info.md` — and update what does

## 7. Guards and records

- [ ] 7.1 Write the write/read guard: it reads the committed inventory and the specifications, recomputes the pairing, and fails on any constant written and neither read nor listed in the deliberate-omission list (D-S5, INV-INS-111)
- [ ] 7.2 Commit the deliberate-omission list as versioned data beside the inventory
- [ ] 7.3 Run the guard against the derived set; it must pass, and it must fail if a constant is deliberately mistyped in a scratch copy
- [ ] 7.4 Regenerate both inventories after all edits: the `jca_android` one diffed against the Group 1 baseline, where every difference must correspond to a task in this change; the `jca` one identical to its baseline, byte for byte
- [ ] 7.5 Record in the replication package that the published numbers reproduce exactly because the `jca` set was frozen, and that the debt this buys is a set that stays reproducible without being correct (D-S0)
- [ ] 7.6 Record that comparisons of violation counts across the two sets now confound two causes — the platform allow-list and the layer-2 repairs present in the derived set only — and that no post-hoc measurement separates them
- [ ] 7.7 Record that the derived Android profile models availability rather than recommendation — `MessageDigest` admits `MD5` and `SHA-1` — so a fall in the violation count across the sets is not evidence of better analysed code

## 8. Empirical verification — depends on issue #100

- [ ] 8.1 Once issue #100 task 5.3 (wrapper registry key) has landed, verify empirically that the corrected `TrustManagerFactorySpec` and `SSLContextSpec` report as intended under the derived set. If it has not landed, record this task as blocked citing the artefact — do not substitute a weaker check (D-S6)
- [ ] 8.2 Confirm the corrected allow-lists become observable, in particular that the `SSLContextSpec` label stops depending on a variable that is never written

## 9. Verification

- [ ] 9.1 Build the sibling reactor from its root and confirm both specification sets generate monitors without error — coordinating with the gh100 session first, since the reactor and `~/.m2` are shared
- [ ] 9.2 Run the full conformance record check: 23 of 23 verdicts present, no blanks (INV-INS-113)
- [ ] 9.3 Run the freeze check and the divergence-record check a final time (INV-INS-109)
- [ ] 9.4 Run `/rv-qa-lint-fix` for the Python touched — `rv-experiment` and any verification scripts
- [ ] 9.5 Run `/rv-verify rv-experiment`
- [ ] 9.6 Invoke `/rv-code-reviewer` via the Skill tool
- [ ] 9.7 Run `/rv-docs-sync` for any module whose docs the Group 6 change makes stale
