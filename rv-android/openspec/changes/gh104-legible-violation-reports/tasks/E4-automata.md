# Group 8 — E4: six structural repairs and two measured sites in `jca_android`

Tracked checkboxes: `tasks.md` §8. Starts after Groups 6 (gates + harness exist) and 7 (every report site already carries its envelope). Five files edited, six repairs, two sites recorded without an edit, one withdrawal; one owner per file, sequential execution is fine — this group is small.

## Subagent brief

This is **not** a replay of gh101's hunks. The 51 `layer-2` and 42 `predicate-graph` hunks of `data/gh101/divergence_record.csv` are out of scope: the predicate half no longer exists (Group 2 removed `ExecutionContext` from the set) and the allow-list half was re-derived from the api30 rules directly (Group 2 task 2.4), so replaying `jca_android`'s edits would import decisions this set does not share. There is no `replay_plan.csv`.

What remains is the set of defects **provable against the CrySL rule, the JDK signature, or the generated monitor itself**. Read `design.md` D-7, D-10 and D-14, the `instrumentation` delta (`Executable Structural Gates`, `Differential Harness`, INV-INS-118/123/124/125/129), and `MetaCrySL/generated/api30/<Rule>.cryptsl` for the specification you are editing. MetaCrySL is read-only. Do not touch `jca/` or the archived `jca_android_bug_predicate/` — reading the archived file as a reference is fine, reading is not touching.

Per repair: one `data/jca_android/divergence_record.csv` entry (kind + reason + task id), one harness run before/after with the classification written out, and the `codes.csv` bijection preserved (a repair that adds or removes a report site adds or removes its row). Line numbers below are the frozen `jca` seed's; after Groups 2 and 7 they have moved — locate by symbol, not by number, and record the number you actually edited.

## What the 2026-08-18 re-confrontation changed

The list this group inherited had seven items and one criterion: repairs that are probable against the source and do not change what is accused. Confronted with the api30 rules, `javap` on `android-30`, the frozen-control monitor (`results/gh101_group8_jca_frozen_control/monitors/`) and the 97,018-row published corpus, two of the seven turned out to be classified backwards and one was not a defect at all.

| # | item | probable? | changes what is accused? | Δ in the corpus |
|---|---|---|---|---|
| 8.1 | `GCMParameterSpecSpec` `c1`→`c2` | yes | no — `fail` unreachable before and after | 0 |
| 8.2 | `SecretKeySpecSpec` parenthesis | in the text; inert in effect | no | 0 |
| 8.3 | `MessageDigestSpec` `reset` | yes — but it is **not** dead | **yes, the largest**: accuses **less** | not derivable; ceiling 100 rows / 7 sites |
| 8.4 | `KeyPairGeneratorSpec` `algorithm` | partly — mechanism was misdiagnosed | no | 0 |
| 8.5 | `SignatureSpec:99,:106` | yes | **yes** — only adds | 0 today |
| 8.6 | `KeyPairGeneratorSpec:71-72` | yes, proven | no | 0 |
| 8.7 | `SSLContextSpec:64`, `TrustManagerFactorySpec:63` | yes | **yes** — only adds; measured, not repaired | 0 today |
| 8.8 | field-versus-argument guard | **no** | **no** — it is a no-op | 0 |

Two corpus facts frame all of it. Thirteen of the seed's 23 specifications are **mute** in the published corpus — zero of the 97,018 rows — and three of them (`GCMParameterSpecSpec`, `SecretKeySpecSpec`, `KeyGeneratorSpec`) are where four of the original seven items lived. And `KeyPairGeneratorSpec` contributes 16 rows with **zero** `UnsafeAlgorithm`, against 8,843 rows of that message shape in five other specifications — which is the corpus confirming 8.6 on its own.

## The six repairs

### 8.1 `GCMParameterSpecSpec` — the duplicate `c1`

`:23` declares `event c1` for `GCMParameterSpec.new(int, byte[])` and `:34` declares `event c1` **again** for `GCMParameterSpec.new(int, byte[], int, int)`. The `ere` at `:48` reads `c1 | c2`, and `c2` is declared nowhere, so the second constructor is invisible to the automaton and the generated monitor carries two `Prop_1_event_c1` methods against one `c1` transition row — precisely the G-6′ hit. `generated/api30/GCMParameterSpec.cryptsl:17,19,21` declares `c1`, `c2` and `Cons := c1 | c2`. **Rename the `:34` declaration to `c2`.** One token. After it: G-6′ = 0 and G-ERE = 0 on this file.

