# ADR 0001 — Environment-variable pattern: ENV_* registry + Layer Purity

**Status**: Accepted (gh55, 2026-05-06)

## Context

Through 2025-2026 the rv-android workspace accumulated 26+ `RV_*` environment
variables spread across Python modules, Docker compose files, shell scripts,
and the Docker entry point. Symptoms by Phase 0 audit (gh55, see
`docs/20260506_plano_env.md`):

- Drift between code and docs — the README documented 3 vars; code recognized
  26+. Operators had no canonical inventory.
- Silent failures — `RV_SA_TIMEOUT` and `RV_JVM_MEMORY` worked through Docker
  entry-point env→flag translation but were ignored when `rv-experiment` ran
  outside Docker, because the standalone CLI had no equivalent flag.
- Layer Purity violations — `rv-tools/.../humanoid/tool.py` (L2) read
  `RV_HUMANOID_URL` directly via `os.environ`; ape/droidmate/fastbot read
  `TOOLS_DIR` likewise; aperv-tool read three names. The L2 plugin layer is
  supposed to receive configuration via the `AbstractTool.configure(config)`
  contract, not via the global environment.
- Dead code — `RV_MEMORY_FILE`, `RV_RVANDROID_URL`, `RV_SKIP_EXPERIMENT`,
  `RV_JCA_SPEC` (the last superseded by `RV_SPEC_SET`).
- The Docker entry point grew to ~150 lines of env→flag translation that
  duplicated argparse/Click logic and produced two parallel paths to
  configure `rv-experiment`.

PRD references: NFR01 Maintainability, NFR03 Testability, NFR05 Reproducibility.

## Decision

The rv-android workspace adopts the following pattern, enforced by a CI lint
script (`scripts/check_env_vars_drift.py`):

1. **Single registry**. Every `RV_*` env-var name is declared as an `ENV_*`
   constant in `modules/rv-android-core/src/rv_android_core/constants.py`.
   The pattern is `ENV_<UPPERCASE_NAME> = "RV_<UPPERCASE_NAME>"`. The L1
   cross-layer infra family (`RV_PYDANTIC`, `RV_PYDANTIC_STRICT`,
   `RV_PYDANTIC_LOG`, plus the legacy non-`RV_*` paths `RVSEC_HOME`,
   `ANDROID_HOME`, `TOOLS_DIR`) is also in this registry.

2. **Layer Purity**. Only `rv-experiment` (L5) reads user-facing `RV_*`
   environment variables. L2 plugins (`rv-tools/builtin/`, `aperv-tool`,
   `rvagent-tool`), L3 modules (`rv-instrumentation*`), and L4 (`rv-platform`)
   receive configuration via Pydantic models from L5. The exception is the
   L1 cross-layer infra family — six names with exactly one canonical reader
   each inside `rv-android-core` utilities.

3. **No string literals in code**. Every `os.environ.get`, `os.environ[`,
   `os.getenv` call MUST reference an `ENV_*` constant. The lint catches all
   five forms (the three above plus `dict(os.environ)` and
   `os.environ.copy()` which leak the entire environment past Layer Purity).

4. **Allow-list at the Docker entry point**. The entry point validates the
   container environment against the registry; unknown `RV_*` names exit 64
   with a named-offender message. Removed names (e.g., `RV_JCA_SPEC`) get
   migration hints. The entry point no longer translates env vars to CLI
   flags — `rv-experiment` reads them directly via `ENV_*` constants.

5. **Pydantic strict validation at boundary classes**. `ExperimentConfig` and
   `PlatformConfig` declare `model_config = ConfigDict(extra="forbid")`
   explicitly at the class body (not only via `BaseValidatedModel`
   inheritance). Combined with the entry-point allow-list and the registry,
   this gives a single tight allow-list at every entry point.

6. **Variant defaults carry per-tool URLs/paths** (gh55 D8). The default for
   any per-tool URL/path/image lives in `tool.get_variants()["default"]`,
   matching the ARES (`ares/tool.py:79` `docker_image`) and QTesting
   precedents. `ToolFactory.create_tool` merges
   `{**variant_defaults, **tool_config.parameters}` and `configure()` reads
   from the merged dict — no `os.environ` access at L2, no hard-coded
   defaults in `configure` bodies.

## Alternatives considered

- **Status quo (string literals + Docker translation)**. Rejected — the
  drift between code, docs, and runtime kept producing silent failures for
  variables the entry point did not know to translate, and Layer Purity
  violations were invisible to lint without a canonical registry.

- **Separate `rv-config` module**. Rejected — `rv-android-core` already owns
  infrastructure constants and is the universal dependency. A sibling module
  would create fan-out without benefit.

