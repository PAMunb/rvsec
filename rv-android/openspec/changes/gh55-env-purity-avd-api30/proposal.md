## Why

GitHub Issue: #55

Two related problems converged in Phase 0 ideation (`docs/20260506_plano_env.md`):

1. **Env var sprawl with silent failures**: 26+ `RV_*` environment variables are recognized in code, but only 16 have constants in `rv-android-core/constants.py`; 4 are dead/deprecated; the README documents only 3. Two variables (`RV_SA_TIMEOUT`, `RV_JVM_MEMORY`) work via Docker entrypoint but have no equivalent CLI flag — they fail silently when `rv-experiment` runs without Docker. One module (`rv-tools/.../humanoid/tool.py:89`) reads `RV_HUMANOID_URL` directly at Layer 2, violating the layered architecture documented in `docs/rv_android_architecture.md` (env reads should occur only at L5/L1 cross-layer).

2. **AVD lock-in to API 29 x86**: `gh50 §17` (commit `07179eb6`) attempted to bump the Docker AVD to API 30 x86_64 but rolled back, attributing the failure to OverlayFS multi-step boot requirements. Host-side empirical investigation on 06/05/2026 (`results/avd_compat_investigation/20260506_133454/`, n=80) **challenges** that diagnosis: API 30 x86_64 boots in 30s on the host with the existing default config (no `-writable-system`), gains 7/20 modern APKs that fail on baseline, and produces 0 regressions in either dataset. The host-side evidence does not by itself reproduce the Docker container scenario the rollback was based on, so a Docker-container boot smoke (task 6.4a) is a hard pre-merge gate before the diagnosis can be considered settled.

Together, these motivate a single consolidated change: clean up the env var contract while it is still small enough to refactor in one pass, and complete the deferred AVD bump now that the empirical blocker has been disproven.

## What Changes

### Env var / Layer Purity (TÓPICO 3 — refator arquitetural)

- Centralize all `RV_*` environment variable string literals into `ENV_*` constants in `rv-android-core/constants.py` (16 new constants for currently-uncovered variables — see Impact table for the 13 user-facing + 3 L1-infra split).
- **BREAKING**: remove 4 dead/deprecated constants and their associated env vars: `ENV_MEMORY_FILE` / `RV_MEMORY_FILE`, `ENV_RVANDROID_URL` / `RV_RVANDROID_URL`, `ENV_SKIP_EXPERIMENT` / `RV_SKIP_EXPERIMENT`, `ENV_JCA_SPEC` / `RV_JCA_SPEC` (the latter superseded by `RV_SPEC_SET`).
- Replace every literal `os.environ.get("RV_*")` in `modules/` with `os.environ.get(ENV_*)`. Lint check on CI.
- **Layer Purity rule**: only `rv-experiment` (L5) and `rv-android-core` (L1, restricted to the cross-layer infra family — `RV_PYDANTIC`, `RV_PYDANTIC_STRICT`, `RV_PYDANTIC_LOG`, `RVSEC_HOME`, `ANDROID_HOME`, `TOOLS_DIR`) may read environment variables. L2/L3/L4 receive configuration via Pydantic models from L5 or via L1 utilities (`JarResolver` for `TOOLS_DIR`). Notes: (a) `RV_PYDANTIC_STRICT` and `RV_PYDANTIC_LOG` are existing live env vars at `modules/rv-android-core/src/rv_android_core/util/validation/config.py:77,82` controlling Pydantic strict-mode and event logging — they are surfaced explicitly here so the registry covers them and they pass the entrypoint allow-list. (b) `TOOLS_DIR` is operator-level deployment metadata (analogous to `ANDROID_HOME` / `RVSEC_HOME`); the canonical read is `rv-android-core/util/jar_resolver.py`, and tool plugins resolve paths via `JarResolver.resolve_jar(...)` instead of reading the env var directly (5 violations in `rv-tools/builtin/{ape,droidmate,fastbot}` and `aperv-tool` migrated as part of this change).
- Migrate `RV_HUMANOID_URL` resolution from `rv-tools/.../humanoid/tool.py:89` (L2) to `rv-experiment` CLI/config (L5), passed through to L2 via the entry of `PlatformConfig.tools` whose `name == "humanoid"` (i.e., its `parameters["humanoid_url"]`). The canonical config key is `humanoid_url` everywhere — no aliases.
- Add CLI flags `--analysis-timeout` (already exposed by `rv-static-analysis` standalone CLI) and `--jvm-memory` to `rv-experiment` to eliminate the silent-failure cliff for `RV_SA_TIMEOUT` and `RV_JVM_MEMORY`.
- **BREAKING**: `docker/rvandroid/docker-entrypoint.sh` is rewritten — it no longer translates env vars to CLI flags; it validates the env var allow-list (rejects unknown `RV_*` with exit 64) and execs `rv-experiment` directly. Modules read env vars themselves at L5.
- Pydantic configs (`ExperimentConfig`, `PlatformConfig`) use `model_config = ConfigDict(extra="forbid")`.
- New canonical files: `.env.example` at repo root, `docs/adr/0001-env-var-pattern.md`, lint script `scripts/check_env_vars_drift.py`.