Write the nil behavioural effect into the divergence entry, with the reason: the monitor is indexed by the constructed object (`GCMParameterSpecSpec(GCMParameterSpec s)`), each monitor therefore receives at most one event, and the `fail` state is unreachable before the repair and after it (`MultiSpec_1RuntimeMonitor.java:4232` one shared row `{1,2,2}`, dispatched at `:4283` and `:4300` under distinct event ids). The two constructors already carry distinct guards, so what collapses is the transition row alone, and it is identical in both. The corpus has 0 rows for this specification.

### 8.2 `SecretKeySpecSpec:27-30` — surplus parenthesis, check before editing

`c1`'s `condition(` opens one group and closes two; compare `c3` at `:44-47`, which is well-formed. The imbalance is real in the text and **inert in effect**: JavaMOP captures the pointcut as raw text up to the first `{` (`javamop.jj:1441`) and parses it without requiring `<EOF>` (`aspectj.jj:49`), so the extra token is discarded without diagnostic and the generated guard is already the intended one (`MultiSpec_1RuntimeMonitor.java:7725`).

Group 2 tasks 2.3 and 2.4 remove **both** terms of that condition — the `ExecutionContext.validate` and the algorithm list — and `generated/api30/SecretKeySpec.cryptsl:29` constrains only `length(keyMaterial) >= off + len`, nothing about `alg`. So check first whether the `condition` still exists at all. If it is gone, close the task with that recorded and make no edit; if it survives, remove the `)` and the lint's unbalanced-parentheses check goes clean.

### 8.3 `MessageDigestSpec:74-76` — the `reset` event, which is not dead

`event reset` has an empty body and no clause behind it in `generated/api30/MessageDigest.cryptsl` (whose `EVENTS`/`ORDER` do not mention it, whose `CONSTRAINTS` are `digestAlg in {…}`, `pre_len > pre_off`, `len > off`, and which carries no `REQUIRES` and no `NEGATES`). It is the **only** true `orphan-without-clause` gate G-2 reports on the entire frozen set — the other 17 orphans are the correct encoding of `CONSTRAINTS`/`REQUIRES`/`FORBIDDEN`, which never enter an `ORDER`. **Delete the event.**

What the inherited brief got wrong, and what it costs: `reset` is not inert. It is the only orphan of the set that has **no `condition()` either**, so nothing gates it, and the generator gives it the row `Prop_1_transition_reset = {4,4,4,4,4}` (`MultiSpec_1RuntimeMonitor.java:6369`) against a `fail` state of 4 (`:6504`). Every woven `MessageDigest.reset()` therefore accuses, whatever the algorithm, and because the `@fail` handler calls `__RESET` the monitor returns to state 0 and the `digest()` that follows accuses again — two `InvalidSequenceOfMethodCalls` per execution of a correct method. Exactly three orphans of the frozen set carry no `condition()`: this one and `PBEKeySpecSpec.f1`/`f2`, and the latter two encode a `FORBIDDEN` clause and are supposed to accuse on sight.

This is **the one repair of the group that removes accusations**. Harness evidence is mandatory and the classification is `removed`, never `unchanged`. Magnitude is not derivable from the published corpus, because `errors.csv` carries no event id and its `class`/`method` columns are the call site (`__LOC`), never the event name — 0 rows name `reset` and that proves nothing. Record instead the identifiable ceiling: the 100 rows over 7 `MessageDigestSpec` call sites that raise `InvalidSequenceOfMethodCalls` and no `UnsafeAlgorithm` at all, inside a universe of 10,135 such rows over 38 apps. Two call sites are confirmed woven in the frozen control's own instrumented APKs (`X509CertificateViewAdapter.getDigest` in `com.owncloud.android_48000100` and `eu.opencloud.android_9`). Note also that the archived `jca_android_bug_predicate` had already deleted this event — the repair has a precedent, not a novelty.

