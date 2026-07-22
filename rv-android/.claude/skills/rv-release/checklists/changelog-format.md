# Changelog Format

Conventions for maintaining CHANGELOG.md and generating release notes.

---

## Changelog Principles

1. **Changelogs are for humans**, not machines
2. **Every version should have an entry**
3. **Group changes by type**
4. **Most recent version first**
5. **Include dates**
6. **Link to issues/PRs** when relevant

---

## File Structure

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- New features not yet released

## [X.Y.Z] - YYYY-MM-DD

### Added
- New features

### Changed
- Changes to existing functionality

### Deprecated
- Features that will be removed

### Removed
- Features removed in this release

### Fixed
- Bug fixes

### Security
- Security fixes

## [X.Y.Z-1] - YYYY-MM-DD
...
```

---

## Change Categories

### Added

New features or capabilities.

```markdown
### Added
- Add support for Qwen3-VL model in rv-agent
- Add `--dry-run` flag to release command
- Add TransitionManager for WTG-guided exploration
```

### Changed

Changes to existing functionality.

```markdown
### Changed
- Improve error messages in TaskExecutor
- Update default timeout from 120s to 300s
- Refactor ScreenParser to use visitor pattern
```

### Deprecated

Features marked for removal in future versions.

```markdown
### Deprecated
- `old_function()` is deprecated, use `new_function()` instead
- `ConfigManager.load_yaml()` - use `ConfigManager.load()` with format parameter
```

### Removed

Features removed in this release.

```markdown
### Removed
- Remove legacy XML parser (deprecated in v1.2.0)
- Remove Python 3.9 support
```

### Fixed

Bug fixes.

```markdown
### Fixed
- Fix race condition in EventBus subscriber notification
- Fix memory leak in screenshot capture loop
- Fix incorrect coordinate normalization for Qwen3-VL (#123)
```

### Security

Security-related fixes.

```markdown
### Security
- Fix SQL injection vulnerability in query builder
- Update cryptography dependency to address CVE-2024-XXXX
- Add input validation for user-provided paths
```

---

## Commit Message to Changelog Mapping

### Conventional Commits

| Commit Prefix | Changelog Category |
|---------------|-------------------|
| `feat:` | Added |
| `fix:` | Fixed |
| `docs:` | (usually omit unless significant) |
| `style:` | (omit - no functional change) |
| `refactor:` | Changed |
| `perf:` | Changed |
| `test:` | (omit - internal) |
| `chore:` | (omit unless user-facing) |
| `BREAKING CHANGE:` | Changed (with callout) |

### Examples

Commit:
```
feat: add support for multimode execution in rv-agent

Support running in pure_algorithm, llm_only, or multimode.
Multimode uses 70% LLM / 30% algorithm by default.
```

Changelog:
```markdown
### Added
- Add multimode execution support in rv-agent (pure_algorithm, llm_only, multimode)
```

Commit:
```
fix: resolve coordinate normalization issue with Qwen3-VL

Qwen3-VL returns coordinates in [0, 1000) range.
Added denormalization to convert to device pixels.

Fixes #123
```

Changelog:
```markdown
### Fixed
- Fix coordinate normalization for Qwen3-VL model (#123)
```

---

## Generating Changelog

### From Git Log

```bash
# Get commits since last tag
LAST_TAG=$(git describe --tags --abbrev=0)
git log ${LAST_TAG}..HEAD --oneline --no-merges

# Group by type
git log ${LAST_TAG}..HEAD --oneline --no-merges | grep "^.*feat:"
git log ${LAST_TAG}..HEAD --oneline --no-merges | grep "^.*fix:"
```

### Automated Generation Script

```bash
#!/bin/bash
# generate-changelog.sh

VERSION=$1
DATE=$(date +%Y-%m-%d)
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")

echo "## [$VERSION] - $DATE"
echo ""

if [ -n "$LAST_TAG" ]; then
    RANGE="${LAST_TAG}..HEAD"
else
    RANGE="HEAD"
fi

# Added
ADDED=$(git log $RANGE --oneline --no-merges | grep -E "^[a-f0-9]+ feat:" | sed 's/^[a-f0-9]* feat:/- /')
if [ -n "$ADDED" ]; then
    echo "### Added"
    echo "$ADDED"
    echo ""
fi

# Fixed
FIXED=$(git log $RANGE --oneline --no-merges | grep -E "^[a-f0-9]+ fix:" | sed 's/^[a-f0-9]* fix:/- /')
if [ -n "$FIXED" ]; then
    echo "### Fixed"
    echo "$FIXED"
    echo ""
fi

# Changed
CHANGED=$(git log $RANGE --oneline --no-merges | grep -E "^[a-f0-9]+ (refactor|perf):" | sed 's/^[a-f0-9]* (refactor|perf):/- /')
if [ -n "$CHANGED" ]; then
    echo "### Changed"
    echo "$CHANGED"
    echo ""
fi
```

---

## Entry Guidelines

### Do

- Use imperative mood ("Add" not "Added" or "Adds")
- Start with a verb
- Be specific but concise
- Include issue/PR references
- Group related changes

```markdown
### Fixed
- Fix memory leak in screenshot capture loop
- Fix race condition when multiple subscribers (#45)
```

### Don't

- Don't include internal changes (test refactoring, CI updates)
- Don't include trivial changes (typo fixes, whitespace)
- Don't copy full commit messages
- Don't include implementation details

```markdown
### Fixed
- Fixed the bug in line 234 of executor.py where the variable was wrong  ❌
- Fix executor error handling  ✓
```

---

## Breaking Changes

Breaking changes deserve special attention:

### In Changelog

```markdown
## [2.0.0] - 2026-01-24

### Breaking Changes

- **API**: `execute_task()` now requires `context` parameter
- **Config**: Removed `legacy_mode` configuration option
- **Python**: Dropped support for Python 3.9

### Migration Guide

See [MIGRATION.md](MIGRATION.md) for upgrade instructions.

### Changed
- Refactor TaskExecutor to use component-based architecture
```

### Migration Guide Example

```markdown
# Migration Guide: v1.x to v2.0

## Breaking Changes

### 1. `execute_task()` signature change

Before (v1.x):
```python
executor.execute_task(task)
```

After (v2.0):
```python
executor.execute_task(task, context=execution_context)
```

### 2. Configuration changes

Remove from your config:
```yaml
# Remove this
legacy_mode: true
```
```

---

## Unreleased Section

Keep an "Unreleased" section at the top for changes not yet released:

```markdown
## [Unreleased]

### Added
- Work in progress feature A

### Fixed
- Bug fix waiting for release
```

At release time:
1. Rename "Unreleased" to version number
2. Add date
3. Create new empty "Unreleased" section

---

## Multi-Module Changelogs

For workspaces with multiple modules:

### Option 1: Single Root Changelog

```markdown
# Changelog

## [1.2.3] - 2026-01-24

### rv-android-core
- Fix error handling in EventBus

### rv-agent
- Add multimode execution support

### rv-platform
- Improve task scheduling performance
```

### Option 2: Per-Module Changelogs

Each module has its own `CHANGELOG.md`:

```
modules/
├── rv-android-core/
│   └── CHANGELOG.md
├── rv-agent/
│   └── CHANGELOG.md
```

Root changelog summarizes:

```markdown
## [1.2.3] - 2026-01-24

See individual module changelogs for details:
- [rv-android-core](modules/rv-android-core/CHANGELOG.md)
- [rv-agent](modules/rv-agent/CHANGELOG.md)
```

---

## Links Section

At the bottom of CHANGELOG.md, add comparison links:

```markdown
[Unreleased]: https://github.com/user/project/compare/v1.2.3...HEAD
[1.2.3]: https://github.com/user/project/compare/v1.2.2...v1.2.3
[1.2.2]: https://github.com/user/project/compare/v1.2.1...v1.2.2
[1.2.1]: https://github.com/user/project/releases/tag/v1.2.1
```
