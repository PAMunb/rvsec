# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Architecture Overview

RV-Android is a modular framework for runtime verification of Android applications with integrated AI-driven testing capabilities. The system uses a Poetry workspace architecture with clean separation of concerns across specialized modules.

### Core Architecture Principles

- **Modular Design**: Independent Poetry modules with clear dependencies and interfaces
- **Event-Driven Communication**: EventBus system for coordinated interaction between components
- **Clean Architecture**: Separation of concerns with domain models, utilities, and application layers
- **Configuration Management**: Unified configuration across all modules using Pydantic models
- **Error Handling**: Comprehensive error handling with proper context and recovery strategies

### System Components

The system consists of 11 core modules in dependency order:

1. **rv-android-core**: Foundation infrastructure with domain models, event system, error handling, and logging
2. **rv-monitor-generator**: JavaMOP/RV-Monitor integration for generating runtime verification monitors
3. **rv-instrumentation**: APK instrumentation with monitor weaving capabilities
4. **rv-static-analysis**: Static analysis tools (GATOR, GESDA, REACH) for Android applications
5. **rv-coverage**: Coverage analysis and tracking for monitored operations
6. **rv-screen-parser**: Android UI parsing with visitor patterns for state analysis
7. **rv-llm**: Language model integration framework with multiple backend support
8. **rv-tools**: Testing tool plugin system with registry and factory patterns
9. **rv-platform**: Central execution platform coordinating task execution and result processing
10. **rvandroid-tool**: AI-driven testing tool with LLM integration and server interface
11. **rv-experiment**: Experiment orchestration and coordination system

## Development Commands

### Environment Setup
```bash
# Set environment variables (development mode)
export RV_PYDANTIC=true  # Enable validation during development
export RVSEC_HOME="/path/to/rvsec"  # Required for monitor generation
export ANDROID_HOME="/path/to/android-sdk"

# Install all modules in dependency order
cd modules
./install.sh

# Verify installation
poetry run python -c "import rv_android_core, rv_monitor_generator; print('Setup complete')"
```

### Common Development Tasks
```bash
# Run all tests from workspace root
poetry run pytest

# Test specific module
poetry run pytest modules/rv-android-core/tests/ -v

# Install single module after changes
cd modules && ./install.sh rv-android-core --verbose

# Run with coverage
poetry run pytest --cov=modules --cov-report=html

# Generate configuration templates
poetry run rv-experiment config --template-type basic --output basic_config.json
```

### Monitor Generation Workflow
```bash
# Generate JCA cryptography monitors
poetry run rv-monitor-generator generate \
  --specs-dir $RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca \
  --output ./output/jca-monitors

# Auto-discover specifications
poetry run rv-monitor-generator generate --output ./output/auto-monitors
```

### Experiment Execution
```bash
# Run complete experiment
poetry run python run_test_framework.py

# Execute with specific configuration
poetry run rv-experiment run --tools monkey,droidbot:dfs_greedy --specification-set jca

# Run rv-platform directly
poetry run rv-platform run --tools monkey --apks-dir ./apks_examples
```

### Code Quality and Linting
```bash
# Format code
poetry run black modules/

# Lint code
poetry run flake8 modules/

# Type checking
poetry run mypy modules/

# Security analysis
poetry run bandit -r modules/
```

## Execution Flow

### Primary Entry Points

1. **rv-experiment CLI** (`modules/rv-experiment/src/rv_experiment/__main__.py`):
   - Main experiment orchestration interface
   - Supports tool specification DSL and configuration files
   - Coordinates three-phase workflow (pre-processing, execution, post-processing)

2. **rv-platform CLI** (`modules/rv-platform/src/rv_platform/__main__.py`):
   - Direct platform execution without experiment wrapper
   - Task generation and execution coordination
   - Result processing and metrics collection

### Core Execution Flow

1. **Experiment Controller** (`modules/rv-experiment/src/rv_experiment/experiment/experiment_controller.py`):
   - Orchestrates complete experiment lifecycle
   - Manages pre-processing (instrumentation, static analysis)
   - Delegates execution to rv-platform via ExecutionController
   - Handles post-processing and cleanup

2. **Platform** (`modules/rv-platform/src/rv_platform/platform.py`):
   - Central execution engine for Android testing tasks
   - Generates tasks from APK discovery and tool configurations
   - Manages task execution through TaskExecutor with component-based architecture
   - Processes results and generates comprehensive reports

3. **Task Executor** (`modules/rv-platform/src/rv_platform/execution/executor.py`):
   - Component-based task execution with proper lifecycle management
   - Coordinates emulator, static analysis, coverage, logcat, and tool execution components
   - Manages Android emulator sessions and application installation
   - Provides comprehensive error handling and performance monitoring

### AI-Driven Testing Integration

1. **RVAndroid Tool** (`modules/rvandroid-tool/src/rvandroid_tool/tools/rvandroid/tool.py`):
   - AI-guided Android application testing using LLM backends
   - Unified configuration management for LLM and prompt strategies
   - Integration with DroidBot for action execution

