# Agile Principles Checklist

A validation checklist ensuring TDD workflow aligns with agile and XP practices.

---

## Overview

Test-Driven Development is a core practice of Extreme Programming (XP). This checklist validates that our TDD workflow follows established agile principles.

---

## XP Testing Practices Alignment

### 1. Test-First Development

| Practice | Description | rv-tdd Phase |
|----------|-------------|--------------|
| Write tests before code | Tests define expected behavior before implementation | Phase 3 (RED) |
| Tests as specification | Tests serve as executable specification | Phase 2 (Planning) |
| Run tests constantly | Tests run after every change | All phases |

**Validation Checklist:**
- [ ] No implementation code written before tests
- [ ] Tests clearly specify expected behavior
- [ ] Tests run immediately after being written

### 2. Incremental Test Development

| Practice | Description | rv-tdd Phase |
|----------|-------------|--------------|
| One test at a time | Focus on one test, make it pass, then next | Phase 3-4 (RED-GREEN) |
| Small increments | Each test adds small increment of functionality | Phase 4 (GREEN) |
| Build up complexity | Start simple, add complexity gradually | Phase 2 (Planning) |

**Validation Checklist:**
- [ ] Tests added one at a time
- [ ] Each test focuses on one behavior
- [ ] Complexity increases gradually

### 3. Automated Testing

| Practice | Description | rv-tdd Phase |
|----------|-------------|--------------|
| Automated execution | All tests run automatically | All phases |
| Fast feedback | Test results available quickly | Phase 3-5 |
| Repeatable | Same tests, same results every time | Test quality rules |

**Validation Checklist:**
- [ ] Tests are automated (no manual verification)
- [ ] Test suite runs quickly (< 1 min for unit tests)
- [ ] Tests are deterministic

---

## XP Development Practices Alignment

### 4. Simple Design

| Practice | Description | How We Apply |
|----------|-------------|--------------|
| YAGNI | Don't implement what's not needed | GREEN phase: minimal code |
| Do the simplest thing | Simplest solution that could work | GREEN phase rules |
| Refactor to simplicity | Improve without adding complexity | REFACTOR phase |

**Validation Checklist:**
- [ ] Implementation is minimal to pass tests
- [ ] No speculative features added
- [ ] Code simplified during refactoring

### 5. Refactoring

| Practice | Description | How We Apply |
|----------|-------------|--------------|
| Continuous improvement | Improve code constantly | Phase 5 (REFACTOR) |
| Tests as safety net | Refactor only when tests pass | REFACTOR rules |
| Small steps | One change at a time | REFACTOR checklist |

**Validation Checklist:**
- [ ] Refactoring done only when GREEN
- [ ] Tests run after each refactoring step
- [ ] Reverted immediately if tests fail

### 6. Continuous Integration

| Practice | Description | How We Apply |
|----------|-------------|--------------|
| Integrate frequently | Merge work often | After each TDD cycle |
| All tests must pass | No integration with failing tests | Phase 5.5 (Verification) |
| Fast feedback | Know quickly if integration broke | rv-verify skill |

**Validation Checklist:**
- [ ] All tests pass before considering work complete
- [ ] Full verification run before integration
- [ ] Broken tests block further work

---

## Agile Manifesto Alignment

### Individuals and Interactions over Processes and Tools

| Principle | How TDD Supports |
|-----------|------------------|
| Collaboration | Tests as communication tool (shared understanding) |
| Feedback | Immediate feedback from test results |
| Trust | Tests provide confidence to make changes |

### Working Software over Comprehensive Documentation

| Principle | How TDD Supports |
|-----------|------------------|
| Executable specifications | Tests ARE the specification |
| Living documentation | Tests document current behavior |
| Verified functionality | Passing tests = working software |

### Responding to Change over Following a Plan

| Principle | How TDD Supports |
|-----------|------------------|
| Safe to change | Tests catch regressions |
| Refactoring freedom | Can improve code anytime |
| Incremental | Add functionality in small steps |

### Customer Collaboration over Contract Negotiation

| Principle | How TDD Supports |
|-----------|------------------|
| Acceptance tests | Tests verify customer requirements |
| Shared understanding | Tests clarify expectations |
| Feedback loop | Fast verification of changes |

---

## Test Types in XP Context

### Unit Tests (Developer Tests)

| Characteristic | Description |
|----------------|-------------|
| Written by | Developer during implementation |
| Purpose | Verify code works as intended |
| Scope | Single function/class |
| Speed | Very fast (< 100ms each) |

**Our coverage:** Phase 3-5 (RED-GREEN-REFACTOR)

### Acceptance Tests (Customer Tests)

| Characteristic | Description |
|----------------|-------------|
| Written by | Customer/PO with developer help |
| Purpose | Verify system meets requirements |
| Scope | User story or feature |
| Speed | Can be slower (system-level) |

**Our coverage:** Integration tests, smoke tests

### Test Pyramid

```
       ╱╲
      ╱  ╲       E2E/UI Tests (few, slow)
     ╱────╲
    ╱      ╲     Integration Tests (some, medium)
   ╱────────╲
  ╱          ╲   Unit Tests (many, fast)
 ╱────────────╲
```

TDD primarily focuses on the **base of the pyramid** (unit tests).

---

## Story-to-Test Traceability

### From User Story to Tests

```
USER STORY
    │
    ▼
ACCEPTANCE CRITERIA
    │
    ▼
TEST SCENARIOS
    │
    ▼
TEST CASES
```

### Traceability Template

```markdown
## Story: [story-id] [story-title]

### Acceptance Criteria
1. Given [context], when [action], then [result]
2. Given [context], when [action], then [result]

### Test Mapping
| Criterion | Test Type | Test Name |
|-----------|-----------|-----------|
| AC-1 | Unit | test_[function]_[scenario]_[expected] |
| AC-2 | Integration | test_[feature]_integration |

### Coverage
- Unit tests: [count]
- Integration tests: [count]
- Acceptance criteria covered: [X/Y]
```

---

## Validation Summary

Use this to validate TDD workflow follows agile principles:

### Must Have (Non-negotiable)
- [ ] Tests written before implementation (Test-First)
- [ ] RED-GREEN-REFACTOR cycle followed
- [ ] Minimal implementation in GREEN phase (YAGNI)
- [ ] Refactoring only when tests pass
- [ ] All tests pass before integration

### Should Have (Best Practice)
- [ ] Tests traceable to requirements
- [ ] Test pyramid respected (more unit, fewer E2E)
- [ ] Fast test execution
- [ ] Tests are independent and deterministic

### Nice to Have (Advanced)
- [ ] Acceptance tests for user stories
- [ ] Story-to-test traceability documented
- [ ] Mutation testing for test quality

---

## Quick Reference

```
┌─────────────────────────────────────────────────────────────────┐
│                 XP TESTING PRACTICES                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  TEST-FIRST: Write test → See it fail → Implement → Pass       │
│                                                                 │
│  INCREMENTAL: One test at a time, small steps                  │
│                                                                 │
│  AUTOMATED: No manual testing, fast feedback                   │
│                                                                 │
│  SIMPLE DESIGN: YAGNI - Only what's needed to pass             │
│                                                                 │
│  REFACTORING: Improve when GREEN, revert if RED                │
│                                                                 │
│  CONTINUOUS: Integrate often, all tests must pass              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```
