# RVDroid Refactoring Plan

This document outlines a comprehensive refactoring plan for the RVDroid tool within the rv-android platform. The plan addresses issues including oversized modules, code duplication, inconsistent terminology, and suboptimal memory management. This refactoring will create a more maintainable, modular architecture while preserving existing functionality.

## System Context and Component Separation

The rv-android platform consists of several distinct components that must be properly understood and respected during this refactoring:

1. **RV-Android**: The core platform that instruments APKs with monitors (JavaMOP and AspectJ) to verify properties at runtime
2. **RVAndroid**: A testing tool that integrates with DroidBot and uses a server interface for AI-guided testing
3. **RVDroid**: An advanced testing tool with memory systems, UI pattern detection, and direct UIAutomator integration
4. **Test Framework**: A separate system for evaluating and comparing different LLM configurations

This refactoring plan **ONLY** affects the RVDroid component and should not modify code outside the `rvandroid/rvdroid/` directory, to avoid breaking other components. Any shared functionality should be properly reused from existing packages rather than recreated.

## Current Issues

1. **Oversized Modules**: Several modules, particularly `service.py`, contain too many responsibilities, making them difficult to maintain and test.
2. **Inconsistent Terminology**: References to "security" throughout the codebase should be updated to "monitored operations" for consistency.
3. **Duplicated Code**: Redundant implementations, especially in UI automation adapters.
4. **Poor Memory Management**: Lack of clear separation between short-term and long-term memory.
5. **Suboptimal Error Handling**: Not consistently using the provided error handling utilities.
6. **Inadequate Documentation**: Missing or incomplete English documentation.

## Refactoring Guidelines

1. **Focus on RVDroid Only**: Changes must be limited to the `rvandroid/rvdroid/` directory, with minimal or no impact on other components.
2. **Use Existing Components**: Leverage existing platform components such as:
   - Error handling (`rvandroid/util/error/error_handler.py`)
   - Logging (`rvandroid/util/logging/manager.py`) 
   - LLM integration (`rvandroid/llm/`)
   - Event Bus (`rvandroid/experiment/event/bus.py`) to listen for events (coverage, mop errors, etc.) if needed
   - Decorators: rvandroid/util/decorators.py, rvandroid/util/error/decorators.py, rvandroid/experiment/event/decorators.py
   - Performance monitoring: rvandroid/util/performance_monitor.py
3. **Complete Migrations**: Do not use adapter patterns or compatibility layers to maintain legacy code. Completely update all code to the new architecture and remove legacy approaches.
4. **English Documentation**: All code comments and documentation must be in English.
5. **Detailed Comments**: Include detailed architectural comments at key points in the code, following the established template pattern (as seen in EventBus, ExecutionManager, TaskExecutor).
6. **Maintain Public Interface**: The public interfaces used by `tools/rvdroid/tool.py` must remain stable to avoid breaking tool integration.

## Directory Structure and Component Organization

### Core Components

```
rvandroid/rvdroid/
├── __init__.py
├── runner.py          # Main entry point (refactored from tool.py)
├── core/
│   ├── __init__.py
│   ├── component.py   # Base component interface
│   ├── lifecycle.py   # Component lifecycle management
│   ├── registry.py    # Component registration and discovery
│   ├── coordinator.py # Orchestration (extracted from service.py)
│   └── config.py      # Configuration management
├── memory/
│   ├── __init__.py
│   ├── interfaces.py  # Memory system interfaces
│   ├── short_term.py  # Short-term memory implementation
│   ├── long_term.py   # Long-term memory implementation
│   ├── factory.py     # Memory factory
│   └── manager.py     # Memory management system
├── ui/
│   ├── __init__.py
│   ├── interfaces.py  # UI interaction interfaces
│   ├── adapter.py     # Base UI adapter
│   ├── uiautomator.py # UIAutomator2 implementation
│   ├── screen.py      # Screen representation
│   └── element.py     # UI element representation
├── strategy/
│   ├── __init__.py
│   ├── interfaces.py   # Strategy interfaces
│   ├── basic.py        # Basic strategies (renamed from basic_strategies.py)
│   ├── advanced.py     # Advanced strategies (renamed from advanced_strategies.py)
│   ├── factory.py      # Strategy factory
│   └── context.py      # Strategy context and execution
├── patterns/
│   ├── __init__.py
│   ├── interfaces.py   # Pattern detector interfaces
│   ├── dialog.py       # Dialog pattern detection
│   ├── form.py         # Form pattern detection
│   ├── list.py         # List pattern detection
│   ├── navigation.py   # Navigation pattern detection
│   └── registry.py     # Pattern detector registry
└── util/
    ├── __init__.py
    ├── error_handler.py # Error handling utilities (using existing)
    ├── logging.py       # Logging utilities (using existing)
    └── decorators.py    # Utility decorators
```

