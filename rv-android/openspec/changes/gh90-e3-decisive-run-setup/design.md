# Design: gh90-e3-decisive-run-setup

## Context

This change is the Python half of a two-repository deliverable. The Java half (`ape` repo, change `telemetry-proof-llm-efficacy`) makes the jar emit the per-step fields that turn a run into evidence: `activity_has_mop`, `pick_channel`, the de-aliased `mop_frontier` boost, single-line `[APE-STEP]` records, and the B1 dead-pair ban. This half decides **what experiment those fields describe**: which arms run, what configuration defines each arm, what the pushed substrate contains, and what provenance is recorded. Neither half is useful alone — the jar without these arms has nothing to contrast, and these arms without the jar produce the same 2.06% attributability the change exists to fix.

Everything below implements decisions already fixed by the project author on 2026-07-29; the source of record is `docs/20260729_propostas_melhorias_e3.md` §0. This document resolves only the implementation details that record left open, and it flags each such resolution explicitly.

Current state of the code this change touches, verified in the worktree:

1. **Arms** live in `ApeRVTool.get_variants()` (`modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py:427`), which returns 26 variants. The frontier configuration is already factored out as the module-level `_FRONTIER_SUBSTRATE` constant (`:318-325`): `_BASELINE_ARM_FLAGS` + `_MOP_SUBSTRATE` + `mop_activity_source_components=True`, `frontier_boost_weight=200`, `mop_frontier_weight=200`, `activity_trigger_enabled=True`. The nine `cal_*` arms already spread it. **There is no arm with MOP guidance off while the frontier stays alive** — that arm is what A1 adds.
2. **Guards** already exist: `ARM_DEFINING_KEYS` (`:171`) with the mapping-completeness and variant-explicitness tests (INV-APV-13/14), plus the `cal_*`-scoped `LLM_ARM_KEYS` guard (INV-APV-26). New arms must satisfy them.
3. **Compaction** is `_compact_static_analysis_json` (`:801-875`): loads the document, dedups `transitions` by canonical fingerprint, writes a minified temp file, returns its path; on `json.JSONDecodeError | OSError | MemoryError` it warns and returns `None`, which the caller reads as "push the source unchanged" (INV-APV-24). The docstring states "two lossless operations" — N6 makes it three and the third is additive, so both the docstring and the spec requirement change.
4. **Property mapping**: `APERV_PROPERTY_MAPPING` (`:75`) already maps `llm_snap_tolerance_px → ape.llmSnapTolerancePx` (`:161`) and `llm_url → ape.llmUrl` (`:140`). `llm_snap_tolerance_px` is deliberately outside `LLM_ARM_KEYS` (`:216`) because the Phase-A jar ignores it — B3 is the change that makes it live.
5. **No provenance capture exists.** The tool knows `llm_url` but never asks the server what it is serving.
6. **No clock↔logcat join exists** anywhere in `aperv_tool`.

Relevant requirements: FR20 (per-tool variant system), FR06 (REACH analysis output), FR11/FR13 (logcat capture and violation detection), FR19 (external tool support), NFR03 (testability), NFR06 (observability).

## Architecture

No new module and no new component in the execution path. Three code sites change inside `aperv-tool`, and one utility is added to the same package.

```
rv-experiment ──► rv-platform ──► ApeRVTool
                                   │
                                   ├─ get_variants()                  ← A1 arms, B2 flag, B3 gate
                                   ├─ configure()                     ← B3 jar-capability gate
                                   ├─ preflight (new, in execute path)← N4 /v1/models + jar stamp
                                   ├─ _compact_static_analysis_json() ← N6 enrichment
                                   ├─ adb capture grace window        ← +15 s → +45 s
                                   └─ (push, run, collect: unchanged)

aperv_tool.analysis.clock_logcat_join   ← A9, offline, never in the run path
        reads: recorded traces + recorded logcat   writes: join report
aperv_tool.analysis.coverage_dump       ← O3, offline, never in the run path
        reads: recorded traces                     writes: per-run coverage rows
```

The decisive run's data path is unchanged: the jar still receives `ape.properties` and `/data/local/tmp/static_analysis.json`, and the only difference in the pushed document is two extra booleans per listener.

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `ApeRVTool.get_variants()` | Declares the three decisive-run arms on `_FRONTIER_SUBSTRATE` | — | `Dict[str, Dict[str, Any]]` |
| `_MOP_OFF_OVERRIDES` (new constant) | The exact key set that turns MOP guidance off while keeping the frontier | — | `Dict[str, Any]` |
| `ApeRVTool._enrich_listener_reach()` (new) | Populates the two handler-reach booleans from the document's `reachability` | `dict` (parsed document) | `int` (listeners enriched) |
| `ApeRVTool._compact_static_analysis_json()` | Dedup → enrich → minify → temp file | `source_path: str` | `str \| None` |
| `ApeRVTool._capture_llm_provenance()` (new) | Live `/v1/models` query + jar file digest | `llm_url: str`, jar path | provenance `dict` |
| `_snap_tolerance_guard` (test-side) | Enforces the B3 coupling: tolerance 150 and declared jar sha travel together | arm dictionaries | pass/fail |
| `aperv_tool.analysis.clock_logcat_join` (new module) | Offline join of step clock against `RVSEC:` lines | run directory | report rows |
| `aperv_tool.analysis.coverage_dump` (new module) | Offline versioned parser of `UICOV` / `UICOV-ACT`, with per-run dump status | run directory | per-run rows + status |

