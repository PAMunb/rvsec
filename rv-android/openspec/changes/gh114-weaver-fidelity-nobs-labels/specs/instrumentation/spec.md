## Purpose

This delta changes two things the `instrumentation` capability owns: how the DEX-native weaver (`rvsec-instrumentation-dexlib2`) turns an advice into bytecode, and what the successor specification set `jca_android` says when it reports.

The weaver half closes five measured divergences from AspectJ semantics. AspectJ's semantics is the reference because the specifications are written in its pointcut language; no other weaver is run or compared. Each divergence was confirmed in the bytecode of instrumented APKs: an untyped `args(...)` matches a call of any arity, so a one-argument `getInstance` fires the two-argument event too; a call whose owner is a framework subtype that inherits the matched method gets no wrapper and nothing counts the drop; a branch whose target is a hooked call jumps over the inserted monitor call; a nested type written with a dot resolves as a package; and an `after` advice does not run when the matched call throws. The first and the last change what a campaign reports, in opposite directions, and each repair is accepted against a count taken before and after it on instrumented APKs rather than against a campaign.

The specification half is about the `-NOBS-` family. A non-observation report says that the predicate store has no entry for the object a rule constrains, and today that single answer covers situations an analysis must treat differently: a `null` the API documents as "use the platform default", a fresh array around a trust manager a factory did issue, an object whose producer already reported it, a first observed event that is not the creation of the object, a failure that follows a creation the specification refused, a second `init` after an operation finished, key material that was random where the rule asks for prepared material. This delta gives each of those its own code inside the existing families, keeps every reported site reported (with one stated exception, the per-element trust-manager credit), keeps the store comparing objects by identity, and appends evidence keys — a fingerprint of the value and the class of a manager — that no verdict reads. Every rule here is a statement about the JCA/Android API or the weaver and holds for any set of APKs; none names an application, a library or a dataset.

One value clause changes: the RSA key-size list of `RSAKeyGenParameterSpecSpec.mop` is transcribed from the sibling expert rule, because the two expert rules for the same key disagree and the literal list admits the weaker key.

The frozen `jca` set is not edited. The weaver is shared code, so its five repairs reach a `jca` run as well; by decision of the researcher (2026-09-15) no impact on `jca` is measured, and the discontinuity is declared rather than enumerated.

## Data Contracts

### Input
- `MultiSpec_1MonitorAspect.json: AspectDescriptor` — advices with `position`, `pointcut` and `monitorCalls`, produced by the monitor generator from `rvsec-mop/src/main/resources/jca_android/*.mop`
- `android.jar` — framework classes read by `AndroidClassIndex` for signature expansion and subtype resolution
- `classes*.dex` of the input APK

### Output
- Woven `classes*.dex` and the monitor DEX
- `instrument_results.json` per APK (`BatchRunner` counts map): `advicesExcludedByArity` now counts advice/overload pairs excluded from matching; new keys `wrapperTargetsUnresolved`, `wrappersAliasedToSubtype` and `wrapperAliasesUnmerged`
- `rvsec-mop/src/main/resources/jca_android/codes.csv` with a seventh column `label`
- Violation lines under tag `RVSEC` whose envelope may carry the evidence keys `vfp` and `vcls` after `msg`

### Side-Effects
- **Report counts**: A1 removes artefactual `-ORDER-` reports; A5 adds reports on calls that throw; the RSA transcription moves one value in each direction. A campaign after this change is not count-comparable with one before it without the discontinuity stated.
- **`data/jca_android/`**: `divergence_record.csv` rows refreshed for every edited hunk of a seeded `.mop`, the RSA `oracle-wart` row (`:376`) rewritten and `:269` amended, and the rows that assumed the skipped `after` advice rewritten; a `conformance_record.csv` key-size row for RSA and re-grounded rows for the digest streams; `coverage_matrix.csv` re-emitted; updated census pins of the predicate-graph gate.

### Error
- `IllegalStateException` from `DexWeaver.registerWrapper` — still raised on a genuine wrapper rebind; aliasing a wrapper to a framework subtype MUST NOT raise it

## Invariants

- **INV-INS-159**: An `args(...)` clause constrains the arity of the call in every form. With `k` positions and no trailing `..`, a call with a parameter count other than `k` MUST NOT match; with a trailing `..` after `k` leading positions, a call with fewer than `k` parameters MUST NOT match. This holds for binding names, `*` and typed positions alike, in `PointcutMatcher.matchArgs` (inline path) and in `WrapperEmitter` grouping (wrapper path). An advice with no `args(...)` clause is not constrained.
- **INV-INS-160**: A call whose static owner `T` is a framework type SHALL be woven with every wrapper-path advice whose owner pattern admits `T` (`Owner+` with `Owner` assignable from `T`), whether `T` declares the method or inherits it. A wrapper target for which no method can be resolved after climbing the framework hierarchy MUST be counted in `wrapperTargetsUnresolved`, and an invoke on a framework subtype that no single registered wrapper covers (its candidate supertype owners have no most specific one) MUST be counted in `wrapperAliasesUnmerged`; no wrapper target and no such invoke MAY be dropped without being counted.
- **INV-INS-161**: Control that reaches a call with an inserted `before` block, by fall-through, by an `if-*` or `goto*` branch, or by a switch case, MUST execute the inserted block (its `if(...)` guard included) before the call. Every label that an `if-*`, `goto*` or switch payload targets at the call, and every line-number debug item located at the call, MUST be located at the first inserted instruction after insertion. Try-range boundaries and local-variable debug items MUST stay where they were. In a method whose register frame grows or whose try ranges the weaver rebuilds, every line-number item is already lost, and the line clause has no object there.
- **INV-INS-162**: A pointcut type written `Outer.Inner`, imported or qualified, MUST resolve to the binary name `Outer$Inner` when `Outer` names a class known to the framework index or the APK.
- **INV-INS-163**: An `after` advice without `returning` or `throwing` MUST run its monitor calls when the matched call completes normally and when it throws, and in the throwing case the original throwable MUST be rethrown unchanged. This holds on the wrapper path and on the inline constructor path; the inline constructor path concerns a plain `after` on a constructor, which no event of `jca_android` declares today (its constructor events are `after … returning`).
- **INV-INS-164**: In `jca_android`, a label code is a numbered code inside an existing family: `-NOBS-` for `platform-default`, `upstream-refused`, `application-manager` and `random-key-material`; `-ORDER-` for `creation-unobserved`, `creation-refused` and `reuse-after-final`. Every row of `codes.csv` carries exactly one `label` from the closed vocabulary `{violation, sequence, not-observed, platform-default, upstream-refused, application-manager, random-key-material, creation-unobserved, creation-refused, reuse-after-final}`, and a code's label MUST agree with its family (`sequence`, `creation-unobserved`, `creation-refused`, `reuse-after-final` only on `-ORDER-`; `not-observed` and the four `-NOBS-` labels only on `-NOBS-`; `violation` on every other family). Every creation event of `jca_android` guarded by an allow-list `condition(...)` MUST have a refused twin with the negated guard for every overload its pointcut admits, so that a creation call in woven code always runs a creation body; a twin added for that purpose MUST NOT report and MUST NOT write fields other than the creation facts.
- **INV-INS-165**: A label code MUST be emitted at the site, and under the branch, where the unlabelled code of the same family would otherwise be emitted. Applying the labels MUST NOT add or remove a reported `(class, method, spec, event, location)` except where the per-element trust-manager credit accepts an array whose every element a factory issued.
- **INV-INS-166**: The evidence keys `vfp` and `vcls` MAY follow `msg` only in a `-NOBS-` envelope, in that order, each at most once, quoted like every other value. No guard, transition or predicate write MAY read them.
- **INV-INS-167**: `RSAKeyGenParameterSpecSpec.mop` MUST admit exactly `{2048, 3072, 4096}`, the list of `KeyPairGenerator.crysl:29`, and the `oracle-wart` row of `data/jca_android/divergence_record.csv` that names both expert clauses MUST record that alignment. The pinned rule file MUST NOT be edited.

