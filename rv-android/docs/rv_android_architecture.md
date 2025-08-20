# RV-Android Architecture

## 1. Introduction

RV-Android is a platform for Android application testing using runtime verification techniques with AI-driven testing capabilities. The platform uses a modular Poetry-based architecture with modules in the `modules` directory. The platform combines static analysis, dynamic testing, formal verification, and LLM-guided exploration to detect issues in Android applications, leveraging JavaMOP (Monitoring-Oriented Programming) and RV-Monitor for property verification.

This document details the architecture of the RV-Android platform, focusing on its modular structure, component-based task execution system, and LLM-guided testing capabilities.

### 1.1 Core Design Principles

The RV-Android architecture is built on several key principles:

1.  **Modular Architecture**: The system is divided into independent, reusable modules managed by Poetry. Each module has a well-defined responsibility and clear separation of concerns.
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
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                              Core Modules                             │  │
│  │                                                                     │  │
│  │  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │  │ rv-android-core  │    │   rv-platform    │    │     rv-tools     │  │
│  │  └──────────────────┘    └──────────────────┘    └──────────────────┘  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                           Testing Modules                             │  │
│  │                                                                     │  │
│  │  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │  │  rv-instrument.. │    │ rv-static-analy… │    │  rv-monitor-gen… │  │
│  │  └──────────────────┘    └──────────────────┘    └──────────────────┘  │
│  │  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │  │   rv-coverage    │    │   rv-evaluator   │    │   rv-experiment  │  │
│  │  └──────────────────┘    └──────────────────┘    └──────────────────┘  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                       LLM and UI Modules                            │  │
│  │                                                                     │  │
│  │  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐  │
│  │  │      rv-llm      │    │ rv-screen-parser │    │  rvandroid-tool  │  │
│  │  └──────────────────┘    └──────────────────┘    └──────────────────┘  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 3. Modules Description

The RV-Android platform is organized into the following modules:

### Core Infrastructure:
*   **rv-android-core**: Foundation module providing domain models, utilities, and interfaces for all other modules
*   **rv-platform**: Task execution orchestration, device management, and result collection
*   **rv-tools**: Testing tool registry and plugin system with factory patterns

### Analysis and Processing:
*   **rv-instrumentation**: APK instrumentation with monitor weaving capabilities  
*   **rv-static-analysis**: Static analysis tools (GATOR, GESDA, REACH) for Android applications
*   **rv-monitor-generator**: JavaMOP/RV-Monitor integration for generating runtime verification monitors
*   **rv-coverage**: Coverage analysis and tracking for monitored operations
*   **rv-screen-parser**: Android UI parsing with visitor patterns for state analysis

### AI and LLM Integration:
*   **rv-llm**: Language model integration framework with multiple backend support
*   **rvandroid-tool**: AI-driven testing tool with LLM integration and server interface
*   **rvdroid-tool**: Alternative testing tool implementation

### Experiment Orchestration:  
*   **rv-experiment**: Experiment orchestration and coordination system
*   **rv-evaluator**: Result evaluation and report generation

## 4. Task Execution Engine

The task execution engine orchestrates individual testing tasks using a component-based architecture.

### 4.0 Workflow Execution and Data Flow

The RV-Android platform follows a structured workflow execution pattern that ensures proper data flow and component coordination:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          Experiment Workflow                                │
│                                                                              │
│  ExperimentController                                                        │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐  │
│  │                 │    │                 │    │                         │  │
│  │  Pre-Processor  │───►│ ExecutionCtrl   │───►│    Post-Processor       │  │
│  │                 │    │                 │    │                         │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────────────┘  │
│                                 │                          │                │
│                                 ▼                          ▼                │
│                    ┌─────────────────┐          ┌─────────────────┐        │
│                    │                 │          │                 │        │
│                    │ ExecutionMgr    │          │  ResultManager  │        │
│                    │                 │          │                 │        │
│                    └─────────────────┘          └─────────────────┘        │
│                             │                                              │
│                             ▼                                              │
│                    ┌─────────────────┐                                     │
│                    │                 │                                     │
│                    │  TaskExecutor   │                                     │
│                    │                 │                                     │
│                    └─────────────────┘                                     │
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
        # ResultManager receives TaskStorage reference
        return ResultManager(results_dir, self.storage, self.event_bus)
    
    def create_post_processor(self, results_dir: str) -> PostProcessor:
        # PostProcessor receives ResultManager instance
        result_manager = self.create_result_manager(results_dir)
        return PostProcessor(results_dir, self.event_bus, execution_controller, result_manager)

