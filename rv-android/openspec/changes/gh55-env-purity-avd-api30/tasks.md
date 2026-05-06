<!-- Subagent dispatch hints:
     This change touches ~30 files but in 4 cleanly independent task groups.
     Sequential execution recommended (each group leaves repo in a consistent state).
     Critical path: 1 → 2 → 3 → 4 → 5 → 6.
     Groups 5 (AVD) and 4 (entrypoint) are independent of each other once 1-3 done. -->

## 1. Foundation: ENV_* registry and dead-code cleanup

- [x] 1.1 Backup existing `modules/rv-android-core/src/rv_android_core/constants.py` to `backup/2026-05-06_env_var_cleanup/constants.py.old`
- [x] 1.2 Add 16 missing `ENV_*` constants to `constants.py` (verifies INV-CORE-30): user-facing (13) — `RV_APKS_DIR`, `RV_SPEC_SET`, `RV_SKIP_EXECUTION`, `RV_NO_QUARANTINE`, `RV_DEVICE_PORT`, `RV_INSTRUMENTATION_VARIANT`, `RV_APKS_FILTER`, `RV_EXPERIMENT_NAME`, `RV_RESUME_DIR`, `RV_SA_DIR`, `RV_SA_TIMEOUT`, `RV_JVM_MEMORY`, `RV_PYDANTIC`; plus L1 cross-layer infra (3) — `RV_PYDANTIC_STRICT`, `RV_PYDANTIC_LOG` (alive at `validation/config.py:77,82`), `TOOLS_DIR` (alive at `jar_resolver.py:300`; not RV_*-prefixed but listed here so the registry covers all canonical L1 readers per design.md D10).
- [x] 1.3 Remove 4 dead constants from `constants.py`: `ENV_MEMORY_FILE`, `ENV_RVANDROID_URL`, `ENV_SKIP_EXPERIMENT`, `ENV_JCA_SPEC`
- [x] 1.4 Verify cleanup: no remaining import of removed `ENV_*` constants in `modules/` or `scripts/` (grep clean). RV_* string-literal references in compose files / Dockerfile / docker-entrypoint / `scripts/calibration_orchestrator.py` are scheduled for migration in groups 5/6 (compose 5.4a, Dockerfile 6.x, entrypoint 5.3, calibration_orchestrator deferred to follow-up).
- [x] 1.5 Add unit test `modules/rv-android-core/tests/test_constants_registry.py` (NEW; verifies INV-CORE-30) — 5 tests covering registry well-formedness, dead-removal, and L1 infra family presence.
- [x] 1.6 Run `/rv-test-run rv-android-core` — 871 passed

## 2. Lint: env-vars drift checker

- [x] 2.1 Create `scripts/check_env_vars_drift.py` (NEW; verifies INV-CORE-31, INV-EXP-30) — 5 read forms covered + 2 cross-checks (RV_* docs ↔ registry).
- [x] 2.2 Add planted-violation fixture in `tests/lint/test_env_vars_drift.py` (NEW) — 10 tests covering all 5 forms + `patch.dict` non-violation + L1 allow-list.
- [ ] 2.3 Wire `scripts/check_env_vars_drift.py` into CI workflow — DEFERRED: `.github/workflows/` does not exist in this repo (no GitHub Actions setup); lint runs via `uv run python scripts/check_env_vars_drift.py` and via `tests/lint/` pytest. CI integration is a separate concern (issue follow-up).
- [x] 2.4 Run the lint locally; 33 violations detected as expected — all addressable in groups 3/4/4bis/7. (Group 7 README/.env.example doc tasks will close the remaining 17 cross-check (c) flags.)

## 3. Migrate string-literal env reads to `ENV_*` constants

