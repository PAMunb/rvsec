# Proposal: Docker-Based Calibration — Infrastructure and Execution Campaign

**GitHub Issue**: #9
**Track**: Full SDD
**Branch**: `modules`

## Why

The calibration framework in rv-agent-validation tunes 24 parameters of the RVAgent exploration strategy across five phases (A through E), totaling ~306 hours of experiment execution. The original implementation used Python-level parallelism (Optuna `n_jobs=6` with thread-safe `EmulatorPool`), which broke on emulator crashes — killing all six workers and losing hours of work.

The infrastructure replacement is complete: two host-side scripts (`calibration_orchestrator.py`, `baseline_docker.py`) adopt the Docker container-level parallelism pattern proven in the rvsec-02 project, with 39 unit tests passing. Dead code removed per P3.

What remains is **running the actual calibration campaign** (~306 hours across Phases B-E) and applying the resulting optimal parameters to the codebase.

### Why SDD for an execution campaign

This is an unconventional use of SDD — we are using the artifact structure (proposal, design, tasks) not for code development but for **execution lifecycle management**. The justification:

1. **Duration and complexity**: ~12.8 days of continuous execution across 4 phases, each with inter-phase dependencies (Phase C needs BASELINE_MAX_ERRORS from Phase B, Phase D needs optimal macro params from Phase C, etc.).

2. **Code corrections during execution**: Bugs discovered during Phase B execution must be fixed (with TDD regression tests) before Phase C can start. The tasks.md structure supports dynamic task insertion for these corrections.

3. **Context window management**: Each future Claude Code session loads ONLY the relevant section of design.md for the current phase. The full runbook (~400 lines) never needs to be loaded at once — each phase section (~80 lines) is self-contained with copy-paste commands and verification procedures.

4. **Multi-machine workflow**: Code lives on the laptop, execution happens on the desktop. Git-committed SDD artifacts provide shared state between machines without relying on conversation history.

5. **Verifiable gates**: Each phase has explicit acceptance criteria (row counts, file existence, statistical thresholds) that must pass before the next phase starts. SDD tasks formalize these gates.

The alternative — running ~300 hours of experiments without structured tracking — risks losing context across the many sessions required, missing verification steps, and accumulating untracked code corrections.

## What Changes

### Infrastructure (COMPLETED — Tasks 1-11)

- **`scripts/calibration_orchestrator.py`** (~580 lines): Optuna ask/tell loop with Docker container parallelism for Phases C/D. Supports `--resume` with orphaned trial recovery.
- **`scripts/baseline_docker.py`** (~360 lines): Batch execution across N containers for Phases B/E. Round-robin APK splitting, auto-aggregation, `--generate-only` mode.
- **Dead code removed**: `optimizer.py`, `runner.py`, `emulator_pool.py` -> `backup/calibration_legacy/`
- **39 unit tests** in `tests/calibration/`
- **Optuna upgraded**: 3.5 -> 4.7.0

### Execution Campaign (Tasks 12-24)

- **Phase B (Baseline)**: 945 tasks, ~18.4h — establish BASELINE_MAX_ERRORS
- **Phase C (Macro calibration)**: 80 trials x 75 APKs, ~122h — tune 8 high-impact parameters
- **Phase D (Micro calibration)**: 100 trials x 75 APKs, ~160h — tune 16 fine-grained parameters (requires SGLang)
- **Phase E (Validation)**: 270 tasks, ~5.6h — validate on 30-APK holdout set
- **Parameter application**: Update `parameter_space.py` defaults and agent spec with optimal values

### Code Corrections (Dynamic)

When execution reveals bugs, correction tasks are inserted between existing tasks. Each correction follows TDD: write regression test, fix, verify. These tasks are numbered as sub-tasks (e.g., Task 15a, 15b) to preserve the original task numbering.

## Impact

### Affected Modules
- **rv-agent-validation**: `calibration/` subpackage (infrastructure already done), `parameter_space.py` (after Phase D — default value updates)

### Affected Specs
- **agent** (`openspec/specs/agent/spec.md`): After Phase D, the calibrated parameter defaults need a delta spec update. This is tracked as Task 23 and will be an FF SDD change.

### Dependencies
- Docker image `phtcosta/rvandroid:0.8.0` (built in resume-docker change)
- Desktop machine with 64 CPUs, 128GB RAM, KVM
- SGLang server at `192.168.0.36:30000` (Phase D only)
- `calibration_dataset_v2/` with 105 instrumented APKs + static analysis files

### Related FRs/NFRs
- **FR21**: RVAgent exploration — parameter calibration tunes the exploration strategy
- **NFR05**: Reproducibility — Optuna SQLite persistence, deterministic seeds, compose file archival
- **NFR07**: Performance — container-level parallelism for throughput
