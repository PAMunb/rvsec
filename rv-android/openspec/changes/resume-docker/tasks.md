## 1. Resume CLI (rv-experiment)

- [ ] 1.1 Add `--resume-dir` Click option to the `run` command in `modules/rv-experiment/src/rv_experiment/__main__.py`. Type: `click.Path(exists=True)`, default `None`. Pass through to `_create_experiment_config_from_cli()`.
- [ ] 1.2 Make `--name` resume-aware in `_create_experiment_config_from_cli()`. When `--name` is provided and `results/<name>/tasks.json` exists, auto-set `skip_monitors=True`, `skip_instrument=True`, `skip_static=True`, and log "Resuming experiment '<name>' — auto-skipping pre-processing".
- [ ] 1.3 Implement `--resume-dir` handling in `_create_experiment_config_from_cli()`. When provided: use as `experiment_dir`, auto-set all skip flags, log "Resuming experiment from <path>". `--resume-dir` overrides `--name` if both are provided. The `--apks-dir` argument is NOT auto-detected — the user must provide it explicitly (or the default applies).

## 2. Platform Resume Wiring (rv-platform)

- [ ] 2.1 In `Platform.run()` (`modules/rv-platform/src/rv_platform/platform.py`), after `_generate_tasks()`: create `ExperimentMetadata` with `experiment_id=self.config.results_dir`, compute `config_checksum` from `PlatformConfig`, set `start_time` to current ISO timestamp, and call `self.task_storage.set_experiment_metadata(metadata)`.
- [ ] 2.2 In `_skip_completed_tasks()`, after confirming completed tasks exist: call `self.task_storage.check_continuation_compatibility(config_dict)`. If it returns `False`, log warning "Config changed since last run — resuming anyway". Keep existing skip logic unchanged.

## 3. Dead Code Removal (rv-experiment)

- [ ] 3.0 Backup `modules/rv-experiment/src/rv_experiment/config.py` to `backup/config.py.bak` before any modifications. This preserves the original for thesis records and enables recovery.
- [ ] 3.1 Delete `get_artifact_validation_config()` method entirely from `config.py` (references undefined `self.artifact_reuse_enabled` and `self.phase_control`; crashes at runtime). No adapter, no deprecation wrapper — complete removal.
- [ ] 3.2 Delete `load_from_status()` method entirely from `config.py` (dead code, never called from any entry point). No compatibility shim — the new resume architecture uses a fundamentally different approach (CLI detection + platform task skipping).
- [ ] 3.3 Grep the entire codebase to confirm zero references to `get_artifact_validation_config` and `load_from_status` (expected: none). Document grep results in the commit message.

## 4. Docker Entry Point

- [ ] 4.1 Create `docker/rvandroid/docker-entrypoint.sh` translating CLI env vars to `rv-experiment run` arguments: RV_TOOLS (→ --tools), RV_TIMEOUTS (→ --timeout), RV_REPETITIONS (→ --repetitions), RV_APKS_DIR (→ --apks-dir), RV_NO_WINDOW (→ --no-window/--window), RV_SPEC_SET (→ --specification-set), RV_JCA_SPEC (→ --specification-set jca/generic, legacy compat), RV_SKIP_MONITORS (→ --skip-monitors), RV_SKIP_INSTRUMENT (→ --skip-instrument), RV_SKIP_STATIC_ANALYSIS (→ --skip-static), RV_DEVICE_PORT (→ --device-port), RV_APKS_FILTER (→ --apks-filter), RV_EXPERIMENT_NAME (→ --name), RV_RESUME_DIR (→ --resume-dir), RV_DEBUG (→ --log-level DEBUG). Include RV_DELAY (sleep before exec). Pass-through vars (RVSEC_HOME, ANDROID_HOME, TOOLS_DIR, RV_HUMANOID_URL, RVAGENT_*, RV_PYDANTIC) are NOT translated — they are read directly by Python modules. Support `bash`/`shell` mode for interactive access. Echo generated command.

## 5. Docker Files

- [ ] 5.1 Update `docker/rvandroid/Dockerfile`: add ENTRYPOINT (`/opt/docker-entrypoint.sh`), CMD (`["run"]`), ENV defaults (RV_TOOLS, RV_TIMEOUTS, RV_REPETITIONS, RV_NO_WINDOW, RV_JCA_SPEC), VOLUME declarations (apks, out, results), and COPY + chmod for the entrypoint script.
- [ ] 5.2 Create `docker/rvandroid_dev/Dockerfile`: based on `phtcosta/rvandroid_tools:0.8.0`, COPY local Poetry files and module sources, run `poetry install`, COPY entrypoint script. Build context is the repo root.
- [ ] 5.3 Create `docker/docker-compose.parallel.yml` with YAML anchors (`x-rvandroid` base), Humanoid service with healthcheck, and rv01/rv02 service definitions with per-container volumes and experiment names. Support env var overrides (BASE_DIR, RV_TOOLS, RV_TIMEOUTS, CPUS, MEMORY).
- [ ] 5.4 Update `docker/docker-compose.yml`: add rvandroid service with env vars, volumes (apks, out, results), device `/dev/kvm`, resource limits, and Humanoid dependency.
- [ ] 5.5 Clean `docker/tools/Dockerfile`: remove all commented-out legacy code (~80 lines of Sapienz, Stoat, Humanoid, pyflann, legacy env vars). Keep only DroidBot installation.
- [ ] 5.6 Update `docker/build_all.sh`: ensure all 4 image layers are built in order (base, android, tools, rvandroid) with error handling.

## 6. Verification

- [ ] 6.1 Run existing tests for rv-experiment and rv-platform modules to confirm no regressions from resume wiring and dead code removal.
- [ ] 6.2 Manual resume smoke test: run `rv-experiment run --tools monkey --apks-dir ./apks_examples --timeout 60 --name test_resume --no-window`, interrupt with Ctrl+C after ~2 tasks, re-run same command, verify "Resume: skipped N already-completed tasks" in logs.
