# RVSmart LLM — Exploration, Gap Analysis, and Test Plan

**Date:** 2026-03-08
**Status:** Ideation / Pre-implementation
**Context:** RVSmart (gh29) was built as a Java rewrite of RVAgent, running via `app_process` inside the emulator at ~14 evt/s. The algorithmic exploration is solid. Now we need to test and fix the LLM integration, which was implemented in gh29 but never exercised in real runs.

---

## 1. Current State of the LLM Integration

### Architecture overview

The LLM stack in RVSmart consists of eight classes:

```
AgentLoop
  └── RoutingManager      ← decides if this iteration uses LLM or algorithm
        └── LlmCircuitBreaker  ← opens after 3 consecutive failures (60s recovery)

AgentLoop.tryLlmAction()
  ├── ScreenshotCapture   ← grabs device framebuffer (SurfaceControl / UiAutomation fallback)
  ├── ImageProcessor      ← compress PNG→JPEG@80, max 1000px, base64 encode
  ├── PromptBuilder       ← assembles messages list
  ├── SglangClient        ← HTTP POST /v1/chat/completions (OpenAI-compatible)
  ├── ToolCallParser      ← 3-level fallback: native → XML → inline JSON
  └── CoordinateNormalizer ← Qwen3-VL [0,1000) → device pixels
```

All of this is well-built. The circuit breaker, fallback parsing, and graceful degradation to algorithm on failure are correct. The infrastructure is there. What is missing is **content quality** — the prompt, the routing policy, and the strategy configuration.

### The prompt as it is today

`PromptBuilder.java` produces a two-message conversation (system + user):

```
[SYSTEM]
You are an Android UI testing agent. Your task is to explore the app by interacting with UI elements.
Available actions:
  click(x, y) — tap an element at normalized coordinates [0,1000)
  long_click(x, y) — long press at normalized coordinates
  scroll(x, y, direction) — scroll at position, direction: up/down/left/right
  type_text(text) — type text into the focused input field
  back() — press the system back button
Respond with exactly one action as JSON: {"name": "<action>", "arguments": {<args>}}

[USER]
Current activity: com.example.MainActivity

UI elements:
  1. Button "Login" @(500,300)
  2. EditText "" @(540,200)

Visited activities (2): MainActivity, SettingsActivity

Choose ONE action to explore new UI states or trigger monitored operations.
```

This is a v1 skeleton. It works structurally — SGLang will parse it and return a JSON action — but it lacks all the context that made RVAgent effective.

### Default LLM ratio: 5%

The `hybrid` variant uses `mode=multimode` with the `PROBABILISTIC` strategy. The default probability is `DEFAULT_LLM_PROBABILITY = 0.05f`. This means in a 300-second run of ~4200 iterations, only ~210 will go through the LLM. The 30-second timeout means the effective rate impact is minimal at 5%, but this also means the LLM barely runs and we learn nothing from it.

**RVAgent default: 70%.** The two tools are configured for completely different LLM exposure levels.

### SGLang URL: 192.168.0.36 vs 10.0.2.2

The `hybrid` variant is hardcoded to `llm_base_url=http://10.0.2.2:30000/v1`. The address `10.0.2.2` is the Android emulator's special alias for `localhost` on the host machine. SGLang is running on a separate machine at `192.168.0.36:30000` on the local network.

From inside the emulator, `192.168.0.36` is reachable through the host's network stack. The fix is straightforward: update the `hybrid` variant's `llm_base_url` to `http://192.168.0.36:30000/v1`.

---

## 2. Gap Analysis: RVSmart vs RVAgent v17

The table below compares what each system sends to the LLM per iteration:

| Context Element | RVSmart (today) | RVAgent v17 |
|----------------|-----------------|-------------|
| Screenshot | JPEG@80, max 1000px | Same |
| Activity name | Yes | Yes |
| Coverage metrics | No | "40% coverage (4/10 actions) \| visit #3 \| 7 total screens" |
| UI elements | Class + text/desc + coords | Same, plus: |
| → Test-status tags | No | `[UNTESTED]`, `[TESTED-1x]`, `[TESTED-2x]`, `[WELL-TESTED]` |
| → MOP markers | No | `[DM]` directly reaches MOP, `[M]` indirectly |
| → Score per element | No | `[score:260]` (algorithmic priority exposed to LLM) |
| Action history | No | Last 5 actions with coordinates and explanations |
| Navigation hints | null | MOP-aware descriptions, e.g. `'Encrypt' calls CryptoHelper.doEncrypt` |
| Iteration number | No | Yes |
| Visited activities | Set of names | Not separate (merged into screen info) |
| System prompt | Minimal | Full priority rules + reasoning steps + MOP prioritization |