## Mapping: Spec → Implementation → Test

| Requirement / Invariant | Implementation | Test |
|-------------|---------------|------|
| Decisive Run Arm Set (FR20) | `get_variants()` + `_MOP_OFF_OVERRIDES` | `test_decisive_arms_single_factor_diff`, `test_decisive_arms_explicit_keys` |
| INV-APV-29 control-arm shape | `_MOP_OFF_OVERRIDES` (weights zeroed, `mop_data` kept) | `test_control_arm_keeps_mop_data`, `test_control_arm_zeroes_all_mop_weights` |
| INV-APV-30 frontier preserved in every arm | all three arms spread `_FRONTIER_SUBSTRATE` | `test_all_decisive_arms_carry_frontier_boost` |
| B2 source-components flag | `_FRONTIER_SUBSTRATE["mop_activity_source_components"]=True` inherited | `test_decisive_arms_set_source_components_explicitly` |
| Snap Tolerance Gating (INV-APV-34) | Paired declaration in the arm dictionary; `[APE-BUILD]` banner comparison at smoke time | `test_tolerance_requires_jar_sha_declaration`, `test_dangling_jar_sha_declaration_fails`; smoke gate 6.3 |
| Static Analysis JSON Compaction (MODIFIED) | `_compact_static_analysis_json()` + `_enrich_listener_reach()` | `test_enrich_transitive_handler_flagged_direct`, `test_enrich_unreachable_handler_false`, `test_enrich_unknown_signature_false` |
| INV-APV-31 additive-only enrichment | `_enrich_listener_reach()` writes only two keys | `test_enrichment_adds_only_two_keys`, `test_enrichment_failure_still_pushes`, `test_source_file_unmodified` |
| INV-APV-32 any-depth direct semantics | `_enrich_listener_reach()` derives from `reachesTarget`, never copies `directlyReachesTarget` | `test_direct_is_not_copied_from_producer_field` |
| Per-Run LLM Backend Provenance (INV-APV-33) | `_capture_llm_provenance()` | `test_provenance_from_live_query`, `test_provenance_records_failure_not_config`, `test_no_query_for_non_llm_arm` |
| Offline Clock-to-Violation Join (INV-APV-35) | `aperv_tool.analysis.clock_logcat_join` | `test_join_reproduces_iter0_totals`, `test_join_run_without_violations`, `test_join_never_writes` |
| Offline Coverage-Dump Parser (INV-APV-36) | `aperv_tool.analysis.coverage_dump`, Activity-grain aggregation only | `test_cross_run_join_uses_activity_grain`, `test_state_keys_never_joined_across_runs`, `test_per_arm_presence_reproduces_iter0` |
| Dump status per run (INV-APV-37) | `coverage_dump` status classifier (complete / partial / absent) | `test_truncated_tail_is_partial`, `test_run_without_dump_is_reported_not_dropped`, `test_rate_carries_its_denominator` |
| Capture Grace Window (MODIFIED execution flow) | `timeout_seconds + 45` in `tool.py` | `test_adb_timeout_uses_45s_grace`; smoke reports observed teardown overrun (task 6.2) |
| RQ-C1 power probe (design diagnostic, no code) | pre-registration §7 declaration + 80-run probe at 300 s | no unit test — gated by tasks 7.1 (blocking declaration), 7.4 (reuses smoke gates 6.3/6.4), 7.6 (reading rule fixed in advance) |

## Goals / Non-Goals

**Goals:** give the experiment its first control arm, in the only shape that isolates MOP guidance; make the direct/transitive scoring axis carry real information without touching the producer; record what actually served each run; and provide the offline evidence base for the "reaching fires the monitor" premise — all implementable and unit-testable without the jar, so the Python half can land while the Java half builds.

**Non-Goals:**
- No change to `rvsec-gator` and no re-running of static analysis (standing rule).
- No modification of source `.apk.json` files — the archived artifact stays byte-identical to the producer's output.
- No mock LLM. Real smoke runs go through rv-platform against a real SGLang server.
- No manual emulator management, in any context, ever.
- No new arm outside the frontier substrate (INV-APV-30).
- `bitbanana` does not enter the 40-APK subset.
- The N5 runtime-logcat mechanism is not designed here; A9 only produces the evidence that would justify it.
- No script for N2 — it is a recorded measurement rule (see Decisions).

## Decisions

### D1 — The three arms, and why the record needed one more decision

The ledger fixed the internal design of the MOP-off arm but never enumerated the arm set of the decisive run. The set below is decided **here**, and it is the minimum that answers both questions the run must answer with a shared reference:

| Arm | Variant name | MOP guidance | LLM | Role |
|---|---|---|---|---|
| 1 — reference | `mop_on_llm_off` | on | off | shared baseline of both contrasts |
| 2 — control | `mop_off_llm_off` | **off** | off | arm 1 vs 2 = effect of MOP guidance (RQ-C1) |
| 3 — LLM | `mop_on_llm_70` | on | **on, 70%** | arm 1 vs 3 = effect of adding the LLM (RQ-C3) |