# 3. PostProcessor uses injected ResultManager
class PostProcessor:
    def _analyze_results(self):
        # Use the configured ResultManager
        if self.result_manager:
            self.result_manager.generate_reports()

# 4. TaskExecutor coordinates component execution with emulator lifecycle
class TaskExecutor:
    def _execute_coordinated_components(self, context: Dict[str, Any]) -> None:
        # Phase 1: Load static data
        static_component.execute(context)
        
        # Phase 2: Initialize coverage tracking  
        coverage_component.execute(context)
        
        # Phase 3: Emulator session with lifecycle management
        with emulator_component.start_emulator("RVSec") as android:
            # Install app
            emulator_component.install_app(android, self.task.app)
            
            # Start tracking
            logcat_component.start_capture()
            coverage_component.start_tracking()
            
            # Execute tool
            tool_component.execute(context)
            
            # Stop tracking and process results
            coverage_component.stop_tracking()
            coverage_component.process_results()
            logcat_component.stop_capture()
```

#### 4.0.2 Key Architectural Features

The implementation provides several key architectural features:

1.  **Dependency Injection**: Components receive dependencies through constructors.
2.  **Emulator Lifecycle Management**: The TaskExecutor manages emulator startup and shutdown.
3.  **Direct Repository Usage**: Direct use of LogcatRepository for performance and simplified data flow.
4.  **Integrated Result Processing**: The PostProcessor uses an injected ResultManager for result generation.
5.  **Optimized Execution Flow**: A single ResultManager execution for efficient data processing.

#### 4.0.3 Component Coordination Flow

The coordinated execution ensures proper data flow:

```
Static Analysis → Coverage Init → Emulator Start → App Install → Logcat Start → 
Coverage Track → Tool Execute → Coverage Stop → Results Process → Logcat Stop → 
Repository Export → ResultManager Generate → CSV/JSON Output
```

This flow guarantees that:
- Static analysis data is loaded before coverage initialization.
- Coverage tracking runs during tool execution.
- Coverage data flows from task execution to result processing.
- Results are exported through the ResultManager.

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

#### 4.1.1 Task Model

The `Task` class provides a model with:

- **UUID-based Identification**: Task identification using UUIDs.
- **Configuration**: Task configuration including APK information, tool parameters, and execution settings.
- **State Transition Tracking**: History of state transitions with timestamps.
- **Result Management**: Result storage including metrics, errors, and coverage data.
- **Repository Integration**: Integration with coverage and error repositories.

```python
class Task(ITask):
    """
    Represents a single testing task within an experiment.
    """
    def __init__(self, config: TaskConfiguration):
        self.id = str(uuid.uuid4())
        self.config = config
        self.result = TaskResult()
        self.app: Optional[App] = None
        self.repository: Optional[LogcatRepository] = None
        
    def update_state(self, state: TaskState, error_message: Optional[str] = None) -> None:
        """Update task state with transition tracking."""
        self.result.add_state_transition(state)
        
        if state == TaskState.RUNNING:
            self.result.start_time = datetime.now()
        elif state in [TaskState.COMPLETED, TaskState.ERROR, TaskState.CANCELED]:
            self.result.end_time = datetime.now()
            if state == TaskState.ERROR and error_message:
                self.result.error_message = error_message
