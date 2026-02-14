# Verification Report: {{MODULE_NAME}}

**Date**: {{DATE}}
**Module Path**: `modules/{{MODULE_NAME}}`

---

## Summary

| Check | Status | Details |
|-------|--------|---------|
| Unit Tests | {{UNIT_STATUS}} | {{UNIT_DETAILS}} |
| Integration Tests | {{INT_STATUS}} | {{INT_DETAILS}} |
| Format (black) | {{BLACK_STATUS}} | {{BLACK_DETAILS}} |
| Format (isort) | {{ISORT_STATUS}} | {{ISORT_DETAILS}} |
| Lint (flake8) | {{FLAKE8_STATUS}} | {{FLAKE8_DETAILS}} |
| Type (mypy) | {{MYPY_STATUS}} | {{MYPY_DETAILS}} |

### Overall: {{OVERALL_STATUS}}

---

## Issues Found

{{#if ISSUES}}
| # | File | Line | Issue | Severity |
|---|------|------|-------|----------|
{{#each ISSUES}}
| {{@index}} | `{{file}}` | {{line}} | {{message}} | {{severity}} |
{{/each}}
{{else}}
No issues found.
{{/if}}

---

## Quick Fix Commands

{{#if NEEDS_FORMAT_FIX}}
```bash
# Fix formatting (from project root)
poetry run black modules/{{MODULE_NAME}}/src/ && poetry run isort modules/{{MODULE_NAME}}/src/
```
{{/if}}

{{#if NEEDS_LINT_FIX}}
```bash
# Review and fix lint issues manually
# File: {{LINT_FILE}} Line: {{LINT_LINE}}
```
{{/if}}

---

## Next Steps

{{#if PASSED}}
- All checks passed
- Ready for code review or commit
{{else}}
1. Fix the issues listed above
2. Re-run `/rv-verify {{MODULE_NAME}}`
3. Proceed when all checks pass
{{/if}}
