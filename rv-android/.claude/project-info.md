# RV-Android Project Reference

Quick reference for common paths, commands, and environment setup.

---

## Module Paths

| Module | Path | Description |
|--------|------|-------------|
| rv-android-core | `modules/rv-android-core` | Foundation infrastructure |
| rv-platform | `modules/rv-platform` | Central execution platform |
| rv-tools | `modules/rv-tools` | Testing tool plugin system |
| rv-uiautomator | `modules/rv-uiautomator` | UIAutomator components |
| rv-monitor-generator | `modules/rv-monitor-generator` | RV monitor generation |
| rv-instrumentation | `modules/rv-instrumentation` | APK instrumentation |
| rv-static-analysis | `modules/rv-static-analysis` | Static analysis tools |
| rv-coverage | `modules/rv-coverage` | Coverage tracking |
| rv-screen-parser | `modules/rv-screen-parser` | UI parsing |
| rv-agent | `modules/rv-agent` | LLM-driven testing |
| rv-llm | `modules/rv-llm` | LLM client abstraction |
| rv-experiment | `modules/rv-experiment` | Experiment orchestration |
| rv-agent-validation | `modules/rv-agent-validation` | Validation framework |

---

## Environment Variables

```bash
# Required
export RVSEC_HOME="/path/to/rvsec"          # Monitor generation
export ANDROID_HOME="/path/to/android-sdk"  # Emulator management

# Development
export RV_PYDANTIC=true                     # Enable validation

# RV-Agent (optional)
export RVAGENT_MODE="multimode"             # pure_algorithm | llm_only | multimode
```

---

## Common Commands

### Installation

```bash
# Install all modules
cd modules && ./install.sh

# Install single module
cd modules && ./install.sh rv-agent --verbose

# Verify installation
poetry run python -c "import rv_android_core, rv_agent; print('OK')"
```

### Testing

```bash
# Run module tests
cd modules/[module-name]
PYTHONPATH=../rv-android-core/src:src poetry run pytest tests/ -v

# Run unit tests only
PYTHONPATH=../rv-android-core/src:src poetry run pytest tests/unit/ -v

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Run single test
poetry run pytest tests/unit/test_file.py::TestClass::test_name -v
```

### Code Quality

```bash
# Format
poetry run black src/ && poetry run isort src/

# Lint
poetry run flake8 src/

# Type check
poetry run mypy src/

# Security scan
poetry run bandit -r src/
```

### Full Verification (tests + lint + type)

```bash
cd modules/[module-name]

# Run all checks
PYTHONPATH=../rv-android-core/src:src poetry run pytest tests/ -v && \
poetry run black --check src/ && \
poetry run isort --check src/ && \
poetry run flake8 src/
```

---

## Entry Points

| Entry Point | Command | Purpose |
|-------------|---------|---------|
| rv-experiment | `poetry run rv-experiment run` | Full experiment workflow |
| rv-platform | `poetry run rv-platform run` | Direct task execution |
| rv-agent | `poetry run rv-agent` | LLM-driven testing |
| rv-monitor-generator | `poetry run rv-monitor-generator generate` | Monitor generation |

---

## Test Data Locations

| Type | Path | Description |
|------|------|-------------|
| Screenshots | `/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots` | LLM testing dataset |
| Test fixtures | `modules/rv-agent/tests/fixtures/screenshots/` | Unit test data |
| UI dumps | `modules/rv-agent/tests/fixtures/ui_dumps/` | UIAutomator XML |

---

## Dependency Order

When installing or updating modules, follow this order:

1. `rv-android-core` (base)
2. `rv-tools`, `rv-uiautomator`, `rv-llm` (infrastructure)
3. `rv-screen-parser`, `rv-coverage`, `rv-static-analysis` (analysis)
4. `rv-instrumentation`, `rv-monitor-generator` (instrumentation)
5. `rv-agent`, `rv-platform` (execution)
6. `rv-experiment`, `rv-agent-validation` (orchestration)

---

## Backup Conventions

Before major changes, create backups following these conventions:

| Type | Location | Naming |
|------|----------|--------|
| Module files | `backup/<purpose>_<date>/` | e.g., `backup/cleanup_20260123/` |
| Refactored code | `modules/<module>/backup/` | e.g., `modules/rv-agent/backup/old_strategy/` |
| Deprecated modules | `backup/deprecated_modules_<date>/` | e.g., `backup/deprecated_modules_20260123/` |

**Backup Commands**:
```bash
# Create dated backup directory
mkdir -p backup/$(date +%Y%m%d)_<purpose>/

# Module-level backup
mkdir -p modules/$MODULE/backup/<description>/

# Move file to backup (preferred over delete)
mv src/old_file.py backup/$(date +%Y%m%d)_cleanup/
```

**Guidelines**:
- Backup before deleting, not after
- Use descriptive names for backup directories
- Clean up old backups periodically (after confirming not needed)
- Backups are gitignored - don't commit them

---

## Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| Import errors | Check `PYTHONPATH` includes `../rv-android-core/src:src` |
| Module not found | Run `./install.sh [module]` |
| LLM connection | Verify SGLang server at `http://192.168.0.36:30000/v1` |
| Emulator issues | Check `ANDROID_HOME` and `adb devices` |
| Monitor generation | Verify `RVSEC_HOME` is set |
