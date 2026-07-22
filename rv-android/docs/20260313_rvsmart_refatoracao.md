# RVSmart Restructuring: Ideation Document

**Date**: 2026-03-13
**Status**: Ideation (input for OpenSpec workflow)
**Author**: Pedro Henrique Teixeira Costa
**GitHub Issue**: TBD (create via `opsx:new`)

---

## 1. Problem Statement

rvsmart is a Java exploration agent running via `app_process` inside the Android emulator. In the latest large-scale comparison (100 APKs, 600s, 3 reps, JCA specs — `docs/20260310_comparacao_resultados.md`), rvsmart:mvp achieved 24.04% method coverage vs APE's 28.38% (gap: -4.39pp, p<0.001). rvsmart is statistically equivalent to FastBot (23.24%, p=0.093).

After that experiment, **gh35 fixed 17 critical bugs** (commit `02066e74`, 2026-03-10), including BACK disabled (0/251K actions), ping-pong cycles (24.5% wasted), and saturation loops. These fixes have not been validated in a large-scale experiment yet. Estimated impact: +3-5pp method coverage, potentially closing the gap to APE.

The thesis objective requires rvsmart to surpass APE and FastBot in both method coverage and MOP violation count. This plan addresses the remaining gaps after gh35.

---

## 2. Current State (Verified Against Code, 2026-03-13)

### 2.1 Verified Configuration Defaults (Config.java)

| Parameter | Current Value | Notes |
|---|---|---|
| `DEFAULT_THROTTLE_MS` | **100** | Controlled by HeapMonitor dynamically |
| `DEFAULT_BACK_BASE_SCORE` | **-100.0f** | Decay: -100 per repeat (`backDecayPerRepeat`) |
| `DEFAULT_RESTART_BASE_SCORE` | **-500.0f** | |
| `DEFAULT_MAX_RETRIES_PER_CYCLE` | **3** | |
| `DEFAULT_LLM_PROBABILITY` | **0.05f** (5%) | |
| `DEFAULT_MOP_DIRECT_SCORE` | **500.0f** | |
| `DEFAULT_MOP_TRANSITIVE_SCORE` | **300.0f** | |

### 2.2 Features Already Implemented

The following were cited as missing in previous analyses but are already present in the codebase:

| Feature | Status | Location |
|---|---|---|
| **SCROLL as first-class action** | 4 directions (down/up/left/right) for `isScrollable()` items | `ActionSelector.java:606-617` |
| **SwipeRefreshLayout** | Pull-to-refresh detection | `ActionSelector.java:629-633` |
| **DrawerLayout** | Edge swipe from left | `ActionSelector.java:635-638` |
| **Context-aware text input** | 6 categories (email, password, number, phone, URL, generic) + value rotation + static analysis fallback | `InputValueGenerator.java` |
| **CycleDetector** | Period 2-4 ring-buffer detection | `recovery/CycleDetector.java` (gh35) |
| **Dual hash** | contentHash (widget content) + structHash (layout structure) | `ScreenState.java` |

### 2.3 Remaining Root Causes

#### RC-1: Throughput Bottleneck (High)

`throttle_ms = 100ms` is still too high for in-emulator execution where UIAutomator capture takes ~30ms and action injection ~5ms. Additionally, HeapMonitor can increase the throttle dynamically under memory pressure.

**Realistic gain**: 100ms → 50ms = ~2x throughput (conservative, accounts for HeapMonitor).

#### RC-2: Backtracking Still Penalized (High)

`back_base_score = -100` combined with `back_decay_per_repeat = 100` makes BACK increasingly unattractive. After 2 ineffective BACKs on the same screen, score drops to -300. gh35 fixed the BACK-disabled bug (BUG-01), but BACK is still scored too negatively to serve as an effective navigation primitive.

#### RC-3: Phase Architecture Complexity (Medium)

PhaseController + PlateauDetector + StuckDetector + CycleDetector manage overlapping concerns. The architecture works (gh35 added safeguards) but is complex for tuning. **However**, each class serves a distinct, validated purpose — simplification should preserve their mechanisms, not delete them.

#### RC-4: Scoring Lacks Principled Exploration (Medium)

6 additive scorers produce wide, hard-to-predict score ranges. The architecture is modular and testable (370+ JUnit tests), but lacks a principled exploration/exploitation balance. A UCB (Upper Confidence Bound) scorer would provide this mathematically.

#### RC-5: Dual Hash Incomplete (Medium)

`contentHash` excludes EditText values (prevents keystroke loops) and non-interactive widget text. `content-description` is never captured. The structHash uses `Objects.hash()` (32-bit, deterministic within JVM but limited collision space). Neither hash captures scroll position — scrolled views create spurious new content hashes.

---

## 3. SOTA Analysis (2024–2025)

The SOTA comparison (`docs/20260313_comparacao_tools_recentes.md`) identifies the following strategies as most impactful:

