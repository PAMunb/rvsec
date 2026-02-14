# RV-Android Architecture

## 1. Introduction

RV-Android is a platform for Android application testing using runtime verification techniques with AI-driven testing capabilities. The platform uses a modular uv-based architecture with modules in the `modules` directory. The platform combines static analysis, dynamic testing, formal verification, and LLM-guided exploration to detect issues in Android applications, leveraging JavaMOP (Monitoring-Oriented Programming) and RV-Monitor for property verification.

This document details the architecture of the RV-Android platform, focusing on its modular structure, component-based task execution system, and LLM-guided testing capabilities.

### 1.1 Core Design Principles

The RV-Android architecture is built on several key principles:

1.  **Modular Architecture**: The system is divided into independent, reusable modules managed by uv. Each module has a well-defined responsibility and clear separation of concerns.
2.  **Component-Based Architecture**: Within modules, a component-based approach with clear interfaces enables flexible system composition.
3.  **Event-Driven Communication**: Decoupled components communicate through an event bus system.
4.  **LLM Integration**: Integration with language models for intelligent test generation.
5.  **Error Handling**: Comprehensive error handling and recovery mechanisms.

## 2. High-Level System Architecture

The RV-Android platform is composed of a set of interconnected modules, each responsible for a specific part of the testing process.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              RV-Android Platform                            │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                              Core Modules                            │   │
│  │                                                                      │   │
│  │  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐│   │
│  │  │ rv-android-core  │    │   rv-platform    │    │     rv-tools     ││   │
│  │  └──────────────────┘    └──────────────────┘    └──────────────────┘│   │
│  │  ┌──────────────────┐                                                │   │
│  │  │ rv-uiautomator   │                                                │   │
│  │  └──────────────────┘                                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                           Testing Modules                            │   │
│  │                                                                      │   │
│  │  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐│   │
│  │  │  rv-instrument.. │    │ rv-static-analy… │    │  rv-monitor-gen… ││   │
│  │  └──────────────────┘    └──────────────────┘    └──────────────────┘│   │
│  │  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐│   │
│  │  │   rv-coverage    │    │   rv-evaluator   │    │   rv-experiment  ││   │
│  │  └──────────────────┘    └──────────────────┘    └──────────────────┘│   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       LLM Testing Tools                              │   │
│  │                                                                      │   │
│  │  ┌──────────────────┐    ┌──────────────────┐                       │   │
│  │  │    rv-agent      │    │ rv-screen-parser │                       │   │
│  │  │  (Main Tool)     │    │                  │                       │   │
│  │  └──────────────────┘    └──────────────────┘                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 3. Modules Description

The RV-Android platform is organized into the following modules:

### Core Infrastructure:
*   **rv-android-core**: Foundation module providing domain models, utilities, and interfaces for all other modules
*   **rv-platform**: Task execution orchestration, device management, and result collection
*   **rv-tools**: Testing tool registry and plugin system with factory patterns
*   **rv-uiautomator**: Shared UIAutomator components providing direct device interaction capabilities

### Analysis and Processing:
*   **rv-instrumentation**: APK instrumentation with monitor weaving capabilities
*   **rv-static-analysis**: Static analysis tools (GATOR, GESDA, REACH) for Android applications
*   **rv-monitor-generator**: JavaMOP/RV-Monitor integration for generating runtime verification monitors
*   **rv-coverage**: Coverage analysis and tracking for monitored operations
*   **rv-screen-parser**: Android UI parsing with visitor patterns for state analysis

### AI and LLM Integration:
*   **rv-agent**: Main LLM-driven testing tool using LangGraph for workflow orchestration, supporting multiple execution modes (algorithm-only, LLM-only, hybrid)

### Experiment Orchestration:
*   **rv-experiment**: Experiment orchestration and coordination system
*   **rv-evaluator**: Result evaluation and report generation

## 4. Task Execution Engine

The task execution engine orchestrates individual testing tasks using a component-based architecture.

### 4.0 Workflow Execution and Data Flow