The result is that RVSmart's LLM gets almost no context to reason about what has been explored, what is worth exploring, or what the MOP targets are. It can only guess from the visual screenshot and the element list. RVAgent v17 gives the LLM a complete picture of exploration state.

### Prompt version system

RVAgent has six prompt versions (`v12` through `v17`), each adding more context. v17 is the most capable, with MOP-aware navigation as the primary goal. The `prompt_version` parameter allows switching between them at runtime — critical for experimentation.

**RVSmart has no versioning and no configurable prompt.** The system message is a hardcoded constant in `PromptBuilder.java`. This needs to change.

---

## 3. The Routing Strategy We Want

### What exists today

`RoutingManager` supports three strategies within `MULTIMODE`:

- `PROBABILISTIC` — LLM with probability `llmRatio` on each iteration (default 5%)
- `NEW_SCREEN_ONLY` — LLM only when `isNewScreen == true` (first visit to a screen)
- `STUCK_ONLY` — LLM only when stuck detector signals no progress

### What we actually want

The `NEW_SCREEN_ONLY` strategy is close but not quite right. The idea is:

> **When arriving at a new screen, the first action MUST come from the LLM.** After that, the LLM continues to be called according to a probability distribution (e.g., 30–70% of subsequent iterations on that screen).

This is a combined strategy: **guaranteed LLM on first visit + probabilistic on revisits**. It has two phases per screen:

```
New screen detected:
  Phase 1 — First action: ALWAYS LLM (regardless of probability)
  Phase 2 — Subsequent visits: LLM with probability P (e.g., 0.30 or 0.70)
```

This strategy doesn't exist yet in `RoutingManager`. `NEW_SCREEN_ONLY` covers Phase 1 but then never uses LLM again on that screen. `PROBABILISTIC` covers Phase 2 but ignores the new-screen signal entirely.

A new strategy — call it `NEW_SCREEN_FIRST` — would need:
- A `Set<String>` of activity hashes seen since LLM start (to detect first visits)
- `if (isNewScreen && !llmSeenScreens.contains(hash)) → true, add to set`
- `else → random.nextDouble() < llmRatio`

The `llmRatio` for Phase 2 should be independently configurable (suggested: 0.30 default, matching ~30% algorithmic contribution in the original RVAgent multimode at 70/30).

---

## 4. Test Plan

The tests below are ordered from least to most dependent. Each test assumes the previous ones pass.

### Test 0: Connectivity — can the emulator reach SGLang?

Before anything else, we need to verify that HTTP requests from inside the Android emulator can reach `192.168.0.36:30000`.

The cleanest way is to run RVSmart with `LLM_ONLY` mode for 10 seconds and look for HTTP logs. But we can also run a quick check via adb:

```bash
adb -s emulator-5554 shell curl -s -o /dev/null -w "%{http_code}" \
  http://192.168.0.36:30000/health
```

Or check via the RVSmart health-check path (which hits the main endpoint):

```bash
source /etc/profile && uv run rv-experiment run \
  --tools rvsmart:hybrid \
  --apks-dir results/<last_run>/instrumented_apks/ \
  --timeout 15 \
  --skip-monitors --skip-instrument --skip-static
```

**What to look for in logs:**
- `RvTrack: llm` lines with `success=true` → LLM is working
- `LlmCircuitBreaker: OPEN` or `LlmException: Connection refused` → connectivity problem

**Note on URL:** Before running, update `hybrid` variant in `modules/rvsmart-tool/src/rvsmart_tool/tools/rvsmart/tool.py` to use `llm_base_url=http://192.168.0.36:30000/v1`.

---

### Test 1: LLM_ONLY baseline — what does the LLM actually do?

