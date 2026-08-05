# Design: gh98-manifest-package-default

## Context

`App.code_package` (`modules/rv-android-core/src/rv_android_core/domain/app.py:119-132`) instantiates `PackageDetector` on first access and returns its election. There is no parameter, no flag and no branch: the heuristic is the only behaviour the property has. Four subsystems consume the result — the GATOR client parameter and the parser filter in `rv-static-analysis`, the coverage re-parse in `rv-platform`, and the quarantine safety guard in `rv-instrumentation-ajc` — so the election silently scopes both the static catalogue and the coverage denominator of every run.

This change makes the manifest package the default and the detector an explicit opt-in (proposal, issue #98). The behaviour is per-run and per-corpus, which is why it is user input rather than an inference, and it is resolved **at the entry points** rather than looked up in the domain layer — which is what `docs/adr/0001-env-var-pattern.md` decision 2 and `docs/WORKFLOW.md` §14 protect: `rv-experiment` reads `RV_PACKAGE_DETECTOR` and so does the standalone `rv-static-analysis` command (D4, owner decision); every layer between them and `App` receives an already-resolved boolean, and `domain/app.py` reads nothing.

Constraints that shape the design:

- **P3 (no backward compatibility)**: no dual-mode property, no `code_package_legacy`, no deprecation path. The property changes meaning and every call site is updated in the same change.
- **Layer Purity (INV-EXP-30)**: the L1 canonical reader set is three files, and `domain/app.py` is not one of them. `scripts/check_env_vars_drift.py:52-91` enforces it mechanically.
- **FR04/FR05/FR06**: the static analyses keep their contracts; only the scope string changes provenance.
- **NFR05/NFR06**: the flag is configuration; the key record is observability.

## Architecture

```
  --package-detector / --no-package-detector ─┐        --package-detector /
  RV_PACKAGE_DETECTOR ────────────────────────┤        --no-package-detector ─┐
                     (rv-experiment, D6)      │        RV_PACKAGE_DETECTOR ───┤ (D4)
                                              ▼                               │
                            ExperimentConfig.package_detector : bool          │
                                              │  passed by value              │
        ┌─────────────────────────────────────┤                               │
        ▼                                     ▼                               ▼
  pre_processor.py                 PlatformConfig.package_detector    rv-static-analysis
  (3 App sites)                    (execution_controller.py:309)      /__main__.py
        │                                     ▼                       (2 App sites,
        │                              platform.py:232                 own argparse)
        └─────────────────────────────────────┴───────────────────────────────┘
                                              ▼
                 App(app_path, package_detector=<bool>)     [L1 — reads no env]
                               │
                 ┌─────────────┴─────────────┐
                 ▼                           ▼
        package_detector=False        package_detector=True
        code_package = package_name   code_package = PackageDetector(...).code_package
        code_package_source="manifest" code_package_source="detector"
                               │
        ┌──────────────┬───────┴────────┬──────────────────┐
        ▼              ▼                ▼                  ▼
  GATOR argv     parser filter   coverage re-parse   AJC quarantine guard
  (sa:255)       (sa:418)        (result_proc:269)   (ajc:849)
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `rv_experiment.config.ExperimentConfig` | Resolve CLI > env > default once per run | flag, `RV_PACKAGE_DETECTOR` | `package_detector: bool` |
| `rv_platform.config.PlatformConfig` | Carry the resolved value into the execution layer | `package_detector` from `ExperimentConfig` | `package_detector: bool` |
| `rv_android_core.domain.App` | Report the package under the chosen policy | `app_path`, `package_detector` | `code_package`, `code_package_source` |
| `rv_android_core.util.android.PackageDetector` | Heuristic election (unchanged) | Androguard `APK` | `PackageDetectionResult` |
| `rv_android_core.util.utils.get_apks` | Build `App` lists from a directory | `apks_dir`, `package_detector` | `list[App]` |
| `rv_static_analysis.__main__` | Standalone entry point resolving flag > env > default itself | argv, `RV_PACKAGE_DETECTOR` | `App`, `StaticAnalyzer` |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| INV-CORE-18 (rewritten) | `domain/app.py` — `code_package` branches on `self.package_detector` | `test_code_package_defaults_to_manifest`, `test_code_package_uses_detector_when_enabled` |
| INV-CORE-55 (new) | absence of `os.environ` in `domain/app.py` | `tests/lint/test_env_vars_drift.py`, `scripts/check_env_vars_drift.py` |
| core: Package Key Provenance | `domain/app.py` — `code_package_source` computed field | `test_code_package_source_matches_mechanism` |
| core: Domain Models (modified) | `App` field + computed fields | `test_app_fields_declared` |
| INV-ANA-03 (rewritten) | `static_analysis.py:418` passes `app.code_package` unchanged | `test_parser_receives_resolved_key` |
| INV-ANA-14 (rewritten) | `PackageDetector` invoked only under the flag | `test_detector_not_invoked_by_default` |
| INV-ANA-58 (new) | no read of the JSON `package` member as a key | `test_json_package_member_is_not_a_filter_key` |
| analysis: Key Provenance Recorded | analysis run record | `test_analysis_records_key_and_origin` |
| INV-EXP-34 (new) | one read site per entry point: `rv_experiment/config.py`, `rv_static_analysis/__main__.py` — both through `ENV_PACKAGE_DETECTOR`, none below | `test_env_read_only_at_entry_points`, `check_env_vars_drift.py` |
| experiment: Opt-In CLI Flag | `rv_experiment/__main__.py` + `config.py`; `rv_static_analysis/__main__.py` | `test_flag_overrides_env`, `test_env_without_flag`, `test_default_is_manifest`, `test_standalone_flag_overrides_env` |
| experiment: propagation into execution | `PlatformConfig.package_detector`, set at `execution_controller.py:309`, read at `platform.py:232` | `test_platform_config_carries_package_detector` |
| experiment: Registry Entry | `constants.py`, `.env.example`, `README.md` | `test_constants_registry.py` |

## Goals / Non-Goals

**Goals:**

- The package that scopes app-owned classes is a user decision on every dataset, defaulting to what the APK declares.
- The detector remains available, unchanged, behind one switch.
- The switch is resolved once, at L5, and travels by value; the domain layer stays free of environment reads.
- A run can state which key it used and where the key came from.

**Non-Goals:**

- Removing `PackageDetector` or altering its heuristics.
- Any normalization of the declared identifier (suffix stripping, prefix repair). Corpus-specific rules stay with the corpus.
- Changing class-membership semantics: the parser's substring match (`static_analysis_parser.py:359`) and GATOR's prefix match stay as they are. Changing the key and the matching rule together would make any measured difference unattributable.
- Re-analysing existing corpora or reconciling stored JSONs with the keys they were measured under.

## Decisions

**D1 — Resolve at L5 and pass by value, rather than read the environment inside `App`.**
Reading `RV_PACKAGE_DETECTOR` directly in `domain/app.py` is fewer lines, and it was considered. It requires adding `domain/app.py` to `L1_ALLOWLIST_FILES` and `RV_PACKAGE_DETECTOR` to `L1_INFRA_NAMES` in `scripts/check_env_vars_drift.py:52,77`, and amending ADR 0001 decision 2 — whose stated rationale for the L1 exception is that those values are *"a property of the host and its concurrency level, not of the experiment"*. A package policy is experiment semantics, so the exception does not extend to it on its own terms. Passing by value also preserves two properties the environment cannot give: per-`App` variation within one process (the #91 case, where each APK needed its own key) and tests that do not mutate global process state.

**D2 — A boolean selector, not a package-valued parameter.**
An alternative surface is `--code-package <value>`, which would have served #91 directly. It is a strictly larger feature: it needs validation, a per-APK source (a CSV or a mapping file), and a decision about what happens when the value matches no class. This change keeps the surface at the choice actually being made — declared vs elected — and leaves the explicit-value knob to a later change that can design its input format properly.

**D3 — `code_package_source` on `App`, not a lookup into the analysis JSON.**
The GATOR artefact records the manifest package in its `package` member regardless of the `codePackage` parameter it ran under. Verified on `SA_RERUN_gh91/`, produced under a neutralised key: `org.fossify.calendar_20.apk.json` carries `package = org.fossify.calendar.debug` while the filter key was `org.fossify.calendar`; `com.jerboa_87.apk.json` and `app.pachli_50.apk.json` show the same pattern. Deriving provenance from the artefact is therefore not merely undesirable, it is not possible. The run states what it did; nothing reads back.

**D4 — `rv-static-analysis` gets both the flag and the variable (owner decision, 2026-08-05).**
It constructs `App` on two standalone paths (`__main__.py:326,404`), and it is a real entry point, not an intermediate layer: a standalone `rv-static-analysis` invocation is a run, and the choice has to be expressible on it. It therefore carries the same negatable flag *and* resolves `RV_PACKAGE_DETECTOR` itself, with the same precedence — flag > env > default. An earlier draft of this design kept the variable L5-only; the owner overrode it, so that a run driven from a shell or a container gets the same behaviour whichever entry point it uses, without the operator having to remember which of the two honours the environment.

This costs no Layer Purity exception and no lint change. `check_env_vars_drift.py` forbids *literal* `os.environ.get("RV_*")` anywhere under `modules/` and wholesale `dict(os.environ)` / `os.environ.copy()` outside L5; a read through the `ENV_PACKAGE_DETECTOR` constant is neither. The precedent is in the same file being edited: `rv_static_analysis/config.py:166,181` already reads `ENV_RVSEC_HOME` and `ENV_ANDROID_HOME` through the registry. What INV-EXP-30 and ADR 0001 actually protect is the *intermediate* layers — `rv-android-core`'s domain model, `rv-platform`, `rv-instrumentation-*` — and that protection is untouched: `domain/app.py` still reads nothing (INV-CORE-55), and every non-entry-point site still receives the boolean by value.

**D5 — `get_apks` grows a parameter rather than a module-level default.**
`util/utils.py:293` builds `App` objects for the AJC entry points (`rv-instrumentation-ajc/__main__.py:413,438`, `ajc_instrumentation.py:195`). A default-carrying module global would be a second, invisible source of the decision. The parameter is threaded, defaulting to `False`.

**D6 — A negatable boolean flag, `--package-detector` / `--no-package-detector` (resolves Open Question 2; owner decision, 2026-08-05).**
The alternative considered was `--package-source manifest|detector`, which would read better if D2's explicit-value knob is ever added as a third source. It was not chosen: the delta spec's precedence scenario already assumes the negatable pair, the Click `is_flag` pair with `default=None` makes *"not given"* distinguishable from *"given as false"* — which is exactly what the CLI > env > default precedence at `config.py:856-867` needs — and a `--package-source` choice would have to be reworked anyway on the day a third source arrives, since that source takes a value rather than a name.

**D7 — The value reaches `rv-platform` through `PlatformConfig`, not through the task.**
`platform.py:232` constructs `App` inside task generation, where the only configuration in scope is `self.config`. `PlatformConfig` gains a `package_detector: bool = False` field, set at `execution_controller.py:309` from `ExperimentConfig`. This is the shape `logcat_diagnostics` already uses at that exact call site, so it adds no new mechanism. Putting the value on `TaskConfiguration` instead was rejected: it is a property of the run, identical for every task, and it would enlarge the task identity that the resume mechanism hashes.

## API Design

### `App(app_path: str, package_detector: bool = False, ...)`

- **Precondition**: `app_path` points to a readable `.apk` (unchanged; `ConfigurationError` otherwise).
- **Postcondition**: `code_package == package_name` and `code_package_source == "manifest"` when `package_detector` is false; `code_package` is the `PackageDetector` election and `code_package_source == "detector"` when true.
- **Positional mapping**: `@validated_model(["app_path"])` maps only the first positional argument, so `App(path)` keeps working and `package_detector` is keyword-only in practice.
- **Laziness**: the detector runs on first access to `code_package`, not at construction, and only when enabled — so the default path never pays for Androguard component enumeration.

```python
class App(BaseValidatedModel):
    app_path: str
    package_detector: bool = Field(
        default=False,
        description="Elect the implementation package heuristically instead of "
                    "reporting the one declared in the manifest",
    )

    @computed_field
    @property
    def code_package(self) -> str: ...

    @computed_field
    @property
    def code_package_source(self) -> str: ...   # "manifest" | "detector"
```

### `get_apks(apks_dir: str, package_detector: bool = False) -> list[App]`

- **Postcondition**: every returned `App` carries the given policy.

### `ExperimentConfig.package_detector: bool`

- **Resolution**: CLI flag if present, else `os.environ.get(ENV_PACKAGE_DETECTOR)` parsed with the project truthiness convention (`"true"`, `"1"`, `"yes"`, `"on"`, case-insensitive; INV-CORE-12), else `False`. Same shape as the `analysis_timeout` / `jvm_memory` precedence already implemented in `rv_experiment/config.py:856-867`.
- **Error**: a value that is neither truthy nor falsy aborts at the CLI boundary rather than defaulting.
- **Flag shape**: `--package-detector/--no-package-detector` with `default=None`, so an absent flag falls through to the environment and an explicit `--no-package-detector` beats `RV_PACKAGE_DETECTOR=true` (D6).

### `PlatformConfig.package_detector: bool`

- **Postcondition**: `platform.py:232` constructs every `App` with this value. Set from `ExperimentConfig` at `execution_controller.py:309`, alongside `logcat_diagnostics` (D7). Default `False`, so a `PlatformConfig` built directly in a test or a script behaves like an unconfigured run.

### `rv-static-analysis` standalone resolution

- **Resolution**: identical precedence, resolved in `__main__.py` before either `App` construction — `--package-detector`/`--no-package-detector` if given, else `ENV_PACKAGE_DETECTOR` under the same truthiness convention, else `False` (D4).
- **Error**: an unparseable environment value aborts the command with a nonzero exit and a message naming the variable, rather than picking a mode. argparse has no `click.BadParameter`, so this is an explicit check at the same point.
- **Shared parsing**: both entry points parse the string through one helper so the two CLIs cannot drift on what `"on"` means. `util/utils.py` already carries `os.getenv`-based coercion helpers at `:442,:470`; the truthiness parser belongs beside them, taking the *value* as an argument so that `rv-android-core` still performs no read of its own.

  As implemented this is two functions rather than one, because a first cut left the two entry points with byte-identical nine-line resolvers and the code review flagged the duplication: `parse_bool_value(value)` owns the vocabulary, and `resolve_bool_setting(cli_value, env_value, var_name)` owns the precedence, the "exported empty means no preference" rule and the error shape. Only `os.environ.get(ENV_PACKAGE_DETECTOR)` stays at each entry point — which is the one line that must, since only entry points may read.

## Data Flow

1. `rv-experiment` resolves `package_detector` once, at CLI parse time, into `ExperimentConfig` (flag > env > default).
2. `PreProcessor` passes it to each `App` it builds (`pre_processor.py:342,461,477`) and into `get_static_analysis_config()` for the sub-module configuration.
3. `ExecutionController` copies it into `PlatformConfig` (`execution_controller.py:309`), and `rv-platform` constructs every `App` with it during task generation (`platform.py:232`). A standalone `rv-static-analysis` invocation resolves the same precedence for itself (D4) instead of receiving a value.
4. `App.code_package` resolves lazily under the policy; `App.code_package_source` reports which mechanism ran.
5. `StaticAnalyzer` passes `app.code_package` to the GATOR argv (`static_analysis.py:255` → `config.py:397`) and to the parser (`static_analysis.py:418`); the run records the key and its origin.
6. `rv-platform` re-parses the JSON for coverage with the key resolved by the current run (`components/static_analysis.py:136`, `result_processor.py:269`) — never with a key read back from the file.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `ConfigurationError` | `App` load/validation | unchanged — raised at construction | fix the APK path |
| `click.BadParameter` | unparseable `RV_PACKAGE_DETECTOR` in `rv-experiment` | abort before experiment setup | set a documented truthy/falsy value |
| nonzero exit naming the variable | unparseable `RV_PACKAGE_DETECTOR` in standalone `rv-static-analysis` | abort before the first `App` is built (argparse has no `BadParameter`) | set a documented truthy/falsy value |
| Empty catalogue (key matches no class) | `StaticAnalysisParser` | not an error — parse succeeds with zero app classes | caller inspects the recorded key; the tool does not repair it |
| Lint violation | `check_env_vars_drift.py` | fatal in CI | keep the read at L5, keep registry + docs in sync |

## Risks / Trade-offs

- **[The AJC quarantine guard weakens on suffixed applicationIds]** → `ajc_instrumentation.py:849` builds `code_pkg_path` from `code_package` and skips quarantining any file under it. With the detector, an app declaring `org.fossify.calendar.debug` yielded `org/fossify` and the guard covered the whole app; under the default it yields `org/fossify/calendar/debug`, which matches no compiled class, so the guard protects nothing. Mitigation: log a WARNING when the guard prefix matches zero files under `tmp_dir` while quarantine patterns are active — the guard becoming inert is exactly the condition worth surfacing. Quarantining app code still requires the operator to have configured a pattern that matches their own app, and `enable_quarantine` is already opt-out.
- **[Every existing corpus was analysed under the old default]** → out of scope by decision: which stored JSON belongs to which key is data management. The change makes the current run's key explicit and recorded, which is what removes the ambiguity going forward.
- **[Silent scope change for anyone who upgrades without reading]** → **BREAKING** is stated in the proposal; the run record names the key on every run, so a scope change is visible in the first output rather than in a coverage number three steps later.
- **[The parser's substring match interacts with longer keys]** → a longer key (the declared package is usually longer than the elected one) is strictly more selective under substring matching, so the failure mode is a narrower catalogue, not a wider one. Left as-is deliberately; see Non-Goals.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit — core | default/opt-in branch, provenance field, detector not invoked by default, verbatim suffix | pytest with a fixture APK; `PackageDetector` spied for non-invocation | ~8 |
| Unit — experiment | CLI > env > default, truthiness parsing, unparseable value aborts | Click runner with patched env | ~6 |
| Unit — standalone SA | same precedence on the argparse entry point; unparseable value exits nonzero | argparse `main()` with patched env | ~4 |
| Unit — propagation | `get_apks`, `PlatformConfig` and each `App` construction site forward the value | direct calls with both values | ~5 |
| Integration — analysis | resolved key reaches GATOR argv and the parser; the run records key + origin | `StaticAnalyzer` against a fixture, GATOR invocation captured | ~3 |
| Lint | env read only at the two entry points and through the constant; no read in `domain/app.py`; registry/docs in sync | `check_env_vars_drift.py`, `test_constants_registry.py` | 2 gates |

Fixtures: one APK whose declared package differs from its implementation package (the Godot case already used at `core/spec.md:597`), and one whose applicationId carries a build-type suffix (`org.fossify.calendar_20.apk` is the documented example).

## Open Questions

1. **Does the AJC quarantine guard need more than a warning?** The risk table proposes surfacing an inert guard. Making the guard robust to a suffixed key would mean giving AJC its own notion of app-code scope, which is a design of its own — out of this change unless the warning proves insufficient in practice.
2. ~~**Flag spelling and negative form.**~~ **RESOLVED (owner, 2026-08-05)**: the negatable boolean `--package-detector` / `--no-package-detector`, on both `rv-experiment` and `rv-static-analysis`. See D6. The same session decided that `rv-static-analysis` also reads `RV_PACKAGE_DETECTOR` (D4) and that the value reaches `rv-platform` through `PlatformConfig` (D7).
3. **Does anything besides the analysis run need the key record?** The provenance requirement is stated for the analysis run. Whether the experiment-level results index should carry it as a column is a `rv-platform` question that this change does not settle.