- [x] 3.1 Migrated `RV_SA_TIMEOUT`/`RV_JVM_MEMORY` literals at `modules/rv-experiment/src/rv_experiment/config.py:745,748` to `ENV_SA_TIMEOUT`/`ENV_JVM_MEMORY` constants. Plumbed CLI flags `--analysis-timeout` / `--jvm-memory` through `__main__.py` and added `analysis_timeout` / `jvm_memory` fields to `ExperimentConfig` (precedence CLI > env > default).
- [x] 3.1a Migrated `RV_PYDANTIC*` literals at `validation/config.py:72,77,82` to `ENV_PYDANTIC`, `ENV_PYDANTIC_STRICT`, `ENV_PYDANTIC_LOG` constants (L1 cross-layer infra exception per INV-EXP-30).
- [x] 3.2 Lint sweep: drift checker confirms only the `os.environ.get("RV_*")` reads addressed by Group 4/4bis remain (8 violations down from 33; the remaining are the 6 cross-check-(c) doc gaps + group 4/4bis migrations).
- [x] 3.3 Applied `model_config = ConfigDict(extra="forbid")` to `ExperimentConfig` at the class body (verifies INV-CORE-32; before: only inherited).
- [x] 3.4 Applied `model_config = ConfigDict(extra="forbid")` to `PlatformConfig` at the class body (verifies INV-CORE-32).
- [x] 3.5 Added unit test `modules/rv-android-core/tests/test_top_level_configs_strict.py` (NEW; 4 tests passing; AST + ValidationError coverage).
- [x] 3.6 Added unit test `modules/rv-experiment/tests/test_config_precedence.py` (NEW; 6 tests passing; CLI > env > default for both `analysis_timeout` and `jvm_memory`).
- [x] 3.7 Ran `scripts/check_env_vars_drift.py` — Group 3 violations resolved (5 fixed).
- [x] 3.8 Ran `/rv-test-run rv-android-core` (875 passed), `/rv-test-run rv-experiment` (184 passed), `/rv-test-run rv-platform` (211 passed, 1 skipped).

## 4. Layer Purity: migrate `RV_HUMANOID_URL` from L2 to L5

- [x] 4.1 Backed up `humanoid/tool.py` to `backup/2026-05-06_env_var_cleanup/humanoid_tool.py.old`.
- [x] 4.2 Migrated `humanoid/tool.py`: (a) `"humanoid_url": "127.0.0.1:50405"` added to `get_variants()["default"]`; (b) `os.environ.get(ENV_HUMANOID_URL)` fallback removed; (c) `ENV_HUMANOID_URL` import removed; (d) `configure(config)` reads `config["humanoid_url"]` (factory-merged dict guarantees presence).
- [x] 4.3 L5 injection added in `rv_experiment/__main__.py:_create_experiment_config_from_cli`: when `RV_HUMANOID_URL` is set in `os.environ`, it's injected into `ToolConfig.parameters["humanoid_url"]` for any `humanoid` tool entry. Variant default carries through when env is unset.
- [x] 4.4 Confirmed `rv_tools.registry.factory.ToolFactory.create_tool` merges only `{**variant_defaults, **tool_config.parameters}` (no env reads at L2 — verified by test 4.6).
- [x] 4.5 Updated `modules/rv-tools/tests/builtin/test_humanoid_tool.py`: 11 tests in `TestConfigure` covering variant-default fallback, L5 override, no-env-fallback, KeyError defensive case. 34 tests passing.
- [x] 4.6 Added `modules/rv-tools/tests/registry/test_tool_factory_parameters_channel.py` (NEW; 5 tests passing) — including a sentinel-env test asserting no leakage.
- [x] 4.7 Lint scope grep over `rv-tools/builtin/`, `aperv-tool/src/`, `rvagent-tool/src/` → 0 hits (rvagent-tool was already clean).
- [x] 4.8 Migrated `ape/tool.py:278`, `droidmate/tool.py:113`, `fastbot/tool.py:401` — TOOLS_DIR-based paths now added by `JarResolver._build_search_paths` at L1 (gh55 D10). Tool code passes only module-dir + standard install paths.
- [x] 4.8a Migrated `aperv-tool/tool.py:329,352,355`: removed `APERV_LLM_BASE_URL`, `RVSEC_HOME`, `TOOLS_DIR` reads. LLM URL flows through `parameters["llm_url"]` from L5; JAR resolution flows through `JarResolver`. Tests updated (3 rewritten + 38 unchanged passing).
- [x] 4.8b `modules/rvagent-tool/src/` confirmed clean (0 env reads).
- [x] 4.9 Lint rule already covers all three plugin trees (verified earlier in Group 2).
- [x] 4.10 Ran tests: rv-tools 394 passed, aperv-tool 41 passed, rv-experiment 184 passed, rv-android-core 875 passed. `jar_resolver.py:280,300` migrated to `ENV_RVSEC_HOME`/`ENV_TOOLS_DIR` constants (still L1 single-reader per D10).

### 4bis. Instrumentation L3 env hardening (per design.md D9)

- [x] 4bis.1 Replaced `_os_env()` with `_build_subprocess_env(extras)` (design.md D9) — forwards only `{PATH, HOME, JAVA_HOME, ANDROID_HOME, RVSEC_HOME}` plus caller extras. Call site updated at line 457.
- [x] 4bis.2 `dexlib_instrumentation.py` literal `"RVSEC_HOME"` replaced with `ENV_RVSEC_HOME` constant (imported from `rv_android_core.constants`).
- [x] 4bis.3 `ajc_instrumentation.py:419` literal `"RVSEC_HOME"` replaced with `constants.ENV_RVSEC_HOME`. `config.py:397` literal `"ANDROID_HOME"` replaced with `constants.ENV_ANDROID_HOME` (already imported in this module).
- [x] 4bis.4 `grep -rnE 'dict\(os\.environ|os\.environ\.copy' modules/` outside rv-experiment → 0 production hits (test files and docstrings excluded by lint logic).
- [x] 4bis.5 Tests passing: rv-instrumentation-dexlib2 16, rv-instrumentation-ajc 78.

