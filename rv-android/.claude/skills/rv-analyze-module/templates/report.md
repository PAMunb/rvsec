# Module Analysis Report

**Module**: {{MODULE_NAME}}
**Date**: {{DATE}}
**Analyst**: Claude Code

---

## Overview

| Metric | Value |
|--------|-------|
| **Location** | `modules/{{MODULE_NAME}}/` |
| **Package** | `{{PACKAGE_NAME}}` |
| **Source Files** | {{SOURCE_FILES}} |
| **Test Files** | {{TEST_FILES}} |
| **Total Lines** | {{TOTAL_LINES}} |

---

## Purpose

{{PURPOSE_DESCRIPTION}}

---

## Directory Structure

```
src/{{PACKAGE_NAME}}/
{{DIRECTORY_TREE}}
```

---

## Key Components

| Component | Purpose | Lines | Complexity |
|-----------|---------|-------|------------|
{{#each COMPONENTS}}
| `{{name}}` | {{purpose}} | {{lines}} | {{complexity}} |
{{/each}}

---

## Dependencies

### Internal (rv-android modules)

| Module | Purpose | Import Count |
|--------|---------|--------------|
{{#each INTERNAL_DEPS}}
| `{{name}}` | {{purpose}} | {{imports}} |
{{/each}}

### External (third-party)

| Package | Purpose | Version |
|---------|---------|---------|
{{#each EXTERNAL_DEPS}}
| `{{name}}` | {{purpose}} | {{version}} |
{{/each}}

---

## Dependency Graph

```
{{MODULE_NAME}}
{{DEPENDENCY_TREE}}
```

---

## Test Coverage

| Category | Files | Test Count | Coverage |
|----------|-------|------------|----------|
{{#each TEST_COVERAGE}}
| {{category}} | {{files}} | {{tests}} | {{coverage}} |
{{/each}}

### Untested Components

{{#if UNTESTED}}
{{#each UNTESTED}}
- `{{this}}`
{{/each}}
{{else}}
All components have test coverage.
{{/if}}

---

## Architecture Assessment

### Strengths
{{#each STRENGTHS}}
- {{this}}
{{/each}}

### Concerns
{{#each CONCERNS}}
- {{this}}
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
