# Release Checklist

Pre-release validation steps to ensure quality releases.

---

## Pre-Release Checklist

### Code Quality

| Check | Command | Criteria | Required |
|-------|---------|----------|----------|
| All tests pass | `uv run pytest -v` | Exit code 0 | **Yes** |
| Lint clean | `uv run flake8 src/` | No errors | **Yes** |
| Type check | `uv run mypy src/` | No errors | Recommended |
| Security scan | `uv run bandit -r src/` | No HIGH issues | Recommended |

### Version Control

| Check | Command | Criteria | Required |
|-------|---------|----------|----------|
| Clean working tree | `git status --porcelain` | Empty output | **Yes** |
| On correct branch | `git branch --show-current` | master/main/release | **Yes** |
| Branch up to date | `git fetch && git status` | "Up to date" | **Yes** |
| All commits pushed | `git log origin/master..HEAD` | Empty | **Yes** |

### Dependencies

| Check | Command | Criteria | Required |
|-------|---------|----------|----------|
| Lock file current | `uv lock --check` | No changes needed | **Yes** |
| No security vulnerabilities | `uv run safety check` | No critical | Recommended |
| Dependencies installable | `uv sync` | Success | **Yes** |

### Documentation

| Check | Location | Criteria | Required |
|-------|----------|----------|----------|
| CHANGELOG updated | `CHANGELOG.md` | Has new version entry | **Yes** |
| README current | `README.md` | No outdated info | Recommended |
| API docs generated | `docs/` | If applicable | Recommended |

---

## Release Type Checklists

### Patch Release (X.Y.Z)

Minimal checklist for bug fixes:

- [ ] Fix implemented and tested
- [ ] All tests pass
- [ ] No lint errors
- [ ] CHANGELOG entry added
- [ ] Version bumped
- [ ] Commit and tag created

### Minor Release (X.Y.0)

Standard checklist for new features:

- [ ] All patch release checks
- [ ] New features documented
- [ ] New tests added for features
- [ ] Deprecation warnings added (if any)
- [ ] Examples updated
- [ ] Migration notes (if any)

### Major Release (X.0.0)

Full checklist for breaking changes:

- [ ] All minor release checks
- [ ] Migration guide written
- [ ] Breaking changes documented
- [ ] Old deprecations removed
- [ ] API documentation updated
- [ ] Upgrade path tested
- [ ] Announcement prepared

---

## Multi-Module Release Checklist

For workspaces with multiple modules:

### Pre-Release

- [ ] All modules have consistent version goal
- [ ] Dependency order documented
- [ ] Inter-module dependencies will be satisfied
- [ ] Each module passes its own checks

### During Release

- [ ] Process modules in dependency order:
  1. [ ] rv-android-core (no deps)
  2. [ ] rv-tools, rv-uiautomator (core deps)
  3. [ ] rv-screen-parser, rv-static-analysis, rv-coverage
  4. [ ] rv-monitor-generator, rv-instrumentation
  5. [ ] rv-platform
  6. [ ] rv-agent
  7. [ ] rv-experiment
  8. [ ] rv-agent-validation

- [ ] Each module version updated
- [ ] Each module's inter-dependencies updated
- [ ] Each module built successfully
- [ ] Each module published to PyPI

### Post-Release

- [ ] All modules available on PyPI
- [ ] Test install from PyPI works
- [ ] Git tags pushed
- [ ] GitHub release created

---

## Validation Commands

### Quick Validation Script

```bash
#!/bin/bash
# run-release-checks.sh

set -e

echo "=== Release Validation ==="

echo "1. Checking git status..."
if [ -n "$(git status --porcelain)" ]; then
    echo "ERROR: Uncommitted changes"
    git status --short
    exit 1
fi
echo "✓ Clean working tree"

echo "2. Checking branch..."
BRANCH=$(git branch --show-current)
if [[ "$BRANCH" != "master" && "$BRANCH" != "main" && "$BRANCH" != release/* ]]; then
    echo "WARNING: On branch $BRANCH (expected master/main/release/*)"
fi
echo "✓ On branch: $BRANCH"

echo "3. Running tests..."
uv run pytest -v --tb=short
echo "✓ Tests passed"

echo "4. Running lint..."
uv run flake8 src/
echo "✓ Lint passed"

echo "5. Checking lock file..."
uv lock --check
echo "✓ Lock file current"

echo ""
echo "=== All checks passed ==="
```

### Full Module Validation

```bash
#!/bin/bash
# validate-all-modules.sh

MODULES=(
    "rv-android-core"
    "rv-tools"
    "rv-uiautomator"
    "rv-screen-parser"
    "rv-static-analysis"
    "rv-coverage"
    "rv-monitor-generator"
    "rv-instrumentation"
    "rv-platform"
    "rv-agent"
    "rv-experiment"
    "rv-agent-validation"
)

echo "=== Validating All Modules ==="

for module in "${MODULES[@]}"; do
    echo ""
    echo "--- $module ---"

    if [ ! -d "modules/$module" ]; then
        echo "SKIP: Module not found"
        continue
    fi

    cd "modules/$module"

    # Check tests
    if uv run pytest -v --tb=line 2>/dev/null; then
        echo "✓ Tests passed"
    else
        echo "✗ Tests failed"
    fi

    # Check lint
    if uv run flake8 src/ 2>/dev/null; then
        echo "✓ Lint passed"
    else
        echo "✗ Lint issues"
    fi

    cd ../..
done

echo ""
echo "=== Validation Complete ==="
```

---

## Common Issues Checklist

### Before Release

| Issue | Check | Resolution |
|-------|-------|------------|
| Tests fail in CI | Run with same Python version | Fix test or update CI |
| Missing dependencies | Check pyproject.toml | Add missing deps |
| Version mismatch | Compare pyproject.toml and __init__.py | Sync versions |
| Outdated lock file | Run `uv lock` | Regenerate and commit |

### After Release

| Issue | Check | Resolution |
|-------|-------|------------|
| Package not on PyPI | Check publish output | Re-run publish |
| Wrong version published | Check PyPI page | Yank and re-release |
| Missing files in package | Check wheel contents | Update MANIFEST.in |
| Import fails | Test install | Fix package structure |

---

## Release Approval Matrix

| Change Type | Reviewer Required | Approval Level |
|-------------|-------------------|----------------|
| Patch (bug fix) | Team member | 1 reviewer |
| Minor (feature) | Senior dev | 1+ reviewers |
| Major (breaking) | Tech lead | Team consensus |
| Security fix | Security team | Expedited |
| Hotfix | On-call engineer | Post-review OK |

---

## Go/No-Go Decision

### GO Conditions

All of these must be true:

- [ ] All required checks pass
- [ ] No blocking issues
- [ ] Changelog is complete
- [ ] Documentation is updated
- [ ] Approvals received (per matrix)

### NO-GO Conditions

Any of these blocks release:

- [ ] Failing tests
- [ ] Critical security vulnerabilities
- [ ] Incomplete migrations for breaking changes
- [ ] Missing documentation for new features
- [ ] Unresolved review comments
