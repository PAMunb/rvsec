# Tasks: gh62-aspectj-grammar-coverage

<!-- ROUND-8 redesign (2026-05-26 — D9-round-8 absorption-aware demand + D12 path-β verdict + D13 if() runtime delegation; §4.E restored per user decision same day).
     This change is documentation + a new Maven test-only submodule + a CI gate + FOURTEEN
     DEMAND-DRIVEN CLOSURES covering every construction with non-zero PIPELINE-level demand
     (post JavaMOP compilation, post coverage-weaver absorption, post DescriptorReader flattening)
     plus the defensively-shipped §4.E execution(...) closure.
     The matrix archives with ZERO SILENT-GAP rows; seven round-7 closures are reclassified
     NOT-NEEDED β based on the round-8 empirical audits (docs/analise_sintese_macro.md).
     No Python module is touched. NO aspectjlang/ Maven submodule (round-7 plan dropped).

     Production parser/matcher/emitter source code changes (§8.1 has the full
     authoritative file list; sketch below):
       - advice-emitter/: NEW — StaticInitSynthesizer (§4.Y), IfRuntimeDelegationEmitter (§4.I);
         EXTENDED — AfterThrowingEmitter (§4.T), EmitterDispatch (§4.T/I wiring).
       - monitor-builder/: NEW — MonitorRuntimeIfHelperEmitter (§4.I — generates
         *RuntimeMonitor.evaluateIf(int, Object[]) switch-case per spec).
       - pointcut-engine/: NEW — BaseAspectExpander (§4.B); EXTENDED —
         PointcutMatcher (§4.W/O/R/X/D/TT/AT), PointcutExpressionParser (§4.N/V/TT/AT/D),
         WithinPC (§4.W), CallPC (§4.O/R/X/V), TargetPC (§4.TT), ArgsPC (§4.AT),
         NamedRefPC (§4.D/B).
       - dex-mutator/: EXTENDED — DexWeaver (§4.T TRY_CATCH_WRAP install).
       - descriptor-reader/: AspectDescriptor + DescriptorReader extended for
         the per-aspect named-pointcut symbol table (§4.D, D11 round-8 narrowing).
       - pom.xml: smali property bump under §0.

     Execution order: smali bump (0) -> namedPointcuts archive precondition (0.5) ->
       DemandCounter helper + count regen (3.4+1.2) -> deferred-by-design draft +
       SHA snapshot single commit (1.3+1.4 — round-8 race-condition fix) -> matrix
       scaffold (2) -> grammar-tests Maven module (3) -> per-designator test classes
       (4) -> fourteen round-8 closures (4.W/O/R/N/V/X/TT/AT/Y/T/B/D/I/E) -> seven
       round-8 NOT-NEEDED β assertion tests (4.G'/S'/A'/RT'/JP'/CV'/WW' — primed
       names to distinguish from the dropped round-7 closures) -> matrix population
       (5) -> integrity tests + CI gate (6) -> smoke validation ≥10 APKs (6.S,
       gates A/B/C) -> archive (7).

     All sibling-repo paths are under
     /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-instrumentation-dexlib2/.

     Round-6 ledger (Fix-now/Follow-up buckets) was ELIMINATED in round-7.
     Round-7 substrate + thisJoinPoint + Coverage.aj end-to-end were ELIMINATED
     in round-8 (NOT-NEEDED β reclassifications per D9-round-8). See proposal.md
     §"Round-8 absorption-aware demand" and design.md §D9/D10-SUPERSEDED/D11-narrowed/
     D12/D13 for rationale. Full evidence in deferred.md §2.2.1 + docs/analise_sintese_macro.md. -->

## 0. Dependency bump: `smali-dexlib2` 3.0.8 → 3.0.9 (isolated commit, gate the matrix work)

**Goal**: bump the smali property in `pom.xml` before any matrix or grammar-tests work so all subsequent test FQNs and API anchors evaluate against the latest published version (per design.md D5). Gate the bump on `mvn package` AND a `dexdump` behavioural diff over 5 APKs from the INV-INS-31 baseline.

- [ ] 0.1 Verify latest published version against `https://maven.google.com/com/android/tools/smali/group-index.xml` — confirm `3.0.9` is the latest `smali-dexlib2` and `smali-baksmali` listed and that `3.0.10` is not present.
- [ ] 0.2 Edit `rvsec-android/rvsec-instrumentation-dexlib2/pom.xml:32`: `<smali.version>3.0.8</smali.version>` → `<smali.version>3.0.9</smali.version>`. No other change in this commit.
- [ ] 0.3 Run reactor build `cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-instrumentation-dexlib2 && mvn -DskipTests=false package`. ALL existing modules SHALL build SUCCESS with 0 failures and 0 test regressions.
- [ ] 0.3a **Behavioural diff (Opus47 M6)**: pick 5 APKs from the INV-INS-31 wrappers-substituted baseline (`MEMORY.md → project_gh52_smoke5_newdata_results`). Pre-bump (HEAD with 3.0.8) and post-bump (3.0.9): build `instr-cli.jar`, instrument the 5 APKs, run `dexdump -d classes.dex`, `diff` per APK. Non-trivial divergence REVERTS step 0.2.
- [ ] 0.4 Run `javap` against the resolved 3.0.9 jar to confirm gh61+ API surfaces are present.
- [ ] 0.5 Commit on `origin/modules`: `chore(gh62): bump smali-dexlib2 3.0.8 -> 3.0.9 (mvn package + dexdump diff PASS)` with `refs #62`. Push.

## 0.5 Archive precondition: verify `AspectDescriptor.namedPointcuts` cross-repo emission (round-8)

**Goal**: round-8 §4.D depends on the JavaMOP toolchain emitting a `namedPointcuts` field in the `AspectDescriptor` JSON. Round-7 assumed this without verification; round-8 verifies empirically before shipping the §4.D consumer. If the field is absent, ship the JavaMOP-side change as a sub-change FIRST.

- [ ] 0.5.1 Locate a representative `AspectDescriptor` JSON produced by the current JavaMOP toolchain — start with `results/gh53_smoke_dexlib2/monitors/` or rebuild via `mvn -pl rvsec-mop package` on the sibling repo.
- [ ] 0.5.2 Inspect the JSON for the field `namedPointcuts`. Expected (round-8 assumption): the field is present as a `Map<String, String>` (key = pointcut name e.g. `BaseAspect.notwithin`, value = the resolved expression string). If present: proceed to §1.
- [ ] 0.5.3 If absent: open a sub-issue in the JavaMOP-emitter side first; gh62 §4.D BLOCKS on that sub-change. Document the blocker in `MEMORY.md` and pause gh62 until upstream lands.
- [ ] 0.5.4 If present but with a different schema shape (e.g. nested object, array of records): document the actual shape and adjust §4.D.1/4.D.2 task body accordingly before implementation.
- [ ] 0.5.5 Document the verification outcome (PASS / BLOCKED / SCHEMA-DIFFERENT) inline at the top of `tasks.md` as a `<!-- §0.5 outcome: ... -->` comment. Commit if any source change resulted: `chore(gh62): verify namedPointcuts upstream emission (§0.5 PASS|BLOCKED)` with `refs #62`.

## 1. Demand regeneration FIRST + Deferred-by-design + SHA snapshot (round-8 — single-commit race-condition fix)

**Goal**: regenerate ALL demand counts (both source and pipeline) via the `DemandCounter` Java helper BEFORE producing the deferred-by-design document, so the document's path-α/β classifications are empirically verified. Round-8 ships `deferred.md` AND `deferred.snapshot.sha256` in the same commit (race-condition fix for the round-7 plan that separated them).