## ADDED Requirements

### Requirement: Positional Arity Is Enforced in Pointcut Matching and Wrapper Grouping

An `args(...)` clause SHALL constrain the number of parameters of the call it matches, in every form it can take (INV-INS-159). `PointcutMatcher.matchArgs` (`pointcut-engine/.../PointcutMatcher.java:268-306`) today returns a match immediately when the clause has no type constraint (`:269-271`), so the binding form `args(alg, *)` matches a one-parameter call; and `WrapperEmitter` (`advice-emitter/.../WrapperEmitter.java:307-314`) counts an arity-incompatible advice into `advicesExcludedByArity` and then fires it anyway. The effect on a run is concrete: `TrustManagerFactory.getInstance(String)` fires both `g1` (`args(alg)`) and `g2` (`args(alg, *)`); `g2` arrives at a state that does not declare it, the monitor reports `-ORDER-00` and resets, and every later event of the same object reports `-ORDER-00` as well. The same happens in `KeyManagerFactorySpec` and `SecureRandomSpec`, and in `SecureRandomSpec` the `@fail` discards the arrays waiting for `RANDOMIZED`, which surfaces later as non-observation reports.

The arity rule is the one AspectJ applies: `k` positions without a trailing `..` require exactly `k` parameters; a trailing `..` after `k` leading positions requires at least `k`. The number of positions is read from `ArgsPC.types()`, which keeps the `..` that `ArgsPC.names()` drops. The rule SHALL apply on both weaving paths: the inline path matches through `PointcutMatcher` (`DexWeaver.java:432`), and the wrapper path groups advices without calling the matcher (`DexWeaver.java:394-405`), so the grouping loop SHALL exclude an incompatible advice from the group of that concrete overload instead of counting and keeping it. `advicesExcludedByArity` keeps its name and its unit (advice/overload pairs) and now counts pairs that were actually excluded.

An advice with no `args(...)` clause is not constrained, and this is not a loophole but the reason the counter was introduced first: 25 wrapper-path `after` advices declare parameters without `args()` and bind them by position (`WrapperEmitter.java:822-832`); a rule that compared the advice's parameter list to the call instead of its `args()` clause would silence them.

#### Scenario: a one-argument call fires only the one-argument event

- **WHEN** `TrustManagerFactory.getInstance("PKIX")` is woven with a descriptor whose `TrustManagerFactorySpec` group carries `g1` with `args(alg)` and `g2` with `args(alg, *)`
- **THEN** the wrapper of `getInstance(String)` MUST call `TrustManagerFactorySpec_g1Event` and MUST NOT call `TrustManagerFactorySpec_g2Event`
- **AND** the wrapper of `getInstance(String, String)` MUST call `g2` and MUST NOT call `g1`
- **AND** `advicesExcludedByArity` MUST be `2` for that APK, one pair per overload

#### Scenario: the binding form is constrained on the inline path

- **WHEN** `PointcutMatcher.matchArgs` evaluates `args(o, o1)` against a call with three parameters
- **THEN** it MUST return no match
- **AND** against a call with two parameters it MUST return a match binding `o` and `o1`
- **AND** `args(*, ..)` MUST match a call with one or more parameters and MUST NOT match a call with none

#### Scenario: an advice without `args()` is untouched

- **WHEN** `SSLContextSpec_init`, an `after` advice declaring `(KeyManager[], TrustManager[], SecureRandom, SSLContext)` with no `args()` clause, is grouped for `SSLContext.init(KeyManager[], TrustManager[], SecureRandom)`
- **THEN** it MUST remain in the group and its monitor call MUST be emitted
- **AND** it MUST contribute `0` to `advicesExcludedByArity`

#### Scenario: the double fire disappears from an instrumented APK

- **WHEN** an APK that calls `getInstance(String)` on `TrustManagerFactory`, `KeyManagerFactory` and `SecureRandom` is instrumented before and after the repair and its woven DEX is disassembled
- **THEN** after the repair no wrapper of a one-parameter `getInstance` MUST invoke a monitor event whose advice declares two `args()` positions
- **AND** the per-wrapper event lists MUST differ between the two DEXes only in those pairs

### Requirement: Methods Inherited by Framework Subtypes Are Woven and Every Unresolved Wrapper Target Is Counted

A call whose static owner is a framework type SHALL be woven with every wrapper-path advice whose owner pattern admits that type, whether the type declares the called method or inherits it (INV-INS-160). Two mechanisms lose such calls today. First, `WrapperEmitter.expandCallTarget` (`WrapperEmitter.java:401-478`) asks `AndroidClassIndex.methods` for the methods **declared** by the pattern's owner (`:443-445`, index `AndroidClassIndex.java:115-126`); for `call(public byte[] SecretKey+.getEncoded())` the interface `javax.crypto.SecretKey` declares no `getEncoded`, the lookup is empty, `literalFallback` returns `null` for an instance target, and the target is dropped at `:291` with no counter. Second, a wrapper is registered under its exact owner descriptor and replaces only invokes whose defining class equals it (`DexWeaver.java:263-281`); aliases to subtypes are created only for classes defined inside the APK (`InheritanceResolver.java:79-96`), so an invoke of `Ljava/security/PublicKey;->getEncoded()[B` never reaches the wrapper registered for `Ljava/security/Key;`. AspectJ's `call(Key+.getEncoded())` matches both.

Resolution SHALL climb the superclass chain and the interfaces of the framework type when the declared lookup is empty, using the ancestry `AndroidClassIndex` already reads (`walkAncestors`, `:142-154`); the resolved signature is the inherited one and the wrapper's owner is the type written at the call site, so the exact-owner replacement finds it. The emitter SHALL fold into the wrapper of each wrapped framework owner the advices of every `Owner+` pattern that admits that owner, so each wrapper fires every advice that applies to its owner. When an invoke's defining class is a framework type assignable to the owners of registered wrappers for the same name and parameter list, the invoke SHALL be routed to the wrapper of the most specific of those owners (the one assignable to all the others), counted in `wrappersAliasedToSubtype`; when no candidate is assignable to all the others, no registered wrapper carries every applicable advice, and the invoke SHALL be left unwoven and counted in `wrapperAliasesUnmerged`. A wrapper target that still resolves to no method SHALL be counted in `wrapperTargetsUnresolved`. The three counters are published in `instrument_results.json` beside `wrappersGenerated`. The lost calls only ever created false non-observation reports — the producer `getEncoded` writes `PREPARED_KEY_MATERIAL` and nothing retracts it — so the repair removes reports and cannot hide a violation.

#### Scenario: an inherited method on a framework interface is wrapped

- **WHEN** an APK calls `secretKey.getEncoded()` through `invoke-interface Ljavax/crypto/SecretKey;->getEncoded()[B` and the descriptor carries `SecretKeySpec_e1` on `call(public byte[] SecretKey+.getEncoded())` and `KeySpec_ge1` on `call(public byte[] Key+.getEncoded())`
- **THEN** the invoke MUST be replaced by a wrapper whose owner is `Ljavax/crypto/SecretKey;`
- **AND** the wrapper MUST call both `SecretKeySpec_e1Event` and `KeySpec_ge1Event`
- **AND** `wrapperTargetsUnresolved` MUST be `0`

#### Scenario: a framework subtype of a wrapped owner is aliased

- **WHEN** an APK calls `invoke-interface Ljava/security/PublicKey;->getEncoded()[B` and only `KeySpec_ge1` on `Key+.getEncoded()` applies
- **THEN** the invoke MUST be routed to the wrapper of `Ljava/security/Key;` and woven with `KeySpec_ge1Event`
- **AND** no `IllegalStateException` MUST be raised by `registerWrapper`
- **AND** `wrappersAliasedToSubtype` MUST be incremented by `1` and `wrapperAliasesUnmerged` MUST stay `0`

#### Scenario: an unresolvable target is counted, not dropped

- **WHEN** a wrapper-path advice names an instance method that neither the owner nor any of its framework ancestors declares
- **THEN** no wrapper MUST be generated for it
- **AND** `wrapperTargetsUnresolved` MUST be incremented by `1` and published in `instrument_results.json`