- **Pydantic `Field(alias=...)` for env mapping**. Rejected — ties the
  registry to one model. The registry needs to be model-agnostic so the
  entry-point allow-list and the README lint can both reference it.

- **Allow-list with translation kept**. Rejected — combines worst of both
  worlds (still two paths). The pure allow-list pattern collapses the
  Docker and standalone code paths into one.

- **Backward-compat aliases for removed vars** (`DeprecationWarning`).
  Rejected per CLAUDE.md P3 ("No Backward Compatibility"). Aliases keep dead
  code alive and require a future cleanup pass.

- **Strict validation everywhere (every BaseValidatedModel subclass with
  explicit `model_config`)**. Rejected — many domain models accept arbitrary
  extra fields by design (serialized tool variants, JSON results). Strict
  only at user-input boundaries (top-level configs).

- **Hard-coded literal in `configure` body** (`config.get("X", "default")`).
  Rejected — couples the default to two places (variant + configure),
  making future changes drift-prone.

- **Raise `KeyError` if per-tool config key is missing**. Rejected — breaks
  existing tests and standalone CLI usage that don't pass the flag; forces
  L5 to always inject even when the localhost default is fine.

## Consequences

**Positive**:

- Single, lint-enforced contract for `RV_*` env vars across the workspace.
- Drift between code, docs, and runtime is detected at PR time, not in
  production.
- Silent-failure paths for `RV_SA_TIMEOUT` / `RV_JVM_MEMORY` eliminated:
  both env vars and CLI flags now work uniformly via `ExperimentConfig`.
- Docker entry point shrinks from ~150 to ~65 lines (single responsibility).
- L2 tool plugins are testable without env mocking — they receive config via
  the merged dict that `ToolFactory.create_tool` produces.
- Adding a new env var has a clear, one-pass procedure (see "Adding a new
  environment variable" below).

**Negative**:

- Existing scripts/Docker invocations setting removed names (`RV_JCA_SPEC`,
  `RV_MEMORY_FILE`, `RV_RVANDROID_URL`, `RV_SKIP_EXPERIMENT`) fail loudly
  with exit 64 — the migration path is explicit but not invisible.
- Image rebuild required after the AVD bump (`phtcosta/rvandroid:0.9.0`).

**Neutral**:

- The L1 cross-layer infra family (6 names) is a deliberate exception to
  pure Layer Purity. The reads are concentrated in three known locations
  (`util/validation/config.py`, `util/jar_resolver.py`,
  `util/android/android.py`), each with exactly one consumer. This is not a
  loophole; it's the documented edge of the rule.

## Adding a new environment variable

When a new env var becomes necessary:

1. **Decide if it's actually necessary**. Can the value be a CLI flag only?
   A config-file field? Env vars are appropriate when the value is
   deployment-environment metadata (paths, URLs of co-deployed services) or
   when scripts need to pass values into Docker without writing config files.

2. **Add the constant**. Edit
   `modules/rv-android-core/src/rv_android_core/constants.py`:
   ```python
   ENV_NEW_FEATURE = "RV_NEW_FEATURE"
   ```

3. **Decide the layer**. User-facing values go through L5
   (`rv-experiment`); infra paths go through L1
   (`rv-android-core` with one canonical reader location).

4. **Wire the reader**. For L5: read in `rv-experiment/config.py` (or
   `__main__.py`) via `os.environ.get(ENV_NEW_FEATURE)`. Add a CLI flag if
   the value is per-run tunable (precedence: CLI > env > default).

5. **Document**. Add an entry to `.env.example` (with comment explaining
   what it does and the CLI flag if any) and to README.md's Environment
   Variables table.

6. **Run the lint**. `uv run python scripts/check_env_vars_drift.py` should
   pass; CI runs the same check.

7. **For L2 (tool) variants**: prefer `get_variants()["default"][key] =
   "..."` over reading env at L2. L5 injects via `ToolConfig.parameters`
   when an override is requested.

## References

- gh55 OpenSpec change: `openspec/changes/gh55-env-purity-avd-api30/`
- Phase 0 ideation: `docs/20260506_plano_env.md`
- LLM audit reports: `docs/analise_claude.md`, `docs/analise_codex.md`,
  `docs/analise_gemini.md`
- Lint script: `scripts/check_env_vars_drift.py`
- Allow-list validator: `docker/rvandroid/scripts/validate_env_vars.sh`
- Constants registry: `modules/rv-android-core/src/rv_android_core/constants.py`
- Tests: `tests/lint/test_env_vars_drift.py`,
  `modules/rv-android-core/tests/test_constants_registry.py`,
  `modules/rv-android-core/tests/test_top_level_configs_strict.py`,
  `modules/rv-experiment/tests/test_config_precedence.py`,
  `modules/rv-tools/tests/registry/test_tool_factory_parameters_channel.py`
