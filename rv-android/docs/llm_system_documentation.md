# LLM Integration in RV-Android

This document describes the integration of Large Language Models (LLMs) in the RV-Android system, detailing the unified architecture, components, and examples of usage.

## Table of Contents

1. [Introduction](#1-introduction)
2. [Consolidated Architecture](#2-consolidated-architecture)
3. [Information Layer](#3-information-layer)
4. [Template Layer](#4-template-layer)
5. [Strategy Layer](#5-strategy-layer)
6. [Unified Framework](#6-unified-framework)
7. [Service Integration](#7-service-integration)
8. [Usage Examples](#8-usage-examples)
9. [System Extension](#9-system-extension)
10. [Modular Template System](#10-modular-template-system)
11. [Best Practices and Lessons Learned](#11-best-practices-and-lessons-learned)

## 1. Introduction

### 1.1 LLM Integration Overview

The RV-Android system uses a sophisticated and consolidated architecture for integrating Large Language Models (LLMs) into the Android application testing process. The architecture provides essential features:

1. **Jinja2-Based Templates**: XML templates with Jinja2 syntax for powerful templating capabilities
2. **Modular Information**: Fragment system that collects and formats information from different sources
3. **Flexible Strategies**: Different approaches for prompt generation as needed
4. **UI Pattern Detection**: Identification of common patterns for better test targeting
5. **Visual Analysis**: Integration of screenshot information to enrich prompts
6. **Monitored Operations**: Tracking of critical operations in the application

### 1.2 Benefits of the Consolidated Architecture

The consolidated architecture offers several advantages:

1. **Elimination of Duplication**: All prompt formatting code is centralized
2. **Improved Maintainability**: XML templates with Jinja2 syntax are easily editable
3. **Extensibility**: Easy addition of new fragments and strategies
4. **Multimodal Integration**: Combination of textual and visual information
5. **Consistent Configuration**: Standardized configuration parameters through ComponentConfigurator
6. **Scalability**: Layered architecture for sustainable growth
7. **Modular Templates**: Template inheritance and fragment inclusion for reusability

### 1.3 Terminology and Concepts

Key concepts in the architecture:

1. **Information Fragment**: Modular component that generates a specific part of a prompt
2. **Information Manager**: Coordinates composition and prioritization of fragments
3. **Prompt Template**: Defines the structure of a prompt with support for variables and conditionals
4. **Template Repository**: Manages templates in XML files with Jinja2 integration
5. **Template Fragments**: Reusable pieces of prompt content that can be included in multiple templates
6. **Prompt Strategy**: Defines how prompts are generated for specific scenarios
7. **Strategy Registry**: Coordinates available strategies through ComponentConfigurator
8. **Unified Framework**: Facade that integrates all layers of the system

## 2. Consolidated Architecture

### 2.1 Three-Layer Architecture

The LLM integration architecture follows a three-layer design with clear separation of responsibilities:

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Unified Framework                             │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│                        Strategy Layer                               │
│ ┌────────────────────┐  ┌────────────────────┐  ┌────────────────┐  │
│ │ StandardStrategy   │  │ BatchActionStrategy │  │ Other          │  │
│ │                    │  │                    │  │ Strategies      │  │
│ └────────────────────┘  └────────────────────┘  └────────────────┘  │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│                        Template Layer                               │
│ ┌────────────────────┐  ┌────────────────────┐  ┌────────────────┐  │
│ │ Jinja2Template     │  │ Jinja2TemplateRepo │  │ XML Templates  │  │
│ │                    │  │                    │  │ with Jinja2    │  │
│ └────────────────────┘  └────────────────────┘  └────────────────┘  │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│                       Information Layer                             │
│ ┌────────────────────┐  ┌────────────────────┐  ┌────────────────┐  │
│ │ InformationFragment│  │ InformationManager │  │ Specialized    │  │
│ │                    │  │                    │  │ Fragments      │  │
│ └────────────────────┘  └────────────────────┘  └────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Key Components and Their Relationships

The system is composed of several interconnected components:

1. **Information Layer** (`information/`):
   - Defines how information is collected and formatted
   - Implements fragments for different information sources
   - Manages the composition of information for prompts

2. **Template Layer** (`template/`):
   - Defines the structure of messages for LLMs
   - Manages templates stored in external XML files with Jinja2 syntax
   - Supports variables, conditionals, and transformations
   - Includes reusable template fragments for modular prompt construction

3. **Strategy Layer** (`strategy/`):
   - Coordinates the prompt generation process
   - Implements strategies for different testing scenarios
   - Connects information and templates with the language model

4. **Unified Framework** (`framework.py`):
   - Provides a unified facade for the entire system
   - Simplifies initialization and configuration
   - Manages the lifecycle of all components

### 2.3 Design Patterns

The implementation leverages several design patterns:

1. **Strategy Pattern**: Applied in different prompt strategies
2. **Composite Pattern**: Used in the composition of fragments
3. **Factory Pattern**: Used in the instantiation of components
4. **Facade Pattern**: Applied in the unified framework
5. **Template Method Pattern**: Used in information fragments
6. **Repository Pattern**: Applied in template management
7. **Inheritance Pattern**: Used in template hierarchies for reusability
8. **Dependency Injection**: Used through ComponentConfigurator

## 3. Information Layer

### 3.1 Information Fragments

The foundation of the information layer is the abstract `InformationFragment` class:

```python
class InformationFragment(abc.ABC):
    """Base class for all information fragments."""
    
    def __init__(self, name: str, priority: int = 100):
        """Initialize the information fragment."""
        self.name = name
        self.priority = priority
        self.logger = # logger configuration
        self.error_handler = ErrorHandler.get_instance()
    
    @abc.abstractmethod
    def generate(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        """Generate the formatted information from the given state and context."""
        pass
    
    def should_include(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> bool:
        """Determine if this fragment should be included in the current prompt."""
        return True
    
    def get_info(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get the information from this fragment if it should be included."""
        try:
            if not self.should_include(state, context):
                return {}
            
            result = self.generate(state, context)
            if result is None:
                return {}
                
            return {self.name: result}
        except Exception as e:
            # error handling
            return {}
```

### 3.2 Specialized Fragments

The system includes various specialized fragments:

#### UIElementsFragment

```python
class UIElementsFragment(InformationFragment):
    """Fragment for extracting and formatting UI element information."""
    
    def __init__(self, name: str = FragmentType.UI_ELEMENTS, priority: int = 200):
        super().__init__(name, priority)
    
    def generate(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        """Generate formatted UI element information."""
        # Format UI elements from the screen state
        # Return a structured text representation of the UI
```

#### UIPatternFragment

```python
class UIPatternFragment(InformationFragment):
    """Fragment for extracting and formatting UI pattern information."""
    
    def __init__(self, name: str = FragmentType.UI_PATTERNS, priority: int = 150):
        super().__init__(name, priority)
    
    def generate(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate UI pattern information."""
        # Detect UI patterns like login forms, settings pages, etc.
        # Return structured information about these patterns
```

#### MonitoredOperationsFragment

```python
class MonitoredOperationsFragment(InformationFragment):
    """Fragment for extracting and formatting monitored operations information."""
    
    def __init__(self, name: str = FragmentType.MONITORED_OPERATIONS, priority: int = 300):
        super().__init__(name, priority)
    
    def generate(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate monitored operations information."""
        # Process information about monitored operations (crypto, network, etc.)
        # Format this information for inclusion in prompts
```

#### ActionHistoryFragment

```python
class ActionHistoryFragment(InformationFragment):
    """Fragment for providing action history information."""
    
    def __init__(self, name: str = FragmentType.ACTION_HISTORY, priority: int = 150):
        super().__init__(name, priority)
    
    def generate(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        """Generate information about action history."""
        # Extract action history from state or context
        # Format history data into a readable text format
        # Return structured history information for prompt inclusion
        
        # Essential to handle the case when history is empty/missing
        if "action_history" not in state:
            return "No previous actions recorded."
            
        # Parse and format history data
        # Return formatted history
```

#### MemoryInsightsFragment

```python
class MemoryInsightsFragment(InformationFragment):
    """Fragment for providing insights from system memory."""
    
    def __init__(self, name: str = FragmentType.MEMORY_INSIGHTS, priority: int = 175):
        super().__init__(name, priority)
    
    def generate(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        """Generate insights from memory system."""
        # Extract insights from memory system
        # Analyze past interactions and patterns
        # Return formatted memory insights
        
        # Handle case when no memory data is available
        if "memory_insights" not in state:
            return "No memory insights available."
            
        # Return formatted memory insights
```

### 3.3 Information Manager

The `InformationManager` coordinates fragments and composes complete information:

```python
class InformationManager:
    """Manages information fragments and composes information for prompt generation."""
    
    def __init__(self):
        self.fragments: Dict[str, InformationFragment] = {}
        self.logger = # logger configuration
        self.error_handler = ErrorHandler.get_instance()
    
    def configure(self, config: ComponentConfigurator) -> None:
        """Configure the InformationManager with the given configuration."""
        # Configuration logic
    
    def register_fragment(self, fragment: InformationFragment) -> None:
        """Register an information fragment."""
        self.fragments[fragment.name] = fragment
    
    def register_fragments(self, fragments: List[InformationFragment]) -> None:
        """Register multiple information fragments."""
        for fragment in fragments:
            self.register_fragment(fragment)
    
    def get_information(self, fragment_name: str, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        """Get information from a specific fragment."""
        fragment = self.fragments.get(fragment_name)
        if not fragment:
            self.logger.warning(f"Fragment not found: {fragment_name}")
            return None
            
        try:
            if not fragment.should_include(state, context):
                return None
                
            return fragment.generate(state, context)
        except Exception as e:
            self.logger.error(f"Error generating information from fragment {fragment_name}: {e}")
            return None
    
    def compose_information(
        self, 
        state: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None,
        requested_fragments: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Compose information from all relevant fragments."""
        result = {}
        
        # Determine which fragments to include
        if requested_fragments:
            fragments_to_process = [
                f for name, f in self.fragments.items() 
                if name in requested_fragments
            ]
        else:
            fragments_to_process = sorted(
                self.fragments.values(),
                key=lambda f: f.priority,
                reverse=True
            )
        
        # Process each fragment
        for fragment in fragments_to_process:
            try:
                if fragment.should_include(state, context):
                    info = fragment.generate(state, context)
                    if info is not None:
                        result[fragment.name] = info
            except Exception as e:
                self.logger.error(f"Error in fragment {fragment.name}: {e}")
                # Continue with other fragments even if one fails
        
        return result
```

## 4. Template Layer

### 4.1 Jinja2 Templates

The `Jinja2Template` class manages variable substitution and rendering:

```python
class Jinja2Template:
    """Template for generating prompt messages with Jinja2 variable substitution."""
    
    def __init__(
        self, 
        template_text: str,
        name: str,
        required_variables: Optional[List[str]] = None,
        transformers: Optional[Dict[str, Callable[[Any], str]]] = None,
        environment: Optional[jinja2.Environment] = None
    ):
        """Initialize a Jinja2 template."""
        self.template_text = template_text
        self.name = name
        self.required_variables = set(required_variables or [])
        self.transformers = transformers or {}
        self.environment = environment or jinja2.Environment(
            loader=jinja2.BaseLoader(),
            autoescape=False,
            undefined=jinja2.StrictUndefined
        )
        self.template = self.environment.from_string(template_text)
        # Logging and error handling configuration
    
    def render(self, data: Dict[str, Any]) -> str:
        """Render the template with the given data."""
        try:
            # Check required variables
            missing_vars = []
            for var in self.required_variables:
                if var not in data:
                    missing_vars.append(var)
            
            if missing_vars:
                missing_vars_str = ", ".join(missing_vars)
                self.logger.warning(f"Required variables not found: {missing_vars_str}")
                return f"ERROR: Required variables not found: {missing_vars_str}"
            
            # Apply transformers
            for var, transformer in self.transformers.items():
                if var in data and callable(transformer):
                    try:
                        data[var] = transformer(data[var])
                    except Exception as e:
                        self.logger.error(f"Error transforming variable {var}: {e}")
            
            # Render the template with Jinja2
            result = self.template.render(**data)
            return result
        except jinja2.exceptions.UndefinedError as e:
            # Missing variable in the template itself
            self.logger.error(f"Undefined variable in template: {e}")
            return f"ERROR: Undefined variable in template: {e}"
        except Exception as e:
            # General error handling
            self.logger.error(f"Error rendering template: {e}")
            return f"ERROR: {str(e)}"
```

### 4.2 Jinja2 Template Repository

The `Jinja2TemplateRepository` manages externalized templates with Jinja2 integration:

```python
class Jinja2TemplateRepository(TemplateRepository):
    """Repository for managing XML prompt templates with Jinja2 integration."""
    
    def __init__(self, template_dir: Optional[str] = None, fragment_dir: Optional[str] = None):
        """Initialize the template repository."""
        self.template_dir = template_dir or os.path.join(
            os.path.dirname(__file__), "templates")
        self.fragment_dir = fragment_dir or os.path.join(
            os.path.dirname(__file__), "fragments")
        
        # Ensure the directories exist
        os.makedirs(self.template_dir, exist_ok=True)
        os.makedirs(self.fragment_dir, exist_ok=True)
        
        # Initialize template and fragment caches
        self.templates: Dict[str, Dict[str, Any]] = {}
        self.template_objects: Dict[str, Dict[str, Jinja2Template]] = {}
        self.fragments: Dict[str, str] = {}
        
        # Create Jinja2 environment with fragment loader
        self.fragment_loader = FragmentDictLoader({})
        self.environment = jinja2.Environment(
            loader=self.fragment_loader,
            autoescape=False,
            undefined=jinja2.StrictUndefined
        )
        
        # Load templates and fragments
        self._load_templates()
        self._load_fragments()
    
    def configure(self, config: ComponentConfigurator) -> None:
        """Configure the template repository with the given configuration."""
        # Get custom directories from configuration if specified
        template_dir = config.get_config("template_dir", str, None)
        fragment_dir = config.get_config("fragment_dir", str, None)
        
        if template_dir:
            self.template_dir = template_dir
            self._load_templates()
            
        if fragment_dir:
            self.fragment_dir = fragment_dir
            self._load_fragments()
    
    def _load_templates(self) -> None:
        """Load templates from XML files in the template directory."""
        # Implementation for loading XML template files
    
    def _load_fragments(self) -> None:
        """Load fragments from XML files in the fragment directory."""
        # Implementation for loading fragments
    
    def get_template(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a template by name."""
        return self.templates.get(name)
    
    def get_template_object(self, name: str, role: str) -> Optional[Jinja2Template]:
        """Get a template object by name and role."""
        template_objects = self.template_objects.get(name, {})
        return template_objects.get(role)
    
    def get_fragment(self, name: str) -> Optional[str]:
        """Get a fragment by name."""
        return self.fragments.get(name)
    
    def get_available_templates(self) -> List[str]:
        """Get a list of available template names."""
        return list(self.templates.keys())
    
    def create_messages(
        self, 
        template_name: str, 
        variables: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Create a list of messages using the specified template."""
        # Get the template
        template = self.get_template(template_name)
        if not template:
            self.logger.error(f"Template not found: {template_name}")
            return []
        
        messages = []
        
        # Create messages for each role in the template
        roles = template.get("roles", {})
        for role, role_template in roles.items():
            template_obj = self.get_template_object(template_name, role)
            if not template_obj:
                continue
            
            # Render the content with Jinja2
            try:
                content = template_obj.render(variables)
                if content.startswith("ERROR:"):
                    self.logger.error(f"Error rendering template {template_name}.{role}: {content}")
                    continue
                
                # Add to message list
                messages.append({
                    "role": role,
                    "content": content
                })
            except Exception as e:
                self.logger.error(f"Error creating message for {template_name}.{role}: {e}")
        
        return messages
```

### 4.3 Fragment Dictionary Loader

The `FragmentDictLoader` class is used to load fragments for Jinja2:

```python
class FragmentDictLoader(jinja2.BaseLoader):
    """A custom Jinja2 loader that loads templates from a dictionary."""
    
    def __init__(self, fragments: Dict[str, str]):
        """Initialize the loader with a dictionary of fragments."""
        self.fragments = fragments
    
    def get_source(self, environment: jinja2.Environment, template: str) -> Tuple[str, str, Callable[[], bool]]:
        """Get the template source from the dictionary."""
        if template not in self.fragments:
            raise jinja2.exceptions.TemplateNotFound(template)
        
        source = self.fragments[template]
        return source, template, lambda: True
    
    def update_fragments(self, fragments: Dict[str, str]) -> None:
        """Update the fragment dictionary."""
        self.fragments.update(fragments)
```

### 4.4 Template Examples with Jinja2 Syntax

Templates are stored in XML files with Jinja2 syntax for variables and control structures. Example:

```xml
<template name="standard">
  <s><![CDATA[
You are an Android testing assistant. Your task is to help test the Android application by identifying UI elements and suggesting testing actions.

The current screen contains the following UI elements:
{{ screen_description }}

{% if ui_patterns %}I've identified the following UI patterns:
{{ ui_patterns }}

{% endif %}{% if monitored_operations %}Pay attention to monitored operations:
{{ monitored_operations.summary }}

{% endif %}
  ]]></s>
  <user><![CDATA[
Based on the current screen, suggest ONE testing action that would help explore the application functionality and potentially trigger monitored operations.{% if additional_guidelines %}

{{ additional_guidelines }}{% endif %}
  ]]></user>
  <required_variables>
    <variable>screen_description</variable>
  </required_variables>
  <metadata>
    <max_tokens>300</max_tokens>
  </metadata>
</template>
```

Note the key differences in syntax from the previous version:
- Variables now use `{{ variable }}` instead of `{variable}`
- Control structures use `{% if condition %}` and `{% endif %}` instead of `{#if condition}` and `{#endif}`
- Fragments are included using `{% include "fragment_name" %}` instead of `{#include fragment_name}`
- The system role tag is now `<s>` instead of `<system>` for better readability

## 5. Strategy Layer

### 5.1 Prompt Strategy

The base `PromptStrategy` class defines the interface for all strategies:

```python
class PromptStrategy(abc.ABC):
    """Base class for all prompt generation strategies."""
    
    DEFAULT_TEMPLATE = "standard"
    
    def __init__(
        self, 
        name: str,
        information_manager: Optional[InformationManager] = None,
        template_repository: Optional[Jinja2TemplateRepository] = None
    ):
        """Initialize the prompt strategy."""
        self.name = name
        self.information_manager = information_manager
        self.template_repository = template_repository
        self.logger = # logger configuration
        self.error_handler = ErrorHandler.get_instance()
    
    def configure(self, config: ComponentConfigurator) -> None:
        """Configure the strategy with the given configuration."""
        self.logger.info(f"Configuring strategy: {self.name}")
        # Specific configuration logic
    
    def get_template_name(self, context: Dict[str, Any]) -> Optional[str]:
        """Get the template name to use for this strategy."""
        # Check if template name is specified in context
        if context and "template" in context:
            return context["template"]
        
        # Use default template
        return self.DEFAULT_TEMPLATE
    
    @abc.abstractmethod
    def generate_prompt(
        self, 
        state: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """Generate a prompt for the given state and context."""
        pass
        
    def generate_mcp_prompt(
        self, 
        state: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None
    ) -> List[LLMMessage]:
        """Generate a prompt for the given state and context in MCP format."""
        # Convert standard prompt to LLM format
        messages = self.generate_prompt(state, context)
        return [LLMMessage(role=msg["role"], content=msg["content"]) for msg in messages]
```

### 5.2 Specialized Strategies

The system includes various specialized strategies:

#### StandardStrategy

```python
class StandardStrategy(PromptStrategy):
    """Standard prompt generation strategy that generates exactly one action per response."""
    
    DEFAULT_TEMPLATE = "standard"
    
    def __init__(
        self,
        name: str = PromptStrategyType.STANDARD,
        information_manager: Optional[InformationManager] = None,
        template_repository: Optional[Jinja2TemplateRepository] = None
    ):
        """Initialize the standard strategy."""
        super().__init__(name, information_manager, template_repository)
    
    def generate_prompt(
        self, 
        state: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """Generate a prompt for the given state and context."""
        if context is None:
            context = {}
            
        try:
            # Determine which template to use
            template_name = self.get_template_name(context)
            
            # Get information from fragments
            info = {}
            if self.information_manager:
                info = self.information_manager.compose_information(state, context)
            
            # Combine information with context
            # Note: context values override information values if there are conflicts
            variables = {**info, **context}
            
            # Generate messages from the template
            if self.template_repository:
                messages = self.template_repository.create_messages(template_name, variables)
                if messages:
                    return messages
            
            # Fallback if template generation failed
            return self._create_fallback_messages(state)
        except Exception as e:
            self.logger.error(f"Error generating prompt: {e}", exc_info=True)
            return self._create_fallback_messages(state)
    
    def _create_fallback_messages(self, state: Dict[str, Any]) -> List[Dict[str, str]]:
        """Create fallback messages if template generation fails."""
        # Simplified fallback for robustness
        return [
            {
                "role": "system",
                "content": "You are an Android testing assistant."
            },
            {
                "role": "user",
                "content": f"Suggest a test action for the current app state."
            }
        ]
```

#### BatchActionStrategy

```python
class BatchActionStrategy(PromptStrategy):
    """Batch action prompt generation strategy for generating multiple actions at once."""
    
    DEFAULT_TEMPLATE = "batch_action"
    
    def __init__(
        self,
        name: str = PromptStrategyType.BATCH_ACTION,
        information_manager: Optional[InformationManager] = None,
        template_repository: Optional[Jinja2TemplateRepository] = None,
        min_actions: int = 3,
        max_actions: int = 10
    ):
        """Initialize the batch action strategy."""
        super().__init__(name, information_manager, template_repository)
        self.min_actions = min_actions
        self.max_actions = max_actions
    
    def generate_prompt(
        self, 
        state: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """Generate a batch action prompt for the given state and context."""
        if context is None:
            context = {}
            
        try:
            # Always use the batch_action template
            template_name = self.get_template_name(context) or self.DEFAULT_TEMPLATE
            
            # Get information from fragments
            info = {}
            if self.information_manager:
                info = self.information_manager.compose_information(state, context)
            
            # Get test history from context
            history = context.get("test_history", [])
            
            # Add specific guidelines for batches
            batch_context = {
                **context,
                "min_actions": self.min_actions,
                "max_actions": self.max_actions,
                "batch_mode": True,
            }
            
            # Combine all information
            variables = {**info, **batch_context}
            
            # Generate messages from the template
            if self.template_repository:
                messages = self.template_repository.create_messages(template_name, variables)
                if messages:
                    return messages
            
            # Fallback if template generation failed
            return self._create_fallback_messages(state)
        except Exception as e:
            self.logger.error(f"Error generating batch action prompt: {e}", exc_info=True)
            return self._create_fallback_messages(state)
    
    def _create_fallback_messages(self, state: Dict[str, Any]) -> List[Dict[str, str]]:
        """Create fallback messages if template generation fails."""
        return [
            {
                "role": "system",
                "content": "You are an Android testing assistant. Generate multiple test actions."
            },
            {
                "role": "user",
                "content": f"Suggest {self.min_actions} to {self.max_actions} test actions for the current app state."
            }
        ]
        
    def should_use_batch(self, state: Dict[str, Any]) -> bool:
        """Determine if batch action strategy should be used for this state."""
        # Check if UI patterns are detected that benefit from batch actions
        # Check if state has complex form or multi-step workflow
```

### 5.3 Strategy Registry

The `StrategyRegistry` manages available strategies and integrates with ComponentConfigurator:

```python
class StrategyRegistry:
    """Registry for prompt generation strategies."""
    
    def __init__(self, configurator: Optional[ComponentConfigurator] = None):
        """Initialize the strategy registry."""
        self.strategies: Dict[str, PromptStrategy] = {}
        self.default_strategy: Optional[str] = None
        self.logger = # logger configuration
        self.error_handler = ErrorHandler.get_instance()
        self.configurator = configurator
    
    def configure(self, config: ComponentConfigurator) -> None:
        """Configure the strategy registry with the given configuration."""
        self.configurator = config
        
        # Configure registered strategies
        for name, strategy in self.strategies.items():
            strategy.configure(config)
        
        # Set default strategy if specified
        default_strategy = config.get_config("default_strategy", str, None)
        if default_strategy and default_strategy in self.strategies:
            self.default_strategy = default_strategy
        
        # Register strategies with the configurator if not already registered
        for name, strategy in self.strategies.items():
            if not self.configurator.has_component(ComponentType.PROMPT_STRATEGY, name):
                self.configurator.register_component(ComponentType.PROMPT_STRATEGY, name, strategy)
    
    def register_strategy(self, strategy: PromptStrategy) -> None:
        """Register a prompt generation strategy."""
        self.strategies[strategy.name] = strategy
        
        # Register with configurator if available
        if self.configurator and not self.configurator.has_component(ComponentType.PROMPT_STRATEGY, strategy.name):
            self.configurator.register_component(ComponentType.PROMPT_STRATEGY, strategy.name, strategy)
        
        # If this is the first strategy, set it as default
        if not self.default_strategy:
            self.default_strategy = strategy.name
    
    def get_strategy(self, name: Optional[str] = None) -> Optional[PromptStrategy]:
        """Get a registered strategy by name."""
        # First check local registry
        if name and name in self.strategies:
            return self.strategies[name]
        
        # Then check configurator
        if name and self.configurator and self.configurator.has_component(ComponentType.PROMPT_STRATEGY, name):
            strategy = self.configurator.get_component(ComponentType.PROMPT_STRATEGY, name)
            if isinstance(strategy, PromptStrategy):
                # Add to local registry for future use
                self.strategies[name] = strategy
                return strategy
        
        # Return default strategy
        if self.default_strategy:
            return self.strategies.get(self.default_strategy)
        
        return None
    
    def get_available_strategies(self) -> List[str]:
        """Get a list of available strategy names."""
        return list(self.strategies.keys())
```

## 6. Unified Framework

### 6.1 PromptFramework Class

The `PromptFramework` class serves as a facade for the entire system:

```python
class PromptFramework:
    """Unified framework for prompt generation."""
    
    def __init__(
        self, 
        information_manager: InformationManager,
        template_repository: Jinja2TemplateRepository,
        strategy_registry: StrategyRegistry,
        config: Optional[ComponentConfigurator] = None,
        model: Optional[LanguageModel] = None
    ):
        """Initialize the prompt framework."""
        self.information_manager = information_manager
        self.template_repository = template_repository
        self.strategy_registry = strategy_registry
        self.config = config
        self.model = model
        self.logger = # logger configuration
        self.error_handler = ErrorHandler.get_instance()
        
        # Configure components if configuration is provided
        if self.config:
            self.configure(self.config)
    
    def configure(self, config: ComponentConfigurator) -> None:
        """Configure the framework and its components."""
        self.config = config
        
        # Configure components
        if self.information_manager:
            self.information_manager.configure(config)
        
        if self.template_repository:
            self.template_repository.configure(config)
        
        if self.strategy_registry:
            self.strategy_registry.configure(config)
    
    @classmethod
    def create(cls, config: Optional[ComponentConfigurator] = None) -> 'PromptFramework':
        """Create and configure a new prompt framework."""
        # Create configuration if not provided
        if not config:
            config = ComponentConfigurator()
        
        # Create components
        information_manager = InformationManager()
        template_repository = Jinja2TemplateRepository()
        strategy_registry = StrategyRegistry(config)
        
        # Register with configurator
        if not config.has_component(ComponentType.INFORMATION_MANAGER, "default"):
            config.register_component(ComponentType.INFORMATION_MANAGER, "default", information_manager)
        
        if not config.has_component(ComponentType.TEMPLATE_REPOSITORY, "default"):
            config.register_component(ComponentType.TEMPLATE_REPOSITORY, "default", template_repository)
        
        if not config.has_component(ComponentType.STRATEGY_REGISTRY, "default"):
            config.register_component(ComponentType.STRATEGY_REGISTRY, "default", strategy_registry)
        
        # Create language model if specified in config
        model = None
        if config.has_llm_config():
            # Create model based on configuration
            model = create_language_model_from_config(config)
        
        # Create framework
        framework = cls(
            information_manager=information_manager,
            template_repository=template_repository,
            strategy_registry=strategy_registry,
            config=config,
            model=model
        )
        
        # Register default fragments and strategies
        framework._register_defaults()
        
        return framework
    
    def _register_defaults(self) -> None:
        """Register default fragments and strategies."""
        # Register default fragments
        self.register_information_fragment(UIElementsFragment())
        self.register_information_fragment(UIPatternFragment())
        self.register_information_fragment(MonitoredOperationsFragment())
        self.register_information_fragment(ActionHistoryFragment())
        self.register_information_fragment(MemoryInsightsFragment())
        
        # Register default strategies
        self.register_prompt_strategy(StandardStrategy(
            information_manager=self.information_manager,
            template_repository=self.template_repository
        ))
        self.register_prompt_strategy(BatchActionStrategy(
            information_manager=self.information_manager,
            template_repository=self.template_repository
        ))
    
    def register_information_fragment(self, fragment: InformationFragment) -> None:
        """Register an information fragment."""
        if self.information_manager:
            self.information_manager.register_fragment(fragment)
    
    def register_prompt_strategy(self, strategy: PromptStrategy) -> None:
        """Register a prompt strategy."""
        if self.strategy_registry:
            self.strategy_registry.register_strategy(strategy)
    
    def get_available_templates(self) -> List[str]:
        """Get a list of available template names."""
        if self.template_repository:
            return self.template_repository.get_available_templates()
        return []
    
    def get_available_strategies(self) -> List[str]:
        """Get a list of available strategy names."""
        if self.strategy_registry:
            return self.strategy_registry.get_available_strategies()
        return []
    
    def get_information(self, fragment_name: str, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        """Get information from a specific fragment."""
        if self.information_manager:
            return self.information_manager.get_information(fragment_name, state, context)
        return None
    
    def generate_prompt(
        self, 
        strategy_name: Optional[str], 
        state: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """Generate a prompt using the specified strategy."""
        if context is None:
            context = {}
        
        try:
            # Get the strategy
            strategy = self.strategy_registry.get_strategy(strategy_name)
            if not strategy:
                self.logger.error(f"Strategy not found: {strategy_name}")
                return []
            
            # Generate the prompt
            return strategy.generate_prompt(state, context)
        except Exception as e:
            self.logger.error(f"Error generating prompt: {e}", exc_info=True)
            return []
    
    def generate_with_llm(
        self, 
        strategy_name: Optional[str], 
        state: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """Generate a prompt and send it to the LLM for a response."""
        if not self.model:
            self.logger.error("No language model available")
            return None
        
        messages = self.generate_prompt(strategy_name, state, context)
        if not messages:
            return None
        
        try:
            # Convert to LLM message format if needed
            llm_messages = [LLMMessage(role=msg["role"], content=msg["content"]) for msg in messages]
            
            # Send to LLM
            response = self.model.generate(llm_messages)
            return response
        except Exception as e:
            self.logger.error(f"Error generating with LLM: {e}", exc_info=True)
            return None
```

## 7. Service Integration

### 7.1 LLMActionService

The `LLMActionService` has been updated to use the unified framework:

```python
class LLMActionService:
    """
    Orchestrates the AI-driven test action generation system.
    
    This service coordinates the entire process of generating testing actions
    from the current application state, including:
    - Enriching the state with additional information
    - Selecting the appropriate prompt strategy
    - Generating prompts using the PromptFramework
    - Processing LLM responses into executable actions
    """
    
    def __init__(self, config: Optional[ComponentConfigurator] = None):
        """Initialize the LLM action service."""
        self.config = config or ComponentConfigurator()
        self.framework = PromptFramework.create(self.config)
        # Initialize other components
    
    def process_state(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process the current state and generate testing actions."""
        # Enrich state with additional information
        enriched_state = self._enrich_state(state)
        
        # Determine which strategy to use based on the state
        strategy_name = self._select_strategy(enriched_state)
        
        # Generate response with the selected strategy
        response = self.framework.generate_with_llm(strategy_name, enriched_state)
        
        # Parse the response into actions
        actions = self._parse_response(response, strategy_name)
        
        return actions
    
    def _enrich_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich the state with additional information."""
        # Ensure all required variables are present
        enriched = state.copy()
        
        # Add default values for commonly required variables if missing
        if "ui_elements" not in enriched:
            enriched["ui_elements"] = "No UI elements detected."
            
        if "action_history" not in enriched:
            enriched["action_history"] = "No previous actions recorded."
            
        if "memory_insights" not in enriched:
            enriched["memory_insights"] = "No memory insights available."
        
        # Add additional context information
        # ...
        
        return enriched
```

### 7.2 LLMConsultationManager

The `LLMConsultationManager` has also been updated:

```python
class LLMConsultationManager(Component):
    """
    Manager for LLM consultation in RVDroid.
    
    This component provides strategic guidance and action feedback through
    LLM consultation, using the PromptFramework for consistent interactions.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the LLM consultation manager."""
        super().__init__(config)
        self.component_config = config.get("component_configurator")
        self.framework = PromptFramework.create(self.component_config)
        # Initialize other components
    
    def initialize(self) -> None:
        """Initialize the LLM consultation manager."""
        super().initialize()
        # Additional initialization
    
    def get_strategic_guidance(self, state: Dict[str, Any]) -> str:
        """Get strategic guidance for the current state."""
        # Ensure state has all required variables
        enriched_state = self._enrich_state(state)
        
        # Generate strategic guidance using the PromptFramework
        response = self.framework.generate_with_llm(
            "strategic_guidance",
            enriched_state,
            {"mode": "guidance"}
        )
        
        # Parse and return the guidance
        return self._parse_guidance(response)
    
    def _enrich_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure state has all required variables."""
        enriched = state.copy()
        
        # Add default values for missing required variables
        if "ui_elements" not in enriched:
            enriched["ui_elements"] = "No UI elements detected."
            
        if "action_history" not in enriched:
            enriched["action_history"] = "No previous actions recorded."
            
        if "memory_insights" not in enriched:
            enriched["memory_insights"] = "No memory insights available."
        
        return enriched
```

## 8. Usage Examples

### 8.1 Basic Framework Usage

```python
from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.llm.prompt.framework import PromptFramework
from rvandroid.llm.constants import StateEntry, PromptStrategyType

# Create configuration
config = ComponentConfigurator()
config.set_llm(
    llm_type="ollama",
    model="llama3",
    temperature=0.3,
    max_tokens=800,
    base_url="http://localhost:11434"
)

# Create and initialize the framework
framework = PromptFramework.create(config)

# Create complete state with all required variables for templates
def create_complete_tutorial_state(activity_name="MainActivity", package_name="com.example.testapp"):
    # Basic state elements
    state = {
        StateEntry.PACKAGE_NAME: package_name,
        StateEntry.ACTIVITY: f"{package_name}.{activity_name}",
        StateEntry.SCREEN_DESCRIPTION: f"Screen of {activity_name} with simulated elements."
    }
    
    # UI elements (required by many templates)
    state["ui_elements"] = """
ELEMENTOS DE UI:
- Text field: Username (id: username_field)
- Text field: Password (id: password_field)
- Button: Login (id: login_button)
- Button: Cancel (id: cancel_button)
- Link: Forgot password (id: forgot_password)
    """
    
    # Action history (required by some templates)
    state["action_history"] = """
PREVIOUS ACTIONS:
- Clicked: App icon
- Loaded: MainActivity
- Clicked: Login button
    """
    
    # Memory insights (required by some templates)
    state["memory_insights"] = """
APP MEMORY INSIGHTS:
- 2 screens previously visited in this session
- Common navigation pattern: Home -> Login -> This screen
- Most visited screens: Home (5x), Settings (2x), Login (3x)
    """
    
    return state

# Create state with all required variables
state = create_complete_tutorial_state()

# Define additional context
context = {
    "additional_guidelines": "Focus on testing the login functionality."
}

# Generate prompt using standard strategy
messages = framework.generate_prompt(PromptStrategyType.STANDARD, state, context)

# Send to LLM and get response
response = framework.generate_with_llm(PromptStrategyType.STANDARD, state, context)
print(f"LLM Response: {response.get_text_content() if hasattr(response, 'get_text_content') else response}")
```

### 8.2 Custom Fragments

```python
from rvandroid.llm.prompt.information.base_fragment import InformationFragment
from rvandroid.llm.prompt.framework import PromptFramework
from rvandroid.llm.constants import StateEntry, PromptStrategyType
from typing import Dict, Any, Optional

# Create custom fragment
class CustomFragment(InformationFragment):
    """Custom information fragment."""
    
    def __init__(self, name: str = "custom_info", priority: int = 100):
        super().__init__(name, priority)
    
    def generate(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        # Extract custom information from state
        package_name = state.get(StateEntry.PACKAGE_NAME, "unknown")
        activity = state.get(StateEntry.ACTIVITY, "unknown")
        
        return f"Testing app: {package_name}\nCurrent activity: {activity}\nAdditional custom information to include in prompts."
    
    def should_include(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> bool:
        # Include only if state has package data
        return StateEntry.PACKAGE_NAME in state

# Create framework
framework = PromptFramework.create()

# Register custom fragment
framework.register_information_fragment(CustomFragment())

# Create complete state with all required variables
state = create_complete_tutorial_state()

# Use the framework with the custom fragment
messages = framework.generate_prompt(PromptStrategyType.STANDARD, state, context)
```

### 8.3 Using Custom Template with Jinja2 Syntax

```python
from rvandroid.llm.prompt.framework import PromptFramework
from rvandroid.llm.constants import StateEntry, PromptStrategyType

# Create a custom template file with Jinja2 syntax
custom_template_content = """<?xml version="1.0" encoding="UTF-8"?>
<template name="security_template" version="1.0" extends="system_base">
  <metadata>
    <description>Template for security testing</description>
    <created>2025-04-18</created>
    <author>RV-Android Team</author>
  </metadata>
  <variables>
    <required>ui_elements</required>
    <optional>action_history</optional>
    <optional>memory_insights</optional>
  </variables>
  <roles>
    <s>
      <variable name="strategy_specific_instructions">
        <![CDATA[
Your task is to analyze the current state for potential security vulnerabilities.

{% include "security_testing_guidelines" %}
        ]]>
      </variable>
      <variable name="response_format_instructions">
        <![CDATA[
{% include "standard_format" %}
        ]]>
      </variable>
    </s>
    <user><![CDATA[
Current Activity: {{ activity }}

{% if action_history %}{{ action_history }}

{% endif %}{% if memory_insights %}{{ memory_insights }}

{% endif %}Current UI Elements:
{{ ui_elements }}

Your task is to identify the single most critical security test for this screen.
    ]]></user>
  </roles>
</template>
"""

# In a real example, you would write this to a file
# Here we'll just create a framework with our custom fragment

# Register the custom fragment and template
framework = PromptFramework.create()

# Create complete state with all required variables
state = create_complete_tutorial_state(
    activity_name="LoginActivity", 
    package_name="com.example.bankapp"
)

context = {
    "template": "security_template",  # This would normally select our custom template
}

# Generate messages
messages = framework.generate_prompt(PromptStrategyType.STANDARD, state, context)
```

## 9. System Extension

### 9.1 Creating New Fragments

To create a new information fragment:

```python
from rvandroid.llm.prompt.information.base_fragment import InformationFragment
from rvandroid.llm.constants import FragmentType, StateEntry
from typing import Dict, Any, Optional, List

class HistoryFragment(InformationFragment):
    """Fragment for providing action history information."""
    
    def __init__(self, name: str = "action_history", priority: int = 150):
        super().__init__(name, priority)
        self.action_history = []
    
    def generate(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        """Generate information about action history in the current state."""
        # First check if action_history already exists in state (preferred source)
        if "action_history" in state:
            return state["action_history"]
            
        # Get current app information
        package_name = state.get(StateEntry.PACKAGE_NAME, "unknown")
        activity = state.get(StateEntry.ACTIVITY, "unknown")
        
        # Format history text
        if not self.action_history:
            return "No previous actions recorded."
        
        history_text = "Previous actions:\n"
        for i, action in enumerate(self.action_history[-5:], 1):
            result_text = "✓" if action.get("success", False) else "✗"
            history_text += f"{i}. {action.get('type', 'unknown')}: {action.get('target', 'unknown')} - {result_text}\n"
        
        return history_text
    
    def add_action(self, action: Dict[str, Any], result: bool) -> None:
        """Add a new action to the history."""
        self.action_history.append({
            "type": action.get("type"),
            "target": action.get("target"),
            "success": result
        })
        # Keep history at reasonable size
        if len(self.action_history) > 20:
            self.action_history = self.action_history[-20:]
    
    def should_include(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> bool:
        # Include if history exists in state or we have local history
        return "action_history" in state or len(self.action_history) > 0
```

### 9.2 Creating New Strategies

To create a new prompt strategy:

```python
from rvandroid.llm.prompt.strategy.base_strategy import PromptStrategy
from rvandroid.llm.constants import PromptStrategyType
from rvandroid.llm.prompt.information.fragment_manager import InformationManager
from rvandroid.llm.prompt.template.jinja_repository import Jinja2TemplateRepository
from typing import Dict, Any, Optional, List

class ExplorationStrategy(PromptStrategy):
    """Strategy focused on exploration breadth."""
    
    DEFAULT_TEMPLATE = "exploration"
    
    def __init__(
        self,
        name: str = "exploration",
        information_manager: Optional[InformationManager] = None,
        template_repository: Optional[Jinja2TemplateRepository] = None
    ):
        """Initialize the exploration strategy."""
        super().__init__(name, information_manager, template_repository)
    
    def generate_prompt(
        self, 
        state: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """Generate an exploration-focused prompt."""
        if context is None:
            context = {}
        
        try:
            # Use exploration template
            template_name = self.get_template_name(context) or self.DEFAULT_TEMPLATE
            
            # Get information with standard fragments
            info = {}
            if self.information_manager:
                info = self.information_manager.compose_information(state, context)
            
            # Add exploration guidelines
            if "additional_guidelines" not in context:
                context["additional_guidelines"] = (
                    "Focus on exploring new screens and UI elements that haven't been visited before. "
                    "Prioritize breadth of exploration rather than depth."
                )
            
            # Generate messages from template
            variables = {**info, **context}
            
            if self.template_repository:
                # Check if the template exists
                available_templates = self.template_repository.get_available_templates()
                if template_name not in available_templates:
                    self.logger.warning(f"Template '{template_name}' not found. Using fallback.")
                    return self._create_fallback_messages(state)
                    
                messages = self.template_repository.create_messages(template_name, variables)
                return messages or self._create_fallback_messages(state)
            else:
                return self._create_fallback_messages(state)
                
        except Exception as e:
            self.logger.error(f"Error generating exploration prompt: {e}", exc_info=True)
            return self._create_fallback_messages(state)
    
    def _create_fallback_messages(self, state: Dict[str, Any]) -> List[Dict[str, str]]:
        """Create fallback messages if template generation fails."""
        return [
            {
                "role": "system",
                "content": "You are an Android testing assistant focused on exploration."
            },
            {
                "role": "user",
                "content": "Suggest an action that would help explore new parts of the app."
            }
        ]
```

### 9.3 Creating New Templates with Jinja2 Syntax

To create a new template with Jinja2 syntax:

```python
import os
from rvandroid.llm.prompt.template.template_utils import create_template_xml_string

# Create template content
template_content = create_template_xml_string(
    name="exploration",
    version="1.0",
    description="Template for exploration-focused prompts",
    author="RV-Android Team",
    created="2025-04-18",
    required_vars=["ui_elements"],
    optional_vars=["action_history", "memory_insights", "additional_guidelines"],
    system_content="""
You are an Android exploration assistant. Your job is to discover new screens and functionality in the app.

The current screen contains:
{{ ui_elements }}

{% if action_history %}Previous actions:
{{ action_history }}

{% endif %}{% if memory_insights %}Memory insights:
{{ memory_insights }}

{% endif %}
""",
    user_content="""
Suggest ONE action that would help explore a new part of this application that hasn't been seen before.{% if additional_guidelines %}

{{ additional_guidelines }}{% endif %}
"""
)

# Write to template file
template_dir = "/path/to/templates"
os.makedirs(template_dir, exist_ok=True)
with open(os.path.join(template_dir, "exploration.xml"), "w") as f:
    f.write(template_content)

# Load in template repository
from rvandroid.llm.prompt.template.jinja_repository import Jinja2TemplateRepository
repository = Jinja2TemplateRepository(template_dir)
repository._load_templates()
```

## 10. Modular Template System

### 10.1 Template Inheritance

The template system supports inheritance through the `extends` attribute, allowing templates to build upon a base template:

```xml
<template name="standard" version="1.0" extends="system_base">
  <metadata>
    <description>Standard template for Android testing</description>
    <created>2025-04-17</created>
    <author>RV-Android Team</author>
  </metadata>
  <variables>
    <required>ui_elements</required>
    <optional>action_history</optional>
    <optional>memory_insights</optional>
    <optional>additional_guidelines</optional>
  </variables>
  <roles>
    <s>
      <variable name="strategy_specific_instructions">
        <!-- Specific instructions that override the parent template -->
        <![CDATA[
IMPORTANT: You will be provided with a list of possible actions, each with a unique action_id. Your job is to select exactly ONE action to perform. Choose the most effective action for thorough testing.
        ]]>
      </variable>
      <variable name="response_format_instructions">
        <!-- Format instructions that override the parent template -->
        <![CDATA[
Format your response as a valid JSON object following this schema:
{
  "action_id": "5",  
  "params": {},  
  "explanation": "Detailed explanation of why this action was chosen"
}

For actions that require parameters (like SET_TEXT), you must include appropriate values:
{
  "action_id": "5",  
  "params": {"text": "test@example.com"},  
  "explanation": "Entering a valid email address in the email field"
}

DO NOT include any additional text outside of the JSON object. Your response must be valid JSON that can be parsed directly.
        ]]>
      </variable>
    </s>
    <user><![CDATA[
Current Activity: {{ activity }}

{% if action_history %}{{ action_history }}

{% endif %}{% if memory_insights %}{{ memory_insights }}

{% endif %}Current UI Elements:
{{ ui_elements }}

SUMMARY: You are testing the {{ activity }} screen. Select ONE action from the available options above that would be most effective for testing this screen. Remember to return your answer as a JSON object using the action_id values provided.{% if additional_guidelines %}

{{ additional_guidelines }}{% endif %}
    ]]></user>
  </roles>
</template>
```

### 10.2 Template Fragments with Jinja2

The system uses template fragments with Jinja2 syntax to create reusable pieces of prompt content:

```xml
<!-- fragments/ui_patterns/form_pattern.xml -->
<fragment name="form_pattern">
  <![CDATA[
For FORM patterns:
- Enter text in all text fields, starting from top to bottom
- Text values should match the expected format (emails, passwords, etc.)
- Select appropriate options in dropdown menus/spinners
- Check or uncheck checkboxes based on context
- Toggle switches appropriately
- ALWAYS fill all required fields BEFORE clicking submit/save buttons
- Test validation by intentionally providing invalid inputs occasionally
  ]]>
</fragment>
```

These fragments can be included in templates using the `{% include "fragment_name" %}` directive:

```xml
<template name="batch_action_modular" version="1.0" extends="system_base">
  <metadata>
    <description>Template for generating batches of testing actions (modular version)</description>
    <created>2025-04-18</created>
    <author>RV-Android Team</author>
  </metadata>
  <variables>
    <required>ui_elements</required>
    <optional>action_history</optional>
    <optional>memory_insights</optional>
    <optional>additional_guidelines</optional>
  </variables>
  <roles>
    <s>
      <variable name="strategy_specific_instructions">
        <![CDATA[
{% include "batch_instructions" %}
        ]]>
      </variable>
      <variable name="response_format_instructions">
        <![CDATA[
{% include "batch_format" %}
        ]]>
      </variable>
      <variable name="additional_guidelines">
        <![CDATA[
{% include "batch_guidelines" %}
        ]]>
      </variable>
    </s>
    <user><![CDATA[
{% include "user_base" %}
{% include "batch_ui_pattern_detection" %}
{% if memory_insights %}{{ memory_insights }}

{% endif %}{% include "batch_critical_task" %}{% if additional_guidelines %}

{{ additional_guidelines }}{% endif %}
    ]]></user>
  </roles>
</template>
```

### 10.3 Fragment Categories

The fragment system organizes fragments into logical categories:

1. **UI Patterns** (`fragments/ui_patterns/`):
   - `form_pattern.xml`: Guidance for testing forms
   - `list_pattern.xml`: Guidance for testing lists
   - `tabs_pattern.xml`: Guidance for testing tabbed interfaces

2. **System Role Fragments** (`fragments/`):
   - `system_intro.xml`: Introduction for system prompts
   - `system_guidelines.xml`: Common guidelines for action selection
   - `standard_instructions.xml`: Instructions for single action strategy
   - `standard_format.xml`: JSON format for single action responses
   - `batch_instructions.xml`: Instructions for batch action strategy
   - `batch_format.xml`: JSON format for batch action responses
   - `batch_guidelines.xml`: Guidelines specific to batch action generation
   - `standard_guidelines.xml`: Additional guidelines for standard strategy

3. **User Role Fragments** (`fragments/`):
   - `user_base.xml`: Common structure for user prompts (current activity, static context, UI elements)
   - `standard_summary.xml`: Summary for standard strategy user prompts
   - `batch_ui_pattern_detection.xml`: UI pattern identification for batch strategy
   - `batch_critical_task.xml`: Critical task definition for batch action generation

This modular organization makes it easy to combine and reuse fragments across different templates while maintaining consistency in the prompt language.

### 10.4 Jinja2 Template Processing

The Jinja2-based template system implements fragment inclusion as part of the rendering process:

```python
def render(self, data: Dict[str, Any]) -> str:
    """
    Render the template with the given data.
    
    Args:
        data: Dictionary of variables to substitute in the template
        
    Returns:
        Rendered template content
    """
    try:
        # Check required variables
        missing_vars = []
        for var in self.required_variables:
            if var not in data:
                missing_vars.append(var)
        
        if missing_vars:
            missing_vars_str = ", ".join(missing_vars)
            self.logger.warning(f"Required variables not found: {missing_vars_str}")
            return f"ERROR: Required variables not found: {missing_vars_str}"
        
        # Apply transformers if needed
        for var, transformer in self.transformers.items():
            if var in data and callable(transformer):
                try:
                    data[var] = transformer(data[var])
                except Exception as e:
                    self.logger.error(f"Error transforming variable {var}: {e}")
        
        # Render the template with Jinja2
        result = self.template.render(**data)
        return result
    except jinja2.exceptions.UndefinedError as e:
        # Special handling for undefined variables
        self.logger.error(f"Undefined variable in template: {e}")
        return f"ERROR: Undefined variable in template: {e}"
    except jinja2.exceptions.TemplateError as e:
        self.logger.error(f"Template rendering error: {e}")
        return f"ERROR: Template rendering error: {e}"
    except Exception as e:
        self.logger.error(f"Error rendering template: {e}", exc_info=True)
        return f"ERROR: {str(e)}"
```

This approach enables highly modular templates with efficient reuse of prompt components, making the system more maintainable and consistent.

## 11. Best Practices and Lessons Learned

### 11.1 State Enrichment

Always ensure that the state object contains all variables required by templates:

```python
def create_complete_tutorial_state(activity_name="MainActivity", package_name="com.example.testapp"):
    """
    Creates a complete state with all potentially required variables
    for templates, avoiding missing variable errors.
    """
    # Basic state elements
    state = {
        StateEntry.PACKAGE_NAME: package_name,
        StateEntry.ACTIVITY: f"{package_name}.{activity_name}",
        StateEntry.SCREEN_DESCRIPTION: f"Screen of {activity_name} with simulated elements."
    }
    
    # Add UI elements information based on screen type
    ui_text = """
UI ELEMENTS:
- Text field: Username (id: username_field)
- Text field: Password (id: password_field)
- Button: Login (id: login_button)
- Button: Cancel (id: cancel_button)
- Link: Forgot password (id: forgot_password)
    """
    
    state["ui_elements"] = ui_text
    
    # Add action history
    state["action_history"] = """
PREVIOUS ACTIONS:
- Clicked: App icon
- Loaded: MainActivity
- Clicked: Login button
    """
    
    # Add memory insights
    state["memory_insights"] = """
APP MEMORY INSIGHTS:
- 2 screens previously visited in this session
- Common navigation pattern: Home -> Login -> This screen
- Most visited screens: Home (5x), Settings (2x), Login (3x)
    """
    
    return state
```

When integrating with the actual system, implement robust state enrichment:

```python
def _enrich_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich the state with additional information."""
    # Create a copy to avoid modifying the original
    enriched = state.copy()
    
    # Add default values for commonly required variables if missing
    if "ui_elements" not in enriched:
        enriched["ui_elements"] = self.ui_detector.extract_elements(state)
            
    if "action_history" not in enriched:
        enriched["action_history"] = self.history_manager.get_formatted_history()
            
    if "memory_insights" not in enriched:
        enriched["memory_insights"] = self.memory_manager.get_insights_for_prompt()
    
    return enriched
```

### 11.2 Public Interface Methods

Ensure key functionality is accessible through public methods to avoid accessing internal attributes:

```python
# Avoid directly accessing private attributes like strategy_registry._strategies
# Instead, provide public methods:

def get_available_strategies(self) -> List[str]:
    """Get a list of available strategy names."""
    if self.strategy_registry:
        return self.strategy_registry.get_available_strategies()
    return []

def get_available_templates(self) -> List[str]:
    """Get a list of available template names."""
    if self.template_repository:
        return self.template_repository.get_available_templates()
    return []

def get_information(self, fragment_name: str, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
    """Get information from a specific fragment."""
    if self.information_manager:
        return self.information_manager.get_information(fragment_name, state, context)
    return None
```

### 11.3 Robust Error Handling

Implement thorough error handling at multiple levels:

```python
def generate_prompt(
    self, 
    strategy_name: Optional[str], 
    state: Dict[str, Any], 
    context: Optional[Dict[str, Any]] = None
) -> List[Dict[str, str]]:
    """Generate a prompt using the specified strategy."""
    if context is None:
        context = {}
    
    try:
        # Get the strategy
        strategy = self.strategy_registry.get_strategy(strategy_name)
        if not strategy:
            self.logger.error(f"Strategy not found: {strategy_name}")
            # Return an empty list instead of raising an exception
            return []
        
        # Generate the prompt
        return strategy.generate_prompt(state, context)
    except Exception as e:
        self.logger.error(f"Error generating prompt: {e}", exc_info=True)
        # Return an empty list instead of propagating the exception
        return []
```

Implement fallback mechanisms in all components:

```python
def _create_fallback_messages(self, state: Dict[str, Any]) -> List[Dict[str, str]]:
    """Create fallback messages if template generation fails."""
    return [
        {
            "role": "system",
            "content": "You are an Android testing assistant."
        },
        {
            "role": "user",
            "content": f"Suggest a test action for the current app state."
        }
    ]
```

### 11.4 Dependency Management

Use dependency injection through ComponentConfigurator instead of direct imports:

```python
def __init__(
    self, 
    information_manager: InformationManager,
    template_repository: Jinja2TemplateRepository,
    strategy_registry: StrategyRegistry,
    config: Optional[ComponentConfigurator] = None,
    model: Optional[LanguageModel] = None
):
    """Initialize the prompt framework with injected dependencies."""
    self.information_manager = information_manager
    self.template_repository = template_repository
    self.strategy_registry = strategy_registry
    self.config = config
    self.model = model
```

And provide factory methods to simplify instantiation:

```python
@classmethod
def create(cls, config: Optional[ComponentConfigurator] = None) -> 'PromptFramework':
    """Create and configure a new prompt framework."""
    # Create configuration if not provided
    if not config:
        config = ComponentConfigurator()
    
    # Create components
    information_manager = InformationManager()
    template_repository = Jinja2TemplateRepository()
    strategy_registry = StrategyRegistry(config)
    
    # Register with configurator
    if not config.has_component(ComponentType.INFORMATION_MANAGER, "default"):
        config.register_component(ComponentType.INFORMATION_MANAGER, "default", information_manager)
    
    # [...more registration...]
    
    # Create framework
    return cls(
        information_manager=information_manager,
        template_repository=template_repository,
        strategy_registry=strategy_registry,
        config=config,
        model=model
    )
```

### 11.5 Defensive Variable Checking

Always check for required variables and provide meaningful error messages:

```python
def render(self, data: Dict[str, Any]) -> str:
    """Render the template with the given data."""
    try:
        # Check required variables
        missing_vars = []
        for var in self.required_variables:
            if var not in data:
                missing_vars.append(var)
        
        if missing_vars:
            missing_vars_str = ", ".join(missing_vars)
            self.logger.warning(f"Required variables not found: {missing_vars_str}")
            return f"ERROR: Required variables not found: {missing_vars_str}"
        
        # Continue with rendering...
    except Exception as e:
        # Error handling...
```

### 11.6 Testing and Mocking

Create standalone test data for testing components in isolation:

```python
def create_test_template_repository():
    """Create a template repository for testing."""
    repo = Jinja2TemplateRepository()
    
    # Add a simple test template
    simple_template = """<?xml version="1.0" encoding="UTF-8"?>
    <template name="test_template" version="1.0">
      <variables>
        <required>ui_elements</required>
        <optional>action_history</optional>
      </variables>
      <roles>
        <s><![CDATA[Test system message with {{ ui_elements }}]]></s>
        <user><![CDATA[Test user message{% if action_history %} with {{ action_history }}{% endif %}]]></user>
      </roles>
    </template>
    """
    
    # Write to a temporary file and load
    with tempfile.NamedTemporaryFile(suffix='.xml', delete=False) as f:
        f.write(simple_template.encode('utf-8'))
        temp_file = f.name
    
    os.makedirs(os.path.join(os.path.dirname(temp_file), 'templates'), exist_ok=True)
    shutil.copy(temp_file, os.path.join(os.path.dirname(temp_file), 'templates', 'test_template.xml'))
    
    repo.template_dir = os.path.join(os.path.dirname(temp_file), 'templates')
    repo._load_templates()
    
    return repo
```

Use mock implementations for testing:

```python
class MockLanguageModel(LanguageModel):
    """Mock language model for testing."""
    
    def __init__(self, response_text="This is a test response"):
        self.response_text = response_text
    
    def generate(self, messages: List[LLMMessage]) -> LLMResponse:
        """Generate a mock response."""
        return LLMResponse(
            content=self.response_text,
            model="test_model",
            finish_reason="stop"
        )
```

With these components implemented, the RV-Android system has a unified and extensible architecture for LLM integration that eliminates code duplication, simplifies maintenance, and provides consistent behavior across all AI-driven testing operations.