Removing the event reindexes `d1`/`d2`/`d3` from event ids 6/7/8 to 5/6/7. Nothing else moves: the transition tables are indexed by state, and the state set comes from the `ere`, which never mentioned `reset`.

### 8.4 `KeyPairGeneratorSpec:26` — `String algorithm` never initialised

The field is declared at `:26` with no initialiser and is an instance field of the monitor class, so it defaults to `null` and compiles (`MultiSpec_1RuntimeMonitor.java:5241`).

Correct the inherited diagnosis in the divergence entry, because both halves of it were wrong. The field is written by `g1`, `g2` and `g3` (`:44`, `:52`, `:59`) — the **`getInstance`** events — and by no `init*` event. And the first read is not `:70` but `:29`, the `switch(algorithm)` inside `validate()`, which the `condition` calls before any body runs; `switch` on a `null` `String` raises `NullPointerException`, so the reachable consequence is an exception, not a false accusation. `:70` is unreachable in any case (task 8.6). The path exists because `KeyPairGenerator.getInstance(String, Provider)` carries no pointcut — only the one- and two-argument overloads are bound (`MultiSpec_1MonitorAspect.aj:357,365`) — so a generator obtained through it reaches `initialize(int)` with the field still `null`.

**Guard the read**: `if (algorithm == null) return false;` at the head of `validate`. Do **not** initialise to `""`: `switch("")` falls through to `return false`, which makes `initError` fire where the call raises today and adds accusations reading `invalid key size for algorithm .` — the same shape as the 8,843 `but found .` rows this change exists to eliminate. Guarding adds none. State the choice and the reason in the divergence entry.

The exception's real damage is not in this file. It is the dispatcher lock: 134 acquisitions, 134 releases, zero `finally` blocks, one `ReentrantLock` shared by every specification (`:9005`), and every other dispatcher spins on `tryLock()`. That is INV-INS-129 and tasks 3.6-3.8, not this group.

### 8.5 Dead pointcuts — `SignatureSpec:99` and `:106`, repaired

Return types in the pointcut declarations do not match the JDK signatures, so the pointcuts can never match. Confirmed with `javap` against `$ANDROID_HOME/platforms/android-30/android.jar`:

- `:99` declares `sign()` returning `byte`; the API is `public final byte[] sign()`. Fix to `byte[]`.
- `:106` declares `sign(byte[], int, int)` returning `byte`; the API is `public final int sign(byte[], int, int)`. Fix to `int`. (`s2` has no `returning` clause and writes its predicate from the bound argument, so the return type does not move its payload.)

The gate is exact in both weavers: AspectJ matches return types exactly, and the dexlib2 engine implements it in code with a dedicated test (`PointcutMatcher.java:361-363`, `PointcutMatcherTest.java:603-612`, "concrete return-type gate MUST be exact"). The advices were generated and simply never fire (`MultiSpec_1MonitorAspect.aj:642-650`).

Why these two are repaired while the pair in 8.7 is not: here the automaton is genuinely broken. `s1`/`s2` are the **only** transition into the accepting state of the signing branch (`Prop_1_transition_s1 = {8,8,8,8,8,8,6,6,8}`, `MultiSpec_1RuntimeMonitor.java:8380`), so with them dead a monitor that has reached state 7 stays there, `@match` never runs on that branch, and a second `initSign`/`initVerify` on the same object accuses falsely.

Both events create monitors, so a revived `sign()` on a `Signature` whose `getInstance` was not observed starts in state 0 and `s1[0] = 8` accuses immediately. The harness before/after must name `introduced` for each. Record that the corpus attributes 0 rows to either site, that all 990 `SignatureSpec` rows are the verification branch over 4 apps, and that the false failures the repair removes have 0 measured instances — the repair fixes nothing already in the dataset and its cost is future accusations only.

### 8.6 `KeyPairGeneratorSpec:71-72` — unreachable branch, removed

