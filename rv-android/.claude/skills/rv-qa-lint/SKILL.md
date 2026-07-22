---
name: rv-qa-lint
description: >-
  Run linter on module or file. Use for code quality checks, pre-commit validation, or CI preparation.
  Do NOT use for: auto-fixing issues (use /rv-qa-lint-fix), full verification (use /rv-verify).
argument-hint: [module-name or file-path]
context: fork
agent: general-purpose
allowed-tools: Read, Bash
---

# Lint Code: $ARGUMENTS

## Quality Standards

This skill verifies **product standards** (code quality) and **process standards** (coding conventions).

| Standard Type | What We Check |
|---------------|---------------|
| **Product** | Code correctness, security patterns, complexity |
| **Process** | Formatting, naming conventions, import order |

### Quality Attributes Targeted

| Attribute | How Verified |
|-----------|--------------|
| Understandability | Style, naming (flake8) |
| Maintainability | Type hints (mypy), complexity (radon) |
| Security | Vulnerability patterns (bandit) |
| Complexity | Cyclomatic complexity (radon) |

---

## Steps

1. **Parse scope** from $ARGUMENTS:
   - Module name: lint entire module
   - File path: lint specific file

2. **Run linters**:
   ```bash
   cd modules/$MODULE

   # Flake8 (style + errors)
   uv run flake8 src/ --max-line-length=120

   # MyPy (type checking)
   uv run mypy src/ --ignore-missing-imports

   # Black (formatting check)
   uv run black src/ --check

   # isort (import order check)
   uv run isort src/ --check-only
   ```

3. **Run security analysis**:
   ```bash
   # Bandit (security vulnerabilities)
   uv run bandit -r src/ --severity-level medium -f txt

   # For detailed JSON report
   uv run bandit -r src/ -f json -o bandit_report.json
   ```

   **Severity Levels**:
   - HIGH: Must fix before commit (e.g., hardcoded passwords, SQL injection)
   - MEDIUM: Review and justify (e.g., use of assert, exec)
   - LOW: Track for future (e.g., binding to all interfaces)

4. **Run complexity metrics** (optional but recommended):
   ```bash
   # Cyclomatic complexity
   uv run radon cc src/ -a -s

   # Maintainability index
   uv run radon mi src/ -s
   ```

   **Complexity Thresholds**:
   | Metric | Good | Acceptable | Review |
   |--------|------|------------|--------|
   | CC (function) | ≤ 5 | 6-10 | > 10 |
   | MI (file) | ≥ 65 | 40-64 | < 40 |

5. **Categorize issues** by severity

6. **Generate report**

## Linter Configuration

```ini
# pyproject.toml or setup.cfg

[flake8]
max-line-length = 120
exclude = .git,__pycache__,build,dist
ignore = E203,W503

[mypy]
python_version = 3.11
ignore_missing_imports = True
strict_optional = True

[tool.black]
line-length = 120
target-version = ['py311']

[tool.isort]
profile = "black"
line_length = 120
```

## Output Format

```
## Lint Report: [scope]

### Summary
| Linter | Issues | Status |
|--------|--------|--------|
| flake8 | X | ✅/❌ |
| mypy | Y | ✅/❌ |
| black | Z | ✅/❌ |
| isort | W | ✅/❌ |
| bandit | V | ✅/❌ |
| radon (CC) | U | ✅/⚠️ |
| radon (MI) | T | ✅/⚠️ |

### Complexity Metrics
| File | CC (avg) | CC (max) | MI | Status |
|------|----------|----------|-----|--------|
| module.py | 4.2 | 8 | 72 | OK |
| parser.py | 7.5 | 15 | 45 | REVIEW |

### Issues by Severity

#### Errors (must fix)
| File | Line | Code | Message |
|------|------|------|---------|
| file.py | 10 | E501 | line too long |

#### Warnings (should fix)
| File | Line | Code | Message |
|------|------|------|---------|
| file.py | 20 | W503 | line break before operator |

#### Style (nice to fix)
| File | Line | Code | Message |
|------|------|------|---------|
| file.py | 30 | C0301 | trailing whitespace |

#### Security Issues (bandit)
| File | Line | Severity | Issue |
|------|------|----------|-------|
| file.py | 42 | HIGH | B105: hardcoded_password_string |

### Auto-Fix Available
Use `/rv-qa-lint-fix $ARGUMENTS` to automatically fix:
- Import sorting (isort)
- Formatting (black)
- Some flake8 issues (autoflake)
```

## Common Issue Codes

### Style Issues (flake8)
| Code | Meaning | Auto-fix? |
|------|---------|-----------|
| E501 | Line too long | black |
| E302 | Expected 2 blank lines | black |
| F401 | Unused import | autoflake |
| F841 | Unused variable | manual |
| W503 | Line break before operator | ignore |

### Complexity Grades (radon)
| Grade | CC Range | MI Range | Action |
|-------|----------|----------|--------|
| A | 1-5 | 100-20 | Excellent, no action |
| B | 6-10 | 19-10 | Good, monitor |
| C | 11-20 | 9-0 | Review, consider refactoring |
| D | 21-30 | - | High priority refactoring |
| E | 31-40 | - | Critical, must refactor |
| F | 41+ | - | Unmaintainable |

### Security Issues (bandit)
| Code | Meaning | Severity |
|------|---------|----------|
| B101 | Use of assert | LOW |
| B105 | Hardcoded password | HIGH |
| B301 | Pickle use | MEDIUM |
| B602 | Subprocess with shell | HIGH |
| B608 | SQL injection | HIGH |
