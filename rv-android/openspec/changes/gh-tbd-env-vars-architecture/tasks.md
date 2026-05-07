# Tasks — Env-Var Resolution Architecture

> Follow-up change for the gh55 gambiarra (`gh55-env-purity-avd-api30/tasks.md §9`). Read `proposal.md` and `design.md` here first, then `gh55/design.md` "Known Limitations" section.

## 1. Pre-work

- [ ] 1.1 File a GitHub issue describing this change; capture the issue number and rename the directory `gh-tbd-env-vars-architecture/` → `gh<N>-env-vars-architecture/` and update the proposal header.
- [ ] 1.2 Verify gh55 is fully archived (no stale `openspec/changes/gh55-*/` outside `archive/`).
- [ ] 1.3 Read `gh55/design.md` "Known Limitations (Gambiarra)" section.

## 2. Spike — choose between option C and D (~2h)

- [ ] 2.1 Create a sandbox script `scripts/spikes/env_resolution_spike.py` (or a `tests/spikes/` test file) implementing both options against a toy config with three fields: `tools: list[str]`, `timeout: int`, `pydantic: bool`.
- [ ] 2.2 Verify list parsing: `RV_TOOLS=ape,fastbot` resolves to `["ape", "fastbot"]` under both options.
- [ ] 2.3 Verify CLI override: `RV_TIMEOUTS=180` + `--timeout 60` resolves to `60` under both options.
- [ ] 2.4 Verify `extra="forbid"` semantics: `RV_BOGUS=x` is rejected under both options.
- [ ] 2.5 Verify standalone module path: invoking the toy script directly with env set behaves identically.
- [ ] 2.6 Document spike outcome in `design.md` under a new "Spike results" section. Pick C or D. If a blocker for D, document it explicitly.
- [ ] 2.7 If D is chosen, confirm `pydantic-settings` is already a workspace dep (`pyproject.toml`); add it if not.

## 3. Implement chosen mechanism in rv-android-core

If option C:
- [ ] 3a.1 Create `modules/rv-android-core/src/rv_android_core/config/env_loader.py` with `load_env_config(allow_list)`.
- [ ] 3a.2 Add unit tests in `modules/rv-android-core/tests/config/test_env_loader.py`.

If option D:
- [ ] 3b.1 Decide whether to expose a shared `BaseRVSettings(BaseSettings)` base in `rv-android-core` (with `env_prefix="RV_"`, `extra="forbid"`, `case_sensitive=True`) or have each L5 config configure `SettingsConfigDict` independently. Recommend the shared base.
- [ ] 3b.2 If shared base: create `modules/rv-android-core/src/rv_android_core/config/settings_base.py`.
- [ ] 3b.3 Add unit tests verifying base behavior (extra="forbid", env_prefix applied, case-sensitive).

## 4. Migrate rv-experiment (replace gh55 §9 gambiarra)

- [ ] 4.1 Backup current `rv-experiment/__main__.py` and `config.py` to `backup/<date>_env_vars_architecture/`.
- [ ] 4.2 Delete the 17 `envvar=ENV_X` entries from `@click.option` decorators.
- [ ] 4.3 Delete the 3 `os.environ.get(ENV_*)` reads in `ExperimentConfig.__post_init__` (`RV_HUMANOID_URL`, `RV_SA_TIMEOUT`, `RV_JVM_MEMORY`).
- [ ] 4.4 Migrate `ExperimentConfig` to the chosen mechanism.
- [ ] 4.5 Update merge logic in `__main__.py`: build config from `{**env, **vars(args)}` (option C) or pass CLI as kwargs to BaseSettings (option D).
- [ ] 4.6 Update unit tests; remove tests that asserted the old gambiarra (they will fail and that's correct).

## 5. Migrate argparse modules (close the standalone gap)

- [ ] 5.1 `rv-platform.__main__`: add env reading via chosen mechanism. Add integration test for standalone env path.
- [ ] 5.2 `rv-static-analysis.__main__`: same pattern. Verify `RV_SA_TIMEOUT` works standalone.
- [ ] 5.3 `rv-instrumentation-ajc.__main__`: same pattern. Verify `RV_JVM_MEMORY` works standalone.
- [ ] 5.4 `rv-monitor-generator.__main__`: same pattern.

## 6. Audit Click modules

- [ ] 6.1 `rv-agent.cli.main`: list any existing `envvar=` declarations; migrate to chosen mechanism for consistency.

## 7. Lint extension

- [ ] 7.1 Extend `scripts/check_env_vars_drift.py` to detect `ENV_*` constants without a matching field/binding under the chosen mechanism (option D: a `BaseSettings` field with the corresponding name; option C: an entry in some entry point's allow-list).
- [ ] 7.2 Add a planted-violation test in `tests/lint/test_env_vars_drift.py`.

## 8. Integration tests

- [ ] 8.1 Per-module precedence test: CLI > env > default × 6 entry points × 3 representative flags.
- [ ] 8.2 Standalone-execution test: `RV_TOOLS=ape RV_TIMEOUTS=180 uv run rv-platform run --apks-dir tests/fixtures/ --skip-execution`, assert resolved config.
- [ ] 8.3 Re-run gh55 smoke 6.5 inside container with new mechanism; assert behavioral parity (same tool selection, same timeouts).

## 9. Verification

- [ ] 9.1 `/rv-verify` clean (tests, lint, types).
- [ ] 9.2 `openspec validate --change "<this-change-name>"` clean.
- [ ] 9.3 Smoke compose runs: `jca-compare`, `comparacao` representative compose files with `--skip-execution`.

## 10. Archive

- [ ] 10.1 `/opsx:archive` (with sync if specs were modified, or `--skip-specs` if not).
- [ ] 10.2 Update `gh55/design.md` "Known Limitations" section with a backlink to this archived change.
- [ ] 10.3 Confirm gh55 §9 envvar= entries are absent from `rv-experiment/__main__.py` post-archive.