### Requirement: An Inserted Before-Block Is Not Bypassed by Control Transfer

Instructions inserted before a matched call SHALL be executed by every path that reaches the call (INV-INS-161). `InstructionInjector.insertBefore` (`dex-mutator/.../InstructionInjector.java:80-87`) inserts through `MutableMethodImplementation.addInstruction` (`:457-463`), which creates new locations and leaves the labels and debug items on the location of the original call. A branch or a switch case that targets the call therefore keeps pointing at the call and jumps over the monitor. In the bytecode of an instrumented APK a method of the shape `if (nonce == null) goto L; …; hook; Cipher.init(mode, key, spec); goto END; hook; L: Cipher.init(mode, key)` never runs the second hook on the path that arrives by `goto L`; the monitor loses that `init` and reports `-ORDER-00` on the following `doFinal`. The same mechanism leaves the debug line entry on the call, so the inserted instructions inherit the line of the previous instruction and a `before` report names the wrong source line.

After the block (and its `if(...)` guard, when the plan carries one) is inserted, the labels located at the call that are targets of an `if-*`, `goto*` or switch payload, and the line-number debug items located at the call, SHALL be moved to the first inserted instruction. Nothing else moves. Try-range start and end labels stay: the inserted block is a static monitor call that throws only on a monitor defect, so which exception range covers it changes nothing the application observes, and moving range boundaries would touch exception handling for no measured gain. Local-variable debug items stay: they serve debuggers only. A method whose register frame grows or whose try ranges are rebuilt by the weaver (an after-throwing handler, a `!holdsLock` guard, a constructor after-finally handler) loses all its line-number items when it is rebuilt, so the line move has no effect in such a method; this requirement does not change that. Moving the line-number item makes the `source` of a `before` report name the line of the call; because the location is part of the collector's dedupe identity, this is a declared discontinuity against earlier campaigns, and the per-misuse count `(class, method, spec)` does not change. The guard's own skip label is created by `installGuard` (`:172-211`) on the call's location after the insertion and is not moved; the guard relies on it. `insertAfter` is not changed: a branch that targets the instruction after a call did not execute the call and must not execute its `after` block.

#### Scenario: a branch to the hooked call runs the hook

- **WHEN** a method `m` contains `if-eqz v5, L` and `L: invoke-virtual Ljavax/crypto/Cipher;->init(ILjava/security/Key;)V`, and a `before` advice on `Cipher.init(int, Key, ..)` is inserted at `L`
- **THEN** after weaving, the target of `if-eqz v5` MUST be the first instruction of the inserted block
- **AND** the fall-through path into the call MUST also pass through the inserted block exactly once

#### Scenario: a switch case, a try range and the line at the call

- **WHEN** a `packed-switch` case targets a hooked call, a try range begins at the same call, and the call carries the line-number entry `line 69`
- **THEN** the case target MUST be the first inserted instruction
- **AND** the try range MUST still begin at the call, not at the inserted block
- **AND** the first inserted instruction MUST carry `line 69`, so a `before` report from that block names line 69

#### Scenario: the guard keeps working

- **WHEN** a `before` plan with an `if(...)` guard is inserted at a call that is also a branch target
- **THEN** the branch MUST land on the first instruction of the guard prefix
- **AND** when the guard condition is false, control MUST reach the call without executing the monitor calls

#### Scenario: no hooked call remains a branch target in an instrumented APK

- **WHEN** `experimento-estudo02/scripts/branch_target_hooks.py` scans an APK instrumented after the repair
- **THEN** it MUST report `0` hooked calls whose address is the target of an `if-*`, `goto*` or switch

### Requirement: Nested Types in Pointcut Signatures Resolve to Binary Names

A type written `Outer.Inner` in a pointcut signature, whether imported by its dotted name or written fully qualified, SHALL resolve to the binary name `Outer$Inner` when `Outer` is a class (INV-INS-162). `TypeResolver.toDescriptor` (`pointcut-engine/.../TypeResolver.java:87-107`) replaces every `.` by `/`, so `java.security.KeyStore.ProtectionParameter` becomes `Ljava/security/KeyStore/ProtectionParameter;`, a descriptor no framework method carries; `KeyStoreSpec`'s events on `getEntry(String, KeyStore.ProtectionParameter)` and `setEntry(String, KeyStore.Entry, KeyStore.ProtectionParameter)` therefore never match. The same dotted assumption sits in `WrapperEmitter.resolveFqn` (`:647-676`) and `AndroidClassIndex.toInternal` (`:223-225`).

Resolution SHALL try the dotted name as a class first and, when no class of that name exists, replace the dots from the right with `$` one at a time until a class exists in the framework index or among the APK's classes, using a public existence query on `AndroidClassIndex` (which already caches presence and absence, `:156-189`). When no candidate exists the current descriptor is kept, so a genuinely unknown type behaves as today.

#### Scenario: an imported nested type resolves

- **WHEN** a specification imports `java.security.KeyStore.ProtectionParameter` and declares `call(public KeyStore.Entry KeyStore.getEntry(String, ProtectionParameter))`
- **THEN** the parameter descriptor MUST be `Ljava/security/KeyStore$ProtectionParameter;` and the return descriptor `Ljava/security/KeyStore$Entry;`
- **AND** a call `invoke-virtual Ljava/security/KeyStore;->getEntry(Ljava/lang/String;Ljava/security/KeyStore$ProtectionParameter;)Ljava/security/KeyStore$Entry;` MUST be woven

#### Scenario: a top-level type is unchanged

- **WHEN** `java.security.KeyStore` is resolved
- **THEN** the descriptor MUST be `Ljava/security/KeyStore;`

### Requirement: After Advice Runs on Normal and Exceptional Completion

An `after` advice that declares neither `returning` nor `throwing` SHALL run its monitor calls whether the matched call returns or throws, and SHALL rethrow the original throwable afterwards (INV-INS-163). This is AspectJ's `after` (after-finally), and `AfterEmitter`'s own contract states it (`advice-emitter/.../AfterEmitter.java:9-13`), but neither weaving path implements it. The wrapper path emits `R result = call(...); <monitor calls>; return result;` with no handler (`WrapperEmitter.appendWrapperMethod`, `:782-801`), and the inline constructor path inserts after the call without a try range (`DexWeaver.applyPlan` case `AFTER`, `:925-927`). In `jca_android`, 58 of the 202 events are plain `after`; `KeyAgreementSpec.dophase`, `SSLContextSpec.init` and `SecureRandomSpec.setSeed2` are among them.

The wrapper SHALL guard the call with a catch-all handler that executes the same monitor calls with the same bound arguments and rethrows; the inline constructor path SHALL use the try-catch installation the `after-throwing` path already uses (`InstructionInjector.installTryCatch`, `:266-360`), with a handler that runs the monitor calls and rethrows instead of binding the throwable. The inline constructor path applies to a plain `after` on a constructor; every constructor event of `jca_android` is `after … returning`, so in that set the path weaves nothing today and the wrapper path carries the repair. `after returning` and `after throwing` keep their current shapes. The whole event body runs on a throwing call, so its predicate writes and staged values happen there as well as its reports.

Only the digest-stream records rest on the skipped-advice behaviour, and they SHALL be rewritten for after-finally semantics: `conformance_record.csv:116,117,119,120` (which also misname the plain `after` of `DigestInputStreamSpec.r2` and `DigestOutputStreamSpec.w2` as `after … returning`) and `:118,121` (a throwing call with `len < 0` now reaches the `len <= 0` site); `divergence_record.csv:45,46`, which record the nested-type and after-finally defects as not repaired, closed as repaired by this change; and `divergence_record.csv:105,106`, with the comment blocks `DigestInputStreamSpec.mop:75-89` and `DigestOutputStreamSpec.mop:76-88`. The two digest guards that become reachable (`off < 0`, `off + len > length`) stay `deferred-constant`, on the ground that the platform refuses the call (decision of 2026-09-15); no code is added.

