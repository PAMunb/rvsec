# Documentation Sync Report

**Date**: {{DATE}}
**Scope**: {{SCOPE}}

---

## Changes Detected

| Module | Files Changed | Change Types | Severity |
|--------|---------------|--------------|----------|
{{#each MODULES}}
| {{name}} | {{file_count}} | {{change_types}} | {{severity}} |
{{/each}}

**Total modules affected**: {{TOTAL_MODULES}}

---

## Actions Taken

| Module | Action | Status | Notes |
|--------|--------|--------|-------|
{{#each ACTIONS}}
| {{module}} | {{action}} | {{status}} | {{notes}} |
{{/each}}

---

## Documentation Updates

{{#each UPDATES}}
### {{module}}/CLAUDE.md

**Sections updated**:
{{#each sections}}
- {{name}}: {{change}}
{{/each}}

{{/each}}

---

## Verification

- [ ] All CLAUDE.md files up to date
- [ ] Module paths correct
- [ ] Dependencies accurate
- [ ] Entry points documented
- [ ] Test paths valid

---

## Summary

| Metric | Value |
|--------|-------|
| Modules scanned | {{SCANNED}} |
| Updates made | {{UPDATES_MADE}} |
| Skipped (no changes) | {{SKIPPED}} |
| Issues found | {{ISSUES}} |

---

## Custom Content Preserved

{{#if PRESERVED}}
The following custom sections were preserved:
{{#each PRESERVED}}
- `{{module}}/CLAUDE.md`: {{section}}
{{/each}}
{{else}}
No custom content markers found.
{{/if}}
