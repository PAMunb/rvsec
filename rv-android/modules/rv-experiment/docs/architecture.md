# rv-experiment Architecture

## Overview

rv-experiment is the top-level experiment orchestration module for the RV-Android framework. It provides the primary CLI interface (`rv-experiment` command) and coordinates a three-phase workflow: (1) pre-processing (monitor generation, APK instrumentation, static analysis), (2) execution (delegated to rv-platform), and (3) post-processing (instrumentation error tracking and completion diagnostics). rv-experiment handles orchestration only -- all task execution, emulator management, and result processing stay in rv-platform.

## Specification Alignment

This module implements requirements from `openspec/specs/experiment/spec.md`.

### Functional Requirements

| FR | Description | Architectural Support |
|----|-------------|----------------------|
| FR15 | Three-phase workflow for experiment lifecycle | `ExperimentController` orchestrates `PreProcessor`, `ExecutionController`, and `PostProcessor` in strict sequential order |
| FR16 | CLI with tool specification DSL | Click-based CLI in `__main__.py` with DSL parser; supports `run`, `config`, `list-tools`, `validate` commands |
| FR16-ext | Experiment resume via CLI | `--resume-dir` (explicit) and `--name` (implicit) resume mechanisms with auto-skip of pre-processing |
| FR16-ext | Docker execution mode | `docker-entrypoint.sh` translates environment variables to CLI arguments |
| FR17 | Just-in-time sub-module configuration | `ExperimentConfig.get_*_config()` methods create sub-module configs on demand |

### Key Invariants

| Invariant | Description | Enforcement Mechanism |
|-----------|-------------|----------------------|
| INV-EXP-01 | Phases execute in strict sequential order | `ExperimentController.run()` calls Phase 1, 2, 3 sequentially |
| INV-EXP-02 | No data transfer from rv-platform back to rv-experiment | `ExecutionController` reads only aggregate success/failure counts from `Platform.run()` |
| INV-EXP-03 | ExperimentConfig validation before execution | `ExperimentConfig.validate()` checks name, tools, repetitions, timeouts, APK directory, specification set |
| INV-EXP-05 | RVSEC_HOME three-level priority resolution | JIT config methods check: (1) `rvsec_root` field, (2) `RVSEC_HOME` env var, (3) raise `ConfigurationError` |
| INV-EXP-06 | `ExecutionController.setup()` before `run()` | `run()` raises `RVExperimentExecutionError` if `setup()` was not called |
| INV-EXP-07 | Skip flags respected in pre-processing | `PreProcessor.process()` checks boolean flags before each step |
| INV-EXP-08 | Instrumentation failure fallback | `PreProcessor` copies original APKs to instrumented directory on failure |
| INV-EXP-09 | Correct DSL comma handling | Parser distinguishes tool separators from parameter separators by detecting `=` tokens |
| INV-EXP-13 | Resume auto-skips pre-processing | CLI forces all skip flags to `True` when resume is detected |
| INV-EXP-14 | Flat results directory | `ExperimentController` uses `config.results_dir` directly without appending subdirectories |

### Specification Scenarios

Scenarios from `openspec/specs/experiment/spec.md` that validate this architecture:

- **Full experiment with all phases enabled**: Exercises the complete three-phase pipeline -- PreProcessor generates monitors and instruments APKs, ExecutionController delegates to Platform, PostProcessor generates diagnostics.
- **Experiment with all pre-processing skipped**: PreProcessor respects skip flags and returns original APKs; execution proceeds with 0% coverage.
- **Pre-processing failure does not abort experiment**: PreProcessor catches instrumentation errors and copies original APKs as fallback; Phase 2 and 3 still execute.
- **Resume with --name detecting existing results**: CLI detects `tasks.json` in named results directory, auto-skips pre-processing, platform skips completed tasks.

## Key Architectural Decisions

### AD-1: Click-Based CLI with Tool Specification DSL

**Choice**: Use Click framework for CLI with a compact DSL (`tool:variant@param=value`) for tool configuration.

**Why**: Experiments are invoked from the command line or Docker entrypoint scripts. Click provides argument parsing, help generation, and command grouping without boilerplate. The tool specification DSL exists because researchers frequently compare multiple tools with different configurations. A verbose JSON-only interface would be impractical for iterative experimentation -- the DSL allows `rv-experiment run --tools monkey,droidbot:dfs_greedy,rvagent:multimode@temperature=0.3` as a single command.

**Invariant cross-reference**: INV-EXP-09 ensures correct comma handling inside parameter sections, distinguishing tool separators from parameter separators by detecting `=` tokens.

### AD-2: Three-Phase Pipeline with Facade

