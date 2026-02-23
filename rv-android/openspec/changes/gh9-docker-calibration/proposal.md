# Proposal: Docker-Based Calibration — Full Lifecycle

**GitHub Issue**: #9
**Track**: Full SDD
**Branch**: `modules`

## Why

The calibration framework in rv-agent-validation tunes 37 parameters (11 MACRO + 26 MICRO) of the RVAgent exploration strategy across six phases (A through E), totaling ~308 hours of experiment execution. The original implementation used Python-level parallelism (Optuna `n_jobs=6` with thread-safe `EmulatorPool`), which broke on emulator crashes — killing all six workers and losing hours of work.

The infrastructure replacement is complete: two host-side scripts (`calibration_orchestrator.py`, `baseline_docker.py`) adopt the Docker container-level parallelism pattern proven in the rvsec-02 project, with 39 unit tests passing. Dead code removed per P3.

However, a deep analysis revealed that all intermediate data from previous runs (instrumented APKs, static analysis files, dataset splits) was never committed (gitignored) and is lost. The pipeline must be re-executed from scratch on the desktop, starting from preprocessing (Phase A) through validation (Phase E).

The key architectural decision: **all phases use Docker containers**. The preprocessing phase (instrumentation + static analysis) runs inside containers using `--skip-execution` to avoid tool execution overhead. This eliminates all host-side dependencies on RVSEC_HOME, Java 8, and Maven — the Docker image `phtcosta/rvandroid:0.8.0` contains everything needed. The image must be rebuilt (same `0.8.0` tag) before calibration to include all gh26 exploration improvements and gh18 error detection.

### Why SDD for an execution campaign

This is an unconventional use of SDD — we are using the artifact structure (proposal, design, tasks) not for code development but for **execution lifecycle management**. The justification:

1. **Duration and complexity**: ~13 days of continuous execution across 6 phases, each with inter-phase dependencies.
2. **Code corrections during execution**: Bugs discovered during execution must be fixed (with TDD regression tests) before the next phase.
3. **Context window management**: Each future Claude Code session loads ONLY the relevant section of design.md for the current phase.
4. **Multi-machine workflow**: Code lives on the laptop, execution happens on the desktop. Git-committed SDD artifacts provide shared state.
5. **Verifiable gates**: Each phase has explicit acceptance criteria that must pass before the next phase starts.

## What Changes

### Infrastructure (COMPLETED — Tasks 1-11)

- **`scripts/calibration_orchestrator.py`** (~600 lines): Optuna ask/tell loop with Docker container parallelism for Phases C/D. Supports `--resume` with orphaned trial recovery.
- **`scripts/baseline_docker.py`** (~390 lines): Batch execution across N containers for Phases B/E. Round-robin APK splitting, auto-aggregation, `--generate-only` mode.
- **Dead code removed**: `optimizer.py`, `runner.py`, `emulator_pool.py` -> `backup/calibration_legacy/`
- **39 unit tests** in `tests/calibration/`
- **Optuna upgraded**: 3.5 -> 4.7.0

### Infrastructure Bug Fixes (Task 12, partially complete)

- **SGLang networking** (DONE): Add `extra_hosts: ["host.docker.internal:host-gateway"]` to compose generators for container-to-host communication on Linux.
- **`llm_base_url` injection** (DONE): Add `--sglang-url` parameter to both scripts; injects `llm_base_url` into tool spec for Phase D (multimode).
- **Naming mismatch** (DONE): Fix `filter_apks_static_analysis.py` to output `passed_apks.txt` (matching `select_dataset.py` expectation).

### Docker Preprocessing Script (Task 12, new)

- **`scripts/preprocess_docker.py`** (NEW): Dedicated compose generator for Phase A. Overrides Docker entrypoint to pass `--skip-execution`, mounts `out/` volume for artifact collection. After containers finish, collects instrumented APKs + SA files and assembles the flat dataset directory.

### Execution Campaign (Tasks 15-24)

- **Phase A (Preprocessing)**: Docker containers run instrumentation + SA on 188 APKs with `--skip-execution` (no emulator, no tool). Host-side post-processing filters for completeness (3 SA files) and assembles `calibration_dataset_v2/`. Estimated ~2h.
- **Phase B (Baseline)**: 945 tasks, ~18.4h — establish BASELINE_MAX_ERRORS
- **Phase C (Macro calibration)**: 80 trials x 75 APKs, ~167h — tune 11 high-impact parameters
- **Phase D (Micro calibration)**: 100 trials x 75 APKs, ~208h — tune 26 fine-grained parameters (requires SGLang)
- **Phase E (Validation)**: 270 tasks, ~7.5h — validate 37 params on 30-APK holdout set (requires SGLang)

### Post-Execution (Tasks 25-27)

- **Parameter application**: Update `parameter_space.py` defaults and agent spec with optimal values

### Code Corrections (Dynamic)

When execution reveals bugs, correction tasks are inserted as sub-tasks (e.g., Task 19a) to preserve the original task numbering.

## Impact

### Affected Modules
- **rv-agent-validation**: `calibration/` subpackage (infrastructure done), `parameter_space.py` (after Phase D)

### Affected Specs
- **agent** (`openspec/specs/agent/spec.md`): After Phase D, the calibrated parameter defaults need a delta spec update (Task 26).

### Dependencies

| Dependency | Where | Notes |
|------------|-------|-------|
| Docker image `phtcosta/rvandroid:0.8.0` | Desktop | Rebuild from `modules` branch to include gh26/gh18 changes (overwrites existing tag) |
| Desktop machine (64 CPUs, 128GB RAM, KVM) | All phases | All execution happens here |
| SGLang server (Qwen3-VL-4B) | Phases D, E | Via `rvsec-vision-llm/docker-compose.yml` on desktop |
| `apks_complete.csv` | Phase A | APK metadata from experiment 1 |
| 188 original APKs (`exp01_jca=True`) | Phase A | Source APKs (unmodified, not instrumented) |

### Related FRs/NFRs
- **FR21**: RVAgent exploration — parameter calibration tunes the exploration strategy
- **NFR05**: Reproducibility — Optuna SQLite persistence, deterministic seeds, compose file archival
- **NFR07**: Performance — container-level parallelism for throughput

## Identified Risks

| # | Severity | Risk | Mitigation |
|---|----------|------|------------|
| R1 | HIGH | `valid_apks.txt` vs `passed_apks.txt` naming mismatch | Fixed (Task 12.5) |
| R3 | HIGH | SGLang container-to-host networking (no `extra_hosts`) | Fixed (Task 12.1-12.2) |
| R4 | HIGH | `llm_base_url` not passed by orchestrator to containers | Fixed (Task 12.3-12.4) |
| R7 | MED | Docker image availability on desktop | Pull before execution |
| R9 | LOW | 188 vs 557 APKs — need correct CSV filter | Use `exp01_jca=True` filter |
| R10 | LOW | Desktop resources (CPU/RAM/disk) | Already validated — 64 CPUs, 128GB |
| R11 | MED | Docker entrypoint doesn't support `RV_SKIP_EXECUTION` | Override entrypoint in preprocessing compose |
