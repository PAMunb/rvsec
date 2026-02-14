# Dead Code Analysis Report

**Target**: {{TARGET}}
**Date**: {{DATE}}
**Analyst**: Claude Code

---

## Summary

| Category | Count | Auto-removable |
|----------|-------|----------------|
| Unused imports | {{UNUSED_IMPORTS_COUNT}} | Yes |
| Unused functions | {{UNUSED_FUNCTIONS_COUNT}} | Review needed |
| Unused variables | {{UNUSED_VARIABLES_COUNT}} | Yes |
| Dead code blocks | {{DEAD_CODE_COUNT}} | Review needed |
| **Total** | **{{TOTAL_COUNT}}** | |

---

## Unused Imports

| File | Import | Line | Confidence |
|------|--------|------|------------|
{{#each UNUSED_IMPORTS}}
| `{{file}}` | `{{import}}` | {{line}} | {{confidence}} |
{{/each}}

---

## Unused Functions

| File | Function | Line | Reason | Confidence |
|------|----------|------|--------|------------|
{{#each UNUSED_FUNCTIONS}}
| `{{file}}` | `{{function}}` | {{line}} | {{reason}} | {{confidence}} |
{{/each}}

---

## Unused Variables

| File | Variable | Line | Confidence |
|------|----------|------|------------|
{{#each UNUSED_VARIABLES}}
| `{{file}}` | `{{variable}}` | {{line}} | {{confidence}} |
{{/each}}

---

## Dead Code Blocks

| File | Lines | Type | Description |
|------|-------|------|-------------|
{{#each DEAD_CODE_BLOCKS}}
| `{{file}}` | {{lines}} | {{type}} | {{description}} |
{{/each}}

---

## Cleanup Commands

### Auto-fix Unused Imports
```bash
cd modules/{{MODULE}}
uv run autoflake --in-place --remove-all-unused-imports src/
```

### Manual Review Required
The following items need manual review before removal:
{{#each MANUAL_REVIEW}}
- `{{file}}:{{line}}` - {{reason}}
{{/each}}

---

## Confidence Levels

| Level | Criteria | Action |
|-------|----------|--------|
| HIGH | No references found, private scope | Safe to remove |
| MEDIUM | Few references, unclear usage | Manual review |
| LOW | Public API, reflection possible | Do not auto-remove |

---

## Recommendations

{{#each RECOMMENDATIONS}}
{{@index}}. {{this}}
{{/each}}

---

## Memory Reference

{{#if PERSISTED}}
- Saved to memory as: `{{ENTITY_NAME}}`
{{else}}
- Not persisted (MCP unavailable)
{{/if}}
