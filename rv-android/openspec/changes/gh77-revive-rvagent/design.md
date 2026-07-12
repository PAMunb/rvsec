# Design: Revive rv-agent as Local Experimental Arm

**GitHub Issue**: #77
**Proposal**: `proposal.md`
**Input report**: `docs/20260712_investigacao_ressurreicao_rvagent.md`

## Context

rv-agent is the Python host-side Android testing tool (UIAutomator2 + LangGraph + Qwen3-VL/SGLang) in `modules/rv-agent/`, wrapped as an rv-platform plugin by `modules/rvagent-tool/`. It shares lineage with APE-RV through rvsmart: both inherited the MOP prioritization primitives (SuccessorTracker, PlateauDetector, +500 direct / +300 transitive weights, v13/v17 prompts). Since rv-agent left CI (commit `674642a0`, 2026-05-31), the concepts kept evolving only in APE-RV — the canonical source for this port is the **`mop-fairtest` branch** (working dir `ape-mop-fairtest/`, ~41 commits ahead of master); all ported code must be read from that branch, never from master.

Verified current state (2026-07-12): rv-agent installs from the uv workspace, 1787/1865 tests pass offline (2 real failures in obsolete recovery-mode tests; 13 SGLang-dependent failures and 39 emulator-dependent errors are environmental), the gh60 MOP→Target rename is applied, and the plugin/static-data contracts with rv-platform are intact:

- `AbstractTool` contract: `modules/rv-android-core/src/rv_android_core/tools/abstract_tool.py:86-136` (`get_variants`, `configure`, `get_tool_spec`, `execute_tool_specific_logic`).
- Static-analysis handoff: `modules/rv-platform/src/rv_platform/components/static_analysis.py:109-142` populates `task.static_data` with the shared `rv_android_core.domain.static.StaticAnalysisData` model (`classes`, `windows`, `wtg`, `components`, `complete`); `rvagent_tool/tools/rvagent/config.py` consumes it. rv-agent has no parser of its own — the port only extends which fields are *read* (notably `components`).
- The ranking layer is already pass-shaped: `Scorer` ABC (`modules/rv-agent/src/rv_agent/strategies/rvagent_strategy/ranking/scorers.py:41`), `ActionRanker(scorers)` (`ranking/action_ranker.py:31`), `RankingContext` (`ranking/context.py:19`, already carries `graph`, `ui_coverage`, `transition_manager`, `successor_tracker`).

Relevant FRs/NFRs: FR21-FR32 (agent domain), FR18-FR20 (tool plugin), NFR02 (configurability), NFR04 (robustness), NFR08 (observability).

Binding constraints (project policy):
- MOP means "monitored operations", never "security".
- Arm-neutral naming: v13/v17 etc., never rvsmart-prefixed.
- No artificial LLM call limits.
- Arms never inherit defaults — frozen variants set all arm-defining keys explicitly, with guard pytest (aperv-tool pattern, `modules/aperv-tool/tests/test_aperv_tool.py`).
- LLM arms isolated from steering arms (LLM latency must not contaminate steering measurement).
- Emulator lifecycle always managed by rv-experiment/rv-platform; local executions only (`apks_examples/`), no GCP/scale experiments.
- `backup/` untouched (archived rvsmart-tool stays as-is).

## Architecture

The port mirrors APE-RV's `scoring` package architecture (10 files under `src/main/java/com/android/commands/monkey/ape/agent/scoring/` on branch `mop-fairtest`) onto the existing rv-agent ranking layer. The umbrella is a **single assembly point** with per-scorer enablement and a pure-arm kill-switch:

```
RVAgentConfig (agent_config.py)
      │  from_config(config)          ── single assembly point
      ▼
ScoringPipeline ──── startup audit log: [RV-ARCH] scorers=[...] flags={...}
      │  pure_mode=True → force all RV steering flags off/0, log forced keys
      ▼
ActionRanker(scorers)                 ── existing, ranking/action_ranker.py
      │  scorer.is_enabled() gate before scorer.score()
      ▼
Scorers (ranking/scorers.py):
  existing: MopScorer, WtgScorer, GradualDecayScorer, ComponentPriorityScorer,
            SystemElementFilter, SaturationScorer, VisitationPenaltyScorer,
            CoverageDensityScorer, StrengthScorer, ...
  new:      MopFrontierScorer (B), MenuGatewayScorer, FrontierScorer,
            StateMopDensityScorer (fair-test C), FormCompletionScorer (fair-test D)
      │
      ▼ reads
RankingContext (ranking/context.py)   ── extended with activity_has_mop,
                                         frontier view, pick counters
```