**Remove** the report. The proof is a set equality, not an inference from control flow: `condition(validate(keySize))` at `:69` compiles to `if (!(validate(keySize))) { return false; }` ahead of the body (`MultiSpec_1RuntimeMonitor.java:5364-5370`), and `validate` (`:29-36`) returns `true` exactly for `{RSA, DSA, DiffieHellman, DH, EC}`, which is `safeAlgorithms` (`:22`) member for member. So `!safeAlgorithms.contains(algorithm)` at `:70` is false whenever it is evaluated, and `algorithm` cannot change between the two — same method, same lock. The corpus agrees: 0 of the 16 `KeyPairGeneratorSpec` rows are `UnsafeAlgorithm`, against 8,843 rows of the same message shape in five other specifications.

Drop the site's `codes.csv` row. Group 7 already flagged this site as unreachable in its census — cross-check that its entry and yours agree.

Record what the removal gives up: api30 `KeyPairGenerator.cryptsl:45` (`alg in {"DSA","DH","RSA"}`) **does** support an `UnsafeAlgorithm` accusation for this specification, and `g3` (`:55-60`, `condition(!safeAlgorithms.contains(alg))`) is the event that could host it — it captures exactly the algorithms outside the list and today only writes the field. Moving the accusation there is behavioural and is **not** done in this group.

## The two sites measured and not repaired (8.7)

Researcher decision, 2026-08-18: reviving either only adds accusations, and the published corpus cannot size that. Add both to `data/jca_android/conformance_record.csv` with the `javap` signature, the transition row and the harness verdict; change no `.mop` text.

- **`SSLContextSpec:64`** declares `createSSLEngine` returning `void`; the API returns `SSLEngine`. Unlike `SignatureSpec`, the automaton is not broken by it: `engine` is a `1→1` loop and the accepting state is reached by `init` (`Prop_1_transition_init = {3,3,1,3}`), which matches api30 `SSLContext.cryptsl:39` making `Engine?` optional. The only loss is a predicate never written, and Group 2 removed the predicates anyway. Reviving it would accuse every `createSSLEngine` outside the accepting state; likely magnitude ≈ 0 (no occurrence of `createSSLEngine` in the 197 CogniCrypt reports of `dataset/cc.csv`; the corpus is dominated by OkHttp, which uses `getSocketFactory()`).
- **`TrustManagerFactorySpec:63`** declares `getTrustManagers` returning `KeyManager[]`; the API returns `TrustManager[]`, and the `returning(TrustManager[][] trustManager)` clause at `:62` is a double array. **This site was not in the lineage's catalogue — say so in the entry.** It is the riskier of the two: `gtm1` is in the `fsm` (`final [ gtm1 -> start ]`) with the row `{3,0,3,3}`, so from the start state it goes straight to `fail`, and it sits on the specification that carries 18,029 of the corpus's 97,018 rows over 64 apps.

A systematic pass over all 138 `call()` pointcuts of the seed against `android-30` finds exactly four return-type mismatches: the two of 8.5 and the two here. Record that the audit was exhaustive, so a later reader does not have to redo it.

## The withdrawal (8.8)

`KeyGeneratorSpec:47` and `MessageDigestSpec:55` guard on `contains(currentAlgorithmInstance)` rather than on the argument the event has just bound. The lineage read this as a stale field never evaluating the fresh algorithm. It is not a defect.

`g1` and its sibling are emitted into the **same wrapper**, with `g1` first — `monitors/mop/MonitorWrappers.java:192-193` (`KeyGenerator`) and `:357-358` (`MessageDigest`), and the same order in `MultiSpec_1MonitorAspect.aj:321-327` and `:459-465` and in the descriptor's `monitorCalls`. Both resolve the same object-indexed monitor (the object is the value `getInstance` just returned, so the monitor is fresh), and `g1`'s body writes `currentAlgorithmInstance = alg` before the sibling's `condition` is evaluated. The field is initialised to `""`, never `null` (`MultiSpec_1RuntimeMonitor.java:4749`, `:6362`). So: a safe algorithm makes `g1` fire and write the field, and the sibling's `!contains(field)` is false; an unsafe algorithm makes `g1` return early without writing, the field stays `""`, and `!contains("")` is true. The sibling fires exactly when `!contains(alg)` — which is what the repair would have produced.