```

### 4.2 Component-Based Task Execution

The task execution system uses a component-based architecture where each aspect of task execution is handled by specialized components.

#### 4.2.1 TaskExecutor Architecture

```python
class TaskExecutor(ITaskExecutor):
    """
    Manages the execution of individual tasks using a component-based architecture.
    """
    
    def __init__(self, task: ITask, tool: AbstractTool, event_bus: Optional[EventBus] = None):
        self.task = task
        self.tool = tool
        self.event_bus = event_bus or get_event_bus()
        self.components = ComponentRegistry()
        self.performance_monitor = PerformanceMonitor.get_instance()
        self.error_handler = ErrorHandler.get_instance()
        
    def execute(self) -> bool:
        """Execute task with monitoring and error handling."""
        try:
            self.task.update_state(TaskState.RUNNING)
            self._publish_task_started_event()
            
            with self.performance_monitor.measure_time("task_execution_total", self.get_task_context()):
                # Initialize all components
                context = self.get_task_context()
                if not self.components.initialize_all(context):
                    raise TaskExecutionError("Failed to initialize components", self.task.id)
                
                # Execute all components in sequence
                for component in self.components.get_all():
                    if not component.execute(context):
                        raise TaskExecutionError(f"Component {component.name} execution failed", self.task.id)
                
                # Clean up all components
                self.components.cleanup_all(context)
            
            self.task.update_state(TaskState.COMPLETED)
            self._publish_task_completed_event()
            return True
            
        except Exception as e:
            self.error_handler.handle_error(e, self.get_task_context())
            self.task.update_state(TaskState.ERROR, str(e))
            self._publish_task_failed_event(str(e))
            self._cleanup_resources()
            return False
```

#### 4.2.2 Task Components

The system includes several specialized components:

1.  **EmulatorComponent**: Manages emulator lifecycle and configuration.
2.  **LogcatComponent**: Handles logcat capture and analysis.
3.  **ToolExecutionComponent**: Executes testing tools on the device.
4.  **CoverageComponent**: Tracks and analyzes coverage metrics.
5.  **StaticAnalysisComponent**: Performs static analysis integration.

```python
class BaseTaskComponent(ITaskComponent):
    """
    Base implementation for task execution components.
    """
    
    def initialize(self, context: Dict[str, Any]) -> bool:
        """Initialize component with task context."""
        self.logger.debug(f"Initializing component: {self.name}")
        return True
        
    def execute(self, context: Dict[str, Any]) -> bool:
        """Execute component's primary function."""
        self.logger.debug(f"Executing component: {self.name}")
        return self._execute_impl(context)
        
    def cleanup(self, context: Dict[str, Any]) -> bool:
        """Clean up component resources."""
        self.logger.debug(f"Cleaning up component: {self.name}")
        return True
```

### 4.3 Task Storage and Management

The platform includes a task storage system with transaction support and atomic operations.

```python
class TaskStorage(ITaskStorage):
    """
    Manages task persistence with atomic operations and transaction support.
    """
    
    def save(self) -> bool:
        """Save tasks using atomic file operations."""
        with self.lock:
            try:
                # Prepare data with UUID-based task serialization
                data = {
                    "version": 2,
                    "timestamp": datetime.now().isoformat(),
                    "tasks": [task.to_dict() for task in self.tasks.values()]
                }
                
                # Atomic write operation
                temp_file = f"{self.storage_file}.tmp"
                with open(temp_file, 'w') as f:
                    json.dump(data, f, indent=2)
                    f.fsync()
                
                # Atomic move
                shutil.move(temp_file, self.storage_file)
                return True
            except Exception as e:
                self.logger.error(f"Failed to save tasks: {e}")
                return False
```

## 5. Testing Tools and Variant System

### 5.1 Tool Variant Architecture

RV-Android implements a comprehensive tool variant system that enables precise tool configuration and selection. Each tool supports multiple variants that represent different operational modes and parameter sets.

#### 5.1.1 Variant System Components

```python
class AbstractTool:
    @classmethod
    def get_variants(cls) -> Dict[str, Dict[str, Any]]:
        """Return available variants with their configurations."""
        return {
            "default": {...},  # Base configuration
            "variant1": {...}, # Specialized configuration
            "variant2": {...}  # Alternative configuration
        }
    
    @classmethod  
    def get_tool_spec(cls) -> ToolSpec:
        """Return tool specification for registration."""
        return cls.TOOL_SPEC
        
    def configure(self, config: Dict[str, Any]) -> None:
        """Apply variant configuration to tool instance."""
        pass