Around the pipeline, four supporting extensions:

1. **MOP-reach predicates** (`services/transition_manager.py`, `services/navigation_guidance.py`): read `StaticAnalysisData.components` to implement A′ (`components.activities[].reachesTarget` as a source of MOP activities → `activity_has_mop(activity)`), plus the DIALOG→host-activity re-key over `windows` + `wtg` edges (port of INV-MOP-25 semantics).
2. **Launch policy** (`strategies/rvagent_strategy/rvagent_strategy.py`): E-mín (MOP-first ordering of the activity launch queue using the A′ predicate) and the dose/denylist launcher (live-consumer denylist, configurable cadence, per-run cap).
3. **Component triggering service** (new module under `services/`): on plateau (existing `PlateauDetector` fires), trigger MOP-reaching non-activity components (services/receivers/broadcast catalog) via `am start-service`/`am broadcast` through the rv-uiautomator `DeviceInterface`; activities keep going through the normal launcher.
4. **Guards/caps as pre-ranking filters and node policy**: foreign-activity/package guards, BACK/MENU pick cap, MOP-target revisit cap, idle-timeout cap, dynamic epsilon, per-activity action budget — implemented as filters before `ActionRanker.rank()` plus policy in the LangGraph `execute`/`validation` nodes.

Observability: `metrics/exporter.py` and the per-iteration trace CSV gain a `decision_source` field with the **same taxonomy** as the aperv `.trace` (precedence MOP > WTG > Menu > Form > Coverage), enabling direct cross-tool comparison.

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `ScoringPipeline.from_config` (new, `ranking/pipeline.py`) | Single assembly of enabled scorers from config; audit log; kill-switch enforcement | `RVAgentConfig` | `ActionRanker` with gated scorers |
| `Scorer.is_enabled()` (extension, `ranking/scorers.py`) | Per-scorer gate consulted at assembly and scoring time | config flags | bool |
| `MopFrontierScorer` (new) | Additive boost when action target is MOP-reaching AND unvisited | `ItemAction`, `RankingContext` | float (`mop_frontier_weight`) |
| `StateMopDensityScorer` (new) | Boost by density of MOP-flagged widgets in target state | `ItemAction`, `RankingContext` | float |
| `FormCompletionScorer` (new) | Prefer filling empty EditTexts before submit; convergent predicate excludes submit until form converged | `ItemAction`, `RankingContext` | float (flag-gated) |
| `TransitionManager.activity_has_mop` (extension) | A′ predicate over `StaticAnalysisData.components` | activity name | bool |
| `TransitionManager` DIALOG re-key (extension) | Re-key DIALOG windows to host activity via WTG edges | `windows`, `wtg` | normalized keys |
| Component trigger service (new, `services/component_trigger.py`) | Plateau escape via `am` intents to MOP-reaching components | `PlateauDetector` signal, `StaticAnalysisData.components` | device intent dispatch |
| Launch policy (extension, `rvagent_strategy.py`) | E-mín MOP-first ordering; dose cadence/cap; denylist | activity list + A′ predicate | ordered launch queue |
| Guards/caps (new filters) | Discard foreign-package trees/actions; consecutive-pick and revisit caps; activity budget | candidate actions + counters | filtered candidates |
| `decision_source` attribution (extension, `metrics/exporter.py`) | Per-decision provenance with aperv-compatible taxonomy | ranked choice | trace CSV field |
| `RVAgentTool.get_variants` (rework, `rvagent_tool/tools/rvagent/tool.py`) | Frozen variants setting ALL arm-defining keys explicitly | — | variants dict |
| Guard pytest (new, `rvagent-tool/tests`) | Every variant sets every arm-defining key; every key has a mapping entry | variants + mapping | CI enforcement |
| Seed/teardown lifecycle (extension, `rvagent_tool`) | Deterministic seed pass-through; teardown in `finally`; static-data fail-fast | Task config | reproducible runs |

## Mapping: Spec → Implementation → Test

Invariant IDs: new agent invariants start at INV-AGT-42 (main spec currently tops at INV-AGT-41); the new `rvagent-tool` capability uses INV-RVA-NN (aperv precedent: INV-APV).