### AVD Upgrade (TÓPICO 2 — Option B, empirically validated)

- **BREAKING**: `docker/android/Dockerfile` defaults bumped to `API_LEVEL=30`, `ARCHITECTURE=x86_64` (image type stays `google_apis`).
- `scripts/run_emulator.sh` AVD name changed from `RVSec29` to `RVSec`.
- All 37 `docker-compose.*.yml` files under `docker/` are audited (`ls docker/docker-compose*.yml | wc -l = 37`); 25 of them currently set the soon-to-be-removed `RV_JCA_SPEC=true` and MUST migrate to `RV_SPEC_SET=jca` in the same commit. List of affected files: `docker-compose.{aperv-comparacao, comparacao, dexlib2-validation.template, exp3-aperv-llm, exp4-calibrated, exp4-prompt-variants, exp5-prompt-600s, exp5-smoke, exp6-component-triggering, exp6-mini, exp-aperv-rvsmart, exp-baseline, exp-finetuned-d, exp-finetuned, exp-rvsmart-ape, final-1a, final-1b, final-2, final-3, madevolve-baseline, parallel, revalidate-redist, revalidate, test-gh35, test}.yml`. P3 — no shims/aliases; one consistent commit.
- Two acceptance gates remain before merge: (a) larger sample matrix (≥100 APKs/dataset) confirms 0 regressions trend, (b) tool smoke matrix (Monkey/ape/aperv:sata_mop/droidbot/fastbot × 5 APKs × 60min) passes on API 30 x86_64.

### Out of scope

- humanoid container-per-APK isolation (TÓPICO 1): refuted upstream — humanoid is stateless TensorFlow inference. Doc note in `modules/rv-tools/CLAUDE.md`.
- `google_apis_playstore` image / NDK Translation: requires `$ADB_VENDOR_KEYS` and ignores `-skip-adb-auth` in headless mode; warrants a separate investigation track if ARM-only APKs become priority.

### Backward compat (P3 — no shims)

- No deprecation aliases, no warnings, no `_legacy` suffixes, no `# removed` comments.
- Old `docker-entrypoint.sh` (~150 lines), pre-refactor `constants.py`, and `rv-tools/.../humanoid/tool.py` are moved to `backup/2026-05-06_env_var_cleanup/` before being overwritten.
- One commit = one consistent state (tests, lint, smoke compose pass per commit).

## Capabilities

### New Capabilities

None. The change refactors the public surface of existing capabilities without introducing new ones.

### Modified Capabilities

