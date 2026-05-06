<!-- Subagent dispatch hints:
     This change touches ~30 files but in 4 cleanly independent task groups.
     Sequential execution recommended (each group leaves repo in a consistent state).
     Critical path: 1 → 2 → 3 → 4 → 5 → 6.
     Groups 5 (AVD) and 4 (entrypoint) are independent of each other once 1-3 done. -->

## 1. Foundation: ENV_* registry and dead-code cleanup

- [ ] 1.1 Backup existing `modules/rv-android-core/src/rv_android_core/constants.py` to `backup/2026-05-06_env_var_cleanup/constants.py.old`
- [ ] 1.2 Add 16 missing `ENV_*` constants to `constants.py` (verifies INV-CORE-30): user-facing (13) — `RV_APKS_DIR`, `RV_SPEC_SET`, `RV_SKIP_EXECUTION`, `RV_NO_QUARANTINE`, `RV_DEVICE_PORT`, `RV_INSTRUMENTATION_VARIANT`, `RV_APKS_FILTER`, `RV_EXPERIMENT_NAME`, `RV_RESUME_DIR`, `RV_SA_DIR`, `RV_SA_TIMEOUT`, `RV_JVM_MEMORY`, `RV_PYDANTIC`; plus L1 cross-layer infra (3) — `RV_PYDANTIC_STRICT`, `RV_PYDANTIC_LOG` (alive at `validation/config.py:77,82`), `TOOLS_DIR` (alive at `jar_resolver.py:300`; not RV_*-prefixed but listed here so the registry covers all canonical L1 readers per design.md D10).
- [ ] 1.3 Remove 4 dead constants from `constants.py`: `ENV_MEMORY_FILE`, `ENV_RVANDROID_URL`, `ENV_SKIP_EXPERIMENT`, `ENV_JCA_SPEC`
- [ ] 1.4 Verify cleanup: `grep -rn "RV_MEMORY_FILE\|RV_RVANDROID_URL\|RV_SKIP_EXPERIMENT\|RV_JCA_SPEC" modules/ docker/ scripts/ docs/` returns 0 hits
- [ ] 1.5 Add unit test `modules/rv-android-core/tests/test_constants_registry.py` (NEW; verifies INV-CORE-30) asserting every `ENV_*` constant matches the regex `^(RV_[A-Z_]+|RVSEC_HOME|ANDROID_HOME|TOOLS_DIR)$`
- [ ] 1.6 Run `/rv-test-run rv-android-core`

## 2. Lint: env-vars drift checker

- [ ] 2.1 Create `scripts/check_env_vars_drift.py` (NEW; verifies INV-CORE-31, INV-EXP-30) performing three cross-checks: (a) every read form covered — `os\.environ\.get\("RV_`, `os\.environ\["RV_`, `os\.getenv\("RV_` — references an `ENV_*` symbol, AND `dict\(os\.environ` / `os\.environ\.copy\(` are flagged outside `modules/rv-experiment/`; (b) every `RV_*` in README and `.env.example` is in the registry; (c) every `ENV_*` constant is documented in README / `.env.example`.
- [ ] 2.2 Add planted-violation fixture in `tests/lint/test_env_vars_drift.py` (NEW) covering all five forms — one fixture per form: `os.environ.get("RV_X")`, `os.environ["RV_X"]`, `os.getenv("RV_X")`, `dict(os.environ)`, `os.environ.copy()`. The test MUST assert lint fails for each, AND that L1 cross-layer infra family reads (`RV_PYDANTIC`, `RV_PYDANTIC_STRICT`, `RV_PYDANTIC_LOG`, `RVSEC_HOME`, `ANDROID_HOME`) inside `rv-android-core/util/validation/` pass via allow-list.
- [ ] 2.3 Wire `scripts/check_env_vars_drift.py` into CI workflow (`.github/workflows/ci.yml`)
- [ ] 2.4 Run the lint locally; expect failures on existing string-literal reads (those are addressed in §3)

## 3. Migrate string-literal env reads to `ENV_*` constants