Each contrast is single-factor because arm 2 differs from arm 1 only in the MOP keys and arm 3 differs only in the LLM keys — a property the guard tests assert by diffing the dictionaries rather than by trusting review. Arm 1 is configurationally `sata_mop_act_frontier` (the ANC2 anchor), so the reference is the configuration that already won the previous multi-arm comparison and no new baseline is invented.

The names are decided here rather than left to implementation because the variant string is the resume identity key (`platform.py:308-318`) and the consolidation column key (`{arm}__{metric}`), so it must exist before any manifest is generated. Spelling out both factors makes each contrast legible from the results CSV header. One consequence needs handling in code: none of the three carries the `cal_` prefix that scopes the `LLM_ARM_KEYS` guard, so that guard's scope must be extended to reach arm 3 — otherwise the guard-verification task passes vacuously.

Alternative considered and rejected: three arms where arm 2 is "no substrate at all". That was the ledger's optional third variant. It answers a different question ("what does the whole mop_data-dependent family contribute?") and confounds MOP guidance with generic WTG navigation. It stays available as an optional fourth arm, not as the control.

### D2 — Why the control arm keeps the document and zeroes the weights

Three shapes could plausibly mean "MOP off". Two of them silently destroy the experiment:

| Shape | What actually happens | Verdict |
|---|---|---|
| `ape.mopDataPath` set, file missing | `requireMopArm` raises `StopTestingException` → **run aborts** (`StatefulAgent.java:216-223`, INV-MOP-22) | fatal |
| `mop_data` omitted → path unset | Loads as `null` without aborting, but `WtgPass:29` and `FrontierPass:35` both require `mopData != null` → **generic WTG and frontier navigation die too** | confounded |
| Document present, weights zeroed, trigger off | Short-circuits are no-ops (`pickBestMopTarget` requires `mopBoost > 0`), MOP boosts never fire, frontier and WTG passes keep running on generic signal | **chosen** |

The residual `[M]` markers still rendered in the prompt are irrelevant for arms 1 and 2 because both have the LLM off — the marker only reaches a model that is not being consulted. This is why the primary MOP contrast is measured with the LLM off, and it is a reason the arm set is shaped as in D1 rather than crossing both factors.

In arm 3 the markers do reach the model, and MOP guidance survives the LLM override. A successful LLM answer bypasses the deterministic MOP short-circuits (`SataAgent.java:580-587`, `:1544-1551`, below the LLM hooks at `:421-453`), but the hooks pass the MOP document through (`getMopData()` at `:425`, `:439`, `:449`) and the prompt renders `[DM]`/`[M]` per widget with an explicit priority instruction. Measured over the recorded iter0 traces, the LLM channel picks MOP-boosted actions at 4.24% against SATA's 1.21%, and MOP-boosted steps per run are 6.11 in the 70% arm against 6.05 in the reference — flat. What the override displaces is the `Coverage` channel, so the cost falls on new states, not on MOP reach, and the arm 1 ↔ arm 3 contrast stays single-factor.

Implementation: a module-level `_MOP_OFF_OVERRIDES` constant spread over `_FRONTIER_SUBSTRATE`, so the control arm is literally "the reference arm plus this delta" in the source, and the single-factor property is visible at the definition site rather than only in a test.

### D3 — N6 lives in the compaction step, and what "direct" now means

The enrichment could live in the producer (rejected: standing gator rule, plus re-analysis of hundreds of APKs), in a separate offline pass rewriting the JSONs (rejected: mutates the archived artifact that offline consolidation re-parses), or inside the existing in-memory compaction (chosen). The compaction already parses the document and writes a derived temp file that is discarded after the push, so the enrichment costs one pass over `windows[].widgets[].listeners[]` and zero extra I/O, and it cannot contaminate any artifact.

The semantic redefinition is the substance of the item, not an implementation detail. The producer's `directlyReachesTarget` is 0-hop: true only when the method's own body invokes a JCA target. UI handlers delegate, so the field is `false` for every handler in the corpus — which is exactly why `[DM]` is 0 across all 181 apps and `mop_weight_direct=500` has never fired. The redefinition is:

- `handlerReachesTarget` := `reachesTarget` of the handler method, looked up by exact signature in `reachability[].methods[]`.
- `handlerDirectlyReachesTarget` := **the handler of this widget reaches a JCA target at any depth** — derived from the same `reachesTarget` bit of that handler, never copied from the producer's 0-hop field (INV-APV-32).

The distinction the scoring pipeline then expresses is *this widget's own handler leads to crypto* (direct) versus *this widget sits in a container from which crypto is reachable* (transitive, computed by the consumer's containment logic). That is the distinction `mop_weight_direct` was always meant to reward.

Lookup is by exact string match on the Soot signature, because both fields come from the same document and the producer emits handler signatures in `listeners[].handler` in exactly the form it uses as `methods[].signature`. A miss yields `false` on both fields and no per-miss warning — misses are expected in apps whose handler set and reachability set were computed over different class subsets.

