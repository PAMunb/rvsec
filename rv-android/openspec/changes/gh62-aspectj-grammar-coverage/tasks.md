# Tasks: gh62-aspectj-grammar-coverage

<!-- This change is documentation + a new Maven test-only submodule + a CI gate.
     No Python module is touched. No production parser/matcher/emitter source code
     changes (only a pom.xml smali property bump under §0).
     Execution order: smali bump (0) -> ledger draft (1) -> matrix scaffold (2) ->
     grammar-tests Maven module (3) -> per-designator test classes (4) ->
     matrix population (5) -> integrity tests + CI gate (6) -> archive (7).
     All sibling-repo paths are under
     /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-instrumentation-dexlib2/. -->

## 0. Dependency bump: `smali-dexlib2` 3.0.8 → 3.0.9 (isolated commit, gate the matrix work)

**Goal**: bump the smali property in `pom.xml` before any matrix or grammar-tests work so all subsequent test FQNs and API anchors evaluate against the latest published version (per design.md D5). Gate the bump on `mvn package` AND a `dexdump` behavioural diff over 5 APKs from the INV-INS-31 baseline.

- [ ] 0.1 Verify latest published version against `https://maven.google.com/com/android/tools/smali/group-index.xml` — confirm `3.0.9` is the latest `smali-dexlib2` and `smali-baksmali` listed and that `3.0.10` is not present (which would change this decision).
- [ ] 0.2 Edit `rvsec-android/rvsec-instrumentation-dexlib2/pom.xml:32`: `<smali.version>3.0.8</smali.version>` → `<smali.version>3.0.9</smali.version>`. No other change in this commit.
- [ ] 0.3 Run reactor build `cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-instrumentation-dexlib2 && mvn -DskipTests=false package`. ALL existing modules SHALL build SUCCESS with 0 failures and 0 test regressions. If any module fails: capture the failure, REVERT step 0.2 in the same session, and open a separate `chore(deps)` issue capturing the regression; gh62 proceeds against 3.0.8.
- [ ] 0.3a **Behavioural diff (added per Opus47 review M6)**: pick 5 APKs from the INV-INS-31 wrappers-substituted baseline (`MEMORY.md → project_gh52_smoke5_newdata_results`). Pre-bump (HEAD with 3.0.8): build `instr-cli.jar`, instrument the 5 APKs, run `dexdump -d classes.dex` over the output, capture stdout. Post-bump (HEAD with 3.0.9): repeat. `diff` the pre/post stdout per APK. Trivial divergences (e.g. ordering of debug info entries that are structurally equivalent) are acceptable; any non-trivial divergence (different opcode emission, different register usage, different try-catch ranges) REVERTS step 0.2 and tracks a separate `chore(deps)` issue.
- [ ] 0.4 Run `javap` against the resolved 3.0.9 jar to confirm the API surfaces gh61 + future closures depend on are present. Verify at minimum: `MutableMethodImplementation` (constructors taking `int` and `MethodImplementation`; methods `newLabelForIndex`, `addCatch`), `DexPool.writeTo(String, DexFile)`, `DexBackedDexFile.fromInputStream`, payload classes (`PackedSwitchPayload`, `SparseSwitchPayload`, `ArrayPayload`). Document the verified signatures in `docs/aspectj_grammar_coverage.md` header (task 2.1).
- [ ] 0.5 Commit on `origin/modules`: `chore(gh62): bump smali-dexlib2 3.0.8 -> 3.0.9 (mvn package + dexdump diff PASS on 5-APK baseline)` with `refs #62`. Push.

## 1. Ledger first (schedules the work this change unblocks)

**Goal**: produce `openspec/changes/gh62-aspectj-grammar-coverage/ledger.md` before populating the matrix, so the bucket assignments inform which `SILENT-GAP` rows are urgent enough to validate carefully in §5.

