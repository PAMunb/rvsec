# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Architecture Overview

RV-Android is a modular framework for runtime verification of Android applications with LLM-driven testing capabilities. The system uses a Poetry workspace architecture with modules in the `modules` directory.

### Core Architecture Principles

- **Modular Design**: Independent Poetry modules with clear dependencies and interfaces
- **Event-Driven Communication**: EventBus system for coordinated interaction between components
- **Component-Based Execution**: TaskExecutor uses pluggable components for different execution phases
- **Configuration Management**: Unified configuration across all modules using Pydantic models
- **Error Handling**: Error handling with proper context and recovery strategies

### System Modules

The system consists of the following modules:

**Core Infrastructure:**
1. **rv-android-core**: Foundation infrastructure with domain models, event system, error handling, and logging
2. **rv-platform**: Central execution platform coordinating task execution and result processing
3. **rv-tools**: Testing tool plugin system with registry and factory patterns
4. **rv-uiautomator**: Shared UIAutomator components for direct device interaction

**Analysis and Processing:**
5. **rv-monitor-generator**: JavaMOP/RV-Monitor integration for generating runtime verification monitors
6. **rv-instrumentation**: APK instrumentation with monitor weaving capabilities
7. **rv-static-analysis**: Static analysis tools (GATOR, GESDA, REACH) for Android applications
8. **rv-coverage**: Coverage analysis and tracking for monitored operations
9. **rv-screen-parser**: Android UI parsing with visitor patterns for state analysis

**LLM Testing:**
10. **rv-agent**: Main LLM-driven testing tool using LangGraph for workflow orchestration

**Experiment Orchestration:**
11. **rv-experiment**: Experiment orchestration and coordination system
12. **rv-evaluator**: Result evaluation and report generation

## Development Commands

### Environment Setup
```bash
# Set environment variables
export RV_PYDANTIC=true  # Enable validation during development
export RVSEC_HOME="/path/to/rvsec"  # Required for monitor generation
export ANDROID_HOME="/path/to/android-sdk"

# Install all modules in dependency order
cd modules
./install.sh

# Verify installation
poetry run python -c "import rv_android_core, rv_agent; print('Setup complete')"
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

### RV-Agent Commands
```bash
# Run rv-agent with multimode (default: 70% LLM / 30% algorithm)
poetry run rv-agent --package-name com.example.app --device emulator-5554

# Run with pure algorithm (no LLM)
poetry run rv-agent --package-name com.example.app --agent-mode pure_algorithm

# Run with LLM only
poetry run rv-agent --package-name com.example.app --agent-mode llm_only

# Run with specific timeout
poetry run rv-agent --package-name com.example.app --timeout 600

# Run via rv-experiment
poetry run rv-experiment run --tools rv-agent:multimode --apks-dir ./apks_examples
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

3. **rv-agent CLI** (`modules/rv-agent/src/rv_agent/__main__.py`):
   - Standalone LLM-driven testing tool
   - Supports multiple execution modes (pure_algorithm, llm_only, multimode)
   - Can run independently or through rv-platform

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
   - Processes results and generates reports

3. **Task Executor** (`modules/rv-platform/src/rv_platform/execution/executor.py`):
   - Component-based task execution with proper lifecycle management
   - Coordinates emulator, static analysis, coverage, logcat, and tool execution components
   - Manages Android emulator sessions and application installation
   - Provides error handling and performance monitoring

### RV-Agent Integration

1. **RVAgent** (`modules/rv-agent/src/rv_agent/agent/rv_agent.py`):
   - LLM-guided Android application testing using LangGraph
   - Supports three execution modes: pure_algorithm, llm_only, multimode
   - Uses SGLang (OpenAI-compatible API) as LLM backend
   - Externalized workflow nodes in `agent/nodes/` directory

2. **Workflow Nodes** (`modules/rv-agent/src/rv_agent/agent/nodes/`):
   - `parse_node.py`: UI capture and parsing
   - `decision_node.py`: LLM/algorithm routing
   - `algorithm_node.py`: Algorithmic action generation
   - `llm_node.py`: LLM-based action generation
   - `validation_node.py`: Action validation and loop detection
   - `execute_node.py`: Device action execution
   - `learn_node.py`: Memory updates and stuck detection

3. **RVAgentStrategy** (`modules/rv-agent/src/rv_agent/strategies/rvagent_strategy/`):
   - Main exploration strategy with DFS-based traversal
   - Successor Tracker for handling state transitions
   - Plateau Detector for stagnation detection
   - MOP Prioritization for security-sensitive method coverage

4. **LLMClient** (`modules/rv-agent/src/rv_agent/llm/llm_client.py`):
   - LLM interaction and tool call handling
   - Configured for Qwen3-VL model via SGLang

## Module Dependencies and Relationships

### Core Infrastructure Modules
- **rv-android-core**: Provides foundation services (EventBus, ErrorHandler, LoggingManager, domain models)
- **rv-tools**: Tool registry and plugin system used by all testing components
- **rv-uiautomator**: Shared UIAutomator components for device interaction

