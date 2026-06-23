# Round-11 addendum (2026-05-29) — root-cause of the `.aj` divergence + fork-free closures — AUTHORITATIVE OVERRIDE

A careful re-audit (triggered by the user's challenge "JavaMOP is deterministic — it can't lose this") established four facts that **supersede the round-10 rationales below where they conflict**. The round-10 *verdicts* (which closures ship) survive almost intact; several round-10 *rationales* and *counts* were wrong and are corrected here.

## R11.1 — The ForkedBooter `execution()` blocks come from the `-s`/`-statistics` flag, not a toolchain change

There are two different `MultiSpec_1MonitorAspect.aj` on disk for each corpus:
- **Production pipeline output** — what `rv-monitor-generator` emits (`javamop -d <out> -merge <specs>.mop`, NO `-s`). jca = 705 lines, **0** `ForkedBooter`, **0** positive `execution()`. This is what `results/gh53_smoke_dexlib2/monitors/` (1-mai) and `empirical-monitors/` (29-mai) both contain — byte-identical, and byte-identical to a fresh 29-mai regen.
- **Stray artifacts in the `.mop` source dirs** — `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/{jca,generic_new}/MultiSpec_1MonitorAspect.aj` (jca = 1042 lines, **23** `ForkedBooter`; generic_new = 592 lines, 27). These are **git-ignored, never-committed, ad-hoc build leftovers**; `generic/` has none; dates differ wildly (jca 26-mai, generic_new 2-abr).

Root cause (proven): the `ForkedBooter.runSuitesInProcess(..)` block is emitted **iff** `-s`/`-statistics` is passed, by `MOPStatistics.advice()` (`$RVSEC_HOME/javamop/src/main/java/javamop/output/combinedaspect/MOPStatistics.java:69-78` — `if (!JavaMOPMain.options.statistics) return "";`). It is a **statistics dump**, not a reset advice. Empirically confirmed: `javamop -merge -n MultiSpec_1 -s` on the jca specs reproduces exactly 23 blocks / 24 `execution(` / 1042 lines (identical to the stray file); without `-s`, 0. **JavaMOP did not change.** The stray files were produced by a one-off `-s` run and are not on the production path.

**Consequence for the matrix:** the round-10 "Source" execution()/within() counts (`execution Source = 1,24,0,28`; `within Source = 22,13,0,13`) were obtained by grepping the **stray `-s` artifacts**, not the `.mop` sources. The true `.mop` source counts are `execution() = 0,0,0` and positive `within() = 0,0,0` everywhere. `DemandCounter.countMop()` MUST scan **only `*.mop`** files (plus `aspect/Coverage.aj` as its own corpus), never any `*.aj` sitting in the `.mop` source dirs. The stray `.aj` files SHOULD be deleted (`§0` task).

## R11.2 — `execution()` and `within()`: the real consumer is `Coverage.aj`; the absorber is `coverage-weaver` (NOT a "JavaMOP execution→call rewrite")

The round-10 AA-decision rationale ("JavaMOP compiler rewrites source-level `execution()` into matching `call()` events") is **false**. JavaMOP emits the pointcut keyword verbatim (`DumpVisitor.java:558-562`; fork fixture `Creation.mop.aj:45` keeps `execution(* *.main(..))`). There is no execution→call rewrite.

The true picture (re-counted; `.mop` excludes stray `.aj`):
- `.mop` specs (jca/generic/generic_new): `execution()` = **0**, positive `within()` = **0** (all `within(` hits are inside the `notwithin()` / `MOP_CommonPointCut()` exclusion macro).
- Hand-written `aspect/Coverage.aj`: `execution(* *.*(..))` = **1** (the coverage-tracing pointcut, `Coverage.aj:50`) and ~24 positive `within(...)` (the `excludedPackages()` macro, used negated).
- Pipeline `.aj` at the dexlib2 matcher: `execution()` = **0**, positive `within()` = **0**.

So **`Coverage.aj` is the sole real consumer of both `execution()` and positive `within()`**, and `Coverage.aj` is absorbed by **`coverage-weaver`** (`coverage-weaver/.../package-info.java:4` "functionally equivalent to the legacy Coverage.aj"; the dexlib2 Python pipeline routes coverage through `coverage-weaver` and filters all `org.aspectj` types out of the APK — `dexlib_instrumentation.py:60-125`). Therefore §4.E and §4.W are correctly **NOT-NEEDED β with absorber = `coverage-weaver`** (same absorber as round-8 §4.CV/§4.WW), **not** "absorbed by JavaMOP" and **not** path α.

## R11.3 — `§4.R` (T+ in `call()` RETURN position) has ZERO demand everywhere → NOT-NEEDED α

Two independent greps confirm `call(Type+ ...)` (the `+` on the return-type token) = **0** in `.mop`, in `Coverage.aj`, and in all three pipeline `.aj`. All subtype polymorphism is in the OWNER position (§4.O, 64 sites). §4.R is speculative under P1 — same category as §4.E/§4.W. **Removed from in-change scope (NOT-NEEDED α).** In-change closures: 12 → **11**.

## R11.4 — Corrected pipeline counts (authoritative, fresh-regen + empirical-monitors agree)

| Closure | round-10 count | R11 corrected (pipeline) |
|---|---|---|
| §4.O `T+` owner | 64 | **64** (gen_new) ✓ |
| §4.X name-glob | 14 | **13** (gen_new) |
| §4.V `(T,..)` varargs | 8/14 (PROVISIONAL) | **6** (jca) — resolved, no longer PROVISIONAL |
| §4.TT `target(Type)` | 22 | **22** (gen_new) ✓ |
| §4.AT `args(Type)` | 5 | **5** (gen_new) ✓ |
| §4.N `!target`/`!args` | 14+2 | **14+2** (gen_new) ✓ |
| §4.Y staticinit | 3 | **3** (gen_new) ✓ |
| §4.T after-throwing | 1 | **1** (gen_new) ✓ |
| §4.I `if()` | 3 | **3** (gen_new) ✓ |
| §4.R `T+` return | (in-change) | **0 — REMOVED** |
| §4.E `execution()` | 0 (NOT-NEEDED β) | **0** — β absorber corrected to `coverage-weaver` |
| §4.W `within()` positive | 0 (NOT-NEEDED β) | **0** — β absorber corrected to `coverage-weaver` |

## R11.5 — `§4.Y` and `§4.I` are realised WITHOUT changing the JavaMOP/RV-Monitor fork (firm constraint)

The round-10 §4.Y (Signature delivery) and the design's D13 §4.I (`evaluateIf`/`ifId`/`MonitorRuntimeIfHelperEmitter` runtime-delegation ABI) both assumed code generated on the fork side. The fork stays untouched. Both close entirely in the dexlib2 weaver + the already-packaged `rvsec-core` runtime jar:

- **§4.Y** — the staticinit monitor expects `org.aspectj.lang.Signature` and calls only `getDeclaringType()`. Ship a minimal `org.aspectj.lang.Signature` interface + `ClassSignature(Class)` impl (~35 LOC) in **`rvsec-core`** (already on the dexlib2 packaging allowlist, already dexed → aspectjrt stays filtered, no packaging change). At each `<clinit>` (declaring class statically known) the weaver emits `const-class` + `new-instance ClassSignature` + `invoke-direct <init>(Class)` + `invoke-static *staticinitEvent(Signature)`, reusing the `CoverageWeaver` const+invoke + `RegisterShifter` register pattern. `StaticInitializationEmitter` special-cases the literal arg token `thisJoinPoint.getStaticPart().getSignature()` (today it routes through the generic binding resolver → `UnresolvedBindingException` → the site is silently skipped). ~70 LOC weaver + 35 LOC rvsec-core.
- **§4.I** — only two expression shapes exist in the corpus (`o == null`, `!Thread.holdsLock(o)`); the bound register is already available in `ctx.match` and the text in `IfPC.javaExpression`. Complete the existing stub `IfGuardEmitter.emit()` with direct DEX lowering of exactly those two shapes (`if-nez`; `invoke-static Ljava/lang/Thread;->holdsLock` + `move-result` + `if-nez`) and a **fail-loud** default for any other shape, reusing the `BuilderInstruction21t` + `newLabelForIndex` label API already proven in `RegisterShifter`. No runtime jar, no fork, no allowlist change. This is a 2-shape closed dispatch, NOT the general Java sub-grammar parser six reviewers rejected in round-7. ~60 LOC, 1 file. **Replaces D13 entirely** (no `evaluateIf`, no `ifId`, no `MonitorRuntimeIfHelperEmitter`, no `IfRuntimeAbi`).

## R11.6 — Post-review consistency pass (2026-05-29, 4 independent LLM reviews + code re-verification)

Four LLM reviews (`docs/analise_{claude,gemini-cli,gpt5-codex,mimo}.md`) were re-verified against the actual dexlib2 source before any artifact edit. Two reviewer claims were **refuted** and must NOT trigger redesign; six were **confirmed** and applied across the five artifacts:

- **REFUTED — §4.T after-throwing "skips user catch":** the spec ALREADY mandates the sibling-handler-preserving range-split (original handlers retained on the matched-invoke range; advice handler listed FIRST; `throw` re-propagation; test asserting BOTH advice + user catch fire) at `spec.md:303,305,307,308`. The reviewers reviewed the *rejected* nested-wrapping alternative. No §4.T design change.
- **REFUTED — `args(..., ..)` uncovered:** functionally COVERED by §4.V (task 4.V.1a applies the `ParamList` refactor to `ArgsPC.matchParams`, not only `CallPC`). Documentation-only undercount in the §4.V headline.
- **CONFIRMED (BLOCKER) — `commonPointcut` never composed:** `DexWeaver.parseCached` (`:539`) parses ONLY `advice.getExpression()`; `descriptor.getCommonPointcut()`/`getBaseAspectExclusions()` have ZERO production call-sites (test-only); `PointcutMatcher.match` (`:75`) takes no descriptor. So §4.B/§4.D would resolve a `NamedRefPC` node the production parser never builds and the exclusion filter is silently dropped. **Fix:** new task §4.D.0 (parse + AND-compose `commonPointcut` before matching) + `DexWeaverCommonPointcutCompositionTest` + a delta-spec scenario.
- **CONFIRMED (BLOCKER) — dead `execution()`+`ifId` dedup requirement:** the live `SHALL` bullet at `spec.md:352` required an impossible path (`execution()` is NOT-NEEDED β; `ifId` retired). **Removed.**
- **CONFIRMED — §4.T × §4.I share one join point:** the sole `after() throwing` site (`...aj:294`, `Comparable_CompareToNullException_badexception`) is also the `if(o==null)` site (`:205`); their composition was unspecified/untested. **Fix:** new composition scenario + task 4.T.2a (`DexWeaverIfGuardedAfterThrowingTest`).
- **CONFIRMED — count reproducibility not pinned:** counts reproduce only under specific rules (§4.O=64 per-occurrence of `+.`, not per-line 39; §4.TT/§4.AT include negated forms that §4.N also counts). **Fix:** INV-INS-93 + task 1.2b now require each row to pin its `Pattern` + per-occurrence-vs-per-line + negated-form ownership.
- **CONFIRMED — runtime-linkage row conflated `Signature`:** `spec.md:78` listed `Signature` under NOT-NEEDED β while §4.Y makes it COVERED. **Fix:** descoped the row to the JoinPoint family; Signature delivery is §4.Y.
- **CONFIRMED — `AbsorptionClaimsContractTest` incomplete:** INV-INS-96 says "every β row" but the aggregation omitted `aspect Foo` / `pointcut p()` (`deferred.md` §2.2.2). **Fix:** added both `AspectDeclarationGrammarTest` methods in tasks §6.8f + design INV-INS-96 list.
- Plus consistency hygiene: `tasks.md:95` `ifId` field contradiction removed; §6.S Gate B "runtime delegation" → "in-weaver guard"; design round-6/8 closure-count fossils (8/14 → 11) corrected; `PipelineDemand` canonical source pinned to the committed `empirical-monitors/` snapshot; Docker-rebuild contradiction reconciled (NOT rebuilt in gh62); `b1` non-goal (BaseAspect.notwithin filter) flipped to in-scope; stale absorber labels / §4.X 16→14→13 corrected.

---

# EMPIRICAL-DEMAND.md — pipeline-level demand audit (round-10, 2026-05-29)
*(round-10 content below is superseded by the Round-11 addendum above where they conflict — specifically the §4.E "JavaMOP rewrite" rationale, the §4.W "macro inflation" rationale, the source-level execution/within counts, the §4.X=14 and §4.V counts, and any "12 closures" total)*

Compiled monitors for all three spec corpora via `rv-monitor-generator` (uses
the fork JavaMOP + RV-Monitor toolchain at `$RVSEC_HOME/{javamop,rv-monitor}/`).
Output preserved under `empirical-monitors/{jca,generic,generic_new}/`.

Inputs (all freshly compiled 2026-05-29):
- `jca/`         ← `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca/` (23 specs)
- `generic/`     ← `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/generic/` (118 specs)
- `generic_new/` ← `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/generic_new/` (27 specs)

Each corpus dir contains four artefacts:

| File                                | Role                                                       | Why preserved                                              |
| ----------------------------------- | ---------------------------------------------------------- | ---------------------------------------------------------- |
| `MultiSpec_1MonitorAspect.aj`       | JavaMOP-compiled aspect (pipeline-level demand target)     | the §4.* demand-counting input                             |
| `MultiSpec_1MonitorAspect.json`     | `AspectDescriptor` consumed by dexlib2 `DescriptorReader`  | confirms `baseAspectExclusions` schema (§4.B / §4.D)       |
| `MultiSpec_1RuntimeMonitor.java`    | runtime monitor classes invoked by advice bodies           | ABI of `evaluateIf` (§4.I), `staticinitEvent` (§4.Y/§4.JP) |
| `Coverage.aj`                       | auxiliary aspect (copied, not compiled)                    | semantic reference for `coverage-weaver` (NOT-NEEDED β)    |

Counts in the table below are taken from `MultiSpec_1MonitorAspect.aj` per corpus.

## Demand table (POSITIVE pipeline-level sites per corpus)

| Construct                              | Round-9 claim         | Empirical (jca, generic, generic_new) | Verdict                                                  |
| -------------------------------------- | --------------------- | ------------------------------------- | -------------------------------------------------------- |
| `execution(...)` POSITIVE              | 24 jca pipeline       | **0, 0, 0**                           | RECLASSIFY §4.E → NOT-NEEDED β (absorption by JavaMOP)   |
| `within(...)` POSITIVE                 | 13 jca + 13 generic_new | **0, 0, 0**                           | RECLASSIFY §4.W → NOT-NEEDED β (no positive consumer)    |
| `!within(...)`                         | absorbed via BaseAspect.notwithin | 13, 13, 13 (identical inline expansion of 13-entry list) | confirms §4.B/§4.D scope                        |
| `if(...)` PCD                          | 8 generic_new         | **0, 0, 3** (generic_new)             | §4.I real, smaller scope                                 |
| `staticinitialization(T+)`             | 6 generic_new         | **0, 0, 3** (generic_new)             | §4.Y real, smaller scope                                 |
| `after() throwing(...)`                | 2 generic_new         | **0, 0, 1** (generic_new)             | §4.T real (single site)                                  |
| `target(Type)`                         | 44 generic_new        | **0, 0, 22** (generic_new)            | §4.TT real, ~½ scope                                     |
| `args(Type)`                           | 10 generic_new        | **0, 0, 5** (generic_new)             | §4.AT real, ½ scope                                      |
| `!target(T)`                           | 28 generic_new        | **0, 0, 14** (generic_new)            | §4.N real (matches Claude/Deepseek panel re-grep)        |
| `!args(T)`                             | 4 generic_new         | **0, 0, 2** (generic_new)             | §4.N real                                                |
| `T+` in `call()` owner                 | ~73 generic_new       | **0, 0, 64** (generic_new)            | §4.O confirmed                                           |
| Method-name glob `*name`               | ~16 generic_new       | **0, 0, 14** (generic_new)            | §4.X confirmed                                           |
| `__STATICSIG`                          | 0 (absorbed)          | **0, 0, 0**                           | absorption CONFIRMED ✓                                   |
| `condition(...)`                       | 0 (absorbed)          | **0, 0, 0**                           | absorption CONFIRMED ✓                                   |
| **`thisJoinPoint` / `JoinPoint.`**     | **0 (§4.JP NOT-NEEDED β)** | **0, 0, 3** (generic_new staticinit)  | **CLAIM REFUTED — survives in staticinit advice bodies** |
| `cflow*` / `withincode` / `handler`    | 0                     | **0, 0, 0**                           | NOT-NEEDED α confirmed ✓                                 |
| `get(FieldPattern)` / `set(FieldPattern)` | 0                  | **0, 0, 0**                           | NOT-NEEDED α confirmed ✓ (resolves mimo concern)         |
| `around`                               | 0                     | **0, 0, 0**                           | EXPLICIT-NO-OP confirmed ✓                               |
| `adviceexecution()` (negated form)     | 0 (vacuous)           | 1, 1, 1 — all from `!adviceexecution()` in `MOP_CommonPointCut` | NOT-NEEDED β confirmed ✓ |
| `BaseAspect.notwithin()`               | 1 jca + 1 generic_new | 2 each (signature + body of same call) | confirmed                                               |

## Three decisive evidences

### 1. §4.E POSITIVE `execution(...)` = 0 across all 3 corpora

The only `execution(` substring hits across all three compiled `.aj` files
are inside `!adviceexecution()` in `MOP_CommonPointCut`:

```
jca/MultiSpec_1MonitorAspect.aj:76:        pointcut MOP_CommonPointCut() : !within(... RVMObject+) && !adviceexecution() && BaseAspect.notwithin();
generic/MultiSpec_1MonitorAspect.aj:24:    pointcut MOP_CommonPointCut() : !within(... RVMObject+) && !adviceexecution() && BaseAspect.notwithin();
generic_new/MultiSpec_1MonitorAspect.aj:39: pointcut MOP_CommonPointCut() : !within(... RVMObject+) && !adviceexecution() && BaseAspect.notwithin();
```

No spec uses `execution(...)` positively at pipeline level. The round-9
defensive-shipping rationale for §4.E ("future specs might use it") is now
dominated by P1 (no speculative features): **§4.E reclassified NOT-NEEDED β**
with absorption stage = JavaMOP compiler (source-level `execution()` in `.mop`
files is rewritten into matching `call()` events during compilation).

### 2. §4.W POSITIVE `within(...)` = 0 across all 3 corpora

All `within(...)` occurrences are inside pointcut declarations themselves
(`pointcut notwithin(): ... within(...) ...` or `MOP_CommonPointCut(): !within(... RVMObject+) ...`).
Zero specs use positive `within(...)` as an event predicate.

**§4.W reclassified NOT-NEEDED β** — the source-level 13+13 count was inflated
by counting body declarations of the `notwithin()` macro.

### 3. §4.JP `thisJoinPoint` SURVIVES 3× in generic_new staticinit (refutes NOT-NEEDED β)

```
empirical-monitors/generic_new/MultiSpec_1MonitorAspect.aj:260:     MultiSpec_1RuntimeMonitor.Collection_HashCode_staticinitEvent(thisJoinPoint.getStaticPart().getSignature());
empirical-monitors/generic_new/MultiSpec_1MonitorAspect.aj:319:     MultiSpec_1RuntimeMonitor.Serializable_NoArgConstructor_staticinitEvent(thisJoinPoint.getStaticPart().getSignature());
empirical-monitors/generic_new/MultiSpec_1MonitorAspect.aj:328:     MultiSpec_1RuntimeMonitor.URLConnection_OverrideGetPermission_staticinitEvent(thisJoinPoint.getStaticPart().getSignature());
```

The round-8 claim that `thisJoinPoint*` is absorbed by Coverage.aj + `__STATICSIG`
is **false for the `staticinit` advice family**: when JavaMOP emits a staticinit
event, it passes the signature derived from `thisJoinPoint.getStaticPart().getSignature()`
as the first argument. §4.Y must therefore deliver the signature object to the
runtime call site (synthesised `<clinit>` injection point + Signature
construction), not just the bare advice invocation.

## Impact on scope

| Closure       | Round-9 status                          | Round-10 (empirical) status                              |
| ------------- | --------------------------------------- | -------------------------------------------------------- |
| §4.E          | COVERED in-change (~230 LOC)            | **NOT-NEEDED β** — saves ~230 LOC                        |
| §4.W          | COVERED in-change (~80 LOC)             | **NOT-NEEDED β** — saves ~80 LOC                         |
| §4.JP         | NOT-NEEDED β (claim of Coverage.aj absorption) | **COVERED inside §4.Y** — extends §4.Y to deliver Signature (+30-50 LOC) |
| §4.I          | 8 sites estimated                       | 3 sites — proportional scope reduction                   |
| §4.T          | 2 sites estimated                       | 1 site — single-fixture validation                       |
| §4.Y          | 6 sites estimated                       | 3 sites (plus Signature delivery sub-task)               |
| §4.TT/§4.AT/§4.N | 44/10/(28+4) estimated               | 22/5/(14+2) confirmed in pipeline                        |
| §4.O          | ~73 estimated                           | 64 confirmed                                             |
| §4.X          | ~16 estimated                           | 14 confirmed                                             |
| §4.B/§4.D     | 1+1 estimated                           | 1+1 confirmed                                            |
| §4.V          | 14 jca + 2 generic_new estimated        | pending pipeline-level re-grep (proposal counts retained, marked PROVISIONAL) |

**In-change closures**: 14 → **12** (§4.E and §4.W exit; §4.JP enters as §4.Y sub-closure).
**Production LOC**: ~865-940 → **~565-660**.
**Coverage**: a real silent gap (`thisJoinPoint` in staticinit) is now closed.

## Decision codes consumed in this round

- **AA-decision** (2026-05-29): §4.E reclassified NOT-NEEDED β based on empirical pipeline demand = 0 across all three corpora. Supersedes round-8 user defensive-shipping decision. The future "execution(...) might be used positively" risk is downgraded to "amend matrix when DemandCounter.countCompiledAj(execution) > 0" — exactly the trigger MatrixIntegrityTest already enforces.
- **AB-decision** (2026-05-29): §4.W reclassified NOT-NEEDED β. Source-level 13+13 was a macro-body inflation; pipeline demand = 0.
- **AC-decision** (2026-05-29): §4.JP `thisJoinPoint`/`Signature` reactivated as in-change work, folded into §4.Y as the Signature-delivery sub-closure. Round-8 NOT-NEEDED β rationale (Coverage.aj absorption) is refuted by 3 generic_new staticinit sites.

## Reproducing this audit

```bash
export RVSEC_HOME=/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
CHANGE=openspec/changes/gh62-aspectj-grammar-coverage

for corpus in jca generic generic_new; do
  uv run rv-monitor-generator generate \
    --specs-dir $RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/$corpus \
    --output $CHANGE/empirical-monitors/$corpus
done
```

Counting recipe used per construct: see commit message of round-10 update.

## R12.1 — Demand-audit gap: the `*`-in-RETURN position was never measured (2026-05-30, apply-discovered)

The round-8→11 `call()`-position audit enumerated three call-signature positions for subtype/wildcard
markers: OWNER (`call_owner_tsubtype`, `+.`), method NAME (`call_name_glob`, `name*(`), and the
RETURN-`T+` position (`call_return_tsubtype`, `Type+ ` immediately after `call(`). The RETURN-`T+`
position measured **0 everywhere** → §4.R' NOT-NEEDED α. **What the audit never measured was the
`*`-in-RETURN position** — the plain match-any return wildcard `call(* Owner.name(..))`. That is in fact
the DOMINANT generic-corpus call shape:

| designator | jca | generic | generic_new | rule |
|---|---|---|---|---|
| `call_return_wildcard` (`*` return) | 0 | 240 | 67 | per-occurrence, `Pattern.compile("call\\(\\* ")` on the compiled `.aj` |

The `*`-return sites are disjoint from the three audited keys: `call_name_glob` requires the `*` to abut
`(` (the method-name token), `call_owner_tsubtype` requires `+.`, and `call_return_tsubtype` requires a
`Type+ ` (identifier with a `+`). The `call(* ` anchor (the `*` followed by a space, in the return slot
before the owner) matches none of those.

This was not just an unmeasured count — it was a verified SILENT-GAP in the matcher: `matchCall` gated
the return type with an exact `toDescriptor(cp.returnType()).equals(mr.getReturnType())`, and for
`returnType == "*"` the resolver returns the last-resort `Ljava/lang/*;`, which never equals any real
return descriptor. Every `call(* ...)` site — the entire generic/generic_new matched-call surface —
silently failed to match. The §4.O/§4.X/§4.V/§4.TT/§4.AT/§4.N closures were exercised only by
concrete-return substitutes (`call(boolean ...)`), so the gap stayed masked. §4.RW (the 12th closure)
skips the return-equality gate when the pattern return is `*`, symmetric to the existing `*` handling for
args positions and method-name globs. It is a prerequisite for the sibling matcher-group closures to fire
end-to-end on the generic/generic_new corpora. Evidence: `CallReturnWildcardGrammarTest`.