## Module Responsibilities

### Runner Module (previously tool.py)

The main entry point for RVDroid, responsible for:
- Processing command-line arguments
- Initializing the system
- Configuring components
- Starting the test execution
- Handling shutdown and cleanup

```python
# High-level pseudocode for runner.py
class RVDroidRunner:
    def __init__(self, config_path=None):
        self.config = self._load_config(config_path)
        self.coordinator = None
        
    @error_handler.handle_error(level="FATAL")
    def initialize(self):
        """Initialize the RVDroid system"""
        # Initialize component registry
        # Load configurations
        # Setup logging
        # Configure error handling
        
    @error_handler.handle_error(level="FATAL")
    def setup_components(self):
        """Configure and register all system components"""
        # Initialize memory system
        # Initialize UI adapter
        # Initialize strategy factory
        # Initialize pattern detectors
        # Initialize coordinator
        
    @error_handler.handle_error(level="FATAL")
    def run(self, apk_path, output_dir=None):
        """Run testing on the specified APK"""
        # Start coordinator
        # Execute testing process
        # Collect results
        
    @error_handler.handle_error(level="WARN")
    def shutdown(self):
        """Perform clean shutdown of all components"""
        # Stop all components
        # Save state if needed
        # Clean up resources
```

### Core Coordinator (extracted from service.py)

Responsible for orchestrating the testing process:
- Managing the testing lifecycle
- Delegating to specialized components
- Handling events and state transitions
- Coordinating between different subsystems

```python
# High-level pseudocode for coordinator.py
class TestingCoordinator:
    def __init__(self, config):
        self.config = config
        self.memory_manager = None
        self.ui_adapter = None
        self.strategy_factory = None
        self.current_strategy = None
        self.pattern_registry = None
        self.event_bus = None
        
    @error_handler.handle_error(level="ERROR")
    def initialize(self):
        """Initialize the coordinator and all required components"""
        # Initialize subsystems
        # Register event handlers
        
    @error_handler.handle_error(level="ERROR")
    def start_testing(self, apk_path):
        """Start the testing process for the given APK"""
        # Select initial strategy
        # Initialize application state
        # Begin execution cycle
        
    @error_handler.handle_error(level="WARN")
    def execute_cycle(self):
        """Execute a single testing cycle"""
        # Get current screen state
        # Analyze UI patterns
        # Update memory
        # Get next action from strategy
        # Execute action
        # Record results
        
    @error_handler.handle_error(level="WARN")
    def handle_error(self, error):
        """Handle errors during execution"""
        # Log error details
        # Attempt recovery if possible
        # Update error statistics
        
    @error_handler.handle_error(level="WARN")
    def shutdown(self):
        """Shutdown the coordinator and all components"""
        # Stop all components
        # Generate final reports
        # Clean up resources
```

### Memory System

Redesigned to clearly separate short-term and long-term memory:

#### Memory Interfaces

```python
# High-level pseudocode for memory/interfaces.py
class MemorySystem:
    """Base interface for all memory systems"""
    def store(self, key, value, metadata=None):
        """Store a value in memory"""
        pass
        
    def retrieve(self, key):
        """Retrieve a value from memory"""
        pass
        
    def update(self, key, value, metadata=None):
        """Update an existing value"""
        pass
        
    def remove(self, key):
        """Remove a value from memory"""
        pass
        
    def clear(self):
        """Clear all memory contents"""
        pass

class ShortTermMemory(MemorySystem):
    """Interface for short-term memory operations"""
    def get_recent_screens(self, count=5):
        """Get the most recent screens"""
        pass
        
    def get_recent_actions(self, count=5):
        """Get the most recent actions"""
        pass
        
    def record_action(self, action, result):
        """Record an action and its result"""
        pass
        
    def record_screen(self, screen):
        """Record a screen state"""
        pass

class LongTermMemory(MemorySystem):
    """Interface for long-term memory operations"""
    def record_pattern(self, pattern, context):
        """Record a UI pattern"""
        pass
        
    def get_patterns_for_screen(self, screen):
        """Get patterns relevant to the current screen"""
        pass
        
    def record_successful_action(self, screen_signature, action):
        """Record actions that were successful on a particular screen type"""
        pass
        
    def get_successful_actions(self, screen_signature):
        """Get actions that were previously successful on similar screens"""
        pass
        
    def store_persistent(self, key, value):
        """Store data that should persist across test runs"""
        pass
```

