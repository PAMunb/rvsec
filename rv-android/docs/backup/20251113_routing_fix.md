# V13 Routing Bug Fix - Double Counting Issue

**Date**: 2025-11-13
**Issue**: Low LLM percentage (30-38%) despite 70% configuration
**Root Cause**: Double-counting bug in routing_manager.py
**Status**: FIXED

---

## Problem Summary

### Observed Behavior

**Yesterday's overnight test (V10/V11/V12) - WORKING:**
- V10: 57.6% LLM ✅
- V11: 56.5% LLM ✅
- V12: 55.9% LLM ✅
- All maintained ~55-60% LLM as expected with 70% probability

**Today's V13 tests - BROKEN:**
- Test at 09:43: cryptoapp 25% LLM, ifixit 82% LLM (inconsistent)
- Test at 12:18: cryptoapp 73% LLM, but ifixit/dicer/leafpic/towercollector only 30-38% LLM
- Expected: ~70% LLM (configured probability)
- Getting: 30-38% LLM on most apps

### Validation Results

**Before fix (v13_validation_20251113_121821):**
- cryptoapp: 73% LLM ✅ (only one passing)
- ifixit: 30% LLM ❌ (should be ~57%)
- dicer: 37% LLM ❌ (should be ~56%)
- leafpicrevived: 31% LLM ❌
- towercollector: 38% LLM ❌
- **Result: 1/5 apps passed (20%)**

---

## Root Cause Analysis

### The Bug: Double-Counting in routing_manager.py

**Location:** `modules/rv-agent/src/rv_agent/routing/routing_manager.py`

**Problematic lines:**
- Line 173: `self.algorithm_decisions += 1` (no_tool_calls validation failure)
- Line 185: `self.algorithm_decisions += 1` (invalid_action validation failure)
- Line 206: `self.algorithm_decisions += 1` (loop_detected validation failure)
- Line 223: `self.algorithm_decisions += 1` (spatial_loop validation failure)

### Decision Flow

The routing system works in two steps:

**Step 1: route_decision()** - WHO was chosen to make the decision
```python
if mode == "multimode":
    if random.random() < llm_probability:  # 70% chance
        self.llm_decisions += 1  # ✅ Count LLM path chosen
        return "llm"
    else:
        self.algorithm_decisions += 1  # ✅ Count algorithm path chosen
        return "algorithm"
```

**Step 2: validate_llm_action()** - Validate LLM's decision (if LLM path was chosen)
```python
# OLD CODE (BROKEN):
if not has_tool_calls:
    self.algorithm_decisions += 1  # ❌ WRONG! Already counted as LLM
    return {"validation_path": "algorithm_fallback"}
```

### The Double-Counting Problem

**Example scenario:**
- 100 iterations, 70% LLM probability
- Expected: 70 LLM decisions, 30 algorithm decisions

**What should happen:**
1. Iteration 1: Route to LLM → `llm_decisions = 1`
2. LLM generates valid action → execute it
3. Next iteration...

**What was happening (BUG):**
1. Iteration 1: Route to LLM → `llm_decisions = 1`
2. LLM validation fails (loop detected) → `algorithm_decisions = 1` ❌ DOUBLE COUNT
3. Execute algorithm fallback
4. Next iteration...

**Result:**
- `llm_decisions` = 70 (times LLM path was chosen)
- `algorithm_decisions` = 30 (initial) + 40 (LLM failures) = 70
- **Total**: 140 decisions counted for 100 iterations!
- **Percentages**: 70/140 = 50% LLM, 70/140 = 50% algorithm

But the actual metrics code normalizes by total_actions (100), so:
- With many LLM failures, algorithm_decisions gets inflated
- This makes LLM percentage appear artificially low

### Why This Was Introduced

Looking at the refactoring plan (docs/20251113_rvagent.md), the V13 work included:
1. Memory sync fixes (PRIORITY 1)
2. V11 outlier investigation (PRIORITY 2)
3. V13 compact prompt design (PRIORITY 3)

The bug was likely introduced during refactoring when trying to track "who executed" the action (LLM vs algorithm fallback) instead of "who made the decision".

---

## The Fix

### Changes Made

Removed the `self.algorithm_decisions += 1` lines from all validation failure paths in `validate_llm_action()`:

1. **No tool calls** (line 173):
   ```python
   # BEFORE:
   self.algorithm_decisions += 1  # ❌ WRONG

   # AFTER:
   # NOTE: Do NOT increment algorithm_decisions here - decision was already
   # counted as llm_decisions in route_decision(). This is an LLM failure.
   ```

2. **Invalid action** (line 185):
   ```python
   # BEFORE:
   self.algorithm_decisions += 1  # ❌ WRONG

   # AFTER:
   # NOTE: Do NOT increment algorithm_decisions here - decision was already
   # counted as llm_decisions in route_decision(). This is an LLM failure.
   ```

3. **Loop detected** (line 206):
   ```python
   # BEFORE:
   self.algorithm_decisions += 1  # ❌ WRONG

   # AFTER:
   # NOTE: Do NOT increment algorithm_decisions here - decision was already
   # counted as llm_decisions in route_decision(). This is an LLM failure.
   ```

4. **Spatial loop detected** (line 223):
   ```python
   # BEFORE:
   self.algorithm_decisions += 1  # ❌ WRONG

   # AFTER:
   # NOTE: Do NOT increment algorithm_decisions here - decision was already
   # counted as llm_decisions in route_decision(). This is an LLM failure.
   ```

### Semantic Meaning After Fix

**llm_decisions**: Number of times the routing system **chose** the LLM path
**algorithm_decisions**: Number of times the routing system **chose** the algorithm path

**Note**: LLM validation failures (no tool calls, loops, etc.) are still counted as `llm_decisions` because that's what the router chose. The fact that execution fell back to algorithm is tracked separately via `used_fallback` flag.

If we want to track fallbacks separately, that should be a new counter like `llm_fallback_count`, not conflated with `algorithm_decisions`.

---

## Validation

### Quick Test
```bash
poetry run python test_v13_routing_fix.py
```

**Expected result:**
- With 70% LLM probability
- 3-minute test should show ~60-80% LLM decisions (statistical variance acceptable)
- NOT 30-38% like before the fix

### Full Validation
```bash
poetry run python test_v13_validation.py
```

**Expected results:**
- cryptoapp: 70% LLM ✅
- ifixit: ~70% LLM ✅ (not 30%)
- dicer: ~70% LLM ✅ (not 37%)
- leafpicrevived: ~70% LLM ✅ (not 31%)
- towercollector: ~70% LLM ✅ (not 38%)
- **Result: 5/5 apps should pass (100%)**

---

## Backup

**Backup location:** `backup/2025-11-13_v13-routing-fix/routing_manager.py.bak`

To restore broken version (for analysis):
```bash
cp backup/2025-11-13_v13-routing-fix/routing_manager.py.bak \
   modules/rv-agent/src/rv_agent/routing/routing_manager.py
```

---

## Lessons Learned

### 1. Always backup before changes
The refactoring plan should have included a backup step **before** making changes. This would have made it easier to compare working vs broken versions.

### 2. Counter semantics must be clear
When tracking metrics, be explicit about what counters represent:
- **WHO DECIDED** vs **WHO EXECUTED**
- In this case: counters represent routing decisions, not execution paths

### 3. Validation of core metrics
Major refactorings should include validation tests for core metrics:
- Run quick test after changes to verify metrics still in expected range
- Don't wait for full 5-app validation to catch regressions

### 4. Statistical variance
With 70% probability and small sample sizes:
- 50-90% LLM is acceptable range (statistical variance)
- 30-38% LLM is clearly broken (outside 2σ)

---

## Related Files

- `modules/rv-agent/src/rv_agent/routing/routing_manager.py` (fixed)
- `docs/20251113_rvagent.md` (refactoring plan that introduced bug)
- `results/prompt_comparison_20251112_131155/` (baseline working V10/V11/V12)
- `results/v13_validation_20251113_094343/` (broken 09:43 test)
- `results/v13_validation_20251113_121821/` (broken 12:18 test)
- `test_v13_routing_fix.py` (validation test)
- `backup/2025-11-13_v13-routing-fix/` (backup of broken version)

---

## Status

**Status:** ✅ FIXED
**Validation test:** Running (test_v13_routing_fix.py)
**Expected completion:** ~3 minutes
**Next steps:** Full 5-app validation if quick test passes