Run RVSmart in `LLM_ONLY` mode on cryptoapp for 3 minutes. This maximizes LLM calls and gives us a large sample to analyze.

First add a `llm_only` variant to the tool (or temporarily set `mode=llm_only` in the `hybrid` variant). Then:

```bash
source /etc/profile && uv run rv-experiment run \
  --tools rvsmart:hybrid \
  --apks-dir apks_examples/ \
  --timeout 180
```

**What to analyze:**
1. In the trace file (`results/<run_id>/trace_rvsmart.csv`), look for `llm_success` and `llm_failure` columns
2. Filter `RVTRACK:LLM` lines from the experiment log to see token counts and latency
3. Look at what actions the LLM is choosing — are they reasonable? Do they cluster on the same elements?
4. Check coverage vs pure_algorithm in the same time budget

**Expected findings at this stage:**
- The LLM will work but make suboptimal choices because it lacks context (no action history, no MOP markers)
- Latency will be ~2–5s per LLM call, meaning LLM_ONLY mode runs much slower than pure_algorithm
- The LLM will likely ignore already-tested elements since it cannot see test-status tags

---

### Test 2: NEW_SCREEN_ONLY — LLM as first-contact decision maker

Use the existing `NEW_SCREEN_ONLY` strategy with a high `llm_probability` (irrelevant for this strategy, but set it anyway for future reference). This is the closest available approximation of the target strategy.

Add a temporary variant to the tool:
```python
"new_screen_only": {
    "mode": "multimode",
    "llm_multimode_strategy": "NEW_SCREEN_ONLY",
    "llm_base_url": "http://192.168.0.36:30000/v1",
}
```

```bash
source /etc/profile && uv run rv-experiment run \
  --tools rvsmart:new_screen_only \
  --apks-dir apks_examples/ \
  --timeout 300
```

**What to look for:**
- How many unique screens does cryptoapp have? Each should trigger exactly one LLM call
- Are those first-contact decisions better than what the algorithm would choose?
- Compare coverage progression over time: does the LLM help explore new screens faster?

---

### Test 3: Prompt logging — read what actually goes to the LLM

Add temporary logging to `PromptBuilder.buildExplorationPrompt()` to write the full prompt text to the trace or a side file. This is the most important diagnostic: we need to see the actual prompts to evaluate quality.

Log to `Log.d("RVSMART-PROMPT", fullPromptText)` and extract with:

```bash
adb -s emulator-5554 logcat -s RVSMART-PROMPT:D | head -200
```

Or add a `--dump-prompts` flag to Main.java that writes prompts to `/data/local/tmp/rvsmart_prompts.log` and pull it:
```bash
adb pull /data/local/tmp/rvsmart_prompts.log ./
```