**Choice**: Decompose the experiment lifecycle into three sequential phases (pre-processing, execution, post-processing) orchestrated by `ExperimentController` as a facade.

**Why**: Each phase has distinct failure modes and skip capabilities. Pre-processing (monitor generation, instrumentation, static analysis) can fail due to missing external tools (JavaMOP, RV-Monitor, ajc) but should not abort the entire experiment. Execution is delegated to rv-platform which manages its own lifecycle. Post-processing generates diagnostics from whatever completed. Making these three explicit phases allows individual operations within Phase 1 to be skipped independently via boolean flags, and allows Phase 3 to execute even if Phase 2 failed.

**Invariant cross-reference**: INV-EXP-01 mandates strict sequential order (Phase 1 before Phase 2 before Phase 3). INV-EXP-07 ensures skip flags are respected.

### AD-3: One-Way Data Flow (Experiment to Platform)

**Choice**: rv-experiment provides configuration to rv-platform but does not read back task results, coverage data, or error logs.

**Why**: If rv-experiment consumed rv-platform's results, the two modules would be bidirectionally coupled, making it impossible to change rv-platform's output format without updating rv-experiment. The one-way flow means rv-platform owns all result processing -- it writes CSV/JSON files to disk, and researchers or analysis tools consume those files directly. rv-experiment receives only an aggregate success/failure count from `Platform.run()` for logging purposes.

**Invariant cross-reference**: INV-EXP-02 formalizes this constraint: the only information flowing back is `{total_tasks, successful_tasks, failed_tasks}`.

### AD-4: Just-in-Time Sub-Module Configuration

**Choice**: `ExperimentConfig` provides `get_monitored_operations_config()`, `get_instrumentation_config()`, and `get_static_analysis_config()` methods that create sub-module configurations on demand.

**Why**: Eager construction of all sub-module configurations during `ExperimentConfig.__init__()` would fail if optional sub-modules are not installed (e.g., rv-monitor-generator might not be present in a skip-monitors run). It would also validate paths that may not be needed (e.g., RVSEC_HOME when all pre-processing is skipped). JIT creation avoids both problems -- configurations are built only when the `PreProcessor` needs them, and only for operations that are actually enabled.

**Invariant cross-reference**: INV-EXP-05 governs RVSEC_HOME resolution: (1) `rvsec_root` field, (2) `RVSEC_HOME` env var, (3) `ConfigurationError`.

### AD-5: Resume via tasks.json Detection with Auto-Skip

**Choice**: Resume is detected by the presence of `tasks.json` in the target results directory. When detected, all pre-processing skip flags are forced to `True`.

**Why**: Docker containers in the ICST study were routinely killed and restarted by orchestrators and watchdog processes. Without resume, a restart discards all completed work. The auto-skip behavior exists because pre-processing artifacts (monitors, instrumented APKs, static analysis files) already exist from the original run. Re-generating them would waste time and potentially overwrite the artifacts that rv-platform needs for coverage tracking. The platform handles task-level resume via identity matching in `_skip_completed_tasks()`.

**Invariant cross-reference**: INV-EXP-13 formalizes the auto-skip: all three pre-processing flags are set to `True` regardless of CLI values when resume is detected.

### AD-6: Flat Results Directory

**Choice**: `ExperimentController` uses `config.results_dir` directly without appending subdirectories. The CLI layer constructs the complete path.

**Why**: The original design appended `config.name` to `config.results_dir`, creating paths like `results/my_experiment/my_experiment`. This caused confusion and broke resume detection (the CLI expected the path it constructed, but the controller modified it). The flat design means the CLI builds `results/my_experiment/` and passes it as-is; the controller writes all artifacts there without further path manipulation.

**Invariant cross-reference**: INV-EXP-14 formalizes this: `ExperimentController` MUST use `config.results_dir` directly.

### AD-7: Instrumentation Failure Fallback

**Choice**: If APK instrumentation fails, `PreProcessor` copies original APKs to the instrumented directory as a fallback.

**Why**: Instrumentation involves complex external toolchains (dex2jar, ajc, d8, jarsigner) that can fail for specific APKs due to obfuscation, multi-dex issues, or version incompatibilities. Aborting the entire experiment because one APK failed to instrument would waste all the successful instrumentation work and prevent data collection on the remaining APKs. The fallback means the experiment continues with uninstrumented APKs (producing 0% coverage for those APKs, which is still useful data for the researcher).

**Invariant cross-reference**: INV-EXP-08 requires this fallback behavior.

## Architectural Patterns

### Pattern: Facade (ExperimentController)

**Description**: `ExperimentController` presents a single `run()` method that coordinates three internal workflow components (`PreProcessor`, `ExecutionController`, `PostProcessor`), hiding the complexity of phase sequencing, error handling, and configuration persistence.