The repair is verified on the woven output: the generated wrapper source and an inline constructor site generated for such an advice carry a try range around the matched invoke whose handler invokes the same monitor calls and rethrows.

#### Scenario: a throwing call still reaches the monitor

- **WHEN** a fixture calls `keyAgreement.doPhase(null, true)`, which throws `InvalidKeyException`, under the `after` advice `KeyAgreementSpec_dophase`
- **THEN** `KeyAgreementSpec_dophaseEvent` MUST be invoked with `pubKey = null`, `lastPhase = true` and the target
- **AND** the `InvalidKeyException` MUST propagate to the caller unchanged

#### Scenario: a returning call behaves as before

- **WHEN** the same call returns normally
- **THEN** the monitor call MUST be invoked exactly once, after the call
- **AND** the wrapper MUST return the call's result

#### Scenario: the woven wrapper carries the handler

- **WHEN** the wrapper for `KeyAgreement.doPhase(Key, boolean)` under `KeyAgreementSpec_dophase` is disassembled from the monitor DEX of an instrumented APK
- **THEN** a try range MUST cover the `invoke-virtual` of `doPhase`, and its catch-all handler MUST invoke `KeyAgreementSpec_dophaseEvent` and end in `throw` of the caught register
- **AND** the normal path MUST invoke `KeyAgreementSpec_dophaseEvent` once and return the call's result

### Requirement: Label Codes of the Successor Specification Set

`jca_android` SHALL distinguish, by code, report situations that the `-NOBS-` and `-ORDER-` families today report under one code each (INV-INS-164, INV-INS-165). No new family is introduced: a label is the next free number of the family in its file (numbering per file and per family, as `NEW_SPEC_CONVENTIONS.md:167` fixes), and `codes.csv` gains a seventh column, `label`, that names what the code means. Keeping the families is deliberate: every consumer that separates "not observed" from "accused" reads the family (`scripts/gh109_nobs_channel.py:153-163` counts every family other than `NOBS` as an accusation; `scripts/gh104_message_gate.py:427-436` requires that a code emitted under a `NOT_OBSERVED` branch be `NOBS`), and a new family would silently become an accusation in all of them.

The seven labels, and where each is emitted:

- **`platform-default`** (`-NOBS-`). In `TrustManagerFactorySpec.init` and `KeyManagerFactorySpec.init`, when the `KeyStore` argument is `null`, and in `SSLContextSpec.init`, separately for a `null` `KeyManager[]`, a `null` `TrustManager[]` and a `null` `SecureRandom`. Each of these `null`s is the documented request for the platform default; the current specifications read them on purpose (`TrustManagerFactorySpec.mop:102-112`, `KeyManagerFactorySpec.mop:91-104`, `SSLContextSpec.mop:176-185,204-208`) and the rule is not satisfiable by them, so they stay reported, under a code that says so.
- **`application-manager`** (`-NOBS-`). In `SSLContextSpec.init`, for a non-null trust-manager array not credited per element (next requirement) that contains an element whose class was defined by a class loader other than the one that defined `javax.net.ssl.TrustManager` — the application's own class. Key-manager arrays get no such code and keep their current reads. The class loader, not a package name, decides, so the rule holds for any APK. This is the code under which a trust-all manager built by the application lands; a delegating manager lands there too, and the monitor cannot tell them apart.
- **`upstream-refused`** (`-NOBS-`). At the consumer sites listed in the requirement below, when the bound object carries its `REPORTED_UPSTREAM` mark.
- **`random-key-material`** (`-NOBS-`). In `SecretKeySpecSpec.c1` and `c2`, when the key material is not `PREPARED_KEY_MATERIAL` but is `RANDOMIZED`. The rule requires prepared material and the specification records that decision (`SecretKeySpecSpec.mop:79-91`); the code separates the recorded decision from an untraceable array.
- **`creation-unobserved`** (`-ORDER-`). In the `@fail` handler of every specification whose automaton begins with a creation event, when no creation event was observed on that monitor. A creation event is every constructor or static-factory event that binds the monitored parameter through `returning(...)`, refused and forbidden twins included; an event bound through `target(...)` never is. The object was created where the monitor cannot see — inside the framework, by a route the rule does not list, or by a subclass — and every failure of that monitor is reported with this code. A creation call in woven code is never such a route: every creation event guarded by an allow-list has a refused twin for every overload it admits (INV-INS-164, next paragraph), so a refused creation runs a body too.
- **`creation-refused`** (`-ORDER-`). In the `@fail` handler of every specification with a refused creation, when the creation observed on that monitor was a refused one: a creation event whose guard is the negation of an allow-list test (`CipherSpec.g3`, `KeyGeneratorSpec.g3`, `KeyManagerFactorySpec.g3`, `KeyStoreSpec.g2`, `MacSpec.g3`, `MessageDigestSpec.g4`, `SecureRandomSpec.g4`/`g5`, `KeyPairGeneratorSpec.g3`/`g4`, and the two-argument twins below), or a forbidden creation that reports `FORB` (`PBEKeySpecSpec.f1`/`f2`, `SSLContextSpec.getDefault`). The automaton of such an object admits no use, so its ordering failure is the consequence of the refusal, not a wrong order the program chose; in the evidence campaign 16,429 report lines (11.7 %) were `-ORDER-00` failures that shared the misuse with a value code. In `KeyStoreSpec` the type is accused only at `getKey`, so for a refused store never read by `getKey` this report is the only one.

The two-argument refused twins complete the set of refused creations. `MessageDigestSpec`, `MacSpec`, `KeyStoreSpec`, `KeyGeneratorSpec` and `KeyManagerFactorySpec` declare a refused twin only for the one-argument `getInstance`, so a refused algorithm or type requested with a provider matches no event: the admitting guard is false, a false guard runs no body, and the later failure would read `creation-unobserved` for an object created in woven code. Each of them SHALL declare a new event with the file's two-argument pointcut and the negated guard, placed in the automaton beside the one-argument twin (the `ere` Kleene prefix, or the `unsafeAlg` transitions of the `fsm`). `CipherSpec` is at the ceiling of 17 events (INV-INS-154), so instead of a new event its `g3` SHALL be widened to `call(public static Cipher Cipher.getInstance(String, ..)) && args(transformation, ..)`, which admits both overloads and whose body only records the creation. `TrustManagerFactorySpec` and `SignatureSpec` accept any algorithm in their one-argument creation and guard only the two-argument one; their new two-argument twin SHALL lead where the first use fails, as it does when no event fires (a `fsm` state with no transitions; an `ere` Kleene prefix before `(g1 | g2)`). A new twin records the creation facts and nothing else: it emits no report and writes none of the fields other events read. The first use of the object therefore fails at the same event as before, and only the handler's code moves.
- **`reuse-after-final`** (`-ORDER-`). In the `@fail` handler of `CipherSpec` and `MacSpec`, when the failing event is an initialisation event and the object had completed an operation, and for every later failure of that monitor. The API permits reinitialising a used `Cipher` or `Mac`; the rule does not (`Cipher.crysl:85`, `Mac.crysl:41`) and the specification records it (`CipherSpec.mop:414-418`).

The precedence when more than one applies at a `-NOBS-` site is `platform-default`, then `upstream-refused`, then `application-manager` or `random-key-material`, then `not-observed`. In an `@fail` handler it is `creation-unobserved`, then `creation-refused`, then `reuse-after-final`, then `sequence`. The three `-ORDER-` labels persist on the monitor: once one of them is reported, every later failure of that monitor carries the same label, because after a reset no creation event can arrive for the object and the automaton cannot return to a state the object's real history satisfies (decision of 2026-09-15). A specification records "creation observed", "creation refused", "operation finished" and "reuse observed" in monitor fields written by the bodies of the corresponding events and by the handler; a refused creation sets "creation observed" as well. The generated `reset()` does not clear user fields (it only resets the state and the category flags), so these facts survive a failure of the same monitor. In the fifteen specifications whose automaton is a single construction (`ere : c1`, `c1 | c2`, …) `@fail` cannot fire, and their `-ORDER-` rows exist only for the bijection between report sites and `codes.csv` rows.

