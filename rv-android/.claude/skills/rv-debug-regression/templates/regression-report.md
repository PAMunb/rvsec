# Regression Analysis Report

**Test**: {{TEST_NAME}}
**Location**: `{{TEST_PATH}}`
**Status**: FAILING
**Date**: {{DATE}}

---

## Error Details

```
{{ERROR_MESSAGE}}
```

### Stack Trace (relevant portion)

```
{{STACK_TRACE}}
```

---

## Investigation Timeline

| Step | Commit | Date | Result | Notes |
|------|--------|------|--------|-------|
{{#each TIMELINE}}
| {{step}} | `{{commit}}` | {{date}} | {{result}} | {{notes}} |
{{/each}}

---

## Breaking Commit Found

| Field | Value |
|-------|-------|
| **Commit** | `{{BREAKING_COMMIT}}` |
| **Author** | {{BREAKING_AUTHOR}} |
| **Date** | {{BREAKING_DATE}} |
| **Message** | {{BREAKING_MESSAGE}} |

---

## What Changed

### Files Modified

{{#each CHANGED_FILES}}
- `{{this}}`
{{/each}}

### Relevant Diff

```diff
{{DIFF}}
```

---

## Root Cause Analysis

**Problem**: {{ROOT_CAUSE}}

**Why it broke**: {{WHY_BROKE}}

**Was this intentional?**: {{#if INTENTIONAL}}Yes - behavior change{{else}}No - accidental regression{{/if}}

---

## Fix Strategy

{{#if OPTION_REVERT}}
### Option 1: Revert (if change was accidental)

```bash
git revert {{BREAKING_COMMIT}}
```

**Pros**: Quick fix, restores previous behavior
**Cons**: Loses intended changes from that commit
{{/if}}

{{#if OPTION_FIX_FORWARD}}
### Option 2: Fix Forward (if behavior should be preserved)

```python
{{FIX_CODE}}
```

**Pros**: Preserves new behavior while fixing regression
**Cons**: Requires understanding original intent
{{/if}}

{{#if OPTION_UPDATE_TEST}}
### Option 3: Update Test (if new behavior is correct)

```python
{{UPDATED_TEST}}
```

**Pros**: Aligns test with intended new behavior
**Cons**: May mask actual bugs if new behavior is wrong
{{/if}}

### Recommended: Option {{RECOMMENDED_OPTION}}

**Reasoning**: {{RECOMMENDATION_REASON}}

---

## Regression Test Template

Add this test to prevent recurrence:

```python
{{REGRESSION_TEST}}
```

---

## Next Steps

1. [ ] Apply fix (Option {{RECOMMENDED_OPTION}})
2. [ ] Add regression test from template above
3. [ ] Run full test suite: `/rv-verify {{MODULE}}`
4. [ ] Verify fix in CI
5. [ ] Document in commit message that this fixes regression from `{{BREAKING_COMMIT}}`
