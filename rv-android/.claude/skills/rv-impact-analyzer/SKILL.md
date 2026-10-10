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

Analyze the ripple effects of changing a file, class, function or module before refactoring.
All commands run from the repository root.

## Supporting Files

- **Templates**: `templates/impact-report.md` - Report output format
- **Coupling scale**: `.claude/skills/rv-analyze-dependencies/reference.md`, section
  **Coupling Beyond Imports** (strength, distance, volatility, diagnosis table, known data
  contracts across languages). Read it at Stage 2.

---

## Workflow

```
STAGE 1: DIRECT DEPENDENCIES ────────────────────────────────────►
    │  Who imports this, and who reads what it writes?
    ▼
STAGE 2: INDIRECT DEPENDENCIES + COUPLING WEIGHT ────────────────►
    │  2 levels of dependents; strength × distance × volatility per relation
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

Find all files that directly import or use the target. `TARGET` is a module, class or
function name (e.g. `llm_client`, `LLMClient`); the source dirs come from the uv workspace
definition, so plugins such as `aperv_tool` are included.

```bash
TARGET="llm_client"
SRCS=$(python3 .claude/skills/rv-analyze-dependencies/scripts/workspace_deps.py --src-dirs)
echo "## imports"; grep -rnE --include='*.py' "^\s*(from|import)\s+[A-Za-z0-9_.]*\b${TARGET}\b|^\s*from\s+\S+\s+import\s+.*\b${TARGET}\b" $SRCS
echo "## other references (calls, multi-line imports, string lookups)"; grep -rnw --include='*.py' "$TARGET" $SRCS | grep -vE ':\s*(from|import)\s'
```

If the target reads or writes a file another component consumes (`.apk.json`, descriptor
JSON, `.mop`, a log line format) or drives a Java tool, its consumers do not import it.
Find them with the **DATA ARTIFACTS** grep of `/rv-analyze-dependencies` Step 4 and the
known-contracts table in its reference, and list each consumer as a direct dependent with
import type `data contract` — including the Java side.

**Output**: List of directly dependent files

### Stage 2: Indirect Dependencies and Coupling Weight

For each direct dependent, find THEIR dependents (Stage 1 again with the dependent as target).

```
Target: llm_client.py
    │
    ├── DIRECT: agent_factory.py imports llm_client
    │   │
    │   └── INDIRECT: <who imports agent_factory>
    │
    └── DIRECT: rv_agent.py imports llm_client
        │
        └── INDIRECT: <who imports rv_agent>
```

**Limit**: 2 levels deep (to avoid explosion)

Then weigh each **direct** relation with the scale in `rv-analyze-dependencies/reference.md`
(do not restate it in the report, cite the levels):
- **Strength**: contract, model, functional or intrusive — what the dependent knows about the
  target, with the file:line that shows it.
- **Distance**: same module, other uv module, or process/language boundary (Java subprocess,
  container, HTTP).
- **Volatility**: co-change of the two units over the last six months:
  ```bash
  bash .claude/skills/rv-analyze-dependencies/scripts/cochange.sh "6 months ago" 1 | grep -E "<target-module>"
  ```
  No line means the module never changed together with another unit in the window: low.
- **Diagnosis**: from the reference's table (critical, acceptable, good, attention).

A change that alters the shape of a data contract across a language boundary is critical
regardless of how few files import the target: the other side fails at run time, not at
import time, and no Python test of this repository catches it.

### Stage 3: Test Coverage Mapping

Find tests that might be affected:

```bash
# Tests that reference the target
grep -rlw --include='*.py' "$TARGET" modules/*/tests/

# All tests of the target's module (MODULE = e.g. rv-agent)
find modules/$MODULE/tests -name 'test_*.py' ! -path '*__pycache__*'
```

For a data-contract target, also list the pinning tests on the other side (fixtures of the
contract file, e.g. `modules/aperv-tool/tests/fixtures/*.apk.json`) and the Java module's tests.

**Output**: List of test files that should be run

### Stage 4: Risk Assessment

Calculate risk based on:

| Factor | Weight | Criteria |
|--------|--------|----------|
| Direct dependents | 3x | Each file importing the target, and each data-contract consumer |
| Indirect dependents | 1x | Transitive dependencies |
| Test coverage | -1x | Tests reduce risk |
| Public API | +5 | If target is public API |
| Cross-module | +3 | If impacts multiple modules |
| Coupling diagnosis | +5 / +2 | Worst Stage 2 relation is critical / attention |

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
| agent/agent_factory.py | from...import | rv-agent |
| agent/rv_agent.py | from...import | rv-agent |

**Direct dependents**: X files

### Stage 2: Indirect Dependencies and Coupling Weight
```
Target
├── agent_factory.py (DIRECT)
│   └── ... (INDIRECT)
└── rv_agent.py (DIRECT)
    └── ... (INDIRECT)
```

| Relation | Strength | Distance | Volatility | Diagnosis |
|----------|----------|----------|------------|-----------|
| rv_agent.py → llm_client | model (`rv_agent.py:50`) | same module | n co-changes | good |

**Total affected files**: Y files (X direct + Z indirect)

### Stage 3: Test Coverage
| Test File | Coverage Type |
|-----------|---------------|
| modules/rv-agent/tests/unit/test_llm_client.py | Unit test |

**Tests to run**: Z test files

### Stage 4: Risk Assessment

| Factor | Score | Reason |
|--------|-------|--------|
| Direct deps | +6 | 2 direct dependents |
| Indirect deps | +4 | 4 indirect dependents |
| Test coverage | -3 | 3 test files |
| Public API | +5 | Used by external modules |
| Coupling diagnosis | +0 | worst relation: good |
| **TOTAL** | **12** | |

### Risk Level: HIGH

### Recommendations

1. **Before changing**:
   - Ensure all tests pass
   - Review indirect dependencies
   - Copy any file that will be deleted to `backup/` first

2. **Change strategy** (P3, no backward compatibility):
   - Change the target and update every caller and data-contract consumer in the same
     change; no adapters, aliases or shims for the old form
   - Grep for dangling references after the change
   - Test after each step

3. **Tests to run** (CI flags):
   ```bash
   uv run pytest modules/rv-agent/tests/unit/test_llm_client.py --import-mode=importlib -o "addopts=" -v
   uv run pytest modules/rv-agent/tests --import-mode=importlib -o "addopts=" -q
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
- **Data contracts across languages**: Keys of `*.apk.json`, JavaMOP descriptor JSON,
  `.mop` names, CLI flags of the Java tools, logcat line formats

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
4. **FLAG public APIs and data contracts** - Extra caution for exported interfaces and files read by another component
5. **RECOMMEND strategy** - Guide user based on risk level, within P3: update all callers in one change, never keep the old form alive