| Tool | Algorithm | Method Coverage | Key Innovation |
|---|---|---|---|
| APE | CEGAR-based dynamic abstraction refinement | 28-37% | States = action-set equivalence classes; refines dynamically |
| Fastbot2 | Probabilistic model + SARSA(n=5), persistent | 23-31% | Cross-run knowledge transfer; 5-stage hierarchical selection |
| LLMDroid | DFS + LLM on plateau only | +26% vs baseline | -70% LLM cost; LLM as escape, not navigator |
| VLM-Fuzz | DFS + budget by widget density | +9% class coverage | Allocate time proportional to interactive widget count |
| Aurora | Screen type classification (21 types) | +19.6% vs APE | Different strategies for login, settings, ads |

### Key Insights from Source Code Analysis

- **APE's backtracking is blunt**: Episode restart every 100-300 steps, not targeted BFS. rvsmart's BacktrackBfs is already more sophisticated.
- **APE's superiority comes from CEGAR state abstraction**: Dynamic naming refinement per activity, not from speed or backtracking.
- **Fastbot2 uses SARSA + persistent cross-run model**: The main advantage is knowledge transfer between runs, not per-step RL.
- **The "30% curse" is real**: All traditional black-box tools plateau at ~30% method coverage. Only tools with LLM guidance or code coverage feedback break through.
- **Throughput ≠ coverage**: Monkey achieves highest throughput (~100 evt/s) with worst coverage. Coverage correlates with algorithmic sophistication above a ~5 evt/s threshold.

---

## 4. Decisions (Resolved Open Questions)

### D1: Dual Hash → Keep and Improve

Keep contentHash + structHash (load-bearing distinction: content identity vs structural navigation). Improvements needed:
- Investigate whether `content-description` should be included in contentHash for accessibility-described widgets
- Investigate scroll-position-aware hashing to prevent spurious state distinctions from scrolled views
- Verify compatibility with Python rv-agent hash (INV-RSM-03 requirement)

### D2: LLM Scope → Periodic with Probability

LLM is invoked **only in `llm_only` and `hybrid` modes** (never in `pure_algorithm`). In hybrid mode:
- Periodic invocation based on configured probability (start at 5%)
- Always invoked the first time a screen appears (first visit = LLM decides)
- The **only** way to exit the rvsmart execution loop is via TIMEOUT (no early termination, no exceptions)

### D3: Phase Sequencing → Track A First, Then Decide

- **Track A (Quick Path)**: Calibration + UCB scorer — validate hypotheses with minimal code change
- **Track B (Full SDD, only if Track A insufficient)**: Targeted algorithmic improvements

### D4: Class Deletion Policy → P3 Strict

Classes that are genuinely superseded or unused after Track A/B: move to `backup/`, delete from source. Do NOT keep dead code. But do NOT pre-emptively delete classes that are still in use — deletion happens as a consequence of refactoring, not as a precondition.

### D5: No Persistent Model

Cross-run knowledge persistence (Fastbot2-style) is out of scope. The thesis compares single-run performance.

---

## 5. Track A: Calibration + UCB (Quick Path)

Configuration changes + one new scorer. Validates throughput and backtracking hypotheses before any restructuring.

### 5.1 Configuration Changes

| Parameter | Current | New | Rationale |
|---|---|---|---|
| `throttle_ms` | 100 | **50** | Conservative 2x gain; validates HeapMonitor behavior |
| `back_base_score` | -100 | **+50** | BACK as navigation primitive, not punishment |
| `back_decay_per_repeat` | 100 | **30** | Slower BACK penalty growth |
| `stuck_max_blocks` | 10 | **7** | Slightly more aggressive escape |

### 5.2 UCB Scorer (New)

Add `UCBScorer` to the existing scorer chain (does NOT replace other scorers):

```
UCB(state, action) = C × sqrt(ln(N_state) / N_action)

Where:
  N_state = total visits to this state
  N_action = times this action was tried in this state
  C = 150 (exploration constant, scaled to match scorer range: GradualDecay=200, MOP=500)
```