| Requirement / Invariant | Implementation | Test |
|-------------|---------------|------|
| INV-AGT-42 (single pipeline assembly + audit log) | `ranking/pipeline.py::ScoringPipeline.from_config` | `test_pipeline_assembly_logged` |
| INV-AGT-43 (pure-arm kill-switch forces all RV flags off; new flags must register) | `pipeline.py` registry + `agent_config.py::pure_mode` | `test_pure_mode_forces_all_registered_flags`, registry-completeness test |
| INV-AGT-44 (pure-arm parity: all flags off ⇒ base policy) | gated scorers return no RV boost | `test_pure_arm_parity` (golden ranking, fixed seed) |
| INV-AGT-45 (A′: `activity_has_mop` sourced from `components.activities[].reachesTarget`) | `transition_manager.py` | `test_activity_has_mop_from_components` |
| INV-AGT-46 (B: MOP-frontier boost only when target MOP-reaching AND unvisited) | `MopFrontierScorer` | `test_mop_frontier_scorer_conditions` |
| INV-AGT-47 (E-mín: MOP-first launch ordering) | `rvagent_strategy.py` launch policy | `test_launch_queue_mop_first` |
| INV-AGT-48 (component triggering only on plateau; activities excluded from trigger) | `services/component_trigger.py` | `test_trigger_on_plateau_only`, `test_activities_not_triggered` |
| INV-AGT-49 (static-data fail-fast at load) | load-time validation in strategy/tool boundary | `test_static_data_fail_fast` |
| INV-AGT-50 (DIALOG re-key to host activity) | `transition_manager.py` | `test_dialog_rekey_host_activity` |
| INV-AGT-51 (guards/caps: foreign package, pick caps, budget) | pre-ranking filters + node policy | per-guard unit tests |
| INV-AGT-52 (`decision_source` taxonomy = aperv trace, precedence MOP>WTG>Menu>Form>Coverage) | `metrics/exporter.py` + trace CSV | `test_decision_source_taxonomy` |
| INV-AGT-53 (deterministic seed reproducibility) | seeded RNG threaded through strategy | `test_seed_reproducibility` |
| INV-RVA-01..04 (variant families; all arm-defining keys explicit; mapping completeness; LLM/steering isolation) | `rvagent_tool/tools/rvagent/tool.py::get_variants` + mapping | guard pytest (aperv pattern) |
| INV-RVA-05 (teardown in `finally`) | `rvagent_tool` execute path | `test_teardown_always_runs` |
| Reactivation (CI) | `.github/workflows/ci.yml` (repo root) | CI run itself |

Exact invariant wording lives in the delta specs (`specs/agent/spec.md`, `specs/rvagent-tool/spec.md`).

## Goals / Non-Goals

**Goals:**
- rv-agent back in CI with a green offline suite; DEPRECATED status reverted in docs.
- Full concept port from APE-RV `mop-fairtest` (§5 inventory of the input report), pure_algorithm mode first.
- Honest measurability: pure arm auditable via kill-switch + parity test; `decision_source` comparable 1:1 with aperv traces; deterministic seeds.
- Variant hygiene in rvagent-tool identical to aperv-tool (explicit arms + guard tests).

**Non-Goals:**
- Any work on rvsmart Java (frozen in the reactor) or on APE-RV itself.
- Real/scale experiments — the revived rv-agent is a local-executions-only experimental arm.
- Changes to rv-android-core models or the rv-platform static-analysis pipeline (read-only consumption; `StaticAnalysisData.components` already models what is needed).
- Solving host-side latency — it is structural; APE-RV remains the in-device tool.

## Decisions

