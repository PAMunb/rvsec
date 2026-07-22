# Impact Analysis Report

**Target**: {{TARGET}}
**Date**: {{DATE}}
**Analyst**: Claude Code

---

## Stage 1: Direct Dependencies

Files that directly import or use the target:

| File | Import Type | Module | Line |
|------|-------------|--------|------|
{{#each DIRECT_DEPS}}
| `{{file}}` | {{import_type}} | {{module}} | {{line}} |
{{/each}}

**Direct dependents**: {{DIRECT_COUNT}} files

---

## Stage 2: Indirect Dependencies

Transitive dependencies (2 levels deep):

```
{{TARGET}}
{{#each DEPENDENCY_TREE}}
├── {{name}} ({{level}})
{{#each children}}
│   └── {{name}} ({{level}})
{{/each}}
{{/each}}
```

**Total affected files**: {{TOTAL_AFFECTED}} ({{DIRECT_COUNT}} direct + {{INDIRECT_COUNT}} indirect)

---

## Stage 3: Test Coverage

Tests that may be affected by changes:

| Test File | Coverage Type | Relevance |
|-----------|---------------|-----------|
{{#each TESTS}}
| `{{file}}` | {{type}} | {{relevance}} |
{{/each}}

**Tests to run**: {{TEST_COUNT}} files

---

## Stage 4: Risk Assessment

| Factor | Score | Reason |
|--------|-------|--------|
| Direct dependents | +{{DIRECT_SCORE}} | {{DIRECT_COUNT}} direct dependents |
| Indirect dependents | +{{INDIRECT_SCORE}} | {{INDIRECT_COUNT}} indirect dependents |
| Test coverage | -{{TEST_SCORE}} | {{TEST_COUNT}} test files |
| Public API | {{#if IS_PUBLIC}}+5{{else}}+0{{/if}} | {{#if IS_PUBLIC}}Used by external modules{{else}}Internal only{{/if}} |
| Cross-module | {{#if CROSS_MODULE}}+3{{else}}+0{{/if}} | {{#if CROSS_MODULE}}Impacts multiple modules{{else}}Single module{{/if}} |
| **TOTAL** | **{{TOTAL_SCORE}}** | |

### Risk Level: {{RISK_LEVEL}}

---

## Recommendations

{{#if HIGH_RISK}}
### HIGH RISK - Proceed with caution

1. **Before changing**:
   - Ensure all tests pass: `/rv-verify {{MODULE}}`
   - Review all {{DIRECT_COUNT}} direct dependents
   - Consider deprecation strategy for public APIs

2. **Change strategy**:
   - Make incremental changes
   - Test after each modification
   - Consider backwards compatibility

3. **Required tests**:
   ```bash
   {{#each TEST_COMMANDS}}
   {{this}}
   {{/each}}
   ```
{{/if}}

{{#if MEDIUM_RISK}}
### MEDIUM RISK - Standard precautions

1. **Before changing**:
   - Run existing tests
   - Review direct dependents

2. **Change strategy**:
   - Make focused changes
   - Run tests after completion

3. **Suggested tests**:
   ```bash
   {{#each TEST_COMMANDS}}
   {{this}}
   {{/each}}
   ```
{{/if}}

{{#if LOW_RISK}}
### LOW RISK - Safe to proceed

1. Change is relatively isolated
2. Run standard verification after changes
3. Suggested: `/rv-verify {{MODULE}}`
{{/if}}

---

## Files Summary

**Target**: `{{TARGET}}`
**Module**: `{{MODULE}}`
**Risk**: {{RISK_LEVEL}} (score: {{TOTAL_SCORE}})
**Direct deps**: {{DIRECT_COUNT}}
**Indirect deps**: {{INDIRECT_COUNT}}
**Test files**: {{TEST_COUNT}}