### Analysis and Processing Modules
- **rv-static-analysis**: Provides static analysis data to other modules
- **rv-coverage**: Tracks coverage during task execution
- **rv-screen-parser**: UI parsing for state analysis in LLM-driven testing
- **rv-monitor-generator**: Creates runtime verification monitors for instrumentation

### Execution and Orchestration
- **rv-platform**: Central execution engine used by rv-experiment
- **rv-experiment**: Experiment orchestration with pre/post processing
- **rv-agent**: Main LLM-driven testing tool
- **rv-instrumentation**: APK instrumentation using monitors from rv-monitor-generator

## Configuration Management

### Environment Variables
- `RV_PYDANTIC=true`: Enable development validation (recommended during development)
- `RVSEC_HOME`: Required for monitor generation (path to RVSEC installation)
- `ANDROID_HOME`: Android SDK path for emulator management
- `RVAGENT_MODE`: Override rv-agent execution mode (pure_algorithm, llm_only, multimode)

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
- AgentFactory creates configured rv-agent instances

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

### RV-Agent Test Structure

The rv-agent module has a well-organized test structure in `modules/rv-agent/tests/`:

| Directory | Purpose | Command |
|-----------|---------|---------|
| `unit/` | Isolated unit tests (no external deps) | `pytest tests/unit/ -v` |
| `integration/` | Component integration tests | `pytest tests/integration/ -v` |
| `smoke/` | Quick sanity checks | `pytest tests/smoke/ -v` |
| `online/` | Tests requiring device/LLM server | `pytest tests/online/ -v` |
| `performance/` | Performance and latency tests | `pytest tests/performance/ -v` |
| `regression/` | Regression tests | `pytest tests/regression/ -v` |
| `system/` | Full system tests | `pytest tests/system/ -v` |
| `fixtures/` | Test data (screenshots, XML dumps) | N/A |

**Running rv-agent tests:**
```bash
cd modules/rv-agent

# Unit tests only (fast, no external dependencies)
PYTHONPATH=../rv-android-core/src:src poetry run pytest tests/unit/ -v

# Smoke tests (quick sanity checks)
PYTHONPATH=../rv-android-core/src:src poetry run pytest tests/smoke/ -v

# All tests
PYTHONPATH=../rv-android-core/src:src poetry run pytest tests/ -v
```

### Test Categories
- Unit tests for individual components and functions
- Integration tests for module interactions
- End-to-end tests for complete workflows
- Performance tests for optimization validation

### Test Data and Datasets
- **Primary screenshot dataset**: `/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots`
  - Contains screenshots from 28+ Android apps for LLM testing
  - Organized by app package name (e.g., `cryptoapp/`, `hashpass/`, `ludo/`)
- **Project test fixtures**: `modules/rv-agent/tests/fixtures/screenshots/`
  - Curated screenshots for unit and integration tests
  - Includes: cryptoapp, hashpass, ludo
- **UI dump fixtures**: `modules/rv-agent/tests/fixtures/ui_dumps/`
  - UIAutomator XML dumps corresponding to screenshots

## Development Guidelines

### Code Structure and Comments
- Use English for all code and comments
- Include comments at architectural decision points
- Comments should reflect current state
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

### Code Evolution Guidelines
- When evolving the system, all changes must be fully implemented
- Do not use strategies that maintain legacy code (e.g., adapters for backwards compatibility)
- Legacy code must be removed or overwritten, not wrapped
- Move old files to the `backup` directory before replacement
- Update all references to use new implementations

### Module Interactions
- rv-experiment coordinates but does not duplicate rv-platform functionality
- rv-platform handles all task execution and result processing
- Clean separation between orchestration (rv-experiment) and execution (rv-platform)
- rv-agent integrates with rv-platform through the tool plugin system

### Instrumentation and Monitoring
- Monitor generation requires RVSEC_HOME environment variable
- APK instrumentation creates monitored versions for runtime verification
- Coverage tracking coordinates with tool execution timing
- Static analysis provides foundation data for other analysis modules

### Specification Sets (Runtime Verification)
The system supports two distinct specification sets for runtime verification:

1. **JCA Specifications**: Detect misuse of Java Cryptography Architecture (JCA) API
   - Example: Proper initialization of ciphers, key generation, secure random

2. **Generic Specifications**: Detect violations of general API usage patterns
   - Example: Must call `hasNext()` before `next()` on Iterator
   - Example: Must close streams after use

**Important**: These sets are used separately in experiments. In one experiment, APKs are instrumented with JCA specifications; in another, with generic specifications. The term "MOP" (Monitored Operations) refers to operations being monitored by ANY specification, not specifically security-related operations. Do not use "security" terminology when referring to MOP - use "monitored operations" instead.

