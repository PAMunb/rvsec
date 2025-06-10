# RVAndroid-Tool Module

Modern AI-driven Android testing server with advanced LLM integration, sophisticated screenshot analysis, and intelligent action generation for comprehensive monitored operations testing with dependency injection architecture.

## Overview

The RVAndroid-Tool module provides a sophisticated AI-driven testing server that combines cutting-edge Large Language Model integration with advanced Android UI analysis to generate contextually-aware and semantically-rich testing actions. It serves as the premier implementation for AI-guided testing in the RV-Android ecosystem, implementing modern architecture patterns with comprehensive error handling, memory management, and multi-provider LLM support.

### Key Features

- **Advanced LLM Integration**: Comprehensive integration with multiple language model providers using rv-llm factories for Ollama, OpenAI, Anthropic, and other providers
- **Sophisticated Screenshot Analysis**: Advanced UI analysis with intelligent action recommendation, visual element detection, and context-aware interpretation
- **Modern Memory Management**: Multi-layered memory systems with long-term pattern learning, short-term context retention, and state transition optimization
- **RESTful Server Architecture**: Modern HTTP server with comprehensive API endpoints, error handling, and standardized response formatting
- **Intelligent Action Generation**: Context-aware Android action generation with constraint handling, semantic understanding, and goal-oriented planning
- **Advanced State Analysis**: Sophisticated UI state understanding with transition planning, pattern recognition, and optimization strategies
- **DI-Ready Tool Integration**: Seamless integration with Android testing tools, emulators, and testing frameworks through modern architecture patterns

## Architecture

### Core Components

#### LLM Service Layer
- **LLMManager**: Centralized language model orchestration and configuration
- **ActionService**: LLM-powered action generation with context awareness
- **ActionGenerator**: Sophisticated action planning and optimization
- **ResponseProcessor**: LLM response parsing and validation
- **StateAnalyzer**: UI state analysis and interpretation

#### Memory Management
- **MemoryManager**: Comprehensive memory coordination and persistence
- **LongTermMemory**: Persistent storage for learned patterns and strategies
- **ShortTermMemory**: Session-based context and action history management
- **StateEnricher**: Context enhancement with historical and static analysis data
- **TransitionManager**: State transition tracking and optimization

#### Screenshot Analysis
- **ScreenshotAnalyzer**: Advanced UI element detection and classification
- **ScreenshotActionComplementor**: Action enhancement based on visual analysis
- **ScreenshotManager**: Screenshot capture and processing coordination

#### Server Infrastructure
- **Server**: Main HTTP server with RESTful API endpoints
- **RequestHandler**: HTTP request processing and routing
- **ResponseFormatter**: Standardized response formatting and error handling

### Integration Points

- **rv-llm**: Uses LLMFactory and PromptStrategyFactory for advanced language model integration and sophisticated prompt generation
- **rv-screen-parser**: Integrates screen parsing capabilities for comprehensive UI state analysis and element detection
- **rv-android-core**: Uses ErrorHandler decorators, LoggingManager, EventBus, and domain models for complete infrastructure integration
- **rv-experiment**: Provides AI-driven testing capabilities for experiment orchestration and intelligent test execution
- **rv-static-analysis**: Integrates static analysis data for enhanced context and intelligent action planning
- **rv-coverage**: Coordinates with coverage tracking for goal-oriented testing and optimization strategies
- **rv-android-core**: Base infrastructure, error handling, and event system
- **rv-coverage**: Coverage information for testing optimization
- **Testing Tools**: Direct integration with DroidBot, Monkey, and other testing frameworks

## Installation

### Prerequisites

- Python 3.12+
- Poetry for dependency management
- rv-android-core, rv-llm, and rv-screen-parser modules
- LLM provider access (Ollama, OpenAI API key, etc.)
- Android SDK and emulator for testing

### Setup

```bash
# Install dependencies
poetry install

# Run tests
poetry run pytest

# Install in development mode
poetry install --extras dev
```

## Usage

### HTTP Server

#### Starting the Server

```bash
# Start with default configuration
rvandroid-tool server --port 8080

# Start with custom LLM configuration
rvandroid-tool server \
    --port 8080 \
    --llm-provider ollama \
    --llm-model llama3.2:3b \
    --temperature 0.2

# Start with advanced memory configuration
rvandroid-tool server \
    --port 8080 \
    --memory-dir /path/to/memory \
    --enable-long-term-memory \
    --memory-persistence-interval 300
```

#### API Endpoints

##### Action Generation
```bash
# Generate actions for current screen
curl -X POST http://localhost:8080/api/actions/generate \
  -H "Content-Type: application/json" \
  -d '{
    "screenshot_path": "/path/to/screenshot.png",
    "current_activity": "MainActivity",
    "action_history": [...],
    "constraints": ["avoid_destructive_actions"],
    "strategy": "exploration"
  }'

# Response
{
  "actions": [
    {
      "type": "click",
      "coordinates": [100, 200],
      "description": "Click login button",
      "confidence": 0.95,
      "reasoning": "Login button appears to be the primary action"
    }
  ],
  "strategy_recommendation": "continue_exploration",
  "confidence": 0.92
}
```