```

#### 5.1.2 Tool Configuration Flow

The variant system follows a structured configuration flow:

```
CLI Input → ToolConfig Creation → Registry Validation → 
Variant Resolution → Configuration Merge → Tool Creation → Execution
```

This flow supports both predefined variants and custom configurations:

- **Predefined Variants**: Tools define standard variants in `get_variants()`
- **Custom Variants**: Users can override parameters while inheriting base configuration
- **Parameter Merging**: Base variant configuration + user overrides = final configuration

#### 5.1.3 Available Tool Variants

The platform includes the following tools with their variant support:

**APE Tool** (5 variants):
- `default`: Standard systematic exploration
- `sata`: State-aware testing approach
- `bfs`: Breadth-first search strategy
- `dfs`: Depth-first search strategy  
- `random`: Random exploration mode

**DroidBot Tool** (6 variants):
- `default`: Balanced exploration strategy
- `dfs_greedy`: Depth-first with greedy selection
- `bfs_greedy`: Breadth-first with greedy selection
- `dfs_naive`: Simple depth-first approach
- `bfs_naive`: Simple breadth-first approach
- `random`: Random action selection

**RVAndroid Tool** (5 variants):
- `default`: Ollama Gemma with single action strategy and vision support
- `llama_batch_detailed`: LLaMA 3.1 70B with batch action strategy
- `gpt4_standard_basic`: GPT-4 with single action strategy and basic visitor
- `ollama_standard_detailed`: Mixtral 8x7B with single action strategy
- `vision`: Gemma with vision strategy for multimodal testing and coordinate actions

**Additional Tools** (3-4 variants each):
- **Monkey**: default, fast, stress variants
- **Ares**: default, debug, fast variants
- **DroidMate**: default, systematic, quick, research variants
- **FastBot**: default, conservative, aggressive, balanced variants
- **Humanoid**: default, visual, nlp, hybrid variants
- **QTesting**: default, qlearning, dqn, ddqn variants

#### 5.1.4 CLI Usage Examples

```bash
# Use default variant
python -m rv_experiment run --tools droidbot

# Use specific variant  
python -m rv_experiment run --tools droidbot:dfs_greedy

# Multiple tools with variants
python -m rv_experiment run --tools ape:sata,droidbot:bfs_greedy,rvandroid:default