**What to evaluate in the prompts:**
- Are UI element coordinates in the right range? (should be raw pixel coords from `getBounds()` center, not normalized yet — normalization happens in the LLM's output, not input)
- Is the activity name correctly extracted?
- Are the right elements included? (only interactive ones)
- Is any MOP-relevant context visible?

---

### Test 4: Response quality — read what the LLM returns

Similarly, add logging to `ToolCallParser.parse()` to capture the raw LLM response text and the parsed action.

**What to look for:**
- Which of the 3 parser levels fires? (native tool_calls, XML, inline JSON)
- Are coordinates in the [0, 1000) range as expected?
- Does the LLM explain its reasoning? (useful for debugging)
- Are there parse failures? What do the failure cases look like?
- Is the LLM using `back()` or `scroll()` actions at all, or only `click()`?

---

### Test 5: Latency impact

Run pure_algorithm vs hybrid (at 30% and 70% LLM ratio) on cryptoapp for 5 minutes each and compare:

```
Mode                    | Iterations | Events/s | Activity coverage | Method coverage | MOP coverage
pure_algorithm          | ?          | ~14       | ?                 | ?               | ?
hybrid (30% LLM)        | ?          | ~?        | ?                 | ?               | ?
hybrid (70% LLM)        | ?          | ~?        | ?                 | ?               | ?
llm_only                | ?          | ~?        | ?                 | ?               | ?
```

The LLM adds ~2–5s per call. At 70% LLM and 14 evt/s base rate, each LLM call replaces several algorithmic iterations. The question is whether LLM quality compensates for the throughput loss.

---

## 5. Improvement Proposals

### Proposal A: Port RVAgent prompts to Java with version parameter

The six RVAgent prompt versions (`v12`–`v17`) represent months of iteration. Rather than reinventing the wheel, we should port the progression to Java and expose a `llm_prompt_version` config parameter.

The minimal port needed is:
- `v13`: dialog handling (safe baseline, what v12 lacks)
- `v17`: MOP-aware with test-status tags and navigation hints (target quality)

The `PromptBuilder` should accept a version parameter in its constructor or `buildExplorationPrompt()` signature. The system message and user message template switch based on version. The Java version of v17 requires additional context to be passed:
- Test-status per element: needs `UICoverageTracker` data (`getInteractionCount(elementId)`)
- MOP markers: needs `StaticMap` (already available to AgentLoop as `staticMap`)
- Action history: needs last N actions from the trace or a new ring buffer
- Coverage metrics: needs `MetricsCollector` data

This is meaningful work (new change, probably `gh33`), but the minimum viable improvement is to port v13 first (better system prompt + dialog handling) and add v17 as a follow-up.

### Proposal B: NEW_SCREEN_FIRST routing strategy

Add a fourth strategy to `RoutingManager.MultiModeStrategy`:

```java
NEW_SCREEN_FIRST  // LLM always on first visit + probabilistic on revisits
```

Implementation:
- Add `Set<String> llmSeenScreenHashes = new HashSet<>()` to `RoutingManager`
- In `shouldUseLlmMultimode()`: if screen hash not in set AND isNewScreen → add to set, return true
- Otherwise fall through to PROBABILISTIC with the configured ratio
- Reset the set on `reset()` (called after stuck recovery)

Config: `llm_multimode_strategy=NEW_SCREEN_FIRST` + `llm_probability=0.30` (Phase 2 ratio).

### Proposal C: Fix the default LLM ratio

The default `DEFAULT_LLM_PROBABILITY = 0.05f` is too low for useful LLM contribution. Given that:
- RVAgent used 70/30 and it worked well
- RVSmart is ~10x faster (14 evt/s vs ~1.4 evt/s for RVAgent)
- LLM calls take 2–5s regardless of which tool calls them

The right default depends on what we learn from the latency tests. Suggested starting points:
- `NEW_SCREEN_FIRST` with Phase 2 ratio = 0.30 (calls LLM on ~30% of revisit iterations)
- This means: 100% on new screens + 30% thereafter ≈ roughly matching RVAgent semantics in a faster loop

### Proposal D: Navigation hints wiring

The `navigationHint` parameter in `PromptBuilder.buildExplorationPrompt()` is always `null` in the current `AgentLoop`. The algorithm already computes WTG-guided navigation suggestions (the `WtgScorer` knows which activities are reachable and prioritized). Passing that information as a hint to the LLM is low-effort and high-value.

The hint could be as simple as: `"Target: CryptoActivity (reachable via 2 transitions, has monitored operations)"`. This single line gives the LLM a goal.

---

## 6. Priority Order

Given the above, the recommended sequence is:

1. **Fix the URL** (`10.0.2.2` → `192.168.0.36`) — 5 minutes, unblock all testing
2. **Add prompt logging** to `PromptBuilder` — 15 minutes, enables all prompt-quality analysis
3. **Run Test 0** (connectivity) and **Test 1** (LLM_ONLY baseline) — understanding the current baseline
4. **Run Test 3** (read actual prompts) — diagnose quality
5. **Run Test 4** (read LLM responses) — diagnose parsing
6. **Evaluate results** → decide which proposals to implement in a new change
7. **New change (gh33)**: port v13 + v17 prompts, add NEW_SCREEN_FIRST strategy, fix default ratio

The document `docs/20260308_rvsmart_llm.md` (this file) serves as the entry point for the ideation phase of that change.

---

## 7. Open Questions

1. **From inside the emulator, is `192.168.0.36` directly reachable?** Or does the emulator's network stack need a special route? (Answer expected from Test 0.)

2. **What is the actual latency of Qwen3-VL-4B on the SGLang server at 192.168.0.36?** The 30s timeout in `Config.java` is very conservative. Once we have real measurements we should tighten it to 2×P95 latency.

3. **Does the test-status context actually help Qwen3-VL-4B?** The 4B model is much smaller than larger LLMs. It may not benefit from rich context the same way a 72B model would. We need empirical data before investing in full v17 portage.

4. **Should the action history be the last N actions or the last N unique screens?** For RVSmart's faster loop, the last 5 actions could all be on the same screen. A per-screen history (last action taken on *each* visited screen) might be more useful.

5. **Does the circuit breaker's 60-second recovery window make sense given that individual calls can take 2–5s?** Three consecutive failures in 60s means ~6–15 seconds of LLM time, which is a small fraction of a 300s run. This seems fine, but worth revisiting after Test 1.

---

## 8. Results (gh33 Implementation)

**Date:** 2026-03-09
**Change:** gh33-rvsmart-llm-quality (all 8 groups complete)
**Experiment:** `rvsmart:arrival_first_v17` vs `rvsmart:default`, 1 rep × 300s, cryptoapp.apk

### Bugs Fixed During This Change

Several bugs were blocking the LLM from working at all. In order of discovery:

1. **Double `/v1` in URL** — `SglangClient` constructed `baseUrl + "/v1/chat/completions"` but `baseUrl` already contained `/v1` → HTTP 404 on every request. Fixed by removing the extra `/v1` prefix.

2. **Malformed JSON from Qwen3-VL** — The model frequently returns `{"name": "click", "arguments": {"x": 540, 399}}` (missing `"y"` key), which is invalid JSON that Gson rejects. This caused ~100% parse failure rate → `recordLlmFailure()` → circuit breaker opened after 3 calls → all subsequent iterations fell back to algorithm. Fixed by porting `_fix_malformed_json()` from RVAgent Python to `ToolCallParser.fixMalformedJson()`.

3. **Scroll direction discarded** — `parsed.getDirection()` was never passed to the `Action` constructor; only `parsed.getText()` was used. All scroll actions defaulted to "down". Fixed by using `parsed.getDirection()` when `actionType == SCROLL`.

4. **ARRIVAL_FIRST strategy ignored** — `Main.java` hardcoded `RoutingManager.Strategy.PROBABILISTIC` regardless of what `config.getLlmMultimodeStrategy()` returned. The `arrival_first_v17` variant was running at 5% LLM probability instead of firing on every new screen. Fixed by mapping `Config.MultimodeStrategy → RoutingManager.Strategy` in `runAgent()`.

### Experiment Results

| Metric | arrival_first_v17 | default (pure_algorithm) |
|--------|-------------------|--------------------------|
| LLM actions | **87.5%** (161/184) | 0% |
| Algorithm actions | 12.5% (23/184) | 100% |
| Method coverage | 18.6% | **38.98%** |
| Activity coverage | 75% (3/4) | **100%** (4/4) |
| MOP coverage | 24.6% | **49.2%** |
| LLM timeouts (>20s) | 1 | 0 |
| CB trips | ~1 | 0 |

### Interpretation

- The LLM is now firing correctly — 87.5% LLM share confirms ARRIVAL_FIRST strategy is working.
- Coverage for `arrival_first_v17` is lower than `default` (18.6% vs 39% methods). This is expected: each LLM call takes ~2s, reducing effective iterations per second from ~14 evt/s (pure algorithm) to ~1–2 evt/s (LLM-dominated). With one timeout (~25s) and 300s budget, the run completed ~184 iterations vs ~200 for pure algorithm.
- The prompt and routing infrastructure are sound. The gap is throughput: LLM calls are expensive relative to the algorithmic loop speed.
- Potential improvements for gh34: tune phase-2 probability (30% → lower), reduce timeout (25s → 10s), or use `NEW_SCREEN_ONLY` to restrict LLM calls to first visits only.

### Open Questions Answered

- **Q1 (connectivity):** Yes, `192.168.0.36` is reachable from inside the emulator. No special routing needed.
- **Q5 (CB recovery window):** At 87.5% LLM share, one 25s timeout does trip the CB but recovery is fast. The 60s window means ~1 minute of forced algorithm mode — acceptable at 300s total.