##### State Analysis
```bash
# Analyze current UI state
curl -X POST http://localhost:8080/api/state/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "screenshot_path": "/path/to/screenshot.png",
    "ui_hierarchy": "...",
    "context": {...}
  }'

# Response
{
  "state_type": "login_screen",
  "ui_elements": [...],
  "interaction_opportunities": [...],
  "recommended_strategy": "form_completion",
  "risk_assessment": "low"
}
```

##### Memory Management
```bash
# Store action results
curl -X POST http://localhost:8080/api/memory/store \
  -H "Content-Type: application/json" \
  -d '{
    "action": {...},
    "result": "success",
    "state_before": {...},
    "state_after": {...},
    "coverage_impact": {...}
  }'

# Retrieve relevant memories
curl -X GET http://localhost:8080/api/memory/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "current_state": {...},
    "query_type": "similar_situations",
    "limit": 10
  }'
```

### Programmatic Interface

```python
from rvandroid_tool.llm.service.action_service import ActionService
from rvandroid_tool.llm.service.memory_manager import MemoryManager
from rvandroid_tool.analysis.screenshot.screenshot_analyzer import ScreenshotAnalyzer

# Initialize components
action_service = ActionService(llm_config)
memory_manager = MemoryManager(memory_config)
screenshot_analyzer = ScreenshotAnalyzer()

# Analyze screenshot and generate actions
screenshot_data = screenshot_analyzer.analyze("/path/to/screenshot.png")
context = memory_manager.get_relevant_context(screenshot_data)

actions = action_service.generate_actions(
    screenshot_data=screenshot_data,
    context=context,
    constraints=["avoid_destructive_actions"],
    strategy="systematic_exploration"
)

# Store results for learning
memory_manager.store_action_result(
    action=actions[0],
    result="success",
    context=context
)
```

### LLM Configuration

```python
from rvandroid_tool.llm.service.llm_manager import LLMManager
from rv_llm.llm.llm_config import LLMConfiguration

# Configure LLM provider
llm_config = LLMConfiguration(
    model_type="ollama",
    model_name="llama3.2:3b",
    temperature=0.2,
    max_tokens=800,
    strategy_type="standard"
)

llm_manager = LLMManager(llm_config)

# Generate contextual response
response = llm_manager.generate_response(
    prompt="Analyze this Android screen and suggest testing actions",
    context={
        "screenshot_analysis": screenshot_data,
        "testing_history": action_history,
        "coverage_info": coverage_metrics
    }
)
```

### Memory System Usage

```python
from rvandroid_tool.core.memory.long_term_memory import LongTermMemory
from rvandroid_tool.core.memory.short_term_memory import ShortTermMemory

# Initialize memory systems
long_term = LongTermMemory("/path/to/memory/db")
short_term = ShortTermMemory(max_history=100)

# Store successful patterns
long_term.store_successful_pattern(
    pattern_type="login_flow",
    context={"screen_type": "login", "app_category": "social"},
    actions=[...],
    success_rate=0.95
)

# Retrieve relevant patterns
patterns = long_term.get_patterns_by_context(
    context={"screen_type": "login"},
    min_success_rate=0.8
)

# Manage short-term context
short_term.add_action(action, result, context)
recent_context = short_term.get_recent_context(window_size=10)
```

## Configuration

### Server Configuration

```yaml
# rvandroid-server.yml
server:
  host: "0.0.0.0"
  port: 8080
  debug: false
  cors_enabled: true

llm:
  provider: "ollama"
  model: "llama3.2:3b"
  temperature: 0.2
  max_tokens: 800
  timeout: 30

memory:
  enable_long_term: true
  persistence_interval: 300
  max_short_term_history: 100
  database_path: "/tmp/rvandroid_memory"

analysis:
  screenshot_timeout: 10
  ui_parsing_strategy: "enhanced"
  confidence_threshold: 0.7
```

### Action Generation Settings

```python
action_config = {
    "strategies": {
        "exploration": {
            "priority": ["unvisited_elements", "form_fields", "buttons"],
            "avoid": ["destructive_actions", "exit_actions"],
            "depth_limit": 5
        },
        "systematic": {
            "priority": ["coverage_optimization", "state_coverage"],
            "methodical": True,
            "backtrack_enabled": True
        }
    },
    "constraints": {
        "safety": ["no_uninstall", "no_factory_reset", "no_payment"],
        "scope": ["current_app_only", "avoid_system_settings"],
        "resource": ["respect_rate_limits", "manage_memory"]
    }
}
```

## API Reference

### Action Generation API

#### POST /api/actions/generate

Generate intelligent actions for current screen state.

**Request Body:**
```json
{
  "screenshot_path": "string",
  "ui_hierarchy": "string (optional)",
  "current_activity": "string",
  "action_history": "array",
  "constraints": "array",
  "strategy": "string",
  "context": "object"
}
```