**When Used**: The experiment lifecycle involves coordinating multiple independent sub-modules (monitor generation, instrumentation, static analysis, platform execution, diagnostics). The facade provides a single entry point that manages the sequencing.

**Advantages**:
- Callers (CLI, Docker entrypoint) interact with one class and one method
- Phase ordering is enforced in one place

**Disadvantages**:
- All three phases must be understood to modify the workflow

### Pattern: Pipeline (PreProcessor)

**Description**: `PreProcessor.process()` executes three steps sequentially: monitor generation, APK instrumentation, and static analysis. Each step is independently skippable via boolean flags and uses lazy imports for optional sub-modules.

**When Used**: Pre-processing involves three ordered operations where each step produces artifacts consumed by the next (monitors -> instrumentation -> static analysis on instrumented APKs).

**Advantages**:
- Individual steps can be skipped without affecting the pipeline structure
- Lazy imports allow operation when optional modules are not installed

**Disadvantages**:
- Fixed ordering; cannot parallelize steps

### Pattern: Bridge (ExecutionController)

**Description**: `ExecutionController` translates `ExperimentConfig` (orchestration domain) into `PlatformConfig` (execution domain), bridging the two layers without exposing platform internals to the experiment layer.

**When Used**: rv-experiment and rv-platform use different configuration models. The bridge pattern keeps them decoupled.

**Advantages**:
- Changes to PlatformConfig do not propagate to ExperimentConfig
- Clear separation between orchestration and execution concerns

**Disadvantages**:
- Configuration mapping logic must be maintained when either config evolves

### Pattern: Factory (ConfigurationFactory)

**Description**: `ConfigurationFactory` creates `ExperimentConfig` instances from various sources: CLI arguments, JSON files, dictionaries, and templates. Centralizes configuration creation logic.

**When Used**: Experiment configurations can originate from CLI arguments, JSON files, or programmatic construction. The factory normalizes all paths into a single validated config object.

**Advantages**:
- Single place to add new configuration sources
- Template generation for common experiment setups

**Disadvantages**:
- Additional indirection for simple cases

---

## Logical View

Shows key domain entities and their relationships.

### Domain Entities

| Entity | Responsibility |
|--------|----------------|
| ExperimentConfig | Holds all experiment parameters; provides JIT sub-module configuration methods |
| ExperimentController | Facade orchestrating the three-phase workflow |
| PreProcessor | Phase 1: monitor generation, APK instrumentation, static analysis |
| ExecutionController | Phase 2: translates config and delegates to rv-platform |
| PostProcessor | Phase 3: instrumentation error tracking, completion diagnostics |
| ResultManager | Generates `instrument_errors.json` from TaskStorage data |
| ConfigurationFactory | Creates ExperimentConfig from CLI args, JSON files, templates |
| WorkflowFactory | Creates workflow components (PreProcessor, ExecutionController, PostProcessor) |

### Component Architecture

```mermaid
%%{init: {'theme': 'neutral'}}%%
flowchart TB
    subgraph RVExperiment["rv-experiment"]
        direction TB
        subgraph CLI["CLI Layer"]
            direction LR
            MainCLI["__main__.py\n(Click commands)"]
            ConfigFactory["ConfigurationFactory"]
        end
        subgraph Orchestration["Orchestration Layer"]
            direction LR
            Controller["ExperimentController"]
            WFactory["WorkflowFactory"]
        end
        subgraph Workflow["Workflow Layer"]
            direction LR
            PreProc["PreProcessor"]
            ExecCtrl["ExecutionController"]
            PostProc["PostProcessor"]
            ResMgr["ResultManager"]
        end
        subgraph ConfigBlock["Configuration"]
            direction LR
            ExpConfig["ExperimentConfig"]
            Constants["constants.py"]
        end
    end

    MainCLI --> ConfigFactory
    ConfigFactory --> ExpConfig
    MainCLI --> Controller
    Controller --> WFactory
    WFactory --> PreProc
    WFactory --> ExecCtrl
    WFactory --> PostProc
    Controller --> PreProc
    Controller --> ExecCtrl
    Controller --> PostProc
    PostProc --> ResMgr
    PreProc --> ExpConfig
    ExecCtrl --> ExpConfig

    subgraph ExternalModules["External Modules"]
        direction LR
        PlatformMod["rv-platform\n(Platform)"]
        MonGen["rv-monitor-generator"]
        Instr["rv-instrumentation"]
        StaticA["rv-static-analysis"]
        ToolsMod["rv-tools\n(ToolRegistry)"]
    end

    PreProc -.-> MonGen
    PreProc -.-> Instr
    PreProc -.-> StaticA
    ExecCtrl --> PlatformMod
    MainCLI -.-> ToolsMod
```

