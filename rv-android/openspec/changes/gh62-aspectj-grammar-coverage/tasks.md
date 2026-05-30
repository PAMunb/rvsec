# Tasks: gh62-aspectj-grammar-coverage

> **ROUND-11 BANNER (2026-05-29) — AUTHORITATIVE OVERRIDE (supersedes Round-10 banner below)** — full evidence: `EMPIRICAL-DEMAND.md` Round-11 addendum.
> - **`.aj` divergence root cause = the `-s`/`-statistics` flag** (`MOPStatistics.java:69-78` emits the `ForkedBooter` stats dump only under `-s`). The `MultiSpec_1MonitorAspect.aj` files sitting in `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/{jca,generic_new}/` are git-ignored `-s` stray artifacts, NOT on the production path — **delete them (§0.6)** and never grep them. `DemandCounter.countMop()` scans **only `*.mop`** (+ `aspect/Coverage.aj`), NEVER `*.aj` in the source dirs.
> - **§4.E / §4.W absorber = `coverage-weaver`** (NOT "JavaMOP call-rewrite"/"MOP macro-body"). Sole consumer of positive `execution()`/`within()` is `aspect/Coverage.aj`, absorbed by `coverage-weaver`. `.mop` demand = 0. The round-10 "Source = 1,24,0,28 / 22,13,0,13" was grepped from the `-s` stray `.aj`.
> - **§4.R REMOVED — NOT-NEEDED α** (`T+` in `call()` return = 0 everywhere). §4.R.1-§4.R.3 below are SUPERSEDED — do NOT execute; replaced by §4.R' (NOT-NEEDED α assertion). **Closure count 12 → 11.**
> - **§4.Y fork-free** (R11.5): ship `org.aspectj.lang.Signature` + `ClassSignature(Class)` in `rvsec-core` (already dexed); weaver emits `const-class`+`new-instance`+`invoke-direct`+`invoke-static` at `<clinit>`; special-case the `getSignature()` arg token. NO `SignatureFactory` constructing AspectJ objects from a fork; NO JavaMOP change.
> - **§4.I fork-free** (R11.5): D13 RETIRED — NO `MonitorRuntimeIfHelperEmitter`, NO `evaluateIf`, NO `IfRuntimeAbi`, NO `ifId` (none exist in either fork). Complete the `IfGuardEmitter` stub with direct DEX lowering of `o==null` and `!Thread.holdsLock(o)` + fail-loud default. §0.7 audit re-scoped accordingly (3 sites, in-weaver bindings).
> - **Counts**: §4.X = 13 (was 14); §4.V = 6 jca (resolves PROVISIONAL); §4.N = 14+2; others confirmed. Closure count **11**; LOC **~470-560**.
> Where this conflicts with anything below — including the Round-10 banner — this banner wins.

> **ROUND-10 BANNER (2026-05-29) — subordinate to the Round-11 banner above**
>
> Empirical pipeline-level demand audit against `empirical-monitors/{jca,generic,generic_new}/` revised three classifications. See `EMPIRICAL-DEMAND.md` for the full delta:
>
> - **AA-decision**: §4.E `execution(...)` — pipeline POSITIVE = 0,0,0 → **REMOVED from in-change scope** (NOT-NEEDED β). Tasks §4.E.1-§4.E.6 below are SUPERSEDED — do NOT execute them; the section is replaced by §4.E' (NOT-NEEDED β assertion test, analogous to §4.G'/§4.S').
> - **AB-decision**: §4.W positive `within(typePattern)` simple `pkg..*` — pipeline POSITIVE = 0,0,0 → **REMOVED from in-change scope** (NOT-NEEDED β). Tasks §4.W.1-§4.W.6 below are SUPERSEDED; section replaced by §4.W' (NOT-NEEDED β assertion test).
> - **AC-decision**: §4.JP `thisJoinPoint*` → **REACTIVATED inside §4.Y**. 3 sites of `thisJoinPoint.getStaticPart().getSignature()` in `empirical-monitors/generic_new/MultiSpec_1MonitorAspect.aj:260,319,328`. §4.Y gains a Signature-delivery sub-closure (§4.Y.5 to be added below); the path-β assertion test §4.JP' is REMOVED.
>
> Count corrections (§4.I 8→3, §4.T 2→1, §4.Y 6→3 + Signature delivery, §4.TT 44→22, §4.AT 10→5, §4.N 32→16, §4.O ~73→64, §4.X ~16→13) are applied inline below as "ROUND-10 EMPIRICAL" annotations on each closure section.
>
> Closure count: 14 → **12**. Total LOC: ~865-940 → **~565-660**. The decision codes A-Z below are preserved as historical context; round-10 adds AA/AB/AC.

<!-- ROUND-8 redesign (2026-05-26 — D9-round-8 absorption-aware demand + D12 path-β verdict + D13 if() runtime delegation; §4.E restored per user decision same day)
     + ROUND-8 EMPIRICAL REVISIONS (2026-05-28 — cross-LLM meta-review pass on 10 reviewer outputs).

     The 2026-05-28 revisions apply convergent findings from the cross-LLM meta-review of the
     change artefacts (analise_claude.md, analise_gemini-2.5-pro.md, analise_gpt-5-codex.md,
     analise_mimo-v2-5-free.md, analise_nemotron-3-super-free.md, codex_old.md,
     deepseek-v4-flash-free.md, deepseek-v4-flash-free_old.md, plus the meta-reviews in
     analise_codex.md + analise_llms.md). Decision codes (A/B/C/D/E/F/G/H/I/J/K/L/M/N/O/P/Q/R/S/U/V/W/X/Y/Z)
     are referenced inline in the artefacts. Highlights:
       - A (empirical): the cross-repo `namedPointcuts: Map` schema change is RETIRED.
         AspectDescriptor.baseAspectExclusions: List<String> already exists in the schema,
         populated by DescriptorWriter.defaultBaseAspectExclusions() with the canonical twelve
         entries. §4.D + §4.B consume the existing field; ~200 LOC saved.
       - G: NamedRefPC fail-closed (UnresolvedNamedRefException / LegacyDescriptorException)
         replaces the always-match-with-WARN trap.
       - M (empirical): IfGuardEmitter already exists at advice-emitter/.../IfGuardEmitter.java;
         §4.I completes its emit() body. The early-round-8 plan to create
         IfRuntimeDelegationEmitter is RETIRED (P3 violation).
       - B: ifId is content-hashed (SHA1 of normalised pointcut + advice form + aspect FQN),
         NOT source-order traversal. Both sides reference IfRuntimeAbi.computeIfId.
       - Y: evaluateIf ABI specified (arg ordering, boxing, fail-loud default-case).
       - F: §4.T applies range-splitting (NOT nested-wrapping) under nested try-catch.
       - Q: §4.T LOC estimate revised 80 -> 150-200.
       - E: §4.E.4 dual-instrumentation algorithm = MethodRef-equality + composite dedup key. **VOID per round-10 AA-decision** (§4.E removed; no `execution()` matcher ships).
       - V: target(Type) / args(Type) use declared-type, not runtime instance-of.
       - X: §4.E `after()` semantics = full (after+throwing), not narrow returning-only. **VOID per round-10 AA-decision** (§4.E removed).
       - D: DemandCounter compiled-`.aj` path configurable (system property + env var + fixture).
       - L: §1.4 SHA snapshot mkdir -p the destination directory first (sequencing fix).
       - N: §0.7 added — audit 8 if() sites in generic_new for advice-bound-only variables.
       - O: §4.D structurally precedes §4.B (dependency-correct ordering).
       - P: handler() + declare precedence + aspect inheritance + abstract aspect + privileged
         aspect reclassified path β -> path α in deferred.md (zero source demand).
       - R: §4.V splitParams ripple to CallPC/ArgsPC documented; LOC revised 50 -> 50-80.
       - S: pipeline demand for generic_new — fallback path documented (fixture regen preferred).
       - U: §4.E Gate C validated via grammar-tests fixture + dexlib2 bytecode inspection
         (not real APK) since no current JCA-226 APK uses execution() positively. **VOID per round-10 AA-decision** (§4.E removed; Gate C bipartite split documented at §6.S supersedes).
       - W: docs/AJ_CONSTRUCTIONS_INVENTORY.md + docs/AJ_TO_DEXLIB2_MAPPING.md carry SUPERSEDED
         banner (INV-INS-102); the matrix is the live contract.
       - Z: §4.B test exercises N=12 (canonical) + N=2 + N=1 + N=0 fail-closed (INV-INS-101).
       - I, J, C, H: housekeeping — "(6)" -> "(7)" in spec; ledger.md -> deferred.md refs in
         design; round-7 residue removed from design API Design section; LOC reconciled to ~865-940.
       - K: docs/analise_sintese_macro.md may not be present locally; deferred.md §Appendix
         carries the load-bearing conclusions inline. References preserved for regeneration later.

     This change is documentation + a new Maven test-only submodule + a CI gate + FOURTEEN
     DEMAND-DRIVEN CLOSURES covering every construction with non-zero PIPELINE-level demand
     (post JavaMOP compilation, post coverage-weaver absorption, post DescriptorReader flattening)
     plus the defensively-shipped §4.E execution(...) closure.
     The matrix archives with ZERO SILENT-GAP rows; seven round-7 closures are reclassified
     NOT-NEEDED β based on the round-8 empirical audits (docs/analise_sintese_macro.md + deferred.md §Appendix).
     No Python module is touched. NO aspectjlang/ Maven submodule (round-7 plan dropped).
     NO namedPointcuts schema change (early-round-8 plan retired per A-decision 2026-05-28).
     NO new IfRuntimeDelegationEmitter class (early-round-8 plan retired per M-decision 2026-05-28).

     Production parser/matcher/emitter source code changes (§8.1 has the full
     authoritative file list; sketch below):
       - advice-emitter/: NEW — ExecutionMatcherEmitter (§4.E); EXTENDED —
         existing IfGuardEmitter (§4.I per M-decision — completes emit() body),
         AfterThrowingEmitter (§4.T with F-decision range-splitting),
         EmitterDispatch (§4.T/I/E wiring).
       - monitor-builder/: NO new files (round-11 R11.5: the round-8
         MonitorRuntimeIfHelperEmitter / evaluateIf / IfRuntimeAbi / ifId path is
         RETIRED — it required JavaMOP/RV-Monitor fork-side generation and exists in
         neither fork; §4.I is fully in-weaver in IfGuardEmitter).
       - rvsec-core/: NEW — org.aspectj.lang.Signature interface + ClassSignature(Class)
         impl (§4.Y fork-free Signature delivery; already on the dexlib2 packaging allowlist).
       - pointcut-engine/: NEW — BaseAspectExpander (§4.B, ~15-20 LOC per A-decision),
         ExecutionPC (§4.E), UnresolvedNamedRefException + LegacyDescriptorException (§4.D, G-decision);
         EXTENDED — PointcutMatcher (§4.W/O/R/X/D/TT/AT), PointcutExpressionParser (§4.N/V/TT/AT/I),
         WithinPC (§4.W), CallPC (§4.O/R/X/V), TargetPC (§4.TT, V-decision declared-type),
         ArgsPC (§4.AT, V-decision declared-type), NamedRefPC (§4.D/B per A-decision),
         IfPC (§4.I — carries the raw `javaExpression`; NO `ifId` field per R11.5).
       - dex-mutator/: NEW — StaticInitSynthesizer (§4.Y); EXTENDED — DexWeaver (§4.T
         TRY_CATCH_WRAP install with F-decision range-splitting per design.md D14).
       - descriptor-reader/: NO schema change (A-decision empirical revision 2026-05-28 —
         existing baseAspectExclusions field consumed directly).
       - docs/: SUPERSEDED banner on AJ_CONSTRUCTIONS_INVENTORY.md + AJ_TO_DEXLIB2_MAPPING.md
         (W-decision per §7.8).
       - pom.xml: smali property bump under §0.

     Execution order: smali bump (0) -> baseAspectExclusions archive precondition (0.5
       per A-decision; replaces early-round-8 namedPointcuts cross-repo verification) ->
       8 if() sites audit (0.7 per N-decision) -> DemandCounter helper + count regen
       (3.4 with D-decision configurable path + 1.2 + 1.2a S-decision generic_new fallback) ->
       deferred-by-design draft + SHA snapshot single commit (1.3+1.4 — round-8 race-condition
       fix + L-decision mkdir -p sequencing fix) -> matrix scaffold (2) -> grammar-tests
       Maven module (3) -> per-designator test classes (4) -> eleven round-11 closures
       (4.W/O/R/N/V/X/TT/AT/Y/T/B/D/I/E — note: §4.D structurally PRECEDES §4.B per O-decision) ->
       seven round-8 NOT-NEEDED β assertion tests (4.G'/S'/A'/RT'/CV'/WW' — primed
       names to distinguish from the dropped round-7 closures; round-10 ADDS
       §4.E' (AA-decision) + §4.W' (AB-decision); round-10 REMOVES §4.JP' per
       AC-decision since the capability is reactivated as §4.Y Signature delivery)
       -> matrix population (5) -> integrity tests + CI gate (6) -> smoke validation
       bipartite gate round-10 (6.S, gates A/B/C with §4.E fixture-and-bytecode
       split DROPPED per AA — U-decision is VOID) -> legacy inventory
       SUPERSEDED banner (7.8 W-decision) -> archive (7).

     All sibling-repo paths are under
     /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-instrumentation-dexlib2/.

     Round-6 ledger (Fix-now/Follow-up buckets) was ELIMINATED in round-7.
     Round-7 substrate + thisJoinPoint + Coverage.aj end-to-end were ELIMINATED
     in round-8 (NOT-NEEDED β reclassifications per D9-round-8). See proposal.md
     §"Round-8 absorption-aware demand" and design.md §D9/D10-SUPERSEDED/D11-narrowed/
     D12/D13/D14/D15 for rationale. Full evidence in deferred.md §2.2.1 +
     docs/analise_sintese_macro.md (or deferred.md §Appendix as the inline fallback). -->

## 0. Dependency bump: `smali-dexlib2` 3.0.8 → 3.0.9 (isolated commit, gate the matrix work)

**Goal**: bump the smali property in `pom.xml` before any matrix or grammar-tests work so all subsequent test FQNs and API anchors evaluate against the latest published version (per design.md D5). Gate the bump on `mvn package` AND a `dexdump` behavioural diff over 5 APKs from the INV-INS-31 baseline.