- [ ] 1.0 **BLOCKER** — execution order: implement `DemandCounter` (detailed spec in §3.4 below) BEFORE running the count regeneration in this task. The helper exposes TWO methods (round-8 introduction): `countMop(designator, corpus)` walks `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/{aspect,jca,generic,generic_new}/` for source-level counts; `countCompiledAj(designator, corpus)` walks `results/gh53_smoke_dexlib2/monitors/` (post-JavaMOP-compilation) for pipeline-level counts. Counts MUST include both `.mop` AND `.aj` files. The regex per designator MUST distinguish pointcut use from Java-statement use (e.g. for `if()`, the canonical pattern is `(?:^|&&|\|\|)\s*if\s*\(`).
- [ ] 1.1 Read `docs/analise_*.md` (6 cross-LLM reviews + `analise_sintese_macro.md` synthesis) to enumerate every silent-gap, verdict discrepancy, and absorption claim surfaced. Catalogue per AspectJ designator + modifier + advice form. The round-8 audit results (3 empirical investigations: APK AJC inspection, compiled `.aj` audit, `coverage-weaver` overlap) are the primary input for the path-β reclassifications.
- [ ] 1.2 Cross-check the §1.0 canonical counts (BOTH `countMop` and `countCompiledAj`) against the reviewers' independent grep results. Any divergence must be resolved by adjusting the regex and re-running `DemandCounter`. Final counts SHALL be the single source of truth quoted inline in the matrix.
- [ ] 1.3 The `openspec/changes/gh62-aspectj-grammar-coverage/deferred.md` document is already populated for round-8 (see the file). Re-verify each entry's evidence against the live audit outputs from §1.2; update file paths if any artefact moved. Three sections: §1 EXPLICIT-NO-OP (only `around`/`proceed`); §2 NOT-NEEDED (§2.1 path α — 24 entries; §2.2 path β — round-8's 7 newly-reclassified + 8 round-7-inherited entries with absorber + empirical evidence per row); §Appendix The Three Empirical Audits.
- [ ] 1.4 **ROUND-8 RACE-CONDITION FIX** — single commit containing BOTH `deferred.md` (final state from §1.3) AND `deferred.snapshot.sha256` (computed from the same `deferred.md` content). Sequence: (a) finalise `deferred.md` content; (b) `sha256sum openspec/changes/gh62-aspectj-grammar-coverage/deferred.md | awk '{print $1}' > rvsec/rvsec-android/rvsec-instrumentation-dexlib2/grammar-tests/src/test/resources/deferred.snapshot.sha256`; (c) `git add` both files; (d) `git commit -m "docs(gh62): deferred-by-design document + frozen SHA-256 snapshot (round-8)"`. Push. This eliminates the round-7 race window where `deferred.md` could be edited between the snapshot generation (§7.4a in round-7) and the post-archive verification.

## 2. Matrix scaffold (no verdicts yet — structure only)

**Goal**: produce `docs/aspectj_grammar_coverage.md` with the canonical column structure including the round-8 `SourceDemand` + `PipelineDemand` split, every required row present, and the `DemandCounter` reference. Verdict and evidence columns are filled with `TBD` for now.

- [ ] 2.1 Create `docs/aspectj_grammar_coverage.md` header citing: the AspectJ Programming Guide §"Pointcuts" URL + snapshot date, the AspectJ 5 quick reference URL, the smali-dexlib2 version verified by §0.4. Document the four-value verdict vocabulary with one-paragraph definitions. Round-8 introduction: explain the `SourceDemand` vs `PipelineDemand` split — scope decisions use PipelineDemand (closures ship when `countCompiledAj ≥ 1`).
- [ ] 2.2 Add "Demand counting" section referencing both `DemandCounter.countMop()` (source) and `DemandCounter.countCompiledAj()` (pipeline) with the per-designator `java.util.regex.Pattern` quoted inline for reviewer audit. NO inline shell; `MatrixIntegrityTest` invokes the Java helpers directly.
- [ ] 2.3 Add stable anchor heading `## Matrix` followed by the table header with columns: `AspectJ syntax | SourceDemand (aspect,jca,generic,generic_new) | PipelineDemand (compiled .aj) | Parser | Matcher | Emitter | Verdict | Evidence | Deferral note`.
- [ ] 2.4 Add one row per **classical pointcut designator** in the closed enumeration: `call`, `execution`, `withincode`, `cflow`, `cflowbelow`, `if`, `handler`, `get`, `set`, `staticinitialization`, `initialization`, `preinitialization`, `adviceexecution`, named-pointcut references.
- [ ] 2.5 Add sub-semantic rows for `target`, `this`, `args` (binding/type-matching sub-rows per spec.md closed enumeration).
- [ ] 2.6 Add one row per **AspectJ 5 annotation pointcut designator**: `@annotation`, `@target`, `@this`, `@args`, `@within`, `@withincode`.
- [ ] 2.7 Add one row per **advice form**: `before`, `after`, `after returning`, `after throwing`, `around`.
- [ ] 2.8 Add rows for **type-pattern modifiers** with positional sub-rows for `T+`.
- [ ] 2.9 Add rows for **SignaturePattern modifiers**: positive visibility, negated visibility, `static`, `final`, `throws ExceptionPattern`.
- [ ] 2.10 Add rows for **within-family per-stage delegation**: `within(...)` positive simple, `within(*..Log)` suffix-wildcard, `within(T+)` T+-inside-positive-within, `!within(...)`.
- [ ] 2.11 Add rows for **composition operators**: `&&`, `||`, `!`, parentheses.
- [ ] 2.12 Add rows for **advice-body reflective API**: `thisJoinPoint`, `thisJoinPointStaticPart`, `thisEnclosingJoinPointStaticPart`, `JoinPoint.getArgs()`, `JoinPoint.getSignature()` + subtypes, `getTarget()/.getThis()`, `getKind()/.getSourceLocation()`.
- [ ] 2.13 Add row for **around-advice mechanics**: `proceed(...)`. Verdict prediction: EXPLICIT-NO-OP.
- [ ] 2.14 Add rows for **aspect declaration mechanics**: `aspect Foo { ... }`, `pointcut p(): ...` named declaration, abstract aspect + concrete subaspect, aspect inheritance, `declare precedence`, privileged aspect.
- [ ] 2.15 Add row for **AspectJ runtime linkage**: `org.aspectj.lang.JoinPoint` family. **Round-8**: prediction `Verdict = NOT-NEEDED β` with `coverage-weaver` as the named upstream absorber.
- [ ] 2.16 Commit on `origin/modules`: `docs(gh62): scaffold aspectj grammar coverage matrix (round-8, source+pipeline demand columns, TBD verdicts)` with `refs #62`. Push.

## 3. `grammar-tests/` Maven submodule scaffold

**Goal**: add the new test-only Maven submodule so the matrix's `Evidence` column can cite test FQNs from §5 onwards.