#### Memory Implementation

```python
# High-level pseudocode for memory/short_term.py
class ShortTermMemoryImpl(ShortTermMemory):
    """Implementation of short-term memory system"""
    def __init__(self, config):
        self.config = config
        self.screens = []  # Circular buffer for recent screens
        self.actions = []  # Circular buffer for recent actions
        self.current_path = []  # Path taken in current session
        
    @error_handler.handle_error(level="WARN")
    def record_screen(self, screen):
        """Record a screen state in short-term memory"""
        # Add screen to circular buffer
        # Update current path
        # Trigger screen recorded event
        
    @error_handler.handle_error(level="WARN")
    def record_action(self, action, result):
        """Record an action and its result"""
        # Add action to circular buffer
        # Record success/failure
        # Trigger action recorded event
        
    # Additional short-term memory methods
```

```python
# High-level pseudocode for memory/long_term.py
class LongTermMemoryImpl(LongTermMemory):
    """Implementation of long-term memory system"""
    def __init__(self, config, persistence_manager=None):
        self.config = config
        self.persistence_manager = persistence_manager
        self.patterns = {}  # Stored UI patterns
        self.successful_actions = {}  # Actions that worked on specific screen types
        self.screen_frequencies = {}  # How often each screen type is encountered
        
    @error_handler.handle_error(level="WARN")
    def record_pattern(self, pattern, context):
        """Record a UI pattern in long-term memory"""
        # Store pattern with context
        # Update pattern statistics
        
    @error_handler.handle_error(level="WARN")
    def record_successful_action(self, screen_signature, action):
        """Record an action that was successful on a particular screen"""
        # Store successful action
        # Update action statistics for screen type
        
    # Additional long-term memory methods
```

```python
# High-level pseudocode for memory/manager.py
class MemoryManager:
    """Manages both short-term and long-term memory"""
    def __init__(self, config):
        self.config = config
        self.short_term = None
        self.long_term = None
        
    @error_handler.handle_error(level="ERROR")
    def initialize(self):
        """Initialize memory systems"""
        # Create short-term memory
        # Create long-term memory
        # Connect event handlers
        
    @error_handler.handle_error(level="WARN")
    def transfer_to_long_term(self):
        """Transfer relevant data from short-term to long-term memory"""
        # Identify patterns to remember
        # Extract successful action sequences
        # Update long-term memory
        
    @error_handler.handle_error(level="WARN") 
    def get_combined_context(self):
        """Get combined context from both memory systems"""
        # Get recent history from short-term
        # Get relevant patterns from long-term
        # Combine for decision making
        
    # Additional memory management methods
```

### UI Adapter System

Refactored to provide a cleaner interface and reduce duplication:

```python
# High-level pseudocode for ui/interfaces.py
class UIAdapter:
    """Base interface for UI automation adapters"""
    @error_handler.handle_error(level="ERROR")
    def initialize(self, package_name):
        """Initialize the UI adapter for the specified package"""
        pass
        
    @error_handler.handle_error(level="WARN")
    def get_current_screen(self):
        """Get the current screen state"""
        pass
        
    @error_handler.handle_error(level="WARN")
    def perform_action(self, action):
        """Perform the specified UI action"""
        pass
        
    @error_handler.handle_error(level="WARN")
    def check_element_exists(self, element_id):
        """Check if an element exists on the current screen"""
        pass
        
    @error_handler.handle_error(level="WARN")
    def get_element_attributes(self, element):
        """Get attributes of the specified element"""
        pass
        
    @error_handler.handle_error(level="ERROR")
    def take_screenshot(self):
        """Take a screenshot of the current screen"""
        pass
        
    @error_handler.handle_error(level="ERROR")
    def shutdown(self):
        """Shut down the UI adapter"""
        pass
```

