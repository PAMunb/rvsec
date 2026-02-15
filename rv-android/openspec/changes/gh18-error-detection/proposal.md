# Proposal: Integrate Error Detection into rv-agent

**Date**: 2026-02-15
**Author**: Pedro Henrique Teixeira Costa (with Claude Code assistance)
**GitHub Issue**: [#18](https://github.com/PAMunb/rvsec/issues/18)
**Domains**: agent (consumer), analysis (provider — no changes)

## 1. Problem Statement

rv-agent explores Android applications using DFS-based algorithmic strategies (pure_algorithm mode) or LLM-guided exploration (llm_only, multimode). During exploration, the agent encounters application errors — crashes, ANR dialogs, permission denials, network errors, validation errors — but has **no mechanism to detect or react to them**.

The consequences are:
- The agent repeats actions that consistently cause errors, wasting exploration budget
- Stuck detection is purely hash-based (same screen = stuck), missing error screens that are visually different each time
- `FailedActionScorer` exists with -9999 penalty but receives no data — it always returns 0
- `ScreenNode.record_action_failure()` exists but is never called
- Error recovery infrastructure (`StuckRecovery` with backtrack BFS) exists but is never triggered by error conditions

Meanwhile, rv-screen-parser already has a complete `ErrorDetector` (790 lines, 3 strategies: color HSV, text regex, visual patterns) that could provide this capability.

## 2. Proposed Solution

Connect the existing error detection infrastructure to create a reactive error handling loop in rv-agent:

1. **Detect**: After each action, check for error indicators on screen
2. **Record**: Call `record_action_failure()` on the current ScreenNode
3. **Penalize**: `FailedActionScorer` assigns -9999, preventing the action from being selected again
4. **Recover**: Execute BACK action to exit the error state

### Detection Approach Decision

The `ErrorDetector` in rv-screen-parser depends on OpenCV (`cv2`) and Tesseract OCR (`pytesseract`). These system packages are **not installed** in the Docker images (base, tools, rvandroid). Four alternatives were analyzed:

| Alternative | Dependencies | Detection Scope | Latency | Docker Impact |
|-------------|-------------|-----------------|---------|---------------|
| **A. Full ScreenshotAnalyzer** | OpenCV + Tesseract | Color + text + visual patterns | ~300ms/frame | Rebuild all images (+150-300MB) |
| **B. Color-only** | OpenCV only | Color patterns (red banners, etc.) | ~50ms/frame | Rebuild all images (+50MB) |
| **C. Text-based via UI hierarchy** | None | Text regex on UIAutomator dump | ~5ms | None |
| **D. Conditional** | Depends on A/B/C | Only when hash unchanged | Amortized | Depends on base |

**Recommended approach**: Start with **Alternative C** (text-based). Apply the same regex patterns from `ErrorDetector` to texts already extracted by UIAutomator dump. Zero new dependencies, ~5ms latency. Handles ~80% of cases (textual errors like "permission denied", "connection failed", "invalid format"). If insufficient, escalate to B then A.

## 3. Impact Assessment

### Modules Affected

| Module | Impact | Changes |
|--------|--------|---------|
| rv-agent | Primary | New error detection logic, integration with FailedActionScorer and StuckRecovery |
| rv-screen-parser | None | Provider of ErrorDetector — no changes needed, regex patterns extracted for reuse |

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| False positives (normal text matched as error) | Medium | Low | Tunable confidence threshold, conservative regex patterns |
| Performance overhead in hot loop | Low | Medium | Alt C is ~5ms; only runs after action execution |
| Interference with calibration campaign (gh9) | High if Alt A/B | High | Decision D7: implement after gh9. Alt C has zero Docker impact |

### Existing Infrastructure (90% ready)

- `ScreenNode.record_action_failure()` — exists, never called
- `FailedActionScorer` — scorer with -9999 penalty, but failure set always empty
- `StuckRecovery` — backtrack BFS already implemented
- `ErrorDetector` — complete in rv-screen-parser (790 lines, 3 strategies)
- Error regex patterns in `ErrorDetector._detect_text_errors()` — extractable for Alt C

### Historical Reference

The discontinued tool `rvsmart` (archived in `backup/rvsmart-tool/`) had a working ErrorDetector integration via a 6-stage pipeline: Screenshot → ScreenshotAnalyzer → ErrorDetector → ScreenshotActionComplementor → StateEnricher → LLM Prompt. However, rvsmart used error detection passively (informing the LLM) without reactive recovery or action blacklisting. rv-agent can do more because it has algorithmic infrastructure (FailedActionScorer, StuckRecovery) that rvsmart lacked.

## 4. Pre-conditions

- gh17-refactoring-cleanup completed (cleans up related TODOs in the same files)
- gh9-docker-calibration completed (Decision D7: frozen Docker image `phtcosta/rvandroid:0.8.0` during ~308h calibration campaign)
- Alternative C (text-based) is strongly preferred to avoid Docker image changes during or after calibration