- [ ] 3.1 In `rvsec-android/rvsec-instrumentation-dexlib2/pom.xml`, add `<module>grammar-tests</module>` to `<modules>`. NOT added to the `instr-cli` shade plugin includes.
- [ ] 3.2 Create `rvsec-android/rvsec-instrumentation-dexlib2/grammar-tests/pom.xml`. Parent: `rvsec-instrumentation-dexlib2`. Test scope deps (pinned in parent `dependencyManagement`):
  - `pointcut-engine`, `advice-emitter`, `dex-mutator`, **`coverage-weaver`** (round-8 introduction — needed for path-β assertion tests citing `coverage-weaver`'s javadoc as absorber evidence)
  - `org.junit.jupiter:junit-jupiter:${junit-jupiter.version}` (reuse parent property; 5.11.3)
  - `org.junit.platform:junit-platform-launcher:1.11.3` (required by `testSkipCountEqualsZero` — round-8 rename from `testSkipCountEqualsSilentGapCount` since no SILENT-GAP rows remain)
  - `org.commonmark:commonmark:0.24.0` + `org.commonmark:commonmark-ext-gfm-tables:0.24.0`
  - `org.junit-pioneer:junit-pioneer:2.3.0`
  No `main/` source; only `src/test/java/` and `src/test/resources/`.
- [ ] 3.3 Create package structure `grammar-tests/src/test/java/br/unb/cic/rv/grammar/`. Add `package-info.java` noting (round-8): this module is the executable oracle for `docs/aspectj_grammar_coverage.md`; tests SHALL be kept in 1:1 correspondence with matrix rows; ZERO `@Disabled` annotations remain post-round-8 (every row has an enabled passing test — COVERED tests assert post-fix behaviour; EXPLICIT-NO-OP tests assert UOE; NOT-NEEDED α tests assert `countMop == 0`; NOT-NEEDED β tests assert `countCompiledAj == 0` plus the named absorber).
- [ ] 3.4 Add `grammar-tests/src/test/java/br/unb/cic/rv/grammar/util/DemandCounter.java` (~150 LOC for round-8, up from round-7's ~120 due to the dual `countMop`/`countCompiledAj` API):
  - `countMop(designator, corpus)`: walks source corpora, returns source-level count.
  - `countCompiledAj(designator, corpus)`: walks `results/gh53_smoke_dexlib2/monitors/` (or a configurable path), returns post-JavaMOP-compilation count.
  - Reads files via `Files.readString()` and applies compiled `Pattern` per designator. Per-designator regex MUST distinguish pointcut use from Java-statement use. No `ProcessBuilder`, no shell. Symlinks NOT followed.
- [ ] 3.5 Add `grammar-tests/src/test/java/br/unb/cic/rv/grammar/util/MatrixMarkdownParser.java` (~60 LOC for round-8): parses the table after `## Matrix` into `record MatrixRow(String syntax, Map<Corpus,Integer> sourceDemand, Map<Corpus,Integer> pipelineDemand, String parserAnchor, String matcherAnchor, String emitterAnchor, Verdict verdict, String evidence, String deferralNote)`. Throws if anchor absent/duplicated.
- [ ] 3.6 Add `grammar-tests/src/test/java/br/unb/cic/rv/grammar/util/AspectJDesignators.java` — `Set<String> DESIGNATORS` constant naming every entry in the closed enumeration.
- [ ] 3.7 Add `grammar-tests/src/test/java/br/unb/cic/rv/grammar/util/AbsorbingStage.java` (round-8 NEW) — enum of recognised upstream absorbers per `Requirement: Upstream Absorption Verdict`: `JAVA_MOP_COMPILER`, `COVERAGE_WEAVER`, `MONITOR_RUNTIME_DISPATCH_LOOP`, `DESCRIPTOR_READER`, `DEXLIB2_INLINE_EMISSION_MODEL`. Used by path-β assertion tests to declare the absorber via a static field.
- [ ] 3.8 Add a smoke test `MavenModuleSmokeTest` asserting `true`. Required to keep the reactor green between commits.
- [ ] 3.9 Run `cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-instrumentation-dexlib2 && mvn -pl grammar-tests test -DskipTests=false -am`. Smoke test SHALL pass. Reactor `mvn package` SHALL build SUCCESS.
- [ ] 3.10 Commit on `origin/modules`: `feat(gh62): add grammar-tests Maven submodule (round-8 scaffold + DemandCounter dual API + AbsorbingStage enum)` with `refs #62`. Push.

## 4. Per-designator grammar test classes (round-8 — zero @Disabled post-archive)

**Goal**: one test class per matrix row group. Round-8 introduction: NO test method carries `@Disabled` at archive — every test is enabled. COVERED tests assert post-fix behaviour; EXPLICIT-NO-OP tests assert UOE; NOT-NEEDED α tests assert `countMop == 0`; NOT-NEEDED β tests assert `countCompiledAj == 0` + named absorber + empirical evidence file exists.

- [ ] 4.1-4.22 (Scaffold the per-designator test classes per round-7 §4.1-§4.22 — see git history. Round-8 modifications:
  - **§4.13 `AdviceExecutionGrammarTest`**: rename `adviceExecutionSemanticMatch` to `adviceExecutionVacuouslyTrueInDexlib2InlineModel`; enable as path-β assertion test (asserts `countMop ≥ 1`, `countCompiledAj == 0` for advice methods, `AbsorbingStage.DEXLIB2_INLINE_EMISSION_MODEL`).
  - **§4.14 `NamedReferenceGrammarTest`**: round-8 narrowed scope — only `baseAspectNotwithinExpansion` survives as in-change (`@Disabled` removed when §4.B/D land); the Coverage.aj two-pointcut sub-test is replaced by §4.CV' absorber assertion.
  - **§4.20 `JoinPointReflectiveApiGrammarTest`**: round-8 rewrite — all methods become path-β assertion tests pointing at `COVERAGE_WEAVER` absorber (the round-7 `@Disabled` SILENT-GAP framing is gone).
  - **§4.21 `AspectDeclarationGrammarTest`**: unchanged (already path-β in round-7).
  - **§4.22 `RobustnessTest`**: unchanged.)
- [ ] 4.23 Run `mvn -pl grammar-tests test`. ALL tests SHALL pass; ZERO skips (round-8 archive condition).
- [ ] 4.24 Commit on `origin/modules`: `test(gh62): per-designator grammar test classes (round-8 — zero @Disabled, path-β assertions for absorbed rows)` with `refs #62`. Push.

## 4.W Positive `within(typePattern)` simple matcher (round-8 — 26 pipeline sites)

**Goal**: filter `classDef` FQN against the `typePattern` argument of positive `within(...)` instead of always-matching. 26 pipeline-level sites (13 jca + 13 generic_new). Coverage.aj's 24 source-level uses are absorbed (§4.WW').

- [ ] 4.W.1 Refactor `pointcut-engine/.../PointcutMatcher.java:109-114` `WithinPC` path: extract `matchesTypePattern` helper from `PointcutMatcher.java:343-358` (round-7 design.md mis-cited `NotWithinPC:343-359`; the helper lives in `PointcutMatcher`). ~10 LOC.
- [ ] 4.W.2 Implement `matchWithinPositive(Context ctx, WithinPC pe)`: compare `ctx.classDef` FQN against `pe.getTypePattern()` via `matchesTypePattern`; return `Match.of(pe)` on match, `Match.empty(pe)` on miss. ~30 LOC.
- [ ] 4.W.3 Update `WithinFamilyGrammarTest.withinPositiveAlwaysMatch_weaverFiltersExpected` → rename to `withinPositiveFiltersClassDef`; assert FQN filter against matching+non-matching `classDef`.
- [ ] 4.W.4 Run `mvn -pl pointcut-engine test`; tests pass. Run `mvn -pl grammar-tests test -Dtest=WithinFamilyGrammarTest`; passes.
- [ ] 4.W.5 Commit: `feat(gh62): positive within(typePattern) simple form (26 pipeline sites; row flips COVERED)` with `refs #62`.

## 4.O `T+` in `call()` owner position (round-8 — ~73 sites generic_new)

**Goal**: extend gh61 parameter-position subtype expansion to owner descriptor matching at `PointcutMatcher.java:153-157`.

- [ ] 4.O.1 Audit gh61's `cpsAwareOwnerMatch` and `InheritanceResolver.isAssignableFrom`. ~5 LOC of grep.
- [ ] 4.O.2 Extend `PointcutMatcher.matchCall`'s owner check (`:153-157`): recognise `+` suffix; invoke subtype-expansion helper. ~30 LOC. Preserve exact-equals path for non-`+` patterns.
- [ ] 4.O.3 Update `CallPointcutGrammarTest.callTSubtypeInOwner`: remove `@Disabled`; assert `call(* javax.crypto.Cipher+.doFinal(..))` against subtype receiver matches.
- [ ] 4.O.4 Run tests.
- [ ] 4.O.5 Commit: `feat(gh62): T+ in call() owner position subtype expansion (~73 sites; row flips COVERED)` with `refs #62`.

## 4.R `T+` in `call()` return position (round-8 — subset of generic_new T+ usage)

**Goal**: symmetric to §4.O for the return descriptor.

- [ ] 4.R.1 Locate the return-descriptor branch in `PointcutMatcher`; apply the same `InheritanceResolver.isAssignableFrom` pattern. ~30 LOC.
- [ ] 4.R.2 Add `CallPointcutGrammarTest.tSubtypeInReturnPosition`: `call(Cipher+ Foo.factory(..))` matches subtype return, not `String`.
- [ ] 4.R.3 Commit: `feat(gh62): T+ in call() return position (§4.R, row flips COVERED)` with `refs #62`.

## 4.N `!target(T)` / `!args(T)` parser specialization (round-8 — 32 sites generic_new)

**Goal**: extend `PointcutExpressionParser.parseUnary()` to specialize negation of `target(T)`/`args(T)` type-matching beyond just `!within`.

- [ ] 4.N.1 Extend `PointcutExpressionParser.parseUnary()`: add cases for `!target(...)` and `!args(...)` constructing `NegationPC` wrapping inner `TargetPC`/`ArgsPC`. ~20 LOC. Note: if `NegationPC` does not exist, this task includes creating it.
- [ ] 4.N.2 Add `NegationPC` matcher: evaluate inner pointcut; invert verdict. ~20 LOC.
- [ ] 4.N.3 Update `CompositionGrammarTest.negationBeyondWithin` → narrow to `negativeTargetArgsParserSpecialization`; remove `@Disabled`; assert `!target(MyClass)` inverts match.
- [ ] 4.N.4 Run tests. Commit: `feat(gh62): !target/!args parser specialization (32 sites; row flips COVERED)` with `refs #62`.

## 4.V `(T, ..)` trailing-mixed varargs in `call()` params (round-8 — 14 jca + 2 generic_new)

**Goal**: extend `PointcutExpressionParser.isVarargs:271-273` to accept trailing-mixed forms.

- [ ] 4.V.1 Refactor `splitParams` to return `ParamList { List<ParamSpec> head; boolean trailingVarargs; }`. ~30 LOC.
- [ ] 4.V.2 Update `CallPC.matchParams`: treat `trailingVarargs=true` as `actualParams.size() >= head.size()` + positional head match + tail accept-any. ~20 LOC.
- [ ] 4.V.3 Add `CallPointcutGrammarTest.trailingMixedVarargsMatchHeadAndAcceptRest`: `call(* SecureRandom.getInstance(String, ..))` matches both single-arg and multi-arg forms.
- [ ] 4.V.4 Commit: `feat(gh62): (T, ..) trailing-mixed varargs (§4.V, row flips COVERED)` with `refs #62`.

## 4.X Method-name glob `name*` (round-8 — ~16 sites generic_new)

**Goal**: replace `expectedName.equals(actualName)` at `PointcutMatcher.java:161-167` with prefix-glob support.

- [ ] 4.X.1 Update `PointcutMatcher.matchCall`'s name check: `expectedName.endsWith("*") ? actualName.startsWith(prefix) : expectedName.equals(actualName)`. ~15 LOC.
- [ ] 4.X.2 Add `CallPointcutGrammarTest.methodNamePrefixGlob`: `call(* Collection.add*(..))` matches `add`/`addAll`/`addLast` but not `remove`.
- [ ] 4.X.3 Commit: `feat(gh62): method-name glob name* (~16 sites; row flips COVERED)` with `refs #62`.

## 4.TT `target(Type)` type-matching (round-8 — 44 sites generic_new)

**Goal**: `PointcutMatcher.java:106-108` currently returns always-match for `TargetPC` regardless of declared `Type`. Implement subtype-aware type checking against the receiver register's declared type.

- [ ] 4.TT.1 Extract `target(Type)` parser path in `PointcutExpressionParser` (distinguish from `target(name)` binding form). Set `Type type;` field on `TargetPC` when arg is a type. ~20 LOC.
- [ ] 4.TT.2 Update `TargetPC` matcher: when `type != null`, check `InheritanceResolver.isAssignableFrom(type, receiverDeclaredType)`; return match iff check passes. Binding form (`name != null`) unchanged. ~30 LOC.
- [ ] 4.TT.3 Add `TargetGrammarTest.targetTypeMatchesByReceiverType`: `target(Cipher)` matches Cipher receiver, not unrelated. Remove `@Disabled`.
- [ ] 4.TT.4 Commit: `feat(gh62): target(Type) type-matching (§4.TT, row flips COVERED)` with `refs #62`.

## 4.AT `args(Type)` type-matching (round-8 — 10 sites generic_new)

**Goal**: symmetric to §4.TT for argument list.

- [ ] 4.AT.1 Extract `args(Type)` parser path. Set `List<Type> types;` field on `ArgsPC`. ~20 LOC.
- [ ] 4.AT.2 Update `ArgsPC` matcher: when `types != null`, walk positionally over the call's argument descriptors. ~30 LOC.
- [ ] 4.AT.3 Add `ArgsGrammarTest.argsTypeMatchesByArgumentType`. Remove `@Disabled`.
- [ ] 4.AT.4 Commit: `feat(gh62): args(Type) type-matching (§4.AT, row flips COVERED)` with `refs #62`.

## 4.Y `staticinitialization(T+)` synthesis when `<clinit>` is absent (round-8 — 6 sites generic_new)

**Goal**: synthesize a minimal `<clinit>` when `staticinitialization(T+)` matches a class without one.

- [ ] 4.Y.1 Add `dex-mutator/src/main/java/br/unb/cic/rv/mutator/StaticInitSynthesizer.java` (~60 LOC): given `ClassDef` without `<clinit>`, append synthesized `<clinit>` containing `return-void`. Flag with debug marker.
- [ ] 4.Y.2 Update `DexWeaver.applyPlan` to invoke synthesizer when `staticinitialization(...)` advice processes a class without `<clinit>`. ~30 LOC.
- [ ] 4.Y.3 Update `StaticInitializationGrammarTest.staticinitializationTSubtype` to assert synthesis path. ~10 LOC test addition.
- [ ] 4.Y.4 Commit: `feat(gh62): synthesize <clinit> for staticinitialization(T+) (6 sites; row flips COVERED)` with `refs #62`.

## 4.T `after() throwing(...)` end-to-end install (round-8 — 2 sites generic_new)

**Goal**: implement `TRY_CATCH_WRAP` in `DexWeaver.applyPlan` (currently `:560-566` discards silently).

- [ ] 4.T.1 Replace `DexWeaver.java:560-566`'s `case TRY_CATCH_WRAP: case REPLACE: break;` with real installer: (a) compute try-range covering matched invoke; (b) allocate fresh exception register honouring `RegisterShifter` (gh61); (c) emit `move-exception` + advice invocation in new handler; (d) update method's try-blocks without disrupting existing handlers. ~80 LOC.
- [ ] 4.T.2 Audit interaction with nested try-catch (the `dexInstrumentationNestedTryCatch` robustness test in §4.22 is the post-fix gate).
- [ ] 4.T.3 Update `AdviceFormGrammarTest.afterThrowingAdvice` (or new `AfterThrowingGrammarTest.installsTryRangeAndHandler`): remove `@Disabled`; assert post-fix bytecode + ART verify.
- [ ] 4.T.4 Run tests.
- [ ] 4.T.5 Commit: `feat(gh62): after() throwing(...) try-range + handler install (2 sites; row flips COVERED)` with `refs #62`.

## 4.B `BaseAspect.notwithin()` macro expansion (round-8 — 1 jca + 1 generic_new)

**Goal**: expand the `BaseAspect.notwithin()` named-ref macro inline. Consumes §4.D's symbol-table resolution.

- [ ] 4.B.1 Implement `BaseAspectExpander` in `pointcut-engine/`: consumes a resolved `PointcutExpression` whose body is an AND-chain of `!within(...)` clauses; produces composed `NotWithinPC` matcher chain. ~50 LOC.
- [ ] 4.B.2 Wire expander into `NamedRefPC` resolution. ~30 LOC.
- [ ] 4.B.3 Add `NamedReferenceGrammarTest.baseAspectNotwithinExpandsInline`: assert correct platform-namespace exclusion.
- [ ] 4.B.4 Commit: `feat(gh62): BaseAspect.notwithin() macro expansion (§4.B, row flips COVERED)` with `refs #62`.

## 4.D `NamedRefPC` resolver via per-aspect symbol table (round-8 — D11 narrowed scope, ~120 LOC)

**Goal**: resolve named-pointcut references against a per-aspect symbol table (`namedPointcuts: Map<String, PointcutExpression>`) populated by `DescriptorReader`. Fall back to `getCommonPointcut()` then to always-match-WARN. **Round-8 narrowing**: the table need only hold one entry per JCA descriptor (`BaseAspect.notwithin`); Coverage.aj's two-pointcut demand is absorbed by `coverage-weaver` (see §4.RT' / §4.CV' below). LOC estimate raised from round-7's ~80 to ~120 to honestly cover the cross-repo schema work.

- [ ] 4.D.1 Extend `AspectDescriptor` schema in `descriptor-reader/src/main/java/br/unb/cic/rv/descriptor/`: add `namedPointcuts: Map<String, PointcutExpression>` field with getter `getNamedPointcuts()`. Additive — existing `commonPointcut` field unchanged. ~30 LOC.
- [ ] 4.D.2 Extend `DescriptorReader.java` to parse new JSON field. Handle absence (e.g. older monitor build) by populating the map with `{commonPointcut-derived-name: commonPointcut-expr}` from existing field. The `commonPointcut-derived-name` is heuristic — first identifier before `(` in the commonPointcut string. Document the fragility in javadoc. ~40 LOC.
- [ ] 4.D.3 Plumb the active `AspectDescriptor` through `pointcut-engine/.../PointcutMatcher.Context`. ~10 LOC.
- [ ] 4.D.4 Rewrite `NamedRefPC` matching: (a) lookup in `ctx.aspectDescriptor.getNamedPointcuts()`; (b) on miss, lookup in `commonPointcut` (string parse); (c) on both misses, log WARN + fall back to always-match. ~40 LOC.
- [ ] 4.D.5 Add `NamedRefResolverTest.tableHit`, `.commonPointcutFallback`, `.alwaysMatchFallback` — all three resolution paths.
- [ ] 4.D.6 Add `DescriptorReaderCompatibilityTest`: assert both old-format JSON (no `namedPointcuts`) and new-format JSON deserialise correctly.
- [ ] 4.D.7 Commit: `feat(gh62): NamedRefPC resolves via per-aspect symbol table (D11 round-8 narrowing; row flips COVERED)` with `refs #62`.

## 4.E `execution(...)` real matcher + emitter (round-8 — RESTORED per user decision 2026-05-26; defensive shipping)

**Goal**: replace the `Match.empty(ex)` placeholder at `PointcutMatcher.matchExecution:307-313` with a real matcher that filters by method signature pattern (name + owner + params + return), AND ship `ExecutionMatcherEmitter` integrating with `DexWeaver`'s method-execution weave path. **Round-8 user decision**: even though the current compiled `.aj` corpora show zero positive consumers of `execution(...)` outside the absorbed `Coverage.aj`, shipping the full closure now (matcher + emitter, ~230 LOC) is preferred over deferring as NOT-NEEDED β — future MOP specs that use `execution(...)` positively will work without re-opening this change. `Coverage.aj`'s `execution(* *.*(..))` form remains absorbed by `coverage-weaver` (not consumed by dexlib2); §4.E is exercised by synthetic fixtures in grammar-tests.

- [ ] 4.E.1 Implement `ExecutionPC` matcher in `pointcut-engine/` (sibling of `CallPC`): walks method body declaration descriptors against the pattern; supports `*` wildcards, `..` standalone+trailing-mixed (via §4.V), `T+` (via §4.O/R), method-name glob (via §4.X). ~80 LOC.
- [ ] 4.E.2 Implement `ExecutionMatcherEmitter` in `advice-emitter/`: the emit path differs from `call()` because the join point is the method body's entry/exit, not a call site. Hook into `DexWeaver`'s method-execution weave path; emit advice invocation at method entry (for `before`) or all return paths (for `after`). ~150 LOC.
- [ ] 4.E.3 Wire `ExecutionPC` through `PointcutMatcher.matchExecution`; remove the `Match.empty(ex)` placeholder. ~10 LOC.
- [ ] 4.E.4 Handle the dual-instrumentation edge case: when a method is matched by both a `call()` MOP pointcut AND an `execution()` pointcut, the weaver MUST avoid double-instrumentation (a method matched by both gets one advice invocation per pointcut, not two for the same site). Add detection logic in the emit-plan ordering pass. ~20 LOC.
- [ ] 4.E.5 Add `grammar-tests/.../ExecutionPointcutGrammarTest`:
  - `executionUniversalMatchesEveryMethod` — `execution(* *.*(..))` matches every method body in a synthetic fixture class.
  - `executionByOwnerName` — `execution(* Cipher.doFinal(..))` matches only `Cipher.doFinal`, not other methods.
  - `executionWithTPlusOwner` — subtype expansion via `InheritanceResolver` works for `execution(* Cipher+.doFinal(..))`.
  - `executionEmitsAtEntryForBeforeAdvice` — assert woven bytecode has the advice invocation immediately after the method's entry prologue.
  - `executionEmitsAtAllReturnPathsForAfterAdvice` — assert every `return`/`return-void`/`return-object` instruction is preceded by the advice invocation.
  - `executionDualInstrumentationNoDouble` — synthesise a method matched by BOTH a `call()` MOP pointcut AND an `execution()` pointcut; assert the woven bytecode has one advice invocation per pointcut (not two for the same site).
  - Remove `@Disabled` from existing scaffold methods (round-7 had stubs).
- [ ] 4.E.6 Commit: `feat(gh62): execution(...) real matcher + emitter (§4.E RESTORED, row flips COVERED)` with `refs #62`.

## 4.I `if(...)` AspectJ PCD via runtime-helper delegation (round-8 — D13 NEW)

**Goal**: 8 sites in generic_new. Round-8 substitutes round-7's in-weaver DEX-lowering plan with runtime-helper delegation (see design.md D13). The weaver assigns a stable `ifId` per `if(...)` clause at weave time and emits `invoke-static MonitorRuntime.evaluateIf(ifId, args_boxed)`. The monitor runtime provides `evaluateIf(int, Object[])` switch-case generated by the JavaMOP toolchain (or a small extension thereof).

- [ ] 4.I.1 Extract `if(<expr>)` parser path in `PointcutExpressionParser`. Build `IfPC` carrying the `<expr>` payload AND a deterministically-assigned `int ifId`. The `ifId` is assigned by source-order traversal of the `.aj` (deterministic). ~20 LOC.
- [ ] 4.I.2 Implement `IfRuntimeDelegationEmitter` in `advice-emitter/` (~60 LOC, round-8 — REPLACES round-7's `IfExpressionLowerer` plan): emits `invoke-static MonitorRuntime.evaluateIf(<ifId>, args_boxed)` where `args_boxed` is an `Object[]` of the bound advice arguments (target, args(...) bindings, `thisJoinPoint` if used). Emits an `if-eqz vReturn, :skip_monitor` short-circuit immediately after the invoke.
- [ ] 4.I.3 Implement `MonitorRuntimeIfHelperEmitter` in `monitor-builder/src/main/java/br/unb/cic/rv/builder/` (~50 LOC, round-8 NEW): generates the `evaluateIf(int ifId, Object[] args)` switch-case method in the per-spec `*RuntimeMonitor` class. Each case arm holds the boolean expression for that `ifId`, lowered by the existing JavaMOP boolean-expression emitter (the same one that lowers `condition(...)` clauses into `*Event(...)` bodies — this path is proven by the `condition()` absorption pattern, see deferred.md §2.2.1-A).
- [ ] 4.I.4 Wire `IfPC` into `PointcutMatcher`: matcher returns always-match (runtime gating is what enforces semantics; the `IfRuntimeDelegationEmitter` does the work). ~5 LOC.
- [ ] 4.I.5 Add `IfGrammarTest.ifSemanticGatesAdviceFire` (round-8 rewrite — exercises the runtime-helper path, not the round-7 in-weaver lowering). Remove `@Disabled`.
- [ ] 4.I.6 Add `IfRuntimeDelegationTest` (round-8 NEW): asserts (a) the weaver emits stable `ifId` values across weave runs (deterministic source-order); (b) the helper switch-case covers every assigned `ifId`; (c) the boolean expression for each `ifId` matches the source-level `if(<expr>)` payload semantics. Failures here fail the build at grammar-test stage, not at runtime (INV-INS-98).
- [ ] 4.I.7 Commit: `feat(gh62): if(...) PCD via runtime-helper delegation (D13, §4.I, row flips COVERED)` with `refs #62`.

## 4.G' `condition(...)` NOT-NEEDED β assertion test (round-8 — replaces round-7 §4.G)

**Goal**: round-7 §4.G `ConditionGuardEmitter` is DROPPED. The `condition(...)` construction is absorbed by the JavaMOP compiler (see deferred.md §2.2.1-A). Round-8 ships an assertion test asserting the absorption holds.

- [ ] 4.G'.1 Add `grammar-tests/.../ConditionGrammarTest.conditionAbsorbedByRuntimeMonitor` (path-β assertion test). Asserts:
  - (a) `DemandCounter.countMop("condition", Corpus.JCA) ≥ 1` AND `Corpus.GENERIC_NEW ≥ 1` (source demand non-zero — 74 total sites);
  - (b) `DemandCounter.countCompiledAj("condition", Corpus.JCA) == 0` (pipeline demand zero — the compiled `.aj` has no `condition(` references);
  - (c) Absorber: `AbsorbingStage.JAVA_MOP_COMPILER` — verified by reading `results/gh53_smoke_dexlib2/monitors/MultiSpec_1MonitorAspect.aj:212-218` and asserting the `*RuntimeMonitor.*Event(...)` method exists (the condition logic moved there).
- [ ] 4.G'.2 Commit: `test(gh62): condition() NOT-NEEDED β assertion test (round-8 reclassification — absorbed by JavaMOP compiler)` with `refs #62`.

## 4.S' `__STATICSIG` NOT-NEEDED β assertion test (round-8 — replaces round-7 §4.S)

**Goal**: round-7 §4.S `StaticSigEmitter` is DROPPED. The macro is absorbed by the JavaMOP compiler (see deferred.md §2.2.1-B). Round-8 ships an assertion test. **Archive precondition SATISFIED 2026-05-26**: the `generic_new` audit confirmed zero `__STATICSIG`/`toLongString`/`thisJoinPointStaticPart` in `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/generic_new/MultiSpec_1MonitorAspect.aj` (592 LOC, 3 source sites all absorbed via inlined `thisJoinPoint.getStaticPart().getSignature()` invocations on lines 521/580/589).

- [x] 4.S'.1 **Archive precondition (COMPLETED 2026-05-26)**: subagent inspection of `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/generic_new/MultiSpec_1MonitorAspect.aj` returned grep counts: `__STATICSIG`=0, `toLongString`=0, `thisJoinPointStaticPart`=0. The compiler inlined `thisJoinPoint.getStaticPart().getSignature()` directly into the `*RuntimeMonitor.*Event(...)` invocations for all 3 sites (`Collection_HashCode.mop:23`, `Serializable_NoArgConstructor.mop:33`, `URLConnection_OverrideGetPermission.mop:21`). Absorber confirmed: `JAVA_MOP_COMPILER`. Evidence file checked into the audit record at `docs/analise_sintese_macro.md` Appendix A.2 plus inline citation in this tasks.md.
- [ ] 4.S'.2 Add `grammar-tests/.../StaticSigGrammarTest.staticSigAbsorbedByJavaMopCompiler` asserting (a) source demand ≥ 1 (3 sites in generic_new), (b) pipeline demand == 0 in both jca and generic_new compiled `.aj`, (c) absorber `JAVA_MOP_COMPILER`, (d) the compiled `MultiSpec_1MonitorAspect.aj` contains `thisJoinPoint.getStaticPart().getSignature()` invocations on the corresponding line ranges (the inlined absorption pattern). The test cross-references the §4.S'.1 audit by quoting the canonical evidence path.
- [ ] 4.S'.3 **Contingency path (NOT ACTIVATED)**: round-8 originally reserved a placeholder for reintroducing §4.S if §4.S'.1 returned non-zero. The audit returned zero; this task is retired. Documented for historical context.
- [ ] 4.S'.4 Commit: `test(gh62): __STATICSIG NOT-NEEDED β assertion test (round-8 reclassification — absorbed by JavaMOP compiler, generic_new audit PASS 2026-05-26)` with `refs #62`.

## 4.A' `adviceexecution()` NOT-NEEDED β assertion test (round-8 — replaces round-7 §4.A)

**Goal**: round-7 §4.A `AdviceExecutionPC` matcher is DROPPED. The `!adviceexecution()` clause in `commonPointcut` is vacuously true in the dexlib2 inline-call emission model (see deferred.md §2.2.1-C).

- [ ] 4.A'.1 Add `grammar-tests/.../AdviceExecutionGrammarTest.adviceExecutionVacuouslyTrueInDexlib2InlineModel` (path-β assertion test). Asserts:
  - (a) The descriptor JSON's `commonPointcut` contains `!adviceexecution()` (source demand non-zero — 2 sites);
  - (b) dexlib2 emits no synthetic advice methods (proven by scanning the woven DEX string pool for method names containing `ajc$before$`/`ajc$after$` and asserting zero hits — fixture: weave a JCA monitor against a sample APK);
  - (c) Matched join points are all call sites (not advice executions), so the negation is satisfied without explicit matcher logic.
  - Absorber: `AbsorbingStage.DEXLIB2_INLINE_EMISSION_MODEL`.
- [ ] 4.A'.2 Commit: `test(gh62): adviceexecution() NOT-NEEDED β assertion test (round-8 reclassification — vacuous in inline-call model)` with `refs #62`.

## 4.RT' AspectJ runtime substrate NOT-NEEDED β assertion test (round-8 — replaces round-7 §4.RT)

**Goal**: round-7 §4.RT `aspectjlang/` Maven submodule + ~600 LOC POJO substrate + ~150 LOC FQN remapper is DROPPED. Sole consumer (Coverage.aj) is absorbed by `coverage-weaver` (see deferred.md §2.2.1-D).

- [ ] 4.RT'.1 Add `grammar-tests/.../RuntimeSubstrateGrammarTest.aspectJSubstrateAbsorbedByCoverageWeaver` (path-β assertion test). Asserts:
  - (a) `coverage-weaver` module produces a synthetic `mop.Coverage` runtime class in the dexlib2 build output (verified by `mvn -pl coverage-weaver test-compile && find target/test-classes -name 'Coverage.class'`);
  - (b) No MOP advice in the JavaMOP-compiled `.aj` references `org.aspectj.lang.*` (only Coverage.aj does; Coverage.aj is not consumed by the dexlib2 pipeline in production builds);
  - (c) The `experimento-20260508` artefact contains zero `org.aspectj.lang.*` references in instrumented DEX (verified by `dexdump` string-pool inspection on a sample instrumented APK from the experiment).
  - Absorber: `AbsorbingStage.COVERAGE_WEAVER`. Empirical evidence: `coverage-weaver/CoverageWeaver.java:23-32` javadoc + `experimento-20260508/RELATORIO.md` §3.2/§7.2.
- [ ] 4.RT'.2 Commit: `test(gh62): AspectJ runtime substrate NOT-NEEDED β assertion test (round-8 reclassification — coverage-weaver absorbs Coverage.aj consumer)` with `refs #62`.

## 4.JP' `thisJoinPoint*` bindings NOT-NEEDED β assertion test (round-8 — replaces round-7 §4.JP)

**Goal**: round-7 §4.JP `ThisJoinPointEmitter` (~250 LOC) is DROPPED. Both consumers (MOP via `__STATICSIG`, Coverage.aj directly) are absorbed upstream (see deferred.md §2.2.1-E).

- [ ] 4.JP'.1 Add `grammar-tests/.../ThisJoinPointGrammarTest.thisJoinPointBindingsAbsorbedByJavaMopAndCoverageWeaver` (path-β assertion test). Asserts:
  - (a) Compiled `.aj` for JCA contains zero `thisJoinPoint*` references;
  - (b) `__STATICSIG` macro is expanded upstream (cross-references §4.S'.1 audit);
  - (c) Only remaining consumer (Coverage.aj) is absorbed by `coverage-weaver` (cross-references §4.RT'.1);
  - (d) APK AJC inspection (`results/gh53_smoke_ajc/instrumented_apks/cryptoapp.apk`) confirms 115/115 MOP advices have zero `Lorg/aspectj/lang/JoinPoint;` references (canonical APK inspection — see `docs/analise_sintese_macro.md` §3.1).
  Absorber: composite — `JAVA_MOP_COMPILER` (for `__STATICSIG`) + `COVERAGE_WEAVER` (for Coverage.aj direct usage).
- [ ] 4.JP'.2 Commit: `test(gh62): thisJoinPoint* NOT-NEEDED β assertion test (round-8 reclassification — composite absorption)` with `refs #62`.

## 4.CV' Coverage.aj end-to-end NOT-NEEDED β assertion test (round-8 — replaces round-7 §4.CV)

**Goal**: round-7 §4.CV `CoverageAjEndToEndTest` (synthesising Android-shaped fixture, weaving Coverage.aj against it) is DROPPED. `coverage-weaver` is byte-for-byte equivalent (see deferred.md §2.2.1-F).

- [ ] 4.CV'.1 Add `grammar-tests/.../CoverageAjAbsorptionGrammarTest.coverageAjAbsorbedByCoverageWeaver` (path-β assertion test). Asserts:
  - (a) `coverage-weaver` module is present in the dexlib2 build output;
  - (b) Instrumented APKs contain `Lmop/Coverage;->log(Ljava/lang/String;)V` invocations at method entries (verified by `dexdump` on a sample experimento-20260508 APK);
  - (c) RVSEC-COV recall metric on the experimento-20260508 sample matches the AJC-variant recall to within 0% (byte-for-byte equivalence claim — verified by re-running the recall comparison from `RELATORIO.md` §7.2);
  - (d) No `Lorg/aspectj/lang/JoinPoint$StaticPart;` or `Lorg/aspectj/runtime/reflect/Factory;` references appear in the instrumented DEX.
  Absorber: `COVERAGE_WEAVER`. Evidence: `CoverageWeaver.java:23-32` javadoc + `SignatureFormatter.java:14-17` javadoc + `experimento-20260508/RELATORIO.md`.
- [ ] 4.CV'.2 Commit: `test(gh62): Coverage.aj NOT-NEEDED β assertion test (round-8 reclassification — coverage-weaver byte-for-byte equivalent)` with `refs #62`.

## 4.WW' `within(*..Log)` + `within(Coverage+)` NOT-NEEDED β assertion test (round-8 — replaces round-7 §4.WW)

**Goal**: round-7 §4.WW extending §4.W to suffix-wildcards and `T+`-in-positive-within is DROPPED. Sole consumer (Coverage.aj) is absorbed by `coverage-weaver` (see deferred.md §2.2.1-G).

- [ ] 4.WW'.1 Add `grammar-tests/.../WithinExtensionsGrammarTest.withinSuffixAndTPlusAbsorbedByCoverageWeaver` (path-β assertion test). Asserts:
  - (a) `coverage-weaver/PackageFilter.java` exists and excludes the expected packages (`android..*`, `java..*`, `kotlin..*`, `mop..*`, `aspectj..*`);
  - (b) Simple positive `within(pkg..*)` form is still in-change via §4.W (other consumers exist in JCA/generic_new);
  - (c) Only the suffix-wildcard and `T+`-in-positive-within sub-forms are absorbed.
  Absorber: `COVERAGE_WEAVER`.
- [ ] 4.WW'.2 Commit: `test(gh62): within(*..Log)/(T+) NOT-NEEDED β assertion test (round-8 reclassification — coverage-weaver PackageFilter absorbs)` with `refs #62`.

## 5. Matrix population (fill verdicts and evidence)

**Goal**: replace every `TBD` in `docs/aspectj_grammar_coverage.md` with a verdict and evidence anchor. The matrix is now the contract.

- [ ] 5.1 For every row, audit current dexlib2 source. Cite `file:line` in `Parser`/`Matcher`/`Emitter`. Round-8 corrections to round-7 anchors:
  - `PointcutMatcher.java:343-358` (not `NotWithinPC:343-359`) for `matchesTypePattern` helper.
  - `PointcutMatcher.java:109-114` (not `:109-112`) for the always-match block.
  - `DexWeaver.java:560-566` (NOT `:534-540`) for `case TRY_CATCH_WRAP: case REPLACE: break;`.
  - Other round-7 anchors preserved.
- [ ] 5.2 Fill BOTH `SourceDemand` and `PipelineDemand` columns per row by invoking `DemandCounter.countMop()` and `.countCompiledAj()` respectively (§3.4 + §1.0-1.2).
- [ ] 5.3 Assign `Verdict` per row using the three-value post-round-8 vocabulary (no `SILENT-GAP` survives):
  - `COVERED` iff there is an enabled passing test exercising the row;
  - `EXPLICIT-NO-OP` iff there is a passing UOE-asserting test + cited `file:line` + deferred.md entry (currently only `around`/`proceed`);
  - `NOT-NEEDED α` iff `SourceDemand == 0` across all corpora AND no parser/matcher implementation AND deferred.md entry;
  - `NOT-NEEDED β` iff `PipelineDemand == 0` AND `SourceDemand ≥ 1` (somewhere) AND deferred.md entry naming the absorber + empirical evidence.
  - If any row would qualify for `SILENT-GAP`, round-8 archive blocker — ship the closure in-change or reclassify to one of the three valid verdicts. `MatrixIntegrityTest.testNoSilentGapRowsRemain` enforces.
- [ ] 5.4 Fill `Evidence` column per row: for COVERED, the passing test FQN; for EXPLICIT-NO-OP, BOTH UOE-assertion test FQN AND `file:line`; for NOT-NEEDED α, `DemandCounter.countMop == 0` assertion test FQN; for NOT-NEEDED β, `DemandCounter.countCompiledAj == 0` assertion test FQN + named absorber + empirical evidence path.
- [ ] 5.5 Cross-check matrix against `deferred.md`: every non-COVERED matrix row appears in exactly one `deferred.md` section; no `deferred.md` entry references non-existent row; every entry has resolvable assertion test FQN.
- [ ] 5.6 Run `mvn -pl grammar-tests test` to confirm matrix claims (every `Evidence` FQN resolves to an existing enabled test).
- [ ] 5.7 Commit: `docs(gh62): populate matrix verdicts + evidence (round-8 source+pipeline columns)` with `refs #62`. Push.

## 6. Integrity tests + CI gates

**Goal**: add `MatrixIntegrityTest` enforcing matrix↔code↔deferred consistency at every CI run, per INV-INS-88..100. Round-8 introduces new tests for the path-β absorber contract (INV-INS-96), the `namedPointcuts` schema (INV-INS-97), and the `if(...)` runtime delegation (INV-INS-98).

- [ ] 6.1 `MatrixIntegrityTest.testEveryDesignatorHasMatrixRow` — set equality between matrix-row syntaxes and `AspectJDesignators.DESIGNATORS`. INV-INS-88.
- [ ] 6.1a `MatrixIntegrityTest.testVerdictMatchesWorstOfPipeline` — re-compute verdict per worst-of-pipeline + absorption-override rule; assert declared verdict matches. INV-INS-89.
- [ ] 6.2 `MatrixIntegrityTest.testVerdictsAreValid` — every verdict ∈ `{COVERED, SILENT-GAP, EXPLICIT-NO-OP, NOT-NEEDED}`; for NOT-NEEDED assert path α (source demand sum == 0 AND parser/matcher MISSING) OR path β (Evidence matches `upstream-stage:.+\s+demand-source:.+\s+test-fqn:.+`). INV-INS-89.
- [ ] 6.3 `MatrixIntegrityTest.testCoveredRowsCiteEnabledPassingTests` — every COVERED row's Evidence FQN resolves to `@Test` non-`@Disabled` method (walk hierarchy for inherited `@Disabled`). INV-INS-90.
- [ ] 6.4 `MatrixIntegrityTest.testNonCoveredRowsAppearInDeferredDocument` — every non-COVERED matrix row appears in `deferred.md` (parsed via commonmark-java); active-then-archive path fallback for the deferred file location. The round-7 `testSilentGapRowsHaveDisabledTestAndLedgerEntry` is dropped (no SILENT-GAP rows post-round-8; the ledger is gone). INV-INS-91.
- [ ] 6.5 `MatrixIntegrityTest.testEnabledTestsResolveToValidMatrixRow` — round-8 rename of round-7's `testEnabledTestsResolveToCoveredOrExplicitNoOpRow`. Every enabled `@Test` in `br.unb.cic.rv.grammar.*GrammarTest` resolves to a matrix row with `Verdict ∈ {COVERED, EXPLICIT-NO-OP, NOT-NEEDED}` — NOT-NEEDED is enabled in round-8 (was disabled in round-7). The `robustness` subpackage is structurally excluded. INV-INS-92.
- [ ] 6.6 `MatrixIntegrityTest.testNoDisabledTestsRemain` — round-8 replacement of round-7's `testDisabledTestsResolveToSilentGapRow`. Asserts ZERO `@Disabled` annotations in `br.unb.cic.rv.grammar.*GrammarTest`. INV-INS-92.
- [ ] 6.7 `MatrixIntegrityTest.testSkipCountEqualsZero` — round-8 replacement of round-7's `testSkipCountEqualsSilentGapCount`. Asserts the JUnit Platform discovery's disabled count == 0. INV-INS-92.
- [ ] 6.8 `MatrixIntegrityTest.testSourceDemandCountsReproducible` and `testPipelineDemandCountsReproducible` — invoke `DemandCounter.countAllMop()` and `.countAllCompiledAj()`; diff against matrix's two demand columns. INV-INS-93.
- [ ] 6.8a `MatrixIntegrityTest.testRoundEightClosuresAreCovered` — round-8 rename of round-7's `testRoundSevenClosuresAreCovered`. For every matrix row covered by the fourteen round-8 in-change closures (§4.{W,O,R,N,V,X,TT,AT,Y,T,B,D,I,E}), assert `Verdict == COVERED` and Evidence FQN resolves to enabled passing test. INV-INS-94.
- [ ] 6.8b `MatrixIntegrityTest.testClosureLocFootprintMatchesMatrixDelta` (advisory; non-blocking) — log LOC delta per closure commit. INV-INS-95.
- [ ] 6.8c `MatrixIntegrityTest.testNoSilentGapRowsRemain` — assert no matrix row carries `Verdict = SILENT-GAP`. INV-INS-91 (round-8).
- [ ] 6.8d **REMOVED in round-8** — round-7's `testInstrCliJarContainsSubstrate` is dropped (no substrate ships in round-8).
- [ ] 6.8e `MatrixIntegrityTest.testDeferredDocumentIsFrozenPostArchive` — read `deferred.snapshot.sha256`; compute SHA-256 of live `deferred.md`; assert equality. INV-INS-100. **Round-8 race-condition fix**: the snapshot is created in the same commit as the final `deferred.md` content (§1.4), eliminating the round-7 race window.
- [ ] 6.8f `AbsorptionClaimsContractTest` (round-8 NEW, INV-INS-96 enforcement) — aggregates all path-β assertion tests (§4.G'/S'/A'/RT'/JP'/CV'/WW'/E'). For each, verifies THREE properties: (a) source demand ≥ 1, (b) pipeline demand == 0, (c) named absorber file/module exists with documented evidence anchor. Fails the build if any property changes (silent regression guard).
- [ ] 6.8g `MatrixIntegrityTest.testNamedPointcutsSchemaPresent` — round-8 NEW (INV-INS-97). Asserts `AspectDescriptor` class has a `namedPointcuts` field of type `Map<String, ?>`; asserts `DescriptorReader` parses it from a sample JSON fixture.
- [ ] 6.8h `IfRuntimeDelegationTest` (already added in §4.I.6 — round-8 NEW, INV-INS-98) — deterministic `ifId` ordering + switch-case coverage + semantic match.
- [ ] 6.9 Run `mvn -pl grammar-tests test`. ALL integrity tests SHALL pass on the populated matrix.
- [ ] 6.10 Extend `rvsec/.github/workflows/ci.yml`: add `mvn test -pl rvsec-android/rvsec-instrumentation-dexlib2/grammar-tests -DskipTests=false -am` after existing `maven-build` step. Declare `env: RVSEC_HOME: ${{ github.workspace }}` (or analogous). Round-8: CI step's stdout SHALL print the absorber-test count (NOT-NEEDED β rows) for visibility — track absorption claims at every run.
- [ ] 6.10a CI sanity check: prepend `test -d "$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca" || { echo "ERROR..."; exit 1; }`.
- [ ] 6.11 Commit: `test(gh62): MatrixIntegrityTest + AbsorptionClaimsContractTest + IfRuntimeDelegationTest + CI gate (round-8)` with `refs #62`. Push.

## 6.S Smoke validation on ≥10 JCA-226 APKs (round-8 — gates A/B/C; Coverage.aj gate DROPPED)

**Goal**: verify the thirteen round-8 closures produce correct monitor events on real APKs from the JCA-226 dataset. The round-7 Coverage.aj end-to-end gate (Gate D) is DROPPED — Coverage.aj is absorbed by `coverage-weaver`, which already produced the production coverage data in experimento-20260508.

- [ ] 6.S.1 Pick ≥10 APKs from the JCA-226 instrumentable subset (re-using INV-INS-31 baseline). Selection MUST cover the fourteen closures collectively (one APK per closure pattern; §4.E is exercised via a synthetic fixture in grammar-tests rather than a real APK, since no JCA spec uses `execution(...)` positively today). At least one APK MUST have nested try-catch DEX topology (for §4.T).
- [ ] 6.S.2 Pre-change snapshot: re-instrument ≥10 APKs with `instr-cli.jar` from `HEAD~N` (pre-closure); run on emulator under standard JCA MOP spec; capture monitor event stream + per-closure pattern-match counts.
- [ ] 6.S.3 Post-change snapshot: re-instrument with `HEAD` (post-closure); run; capture.
- [ ] 6.S.4 Three gates (round-8 — drops round-7's Gate D):
  - **GATE A (hard, no-new-VerifyError)**: post-change DEX MUST pass ART install + DexBackedDexFile round-trip on all ≥10 APKs. Any new VerifyError REVERTS the responsible closure series.
  - **GATE B (hard, monotonic non-decrease event count)**: total post-change event count ≥ pre-change. Round-8 note: §4.I `if(...)` runtime delegation can short-circuit events (when the guard returns false); the gate is monotonic OVER THE SET OF APKS WHERE NO `if(...)` GUARD IS EXERCISED. The smoke harness MUST distinguish: APKs exercising `if(...)` clauses are evaluated against the closure-specific positive-evidence gate (Gate C); APKs not exercising them are evaluated against the monotonic gate.
  - **GATE C (hard, positive-evidence per closure)**: each of the fourteen closures MUST produce ≥1 new event in ≥1 APK whose pattern matches the closure (§4.E: positive evidence via the synthetic grammar-tests fixture cited above, not a real APK). A closure producing zero new events anywhere is either inert (bug) or APK selection was wrong.
- [ ] 6.S.5 If any gate fails, REVERT the offending closure commit(s) (bisect-friendly per atomic commits) and re-evaluate.
- [ ] 6.S.6 Commit: `chore(gh62): ≥10-APK smoke validation PASS for round-8 closures (gates A/B/C)` with `refs #62`. Push.

## 7. Cross-Cutting Verification + Archive

- [ ] 7.1 Validate the openspec change: `openspec validate --changes gh62-aspectj-grammar-coverage --strict`. SHALL return PASS.
- [ ] 7.2 Invoke `/rv-code-reviewer` via the Skill tool against the gh62 diff (matrix, `deferred.md`, `grammar-tests/` module, CI step in `rvsec/.github/workflows/ci.yml`). Address review findings inline.
- [ ] 7.3 Update `MEMORY.md` with a `project_gh62_grammar_coverage_round8` entry capturing: (a) row count per category (COVERED, EXPLICIT-NO-OP, NOT-NEEDED α, NOT-NEEDED β); (b) the seven round-8 reclassifications with their absorbers; (c) the LOC reduction (round-7 ~2 000 → round-8 ~785); (d) the `coverage-weaver` semantic equivalence reference.
- [ ] 7.4 Run `/opsx:verify` against the change.
- [ ] 7.4a **REMOVED in round-8** — the round-7 separate snapshot commit is folded into §1.4 (race-condition fix). No standalone snapshot task at this stage.
- [ ] 7.5 Run `/opsx:archive` (`openspec archive gh62-aspectj-grammar-coverage --yes`). Delta spec for `instrumentation` SHALL auto-merge.
- [ ] 7.6 Commit on `origin/modules`: `chore(gh62): archive change (closes #62, round-8 lean redesign)`. Push.
- [ ] 7.7 Close issue #62 via `gh issue close 62 --repo PAMunb/rvsec --comment "..."` referencing the matrix, `deferred.md` snapshot SHA, the `grammar-tests/` module, the `MatrixIntegrityTest` + `AbsorptionClaimsContractTest` CI gates, and the round-8 redesign rationale (`docs/analise_sintese_macro.md` + the seven path-β reclassifications). Future closures open their own issues and OpenSpec changes when pipeline demand surfaces for any deferred row (caught by `testPipelineDemandCountsReproducible`).

## 8. Out-of-scope cross-cutting checks

- [ ] 8.1 Confirm production source code changes are SCOPED to the round-8 in-change closure set (per design D8 + D9-round-8 + D11-narrowed + D13). `git diff origin/modules~N..origin/modules -- rvsec-android/rvsec-instrumentation-dexlib2/` SHALL touch the following modules and files only:
  - **advice-emitter/**: new — `IfRuntimeDelegationEmitter.java` (§4.I, ~60 LOC), `ExecutionMatcherEmitter.java` (§4.E, ~150 LOC — RESTORED per user decision). Extended: `AfterThrowingEmitter.java` (§4.T), `EmitterDispatch.java` (§4.T/I/E wiring).
  - **monitor-builder/**: new — `MonitorRuntimeIfHelperEmitter.java` (§4.I, ~50 LOC — generates `evaluateIf(int, Object[])` switch-case).
  - **pointcut-engine/**: new — `BaseAspectExpander.java` (§4.B), `ExecutionPC.java` (§4.E, ~80 LOC — RESTORED per user decision); extended — `PointcutMatcher.java` (§4.W, §4.O, §4.R, §4.X, §4.D, §4.TT, §4.AT, §4.E removes the `Match.empty(ex)` placeholder at `:307-313`), `PointcutExpressionParser.java` (§4.N, §4.V, §4.TT, §4.AT, §4.D, §4.I), `WithinPC.java` (§4.W), `CallPC.java` (§4.O, §4.R, §4.X, §4.V), `TargetPC.java` (§4.TT), `ArgsPC.java` (§4.AT), `NamedRefPC.java` (§4.D, §4.B), `IfPC.java` (§4.I — adds `int ifId` field), `NegationPC.java` (§4.N — NEW if absent).
  - **dex-mutator/**: new — `StaticInitSynthesizer.java` (§4.Y); extended — `DexWeaver.java` (§4.T TRY_CATCH_WRAP install).
  - **descriptor-reader/**: extended — `AspectDescriptor.java` (§4.D `namedPointcuts` field), `DescriptorReader.java` (§4.D JSON parser).
  - **coverage-weaver/**: NO change (round-8 — Coverage.aj absorption is a runtime claim, not a code change; tests in grammar-tests cite the existing module as evidence).
  - **instr-cli/**: NO `pom.xml` change (round-7 plan to add `aspectjlang` to shade includes is dropped — no `aspectjlang/` module exists).
  - **NOT touched** (round-7 plan dropped): `aspectjlang/` Maven submodule does NOT exist; `AspectJRuntimeRemapper.java` is NOT created; `ConditionGuardEmitter.java` / `StaticSigEmitter.java` / `AdviceExecutionEmitter.java` / `ThisJoinPointEmitter.java` are NOT created; `IfExpressionLowerer.java` is NOT created (replaced by `IfRuntimeDelegationEmitter` + `MonitorRuntimeIfHelperEmitter`). **Note**: `ExecutionMatcherEmitter.java` IS created (§4.E RESTORED per user decision 2026-05-26 — moved from the round-7-dropped list back to the in-change list above).
  Other production code MUST NOT be touched.
- [ ] 8.2 Confirm `instr-cli.jar`'s observable behaviour changes are SCOPED: re-run per-module test bars and assert 0 NEW failures vs. pre-task-4.{closure-set} baseline. Shaded jar's byte hash WILL change. §6.S smoke validation is the empirical gate.
- [ ] 8.3 Re-instrument the ≥10-APK JCA-226 smoke subset (§6.S) only. NO full 190-APK re-instrumentation; NO Docker image rebuild beyond §6.S; NO APE experiment re-run.