1. **Port onto the existing ranking layer, not a parallel package.** The `Scorer`/`ActionRanker`/`RankingContext` trio is already the Python analog of APE-RV's `ScoringPass`/`ScoringContext`. Adding `from_config` assembly + `is_enabled()` gates is a light refactor (P1); a new parallel pipeline would duplicate the layer and violate P3 when the old one died. Alternative considered: transliterate the Java package 1:1 — rejected, the shapes already match.
2. **Kill-switch as a registry, not a flag enumeration.** `pure_mode` forces off every flag registered as an RV steering flag, and a completeness test fails if a config field marked arm-defining is not registered. This is APE-RV's `apePureMode` design (INV-ARCH-01 in `ape-mop-fairtest/docs/20260708_arquitetura_separacao_aperv.md`) and avoids the plugin having to enumerate ~18 keys. Alternative: enumerate flags in rvagent-tool variants only — rejected; that was the exact mechanism of the aperv contamination incident (`frontierBoostWeight`/`activityTriggerEnabled` inherited silently).
3. **Taxonomy mirrored 1:1 with APE-RV.** Flag names (snake_cased), weight semantics, and `decision_source` values match the Java side so specs and analyses serve both tools; divergences must be documented in the delta specs. Cost: occasional awkward names in Python; benefit: cross-tool comparability, single mental model. Dual maintenance is a known trade-off, accepted by scope decision.
4. **pure_algorithm first, LLM last.** All steering work (pipeline, scorers, strategies, guards, fair-test, variants) lands and is validated with the LLM path untouched; the LLM block (llm_only/multimode, routing, LLM observability) is the final task group. Rationale: the pure arm is the measurement baseline and has no SGLang dependency, so every intermediate state is CI-verifiable offline.
5. **Component triggering as a host-side service via `am`.** In-device APE-RV dispatches intents directly; the host-side equivalent is `adb shell am` through the existing `DeviceInterface`. Activities are excluded from triggering (gh11 correction) — they go through the normal launcher with E-mín ordering.
6. **Calibration smoke before comparison.** `mop_frontier_weight` × `frontier_boost_weight` are additive frontier boosts; a local calibration smoke (cryptoapp) is a mandatory gate before any side-by-side with aperv.
7. **CI re-inclusion is a one-line revert with test hygiene, done first.** Reverting the exclusion from `674642a0` plus fixing the 2 obsolete tests and marking SGLang-dependent tests (`pytest.mark.skipif` on server availability) makes every subsequent task group CI-guarded from day one.

## API Design

### `ScoringPipeline.from_config(config: RVAgentConfig) -> ActionRanker`

- **Preconditions**: `config` validated (Pydantic); when `config.pure_mode` is True, all registered RV steering flags are forced off/0 before assembly and each forced key is logged.
- **Postconditions**: returns an `ActionRanker` containing only scorers whose `is_enabled(config)` is True; emits one `[RV-ARCH] scorers=[...] flags={...}` audit line; assembly happens nowhere else.
- **Errors**: unknown/unregistered arm-defining flag → `ConfigurationError` at assembly (fail-fast, no silent default).

### `Scorer.is_enabled(config: RVAgentConfig) -> bool` (ABC extension)

Default True for base-policy scorers; RV steering scorers return the value of their flag. Called at assembly; disabled scorers are not instantiated into the pipeline (no dead weights at runtime).

### `TransitionManager.activity_has_mop(activity: str) -> bool`

- **Preconditions**: `static_data.components` loaded (fail-fast happened at load).
- **Postconditions**: True iff the activity (post DIALOG re-key normalization) appears with `reachesTarget=True` in `components.activities` or via the pre-existing widget/method reachability source.

### `ComponentTriggerService.maybe_trigger(plateau: bool) -> Optional[TriggerAction]`

- **Preconditions**: plateau signal from `PlateauDetector`; component catalog from `StaticAnalysisData.components` (services/receivers only).
- **Postconditions**: at most one trigger dispatched per invocation, respecting `component_percentage` cadence; dispatch goes through `DeviceInterface` (`am start-service` / `am broadcast`); every dispatch is attributed in `decision_source`.

### `RVAgentTool.get_variants() -> dict[str, dict]`

Frozen variants (`pure_algorithm`, `llm_only`, `multimode`, plus steering arms defined during implementation) each set **all** arm-defining keys explicitly. Config layering follows the L2 pattern: defaults live in `get_variants()`, `configure()` reads the merged dict, no `os.environ` at L2.

New `RVAgentConfig` fields (Pydantic, defaults preserve current behavior — flags off/0):

```python
pure_mode: bool = False                    # kill-switch: forces all registered RV flags off
mop_frontier_weight: float = 0.0           # B (0 = disabled)
mop_activity_source_components: bool = False  # A′
trigger_mop_first: bool = False            # E-mín
component_trigger_enabled: bool = False    # §5.3 stagnation escape
component_percentage: float = 0.05
state_mop_density_enabled: bool = False    # fair-test C
form_completion_enabled: bool = False      # fair-test D
seed: Optional[int] = None                 # fair-test A
# guards/caps: foreign_activity_guard, back_menu_pick_cap, mop_target_pick_cap,
# idle_timeout_cap, dynamic_epsilon, activity_budget_enabled, ...
```