---

## Development View

Shows code organization for developers.

### Module Structure

```
modules/rv-experiment/
├── src/
│   └── rv_experiment/
│       ├── __init__.py
│       ├── __main__.py                    # CLI entry point (Click: run, config, list-tools, validate)
│       ├── config.py                      # ExperimentConfig Pydantic model with JIT configs
│       ├── constants.py                   # Directory paths, defaults, spec set constants
│       ├── experiment/
│       │   ├── __init__.py
│       │   ├── experiment_controller.py   # Three-phase workflow orchestrator
│       │   └── workflow/
│       │       ├── __init__.py
│       │       ├── workflow_factory.py    # Factory for workflow components
│       │       ├── pre_processor.py       # Phase 1: monitors, instrumentation, static analysis
│       │       ├── execution_controller.py # Phase 2: rv-platform bridge
│       │       ├── post_processor.py      # Phase 3: diagnostics and error tracking
│       │       └── result_manager.py      # Instrumentation error JSON generation
│       └── factories/
│           ├── __init__.py
│           └── configuration_factory.py   # Factory for ExperimentConfig creation
├── tests/
│   ├── conftest.py
│   ├── helpers.py
│   ├── experiment/                        # Controller tests
│   ├── test_config_jit.py                 # JIT configuration tests
│   ├── test_config_json.py                # JSON serialization tests
│   ├── test_config_validation.py          # Validation tests
│   ├── test_configuration_factory.py      # Factory tests
│   ├── test_constants.py                  # Constants tests
│   ├── test_post_processor.py             # Post-processing tests
│   └── test_resume_cli.py                 # Resume mechanism tests
└── pyproject.toml
```

### Package Dependencies

```mermaid
%%{init: {'theme': 'neutral'}}%%
flowchart TB
    subgraph CLILayer["CLI Layer"]
        MainModule["__main__.py"]
    end
    subgraph FactoryLayer["Factory Layer"]
        ConfigFact["configuration_factory"]
    end
    subgraph OrchestrationLayer["Orchestration Layer"]
        ExpController["experiment_controller"]
    end
    subgraph WorkflowLayer["Workflow Layer"]
        PreProcess["pre_processor"]
        ExecControl["execution_controller"]
        PostProcess["post_processor"]
        ResultMgr["result_manager"]
    end
    subgraph ConfigLayer["Configuration Layer"]
        ConfigMod["config"]
        ConstantsMod["constants"]
    end

    MainModule --> ConfigFact
    MainModule --> ExpController
    ConfigFact --> ConfigMod
    ExpController --> PreProcess
    ExpController --> ExecControl
    ExpController --> PostProcess
    PostProcess --> ResultMgr
    PreProcess --> ConfigMod
    ExecControl --> ConfigMod
    ConfigMod --> ConstantsMod
```

---

## Process View

Shows run-time behavior during a complete experiment execution.

### Execution Flow

```mermaid
%%{init: {'theme': 'neutral'}}%%
sequenceDiagram
    participant CLI as __main__.py
    participant CF as ConfigurationFactory
    participant EC as ExperimentController
    participant PP as PreProcessor
    participant XC as ExecutionController
    participant PO as PostProcessor
    participant PLT as Platform (rv-platform)

    CLI->>CF: parse CLI args
    CF-->>CLI: ExperimentConfig
    CLI->>EC: __init__(config)
    CLI->>EC: run()

    Note over EC: Phase 1: Pre-Processing
    EC->>PP: process()
    PP->>PP: _generate_monitors() [if enabled]
    PP->>PP: _instrument_apks() [if enabled]
    PP->>PP: _run_static_analysis() [if enabled]
    PP-->>EC: instrumented APKs list

    Note over EC: Phase 2: Execution
    EC->>XC: setup(tools, apps)
    XC->>XC: _create_platform_config()
    EC->>XC: run()
    XC->>PLT: Platform.run()
    PLT-->>XC: {total, successful, failed}
    XC-->>EC: success/failure

    Note over EC: Phase 3: Post-Processing
    EC->>PO: process()
    PO->>PO: generate instrument_errors.json
    PO->>PO: generate experiment_completion.json
    PO-->>EC: done

    EC-->>CLI: True/False
```

### Resume Flow

When resume mode is detected (existing `tasks.json`), the flow differs:

1. CLI detects existing results directory and sets `resume_mode=True`
2. All pre-processing flags are forced to `False` (INV-EXP-13)
3. Phase 1 (`PreProcessor.process()`) executes but all steps are skipped
4. Phase 2 delegates to rv-platform, which loads `tasks.json` and skips completed tasks
5. Phase 3 runs normally to update diagnostics

