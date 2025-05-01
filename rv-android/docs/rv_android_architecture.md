# RV-Android Architecture

## 1. Introduction

RV-Android is a comprehensive platform for testing Android applications using runtime verification techniques. It combines static analysis, dynamic testing, and formal verification to detect potential issues in Android applications. The platform leverages JavaMOP (Monitoring-Oriented Programming) and RV-Monitor to define and verify properties at runtime, providing a powerful framework for ensuring application correctness and security.

This document details the architecture, components, and execution flow of the RV-Android platform.

### 1.1 System Components Overview

The RV-Android ecosystem consists of several interconnected components, each serving a specific purpose in the Android application testing workflow:

1. **RV-Android Platform**: The core infrastructure that orchestrates the entire testing process from property specification to result analysis. It handles the pre-processing of applications, test execution, and post-processing of results.

2. **RVAndroid Tool**: A specialized testing tool integrated with DroidBot that enhances test generation using Language Model (LLM) guidance. It intercepts DroidBot's state exploration, analyzes screen content using a structured approach, and uses LLMs to select optimal actions for effective testing.

3. **RVDroid Tool**: An alternative, more advanced testing tool that uses UIAutomator for state extraction and employs LLMs with a sophisticated memory system and strategy framework for enhanced test generation.

4. **Test Framework**: A comparative evaluation system for systematically testing and comparing different configurations, tools, and strategies, providing metrics and visualizations for test coverage and effectiveness.

The relationship between these components is hierarchical but also collaborative:

- **RV-Android** serves as the foundation and orchestration layer
- **RVAndroid** and **RVDroid** are specialized testing tools that can be deployed within RV-Android
- **Test Framework** evaluates and compares the performance of these tools

This separation of concerns allows for modular development and evaluation of testing approaches while maintaining a unified platform for runtime verification.

## 2. RV-Android Platform Architecture

### 2.1 High-Level Architecture

RV-Android follows a modular architecture organized around the key phases of Android application testing:

1. **Pre-processing Phase**: Application analysis, instrumentation, and preparation
2. **Execution Phase**: Test execution and runtime monitoring
3. **Post-processing Phase**: Result collection, analysis, and visualization

The platform is designed to be extensible, allowing for the integration of various testing tools, static analysis techniques, and verification approaches. It provides a unified interface for orchestrating the testing process, from property specification to result analysis.