2. **LLM Action Service** (`modules/rvandroid-tool/src/rvandroid_tool/llm/service/action_service.py`):
   - Orchestrates AI-driven action generation pipeline
   - Processes application state and generates testing actions
   - Coordinates state enrichment, prompt generation, and response processing

3. **Server Interface** (`modules/rvandroid-tool/src/rvandroid_tool/server.py`):
   - REST API server for DroidBot integration
   - Processes application states and returns generated actions
   - Manages LLM service lifecycle and error recovery

## Module Dependencies and Relationships

### Core Infrastructure Modules
- **rv-android-core**: Provides foundation services (EventBus, ErrorHandler, LoggingManager, domain models)
- **rv-tools**: Tool registry and plugin system used by all testing components
- **rv-llm**: LLM backend integration used by rvandroid-tool

### Analysis and Processing Modules
- **rv-static-analysis**: Provides static analysis data to other modules
- **rv-coverage**: Tracks coverage during task execution
- **rv-screen-parser**: UI parsing for state analysis in AI-driven testing
- **rv-monitor-generator**: Creates runtime verification monitors for instrumentation

### Execution and Orchestration
- **rv-platform**: Central execution engine used by rv-experiment
- **rv-experiment**: Experiment orchestration with pre/post processing
- **rvandroid-tool**: AI-driven testing tool using rv-llm and rv-screen-parser
- **rv-instrumentation**: APK instrumentation using monitors from rv-monitor-generator

## Configuration Management

### Environment Variables
- `RV_PYDANTIC=true`: Enable development validation (recommended during development)
- `RVSEC_HOME`: Required for monitor generation (path to RVSEC installation)
- `ANDROID_HOME`: Android SDK path for emulator management

### Configuration Files
- Tool configurations support unified configuration through Pydantic models
- Experiment configurations in JSON format with validation
- Module-specific configuration classes with composition patterns

## Key Architectural Patterns

### Event-Driven Architecture
- EventBus system (`rv_android_core.event.bus`) coordinates communication
- Components publish lifecycle, task, and error events
- Event handlers provide system monitoring and coordination

### Component-Based Execution
- TaskExecutor uses pluggable components for different execution phases
- Components follow initialize/execute/cleanup lifecycle
- Proper resource management and error handling

### Factory and Registry Patterns
- ToolFactory creates configured tool instances
- ToolRegistry manages available tools and variants
- LLMComponentFactory creates LLM backend instances

### Error Handling Strategy
- ErrorHandler decorator provides consistent error management
- Context-aware error reporting with proper logging
- Graceful degradation and recovery mechanisms

## Testing Strategy

### Test Organization
```bash
# Fast unit tests (no external dependencies)
poetry run pytest -m "not slow" -v

# Integration tests (requires RVSEC)
poetry run pytest -m "slow" -v

# Module-specific testing
poetry run pytest modules/MODULE_NAME/tests/ -v
```

### Test Categories
- Unit tests for individual components and functions
- Integration tests for module interactions
- End-to-end tests for complete workflows
- Performance tests for optimization validation

## Development Guidelines

### Code Structure and Comments
- Use English for all code and comments
- Include detailed comments at architectural decision points
- Follow existing comment templates (EventBus, ExecutionManager, TaskExecutor patterns)
- Comments should reflect current state, not migration history
- Avoid promotional language and bias terms in comments

### Error Handling
- Use ErrorHandler decorators for consistent error management
- Provide meaningful error messages with context
- Implement proper cleanup in error scenarios
- Log errors with appropriate context information

### Configuration Management
- Use unified configuration objects instead of parameter duplication
- Validate configuration at module boundaries
- Provide clear configuration schemas and examples
- Support both programmatic and file-based configuration

### Performance Considerations
- Use PerformanceMonitor for metrics collection
- Implement lazy initialization where appropriate
- Proper resource cleanup and lifecycle management
- Monitor memory usage in long-running operations

## Important Implementation Notes

### Legacy Code Migration
- Remove or replace legacy code without compatibility layers
- Move outdated files to backup directories
- Update all references to use new implementations
- Ensure complete removal of deprecated patterns

### Module Interactions
- rv-experiment coordinates but does not duplicate rv-platform functionality
- rv-platform handles all task execution and result processing
- Clean separation between orchestration (rv-experiment) and execution (rv-platform)
- rvandroid-tool integrates with both rv-llm and rv-platform through defined interfaces

### Instrumentation and Monitoring
- Monitor generation requires RVSEC_HOME environment variable
- APK instrumentation creates monitored versions for runtime verification
- Coverage tracking coordinates with tool execution timing
- Static analysis provides foundation data for other analysis modules

This architecture enables comprehensive Android application testing with runtime verification, AI-driven exploration, and detailed analysis capabilities while maintaining clean separation of concerns and extensibility.