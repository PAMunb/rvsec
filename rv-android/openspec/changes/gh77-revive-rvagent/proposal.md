# Proposal: Revive rv-agent as Local Experimental Arm

**GitHub Issue**: #77
**Date**: 2026-07-12
**Track**: Full SDD
**Input report**: `docs/20260712_investigacao_ressurreicao_rvagent.md`

## Why

rv-agent (the Python host-side Android testing tool: UIAutomator2 + LangGraph + Qwen3-VL/SGLang, modules `rv-agent` + `rvagent-tool`) has been excluded from CI and marked deprecated since 2026-05-31 (commit `674642a0`), while the MOP-guided exploration concepts it shares lineage with (via rvsmart) kept evolving only in APE-RV (the Java in-device fork, branch `mop-fairtest`, ~41 commits ahead of master). This leaves RV-Android without a host-side experimental arm to iterate MOP steering and multimodal LLM concepts quickly — in Python, with the full rv-android infrastructure — before porting them to APE-RV's Java (GitHub Issue: #77).

The 2026-07-12 investigation verified rv-agent is in good shape: 1787/1865 tests pass offline (only 2 real failures, in obsolete recovery-mode tests), the AbstractTool plugin contract and the `task.static_data` handoff with rv-platform are intact, and the gh60 MOP→Target rename is already applied. Reviving it is reactivation plus a concept port, not a rebuild.

## What Changes

Ordered by priority: everything concerning the `pure_algorithm` mode comes first; the LLM mode block comes last.

- **Reactivation**: re-include rv-agent in the per-module CI loop (`.github/workflows/ci.yml`); remove/adapt the 2 obsolete recovery-mode tests; conditionally skip SGLang-dependent tests offline; revert the DEPRECATED status in docs and CLAUDE.md.
- **ScoringPipeline architecture** (port of APE-RV's `scoring` package): single assembly point `from_config` for the scorer pipeline with a startup audit log line (pipeline composition + flags), per-scorer `is_enabled()` gating, and a **pure-arm kill-switch** (`pure_mode`, analogous to APE-RV's `apePureMode`) that forces all RV steering flags off and logs what it forced. New RV flags MUST register with the kill-switch (testable invariant). Includes a parity test: with all RV flags off, `pure_algorithm` degenerates to the documented base policy.
- **MOP-reach strategies**: A′ (`components.activities[].reachesTarget` as a source of MOP activities, exposing `activity_has_mop`), B (`MopFrontierScorer`: additive boost when a frontier target is MOP-reaching and unvisited), E-mín (MOP-first ordering of the activity launch queue). Requires reading `StaticAnalysisData.components` (field exists in the shared core model; rv-agent currently ignores it).
- **Component triggering with stagnation escape**: on plateau (existing `PlateauDetector` is the trigger), directly trigger MOP-reaching components (services/receivers/broadcasts) via `am start/startservice/broadcast` through rv-uiautomator/DeviceInterface; static-data fail-fast at load; DIALOG→host-activity re-key in the TransitionManager.
- **Exploration guards and caps**: foreign-activity/package guards, BACK/MENU consecutive-pick cap, MOP-target revisit cap, idle-timeout cap, dynamic epsilon, per-activity action budget — targeting the action waste that killed rvsmart (35% SKIP+RESTART).
- **Fair-test items (A–F port)**: deterministic seed, teardown in `finally`, `state_mop_density` scorer, convergent form-completion predicate, `decision_source` attribution per decision with the same taxonomy as the aperv `.trace` (direct comparability), typed input generation.
- **Launcher with dose/denylist**: activity launcher with live-consumer denylist, configurable cadence and per-run cap; complements E-mín.
- **Explicit variants policy in rvagent-tool**: frozen variants set ALL arm-defining keys explicitly (arms never inherit defaults); guard pytest replicating the aperv-tool pattern (every variant sets every arm-defining key; every arm-defining key has a mapping entry). LLM arms stay isolated from steering arms.
- **LLM mode block (LAST)**: reactivate/validate `llm_only` and `multimode` variants, probabilistic routing, LLM observability (screenshot-failure counters in routing telemetry), SGLang URL/model revalidation and hybrid tool-calling check. No artificial LLM call limits.

Out of scope: rvsmart Java (frozen in the reactor, zero work), real/scale experiments (revived rv-agent runs **local executions only** — host-side latency makes fair comparison at scale unviable), any change to APE-RV itself.

## Capabilities

### New Capabilities

- `rvagent-tool`: rv-platform plugin contract for the revived rvagent tool — variant families (`pure_algorithm` × `llm_only` × `multimode`), explicit arm-defining key policy with guard tests, deterministic seed and teardown lifecycle, static-data fail-fast. Mirrors the existing `aperv` capability spec pattern.

### Modified Capabilities

- `agent`: composite action ranking becomes a config-assembled ScoringPipeline with per-scorer enablement, pure-arm kill-switch and parity requirement; new scorers (MOP frontier, state MOP density, form completion); MOP-reach strategies A′/B/E-mín over `StaticAnalysisData.components`; component triggering as plateau escape; exploration guards/caps; `decision_source` telemetry; DIALOG→host-activity re-key in WTG-guided navigation.

## Impact

- **Modules changed**: `rv-agent` (ranking, strategies, services, metrics, config), `rvagent-tool` (variants, mapping, lifecycle, guard tests). CI workflow file at repo root (`.github/workflows/ci.yml`).
- **Read-only dependencies**: `rv-android-core` (`StaticAnalysisData.components` — model already supports what is needed, no core change expected), `rv-platform` (static-analysis handoff unchanged), `rv-uiautomator` (DeviceInterface used for component triggering; extension only if `am` invocation helpers are missing), `rv-tools` (registration unchanged, INV-TOOL-12 preserved).
- **FRs/NFRs**: FR21 (LangGraph workflow), FR22 (execution modes), FR25 (probabilistic routing), FR26-FR30 (exploration strategy, ranking, memory, recovery, WTG navigation), FR18-FR20 (tool plugin integration), NFR02 (configurability), NFR04 (robustness), NFR08 (observability).
- **Port source**: APE-RV branch `mop-fairtest` (working dir `ape-mop-fairtest/`), NOT master. Concept taxonomy (flag names, weights semantics, `decision_source` values) is mirrored 1:1 with APE-RV so specs and analyses serve both; divergences must be documented in design.
- **Risk**: `mop_frontier_weight` × `frontier_boost_weight` interaction (two additive frontier boosts) requires a local calibration smoke before any comparison with aperv. Historical caveat: in rvsmart the hybrid LLM mode measured worse than pure algorithm (−1.65pp, p=0.003); the pure-arm kill-switch is what makes remeasuring this honest.