```
┌─────────────────────────────────────────────────────────────────┐
│                      RV-Android Platform                         │
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │             │    │             │    │                     │  │
│  │ Static      │    │ Runtime     │    │ Result Analysis     │  │
│  │ Analysis    │◄───┤ Testing     │◄───┤ and Visualization   │  │
│  │ & Prep      │    │ & Monitoring│    │                     │  │
│  │             │    │             │    │                     │  │
│  └─────────────┘    └─────────────┘    └─────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                 Testing Tools Integration                 │  │
│  │                                                          │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────────────┐  │  │
│  │  │            │  │            │  │                    │  │  │
│  │  │  RVAndroid │  │  RVDroid   │  │  Other Testing     │  │  │
│  │  │  (Droidbot)│  │ (UIAuto)   │  │  Tools (Monkey,etc)│  │  │
│  │  │            │  │            │  │                    │  │  │
│  │  └────────────┘  └────────────┘  └────────────────────┘  │  │
│  │                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Core Components

The RV-Android platform comprises several core components that work together to facilitate the testing process:

1. **Property Specification System**: Enables the definition of formal properties using JavaMOP that will be monitored during runtime.

2. **Instrumentation Engine**: Modifies the Android application bytecode to insert monitoring code for property verification.

3. **Test Execution Controller**: Manages the execution of tests, including emulator setup, application installation, and test tool coordination.

4. **Static Analysis Engine**: Performs static analysis on the application to identify potential issues and provide context for dynamic testing.

5. **Result Collection and Analysis**: Gathers test results, analyzes property violations, and generates comprehensive reports.

6. **Configuration Management**: Handles the configuration of the testing process, including tool selection, test parameters, and property definitions.

## 3. Execution Flow

### 3.1 Pre-processing Phase

The pre-processing phase prepares the Android application for testing by analyzing its structure and instrumenting it with monitoring code. This phase involves several key steps:

1. **Property Definition**: Formal properties are defined using JavaMOP, specifying the expected behavior of the application.

2. **Static Analysis**: The application is analyzed to extract information about its structure, including class hierarchies, method signatures, and potential entry points.

   ```
   Static analysis begins with the APK file being processed through multiple tools:
   - GESDA (Guided Exploration State Discovery Analysis) identifies state transitions
   - Gator analyzes the Window Transition Graph (WTG)
   - Reach analysis identifies methods that can reach monitored operations
   ```

3. **Monitor Generation**: JavaMOP properties are compiled into RV-Monitor observers that will detect violations at runtime.

4. **Instrumentation**: The application is instrumented using AspectJ to insert:
   - Monitoring code for property verification
   - Logging aspects to record method calls to the logcat
   - Additional instrumentation for coverage tracking

   This process transforms the application by adding a new layer of monitoring code while preserving its original functionality. The instrumentation engine carefully injects monitors at key points in the code, focusing on the methods and classes identified during static analysis.

5. **APK Repackaging**: The instrumented code is repackaged into a new APK file, signed with a test certificate, and prepared for installation.

### 3.2 Execution Phase

During the execution phase, the instrumented application is installed on an emulator or device, and various testing tools are used to exercise its functionality. The key steps are:

1. **Emulator Setup**: An Android emulator is configured and launched with the specified parameters.

2. **Application Installation**: The instrumented APK is installed on the emulator.

3. **Test Tool Deployment**: Selected testing tools are deployed to interact with the application. This may include:
   - **Monkey**: For random UI event generation
   - **DroidBot**: For model-based testing
   - **DroidMate**: For systematic UI exploration
   - **APE**: For refined UI testing
   - **FastBot**: For rapid state exploration
   - **RVAndroid**: For LLM-guided testing integrated with DroidBot
   - **RVDroid**: For advanced LLM-guided testing with UIAutomator

4. **Test Execution**: The selected tools execute tests on the application, exploring its functionality and triggering runtime verification monitors.

   When using RVAndroid or RVDroid, a typical test sequence unfolds as follows:
   
   ```
   For example, when RVAndroid is running with DroidBot:
   
   1. DroidBot navigates to a new state in the application
   2. The current screen information is captured
   3. DroidBot forwards state data to RVAndroid's server
   4. RVAndroid parses the screen into a structured representation
   5. The screen description is processed through a prompt generation strategy
   6. An LLM receives the prompt and generates action recommendations
   7. The selected actions are returned to DroidBot
   8. DroidBot executes the recommended actions
   9. The cycle repeats, with each new state being analyzed
   ```

5. **Runtime Monitoring**: Throughout execution, the instrumented code triggers monitors when relevant methods are called, verifying property compliance and logging violations.

6. **Data Collection**: Various data is collected during execution:
   - Logcat entries for method calls
   - Property violation reports
   - Coverage information
   - Screenshots and state information

The execution phase is a dynamic process where the testing tools and monitors work together to explore the application and identify potential issues. The runtime verification system continuously evaluates the application's behavior against the specified properties, flagging any violations for further analysis.

### 3.3 Post-processing Phase

After test execution, the collected data is processed and analyzed to generate meaningful insights about the application's behavior:

1. **Log Analysis**: The logcat logs are parsed to extract method call sequences, exceptions, and other relevant information.

2. **Coverage Calculation**: Code coverage metrics are computed to assess the thoroughness of testing.

3. **Violation Analysis**: Property violations are aggregated and categorized to identify patterns and root causes.

4. **Result Visualization**: Graphs, charts, and other visualizations are generated to represent test results and coverage.

5. **Report Generation**: Comprehensive reports are created, detailing test execution, coverage, and identified issues.

The post-processing phase transforms raw test data into actionable insights, helping developers understand the application's behavior and identify potential issues. The platform provides various visualization tools to make this information accessible and useful.

## 4. Data Flow

The RV-Android platform processes and transforms data through various stages:

### 4.1 Input Data

- **APK File**: The Android application to be tested
- **Property Specifications**: JavaMOP files defining expected behavior
- **Configuration Files**: Parameters for testing tools and platform behavior

### 4.2 Intermediate Data

- **Static Analysis Results**: 
  - Class hierarchies
  - Method call graphs
  - Window transition graphs
  - Reachability information
  
- **Instrumented Application**:
  - Original application code
  - Injected monitoring code
  - Logging aspects
  
- **Runtime Data**:
  - Method call logs
  - UI event sequences
  - Property violation reports
  - State information
  - Screenshots

### 4.3 Output Data

- **Coverage Reports**: Metrics showing code coverage achieved during testing
- **Violation Reports**: Detailed information about property violations
- **Performance Metrics**: Execution time, resource usage, and other performance indicators
- **Visualizations**: Graphs and charts representing test results
- **Consolidated Reports**: Comprehensive documentation of the testing process and results

## 5. Component Interactions

### 5.1 Static Analysis and Instrumentation

The static analysis component provides essential information for the instrumentation process:

```
┌─────────────────┐                ┌─────────────────┐
│                 │                │                 │
│  Static Analysis│───Class Data───►  Monitor        │
│                 │                │  Generation     │
└────────┬────────┘                └────────┬────────┘
         │                                  │
         │                                  │
         │                                  ▼
         │                         ┌─────────────────┐
         │                         │                 │
         └──Method Information────►│ Instrumentation │
                                   │                 │
                                   └────────┬────────┘
                                            │
                                            │
                                            ▼
                                   ┌─────────────────┐
                                   │                 │
                                   │ Instrumented APK│
                                   │                 │
                                   └─────────────────┘