The RV-Android platform follows a structured workflow execution pattern that ensures proper data flow and component coordination:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          Experiment Workflow                                 │
│                                                                              │
│  ExperimentController                                                        │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐   │
│  │                 │    │                 │    │                         │   │
│  │  Pre-Processor  │───►│ ExecutionCtrl   │───►│    Post-Processor       │   │
│  │                 │    │                 │    │                         │   │
│  └─────────────────┘    └─────────────────┘    └─────────────────────────┘   │
│                                 │                          │                 │
│                                 ▼                          ▼                 │
│                    ┌─────────────────┐          ┌─────────────────┐          │
│                    │                 │          │                 │          │
│                    │ ExecutionMgr    │          │  ResultManager  │          │
│                    │                 │          │                 │          │
│                    └─────────────────┘          └─────────────────┘          │
│                             │                                                │
│                             ▼                                                │
│                    ┌─────────────────┐                                       │
│                    │                 │                                       │
│                    │  TaskExecutor   │                                       │
│                    │                 │                                       │
│                    └─────────────────┘                                       │
└──────────────────────────────────────────────────────────────────────────────┘
```

#### 4.0.1 Data Flow Architecture

The data flow architecture ensures component coordination without singleton dependencies:

```python
# 1. ExperimentController creates core infrastructure
class ExperimentController:
    def __init__(self):
        # Create single TaskStorage instance
        storage_file = os.path.join(self.results_dir, "tasks.json")
        self.task_storage = TaskStorage(storage_file)

        # Create WorkflowFactory with TaskStorage
        self.factory = WorkflowFactory(self.task_storage, self.event_bus)

        # Create workflow components with proper dependencies
        self.pre_processor = self.factory.create_pre_processor(self.results_dir)
        self.execution_controller = self.factory.create_execution_controller()
        self.post_processor = self.factory.create_post_processor(self.results_dir)
        self.result_manager = self.factory.create_result_manager(self.results_dir)

# 2. WorkflowFactory ensures proper dependency injection
class WorkflowFactory:
    def create_result_manager(self, results_dir: str) -> ResultManager:
        return ResultManager(results_dir, self.storage, self.event_bus)

    def create_post_processor(self, results_dir: str) -> PostProcessor:
        result_manager = self.create_result_manager(results_dir)
        return PostProcessor(results_dir, self.event_bus, execution_controller, result_manager)

# 3. TaskExecutor coordinates component execution with emulator lifecycle
class TaskExecutor:
    def _execute_coordinated_components(self, context: Dict[str, Any]) -> None:
        # Phase 1: Load static data
        static_component.execute(context)

        # Phase 2: Initialize coverage tracking
        coverage_component.execute(context)

        # Phase 3: Emulator session with lifecycle management
        with emulator_component.start_emulator("RVSec") as android:
            emulator_component.install_app(android, self.task.app)
            logcat_component.start_capture()
            coverage_component.start_tracking()
            tool_component.execute(context)
            coverage_component.stop_tracking()
            coverage_component.process_results()
            logcat_component.stop_capture()
```

#### 4.0.2 Key Architectural Features

1.  **Dependency Injection**: Components receive dependencies through constructors.
2.  **Emulator Lifecycle Management**: The TaskExecutor manages emulator startup and shutdown.
3.  **Direct Repository Usage**: Direct use of LogcatRepository for simplified data flow.
4.  **Integrated Result Processing**: The PostProcessor uses an injected ResultManager for result generation.

#### 4.0.3 Component Coordination Flow

```
Static Analysis → Coverage Init → Emulator Start → App Install → Logcat Start →
Coverage Track → Tool Execute → Coverage Stop → Results Process → Logcat Stop →
Repository Export → ResultManager Generate → CSV/JSON Output
```

### 4.1 Task Model and Lifecycle

Tasks in RV-Android follow a lifecycle with detailed state tracking:

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│              │  │              │  │              │  │              │
│   CREATED    │──►  CONFIGURED  │──►INITIALIZING  │──►    READY     │
│              │  │              │  │              │  │              │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
                                                              │
┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│              │  │              │  │              │         │
│   CLEANUP    │◄─┤   COMPLETED  │◄─┤   RUNNING    │◄────────┘
│              │  │              │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
       │                                   │
       ▼                                   ▼
┌──────────────┐                   ┌──────────────┐
│              │                   │              │
│   ARCHIVED   │                   │    ERROR     │
│              │                   │              │
└──────────────┘                   └──────────────┘
```

