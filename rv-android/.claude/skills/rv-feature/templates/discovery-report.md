# Discovery Report Template

---

## Discovery Report

### Feature: `[feature name]`
### Date: `[YYYY-MM-DD]`

---

## 1. Requirements Understanding

### User Request

> [Original user request quoted here]

### Interpreted Goal

[What the feature actually needs to accomplish]

### User Story

As a [user type], I want [feature] so that [benefit].

### Acceptance Criteria

1. [ ] [Criterion 1 - specific, testable]
2. [ ] [Criterion 2]
3. [ ] [Criterion 3]

---

## 2. Codebase Analysis

### Target Module

- **Module**: `modules/[module-name]/`
- **Package**: `[package_name]`

### Similar Existing Features

| Feature | Location | Relevance |
|---------|----------|-----------|
| [feature] | `path/to/file.py` | Pattern to follow |

### Patterns to Follow

- [Pattern 1 from codebase]
- [Pattern 2]

### Files to Modify

| File | Change Type | Description |
|------|-------------|-------------|
| `existing.py` | MODIFY | Add new method |
| `new_file.py` | CREATE | New component |

---

## 3. Dependencies

### Internal Dependencies

| Module | Purpose |
|--------|---------|
| `rv-android-core` | Base classes |

### External Dependencies

| Package | Version | Purpose | New? |
|---------|---------|---------|------|
| `langchain` | ^0.1 | Orchestration | No |
| `new-package` | ^1.0 | New feature | Yes |

---

## 4. Constraints

### Technical Constraints

- [Constraint 1]
- [Constraint 2]

### Business Constraints

- [Constraint]

### Performance Requirements

- [Requirement]

---

## 5. Open Questions

| Question | Impact | Needs Answer Before |
|----------|--------|---------------------|
| [Question 1] | HIGH | Design phase |
| [Question 2] | MEDIUM | Implementation |

---

## 6. Initial Effort Estimate

| Phase | Complexity |
|-------|------------|
| Design | LOW / MEDIUM / HIGH |
| Implementation | LOW / MEDIUM / HIGH |
| Testing | LOW / MEDIUM / HIGH |

---

## 7. Next Steps

1. Present discovery to user
2. Proceed to design phase
3. Brainstorm approaches