```

### 5.2 Test Execution and Monitoring

During test execution, the various components interact to provide comprehensive testing and monitoring:

```
┌─────────────────┐                ┌─────────────────┐
│                 │                │                 │
│  Test Execution │───UI Events───►│ Instrumented    │
│  Controller     │                │ Application     │
└────────┬────────┘                └────────┬────────┘
         │                                  │
         │                                  │
         ▼                                  ▼
┌─────────────────┐                ┌─────────────────┐
│                 │                │                 │
│  Testing Tools  │◄──State Info──►│ Runtime         │
│  (RVAndroid etc)│                │ Monitors        │
└────────┬────────┘                └────────┬────────┘
         │                                  │
         │                                  │
         ▼                                  ▼
┌─────────────────┐                ┌─────────────────┐
│                 │                │                 │
│  Data Collection│◄───Logs/Data───┤ Violation       │
│                 │                │ Reports         │
└─────────────────┘                └─────────────────┘
```

### 5.3 Result Analysis and Visualization

After testing, the collected data is processed and visualized:

```
┌─────────────────┐                ┌─────────────────┐
│                 │                │                 │
│  Log Parser     │───Parsed Data──►  Coverage       │
│                 │                │  Calculator     │
└────────┬────────┘                └────────┬────────┘
         │                                  │
         │                                  │
         ▼                                  ▼
┌─────────────────┐                ┌─────────────────┐
│                 │                │                 │
│  Violation      │───Analysis Data►  Visualization  │
│  Analyzer       │                │  Engine         │
└────────┬────────┘                └────────┬────────┘
         │                                  │
         │                                  │
         ▼                                  ▼
