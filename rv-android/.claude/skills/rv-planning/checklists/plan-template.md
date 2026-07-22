# Plan Document Template

Standard template for technical implementation plans.

---

## File Location

Save plans to: `docs/plans/YYYY-MM-DD-<feature-slug>.md`

**Naming Convention**:
- Date: ISO format (2026-01-24)
- Slug: Lowercase, hyphens, descriptive
- Examples:
  - `2026-01-24-user-authentication.md`
  - `2026-01-25-refactor-payment-service.md`
  - `2026-01-26-add-export-csv.md`

---

## Template

```markdown
# Plan: [Feature/Task Name]

**Date**: YYYY-MM-DD
**Author**: Claude Code
**Status**: Draft | Under Review | Approved | In Progress | Completed

---

## Overview

[1-2 paragraphs describing what is being built and why. Include the problem being solved and the value delivered.]

---

## Requirements

### Functional Requirements

What the system must do:

- [ ] FR-1: [Requirement description]
- [ ] FR-2: [Requirement description]
- [ ] FR-3: [Requirement description]

### Non-Functional Requirements

Quality attributes:

- [ ] NFR-1: [Performance, security, reliability, etc.]
- [ ] NFR-2: [Constraint or quality requirement]

### Out of Scope

Explicitly NOT included in this plan:

- [Feature or behavior not covered]
- [Future enhancement deferred]
- [Related but separate concern]

### Assumptions

Conditions assumed to be true:

- [Assumption 1]
- [Assumption 2]

---

## Affected Files

| File | Change Type | Description |
|------|-------------|-------------|
| `path/to/file.py` | Modify | [What changes] |
| `path/to/new_file.py` | Create | [What it contains] |
| `path/to/old_file.py` | Delete | [Why removing] |

---

## Tasks

### Task 1: [Title]

**Description**: [What to do - be specific]

**Files**:
- `path/to/file.py`

**Acceptance Criteria**:
- [ ] [Observable outcome 1]
- [ ] [Observable outcome 2]

**Risk**: Low

**Depends on**: None

---

### Task 2: [Title]

**Description**: [What to do]

**Files**:
- `path/to/file.py`

**Acceptance Criteria**:
- [ ] [Observable outcome]

**Risk**: Medium - [Brief explanation of uncertainty]

**Mitigation**: [How to reduce risk]

**Depends on**: Task 1

---

### Task 3: [Title]

**Description**: [What to do]

**Files**:
- `path/to/file.py`
- `path/to/other_file.py`

**Acceptance Criteria**:
- [ ] [Observable outcome]

**Risk**: High - [Why this is risky]

**Mitigation**: [Preventive action]

**Contingency**: [If risk materializes, do this]

**Depends on**: Task 2

---

[Continue for all tasks...]

---

## Dependencies

### Task Dependency Graph

```
[Task 1] ──► [Task 2] ──► [Task 4]
                    └──► [Task 5]
[Task 3] ──────────────► [Task 5]
```

### Critical Path

The longest dependency chain determining minimum completion:

**Critical Path**: Task 1 → Task 2 → Task 4

### Parallel Opportunities

Tasks that can be executed simultaneously:

- Task 3 can run parallel to Task 1, 2
- Task 4 and Task 5 can run parallel after Task 2

---

## Risks

### Risk Summary

| ID | Risk | Level | Mitigation |
|----|------|-------|------------|
| R1 | [Description] | Low | [Action] |
| R2 | [Description] | Medium | [Action] |
| R3 | [Description] | High | [Action + Contingency] |

### High-Risk Details

#### R3: [Risk Name]

**Description**: [What might go wrong]

**Impact**: [Consequence if it happens]

**Probability**: [Low/Medium/High]

**Mitigation**:
- [Preventive action 1]
- [Preventive action 2]

**Contingency**:
- [If risk occurs, do this]
- [Fallback approach]

---

## Rollback Strategy

If implementation fails or needs to be reverted:

### Revert Steps

1. [Step to undo change 1]
2. [Step to undo change 2]
3. [Step to restore previous state]

### Verification

How to confirm rollback succeeded:

- [ ] [Check 1]
- [ ] [Check 2]
- [ ] All tests pass

### Point of No Return

[If applicable, identify point after which rollback is significantly harder]

---

## Estimation

### Task Estimates

| Task | Base | Risk | Contingency | Total |
|------|------|------|-------------|-------|
| Task 1 | 3 min | Low | +30% | 4 min |
| Task 2 | 5 min | Medium | +40% | 7 min |
| Task 3 | 8 min | High | +50% | 12 min |
| **Total** | 16 min | | | **23 min** |

### Confidence Level

**Overall Confidence**: Low | Medium | High

**Uncertainty Sources**:
- [Factor contributing to uncertainty]
- [Another factor]

---

## Testing Strategy

### Test Coverage

| Task | Test Required | Test Type |
|------|---------------|-----------|
| Task 1 | test_[name] | Unit |
| Task 2 | test_[name] | Unit |
| Task 4 | test_[name] | Integration |

### Verification Commands

```bash
# Run specific tests
pytest path/to/tests/test_file.py -v

# Run all module tests
pytest path/to/tests/ -v

# Verify no regressions
pytest --tb=short
```

---

## Approval

### Review Checklist

- [ ] Requirements are clear and complete
- [ ] All affected files identified
- [ ] Tasks are appropriately sized (2-5 min each)
- [ ] Each task has acceptance criteria
- [ ] Risks assessed and mitigations planned
- [ ] Dependencies are explicit
- [ ] Rollback strategy defined
- [ ] Estimates include contingency
- [ ] Testing strategy defined

### Sign-off

| Role | Name | Date | Status |
|------|------|------|--------|
| Author | Claude Code | YYYY-MM-DD | Draft |
| Reviewer | [Name] | | Pending |
| Approver | [Name] | | Pending |

---

## Execution Log

Track progress during implementation:

| Task | Started | Completed | Actual | Notes |
|------|---------|-----------|--------|-------|
| Task 1 | | | | |
| Task 2 | | | | |

---

## Post-Implementation

### Lessons Learned

[To be filled after completion]

- What went well:
- What was harder than expected:
- Estimation accuracy:

### Follow-up Items

[Items discovered during implementation for future work]

- [ ] [Follow-up item]
```

---

## Section Guidelines

### Overview Section

Write for someone unfamiliar with the task:
- What problem are we solving?
- Why is this valuable?
- What approach are we taking?

### Requirements Section

Be specific and testable:
- Bad: "System should be fast"
- Good: "Response time under 200ms for 95th percentile"

### Tasks Section

Follow task-breakdown guidelines:
- 2-5 minutes per task
- Single responsibility
- Clear acceptance criteria

### Dependencies Section

Use visual notation:
- `→` for hard dependency
- `~>` for soft dependency
- `∥` for parallel

### Risks Section

Include only non-trivial risks:
- Low risks: brief mention
- Medium risks: mitigation strategy
- High risks: full contingency plan

### Estimation Section

Always include:
- Base estimate
- Risk-based contingency
- Confidence level

### Rollback Section

Plan for failure:
- Steps must be executable
- Verification must be concrete
- Identify point of no return

---

## Checklist Before Submission

- [ ] File saved to correct location
- [ ] Naming follows convention
- [ ] All sections completed
- [ ] No TODO placeholders remaining
- [ ] Tasks are numbered sequentially
- [ ] Dependencies reference correct task numbers
- [ ] Estimates add up correctly
- [ ] Ready for user review