**Response:**
```json
{
  "actions": [
    {
      "type": "click|swipe|type|back|home",
      "coordinates": [x, y],
      "text": "string (for type actions)",
      "description": "string",
      "confidence": "float",
      "reasoning": "string"
    }
  ],
  "strategy_recommendation": "string",
  "confidence": "float",
  "estimated_impact": "object"
}
```

### State Analysis API

#### POST /api/state/analyze

Analyze current UI state and provide insights.

**Request Body:**
```json
{
  "screenshot_path": "string",
  "ui_hierarchy": "string (optional)",
  "context": "object"
}
```

**Response:**
```json
{
  "state_type": "string",
  "ui_elements": "array",
  "interaction_opportunities": "array",
  "recommended_strategy": "string",
  "risk_assessment": "string",
  "complexity_score": "float"
}
```

### Memory API

#### POST /api/memory/store

Store action results for learning.

#### GET /api/memory/retrieve

Retrieve relevant historical context.

#### GET /api/memory/stats

Get memory system statistics.

## Integration Examples

### With DroidBot

```python
# DroidBot integration with RVAndroid server
import droidbot
import requests

class RVAndroidPolicy(droidbot.Policy):
    def __init__(self):
        self.rvandroid_url = "http://localhost:8080"
        
    def generate_event(self, device_state):
        # Send screenshot to RVAndroid server
        screenshot_path = device_state.screenshot_path
        
        response = requests.post(f"{self.rvandroid_url}/api/actions/generate", 
                               json={
                                   "screenshot_path": screenshot_path,
                                   "current_activity": device_state.foreground_activity,
                                   "action_history": self.get_action_history(),
                                   "strategy": "exploration"
                               })
        
        actions = response.json()["actions"]
        return self.convert_to_droidbot_event(actions[0])
```

### With Testing Framework

```bash
# Start RVAndroid server
rvandroid-tool server --port 8080 &

# Run testing framework with RVAndroid integration
python test_runner.py \
    --rvandroid-server http://localhost:8080 \
    --strategy ai_guided \
    --max-actions 1000
```

### With Experiment Pipeline

```python
# Integration with rv-experiment
from rv_experiment.experiment.task.components import ToolExecutionComponent

class RVAndroidComponent(ToolExecutionComponent):
    def setup(self):
        # Start RVAndroid server
        self.start_rvandroid_server()
        
    def execute_tool(self, task, app):
        # Configure tool to use RVAndroid server
        tool_config = {
            "rvandroid_server": "http://localhost:8080",
            "strategy": "systematic_exploration",
            "memory_enabled": True
        }
        
        return self.run_with_rvandroid(task, app, tool_config)
```

## Performance Characteristics

### LLM Response Times
- **Local Models (Ollama)**: 2-5 seconds per action generation
- **Cloud Models (OpenAI)**: 1-3 seconds per action generation
- **Caching**: 50ms for cached similar scenarios

### Memory Operations
- **Pattern Storage**: < 100ms per pattern
- **Pattern Retrieval**: < 50ms for relevant context lookup
- **Memory Persistence**: Background operation, non-blocking

### Screenshot Analysis
- **UI Parsing**: 200-500ms per screenshot
- **Element Detection**: 100-300ms per screen
- **Action Recommendation**: 50-150ms per suggestion

## Error Handling

The server provides comprehensive error handling:

- **LLM Errors**: Provider failures, rate limiting, timeout handling
- **Screenshot Errors**: Invalid images, parsing failures, format issues
- **Memory Errors**: Database issues, persistence failures, corruption recovery
- **API Errors**: Malformed requests, authentication, rate limiting
- **Integration Errors**: Tool communication failures, emulator issues

## Testing

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=rvandroid_tool

# Run specific test categories
poetry run pytest tests/analysis/screenshot/
poetry run pytest tests/llm/service/
```

### Test Structure

- `tests/analysis/screenshot/`: Screenshot analysis functionality
- `tests/llm/service/`: LLM service integration tests
- `tests/core/memory/`: Memory system validation
- `tests/server/`: HTTP server and API tests

### Current Test Status

Tests are focused on core functionality with mock integrations for external dependencies.

## Dependencies

- `rv-android-core`: Core infrastructure and utilities
- `rv-llm`: Language model integration framework
- `rv-screen-parser`: UI parsing and analysis
- `requests`: HTTP client for API integrations
- `flask`: HTTP server framework
- `sqlite3`: Memory persistence (for LongTermMemory)

## Contributing

### Development Guidelines

1. Follow existing architectural patterns for service components
2. Use comprehensive error handling with rv-android-core infrastructure
3. Implement proper logging for debugging and monitoring
4. Add integration tests for new API endpoints
5. Document LLM prompt engineering decisions

### API Design Principles

1. Maintain RESTful API conventions
2. Use consistent response formats across endpoints
3. Implement proper authentication and rate limiting
4. Provide comprehensive error responses with context
5. Follow semantic versioning for API changes

## License

This module is part of the RV-Android project and follows the same licensing terms.