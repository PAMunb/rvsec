## Purpose

This delta spec captures requirement-level changes to the `rvsmart` capability introduced by gh33. The rvsmart domain already has a complete base spec at `openspec/specs/rvsmart/spec.md`. This file documents only the requirements that are being added or modified; everything else in the base spec remains unchanged.

The changes address two distinct problems. First, the LLM integration was unreachable in practice because the `hybrid` variant hardcoded a URL alias (`10.0.2.2`) that points to the host's localhost — not to the SGLang server on a separate machine. Second, the prompt sent to the LLM contained so little context that the model had no basis for making informed exploration decisions: it could see UI elements but not which ones were already tested, not which ones reach monitored operations, and not what the algorithm's own scoring suggested. Together these problems meant that even when LLM calls succeeded, they provided negligible guidance.

This delta introduces prompt versioning (V13 and V17 ported from RVAgent), a richer context object, a new routing strategy (ARRIVAL_FIRST) that fires the LLM on every screen arrival rather than only on first-ever visits, a guard that prevents LLM invocation when the agent is outside the target app, and diagnostic logging to make prompt and response content observable.

## Invariants

- **INV-RSM-LLM-01**: The `llm_base_url` config parameter SHALL be set to the actual SGLang server address for the deployment environment. No default value in the spec is authoritative — the correct address is deployment-specific and must be supplied by the tool variant or experiment configuration.
- **INV-RSM-LLM-02**: LLM SHALL NOT be invoked when `outOfAppCount > 0`. Only the algorithm path may act during out-of-app recovery. This prevents wasting LLM budget on home screen / launcher screenshots.
- **INV-RSM-LLM-03**: `PromptBuilder` SHALL accept a `PromptVersion` parameter and dispatch to the corresponding template. V13 is the baseline (dialog handling, priority rules). V17 is the rich context version (test-status tags, MOP markers, element scores, action history, navigation hints). Unknown version values SHALL raise `IllegalArgumentException` at construction time.
- **INV-RSM-LLM-04**: `PromptContext` SHALL encapsulate all context fields required by any prompt version. Fields required only by V17 (interaction counts, MOP sets, element scores, recent actions, coverage metrics) SHALL be nullable — when null or empty, V17 degrades gracefully to V13-equivalent output for that section.
- **INV-RSM-LLM-05**: The ARRIVAL_FIRST strategy SHALL define "arrival" as: the current screen hash differs from the screen hash of the previous iteration. This fires on every navigation event, including returning to a previously-visited screen. The `llmSeenHashes` set used by `NEW_SCREEN_ONLY` is irrelevant to ARRIVAL_FIRST.
- **INV-RSM-LLM-06**: In ARRIVAL_FIRST mode, after the first action on a new arrival, subsequent actions on the same screen (hash unchanged) SHALL use the LLM with probability `llm_new_screen_phase2_probability` (default 0.30). The circuit breaker applies to both the arrival action and phase-2 probabilistic actions.

## MODIFIED Requirements

### Requirement: Routing Manager (LLM Hybrid)

The `RoutingManager` decides per iteration whether to use the algorithm path or the LLM path. It operates within three top-level modes: `pure_algorithm` (LLM never called), `llm_only` (LLM always attempted, subject to circuit breaker), and `multimode` (LLM/algorithm blend via strategy). The in-app guard applies in all modes: when `outOfAppCount > 0`, the routing manager SHALL return false regardless of mode or strategy (INV-RSM-LLM-02).

Four strategies are supported within `multimode`:

- `probabilistic`: Random threshold against `llm_probability`. The `llm_probability` default is 0.05 (retained for backward compatibility with calibration infrastructure) but SHALL NOT be used as the default in new tool variants — new variants use `arrival_first` instead.
- `new_screen_only`: LLM only on first-ever visit to a screen (`visitCount == 1` at the time of the check). Retained for backward compatibility and experimentation.
- `stuck_only`: LLM only when `StuckDetector` fires. Retained for targeted recovery experiments.
- `arrival_first` (new): LLM on every screen arrival (hash changed from previous iteration) AND probabilistically with ratio `llm_new_screen_phase2_probability` (default 0.30) when hash is unchanged. See INV-RSM-LLM-05 and INV-RSM-LLM-06.

New config parameters:
- `llm_multimode_strategy: String` — active multimode strategy. Values: `probabilistic`, `new_screen_only`, `stuck_only`, `arrival_first`. Default: `probabilistic` (Java Config.java default; overridden to `arrival_first` in new Python variants).
- `llm_new_screen_phase2_probability: float` — phase-2 LLM probability for `arrival_first` strategy. Default 0.30. Has no effect in other strategies.

#### Scenario: ARRIVAL_FIRST fires on screen change
- **WHEN** mode is `multimode`, strategy is `arrival_first`, current screen hash differs from previous iteration's hash
- **THEN** `shouldUseLlm()` SHALL return true (subject to circuit breaker)
- **AND** the new hash is recorded as the current screen hash for comparison in the next iteration

#### Scenario: ARRIVAL_FIRST uses phase-2 probability on same screen
- **WHEN** mode is `multimode`, strategy is `arrival_first`, current screen hash equals previous iteration's hash, `llm_new_screen_phase2_probability` is 0.30
- **THEN** `shouldUseLlm()` SHALL return true with probability 0.30 and false with probability 0.70

#### Scenario: LLM skipped when out of app
- **WHEN** `outOfAppCount > 0` (agent is in out-of-app tolerance window), mode is `multimode` or `llm_only`
- **THEN** `shouldUseLlm()` SHALL return false regardless of strategy or circuit breaker state
- **AND** the iteration uses the algorithm path