The corpus agrees: `KeyGeneratorSpec` has 0 rows of 97,018, and no `MessageDigestSpec` row carries a **safe** algorithm in its `but found` (the distinct values are `MD5` 3,552, `SHA-1` 1,915, `SHA1` 424, `SHA` 1, and `.` 156), which is the signature a stale field would have left. The 156 empty ones come from objects that saw no `getInstance` event at all — Guava's `prototype.clone()` and kmp-tor — a different cause.

Enter it in the conformance record as a **checked non-defect**, with the fragility named: the equivalence rests on declaration order, so a set that reordered the events would change behaviour. Make no edit. `design.md` D-4's residues paragraph has been corrected to match, and the `KeyPairGeneratorSpec` `__RESET` residue it also declares is unaffected.

## What is explicitly out of scope here

- The 51 `layer-2` and 42 `predicate-graph` gh101 hunks, and the `CipherSpec` 17→14 / `MacSpec` 8→11 alphabet re-budgets that came with them. If a repair above needed a new `Cipher` event, the ceiling would still bind (INV-INS-115: 17 events generate in 53 s / 3.3 GB, 18 raise `StackOverflowError`) — none of them does.
- `SecretKeySpec` (the null detector) and `RandomStringPassword` — both left the set in Group 2.
- Any allow-list content: settled in Group 2 tasks 2.4-2.7 and held by gate G-CONF.
- The dispatcher lock (INV-INS-129): a generator repair, owned by Group 3 tasks 3.6-3.8, not by any `.mop`.
- Moving `KeyPairGeneratorSpec`'s `UnsafeAlgorithm` accusation to `g3`; reviving the two pointcuts of 8.7; anything in `MetaCrySL`.

## Conformance record (task 8.11)

`data/jca_android/conformance_record.csv` must be complete when this group ends: one row per surviving specification (21), columns as `data/gh101/conformance_record.csv`. There is **one** anchor, the api30 rule (design D-10, single oracle) — do not reintroduce a per-clause availability/recommendation split. Group 2 wrote most of it; you add the rows the six repairs touch and check that the entries it owed are there: the `EC` divergence of task 2.6, the four ECDSA algorithms of task 2.7, the declared cost of the `api30-admits` rule from task 2.4 (5,892 of 6,048 `MessageDigestSpec/UnsafeAlgorithm` rows stop being reported), the two measured-not-repaired pointcuts of 8.7, and the withdrawn item of 8.8.

## Commands

```bash
python3 scripts/gh104_gates.py <scratch>/MultiSpec_1RuntimeMonitor.java --allowlist data/jca_android/gate_allowlist.csv   # G-2 orphan-without-clause 0; G-6' 0; G-ERE 0
python3 scripts/gh104_mop_lint.py ../rvsec/rvsec-mop/src/main/resources/jca_android      # clean
python3 scripts/gh104_divergence_record.py --check
python3 scripts/gh104_diff_harness.py --a <snapshot before this file's edit> --b ../rvsec/rvsec-mop/src/main/resources/jca_android --traces traces --out evidence/harness/e4-<Spec>
grep -c "^\s*event " ../rvsec/rvsec-mop/src/main/resources/jca_android/CipherSpec.mop   # <= 17; record generation time and RSS
javap -cp $ANDROID_HOME/platforms/android-30/android.jar java.security.Signature         # return-type evidence for 8.5
uv run pytest --import-mode=importlib -o "addopts=" tests/parity -q
```

## Acceptance

- The six repairs landed, each with a divergence entry naming the CrySL clause, the JDK signature or the generated-monitor line that proves it is a defect.
- The two sites of 8.7 and the withdrawal of 8.8 recorded in the conformance record, with no `.mop` text changed for any of them.
- Gates on `jca_android`: G-2 `orphan-without-clause` = 0, G-6′ = 0, G-ERE = 0, G-CONF green, G-PRED green, lint clean; every remaining G-2b′/G-2d hit allowlisted with a reason.
- Harness evidence per file, with `removed` explicitly named for 8.3, `introduced` for the two revived pointcuts of 8.5, and `unchanged` for 8.1, 8.2, 8.4 and 8.6.
- `CipherSpec` still generates within the ceiling (time and memory recorded).
- Conformance record complete (21 rows) and its pytest green.
- One commit per repair or one per file: `fix(jca_android): <o defeito> (refs #104)`.