---

## Data Flow

This section traces how data moves through rv-experiment during a complete experiment run, from user input through to output artifacts.

### Configuration Assembly

```mermaid
%%{init: {'theme': 'neutral'}}%%
flowchart LR
    subgraph Input["User Input"]
        CLIArgs["CLI arguments\n(--tools, --timeouts, etc.)"]
        JSONFile["JSON config file\n(--config)"]
        EnvVars["Environment vars\n(RVSEC_HOME, etc.)"]
        DockerVars["Docker env vars\n(RV_TOOLS, etc.)"]
    end

    subgraph Parsing["CLI Layer"]
        DSLParse["DSL Parser\ntool:variant@param=val"]
        ConfigFact["ConfigurationFactory"]
    end

    subgraph Validation["Configuration"]
        ExpConfig["ExperimentConfig\n(Pydantic validated)"]
        JITGen["get_monitored_operations_config()"]
        JITInstr["get_instrumentation_config()"]
        JITStatic["get_static_analysis_config()"]
    end

    CLIArgs --> DSLParse
    DSLParse --> ConfigFact
    JSONFile --> ConfigFact
    DockerVars -->|"entrypoint.sh\ntranslates"| CLIArgs
    ConfigFact --> ExpConfig
    EnvVars --> ExpConfig
    ExpConfig -.->|"on demand\n(Phase 1 only)"| JITGen
    ExpConfig -.->|"on demand"| JITInstr
    ExpConfig -.->|"on demand"| JITStatic
```

Configuration enters rv-experiment through two paths:
1. **CLI mode**: The DSL parser converts `--tools monkey,droidbot:dfs_greedy` into `ToolConfig` instances; `ConfigurationFactory` assembles the full `ExperimentConfig`.
2. **Config file mode**: `ExperimentConfig.from_file()` loads a JSON file directly, bypassing the DSL parser.

In Docker mode, `docker-entrypoint.sh` translates environment variables (`RV_TOOLS`, `RV_TIMEOUTS`, etc.) into CLI arguments before the Python process starts.

JIT configuration methods (`get_monitored_operations_config()`, etc.) are called only by `PreProcessor` during Phase 1, and only when the corresponding operation is enabled (INV-EXP-05).

### Three-Phase Data Flow

```mermaid
%%{init: {'theme': 'neutral'}}%%
flowchart TB
    subgraph Phase1["Phase 1: Pre-Processing"]
        direction TB
        MOP[".mop spec files"] --> MonGen["Monitor Generation\n(rv-monitor-generator)"]
        MonGen --> Monitors[".aj aspects +\n.java monitors"]
        Monitors --> Instr["APK Instrumentation\n(rv-instrumentation)"]
        OrigAPKs["Original APKs"] --> Instr
        Instr --> InstrAPKs["Instrumented APKs\n(out/instrumented_apks/)"]
        InstrAPKs --> Static["Static Analysis\n(rv-static-analysis)"]
        Static --> SAFiles[".wtg, .gesda,\n.reach files"]
    end

    subgraph Phase2["Phase 2: Execution"]
        direction TB
        InstrAPKs2["Instrumented APKs"] --> PlatConfig["PlatformConfig\ncreation"]
        PlatConfig --> PlatRun["Platform.run()\n(rv-platform)"]
        PlatRun --> Results["coverage.csv\nerrors.csv\nsummary.csv\nresults.json\nperformance.csv\ntasks.json"]
    end

    subgraph Phase3["Phase 3: Post-Processing"]
        direction TB
        TasksJSON["tasks.json"] --> PostProc["PostProcessor"]
        PostProc --> InstrErrors["instrument_errors.json"]
        PostProc --> CompDiag["experiment_completion.json"]
    end

    InstrAPKs --> InstrAPKs2
    SAFiles -.->|"co-located\nwith APKs"| InstrAPKs2
    Results --> TasksJSON

    style Phase1 fill:#f9f9f9
    style Phase2 fill:#f0f0ff
    style Phase3 fill:#f0fff0
```

Data flows one-way through the three phases:

1. **Phase 1 (Pre-Processing)**: `.mop` specifications are compiled into AspectJ aspects and Java monitors by rv-monitor-generator. These monitors are woven into APKs by rv-instrumentation, producing instrumented APKs. Static analysis (GATOR/GESDA/REACH) runs on the instrumented APKs, producing `.wtg`, `.gesda`, and `.reach` files co-located with the APKs. Each step is independently skippable.