#### Scenario: the platform default is labelled

- **WHEN** an application calls `TrustManagerFactory.getInstance("PKIX")` and then `init((KeyStore) null)`
- **THEN** the report of `TrustManagerFactorySpec.init` MUST carry a `TRUSTMANAGERFACTORY-NOBS-NN` code whose `codes.csv` label is `platform-default`
- **AND** no `TRUSTMANAGERFACTORY-NOBS-00` MUST be reported for that call

#### Scenario: `SSLContext.init(null, tms, null)` yields two platform-default codes

- **WHEN** an application calls `sslContext.init(null, factory.getTrustManagers(), null)` with the array returned by the factory
- **THEN** the key-manager and random reads MUST report the two `platform-default` codes of `SSLContextSpec`
- **AND** the trust-manager read MUST NOT report

#### Scenario: an object created outside the monitor's view

- **WHEN** a `KeyPair` obtained from `KeyPairGenerator.generateKeyPair()` has `getPublic()` called on it and `KeyPairSpec`'s automaton fails on `gpu`
- **THEN** the report MUST carry `KEYPAIR-ORDER-01` with label `creation-unobserved`
- **AND** a second failing event on the same monitor MUST also carry `KEYPAIR-ORDER-01`

#### Scenario: a digest of a refused algorithm requested with a provider

- **WHEN** an application calls `d = MessageDigest.getInstance("MD5", "BC")` and then `d.digest()`
- **THEN** the refused two-argument twin of `MessageDigestSpec` MUST run and emit no report of its own
- **AND** `d1` MUST report the value code for `MD5` and the `@fail` at `d1` MUST carry the `MessageDigestSpec` code labelled `creation-refused`, not `MESSAGEDIGEST-ORDER-01`
- **AND** the reported `(spec, event)` pairs MUST be the ones reported without the twin

#### Scenario: a forbidden constructor followed by use

- **WHEN** an application calls `spec = new PBEKeySpec(chars)` and then `spec.clearPassword()`
- **THEN** `PBEKeySpecSpec.f1` MUST report its `FORB` code
- **AND** the ordering failure at `clearPassword` MUST carry the `PBEKeySpecSpec` code labelled `creation-refused`

#### Scenario: a reinitialised cipher

- **WHEN** an application calls `c = Cipher.getInstance("AES/GCM/NoPadding")`, `c.init(1, k, spec1)`, `c.doFinal(p1)`, `c.init(1, k, spec2)`
- **THEN** the report of the second `init` MUST carry the `CipherSpec` code labelled `reuse-after-final`
- **AND** a following `c.doFinal(p2)` that fails MUST carry the same label

#### Scenario: random bytes used as key material

- **WHEN** an application fills `byte[] raw = new byte[32]` with `SecureRandom.nextBytes` on an observed, admitted `SecureRandom` and calls `new SecretKeySpec(raw, "AES")`
- **THEN** the report MUST carry the `SecretKeySpecSpec` code labelled `random-key-material`, not `SECRETKEYSPEC-NOBS-00`

#### Scenario: the labels do not change which sites report

- **WHEN** the differential harness (`scripts/gh104_diff_harness.py`) replays its traces against the specification set before and after the labels
- **THEN** the set of reported `(spec, event, class, method, location)` MUST be equal, except for traces in which a trust-manager array is credited per element
- **AND** every difference in code MUST map an old code to a new code of the same family

### Requirement: Per-Element Credit of Trust-Manager Arrays

`TrustManagerFactorySpec.gtm1` SHALL mark every non-null element of the array the factory returns with `GENERATED_TRUST_MANAGERS`, in addition to the array itself (the constant exists in `Property.java:97-108` and has no producer or consumer today). `SSLContextSpec.init` SHALL answer `SATISFIED` for the trust-manager array when the array itself is marked, or when the array read answers `NOT_OBSERVED` and the array is non-empty and **every** element is marked. A `VIOLATED` answer is not upgraded by the elements; no site withdraws `GENERATED_TRUST_MANAGER` today, so no program distinguishes the two readings. Key-manager arrays are not credited per element (decision of 2026-09-15): `KeyManagerFactorySpec.gkm1` and the key-manager read of `SSLContextSpec.init` keep their current behaviour, apart from the `platform-default` label for `null`. An array with one unmarked element is not credited. Requiring every element closes the case of an array that mixes a factory-issued manager with a manager written by the application.

This is the one label rule that changes which sites report, and it is admitted because the object the rule constrains is the manager, and the manager is exactly the one the factory issued: an application that copies it into a new array (`arrayOf(trustManager)`) passes an array the store has never seen and today draws a non-observation report for a correct program.

#### Scenario: a manager copied into a new array is credited

- **WHEN** an application obtains `tms = factory.getTrustManagers()`, takes `tm = tms[0]` and calls `sslContext.init(null, new TrustManager[]{ tm }, null)`
- **THEN** `SSLContextSpec.init` MUST NOT report on the trust-manager argument

#### Scenario: a mixed array is not credited

- **WHEN** the array passed is `new TrustManager[]{ tm, trustAll }` with `tm` from the factory and `trustAll` an instance of an application class
- **THEN** `SSLContextSpec.init` MUST report the `application-manager` code
- **AND** `vcls` MUST name both element classes, in array order

### Requirement: Upstream-Refusal Mark

A producer specification that reports on the object it produces SHALL mark that object with the new appended property `REPORTED_UPSTREAM`, and a consumer that is about to report `-NOBS-` for a bound object SHALL report the `upstream-refused` code instead when the object carries the mark. A consumer that reports on an object it produces in turn marks that product, so a chain reports its first failure with its own code and every later link with `upstream-refused`.

The mark is written only by direct producers and by the `getEncoded()` bridge, and only when the site reports on the object by value or by origin (a code of the families `ALG`, `KEYSIZE`, `KSTYPE`, `PROTO`, `FORB`, `CONSTR` or `NOBS`, labels included); an `-ORDER-` report never marks. The producers and the object each marks: `SecretKeySpecSpec` (`c1`, `c2`) the constructed `SecretKeySpec`; `GCMParameterSpecSpec` (`c1`, `c2`) and `IvParameterSpec` (`c1`, `c2`) the constructed spec; `PBEKeySpecSpec.c1` the constructed spec; `X509EncodedKeySpecSpec.c1` the constructed spec; `KeyFactorySpec` (`genPublic`, `genPrivate`) and `SecretKeyFactorySpec.gen` the returned key; `KeyAgreementSpec` (`gs1`, `gs2`) the secret buffer when `conforms` is false; `KeySpec.ge1` and `SecretKeySpec.e1` the array `getEncoded()` returns when the key carries the mark. The bridge is included because without it the re-wrap `new SecretKeySpec(derived.getEncoded(), "AES")`, which `CipherSpec.mop:195-198` names as the conforming path after a key derivation, breaks the chain in the middle. The consumers are the `-NOBS-` sites whose bound object one of those producers can mark: `CipherSpec.i2`, `MacSpec.i1`, `IvChainJunction.use`, `SecretKeyFactorySpec.gen`, `KeyFactorySpec.genPublic`/`genPrivate`, `KeyAgreementSpec.dophase`, `SignatureSpec.i4`, `SecretKeySpecSpec.c1`/`c2`, `X509EncodedKeySpecSpec.c1`. Both lists are the ones decided on 2026-09-15 and are not closed: other producers that report on their product do not mark, and other `-NOBS-` sites keep `not-observed` even when a producer refused their object. In particular `MacSpec.i2`, whose key read is the same as `i1`'s, is not a consumer, and `PBEKeySpecSpec.f1`/`f2`, which report `FORB` on the spec they construct, do not mark it.

`SecureRandomSpec` and `KeyGeneratorSpec` do not mark (decision of 2026-09-15). A `SecureRandom` of a refused algorithm, and the arrays `SecureRandomSpec` discards in `@fail`, would be marked by a sequence failure or by the discard itself, which mixes the order channel into the origin channel; the discard is also an open defect of the specification's wiring that a label would hide. No cascade measured on a complete campaign starts at either specification. Consequently the `RANDOMIZED` readers (`IvParameterSpec`, `GCMParameterSpecSpec`, `PBEKeySpecSpec`, `SecureRandomSpec.setSeed2`/`c2`, the `SecureRandom` argument of `SSLContextSpec.init`) keep their `not-observed` codes and are not consumers of the mark.