### RV-Agent Specifics
- Uses LangGraph for workflow orchestration
- SGLang server required for LLM backend (default: http://192.168.0.36:30000/v1)
- Default model: Qwen/Qwen3-VL-4B-Instruct
- Multimode default: 70% LLM / 30% algorithm decisions

### Tool Calling Híbrido (Qwen3-VL + SGLang)

**Contexto**: O SGLang não possui suporte oficial a tool calling para modelos Qwen3-VL (vision/multimodal). O comportamento observado é não-determinístico: ~50% native tool_calls, ~50% XML no content.

**Decisão (2026-01-07)**: Usar abordagem híbrida com fallback parser.

**Fluxo**:
1. LangChain `bind_tools()` tenta obter `response.tool_calls` (native)
2. Se vazio, `tool_call_parser.py` extrai do `response.content` (XML/JSON)
3. Ambas as estratégias funcionam com 100% de sucesso

**Estratégias de parsing** (em ordem de prioridade):
- `native`: tool_calls estruturados da API
- `xml`: tags `<tool_call>` no content (formato Hermes)
- `json_array`, `json_object`, `markdown`, `pythonic`: fallbacks adicionais

**Observações**:
- Latência XML (~700ms) é menor que native (~1500ms) devido a menos tokens gerados
- Parser robusto em `rv_agent/llm/tools/tool_call_parser.py`
- Métricas coletadas via `parser_stats.get_stats()`

**Documentação completa**: `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec-vision-llm/docs/022_problema_sglang_native_tools.md`

### Qwen3-VL Coordinate System
- Qwen3-VL returns coordinates in normalized [0, 1000) range for both x and y
- Conversion to device pixels: `pixel_x = int((x / 1000) * device_width)`
- `ActionNormalizer` in `domain/action.py` handles this conversion using `denormalize_qwen_coords()`
- Reference: https://github.com/QwenLM/Qwen3-VL/issues/1486
- Validated empirically: 84.2% hit rate with 20 apps (see `docs/20260107_rvagent_validacao_multimodal.md`)

---

## Current Work

### Active Tasks (2026-01-06)

**Status**: Integração do TransitionManager (WTG) no rv-agent

**Documentos Relevantes**:
- `docs/20260105_rvagent_refactoring.md` - Plano de refatoração com 3 melhorias
- `docs/20251231_rvagent_validacao.md` - Plano de validação extensiva (Seção 13 adicionada)

**Contexto**:
Integração do TransitionManager para guiar exploração usando Window Transition Graph (WTG) da análise estática.

**TransitionManager Integration** (2026-01-06):
- ✅ TransitionManager criado em `services/transition_manager.py`
- ✅ Integrado em `agent_factory.py` (criação)
- ✅ Integrado em `strategy_registry.py` (passagem de parâmetro)
- ✅ Integrado em `rvagent_strategy.py` (uso via `_get_wtg_guided_action`)
- ✅ **NavigationGuidance** criado em `services/navigation_guidance.py` (abstração unificada)
- ✅ Integrado em `llm_client.py` (parâmetro navigation_hint)
- ✅ Integrado em `llm_node.py` (obtém guidance e passa para LLM)
- ✅ Integrado em `prompts/v12.py` (build_user_message aceita navigation_hint)

**Melhorias Planejadas** (3 de alta prioridade):
1. **Failed Actions Tracking**: Evitar re-execução de ações que causaram crash
2. **UI Mutation Detection**: Detectar mudanças de estado enabled/disabled/checked
3. **Scroll Detection**: Revelar conteúdo oculto em listas e views scrollable

**Fluxo de Trabalho**:
1. ✅ Análise de sugestões de outras LLMs
2. ✅ Criação do plano de refatoração (`docs/20260106_rvagent_refactoring.md`)
3. ✅ Integração do TransitionManager (algoritmo)
4. ⏳ Integração do TransitionManager (LLM) - ver TODO acima
5. ⏳ Executar validação baseline (14 apps, 4 estratégias)
6. ⏳ Analisar resultados e refinar plano
7. ⏳ Implementar melhorias restantes
8. ⏳ Validar novamente e comparar com baseline

**Arquivos Principais do rv-agent**:
- `modules/rv-agent/src/rv_agent/agent/rv_agent.py` - Agente principal (LangGraph)
- `modules/rv-agent/src/rv_agent/agent/nodes/` - Nodes externalizados do workflow
- `modules/rv-agent/src/rv_agent/agent/dynamic_state_graph.py` - Grafo de estados
- `modules/rv-agent/src/rv_agent/strategies/rvagent_strategy/` - Estratégia principal
- `modules/rv-agent/src/rv_agent/strategies/base_strategy.py` - Classe base de estratégias
- `modules/rv-agent/src/rv_agent/services/transition_manager.py` - Integração WTG + DynamicGraph
- `modules/rv-agent/src/rv_agent/services/navigation_guidance.py` - Abstração unificada para LLM e algoritmo
- `modules/rv-agent/src/rv_agent/routing/` - Routing entre LLM e algoritmo
- `modules/rv-agent/src/rv_agent/llm/llm_client.py` - Cliente LLM com navigation_hint
- `modules/rv-agent/src/rv_agent/prompts/v12.py` - Prompt com suporte a navigation guidance
