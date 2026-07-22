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
| rv-experiment | `modules/rv-experiment` | Experiment orchestration |

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
uv run python -c "import rv_android_core, rv_agent; print('OK')"
```

### Testing

```bash
# Run module tests
cd modules/[module-name]
PYTHONPATH=../rv-android-core/src:src uv run pytest tests/ -v

# Run unit tests only
PYTHONPATH=../rv-android-core/src:src uv run pytest tests/unit/ -v

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run single test
uv run pytest tests/unit/test_file.py::TestClass::test_name -v
```

### Code Quality

```bash
# Format
uv run black src/ && uv run isort src/

# Lint
uv run flake8 src/

# Type check
uv run mypy src/

# Security scan
uv run bandit -r src/
```

### Full Verification (tests + lint + type)

```bash
cd modules/[module-name]

# Run all checks
PYTHONPATH=../rv-android-core/src:src uv run pytest tests/ -v && \
uv run black --check src/ && \
uv run isort --check src/ && \
uv run flake8 src/
```

---

## Entry Points

| Entry Point | Command | Purpose |
|-------------|---------|---------|
| rv-experiment | `uv run rv-experiment run` | Full experiment workflow |
| rv-platform | `uv run rv-platform run` | Direct task execution |
| rv-agent | `uv run rv-agent` | LLM-driven testing |
| rv-monitor-generator | `uv run rv-monitor-generator generate` | Monitor generation |

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
2. `rv-tools`, `rv-uiautomator` (infrastructure)
3. `rv-screen-parser`, `rv-coverage`, `rv-static-analysis` (analysis)
4. `rv-instrumentation`, `rv-monitor-generator` (instrumentation)
5. `rv-agent`, `rv-platform` (execution)
6. `rv-experiment` (orchestration)

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

---

## Docker Execution

```bash
# Run experiment in Docker container
docker run --rm --device /dev/kvm \
  -e RV_TOOLS=monkey \
  -e RV_TIMEOUTS=300 \
  -e RV_NO_WINDOW=true \
  -e RV_APKS_DIR=/opt/rvsec/rv-android/apks \
  -v ./apks_examples:/opt/rvsec/rv-android/apks \
  -v ./results:/opt/rvsec/rv-android/results \
  phtcosta/rvandroid_dev:0.8.0

# Resume interrupted experiment (same --name, same volume)
docker run --rm --device /dev/kvm \
  -e RV_TOOLS=monkey \
  -e RV_TIMEOUTS=300 \
  -e RV_EXPERIMENT_NAME=batch_01 \
  -v ./results:/opt/rvsec/rv-android/results \
  phtcosta/rvandroid_dev:0.8.0
```

### Docker Security Checks

```bash
# Pre-build: lint Dockerfile
hadolint docker/base/Dockerfile

# Post-build: image CIS benchmarks
dockle phtcosta/rvandroid:0.8.0

# Post-build: vulnerability scan
trivy image --severity HIGH,CRITICAL phtcosta/rvandroid:0.8.0
```

See `docker/SECURITY.md` for full details.

---

## Monitor Generation

```bash
# Generate JCA cryptography monitors
uv run rv-monitor-generator generate \
  --specs-dir $RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca \
  --output ./output/jca-monitors

# Auto-discover specifications
uv run rv-monitor-generator generate --output ./output/auto-monitors
```

---

## Output Directory Structure

```
rv-android/
├── apks_examples/              # Source APKs (input, not cleaned)
├── out/                        # Temporary artifacts (cleaned by clear.sh)
│   ├── monitors/               # Generated monitors from rv-monitor-generator
│   ├── instrumented_apks/      # APKs with monitors woven by rv-instrumentation
│   └── static_analysis/        # GATOR, GESDA, REACH output files
├── results/                    # Persistent experiment results
│   └── <experiment_id>/        # Per-experiment directory
│       └── <apk_name>/         # Per-APK results
│           ├── coverage.csv    # Per-method coverage data
│           ├── errors.csv      # Monitored operations violations
│           ├── summary.csv     # Aggregate metrics per task
│           ├── results.json    # Complete experiment data (JSON)
│           ├── performance.csv # Task execution timing
│           └── tasks.json      # Task state persistence
├── tmp/, rvm_tmp/, lib_tmp/    # Various temporary files
├── sootOutput/                 # Soot compiler output
└── clear.sh                    # Cleanup script
```

**What gets cleaned by `./clear.sh`:**
- `out/`, `tmp/`, `rvm_tmp/`, `lib_tmp/`, `sootOutput/`, `output/`, `mop_out/`, `__pycache__/`, `*.dex`, `ajcore*.txt`

**Preserved (unless `--clean-results`):** `results/`, `apks_examples/`

---

## Reusing Pre-Processed Artifacts (--skip-* flags)

When using `--skip-monitors`, `--skip-instrument`, or `--skip-static`, **`--apks-dir` must point to instrumented APKs** from a previous run, not original APKs (otherwise coverage = 0%).

```bash
# WRONG: Points to original APKs — coverage will be 0%
rv-experiment run --tools rvagent:pure_algorithm --apks-dir ./apks_examples --skip-monitors --skip-instrument --skip-static

# CORRECT: Point to instrumented APKs from a previous run
rv-experiment run --tools rvagent:pure_algorithm \
  --apks-dir ./results/<experiment_id>/instrumented_apks \
  --skip-monitors --skip-instrument --skip-static
```

**Pre-processed artifact locations** (from a completed experiment):
- `results/<experiment_id>/instrumented_apks/` — Instrumented APKs with monitors
- `results/<experiment_id>/static_analysis/` — GATOR, GESDA, REACH output
- `out/monitors/` — Generated monitors (may be cleaned by clear.sh)
