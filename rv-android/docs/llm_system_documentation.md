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

## 1. Introduction

### 1.1 LLM Integration Overview

The RV-Android system uses a sophisticated and consolidated architecture for integrating Large Language Models (LLMs) into the Android application testing process. The architecture provides essential features:

1. **Externalized Templates**: XML templates with CDATA sections for easy editing without code changes
2. **Modular Information**: Fragment system that collects and formats information from different sources
3. **Flexible Strategies**: Different approaches for prompt generation as needed
4. **UI Pattern Detection**: Identification of common patterns for better test targeting
5. **Visual Analysis**: Integration of screenshot information to enrich prompts
6. **Monitored Operations**: Tracking of critical operations (formerly called "security operations")

### 1.2 Benefits of the Consolidated Architecture

The consolidated architecture offers several advantages:

1. **Elimination of Duplication**: All prompt formatting code is centralized
2. **Improved Maintainability**: XML templates are easily editable
3. **Extensibility**: Easy addition of new fragments and strategies
4. **Multimodal Integration**: Combination of textual and visual information
5. **Consistent Configuration**: Standardized configuration parameters
6. **Scalability**: Layered architecture for sustainable growth
7. **Modular Templates**: Template inheritance and fragment inclusion for reusability

### 1.3 Terminology and Concepts

Key concepts in the architecture:

1. **Information Fragment**: Modular component that generates a specific part of a prompt
2. **Information Manager**: Coordinates composition and prioritization of fragments
3. **Prompt Template**: Defines the structure of a prompt with support for variables and conditionals
4. **Template Repository**: Manages externalized templates in XML files
5. **Template Fragments**: Reusable pieces of prompt content that can be included in multiple templates
6. **Prompt Strategy**: Defines how prompts are generated for specific scenarios
7. **Strategy Registry**: Coordinates available strategies and their usage
8. **Unified Framework**: Facade that integrates all layers of the system

## 2. Consolidated Architecture

### 2.1 Three-Layer Architecture