```python
# High-level pseudocode for ui/uiautomator.py
class UIAutomator2Adapter(UIAdapter):
    """UIAutomator2 implementation of the UI adapter"""
    def __init__(self, config):
        self.config = config
        self.device = None
        self.session = None
        
    @error_handler.handle_error(level="ERROR")
    def initialize(self, package_name):
        """Initialize UIAutomator2 for the specified package"""
        # Connect to device
        # Start application
        # Initialize session
        
    @error_handler.handle_error(level="WARN")
    def get_current_screen(self):
        """Get the current screen state using UIAutomator2"""
        # Dump UI hierarchy
        # Parse into screen model
        # Extract active elements
        # Return screen object
        
    @error_handler.handle_error(level="WARN")
    def perform_action(self, action):
        """Perform UI action using UIAutomator2"""
        # Map action to UIAutomator2 commands
        # Execute command
        # Wait for UI to stabilize
        # Return action result
        
    # Additional UIAutomator2-specific methods
```

### Strategy System

Refactored to improve strategy management and selection:

```python
# High-level pseudocode for strategy/interfaces.py
class TestStrategy:
    """Base interface for all test strategies"""
    def initialize(self, app_info, memory_manager):
        """Initialize the strategy"""
        pass
        
    def decide_next_action(self, current_screen, memory_context):
        """Decide the next action to take based on current state"""
        pass
        
    def handle_result(self, action, result):
        """Process the result of an action"""
        pass
        
    def should_continue(self):
        """Determine if the strategy should continue or switch"""
        pass
        
    def get_progress(self):
        """Get the progress made by this strategy"""
        pass
```

```python
# High-level pseudocode for strategy/basic.py
class RandomExplorationStrategy(TestStrategy):
    """Simple random exploration strategy"""
    def __init__(self, config):
        self.config = config
        self.app_info = None
        self.memory_manager = None
        
    @error_handler.handle_error(level="WARN")
    def initialize(self, app_info, memory_manager):
        """Initialize the random exploration strategy"""
        self.app_info = app_info
        self.memory_manager = memory_manager
        
    @error_handler.handle_error(level="WARN")
    def decide_next_action(self, current_screen, memory_context):
        """Randomly select an action from available options"""
        # Get all interactive elements
        # Randomly select one
        # Create action object
        # Return action
        
    # Additional methods

class MonitoredOperationsFocusedStrategy(TestStrategy):
    """Strategy focused on monitored operations (renamed from SecurityFocusedStrategy)"""
    def __init__(self, config):
        self.config = config
        self.app_info = None
        self.memory_manager = None
        self.monitored_operations = []
        
    @error_handler.handle_error(level="WARN")
    def initialize(self, app_info, memory_manager):
        """Initialize the monitored operations strategy"""
        self.app_info = app_info
        self.memory_manager = memory_manager
        # Load monitored operations specifications
        # Initialize operation priorities
        
    @error_handler.handle_error(level="WARN")
    def decide_next_action(self, current_screen, memory_context):
        """Select action most likely to trigger monitored operations"""
        # Analyze screen for monitored operation related elements
        # Prioritize elements based on monitored operation coverage
        # Select highest priority action
        # Return action
        
    # Additional methods
```

```python
# High-level pseudocode for strategy/factory.py
class StrategyFactory:
    """Factory for creating and managing test strategies"""
    def __init__(self, config):
        self.config = config
        self.strategies = {}
        self.strategy_configs = {}
        
    @error_handler.handle_error(level="ERROR")
    def initialize(self):
        """Initialize the strategy factory"""
        # Register all available strategies
        # Load strategy configurations
        
    @error_handler.handle_error(level="WARN")
    def create_strategy(self, strategy_name):
        """Create a strategy instance by name"""
        # Get strategy class
        # Create instance with configuration
        # Return instance
        
    @error_handler.handle_error(level="WARN")
    def get_strategy_for_context(self, context):
        """Select appropriate strategy based on testing context"""
        # Analyze context
        # Apply selection rules
        # Return best strategy for current situation
        
    # Additional factory methods
```

### Pattern Detection System

Expanded to better handle UI pattern recognition:

```python
# High-level pseudocode for patterns/interfaces.py
class PatternDetector:
    """Base interface for UI pattern detectors"""
    def initialize(self):
        """Initialize the pattern detector"""
        pass
        
    def detect(self, screen, memory_context=None):
        """Detect patterns in the given screen"""
        pass
        
    def get_pattern_id(self):
        """Get the unique identifier for this pattern type"""
        pass
        
    def get_confidence(self):
        """Get confidence level in the detection (0.0-1.0)"""
        pass
```

