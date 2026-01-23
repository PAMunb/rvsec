---
name: rv-impact-analyzer
description: >-
  Analyze change impact before refactoring. Use to assess risk and identify affected code paths.
  Do NOT use for: making changes (use /rv-refactor), dependency analysis only (use /rv-analyze-dependencies).
argument-hint: [file-path or module-name]
context: fork
agent: general-purpose
allowed-tools: Grep, Glob, Read, Bash
---

# Impact Analysis: $ARGUMENTS

Analyze the ripple effects of changing a file, class, or function before refactoring.

## Supporting Files

- **Templates**: `templates/impact-report.md` - Report output format

---

## Workflow

```
STAGE 1: DIRECT DEPENDENCIES ────────────────────────────────────►
    │  Who imports this file/module?
    ▼
STAGE 2: INDIRECT DEPENDENCIES ──────────────────────────────────►
    │  2 levels of transitive dependencies
    ▼
STAGE 3: TEST COVERAGE MAPPING ──────────────────────────────────►
    │  Which tests exercise this code?
    ▼
STAGE 4: RISK ASSESSMENT ────────────────────────────────────────►
    │  HIGH / MEDIUM / LOW
    ▼
REPORT ──────────────────────────────────────────────────────────►
```

---

## Stages

### Stage 1: Direct Dependencies

Find all files that directly import or use the target.

```bash
# For a file
TARGET="llm_client"
grep -r "from.*import.*$TARGET" modules/*/src/ --include="*.py"
grep -r "import.*$TARGET" modules/*/src/ --include="*.py"

# For a class/function
grep -r "class $TARGET" modules/*/src/ --include="*.py"
grep -r "$TARGET(" modules/*/src/ --include="*.py"
```

**Output**: List of directly dependent files

### Stage 2: Indirect Dependencies (2 levels)

For each direct dependent, find THEIR dependents.

```
Target: llm_client.py
    │
    ├── DIRECT: llm_node.py imports llm_client
    │   │
    │   └── INDIRECT: rv_agent.py imports llm_node
    │
    └── DIRECT: action_generator.py imports llm_client
        │
        └── INDIRECT: strategy.py imports action_generator
```

**Limit**: 2 levels deep (to avoid explosion)

### Stage 3: Test Coverage Mapping

Find tests that might be affected:

```bash
# Tests that import target
grep -r "$TARGET" modules/*/tests/ --include="*.py"

# Tests in same module
MODULE=$(dirname $TARGET | sed 's/src/tests/')
ls $MODULE/

# Tests that test related functionality
grep -r "test_${TARGET}" modules/*/tests/ --include="*.py"
```

**Output**: List of test files that should be run

### Stage 4: Risk Assessment

Calculate risk based on:

| Factor | Weight | Criteria |
|--------|--------|----------|
| Direct dependents | 3x | Each file importing target |
| Indirect dependents | 1x | Transitive dependencies |
| Test coverage | -1x | Tests reduce risk |
| Public API | +5 | If target is public API |
| Cross-module | +3 | If impacts multiple modules |

**Risk Levels**:
- **HIGH** (score > 10): Requires careful planning, incremental changes
- **MEDIUM** (score 5-10): Proceed with caution, run extended tests
- **LOW** (score < 5): Safe to proceed with normal workflow

---

## Output Format

```markdown
## Impact Analysis Report

### Target: [file/class/function]

### Stage 1: Direct Dependencies
| File | Import Type | Module |
|------|-------------|--------|
| llm_node.py | from...import | rv-agent |
| action_service.py | import | rv-agent |

**Direct dependents**: X files

### Stage 2: Indirect Dependencies
```
Target
├── llm_node.py (DIRECT)
│   ├── rv_agent.py (INDIRECT)
│   └── decision_node.py (INDIRECT)
└── action_service.py (DIRECT)
    └── strategy.py (INDIRECT)
```

**Total affected files**: Y files (X direct + Z indirect)

### Stage 3: Test Coverage
| Test File | Coverage Type |
|-----------|---------------|
| test_llm_client.py | Unit test |
| test_llm_node.py | Integration |

**Tests to run**: Z test files

### Stage 4: Risk Assessment

| Factor | Score | Reason |
|--------|-------|--------|
| Direct deps | +6 | 2 direct dependents |
| Indirect deps | +4 | 4 indirect dependents |
| Test coverage | -3 | 3 test files |
| Public API | +5 | Used by external modules |
| **TOTAL** | **12** | |

### Risk Level: HIGH

### Recommendations

1. **Before changing**:
   - Ensure all tests pass
   - Review indirect dependencies
   - Consider deprecation strategy

2. **Change strategy**:
   - Make incremental changes
   - Test after each step
   - Consider backwards compatibility

3. **Tests to run**:
   ```bash
   poetry run pytest tests/unit/test_llm_client.py -v
   poetry run pytest tests/integration/test_llm_node.py -v
   ```
```

---

## Special Considerations

### High-Risk Indicators

Watch for these patterns:
- **Public API changes**: Functions used outside module
- **Protocol/Interface changes**: Abstract classes, type hints
- **Cross-module impact**: Changes affecting multiple modules
- **Core infrastructure**: Changes to domain models, event system

### Low-Risk Indicators

These suggest safer changes:
- **Private functions**: Names starting with `_`
- **Internal modules**: Not exported in `__init__.py`
- **High test coverage**: Many tests for this code
- **Isolated code**: Few or no dependents

---

## Integration Notes

This skill is invoked by `rv-refactor` orchestrator:
```
Phase 1: Analysis
1. Run /rv-impact-analyzer on refactoring target
2. Use risk assessment to inform planning
```

---

## Rules

1. **ANALYZE before changing** - Always assess impact first
2. **TWO LEVELS max** - Don't go deeper than indirect deps
3. **COUNT tests** - Test coverage reduces risk
4. **FLAG public APIs** - Extra caution for exported interfaces
5. **RECOMMEND strategy** - Guide user based on risk level
