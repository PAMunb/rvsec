# Implementation Plan Template

---

## Implementation Plan

### Feature: `[feature name]`
### Approach: `[selected approach]`
### Date: `[YYYY-MM-DD]`

---

## 1. Overview

### Summary

[Brief summary of what will be implemented]

### Files Overview

| Action | File | Purpose |
|--------|------|---------|
| CREATE | `new_file.py` | New component |
| MODIFY | `existing.py` | Add integration |
| CREATE | `test_new.py` | Tests |

---

## 2. Implementation Steps

### Step 1: [Component Name]

**Goal**: [What this step accomplishes]

**Files**:
- CREATE: `path/to/new_file.py`
- MODIFY: `path/to/existing.py`

**Tests**:
- `test_component_init`
- `test_component_basic`

**Dependencies**: None

**Deliverable**: [What's working when done]

---

### Step 2: [Component Name]

**Goal**: [What this step accomplishes]

**Files**:
- MODIFY: `path/to/file.py`

**Tests**:
- `test_feature_x`
- `test_feature_y`

**Dependencies**: Step 1

**Deliverable**: [What's working when done]

---

### Step 3: [Integration]

**Goal**: Connect components

**Files**:
- MODIFY: `path/to/main.py`

**Tests**:
- `test_integration`

**Dependencies**: Steps 1, 2

**Deliverable**: Feature fully working

---

## 3. Execution Order

```
Step 1 ──► Step 2 ──► Step 3
  │          │          │
  ▼          ▼          ▼
Tests     Tests     Tests
```

---

## 4. Testing Strategy

### Unit Tests

| Component | Test File | Cases |
|-----------|-----------|-------|
| Component A | `test_a.py` | 5 |
| Component B | `test_b.py` | 3 |

### Integration Tests

| Integration | Test File | Cases |
|-------------|-----------|-------|
| A + B | `test_integration.py` | 2 |

### Coverage Target

- New code: 90%+
- Modified code: 80%+

---

## 5. Rollback Strategy

### If Step Fails

1. Revert changes from current step
2. Tests should still pass (previous steps intact)
3. Analyze failure before retrying

### Full Rollback

```bash
git checkout HEAD -- path/to/files
```

---

## 6. Success Criteria

- [ ] All steps completed
- [ ] All tests pass
- [ ] Code review approved
- [ ] Acceptance criteria met
- [ ] Documentation updated (if needed)

---

## 7. Approval

**Plan Status**: PENDING / APPROVED

**User Notes**: [any modifications]