```python
# High-level pseudocode for patterns/dialog.py
class DialogDetector(PatternDetector):
    """Detector for dialog UI patterns"""
    def __init__(self, config):
        self.config = config
        self.detection_rules = []
        self.confidence_threshold = 0.7
        
    @error_handler.handle_error(level="WARN")
    def initialize(self):
        """Initialize the dialog detector"""
        # Load detection rules
        # Configure confidence threshold
        
    @error_handler.handle_error(level="WARN")
    def detect(self, screen, memory_context=None):
        """Detect dialog patterns in the screen"""
        # Apply detection rules
        # Calculate confidence score
        # Return detection result if above threshold
        
    # Additional dialog detector methods
```

```python
# High-level pseudocode for patterns/registry.py
class PatternRegistry:
    """Registry for UI pattern detectors"""
    def __init__(self, config):
        self.config = config
        self.detectors = {}
        
    @error_handler.handle_error(level="ERROR")
    def initialize(self):
        """Initialize the pattern registry"""
        # Register all pattern detectors
        # Initialize each detector
        
    @error_handler.handle_error(level="WARN")
    def detect_all_patterns(self, screen, memory_context=None):
        """Run all pattern detectors on the given screen"""
        # Apply each detector
        # Collect results
        # Resolve conflicts
        # Return combined results
        
    @error_handler.handle_error(level="WARN")
    def get_detector(self, pattern_id):
        """Get a specific pattern detector by ID"""
        # Return detector if registered
        
    # Additional registry methods
```

## Terminology Updates

The following terminology changes will be applied throughout the RVDroid codebase:

| Old Term | New Term |
|----------|----------|
| Security Analysis | Monitored Operations Analysis |
| Security Violation | Monitored Operation Violation |
| Security Focused Strategy | Monitored Operations Focused Strategy |
| Security Event | Monitored Operation Event |
| Security Specification | Monitored Operation Specification |
| Security Coverage | Monitored Operation Coverage |
| Security Rule | Monitored Operation Rule |

Files requiring terminology updates are **strictly limited to the RVDroid directory**:
- `rvandroid/rvdroid/strategy/basic_strategies.py`
- `rvandroid/rvdroid/strategy/advanced_strategies.py`
- `rvandroid/rvdroid/core/service.py`

NOTE: Do NOT modify files outside the RVDroid directory, such as:
- ~~rvandroid/tools/rvdroid/tool.py~~ (leave this unchanged)
- ~~rvandroid/domain/coverage.py~~ (leave this unchanged)
- ~~rvandroid/analysis/results/processor.py~~ (leave this unchanged)

The terminology changes must be contained within the RVDroid component to avoid breaking other parts of the system.

## Integration with Error Handling and Logging

All components will consistently use the error handling and logging decorators from `rvandroid/util/error/error_handler.py` and `rvandroid/util/logging/manager.py`. Key principles include:

1. **Appropriate Error Levels**:
   - FATAL: Errors that prevent system initialization or operation
   - ERROR: Serious errors affecting functionality but not fatal
   - WARN: Issues that might affect results but allow continued operation
   - INFO: Informational messages about normal operation

2. **Contextual Logging**:
   - Include relevant context with all log messages
   - Use structured logging where appropriate
   - Maintain consistent log formatting

3. **Error Recovery**:
   - Implement graceful degradation where possible
   - Provide clear error messages for debugging
   - Record errors in test results for analysis

## Integration with LLM Components

The system will leverage the existing MCP-based LLM components from `rvandroid/llm/` package rather than creating new implementations. This integration will reuse:

1. **MCP Data Structures**: Using the standardized `MCPMessage`, `MCPRole`, and content types from `rvandroid/llm/data_structures.py`

2. **Template System**: Leveraging the advanced template system from `rvandroid/llm/templates/template.py` for prompt generation instead of maintaining a separate template system in RVDroid

3. **Component Configurator**: Using the centralized configuration system for managing LLM settings

The LLM integration will facilitate:

1. **Action Generation**:
   - Using LLM to suggest intelligent test actions
   - Analyzing screen content semantically
   - Understanding application context

2. **Pattern Recognition**:
   - Enhancing UI pattern detection with LLM capabilities
   - Identifying complex UI patterns
   - Learning from previous interactions

