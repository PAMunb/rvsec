---
name: rv-qa-lint
description: Run linter on module or file. Use for code quality checks, pre-commit validation, or CI preparation.
argument-hint: [module-name or file-path]
context: fork
agent: general-purpose
allowed-tools: Read, Bash
---

# Lint Code: $ARGUMENTS

## Steps

1. **Parse scope** from $ARGUMENTS:
   - Module name: lint entire module
   - File path: lint specific file

2. **Run linters**:
   ```bash
   cd modules/$MODULE

   # Flake8 (style + errors)
   poetry run flake8 src/ --max-line-length=120

   # MyPy (type checking)
   poetry run mypy src/ --ignore-missing-imports

   # Black (formatting check)
   poetry run black src/ --check

   # isort (import order check)
   poetry run isort src/ --check-only
   ```

3. **Categorize issues** by severity

4. **Generate report**

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

### Auto-Fix Available
Use `/rv-qa-lint-fix $ARGUMENTS` to automatically fix:
- Import sorting (isort)
- Formatting (black)
- Some flake8 issues (autoflake)
```

## Common Issue Codes

| Code | Meaning | Auto-fix? |
|------|---------|-----------|
| E501 | Line too long | black |
| E302 | Expected 2 blank lines | black |
| F401 | Unused import | autoflake |
| F841 | Unused variable | manual |
| W503 | Line break before operator | ignore |
