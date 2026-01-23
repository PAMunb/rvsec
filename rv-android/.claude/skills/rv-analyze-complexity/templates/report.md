# Complexity Analysis Report

**Target**: {{TARGET}}
**Date**: {{DATE}}
**Analyst**: Claude Code

---

## Summary

- **Total files analyzed**: {{TOTAL_FILES}}
- **Files exceeding thresholds**: {{FILES_OVER_THRESHOLD}}
- **Priority refactoring targets**: {{PRIORITY_TARGETS}}

---

## Thresholds Used

| Metric | Threshold | Files Exceeding |
|--------|-----------|-----------------|
| Lines per file | > 500 | {{FILES_OVER_LINES}} |
| Function length | > 50 lines | {{FILES_OVER_FUNCTION}} |
| Classes per file | > 3 | {{FILES_OVER_CLASSES}} |
| Imports | > 20 | {{FILES_OVER_IMPORTS}} |
| Nesting depth | > 4 levels | {{FILES_OVER_NESTING}} |

---

## Files Over Threshold

| File | Lines | Functions | Classes | Imports | Issue | Priority |
|------|-------|-----------|---------|---------|-------|----------|
{{#each FILES}}
| `{{path}}` | {{lines}} | {{functions}} | {{classes}} | {{imports}} | {{issue}} | {{priority}} |
{{/each}}

---

## Detailed Analysis

{{#each PRIORITY_FILES}}
### {{priority}}: `{{path}}`

**Metrics**:
- Lines: {{lines}}
- Functions: {{functions}}
- Classes: {{classes}}
- Max function length: {{max_function_length}}
- Max nesting: {{max_nesting}}

**Issues**:
{{#each issues}}
- {{this}}
{{/each}}

**Recommended Action**: {{action}}

---
{{/each}}

## Recommendations

{{#each RECOMMENDATIONS}}
{{@index}}. **{{file}}** (Priority {{priority}})
   - Issue: {{issue}}
   - Action: {{action}}
{{/each}}

---

## Memory Reference

{{#if PERSISTED}}
- Saved to memory as: `{{ENTITY_NAME}}`
{{else}}
- Not persisted (MCP unavailable)
{{/if}}