┌─────────────────┐                ┌─────────────────┐
│                 │                │                 │
│  Report         │◄──Visualizations  Results        │
│  Generator      │                │  Dashboard      │
└─────────────────┘                └─────────────────┘
```

## 6. Integration with Testing Tools

RV-Android provides a flexible framework for integrating various testing tools through a plugin architecture. Each tool is wrapped in a standardized interface that allows the platform to control its execution and collect results.

### 6.1 Testing Tool Integration

Each testing tool is integrated into the platform through a dedicated adapter that:

1. **Translates Configuration**: Converts RV-Android configuration parameters to tool-specific settings
2. **Manages Execution**: Handles tool startup, shutdown, and interaction with the application
3. **Collects Results**: Gathers tool-specific output and transforms it into a standardized format
4. **Provides Feedback**: Reports tool status and progress to the central controller

### 6.2 RVAndroid Integration

RVAndroid is tightly integrated with the DroidBot testing tool, enhancing its state exploration with LLM-guided decisions:

1. The RVAndroid server runs alongside the RV-Android platform
2. A custom DroidBot policy forwards state information to the RVAndroid server
3. RVAndroid processes the state, generates prompts, and queries an LLM
4. The LLM's recommended actions are returned to DroidBot
5. DroidBot executes the actions, continuing the exploration process

This integration enables intelligent testing that understands the application's context and can make more relevant testing decisions than traditional random or model-based approaches.

### 6.3 RVDroid Integration

RVDroid operates as a standalone testing tool within the RV-Android platform:

1. RVDroid uses UIAutomator to extract application state information
2. The extracted state is processed through a structured analysis pipeline
3. An advanced LLM service with memory and strategy components generates test actions
4. RVDroid executes the actions using UIAutomator commands
5. Results and state changes are tracked and fed back into the decision system

RVDroid's sophisticated architecture allows for more nuanced testing strategies, including goal-oriented testing, memory-based exploration, and adaptive testing approaches.

## 7. Configuration System

RV-Android uses a comprehensive configuration system to control all aspects of the testing process. The configuration is managed through JSON files that specify:

1. **Application Details**: APK path, package name, and other application-specific information
2. **Property Specifications**: Paths to JavaMOP property files and related parameters
3. **Testing Tools**: Selection of testing tools and their parameters
4. **Execution Parameters**: Emulator settings, test duration, and other execution details
5. **Analysis Options**: Settings for result analysis and visualization

The configuration system allows for flexible experimentation with different testing approaches and parameters, facilitating comparative studies and optimization of the testing process.

## 8. Conclusion

The RV-Android platform provides a comprehensive framework for testing Android applications using runtime verification techniques. Its modular architecture, integration with various testing tools, and sophisticated analysis capabilities make it a powerful tool for ensuring application correctness and security.

The platform continues to evolve, with ongoing development of new testing approaches, improved analysis techniques, and enhanced integration with state-of-the-art testing tools like RVAndroid and RVDroid.

## Appendix A: Experiment Execution System

This appendix provides a detailed explanation of the experiment execution management system, including the relationships between key components and the lifecycle of tasks from creation to completion.

### A.1 Experiment Execution Architecture

The experiment execution system in RV-Android follows a structured, component-based architecture that separates concerns while maintaining clear relationships between components:

```
┌──────────────────────────────────────────────────────────────────────────┐
│                                                                          │
│                        Experiment Controller                             │
│                                                                          │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────┐  │
│  │               │  │               │  │               │  │           │  │
│  │ Pre-Processor │  │ Execution     │  │ Post-         │  │ Result    │  │
│  │               │  │ Controller    │  │ Processor     │  │ Manager   │  │
│  │               │  │               │  │               │  │           │  │
│  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘  └─────┬─────┘  │
│          │                  │                  │                │        │
└──────────┼──────────────────┼──────────────────┼────────────────┼────────┘
           │                  │                  │                │
           ▼                  ▼                  ▼                ▼
┌──────────────────┐ ┌─────────────────┐ ┌─────────────────┐ ┌──────────────┐
│                  │ │                 │ │                 │ │              │
│ Static Analysis/ │ │ Task Manager    │ │ Coverage        │ │ Report       │
│ Instrumentation  │ │                 │ │ Calculator      │ │ Generator    │
│                  │ │ ┌─────────────┐ │ │                 │ │              │
│                  │ │ │  Task       │ │ │                 │ │              │
│                  │ │ │  Storage    │ │ │                 │ │              │
│                  │ │ └─────────────┘ │ │                 │ │              │
│                  │ │                 │ │                 │ │              │
└──────────────────┘ └────────┬────────┘ └─────────────────┘ └──────────────┘
                              │
                              ▼
             ┌────────────────────────────────────────┐
             │                                        │
             │              Task Executor             │
             │                                        │
             │ ┌────────────┐ ┌────────────────────┐  │
             │ │            │ │                    │  │
             │ │ Component  │ │ Emulator/Logcat/   │  │
             │ │ Registry   │ │ Tool Components    │  │
             │ │            │ │                    │  │
             │ └────────────┘ └────────────────────┘  │
             │                                        │
             └────────────────────────────────────────┘
