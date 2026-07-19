# Javadoc & Inline-Comment Improvement Plan — `rvsec-instrumentation-dexlib2`

> Status: **PROPOSAL — awaiting approval. Nothing implemented yet.**
> Scope: the 9 main Maven sub-modules of `rvsec-instrumentation-dexlib2` (Java, `br.unb.cic.rv.*`).
> Language of all Javadoc/comments: **English** (project rule: "Use English for all code and comments").
> Governing principles: **P1 Simplicity · P2 Human-Readable · P3 No Backward-Compat · P4 Current-State.**

---

## 1. Why this plan looks different from the original request

The request was "create/improve Javadoc + add inline comments at the key points". A read-only survey of every `src/main/java` file (172 Java files total; ~89 main sources across 9 sub-modules), performed by four parallel sub-agents cross-checked against the module's canonical `architecture.md` and the current `rv-android/docs/architecture/instrumentation.md`, changed the picture:

**The documentation is already GOOD-to-RICH almost everywhere.**

- Class-level Javadoc is **universal** — the only class with none is `ParameterDescriptor`.
- **Every** package already has a `package-info.java`.
- The hardest algorithms (`RegisterShifter`, `DexWeaver`, `PointcutMatcher`, `MonitorInvokeBuilder`, `MultidexMerger` STORED-`resources.arsc`, `CoverageWeaver` spill) are **already** densely commented, tied to invariant IDs (`INV-INS-xx`) and post-mortems.

So this is **not** a "write missing Javadoc" job. It is a **surgical quality pass** in three flavours:

- **(A) Accuracy defects** — a small set of comments that are *factually wrong or stale* and actively mislead a reader. Highest value.
- **(B) Missing method-level headers** on key public methods that today lean entirely on class-level Javadoc — weak for generated API HTML.
- **(C) Inline density** on a short list of genuinely dense algorithms where the code still outruns the commentary.

Plus **(D)** ensuring every `package-info.java` is accurate so the generated Javadoc HTML is complete and link-clean.

### Design rules for the whole pass

1. **Preserve good docs.** Update/extend; never rewrite Javadoc that already meets the bar. The existing `<h2>/<h3>`-sectioned class docs (e.g. `RegisterShifter`, `CoverageWeaver`) are the *style target*, not something to replace.
2. **Tier the effort** (adapted from the `rv-doc-code` skill): Tier 1 = public API / orchestrators / primary components (full Javadoc + `@param`/`@return`/`@throws`); Tier 2 = internal methods >10 lines (summary + params + return); Tier 3 = trivial helpers (one line or skip); **Skip** = self-evident accessors, `toString`, picocli `run()` boilerplate. Do **not** over-document trivial beans (P1).
3. **Explain WHY, not WHAT** (P2). Inline comments justify a decision or a hazard; they never restate the code.
4. **No history, no promo** (P4). Remove "task 5.x / Group 5 / will host / migrated from" placeholders; describe current behaviour only.
5. **English only.**
6. **Verify against the implementation before rewriting a "fact".** The `dex-mutator/package-info.java` defect below was only caught because the survey cross-checked `RegisterShifter`'s real body. Every accuracy fix must be confirmed against the code, not the old comment.

### Java ⇆ `rv-doc-code` (Python skill) mapping used throughout

| `rv-doc-code` concept | Java/Javadoc form applied here |
|---|---|
| Tier 1/2/3/Skip depth | same tiers |
| `### Architectural Decisions / Role / Key Features / Integration Points` | `<h2>`/`<h3>` sections in class Javadoc (already the house style) |
| `Args: / Returns: / Raises:` | `@param` / `@return` / `@throws` |
| `# Phase N:` (orchestration) | `// Phase N:` (e.g. `BatchRunner.runPipeline`) |
| `# Step N:` (algorithms) | `// Step N:` at the dense hotspots |
| WHY blocks | `//` rationale directly above the non-obvious code |
| P1–P4 | identical, incl. cleaning P4-violating placeholders |

---

## 2. Phase 1 — Accuracy defects (do first; small, high-value, corrects mental models)

These are few, localized, and each **actively misleads**. Each must be verified against the current implementation before editing.

