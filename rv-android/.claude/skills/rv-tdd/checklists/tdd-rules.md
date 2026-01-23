# TDD Rules Checklist

Follow these rules strictly throughout the TDD workflow.

---

## The Three Laws of TDD

1. **You may not write production code until you have written a failing test**
2. **You may not write more of a test than is sufficient to fail**
3. **You may not write more production code than is sufficient to pass the test**

---

## RED Phase Checklist

Before writing implementation:

- [ ] Test file created
- [ ] Test imports the target (even if it doesn't exist yet)
- [ ] Test clearly describes expected behavior
- [ ] Test runs and **FAILS** for the right reason
- [ ] Failure is due to missing/incomplete implementation, NOT syntax errors

### RED Phase Stop Conditions

**STOP and fix if:**
- Test fails due to import error (file doesn't exist)
- Test fails due to syntax error
- Test passes (you wrote too much implementation!)

---

## GREEN Phase Checklist

When implementing:

- [ ] Write **minimum** code to pass the current test
- [ ] Do NOT add extra features
- [ ] Do NOT optimize
- [ ] Do NOT refactor
- [ ] Run tests after each small change
- [ ] All tests pass (GREEN state achieved)

### GREEN Phase Stop Conditions

**STOP implementing when:**
- Current test passes
- Do not continue to next test until current is GREEN

---

## REFACTOR Phase Checklist

After tests pass:

- [ ] All tests still GREEN before starting
- [ ] Make ONE small change at a time
- [ ] Run tests after EACH change
- [ ] If tests fail, REVERT immediately
- [ ] Improve code quality without changing behavior:
  - [ ] Remove duplication
  - [ ] Improve naming
  - [ ] Simplify logic
  - [ ] Extract methods if needed

### REFACTOR Phase Stop Conditions

**STOP if:**
- Tests fail (revert!)
- No more obvious improvements
- About to add new functionality (that's next RED cycle)

---

## Test Quality Checklist

Each test should:

- [ ] Test ONE thing (single assertion when possible)
- [ ] Have a descriptive name explaining the scenario
- [ ] Be independent (no reliance on other tests)
- [ ] Be deterministic (same result every run)
- [ ] Be fast (< 1 second for unit tests)
- [ ] Follow Arrange-Act-Assert pattern

---

## Cycle Verification

After each RED-GREEN-REFACTOR cycle:

| Phase | Expected State | Actual | Notes |
|-------|----------------|--------|-------|
| RED | Tests fail | [ ] | Must fail for right reason |
| GREEN | Tests pass | [ ] | Minimal implementation |
| REFACTOR | Tests pass | [ ] | Code improved |

---

## Common TDD Mistakes

### Mistakes to Avoid

| Mistake | Why It's Bad | Correct Approach |
|---------|--------------|------------------|
| Writing implementation first | Defeats TDD purpose | Write test first |
| Writing too many tests at once | Loses focus | One test at a time |
| Over-implementing in GREEN | Extra untested code | Minimal to pass |
| Refactoring in RED | Can't verify correctness | Wait for GREEN |
| Skipping REFACTOR | Technical debt | Always refactor |

---

## Test Loop Limits

```
Max attempts to make a test pass: 5

If stuck after 5 attempts:
1. STOP
2. Analyze what's wrong
3. Ask user for guidance
4. Do NOT continue blindly
```

---

## Progress Tracking

Use this to track your TDD cycles:

| Cycle | Test Name | RED | GREEN | REFACTOR |
|-------|-----------|-----|-------|----------|
| 1 | test_happy_path | [ ] | [ ] | [ ] |
| 2 | test_edge_case | [ ] | [ ] | [ ] |
| 3 | test_error_case | [ ] | [ ] | [ ] |