**Known scope limit, recorded honestly**: in Compose apps there are no widgets and no listeners at all (median 0 widgets; 74.3% of Compose-bundled apps have zero listeners anywhere in the document), so the enrichment is a no-op there. Note that "Compose-bundled" here — apps shipping the Compose runtime — is a wider population than the detector-defined "Compose app" of D7, and the two are not interchangeable as denominators; any figure quoted from one SHALL name which it used. N6 improves the direct/transitive axis in the View and hybrid strata only, and its expected effect must be counted over the apps that have widgets, not over the 181. See `docs/20260730_compose_gator_substrato_estatico.md` §5.4.

### D4 — B3's gate is a declaration plus a verification, because the jar cannot be introspected

The obvious mechanism — open `ape-rv.jar` and read a stamped capability entry — **cannot work**, and the reason is worth recording because it is easy to re-derive wrongly. APE-RV's build provenance (issue #14 in the `ape` repository) is deliberately implemented as a *generated Java constant* dexed into `classes.dex`, explicitly **not** as a packaged resource: `d8` converts only `.class` entries, so a `.properties` resource bundled into the intermediate jar is dropped from `ape-rv.jar` and `getResourceAsStream` returns `null` on device (INV-BUILD-09). The only readable form of the stamp is the `[APE-BUILD]` banner the agent emits once per session, carrying `git_sha`, `jar_built`, `schema`, and the MOP load state (INV-BUILD-11). That banner exists only *after* a run starts — too late to gate configuration.

The gate is therefore split across the two moments where each half is actually possible:

| Moment | Mechanism | Enforced by |
|---|---|---|
| Configuration | The arm carrying `llm_snap_tolerance_px=150` also carries the expected jar git sha; both present or both absent | Guard test in the suite |
| Verification | The `git_sha` in the smoke run's `[APE-BUILD]` banner is compared against the declared value | Smoke gate, before the decisive run |