| # | File | Location | Defect | Fix |
|---|---|---|---|---|
| A1 | `dex-mutator/…/mutator/package-info.java` | lines 10–13 | Says `RegisterShifter` bumps `registerCount` **via reflection** and widens to **`/from32`**, cites **INV-INS-53**. All wrong: the impl **clones the MMI** (reflection was invisible to `DexPool`), there is **no `/from32`**, and the real invariants are **INV-INS-80/-87**. This is the entry doc for the hardest module. | Rewrite to the clone-based reality, matching `RegisterShifter`'s own (correct) class Javadoc; fix invariant refs. |
| A2 | `dex-mutator/…/mutator/InstructionInjector.java` | class doc lines 26–33 vs body 259–347 | Class doc claims it does **NOT** install try/catch labels ("belongs to the caller") — but `installTryCatch` is now the class's most complex method and does exactly that. | Update class doc to describe the try/catch-installation responsibility it now owns. |
| A3 | `validator/…/validator/package-info.java` | lines 18–19 | `{@link}` to `Layer1BaksmaliDiffer`, `Layer2BootValidator`, … — **class names that do not exist** (actual: `BaksmaliDiffer`, `BootValidator`, …) → **dead links in Javadoc HTML**; also stale "skeletons … deferred to Phase 5". | Fix the `{@link}` targets to real class names; drop the "skeleton/Phase 5" wording (all layers implemented). |
| A4 | `cli/…/cli/ConfigResolver.java` | class Javadoc, final sentence | Corrupted/garbled sentence: "*…the `ciphertext` of a monitor-builder or multidex-merger tool path missing*" — "ciphertext" is nonsense here. | Rewrite the sentence to state the real fail-fast contract (a required tool path cannot be resolved). |
| A5 | `cli/…/cli/BatchRunner.java` | class Javadoc phase list | Phase taxonomy **omits `build_only`**, which the code returns (~line 306). | Add `build_only` to the documented `phase=` taxonomy. |
| A6 | `advice-emitter/…/emitter/AdviceEmitter.java`; `dex-mutator/…/DexWeaver.java` (`applyPlan` REPLACE branch); `advice-emitter/…/emitter/ThisJoinPointEmitter.java` (`signatureFor`) | inline | P4-violating placeholders referencing unfinished "task 5.x / Group 5"; `signatureFor` is a stub returning the raw expression. | Remove the "task/Group" placeholder wording (describe current state). For `signatureFor`: **decide** — either document it explicitly as an intentional pass-through, or (open question Q5) treat as dead code. |
| A7 | `pointcut-engine/…/pointcut/package-info.java` | body | P4-violating forward references: "task 3.6", "this module **will host**". | Rewrite to present tense / current state. |
| A8 | `cli/…/cli/InstrumentationCli.java` | `version = "0.8.0-SNAPSHOT"` | Stale version string (project is `0.9.1-SNAPSHOT`). Not a doc-comment per se. | Open question Q2 — fix in this pass or leave to release tooling. |

**Effort:** ~1 focused session, one careful agent (or a couple), single commit `docs(dexlib2): fix stale/inaccurate Javadoc & package-info`.

---

## 3. Phase 2 — Missing method-level Javadoc on key public methods (core pipeline)

These classes lean on rich class docs; adding short method headers makes the generated API HTML complete and helps someone landing mid-file. Tier 1 unless noted.

**cli**
- `BatchRunner.runPipeline` — **highest value**: *the* orchestrator (has per-phase inline comments, no method header). Add contract/return summary; keep the phase comments.
- `BatchRunner.instrumentOne`, `BatchRunner.instrumentBatch` — public entries; document the batch-vs-single distinction and `resultsJson == null` behaviour.
- `ConfigResolver.resolve` — document the flag→env→default precedence at method level (class doc already explains the concept).

**coverage-weaver**
- `CoverageWeaver.weave(DexFile, MutableImplSupplier)` — add `@return CoverageReport` header.

**descriptor-reader**
- `ParameterDescriptor` — add the one missing **class** Javadoc (Jackson POJO for an advice parameter `type name`). Getters/setters stay undocumented (P1).
- `DescriptorReader.read(...)` overloads — Tier 3, low value (trivial delegation); optional.

**Effort:** small; folds into the per-submodule agents of Phase 4.

---

## 4. Phase 3 — Inline density at the algorithmic hotspots (the "principais pontos")