# Custom variant with parameter overrides in configuration
{
  "tool_configs": [
    {
      "name": "rvandroid",
      "variants": ["custom"],
      "parameters": {
        "llm_model": "qwen2.5:7b",
        "temperature": 0.2,
        "llm_type": "ollama",
        "prompt_strategy": "single"
      }
    }
  ]
}
```

### 5.2 RVAndroid - LLM-Guided Testing

RVAndroid provides LLM-enhanced testing through integration with multiple language model backends.

#### 5.2.1 RVAndroid Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                               RVAndroid Tool                                │
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐  │
│  │                 │    │                 │    │                         │  │
│  │ Action Service  │◄───┤     Server      │◄───┤    LLM Manager         │  │
│  │                 │    │                 │    │                         │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────────────┘  │
│           │                       │                          │              │
│           ▼                       ▼                          ▼              │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐  │
│  │                 │    │                 │    │                         │  │
│  │ State Enricher  │    │ Action Generator│    │  Prompt Framework      │  │
│  │                 │    │                 │    │  - Template System     │  │
│  │                 │    │                 │    │  - Strategy Manager    │  │
│  │                 │    │                 │    │  - Fragment Manager    │  │
│  │                 │    │                 │    │                         │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────────────┘  │
│           │                       │                          │              │
│           ▼                       ▼                          ▼              │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐  │
│  │                 │    │                 │    │                         │  │
│  │ Memory Manager  │    │Response Processor│    │ Transition Manager     │  │
│  │                 │    │                 │    │                         │  │
│  │                 │    │                 │    │                         │  │
│  │                 │    │                 │    │                         │  │
│  │                 │    │                 │    │                         │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 5.2.2 LLM Action Service

The LLMActionService coordinates AI-driven action generation:

```python
class LLMActionService:
    """
    Orchestrates AI-driven test action generation using unified configuration.
    """
    
    def __init__(self, static_data: StaticAnalysisData, tool_config: RvAndroidToolConfig):
        self.tool_config = tool_config
        self.static_data = static_data
        self.llm_config = tool_config.llm_config
        self.prompt_config = tool_config.prompt_config
        
        # Initialize LLM manager and prompt framework
        self.llm_manager = LLMManager(self.llm_config)
        self.prompt_framework = RVAndroidPromptFramework.create(self.prompt_config)
        
        # Initialize specialized processors
        self.state_enricher = StateEnricher(static_data=static_data, config=self.prompt_config)
        self.response_processor = ResponseProcessor(config=self.llm_config)
        self.action_generator = ActionGenerator(config=self.llm_config, static_data=static_data)
        
        # Initialize coordination components
        self.transition_manager = TransitionManager(static_data)
        self.memory_manager = MemoryManager(static_data)
        
    def process_state(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process application state and generate testing actions."""
        # Enrich state with additional information
        self.state_enricher.enrich_state(state)
        
        # Generate context-aware prompt
        prompt_context = self._create_prompt_context(state)
        messages = self.prompt_framework.generate_prompt(state, prompt_context)
        
        # Process LLM interaction
        llm_response = self.llm_manager.generate(messages)
        response_text = llm_response.content if hasattr(llm_response, 'content') else str(llm_response)
        
        # Process response into actions
        actions, errors = self.response_processor.process_response(response_text, state)
        generated_actions = self.action_generator.create_actions(actions, state)
        
        # Update memory with interaction history
        self.memory_manager.record_actions(state, generated_actions)
        
        return [action.to_droidbot_format() for action in generated_actions]
```

#### 5.2.3 Event Bus Integration

RVAndroid integrates with the event bus for real-time coverage and error tracking:

```python
class LLMActionService:
    def subscribe_to_event_bus(self):
        """Subscribe to coverage and error events for prompt context."""
        from rv_android_core.event.models import EventType
        self.event_bus.subscribe(
            EventType.COVERAGE_UPDATED,
            self._on_coverage_updated,
            filter_fn=lambda event: hasattr(event, 'source') and event.source == "CoverageTracker"
        )
        self.event_bus.subscribe(
            EventType.MOP_ERROR_DETECTED,
            self._on_mop_error_detected,
            filter_fn=lambda event: hasattr(event, 'source') and event.source == "CoverageTracker"
        )
        
    def _on_coverage_updated(self, event) -> None:
        """Handle coverage updates from CoverageTracker."""
        try:
            self.current_coverage_metrics = event.data.coverage_metrics
        except Exception as e:
            self.logger.warning(f"Error processing coverage update: {e}")

    def _on_mop_error_detected(self, event) -> None:
        """Handle MOP error detection events from CoverageTracker."""
        try:
            error_data = event.data.error_log
            error_context = {
                **error_data,
                "detected_at": datetime.datetime.now().isoformat()
            }
            
            # Add to recent errors list for prompt context
            self.recent_mop_errors.append(error_context)
            if len(self.recent_mop_errors) > 5:
                self.recent_mop_errors.pop(0)
                
        except Exception as e:
            self.logger.error(f"Error processing MOP error detection: {e}", exc_info=True)
```

### 5.3 RVAndroid - DroidBot Integration

RVAndroid provides LLM-enhanced testing by integrating with DroidBot:

```python
class RVAndroidTool(AbstractTool):
    """
    RVAndroid tool that enhances DroidBot with LLM guidance.
    """
    
    def execute(self, timeout: int, repetition: int, no_window: bool = False, **kwargs) -> bool:
        """Execute RVAndroid testing with DroidBot integration."""
        try:
            # Start RVAndroid server for LLM integration
            server_process = self._start_rvandroid_server()
            
            # Configure DroidBot with RVAndroid policy
            droidbot_config = self._prepare_droidbot_config(timeout, no_window)
            
            # Execute DroidBot with LLM guidance
            result = self._execute_droidbot(droidbot_config)
            
            return result
            
        finally:
            # Clean up server process
            if server_process:
                server_process.terminate()
```

## 6. LLM Integration and Services

### 6.1 LLM Service Architecture

The platform provides LLM integration through a modular service architecture:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            LLM Service Layer                                │
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐  │
│  │                 │    │                 │    │                         │  │
│  │  LLM Manager    │◄───┤  Adapter Layer  │◄───┤  Provider Adapters     │  │
│  │                 │    │                 │    │  - Ollama               │  │
│  │                 │    │                 │    │  - HuggingFace          │  │
│  │                 │    │                 │    │  - Frontier Models      │  │
│  │                 │    │                 │    │                         │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────────────┘  │
│           │                       │                          │              │
│           ▼                       ▼                          ▼              │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐  │
│  │                 │    │                 │    │                         │  │
│  │  Prompt         │    │  Response       │    │  Context Management    │  │
│  │  Framework      │    │  Processing     │    │                         │  │
│  │  - Templates    │    │  - Parsing      │    │                         │  │
│  │  - Strategies   │    │  - Validation   │    │                         │  │
│  │  - Information │    │  - Error Handle │    │                         │  │
│  │    Fragments    │    │                 │    │                         │  │
│  │                 │    │                 │    │                         │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### 6.1.1 Prompt Framework

The platform includes a prompt generation system:

```python
class PromptFramework:
    """
    Prompt generation framework with a modular template system.
    """
    
    def __init__(self):
        self.template_repository = JinjaTemplateRepository()
        self.fragment_manager = InformationFragmentManager()
        self.strategy_manager = PromptStrategyManager()
        
    def generate_prompt(self, strategy_name: str, context: Dict[str, Any]) -> str:
        """Generate prompt using specified strategy and context."""
        # Get strategy and template
        strategy = self.strategy_manager.get_strategy(strategy_name)
        template = self.template_repository.get_template(strategy.template_name)
        
        # Collect information fragments
        fragments = self.fragment_manager.collect_fragments(
            strategy.required_fragments, context
        )
        
        # Render prompt with fragments and context
        prompt = template.render({
            **context,
            **fragments,
            'strategy_config': strategy.config
        })
        
        return prompt
```

#### 6.1.2 Multi-Provider LLM Support

The system supports multiple LLM providers through a unified adapter pattern:

```python
class LLMManager:
    """
    Manages multiple LLM providers through a unified interface.
    """
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.adapters = {
            'ollama': OllamaAdapter(config.ollama_config),
            'huggingface': HuggingFaceAdapter(config.huggingface_config),
            'frontier': FrontierAdapter(config.frontier_config)
        }
        self.current_adapter = self.adapters[config.default_provider]
        
    async def generate_response(self, prompt: str, context: Dict[str, Any] = None) -> LLMResponse:
        """Generate response using the current LLM provider."""
        try:
            response = await self.current_adapter.generate(prompt, context)
            return LLMResponse(
                content=response.content,
                provider=self.current_adapter.provider_name,
                model=response.model,
                tokens_used=response.tokens_used,
                latency=response.latency
            )
        except Exception as e:
            # Fallback to alternative provider if configured
            if self.config.enable_fallback:
                return await self._try_fallback_provider(prompt, context)
            raise
```

## 7. Event-Driven Architecture

### 7.1 Event Bus System

The platform uses an event bus for decoupled component communication:

```python
class EventBus:
    """
    Event bus supporting typed events, channels, and filtering.
    """
    
    # Channel definitions
    LIFECYCLE_CHANNEL = "lifecycle"
    ERROR_CHANNEL = "error"
    METRICS_CHANNEL = "metrics"
    LLM_CHANNEL = "llm"
    
    def __init__(self):
        self.handlers: Dict[str, List[EventHandler]] = defaultdict(list)
        self.filters: Dict[str, List[EventFilter]] = defaultdict(list)
        self.transformers: Dict[str, List[EventTransformer]] = defaultdict(list)
        
    def publish_task_event(self, event_type: EventType, task_id: str, 
                          task_config: Dict[str, Any], details: Dict[str, Any] = None,
                          source: str = "Unknown", channel: str = LIFECYCLE_CHANNEL):
        """Publish task-related events with full context."""
        event = TaskEvent(
            type=event_type,
            task_id=task_id,
            task_config=task_config,
            details=details or {},
            source=source,
            timestamp=datetime.now(),
            channel=channel
        )
        
        self._process_event(event, channel)
```

### 7.2 Event Types and Handlers

The system defines event types for different aspects of operation:

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
    
    # Memory events
    STATE_ANALYZED = "state_analyzed"
    PATTERN_DETECTED = "pattern_detected"
    STRATEGY_CHANGED = "strategy_changed"
```

## 8. Error Handling and Recovery

### 8.1 Error Management

The platform includes an error handling system with classification and recovery strategies:

```python
class ErrorHandler:
    """
    Error handling with classification and recovery strategies.
    """
    
    def __init__(self):
        self.recovery_strategies = {
            EmulatorError: EmulatorRecoveryStrategy(),
            ToolError: ToolRecoveryStrategy(),
            LLMError: LLMRecoveryStrategy(),
            ExecutionError: GeneralRecoveryStrategy()
        }
        self.error_metrics = ErrorMetrics()
        
    def handle_error(self, error: Exception, context: Dict[str, Any]) -> bool:
        """Handle error with appropriate recovery strategy."""
        # Classify error
        error_type = self._classify_error(error)
        
        # Record error metrics
        self.error_metrics.record_error(error_type, context)
        
        # Attempt recovery
        recovery_strategy = self.recovery_strategies.get(type(error))
        if recovery_strategy:
            return recovery_strategy.attempt_recovery(error, context)
        
        # Default handling for unclassified errors
        return self._default_error_handling(error, context)
```

### 8.2 Recovery Strategies

Different error types have specialized recovery strategies:

```python
class EmulatorRecoveryStrategy(RecoveryStrategy):
    """Recovery strategy for emulator-related errors."""
    
    def attempt_recovery(self, error: EmulatorError, context: Dict[str, Any]) -> bool:
        """Attempt to recover from emulator error."""
        if isinstance(error, EmulatorStartupError):
            # Try restarting emulator
            return self._restart_emulator(context)
        elif isinstance(error, EmulatorCrashError):
            # Clean up and restart
            return self._cleanup_and_restart(context)
        elif isinstance(error, EmulatorTimeoutError):
            # Extend timeout and retry
            return self._extend_timeout_and_retry(context)
        
        return False
```

## 9. Coverage Analysis System

### 9.1 Repository Architecture

The RV-Android platform implements a coverage analysis system with direct repository integration.

#### 9.1.1 Coverage Tracker Design

The `CoverageTracker` uses direct LogcatRepository integration:

```python
class CoverageTracker:
    """
    Tracks code coverage with direct repository integration.
    """
    
    def __init__(self, logcat_file: str, static_data: Optional[StaticAnalysisData] = None):
        # Initialize LogcatRepository directly
        self.repository = LogcatRepository()
        
        # Initialize with static analysis data if available
        if static_data:
            self._initialize_from_static_data(static_data)
    
    def _process_logcat_line(self, line: str) -> None:
        """Process logcat line and update repository directly."""
        error_log, coverage_log = parse_logcat_line(line)
        
        if error_log:
            self.repository.register_rv_error(error_log)
        elif coverage_log:
            self.repository.register_method_call(coverage_log)
```

#### 9.1.2 Repository Integration Benefits

The direct LogcatRepository integration provides several benefits:

1.  **Performance**: Direct method calls eliminate delegation overhead.
2.  **Simplified Data Flow**: Coverage data flows directly from tracker to repository.
3.  **Reduced Complexity**: Fewer abstraction layers mean easier debugging and maintenance.
4.  **Method Availability**: All LogcatRepository methods are directly accessible.
5.  **Memory Efficiency**: Direct object usage without intermediate layers.

#### 9.1.3 Coverage Data Flow

The coverage data flow ensures efficient processing:

```
Static Analysis → LogcatRepository Initialization → 
CoverageTracker → Direct Repository Updates → 
Metrics Calculation → Result Processing → 
CSV/JSON Export
```

This direct flow provides:
- Performance with direct method calls.
- Data consistency through a single source of truth.
- Complete method availability.
- Efficient memory usage.

#### 9.1.4 Task Repository Integration

The coverage data is preserved through the task execution lifecycle:

```python
class CoverageComponent:
    def process_results(self) -> bool:
        """Process coverage data and store in task."""
        # Get repository directly from coverage tracker
        repository = self.coverage_tracker.repository
        
        # Calculate final metrics
        metrics = repository.calculate_metrics()
        
        # Store repository directly in task for result processing
        self.task.repository = repository
        
        return True
```

This ensures that:
- Coverage data persists beyond component cleanup.
- ResultManager can access complete coverage information.
- Data consistency is maintained throughout the experiment lifecycle.
- All repository methods are available for result processing.

## 10. Performance Monitoring and Metrics

### 10.1 Performance Monitoring System

The platform includes performance monitoring:

```python
class PerformanceMonitor:
    """
    Performance monitoring system.
    """
    
    def __init__(self):
        self.metrics_storage = MetricsStorage()
        self.resource_tracker = ResourceTracker()
        self.trend_analyzer = TrendAnalyzer()
        
    @contextmanager
    def measure_time(self, operation_name: str, context: Dict[str, Any] = None):
        """Context manager for measuring operation time."""
        start_time = time.time()
        start_resources = self.resource_tracker.get_current_usage()
        
        try:
            yield
        finally:
            end_time = time.time()
            end_resources = self.resource_tracker.get_current_usage()
            
            # Record performance metrics
            self.record_metric(
                name=f"{operation_name}_duration",
                value=end_time - start_time,
                unit="s",
                context=context
            )
            
            # Record resource usage
            self._record_resource_usage(
                operation_name, start_resources, end_resources, context
            )
```

## 11. Configuration and Extensibility

### 11.1 Component Configurator

The platform uses a configuration system:

```python
class ComponentConfigurator:
    """
    Component configuration system.
    """
    
    def __init__(self, config_file: str):
        self.config = self._load_configuration(config_file)
        self.validators = self._setup_validators()
        self.factories = self._setup_factories()
        
    def configure_llm_service(self) -> LLMManager:
        """Configure LLM service based on settings."""
        llm_config = LLMConfig(
            default_provider=self.config.llm.default_provider,
            ollama_config=self.config.llm.ollama,
            huggingface_config=self.config.llm.huggingface,
            frontier_config=self.config.llm.frontier,
            enable_fallback=self.config.llm.enable_fallback
        )
        
        return LLMManager(llm_config)
```

## 12. Testing and Validation

### 12.1 Test Framework Integration

The platform includes a test framework for validation:

```python
class TestFramework:
    """
    Testing framework for RV-Android validation.
    """
    
    def __init__(self, config: TestFrameworkConfig):
        self.config = config
        self.executor = TestSuiteExecutor()
        self.analyzer = ComparativeAnalyzer()
        self.visualizer = ResultVisualizer()
        
    def run_comprehensive_test(self, test_configurations: List[TestConfig]) -> TestResults:
        """Run testing across multiple configurations."""
        results = []
        
        for config in test_configurations:
            # Execute test suite
            suite_result = self.executor.execute_suite(config)
            
            # Analyze results
            analysis = self.analyzer.analyze_results(suite_result)
            
            # Store results
            results.append(TestResult(
                configuration=config,
                execution_result=suite_result,
                analysis=analysis
            ))
        
        # Perform comparative analysis
        comparative_analysis = self.analyzer.compare_configurations(results)
        
        # Generate visualizations
        visualizations = self.visualizer.generate_comprehensive_report(
            results, comparative_analysis
        )
        
        return TestResults(
            individual_results=results,
            comparative_analysis=comparative_analysis,
            visualizations=visualizations
        )
```

## 13. Conclusion

The RV-Android platform provides a modular and extensible architecture for testing Android applications with runtime verification. Its key features include a component-based design, LLM integration, event-driven communication, and comprehensive error handling. The platform is a robust foundation for research and development in Android application testing and verification.
