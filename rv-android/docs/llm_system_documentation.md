# LLM Integration in RV-Android Architecture

This document provides comprehensive documentation of the Language Model (LLM) integration within the RV-Android platform, detailing its architecture, components, and usage in both the main RV-Android system and the test framework.

## Table of Contents

1. [Introduction](#1-introduction)
2. [Architecture Overview](#2-architecture-overview)
3. [Template System](#3-template-system)
4. [Prompt Strategies](#4-prompt-strategies)
5. [Screen Parsers and Visitor Pattern](#5-screen-parsers-and-visitor-pattern)
6. [Monitored Operations Integration](#6-monitored-operations-integration)
7. [RV-Android Tools Integration](#7-rv-android-tools-integration)
8. [Test Framework Integration](#8-test-framework-integration)
9. [Extending the System](#9-extending-the-system)
10. [Usage Examples](#10-usage-examples)
11. [Troubleshooting](#11-troubleshooting)

## 1. Introduction

The LLM integration in RV-Android provides intelligent guidance for Android application testing, leveraging large language models to analyze application state, understand UI elements, and generate optimal testing actions. This system is designed to enhance the exploration capabilities of traditional testing tools by incorporating contextual understanding and goal-directed behavior.

### 1.1 Key Features

- **Intelligent Test Guidance**: Uses LLMs to analyze application state and determine optimal testing actions
- **Multiple Model Support**: Compatible with various LLM providers, including Ollama, DSPy, and Frontier models
- **Flexible Prompt Strategies**: Configurable strategies for generating effective prompts
- **Template-Based System**: Versioned, composable templates for consistent prompt generation
- **Static Analysis Integration**: Incorporates information about monitored operations from formal specifications
- **Adaptive Exploration**: Adjusts testing strategies based on application characteristics and runtime behavior

### 1.2 Use Cases

The LLM integration serves two primary use cases within the RV-Android ecosystem:

1. **RV-Android Tools**: Provides intelligent test guidance in the RVAndroid and RVDroid testing tools
2. **Test Framework**: Enables systematic experimentation with different LLM configurations and prompt strategies

## 2. Architecture Overview

The LLM integration follows a modular, component-based architecture with clear separation of concerns.

```
docs/images/llm_architecture_overview.puml
```

### 2.1 Core Components

- **LLMActionService**: Orchestrates the entire LLM-guided testing process
- **PromptProcessor**: Manages prompt generation and formatting
- **LLMManager**: Handles communication with LLM providers
- **ResponseProcessor**: Parses and validates LLM responses
- **ActionGenerator**: Converts parsed responses to executable actions
- **StateAnalyzer**: Enhances application state with analytical insights
- **TransitionManager**: Tracks and guides application state transitions

### 2.2 Component Layers

```
docs/images/llm_component_layers.puml
```

The LLM integration is organized into the following layers:

1. **Strategy Layer**: Defines how prompts are structured and what guidance is provided
2. **Processing Layer**: Manages the flow of data between components
3. **Integration Layer**: Connects with LLM providers and testing tools
4. **Execution Layer**: Converts LLM outputs into executable actions

### 2.3 Design Patterns

The LLM integration implements several design patterns to ensure flexibility and maintainability:

- **Strategy Pattern**: For different prompt generation approaches
- **Factory Pattern**: For LLM and strategy instance creation
- **Template Method**: In the BasePromptStrategy hierarchy
- **Visitor Pattern**: For processing UI elements
- **Facade Pattern**: In LLMActionService orchestration
- **Composition**: In the ComposablePromptStrategy approach

## 3. Template System

The template system provides a flexible, composable approach to prompt generation.

```
docs/images/llm_template_system.puml
```

### 3.1 Core Template Components

- **PromptTemplate**: Main template class with variable substitution and conditional sections
- **TemplateFragment**: Reusable pieces of template content
- **PromptLibrary**: Central repository of templates and fragments

### 3.2 Template Features

```python
# Example of a prompt template with conditionals and fragments
template = """You are an Android UI testing expert. Your task is to analyze the current app state and suggest the MOST EFFECTIVE NEXT ACTIONS to take for testing the application thoroughly.

Focus on:
1. {exploration_goal}
2. Maximizing code coverage by targeting untested UI elements
3. Prioritizing testing of methods of interest that directly or indirectly affect operations defined in formal specifications
4. Testing complete workflows from start to finish

{response_format}

{#include dropdown_guidelines}

{#include form_guidelines}

{#if additional_guidelines}{additional_guidelines}{#endif}

DO NOT include any additional text outside of the JSON array. Your response must be valid JSON that can be parsed directly."""
```

The template system supports:

- **Variable Substitution**: Replace placeholders with dynamic values
- **Conditional Sections**: Include content based on conditions
- **Fragment Inclusion**: Embed reusable fragments
- **Inheritance**: Derive templates from parent templates
- **Versioning**: Track template versions for evolution management
- **Serialization**: Save/load templates from JSON files

### 3.3 Template Versioning

Templates are versioned to track their evolution and ensure backward compatibility:

```python
def derive(self, template_text: str = "", name: str = "", version: str = "") -> 'PromptTemplate':
    """
    Create a derived template that inherits from this one.
    """
    new_name = name or f"{self.name}_derived"
    new_version = version or f"{self.version}.1"
    new_text = template_text or self.template_text
    
    derived = PromptTemplate(
        template_text=new_text,
        name=new_name,
        version=new_version,
        required_variables=self.required_variables.copy(),
        parent=self,
        metadata={**self.metadata, "derived_from": self.name}
    )
    
    # Copy transformers and fragments
    # [implementation details]
    
    return derived
```

This versioning system allows for:

- Tracking template evolution over time
- Creating specialized templates for different contexts
- Managing template dependencies
- Resolving conflicts between different template versions

### 3.4 Standard Templates

The `PromptLibrary` includes standard templates for common use cases:

- **system_base_template**: Defines the LLM's role and instructions
- **user_base_template**: Provides application state information
- **single_action_format**: Format instructions for single action responses
- **multi_action_format**: Format instructions for multiple action responses
- **dropdown_guidelines**: Guidelines for dropdown interaction
- **form_guidelines**: Guidelines for form testing
- **advanced_guidelines**: Advanced testing strategies

## 4. Prompt Strategies

Prompt strategies determine how application state is transformed into effective prompts for the LLM.

```
docs/images/llm_prompt_strategies.puml
```

### 4.1 Strategy Hierarchy

The prompt strategies follow a clear inheritance hierarchy:

- **PromptStrategy** (Abstract): Defines the interface for all strategies
- **BasePromptStrategy**: Implements common functionality for all strategies
- **SingleActionPromptStrategy**: Specialized for generating exactly one action with enhanced guidance
- **ComposablePromptStrategy**: Uses a composition-based approach for flexible assembly of prompt components
- **ComposableSingleActionStrategy**: Combines composable approach with single action focus
- **FlowBasedBatchActionStrategy**: Generates logical sequences of related actions based on detected UI patterns
- **Other Specialized Strategies**: Like BasicPromptStrategy001, DSPyPromptStrategy, FrontierPromptStrategy

### 4.2 Strategy Factory

The `PromptStrategyFactory` provides a centralized mechanism for creating strategy instances:

```python
@classmethod
def create(cls,
           strategy_type: str,
           static_data: Optional[StaticAnalysisData] = None,
           parser: Optional[AbstractScreenParser] = None) -> BasePromptStrategy:
    """
    Create a prompt strategy instance of the specified type.
    """
    # Default to composable_single_action if not specified
    if not strategy_type:
        strategy_type = cls.get_default_strategy()

    # Get parser instance if none provided
    if parser is None:
        parser = ParserFactory.create(ParserType.DROIDBOT)

    # Get strategy class from registry
    strategy_registry = ComponentConfigurator._registries['strategy']
    strategy_class = strategy_registry.get(strategy_type.lower())
    
    # [Implementation details and fallback logic]
    
    # Create and return strategy instance
    return strategy_class(static_data, parser)
```

This factory approach allows:
- Dynamic selection of strategies based on configuration
- Flexible extension with new strategy types
- Default strategy fallback
- Registry-based strategy discovery

### 4.3 Key Strategy Implementations

#### 4.3.1 BasePromptStrategy

Provides common functionality for all strategies:

```python
def generate_user_prompt(self, state: Dict[str, Any]) -> str:
    """Generate a user prompt based on current application state."""
    try:
        # Process screen description
        screen_description = self.process_screen(state)
        
        # Get activity name
        activity = self.parser.get_activity_name(state)
        
        # Format UI elements for the prompt
        ui_elements = self._format_ui_elements(screen_description, state)
        
        # Get static analysis context
        static_context = self._add_static_analysis_context(activity)
        
        # Format action history
        action_history = self._format_action_history(state)
        
        # Generate the summary section
        summary = self._generate_summary(activity, screen_description, state)
        
        # Add workflow guidance
        workflow = self._add_workflow_guidance(screen_description, state.get("action_history", []))
        if workflow:
            summary += "\n\n" + workflow
        
        # Render the template with all components
        return self.user_template.render({
            "activity": activity,
            "static_context": static_context,
            "ui_elements": ui_elements,
            "action_history": action_history,
            "summary": summary
        })
    except Exception as e:
        # Error handling and fallback
        # [Implementation details]
```

#### 4.3.2 SingleActionPromptStrategy

Specialized for generating exactly one action:

```python
def generate_system_prompt(self) -> str:
    """Generate a system prompt for single action generation."""
    exploration_goal = ("Systematically exploring ALL parts of the application, "
                        "ensuring exactly ONE action is recommended")
    
    # Use single action format
    response_format = PromptLibrary.single_action_format()
    
    # Add additional guidelines for single action context
    additional_guidelines = (
        "IMPORTANT: You MUST respond with EXACTLY ONE action. "
        "The action should be the most valuable next step for testing. "
        "Consider coverage, unexplored areas, and monitored operations."
    )
    
    # Render template
    return self.system_template.render({
        "exploration_goal": exploration_goal,
        "response_format": response_format,
        "additional_guidelines": additional_guidelines
    })
```

#### 4.3.3 ComposablePromptStrategy

The ComposablePromptStrategy represents a fundamentally different approach to prompt generation using composition-based design:

```python
def __init__(self, static_data: Optional[StaticAnalysisData] = None,
             parser: Union[ParserType, AbstractScreenParser, None] = None):
    """Initialize with component-based structure."""
    super().__init__(static_data, parser)
    
    # Initialize component registry
    self.components = {
        "header": self._generate_header,
        "state_description": self._generate_state_description,
        "static_analysis": self._generate_static_analysis,
        "action_history": self._generate_action_history,
        "guidance": self._generate_guidance,
        "workflow_hints": self._generate_workflow_hints,
        "action_prioritization": self._generate_action_prioritization
    }
    
    # Default component order
    self.component_order = [
        "header",
        "state_description",
        "static_analysis",
        "action_history",
        "guidance",
        "workflow_hints",
        "action_prioritization"
    ]
```

The composition-based approach allows for more flexible and modular prompt generation:

```python
def generate_user_prompt(self, state: Dict[str, Any]) -> str:
    """Generate a user prompt using the component composition approach."""
    try:
        # Process the screen first to have a consistent representation
        screen_description = self.process_screen(state)
        state["screen_description"] = screen_description
        
        # Generate each component in the specified order
        sections = []
        for component_name in self.component_order:
            if component_name in self.components:
                component_func = self.components[component_name]
                component_content = component_func(state)
                if component_content:
                    sections.append(component_content)
        
        # Join all sections with double newlines
        return "\n\n".join(sections)
        
    except Exception as e:
        self.logger.error(f"Error generating composable prompt: {e}", exc_info=True)
        # Fallback to basic prompt generation
        # [Implementation details]
```

Individual components can be implemented as separate methods, making them easier to maintain and extend:

```python
def _generate_state_description(self, state: Dict[str, Any]) -> str:
    """Generate the state description component."""
    screen_description = state.get("screen_description")
    if not screen_description:
        return "Current UI State: [Unable to parse UI state]"
    
    activity = self.parser.get_activity_name(state)
    ui_elements = self._format_ui_elements(screen_description, state)
    
    return f"Current Activity: {activity}\n\nUI Elements and Available Actions:\n{ui_elements}"

def _generate_action_history(self, state: Dict[str, Any]) -> str:
    """Generate the action history component."""
    if "action_history" not in state or not state["action_history"]:
        return ""
    
    history = state["action_history"]
    recent_actions = history[-10:] if len(history) > 10 else history
    
    history_section = ["RECENT ACTIONS:"]
    for i, action in enumerate(recent_actions):
        history_section.append(f"{i+1}. {action}")
    
    return "\n".join(history_section)
```

This composition-based approach offers several advantages:

1. **Modularity**: Each component can be developed, tested, and maintained independently
2. **Flexibility**: Components can be added, removed, or reordered without changing the core logic
3. **Customization**: Different strategies can reuse the same components but arrange them differently
4. **Testing**: Individual components can be tested in isolation
5. **Extension**: New components can be added without modifying existing code
6. **A/B Testing**: Different component combinations can be easily tested

Here's an example of how this approach enables easy customization:

```python
# Create a customized composable strategy
custom_strategy = ComposablePromptStrategy(static_data, parser)

# Add a new custom component
custom_strategy.components["app_specific_guidance"] = custom_app_guidance_function

# Modify the component order
custom_strategy.component_order = [
    "header",
    "app_specific_guidance",  # New component inserted here
    "state_description",
    "action_history",
    "workflow_hints",
    "action_prioritization"
]

# Remove a component
custom_strategy.component_order.remove("static_analysis")
```

### 4.4 Using Strategies with Templates

Here's a concrete example of how a prompt strategy uses templates to generate prompts:

```python
class MyCustomStrategy(BasePromptStrategy):
    """A custom prompt strategy that uses templates for generation."""
    
    def __init__(self, static_data=None, parser=None):
        """Initialize with custom templates."""
        super().__init__(static_data, parser)
        
        # Load custom templates
        self.system_template = PromptLibrary.get_template("specialized_system")
        if not self.system_template:
            # Create a specialized system template
            base_template = PromptLibrary.get_template("system_base")
            self.system_template = base_template.derive(
                template_text=base_template.template_text + "\n\n{#if focus_on_mop}FOCUS ON MONITORED OPERATIONS: Prioritize testing actions that might trigger monitored operations.{#endif}",
                name="specialized_system",
                version="1.1"
            )
            PromptLibrary.register_template(self.system_template, "system")
        
        # Load or create user template
        self.user_template = PromptLibrary.get_template("custom_user")
        if not self.user_template:
            # Create a custom user template
            self.user_template = PromptTemplate(
                template_text="""Current App: {app_name}
Activity: {activity}

UI ELEMENTS AND ACTIONS:
{ui_elements}

TESTING HISTORY:
{action_history}

TESTING OBJECTIVES:
1. Find paths to monitored operations
2. Verify app functionality
3. Maximize code coverage

{#if has_forms}FORM GUIDANCE: Complete forms methodically - fill all fields before submitting.{#endif}""",
                name="custom_user",
                version="1.0",
                required_variables=["activity", "ui_elements"]
            )
            PromptLibrary.register_template(self.user_template, "user")
    
    def generate_system_prompt(self) -> str:
        """Generate system prompt using the specialized template."""
        # Prepare template variables
        vars = {
            "exploration_goal": "Exploring the application thoroughly with focus on critical operations",
            "response_format": PromptLibrary.single_action_format(),
            "focus_on_mop": True  # This will activate our conditional section
        }
        
        # Render the template
        return self.system_template.render(vars)
    
    def generate_user_prompt(self, state: Dict[str, Any]) -> str:
        """Generate user prompt using the custom template."""
        # Process screen to get UI elements
        screen_description = self.process_screen(state)
        
        # Check if the screen has form elements
        has_forms = any("form" in item.base_description.lower() 
                      or "edit" in item.base_description.lower()
                      for item in screen_description.items)
        
        # Format UI elements for prompt
        ui_elements = self._format_ui_elements(screen_description, state)
        
        # Format action history
        action_history = self._format_action_history(state)
        if not action_history:
            action_history = "No previous actions recorded."
        
        # Get activity name
        activity = self.parser.get_activity_name(state)
        
        # Get app name from package
        app_name = state.get("package_name", "Unknown App")
        
        # Render the template with all variables
        return self.user_template.render({
            "app_name": app_name,
            "activity": activity,
            "ui_elements": ui_elements,
            "action_history": action_history,
            "has_forms": has_forms
        })
```

This example shows:
1. How to initialize custom templates 
2. How to derive a template from an existing one with additional content
3. How to prepare variables based on application state
4. How to use conditional sections in templates
5. How to render templates with the prepared variables

## 5. Screen Parsers and Visitor Pattern

The LLM integration relies on a powerful screen parsing system that uses the Visitor Pattern to transform UI hierarchies into structured descriptions suitable for prompts.

```
docs/images/llm_screen_parsing.puml
```

### 5.1 Parser Types

The framework supports different parser types through the `ParserFactory`:

- **DroidBot**: Parses JSON state from DroidBot
- **UIAutomator**: Parses XML output from UIAutomator
- **Generic**: Generic parser for other state formats

### 5.2 Visitor Pattern Implementation

The Visitor Pattern is used to traverse UI element hierarchies:

```python
class BaseScreenVisitor(ABC):
    """
    Abstract base visitor implementation for processing Android UI elements.
    """
    def __init__(self, static_info: Optional[StaticAnalysisData], activity: str):
        """Initialize the visitor with static analysis data and activity context."""
        self.logger = logging.getLogger(__name__)
        self.static_info = static_info
        self.activity = activity
        self.window = None
        
        # Initialize window info if static info is available
        if static_info and static_info.windows:
            self.window = static_info.windows.get_window(activity)

        self.counter = Counter()
        self.items: List[ScreenItem] = []
        self.visited_nodes: Set[str] = set()  # Track visited nodes to avoid duplicates
        
        # Initialize element handlers
        self.handlers: Dict[UiElementType, ElementHandler] = {}
        self._register_default_handlers()

    def visit(self, node: Node) -> None:
        """
        Visit a node in the UI hierarchy - simplified generic method.
        Finds the appropriate handler for the node type and processes it.
        """
        # Skip already visited nodes
        node_id = node.get_unique_id()
        if node_id in self.visited_nodes:
            return

        # Skip system navigation buttons
        if self.should_exclude_system_button(node):
            return

        # Find handler for this element type
        handler = self.handlers.get(node.element_type)

        # Use generic processing if no specific handler
        if handler and handler.can_handle(node):
            item = handler.handle(node, self)
            if item:
                self.items.append(item)
                self.visited_nodes.add(node_id)
                self.window_info["interactive_elements"] += 1
        elif node.actionable:
            # Generic handling for actionable elements
            self._process_actionable_node(node)
```

### 5.3 Screen Description Structure

The result of parsing is a `ScreenDescription` with actionable UI elements:

```python
class ScreenDescription:
    """Represents the complete description of a screen including all UI elements and their actions."""

    def __init__(self, activity: str, items: List[ScreenItem]):
        """
        Initialize screen description.
        """
        self.activity = activity
        self.items = items

        # Add a standard BACK action if needed
        self._add_standard_back_action()

        # Update the events dictionary
        self.events_by_id: Dict[int, ItemAction] = {
            action.id: action
            for item in items
            for action in item.actions
        }
```

### 5.4 Relationship Between Parsers and Prompt Strategies

The relationship between screen parsers and prompt strategies is bi-directional:

1. **Parser → Strategy Flow**:
   - Screen Parser extracts UI elements and their properties
   - Visitor traverses the UI hierarchy and identifies possible actions
   - ScreenDescription is created as a structured representation of the state
   - Prompt Strategy uses ScreenDescription to generate contextual prompts
   - Static analysis info is integrated to highlight monitored operations

2. **Strategy → Parser Reference**:
   - Each BasePromptStrategy holds a reference to a parser
   - Strategy can request screen parsing as needed
   - Different strategies can work with different parser types
   - Configuration system allows matching compatible parsers and strategies

This design enables flexible combination of different parsers and strategies to optimize for different testing scenarios.

## 6. UI Pattern Detection and Batch Actions

The LLM integration includes a sophisticated pattern detection system that identifies common UI patterns and generates batch actions for efficient testing.

```
docs/images/llm_batch_actions.puml
```

### 6.1 Pattern Detection System

The pattern detection system uses both visual and structural analysis to identify UI patterns:

```python
class UIPatternDetector:
    """Base class for UI pattern detectors."""
    
    def __init__(self, static_data: Optional[StaticAnalysisData] = None):
        """Initialize with static analysis data."""
        self.static_data = static_data
        self.logger = logging.getLogger(self.__class__.__name__)
        
    @abstractmethod
    def detect(self, screen_description: ScreenDescription) -> PatternDetectionResult:
        """Detect patterns in the given screen."""
        pass
```

Multiple specialized pattern detectors work together to identify common UI structures:

- **FormDetector**: Identifies form structures and related fields
- **ListDetector**: Detects list and grid layouts
- **TabDetector**: Identifies tab-based navigation
- **NavigationDetector**: Detects navigation elements (menus, drawers)
- **DialogDetector**: Identifies dialog components

Each detector produces a `PatternDetectionResult` with confidence scores and suggested batch actions.

### 6.2 Batch Action Generation

The `BatchActionGenerator` creates sequences of related actions based on detected patterns:

```python
class BatchActionGenerator:
    """Generates batch actions based on detected UI patterns."""
    
    def __init__(self, detectors: List[UIPatternDetector]):
        """Initialize with pattern detectors."""
        self.detectors = detectors
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def generate_batch_actions(self, screen_description: ScreenDescription) -> List[BatchAction]:
        """Generate batch actions for the current screen."""
        batch_actions = []
        
        # Apply each detector
        for detector in self.detectors:
            result = detector.detect(screen_description)
            if result.confidence >= CONFIDENCE_THRESHOLD:
                # Generate batch actions based on pattern type
                pattern_actions = self._create_actions_for_pattern(
                    result.pattern_type,
                    result.elements,
                    screen_description
                )
                batch_actions.extend(pattern_actions)
        
        return batch_actions
```

### 6.3 Visual Error Detection

The system includes comprehensive visual error detection capabilities:

- **Color-based Detection**: Identifies red and orange elements associated with errors
- **Text-based Detection**: Uses OCR to recognize error messages
- **Icon-based Detection**: Detects common error icons
- **Pattern-based Detection**: Recognizes dialog patterns common in error presentations

Error detection is integrated with batch action generation to create intelligent recovery sequences.

### 6.4 Prompt Strategy Integration

The `FlowBasedBatchActionStrategy` integrates pattern detection with LLM prompting:

```python
class FlowBasedBatchActionStrategy(BasePromptStrategy):
    """Strategy for generating batches of related actions."""
    
    def __init__(self, static_data: Optional[StaticAnalysisData] = None,
                 parser: Union[ParserType, AbstractScreenParser, None] = None):
        """Initialize with detectors."""
        super().__init__(static_data, parser)
        
        # Initialize pattern detectors
        self.form_detector = FormDetector(static_data)
        self.list_detector = ListDetector(static_data)
        self.tab_detector = TabDetector(static_data)
        self.navigation_detector = NavigationDetector(static_data)
        self.dialog_detector = DialogDetector(static_data)
        
        # Create batch action generator
        self.batch_generator = BatchActionGenerator([
            self.form_detector,
            self.list_detector,
            self.tab_detector,
            self.navigation_detector,
            self.dialog_detector
        ])
        
    def generate_system_prompt(self) -> str:
        """Generate a system prompt for batch action generation."""
        # Customize the system prompt for batch action generation
        exploration_goal = ("Analyzing UI patterns and generating logical sequences "
                           "of related actions for complete workflow testing")
        
        # Use batch action response format
        response_format = PromptLibrary.batch_action_format()
        
        # Add additional guidelines
        additional_guidelines = (
            "IMPORTANT: Analyze the UI to identify patterns like forms, lists, tabs, "
            "navigation elements, and dialogs. Then generate a LOGICAL SEQUENCE of "
            "actions that test complete workflows within the identified pattern.\n\n"
            "FOR EACH PATTERN:\n"
            "1. Begin with a clear pattern identification\n"
            "2. List 2-5 related actions that form a cohesive testing sequence\n"
            "3. Explain the testing objective for this sequence"
        )
        
        # Render template
        return self.system_template.render({
            "exploration_goal": exploration_goal,
            "response_format": response_format,
            "additional_guidelines": additional_guidelines
        })
```

### 6.5 Action Execution Integration

Batch actions are executed through the `BatchActionExecutor` which handles sequences appropriately:

```python
class BatchActionExecutor:
    """Executes batches of related actions."""
    
    def __init__(self, action_executor: ActionExecutor):
        """Initialize with an action executor."""
        self.action_executor = action_executor
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def execute_batch(self, batch_action: BatchAction) -> BatchActionResult:
        """Execute a batch of actions and return the result."""
        results = []
        
        # Execute each action in the batch sequentially
        for action in batch_action.actions:
            # Execute action
            result = self.action_executor.execute(action)
            results.append(result)
            
            # Stop if action failed
            if not result.success:
                self.logger.warning(f"Batch execution stopped after action {action.id} failed")
                break
                
            # Capture intermediate state if needed
            if action != batch_action.actions[-1]:
                # Wait for UI to update
                time.sleep(1)
        
        # Return overall batch result
        return BatchActionResult(
            batch_action=batch_action,
            action_results=results,
            success=all(r.success for r in results)
        )
```

This integration allows RVDroid to efficiently handle complex UI workflows with fewer LLM queries, improving both testing efficiency and coverage.

## 7. Monitored Operations Integration

A key feature of the LLM integration is its ability to incorporate information about monitored operations from formal specifications.

```
docs/images/llm_monitored_operations.puml
```

### 6.1 Monitored Operations Concept

In RV-Android, "monitored operations" refer to methods that are being observed by formal specifications. These specifications can detect violations of expected behavior, such as:

- Proper API usage (e.g., calling `hasNext()` before `next()` on an Iterator)
- Cryptographic protocol compliance (e.g., using secure random number generators)
- Other domain-specific rules defined in JavaMOP specifications

It's important to note that RV-Android uses two main sets of specifications:
1. One set for detecting cryptographic API misuse in Java Cryptography Architecture (JCA)
2. Another set for generic programming rules like proper Iterator usage

These specification sets are used separately in different experiments, with applications being instrumented with only one set at a time.

### 6.2 Static Analysis Integration

The static analysis data includes information about methods that reach or directly reach monitored operations:

```python
class Method:
    """
    Represents a method in a class with its properties and relationships.
    Used for tracking method reachability and MOP analysis.
    """

    def __init__(
            self,
            class_name: str,
            name: str,
            params: List[str],
            signature: str,
            reachable: bool,
            reaches_mop: bool,
            directly_reaches_mop: bool
    ):
        """
        Initialize a Method with its properties.
        
        Args:
            reaches_mop: Whether the method reaches a MOP method
            directly_reaches_mop: Whether the method directly reaches a MOP method
        """
        self.class_name = class_name
        self.name = name
        self.params = params
        self.signature = signature
        self.reachable = reachable
        self.reaches_mop = reaches_mop
        self.directly_reaches_mop = directly_reaches_mop
        self.reached = False
```

This information is propagated from the static analysis to UI elements via the Visitor pattern.

### 6.3 Visitor Integration of Monitored Operations

The visitor pattern enriches `ItemAction` objects with information about monitored operations:

```python
def _update_action_monitored_op_info(self, action: ItemAction, node: Node) -> None:
    """
    Update an action with monitored operations information from static analysis.
    """
    widget = self.find_matching_widget(node.data)
    if not widget:
        return

    # Find matching event type
    for event in widget.events:
        if event.type == action.event:
            # Check if method reaches or directly reaches MOP
            action.reaches_mop = self._check_method_reaches_mop(event.signature)
            action.directly_reaches_mop = self._check_method_directly_reaches_mop(event.signature)
            if action.reaches_mop or action.directly_reaches_mop:
                self.logger.debug(
                    f"Action {action.id} MOP info updated: reaches_mop={action.reaches_mop}, directly_reaches_mop={action.directly_reaches_mop}")
            return
```

### 6.4 Prompt Strategy Utilization

Prompt strategies highlight monitored operations in the prompts to guide the LLM:

```python
def _format_ui_elements(self, screen_description: ScreenDescription, state: Dict[str, Any]) -> str:
    """Format UI elements for prompt display."""
    # [implementation details]
    
    for item in screen_description.items:
        # [implementation details]
        
        for action in item.actions:
            # Add indicators for operations of interest
            importance_tag = ""
            if action.directly_reaches_mop:
                importance_tag = " [CRITICAL: Directly reaches operation of interest]"
            elif action.reaches_mop:
                importance_tag = " [IMPORTANT: Can reach operation of interest]"
            
            # Create detailed action description
            action_desc = f"  - {action.text} (action_id: \"{action.id}\"){importance_tag}{history_tag}"
            
            # [implementation details]
```

### 6.5 LLM Decision Making

This integration influences LLM decision making by:

1. **Highlighting Critical Operations**: Marking actions that directly reach monitored methods
2. **Prioritizing Relevant Actions**: Guiding the LLM to test paths that lead to monitored operations
3. **Context Enhancement**: Providing insights about which operations are being monitored
4. **Workflow Guidance**: Helping the LLM understand sequences that lead to monitored operations

## 7. RV-Android Tools Integration

The LLM integration is utilized by two key tools in RV-Android: RVAndroid and RVDroid.

```
docs/images/llm_tools_integration.puml
```

### 7.1 RVAndroid Tool

RVAndroid uses the LLM integration to guide DroidBot's exploration:

```python
class ToolSpec(ConfigurableTool):
    """
    A specialized tool implementation for RV-Android's AI-driven test automation workflow.
    """
    def __init__(self):
        """Initialize the RVAndroid tool with default configuration."""
        super().__init__(
            "rvandroid",
            "AI-driven Android testing tool using LLM guidance",
            "br.unb.cic.rvsec"
        )

        # Set default LLM configuration
        self.component_config.set_llm("ollama", "llama3.2:3b")
        self.component_config.set_strategy("composable_single_action")
        self.component_config.set_visitor("enhanced")
        self.component_config.set_parser("droidbot")

    def execute_tool_specific_logic(self, task: Task, app: App):
        """Execute RVAndroid testing with the configured LLM and components."""
        # Create service
        service = LLMActionService(task.static_data, config=self.component_config)

        # Start server and run experiment
        server = Server(service, port=5000)
        try:
            if server.start():
                logger.info("Server started successfully")
                with open(task.result.trace_file, "wb") as trace:
                    exec_cmd = Command("droidbot", [
                        "-d", "emulator-5554",
                        "-a", app.path,
                        "--rvandroid_url", rvandroid_url,
                        "-policy", "rvandroid",
                        "-is_emulator",
                    ], task.config.timeout)
                    exec_cmd.invoke(stdout=trace)
```

Key characteristics of RVAndroid:
- Uses DroidBot as the execution engine
- Operates through a REST API server
- DroidBot sends screen states to the server
- LLMActionService processes states and returns actions
- Leverages DroidBot's policy extension mechanism

### 7.2 RVDroid Tool

RVDroid provides a more integrated approach:

```python
class RVDroidTool(ConfigurableTool):
    """
    A specialized tool implementation for RVDroid, a UIAutomator2-based testing tool.
    """
    def __init__(self):
        """Initialize the RVDroid tool with default configuration."""
        super().__init__(
            "rvdroid",
            "UIAutomator2-based Android testing tool with AI-guided exploration",
            "br.unb.cic.rvsec"
        )

        # Initialize component configurator
        self.component_config = ComponentConfigurator()

        # Set defaults
        self.component_config.set_parser("uiautomator")
        self.component_config.set_visitor("enhanced")

        # Default configuration
        self.config = {
            "use_llm": False,  # Default to no LLM guidance
            "preferred_strategy": "VisualAwareStrategy",
            "use_screenshot_analysis": True,
            "screenshot_analysis_level": "standard",
        }

    def execute_tool_specific_logic(self, task: Task, app: App):
        """Execute RVDroid with the configured parameters."""
        # Create RVDroid service
        service = RVDroidService(
            static_data=static_data,
            config=self.component_config,
            device_id=device_id,
            use_llm=use_llm,
            preferred_strategy=preferred_strategy,
            use_screenshot_analysis=use_screenshot_analysis,
            execution_timeout=timeout
        )

        # Start UIAutomator2 server
        # [implementation details]

        # Execute the main testing loop
        results = service.execute_testing_loop()
```

Key characteristics of RVDroid:
- Uses UIAutomator2 for UI interaction
- Tighter integration with the LLM system
- More sophisticated memory management
- Enhanced strategy framework
- Support for screenshot analysis

### 7.3 Comparison

| Feature | RVAndroid | RVDroid |
|---------|-----------|---------|
| **Base Technology** | DroidBot | UIAutomator2 |
| **Architecture** | Client-Server | Integrated |
| **Primary Parser** | DroidBot | UIAutomator |
| **Memory System** | Basic | Advanced |
| **Screenshot Analysis** | Limited | Comprehensive |
| **Strategy Framework** | Basic | Hierarchical |
| **Execution Model** | External Process | Direct Control |

## 8. Test Framework Integration

The LLM integration is also used by the Test Framework to optimize testing configurations.

```
docs/images/llm_test_framework.puml
```

### 8.1 Test Framework Overview

The Test Framework provides a systematic approach to evaluate different LLM configurations, prompt strategies, parsers, and visitors for testing Android applications.

### 8.2 Configuration System

The Test Framework uses a comprehensive configuration system for LLM parameters:

```python
class ToolConfiguration:
    """Defines how a testing tool should be configured for execution."""
    
    def __init__(self, tool_name: str, **kwargs):
        """Initialize with tool name and parameters."""
        self.tool_name = tool_name
        self.timeout = kwargs.get("timeout", 300)
        self.no_window = kwargs.get("no_window", True)
        
        # LLM parameters
        self.llm_type = kwargs.get("llm_type", "ollama")
        self.llm_model = kwargs.get("llm_model", "llama3.2:3b")
        self.temperature = kwargs.get("temperature", 0.2)
        self.max_tokens = kwargs.get("max_tokens", 800)
        
        # Strategy parameters
        self.strategy_type = kwargs.get("strategy_type", "single_action")
        self.parser_type = kwargs.get("parser_type", "uiautomator")
        self.visitor_type = kwargs.get("visitor_type", "enhanced")
        
        # Feature flags
        self.use_static_analysis = kwargs.get("use_static_analysis", True)
        self.static_analysis_level = kwargs.get("static_analysis_level", "detailed")
        self.use_screenshot_analysis = kwargs.get("use_screenshot_analysis", True)
        self.screenshot_analysis_level = kwargs.get("screenshot_analysis_level", "standard")
        
        # Additional parameters
        self.extra_params = kwargs.get("extra_params", {})
```

### 8.3 Execution Process

The framework executes tests with different LLM configurations:

```python
def run(self, progress_callback: Optional[Callable[[int, int, str], None]] = None) -> List[TestResult]:
    """
    Run the configured test suite.
    """
    if not self.current_test_suite:
        raise ValueError("Test suite not configured. Call configure() first.")
    
    self.logger.info(f"Starting test suite: {self.current_test_suite.name}")
    
    # Create test runner
    runner = TestRunner(output_dir=self.run_dir)
    
    # Run test suite
    self.current_results = runner.run_test_suite(
        self.current_test_suite,
        progress_callback
    )
    
    self.logger.info(f"Test suite completed with {len(self.current_results)} results")
    
    return self.current_results
```

### 8.4 Analysis of LLM Performance

The framework analyzes the performance of different LLM configurations:

```python
def analyze(self) -> Dict[str, Any]:
    """
    Analyze test results.
    """
    if not self.current_results:
        raise ValueError("No test results available. Call run() first.")
    
    self.logger.info("Analyzing test results")
    
    # Create analyzer
    analyzer = ResultAnalyzer(self.current_results, self.run_dir)
    
    # Generate report
    self.analysis_report = analyzer.generate_report()
    
    # Get analysis results
    analysis_result = analyzer.analyze()
    
    self.logger.info(f"Analysis completed. Report saved to {self.analysis_report}")
    
    return analysis_result
```

### 8.5 Integration Points

The Test Framework integrates with the LLM system at several key points:

1. **Configuration**: Defines LLM parameters, strategies, and models to test
2. **Execution**: Creates tool instances with specified LLM configurations
3. **Data Collection**: Captures coverage and error metrics for each configuration
4. **Analysis**: Evaluates and compares the performance of different LLM setups
5. **Visualization**: Creates charts and dashboards showing LLM performance
6. **Recommendations**: Suggests optimal LLM configurations for different app types

### 8.6 Test Framework Use Cases

The Test Framework uses the LLM integration for:

- Comparing different LLM models (e.g., Llama vs. Claude)
- Evaluating prompt strategies (e.g., single_action vs. composable)
- Testing parser and visitor combinations
- Identifying optimal temperature and token settings
- Determining the impact of static analysis integration
- Measuring the value of screenshot analysis

## 9. Extending the System

The LLM integration in RV-Android is designed to be highly extensible.

```
docs/images/llm_extension_points.puml
```

### 9.1 Adding New LLM Models

To add support for a new LLM provider:

1. Create a new implementation of the `LanguageModel` interface:
   ```python
   class NewProviderLLM(LanguageModel):
       """Implementation for a new LLM provider."""
       
       def __init__(self, model_name: str, **kwargs):
           """Initialize with model name and provider-specific parameters."""
           super().__init__(model_name)
           self.api_key = kwargs.get("api_key")
           self.api_endpoint = kwargs.get("api_endpoint", "https://api.newprovider.com")
           # Additional initialization
       
       def generate_text(self, prompt: str, **kwargs) -> str:
           """Generate text from the prompt."""
           # Implementation details
       
       def generate(self, messages: List[Dict[str, str]], **kwargs) -> str:
           """Generate a response to the given messages."""
           # Implementation details
       
       def cleanup(self) -> None:
           """Clean up resources."""
           # Implementation details
   ```

2. Register the new model in the `ModelFactory`:
   ```python
   @classmethod
   def create(cls, llm_type: str, model_name: str, **kwargs) -> LanguageModel:
       """Create a language model instance based on type."""
       if llm_type.lower() == "newprovider":
           return NewProviderLLM(model_name, **kwargs)
       # Other model types
   ```

3. Update configuration validation to support the new provider.

### 9.2 Creating Custom Prompt Strategies

To create a new prompt strategy:

1. Extend the `BasePromptStrategy` class:
   ```python
   class CustomPromptStrategy(BasePromptStrategy):
       """A custom prompt strategy implementation."""
       
       def __init__(self, static_data: Optional[StaticAnalysisData] = None,
                    parser: Union[ParserType, AbstractScreenParser, None] = None):
           """Initialize the custom strategy."""
           super().__init__(static_data, parser, detailed_static_analysis=True)
           # Custom initialization
       
       def generate_system_prompt(self) -> str:
           """Generate a custom system prompt."""
           # Custom implementation
       
       def generate_user_prompt(self, state: Dict[str, Any]) -> str:
           """Generate a custom user prompt."""
           # Custom implementation or call super() and modify
   ```

2. Register the strategy with the `PromptStrategyFactory`:
   ```python
   PromptStrategyFactory.register_strategy(
       "custom_strategy", 
       CustomPromptStrategy,
       metadata={"description": "A specialized prompt strategy for specific scenarios"}
   )
   ```

3. Use the strategy in configurations:
   ```python
   component_config.set_strategy("custom_strategy")
   ```

### 9.3 Extending Templates

To extend the template system:

1. Create new template fragments:
   ```python
   custom_guidelines = PromptTemplate(
       template_text="CUSTOM GUIDELINES:\n1. First guideline\n2. Second guideline",
       name="custom_guidelines",
       version="1.0",
       metadata={"description": "Custom guidelines for specific scenarios"}
   )
   PromptLibrary.register_template(custom_guidelines, "guidelines")
   ```

2. Create derived templates:
   ```python
   base_template = PromptLibrary.get_template("system_base")
   specialized_template = base_template.derive(
       template_text=base_template.template_text + "\n\n{#include custom_guidelines}",
       name="specialized_system",
       version="1.0"
   )
   PromptLibrary.register_template(specialized_template, "system")
   ```

3. Reference in strategies:
   ```python
   def generate_system_prompt(self) -> str:
       """Generate system prompt using specialized template."""
       template = PromptLibrary.get_template("specialized_system")
       return template.render({
           "exploration_goal": self.exploration_goal,
           "response_format": self.response_format
       })
   ```

### 9.4 Creating Custom Visitors

To create a custom visitor for UI element processing:

1. Extend the `BaseScreenVisitor` class:
   ```python
   class CustomVisitor(BaseScreenVisitor):
       """A custom visitor implementation."""
       
       def _register_default_handlers(self) -> None:
           """Register custom element handlers."""
           super()._register_default_handlers()
           self.register_handler(CustomButtonHandler(UiElementType.BUTTON))
           self.register_handler(CustomTextFieldHandler(UiElementType.TEXT_FIELD))
       
       def _process_actionable_node(self, node: Node) -> None:
           """Custom processing for actionable nodes."""
           # Custom implementation
   ```

2. Create custom handlers:
   ```python
   class CustomButtonHandler(ElementHandler):
       """Custom handler for button elements."""
       
       def handle(self, node: Node, visitor: BaseScreenVisitor) -> Optional[ScreenItem]:
           """Process a button node and generate a ScreenItem."""
           # Custom implementation
   ```

3. Register with the visitor factory and use in configurations.

## 10. Usage Examples

This section provides practical examples of using the LLM integration in different contexts.

### 10.1 RVAndroid Basic Usage

```bash
# Run RVAndroid with default LLM configuration
python main.py -tools rvandroid -r 1 -t 300 --no_window

# Run with custom model and strategy
python main.py -tools rvandroid@model=llama3.2:3b,strategy=single_action,temperature=0.1 -r 1 -t 300 --no_window
```

### 10.2 RVDroid Basic Usage

```bash
# Run RVDroid with default configuration
python main.py -tools rvdroid -r 1 -t 300 --no_window

# Run with LLM enabled and visual aware strategy
python main.py -tools rvdroid@use_llm=true,preferred_strategy=VisualAwareStrategy -r 1 -t 300 --no_window
```

### 10.3 Test Framework Examples

```bash
# Run test suite with multiple LLM configurations
python run_test_framework.py -c test_configs/llm_comparison.json

# Generate and run test suite for a specific app
python run_test_framework.py --generate-config --app path/to/app.apk --llm-models llama3.2:3b claude-3-haiku gpt-3.5-turbo --strategies single_action composable
```

### 10.4 Programmatic API Usage

```python
from rvandroid.llm.service.action_service import LLMActionService
from rvandroid.config.component_configurator import ComponentConfigurator

# Create component configurator
config = ComponentConfigurator()
config.set_llm("ollama", "llama3.2:3b")
config.set_strategy("composable_single_action")
config.set_parser("uiautomator")
config.set_visitor("enhanced")

# Create LLM action service
service = LLMActionService(static_data, config=config)

# Process application state
actions = service.process_state(current_state)

# Execute actions
for action in actions:
    execute_action(action)
```

### 10.5 Custom Template Creation

```python
from rvandroid.llm.prompt.prompt_template import PromptTemplate, PromptLibrary

# Create custom template
monitored_ops_focused_template = PromptTemplate(
    template_text="""You are an Android tester focused on monitored operations. Your goal is to find potential violations of formal specifications in the application.

Focus on:
1. Testing operations that are being monitored by formal specifications
2. Examining data handling
3. Identifying input validation issues
4. Testing proper API usage sequence

{response_format}

{#include monitored_ops_guidelines}""",
    name="monitored_ops_system",
    version="1.0",
    required_variables=["response_format"],
    metadata={"description": "Monitored operations focused system prompt"}
)

# Create monitored operations guidelines fragment
monitored_ops_guidelines = PromptTemplate(
    template_text="""MONITORED OPERATIONS TESTING GUIDELINES:
1. Test with both valid and invalid inputs
2. Look for proper API sequence usage
3. Check for iterator usage patterns
4. Verify cryptographic operations follow proper protocols""",
    name="monitored_ops_guidelines",
    version="1.0"
)

# Register templates
PromptLibrary.register_template(monitored_ops_guidelines, "guidelines")
monitored_ops_focused_template.add_fragment("monitored_ops_guidelines", monitored_ops_guidelines)
PromptLibrary.register_template(monitored_ops_focused_template, "system")
```

## 11. Troubleshooting

This section covers common issues and their solutions when working with the LLM integration.

### 11.1 LLM Connection Issues

**Problem**: Unable to connect to LLM provider or timeouts during request processing.

**Solutions**:
1. Check network connectivity and firewall settings
2. Verify API keys and endpoints are correctly configured
3. Check if the model is available and properly installed (for local models)
4. Increase timeout settings in configuration
5. Use smaller prompts or reduce max_tokens parameter

### 11.2 Prompt Generation Errors

**Problem**: Errors during prompt generation or unexpected prompt formats.

**Solutions**:
1. Ensure all required template variables are provided
2. Check for syntax errors in custom templates
3. Verify screen parser is correctly processing the UI state
4. Enable debug logging for detailed error messages
5. Validate that static analysis data is properly loaded

### 11.3 Response Parsing Failures

**Problem**: Unable to parse LLM responses into actionable commands.

**Solutions**:
1. Check if the LLM is generating valid JSON responses
2. Verify the response format instructions in the system prompt
3. Adjust temperature settings (lower temperature for more consistent outputs)
4. Ensure the action IDs in the response match available actions
5. Check if the LLM is exceeding token limits

### 11.4 Low Coverage with LLM Testing

**Problem**: LLM-guided testing achieves lower coverage than expected.

**Solutions**:
1. Increase exploration focus in prompt strategies
2. Ensure static analysis is properly integrated
3. Try different LLM models or prompt strategies
4. Adjust the balance between exploration and exploitation
5. Implement memory mechanisms to track visited states

### 11.5 Memory and Performance Issues

**Problem**: High memory usage or slow performance during testing.

**Solutions**:
1. Use smaller LLM models
2. Reduce the complexity of prompts
3. Limit the amount of history included in prompts
4. Process screen descriptions more efficiently
5. Use structured state fingerprinting to avoid redundant processing