- [x] 0.1 Verify latest published version against `https://maven.google.com/com/android/tools/smali/group-index.xml` — confirm `3.0.9` is the latest `smali-dexlib2` and `smali-baksmali` listed and that `3.0.10` is not present. <!-- DONE 2026-05-29: dl.google.com group-index lists 3.0.0..3.0.9 (no 3.0.7-gap aside); 3.0.9 highest for both smali-dexlib2 + smali-baksmali; 3.0.10 absent. -->
- [x] 0.2 Edit `rvsec-android/rvsec-instrumentation-dexlib2/pom.xml:32`: `<smali.version>3.0.8</smali.version>` → `<smali.version>3.0.9</smali.version>`. No other change in this commit. <!-- DONE 2026-05-29 -->
- [x] 0.3 Run reactor build `cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-instrumentation-dexlib2 && mvn -DskipTests=false package`. ALL existing modules SHALL build SUCCESS with 0 failures and 0 test regressions. <!-- DONE 2026-05-29: BUILD SUCCESS, 10/10 modules, all tests 0 fail/0 err/0 skip. -->
- [x] 0.3a **Behavioural diff (Opus47 M6)**: pick 5 APKs from the INV-INS-31 wrappers-substituted baseline (`MEMORY.md → project_gh52_smoke5_newdata_results`). Pre-bump (HEAD with 3.0.8) and post-bump (3.0.9): build `instr-cli.jar`, instrument the 5 APKs, run `dexdump -d classes.dex`, `diff` per APK. Non-trivial divergence REVERTS step 0.2. <!-- DONE 2026-05-29: woven classes.dex BYTE-IDENTICAL (md5 match) across all 5 APKs (blockads/anihyou/cajuscan/droidstress/solxpect); dex_only phase, jca descriptor; only raw-dump diff = the 4 file-path banner lines. Zero behavioural divergence. droidstress wrappersSubstituted=4 matches INV-INS-31 baseline. -->
<!-- §0.3a method note: 3.0.8 jar built via `mvn -pl cli -am -DskipTests clean package` after reverting pom; CLEAN build required (incremental skipped re-shade → false-identical jars). Both jars confirmed distinct md5 + correct smali-dexlib2-{3.0.8,3.0.9}.jar in shade WARNING before diffing. -->
<!-- §0.6 outcome: PENDING. §0.7 audit table: PENDING. §0.5 outcome (baseAspectExclusions): PENDING. §1.2a outcome: PENDING. -->
<!-- STATUS 2026-05-29: §0.5=PASS, §0.6=closed-by-rationale, §0.7=PASS, §1.2a=(i). -->
<!-- §1.2 DEMAND BASELINE (authoritative DemandCounter Java counts, 2026-05-29) — SourceDemand[aspect,jca,generic,generic_new] / PipelineDemand[jca,generic,generic_new]:
     condition           SRC 0,64,0,10  PIPE 0,0,0   (β JavaMOP)
     __STATICSIG         SRC 0,0,0,3    PIPE 0,0,0   (β JavaMOP)
     adviceexecution     SRC 0,0,0,0    PIPE 1,1,1   (β DEXLIB2_INLINE; the !adviceexecution() in compiled commonPointcut — source lives in descriptor commonPointcut, not .mop)
     execution_positive  SRC 1,0,0,0    PIPE 0,0,0   (β coverage-weaver; Coverage.aj)
     within_positive     SRC 24,0,0,0   PIPE 0,0,0   (β coverage-weaver; Coverage.aj excludedPackages)
     not_within          SRC 0,0,0,0    PIPE 13,13,13 (commonPointcut RVMObject exclusion; flows via §4.B/§4.D)
     if_pcd              SRC 0,0,0,5    PIPE 0,0,3    (§4.I COVERED — 3 pipeline matches §0.7)
     target_type         SRC 0,0,0,8    PIPE 0,0,8    (§4.TT COVERED, positive only)
     args_type           SRC 0,0,0,3    PIPE 0,0,3    (§4.AT COVERED, positive only)
     not_target          SRC 0,0,0,14   PIPE 0,0,14   (§4.N)
     not_args            SRC 0,0,0,2    PIPE 0,0,2     (§4.N; not_target+not_args=16)
     call_return_tsubtype SRC 0,0,0,0   PIPE 0,0,0    (§4.R' NOT-NEEDED α)
     §1.2b RECONCILIATION: round-10 '§4.TT=22' = target_type(8)+not_target(14); '§4.AT=5' = args_type(3)+not_args(2); '§4.N=16' = not_target(14)+not_args(2). Negated forms owned by exactly one designator key (no double-count). TODO §4/§5: add §4.O(T+ owner,pipe=64), §4.X(name glob,pipe=13), §4.V(varargs,pipe=6 jca) designators to DemandCounter regex map. -->
<!-- §1.2a outcome: (i) — generic_new compiled .aj shipped in grammar-tests/src/test/resources/compiled-aj-fixtures/generic_new/; countCompiledAj(_,GENERIC_NEW) returns REAL counts (no fallback annotation). All three corpora {jca,generic,generic_new} present. -->
- [x] 0.4 Run `javap` against the resolved 3.0.9 jar to confirm gh61+ API surfaces are present. <!-- DONE 2026-05-29: MutableMethodImplementation, MethodImplementationBuilder, BuilderInstruction21t/35c, ClassDef, DexBackedDexFile all OK. -->
- [x] 0.5 Commit on `origin/modules`: `chore(gh62): bump smali-dexlib2 3.0.8 -> 3.0.9 (mvn package + dexdump diff PASS)` with `refs #62`. Push. <!-- DONE 2026-05-29: committed LOCALLY as 7153b651 in sibling rvsec repo (scoped to pom only). PUSH DEFERRED per user decision (commit locally, don't push). -->

## 0.5 Archive precondition: verify `AspectDescriptor.baseAspectExclusions` is populated in production (round-8 empirical revision 2026-05-28 — A-decision per cross-LLM meta-review)

**Round-8 SCOPE CHANGE (2026-05-28)**: the early-round-8 §0.5 verified a cross-repo `namedPointcuts: Map` schema field that does NOT exist. Empirical inspection of the canonical schema (`descriptor-reader/src/main/java/br/unb/cic/rv/descriptor/AspectDescriptor.java`), the JavaMOP-side producer (`javamop/src/main/java/javamop/output/descriptor/DescriptorWriter.java`), and the production JSON fixture (`descriptor-reader/src/test/resources/MultiSpec_1MonitorAspect.json`) proved the schema already exposes a load-bearing `baseAspectExclusions: List<String>` field populated by `DescriptorWriter.defaultBaseAspectExclusions()` with the canonical twelve-entry expansion. The cross-repo schema change is RETIRED; the §4.D / §4.B closures consume the existing field directly. §0.5 is downgraded from "verify cross-repo emission of new field" to "verify production descriptors carry the canonical exclusion list".

**Goal (round-8 empirical revision)**: confirm that production `AspectDescriptor` JSON descriptors carry `baseAspectExclusions: List<String>` populated with the canonical twelve-entry baseline (`["sun..*", "java..*", "javax..*", "com.sun..*", "org.dacapo.harness..*", "org.apache.commons..*", "org.apache.geronimo..*", "net.sf.cglib..*", "mop..*", "javamoprt..*", "rvmonitorrt..*", "com.runtimeverification..*"]`) so the §4.D / §4.B closures can consume the existing field. NO cross-repo schema change is required.

- [ ] 0.5.1 Locate a representative `AspectDescriptor` JSON produced by the current JavaMOP toolchain — start with `results/gh53_smoke_dexlib2/monitors/` or rebuild via `mvn -pl rvsec-mop package` on the sibling repo. The canonical fixture at `descriptor-reader/src/test/resources/MultiSpec_1MonitorAspect.json` may be reused as ground truth — it ships the field with the twelve-entry baseline.
- [ ] 0.5.2 Inspect the JSON for the field `baseAspectExclusions`. Expected: present as `List<String>` (JSON array of strings) with at least the twelve baseline patterns. If present: proceed to §1.
- [ ] 0.5.3 If absent (legacy descriptor produced by a JavaMOP build pre-dating the field): document the production-corpus version drift in `MEMORY.md` and regenerate the descriptors via the current JavaMOP toolchain (`mvn -pl rvsec-mop package` on the sibling repo); the §4.D matcher will throw `LegacyDescriptorException` on empty lists per the G-decision fail-closed contract (INV-INS-97), so legacy descriptors are NOT a silent failure — the closure surfaces them at instrumentation time.
- [ ] 0.5.4 If present with a different shape (e.g. `Map<String, Object>` instead of `List<String>`): document the actual shape, file a JavaMOP-side fix to restore the canonical shape, and pause gh62 until the shape stabilises. This is unlikely — the canonical shape is enforced by `DescriptorReader`'s Jackson binding (`@JsonProperty` + `List<String>` field type) and a divergent JavaMOP emit would fail deserialisation today.
- [ ] 0.5.5 Document the verification outcome (PASS / LEGACY-DESCRIPTOR / SHAPE-DIFFERENT) inline at the top of `tasks.md` as a `<!-- §0.5 outcome: ... -->` comment. Commit if any source change resulted: `chore(gh62): verify baseAspectExclusions in production descriptors (§0.5 PASS — A-decision empirical revision 2026-05-28)` with `refs #62`.

## 0.6 Archive precondition: delete the git-ignored `-s` stray `.aj` artifacts from the `.mop` source dirs (round-11 R11.1)

**Goal**: `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/{jca,generic_new}/MultiSpec_1MonitorAspect.aj` are leftover JavaMOP outputs from a one-off `-s`/`-statistics` run (they carry the `ForkedBooter.runSuitesInProcess` stats-dump advice that the production `-merge` pipeline never emits). They are git-ignored, never committed, not on the production path, and they pollute any `grep`-based demand count (they are the source of the bogus round-10 `execution Source = 1,24,0,28` / `within = 22,13,0,13` figures). Remove them so no audit ever greps them again.

- [x] 0.6.1 Confirm they are git-ignored and untracked (`git -C $RVSEC_HOME/rvsec check-ignore rvsec-mop/src/main/resources/jca/MultiSpec_1MonitorAspect.aj` returns the path; `git ls-files` returns nothing). `aspect/Coverage.aj` is a REAL source aspect — do NOT delete it. <!-- DONE 2026-05-29: both strays ignored by rvsec-mop/.gitignore:2 `*.aj`, untracked (git ls-files empty). Both carry ForkedBooter/MOPStatistics marker = confirmed -s strays. Coverage.aj kept. -->
- [x] 0.6.2 Delete `rvsec-mop/src/main/resources/{jca,generic_new}/MultiSpec_1MonitorAspect.aj` (and any other stray `MultiSpec_*MonitorAspect.aj`/`.json`/`.java` in the `.mop` source dirs). The pipeline regenerates these into `out/`/`results/` per run; nothing reads the in-source copies. <!-- CLOSED-BY-RATIONALE 2026-05-29 (user decision: leave them). Physical deletion SKIPPED — DemandCounter (§3.4) is scoped to *.mop + aspect/Coverage.aj only, so the strays cannot pollute counts; the existing `*.aj` gitignore rule keeps them untracked. No functional impact. -->
- [x] 0.6.3 Add a `.gitignore` rule (or confirm the existing one) covering `src/main/resources/**/MultiSpec_*MonitorAspect.*` so they cannot reappear tracked. <!-- DONE 2026-05-29: existing `*.aj` rule (rvsec-mop/.gitignore:2) already covers the strays — confirmed via git check-ignore -v. No new rule needed. -->
- [ ] 0.6.4 Commit: `chore(gh62): delete git-ignored -s stray .aj artifacts from .mop source dirs (§0.6, R11.1)` with `refs #62` (only if a tracked file or `.gitignore` changed; the deletes themselves touch only ignored files). <!-- N/A 2026-05-29: no tracked file or .gitignore change resulted (existing `*.aj` rule sufficient); the deletes touch only ignored files → no commit per the task's own condition. -->

## 0.7 Archive precondition: audit the 3 `if(...)` sites in `generic_new/` (round-11 R11.5 re-scope — in-weaver lowering, not runtime delegation)

**Goal (round-11 re-scope)**: §4.I lowers `if(<expr>)` directly in the dexlib2 weaver (R11.5 — no runtime helper). The empirical pipeline demand is **3 sites** (generic_new), with only two expression shapes: `o == null` and `!Thread.holdsLock(o)`, where `o` is bound by `target(o)` / `args(o)`. The audit confirms (a) the count is 3 (not 8), (b) every referenced variable is a `target`/`args` binding reachable from `ctx.match` at the weave site (no advice-local variables), and (c) no third shape exists. If all three hold, the in-weaver 2-shape lowering is sufficient; any new shape fails loud (`UnsupportedAspectConstructError`).

<!-- §0.7 audit table (DONE 2026-05-29 — PASS; compiled empirical-monitors/generic_new/MultiSpec_1MonitorAspect.aj):
     | line | full pointcut clause                                                         | <expr>                | var | binding   | class | shape      |
     | 135  | Object_MonitorOwner_bad_wait: call(* Object+.wait(..)) && target(o) && if(…) | !Thread.holdsLock(o)  | o   | target(o) | (a)   | holdsLock  |
     | 140  | Object_MonitorOwner_bad_notify: …notify/notifyAll && target(o) && if(…)      | !Thread.holdsLock(o)  | o   | target(o) | (a)   | holdsLock  |
     | 205  | Comparable_CompareToNullException_badexception: …compareTo && args(o) && if(…)| o == null             | o   | args(o)   | (b)   | null-check |
     count=3 (NOT round-8's 8). Two shapes only (holdsLock, null-check). Every var is target/args-bound (class a/b) — reachable from ctx.match. Zero advice-locals (class c). §0.7.3 → PASS: in-weaver 2-shape lowering sufficient; proceed to §4.I. NOTE: line 205 site is also the §4.T after()throwing site (§4.T.2a composition). -->
- [x] 0.7.1 Enumerate the **3** `if(...)` clauses in the compiled `empirical-monitors/generic_new/MultiSpec_1MonitorAspect.aj` (lines 135, 140, 205). Anchor each by line + the verbatim `<expr>` payload. Confirm the count is 3 (not the round-8 estimate of 8) and that the only shapes are `!Thread.holdsLock(o)` and `o == null`. <!-- DONE: 3 sites at 135/140/205, verbatim exprs captured in audit table above; shapes = {!Thread.holdsLock(o), o == null} only. -->
- [x] 0.7.2 For each site, identify the variable referenced inside `<expr>` and its binding source. Expected: `o` bound by `target(o)` (lines 135/140) or `args(o)` (line 205) — both reachable from `ctx.match` at the weave site. Classify any variable as: (a) `target(name)`-bound; (b) `args(name)`-bound; (c) advice-local (declared inside the advice body, NOT by a pointcut binding). <!-- DONE: 135/140 = target(o) [class a]; 205 = args(o) [class b]. No class (c). -->
- [x] 0.7.3 If every variable is class (a) or (b) — reachable from `ctx.match` — the in-weaver lowering (R11.5) is sufficient: proceed to §4.I. Document the 3-row audit table as a `<!-- §0.7 audit table -->` comment block at the top of `tasks.md`. <!-- DONE: all class a/b → PASS; audit table recorded above. -->
- [x] 0.7.4 If any variable is class (c) — advice-local — `IfGuardEmitter` cannot resolve its register; the site fails loud (`UnsupportedAspectConstructError`). Document the offending site(s) and either (i) extend the 2-shape dispatch if the variable is in fact pointcut-bound under a different name, or (ii) exclude the site and record NOT-NEEDED-with-rationale. (The retired D13 "runtime helper / captured-locals map" resolutions no longer apply — there is no runtime helper.) <!-- N/A 2026-05-29: zero class-(c) sites; no advice-local variables. -->
- [ ] 0.7.5 Commit (only if audit produced source-of-truth documents): `chore(gh62): audit 3 if() sites in generic_new for target/args-bound variables (§0.7 PASS|BLOCKED — R11.5)` with `refs #62`. <!-- audit table lives in tasks.md (rv-android repo); will fold into a progress commit. PUSH DEFERRED. -->

## 1. Demand regeneration FIRST + Deferred-by-design + SHA snapshot (round-8 — single-commit race-condition fix)

**Goal**: regenerate ALL demand counts (both source and pipeline) via the `DemandCounter` Java helper BEFORE producing the deferred-by-design document, so the document's path-α/β classifications are empirically verified. Round-8 ships `deferred.md` AND `deferred.snapshot.sha256` in the same commit (race-condition fix for the round-7 plan that separated them).

- [x] 1.0 **BLOCKER** — execution order: implement `DemandCounter` (detailed spec in §3.4 below) BEFORE running the count regeneration in this task. The helper exposes TWO methods: `countMop(designator, corpus)` walks `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/{aspect,jca,generic,generic_new}/` matching **only `*.mop` files plus `aspect/Coverage.aj`** (round-11 R11.1: it MUST NOT match any `*.aj` build artifact sitting in the `.mop` source dirs — those are git-ignored `-s` stray outputs that inflate execution()/within() counts); `countCompiledAj(designator, corpus)` walks the canonical pipeline corpus `empirical-monitors/{jca,generic,generic_new}/MultiSpec_1MonitorAspect.aj` (freshly compiled via `rv-monitor-generator` WITHOUT `-s`; byte-identical to `results/gh53_smoke_dexlib2/monitors/`). The regex per designator MUST distinguish pointcut use from Java-statement use (e.g. for `if()`, the canonical pattern is `(?:^|&&|\|\|)\s*if\s*\(`).
- [x] 1.1 Read `docs/analise_*.md` (6 cross-LLM reviews + `analise_sintese_macro.md` synthesis) to enumerate every silent-gap, verdict discrepancy, and absorption claim surfaced. Catalogue per AspectJ designator + modifier + advice form. The round-8 audit results (3 empirical investigations: APK AJC inspection, compiled `.aj` audit, `coverage-weaver` overlap) are the primary input for the path-β reclassifications. **K-decision (round-8 2026-05-28)**: `docs/analise_sintese_macro.md` is generated per-session by the cross-LLM review process and may not be present on every workstation/branch. References to it are preserved across artifacts; the load-bearing conclusions are replicated inline in `deferred.md` §Appendix so the empirical evidence is auditable without that file. When reading on a workstation that does not have the synthesis document, fall back to the `deferred.md` Appendix for the same conclusions.
- [x] 1.2 Cross-check the §1.0 canonical counts (BOTH `countMop` and `countCompiledAj`) against the reviewers' independent grep results. Any divergence must be resolved by adjusting the regex and re-running `DemandCounter`. Final counts SHALL be the single source of truth quoted inline in the matrix.
- [x] 1.2a See `## 1.2a` section below — S-decision generic_new pipeline-demand fallback selection (i/ii/iii); the chosen outcome is recorded inline at the top of `tasks.md` as a `<!-- §1.2a outcome: ... -->` comment.
- [x] 1.2b **(round-11 reproducibility pin — INV-INS-93)** For EVERY matrix row, quote the per-designator `java.util.regex.Pattern` literal inline in the matrix AND state the counting rule: (a) per-occurrence vs per-line, and (b) negated-form ownership. The empirical counts only reproduce under specific rules — e.g. §4.O `T+`-owner = 64 requires counting **per-occurrence of the `+.` owner token** (per-line yields 39); §4.TT `target(Type)` = 22 and §4.AT `args(Type)` = 5 **include the negated `!target`/`!args` occurrences**, which §4.N also counts (16) — disambiguate so the 14 negated `!target` sites are owned by exactly ONE row, never double-counted. Bake the chosen rule into `DemandCounter`'s regex map so `testPipelineDemandCountsReproducible` (§6.8) asserts against a deterministic count. Without (a)+(b) pinned, that test has no count to assert.
- [x] 1.3 The `openspec/changes/gh62-aspectj-grammar-coverage/deferred.md` document is already populated for round-8 (see the file). Re-verify each entry's evidence against the live audit outputs from §1.2; update file paths if any artefact moved. Three sections: §1 EXPLICIT-NO-OP (only `around`/`proceed`); §2 NOT-NEEDED (§2.1 path α — 24 entries; §2.2 path β — round-8's 7 newly-reclassified + 8 round-7-inherited entries with absorber + empirical evidence per row); §Appendix The Three Empirical Audits. **P-decision verification 2026-05-28 (cross-LLM meta-review on path-β over-inclusion)**: confirm `deferred.md` §2.1 (path α) contains the five round-8-reclassified items (`handler(...)`, `declare precedence`, aspect inheritance, abstract aspect, privileged aspect — each with explicit "Round-8 reclassification 2026-05-28 (P-decision)" marker), AND confirm §2.2.2 (NOT-NEEDED β) does NOT carry those five items anymore (they were moved out per cross-LLM meta-review consensus that zero-source-demand items belong in α, not β). The P-decision body lives in `deferred.md` lines 64-68 (α entries) + §2.2.2 narrowing note.
- [x] 1.4 **ROUND-8 RACE-CONDITION FIX + L-decision sequencing fix 2026-05-28** — single commit containing BOTH `deferred.md` (final state from §1.3) AND `deferred.snapshot.sha256` (computed from the same `deferred.md` content). **L-decision (cross-LLM meta-review)**: the SHA destination file is under `rvsec-android/rvsec-instrumentation-dexlib2/grammar-tests/src/test/resources/` — a directory created by §3.1 / §3.2 of the grammar-tests Maven submodule scaffold. To avoid a `No such file or directory` error when §1.4 runs before §3.x, §1.4 SHALL explicitly `mkdir -p` the destination directory FIRST. Sequence: (a) finalise `deferred.md` content; (b) `mkdir -p rvsec/rvsec-android/rvsec-instrumentation-dexlib2/grammar-tests/src/test/resources/` (idempotent — succeeds if the directory exists from a previous run; creates it if §3.x has not yet committed it); (c) `sha256sum openspec/changes/gh62-aspectj-grammar-coverage/deferred.md | awk '{print $1}' > rvsec/rvsec-android/rvsec-instrumentation-dexlib2/grammar-tests/src/test/resources/deferred.snapshot.sha256`; (d) `git add` both files plus the new directory's `.gitkeep` if the directory didn't pre-exist; (e) `git commit -m "docs(gh62): deferred-by-design document + frozen SHA-256 snapshot (round-8)"`. Push. This eliminates the round-7 race window where `deferred.md` could be edited between the snapshot generation (§7.4a in round-7) and the post-archive verification, AND the early-round-8 file-not-found sequencing bug between §1.4 and §3.1.

## 1.2a S-decision generic_new pipeline-demand fallback (round-8 2026-05-28 per cross-LLM meta-review)

**Goal**: decide how the matrix's `PipelineDemand` column for `generic_new` is populated, given that the `countCompiledAj` corpus historically covers only the JCA-derived compiled `.aj` files (`results/gh53_smoke_dexlib2/monitors/MultiSpec_1MonitorAspect.aj`). For constructions whose primary demand is in `generic_new/` — notably §4.I = 8 sites, §4.O = ~73 sites, §4.TT = 44 sites, §4.AT = 10 sites — the `PipelineDemand` column may need a fallback.

**Three options ranked**:

- (i) **PREFERRED** — regenerate compiled `.aj` for `generic_new/` via `mvn -pl rvsec-mop package -P generic-new` (if the profile exists on the sibling repo) and add the regenerated files to the §3.4 fixture directory (`grammar-tests/src/test/resources/compiled-aj-fixtures/`) so `countCompiledAj("...", Corpus.GENERIC_NEW)` returns real counts.
- (ii) **FALLBACK** — if the generic_new compile is unavailable on the current workstation, document the matrix `PipelineDemand` columns for generic_new as `(source-level used — compiled .aj unavailable for generic_new on this branch)` AND add `MatrixIntegrityTest.testGenericNewPipelineDemandFallbackDocumented` asserting the fallback annotation appears in the matrix for every generic_new-primary row.
- (iii) **HARD-BLOCK** — refuse to archive until the regenerate happens.

**Round-8 default**: option (ii) — fallback with documented annotation — so the change can archive without a sibling-repo build dependency; option (i) is the post-archive cleanup task.

- [x] 1.2a.1 Select option (i / ii / iii) — round-8 default is (ii).
- [x] 1.2a.2 If (i) selected: regenerate and commit `grammar-tests/src/test/resources/compiled-aj-fixtures/generic_new/*.aj`; update `DemandCounter` corpus enum to include `GENERIC_NEW` with the new fixture path.
- [x] 1.2a.3 If (ii) selected: update §5.2 matrix-population task to apply the documented annotation; add `MatrixIntegrityTest.testGenericNewPipelineDemandFallbackDocumented`; update `testPipelineDemandCountsReproducible` to accept the documented fallback.
- [x] 1.2a.4 If (iii) selected: add a §0 archive-precondition checklist item refusing archive until generic_new compiles are present; pause the change until the sibling-repo build profile is published.
- [x] 1.2a.5 Document the chosen option inline at the top of `tasks.md` as a `<!-- §1.2a outcome: (i|ii|iii) — <one-line rationale> -->` comment.

## 2. Matrix scaffold (no verdicts yet — structure only)

**Goal**: produce `docs/aspectj_grammar_coverage.md` with the canonical column structure including the round-8 `SourceDemand` + `PipelineDemand` split, every required row present, and the `DemandCounter` reference. Verdict and evidence columns are filled with `TBD` for now.

- [x] 2.1 Create `docs/aspectj_grammar_coverage.md` header citing: the AspectJ Programming Guide §"Pointcuts" URL + snapshot date, the AspectJ 5 quick reference URL, the smali-dexlib2 version verified by §0.4. Document the four-value verdict vocabulary with one-paragraph definitions. Round-8 introduction: explain the `SourceDemand` vs `PipelineDemand` split — scope decisions use PipelineDemand (closures ship when `countCompiledAj ≥ 1`).
- [x] 2.2 Add "Demand counting" section referencing both `DemandCounter.countMop()` (source) and `DemandCounter.countCompiledAj()` (pipeline) with the per-designator `java.util.regex.Pattern` quoted inline for reviewer audit. NO inline shell; `MatrixIntegrityTest` invokes the Java helpers directly.
- [x] 2.3 Add stable anchor heading `## Matrix` followed by the table header with columns: `AspectJ syntax | SourceDemand (aspect,jca,generic,generic_new) | PipelineDemand (compiled .aj) | Parser | Matcher | Emitter | Verdict | Evidence | Deferral note`.
- [x] 2.4 Add one row per **classical pointcut designator** in the closed enumeration: `call`, `execution`, `withincode`, `cflow`, `cflowbelow`, `if`, `handler`, `get`, `set`, `staticinitialization`, `initialization`, `preinitialization`, `adviceexecution`, named-pointcut references.
- [x] 2.5 Add sub-semantic rows for `target`, `this`, `args` (binding/type-matching sub-rows per spec.md closed enumeration).
- [x] 2.6 Add one row per **AspectJ 5 annotation pointcut designator**: `@annotation`, `@target`, `@this`, `@args`, `@within`, `@withincode`.
- [x] 2.7 Add one row per **advice form**: `before`, `after`, `after returning`, `after throwing`, `around`.
- [x] 2.8 Add rows for **type-pattern modifiers** with positional sub-rows for `T+`.
- [x] 2.9 Add rows for **SignaturePattern modifiers**: positive visibility, negated visibility, `static`, `final`, `throws ExceptionPattern`.
- [x] 2.10 Add rows for **within-family per-stage delegation**: `within(...)` positive simple, `within(*..Log)` suffix-wildcard, `within(T+)` T+-inside-positive-within, `!within(...)`.
- [x] 2.11 Add rows for **composition operators**: `&&`, `||`, `!`, parentheses.
- [x] 2.12 Add rows for **advice-body reflective API**: `thisJoinPoint`, `thisJoinPointStaticPart`, `thisEnclosingJoinPointStaticPart`, `JoinPoint.getArgs()`, `JoinPoint.getSignature()` + subtypes, `getTarget()/.getThis()`, `getKind()/.getSourceLocation()`.
- [x] 2.13 Add row for **around-advice mechanics**: `proceed(...)`. Verdict prediction: EXPLICIT-NO-OP.
- [x] 2.14 Add rows for **aspect declaration mechanics**: `aspect Foo { ... }`, `pointcut p(): ...` named declaration, abstract aspect + concrete subaspect, aspect inheritance, `declare precedence`, privileged aspect.
- [x] 2.15 Add row for **AspectJ runtime linkage**: `org.aspectj.lang.JoinPoint` family. **Round-8**: prediction `Verdict = NOT-NEEDED β` with `coverage-weaver` as the named upstream absorber.
- [x] 2.16 Commit on `origin/modules`: `docs(gh62): scaffold aspectj grammar coverage matrix (round-8, source+pipeline demand columns, TBD verdicts)` with `refs #62`. Push. <!-- DONE 2026-05-29: created rv-android/docs/aspectj_grammar_coverage.md — 73 rows (exact closed enumeration from spec.md), single `## Matrix` anchor, no dup keys; demand/parser/matcher/emitter/verdict/evidence/deferral = TBD (filled in §1/§5). Committed LOCALLY; PUSH DEFERRED. -->

## 3. `grammar-tests/` Maven submodule scaffold

**Goal**: add the new test-only Maven submodule so the matrix's `Evidence` column can cite test FQNs from §5 onwards.

- [x] 3.1 In `rvsec-android/rvsec-instrumentation-dexlib2/pom.xml`, add `<module>grammar-tests</module>` to `<modules>`. NOT added to the `instr-cli` shade plugin includes.
- [x] 3.2 Create `rvsec-android/rvsec-instrumentation-dexlib2/grammar-tests/pom.xml`. Parent: `rvsec-instrumentation-dexlib2`. Test scope deps (pinned in parent `dependencyManagement`):
  - `pointcut-engine`, `advice-emitter`, `dex-mutator`, **`coverage-weaver`** (round-8 introduction — needed for path-β assertion tests citing `coverage-weaver`'s javadoc as absorber evidence)
  - `org.junit.jupiter:junit-jupiter:${junit-jupiter.version}` (reuse parent property; 5.11.3)
  - `org.junit.platform:junit-platform-launcher:1.11.3` (required by `testSkipCountEqualsZero` — round-8 rename from `testSkipCountEqualsSilentGapCount` since no SILENT-GAP rows remain)
  - `org.commonmark:commonmark:0.24.0` + `org.commonmark:commonmark-ext-gfm-tables:0.24.0`
  - `org.junit-pioneer:junit-pioneer:2.3.0`
  No `main/` source; only `src/test/java/` and `src/test/resources/`.
- [x] 3.3 Create package structure `grammar-tests/src/test/java/br/unb/cic/rv/grammar/`. Add `package-info.java` noting (round-8): this module is the executable oracle for `docs/aspectj_grammar_coverage.md`; tests SHALL be kept in 1:1 correspondence with matrix rows; ZERO `@Disabled` annotations remain post-round-8 (every row has an enabled passing test — COVERED tests assert post-fix behaviour; EXPLICIT-NO-OP tests assert UOE; NOT-NEEDED α tests assert `countMop == 0`; NOT-NEEDED β tests assert `countCompiledAj == 0` plus the named absorber).
- [x] 3.4 Add `grammar-tests/src/test/java/br/unb/cic/rv/grammar/util/DemandCounter.java` (~165 LOC for round-8 — up from the earlier ~150 estimate because round-8 D-decision 2026-05-28 makes the compiled-`.aj` corpus path configurable, with system-property + env-var + fixture-default lookup chain):
  - `countMop(designator, corpus)`: walks source corpora at `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/{aspect,jca,generic,generic_new}/`, returns source-level count.
  - `countCompiledAj(designator, corpus)`: walks the compiled-`.aj` corpus directory, returns post-JavaMOP-compilation count. **D-decision configurable path (round-8 per cross-LLM meta-review)**: the directory is resolved by a three-step lookup chain — (1) JVM system property `gh62.compiled.aj.path` if set; (2) environment variable `GH62_COMPILED_AJ_PATH` if set; (3) the committed fixture directory `grammar-tests/src/test/resources/compiled-aj-fixtures/` shipped with the change as a reproducible baseline (round-8 S-decision: ships at least one canonical compiled `.aj` per corpus so CI runs without `$RVSEC_HOME` access still produce reproducible counts). Hardcoded `results/gh53_smoke_dexlib2/monitors/` is RETIRED as a load-bearing path — it remains a documented fallback only for local developer convenience when neither the property nor the env-var is set AND the fixture directory is missing (which would be a misconfiguration). A directory-existence guard test (`DemandCounterPathGuardTest.compiledAjCorpusDirectoryExists`) SHALL fail early with a diagnostic when the resolved path does not exist, preventing silent vacuous-pass on path-β assertion tests.
  - Reads files via `Files.readString()` and applies compiled `Pattern` per designator. Per-designator regex MUST distinguish pointcut use from Java-statement use. No `ProcessBuilder`, no shell. Symlinks NOT followed.
- [x] 3.5 Add `grammar-tests/src/test/java/br/unb/cic/rv/grammar/util/MatrixMarkdownParser.java` (~60 LOC for round-8): parses the table after `## Matrix` into `record MatrixRow(String syntax, Map<Corpus,Integer> sourceDemand, Map<Corpus,Integer> pipelineDemand, String parserAnchor, String matcherAnchor, String emitterAnchor, Verdict verdict, String evidence, String deferralNote)`. Throws if anchor absent/duplicated.
- [x] 3.6 Add `grammar-tests/src/test/java/br/unb/cic/rv/grammar/util/AspectJDesignators.java` — `Set<String> DESIGNATORS` constant naming every entry in the closed enumeration.
- [x] 3.7 Add `grammar-tests/src/test/java/br/unb/cic/rv/grammar/util/AbsorbingStage.java` (round-8 NEW) — enum of recognised upstream absorbers per `Requirement: Upstream Absorption Verdict`: `JAVA_MOP_COMPILER`, `COVERAGE_WEAVER`, `MONITOR_RUNTIME_DISPATCH_LOOP`, `DESCRIPTOR_READER`, `DEXLIB2_INLINE_EMISSION_MODEL`. Used by path-β assertion tests to declare the absorber via a static field.
- [x] 3.8 Add a smoke test `MavenModuleSmokeTest` asserting `true`. Required to keep the reactor green between commits.
- [x] 3.9 Run `cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-instrumentation-dexlib2 && mvn -pl grammar-tests test -DskipTests=false -am`. Smoke test SHALL pass. Reactor `mvn package` SHALL build SUCCESS.
- [x] 3.10 Commit on `origin/modules`: `feat(gh62): add grammar-tests Maven submodule (round-8 scaffold + DemandCounter dual API + AbsorbingStage enum)` with `refs #62`. Push. <!-- DONE 2026-05-29: created grammar-tests module (pom + DemandCounter + MatrixMarkdownParser + AspectJDesignators[73 keys] + AbsorbingStage + MavenModuleSmokeTest + compiled-aj-fixtures{jca,generic,generic_new}). mvn -pl grammar-tests -am test = BUILD SUCCESS, smoke PASS. DemandCounter regexes sanity-checked vs grep (condition src=64/pipe=0, if-PCD generic_new=3, !within jca=13, exec-positive=0). DEVIATIONS (P1): (1) commonmark/junit-platform-launcher/junit-pioneer pinned INLINE in grammar-tests/pom.xml not parent depMgmt (one-module deps); (2) matrix path resolves via $RVSEC_HOME/rv-android/docs + gh62.matrix.path override (single-repo, two subtrees); (3) MatrixRow holds raw column strings (typed accessors deferred to §6 where populated matrix is parsed). Committed LOCALLY; PUSH DEFERRED. -->

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

## 4.W ~~Positive `within(typePattern)` simple matcher~~ — **SUPERSEDED (round-10 AB-decision 2026-05-29)**

**Empirical evidence**: pipeline POSITIVE `within(...)` count = 0,0,0 across `empirical-monitors/{jca,generic,generic_new}/MultiSpec_1MonitorAspect.aj`. Every `within(` hit is inside `pointcut notwithin()` or `MOP_CommonPointCut(): !within(... RVMObject+) && ...` body declarations — never used as an event predicate by any spec.

**Action**: do NOT execute tasks 4.W.1-4.W.5. The row is reclassified NOT-NEEDED β. The replacement assertion task is §4.W' below.

- [ ] ~~4.W.1~~ SUPERSEDED
- [ ] ~~4.W.2~~ SUPERSEDED
- [ ] ~~4.W.3~~ SUPERSEDED
- [ ] ~~4.W.4~~ SUPERSEDED
- [ ] ~~4.W.5~~ SUPERSEDED

## 4.W' positive `within(typePattern)` NOT-NEEDED β assertion test (round-10 AB-decision)

**Goal**: enable a `grammar-tests` assertion test that pins the round-10 verdict so a future corpus introducing positive `within(...)` triggers `MatrixIntegrityTest` failure.

- [ ] 4.W'.1 Add `WithinPositiveGrammarTest.withinPositiveAbsorptionAssertion` in `grammar-tests/`: assert `DemandCounter.countMop(WITHIN_POSITIVE, {jca,generic,generic_new}) == 0` AND `countMop(WITHIN_POSITIVE, aspect) ≥ 1` (the sole positive consumer is `Coverage.aj`'s `excludedPackages()` macro), `DemandCounter.countCompiledAj(WITHIN_POSITIVE, *) == 0` across all corpora, and `AbsorbingStage.COVERAGE_WEAVER` is named (round-11 R11.2 — NOT `MOP_MACRO_BODY_ABSORPTION`). ~20 LOC.
- [ ] 4.W'.2 Run `mvn -pl grammar-tests test -Dtest=WithinPositiveGrammarTest`; passes.
- [ ] 4.W'.3 Commit: `test(gh62): within(typePattern) positive NOT-NEEDED β assertion (round-10 AB)` with `refs #62`.

## 4.O `T+` in `call()` owner position (round-8 — ~73 sites generic_new → **round-10 empirical: 64 sites**)

**Goal**: extend gh61 parameter-position subtype expansion to owner descriptor matching at `PointcutMatcher.java:153-157`.

- [x] 4.O.1 Audit gh61's `cpsAwareOwnerMatch` and `InheritanceResolver.isAssignableFrom`. ~5 LOC of grep.
- [x] 4.O.2 Extend `PointcutMatcher.matchCall`'s owner check (`:153-157`): recognise `+` suffix; invoke subtype-expansion helper. ~30 LOC. Preserve exact-equals path for non-`+` patterns.
- [x] 4.O.3 Update `CallPointcutGrammarTest.callTSubtypeInOwner`: remove `@Disabled`; assert `call(* javax.crypto.Cipher+.doFinal(..))` against subtype receiver matches.
- [x] 4.O.4 Run tests.
- [x] 4.O.5 Commit: `feat(gh62): T+ in call() owner position subtype expansion (64 sites; row flips COVERED)` with `refs #62`.

## 4.R ~~`T+` in `call()` return position~~ — **SUPERSEDED (round-11 R11.3 — NOT-NEEDED α)**

§4.R.1-§4.R.3 are SUPERSEDED — do NOT execute. Empirical demand for `T+` in `call()` RETURN position is **0** across `.mop`, `aspect/Coverage.aj`, and all three pipeline `.aj` (all subtype polymorphism is owner-position §4.O). No matcher code ships. Replaced by §4.R' below.

## 4.R' `T+` in `call()` return position NOT-NEEDED α assertion test (round-11 R11.3)

- [ ] 4.R'.1 Add `CallPointcutGrammarTest.returnPositionTSubtypeNotNeeded`: assert `DemandCounter.countMop(CALL_RETURN_TSUBTYPE, *) == 0` AND `countCompiledAj(CALL_RETURN_TSUBTYPE, *) == 0` across all corpora (path α — zero demand everywhere, no absorber needed). Matrix row carries `Verdict = NOT-NEEDED α`. ~15 LOC.
- [ ] 4.R'.2 Commit: `test(gh62): T+ in call() return is NOT-NEEDED α (§4.R' assertion, R11.3)` with `refs #62`.

## 4.N `!target(T)` / `!args(T)` parser specialization (round-8 — 32 sites generic_new → **round-10 empirical: 14 `!target` + 2 `!args` = 16 sites**)

**Goal**: extend `PointcutExpressionParser.parseUnary()` to specialize negation of `target(T)`/`args(T)` type-matching beyond just `!within`.

- [ ] 4.N.1 Extend `PointcutExpressionParser.parseUnary()`: add cases for `!target(...)` and `!args(...)` constructing `NegationPC` wrapping inner `TargetPC`/`ArgsPC`. ~20 LOC. Note: if `NegationPC` does not exist, this task includes creating it.
- [ ] 4.N.2 Add `NegationPC` matcher: evaluate inner pointcut; invert verdict. ~20 LOC.
- [ ] 4.N.3 Update `CompositionGrammarTest.negationBeyondWithin` → narrow to `negativeTargetArgsParserSpecialization`; remove `@Disabled`; assert `!target(MyClass)` inverts match.
- [ ] 4.N.4 Run tests. Commit: `feat(gh62): !target/!args parser specialization (16 sites; row flips COVERED)` with `refs #62`.

## 4.V `(T, ..)` trailing-mixed varargs (round-11 empirical: 6 jca in `call()` signatures + the `args(..., ..)` side — R-decision ripple scoping)

<!-- Round-11 narrative correction: the headline pipeline count is 6 (jca, inside `call(...)` signatures: empirical-monitors/jca/MultiSpec_1MonitorAspect.aj:157,162,347,586,596,691). There are ALSO 4 trailing-mixed occurrences inside `args(...)` designators (jca:157,162; generic_new:75,110) — these are functionally COVERED by the SAME closure because §4.V.1a applies the `ParamList` refactor to `ArgsPC.matchParams`, not only `CallPC.matchParams` (see design.md ArgsGrammarTest `args(*, name, ..)` row). The old "14 jca + 2 generic_new" was a source-level estimate. -->


**Goal**: extend `PointcutExpressionParser.isVarargs:271-273` to accept trailing-mixed forms.

**Round-8 R-decision (2026-05-28 per cross-LLM meta-review on §4.V ripple effects)**: the refactor of `splitParams` from `String[]` to `ParamList { List<ParamSpec> head; boolean trailingVarargs; }` is NOT a localised change — it ripples through `CallPC.matchParams` AND `ArgsPC.matchParams` (and any callers consuming the old `String[]` return shape). The LOC estimate is revised UP from ~50 to ~50-80 to honestly account for the call-site updates across both PC classes. The refactor MUST land atomically (all call sites updated in the same commit) to avoid leaving the codebase in a half-shape state.

- [x] 4.V.1 Refactor `splitParams` to return `ParamList { List<ParamSpec> head; boolean trailingVarargs; }`. ~30 LOC for the helper itself.
- [x] 4.V.1a (R-decision new sub-step) Update every call site of `splitParams` atomically: `CallPC.matchParams`, `ArgsPC.matchParams`, and any other consumer (grep `splitParams` to enumerate; expect 2-4 call sites). Each call site that previously consumed `String[]` is rewritten to consume `ParamList` (head positional iteration + trailing flag check). ~20-30 LOC across all call sites combined.
- [x] 4.V.2 Update `CallPC.matchParams`: treat `trailingVarargs=true` as `actualParams.size() >= head.size()` + positional head match + tail accept-any. ~10 LOC of net new logic on top of §4.V.1a refactor.
- [x] 4.V.3 Add `CallPointcutGrammarTest.trailingMixedVarargsMatchHeadAndAcceptRest`: `call(* SecureRandom.getInstance(String, ..))` matches both single-arg and multi-arg forms.
- [x] 4.V.4 Commit: `feat(gh62): (T, ..) trailing-mixed varargs + splitParams ripple refactor (§4.V + R-decision; row flips COVERED)` with `refs #62`. <!-- DONE 2026-05-30: splitParams now returns CallPC.ParamList{List<ParamSpec> head; boolean trailingVarargs}; trailing `..` sets the flag and is dropped from head, covering standalone `(..)` (empty head, match-anything), trailing-mixed `(T, ..)` (pinned head + accept-any tail), exact `()`/`(T,U)`. Files: CallPC.java (+ParamList record, varargs javadoc), PointcutExpressionParser.java (splitParams→ParamList, removed isVarargs + Collections import), PointcutMatcher.java (param block: varargs ⇒ size≥headSize, else ==headSize, single positional head loop), CallPointcutGrammarTest.java (+trailingMixedVarargsMatchHeadAndAcceptRest). splitParams call sites updated atomically: parseCallBody constructor path + method path (the only 2; ArgsPC does not call splitParams — its `..` is dropped in parseArgsBody, so the args-side trailing-mixed rows are functionally covered with no ArgsPC.matchParams to change). Validation: mvn -pl pointcut-engine,grammar-tests -am test = BUILD SUCCESS (pointcut-engine 13+5+13, CallPointcutGrammarTest 3, 0 fail/0 err); full reactor `mvn test` = BUILD SUCCESS, 9/9 modules, 0 failures/0 errors. -->


## 4.X Method-name glob `name*` (round-8 — ~16 sites generic_new → **round-11 empirical: 13 sites**)

**Goal**: replace `expectedName.equals(actualName)` at `PointcutMatcher.java:161-167` with prefix-glob support.

- [x] 4.X.1 Update `PointcutMatcher.matchCall`'s name check: `expectedName.endsWith("*") ? actualName.startsWith(prefix) : expectedName.equals(actualName)`. ~15 LOC.
- [x] 4.X.2 Add `CallPointcutGrammarTest.methodNamePrefixGlob`: `call(* Collection.add*(..))` matches `add`/`addAll`/`addLast` but not `remove`.
- [x] 4.X.3 Commit: `feat(gh62): method-name glob name* (13 sites; row flips COVERED)` with `refs #62`.

## 4.TT `target(Type)` type-matching (round-8 — 44 sites generic_new → **round-10 empirical: 22 sites**)

**Goal**: `PointcutMatcher.java:106-108` currently returns always-match for `TargetPC` regardless of declared `Type`. Implement subtype-aware type checking against the receiver register's declared type.

- [ ] 4.TT.1 Extract `target(Type)` parser path in `PointcutExpressionParser` (distinguish from `target(name)` binding form). Set `Type type;` field on `TargetPC` when arg is a type. ~20 LOC.
- [ ] 4.TT.2 Update `TargetPC` matcher: when `type != null`, check `InheritanceResolver.isAssignableFrom(type, receiverDeclaredType)`; return match iff check passes. Binding form (`name != null`) unchanged. ~30 LOC.
- [ ] 4.TT.3 Add `TargetGrammarTest.targetTypeMatchesByReceiverType`: `target(Cipher)` matches Cipher receiver, not unrelated. Remove `@Disabled`.
- [ ] 4.TT.4 Commit: `feat(gh62): target(Type) type-matching (§4.TT, row flips COVERED)` with `refs #62`.

## 4.AT `args(Type)` type-matching (round-8 — 10 sites generic_new → **round-10 empirical: 5 sites**)

**Goal**: symmetric to §4.TT for argument list.

- [ ] 4.AT.1 Extract `args(Type)` parser path. Set `List<Type> types;` field on `ArgsPC`. ~20 LOC.
- [ ] 4.AT.2 Update `ArgsPC` matcher: when `types != null`, walk positionally over the call's argument descriptors. ~30 LOC.
- [ ] 4.AT.3 Add `ArgsGrammarTest.argsTypeMatchesByArgumentType`. Remove `@Disabled`.
- [ ] 4.AT.4 Commit: `feat(gh62): args(Type) type-matching (§4.AT, row flips COVERED)` with `refs #62`.

## 4.Y `staticinitialization(T+)` synthesis when `<clinit>` is absent + `Signature` delivery (round-8 — **round-10 empirical: 3 sites generic_new + AC-decision Signature sub-closure**)

**Goal**: synthesize a minimal `<clinit>` when `staticinitialization(T+)` matches a class without one **AND** deliver the `org.aspectj.lang.Signature` object expected by `*staticinitEvent(Signature)` since the JavaMOP-compiled advice body invokes `thisJoinPoint.getStaticPart().getSignature()`. Round-10 AC-decision (2026-05-29) — refutes the round-8 NOT-NEEDED β claim for `thisJoinPoint*` after empirical inspection of `empirical-monitors/generic_new/MultiSpec_1MonitorAspect.aj:260,319,328` showed three live `getSignature()` call sites in staticinit advice bodies.

- [ ] 4.Y.1 Add `dex-mutator/src/main/java/br/unb/cic/rv/mutator/StaticInitSynthesizer.java` (~60 LOC): given `ClassDef` without `<clinit>`, append synthesized `<clinit>` containing `return-void`. Flag with debug marker.
- [ ] 4.Y.2 Update `DexWeaver.applyPlan` to invoke synthesizer when `staticinitialization(...)` advice processes a class without `<clinit>`. ~30 LOC.
- [ ] 4.Y.3 Update `StaticInitializationGrammarTest.staticinitializationTSubtype` to assert synthesis path. ~10 LOC test addition.
- [ ] 4.Y.4 **(round-11 R11.5 — fork-free Signature substrate)** Add to **`rvsec-core`** (NOT advice-emitter; NOT a fork change): `org.aspectj.lang.Signature` (interface, 7 methods — `toString`/`toShortString`/`toLongString`/`getName`/`getModifiers`/`getDeclaringType`/`getDeclaringTypeName`; only `getDeclaringType()` is exercised) + `org.aspectj.lang.ClassSignature implements Signature` (one field `Class<?> declaringType` set via constructor; `getDeclaringType()` returns it; the other 6 return `declaringType.getName()`/`0`/empty). ~35 LOC. **A `String` FQN is NOT sufficient** — the monitor body does `Class klass = staticsig.getDeclaringType(); klass.getDeclaredMethod(...)` (`MultiSpec_1RuntimeMonitor.java:1524`), so `getDeclaringType()` MUST return a live `java.lang.Class`. `rvsec-core` is already on the dexlib2 packaging allowlist (`dexlib_instrumentation.py:117-121`), so this ships into the APK without re-introducing aspectjrt.
- [ ] 4.Y.5 **(round-11)** In `StaticInitializationEmitter`, special-case the literal monitorCall arg token `thisJoinPoint.getStaticPart().getSignature()` (today it routes through the generic binding resolver → `UnresolvedBindingException` → the site is silently SKIPPED, `plansSkippedUnresolvedBinding`). At the statically-known `<clinit>` owner, emit `const-class vC, <DeclaringTypeDescriptor>` + `new-instance vS, Lorg/aspectj/lang/ClassSignature;` + `invoke-direct {vS, vC}, ClassSignature.<init>(Ljava/lang/Class;)V` + `invoke-static {vS}, *staticinitEvent(Lorg/aspectj/lang/Signature;)V`, reusing the `CoverageWeaver` const+invoke + `RegisterShifter` register pattern. Thread the declaring class descriptor into `EmitContext` (currently absent; add ~4 LOC at `DexWeaver` where `classDef` is in scope). Verify the three `generic_new` sites all receive a `ClassSignature`. ~70 LOC weaver-side.
- [ ] 4.Y.6 **(round-11)** Add `StaticInitializationGrammarTest.signatureDeliveryForStaticinitEvent`: synthesize a class without `<clinit>`, match a `staticinitialization(T+)` pointcut with a generic_new-shaped advice body invoking `getSignature()`, assert (a) `<clinit>` was synthesized, (b) the woven `*staticinitEvent` call receives a `ClassSignature`, (c) **`getDeclaringType() == Foo.class`** (the matched class — NOT merely non-null). ~25 LOC.
- [ ] 4.Y.7 Commit: `feat(gh62): synthesize <clinit> + fork-free Signature delivery via rvsec-core ClassSignature (3 sites, R11.5; row flips COVERED)` with `refs #62`.

## 4.T `after() throwing(...)` end-to-end install with range-splitting (round-8 — 2 sites generic_new → **round-10 empirical: 1 site** + Q-decision LOC revision + F-decision range-splitting policy)

**Goal**: implement `TRY_CATCH_WRAP` in `DexWeaver.applyPlan` (currently `:560-566` discards silently).

**Round-8 Q-decision (2026-05-28 per cross-LLM meta-review on §4.T LOC underestimation)**: the early-round-8 LOC estimate of ~80 LOC was insufficient for the DEX try-block surgery needed under nested-try-catch edge cases. Revised estimate: **~150-200 LOC**, accounting for range-splitting, RegisterShifter coordination, handler-ordering reshuffle, and `MethodImplementationBuilder` API friction.

**Round-8 F-decision (2026-05-28 per cross-LLM meta-review on §4.T policy)**: when the matched invoke sits inside one or more pre-existing user try-blocks, the weaver applies **range-splitting** (NOT nested-wrapping). Each enclosing user try-block is split at the matched invoke into three sequential ranges: head segment `[start, invoke)` preserving original handlers; matched-invoke range `[invoke, invoke+1)` carrying BOTH the new `after-throwing` handler (listed FIRST so it fires before user catch) AND the original handlers; tail segment `[invoke+1, end)` preserving original handlers. The new handler block starts with `move-exception vException` (ART invariant) and ends with `throw vException` (re-throw so user catch still sees the exception). Nested-wrapping produces overlapping ranges that ART's verifier rejects; range-splitting preserves strictly-nested layout. See design.md D14 for the full rationale and edge cases.

- [ ] 4.T.1 Replace `DexWeaver.java:560-566`'s `case TRY_CATCH_WRAP: case REPLACE: break;` with the real installer. Sub-steps: (a) enumerate every enclosing try-block covering the matched invoke offset; (b) for each enclosing block, apply the range-splitting transformation per F-decision (split into head + matched-invoke + tail; the matched-invoke range carries the new handler FIRST + original handlers in original order); (c) allocate fresh exception register honouring `RegisterShifter` (gh61) — the shifter's emit-plan covers the new handler block so register liveness analysis remains consistent across the split ranges; (d) emit `move-exception vException` as the new handler block's first instruction (ART invariant); (e) emit the advice invocation; (f) emit `throw vException` as the new handler block's last instruction (re-throw); (g) serialise the resulting try-blocks via dexlib2 `MethodImplementationBuilder` in start-offset order. ~120-160 LOC.
- [ ] 4.T.2 Audit interaction with nested try-catch via a dedicated unit test, NOT just the §4.22 robustness test: add `DexWeaverNestedTryCatchTest.afterThrowingInsideExistingTryBlockSplitsRangesCleanly` exercising the policy with a synthetic fixture asserting (a) ART installation succeeds (no VerifyError); (b) when the call throws an exception that matches the user catch, both the new advice handler AND the user catch fire in order (new advice FIRST, then user catch); (c) when the call throws an exception that the user catch does not match, the new advice handler still fires and the exception propagates to the caller. ~30 LOC.
- [ ] 4.T.2a **(round-11 M1 — §4.T×§4.I composition on the shared join point)** The SOLE `after() throwing` site (`Comparable_CompareToNullException_badexception`, `empirical-monitors/generic_new/MultiSpec_1MonitorAspect.aj:294`) shares its pointcut with the §4.I `if(o == null)` guard (`:205`) — the two closures co-reside on ONE join point. Ensure the §4.I guard gates the §4.T handler-side advice invoke (not only a `before`/`after returning` invoke), so the after-throwing advice fires only when `o == null` (AspectJ binds the advice by the FULL pointcut, including the `if`). Coordinate with §4.I.2: `IfGuardEmitter` MUST wrap the handler-side emit plan, not only the normal-flow plan. Add `DexWeaverIfGuardedAfterThrowingTest`: assert the after-throwing advice fires when `o == null` and is skipped when `o != null`. ~25 LOC. (The bipartite gate validates §4.T and §4.I via separate fixtures; this is the missing composition coverage.)
- [ ] 4.T.3 Update `AdviceFormGrammarTest.afterThrowingAdvice` (or new `AfterThrowingGrammarTest.installsTryRangeAndHandler`): assert post-fix bytecode + ART verify. Also exercise the non-nested (simpler) case as a baseline.
- [ ] 4.T.4 Run tests.
- [ ] 4.T.5 Commit: `feat(gh62): after() throwing(...) try-range + range-splitting policy (1 site; F/Q-decisions; row flips COVERED)` with `refs #62`.

## 4.D `NamedRefPC` resolver via the EXISTING `baseAspectExclusions` field (round-8 empirical revision 2026-05-28 — A-decision + G-decision + O-decision)

**Round-8 ORDERING REVISION (O-decision)**: §4.D now PRECEDES §4.B because §4.B consumes §4.D's resolved `BaseAspect.notwithin` reference. The early-round-8 task numbering listed §4.B before §4.D but the dependency arrow points the other way; this section is structurally moved up. The §4.B section follows immediately after.

**Goal (round-8 empirical revision)**: implement `NamedRefPC` matching so that the literal name `BaseAspect.notwithin` resolves against the EXISTING `AspectDescriptor.baseAspectExclusions: List<String>` field (populated by `javamop.output.descriptor.DescriptorWriter#defaultBaseAspectExclusions()` with the canonical twelve-entry expansion). Any other `NamedRefPC` name fails closed with `UnresolvedNamedRefException`; an empty exclusions list fails closed with `LegacyDescriptorException`. The early-round-8 plan for a cross-repo `namedPointcuts: Map<String, PointcutExpression>` schema field is RETIRED — empirical inspection 2026-05-28 (see §0.5) proved the existing field already carries the required data. LOC drops from the earlier ~120 estimate to ~30-40.

- [x] 4.D.0 **(round-11 — BLOCKER; closes the §4.B/§4.D integration gap)** In `dex-mutator/.../DexWeaver` (the per-advice match loop, ~`:332`), BEFORE matching, parse `descriptor.getCommonPointcut()` ONCE per descriptor (cache it alongside `parseCached`) into `PointcutExpression commonAst`, and match each advice against `CombinedPC(AND, commonAst, parseCached(advice))` instead of `parseCached(advice)` alone. **Rationale**: verified at code level — `DexWeaver.parseCached` (`:539`) parses ONLY `advice.getExpression()`; `descriptor.getCommonPointcut()` and `descriptor.getBaseAspectExclusions()` have ZERO production call-sites (test-only at `DescriptorReaderTest.java:40`); `PointcutMatcher.match` (`:75`) takes no descriptor; and the `BaseAspect.notwithin()`/`!within(...)` clauses live ONLY in `commonPointcut`, never in the advice `expression`. Without this step the production parser never constructs a `NamedRefPC` node, so §4.D/§4.B resolve a node that never exists and the exclusion filter is silently dropped. This makes §4.D/§4.B reachable in production. Add `DexWeaverCommonPointcutCompositionTest`: (a) a class under `mop..*` yields zero matches despite a matching call-site signature; (b) a class outside all exclusions still matches; (c) `commonPointcut` is parsed once per descriptor. ~25 LOC. **MUST land with (or before) §4.D — §4.D/§4.B are inert without it.**
- [x] 4.D.1 Add `UnresolvedNamedRefException` and `LegacyDescriptorException` in `pointcut-engine/src/main/java/br/unb/cic/rv/pointcut/`. Both carry the descriptor's `aspectName` + the unresolved name (or empty-list cause). ~15 LOC.
- [x] 4.D.2 Plumb the active `AspectDescriptor` through `pointcut-engine/.../PointcutMatcher.Context` so the matcher can read `descriptor.getBaseAspectExclusions()`. ~10 LOC.
- [x] 4.D.3 Rewrite `NamedRefPC` matching: (a) if `name.equals("BaseAspect.notwithin")` and `ctx.descriptor.getBaseAspectExclusions().isEmpty()`, throw `LegacyDescriptorException`; (b) if `name.equals("BaseAspect.notwithin")` and the list is non-empty, delegate to `BaseAspectExpander` (§4.B) and substitute the composed matcher; (c) for any other `name`, throw `UnresolvedNamedRefException` (round-8 G-decision: fail-closed replaces the round-7 always-match-with-WARN trap). ~15 LOC.
- [x] 4.D.4 Add `NamedRefResolverTest.baseAspectNotwithinExpansion` (asserts successful expansion against the canonical twelve-entry list), `.unrecognisedNameFailsClosed` (asserts `UnresolvedNamedRefException` for e.g. `"adviceexecution"` or `"FooBar.bar"`), `.emptyExclusionsFailsClosed` (asserts `LegacyDescriptorException` when the list is empty).
- [x] 4.D.5 Commit: `feat(gh62): NamedRefPC resolves BaseAspect.notwithin via baseAspectExclusions (round-8 A/G/O-decision empirical revision 2026-05-28; row flips COVERED; fail-closed)` with `refs #62`.

## 4.B `BaseAspect.notwithin()` macro expansion (round-8 — 1 jca + 1 generic_new; consumes §4.D resolution)

**Goal**: implement `BaseAspectExpander` that consumes `AspectDescriptor.getBaseAspectExclusions()` (the canonical `List<String>` of twelve package patterns) and returns a composed AND-chain of `NotWithinPC(pattern)` matchers — one per list entry. Returns the single `NotWithinPC` when the list has one entry (no degenerate AND-of-one). Round-8 empirical revision drops the LOC estimate from ~50-80 to ~15-20 because the input is already pre-expanded.

- [x] 4.B.1 Implement `BaseAspectExpander` in `pointcut-engine/src/main/java/br/unb/cic/rv/pointcut/`: single static method `public static PointcutExpression expand(List<String> exclusions)` returning a `NotWithinPC` (for N=1) or a `CombinedPC(AND, ...)` chain (for N≥2). ~15-20 LOC.
- [x] 4.B.2 Wire the expander into the §4.D `NamedRefPC` matcher dispatch (already done in 4.D.3.b).
- [x] 4.B.3 Add `NamedReferenceGrammarTest.baseAspectNotwithinExpandsTwelveExclusionsList` (round-8 Z-decision INV-INS-101 per cross-LLM meta-review): (a) N=12 canonical expansion against `["sun..*", "java..*", "javax..*", "com.sun..*", "org.dacapo.harness..*", "org.apache.commons..*", "org.apache.geronimo..*", "net.sf.cglib..*", "mop..*", "javamoprt..*", "rvmonitorrt..*", "com.runtimeverification..*"]` — assert each entry is matched by a `NotWithinPC` node in the composed expression; (b) N=2 smallest non-degenerate AND-chain — assert the composition shape; (c) N=1 degenerate — assert the single `NotWithinPC` is returned (no AND-of-one); (d) N=0 empty — assert §4.D throws `LegacyDescriptorException` (verified via `assertThrows`).
- [x] 4.B.4 Commit: `feat(gh62): BaseAspect.notwithin() expansion via baseAspectExclusions (§4.B + Z-decision multi-entry test; row flips COVERED)` with `refs #62`.

## 4.E ~~`execution(...)` real matcher + emitter~~ — **SUPERSEDED (round-10 AA-decision 2026-05-29)**

**Empirical evidence**: pipeline POSITIVE `execution(...)` count = 0,0,0 across `empirical-monitors/{jca,generic,generic_new}/MultiSpec_1MonitorAspect.aj`. The only `execution(` substring hits in any of the three compiled aspects are inside `!adviceexecution()` in `MOP_CommonPointCut`. No `.mop` spec — present or surveyed — produces a positive `execution(...)` clause at pipeline level; the JavaMOP compiler absorbs source-level `execution()` into matching `call()` events. The round-8 "defensive shipping" rationale is dominated by P1 (No speculative features).

**Action**: do NOT execute tasks 4.E.1-4.E.6. The row is reclassified NOT-NEEDED β. The replacement assertion task is §4.E' below.

- [ ] ~~4.E.1~~ SUPERSEDED
- [ ] ~~4.E.2~~ SUPERSEDED
- [ ] ~~4.E.3~~ SUPERSEDED
- [ ] ~~4.E.4~~ SUPERSEDED
- [ ] ~~4.E.5~~ SUPERSEDED
- [ ] ~~4.E.6~~ SUPERSEDED

## 4.E' `execution(...)` NOT-NEEDED β assertion test (round-10 AA-decision)

**Goal**: enable a `grammar-tests` assertion test that pins the round-10 verdict so a future corpus introducing positive `execution(...)` triggers `MatrixIntegrityTest` failure and forces amendment.

- [ ] 4.E'.1 Add `ExecutionPointcutGrammarTest.executionPositiveAbsorptionAssertion` in `grammar-tests/`: assert `DemandCounter.countMop(EXECUTION_POSITIVE, {jca,generic,generic_new}) == 0` AND `countMop(EXECUTION_POSITIVE, aspect) ≥ 1` (the sole consumer is `Coverage.aj:50` `execution(* *.*(..))`), `DemandCounter.countCompiledAj(EXECUTION_POSITIVE, *) == 0` across all corpora, `AbsorbingStage.COVERAGE_WEAVER` named (round-11 R11.2 — NOT `JAVAMOP_COMPILER_CALL_REWRITE`; JavaMOP emits `execution()` verbatim), and `empirical-monitors/` evidence files present. ~25 LOC.
- [ ] 4.E'.2 Run `mvn -pl grammar-tests test -Dtest=ExecutionPointcutGrammarTest`; passes.
- [ ] 4.E'.3 Commit: `test(gh62): execution(...) NOT-NEEDED β assertion (round-10 AA)` with `refs #62`.

<!-- Round-9 §4.E content preserved below for archive-history only — DO NOT EXECUTE these tasks; superseded by round-10 AA-decision above.

**Goal (round-9)**: replace the `Match.empty(ex)` placeholder at `PointcutMatcher.matchExecution:307-313` with a real matcher that filters by method signature pattern (name + owner + params + return), AND ship `ExecutionMatcherEmitter` integrating with `DexWeaver`'s method-execution weave path. **Round-8 user decision**: even though the current compiled `.aj` corpora show zero positive consumers of `execution(...)` outside the absorbed `Coverage.aj`, shipping the full closure now (matcher + emitter, ~230 LOC) is preferred over deferring as NOT-NEEDED β — future MOP specs that use `execution(...)` positively will work without re-opening this change. `Coverage.aj`'s `execution(* *.*(..))` form remains absorbed by `coverage-weaver` (not consumed by dexlib2); §4.E is exercised by synthetic fixtures in grammar-tests.
-->

<!-- Round-9 §4.E task body preserved as commented archive history below for diff transparency:

- [ ] 4.E.1 Implement `ExecutionPC` matcher in `pointcut-engine/` (sibling of `CallPC`): walks method body declaration descriptors against the pattern; supports `*` wildcards, `..` standalone+trailing-mixed (via §4.V), `T+` (via §4.O/R), method-name glob (via §4.X). ~80 LOC.
- [ ] 4.E.2 Implement `ExecutionMatcherEmitter` in `advice-emitter/`: the emit path differs from `call()` because the join point is the method body's entry/exit, not a call site. Hook into `DexWeaver`'s method-execution weave path; emit advice invocation at method entry (for `before`) or all method-exit points (for `after`). **X-decision 2026-05-28 (cross-LLM meta-review on `after()` semantics)**: `after()` SHALL emit at ALL exit points — every `return`/`return-void`/`return-object` instruction AND every uncaught-throw exit (the latter via the same range-splitting + handler installation pattern as §4.T per F-decision). This is the FULL `after()` semantics (after returning + after throwing), NOT the narrow returning-only subset that the round-7 placeholder assumed. The `after returning` and `after throwing` specialisations are sub-cases that the emit-plan distinguishes via the advice-form discriminator. ~150 LOC.
- [ ] 4.E.3 Wire `ExecutionPC` through `PointcutMatcher.matchExecution`; remove the `Match.empty(ex)` placeholder. ~10 LOC.
- [ ] 4.E.4 **Dual-instrumentation algorithm (round-8 E-decision 2026-05-28 per cross-LLM meta-review on §4.E.4 underspecification)**: when a method is matched by both a `call()` MOP pointcut at one or more call sites AND an `execution()` pointcut at the method body, emit one advice invocation per **distinct (pointcut, advice-form, injection-site)** triple — NOT a deduped single invocation. The emit-plan dedup key SHALL be `dedup_key = sha1(emitter_class + ":" + advice_form + ":" + ifId + ":" + pointcut_AST_hash + ":" + resolved_MethodReference_fully_qualified)` (Claude meta-review refinement). Algorithm:
  - (a) Build the per-method emit-plan list by running both the `call()` matcher (returns plans rooted at call-site offsets inside the method body) and the `execution()` matcher (returns plans rooted at the method entry offset for `before`, at every return offset for `after`).
  - (b) For each pair of plans (p1, p2), compute `dedup_key(p1)` and `dedup_key(p2)`.
  - (c) Plans p1 and p2 collapse to a single emitter invocation ONLY IF `dedup_key(p1).equals(dedup_key(p2))` AND `p1.injection_offset == p2.injection_offset` (same DEX-level injection site).
  - (d) Plans p1 and p2 that share `dedup_key` but inject at distinct offsets (e.g. `call()` at offset 0x12 inside the method whose body is matched by `execution()` at offset 0x00) MUST emit two distinct invocations — they are semantically distinct join points (one fires at a specific call site, the other at the method body).
  - (e) Concretely this means: a method matched by `call(* Foo.bar(..))` at one internal call to `bar()` AND by `execution(* *.*(..))` at its entry will emit TWO invocations (advice fires once when the internal call happens, once at method entry). A method matched by `execution(* Foo.method(..))` (entry) AND also matched at the SAME entry offset by a degenerate `call()` plan (which cannot happen with current matchers but is theoretically representable) would collapse to ONE invocation.
  - LOC: ~30-40 (was 20 — the algorithm is more nuanced than the early-round-8 placeholder).
- [ ] 4.E.5 Add `grammar-tests/.../ExecutionPointcutGrammarTest`:
  - `executionUniversalMatchesEveryMethod` — `execution(* *.*(..))` matches every method body in a synthetic fixture class.
  - `executionByOwnerName` — `execution(* Cipher.doFinal(..))` matches only `Cipher.doFinal`, not other methods.
  - `executionWithTPlusOwner` — subtype expansion via `InheritanceResolver` works for `execution(* Cipher+.doFinal(..))`.
  - `executionEmitsAtEntryForBeforeAdvice` — assert woven bytecode has the advice invocation immediately after the method's entry prologue.
  - `executionEmitsAtAllReturnPathsForAfterAdvice` — assert every `return`/`return-void`/`return-object` instruction is preceded by the advice invocation.
  - `executionDualInstrumentationNoDouble` — synthesise a method matched by BOTH a `call()` MOP pointcut AND an `execution()` pointcut; assert the woven bytecode has one advice invocation per pointcut (not two for the same site).
  - Remove `@Disabled` from existing scaffold methods (round-7 had stubs).
- [ ] 4.E.6 Commit: `feat(gh62): execution(...) real matcher + emitter (§4.E RESTORED, row flips COVERED)` with `refs #62`.
-->

## 4.I `if(...)` AspectJ PCD via fork-free in-weaver 2-shape lowering (round-11 R11.5 — D13 RETIRED; **3 sites generic_new**)

**Goal**: 3 sites in generic_new, only two expression shapes: `o == null` and `!Thread.holdsLock(o)`, where `o` is bound by `target(o)`/`args(o)`. Lower the guard **entirely in the dexlib2 weaver** by completing the existing `IfGuardEmitter.emit()` stub. NO JavaMOP/RV-Monitor fork change.

**Round-11 R11.5 — D13 RETIRED**: the round-8 runtime-helper-delegation design (`MonitorRuntime.evaluateIf(int, Object[])` switch-case generated by `MonitorRuntimeIfHelperEmitter`, content-hashed `ifId`, shared `IfRuntimeAbi`) required code generated on the fork side — and `evaluateIf`/`ifId`/`MonitorRuntimeIfHelperEmitter`/`IfRuntimeAbi` exist in **neither** the JavaMOP nor the RV-Monitor fork (confirmed by source grep). Under the firm "no fork change" constraint, that architecture is impossible. It is replaced by direct in-weaver lowering of the two corpus shapes, with a fail-loud default for anything else. This is NOT the general Java sub-grammar parser round-7 proposed (and 6/6 reviews rejected) — it is a 2-shape closed dispatch. The existing `IfGuardEmitter` (today a stub that only reserves a scratch register) is completed; no parallel class ships (P3).

**Inputs already available at emit time** (no new plumbing): the bound register for `o` is in `ctx.match` (`target(o)` → `match.targetRegister`; `args(o)` → `match.argBindings`); the expression text is in `IfPC.javaExpression`; the branch label uses `BuilderInstruction21t` + `MutableMethodImplementation.newLabelForIndex(...)` (proven in `RegisterShifter`).

- [ ] 4.I.0 **(precondition)**: §0.7 audit of the 3 `if(...)` sites MUST be PASS before §4.I.1 — confirms count = 3, both shapes are `o==null`/`!Thread.holdsLock(o)`, and every referenced var is a `target`/`args` binding (no advice-locals). If a third shape or an advice-local appears, pause and extend the dispatch (or fail-loud).
- [ ] 4.I.1 In `PointcutExpressionParser`, ensure `IfPC` carries the raw `<expr>` text (`javaExpression`). No `ifId`, no hash. ~10 LOC (likely already present — verify).
- [ ] 4.I.2 **Complete the EXISTING `IfGuardEmitter.emit()` body** (`advice-emitter/src/main/java/br/unb/cic/rv/emitter/IfGuardEmitter.java`): dispatch on the `IfPC.javaExpression` shape —
      (a) `<bound> == null` → resolve `<bound>` to its register from `ctx.match`, emit `if-nez vBound, :skip_monitor`;
      (b) `!Thread.holdsLock(<bound>)` → emit `invoke-static {vBound}, Ljava/lang/Thread;->holdsLock(Ljava/lang/Object;)Z` + `move-result vGuard` + `if-nez vGuard, :skip_monitor`;
      (c) delegate to the inner advice emitter; emit `:skip_monitor` after the delegated plan so the monitor invoke is bypassed exactly when the guard is false;
      (d) any other shape → throw `UnsupportedAspectConstructError` (fail-loud, no silent always-match).
      ~60 LOC. No runtime jar, no fork, no `MonitorRuntime` call.
- [ ] 4.I.3 Reuse the existing `target`/`args` binding-name → register resolution (e.g. the `extractSingleName`/`extractCommaList` logic in `MonitorInvokeBuilder.resolveBindings`) to map the variable inside `if(...)` to its register. No new resolver. ~10 LOC of reuse.
- [ ] 4.I.4 `PointcutMatcher` keeps routing `IfPC` through `EmitterDispatch` → `ifGuard.wrapping(base)` (already wired); the matcher no longer needs to treat `IfPC` as always-match-at-runtime since the guard now actually gates. ~5 LOC review.
- [ ] 4.I.5 Add `IfGuardLoweringTest` (replaces the retired `IfRuntimeDelegationTest`): assert (a) `nullCheckShapeLowersToIfNez`; (b) `holdsLockShapeLowersToInvokeStaticAndBranch`; (c) `unsupportedShapeFailsLoud` (throws `UnsupportedAspectConstructError`); (d) `guardSkipsMonitorWhenFalse` — the monitor invoke is bypassed exactly when the guard is false, for both shapes. ~50 LOC.
- [ ] 4.I.6 Commit: `feat(gh62): if(...) PCD via fork-free in-weaver 2-shape lowering in IfGuardEmitter (R11.5; D13 retired; row flips COVERED)` with `refs #62`.

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

## 4.JP' ~~`thisJoinPoint*` bindings NOT-NEEDED β assertion test~~ — **REMOVED (round-10 AC-decision 2026-05-29)**

**Empirical evidence refuting the absorption claim**: `empirical-monitors/generic_new/MultiSpec_1MonitorAspect.aj` contains three live `thisJoinPoint.getStaticPart().getSignature()` sites in staticinit advice bodies:
- line 260 (`Collection_HashCode_staticinitEvent`)
- line 319 (`Serializable_NoArgConstructor_staticinitEvent`)
- line 328 (`URLConnection_OverrideGetPermission_staticinitEvent`)

The round-8 composite-absorption claim (JavaMOP + Coverage.aj) is partially valid (Coverage.aj IS absorbed by `coverage-weaver`), but `thisJoinPoint.getStaticPart().getSignature()` is NOT absorbed — JavaMOP retains it as the `Signature` argument for `*staticinitEvent(Signature)`. The capability is REACTIVATED inside §4.Y as the Signature-delivery sub-closure (§4.Y.4, §4.Y.5, §4.Y.6).

**Action**: do NOT execute 4.JP'.1 or 4.JP'.2. The path-β test is removed from `AbsorptionClaimsContractTest` aggregation (see design.md INV-INS-96 round-10 update). The COVERED behaviour is verified by §4.Y.6 instead.

- [ ] ~~4.JP'.1~~ SUPERSEDED
- [ ] ~~4.JP'.2~~ SUPERSEDED

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

**Goal**: add `MatrixIntegrityTest` enforcing matrix↔code↔deferred consistency at every CI run, per INV-INS-88..100. Round-8 introduces new tests for the path-β absorber contract (INV-INS-96), the `baseAspectExclusions` schema (INV-INS-97 — round-8 A-decision: the early-round-8 `namedPointcuts` schema test is RETIRED), and the `if(...)` in-weaver 2-shape lowering (INV-INS-98 — round-11 R11.5; runtime delegation RETIRED).

- [ ] 6.1 `MatrixIntegrityTest.testEveryDesignatorHasMatrixRow` — set equality between matrix-row syntaxes and `AspectJDesignators.DESIGNATORS`. INV-INS-88.
- [ ] 6.1a `MatrixIntegrityTest.testVerdictMatchesWorstOfPipeline` — re-compute verdict per worst-of-pipeline + absorption-override rule; assert declared verdict matches. INV-INS-89.
- [ ] 6.2 `MatrixIntegrityTest.testVerdictsAreValid` — every verdict ∈ `{COVERED, SILENT-GAP, EXPLICIT-NO-OP, NOT-NEEDED}`; for NOT-NEEDED assert path α (source demand sum == 0 AND parser/matcher MISSING) OR path β (Evidence matches `upstream-stage:.+\s+demand-source:.+\s+test-fqn:.+`). INV-INS-89.
- [ ] 6.3 `MatrixIntegrityTest.testCoveredRowsCiteEnabledPassingTests` — every COVERED row's Evidence FQN resolves to `@Test` non-`@Disabled` method (walk hierarchy for inherited `@Disabled`). INV-INS-90.
- [ ] 6.4 `MatrixIntegrityTest.testNonCoveredRowsAppearInDeferredDocument` — every non-COVERED matrix row appears in `deferred.md` (parsed via commonmark-java); active-then-archive path fallback for the deferred file location. The round-7 `testSilentGapRowsHaveDisabledTestAndLedgerEntry` is dropped (no SILENT-GAP rows post-round-8; the ledger is gone). INV-INS-91.
- [ ] 6.5 `MatrixIntegrityTest.testEnabledTestsResolveToValidMatrixRow` — round-8 rename of round-7's `testEnabledTestsResolveToCoveredOrExplicitNoOpRow`. Every enabled `@Test` in `br.unb.cic.rv.grammar.*GrammarTest` resolves to a matrix row with `Verdict ∈ {COVERED, EXPLICIT-NO-OP, NOT-NEEDED}` — NOT-NEEDED is enabled in round-8 (was disabled in round-7). The `robustness` subpackage is structurally excluded. INV-INS-92.
- [ ] 6.6 `MatrixIntegrityTest.testNoDisabledTestsRemain` — round-8 replacement of round-7's `testDisabledTestsResolveToSilentGapRow`. Asserts ZERO `@Disabled` annotations in `br.unb.cic.rv.grammar.*GrammarTest`. INV-INS-92.
- [ ] 6.7 `MatrixIntegrityTest.testSkipCountEqualsZero` — round-8 replacement of round-7's `testSkipCountEqualsSilentGapCount`. Asserts the JUnit Platform discovery's disabled count == 0. INV-INS-92.
- [ ] 6.8 `MatrixIntegrityTest.testSourceDemandCountsReproducible` and `testPipelineDemandCountsReproducible` — invoke `DemandCounter.countAllMop()` and `.countAllCompiledAj()`; diff against matrix's two demand columns. INV-INS-93.
- [ ] 6.8a `MatrixIntegrityTest.testRoundEightClosuresAreCovered` — method name retained for cross-commit stability; it now asserts the **eleven round-11 closures**. For every matrix row covered by the **eleven round-11 in-change closures** (§4.{O,N,V,X,TT,AT,Y,T,B,D,I} — §4.E/§4.W NOT-NEEDED β [coverage-weaver]; §4.R NOT-NEEDED α [R11.3]; §4.JP folded into §4.Y), assert `Verdict == COVERED` and Evidence FQN resolves to enabled passing test. INV-INS-94.
- [ ] 6.8b `MatrixIntegrityTest.testClosureLocFootprintMatchesMatrixDelta` (advisory; non-blocking) — log LOC delta per closure commit. INV-INS-95.
- [ ] 6.8c `MatrixIntegrityTest.testNoSilentGapRowsRemain` — assert no matrix row carries `Verdict = SILENT-GAP`. INV-INS-91 (round-8).
- [ ] 6.8d **REMOVED in round-8** — round-7's `testInstrCliJarContainsSubstrate` is dropped (no substrate ships in round-8).
- [ ] 6.8e `MatrixIntegrityTest.testDeferredDocumentIsFrozenPostArchive` — read `deferred.snapshot.sha256`; compute SHA-256 of live `deferred.md`; assert equality. INV-INS-100. **Round-8 race-condition fix**: the snapshot is created in the same commit as the final `deferred.md` content (§1.4), eliminating the round-7 race window.
- [ ] 6.8f `AbsorptionClaimsContractTest` (round-8 NEW, INV-INS-96 enforcement; round-10 updated; round-11 completed) — aggregates **all** path-β assertion tests (INV-INS-96 says "every NOT-NEEDED β row"): §4.G'/S'/A'/RT'/CV'/WW' (round-8) **+ §4.E' (round-10 AA-decision) + §4.W' (round-10 AB-decision) + `AspectDeclarationGrammarTest.aspectFooAbsorbedByDescriptorReader` + `AspectDeclarationGrammarTest.namedPointcutDeclarationAbsorbedByDescriptorReader` (round-11 — the `aspect Foo {…}` and `pointcut p(): …` β rows from `deferred.md` §2.2.2 lines 124-125, absorber = JavaMOP-descriptor-emit / `DescriptorReader`; previously omitted, which left INV-INS-96's "every" unsatisfied at 8 of 10)**; §4.JP' is REMOVED from aggregation (round-10 AC-decision: capability reactivated as §4.Y Signature-delivery sub-closure, COVERED). For each, verifies THREE properties: (a) source demand ≥ 1, (b) pipeline demand == 0, (c) named absorber file/module exists with documented evidence anchor. Fails the build if any property changes (silent regression guard).
- [ ] 6.8g `MatrixIntegrityTest.testBaseAspectExclusionsSchemaPresent` — round-8 NEW (INV-INS-97 empirical revision 2026-05-28). Asserts `AspectDescriptor` class has a `baseAspectExclusions` field of type `List<String>` (the EXISTING field populated by `DescriptorWriter.defaultBaseAspectExclusions()`); asserts `DescriptorReader` parses it from the canonical fixture `descriptor-reader/src/test/resources/MultiSpec_1MonitorAspect.json` with exactly the twelve baseline patterns. Replaces the round-7/early-round-8 `testNamedPointcutsSchemaPresent` (the cross-repo `namedPointcuts: Map` change is retired per A-decision).
- [ ] 6.8h `IfGuardLoweringTest` (added in §4.I.5 — round-11 R11.5, INV-INS-98 repurposed) — 2-shape lowering coverage (`if-nez` for null-check; `invoke-static Thread.holdsLock` + branch), fail-loud on unsupported shape, monitor-skipped-when-guard-false. (The round-8 `IfRuntimeDelegationTest`/`ifId`/`evaluateIf` path is RETIRED — fork-free, no runtime helper.)
- [ ] 6.8i `MatrixIntegrityTest.testRoundSevenInvariantsRemainSuperseded` — round-8 NEW (INV-INS-99 enforcement: round-7-supersession). Asserts that the round-7 invariants whose targets do not ship in round-8 remain superseded: (a) no test class references the (now-deleted) `br.unb.cic.rv.aspectjlang.*` substrate package (round-7 INV-INS-96 target); (b) no `AspectJRuntimeRemapper` class or FQN-remap test exists (round-7 INV-INS-97 target); (c) no `Coverage.aj` end-to-end smoke test exists in `grammar-tests/` (round-7 INV-INS-99 target — Coverage.aj is absorbed by `coverage-weaver` per §4.CV'). Fails the build if any of these reappear without an accompanying spec amendment, guarding against silent un-supersession via copy-paste from a future branch. INV-INS-99 (round-8 round-7-supersession marker).
- [ ] 6.9 Run `mvn -pl grammar-tests test`. ALL integrity tests SHALL pass on the populated matrix.
- [ ] 6.10 Extend `rvsec/.github/workflows/ci.yml`: add `mvn test -pl rvsec-android/rvsec-instrumentation-dexlib2/grammar-tests -DskipTests=false -am` after existing `maven-build` step. Declare `env: RVSEC_HOME: ${{ github.workspace }}` (or analogous). Round-8: CI step's stdout SHALL print the absorber-test count (NOT-NEEDED β rows) for visibility — track absorption claims at every run.
- [ ] 6.10a CI sanity check: prepend `test -d "$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca" || { echo "ERROR..."; exit 1; }`.
- [ ] 6.11 Commit: `test(gh62): MatrixIntegrityTest + AbsorptionClaimsContractTest + IfGuardLoweringTest + CI gate (round-11)` with `refs #62`. Push.

## 6.S Smoke validation — bipartite gate (round-10 — supersedes round-8 §4.E fixture/bytecode split since §4.E is REMOVED per AA-decision)

**Goal**: verify the **eleven round-11 closures** (§4.{O,N,V,X,TT,AT,Y,T,B,D,I}) using a **bipartite gate** because the JCA-226 corpus only exercises a subset of closures (the rest are generic_new-only per round-11 empirical demand and no production APK is instrumented end-to-end with generic_new). Gate (i) ≥10 JCA APKs validate §4.O/§4.V/§4.B/§4.D on ART; gate (ii) grammar-tests fixture + `dexdump` validates §4.I/§4.Y/§4.X/§4.N/§4.TT/§4.AT/§4.T. The round-7 Coverage.aj end-to-end gate (Gate D) remains DROPPED — Coverage.aj is absorbed by `coverage-weaver`.

**Gate split (round-10)**:
- **Gate (i) — ≥10 JCA APKs on ART**: validates §4.O, §4.V, §4.B, §4.D (the 4 closures with JCA pipeline demand; §4.R removed per R11.3).
- **Gate (ii) — grammar-tests fixture + `dexdump` diff**: validates §4.I, §4.Y (incl. Signature delivery), §4.X, §4.N, §4.TT, §4.AT, §4.T (the 7 closures with generic_new-only pipeline demand).

- [ ] 6.S.1 Pick ≥10 APKs from the JCA-226 instrumentable subset (re-using INV-INS-31 baseline). Selection MUST cover **Gate (i) closures** collectively. At least one APK MUST have nested try-catch DEX topology to support §4.T fixture cross-checks even though §4.T's primary validation is fixture-based.
- [ ] 6.S.2 Pre-change snapshot: re-instrument ≥10 APKs with `instr-cli.jar` from `HEAD~N` (pre-closure); run on emulator under standard JCA MOP spec; capture monitor event stream + per-closure pattern-match counts.
- [ ] 6.S.3 Post-change snapshot: re-instrument with `HEAD` (post-closure); run; capture.
- [ ] 6.S.4 Three gates (round-10 — drops round-7's Gate D; **drops round-8 U-decision §4.E fixture/bytecode gate per AA**):
  - **GATE A (hard, no-new-VerifyError)**: post-change DEX MUST pass ART install + DexBackedDexFile round-trip on all ≥10 APKs. Any new VerifyError REVERTS the responsible closure series.
  - **GATE B (hard, monotonic non-decrease event count)**: total post-change event count ≥ pre-change. §4.I `if(...)` in-weaver guard lowering (R11.5 — NOT runtime delegation) can short-circuit events (when the guard evaluates false); the gate is monotonic OVER THE SET OF APKS WHERE NO `if(...)` GUARD IS EXERCISED.
  - **GATE C (hard, positive-evidence per closure — bipartite)**: **Gate (i) — JCA APKs**: each of §4.O, §4.V, §4.B, §4.D MUST produce ≥1 new event in ≥1 JCA APK whose pattern matches the closure. **Gate (ii) — grammar-tests fixture + `dexdump` diff**: each of §4.I, §4.Y, §4.X, §4.N, §4.TT, §4.AT, §4.T MUST be validated by (a) the closure's dedicated `*GrammarTest` method(s) PASSing under `mvn -pl grammar-tests test`, AND (b) a `dexdump` diff comparing pre-change vs post-change weaver output on the closure's synthetic fixture asserting the expected new `invoke-static` / try-block / `<clinit>`-synthesis emission appears at the expected DEX offset. §4.Y additionally validates the Signature-delivery sub-closure via `StaticInitializationGrammarTest.signatureDeliveryForStaticinitEvent` (round-10 AC). A closure producing zero evidence is either inert (bug) or its fixture is misconfigured.
- [ ] 6.S.5 If any gate fails, REVERT the offending closure commit(s) (bisect-friendly per atomic commits) and re-evaluate.
- [ ] 6.S.6 Commit: `chore(gh62): ≥10-APK smoke validation PASS for round-8 closures (gates A/B/C)` with `refs #62`. Push.

## 7. Cross-Cutting Verification + Archive

- [ ] 7.1 Validate the openspec change: `openspec validate --changes gh62-aspectj-grammar-coverage --strict`. SHALL return PASS.
- [ ] 7.2 Invoke `/rv-code-reviewer` via the Skill tool against the gh62 diff (matrix, `deferred.md`, `grammar-tests/` module, CI step in `rvsec/.github/workflows/ci.yml`). Address review findings inline.
- [ ] 7.3 Update `MEMORY.md` with a `project_gh62_grammar_coverage_round8` entry capturing: (a) row count per category (COVERED, EXPLICIT-NO-OP, NOT-NEEDED α, NOT-NEEDED β); (b) the seven round-8 reclassifications with their absorbers; (c) the LOC reduction (round-7 ~2 000 → round-8 ~865-940, per H-reconciliation 2026-05-28); (d) the `coverage-weaver` semantic equivalence reference.
- [ ] 7.4 Run `/opsx:verify` against the change.
- [ ] 7.4a **REMOVED in round-8** — the round-7 separate snapshot commit is folded into §1.4 (race-condition fix). No standalone snapshot task at this stage.
- [ ] 7.5 Run `/opsx:archive` (`openspec archive gh62-aspectj-grammar-coverage --yes`). Delta spec for `instrumentation` SHALL auto-merge.
- [ ] 7.6 Commit on `origin/modules`: `chore(gh62): archive change (closes #62, round-8 lean redesign)`. Push.
- [ ] 7.7 Close issue #62 via `gh issue close 62 --repo PAMunb/rvsec --comment "..."` referencing the matrix, `deferred.md` snapshot SHA, the `grammar-tests/` module, the `MatrixIntegrityTest` + `AbsorptionClaimsContractTest` CI gates, and the round-8 redesign rationale (`docs/analise_sintese_macro.md` + the seven path-β reclassifications). Future closures open their own issues and OpenSpec changes when pipeline demand surfaces for any deferred row (caught by `testPipelineDemandCountsReproducible`).

## 7.8 Legacy inventory documents — SUPERSEDED banner (round-8 W-decision 2026-05-28 per Codex meta-review on inventory duplication)

**Goal**: prevent the matrix from competing with the pre-existing inventory documents `docs/AJ_CONSTRUCTIONS_INVENTORY.md` and `docs/AJ_TO_DEXLIB2_MAPPING.md` as a source of truth. The matrix is the live contract; the legacy inventories survive for historical reference only.

- [ ] 7.8.1 Add to `docs/AJ_CONSTRUCTIONS_INVENTORY.md` at the very top (line 1, before any other content): `> **SUPERSEDED** — see `docs/aspectj_grammar_coverage.md` as the live contract for the dexlib2 AspectJ surface. This file is preserved as historical inventory only; entries here may diverge from the matrix and SHOULD NOT be cited in new tests, scenarios, or invariants. See gh62 D15 design rationale + INV-INS-102.`
- [ ] 7.8.2 Add the same banner (verbatim) at the top of `docs/AJ_TO_DEXLIB2_MAPPING.md`.
- [ ] 7.8.3 Add `MatrixIntegrityTest.testNoCompetingSourceOfTruth` (INV-INS-102) that asserts the banner string appears at line 1-3 of both files; failure mode: "file <X> was amended without the SUPERSEDED banner — the matrix is the live contract, see gh62 D15 + INV-INS-102". The test reads the first few lines via `Files.readString()` and matches the banner regex `^> \*\*SUPERSEDED\*\* — see \\\`docs/aspectj_grammar_coverage\\.md\\\`.*`.
- [ ] 7.8.4 Commit: `docs(gh62): SUPERSEDED banner on legacy inventories (W-decision; matrix is the live contract)` with `refs #62`.

## 8. Out-of-scope cross-cutting checks

- [ ] 8.1 Confirm production source code changes are SCOPED to the round-8 in-change closure set (per design D8 + D9-round-8 + D11-narrowed + D13). `git diff origin/modules~N..origin/modules -- rvsec-android/rvsec-instrumentation-dexlib2/` SHALL touch the following modules and files only:
  - **rvsec-core/** (sibling runtime jar, already on the dexlib2 packaging allowlist): **new (round-11 R11.5)** — `org/aspectj/lang/Signature.java` (7-method interface stub) + `org/aspectj/lang/ClassSignature.java` (one-field `Class<?>` impl; `getDeclaringType()` returns it). ~35 LOC. Ships the §4.Y substrate WITHOUT touching aspectjrt or the JavaMOP fork.
  - **advice-emitter/**: ~~new — `ExecutionMatcherEmitter.java`~~ **VOID (AA)** — NOT created. ~~new — `SignatureFactory.java`~~ **VOID (round-11 R11.5)** — NOT created; §4.Y Signature delivery is fork-free via the `rvsec-core` `ClassSignature` substrate + `StaticInitializationEmitter` arg-token special-case (NOT a string/opaque `SignatureFactory`). extended — `IfGuardEmitter.java` (§4.I R11.5: COMPLETES the EXISTING `emit()` stub with direct 2-shape DEX lowering — `o==null`, `!Thread.holdsLock(o)` — + fail-loud default; ~60 LOC; NO `evaluateIf`, NO `ifId`), `StaticInitializationEmitter.java` (§4.Y R11.5: special-case the `getSignature()` arg token; emit `const-class`+`new-instance ClassSignature`+`invoke-direct`+`invoke-static`; ~40 LOC), `AfterThrowingEmitter.java` (§4.T range-splitting; ~120-160 LOC), `EmitterDispatch.java` (§4.T/I wiring).
  - **monitor-builder/**: **NO new files (round-11 R11.5)** — ~~`MonitorRuntimeIfHelperEmitter.java`~~ and ~~`IfRuntimeAbi.java`~~ are NOT created; the D13 runtime-delegation path is RETIRED (it required JavaMOP/RV-Monitor fork-side generation; §4.I is fully in-weaver in `IfGuardEmitter`).
  - **pointcut-engine/**: new — `BaseAspectExpander.java` (§4.B, ~15-20 LOC — AND-chain of `!within(...)`), ~~`ExecutionPC.java`~~ **VOID (AA)** — NOT created, `UnresolvedNamedRefException.java` + `LegacyDescriptorException.java` (§4.D, ~15 LOC — G-decision fail-closed); extended — `PointcutMatcher.java` (§4.O, §4.X, §4.D, §4.TT, §4.AT — `§4.W` removed per AB and `§4.R` removed per R11.3; the `Match.empty(ex)` placeholder at `:307-313` for `execution` is LEFT AS-IS), `PointcutExpressionParser.java` (§4.N, §4.V, §4.TT, §4.AT, §4.I), ~~`WithinPC.java`~~ **VOID (AB)** — NOT modified, `CallPC.java` (§4.O, §4.X, §4.V — `§4.R` removed per R11.3), `TargetPC.java` (§4.TT), `ArgsPC.java` (§4.AT), `NamedRefPC.java` (§4.D), `IfPC.java` (§4.I — carries the raw `javaExpression`; **NO `ifId` field** per R11.5), `NegationPC.java` (§4.N — NEW if absent).
  - **dex-mutator/**: new — `StaticInitSynthesizer.java` (§4.Y); extended — `DexWeaver.java` (§4.D.0 round-11: parse `descriptor.getCommonPointcut()` once per descriptor and AND-compose it onto each advice expression before matching — without this the `BaseAspect.notwithin()`/`!within(...)` exclusions never reach the matcher and §4.B/§4.D are inert; §4.T TRY_CATCH_WRAP install with range-splitting per D14; §4.Y thread declaring-class descriptor into `EmitContext`). The §4.D.0/§4.T.2a unit tests (`DexWeaverCommonPointcutCompositionTest`, `DexWeaverIfGuardedAfterThrowingTest`) live in `dex-mutator/src/test/java/...` with the `*Test` suffix (NOT `*GrammarTest`, NOT under `br.unb.cic.rv.grammar.*`) — so they sit OUTSIDE INV-INS-92's bijection scope, mirroring the existing `DexWeaverNestedTryCatchTest` precedent (they are weaver unit tests, not matrix-row grammar tests).
  - **descriptor-reader/**: **NO schema change** (round-8 empirical revision 2026-05-28 per A-decision: the existing `AspectDescriptor.baseAspectExclusions: List<String>` field is sufficient; the cross-repo `namedPointcuts: Map<String, ?>` change is RETIRED). The §4.D matcher consumes the existing field via `descriptor.getBaseAspectExclusions()` — no new schema, no new parser, no JavaMOP-side change.
  - **docs/**: amended `AJ_CONSTRUCTIONS_INVENTORY.md` and `AJ_TO_DEXLIB2_MAPPING.md` with SUPERSEDED banner per W-decision (§7.8).
  - **coverage-weaver/**: NO change (round-8 — Coverage.aj absorption is a runtime claim, not a code change; tests in grammar-tests cite the existing module as evidence).
  - **instr-cli/**: NO `pom.xml` change (round-7 plan to add `aspectjlang` to shade includes is dropped — no `aspectjlang/` module exists).
  - **NOT touched / NOT created**: `aspectjlang/` Maven submodule does NOT exist; `AspectJRuntimeRemapper.java`, `ConditionGuardEmitter.java`, `StaticSigEmitter.java`, `AdviceExecutionEmitter.java`, `ThisJoinPointEmitter.java`, `IfExpressionLowerer.java`, `IfRuntimeDelegationEmitter.java` are NOT created; `AspectDescriptor.namedPointcuts: Map` is NOT added (A-decision); `ExecutionMatcherEmitter.java` / `ExecutionPC.java` NOT created (AA); positive-`within` extension to `WithinPC.java` NOT applied (AB); **round-11 additions**: `SignatureFactory.java` is **NOT created** (R11.5 — §4.Y is fork-free via the `rvsec-core` `ClassSignature` substrate, NOT a string/opaque factory); `MonitorRuntimeIfHelperEmitter.java` / `IfRuntimeAbi.java` are **NOT created** (R11.5 — D13 retired; §4.I fully in-weaver); the return-position `T+` branch in `CallPC.java`/`PointcutMatcher.java` is **NOT added** (R11.3 — §4.R removed, zero demand); **NO JavaMOP / RV-Monitor fork change** anywhere.
  Other production code MUST NOT be touched.
- [ ] 8.2 Confirm `instr-cli.jar`'s observable behaviour changes are SCOPED: re-run per-module test bars and assert 0 NEW failures vs. pre-task-4.{closure-set} baseline. Shaded jar's byte hash WILL change. §6.S smoke validation is the empirical gate.
- [ ] 8.3 Re-instrument the ≥10-APK JCA-226 smoke subset (§6.S) only. NO full 190-APK re-instrumentation; NO Docker image rebuild beyond §6.S; NO APE experiment re-run.
