# Change Plan: gh38-cicd-restructure

**Date**: 2026-03-13
**Track**: Quick Path
**Priority**: High
**GitHub Issue**: [#38](https://github.com/PAMunb/rvsec/issues/38)
**PRD Reference**: N/A
**Domains**: N/A (CI/CD infrastructure, outside module scope)

## 1. Context

The CI pipeline (`.github/workflows/ci.yml`) is completely broken. It reflects a state from months ago and fails on every push to `modules` or `develop`. The immediate fatal error is Maven failing to resolve `android.jar` for the `rvsmart` module, which kills the entire single-job pipeline before any Python tests run.

Seven problems identified in [#38](https://github.com/PAMunb/rvsec/issues/38):

1. **Poetry**: The project migrated to uv workspace, but CI still uses `snok/install-poetry`, `poetry install`, `poetry run`.
2. **Dead modules**: CI tests `rv-llm` and `rvandroid-tool`, both deleted. The current 15 modules are ignored.
3. **Maven/rvsmart**: `rvsmart` depends on `android.jar` (API 29) via `systemPath`. GitHub runners don't have this file at `/usr/local/lib/android/sdk/platforms/android-29/android.jar`.
4. **Monolithic job**: Maven failure exits the job, Python tests never execute.
5. **Disk space hacks**: Per-module install/clean cycles to fit 14GB runner limit. With uv workspace (single shared `.venv`), this is unnecessary.
6. **`continue-on-error: true`**: Applied to every test step, masking real failures.
7. **Backup dirs in git**: `backup/`, `docs/backup/`, `modules/rv-agent/backup/`, `modules/rv-agent-validation/backup/` are tracked — ~700MB downloaded on every checkout, wasting runner disk and time.

## 2. Scope

Single file rewrite: `.github/workflows/ci.yml` (relative to repo root).

**Group A — CI workflow rewrite**: Replace the entire `ci.yml` with two independent jobs:

- **`maven-build`**: Checks out code, removes backup dirs, builds Maven project excluding `rvsmart`.
- **`python-test`**: Checks out code, removes backup dirs, installs via `uv sync`, runs `uv run pytest`.

Both jobs are independent (no `needs:` dependency between them).

## 3. File Inventory

| File | Action | Detail |
|------|--------|--------|
| `.github/workflows/ci.yml` | Rewrite | Replace entire file with new 2-job pipeline |

### New workflow structure

**Job `maven-build`**:
1. `actions/checkout@v4`
2. Remove backup directories (`rm -rf rv-android/backup/ rv-android/docs/backup/ rv-android/modules/rv-agent/backup/ rv-android/modules/rv-agent-validation/backup/`)
3. `actions/setup-java@v4` — JDK 21 Temurin with Maven cache
4. `mvn clean install -DskipTests -DskipMopAgent -pl '!rvsec/rvsec-android/rvsmart'`

**Job `python-test`**:
1. `actions/checkout@v4`
2. Remove backup directories (same as above)
3. `actions/setup-python@v5` — Python 3.12
4. `astral-sh/setup-uv@v4` — with cache on `rv-android/uv.lock`
5. Set `RVSEC_HOME=${{ github.workspace }}`
6. `uv sync` (working-directory: `rv-android`)
7. `uv run pytest modules/ -m "not slow" --tb=short -q` (working-directory: `rv-android`)

### What is removed from the old workflow

- `snok/install-poetry@v1` and all Poetry references
- `actions/cache@v3` for Poetry (replaced by uv's built-in cache)
- All per-module install/test/clean steps (rv-android-core, rv-monitor-generator, rv-static-analysis, rv-llm, rvandroid-tool)
- Integration test step (`-m "slow"`)
- Code quality checks step (flake8, bandit)
- Coverage config creation and coverage artifact upload
- Quality report generation and upload
- All `continue-on-error: true` directives

## 4. Execution Order

Single group — sequential:

1. Write the new `ci.yml`
2. Validate syntax (actionlint or manual review)
3. Verify acceptance criteria

## 5. Acceptance Criteria

- [ ] `ci.yml` has two independent jobs: `maven-build` and `python-test`
- [ ] Maven job excludes `rvsmart` module via `-pl '!rvsec/rvsec-android/rvsmart'`
- [ ] Python job uses `uv sync` + `uv run pytest` (no Poetry references anywhere)
- [ ] No references to deleted modules (`rv-llm`, `rvandroid-tool`)
- [ ] No `continue-on-error: true` on any step
- [ ] Both jobs remove backup directories after checkout to free disk space
- [ ] Triggers on push/PR to `develop` and `modules` branches