- [ ] 1.1 Read `docs/analise_codex_gpt5_gh62.md`, `docs/analise_deepseek-v4-flash-free.md`, `docs/analise_gemini.md`, `docs/analise_opus47_gh62.md` to enumerate every silent-gap surfaced in the cross-LLM review of gh62's earlier draft. Catalogue per AspectJ designator + modifier + advice form.
- [ ] 1.2 Re-run the demand inventory across `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/{jca,generic,generic_new}/` and `aspect/Coverage.aj`. For each enumerated production write a `java.util.regex.Pattern` that distinguishes pointcut use from method-name use (the earlier draft's 356/158 `get/set` count was a substring grep that mixed both). Record counts per (production, corpus). The patterns inform `DemandCounter` in §6 and are quoted inline in the matrix.
- [ ] 1.3 Draft `openspec/changes/gh62-aspectj-grammar-coverage/ledger.md` with three sections (`## Fix-now`, `## Follow-up`, `## Deferred-by-design`). Each entry: AspectJ designator + sub-semantic (if applicable) + modifier, demand summary, planned sub-change identifier (`gh-XX-<kebab>`) or "deferred", one-paragraph rationale, **`Owner: @user`** (TBD allowed only in `Follow-up`/`Deferred-by-design`), **`Target milestone: vX.Y`** (TBD allowed only in `Follow-up`). Assignment rules per design.md D4: `Fix-now` requires non-zero corpus demand AND owner/milestone; `Deferred-by-design` requires existing `EXPLICIT-NO-OP` evidence or ADR.
- [ ] 1.3a Initial Fix-now bucket (subject to demand verification in §5, baseline counts re-verified 2026-05-25 — entries are scheduled either by non-zero corpus demand OR by structural-parity necessity at zero observed demand): trailing-varargs `(T, ..)` (jca=14, generic_new=4); `T+` in `call()` owner (generic_new=135); `T+` in `call()` return; `execution(...)` real matcher (aspect=1, jca=23, generic_new=27); `BaseAspect.notwithin()` named-ref expansion; **`after() throwing(...)` end-to-end** (re-classified from EXPLICIT-NO-OP — `DexWeaver.java:560-566` is silent, not documented; 2 hits in `generic_new/`); `target(Type)` type-matching; `args(Type)` type-matching; `if(...)` matcher semantic evaluation (aspect=8, jca=16, generic_new=37 — the `IfGuardEmitter` scaffold is wired via `EmitterDispatch.java:70-74` but the matcher remains always-match, so the row is SILENT-GAP at the matcher stage); **`adviceexecution()` real semantics** (parser at `PointcutExpressionParser.java:131` routes to `NamedRefPC` → matcher always-match; jca=1, generic_new=1; previously misclassified as COVERED); **advice-body reflective API: `thisJoinPoint` binding** (generic_new=3) + **`JoinPoint.getSignature()` + `Signature` subtypes** (aspect=8, generic_new=3) — without these the MOP monitor body cannot read the bound call context; sub-rows `getArgs()` / `getTarget()` / `getThis()` / `getKind()` are Fix-now by parity even at zero observed demand because monitors that use one typically use several; **`org.aspectj.lang.JoinPoint` runtime linkage** (prerequisite); **`aspect Foo` declaration syntax** (aspect=1, jca=2, generic_new=2 — the parser must accept this top-level construct); **`pointcut p(): ...` named declaration** (aspect=2, jca=1, generic_new=1 — distinct from named-pointcut reference).
- [ ] 1.3b Initial Follow-up bucket: `get(FieldPattern)`/`set(FieldPattern)` (zero demand after corrected grep, but completeness); `this(name)`/`this(Type)` (zero corpus demand confirmed; no `ThisPC` class — matrix completeness only); `withincode(...)`; `cflow`/`cflowbelow`; `initialization(...)`/`preinitialization(...)`; AspectJ 5 `@*` family (6 designators, zero demand); positive `within(...)` weaver-side filter; `T+` inside `!within(...)`; SignaturePattern modifiers; `thisJoinPointStaticPart` (aspect=1, rarely consumed); `thisEnclosingJoinPointStaticPart` (zero demand — completeness); `JoinPoint.getSourceLocation()` grouped row (zero demand — completeness); aspect inheritance (`aspect Bar extends Foo`); abstract-aspect + concrete subaspect (zero demand today but relevant for future `BaseAspect`-style refactors); privileged aspect; advice forms `before`/`after`/`after returning` are COVERED so don't appear here.
- [ ] 1.3c Initial Deferred-by-design bucket: `around` advice (assertion in `EmitterDispatchTest.java:54-59`); `proceed(...)` keyword in around body (EXPLICIT-NO-OP consistent with `around` itself); `handler(...)` (no DEX-level analogue in scope); `declare precedence` (advice-ordering across aspects — the runtime serializes monitor dispatch in a loop, so ordering is a runtime property, not a weaver property). Note: `lock`/`unlock` are NOT in this bucket because they are NOT matrix rows at all (design.md OQ3 — zero demand AND outside the closed enumeration). Ledger entries map 1:1 to matrix rows; non-rows do not appear in any bucket.
- [ ] 1.4 Commit on `origin/modules`: `docs(gh62): draft scope ledger for AspectJ grammar coverage` with `refs #62`. Push.

## 2. Matrix scaffold (no verdicts yet — structure only)

**Goal**: produce `docs/aspectj_grammar_coverage.md` with the canonical column structure, every required row present (one per item in the closed enumeration declared in the delta spec), and the `DemandCounter` reference. Verdict and evidence columns are filled with `TBD` for now.

- [ ] 2.1 Create `docs/aspectj_grammar_coverage.md` with a header section that cites: the AspectJ Programming Guide §"Pointcuts" URL + snapshot date, the AspectJ 5 quick reference URL (annotation pointcuts are AspectJ 5+), the smali-dexlib2 version verified by §0.4. Document the four-value verdict vocabulary with one-paragraph definitions. State explicitly: `NOT-NEEDED` requires zero `DemandCounter` count AND no parser/matcher/emitter implementation; pure-zero-demand-with-implementation is `COVERED`.
- [ ] 2.2 Add a section "Demand counting" that references `DemandCounter` (in `grammar-tests`) as the source of truth and lists the `java.util.regex.Pattern` per designator (so reviewers can audit the regex without opening Java code). NO inline shell snippet; `MatrixIntegrityTest.testDemandCountsReproducible` invokes the Java helper directly.
- [ ] 2.3 Add the stable anchor heading `## Matrix` followed by the table header with columns `AspectJ syntax | Demand (aspect, jca, generic, generic_new) | Parser | Matcher | Emitter | Verdict | Evidence`.
- [ ] 2.4 Add one row per **classical pointcut designator** in the closed enumeration: `call`, `execution`, `withincode`, `cflow`, `cflowbelow`, `if`, `handler`, `get`, `set`, `staticinitialization`, `initialization`, `preinitialization`, `adviceexecution`, named-pointcut references. Verdict/Evidence = `TBD`. Note: `within`/`!within` are NOT classical here — they live under §2.10 Within-family per-stage delegation, because the dexlib2 pipeline diverges per polarity.
- [ ] 2.5 Add sub-semantic rows for `target`, `this`, `args`:
  - `target(name)` — value binding (receiver register); high demand
  - `target(Type)` — type-matching; SILENT-GAP
  - `this(name)` — value binding; SILENT-GAP (no `ThisPC`)
  - `this(Type)` — type-matching; SILENT-GAP
  - `args(name)` — value binding; COVERED
  - `args(Type)` — type-matching; SILENT-GAP
  - `args(*, name, ..)` — mixed
- [ ] 2.6 Add one row per **AspectJ 5 annotation pointcut designator**: `@annotation`, `@target`, `@this`, `@args`, `@within`, `@withincode`.
- [ ] 2.7 Add one row per **advice form** (not designators): `before`, `after`, `after returning`, `after throwing`, `around`. The `returning(Id)`/`throwing(Id)` advice-binding identifiers are tested via these rows (e.g. `after() returning(name)` binding correctness), not as standalone rows.
- [ ] 2.8 Add rows for **type-pattern modifiers** (with positional sub-rows for `T+` since matcher diverges per position):
  - `T+` in `call()` param
  - `T+` in `call()` owner
  - `T+` in `call()` return
  - `T+` inside `!within(...)`
  - `*` wildcard
  - `..` standalone varargs
  - `..` trailing-mixed `(T, ..)`
  - dot-glob (`..*`)
  - single-level glob (`.*`)
  - arrays (`T[]`, `T[][]`)
  - inner-class qualifier (`Outer.Inner` vs `Outer$Inner`)
- [ ] 2.9 Add rows for **SignaturePattern modifiers**: positive visibility (`public`/`private`/`protected`), negated visibility (`!public`), `static`, `final`, `throws ExceptionPattern`.
- [ ] 2.10 Add rows for **within-family per-stage delegation**: `within(...)` positive (matcher always-match — weaver-side filter required), `!within(...)`.
- [ ] 2.11 Add rows for **composition operators**: `&&`, `||`, `!`, parentheses.
- [ ] 2.12 Add rows for **advice-body reflective API** (behavioural-parity surface):
  - `thisJoinPoint` binding
  - `thisJoinPointStaticPart` binding
  - `thisEnclosingJoinPointStaticPart` binding
  - `JoinPoint.getArgs()`
  - `JoinPoint.getSignature()` + `Signature` subtype accessors (`MethodSignature` / `ConstructorSignature` / `FieldSignature` with `.getName()` / `.getDeclaringType()` / `.getParameterTypes()` / `.getReturnType()`) — single row for the group
  - `JoinPoint.getTarget()` / `JoinPoint.getThis()` — single grouped row
  - `JoinPoint.getKind()` / `JoinPoint.getSourceLocation()` — single grouped row
- [ ] 2.13 Add row for **around-advice mechanics**: `proceed(...)` keyword inside around body. Verdict prediction: EXPLICIT-NO-OP (consistent with `around` itself).
- [ ] 2.14 Add rows for **aspect declaration mechanics**:
  - `aspect Foo { ... }` top-level declaration syntax
  - `pointcut p(): ...` named-pointcut declaration (binding side; reference side is row §2.4 named-pointcut references)
  - abstract aspect + concrete subaspect (`BaseAspect` idiom)
  - aspect inheritance (`aspect Bar extends Foo`)
  - `declare precedence: A, B;`
  - privileged aspect
- [ ] 2.15 Add row for **AspectJ runtime linkage**: `org.aspectj.lang.JoinPoint` class (plus `JoinPoint.StaticPart` and `Signature` subtypes) availability in instrumented bytecode classpath. One row; per-subtype availability is implicit.
- [ ] 2.16 Commit on `origin/modules`: `docs(gh62): scaffold aspectj grammar coverage matrix (closed enumeration, TBD verdicts)` with `refs #62`. Push.

## 3. `grammar-tests/` Maven submodule scaffold

**Goal**: add the new test-only Maven submodule so the matrix's `Evidence` column can cite test FQNs from §5 onwards.

- [ ] 3.1 In `rvsec-android/rvsec-instrumentation-dexlib2/pom.xml`, add `<module>grammar-tests</module>` to `<modules>`. Do NOT add it to the `instr-cli` shade plugin's includes.
- [ ] 3.2 Create `rvsec-android/rvsec-instrumentation-dexlib2/grammar-tests/pom.xml`. Parent: `rvsec-instrumentation-dexlib2`. Test scope deps (pin in parent `dependencyManagement` so versions are explicit, not transitive):
  - `pointcut-engine`, `advice-emitter`, `dex-mutator` (project modules)
  - `org.junit.jupiter:junit-jupiter:5.10.x` (already in BOM)
  - `org.junit.platform:junit-platform-launcher:1.10.x` (NEW — required by `testSkipCountEqualsSilentGapCount` for JUnit Platform discovery via `SummaryGeneratingListener`)
  - `org.commonmark:commonmark:0.24.0` (Java 11+ compatible; 0.28.x requires Java 17 — pin to 0.24.0)
  - `org.commonmark:commonmark-ext-gfm-tables:0.24.0` (Markdown table parsing — the matrix uses GFM tables, the core parser alone does not recognise them)

  No `main/` source directory; only `src/test/java/` and `src/test/resources/`.
- [ ] 3.3 Create the package structure: `grammar-tests/src/test/java/br/unb/cic/rv/grammar/`. Add a package-info.java with a one-paragraph note: this module is the executable oracle for `docs/aspectj_grammar_coverage.md`; tests SHALL be kept in 1:1 correspondence with matrix rows; SILENT-GAP rows MUST be `@Disabled` with the reason `"gh62 SILENT-GAP: <one-line>"`.
- [ ] 3.4 Add `grammar-tests/src/test/java/br/unb/cic/rv/grammar/util/DemandCounter.java` (~80 LOC): `count(designatorPattern, corpusRoot)` walks `corpusRoot` via `Files.walk()`, reads each `.mop` file with `Files.readString()`, applies the compiled `Pattern`, returns the integer match count. `countAll(corpusRoot)` returns `Map<Designator, Map<Corpus, Integer>>`. No `ProcessBuilder`, no shell.
- [ ] 3.5 Add `grammar-tests/src/test/java/br/unb/cic/rv/grammar/util/MatrixMarkdownParser.java` (~50 LOC, on `commonmark-java`): locates the table immediately following the literal heading `## Matrix` in `docs/aspectj_grammar_coverage.md`; parses each row into `record MatrixRow(String syntax, Map<Corpus,Integer> demand, String parserAnchor, String matcherAnchor, String emitterAnchor, Verdict verdict, String evidence)`. Throws if the anchor is absent or duplicated.
- [ ] 3.6 Add `grammar-tests/src/test/java/br/unb/cic/rv/grammar/util/AspectJDesignators.java` — a `Set<String> DESIGNATORS` constant naming every entry in the closed enumeration declared in the delta spec. Source of truth for `MatrixIntegrityTest.testEveryDesignatorHasMatrixRow`. The set MUST include all 8 families enumerated in `specs/instrumentation/spec.md`: classical pointcut designators (incl. `target`/`this`/`args` sub-semantics), AspectJ 5 `@*` family, advice forms, type-pattern modifiers, signature-pattern modifiers, within-family delegation, composition operators, **advice-body reflective API (F1)**, **around-advice mechanics (F2 = `proceed(...)`)**, **aspect declaration mechanics (F3)**, **AspectJ runtime linkage (F4)**.
- [ ] 3.7 Add a smoke test `MavenModuleSmokeTest` that asserts `true`. Required to keep the reactor green between commits.
- [ ] 3.8 Run `cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-instrumentation-dexlib2 && mvn -pl grammar-tests test -DskipTests=false -am`. Smoke test SHALL pass. Reactor `mvn package` from the same root SHALL build SUCCESS for all modules including the new one.
- [ ] 3.9 Commit on `origin/modules`: `feat(gh62): add grammar-tests Maven submodule (scaffold + DemandCounter + MatrixMarkdownParser + smoke)` with `refs #62`. Push.

## 4. Per-designator grammar test classes

**Goal**: one test class per matrix row group, every method's Javadoc cites the matrix row by AspectJ syntax. Method bodies are stubbed with `// TODO matrix row X.Y` until §5 populates verdicts; `@Disabled` is applied for any row whose stub assertion fails today (most `SILENT-GAP` rows).

- [ ] 4.1 Add `CallPointcutGrammarTest`. Test methods: `callExactDescriptorMatch`, `callWildcardStarInName`, `callDotDotStandaloneParams`, `callTrailingVarargsMixedParams`, `callTSubtypeInParam`, `callTSubtypeInOwner`, `callTSubtypeInReturnType`.
- [ ] 4.2 Add `ExecutionPointcutGrammarTest`. Test methods: `executionExactSignature`, `executionWildcardName`. Most `@Disabled` (`PointcutMatcher.matchExecution:307-313` is placeholder).
- [ ] 4.3 Add `TargetGrammarTest`. Methods: `targetNameBinding` (COVERED via `buildCallMatch`), `targetTypeFiltering` (`@Disabled` — `PointcutMatcher.java:106-108` always-match).
- [ ] 4.4 Add `ThisGrammarTest`. Methods: `thisNameBinding` (`@Disabled` — no `ThisPC`), `thisTypeFiltering` (`@Disabled`).
- [ ] 4.5 Add `ArgsGrammarTest`. Methods: `argsNameBinding` (COVERED), `argsTypeFiltering` (`@Disabled`), `argsMixedWildcardAndBind` (`@Disabled`).
- [ ] 4.6 Add `WithinFamilyGrammarTest`. Methods: `withinPositiveAlwaysMatch_weaverFiltersExpected` (`@Disabled` — matcher always-match; weaver does NOT filter; SILENT-GAP for positive `within()`), `notWithinExactMatch` (COVERED after gh61 Group B), `notWithinTPlusInsideStripsToExactMatch` (`@Disabled` — `matchesTypePattern` strips `+` and does exact match; new gap exposed by Deepseek review).
- [ ] 4.7 Add `CflowGrammarTest`. Methods: `cflow`, `cflowbelow`. Both `@Disabled` (Follow-up; no JCA/generic demand).
- [ ] 4.8 Add `IfGrammarTest`. Methods: `ifSemanticEvaluation` (`@Disabled` — matcher at `PointcutMatcher.java:109-114` is always-match; `IfGuardEmitter` is wired via `EmitterDispatch.java:70-74` but performs no boolean evaluation; aspect=8, jca=16, generic_new=37 → Fix-now).
- [ ] 4.9 Add `HandlerGrammarTest`. Method `handlerExceptionType` (`@Disabled` — Deferred-by-design).
- [ ] 4.10 Add `FieldAccessGrammarTest`. Methods: `getField`, `setField`. Both `@Disabled` (SILENT-GAP, zero corrected-demand → Follow-up).
- [ ] 4.11 Add `StaticInitializationGrammarTest`. Method: `staticinitializationTSubtype` — COVERED (`PointcutMatcher.matchStaticInit:315-327`).
- [ ] 4.12 Add `InitializationGrammarTest`. Methods: `initializationConstructor`, `preinitializationConstructor`. Both `@Disabled`.
- [ ] 4.13 Add `AdviceExecutionGrammarTest`. Method: `adviceExecutionSemanticMatch` — `@Disabled` SILENT-GAP. Reason: `PointcutExpressionParser.java:131` routes `adviceexecution` to `NamedRefPC`, which `PointcutMatcher.java:109-114` treats as always-match — there is no real semantic match against advice-execution join points. The test body asserts the correct AspectJ semantics (advice-execution join point is reached only inside advice bodies); fails today because matcher matches every join point indiscriminately. Demand: jca=1, generic_new=1 → Fix-now bucket.
- [ ] 4.14 Add `NamedReferenceGrammarTest`. Methods: `namedRefAlwaysMatch` (COVERED for the project's current use), `baseAspectNotWithinExpansion` (`@Disabled` SILENT-GAP).
- [ ] 4.15 Add `AnnotationPointcutGrammarTest` (NEW per cross-LLM review). Methods: `annotationAtAnnotation`, `annotationAtTarget`, `annotationAtThis`, `annotationAtArgs`, `annotationAtWithin`, `annotationAtWithincode`. All `@Disabled` SILENT-GAP (parser routes all to `NamedRefPC`).
- [ ] 4.16 Add `AdviceFormGrammarTest` (NEW per cross-LLM review). Methods: `beforeAdvice` (COVERED via `BeforeEmitter`), `afterAdvice` (COVERED with weaver-side ressalva — see Deepseek analysis), `afterReturningAdvice` (COVERED via `AfterReturningEmitter`), `afterThrowingAdvice` (`@Disabled` SILENT-GAP — `DexWeaver.java:560-566` discards the plan silently), `aroundAdvice` (EXPLICIT-NO-OP — `EmitterDispatch.java:61-65` throws `UnsupportedOperationException`, asserted in `EmitterDispatchTest.java:54-59`), `aroundProceedSemantics` (EXPLICIT-NO-OP for the `proceed(...)` keyword — same `UnsupportedOperationException` path is reached before any `proceed` token would matter; one extra method here avoids creating a standalone `ProceedGrammarTest` for a single row).
- [ ] 4.17 Add `TypePatternGrammarTest`. Methods covering `*` in name pattern, `..` in package pattern, dot-glob, single-level glob, arrays, inner classes.
- [ ] 4.18 Add `SignatureModifierGrammarTest` (NEW per cross-LLM review). Methods: `positiveVisibilityStripped` (COVERED — parser strips), `negatedVisibility` (`@Disabled`), `staticModifier`, `finalModifier`, `throwsExceptionPattern`. Most `@Disabled` SILENT-GAP.
- [ ] 4.19 Add `CompositionGrammarTest`. Methods covering `&&`, `||`, `!`, parens. Most COVERED.
- [ ] 4.20 Add `JoinPointReflectiveApiGrammarTest` (NEW — behavioural-parity surface; the AspectJ contract that advice bodies depend on). Methods: `thisJoinPointBinding`, `thisJoinPointStaticPartBinding`, `thisEnclosingJoinPointStaticPartBinding`, `joinPointGetArgs`, `joinPointGetSignatureAndSubtypes` (asserts `Signature.getName()` / `.getDeclaringType()` / `.getParameterTypes()` / `.getReturnType()` return AspectJ-equivalent values), `joinPointGetTargetAndThis`, `joinPointGetKindAndSourceLocation`, `aspectjRuntimeJoinPointClassPresent` (checks `org.aspectj.lang.JoinPoint` linkage in the instrumented bytecode). Most `@Disabled` SILENT-GAP at gh62 archive; the row verdicts in §5 will confirm against the actual emitter behaviour (audit `BeforeEmitter` / `AfterEmitter` / `AfterReturningEmitter` to see which `JoinPoint` accessors they populate).
- [ ] 4.21 Add `AspectDeclarationGrammarTest` (NEW — aspect declaration mechanics, distinct from pointcut grammar). Methods: `topLevelAspectDeclaration` (parser accepts `aspect Foo { ... }`), `namedPointcutDeclaration` (parser accepts `pointcut p(): ...;` binding side), `abstractAspectAndConcreteSubaspect` (`BaseAspect` idiom — abstract aspect declares the pointcut family, concrete subaspect picks the implementation), `aspectInheritance` (`aspect Bar extends Foo`), `declarePrecedence` (`declare precedence: A, B;` — currently Deferred), `privilegedAspect` (access to private members across types). Verdict mix: `topLevelAspectDeclaration` and `namedPointcutDeclaration` likely COVERED (existing aspect templates parse today); the rest `@Disabled` SILENT-GAP / EXPLICIT-NO-OP per §5 audit.
- [ ] 4.22 Run `mvn -pl grammar-tests test`. All non-`@Disabled` tests SHALL pass; the test report SHALL list every `@Disabled` skip with its `gh62 SILENT-GAP:` reason.
- [ ] 4.23 Commit on `origin/modules`: `test(gh62): per-designator grammar test classes (stubs + @Disabled SILENT-GAP)` with `refs #62`. Push.

## 5. Matrix population (fill verdicts and evidence)

**Goal**: replace every `TBD` in `docs/aspectj_grammar_coverage.md` with a verdict and an evidence anchor. The matrix is now the contract.

- [ ] 5.1 For every row, audit the current dexlib2 source. Cite `file:line` in the `Parser` / `Matcher` / `Emitter` columns. Use the analyses in `docs/analise_*.md` as a starting point; verify every claim against current `HEAD`. Specific corrections from the cross-LLM review:
  - `PointcutMatcher.java:109-114` (not `:109-112`) — the always-match block for `IfPC`/`NamedRefPC`/`WithinPC`.
  - `PointcutMatcher.java:307-313` — `matchExecution` placeholder.
  - `EmitterDispatchTest.java:54-59` (not `:58`) — `aroundAdviceRejected` test.
  - `DexWeaver.java:560-566` (NOT `:534-540` — that's the `MutableImplSupplier` interface) — the `case TRY_CATCH_WRAP: case REPLACE: break;` silent discard. Cite this for `after throwing` row as SILENT-GAP.
  - `PointcutExpressionParser.java:131` — `adviceexecution` routes to `NamedRefPC` (matrix row was previously declared COVERED; correct verdict is SILENT-GAP per the same NamedRefPC-fallback mechanism as the AspectJ 5 `@*` family).
  - `PointcutExpressionParser.java:271-273` (not `:256-258` — that range is `splitParams`, which is split-by-comma logic) — the `isVarargs` check that treats `..` as a sentinel only when isolated. Cite this for the `..` standalone vs `(T, ..)` trailing-mixed split.
  - `EmitterDispatch.java:70-74` — `IfGuardEmitter.wrapping(base)` is wired when the pointcut expression contains `if(`. The emitter pipeline is *present* for `if(...)` even though the matcher remains always-match; the row verdict is still SILENT-GAP (semantic match is the failure mode), but the Emitter column anchors to this line, not to `MISSING`.
- [ ] 5.2 Fill the `Demand` column per row by invoking `DemandCounter.countAll()` (§3.4). Record the integer counts. Cross-check that the regex per designator distinguishes pointcut use from method-name use — the earlier draft's 356/158 `get/set` count was a substring grep error.
- [ ] 5.3 Assign a `Verdict` per row using the four-value vocabulary:
  - `COVERED` iff there is a passing (non-`@Disabled`, including no inherited `@Disabled`) test in `grammar-tests/` exercising the row;
  - `SILENT-GAP` iff there is a `@Disabled` test AND the row appears in the ledger (Fix-now or Follow-up);
  - `EXPLICIT-NO-OP` iff there is a passing test asserting `UnsupportedOperationException` (or equivalent documented assertion) AND the no-op is documented at the cited `file:line`;
  - `NOT-NEEDED` iff `Demand` is 0 across all four corpora AND the row has neither parser nor matcher implementation.
- [ ] 5.4 Fill the `Evidence` column per row: for `COVERED`, the passing test FQN; for `SILENT-GAP`, the `@Disabled` test FQN; for `EXPLICIT-NO-OP`, BOTH the assertion test FQN AND the `file:line` of the no-op declaration; for `NOT-NEEDED`, the `DemandCounter` zero result.
- [ ] 5.5 Cross-check matrix against ledger: every `SILENT-GAP` matrix row MUST appear in exactly one ledger bucket; no ledger entry MUST reference a non-existent row.
- [ ] 5.6 Run `mvn -pl grammar-tests test` again to confirm the matrix's claims (every `Evidence` FQN resolves to an existing test with the expected enabled/disabled status).
- [ ] 5.7 Commit on `origin/modules`: `docs(gh62): populate aspectj grammar matrix with verdicts + evidence` with `refs #62`. Push.

## 6. Integrity tests + CI gates

**Goal**: add `MatrixIntegrityTest` so the matrix↔code↔ledger consistency is enforced at every CI run, per INV-INS-88..93. Closure atomicity is enforced by the bidirectional integrity test (orphan-test and orphan-row detection at commit time); a separate cross-repo PR-check workflow was considered and rejected in design D6.

- [ ] 6.1 Add `MatrixIntegrityTest.testEveryDesignatorHasMatrixRow`: parse matrix via `MatrixMarkdownParser`, assert **set equality** between matrix-row syntaxes and `AspectJDesignators.DESIGNATORS` (both directions — no missing rows, no extra rows). INV-INS-88.
- [ ] 6.2 Add `MatrixIntegrityTest.testVerdictsAreValid`: every row's `Verdict` is exactly one of `{COVERED, SILENT-GAP, EXPLICIT-NO-OP, NOT-NEEDED}`; for `NOT-NEEDED` rows assert demand sum == 0 AND parser/matcher anchors == `MISSING`. INV-INS-89.
- [ ] 6.3 Add `MatrixIntegrityTest.testCoveredRowsCiteEnabledPassingTests`: for every `COVERED` row, resolve the FQN via reflection (`Class.forName` + `Method` lookup); assert the method is annotated with `@Test` and NOT with `@Disabled` (walk the class hierarchy for inherited `@Disabled`). INV-INS-90.
- [ ] 6.4 Add `MatrixIntegrityTest.testSilentGapRowsHaveDisabledTestAndLedgerEntry`: for every `SILENT-GAP` row, (a) resolve the FQN and assert `@Disabled` is present and the reason starts with `"gh62 SILENT-GAP:"`, AND (b) parse the ledger and assert the row's AspectJ syntax appears in exactly one bucket. The ledger path is resolved with active-then-archive fallback: first try `openspec/changes/gh62-aspectj-grammar-coverage/ledger.md`; if absent, glob `openspec/changes/archive/*-gh62-aspectj-grammar-coverage/ledger.md` (post-archive path). After gh62 archive the test continues to pass against the moved ledger; per INV-INS-91 only gh62-time SILENT-GAPs require a ledger entry, so SILENT-GAP rows added in later changes are exempt from the ledger half of this assertion (the test ignores rows whose AspectJ syntax is not present in any bucket *and* was introduced after archive — implemented by snapshotting the ledger's syntax set at test class-init and only enforcing membership for rows in that set). INV-INS-91.
- [ ] 6.5 Add `MatrixIntegrityTest.testEnabledTestsResolveToCoveredOrExplicitNoOpRow` (NEW per cross-LLM review — bidirectional enforcement): enumerate all `@Test` methods in `br.unb.cic.rv.grammar.*GrammarTest` that are NOT `@Disabled`; assert each resolves to exactly one matrix row with `Verdict ∈ {COVERED, EXPLICIT-NO-OP}`. EXPLICIT-NO-OP rows are enabled tests asserting `UnsupportedOperationException` (or equivalent), not `@Disabled`. Orphan enabled tests break the build. INV-INS-92.
- [ ] 6.6 Add `MatrixIntegrityTest.testDisabledTestsResolveToSilentGapRow` (NEW): enumerate all `@Disabled` `@Test` methods in `br.unb.cic.rv.grammar.*GrammarTest`; assert each resolves to exactly one matrix row with `Verdict = SILENT-GAP`. INV-INS-92.
- [ ] 6.7 Add `MatrixIntegrityTest.testSkipCountEqualsSilentGapCount` (NEW): parse the JUnit Platform discovery; assert `(disabled count) == (matrix rows with Verdict = SILENT-GAP)`. A `@Disabled` test that begins to pass silently breaks the build. INV-INS-92.
- [ ] 6.8 Add `MatrixIntegrityTest.testDemandCountsReproducible`: invoke `DemandCounter.countAll($RVSEC_HOME/rvsec/rvsec-mop/src/main/resources)` directly (no `ProcessBuilder`, no shell); diff against the matrix's `Demand` columns; fail with a diff if any cell mismatches. INV-INS-93.
- [ ] 6.9 Run `mvn -pl grammar-tests test`. All 8 integrity tests SHALL pass on the populated matrix.
- [ ] 6.10 Extend `rvsec/.github/workflows/ci.yml`: add a dedicated step `mvn test -pl rvsec-android/rvsec-instrumentation-dexlib2/grammar-tests -DskipTests=false -am` after the existing `maven-build` step. Declare `env: RVSEC_HOME: ${{ github.workspace }}` (or analogous path so `DemandCounter` finds `rvsec/rvsec-mop/src/main/resources/`). The CI step's stdout SHALL print the skipped-test count (number of `SILENT-GAP` rows) for visibility. (Note: the current `ci.yml` builds with `-DskipTests`; this task is to add a step that explicitly enables tests for `grammar-tests` only — not to flip the global build.)
- [ ] 6.11 Commit on `origin/modules`: `test(gh62): MatrixIntegrityTest (bidirectional) + CI step for grammar coverage` with `refs #62`. Push. (The earlier draft proposed a cross-repo `grammar-pr-check.yml` GitHub Action for closure atomicity; rejected in design D6 — `MatrixIntegrityTest` running in CI at commit time enforces the same invariant via orphan-test and orphan-row detection.)

## 7. Cross-Cutting Verification + Archive

- [ ] 7.1 Validate the openspec change: `openspec validate --changes gh62-aspectj-grammar-coverage --strict`. SHALL return PASS.
- [ ] 7.2 Invoke `/rv-code-reviewer` via the Skill tool against the gh62 diff (matrix, ledger, `grammar-tests/` module, CI step in `rvsec/.github/workflows/ci.yml`). Address review findings inline.
- [ ] 7.3 Update `MEMORY.md` with a `project_gh62_grammar_coverage` entry capturing the row count (per category), the SILENT-GAP count by corpus, the initial Fix-now bucket, and the corrected `get/set` demand baseline (zero across all corpora).
- [ ] 7.4 Run `/opsx:verify` against the change.
- [ ] 7.5 Run `/opsx:archive` (`openspec archive gh62-aspectj-grammar-coverage --yes`). Delta spec for `instrumentation` SHALL auto-merge.
- [ ] 7.6 Commit on `origin/modules`: `chore(gh62): archive change (closes #62)`. Push.
- [ ] 7.7 Close issue #62 via `gh issue close 62 --repo PAMunb/rvsec --comment "..."` referencing the matrix, the ledger snapshot, the `grammar-tests/` module, and the `MatrixIntegrityTest` CI gate. Future closures open their own issues and OpenSpec changes when scheduled — the matrix's `SILENT-GAP` rows are the live backlog; no preemptive issue creation.

## 8. Out-of-scope cross-cutting checks

- [ ] 8.1 Confirm no production parser/matcher/emitter source code was modified: `git diff origin/modules~N..origin/modules -- rvsec-android/rvsec-instrumentation-dexlib2/pointcut-engine/src/main/ rvsec-android/rvsec-instrumentation-dexlib2/advice-emitter/src/main/ rvsec-android/rvsec-instrumentation-dexlib2/dex-mutator/src/main/ rvsec-android/rvsec-instrumentation-dexlib2/coverage-weaver/src/main/` SHALL be empty. The only production-tree diff allowed is the one-line `pom.xml` smali bump from task 0.2.
- [ ] 8.2 Confirm `instr-cli.jar`'s observable behaviour is unchanged: re-run a representative subset of the existing per-module test bars (`mvn -pl pointcut-engine test`, `mvn -pl advice-emitter test`, `mvn -pl dex-mutator test`, `mvn -pl coverage-weaver test`) and assert 0 failures vs. the pre-task-0 baseline. The shaded jar's byte hash MAY change (different smali version bytes shipped) — that is expected; the contract being verified is behavioural equivalence, not byte identity. The §0.3a `dexdump` diff is the empirical gate.
- [ ] 8.3 No re-instrumentation of the 190-APK dataset; no Docker image rebuild; no APE experiment re-run. (§0.3a re-instruments 5 APKs for `dexdump` diff only.)
