# Dependency Analysis Report

**Target**: {{TARGET}}
**Date**: {{DATE}}
**Analyst**: Claude Code

---

## Module Dependency Graph

```
{{DEPENDENCY_TREE}}
```

---

## Dependency Matrix

| Module | Layer | Depends On | Depended By |
|--------|-------|------------|-------------|
{{#each MODULES}}
| {{name}} | {{layer}} | {{depends_on}} | {{depended_by}} |
{{/each}}

---

## Layer Analysis

```
Layer 1 (Foundation):
  {{LAYER_1}}

Layer 2 (Utilities):
  {{LAYER_2}}

Layer 3 (Analysis):
  {{LAYER_3}}

Layer 4 (Execution):
  {{LAYER_4}}

Layer 5 (Orchestration):
  {{LAYER_5}}

Layer 6 (Experiment):
  {{LAYER_6}}
```

---

## Issues Found

| Issue Type | Modules | Severity | Description |
|------------|---------|----------|-------------|
{{#each ISSUES}}
| {{type}} | {{modules}} | {{severity}} | {{description}} |
{{/each}}

### Issue Details

{{#each ISSUES}}
#### {{type}}: {{modules}}

**Severity**: {{severity}}
**Description**: {{description}}
**Impact**: {{impact}}
**Recommendation**: {{recommendation}}

---
{{/each}}

## Cross-Module Imports

| From Module | To Module | Import | File:Line |
|-------------|-----------|--------|-----------|
{{#each CROSS_IMPORTS}}
| {{from}} | {{to}} | {{import}} | {{location}} |
{{/each}}

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