## 5. Docker entry-point refactor (allow-list validation)

- [x] 5.1 Backed up `docker-entrypoint.sh` (150 lines) to `backup/2026-05-06_env_var_cleanup/docker-entrypoint.sh.old`.
- [x] 5.2 Created `docker/rvandroid/scripts/validate_env_vars.sh` (NEW, 89 lines): parses `constants.py` via Python, allow-lists L1 infra (RV_PYDANTIC*, RVSEC_HOME, ANDROID_HOME, TOOLS_DIR), exits 64 on unknown with migration hints for removed vars (RV_JCA_SPEC → RV_SPEC_SET; RV_MEMORY_FILE / RV_RVANDROID_URL / RV_SKIP_EXPERIMENT → "removed").
- [x] 5.3 Rewrote `docker-entrypoint.sh` (150 → 65 lines): allow-list validation → RV_DELAY → socat bridge → SA file copy → `exec uv run rv-experiment run` (no env→flag translation). Bash/shell shortcut bypasses validation (operator debugging).
- [x] 5.4 Audited all 37 `docker-compose.*.yml`. Vars used: 17 unique RV_* — all in registry. No removed-var references in any compose file (verified by grep).
- [x] 5.4a Migrated 25 compose files in `docker/` (mapping form `RV_JCA_SPEC: "true"` → `RV_SPEC_SET: "jca"`) plus 1 in `docker/docker-compose.yml` (list form `- RV_JCA_SPEC=true` → `- RV_SPEC_SET=jca`) plus 2 in `docker/data/gh26_experiment/`. Also migrated `docker/rvandroid_dev/Dockerfile:84` and `scripts/calibration_orchestrator.py:215`. `grep -rn 'RV_JCA_SPEC' docker/ scripts/ modules/` now returns only the validator's hint message and Dockerfile's comment.
- [x] 5.5 Added `tests/integration/test_validate_env_vars.bats` (NEW; 9 cases): empty env, known vars, unknown var (exit 64), removed RV_JCA_SPEC + hint, removed RV_MEMORY_FILE + hint, L1 infra family, RV_DELAY allow-list, RV_ANDROID_CONSTANTS_FILE self-allow-list, missing constants.py error. Manual smoke confirms 5/5 happy path + error cases.
- [ ] 5.6 Smoke matrix — DEFERRED: requires Docker daemon and rebuilt image. Stub for execution: `docker compose -f docker-compose.{jca-compare,comparacao,instrument-jca-ajc,parallel,test}.yml run --rm rvandroid bash -c 'echo allow-list passed; exit 0'`. Manual integration smoke (5.5) covers the validator alone.
- [x] 5.7 `/rv-verify rv-experiment` — 184 passed.

## 6. AVD bump to API 30 x86_64