The mark is written with `ensure` and read with `validateAny`; the census of the predicate-graph gate (`tests/parity/test_gh105_predicate_gates.py:1362-1395`) moves by the number of new sites and SHALL be restated with them.

#### Scenario: a refused salt is reported once as not observed and then as refused

- **WHEN** an application builds `new PBEKeySpec(pw, storedSalt, 100000, 256)` from a salt read from storage, derives `k = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256").generateSecret(spec)`, and calls `cipher.init(1, new SecretKeySpec(k.getEncoded(), "AES"), iv)`
- **THEN** `PBEKeySpecSpec.c1` MUST report `PBEKEYSPEC-NOBS-01` (label `not-observed`)
- **AND** `SecretKeyFactorySpec.gen`, `SecretKeySpecSpec.c1` and `CipherSpec.i2` MUST each report their `upstream-refused` code
- **AND** none of those three MUST report its `not-observed` code for this chain

#### Scenario: an unmarked unknown object is still not observed

- **WHEN** `cipher.init(1, key)` is called with a key the store has no entry of any kind for
- **THEN** `CipherSpec.i2` MUST report `CIPHER-NOBS-00` with label `not-observed`

### Requirement: Evidence Keys of a Non-Observation Report

Every `-NOBS-` report of `jca_android`, of any label, SHALL append after `msg` the evidence key the specification can compute for the bound object (INV-INS-166): `vfp='sha256:<16 hex>'`, the first eight bytes of the SHA-256 of the bytes, when the bound object is a `byte[]`; `vcls='<binary class names>'`, the comma-joined runtime classes of the elements in array order, when the bound object is a `TrustManager[]`. No other bound object carries evidence, and a `null` bound object carries none (decision of 2026-09-15). The helper that computes them, `br.unb.cic.mop.eh.Evidence.keysFor(Object)`, lives in `rvsec-core` and is called from the specification bodies; it is not named `suffix`, a reserved token of the JavaMOP grammar that a `.mop` cannot use as a method name.

The keys exist so that an analysis can triage non-observation reports without reading source: a fingerprint that is identical across independent installations points to a value embedded in the application, and an application-defined manager class points to a manager worth reading. Neither key decides anything, and the collector's dedupe identity (`ErrorSummary`: spec, error type, class, method, location, code, event) does not include the message, so a device logs the evidence of the first report of each identity per process.

#### Scenario: a constant key material carries a stable fingerprint

- **WHEN** `new SecretKeySpec(new byte[]{1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16}, "AES")` draws `SECRETKEYSPEC-NOBS-00`
- **THEN** the envelope MUST end in `msg='…' vfp='sha256:<h>'` where `<h>` is the first 16 hex digits of SHA-256 over those 16 bytes, with no `vcls`
- **AND** the same value in another process MUST yield the same `<h>`

#### Scenario: evidence never follows another family

- **WHEN** the message gate scans `jca_android/*.mop`
- **THEN** every site that appends `vfp` or `vcls` MUST emit a `-NOBS-` code
- **AND** no guard, transition or `ensure`/`validate` call MUST read the evidence helper's result

### Requirement: RSA Key Sizes Follow the Sibling Expert Rule

`RSAKeyGenParameterSpecSpec.mop` SHALL admit the RSA key sizes `{2048, 3072, 4096}` (INV-INS-167). The pinned expert rules disagree with each other about the same key: `RSAKeyGenParameterSpec.crysl:15` lists `{1024, 2048, 4096}` and `KeyPairGenerator.crysl:29` lists `{4096, 3072, 2048}`. Transcribed literally, an application that calls `initialize(1024)` is reported and one that calls `initialize(new RSAKeyGenParameterSpec(1024, F4))` is not, while a 3072-bit key — 128-bit security against 112 for 2048 and 80 for 1024 in NIST SP 800-57 Part 1 — is reported through the second route. The transcription follows the evident intent under the D-20.4 precedent (`data/jca_android/divergence_record.csv:31`, where `p >= 1^2048` was transcribed as a bit length): the value set comes from the same experts' sibling rule, the normative source is cited as support, and the pinned rule is not edited (D-21).

`divergence_record.csv:376` is already the `oracle-wart` row for the two clauses and records that neither is edited; it SHALL be rewritten in place to record the alignment, citing both expert clauses, the NIST reference and D-20.4. Row `:269`, which says 1024 stays in the list, SHALL gain an addendum, and `conformance_record.csv` SHALL gain the key-size row.

#### Scenario: 3072 is admitted and 1024 is reported

- **WHEN** an application constructs `new RSAKeyGenParameterSpec(3072, RSAKeyGenParameterSpec.F4)`
- **THEN** `RSAKeyGenParameterSpecSpec.c1` MUST NOT report `RSAKEYGENPARAMETERSPEC-KEYSIZE-00`
- **AND** `new RSAKeyGenParameterSpec(1024, RSAKeyGenParameterSpec.F4)` MUST report it with `val='1024'`

## MODIFIED Requirements

### Requirement: Violation Report Message Envelope

Every report site in `jca_android` SHALL call the four-argument `ErrorDescription` constructor, and the fourth argument SHALL be a v1 envelope:

```
v=1 code=<SPEC>-<KIND>-<NN> ev=<event> obj=<SimpleClass> val='<observed>' exp='<expected>' msg='<free text>'[ vfp='<fingerprint>'][ vcls='<class>']
```