3. **Test Strategy Optimization**:
   - Adapting strategies based on application behavior
   - Identifying promising test paths
   - Optimizing for monitored operation coverage

The integration will follow this approach:

```python
# High-level pseudocode for LLM integration
from rvandroid.llm.data_structures import MCPMessage, MCPRole, MCPTextContent
from rvandroid.llm.templates.template import MCPPromptTemplate
from rvandroid.config.component_configurator import ComponentConfigurator

class RVDroidLLMService:
    """Service for LLM-based testing guidance"""
    
    def __init__(self, static_data=None):
        """Initialize with configuration and templates"""
        # Use ComponentConfigurator to set up LLM
        self.configurator = ComponentConfigurator()
        self.model = self.configurator.create_llm()
        self.template_repository = self._load_templates()
        self.static_data = static_data
        
    def analyze_screen(self, screen_data):
        """Analyze screen content using LLM"""
        # Use templates to generate MCP messages
        template = self.template_repository.get_template("screen_analysis")
        messages = template.render({
            "screen": screen_data,
            "static_data": self.static_data
        })
        
        # Get response using MCP
        return self.model.generate_sync(messages)
        
    def generate_actions(self, screen_data, context):
        """Generate potential actions using LLM"""
        # Similar pattern using MCP messages and templates
        pass
        
    def optimize_strategy(self, execution_history, app_info):
        """Optimize testing strategy based on execution history"""
        # Similar pattern using MCP messages and templates
        pass
```

## Code Documentation Standards

All new and refactored code must adhere to the following documentation standards:

1. **Class Documentation**:
   ```python
   class ComponentName:
       """
       Brief description of the component's purpose.

       ### Architectural Decisions:
       - Key architectural decision 1
       - Key architectural decision 2
       - Design patterns used
       - Tradeoffs made

       ### Role in the System:
       - Primary responsibilities
       - Interactions with other components
       - Where it fits in the data/control flow
       - Key features provided
       """
   ```

2. **Method Documentation**:
   ```python
   def method_name(self, param1, param2):
       """
       Brief description of what the method does.

       Args:
           param1: Description of parameter 1
           param2: Description of parameter 2

       Returns:
           Description of return value

       Raises:
           ErrorType: When/why this error is raised
       """
   ```

3. **Module Documentation**:
   Each module should have a docstring at the top explaining its purpose, key components, and relation to other modules.

## Implementation Phases

The refactoring should be implemented in the following phases:

1. **Phase 1**: Core Structure Setup
   - Set up directory structure
   - Create base interfaces
   - Implement core coordinator

2. **Phase 2**: Memory System Refactoring
   - Implement memory interfaces
   - Refactor short-term and long-term memory
   - Create memory manager

3. **Phase 3**: UI Adapter Refactoring
   - Create adapter interfaces
   - Implement UIAutomator adapter
   - Set up screen representation

4. **Phase 4**: Strategy System Refactoring
   - Implement strategy interfaces
   - Refactor basic and advanced strategies
   - Create strategy factory and context

5. **Phase 5**: Pattern Detection
   - Implement pattern interfaces
   - Create individual pattern detectors
   - Set up pattern registry

6. **Phase 6**: LLM Integration
   - Connect to existing MCP components
   - Set up templates for AI guidance
   - Integrate with strategies

7. **Phase 7**: Testing and Finalization
   - Unit testing
   - Integration testing
   - Documentation finalization

## Expected Benefits

1. **Improved Maintainability**:
   - Smaller, focused components with clear responsibilities
   - Well-defined interfaces between subsystems
   - Consistent error handling and logging

2. **Enhanced Extensibility**:
   - Easier to add new strategies, pattern detectors, and UI adapters
   - Clearer extension points for future development
   - Better separation of concerns

3. **Better Memory Management**:
   - Clear distinction between short-term and long-term memory
   - More efficient state tracking
   - Improved context for decision making

4. **Consistent Terminology**:
   - Updated "monitored operations" terminology throughout
   - Clearer communication about system purpose
   - Consistency with academic literature

5. **Reduced Code Duplication**:
   - Shared utilities and base implementations
   - Consistent interfaces across the codebase
   - Better reuse of common functionality

6. **Improved LLM Integration**:
   - Standardized MCP-based communication
   - Reuse of advanced template system
   - Centralized LLM configuration