This keeps the coupling visible at the definition site (a reader sees the tolerance and the jar it belongs to in the same dictionary), enforced mechanically (the guard fails on either half alone, including a dangling declaration left behind after a rollback), and confronted with reality before any wall-clock is spent (the banner is emitted before the first MOP-scoring line, so a stale jar is caught in the smoke's first seconds).

Alternatives rejected: pinning the jar's file sha256 (works exactly once — the next rebuild for any reason breaks it, and the failure mode is silent reversion rather than a legible message); applying 150 unconditionally and checking afterwards (the bad combination would already have consumed the decisive run); asking the sister change to add a resource stamp (it would violate INV-BUILD-06 and be dropped by `d8` anyway).

### D5 — A9 and N4 live in the tool package, not in a campaign directory

The author's decision, and the reason is that the thesis consumes the **real** experiment, not the calibration. `experimento-cal/scripts/` is scoped to one campaign; a utility placed there would have to be copied or imported across a repository boundary to serve the real run. Both therefore live in `aperv_tool`: N4 inside the tool's execute path, A9 as `aperv_tool.analysis.clock_logcat_join`, importable and unit-testable without a device.

### D6 — Provenance is a live query, and its failure is data

Reading the configured model name would record the intent, not the fact. The failure this guards against is precisely intent and fact diverging: an SGLang server restarted with a different checkpoint, quantization, or sampling default serves a different experiment under the same configuration, and nothing downstream could tell. So the record comes from `GET {llm_url}/v1/models` at run start.

When the query fails the run proceeds — aborting would trade a small evidential gap for a lost run — but the fields record the failure explicitly and are never back-filled from configuration (INV-APV-33). Downstream analysis can then distinguish "we know it was model X" from "we do not know", which a config-derived value would erase.

### D7 — Recorded measurement rules (no code)

Two rules are decided here and deliberately produce no script, per P1:

- **N2 — grounding measurements report both metrics.** Any future measurement of LLM grounding reports centre distance **and** containment. The two disagree systematically (a point can be inside a widget's bounds while far from its centre — the geometry that item B4 fixes in the jar), and reporting only one has already produced numbers that could not be compared across documents. No script is created because the offline harness that would host it is frozen.
- **Pre-registered stratification by UI toolkit.** The decisive run's analysis reports the paired Δ per UI-toolkit stratum in addition to the aggregate. Reason: in ~30% of Compose apps every activity is MOP-flagged, so `activity_has_mop` is constant 1 there and the MOP-guided arm has no contrast to exhibit — a null Δ in that stratum is absence of contrast in the instrument, not evidence against the hypothesis, and pooling the strata biases the aggregate toward the null. The detector is deterministic and runs offline over the existing `.apk.json` files: an app is Compose when `androidx.compose.runtime.Composer` appears in any `reachability[].methods[].signature` (the Compose compiler injects that parameter into every `@Composable` function). Measured basis and full rationale: `docs/20260730_compose_gator_substrato_estatico.md` §4 and §5.2.

- **Pre-registered normalization by step count.** The decisive run's analysis reports each outcome per *step* alongside per *run*. Reason: on this substrate the LLM arm is latency-bound, not selection-bound, and the two are indistinguishable at run level. Measured on the 84 `cal_a1` runs of iter0 against the paired reference arm (`sata_mop_act_frontier`, the same configuration as arm 1): the LLM arm executes **0.622×** the steps and discovers **0.729×** the distinct states, losing on 67 of 80 APK×rep pairs (median Δ −7 states), while spending **35%** of the 300 s budget waiting on inference. Both ratios are computed over the 80 paired runs as ratios of means — the step ratio is 161.8 ÷ 260.2 (see the dose paragraph below). The medians are reported separately because they do not reproduce the ratios and are not their basis: 168 vs 264.5 steps (ratio of medians 0.635) and 22 vs 27 distinct states (0.815). Stating both keeps a reader from deriving one from the other. Per step the two arms are near-equal — ≈11.9% vs ≈12.5% new-state rate. A run-level null therefore carries two incompatible readings, "the LLM selects worse" and "the LLM selects at the same quality but gets fewer chances", and only the per-step figure separates them. The normalization is descriptive, not an additional test family, and costs nothing at run time — the step count is already on every `[APE-STEP]` line. It does **not** displace the run-level outcome, which stays primary: a tool that cannot spend its wall clock is genuinely worse in deployment. The per-step view names why, so a decision to drop the LLM rests on the right reason.

### D8 — The LLM dose of arm 3 is 70%

Arm 3 reuses the `cal_a1` LLM key block verbatim: `llm_percentage=0.7`, prompt variant `v13`, temperature 0, `top_p` 0.6, `top_k` 50, both routing triggers on.

The dose has to be high enough to be a treatment and low enough to stay a single-factor contrast, and iter0 bounds it from both sides. Below ~30% there is nothing to measure: `cal_a3` routed on stagnation alone and made 0.1 calls per run (73 of 80 runs made zero), landing at 259.9 steps against the reference's 260.2 — it is the reference with a dead trigger. Above 70% the knob stops buying what it promises: the percentage gates only the random channel while `Coverage`, `Form` and `MOP` keep priority, and 34% of calls return `no_match` and fall back to SATA, so nominal 70% means the LLM decides about **46%** of steps (0.70 × 0.66) on the iter0 jar. Pushing to 90% would add roughly **13** points of decision share (0.20 × 0.66), and the residual algorithmic share cannot be removed without disabling the priority channels — which would make arm 3 differ from arm 1 in MOP keys too, destroying the property D1 exists to protect.

**On the decisive-run jar that share is lower still, and the figure matters because both changes reason about it.** B1 introduces a new `no_match` cause (`reason=dead_pair`) that did not exist when the 34% was measured, so the two refusal mechanisms compose rather than overlap: the ban refuses 27.5% of the decisions that survive to be executable. Composing the three gates — 0.70 × 0.66 × 0.725 — arm 3's realized LLM decision share is **≈34%**, not 46%. This is arithmetic over figures both changes already assert, not a new measurement, and it does not change the dose: 34% is still unambiguously a treatment, and it sits comfortably inside the sister change's binding criterion (refusal under 30% of the executable stream, `ape` design D1), which is the criterion that rejected k=1. It is recorded because the dose argument here and the threshold argument there are arguments about the same quantity, and each was previously made holding the other mechanism at its pre-change value.

What settles it on 70% rather than 30% is that only 70% has a measured counterpart at 300 s on this same substrate and subset (a counterpart the confound paragraph below qualifies, and which survives as an exploratory reading rather than a confirmatory one): `cal_a1` is the sole arm whose paired difference against the reference excludes zero (Δ`cov_mop` −4.07 [−7.39; −0.40], Holm p=0.0169). That makes the 1800 s result readable as a dose × budget interaction instead of an isolated number — a dose with no 300 s counterpart would leave a null unable to separate "dose too high" from "budget still insufficient". The accepted cost is 161.8 steps per run against 260.2, a 38% deficit from inference latency; at 300 s it exactly cancels the arm's per-step advantage (both discover 1.12 distinct violations per run after the first 10 s), and closing that cancellation is what the 1800 s budget is for.

**Confound to declare: the 300 s counterpart ran a different LLM path.** The paragraph above rests on `cal_a1`@300 s and arm 3@1800 s being the same treatment with only the budget changed, and that is no longer true — the qualification below governs it. The sister change (`ape`, `telemetry-proof-llm-efficacy`) puts its whole efficacy group in the decisive-run jar; none of it was in the iter0 jar. **Seven items** change LLM-arm behaviour, not one:

| Item | Change to the LLM path | Direction |
|---|---|---|
| B1 | dead-pair ban — refuses **27.5%** of the arm's executable LLM decisions at **k=5**, raising per-decision yield ≈11.4% → ≈14.7% | favours the LLM |
| B6(i) | `click` answers constrained to `MODEL_CLICK` (today CLICK executes on 80.9% of them) | favours the LLM |
| B6(iii) | per-request tool schema — stops advertising `type_text` the prompt denies | favours the LLM |
| B6(iv) | `fixTextEdit` — a click resolving to an input widget becomes text entry | favours the LLM |
| N1 | identifiers in prompt element lines (measured hit rate 33.1% without vs 71.4% with) | favours the LLM |
| B4 | edge-based snapping replaces centre distance | favours the LLM |
| B7(i) | stagnation trigger actually fires — more LLM calls, therefore more latency | adds cost |

The A-group items are arm-neutral telemetry and do not enter this list. The two points therefore differ in budget **and** in the LLM path: there is no clean dose × budget interaction available to read.

*B1's threshold moved after this table was first written (2026-07-31, sister change design D1).* The original k=3 was chosen from a sweep that keyed both ban result types by `(state, pixel)`; the shipped `matched` key is `Name`-level and covers 84.1% of the decision stream, under which k=3 refuses 37.6% rather than 27.9% — past the "under 30%" ceiling that was the reason for choosing it. k=5 restores 27.5%. Nothing in this change depends on the value of k: B3's gate (INV-APV-34) is on the **presence** of the ban in the jar, not on its threshold, and the primary contrast holds every one of the seven items constant between arms 1 and 3. The refusal figure in the table is updated only so the two changes do not disagree in print.

**The confound is directional, and the analysis commits to that asymmetry in advance.** Six of the seven push the arm toward better performance; only B7(i) adds cost. The comparison is consequently informative in exactly one direction, and the pre-registration fixes which before any result is seen:

- **arm 3@1800 s null or negative** → the comparison is read, and it *strengthens* the conclusion: the LLM path was repaired in seven places and given 6× the budget and still does not beat the algorithm. The confound reinforces this reading rather than undermining it.
- **arm 3@1800 s positive** → the comparison is **not** read. The gain cannot be apportioned between budget and repairs, and attempting it after the fact would be a post-hoc choice.

The cross-budget comparison is therefore carried as an **exploratory** analysis with that directional commitment recorded before results (`docs/20260730_preregistro_corrida_decisiva.md` §7). It is not a confirmatory outcome and decides nothing.

**What is unaffected:** the primary contrast. Arms 1 and 3 run the same jar, paired per APK, so every item above is held constant across the comparison that actually decides whether the LLM stays in the design. The cost of this confound is one interpretive paragraph in the report, not the experiment.

### D9 — O3 and the grace window: two independent attacks on the same loss (ADDED 2026-07-31)

Neither item is in the source of record; both come from the adversarial verification and are decided here.

**The parser (O3) exists because the recovery has no consumer.** The sister change hoists the dump so that 333 of the 338 runs that lose it keep it — but a grep for `UICOV` across the whole rv-android tree returns zero hits in Python, so today that recovery would produce data nothing reads. The parser is offline, read-only and versioned.

Two constraints on it are not preferences. **Activity grain is mandatory**: the per-state `UICOV` key embeds `StateKey.toString()`, whose hash includes the JVM identity hash of a `Naming` object overriding neither `equals` nor `hashCode`, so state keys do not survive across runs — measured cross-replica Jaccard is 0.000 at mean, median *and* maximum, meaning not one state line pairs with its counterpart. Anything aggregated across runs therefore comes from `UICOV-ACT`. **Every run is reported with an explicit status** — complete, partial or absent — because the quantity being studied *is* the loss rate: a parser that silently dropped the runs without dumps would compute coverage over the survivors and report it as coverage over all runs, which is the exact error the 165/880 figure came from.

**The grace window is a hypothesis, and is labelled as one.** `tool.py` gives the `adb` invocation `timeout_seconds + 15` before SIGKILL, and among runs whose teardown completed the overrun reaches 12,991 ms with 32 runs stacked against that ceiling and none beyond it — the signature of a hard wall, not a distribution. Widening to +45 s costs one line and touches no jar. It is **not** redundant with the sister change's reordering and does not replace it: the reordering moves the dump ahead of the expensive write, the window gives the whole chain room to finish. What cannot be claimed is a recovery rate — the true teardown duration of the runs that were cut is unobservable, which is what censoring means — so the smoke reports what the new window actually cost rather than confirming a prediction.

### D10 — The RQ-C1 power probe, and why it runs at 300 s (ADDED 2026-07-31)

The verification established that the exact McNemar cannot reject at Holm α=0.025 with fewer than 7 discordant pairs, and that the iter0 analogues predict 3–4. The gap this probe fills is that **no recorded arm answers the question for the real contrast**: no iter0 arm fixes the frontier substrate while turning MOP off, and the nearest analogue (`ape:default`) differs in 18 keys rather than the 6 that separate arms 1 and 2. So the decisive run could consume 8 h to discover its primary contrast had nothing to measure.

**300 s, not 1800 s, and the reason is isolation.** At 300 s the probe (a) produces none of the decisive run's runs, so no datum is reused or discarded — run identity is `(apk, tool, variant, repetition, timeout)`, and the differing timeout keeps the two campaigns disjoint on resume; and (b) is directly comparable to the confounded iter0 analogue, isolating exactly what changes: a MOP-off arm that *keeps* the frontier substrate. At 1800 s it would stop being a probe and become the RQ-C1 half of the decisive run — a legitimate choice, but then §4's multiplicity structure has to be rebuilt first, because deciding about RQ-C3 after seeing RQ-C1 turns a simultaneous two-contrast family into a sequential design, for which a fixed two-step Holm is no longer the right correction. (§4 fixes the family; it says nothing about ordering, so this consequence is an inference from it, not a quotation of it.)

**It is a design diagnostic, never an outcome**, and the anti-peeking discipline is the substance of the item rather than paperwork around it: the probe must be declared in the pre-registration §7 *before* it runs, stating that its results never enter the confirmatory analysis, and its reading rule is fixed in advance (`tasks.md` 7.6). Task 7.1 is blocking for the rest of the group for that reason.

**One residual the artifacts cannot settle, and it is the author's call.** The probe's `n_disc ≤ 3` branch admits "revise the primary outcome before freezing" as an option. The pre-registration states that it fixes the analysis plan *before any result is seen*, and the probe measures the same estimand as the primary contrast — same arms, same binary outcome, only the budget differs. Declaring the probe in advance blocks peeking on its *result*; it does not by itself block the result from feeding back into the *choice of outcome*. The design here makes the sequence auditable rather than impossible (task 7.7 requires the probe's journal stamp to be separate from the freeze stamp, so the order of the two events is inspectable). Closing it fully requires pre-committing, before the probe runs, which branch will be taken at `n_disc ≤ 3` — or declaring the primary outcome non-revisable whatever the probe returns.

## API Design

### `_enrich_listener_reach(document: dict) -> int`

Populates the two handler-reach booleans in place.

- **Preconditions**: `document` is the parsed static-analysis JSON. No structural guarantee is assumed — every section access is defensive.
- **Postconditions**: every object in `windows[].widgets[].listeners[]` carries `handlerReachesTarget: bool` and `handlerDirectlyReachesTarget: bool`. No other key anywhere in the document is added, removed, reordered, or altered (INV-APV-31). Returns the number of listeners enriched.
- **Errors**: raises nothing. A malformed `reachability` section causes the function to return `0` with no fields written, leaving the document valid for the dedup+minify path.

### `_capture_llm_provenance(llm_url: str, jar_path: str) -> dict`

- **Preconditions**: called once per run, before execution, only when the arm declares LLM keys.
- **Postconditions**: returns `{"llm_backend", "llm_model", "llm_sampling", "jar_sha256", "capture_status"}`. `capture_status` is `"ok"` or a failure token; on failure the model and sampling fields are `None`, never config-derived (INV-APV-33). `jar_sha256` is the digest of the jar file as pushed — it identifies the binary for post-hoc correlation, and is **not** the B3 gate (D4: the gate's runtime half is the `[APE-BUILD]` banner's `git_sha`).
- **Errors**: network and parse failures are caught and encoded in `capture_status`; the run is never aborted.

### `clock_logcat_join(run_dir: Path) -> JoinReport`

- **Preconditions**: `run_dir` contains the recorded trace and logcat artifacts of one run.
- **Postconditions**: returns rows correlating step clock positions with `RVSEC:` violation timestamps. Every artifact read is byte-identical afterwards (INV-APV-35). A run with zero violations yields a valid empty-violation report, not an omission.
- **Errors**: `SystemExit(2)` on a missing or unreadable run directory, naming the path.

## Data Flow

**Configuration**: `get_variants()` resolves the arm dictionary → `configure()` validates and consults `_jar_declares_dead_pair_ban()` to decide `llm_snap_tolerance_px` → `APERV_PROPERTY_MAPPING` translates the surviving keys into `ape.properties`.

**Substrate**: `_find_static_analysis_file()` locates `<results_dir>/<apk_name>.json` → `_compact_static_analysis_json()` parses it → `transitions` dedup → `_enrich_listener_reach()` adds the two booleans → minified temp file → pushed to `/data/local/tmp/static_analysis.json` → temp unlinked. The jar's `MopData` then reads `listeners[].handlerReachesTarget` / `handlerDirectlyReachesTarget` with precedence over its local join (`MopData.java:516-517,531-533`), so the enrichment reaches the scoring pipeline with no jar change.

**Provenance**: at run start, `_capture_llm_provenance()` queries `/v1/models` and reads the jar stamp → both land in the task output next to the run's results.

**Offline analysis**: after the run, `clock_logcat_join` reads the recorded artifacts and emits the correlation report. Nothing in this path touches a device.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `json.JSONDecodeError`, `OSError`, `MemoryError` | `_compact_static_analysis_json` | Warn, return `None` (INV-APV-24) | Caller pushes the source unchanged |
| Malformed `reachability` section | `_enrich_listener_reach` | Warn once naming the file, return `0` | Dedup + minify + push proceed un-enriched (INV-APV-31) |
| Handler signature not in `reachability` | `_enrich_listener_reach` | Both fields `false`, no warning | Expected; not a failure |
| `/v1/models` unreachable or malformed | `_capture_llm_provenance` | Encode in `capture_status`, never infer from config | Run proceeds; analysis sees "unknown", not a wrong value |
| Declared jar sha absent while tolerance is 150 (or vice versa) | Guard test | Fail the suite naming INV-APV-34 | Restore the pairing or drop both |
| Observed `[APE-BUILD]` `git_sha` differs from the declared one | Smoke gate | Fail before the decisive run, naming both shas | Rebuild or correct the declaration |
| Missing run directory | `clock_logcat_join` | `SystemExit(2)` naming the path | Operator supplies the correct path |

## Risks / Trade-offs

- [The control arm's zeroed weights do not fully silence MOP guidance, e.g. a code path boosts without consulting a weight] → the smoke gate asserts `decision_source=MOP` count == 0 and the `mop=` field always 0 across the whole control-arm smoke; a single non-zero occurrence invalidates the arm before the decisive run consumes wall-clock.
- [N6's redefined "direct" is too **sparse** to discriminate] → a census over the 40-APK subset, applying exactly the lookup N6 implements, flags 160 of 45,200 listeners (**0.4%**), with only 7 of 40 apps carrying any flaggable listener (`aegis` 79, `freeotpplus` 38, `owncloud` 12, `messages` 12, `cry.otp` 9, `vscan` 6, `blau` 4). N6 still earns its place — those 160 widgets move from 300 to 500 against zero direct-flagged widgets today — but the axis is reported as sparse, and the smoke's APK selection has to come from those 7 apps or the `[DM]` gate fails by sampling rather than by defect.
- [The decisive run's primary outcome may be insensitive: `mop_unique` saturated at 4.12–4.41 across all eleven iter0 arms, and 73% of distinct violations appear within 10 s of launch, before exploration begins] → out of scope for this change, which defines arms rather than the analysis plan; recorded here because it conditions how this change's output is read. The registered response is `docs/20260730_preregistro_corrida_decisiva.md`, which makes the binary per-app outcome (exact McNemar on "found ≥1 violation") the primary and demotes the continuous delta to secondary — chosen precisely because this regime is where the continuous outcome has least to see.
- [B3's gate is declarative at configuration time, so a wrong declaration is only caught at smoke time] → the smoke's `[APE-BUILD]` banner is emitted before the first MOP-scoring line, so the mismatch surfaces within seconds of the smoke starting and costs no decisive-run wall-clock; and the guard test makes the far more likely error — tolerance and declaration drifting apart — a suite failure.
- [A9's join is only as good as the clock alignment between the trace and logcat] → the validation gate is exact reproduction of three independent totals (9,586 lines / 605 runs / 32 APKs) over recorded data; a misalignment that changed attribution would move at least one of them.
- [The whole change lands hours before the decisive run, with no slack for a second rebuild] → every item here is unit-testable offline against recorded iter0 data and needs no device, so the Python half can be complete and green before the jar exists.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit | Arm dictionaries: control-arm shape, single-factor diffs, explicit flags, existing `ARM_DEFINING_KEYS`/`LLM_ARM_KEYS` guards still pass | Pure dict assertions, no I/O | ~8 |
| Unit | Enrichment: transitive handler flagged direct, unreachable handler false, unknown signature false, additive-only, malformed section degrades, source untouched | Fixtures built from real `.apk.json` excerpts | ~8 |
| Unit | B3 gate coupling: tolerance 150 requires the declared jar sha; a dangling declaration fails too | Pure dict assertions | ~2 |
| Unit | Provenance: live query recorded, failure encoded not inferred, no query for non-LLM arms | Stubbed HTTP boundary | ~3 |
| Integration | A9 join against the recorded iter0 corpus | Real recorded artifacts, read-only | ~3 |
| Integration | Coverage-dump parser against recorded iter0 traces: complete dump, absent dump, synthetic truncated tail, per-arm presence reproducing the recorded 43.8%–65.0% range and 462/800 overall, fixtures byte-identical afterwards | Real recorded traces as read-only fixtures | ~6 |
| Real smoke | Infrastructure: containers up, emulator boots, APKs install, every task COMPLETED, coverage > 0, SGLang answers, the intended jar is the one running — plus the single behavioural check whose failure invalidates the run (control arm emits zero `decision_source=MOP` and `mop=` always 0) | 3 APKs × 3 arms, short timeout; APK set must include `freeotpplus` and `aegis` (§Risks: the `[DM]` gate is reachable on 7 of 40 apps only); **no mock LLM, no manual emulator management** | 1 run |

Test command follows the CI contract: `uv run pytest --import-mode=importlib -o "addopts=" modules/aperv-tool/tests/`.

The A9 validation gate is the sharpest test in the change: reproducing 9,586 `RVSEC:` lines across exactly 605 runs and 32 APKs over the recorded corpus is a three-way check that no plausible-but-wrong join can pass by accident.

## Open Questions

Three decisions are outside this change's scope but block the run it feeds. None is answered here; all three are recorded so they are not discovered on the morning of the launch.

- **Where the decisive run lives.** No artifact answers this. `experimento-cal/` is scoped to the calibration campaign by its own spec, and the standing rule separates calibration from the real experiment, so a new `iterN/` there is not obviously legitimate; a hand-built `experimento-<date>/` gives up the resolved manifest, preflight and journal that the campaign scaffold provides. Whatever is chosen has to precede manifest generation, since the manifest is what pins arms, image and dose. Note that D5 decides where the *utilities* live, not where the run lives — the two questions are unrelated.
- **The pre-registration is written but not frozen.** `docs/20260730_preregistro_corrida_decisiva.md` fixes the outcomes, the pairing unit, the tests and their correction, the tie-breaking rule, the toolkit stratum and the falsification criteria. What remains is the freeze itself: recording its sha256 in `calibracao/journal.jsonl` before the run starts, since an unstamped pre-registration carries no evidential weight. Three of its own open items also remain — D13/C12 (quality criterion), where the run lives, and **the §7 declaration of the RQ-C1 power probe that task 7.1 makes a blocking prerequisite** (D10: without it the probe is peeking on the pre-registered contrast). All three have to be settled before the freeze, because the freeze is what makes the document evidence. (The cross-budget reading was a third; it is settled — exploratory, with the directional commitment recorded in D8 and §7 of the pre-registration.)
- Whether the optional fourth "no substrate at all" arm runs at all is a wall-clock decision to be taken when the jar lands and the real per-arm cost is known. At 1800 s it would add 40 runs, taking the campaign from ≈ 8.0 h to ≈ 10.5 h.