2. **Phase 2 (Execution)**: `ExecutionController` translates `ExperimentConfig` into `PlatformConfig` (the bridge pattern) and delegates to `Platform.run()`. All task execution, emulator management, coverage tracking, and result processing happen inside rv-platform. rv-experiment receives only `{total_tasks, successful_tasks, failed_tasks}` back (INV-EXP-02).

3. **Phase 3 (Post-Processing)**: `PostProcessor` reads `tasks.json` (via `TaskStorage`) to generate `instrument_errors.json` tracking which APKs failed instrumentation. It also writes `experiment_completion.json` with timestamps and completion status.

### Resume Data Flow

On resume, the data flow changes:
- Phase 1 is effectively bypassed: all skip flags are forced to `True` (INV-EXP-13), so no pre-processing artifacts are regenerated.
- Phase 2 reuses the existing `tasks.json`: rv-platform loads completed tasks, skips them via identity matching, and executes only remaining tasks.
- Phase 3 runs normally, updating diagnostics with the combined results.

---

## Core Components

### ExperimentController

**Purpose**: Central orchestrator that coordinates the three-phase experiment workflow.

**Location**: `src/rv_experiment/experiment/experiment_controller.py`

**Key Classes**:
- `ExperimentController`: Facade over PreProcessor, ExecutionController, and PostProcessor. Manages experiment lifecycle from initialization through completion.

**Dependencies**:
- Internal: `config.py`, `workflow/pre_processor.py`, `workflow/execution_controller.py`, `workflow/post_processor.py`
- External: rv-android-core (ErrorHandler, LoggingManager, AbstractTool), rv-tools (ToolFactory)

### ExperimentConfig

**Purpose**: Type-safe experiment configuration with Pydantic validation and JIT sub-module config creation.

**Location**: `src/rv_experiment/config.py`

**Key Classes**:
- `ExperimentConfig(BaseValidatedModel)`: Holds all experiment parameters. Provides `get_monitored_operations_config()`, `get_instrumentation_config()`, `get_static_analysis_config()`, and `get_module_config()` for on-demand sub-module configuration. `get_rv_instrumentation_config()` is an alias for `get_instrumentation_config()`.

**Dependencies**:
- Internal: `constants.py`
- External: rv-android-core (BaseValidatedModel, ToolConfig, ConfigurationError), rv-monitor-generator (RVGeneratorConfig), rv-instrumentation (RVInstrumentationConfig), rv-static-analysis (RVStaticAnalysisConfig)

### PreProcessor

**Purpose**: Phase 1 -- executes monitor generation, APK instrumentation, and static analysis as a sequential pipeline with independent skip capabilities.

**Location**: `src/rv_experiment/experiment/workflow/pre_processor.py`

**Key Classes**:
- `PreProcessor`: Manages three ordered pre-processing steps. Uses lazy imports for optional sub-modules (rv-monitor-generator, rv-instrumentation, rv-static-analysis).

**Dependencies**:
- Internal: `config.py`
- External: rv-monitor-generator (optional), rv-instrumentation (optional), rv-static-analysis (optional)

### ExecutionController

**Purpose**: Phase 2 -- bridges rv-experiment configuration to rv-platform, translating `ExperimentConfig` into `PlatformConfig` and delegating execution.

**Location**: `src/rv_experiment/experiment/workflow/execution_controller.py`

**Key Classes**:
- `ExecutionController`: Creates PlatformConfig from ExperimentConfig, instantiates Platform, calls `Platform.run()`. Returns only aggregate success/failure counts (INV-EXP-02).

**Dependencies**:
- Internal: `config.py`
- External: rv-platform (Platform, PlatformConfig, TaskStorage)

### PostProcessor

**Purpose**: Phase 3 -- generates instrumentation error reports and experiment completion diagnostics.

**Location**: `src/rv_experiment/experiment/workflow/post_processor.py`

**Key Classes**:
- `PostProcessor`: Coordinates ResultManager for error JSON generation and writes `experiment_completion.json`.

**Dependencies**:
- Internal: `workflow/result_manager.py`
- External: rv-platform (TaskStorage)

### CLI (__main__.py)

**Purpose**: Click-based CLI providing four commands (`run`, `config`, `list-tools`, `validate`) and tool specification DSL parsing.

**Location**: `src/rv_experiment/__main__.py`

**Key Functions**:
- `run()`: Main experiment execution command with tool DSL, skip flags, resume support
- `config()`: Configuration template generation
- `list_tools()`: Tool discovery and display
- `validate()`: Configuration file validation

**Dependencies**:
- Internal: `config.py`, `factories/configuration_factory.py`, `experiment/experiment_controller.py`
- External: Click, rv-tools (ToolRegistry)

### ConfigurationFactory

**Purpose**: Factory for creating ExperimentConfig from CLI arguments, JSON files, dictionaries, and templates.