UCB provides a principled exploration bonus that naturally decays as actions are tried. C=150 is scaled so that untried actions get ~200 points (comparable to GradualDecayScorer's 200 base), decaying as actions are explored. It complements (not replaces) GradualDecayScorer — UCB handles exploration/exploitation balance while GradualDecayScorer handles per-action decay.

### 5.3 LLM Probability Adjustment

Default routing strategy is already PROBABILISTIC (no switch needed). Add first-visit-ever detection:
- 5% probability per iteration (existing `DEFAULT_LLM_PROBABILITY`, PROBABILISTIC strategy)
- 100% on first-ever visit to each unique screen (new behavior, via `visitedScreens` HashSet)
- Only in MULTIMODE (LLM_ONLY already invokes 100%)

### 5.4 Verification

```bash
# Local quick test (cryptoapp, 300s, 3 reps)
source /etc/profile
uv run rv-experiment run --tools rvsmart --apks-dir apks_examples/ --timeout 300 --repetitions 3

# Full validation on Docker machine (100 APKs, 600s, 3 reps)
# Compare against pre-gh35 baseline from docs/20260310_comparacao_resultados.md
```

**Metrics to compare**: method_cov, activity_cov, MOP_cov, violations, evt/s, BACK%, RESTART%, unique_states.

**Go/No-go for Track B**: If Track A achieves ≥28% method coverage (APE parity), Track B focuses on marginal improvements only. If <28%, Track B addresses algorithmic gaps.

---

## 6. Track B: Targeted Improvements (Full SDD, if needed)

Only if Track A does not close the gap to APE.

### 6.1 Potential Improvements (prioritized)

| # | Improvement | Source | Impact |
|---|---|---|---|
| 1 | Reduce retry budget (`max_retries_per_cycle`: 3→1, 0 on saturated screens) | gh36 analysis: 52.6% actions are retries | +80 iters/APK → +5-8pp |
| 2 | Forward navigation on saturation (navigate to nearest frontier state instead of BFS to ancestor) | gh36 analysis: BFS ancestor causes revisit cycles | +5-10pp (less revisitation) |
| 3 | Sterile screen blacklist (mark SKIP-producing hashes, never return) | gh36 analysis: 19% actions on unparseable screens | +1-2pp |
| 4 | Component budget allocation (per-Activity time) | VLM-Fuzz pattern | +5-9% activity coverage |
| 5 | Anti-tarpit detection (block repetitive patterns) | VET (FSE 2021) | Recover wasted iterations |
| 6 | Wire RewardPropagator to scorer chain | Already exists, not connected | Trajectory-level learning |
| 7 | Improve dual hash (content-description, scroll-awareness) | Hash analysis | Better state identity |
| 8 | Simplify PhaseController (merge Phase 2 into Phase 1 with coverage-gap tiebreaker) | Reduce complexity | Better tunability |

### 6.2 What NOT to Do

- Do NOT delete PhaseController, PlateauDetector, CycleDetector, StuckDetector (they serve validated purposes)
- Do NOT inline scorer classes (keep modularity + 370+ tests)
- Do NOT merge StructuralGraph into NavigationMap (different responsibilities)
- Do NOT re-implement scrolling or InputValueGenerator (already complete)
- Do NOT implement cross-run persistence (out of scope)

---

## 7. Baseline Experiment Plan

### 7.1 Pre-Existing Baseline (Pre-gh35)

From `docs/20260310_comparacao_resultados.md` (100 APKs, 600s, 3 reps):

| Metric | rvsmart:mvp | APE | FastBot |
|---|---|---|---|
| Method cov (mean) | 24.04% | **28.38%** | 23.24% |
| Activity cov (mean) | 58.14% | **64.11%** | 54.71% |
| MOP cov (mean) | 32.64% | **37.98%** | 31.48% |
| Total violations | 340 | **363** | 307 |
| BACK actions | **0** (BUG-01) | N/A | N/A |

### 7.2 Post-gh35 Baseline (Needed)

Run on Docker machine with current code (gh35 fixes included):
- Same 100 APKs, 600s, 3 reps, JCA specs
- This establishes the true baseline after 17 bug fixes
- Expected: +3-5pp method coverage from BACK fix + cycle detection + saturation fix

### 7.3 Track A Experiment

After calibration changes (Section 5):
- Same 100 APKs, 600s, 3 reps
- Compare against both pre-gh35 and post-gh35 baselines

---

## 8. Expected Impact (Realistic)

| Dimension | Pre-gh35 | Post-gh35 (est.) | Post-Track A (est.) | Basis |
|---|---|---|---|---|
| Throughput | ~5 evt/s | ~5 evt/s | ~10 evt/s | 100→50ms throttle |
| Method coverage | 24.04% | 27-29% | 30-35% | BACK fix + UCB + calibration |
| Activity coverage | 58.14% | 63-66% | 65-70% | BACK + backtrack improvements |
| MOP coverage | 32.64% | 35-38% | 38-42% | Coverage × MOP-aware scoring |
| BACK actions | 0% | >5% | >10% | BUG-01 fix + positive score |

---

## 9. Related Documents

- `docs/20260310_comparacao_resultados.md` — Large-scale experiment results (100 APKs, pre-gh35)
- `docs/20260313_comparacao_tools_recentes.md` — SOTA tool comparison (25+ tools)
- `docs/analise_claude.md` — Source-code-verified analysis (most thorough)
- `docs/analise_codex.md` — Codex analysis (verified, good on hash/abstraction gaps)
- `docs/analise_gemini.md` — Gemini analysis (UCB recommendation)
- `docs/analise_minimax.md` — Minimax analysis (anti-tarpit, persistence gaps)
- `docs/analise_qwen.md` — Qwen analysis (comprehensive structure)
- `docs/analise-rvsmart-bugs-e-problemas.md` — 15 bugs with severity ratings (pre-gh35)
- `openspec/specs/tools/spec.md` — rvsmart domain specification
- `openspec/changes/gh35-rvsmart-bugfixes/` — gh35 change artifacts (implemented, pending experimental validation)

---

*End of ideation document. Next step: run post-gh35 baseline, then `opsx:new` to create the Track A change.*