### 4.2 Component-Based Task Execution

The task execution system uses a component-based architecture where each aspect of task execution is handled by specialized components:

1.  **EmulatorComponent**: Manages emulator lifecycle and configuration.
2.  **LogcatComponent**: Handles logcat capture and analysis.
3.  **ToolExecutionComponent**: Executes testing tools on the device.
4.  **CoverageComponent**: Tracks and analyzes coverage metrics.
5.  **StaticAnalysisComponent**: Performs static analysis integration.

### 4.3 Task Storage and Management

The platform includes a task storage system with transaction support and atomic operations.

## 5. Testing Tools and Variant System

### 5.1 Tool Variant Architecture

RV-Android implements a tool variant system that enables precise tool configuration and selection. Each tool supports multiple variants that represent different operational modes and parameter sets.

#### 5.1.1 Variant System Components

```python
class AbstractTool:
    @classmethod
    def get_variants(cls) -> Dict[str, Dict[str, Any]]:
        """Return available variants with their configurations."""
        return {
            "default": {...},
            "variant1": {...},
            "variant2": {...}
        }

    @classmethod
    def get_tool_spec(cls) -> ToolSpec:
        """Return tool specification for registration."""
        return cls.TOOL_SPEC

    def configure(self, config: Dict[str, Any]) -> None:
        """Apply variant configuration to tool instance."""
        pass
```

#### 5.1.2 Available Tools

The platform includes the following tools:

**Third-Party Tools**:
- **APE Tool** (5 variants): default, sata, bfs, dfs, random
- **DroidBot Tool** (6 variants): default, dfs_greedy, bfs_greedy, dfs_naive, bfs_naive, random
- **Monkey**: default, fast, stress variants
- **Ares**: default, debug, fast variants
- **DroidMate**: default, systematic, quick, research variants
- **FastBot**: default, conservative, aggressive, balanced variants
- **Humanoid**: default, visual, nlp, hybrid variants
- **QTesting**: default, qlearning, dqn, ddqn variants

**RV-Android Tools**:
- **rv-agent**: Main LLM-driven testing tool (see Section 6)

#### 5.1.3 CLI Usage Examples

```bash
# Use default variant
python -m rv_experiment run --tools droidbot

# Use specific variant
python -m rv_experiment run --tools droidbot:dfs_greedy

# Multiple tools with variants
python -m rv_experiment run --tools ape:sata,droidbot:bfs_greedy,rv-agent:multimode
```

## 6. RV-Agent - LLM-Guided Testing

RV-Agent is the main LLM-driven testing tool in the RV-Android platform. It uses LangGraph for workflow orchestration and supports multiple execution modes.

### 6.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                               RV-Agent                                      │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        Core Components                               │   │
│  │                                                                      │   │
│  │  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐│   │
│  │  │   AgentFactory   │───►│     RVAgent      │◄───│  RVAgentConfig   ││   │
│  │  └──────────────────┘    │   (LangGraph)    │    └──────────────────┘│   │
│  │                          └──────────────────┘                        │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Exploration Components                           │   │
│  │                                                                      │   │
│  │  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐│   │
│  │  │  RVAgentStrategy │    │  RoutingManager  │    │   LLMClient      ││   │
│  │  │  - Successor     │    │  - LLM/Algorithm │    │  - SGLang        ││   │
│  │  │    Tracker       │    │    routing       │    │  - Qwen3-VL      ││   │
│  │  │  - Plateau       │    │  - Fallback      │    │                  ││   │
│  │  │    Detector      │    │                  │    │                  ││   │
│  │  └──────────────────┘    └──────────────────┘    └──────────────────┘│   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        Memory Systems                                │   │
│  │                                                                      │   │
│  │  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐│   │
│  │  │MemoryCoordinator │    │ DynamicStateGraph│    │ UICoverageTracker││   │
│  │  └──────────────────┘    └──────────────────┘    └──────────────────┘│   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                     Device Interaction                               │   │
│  │                                                                      │   │
│  │  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐│   │
│  │  │ DeviceInterface  │    │  ToolExecutor    │    │  ImageHandler    ││   │
│  │  └──────────────────┘    └──────────────────┘    └──────────────────┘│   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Execution Modes