**Location**: `src/rv_experiment/factories/configuration_factory.py`

**Key Classes**:
- `ConfigurationFactory`: Provides `create_cli_config()`, `create_basic_template()`, `create_advanced_template()`, `create_llm_template()`, and `parse_tool_specifications()`.

**Dependencies**:
- Internal: `config.py`
- External: rv-android-core (ToolConfig)

---

## NFR Support

How the architecture supports non-functional requirements from `docs/PRD.md` Section 7.

| NFR | PRD ID | Priority | Architectural Support |
|-----|--------|----------|----------------------|
| Modularity | NFR01 | P0 | rv-experiment is an independent uv workspace module with clear boundaries; orchestrates other modules without embedding their logic |
| Extensibility | NFR02 | P1 | Tool discovery via ToolRegistry; new tools are added to rv-tools or as external modules without modifying rv-experiment |
| Testability | NFR03 | P1 | 12 test files covering configuration validation, JIT configs, JSON serialization, resume CLI, and post-processing; test fixtures mock sub-modules |
| Resilience | NFR04 | P1 | Instrumentation failure fallback (INV-EXP-08); optional module import error handling; ErrorHandler decorators on key methods |
| Configurability | NFR05 | P0 | ExperimentConfig Pydantic model with JIT sub-module configs; CLI with DSL; JSON config files; environment variable support; priority-based RVSEC_HOME resolution |
| Reproducibility | NFR08 | P0 | Experiment config persistence (`experiment_config.json`); resume via `tasks.json` detection; deterministic results directory naming |

---

## Key Interfaces

### ExperimentConfig JIT Configuration

```python
class ExperimentConfig(BaseValidatedModel):
    """Central configuration for Android testing experiments.

    JIT methods create sub-module configs on demand, avoiding
    eager validation of modules that may be skipped or not installed.
    """

    def get_monitored_operations_config(self) -> "RVGeneratorConfig":
        """Create monitor generation config with RVSEC_HOME resolution."""
        ...

    def get_instrumentation_config(self) -> "RVInstrumentationConfig":
        """Create instrumentation config with validated paths."""
        ...

    def get_rv_instrumentation_config(self) -> "RVInstrumentationConfig":
        """Alias for get_instrumentation_config()."""
        ...

    def get_static_analysis_config(self) -> "RVStaticAnalysisConfig":
        """Create static analysis config for GATOR/GESDA/REACH."""
        ...

    def get_module_config(self, module_name: str) -> Union[...]:
        """Dispatch to the appropriate get_*_config() method by module name."""
        ...
```

### ExperimentController Workflow

```python
class ExperimentController:
    """Orchestrate three-phase experiment workflow."""

    def __init__(self, config: ExperimentConfig, experiment_id: str = None):
        """Initialize with workflow components."""
        ...

    def run(self) -> bool:
        """Execute Phase 1 -> Phase 2 -> Phase 3 sequentially."""
        ...
```

### Workflow Component Interaction

```mermaid
%%{init: {'theme': 'neutral'}}%%
classDiagram
    class ExperimentController {
        -config: ExperimentConfig
        -pre_processor: PreProcessor
        -execution_controller: ExecutionController
        -post_processor: PostProcessor
        +run() bool
    }

    class PreProcessor {
        -config: ExperimentConfig
        +process() List~App~
    }

    class ExecutionController {
        -config: ExperimentConfig
        -platform: Platform
        +setup(tools, apps)
        +run() bool
    }

    class PostProcessor {
        -results_dir: str
        -result_manager: ResultManager
        +process()
    }

    class ExperimentConfig {
        +name: str
        +tool_configs: List~ToolConfig~
        +generate_monitors: bool
        +instrument_apks: bool
        +run_static_analysis: bool
        +resume_mode: bool
        +get_monitored_operations_config() RVGeneratorConfig
        +get_instrumentation_config() RVInstrumentationConfig
        +get_rv_instrumentation_config() RVInstrumentationConfig
        +get_static_analysis_config() RVStaticAnalysisConfig
        +get_module_config(module_name) Union
        +validate()
    }

    ExperimentController --> PreProcessor
    ExperimentController --> ExecutionController
    ExperimentController --> PostProcessor
    ExperimentController --> ExperimentConfig
    PreProcessor --> ExperimentConfig
    ExecutionController --> ExperimentConfig
```

---

## Scenarios

Key use cases that validate the architecture.

### Scenario 1: Full Experiment Run

**Description**: A researcher runs a complete experiment with JCA specifications, two tools, and all pre-processing enabled.