```

### A.2 Key Components and Responsibilities

#### A.2.1 Experiment Controller

The `ExperimentController` is the central orchestrator of the experiment execution process, responsible for:

1. **Initialization**: Setting up experiment directories, logging, and other resources
2. **Workflow Management**: Coordinating the pre-processing, execution, and post-processing phases
3. **Event Handling**: Publishing and responding to experiment events
4. **Error Management**: Handling errors that occur during any phase of the experiment

The controller uses a modular architecture with specialized components for each phase of the experiment:

```python
def execute(self, repetitions: int, timeouts: List[int], tools: List[AbstractTool],
            memory_file: str = "", generate_monitors: bool = True, instrument: bool = True,
            static_analysis: bool = True, skip_experiment: bool = False, no_window: bool = False):
    """Execute the entire experiment workflow with configurable phases."""
    
    # Handle memory file for experiment resumption
    if memory_file:
        self._resume_from_memory(memory_file)
    else:
        # Pre-process APKs if not resuming
        if generate_monitors or instrument or static_analysis:
            self.pre_processor.process(generate_monitors, instrument, static_analysis)

    # Run experiment if not skipped
    if not skip_experiment:
        # Configure execution parameters
        instrumented_apks = self.pre_processor.get_instrumented_apks()

        # Set up experiment execution
        self.execution_controller.setup(
            apks=instrumented_apks,
            repetitions=repetitions,
            timeouts=timeouts,
            tools=tools,
            no_window=no_window
        )

        # Run the experiment tasks
        self.execution_controller.run()

        # Process results
        self.post_processor.process()

        # Generate reports
        self.result_manager.generate_reports()
```

#### A.2.2 Task Manager

The `TaskManager` handles task lifecycle management, including:

1. **Task Creation**: Generating tasks for each combination of APK, tool, timeout, and repetition
2. **Task Scheduling**: Determining the order of task execution
3. **Task Storage**: Persisting task state in a storage system
4. **Execution Tracking**: Monitoring and reporting on task execution progress

Task generation creates a matrix of testing configurations:

```python
def setup_execution(self, 
                   apks: List[App],
                   repetitions: int,
                   timeouts: List[int],
                   tools: List[AbstractTool],
                   **kwargs):
    """Set up tasks for execution."""
    # Create tasks for each combination
    factory = TaskFactory(Task)
    
    for app in apks:
        for rep in range(1, repetitions + 1):
            for timeout in timeouts:
                for tool in tools:
                    # Create task configuration
                    config = TaskConfiguration(
                        apk_name=app.name,
                        repetition=rep,
                        timeout=timeout,
                        tool_name=tool.name,
                        **kwargs
                    )
                    
                    # Create and register task
                    task = factory.create_task(config)
                    task.initialize(self.base_results_dir)
                    task.set_app(app)
                    
                    # Add to storage
                    self.storage.add_task(task)