## Data Flow

1. rv-platform `StaticAnalysisComponent` populates `task.static_data` (unchanged) → rvagent-tool validates it **fail-fast** at configure time → passes `StaticAnalysisData` + merged variant config into rv-agent.
2. `RVAgentConfig` → `ScoringPipeline.from_config` → audit log → `ActionRanker` with enabled scorers.
3. Per step: UI state parsed → guards/caps filter candidates → `ActionRanker.rank(candidates, RankingContext)` → chosen action tagged with `decision_source` → executed via UIAutomator2 → `metrics/exporter.py` writes the trace row.
4. On plateau: `PlateauDetector` → `ComponentTriggerService` → `am` intent via DeviceInterface → attribution in trace.
5. Launch queue: activity list → A′ predicate → E-mín ordering + dose/denylist → normal launcher.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `ConfigurationError` | Unregistered arm-defining flag at pipeline assembly | Fail-fast, abort run | Fix config/registry; guard pytest prevents recurrence |
| Static-data invalid/missing fields | Load in rvagent-tool `configure` | Fail-fast with explicit message (no silent degraded run) | Re-run pre-processing; platform pipeline unchanged |
| `am` dispatch failure | Component trigger via DeviceInterface | Log + add component to denylist, continue exploration | Denylist prevents repeat waste |
| Foreign-package UI tree | Guard during parsing | Discard tree, escape action | Guard counters in telemetry |
| SGLang unavailable | LLM arms only | Existing degradation path; steering arms unaffected by design | Offline CI skips LLM-server tests |
| Teardown skipped on crash | Tool execute path | `finally` teardown (fair-test A) | Idempotent cleanup |

## Risks / Trade-offs

- [Additive frontier boosts interact (`mop_frontier_weight` × `frontier_boost_weight`)] → mandatory local calibration smoke before any aperv comparison.
- [Dual maintenance of MOP concepts in Java (APE-RV) and Python (rv-agent)] → 1:1 taxonomy mirroring; divergences documented in delta specs.
- [Host-side latency makes scale comparison unfair] → scope pinned to local executions; the tool's value is fast concept iteration, not benchmark participation.
- [Hybrid LLM historically underperformed pure algorithm in rvsmart (−1.65pp, p=0.003)] → pure-arm kill-switch + parity test make remeasurement honest; LLM block last keeps steering results independent.
- [Port drift from `mop-fairtest` while this change is in flight] → each task group cites the source commits (§5 of the input report); re-check the branch head at implementation start.
- [CI time growth from re-including rv-agent (~4m40s suite)] → acceptable; SGLang/emulator tests skipped offline.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit | New scorers, predicates (A′, re-key), guards/caps, kill-switch registry, seed | Mock `RankingContext`/static data fixtures (existing `tests/fixtures/static_analysis/cryptoapp/`) | ~40 |
| Unit (parity) | Pure arm degenerates to base policy with all flags off | Golden ranking on fixed fixtures + fixed seed | ~3 |
| Unit (guard) | Variants set all arm-defining keys; mapping completeness | rvagent-tool guard pytest (aperv pattern) | ~6 |
| Integration | Pipeline assembly from config; trigger service with fake DeviceInterface; trace `decision_source` | In-process, no device | ~10 |
| E2E (gate, manual) | `uv run rv-experiment run --tools rvagent:pure_algorithm --apks-dir ./apks_examples --timeouts 60` per phase; final side-by-side smoke with aperv on cryptoapp (local) | Platform-managed emulator | per phase |

CI contract: `pytest --import-mode=importlib -o "addopts="` per module, offline-green.

## Open Questions

- Which steering arms (beyond `pure_algorithm`/`llm_only`/`multimode`) get frozen as named variants in rvagent-tool at this stage — mirror aperv's arm set (`sata_mop_widget`-style, arm-neutral names) or defer until the calibration smoke? Default: define during implementation of the variants task group, after calibration.
- E-ext (exported receivers/services via `am` beyond the plateau-escape catalog) was left out of the APE-RV round — the report suggests it can join §5.3 here; confirm inclusion when implementing the trigger service.
- SGLang pin: revalidate default URL/model (`http://192.168.0.36:30000/v1`, Qwen3-VL-4B) against the version pinned by APE-RV (v0.5.6.post2) when the LLM block starts.
