# File Analysis Report

**File**: {{FILE_PATH}}
**Date**: {{DATE}}
**Analyst**: Claude Code

---

## Overview

| Metric | Value |
|--------|-------|
| **Path** | `{{FILE_PATH}}` |
| **Module** | {{MODULE}} |
| **Lines** | {{LINES}} |
| **Classes** | {{CLASS_COUNT}} |
| **Functions** | {{FUNCTION_COUNT}} |

---

## Imports

### Standard Library
{{#each STDLIB_IMPORTS}}
- `{{this}}`
{{/each}}

### Third-Party
{{#each THIRDPARTY_IMPORTS}}
- `{{this}}`
{{/each}}

### Internal (rv-android)
{{#each INTERNAL_IMPORTS}}
- `{{this}}`
{{/each}}

---

## Structure

### Classes

| Class | Methods | Lines | Purpose |
|-------|---------|-------|---------|
{{#each CLASSES}}
| `{{name}}` | {{methods}} | {{lines}} | {{purpose}} |
{{/each}}

### Functions

| Function | Lines | Parameters | Purpose |
|----------|-------|------------|---------|
{{#each FUNCTIONS}}
| `{{name}}` | {{lines}} | {{params}} | {{purpose}} |
{{/each}}

### Constants/Globals

| Name | Type | Value |
|------|------|-------|
{{#each CONSTANTS}}
| `{{name}}` | {{type}} | {{value}} |
{{/each}}

---

## Dependencies

### Used By (files that import this)

| File | Import |
|------|--------|
{{#each USED_BY}}
| `{{file}}` | `{{import}}` |
{{/each}}

### Uses (files this imports)

| Module | What |
|--------|------|
{{#each USES}}
| `{{module}}` | {{what}} |
{{/each}}

---

## Quality Assessment

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Total lines | {{LINES}} | 500 | {{LINES_STATUS}} |
| Max function length | {{MAX_FUNCTION_LENGTH}} | 50 | {{FUNCTION_STATUS}} |
| Max nesting depth | {{MAX_NESTING}} | 4 | {{NESTING_STATUS}} |
| Import count | {{IMPORT_COUNT}} | 20 | {{IMPORT_STATUS}} |

---

## Patterns Identified

{{#each PATTERNS}}
- **{{name}}**: {{description}}
{{/each}}

---

## Code Smells

{{#if CODE_SMELLS}}
{{#each CODE_SMELLS}}
- **{{type}}** (line {{line}}): {{description}}
{{/each}}
{{else}}
No significant code smells detected.
{{/if}}

---

## Recommendations

{{#each RECOMMENDATIONS}}
{{@index}}. {{this}}
{{/each}}