The new LLM integration architecture follows a three-layer design with clear separation of responsibilities:

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
│ │ XMLTemplate        │  │ XMLTemplateRepo    │  │ XML Templates  │  │
│ │                    │  │                    │  │ with CDATA     │  │
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
   - Manages templates stored in external XML files with CDATA sections
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
    
    def compose_information(
        self, 
        state: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None,
        requested_fragments: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Compose information from all relevant fragments."""
        # Get fragments ordered by priority
        # Collect information from each fragment
        # Combine all information into a single dictionary
```

## 4. Template Layer

### 4.1 XML Templates

The `XMLTemplate` class manages variable substitution and rendering:

```python
class XMLTemplate:
    """Template for generating prompt messages with variable substitution."""
    
    # Regex patterns for template syntax parsing
    VARIABLE_PATTERN = r"\{([a-zA-Z0-9_\.]+)(?:\|([a-zA-Z0-9_]+))?\}"
    CONDITIONAL_START_PATTERN = r"\{#if ([a-zA-Z0-9_\.]+)\}"
    CONDITIONAL_END_PATTERN = r"\{#endif\}"
    ITERATION_START_PATTERN = r"\{#for ([a-zA-Z0-9_\.]+) as ([a-zA-Z0-9_]+)\}"
    ITERATION_END_PATTERN = r"\{#endfor\}"
    INCLUDE_PATTERN = r"\{#include ([a-zA-Z0-9_]+)\}"
    
    def __init__(
        self, 
        template_text: str,
        name: str,
        required_variables: Optional[List[str]] = None,
        transformers: Optional[Dict[str, Callable[[Any], str]]] = None
    ):
        """Initialize an XML template."""
        self.template_text = template_text
        self.name = name
        self.required_variables = set(required_variables or [])
        self.transformers = transformers or {}
        # Logging and error handling configuration
        # Extraction of variables from the template
    
    def render(self, data: Dict[str, Any]) -> str:
        """Render the template with the given data."""
        try:
            # Check required variables
            # Process include directives
            # Process conditional sections
            # Process iteration sections
            # Substitute variables
            # Return the rendered template
        except Exception as e:
            # error handling
            return self.template_text  # Return the original template as fallback
```

### 4.2 XML Template Repository

The `XMLTemplateRepository` manages externalized XML templates:

```python
class XMLTemplateRepository:
    """Repository for managing XML prompt templates."""
    
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
        self.template_objects: Dict[str, XMLTemplate] = {}
        self.fragments: Dict[str, str] = {}
        
        # Load templates and fragments
        self._load_templates()
        self._load_fragments()
    
    def configure(self, config: ComponentConfigurator) -> None:
        """Configure the template repository with the given configuration."""
        # Check if custom directories are specified
    
    def _load_templates(self) -> None:
        """Load templates from XML files in the template directory."""
        # Load all XML template files
        # Create template objects for each role (system, user, assistant)
    
    def _load_fragments(self) -> None:
        """Load fragments from XML files in the fragment directory."""
        # Load fragments from fragment directory and subdirectories
    
    def _create_default_templates(self) -> None:
        """Create default templates if the template directory is empty."""
        # Create default templates for exploration, feedback, etc.
    
    def get_template(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a template by name."""
        return self.templates.get(name)
    
    def get_template_object(self, name: str, role: str) -> Optional[XMLTemplate]:
        """Get a template object by name and role."""
        template_key = f"{name}.{role}"
        return self.template_objects.get(template_key)
    
    def get_fragment(self, name: str) -> Optional[str]:
        """Get a fragment by name."""
        return self.fragments.get(name)
    
    def update_template(self, name: str, template_data: Dict[str, Any]) -> None:
        """Update or create a template."""
        # Save template data
        # Create template objects for each role
        # Write the template to a file
    
    def create_messages(
        self, 
        template_name: str, 
        variables: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """Create a list of messages using the specified template."""
        # Get the template
        # Create messages for each role in the template
        # Render the content with fragment inclusion
        # Return formatted message list
```

### 4.3 XML Template Examples

Templates are stored in XML files with CDATA sections for easy editing. Example:

```xml
<template name="standard">
  <s><![CDATA[
You are an Android testing assistant. Your task is to help test the Android application by identifying UI elements and suggesting testing actions.

The current screen contains the following UI elements:
{screen_description}

{#if ui_patterns}I've identified the following UI patterns:
{ui_patterns}

{#endif}{#if monitored_operations}Pay attention to monitored operations:
{monitored_operations.summary}

{#endif}
  ]]></s>
  <user><![CDATA[
Based on the current screen, suggest ONE testing action that would help explore the application functionality and potentially trigger monitored operations.{#if additional_guidelines}

{additional_guidelines}{#endif}
  ]]></user>
  <required_variables>
    <variable>screen_description</variable>
  </required_variables>
  <metadata>
    <max_tokens>300</max_tokens>
  </metadata>
</template>
```

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
        template_repository: Optional[XMLTemplateRepository] = None
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
    ) -> List[MCPMessage]:
        """Generate an MCP prompt for the given state and context."""
        # Convert standard prompt to MCP format
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
        template_repository: Optional[XMLTemplateRepository] = None
    ):
        """Initialize the standard strategy."""
        super().__init__(name, information_manager, template_repository)
    
    def generate_prompt(
        self, 
        state: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """Generate a prompt for the given state and context."""
        # Determine which template to use based on context
        # Get information from fragments
        # Combine information with context
        # Generate messages from the template
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
        template_repository: Optional[XMLTemplateRepository] = None,
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
        # Always use the batch_action template
        # Get information from fragments
        # Extract test history from context
        # Add specific guidelines for batches
        # Generate messages from the template
        
    def should_use_batch(self, state: Dict[str, Any]) -> bool:
        """Determine if batch action strategy should be used for this state."""
        # Check if UI patterns are detected that benefit from batch actions
        # Check if state has complex form or multi-step workflow
```

### 5.3 Strategy Registry

The `StrategyRegistry` manages available strategies:

```python
class StrategyRegistry:
    """Registry for prompt generation strategies."""
    
    def __init__(self):
        """Initialize the strategy registry."""
        self.strategies: Dict[str, PromptStrategy] = {}
        self.default_strategy: Optional[str] = None
        self.logger = # logger configuration
        self.error_handler = ErrorHandler.get_instance()
    
    def configure(self, config: ComponentConfigurator) -> None:
        """Configure the strategy registry with the given configuration."""
        # Configure registered strategies
        # Set default strategy if specified
    
    def register_strategy(self, strategy: PromptStrategy) -> None:
        """Register a prompt generation strategy."""
        self.strategies[strategy.name] = strategy
        # If this is the first strategy, set it as default
    
    def get_strategy(self, name: Optional[str] = None) -> Optional[PromptStrategy]:
        """Get a registered strategy by name."""
        # Return strategy by name or the default strategy
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
        template_repository: XMLTemplateRepository,
        strategy_registry: StrategyRegistry,
        model: Optional[LanguageModel] = None
    ):
        """Initialize the prompt framework."""
        self.information_manager = information_manager
        self.template_repository = template_repository
        self.strategy_registry = strategy_registry
        self.model = model
        self.logger = # logger configuration
        self.error_handler = ErrorHandler.get_instance()
    
    @classmethod
    def create(cls, config: Optional[ComponentConfigurator] = None) -> 'PromptFramework':
        """Create and configure a new prompt framework."""
        # Create and configure components
        # Register default fragments and strategies
        pass
    
    def generate_prompt(
        self, 
        strategy_name: Optional[str], 
        state: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        """Generate a prompt using the specified strategy."""
        # Implementation for generating prompts
        pass
    
    def generate_with_llm(
        self, 
        strategy_name: Optional[str], 
        state: Dict[str, Any], 
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """Generate a prompt and send it to the LLM for a response."""
        # Implementation for LLM interaction
        pass
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
```

## 8. Usage Examples

### 8.1 Basic Framework Usage

```python
from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.llm.prompt.framework import PromptFramework
from rvandroid.llm.constants import StateEntry, PromptStrategyType

# Criar configuração
config = ComponentConfigurator()
config.set_llm(
    llm_type="ollama",
    model="llama3",
    temperature=0.3,
    max_tokens=800,
    base_url="http://localhost:11434"
)

# Criar e inicializar o framework
framework = PromptFramework.create(config)

# Criar estado de teste
state = {
    StateEntry.PACKAGE_NAME: "com.example.testapp",
    StateEntry.ACTIVITY: "com.example.testapp.MainActivity",
    StateEntry.SCREEN_DESCRIPTION: "The screen shows a login form with username and password fields, and a Login button.",
    StateEntry.SCREEN_PATTERNS: {
        "title": "Login",
        "components": [
            {
                "type": "EditText",
                "text": "",
                "resource_id": "username_field",
                "hint": "Username",
                "clickable": True,
                "bounds": {"left": 50, "top": 100, "right": 300, "bottom": 150}
            },
            {
                "type": "EditText",
                "text": "",
                "resource_id": "password_field",
                "hint": "Password",
                "clickable": True,
                "bounds": {"left": 50, "top": 200, "right": 300, "bottom": 250}
            },
            {
                "type": "Button",
                "text": "Login",
                "resource_id": "login_button",
                "clickable": True,
                "bounds": {"left": 50, "top": 300, "right": 300, "bottom": 350}
            }
        ]
    }
}

# Definir contexto adicional
context = {
    "additional_guidelines": "Focus on testing the login functionality."
}

# Gerar prompt usando estratégia padrão
messages = framework.generate_prompt(PromptStrategyType.STANDARD, state, context)

# Enviar para LLM e obter resposta
response = framework.generate_with_llm(PromptStrategyType.STANDARD, state, context)
print(f"LLM Response: {response.get_text_content() if hasattr(response, 'get_text_content') else response}")
```

### 8.2 Custom Fragments

```python
from rvandroid.llm.prompt.information.base_fragment import InformationFragment
from rvandroid.llm.prompt.framework import PromptFramework
from rvandroid.llm.constants import StateEntry, PromptStrategyType
from typing import Dict, Any, Optional

# Criar fragmento personalizado
class CustomFragment(InformationFragment):
    """Custom information fragment."""
    
    def __init__(self, name: str = "custom_info", priority: int = 100):
        super().__init__(name, priority)
    
    def generate(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        # Extrair informações personalizadas do estado
        package_name = state.get(StateEntry.PACKAGE_NAME, "unknown")
        activity = state.get(StateEntry.ACTIVITY, "unknown")
        
        return f"Testing app: {package_name}\nCurrent activity: {activity}\nAdditional custom information to include in prompts."
    
    def should_include(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> bool:
        # Incluir apenas se o estado tiver dados do pacote
        return StateEntry.PACKAGE_NAME in state

# Criar framework
framework = PromptFramework.create()

# Registrar fragmento personalizado
framework.register_information_fragment(CustomFragment())

# Usar o framework com o fragmento personalizado
messages = framework.generate_prompt(PromptStrategyType.STANDARD, state, context)
```

### 8.3 Using with LLMActionService

```python
from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.llm.service.action_service import LLMActionService
from rvandroid.llm.constants import StateEntry

# Criar configuração
config = ComponentConfigurator()
config.set_llm(
    llm_type="ollama",
    model="llama3",
    temperature=0.3,
    max_tokens=800,
    base_url="http://localhost:11434"
)

# Criar serviço de ação
service = LLMActionService(config=config)

# Processar estado e gerar ações
state = {
    StateEntry.PACKAGE_NAME: "com.example.testapp",
    StateEntry.ACTIVITY: "com.example.testapp.MainActivity",
    StateEntry.SCREEN_DESCRIPTION: "The screen shows a login form with username and password fields, and a Login button.",
    StateEntry.SCREENSHOT_PATH: "/path/to/screenshot.png",
    StateEntry.SCREEN_PATTERNS: {
        "title": "Login",
        "components": [
            # UI components as before
        ]
    }
}

actions = service.process_state(state)
for action in actions:
    print(f"Action: {action}")
```

### 8.4 Using with LLMConsultationManager

```python
from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.rvdroid.core.llm_consultation_manager import LLMConsultationManager

# Criar configuração
config = {
    "static_data": static_data,
    "memory_system": memory_system,
    "use_llm": True
}

# Configurar modelo Ollama para o consultation manager 
# (A configuração será usada pelo PromptFramework criado internamente)
component_config = ComponentConfigurator(static_data=static_data)
component_config.set_llm(
    llm_type="ollama",
    model="llama3",
    temperature=0.3,
    max_tokens=800,
    base_url="http://localhost:11434"
)

# Adicionar a configuração de componente na configuração do consultation manager
config["component_configurator"] = component_config

# Criar consultation manager
consultation_manager = LLMConsultationManager(config)
consultation_manager.initialize()
consultation_manager.start()

# Obter orientação estratégica
```

### 8.5 Using Custom Template with Fragments

```python
from rvandroid.llm.prompt.framework import PromptFramework
from rvandroid.llm.constants import StateEntry, PromptStrategyType

# Create a custom template file with fragment inclusion
custom_template_content = """<?xml version="1.0" encoding="UTF-8"?>
<template name="security_template" version="1.0" extends="system_base">
  <metadata>
    <description>Template for security testing</description>
    <created>2025-04-18</created>
    <author>RV-Android Team</author>
  </metadata>
  <variables>
    <required>screen_elements</required>
    <optional>data_usage</optional>
  </variables>
  <roles>
    <s>
      <variable name="strategy_specific_instructions">
        <![CDATA[
Your task is to analyze the current state for potential security vulnerabilities.

{#include security_testing_guidelines}
        ]]>
      </variable>
      <variable name="response_format_instructions">
        <![CDATA[
{#include standard_format}
        ]]>
      </variable>
    </s>
    <user><![CDATA[
Current Activity: {activity}

{#if data_usage}{data_usage}

{#endif}Current UI Elements:
{screen_elements}

Your task is to identify the single most critical security test for this screen.
    ]]></user>
  </roles>
</template>
"""

# In a real example, you would write this to a file
# Here we'll just create a framework with our custom fragment

# Register the custom fragment and template
framework = PromptFramework.create()

# Use the framework with our custom template
state = {
    StateEntry.PACKAGE_NAME: "com.example.bankapp",
    StateEntry.ACTIVITY: "com.example.bankapp.LoginActivity",
    StateEntry.SCREEN_DESCRIPTION: "Login screen with username and password fields.",
}

context = {
    "template": "security_template",  # This would normally select our custom template
}

# Generate messages
messages = framework.generate_prompt(PromptStrategyType.STANDARD, state, context)
```

## 9. System Extension

### 9.1 Creating New Fragments

Para criar um novo fragment de informação:

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
        # Obter informações atuais do app
        package_name = state.get(StateEntry.PACKAGE_NAME, "unknown")
        activity = state.get(StateEntry.ACTIVITY, "unknown")
        
        # Formatar texto do histórico
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
        # Manter histórico em tamanho razoável
        if len(self.action_history) > 20:
            self.action_history = self.action_history[-20:]
    
    def should_include(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> bool:
        # Incluir apenas se tivermos algum histórico
        return len(self.action_history) > 0
```

### 9.2 Creating New Strategies

Para criar uma nova estratégia de prompt:

```python
from rvandroid.llm.prompt.strategy.base_strategy import PromptStrategy
from rvandroid.llm.constants import PromptStrategyType
from rvandroid.llm.prompt.information.fragment_manager import InformationManager
from rvandroid.llm.prompt.template.xml_repository import XMLTemplateRepository
from typing import Dict, Any, Optional, List

class ExplorationStrategy(PromptStrategy):
    """Strategy focused on exploration breadth."""
    
    DEFAULT_TEMPLATE = "exploration"
    
    def __init__(
        self,
        name: str = "exploration",
        information_manager: Optional[InformationManager] = None,
        template_repository: Optional[XMLTemplateRepository] = None
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
            # Usar template de exploração
            template_name = self.get_template_name(context) or self.DEFAULT_TEMPLATE
            
            # Obter informações com fragments padrão
            info = {}
            if self.information_manager:
                info = self.information_manager.compose_information(state, context)
            
            # Adicionar diretrizes de exploração
            if "additional_guidelines" not in context:
                context["additional_guidelines"] = (
                    "Focus on exploring new screens and UI elements that haven't been visited before. "
                    "Prioritize breadth of exploration rather than depth."
                )
            
            # Gerar mensagens a partir do template
            variables = {**info, **context}
            
            if self.template_repository:
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

### 9.3 Creating New XML Templates

Para criar um novo template XML:

```python
import os
from rvandroid.llm.prompt.template.xml_utils import create_template_xml_string

# Criar conteúdo do template
template_content = create_template_xml_string(
    name="exploration",
    version="1.0",
    description="Template for exploration-focused prompts",
    author="RV-Android Team",
    created="2025-04-18",
    required_vars=["screen_description"],
    optional_vars=["ui_patterns", "history", "additional_guidelines"],
    system_content="""
You are an Android exploration assistant. Your job is to discover new screens and functionality in the app.

The current screen contains:
${screen_description}

${#if ui_patterns}I've identified these UI patterns:
${ui_patterns}

${#endif}${#if history}Previous actions:
${history}

${#endif}
""",
    user_content="""
Suggest ONE action that would help explore a new part of this application that hasn't been seen before.${#if additional_guidelines}

${additional_guidelines}${#endif}
"""
)

# Escrever em arquivo de template
template_dir = "/path/to/templates"
os.makedirs(template_dir, exist_ok=True)
with open(os.path.join(template_dir, "exploration.xml"), "w") as f:
    f.write(template_content)

# Carregar no repositório de templates
from rvandroid.llm.prompt.template.xml_repository import XMLTemplateRepository
repository = XMLTemplateRepository(template_dir)
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
    <required>screen_elements</required>
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
Current Activity: {activity}

{static_context}

Current UI Elements and Available Actions:
{ui_elements}

{#if action_history}{action_history}

{#endif}SUMMARY: You are testing the {activity} screen. Select ONE action from the available options above that would be most effective for testing this screen. Remember to return your answer as a JSON object using the action_id values provided.{#if additional_guidelines}

{additional_guidelines}{#endif}
    ]]></user>
  </roles>
</template>
```

### 10.2 Template Fragments

The system uses template fragments to create reusable pieces of prompt content:

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

These fragments can be included in templates using the `{#include fragment_name}` directive:

```xml
<template name="batch_action_modular" version="1.0" extends="system_base">
  <metadata>
    <description>Template for generating batches of testing actions (modular version)</description>
    <created>2025-04-18</created>
    <author>RV-Android Team</author>
  </metadata>
  <variables>
    <required>screen_elements</required>
    <optional>additional_guidelines</optional>
    <optional>ui_patterns</optional>
    <optional>monitored_operations</optional>
    <optional>testing_history</optional>
  </variables>
  <roles>
    <s>
      <variable name="strategy_specific_instructions">
        <![CDATA[
{#include batch_instructions}
        ]]>
      </variable>
      <variable name="response_format_instructions">
        <![CDATA[
{#include batch_format}
        ]]>
      </variable>
      <variable name="additional_guidelines">
        <![CDATA[
{#include batch_guidelines}
        ]]>
      </variable>
    </s>
    <user><![CDATA[
{#include user_base}
{#include batch_ui_pattern_detection}
{#if workflow_guidance}{workflow_guidance}

{#endif}{#include batch_critical_task}{#if additional_guidelines}

{additional_guidelines}{#endif}
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

### 10.4 Template Processor Implementation

The template processor implements fragment inclusion as part of the rendering process:

```python
def _process_includes(self, template: str, fragments: Dict[str, str]) -> str:
    """
    Process fragment includes in the template.
    
    Args:
        template: The template text
        fragments: Dictionary of fragment name to fragment content
        
    Returns:
        Template with includes resolved
    """
    include_pattern = r"\{#include ([a-zA-Z0-9_]+)\}"
    
    while True:
        match = re.search(include_pattern, template)
        if not match:
            break
            
        fragment_name = match.group(1)
        fragment_content = fragments.get(fragment_name)
        
        if fragment_content:
            template = template.replace(match.group(0), fragment_content)
        else:
            self.logger.warning(f"Fragment not found: {fragment_name}")
            template = template.replace(match.group(0), "")
    
    return template
```

This approach enables highly modular templates with efficient reuse of prompt components, making the system more maintainable and consistent.

Com esses componentes implementados, o sistema RV-Android possui uma arquitetura unificada e extensível para integração com LLM que elimina duplicação de código, simplifica a manutenção e proporciona comportamento consistente em todas as operações de teste baseadas em IA.