#### Scenario: Probabilistic routing in multimode (unchanged)
- **WHEN** mode is `multimode`, strategy is `probabilistic`, `llm_probability` is 0.05
- **THEN** approximately 5% of iterations SHALL use the LLM path

### Requirement: Prompt Builder

`PromptBuilder` assembles the messages list for LLM exploration requests. It now accepts a `PromptVersion` (V13 or V17) and a `PromptContext` object, and dispatches to the appropriate template.

**V13 template** is a direct port of RVAgent's v13 Python prompt. The system message instructs the model to check for blocking dialogs before any other action (permission dialogs, error dialogs, modal popups), describes interaction priority (MOP targets > navigation to new screens > untested elements), and lists available actions. The user message includes: screenshot image, current activity, numbered UI elements (class + text/desc + coordinates), navigation hint if non-null, iteration number.

**V17 template** extends V13 with rich context. Each UI element is annotated with:
- Test-status tag: `[UNTESTED]` (0 interactions), `[TESTED-Nx]` (N interactions, N < 5), `[WELL-TESTED]` (5+ interactions)
- MOP marker: `[DM]` if the element's activity directly reaches a monitored operation per StaticMap; `[M]` if transitively reachable
- Algorithm score: `[score:N]` reflecting the composite scorer value for that element

The V17 user message additionally includes: last 5 actions (type + coordinates + simple explanation), screen info line (`SCREEN: ActivityName | X% coverage (K/N actions) | visit #V`), and a `MOP NAVIGATION:` section when the navigation hint describes MOP-relevant targets.

When V17 context fields are absent (null StaticMap, empty interaction counts, no recent actions), those sections are omitted without error — the output degrades to V13-equivalent for the missing sections (INV-RSM-LLM-04).

Diagnostic logging: when enabled, the full assembled prompt text is written to logcat tag `RVSMART-PROMPT` at DEBUG level. Raw LLM response text from `ToolCallParser` is written to logcat tag `RVSMART-LLM-RESP` at DEBUG level.

#### Scenario: V13 prompt structure
- **WHEN** `PromptVersion.V13`, activity is `com.example.MainActivity`, 3 interactive elements, no navigation hint
- **THEN** system message SHALL contain dialog handling instructions and priority rules
- **AND** user message SHALL contain numbered element list with class, text, and coordinates
- **AND** user message SHALL NOT contain test-status tags, MOP markers, or score annotations

#### Scenario: V17 enriches elements with test-status and MOP markers
- **WHEN** `PromptVersion.V17`, element A has 0 interactions (untested), element B has 2 interactions, element B's activity directly reaches a MOP per StaticMap
- **THEN** element A SHALL be formatted as `[UNTESTED] Button "Submit" at position (500, 416) [score:260]`
- **AND** element B SHALL be formatted as `[TESTED-2x] Button "Encrypt" at position (500, 600) [score:460] [DM]`

#### Scenario: V17 includes action history
- **WHEN** `PromptVersion.V17`, ring buffer contains last 3 actions
- **THEN** user message SHALL contain a `Recent actions (3):` section listing each action's type, coordinates, and activity
- **AND** the section SHALL appear before the MOP NAVIGATION section

#### Scenario: V17 graceful degradation when context absent
- **WHEN** `PromptVersion.V17`, StaticMap is null, interaction counts are empty
- **THEN** elements SHALL be formatted without MOP markers and without test-status tags
- **AND** no exception SHALL be thrown
- **AND** output SHALL match V13 format for those elements

#### Scenario: Diagnostic prompt logging
- **WHEN** debug logging is enabled, an LLM call is made with V13 or V17
- **THEN** the full assembled prompt SHALL be written to logcat tag `RVSMART-PROMPT` at DEBUG level before the HTTP call

### Requirement: Tool Variants (rvsmart-tool)

The Python `RVSmartTool` variant registry SHALL include the following variants after this change:

- `default` (pure_algorithm, throttle_ms=50) — unchanged
- `fast` (pure_algorithm, throttle_ms=30) — unchanged
- `llm_only` (mode=llm_only, llm_base_url=http://192.168.0.36:30000/v1) — new; for diagnostic testing with maximum LLM exposure
- `arrival_first_v13` (mode=multimode, llm_multimode_strategy=arrival_first, llm_prompt_version=v13, llm_new_screen_phase2_probability=0.30, llm_base_url=http://192.168.0.36:30000/v1) — new; default recommendation for LLM-enabled runs
- `arrival_first_v17` (mode=multimode, llm_multimode_strategy=arrival_first, llm_prompt_version=v17, llm_new_screen_phase2_probability=0.30, llm_base_url=http://192.168.0.36:30000/v1) — new; full rich-context variant

The previous `hybrid` variant SHALL be removed (P3: no backward-compatibility aliases). Its configuration is superseded by `arrival_first_v13`.

#### Scenario: arrival_first_v17 passes correct config to Java
- **WHEN** variant `arrival_first_v17` is configured
- **THEN** the properties file pushed to the device SHALL contain `mode=multimode`, `llm_multimode_strategy=arrival_first`, `llm_prompt_version=v17`, `llm_new_screen_phase2_probability=0.30`, and `llm_base_url=http://192.168.0.36:30000/v1`

#### Scenario: llm_only variant for diagnostics
- **WHEN** variant `llm_only` is used and SGLang is reachable at `192.168.0.36:30000`
- **THEN** every iteration (except out-of-app) SHALL attempt an LLM call
- **AND** the trace SHALL show `llm_actions` close to `total_actions` in the metrics report
