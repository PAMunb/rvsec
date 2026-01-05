# RVAgent Pure Algorithm - Loop Detection Fix

## Problem

RVAgent pure algorithm test was failing with `GraphRecursionError` after only 58 seconds due to infinite loop caused by interaction between RVAgent strategy and external loop detector.

### Root Cause

In `pure_algorithm` mode, the `RoutingManager` was still validating algorithm actions with the loop detector. When a loop was detected, it triggered "algorithm_fallback", which called the algorithm again → algorithm selected the same action → loop detector rejected → **infinite cycle**.

### Specific Issue

State `00c7277a`:
- RVAgent's successor tracker correctly re-enabled an action (successor at 23.5% coverage)
- Algorithm selected action `CLICK at (540, 383)`
- Loop detector detected 3 consecutive CLICKs → rejected action
- Algorithm retried → same action selected → loop detector rejected → repeat
- Eventually hit LangGraph recursion limit (25 iterations)

## Solution

**Disabled loop detection in `pure_algorithm` mode** because RVAgent has its own loop prevention mechanisms:
1. **Backtracking** when states are exhausted
2. **Successor tracking** to re-enable actions appropriately
3. **Plateau detection** (informational only)

### Implementation

Modified `routing/routing_manager.py:validate_action()`:

```python
def validate_action(
    self,
    action: Optional[Dict[str, Any]],
    recent_actions: list,
    decision_maker: str = "llm"
) -> Dict[str, Any]:
    """
    NOTE: In pure_algorithm mode, loop detection is DISABLED because
    RVAgent strategy has its own loop prevention mechanisms:
    - Backtracking when states exhausted
    - Successor tracking
    - Plateau detection
    """
    # In pure_algorithm mode, SKIP loop detection entirely
    mode = self.config.get_agent_mode()
    if mode == "pure_algorithm":
        # Only check for missing action
        if not action or not action.get("action_type"):
            return {
                "validation_path": "execute",
                "loop_detected": False,
                "used_fallback": False,
                "current_action": None
            }

        # Valid action - no loop detection in pure_algorithm mode
        return {
            "validation_path": "execute",
            "loop_detected": False,
            "used_fallback": False,
            "current_action": action
        }

    # For LLM and multimode: perform normal loop detection
    # ... (existing loop detection code)
```

## Results

### Before Fix (with loop detection)
- ❌ **Status**: GraphRecursionError after 58s
- **States Explored**: 7
- **Iterations**: 13
- **Max Depth**: 25 (hit recursion limit)
- **Error**: "Recursion limit of 25 reached without hitting a stop condition"

### After Fix (loop detection disabled)
- ✅ **Status**: Ran to timeout (181s) - as designed!
- **States Explored**: **23** (3.3x improvement)
- **Iterations**: **70** (5.4x improvement)
- **Max Depth**: **63** (2.5x improvement)
- **Loop Detection Messages**: **0** (completely bypassed)
- **Errors**: Only 2 minor swipe errors (expected)

## Verification

1. **No GraphRecursionError**: Test completed normally via timeout
2. **No loop detection interference**: 0 "Loop detected" messages in 181s test
3. **RVAgent logic working**: Successor tracking, backtracking, plateau detection all functioning
4. **Exploration improved**: 3x more states, 5x more iterations

## Files Modified

1. `modules/rv-agent/src/rv_agent/routing/routing_manager.py:validate_action()` - Added pure_algorithm mode check to skip loop detection

## Related Fixes (from previous session)

1. **Text Input Support** (`rv_screen_parser/parser/screen/visitor/model.py`):
   - Added `text_input: Optional[str]` field to ItemAction model
   - Fixed Pydantic validation error when setting text values

2. **Coordinate Validation** (`rv_agent/strategies/rvagent_strategy/rvagent_strategy.py`):
   - Updated `_is_system_action()` to use `get_execution_coordinates()`
   - Filters out actions without valid coordinates

3. **Plateau Detection** (`rv_agent/strategies/rvagent_strategy/rvagent_strategy.py`):
   - Made plateau detection **informational only** (logging)
   - Removed from termination logic
   - **Timeout is the ONLY stop condition**

## Key Architectural Insight

**RVAgent pure algorithm mode should NOT use external loop detection** because:

1. **RVAgent has its own loop prevention** via backtracking and successor tracking
2. **External loop detector interferes** with RVAgent's exploration strategy
3. **Different modes have different needs**:
   - `pure_algorithm`: Uses RVAgent's internal logic
   - `llm_only` / `multimode`: Needs external loop detection for LLM actions

This separation ensures each mode operates optimally without interference.

## Testing

Tested with CryptoApp (br.unb.cic.cryptoapp) for 180s:
- ✅ Exploration runs to timeout
- ✅ No infinite loops
- ✅ Successor tracking working
- ✅ Backtracking working
- ✅ Plateau detection informational only
- ✅ 23 states explored, 70 iterations, depth 63

## Status

**✅ FIXED** - RVAgent pure algorithm mode now works correctly without loop detection interference.