- `core`: `ENV_*` constants table normalized (additions + removals); becomes the single source of truth for environment-variable identifiers consumed by upper layers.
- `experiment`: CLI surface gains `--analysis-timeout` and `--jvm-memory`; the Docker entrypoint contract is simplified (env-var allow-list validation instead of env→flag translation); silent-failure paths for static-analysis tuning are eliminated.
- `platform`: `PlatformConfig.tools` (the existing `List[ToolConfig]` field) is the supported channel for tool URLs/credentials previously read from environment variables in lower layers (Layer Purity); humanoid URL injection (via `ToolConfig.parameters["humanoid_url"]`) is the canonical example.
- `tools`: tool implementations (`HumanoidTool` first, others audited) no longer read environment variables at Layer 2; they receive configuration via the constructor/`configure()` path established in `AbstractTool`.

## Impact

**Modules touched:**

| Module | Change |
|--------|--------|
| `rv-android-core` | `constants.py`: +16 `ENV_*` constants (13 user-facing + 3 L1-infra: `ENV_PYDANTIC_STRICT`, `ENV_PYDANTIC_LOG`, `ENV_TOOLS_DIR`), −4 dead constants; lint contract for centralization. `util/validation/config.py:72,77,82` migrated from `os.getenv("RV_PYDANTIC*")` literals to constants; `util/jar_resolver.py:300` becomes the single canonical reader for `TOOLS_DIR`. |
| `rv-experiment` | `__main__.py`: +2 CLI flags. `config.py`: env reads via `ENV_*` constants; `extra="forbid"` strict validation. Docker entrypoint refactor. |
| `rv-platform` | `PlatformConfig.tools` (the existing `List[ToolConfig]` field; `ToolConfig.parameters` is the per-tool config dict) consolidated as the env-var injection point; lint forbids env reads. |
| `rv-tools` | `humanoid/tool.py:89`: env read removed; URL received via config. Other tool plugins audited for similar violations. |
| `docker/rvandroid/` | `docker-entrypoint.sh` rewritten; new `validate_env_vars.sh`. |
| `docker/android/` | `Dockerfile`: `API_LEVEL=30`, `ARCHITECTURE=x86_64`. |
| `scripts/` | `run_emulator.sh`: `EMULATOR_NAME=RVSec`. New `check_env_vars_drift.py` lint. |
| `docker/docker-compose.*.yml` | All 37 compose files audited; 25 migrate `RV_JCA_SPEC=true` → `RV_SPEC_SET=jca`. |
| `README.md`, `.env.example`, `docs/adr/0001-env-var-pattern.md` | New canonical documentation surface. |

**FRs/NFRs:**

- NFR01 Maintainability — single source of truth for env var contract; CI lint prevents drift.
- NFR03 Testability — module-level env reads removed, simplifying mocking; layer purity tested via grep-based lint.
- NFR05 Reproducibility — `.env.example` codifies defaults; strict validation prevents silent typos.

**Breaking changes for consumers:**

- Users / scripts setting `RV_MEMORY_FILE`, `RV_RVANDROID_URL`, `RV_SKIP_EXPERIMENT`, or `RV_JCA_SPEC` will be rejected by the new entrypoint with exit 64. Migration: remove them; use `RV_SPEC_SET` instead of `RV_JCA_SPEC`.
- Users running `docker run -e RV_X=... phtcosta/rvandroid:VERSION` who relied on the entrypoint translating env→flag will see no behavior change for documented variables, but unknown `RV_*` names now fail loudly.
- Local development against the Docker image must rebuild after `Dockerfile` API_LEVEL bump (image label changes).

**Cross-module dependencies:**

- L5 (`rv-experiment`) becomes the only environment-reading layer for user-facing config; L2/L3/L4 are downstream consumers of the resolved Pydantic model.
- `rv-platform.PlatformConfig.tools` (existing field; no schema change) gains a normative invariant requiring `ToolConfig.parameters` to be the sole channel for forwarding L5-resolved tool config (URLs, credentials), without introducing new abstractions.