```

#### A.2.3 Task Executor

The `TaskExecutor` is responsible for the detailed execution of individual tasks, with features for:

1. **Component Management**: Managing task execution components (emulator, tool execution, etc.)
2. **Error Handling**: Providing comprehensive error handling during task execution
3. **Performance Monitoring**: Tracking execution time and resource usage
4. **Event Publication**: Notifying the system of task lifecycle events

Task execution follows a component-based approach:

```python
def execute(self) -> bool:
    """Execute the task with comprehensive error handling and performance monitoring."""
    try:
        # Update task state to running
        self.task.update_state(TaskState.RUNNING)
        self._publish_task_started_event()

        # Measure the total execution time
        with self.performance_monitor.measure_time("task_execution_total", self.get_task_context()):
            # Initialize all components
            context = self.get_task_context()
            if not self.components.initialize_all(context):
                raise TaskExecutionError("Failed to initialize components", self.task.id)
            
            # Execute all components in order
            for component in self.components.get_all():
                with self.performance_monitor.measure_time(f"component_{component.name.lower()}", context):
                    self.logger.info(f"Executing component: {component.name}")
                    if not component.execute(context):
                        raise TaskExecutionError(f"Component {component.name} execution failed", self.task.id)
                        
            # Clean up all components
            self.components.cleanup_all(context)

        # Mark task as completed
        self.task.update_state(TaskState.COMPLETED)
        
        # Publish completed event
        self._publish_task_completed_event()
        
        return True

    except Exception as e:
        # Handle error and update task status
        self.task.update_state(TaskState.ERROR, str(e))
        
        # Publish failed event
        self._publish_task_failed_event(str(e))
        
        # Clean up resources
        self._cleanup_resources()
        
        return False
```

#### A.2.4 Task Components

The task execution process is broken down into specialized components:

1. **Emulator Manager**: Handles emulator setup, launch, and cleanup
2. **Logcat Manager**: Manages logcat capture and analysis
3. **Tool Execution Component**: Executes testing tools on the device
4. **Coverage Component**: Tracks and reports on coverage metrics
5. **Error Handler**: Provides centralized error handling

### A.3 Task Lifecycle

The lifecycle of a task within the RV-Android execution system follows these stages:

#### A.3.1 Creation Phase

1. **Task Configuration Creation**: A `TaskConfiguration` object is created with parameters like APK name, tool name, repetition number, and timeout
2. **Task Object Creation**: A new `Task` object is instantiated using a factory pattern with the configuration
3. **Task Initialization**: The task is initialized with a results directory and associated with an app instance
4. **Task Storage**: The task is added to the task storage system for persistence

#### A.3.2 Execution Phase

1. **Task Retrieval**: A pending task is retrieved from the task storage
2. **Task Executor Creation**: A new `TaskExecutor` is created for the task with appropriate components
3. **State Update**: The task's state is updated to `RUNNING` and a task started event is published
4. **Component Execution**: Each task component is executed in sequence:
   - Emulator Setup: Launching the emulator with the specified configuration
   - App Installation: Installing the APK on the emulator
   - Logcat Capture: Starting the logcat capture process
   - Tool Execution: Running the selected testing tool
   - Coverage Collection: Collecting coverage data during execution
5. **Component Cleanup**: All components are cleaned up in reverse order after execution
6. **State Update**: The task's state is updated to `COMPLETED` or `ERROR` and appropriate events are published

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│              │  │              │  │              │  │              │  │              │
│  PENDING     │──►  RUNNING     │──►  COMPLETED   │  │  ERROR       │  │  CANCELLED   │
│              │  │              │  │              │  │              │  │              │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
       │                 │                 │                 │
       │                 │                 │                 │
       ▼                 ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ TASK_CREATED │  │ TASK_STARTED │  │TASK_COMPLETED│  │ TASK_FAILED  │
│    Event     │  │    Event     │  │    Event     │  │    Event     │
└──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘
```

#### A.3.3 Post-Execution Phase

1. **Result Collection**: The task's results (coverage data, logs, etc.) are collected and stored
2. **Metrics Calculation**: Coverage metrics are calculated based on the collected data
3. **Result Storage**: The task's updated state and metrics are stored in the task storage
4. **Event Publication**: Task completed events are published to the event system
5. **Task Finalization**: Any remaining resources are cleaned up and the task is marked as fully processed

### A.4 Event System

The experiment execution system uses an event-driven architecture with the `EventBus` as a central communication mechanism:

1. **Event Types**: Different event types represent various stages in the experiment and task lifecycle:
   - Experiment events: EXPERIMENT_STARTED, EXPERIMENT_COMPLETED, EXPERIMENT_FAILED
   - Task events: TASK_CREATED, TASK_STARTED, TASK_COMPLETED, TASK_FAILED
   - Component events: EMULATOR_STARTED, TOOL_STARTED, etc.