RV-Agent supports three execution modes:

| Mode | Description | LLM Usage |
|------|-------------|-----------|
| `pure_algorithm` | Algorithmic exploration using RVAgentStrategy | None |
| `llm_only` | LLM decides all actions | 100% |
| `multimode` | Hybrid approach with routing | 70% LLM / 30% Algorithm |

### 6.3 LangGraph Workflow

The agent uses LangGraph for workflow orchestration:

```
           start
             ↓
         parse_ui
             ↓
      decision_router
     ↙      ↓      ↘
  algorithm  llm   end
     ↓        ↓
algorithm_node  capture_screenshot
     ↓        ↓
     │     llm_generate
     │        ↓
     │    validation_router
     │     ↙       ↘
     │  execute  algorithm_node
     │     ↓         ↓
     └─→ execute ←───┘
           ↓
         learn
           ↓
          END
```

### 6.4 RVAgentStrategy

The main exploration strategy includes:

1.  **Successor Tracker**: Tracks state transitions and re-enables actions if successors are not fully explored. Solves the "combobox problem" where clicking an element opens a dropdown that needs exploration.

2.  **Plateau Detector**: Monitors exploration progress and detects stagnation when no new states are discovered over a configurable window.

3.  **MOP Prioritization**: Prioritizes actions that lead to Monitored Operations (security-sensitive methods) when static analysis data is available.

4.  **DynamicStateGraph**: Maintains a graph of explored states and transitions for coverage-optimized exploration.

### 6.5 LLM Backend Configuration

RV-Agent uses SGLang (OpenAI-compatible API) as the LLM backend:

```python
class RVAgentConfig(BaseValidatedModel):
    # LLM Configuration
    llm_model: str = "Qwen/Qwen3-VL-4B-Instruct"
    llm_base_url: str = "http://192.168.0.21:30000/v1"
    llm_temperature: float = 0.01
    llm_top_p: float = 0.6
    llm_max_tokens: int = 2048

    # Execution Mode
    agent_mode: str = "multimode"  # pure_algorithm, llm_only, multimode
    llm_probability: float = 0.7   # For multimode: 70% LLM / 30% algorithm
```

### 6.6 Memory Systems

RV-Agent uses a coordinated memory system:

- **ShortTermMemory**: Recent actions and states (configurable window size)
- **LongTermMemory**: Persistent state patterns and learned behaviors
- **UICoverageTracker**: Tracks UI element coverage and interaction history
- **DynamicStateGraph**: Exploration graph with state transitions

### 6.7 Stuck State Detection

The agent implements multiple recovery mechanisms:

1.  **Screen Hash Monitoring**: Detects when the screen doesn't change after actions
2.  **Deadlock Detection**: Identifies when no actions are available
3.  **Forced BACK**: Automatically navigates back after threshold consecutive stuck iterations
4.  **Loop Detection**: Prevents repetitive action sequences

### 6.8 Usage

```bash
# Run with multimode (default)
rv-agent --package-name com.example.app --device emulator-5554

# Run with pure algorithm (no LLM)
rv-agent --package-name com.example.app --agent-mode pure_algorithm

# Run with specific timeout
rv-agent --package-name com.example.app --timeout 600
```

## 7. Event-Driven Architecture

### 7.1 Event Bus System

The platform uses an event bus for decoupled component communication:

```python
class EventBus:
    # Channel definitions
    LIFECYCLE_CHANNEL = "lifecycle"
    ERROR_CHANNEL = "error"
    METRICS_CHANNEL = "metrics"
    LLM_CHANNEL = "llm"

    def publish_task_event(self, event_type: EventType, task_id: str,
                          task_config: Dict[str, Any], details: Dict[str, Any] = None,
                          source: str = "Unknown", channel: str = LIFECYCLE_CHANNEL):
        """Publish task-related events with full context."""
```

### 7.2 Event Types

```python
class EventType(Enum):
    # Experiment lifecycle
    EXPERIMENT_STARTED = "experiment_started"
    EXPERIMENT_COMPLETED = "experiment_completed"
    EXPERIMENT_FAILED = "experiment_failed"

    # Task lifecycle
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"

    # Component events
    EMULATOR_STARTED = "emulator_started"
    EMULATOR_STOPPED = "emulator_stopped"
    TOOL_STARTED = "tool_started"
    TOOL_COMPLETED = "tool_completed"

    # LLM events
    LLM_REQUEST_SENT = "llm_request_sent"
    LLM_RESPONSE_RECEIVED = "llm_response_received"
    LLM_ERROR = "llm_error"
```

## 8. Error Handling and Recovery

### 8.1 Error Management

The platform includes an error handling system with classification and recovery strategies:

```python
class ErrorHandler:
    def __init__(self):
        self.recovery_strategies = {
            EmulatorError: EmulatorRecoveryStrategy(),
            ToolError: ToolRecoveryStrategy(),
            LLMError: LLMRecoveryStrategy(),
            ExecutionError: GeneralRecoveryStrategy()
        }

    def handle_error(self, error: Exception, context: Dict[str, Any]) -> bool:
        """Handle error with appropriate recovery strategy."""
        error_type = self._classify_error(error)
        self.error_metrics.record_error(error_type, context)

        recovery_strategy = self.recovery_strategies.get(type(error))
        if recovery_strategy:
            return recovery_strategy.attempt_recovery(error, context)

        return self._default_error_handling(error, context)
```

## 9. Coverage Analysis System

### 9.1 Repository Architecture

The RV-Android platform implements a coverage analysis system with direct repository integration.

```python
class CoverageTracker:
    def __init__(self, logcat_file: str, static_data: Optional[StaticAnalysisData] = None):
        self.repository = LogcatRepository()
        if static_data:
            self._initialize_from_static_data(static_data)

    def _process_logcat_line(self, line: str) -> None:
        """Process logcat line and update repository."""
        error_log, coverage_log = parse_logcat_line(line)

        if error_log:
            self.repository.register_rv_error(error_log)
        elif coverage_log:
            self.repository.register_method_call(coverage_log)
```

### 9.2 Coverage Data Flow

```
Static Analysis → LogcatRepository Initialization →
CoverageTracker → Direct Repository Updates →
Metrics Calculation → Result Processing →
CSV/JSON Export
```

## 10. Configuration and Extensibility

### 10.1 Environment Variables

- `RVSEC_HOME`: Required for monitor generation (path to RVSEC installation)
- `ANDROID_HOME`: Android SDK path for emulator management
- `RV_PYDANTIC=true`: Enable development validation
- `RVAGENT_MODE`: Override rv-agent execution mode

### 10.2 Configuration Files

Tool configurations support unified configuration through Pydantic models. Experiment configurations use JSON format with validation.

## 11. Testing and Validation

### 11.1 Test Organization

```bash
# Run all tests from workspace root
uv run pytest

# Test specific module
uv run pytest modules/rv-android-core/tests/ -v

# Run with coverage
uv run pytest --cov=modules --cov-report=html
```

### 11.2 Test Categories

- Unit tests for individual components and functions
- Integration tests for module interactions
- End-to-end tests for complete workflows

## 12. Conclusion

The RV-Android platform provides a modular and extensible architecture for testing Android applications with runtime verification. Its key features include a component-based design, LLM integration through rv-agent, event-driven communication, and comprehensive error handling. The platform serves as a foundation for research and development in Android application testing and verification.
