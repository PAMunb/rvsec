## Why

RVSmart's LLM integration was built in gh29 as functional infrastructure, but the prompt quality, routing policy, and default configuration are insufficient for meaningful LLM contribution. In practice the LLM never runs: the `hybrid` variant points to `10.0.2.2:30000` while SGLang is on a separate machine at `192.168.0.36`, so every LLM call silently times out, the circuit breaker opens, and the agent runs as pure algorithm. Even if connectivity were fixed, the default 5% probabilistic ratio and content-free prompt would provide negligible improvement. This change brings RVSmart's LLM quality to parity with RVAgent v17 — its Python counterpart — so both tools operate at the same level of LLM-guided exploration. GitHub Issue: #33

## What Changes

- **Fix SGLang URL** — `llm_base_url` default in the `hybrid` Python variant changes from `http://10.0.2.2:30000/v1` to `http://192.168.0.36:30000/v1`; `Config.java` default is updated from hardcoded `10.0.2.2` to the same address; the spec updates to reflect that the URL is deployment-specific.
- **Add diagnostic logging** — `PromptBuilder` logs the full assembled prompt to logcat tag `RVSMART-PROMPT`; `ToolCallParser` logs raw LLM response text to `RVSMART-LLM-RESP`. Both are guarded by `BuildConfig.DEBUG` to avoid production overhead.
- **Prompt versioning** — new `PromptVersion` enum (`V13`, `V17`) in `Config.java`; new `PromptContext` value object carrying all context fields; `PromptBuilder` accepts a `PromptVersion` and a `PromptContext` and dispatches to the appropriate template. New config param `llm_prompt_version` (string, default `v13`).
- **Port RVAgent v13 prompt** — Java equivalent of the Python v13 system message: dialog detection and dismissal logic, priority ordering (MOP > navigation > untested elements), action vocabulary rules.
- **Port RVAgent v17 prompt** — Java equivalent of the Python v17 system message and user message: test-status tags (`[UNTESTED]`/`[TESTED-Nx]`/`[WELL-TESTED]`), MOP markers (`[DM]` for directly-reachable, `[M]` for transitively-reachable), per-element algorithm scores, last-5-actions history, screen info line (activity + coverage % + visit count), and MOP navigation section.
- **Rich context wiring** — `AgentLoop.tryLlmAction()` builds a `PromptContext` with data from `UICoverageTracker` (interaction counts for test-status), `StaticMap` (MOP reachability for markers), `ActionSelector.getLastScoreBreakdown()` (element scores), and a new last-5-actions ring buffer. Navigation hint is computed from `StaticMap` highest-value activity instead of passed as null.
- **ARRIVAL_FIRST routing strategy** — new fourth strategy in `RoutingManager.MultiModeStrategy`: LLM is used whenever the current screen hash differs from the previous iteration's hash (screen arrival), plus probabilistically with ratio `llm_new_screen_phase2_probability` (default 0.30) when the hash is unchanged. This replaces the conceptual intent of `NEW_SCREEN_ONLY` (which fires only on first-ever visits and never again) and covers all arrivals regardless of prior visit history.
- **In-app guard for LLM** — LLM is only invoked when `outOfAppCount == 0`. When the agent is in the out-of-app tolerance window (recovering from launcher/home), LLM calls are skipped and the algorithm handles navigation.
- **New Python tool variants** — `llm_only` (mode=llm_only, for diagnostic testing), `arrival_first_v13` (ARRIVAL_FIRST + v13 prompt), `arrival_first_v17` (ARRIVAL_FIRST + v17 prompt, llm_new_screen_phase2_probability=0.30). Default `hybrid` variant updated to ARRIVAL_FIRST + v13 as a safe starting point.
- **Default probability update** — `llm_new_screen_phase2_probability` defaults to 0.30 in the new variants. The existing `llm_probability` field is retained for `PROBABILISTIC` strategy compatibility.

## Capabilities

### New Capabilities

None. All changes are improvements to the existing `rvsmart` capability domain.

### Modified Capabilities

- `rvsmart`: Multiple requirement-level changes:
  - `llm_base_url` default value (INV-RSM network section)
  - LLM routing strategies: add `arrival_first`, update `probabilistic` default ratio
  - Prompt architecture: add versioning, rich context, v13/v17 templates
  - LLM usage guard: only invoke LLM when `outOfAppCount == 0`
  - New config parameters: `llm_prompt_version`, `llm_new_screen_phase2_probability`
  - New tool variants in `rvsmart-tool`

## Impact

**Primary modules:**
- `rvsec-android/rvsmart/` (Java) — `Config.java`, `PromptBuilder.java`, `RoutingManager.java`, `AgentLoop.java`; new `PromptContext.java`, `PromptVersion` enum; updated unit tests

**Secondary modules:**
- `modules/rvsmart-tool/` (Python) — `tool.py` variants dict, new variant entries, `llm_base_url` update

**No impact on:** rv-platform, rv-experiment, rv-agent, rv-android-core or any other module. The changes are entirely contained within the rvsmart boundary.

**PRD references:** FR21 (LLM-driven exploration), FR28 (MOP-prioritized actions), FR31 (hybrid exploration modes), NFR06 (configurability).
