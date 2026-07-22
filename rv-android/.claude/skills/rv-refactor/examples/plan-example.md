# Plan Example

This is an example of a well-structured refactoring plan that was approved.

---

## Refactoring Plan

### Target: `modules/rv-agent/src/rv_agent/strategies/rvagent_strategy/`
### Date: 2026-01-15
### Based on Analysis: analysis-report from 2026-01-15

---

## 1. Scope

### In Scope

- [x] rvagent_strategy.py - Extract state management
- [x] rvagent_strategy.py - Extract action generation logic

### Out of Scope

- [ ] rv_agent.py (reason: depends on strategy refactoring)
- [ ] llm_client.py (reason: separate effort, lower priority)

---

## 2. Refactoring Steps

### Step 1: Create State Manager

**Target**: Extract from `rvagent_strategy.py`

**What**:
- Extract state-related methods to new `state_manager.py`
- Methods: `_update_state`, `_get_current_state`, `_reset_state`
- Keep interface unchanged

**How**:
```
Before: RVAgentStrategy handles state internally with _state dict
After:  StateManager class manages state, RVAgentStrategy delegates
```

**Dependencies**: None

**Verification**:
- [ ] Unit tests for StateManager
- [ ] Existing strategy tests pass

---

### Step 2: Create Action Generator

**Target**: Extract from `rvagent_strategy.py`

**What**:
- Extract action generation to new `action_generator.py`
- Methods: `_generate_action`, `_select_best_action`, `_filter_actions`
- Receives state from StateManager

**How**:
```
Before: RVAgentStrategy.generate_action() - 150 lines
After:  ActionGenerator.generate() - focused, testable
```

**Dependencies**: Step 1 (needs StateManager interface)

**Verification**:
- [ ] Unit tests for ActionGenerator
- [ ] Integration test with StateManager

---

### Step 3: Update RVAgentStrategy

**Target**: `rvagent_strategy.py`

**What**:
- Remove extracted code
- Add composition with StateManager and ActionGenerator
- Update __init__ to create/inject dependencies

**How**:
```python
# Before
class RVAgentStrategy:
    def __init__(self):
        self._state = {}
        # ... 800+ lines

# After
class RVAgentStrategy:
    def __init__(self, state_manager=None, action_generator=None):
        self._state_manager = state_manager or StateManager()
        self._action_generator = action_generator or ActionGenerator()
        # ... 300 lines (orchestration only)
```

**Dependencies**: Steps 1 and 2

**Verification**:
- [ ] All existing tests pass
- [ ] No functionality change

---

## 3. Execution Order

```
Step 1 (StateManager)
    │
    ▼
Step 2 (ActionGenerator)
    │
    ▼
Step 3 (Update RVAgentStrategy)
```

| Step | Depends On | Can Parallelize |
|------|------------|-----------------|
| 1 | - | No |
| 2 | 1 | No |
| 3 | 1, 2 | No |

---

## 4. Impact Assessment

### Files Modified

| File | Changes | Risk |
|------|---------|------|
| `rvagent_strategy.py` | Major restructure | MEDIUM |

### Files Created

| File | Purpose | Risk |
|------|---------|------|
| `state_manager.py` | State management | LOW |
| `action_generator.py` | Action generation | LOW |
| `tests/unit/test_state_manager.py` | Tests | LOW |
| `tests/unit/test_action_generator.py` | Tests | LOW |

### Breaking Changes

| Change | Affected Code | Migration |
|--------|---------------|-----------|
| None (interface preserved) | - | - |

---

## 5. Rollback Strategy

### Backup Locations

```
backup/
└── rvagent_strategy_20260115.py
```

### Rollback Commands

```bash
# Full rollback
cp backup/rvagent_strategy_20260115.py \
   modules/rv-agent/src/rv_agent/strategies/rvagent_strategy/rvagent_strategy.py
rm modules/rv-agent/src/rv_agent/strategies/rvagent_strategy/state_manager.py
rm modules/rv-agent/src/rv_agent/strategies/rvagent_strategy/action_generator.py
```

---

## 6. Success Criteria

- [x] All unit tests pass
- [x] All integration tests pass
- [x] No new linting errors
- [x] Code review approved
- [x] Complexity metrics improved

### Metrics Goals

| Metric | Before | Target | Actual |
|--------|--------|--------|--------|
| Lines in rvagent_strategy.py | 850 | < 400 | 320 |
| Max function length | 75 | < 50 | 35 |
| Number of files | 1 | 3 | 3 |

---

## 7. Approval

**Plan Status**: APPROVED

**User Decision**: Approved with note to ensure backwards compatibility

**Notes**: User requested keeping the original public interface intact