2. **Event Channels**: Events are published on different channels for better organization:
   - LIFECYCLE_CHANNEL: Normal lifecycle events
   - ERROR_CHANNEL: Error events
   - METRICS_CHANNEL: Performance and metrics events

3. **Event Handlers**: Components can subscribe to events to react to system changes:
   ```python
   self.event_bus.subscribe(
       event_type=EventType.TASK_STARTED, 
       callback=on_task_started,
       channel=EventBus.LIFECYCLE_CHANNEL
   )
   ```

### A.5 Resource Management

The execution system carefully manages resources to ensure proper cleanup even in error cases:

#### A.5.1 Emulator Management

The `EmulatorManager` provides context managers for safe emulator usage:

```python
@contextmanager
def start_emulator(self, avd_name: str, no_window: bool = False) -> Android:
    """Start an emulator and yield an Android instance for interaction."""
    try:
        # Start the emulator
        self.android.start_emulator(avd_name, no_window)
        yield self.android
    finally:
        # Always try to clean up
        try:
            self.logger.info(f"Shutting down emulator {avd_name}")
            self.android.kill_emulator(avd_name)
        except Exception as e:
            self.logger.warning(f"Error shutting down emulator: {e}")
```

#### A.5.2 Logcat Management

The `LogcatManager` handles logcat process lifecycle:

```python
def start_capture(self, output_file: str, tags: List[str] = None, clear_buffer: bool = True) -> bool:
    """Start capturing logcat output to a file."""
    try:
        # Start logcat capture
        logcat_cmd = Command("adb", cmd_args)
        log_file = open(output_file, "wb")
        self.logcat_process = logcat_cmd.invoke_as_deamon(stdout=log_file)
        self.logcat_file_handle = log_file
        return True
    except Exception as e:
        # Handle errors and clean up
        return False

def stop_capture(self) -> bool:
    """Stop logcat capture and clean up resources."""
    # Kill logcat process
    if self.logcat_process:
        try:
            self.logcat_process.kill()
            self.logcat_process = None
        except Exception:
            pass
            
    # Close logcat file handle
    if self.logcat_file_handle:
        try:
            self.logcat_file_handle.close()
            self.logcat_file_handle = None
        except Exception:
            pass
```

### A.6 Performance Monitoring

The execution system includes comprehensive performance monitoring through the `PerformanceMonitor`:

1. **Time Measurement**: Measures execution time for tasks and components
   ```python
   with self.performance_monitor.measure_time("task_execution_total", context):
       # Execute task...
   ```

2. **Metric Recording**: Records various metrics about the execution
   ```python
   self.performance_monitor.record_metric(
       name="task_duration",
       value=task.result.execution_time_seconds,
       unit="s",
       context=context
   )
   ```

3. **Resource Usage**: Tracks resource usage like CPU and memory
   ```python
   self.performance_monitor.start_resource_tracking(task_id)
   # ... execution ...
   usage = self.performance_monitor.stop_resource_tracking(task_id)
   ```

### A.7 Error Handling

The system provides robust error handling through the `ErrorHandler` component:

1. **Centralized Error Handling**: All errors are routed through a central handler
   ```python
   try:
       # Execute task...
   except Exception as e:
       self.error_handler.handle_error(e, self.get_task_context())
   ```

2. **Error Classification**: Errors are classified into different categories
   ```python
   if isinstance(e, EmulatorError):
       # Handle emulator-specific errors
   elif isinstance(e, ToolError):
       # Handle tool-specific errors
   else:
       # Handle general errors
   ```

3. **Recovery Strategies**: Different recovery strategies for different error types
   ```python
   if error_type == "emulator_crash":
       # Attempt to restart emulator
   elif error_type == "anr":
       # Force stop the application and retry
   else:
       # Mark task as failed
   ```

This detailed approach to experiment execution management ensures that RV-Android can reliably and efficiently execute complex testing workflows, handle errors gracefully, and provide comprehensive metrics and reports.