`code` is the failure identifier of the site: in a `@fail` handler, `<SPEC>-ORDER-00` and, where the specification carries them, the label codes `creation-unobserved`, `creation-refused` and `reuse-after-final` of the same family; at a value or predicate site, one code per site and label (Requirement: Label Codes of the Successor Specification Set). Every code is listed in `jca_android/codes.csv` with its `label` and cross-checked by the message-property gate; `ev` is the name of the event that fired, obtained from the `__EVENTNAME` macro the generator expands (INV-INS-120); `obj` is the simple class of the monitored object; `val` and `exp` carry the observed and the expected value, both quoted with `'`, a literal `'` escaped as `\'`; `msg` is the human sentence. The optional evidence keys `vfp` and `vcls` follow `msg`, in that order, only in a `-NOBS-` envelope (INV-INS-166); they sit after `msg` so that every reader that locates `code`, `ev`, `val` and `exp` by position or by a leading-key pattern (`ErrorDescription.java:63-65`, `scripts/gh104_diff_harness.py:64`) is unaffected. There is no `st=` field: state indices are assigned after minimisation and do not follow declaration order, so a spec-side state name would be silently wrong. Commas are allowed inside values (27 % of today's messages contain them and every consumer rejoins field 7); `\n` and `:::` are not, because the first splits the logcat line and the second is the separator of `unique_msg`. Truncation is the consumer's problem to detect: the producer bounds `val` to 512 characters and the parser treats an unclosed quote as a truncated record.

`ErrorType` (`rvsec-core/.../eh/ErrorType.java`) SHALL gain `ForbiddenMethod`, with the `code` prefix `FORB` in `codes.csv`. A CrySL `FORBIDDEN` clause is not a predicate — it names a constructor or method that must never be called at all — and the set already encodes two of them, at `PBEKeySpecSpec.mop:24,30`, where they are reported as `InvalidSequenceOfMethodCalls`. That type says the calls arrived in the wrong order, which tells the developer to reorder something that no reordering can fix. `RequiredPredicate` SHALL NOT be added: `REQUIRES` clauses are what INV-INS-128 removes from this set, and an `ErrorType` no site can emit is a promise the enum makes and the specifications break.

The 16 sites whose message reads `but found` and interpolates a monitor field (`currentAlgorithmInstance`, `currentTransformation`, `currentKSType`, `currentProtocol`, `algorithm`) SHALL interpolate instead the value read from the target object the reporting event binds — `getAlgorithm()` on `Cipher`, `KeyGenerator`, `KeyPairGenerator`, `Mac`, `MessageDigest`, `Signature`, `KeyManagerFactory`, `TrustManagerFactory`; `getType()` on `KeyStore`; `getProtocol()` on `SSLContext` — because none of those events binds the algorithm, type or protocol argument (only the `getInstance` events do; `SecureRandomSpec.mop:82`, in `g4`, already interpolates its argument and stays). The field is empty until an instantiation event writes it in the same parameter slice, which is the mechanism behind the 8,843 empty labels; the getter has no such gap. The guard of those sites, however, still tests the field (`MessageDigestSpec.mop:68`, `CipherSpec.mop:59`, `SignatureSpec.mop:56`, `SSLContextSpec.mop:56`, `TrustManagerFactorySpec.mop:55`, and the same shape in `KeyManagerFactory`, `Mac`, `KeyStore`, `KeyGenerator`): for an object whose `getInstance` was never observed — a digest obtained through `clone()`, a factory built before instrumentation attached — the guard fires on `""` and the envelope reads `val='SHA-256' exp='…SHA-256…'`, a report that contradicts itself. The message contract declares that case rather than repairing it: each such site has a row in `data/jca_android/conformance_record.csv` and one harness trace with no observed `getInstance`, and the message-property gate and the harness report flag every envelope whose `val` is a member of `exp` as a **self-contradicting envelope**. Moving the guard to the bound argument or the getter changes what is accused, so it is a measured repair of the automata group, accepted only where the harness classes exactly the traces with no observed `getInstance` as `removed`.

Message text SHALL agree with the check that guards it (INV-INS-121). The census this contract starts from — measured on the frozen `jca`, carried into `jca_android` by the seed — is: `PBEKeySpecSpec.mop:50` and `PBEParameterSpecSpec.mop:50` say `1000` where the condition tests `10000`, and the api30 `PBEKeySpec` rule agrees with the condition at `>= 10000`; `PBEParameterSpecSpec.mop:49` reports `UnsafeAlgorithm` for an iteration-count constraint and MUST report `UnsatisfiedConstraint`; `PBEKeySpecSpec.mop:24,30` report `InvalidSequenceOfMethodCalls` for a forbidden constructor and MUST report `ForbiddenMethod`; `SecretKeySpecSpec.mop:48,55` report `UnsatisfiedConstraint` for half an algorithm test; `MessageDigestSpec.mop:70,92` list three algorithms where the allow-list at `:16` has six (the commented report at `:57-58` is not a live site: reviving it adds an accusation on every `getInstance(String)` outside the list, so it is a measured repair of the automata group, expected class `introduced`, and not part of the message repair — which leaves 50 live sites of the 51 `new ErrorDescription(` occurrences); `CipherSpec.mop:61,76` name two accepted transformations and elide the rest with a literal `...`; `KeyGeneratorSpec.mop:64` and `KeyStoreSpec.mop:68` lack the space after `expecting one of`; `MacSpec.mop:62` lacks the verb; `SecretKeySpecSpec.mop:49` says `keyMaterial.length is not randomized` where `:46` tests the array; `KeyPairGeneratorSpec.mop:71-72` is unreachable because `validate()` returns `false` for every algorithm outside its `switch`; leading spaces at `MacSpec.mop:50`, `KeyManagerFactorySpec.mop:55`, `KeyPairGeneratorSpec.mop:72`, `SecretKeySpecSpec.mop:49,56`; and `ErrorDescription.toString()` (`:143`) prefixes `expecting`, so a consumer of `toString()` sees it twice in front of a message that itself starts with `expecting` — the logcat collector emits `getErrorSummary()+","+getExpecting()` (`ErrorCollector.java:38`) and `errors.csv` carries the envelope as written, so the duplication is recorded as a `toString()`-only artefact and is not a rule on `msg`, whose `expecting one of … but found …` idiom stays. Correcting these is a precondition of the envelope, not a consequence: an envelope around a lying sentence certifies the lie with a `code`.

#### Scenario: a `@fail` handler names its event

- **WHEN** `jca_android/TrustManagerFactorySpec` reaches `fail` on event `init` after `g1` and `g2` were never seen
- **THEN** the report's message MUST be `v=1 code=TRUSTMANAGERFACTORY-ORDER-01 ev=init obj=TrustManagerFactory val='' exp='' msg='init() before getInstance()'` (free text as authored), `TRUSTMANAGERFACTORY-ORDER-01` being the code labelled `creation-unobserved` because no creation event was observed on the monitor
- **AND** the record's `error_type` MUST be `InvalidSequenceOfMethodCalls`
- **AND** the envelope MUST be composed before `__RESET` runs

#### Scenario: a value site interpolates the getter of the bound object

- **WHEN** `jca_android/TrustManagerFactorySpec` reaches event `init` (binding `mf`) on a factory obtained through `getInstance("SunPKIX")` — a value in neither the expert clause nor the alias table; `SunX509`, the value the seed's version of this scenario used, is an expert entry and under D-15 is no longer a misuse — the report site of the specification (`TrustManagerFactorySpec.mop:55-57` in the seed: `g3` at `:44-49` only writes the field, `init` reports)
- **THEN** the message MUST be `v=1 code=TRUSTMANAGERFACTORY-ALG-01 ev=init obj=TrustManagerFactory val='SunPKIX' exp='PKIX,SunX509' msg='expecting one of PKIX,SunX509 but found SunPKIX'`
- **AND** `val` MUST come from `mf.getAlgorithm()`, never from `currentAlgorithmInstance`
- **AND** `exp` MUST be the transcribed expert list joined with `,`, so the message and the allow-list cannot drift apart
- **AND** whether the report moves from `init` to `g3` is not decided by the message repair — it is the broadcast-event question measured in the automata group

#### Scenario: a forbidden constructor reports as forbidden

- **WHEN** `jca_android/PBEKeySpecSpec` fires the site at `:24`, which today reports `InvalidSequenceOfMethodCalls`
- **THEN** the record's `error_type` MUST be `ForbiddenMethod` and the envelope's `code` MUST carry the `FORB` prefix
- **AND** `ErrorType` MUST NOT contain `RequiredPredicate`, since no site of the set can emit it

#### Scenario: no three-argument site remains

- **WHEN** the message-property gate scans `jca_android/*.mop`
- **THEN** it MUST find zero `new ErrorDescription(` calls with three arguments (the frozen `jca` has 25: 21 `@fail` blocks, `IvParameterSpec.mop:48,55`, `PBEKeySpecSpec.mop:24,30`)
- **AND** every `code` it finds MUST exist in `codes.csv`, and every `codes.csv` row MUST be emitted by exactly one site
- **AND** every `codes.csv` row MUST carry a `label` from the closed vocabulary of INV-INS-164 that agrees with the code's family

#### Scenario: a numeric literal disagrees with its guard

- **WHEN** a message says `>= 1000` and the `condition()` guarding it tests `< 10000`
- **THEN** the message-property gate MUST fail naming the file, the line and the two literals

#### Scenario: a self-contradicting envelope is flagged

- **WHEN** the harness replays a trace of `MessageDigestSpec` whose digest was obtained through `clone()` and no `getInstance` was observed, and the `update` site reports `val='SHA-256' exp='MD5,SHA-224,SHA-256,SHA-1,SHA-512,SHA-384'`
- **THEN** the harness report MUST flag the envelope as `self-contradicting` because `val` is a member of `exp`, and the message-property gate MUST flag any site whose guard tests a monitor field while its `val` reads a getter of the bound object
- **AND** the site MUST have a row in `data/jca_android/conformance_record.csv` declaring the case, and the envelope itself MUST NOT be rewritten by the message repair — the guard change is measured in the automata group

#### Scenario: evidence keys follow `msg` in a non-observation envelope

- **WHEN** `SecretKeySpecSpec.c1` reports `SECRETKEYSPEC-NOBS-00` for a 16-byte array
- **THEN** the envelope MUST be `v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='AES' exp='…' msg='…' vfp='sha256:<16 hex>'`
- **AND** `ErrorDescription` MUST still extract `code=SECRETKEYSPEC-NOBS-00` and `ev=c1`

### Requirement: The Java SE Specification Set Is Frozen

The `jca` specification set, together with the `CipherTransformationUtil` its `CipherSpec` delegates to, SHALL remain byte-identical to its state at commit `7e7acb69`. A specification set that has produced published measurements is an experimental instrument, and altering it retroactively invalidates the reproduction of every result computed with it.

Corrections to the platform-independent portion of a specification — an event binding, a pointcut signature, membership of an event in its own automaton, a handler, a report message, or an allow-list — SHALL therefore be applied to a set other than `jca`, even though the same defect is present in `jca`: the derived set under gh101, now archived as `jca_android_bug_predicate`, and the successor set `jca_android` under the legible-report programme. Each such correction SHALL be entered in that set's divergence record naming the hunk, the reason, and the task that introduced it. Divergence between the sets outside allow-lists is the expected outcome; divergence that is not recorded is not.

Two consequences SHALL be carried in the change's records rather than left to be inferred. The `jca` set knowingly retains its defects and the spurious reports they produce, so results measured under it are reproducible without being correct. And a difference in outcome between `jca` and any other set can no longer be attributed to the platform allow-list alone, because it may equally arise from a repair present in one set only; no measurement separates the two contributions after the fact. `jca_android` widens that gap deliberately — it changes allow-lists, messages, automata and the predicate regime at once — so every comparison against it MUST name which of those it is attributing the difference to, and the differential harness exists to make that attribution per trace rather than per campaign.

The freeze governs what the instrument **states** — the specifications and the transformation tables the frozen `CipherSpec` delegates to — and not the runtime it executes on, and not the monitor a `.mop` generates. Reproducing a published measurement is done by pinning the toolchain, and the pin SHALL name the **JDK**: the state numbering a generated monitor carries depends on the JDK that ran the generation, because the ERE-to-FSM conversion of the logic repository returns its states in a different order, so a monitor regenerated under a different JDK is isomorphic to the frozen control — same automaton, same verdicts, different state labels — and not byte-identical to it. Any diff of a regenerated monitor against an existing control MUST therefore name the JDK that produced the control (`data/gh104/evidence/g_regeneration.md`), and a gate MUST NOT read a raw state number as an identity. Additive changes to shared Java are admissible where the frozen set cannot observe them at all: a new `Property` constant that no `jca` specification references, or a new class that no `jca` specification imports, leaves the frozen set's generated monitor unchanged. The new transformation utility `jca_android/CipherSpec.mop` names is admissible on exactly this ground: it is a new class in `rvsec-core/src/main/java/br/unb/cic/mop/jca/util/` that neither `CipherTransformationUtil` nor `AndroidCipherTransformationUtil` is edited to accommodate, and that no `jca` specification imports. The alias utility of INV-INS-127 is admissible on the same ground and for the same reason.

A **repair to shared runtime code the frozen set does reference** is also admissible, under two conditions and not otherwise. The repair MUST apply identically to both sets — shared code MUST NOT branch on the active specification set, because that would place the frozen set's verdict under state set outside its own specification, which is the hazard INV-INS-112 exists to prevent. And its effect on the frozen set MUST be enumerated site by site in the change's records rather than assumed absent, unless the researcher declares it as a count discontinuity instead, as for the weaver repairs below (decision of 2026-09-15). A defect in the machinery is not made correct by having been present when a measurement was taken, and a rule forbidding its repair would forbid repairing the weaver as well. The legible-report programme makes four such repairs that change what a `jca` run executes — the collector's escaping and null sentinel (`ErrorCollector`), the `ViolationRecorder` frame filter that fills `location`, the lock framing of the generated dispatcher (INV-INS-129), and the `ErrorSummary` dedupe identity — and enumerates their effect on `jca` in its records, in the consumer-matrix task of the transport group; the five weaver repairs of gh114 — positional arity, framework subtypes, branch targets, nested types and after-finally (INV-INS-159 to INV-INS-163) — change what a `jca` run executes and are declared as a count discontinuity, not enumerated; and the dedupe identity changes what `jca` reports and is declared as a count discontinuity, not hidden.

The distinction is between a correction of what counts as a misuse, which is confined to a non-frozen set, and a correction of the mechanism that decides it, which is not confinable and is therefore recorded.

#### Scenario: Correction reaches the frozen set

- **WHEN** a layer-2 correction is applied to a file under `jca/`, or to `CipherTransformationUtil.java`
- **THEN** the freeze check MUST fail against the base commit
- **AND** the correction MUST be moved to a non-frozen set, however clearly it repairs a real defect

#### Scenario: Correction does not land in the archived derived set

- **WHEN** a binding defect present in `jca` and in `jca_android_bug_predicate` is corrected
- **THEN** the correction MUST land in `jca_android`, never in the archived directory, which receives no repair from this contract
- **AND** the freeze check MUST pass and both `jca/` and `jca_android_bug_predicate/` MUST stay byte-unchanged
- **AND** both MUST retain the defect, recorded as knowingly retained

#### Scenario: Correction lands in the derived set

- **WHEN** a report message of `jca` is rewritten in `jca_android` only
- **THEN** the freeze check MUST pass
- **AND** `data/jca_android/divergence_record.csv` MUST gain an entry naming the hunk and the reason
- **AND** the `jca` set MUST keep emitting `unknown` at that site, recorded as knowingly retained

#### Scenario: Divergence appears without a record entry

- **WHEN** the two sets differ outside allow-list content in a hunk that no divergence-record entry names
- **THEN** the check MUST fail
- **AND** the hunk MUST either gain an entry with its reason or be reverted

#### Scenario: Shared Java gains a symbol the frozen set cannot observe

- **WHEN** `rvsec-core/src/main/java/br/unb/cic/mop/jca/util/` gains the transformation utility `jca_android/CipherSpec.mop` names, and no `jca` specification imports it
- **THEN** the freeze check MUST pass
- **AND** the monitor generated from the `jca` set MUST be unchanged, which is what makes the addition admissible
- **AND** `CipherTransformationUtil.java` and `AndroidCipherTransformationUtil.java` MUST both be byte-unchanged

#### Scenario: Shared runtime code the frozen set references is repaired

- **WHEN** a defect is corrected in runtime code that specifications of both sets execute — the collector's escape and null sentinel, the `ViolationRecorder` frame filter, the generated dispatcher's lock framing, or the `ErrorSummary` identity
- **THEN** the repair MUST apply identically to both sets, with no branch on the active specification set
- **AND** the four sites and their effect on a `jca` run MUST be enumerated in the change's records — a `jca` message with a comma or newline now arrives intact instead of splitting the line; a `jca` report whose frame is in the monitor now carries the application frame as `location`; a `jca` handler that throws now releases the lock instead of converting the run into a busy-wait; a `jca` record's `unique_msg` now has seven parts and the counts are discontinuous with the baseline — and the consumer-matrix task of the transport group records them
- **AND** the freeze check passing MUST NOT be reported as evidence that the frozen set's behaviour is unchanged

## REMOVED Requirements

### Requirement: Arity Mismatch Is Measured, Not Filtered, in Wrapper Grouping

**Reason**: The requirement published the arity counter before any filter, so that a filter could be judged against its number. The judgement has been made: a complete campaign attributed 25.5 % of its report lines to the double fire this counter measures, and the requirement's own text recorded the binding-form check in `PointcutMatcher` as the root fix. `Positional Arity Is Enforced in Pointcut Matching and Wrapper Grouping` replaces it; the counter survives there with the same name and unit, now counting excluded pairs. The tests that pin the measure-only behaviour (`WrapperMergeTest.anArityIncompatibleAdviceIsCountedAndStillFires`, `PointcutMatcherArgsTypeTest.bindingOnlyArgsAlwaysMatchesRegardlessOfActualArity`, `wildcardAndRestOnlyArgsHaveNoTypeConstraint`) are deleted and replaced, not kept beside the new ones.