**Flow**:
1. User invokes `rv-experiment run --tools monkey,droidbot:dfs_greedy --specification-set jca --apks-dir ./apks/`
2. CLI parses DSL into two `ToolConfig` objects; `ConfigurationFactory` creates `ExperimentConfig`
3. `ExperimentController.run()` starts Phase 1: `PreProcessor` generates monitors from JCA `.mop` files, instruments APKs with monitors, runs GATOR/GESDA/REACH static analysis
4. Phase 2: `ExecutionController` translates config to `PlatformConfig`, delegates to `Platform.run()` which manages emulators, executes tools, tracks coverage
5. Phase 3: `PostProcessor` generates `instrument_errors.json` and `experiment_completion.json`
6. Controller returns `True`

### Scenario 2: Docker Resume After Container Restart

**Description**: A Docker container running an experiment is killed mid-execution and restarted with the same configuration.

**Flow**:
1. Container starts with `RV_EXPERIMENT_NAME=batch_01`; `docker-entrypoint.sh` translates to `--name batch_01`
2. CLI detects `results/batch_01/tasks.json` exists; enables resume mode
3. All pre-processing skip flags are forced to `True` (INV-EXP-13)
4. Phase 1: `PreProcessor.process()` executes but all steps are skipped
5. Phase 2: rv-platform loads `tasks.json`, skips completed tasks, executes remaining tasks
6. Phase 3: `PostProcessor` updates diagnostics with new completion data

### Scenario 3: Missing Sub-Module Graceful Degradation

**Description**: rv-monitor-generator is not installed, but the experiment should proceed with pre-instrumented APKs.

**Flow**:
1. User invokes `rv-experiment run --tools monkey --skip-monitors --apks-dir ./instrumented_apks/`
2. `PreProcessor` skips monitor generation (flag is `False`)
3. If instrumentation step encounters `ImportError` for rv-instrumentation, it logs a warning and copies original APKs as fallback
4. Execution and post-processing proceed normally

---

## Extension Points

- **Adding tools**: Register new tools in rv-tools via `ToolRegistry`. rv-experiment discovers them automatically through `list-tools` and the DSL parser.
- **Custom specification sets**: Use `--specification-set custom --custom-specs-dir /path/to/mop/files` to provide user-defined MOP specifications without modifying rv-experiment code.
- **Configuration templates**: Add new template methods to `ConfigurationFactory` for specialized experiment configurations.
- **Docker deployment patterns**: Create new Docker Compose files with different container counts, port assignments, and delay configurations for parallel experiments.

## Dependencies

### Internal (rv-android modules)

| Module | Purpose |
|--------|---------|
| rv-android-core | Domain models (App, ToolConfig), ErrorHandler, LoggingManager, BaseValidatedModel, constants |
| rv-platform | Platform execution engine, PlatformConfig, TaskStorage |
| rv-tools | ToolRegistry for tool discovery, ToolFactory for tool instantiation |
| rv-monitor-generator | Phase 1 Step 1: monitor generation from MOP specifications (optional import) |
| rv-instrumentation | Phase 1 Step 2: APK instrumentation with monitor weaving (optional import) |
| rv-static-analysis | Phase 1 Step 3: GATOR/GESDA/REACH static analysis (optional import) |

Note: rv-screen-parser and rv-coverage are declared in `pyproject.toml` but have no imports in source code. They are unused dependencies.

### External

| Package | Version | Purpose |
|---------|---------|---------|
| pydantic | >=2.9.0 | Configuration validation (ExperimentConfig extends BaseValidatedModel) |
| matplotlib | >=3.9.0 | Declared dependency (used for result visualization) |
| click | (via rv-android-core) | CLI framework for command parsing and help generation |

## Testing Strategy

| Type | Location | Purpose |
|------|----------|---------|
| Unit | tests/test_config_validation.py | ExperimentConfig field validation and defaults |
| Unit | tests/test_config_jit.py | JIT sub-module configuration creation |
| Unit | tests/test_config_json.py | JSON serialization/deserialization round-trips |
| Unit | tests/test_configuration_factory.py | ConfigurationFactory creation methods |
| Unit | tests/test_constants.py | Directory constants and path utilities |
| Unit | tests/test_post_processor.py | PostProcessor diagnostics generation |
| Integration | tests/experiment/ | ExperimentController three-phase workflow |
| Integration | tests/test_resume_cli.py | Resume mechanism (--name, --resume-dir) |

## Related Documentation

- [Domain Spec](../../openspec/specs/experiment/spec.md) - Requirements and invariants for the experiment orchestration domain
- [PRD](../../docs/PRD.md) - Product Requirements Document (FR15-FR17, NFR01-08)
- [CLAUDE.md](../../CLAUDE.md) - Quick reference for Claude Code
- [Module CLAUDE.md](../CLAUDE.md) - rv-experiment development guide