This is the part that most serves the stated goal — *help a reader truly understand what is happening*. Ranked by (complexity × how thin the current commentary is). Each gets `// Step N:` markers and/or WHY blocks; **no Javadoc rewrite of already-good class docs.**

### dex-mutator (hardest — register-encoding danger zones)
1. `RegisterShifter.expand22cViaScratch` (~654–684) + `expandOverflow` (~623–652) — **the single densest under-explained spot.** 4-bit→wider bridging for `iget/iput/instance-of/new-array` when one operand overflows v15. Document the read-vs-write asymmetry (write: core then `move-from16 back`; read: `move-from16 prep` then core), wide-slot handling, and the `aOver && bOver → null` veto. Add rationale to the `isDestWrite22c`/`isObjectSlot22cA/B` predicates.
2. `RegisterShifter.shift` (~299–477) — the giant per-`Format` switch. Add a short note per width class (which formats are 4-bit and can overflow vs 8/16-bit) so the widening hazard is legible.
3. `RegisterShifter.cloneInstructions` (~174–258) — the three-pass clone (why three passes is commented; make the `newLabelForIndex` ↔ placeholder-prefill interaction explicit, as it is the try/catch re-homing hazard behind INV-INS-80).
4. `DexWeaver.weave` (~366–526) — already well commented; add one note on the **ordering invariant** among the three MMI-swap sites (`allocate → replaceImpl → applyPlan → rebuilt → replaceImpl`, INV-INS-87).

### advice-emitter
5. `WrapperEmitter.expandCallTarget` (~283–357) — varargs/`fixedPrefix` arithmetic and the middle-`..`-vs-trailing-`..` behaviour that drives which Android overloads become wrappers (INV-INS-66 surface).
6. `WrapperEmitter.buildMonitorArgs` (~633–664) — the `target(name)→"recv"` + positional `p0..pN` + `returning→"result"` interleave; make the `wrapperIdx`-skip-when-target-bound rule explicit.
7. `WrapperEmitter.patternMatchesFqnRaw` (~388–409) — array-suffix peeling + subtype-vs-exact.

### pointcut-engine
8. `PointcutExpressionParser.parseCallBody` (~148–189) — the constructor-vs-method split via raw `indexOf(' ')`/`lastIndexOf('.')`/`matchingClose` index arithmetic (the densest under-commented spot in the two parse modules).
9. `InheritanceResolver.walkApkAncestors` — the two "cross into android.jar from an APK leaf" branches (mixed-hierarchy graph walk).
10. (optional) `PointcutExpressionParser.parseOr/parseAnd/parsePrimary` — one-line precedence pointers (class-level grammar already covers them).

### validator (CI-gate tooling — see open question Q1)
11. `BootValidator.capture` (~218–278) — the adb sequence (`uninstall → install -r -g → logcat -c → monkey → sleep → logcat -d → uninstall`): why this order. Plus `firstPackageLikeToken` prefix blocklist rationale.
12. `TraceComparator.parseOracle` (~581–673) — the hand-rolled indentation YAML state machine (baseIndent/itemIndent tracking, the "re-evaluate line at top level" branch).
13. `BaksmaliDiffer.deriveWrapperName` (~233–283) — manual `call(...)` paren-walking + FQN reconstruction (mirrors `WrapperEmitter`; state that intent once, clearly).
14. `BatchValidator.analyzePerSpec` (~319–414) — add method Javadoc + explain the asymmetric gate (non-inferiority for **all** specs vs equivalence for ≥80%).
15. `TraceComparator.scoreOracle`/`f1` (~418–517) — make the confusion-matrix definitions (FP/FN) and the `(tp+fp)==0 → precision=1.0` edge conventions explicit.
16. `CoverageValidator.compare` (~89–137) — add method Javadoc; comment the recall/`delta ≤ 0.01·totalAjc` gate and the vacuous-but-fail empty-pairs branch.
17. `MethodRefAuditor.countMethodRefs` (~113–125) — strengthen the caveat that this is an **approximation**, not the true DEX `method_ids` count, since the whole gate keys on it.

---

## 5. Phase 4 — package-info & generated-HTML completeness