- [ ] 3.1 In `modules/rv-experiment/src/rv_experiment/config.py`, replace `os.environ.get("RV_SA_TIMEOUT")` (line 745) and `os.environ.get("RV_JVM_MEMORY")` (line 748) with `ENV_SA_TIMEOUT`/`ENV_JVM_MEMORY` constants imported from `rv_android_core.constants`
- [ ] 3.1a In `modules/rv-android-core/src/rv_android_core/util/validation/config.py`, replace `os.getenv("RV_PYDANTIC", ...)` (line 72), `os.getenv("RV_PYDANTIC_STRICT", ...)` (line 77), and `os.getenv("RV_PYDANTIC_LOG", ...)` (line 82) with `os.getenv(ENV_PYDANTIC, ...)`, `os.getenv(ENV_PYDANTIC_STRICT, ...)`, `os.getenv(ENV_PYDANTIC_LOG, ...)` (constants imported from same module's `constants.py`). These three reads remain at L1 — they are authorized cross-layer infra exceptions per INV-EXP-30.
- [ ] 3.2 Audit all files under `modules/` for `os.environ.get("RV_*")` and replace with constants. Save backups of any file with > 1 hit to `backup/2026-05-06_env_var_cleanup/<original_path>` before editing
- [ ] 3.3 Apply `model_config = ConfigDict(extra="forbid")` to `ExperimentConfig` (`modules/rv-experiment/src/rv_experiment/config.py`) — verifies INV-CORE-32 for the experiment top-level model
- [ ] 3.4 Apply `model_config = ConfigDict(extra="forbid")` to `PlatformConfig` (`modules/rv-platform/src/rv_platform/config/platform_config.py`) — verifies INV-CORE-32 for the platform top-level model
- [ ] 3.5 Add unit test `tests/test_top_level_configs_strict.py` (NEW; verifies INV-CORE-32 and the "Top-level config explicitly declares extra='forbid'" scenario in core/spec.md MODIFIED Pydantic Validation): (a) AST/string-match assertion that `ExperimentConfig` and `PlatformConfig` source contains `model_config = ConfigDict(extra="forbid")` at class body; (b) `ExperimentConfig(unknown_field="x")` raises `ValidationError`; (c) `PlatformConfig(unknown_field="x")` raises `ValidationError`
- [ ] 3.6 Add unit test `tests/test_config_precedence.py` (verifies INV-EXP-32): for `analysis_timeout` and `jvm_memory`, exercise three modes — env-only, CLI-flag-only, env+CLI (CLI wins). 6 cases total; assert resolved `ExperimentConfig` field matches expected precedence
- [ ] 3.7 Run `scripts/check_env_vars_drift.py` — expect pass on rule (a)
- [ ] 3.8 Run `/rv-test-run rv-experiment` and `/rv-test-run rv-platform`

## 4. Layer Purity: migrate `RV_HUMANOID_URL` from L2 to L5

- [ ] 4.1 Backup `modules/rv-tools/src/rv_tools/builtin/humanoid/tool.py` to `backup/2026-05-06_env_var_cleanup/`
- [ ] 4.2 In `modules/rv-tools/src/rv_tools/builtin/humanoid/tool.py`: (a) add `"humanoid_url": "127.0.0.1:50405"` to `get_variants()["default"]` (variant default — same pattern as ARES `"docker_image"` at `ares/tool.py:79`); (b) remove the `or os.environ.get(ENV_HUMANOID_URL) or "127.0.0.1:50405"` fallback chain at lines 87-91; (c) remove the `from rv_android_core.constants import ENV_HUMANOID_URL` import at line 13; (d) `configure(config)` reads `self.url = config["humanoid_url"]` (key always present after factory merge `{**variant_defaults, **tool_config.parameters}`).
- [ ] 4.3 In `modules/rv-experiment/src/rv_experiment/__main__.py` (canonical resolution site) plus `ConfigurationFactory` translation (when populating `PlatformConfig.tools`), resolve `RV_HUMANOID_URL` at L5 and inject into `ToolConfig.parameters["humanoid_url"]` for any `tool_configs` entry with `name="humanoid"`. Decision: resolution lives in `__main__.py`; `ConfigurationFactory` only forwards. Document this in design.md D7 if not already.
- [ ] 4.4 In `rv_tools.registry.factory.ToolFactory.create_tool(tool_config)` (verifies INV-TOOL-25 — see platform/spec.md note: factory lives in rv-tools L2, not rv-platform L4), confirm the only L2 input is the merge of variant defaults and `tool_config.parameters` — no `os.environ` reads, no config-file reads, no other sources
- [ ] 4.5 Update `modules/rv-tools/tests/builtin/test_humanoid_tool.py` (verifies INV-TOOL-21 + new variant-default behavior): replace env-var mocks with `parameters` dict; add (a) scenario where `parameters={}` exercises the variant default `humanoid_url == "127.0.0.1:50405"`; (b) scenario where `parameters={"humanoid_url": "http://humanoid:50405"}` overrides the variant default; (c) scenario where `RV_HUMANOID_URL` is set in `os.environ` but `parameters={}` — expect tool to use the variant default (env is NOT consulted at L2).
- [ ] 4.6 Add unit test `modules/rv-tools/tests/registry/test_tool_factory_parameters_channel.py` (NEW; verifies INV-TOOL-25): patch `os.environ` and inspect `AbstractTool.configure()` calls — assert config dict is exactly `{**variant_defaults, **tool_config.parameters}`, never sourced from environment or other channels. (The test lives in rv-tools because that is where the factory lives.)
- [ ] 4.7 Run `grep -rnE 'os\.(environ|getenv)' modules/rv-tools/src/rv_tools/builtin/ modules/aperv-tool/src/ modules/rvagent-tool/src/` (verifies INV-TOOL-20) — assert 0 hits across all three plugin trees
- [ ] 4.8 Migrate `TOOLS_DIR` reads in `modules/rv-tools/src/rv_tools/builtin/{ape,droidmate,fastbot}/tool.py` per design.md D10: replace `os.environ.get("TOOLS_DIR", "")` (ape:278, droidmate:113, fastbot:401) with `JarResolver.resolve_jar(...)` (existing API in `rv-android-core/util/jar_resolver.py`) — the resolver itself reads `TOOLS_DIR` once at L1; tool plugins call the resolver and never see the env var. Add tests asserting tool init no longer reads env.
- [ ] 4.8a Migrate the three reads in `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py`: (a) `APERV_LLM_BASE_URL` (line 329) → `parameters["llm_base_url"]` (variant default `"http://localhost:8000"` per ARES/QTesting pattern D8); (b) `RVSEC_HOME` (line 352) → call `JarResolver.resolve_jar(...)` instead of building paths from RVSEC_HOME directly (the resolver already handles RVSEC_HOME at L1); (c) `TOOLS_DIR` (line 355) → likewise routed through `JarResolver.resolve_jar(...)`. Remove all three `os.environ.get` calls from `aperv-tool/tool.py`.
- [ ] 4.8b Confirm `modules/rvagent-tool/src/` has 0 env reads today (`grep -rnE 'os\.(environ|getenv)' modules/rvagent-tool/src/` empty); if reads emerge during implementation, migrate analogously to 4.8a.
- [ ] 4.9 Add lint rule to `check_env_vars_drift.py`: scoped grep on `modules/rv-tools/src/rv_tools/builtin/`, `modules/aperv-tool/src/`, and `modules/rvagent-tool/src/` returns 0 hits
- [ ] 4.10 Run `/rv-test-run rv-tools` and `/rv-test-run rv-platform`

### 4bis. Instrumentation L3 env hardening (per design.md D9)

- [ ] 4bis.1 In `modules/rv-instrumentation-dexlib2/src/rv_instrumentation_dexlib2/dexlib_instrumentation.py`: replace `_os_env()` (lines 521-525, currently `return dict(os.environ)`) with `_build_subprocess_env(extras)` per design.md D9 — forwards only `{PATH, HOME, JAVA_HOME, ANDROID_HOME, RVSEC_HOME}` plus extras. Update the call site at line 457 accordingly.
- [ ] 4bis.2 In `dexlib_instrumentation.py:592` replace literal `os.environ.get("RVSEC_HOME")` with `os.environ.get(ENV_RVSEC_HOME)` (importing the constant from `rv_android_core.constants`).
- [ ] 4bis.3 In `modules/rv-instrumentation-ajc/src/rv_instrumentation_ajc/ajc_instrumentation.py:419` replace literal `os.environ.get("RVSEC_HOME")` with `os.environ.get(ENV_RVSEC_HOME)`.
- [ ] 4bis.4 Verify `grep -rnE 'dict\(os\.environ|os\.environ\.copy' modules/` returns 0 hits outside `modules/rv-experiment/`.
- [ ] 4bis.5 Run `/rv-test-run rv-instrumentation-dexlib2` and `/rv-test-run rv-instrumentation-ajc`.

## 5. Docker entry-point refactor (allow-list validation)

- [ ] 5.1 Backup `docker/rvandroid/docker-entrypoint.sh` (~150 lines) to `backup/2026-05-06_env_var_cleanup/docker-entrypoint.sh.old`
- [ ] 5.2 Create `docker/rvandroid/scripts/validate_env_vars.sh` (NEW; verifies INV-EXP-31) implementing allow-list check: derive valid set from `ENV_*` constants (parse `constants.py` or `python -c "..."`); compare against set of `RV_*` env vars present; exit 64 with named offenders on any unknown. The allow-list also includes the L1 cross-layer infra family (`RV_PYDANTIC`, `RV_PYDANTIC_STRICT`, `RV_PYDANTIC_LOG`).
- [ ] 5.3 Rewrite `docker/rvandroid/docker-entrypoint.sh` (~30 lines; verifies INV-EXP-31, INV-EXP-32 indirectly) to: (a) source `validate_env_vars.sh`, (b) handle interactive `bash`/`shell` shortcut, (c) honor `RV_DELAY` sleep, (d) `exec uv run rv-experiment run` (no env→flag translation)
- [ ] 5.4 Audit and update all 37 `docker/docker-compose.*.yml` files (`ls docker/docker-compose*.yml | wc -l` confirms count). Remove any reliance on env→flag translation (rv-experiment now reads env directly); confirm no compose file sets a removed `RV_*` variable.
- [ ] 5.4a Migrate the 25 compose files that set `RV_JCA_SPEC=true` to `RV_SPEC_SET=jca`: `docker-compose.{aperv-comparacao, comparacao, dexlib2-validation.template, exp3-aperv-llm, exp4-calibrated, exp4-prompt-variants, exp5-prompt-600s, exp5-smoke, exp6-component-triggering, exp6-mini, exp-aperv-rvsmart, exp-baseline, exp-finetuned-d, exp-finetuned, exp-rvsmart-ape, final-1a, final-1b, final-2, final-3, madevolve-baseline, parallel, revalidate-redist, revalidate, test-gh35, test}.yml`. Verify with `grep -c '^\s*RV_JCA_SPEC' docker/docker-compose*.yml | grep -v ':0$'` returns empty after migration.
- [ ] 5.5 Add integration test `tests/integration/test_docker_entrypoint.sh` covering: known-only proceeds, unknown rejects exit 64, removed-var rejects with helpful message, interactive shortcut works, RV_DELAY sleeps
- [ ] 5.6 Smoke matrix (≥5 representative compose files spanning RV_JCA_SPEC migrators and non-migrators): run `docker-compose.jca-compare.yml`, `docker-compose.comparacao.yml`, `docker-compose.instrument-jca-ajc.yml`, `docker-compose.parallel.yml`, `docker-compose.test.yml` with `--skip-execution` to confirm no breakage from refactor (entrypoint allow-list + JCA_SPEC migration)
- [ ] 5.7 Run `/rv-verify rv-experiment`

## 6. AVD bump to API 30 x86_64

- [ ] 6.1 Backup `docker/android/Dockerfile` to `backup/2026-05-06_env_var_cleanup/Dockerfile.old`
- [ ] 6.2 Update `docker/android/Dockerfile`: `ARG API_LEVEL=30`, `ARG ARCHITECTURE=x86_64` (image type stays `google_apis`); rewrite the gh50 §17 historical comment block per P4 (current-state comments only)
- [ ] 6.3 Update `scripts/run_emulator.sh:4`: `EMULATOR_NAME="RVSec"` (drop `RVSec29`); remove "OLD"/"NEW" comment block
- [ ] 6.4 Build local image `phtcosta/rvandroid:0.9.0-api30` via `docker/rvandroid/build.sh`; tag with API level for traceability
- [ ] 6.4a **Docker-container boot smoke** (closes the gap left by host-side n=80): start a fresh container from `phtcosta/rvandroid:0.9.0-api30` with default compose config; confirm the API 30 x86_64 emulator boots to BOOT_COMPLETED inside the container within 90s (host-side measured 30s; allow margin for Docker overhead) for ≥3 consecutive runs. This directly addresses the `gh50 §17` rollback context (Docker, not host); without this evidence the OverlayFS-diagnosis challenge in proposal/design remains conjecture.
- [ ] 6.5 Smoke matrix gate (H4): run `rv-experiment run` with 5 APKs × 5 tools (Monkey, ape, aperv:sata_mop, droidbot, fastbot) × 60min timeout against the new image; record results
- [ ] 6.6 Larger AVD sample gate: run `scripts/investigate_avd_compat.sh --sample 100 phase2 /home/pedro/desenvolvimento/RV_ANDROID/NOVO/APKS /home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKs`; confirm 0 regressions trend
- [ ] 6.7 Update `docs/20260506_plano_env.md` Section 10 with larger-sample data
- [ ] 6.8 If gates 6.5 + 6.6 pass: tag image as `phtcosta/rvandroid:0.9.0` (the merged candidate). If any tool fails on API 30, document and decide per-tool fallback (escalate as separate change if needed)

## 7. Documentation: canonical surface

- [ ] 7.1 Create `.env.example` at repo root with all 25 surviving env vars, grouped by category (inputs, timeouts, skip flags, static analysis, instrumentation, tool URLs, SDK paths, dev toggles), with comments explaining each
- [ ] 7.2 Update `README.md` "Environment Variables" table to canonical 25-var form, with columns: Name, CLI Flag, Default, Read By, Description
- [ ] 7.3a Create `docs/adr/` directory and `docs/adr/README.md` documenting the ADR numbering convention (`NNNN-kebab-case-title.md`, sequential, never reuse numbers) — directory does not exist today.
- [ ] 7.3 Create ADR `docs/adr/0001-env-var-pattern.md` (NEW) following `.claude/skills/rv-doc-adr/templates/adr.md` — documenting: chosen pattern (centralize via `ENV_*`, Layer Purity), alternatives considered (status quo with literals, separate `rv-config` module, Pydantic `Field(alias=...)`), policy for adding new env var (registry update + lint reconciliation steps from design D1)
- [ ] 7.4 Add "Adding a new environment variable" section to `docs/WORKFLOW.md` (or new `docs/CONTRIBUTING.md`)
- [ ] 7.5 Update `docs/rv_android_architecture.md` §9 NFR Support (the Layer Purity rule is a Maintainability NFR per NFR01, which is the natural home; §8 is module descriptions, not policies) with Layer Purity rule and the 6 cross-layer infra exceptions (`RV_PYDANTIC`, `RV_PYDANTIC_STRICT`, `RV_PYDANTIC_LOG`, `RVSEC_HOME`, `ANDROID_HOME`, `TOOLS_DIR`)
- [ ] 7.6 Add doc note to `modules/rv-tools/CLAUDE.md` about humanoid stateless inference (Phase 0 finding, out-of-scope-but-relevant)
- [ ] 7.7 Run `/rv-docs-sync` to align module-level docs

## 8. Final integration and verification

- [ ] 8.1 Run `scripts/check_env_vars_drift.py` end-to-end; assert 0 hits across all 3 rules
- [ ] 8.2 Run `/rv-qa-lint-fix rv-android-core rv-experiment rv-platform rv-tools`
- [ ] 8.3 Run `/rv-verify rv-android-core` and `/rv-verify rv-experiment` and `/rv-verify rv-platform` and `/rv-verify rv-tools`
- [ ] 8.4 Run full per-module test suite per CLAUDE.md instructions (each module isolated with `--import-mode=importlib`)
- [ ] 8.5 Invoke `/rv-code-reviewer` via Skill tool
- [ ] 8.6 Address review feedback (commit fixes; do not amend)
- [ ] 8.7 Run `/opsx:verify` to confirm implementation matches spec deltas
- [ ] 8.8 Update PR/CHANGELOG noting BREAKING removed env vars (`RV_MEMORY_FILE`, `RV_RVANDROID_URL`, `RV_SKIP_EXPERIMENT`, `RV_JCA_SPEC`) and the AVD bump (`API_LEVEL=30`, `ARCHITECTURE=x86_64`)