- [x] 6.1 Backed up `docker/android/Dockerfile` to `backup/2026-05-06_env_var_cleanup/android.Dockerfile.old`.
- [x] 6.2 Updated `docker/android/Dockerfile`: `ARG API_LEVEL=30`, `ARG ARCHITECTURE=x86_64`, `IMG_TYPE=google_apis` unchanged. Rewrote the gh50 §17 historical comment block per P4 — current-state only, references the gh55 6.4a Docker boot smoke as the pre-merge gate.
- [x] 6.3 Updated `scripts/run_emulator.sh`: `EMULATOR_NAME="RVSec"`. Removed the OLD/NEW commented-out blocks. Added flag-by-flag rationale for the canonical launch (writable-system, wipe-data, no-boot-anim, noaudio, no-snapshot-save, delay-adb).
- [x] 6.4 Rebuilt the entire image chain via `docker/build_all.sh` (6 images: rvsec_base 0.8.0 → rvsec_android 0.8.0 → rvandroid_tools 0.8.0 → rvandroid 0.8.0 → ares latest → qtesting latest). Tag preserved (`phtcosta/rvandroid:0.8.0`); content differentiation via image creation timestamp. Pre-flight fixes during build: (a) `docker/base/Dockerfile` Maven URL bumped 3.9.14 → 3.9.15 (3.9.14 dropped from `dlcdn`; `archive.apache.org` unreachable from Docker network namespace in this environment); (b) all 4 `docker/{base,android,tools,rvandroid}/build.sh` scripts patched to use `docker build -t IMAGE:VERSION -t IMAGE:latest` directly (the legacy `docker images | awk '{print $3}'` ID extraction broke under Docker 29.4 because the column layout changed — `$3` is now `DISK USAGE`).
- [x] 6.4a **Docker-container boot smoke** PASS: 3/3 consecutive BOOT_COMPLETED runs at 34s / 31s / 33s wall-clock (all <90s budget). Cold-boot via `start-emulator.sh` inside `phtcosta/rvandroid:0.8.0` with `--device /dev/kvm`. Confirms the API 30 x86_64 emulator boots inside the container with the existing default config (no `-writable-system` multi-step required) — the gh50 §17 OverlayFS diagnosis is empirically refuted in the Docker-container scenario.
- [ ] 6.5 Smoke matrix gate (H4): run `rv-experiment run` with 5 APKs × 5 tools (Monkey, ape, aperv:sata_mop, droidbot, fastbot) × 60min timeout against the rebuilt image; record results. **PAUSED for configuration review before execution** (per user direction).
- [ ] 6.6 Larger AVD sample gate: run `scripts/investigate_avd_compat.sh --sample 100 phase2 ...` on both datasets; confirm 0 regressions trend.
- [ ] 6.7 Update `docs/20260506_plano_env.md` Section 10 with larger-sample data after 6.6.
- [ ] 6.8 If gates 6.5 + 6.6 pass: **no tag bump** — the existing `phtcosta/rvandroid:0.8.0` is updated in place. If any tool fails on API 30, document and decide per-tool fallback (escalate as separate change if needed); rollback path is a rebuild with `--build-arg API_LEVEL=29 --build-arg ARCHITECTURE=x86`.

## 7. Documentation: canonical surface

- [x] 7.1 Created `.env.example` at repo root: 28 ENV_* names categorized (Inputs, Execution, Skip flags, Static analysis, Tool overrides, Developer toggles, L1 cross-layer infra). Each entry includes the CLI flag and a one-line rationale. Default values match Pydantic defaults.
- [x] 7.2 Updated `README.md` "Environment Variables" table to the canonical 28-var form (Name, CLI flag, Default, Read by, Description). Added "Removed by gh55" footnote with migration hints.
- [x] 7.3a Created `docs/adr/` directory + `docs/adr/README.md` documenting the ADR numbering convention (`NNNN-kebab-case-title.md`, sequential, never reused) and lifecycle (immutable once Accepted; supersede via new ADR).
- [x] 7.3 Created `docs/adr/0001-env-var-pattern.md` (Accepted, gh55, 2026-05-06): full Context (drift, silent failures, Layer Purity violations, dead code), Decision (registry + Layer Purity + lint + allow-list + strict validation + variant defaults), Alternatives considered (8 options with trade-offs), Consequences (positive/negative/neutral), Adding-a-new-env-var procedure, References to all artifacts.
- [x] 7.4 Added §14 "Adding a new environment variable" to `docs/WORKFLOW.md` — 7-step procedure aligned with the ADR + lint contract.
- [x] 7.5 Added "Layer Purity for Environment Variables (gh55)" subsection under `docs/rv_android_architecture.md` §9 NFR Support — table of the 6 L1 cross-layer infra readers + reference to the ADR.
- [x] 7.6 Updated `modules/rv-tools/CLAUDE.md`: humanoid stateless-inference note in the tools table + new "Variant-default pattern" subsection with canonical example + ADR reference.
- [ ] 7.7 Run `/rv-docs-sync` — DEFERRED: docs already synced manually (this commit). Follow-up sweep in Group 8 if needed.

## 8. Final integration and verification

- [ ] 8.1 Run `scripts/check_env_vars_drift.py` end-to-end; assert 0 hits across all 3 rules
- [ ] 8.2 Run `/rv-qa-lint-fix rv-android-core rv-experiment rv-platform rv-tools`
- [ ] 8.3 Run `/rv-verify rv-android-core` and `/rv-verify rv-experiment` and `/rv-verify rv-platform` and `/rv-verify rv-tools`
- [ ] 8.4 Run full per-module test suite per CLAUDE.md instructions (each module isolated with `--import-mode=importlib`)
- [ ] 8.5 Invoke `/rv-code-reviewer` via Skill tool
- [ ] 8.6 Address review feedback (commit fixes; do not amend)
- [ ] 8.7 Run `/opsx:verify` to confirm implementation matches spec deltas
- [ ] 8.8 Update PR/CHANGELOG noting BREAKING removed env vars (`RV_MEMORY_FILE`, `RV_RVANDROID_URL`, `RV_SKIP_EXPERIMENT`, `RV_JCA_SPEC`) and the AVD bump (`API_LEVEL=30`, `ARCHITECTURE=x86_64`)