- All 9 `package-info.java` **exist**. Accuracy fixes already covered by A1 (dex-mutator), A3 (validator), A7 (pointcut-engine).
- Sweep the remaining six (`descriptor`, `emitter`, `coverage`, `builder`, `merger`, `cli`) for any stale `{@link}` and confirm each opens with a one-paragraph role statement suitable for the package overview page. Most are already adequate — this is a verification, not a rewrite.

---

## 6. Execution structure

The 9 sub-modules have **disjoint file sets**, so writing agents can run in parallel without git conflicts (no worktrees needed).

- **Step 1 — Phase 1 (accuracy).** One careful agent handles A1–A7 (and A8 if Q2=yes). It must, per defect: read the real implementation → confirm the fact → edit → not touch adjacent good docs. Single commit.
- **Step 2 — Phases 2+3+4, parallel by sub-module.** One agent per sub-module (or grouped: {descriptor, pointcut}, {advice-emitter, dex-mutator}, {coverage, builder, merger, cli}, {validator}). Each agent gets: this plan's items for its module, the design rules (§1), and the instruction to preserve good docs and add only the listed headers/inline blocks.
- **Ordering:** dex-mutator and advice-emitter (the hardest, highest-value inline work) first or given the strongest agent; validator last (lower priority, Q1).

### Verification (gate before each commit)
- `mvn -q -pl :<module> -am compile` — comments never break compile, but this catches any accidental code edit.
- **`{@link}` correctness without HTML** (per Q4 = no site): for every changed/added `{@link}`, confirm the referenced class/member name actually exists (grep/read the target). This is how the A3 dead links (`Layer1BaksmaliDiffer` → `BaksmaliDiffer`) get caught without running `javadoc:javadoc`.
- Spot-check against §1 rules (no restating, no promo, English, WHY-not-WHAT).

### Commit strategy (proposal)
- Commit 1: `docs(dexlib2): fix stale/inaccurate Javadoc & package-info` (Phase 1).
- Commits 2..n: one per sub-module (or per group), `docs(dexlib2/<module>): method headers + inline explanations at hotspots`.
- No `Co-Authored-By` trailer (project rule).

---

## 7. Scope at a glance

| Category | Items | Files touched (approx.) | Priority |
|---|---|---|---|
| A — Accuracy defects | 8 (A1–A8) | 6–7 | **Highest** |
| B — Missing method headers | ~8 methods + 1 class doc | 4–6 | Medium |
| C — Inline density hotspots | 17 hotspots | ~10 | High (serves the stated goal) |
| D — package-info/HTML sweep | 9 files (mostly verify) | ≤9 | Medium |

No file is being rewritten wholesale; the vast majority of existing Javadoc is **kept as-is**.

---

## 8. Open questions — RESOLVED

- **Q1 — validator scope.** ✅ **Include the `validator` module, last / lowest priority** (Phase 3 items 11–17, after the core pipeline).
- **Q2 — stale version string (A8).** ✅ **Fix now** — `InstrumentationCli` `0.8.0-SNAPSHOT → 0.9.1-SNAPSHOT`.
- **Q3 — value-type public fields** (`BootValidator`/`BatchValidator` options/reports). ✅ **Document all public fields**, not only the non-obvious ones.
- **Q4 — generate the Javadoc HTML site.** ✅ **Do NOT generate the site.** Consequently the `javadoc:javadoc` HTML gate is dropped; `{@link}` correctness is verified by confirming the referenced class/member names exist (grep/read) plus `mvn compile`.
- **Q5 — `ThisJoinPointEmitter.signatureFor` stub.** ✅ **Document as an intentional pass-through.** Do not touch the code (this is a docs-only pass).

---

## 9. Explicitly NOT doing

- Not rewriting the already-rich class docs (`RegisterShifter`, `DexWeaver`, `CoverageWeaver`, `MultidexMerger`, `MonitorInvokeBuilder`, `PointcutMatcher`, `BatchValidator`, `TraceComparator`, `BaksmaliDiffer`, …).
- Not adding Javadoc to trivial beans/accessors, `toString`, or picocli `run()` boilerplate (P1).
- Not duplicating `architecture.md` content into code comments — comments link to invariant IDs / `architecture.md §` instead.
- Not touching `src/test` or `grammar-tests` (test-only) as part of this pass.
- Not deleting or refactoring any code (only A6/Q5 `signatureFor` flagged, and only with your approval).
