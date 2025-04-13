# Model Context Protocol (MCP) in RV-Android

This document provides comprehensive documentation of the Model Context Protocol (MCP) integration within the RV-Android platform, detailing its architecture, components, and usage patterns.

## Table of Contents

1. [Introduction](#1-introduction)
2. [Architecture Overview](#2-architecture-overview)
3. [Core Components](#3-core-components)
4. [Model Adapters](#4-model-adapters)
5. [Template System](#5-template-system)
6. [Prompt Strategies](#6-prompt-strategies)
7. [Integration with Test Framework](#7-integration-with-test-framework)
8. [Usage Examples](#8-usage-examples)
9. [Extending the System](#9-extending-the-system)
10. [Troubleshooting](#10-troubleshooting)

## 1. Introduction

### 1.1 What is Model Context Protocol (MCP)?

The Model Context Protocol (MCP) is a standardized interface for interacting with Large Language Models (LLMs) in the RV-Android system. It provides a unified approach to message representation, formatting, and exchange across different LLM providers, ensuring consistency and modularity.

MCP addresses several critical challenges in LLM integration:

1. **Standardized Message Format**: Provides a consistent message structure across all LLM providers
2. **Model-Agnostic Communication**: Abstracts away provider-specific message formats
3. **Structured Template System**: Enables type-safe template generation and composition
4. **Adapter-Based Design**: Facilitates easy integration of new LLM providers
5. **Centralized Configuration**: Unifies configuration across different models

### 1.2 Benefits of Using MCP

The adoption of MCP in RV-Android offers several significant benefits:

1. **Reduced Duplication**: Eliminates duplicated format handling code across model implementations
2. **Enhanced Maintainability**: Centralizes message formatting logic in adapters
3. **Improved Extensibility**: Simplifies adding support for new LLM providers
4. **Type Safety**: Provides structured data types for messages and content
5. **Versioned Templates**: Enables systematic template management and evolution
6. **Consistent Configuration**: Standardizes configuration parameters across models

### 1.3 Limitations and Considerations

While MCP provides significant advantages, it's important to be aware of its limitations:

1. **Additional Layer of Abstraction**: Introduces a translation layer between application code and LLM APIs
2. **Potential Performance Overhead**: The adapter conversion process adds some computational overhead
3. **Least Common Denominator Effect**: The standardized interface may not expose all provider-specific features
4. **Learning Curve**: Requires understanding the MCP structures and adapter system

### 1.4 MCP in the Context of Monitored Operations

The MCP implementation in RV-Android is designed to support the system's approach of using different specification sets in separate experiments, particularly for testing:

1. **Cryptography-related specifications**: Detecting misuse of Java Cryptography Architecture (JCA)
2. **General programming specifications**: Enforcing proper API usage patterns (like Iterator hasNext/next validation)

Throughout the MCP system, we use the term "monitored operations" to refer to operations being tracked by any specification, without assuming a security-specific context.

## 2. Architecture Overview

### 2.1 High-Level Architecture

The MCP architecture follows a clean layered design with clear separation of concerns:

```
┌───────────────────────────────────────────────────────────┐
│                     Application Layer                     │
│ ┌─────────────────┐ ┌─────────────────┐ ┌───────────────┐ │
│ │  Prompt Strategy │ │  Test Framework │ │    RV Tools   │ │
│ └─────────────────┘ └─────────────────┘ └───────────────┘ │
└───────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼───────────────────────────────┐
│                        MCP Layer                          │
│ ┌─────────────────┐ ┌─────────────────┐ ┌───────────────┐ │
│ │  Data Structures│ │ Template System │ │Language Model │ │
│ └─────────────────┘ └─────────────────┘ └───────────────┘ │
└───────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼───────────────────────────────┐
│                      Adapter Layer                        │
│ ┌─────────────────┐ ┌─────────────────┐ ┌───────────────┐ │
│ │  Ollama Adapter │ │  DSPy Adapter   │ │ Other Adapters│ │
│ └─────────────────┘ └─────────────────┘ └───────────────┘ │
└───────────────────────────────────────────────────────────┘
                            │
┌───────────────────────────▼───────────────────────────────┐
│                      Provider Layer                       │
│ ┌─────────────────┐ ┌─────────────────┐ ┌───────────────┐ │
│ │  Ollama Models  │ │  HuggingFace    │ │ Frontier LLMs │ │
│ └─────────────────┘ └─────────────────┘ └───────────────┘ │
└───────────────────────────────────────────────────────────┘
```

### 2.2 Key Components and Relations

The MCP system is composed of several interconnected components:

1. **Core Data Structures** (`data_structures.py`):
   - Defines fundamental message and content representations
   - Provides the structural foundation for the entire protocol

2. **Adapter System** (`adapter.py`, `adapters/`):
   - Defines the adapter interface for model-specific conversions
   - Implements concrete adapters for each supported LLM provider

3. **Language Model Interface** (`language_model.py`):
   - Provides a standardized interface for all LLM implementations
   - Utilizes adapters for format conversion

4. **Template System** (`templates/`):
   - Implements a structured, type-safe template system
   - Supports versioning, inheritance, and composition

5. **Model Factory** (`model_factory.py`):
   - Creates model instances based on configuration
   - Handles model registration and discovery

The relationship between these components is hierarchical and well-defined:

- Application code interacts primarily with the Language Model interface
- Language Model implementations use Adapters for format conversion
- Adapters convert between MCP structures and provider-specific formats
- Templates generate structured MCP messages
- Data Structures provide the foundational types for all components

### 2.3 Design Patterns

The MCP implementation leverages several design patterns:

1. **Adapter Pattern**: Core to the model-specific format conversion
2. **Factory Pattern**: Used in model instantiation and configuration
3. **Strategy Pattern**: Applied in different template strategies
4. **Decorator Pattern**: Employed for message enrichment
5. **Builder Pattern**: Used in message and content construction
6. **Repository Pattern**: Applied in template management

## 3. Core Components

### 3.1 MCP Data Structures

The foundation of the MCP system is a set of standardized data structures defined in `data_structures.py`:

```python
from enum import Enum
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass

class MCPRole(Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"
    
@dataclass
class MCPTextContent:
    text: str
    
@dataclass
class MCPImageContent:
    url: str
    detail: Optional[str] = "auto"
    
MCPContentType = Union[MCPTextContent, MCPImageContent]

@dataclass
class MCPMessage:
    role: MCPRole
    content: List[MCPContentType]
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    
@dataclass
class MCPConfiguration:
    model_name: str
    model_type: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop: Optional[List[str]] = None
```

Key features of the data structures:

1. **Role Enumeration**: Standardizes message roles (system, user, assistant, tool)
2. **Content Types**: Supports both text and image content
3. **Structured Messages**: Provides a consistent message format with optional attributes
4. **Configuration Parameters**: Standardizes model configuration options

### 3.2 Creating and Using MCP Messages

Working with MCP messages is straightforward:

```python
# Create text content
system_content = MCPTextContent(
    text="You are an AI assistant helping to test Android applications."
)

# Create a system message
system_message = MCPMessage(
    role=MCPRole.SYSTEM,
    content=[system_content]
)

# Create user content with both text and image
user_text = MCPTextContent(
    text="Analyze this screen and suggest possible actions."
)
user_image = MCPImageContent(
    url="file:///path/to/screenshot.png"
)

# Create a user message with mixed content
user_message = MCPMessage(
    role=MCPRole.USER,
    content=[user_text, user_image]
)

# Create a conversation
messages = [system_message, user_message]

# Create model configuration
config = MCPConfiguration(
    model_name="llama3.2",
    model_type="ollama",
    temperature=0.3,
    max_tokens=800
)
```

### 3.3 The MCP Adapter Interface

The `MCPAdapter` interface defines the contract for model-specific adapters:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List

class MCPAdapter(ABC):
    @abstractmethod
    def prepare_messages(self, messages: List[MCPMessage]) -> Dict[str, Any]:
        """Convert MCP messages to model-specific format"""
        pass
    
    @abstractmethod
    def prepare_config(self, config: MCPConfiguration) -> Dict[str, Any]:
        """Convert MCP configuration to model-specific parameters"""
        pass
    
    @abstractmethod
    def parse_response(self, response: Any) -> MCPMessage:
        """Parse model response into MCP message"""
        pass
    
    @abstractmethod
    def validate_request(self, messages: List[MCPMessage], config: MCPConfiguration) -> bool:
        """Validate that messages and config are compatible with this adapter"""
        pass
```

The adapter interface ensures that:
1. MCP messages can be converted to model-specific formats
2. Configuration parameters are properly mapped
3. Model responses are converted back to MCP format
4. Request compatibility is validated before submission

### 3.4 Language Model Interface

The `LanguageModel` abstract base class defines the standard interface for all LLM implementations:

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Type, ClassVar

class LanguageModel(ABC):
    """
    Base class for language model implementations using the Model Context Protocol.
    """

    def __init__(self, model_name: str, **kwargs):
        """
        Initialize language model.
        """
        self.model_name = model_name
        self.adapter = self._get_adapter()
        self.config = MCPConfiguration(
            model_name=model_name,
            model_type=self._get_model_type()
        )

        # Update config with kwargs
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)

        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    def _get_model_type(self) -> str:
        """Get model type string."""
        pass

    @abstractmethod
    def _get_adapter(self) -> MCPAdapter:
        """Get the appropriate MCP adapter for this model."""
        pass

    @abstractmethod
    async def generate(self,
                      messages: List[MCPMessage],
                      config: Optional[MCPConfiguration] = None) -> MCPMessage:
        """Generate a response using the language model."""
        pass

    @abstractmethod
    def generate_sync(self,
                     messages: List[MCPMessage],
                     config: Optional[MCPConfiguration] = None) -> MCPMessage:
        """Generate a response synchronously."""
        pass
        
    @classmethod
    def models(cls) -> List[str]:
        """
        Get a list of available models for this type.
        """
        # Default implementation - subclasses should override
        return getattr(cls, "MODELS", [])
```

This interface ensures that:
1. All model implementations follow a consistent pattern
2. Both synchronous and asynchronous generation is supported
3. Model-specific adapters are properly utilized
4. Configuration is handled uniformly
5. Models can report their available variants

## 4. Model Adapters

### 4.1 Adapter System Overview

The adapter system is responsible for translating between MCP's standardized structures and model-specific formats. Each adapter handles the conversion for a particular LLM provider.

```
┌─────────────────┐      ┌──────────────┐     ┌─────────────────┐
│                 │      │              │     │                 │
│  MCP Structures ├─────►│ MCP Adapter  ├────►│ Provider Format │
│                 │      │              │     │                 │
└─────────────────┘      └──────────────┘     └─────────────────┘
        ▲                       │                     │
        │                       │                     │
        │                       ▼                     ▼
┌─────────────────┐      ┌──────────────┐     ┌─────────────────┐
│                 │      │              │     │                 │
│  MCP Message    │◄─────┤ Parse        │◄────┤ Provider Response│
│                 │      │ Response     │     │                 │
└─────────────────┘      └──────────────┘     └─────────────────┘
```

### 4.2 Ollama Adapter Implementation

Here's an example of a concrete adapter implementation for Ollama:

```python
from typing import Dict, Any, List
import logging
from rvandroid.llm.adapter import MCPAdapter
from rvandroid.llm.data_structures import MCPMessage, MCPRole, MCPTextContent, MCPConfiguration

class OllamaAdapter(MCPAdapter):
    """
    Adapter for converting between MCP format and Ollama API format.
    """
    
    def __init__(self):
        """Initialize the Ollama adapter."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def prepare_messages(self, messages: List[MCPMessage]) -> Dict[str, Any]:
        """
        Convert MCP messages to Ollama format.
        
        Args:
            messages: List of MCP messages
            
        Returns:
            Dictionary with Ollama-specific message format
        """
        ollama_messages = []
        
        for message in messages:
            # Extract text content from message
            text_content = ""
            for content_item in message.content:
                if isinstance(content_item, MCPTextContent):
                    text_content += content_item.text
            
            # Map MCP role to Ollama role
            role = message.role.value
            
            # Create Ollama message
            ollama_message = {
                "role": role,
                "content": text_content
            }
            
            # Add name if present
            if message.name:
                ollama_message["name"] = message.name
                
            ollama_messages.append(ollama_message)
        
        return {"messages": ollama_messages}
    
    def prepare_config(self, config: MCPConfiguration) -> Dict[str, Any]:
        """
        Convert MCP configuration to Ollama parameters.
        
        Args:
            config: MCP configuration
            
        Returns:
            Dictionary with Ollama-specific parameters
        """
        ollama_config = {
            "model": config.model_name,
            "temperature": config.temperature,
            "top_p": config.top_p
        }
        
        # Add optional parameters if present
        if config.max_tokens:
            ollama_config["num_predict"] = config.max_tokens
        
        if config.stop:
            ollama_config["stop"] = config.stop
            
        return ollama_config
    
    def parse_response(self, response: Dict[str, Any]) -> MCPMessage:
        """
        Parse Ollama response into MCP message.
        
        Args:
            response: Ollama response dictionary
            
        Returns:
            MCPMessage containing the response
        """
        try:
            # Extract response content
            content_text = response.get("response", "")
            
            # Create MCP message
            return MCPMessage(
                role=MCPRole.ASSISTANT,
                content=[MCPTextContent(text=content_text)]
            )
        except Exception as e:
            self.logger.error(f"Error parsing Ollama response: {e}")
            # Return empty message on error
            return MCPMessage(
                role=MCPRole.ASSISTANT,
                content=[MCPTextContent(text="")]
            )
    
    def validate_request(self, messages: List[MCPMessage], config: MCPConfiguration) -> bool:
        """
        Validate that messages and config are compatible with Ollama.
        
        Args:
            messages: List of MCP messages
            config: MCP configuration
            
        Returns:
            True if the request is valid for Ollama
        """
        # Check if model name is valid
        if not config.model_name:
            self.logger.error("Model name is required for Ollama")
            return False
        
        # Check if messages are valid
        if not messages:
            self.logger.error("At least one message is required")
            return False
        
        # Ollama doesn't support image content
        for message in messages:
            for content in message.content:
                if not isinstance(content, MCPTextContent):
                    self.logger.warning("Ollama adapter will ignore non-text content")
        
        return True
```

### 4.3 DSPy Adapter Implementation

The adapter for DSPy demonstrates a different integration approach:

```python
from typing import Dict, Any, List
import logging
from rvandroid.llm.adapter import MCPAdapter
from rvandroid.llm.data_structures import MCPMessage, MCPRole, MCPTextContent, MCPConfiguration

class DSPyAdapter(MCPAdapter):
    """
    Adapter for converting between MCP format and DSPy format.
    """
    
    def __init__(self):
        """Initialize the DSPy adapter."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def prepare_messages(self, messages: List[MCPMessage]) -> Dict[str, Any]:
        """
        Convert MCP messages to DSPy format.
        
        Args:
            messages: List of MCP messages
            
        Returns:
            Dictionary with DSPy-specific message format
        """
        # DSPy doesn't use a standard chat format but expects a single prompt
        # We'll concatenate everything into a single prompt text
        prompt_text = ""
        
        for message in messages:
            # Add role prefix
            role_prefix = f"{message.role.value.upper()}: "
            
            # Extract text content
            message_text = ""
            for content_item in message.content:
                if isinstance(content_item, MCPTextContent):
                    message_text += content_item.text
            
            # Add to prompt
            prompt_text += f"{role_prefix}{message_text}\n\n"
        
        # Add final assistant prompt
        prompt_text += "ASSISTANT: "
        
        return {"prompt": prompt_text}
    
    def prepare_config(self, config: MCPConfiguration) -> Dict[str, Any]:
        """
        Convert MCP configuration to DSPy parameters.
        
        Args:
            config: MCP configuration
            
        Returns:
            Dictionary with DSPy-specific parameters
        """
        dspy_config = {
            "temperature": config.temperature,
            "top_p": config.top_p
        }
        
        # Add optional parameters if present
        if config.max_tokens:
            dspy_config["max_tokens"] = config.max_tokens
        
        return dspy_config
    
    def parse_response(self, response: str) -> MCPMessage:
        """
        Parse DSPy response into MCP message.
        
        Args:
            response: DSPy response text
            
        Returns:
            MCPMessage containing the response
        """
        try:
            # DSPy returns raw text
            return MCPMessage(
                role=MCPRole.ASSISTANT,
                content=[MCPTextContent(text=response)]
            )
        except Exception as e:
            self.logger.error(f"Error parsing DSPy response: {e}")
            # Return empty message on error
            return MCPMessage(
                role=MCPRole.ASSISTANT,
                content=[MCPTextContent(text="")]
            )
    
    def validate_request(self, messages: List[MCPMessage], config: MCPConfiguration) -> bool:
        """
        Validate that messages and config are compatible with DSPy.
        
        Args:
            messages: List of MCP messages
            config: MCP configuration
            
        Returns:
            True if the request is valid for DSPy
        """
        # Check if messages are valid
        if not messages:
            self.logger.error("At least one message is required")
            return False
        
        # DSPy doesn't support image content
        for message in messages:
            for content in message.content:
                if not isinstance(content, MCPTextContent):
                    self.logger.warning("DSPy adapter will ignore non-text content")
        
        return True
```

### 4.4 Implementing Other Adapters

The MCP system in RV-Android includes adapters for multiple LLM providers:

1. **Ollama**: Local models through Ollama API
2. **DSPy**: DSPy-compatible models
3. **HuggingFace**: Models from the Hugging Face ecosystem
4. **Frontier**: Models from commercial providers like OpenAI and Anthropic
5. **Langchain**: Models accessed through the Langchain framework

Each adapter follows the same pattern but handles the specific format requirements of its provider.

### 4.5 Component Configurator and Registration

The `ComponentConfigurator` centralizes component creation and configuration:

```python
class ComponentConfigurator:
    """
    A sophisticated configuration management system for dynamically configuring 
    and composing experimental components.
    """
    
    @classmethod
    def register_llm(cls, name: str, implementation=None, module_path=None, 
                    class_name=None, metadata=None) -> None:
        """
        Register a language model implementation.

        Args:
            name: Model type name
            implementation: Implementation class (optional if module_path is provided)
            module_path: Module path for lazy loading (required if implementation is None)
            class_name: Class name for lazy loading (required if implementation is None)
            metadata: Additional metadata
        """
        registry = cls._registries['llm']
        if implementation:
            registry.register(name, implementation, metadata=metadata)
        elif module_path and class_name:
            registry.register_lazy(name, module_path, class_name, metadata=metadata)
        else:
            raise ValueError("Either implementation or module_path+class_name must be provided")
            
    def create_llm(self):
        """
        Create an LLM instance based on current configuration.

        Returns:
            LanguageModel instance

        Raises:
            ValueError: If LLM creation fails
        """
        # Get LLM implementation from registry
        llm_registry = self._registries['llm']
        model_class = llm_registry.get(self.llm_config.model_type)
        
        if not model_class:
            raise ValueError(f"Unknown model type: {self.llm_config.model_type}")
            
        # Create model instance with appropriate parameters
        return model_class(self.llm_config.model_name, **self.llm_config.kwargs)
```

## 5. Template System

### 5.1 Template System Overview

The MCP template system provides a structured approach to generating prompts:

```
┌─────────────────┐      ┌──────────────┐     ┌─────────────────┐
│                 │      │              │     │                 │
│ Template Library├─────►│ Templates    ├────►│ MCP Messages    │
│                 │      │              │     │                 │
└─────────────────┘      └──────────────┘     └─────────────────┘
        ▲                       │                     │
        │                       │                     │
        │                       ▼                     ▼
┌─────────────────┐      ┌──────────────┐     ┌─────────────────┐
│                 │      │              │     │                 │
│ Template        │      │ Fragments    │     │ Language Model  │
│ Repository      │      │              │     │                 │
└─────────────────┘      └──────────────┘     └─────────────────┘
```

Key components include:
1. **PromptTemplate**: The core template class for rendering content
2. **TemplateFragment**: Reusable components for template composition
3. **TemplateLibrary**: Central repository for template management
4. **TemplateRepository**: Storage for shared fragments

### 5.2 Template Definition and Usage

Templates are defined using a structured format and can include variables, conditionals, and fragments:

```python
from rvandroid.llm.templates.template import PromptTemplate
from rvandroid.llm.templates.library import PromptLibrary
from rvandroid.llm.data_structures import MCPRole, MCPTextContent, MCPMessage

# Define a system prompt template
system_template = PromptTemplate(
    template_text="""You are an AI assistant helping to test Android applications. Your task is to analyze the current app state and suggest the MOST EFFECTIVE NEXT ACTION to take for testing the application thoroughly.

Focus on:
1. {exploration_goal}
2. Maximizing code coverage by targeting untested UI elements
3. Prioritizing testing of methods of interest that directly or indirectly affect monitored operations
4. Testing complete workflows from start to finish

{response_format}

{#if additional_guidelines}{additional_guidelines}{#endif}""",
    name="system_base",
    version="1.0",
    required_variables=["exploration_goal", "response_format"]
)

# Register template in library
PromptLibrary.register_template(system_template, "system")

# Create a fragment for dropdown guidelines
dropdown_guidelines = PromptTemplate(
    template_text="""DROPDOWN GUIDELINES:
1. Test selecting different options from dropdowns
2. Verify the app's behavior after each selection
3. Try selecting the first, last, and a middle option""",
    name="dropdown_guidelines",
    version="1.0"
)

# Register fragment
PromptLibrary.register_template(dropdown_guidelines, "guidelines")

# Using templates to generate MCP messages
def generate_system_message(exploration_goal, additional_guidelines=None):
    # Get template from library
    template = PromptLibrary.get_template("system_base")
    
    # Prepare variables
    variables = {
        "exploration_goal": exploration_goal,
        "response_format": "RESPONSE FORMAT: JSON with 'action_id' and 'reason'",
        "additional_guidelines": additional_guidelines
    }
    
    # Render template
    rendered_text = template.render(variables)
    
    # Create MCP message
    return MCPMessage(
        role=MCPRole.SYSTEM,
        content=[MCPTextContent(text=rendered_text)]
    )
```

### 5.3 Template Inheritance and Versioning

Templates support inheritance and versioning to enable easy specialization:

```python
# Get base template
base_template = PromptLibrary.get_template("system_base")

# Create a specialized template through inheritance
specialized_template = base_template.derive(
    template_text=base_template.template_text + "\n\n{#include dropdown_guidelines}",
    name="dropdown_system",
    version="1.1"
)

# Register the specialized template
PromptLibrary.register_template(specialized_template, "system")

# Create a newer version with additional content
advanced_template = specialized_template.derive(
    template_text=specialized_template.template_text + "\n\nIMPORTANT: Focus on actions that could lead to monitored operations.",
    name="monitored_ops_system",
    version="1.2"
)

# Register the advanced template
PromptLibrary.register_template(advanced_template, "system")

# Get the latest version of a template
latest_template = PromptLibrary.get_template("system_base")  # Gets the most recent version

# Get a specific version
specific_template = PromptLibrary.get_template("system_base", version="1.0")
```

### 5.4 Conditional Logic and Fragment Inclusion

Templates support conditional sections and fragment inclusion:

```python
# Template with conditional sections and fragment inclusion
advanced_template = PromptTemplate(
    template_text="""You are a specialized Android tester.

{#if focus_on_mop}
FOCUS ON MONITORED OPERATIONS: Your primary goal is to test paths that lead to monitored operations.
{#else}
FOCUS ON EXPLORATION: Your primary goal is to explore the application completely.
{#endif}

{#include base_guidelines}

{#if has_forms}
{#include form_guidelines}
{#endif}

{#if has_dropdowns}
{#include dropdown_guidelines}
{#endif}""",
    name="conditional_template",
    version="1.0"
)

# Using conditional template
variables = {
    "focus_on_mop": True,
    "has_forms": True,
    "has_dropdowns": False
}

# Render with conditions
rendered_text = advanced_template.render(variables)
```

### 5.5 Type-Safe Message Generation

The template system can directly generate MCP messages:

```python
# Template that produces MCP messages
def render_conversation(variables):
    # Get system template
    system_template = PromptLibrary.get_template("system_base")
    
    # Get user template
    user_template = PromptLibrary.get_template("user_base")
    
    # Render system message
    system_message = MCPMessage(
        role=MCPRole.SYSTEM,
        content=[MCPTextContent(text=system_template.render(variables))]
    )
    
    # Render user message
    user_message = MCPMessage(
        role=MCPRole.USER,
        content=[MCPTextContent(text=user_template.render(variables))]
    )
    
    # Return message sequence
    return [system_message, user_message]
```

## 6. Prompt Strategies

The MCP system integrates with RV-Android's prompt strategies, providing a standardized approach to generating LLM interactions.

### 6.1 Strategy Hierarchy

The prompt strategies follow a clear inheritance hierarchy with MCP integration:

```
BasePromptStrategy
├── SingleActionPromptStrategy
├── ComposablePromptStrategy
│   └── ComposableSingleActionStrategy
└── FlowBasedBatchActionStrategy
```

### 6.2 Base Prompt Strategy with MCP

The `BasePromptStrategy` incorporates MCP for message generation:

```python
class BasePromptStrategy:
    """Base class for prompt strategies using MCP."""
    
    def __init__(self, static_data=None, parser=None):
        """Initialize with MCP integration."""
        self.static_data = static_data
        self.parser = parser_factory.get_parser(parser) if isinstance(parser, str) else parser
        
        # Initialize templates from library
        self.system_template = PromptLibrary.get_template("system_base")
        self.user_template = PromptLibrary.get_template("user_base")
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def generate_messages(self, state: Dict[str, Any]) -> List[MCPMessage]:
        """Generate MCP messages for the given context."""
        try:
            # Generate system message
            system_message = MCPMessage(
                role=MCPRole.SYSTEM,
                content=[MCPTextContent(text=self.generate_system_prompt())]
            )
            
            # Generate user message
            user_message = MCPMessage(
                role=MCPRole.USER,
                content=[MCPTextContent(text=self.generate_user_prompt(state))]
            )
            
            # Return message sequence
            return [system_message, user_message]
        except Exception as e:
            self.logger.error(f"Error generating MCP messages: {e}", exc_info=True)
            # Fallback to simple messages
            return self._generate_fallback_messages(state)
    
    def generate_system_prompt(self) -> str:
        """Generate system prompt using the template."""
        # Prepare variables
        variables = {
            "exploration_goal": "Exploring the application thoroughly and systematically",
            "response_format": PromptLibrary.get_template("response_format").render({})
        }
        
        # Render the template
        return self.system_template.render(variables)
    
    def generate_user_prompt(self, state: Dict[str, Any]) -> str:
        """Generate user prompt using the template."""
        try:
            # Process screen description
            screen_description = self.process_screen(state)
            
            # Format UI elements for the prompt
            ui_elements = self._format_ui_elements(screen_description, state)
            
            # Get activity name
            activity = self.parser.get_activity_name(state)
            
            # Format action history
            action_history = self._format_action_history(state)
            
            # Render the template with variables
            return self.user_template.render({
                "activity": activity,
                "ui_elements": ui_elements,
                "action_history": action_history
            })
        except Exception as e:
            self.logger.error(f"Error generating user prompt: {e}", exc_info=True)
            return "Analyze the current screen and suggest the next testing action."
```

### 6.3 Flow-Based Batch Strategy with MCP

The `FlowBasedBatchActionStrategy` leverages MCP for generating batch actions:

```python
class FlowBasedBatchActionStrategy(BasePromptStrategy):
    """Strategy for generating batches of related actions using MCP."""
    
    def __init__(self, static_data=None, parser=None):
        """Initialize with pattern detection."""
        super().__init__(static_data, parser)
        
        # Initialize pattern detectors
        self.form_detector = FormDetector(static_data)
        self.list_detector = ListDetector(static_data)
        self.tab_detector = TabDetector(static_data)
        self.navigation_detector = NavigationDetector(static_data)
        
        # Use specialized templates
        self.system_template = PromptLibrary.get_template("batch_system")
        self.user_template = PromptLibrary.get_template("batch_user")
    
    def generate_system_prompt(self) -> str:
        """Generate a system prompt for batch action generation."""
        # Customize for batch action generation
        exploration_goal = ("Analyzing UI patterns and generating logical sequences "
                          "of related actions for complete workflow testing")
        
        # Use batch action response format
        response_format = PromptLibrary.get_template("batch_format").render({})
        
        # Add guidelines based on detected patterns
        additional_guidelines = (
            "Generate logical sequences of 2-5 related actions that form a cohesive "
            "testing workflow. Focus on completing forms, exploring lists, and "
            "navigating through tabs."
        )
        
        # Render template
        return self.system_template.render({
            "exploration_goal": exploration_goal,
            "response_format": response_format,
            "additional_guidelines": additional_guidelines
        })
    
    def generate_user_prompt(self, state: Dict[str, Any]) -> str:
        """Generate a user prompt with pattern detection."""
        try:
            # Process screen description
            screen_description = self.process_screen(state)
            
            # Detect UI patterns
            patterns = self._detect_patterns(screen_description)
            
            # Format UI elements
            ui_elements = self._format_ui_elements(screen_description, state)
            
            # Get activity name
            activity = self.parser.get_activity_name(state)
            
            # Format patterns for the prompt
            pattern_descriptions = self._format_patterns(patterns)
            
            # Render template with pattern information
            return self.user_template.render({
                "activity": activity,
                "ui_elements": ui_elements,
                "patterns": pattern_descriptions
            })
        except Exception as e:
            self.logger.error(f"Error generating batch user prompt: {e}", exc_info=True)
            return "Analyze the UI patterns and suggest sequences of related actions."
```

### 6.4 Using Strategies with Language Models

The prompt strategies work seamlessly with language models using MCP:

```python
async def generate_actions(strategy, model, state):
    """Generate actions using a strategy and model with MCP."""
    try:
        # Generate MCP messages
        messages = strategy.generate_messages(state)
        
        # Get language model response
        response = await model.generate(messages)
        
        # Process response
        return strategy.process_response(response, state)
    except Exception as e:
        logger.error(f"Error generating actions: {e}")
        return []
```

## 7. Integration with Test Framework

### 7.1 Test Framework Configuration

The RV-Android Test Framework integrates with MCP through its configuration system:

```python
class ToolConfiguration:
    """Defines how a testing tool should be configured for execution."""
    
    def __init__(self, tool_name: str, **kwargs):
        """Initialize with tool name and parameters."""
        self.tool_name = tool_name
        
        # MCP model configuration
        self.model_type = kwargs.get("model_type", "ollama")
        self.model_name = kwargs.get("model_name", "llama3.2:3b")
        self.temperature = kwargs.get("temperature", 0.2)
        self.max_tokens = kwargs.get("max_tokens", 800)
        
        # Strategy configuration
        self.strategy_type = kwargs.get("strategy_type", "single_action")
        self.parser_type = kwargs.get("parser_type", "uiautomator")
        
        # Other parameters
        # [implementation details]
```

### 7.2 Configuration Validation

The framework enforces MCP usage through validation:

```python
def validate_model_configuration(config):
    """Validate model configuration for MCP compatibility."""
    # Check model type
    if not config.model_type:
        raise ValidationError("Model type is required")
    
    # Check model name
    if not config.model_name:
        raise ValidationError("Model name is required")
    
    # Check temperature range
    if config.temperature < 0 or config.temperature > 2:
        raise ValidationError("Temperature must be between 0 and 2")
    
    # Check for supported model types
    from rvandroid.config.component_configurator import ComponentConfigurator
    supported_model_types = ComponentConfigurator._registries['llm'].get_names()
    if config.model_type not in supported_model_types:
        raise ValidationError(
            f"Unsupported model type: {config.model_type}. "
            f"Supported types: {', '.join(supported_model_types)}"
        )
    
    # Validate model name based on type
    model_class = ComponentConfigurator._registries['llm'].get(config.model_type)
    if model_class and hasattr(model_class, 'models'):
        available_models = model_class.models()
        if available_models and config.model_name not in available_models:
            raise ValidationError(
                f"Unknown model name '{config.model_name}' for type '{config.model_type}'. "
                f"Available models: {', '.join(available_models)}"
            )
```

### 7.3 Model Creation in Test Framework

The Test Framework uses the ComponentConfigurator to create model instances:

```python
def create_model_from_config(config):
    """Create a model instance from configuration."""
    try:
        # Create configurator
        configurator = ComponentConfigurator()
        
        # Configure LLM
        configurator.set_llm(
            config.model_type,
            config.model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens
        )
        
        # Create model using configurator
        model = configurator.create_llm()
        
        logger.info(f"Created {config.model_type} model: {config.model_name}")
        return model
    except Exception as e:
        logger.error(f"Error creating model: {e}")
        raise
```

### 7.4 Tool Integration

The Test Framework tools integrate with MCP:

```python
class RVAndroidTool(ConfigurableTool):
    """RVAndroid tool implementation with MCP integration."""
    
    def __init__(self):
        """Initialize the RVAndroid tool."""
        super().__init__(
            "rvandroid",
            "AI-driven Android testing tool using LLM guidance",
            "br.unb.cic.rvsec"
        )
        
        # Set default MCP configuration
        self.component_config.set_model_type("ollama")
        self.component_config.set_model_name("llama3.2:3b")
        self.component_config.set_strategy("composable_single_action")
        
    def execute(self, task, app):
        """Execute RVAndroid with MCP configuration."""
        # Get model using component configurator
        model = self.component_config.create_llm()
        
        # Create prompt strategy
        strategy = PromptStrategyFactory.create(
            strategy_type=self.component_config.strategy_type,
            static_data=task.static_data
        )
        
        # Create action service with MCP components
        service = LLMActionService(
            model=model,
            strategy=strategy,
            static_data=task.static_data
        )
        
        # Execute testing
        # [implementation details]
```

### 7.5 Comparative Analysis

The Test Framework enables comparative analysis of different MCP configurations:

```python
def compare_model_configurations(configurations, app_path):
    """Compare different MCP model configurations."""
    results = []
    
    for config in configurations:
        # Create test case with this configuration
        test_case = TestCase(
            name=f"{config.model_type}_{config.model_name}_{config.strategy_type}",
            app_path=app_path,
            tool_config=config
        )
        
        # Execute test case
        result = executor.run_test_case(test_case)
        results.append(result)
    
    # Generate comparative analysis
    analyzer = ComparativeAnalyzer(results)
    report = analyzer.generate_report()
    
    return report
```

## 8. Usage Examples

### 8.1 Basic MCP Usage

```python
from rvandroid.llm.data_structures import MCPMessage, MCPRole, MCPTextContent
from rvandroid.config.component_configurator import ComponentConfigurator

# Create MCP messages
system_message = MCPMessage(
    role=MCPRole.SYSTEM,
    content=[MCPTextContent(text="You are an AI assistant for Android testing.")]
)

user_message = MCPMessage(
    role=MCPRole.USER,
    content=[MCPTextContent(text="Suggest a test action for the login screen.")]
)

# Create model using configurator
configurator = ComponentConfigurator()
configurator.set_llm(
    "ollama", 
    "llama3.2:3b", 
    temperature=0.3
)
model = configurator.create_llm()

# Generate response
response = model.generate_sync([system_message, user_message])

# Access response content
response_text = response.content[0].text
print(f"Model response: {response_text}")
```

### 8.2 Using Templates with MCP

```python
from rvandroid.llm.templates.template import PromptTemplate
from rvandroid.llm.templates.library import PromptLibrary
from rvandroid.llm.data_structures import MCPMessage, MCPRole, MCPTextContent
from rvandroid.config.component_configurator import ComponentConfigurator

# Define a template
template = PromptTemplate(
    template_text="""You are an Android testing assistant.

CURRENT SCREEN: {screen_name}

UI ELEMENTS:
{ui_elements}

Suggest the best next action to take for testing this screen thoroughly.""",
    name="testing_template",
    version="1.0",
    required_variables=["screen_name", "ui_elements"]
)

# Register template
PromptLibrary.register_template(template, "user")

# Render template with variables
rendered_text = template.render({
    "screen_name": "LoginActivity",
    "ui_elements": "1. Username field\n2. Password field\n3. Login button"
})

# Create MCP message
user_message = MCPMessage(
    role=MCPRole.USER,
    content=[MCPTextContent(text=rendered_text)]
)

# Create model and generate response
configurator = ComponentConfigurator()
configurator.set_llm("ollama", "llama3.2:3b")
model = configurator.create_llm()
response = model.generate_sync([user_message])

print(f"Response: {response.content[0].text}")
```

### 8.3 Advanced Strategy Integration

```python
from rvandroid.llm.prompt.flow_based_batch_action_strategy import FlowBasedBatchActionStrategy
from rvandroid.config.component_configurator import ComponentConfigurator

# Create strategy
strategy = FlowBasedBatchActionStrategy(static_data)

# Create configurator and model
configurator = ComponentConfigurator(static_data)
configurator.set_llm("ollama", "llama3.2:3b")
configurator.set_strategy("flow_based_batch_action")
model = configurator.create_llm()

# Get current app state
state = get_current_state()  # Implementation-specific

# Generate messages using strategy
messages = strategy.generate_messages(state)

# Generate response
response = model.generate_sync(messages)

# Process response using strategy
actions = strategy.process_response(response, state)

# Execute actions
for action in actions:
    execute_action(action)  # Implementation-specific
```

### 8.4 Custom Adapter Creation

```python
from typing import Dict, Any, List
import logging
from rvandroid.llm.adapter import MCPAdapter
from rvandroid.llm.data_structures import MCPMessage, MCPRole, MCPTextContent, MCPConfiguration

class CustomAdapter(MCPAdapter):
    """Custom adapter for a new LLM provider."""
    
    def __init__(self):
        """Initialize the custom adapter."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def prepare_messages(self, messages: List[MCPMessage]) -> Dict[str, Any]:
        """Convert MCP messages to custom format."""
        # Implementation for your specific provider
        custom_format = {"messages": []}
        
        for message in messages:
            # Extract text content
            text = "".join(c.text for c in message.content if isinstance(c, MCPTextContent))
            
            # Add to custom format
            custom_format["messages"].append({
                "type": message.role.value,
                "content": text
            })
        
        return custom_format
    
    def prepare_config(self, config: MCPConfiguration) -> Dict[str, Any]:
        """Convert MCP configuration to custom parameters."""
        # Map configuration parameters
        return {
            "model": config.model_name,
            "temp": config.temperature,
            "max_length": config.max_tokens
        }
    
    def parse_response(self, response: Any) -> MCPMessage:
        """Parse custom response into MCP message."""
        # Extract response text
        if isinstance(response, dict) and "output" in response:
            text = response["output"]
        else:
            text = str(response)
        
        # Create MCP message
        return MCPMessage(
            role=MCPRole.ASSISTANT,
            content=[MCPTextContent(text=text)]
        )
    
    def validate_request(self, messages: List[MCPMessage], config: MCPConfiguration) -> bool:
        """Validate that messages and config are compatible."""
        # Implement validation logic
        return len(messages) > 0 and config.model_name != ""

# Register adapter with a custom model
class CustomModel(LanguageModel):
    """Custom model implementation."""
    
    def __init__(self, model_name: str, **kwargs):
        """Initialize custom model."""
        super().__init__(model_name, **kwargs)
        
    def _get_model_type(self) -> str:
        """Get model type."""
        return "custom"
    
    def _get_adapter(self) -> MCPAdapter:
        """Get custom adapter."""
        return CustomAdapter()
    
    async def generate(self, messages: List[MCPMessage], config=None) -> MCPMessage:
        """Generate asynchronously."""
        # Implementation details
        
    def generate_sync(self, messages: List[MCPMessage], config=None) -> MCPMessage:
        """Generate synchronously."""
        # Implementation details

# Register the custom model
ComponentConfigurator.register_llm("custom", CustomModel)

# Use the custom model
configurator = ComponentConfigurator()
configurator.set_llm("custom", "my-custom-model")
model = configurator.create_llm()
```

### 8.5 Test Framework Configuration

```json
{
  "name": "MCP Model Comparison",
  "description": "Compare different MCP model configurations",
  "apps": ["path/to/app1.apk", "path/to/app2.apk"],
  "repetitions": 3,
  "tools": [
    {
      "name": "rvandroid",
      "timeout": 300,
      "model_type": "ollama",
      "model_name": "llama3.2:3b",
      "temperature": 0.2,
      "strategy_type": "single_action"
    },
    {
      "name": "rvandroid",
      "timeout": 300,
      "model_type": "ollama",
      "model_name": "llama3.2:8b",
      "temperature": 0.2,
      "strategy_type": "single_action"
    },
    {
      "name": "rvandroid",
      "timeout": 300,
      "model_type": "frontier",
      "model_name": "claude-3-haiku",
      "temperature": 0.2,
      "strategy_type": "flow_based_batch"
    }
  ]
}
```

## 9. Extending the System

### 9.1 Adding New Model Types

To add support for a new LLM provider to the MCP system:

1. **Create an Adapter**:
   ```python
   class NewProviderAdapter(MCPAdapter):
       """Adapter for new provider."""
       
       def prepare_messages(self, messages):
           # Convert MCP messages to provider format
           
       def prepare_config(self, config):
           # Convert MCP config to provider parameters
           
       def parse_response(self, response):
           # Parse provider response to MCP message
           
       def validate_request(self, messages, config):
           # Validate request for provider
   ```

2. **Implement Language Model**:
   ```python
   class NewProviderModel(LanguageModel):
       """Model implementation for new provider."""
       
       def _get_model_type(self):
           return "new_provider"
           
       def _get_adapter(self):
           return NewProviderAdapter()
           
       async def generate(self, messages, config=None):
           # Async generation implementation
           
       def generate_sync(self, messages, config=None):
           # Sync generation implementation
   ```

3. **Register the Model**:
   ```python
   # Register with component configurator
   ComponentConfigurator.register_llm("new_provider", NewProviderModel)
   ```

### 9.2 Creating Custom Templates

To create custom templates for the MCP system:

1. **Define Template**:
   ```python
   custom_template = PromptTemplate(
       template_text="""Custom template content with {variable} placeholders
   and {#if condition}conditional sections{#endif}
   and {#include fragment} inclusions.""",
       name="custom_template",
       version="1.0",
       required_variables=["variable"]
   )
   ```

2. **Register Template**:
   ```python
   PromptLibrary.register_template(custom_template, "custom")
   ```

3. **Use in Strategies**:
   ```python
   class CustomStrategy(BasePromptStrategy):
       """Custom strategy with specialized templates."""
       
       def __init__(self, static_data=None, parser=None):
           super().__init__(static_data, parser)
           self.specialized_template = PromptLibrary.get_template("custom_template")
   ```

### 9.3 Creating Custom Prompt Strategies

To implement a custom prompt strategy:

1. **Extend Base Strategy**:
   ```python
   class CustomStrategy(BasePromptStrategy):
       """Custom prompt strategy implementation."""
       
       def __init__(self, static_data=None, parser=None):
           """Initialize custom strategy."""
           super().__init__(static_data, parser)
           # Custom initialization
           
       def generate_system_prompt(self):
           """Generate custom system prompt."""
           # Custom implementation
           
       def generate_user_prompt(self, state):
           """Generate custom user prompt."""
           # Custom implementation
           
       def process_response(self, response, state):
           """Process response in custom way."""
           # Custom implementation
   ```

2. **Register Strategy**:
   ```python
   PromptStrategyFactory.register_strategy(
       "custom_strategy", 
       CustomStrategy,
       metadata={"description": "Custom strategy implementation"}
   )
   ```

3. **Use Strategy**:
   ```python
   # Create strategy instance
   strategy = PromptStrategyFactory.create("custom_strategy", static_data)
   
   # Use in testing
   configurator = ComponentConfigurator(static_data)
   configurator.set_llm("ollama", "llama3.2:3b")
   model = configurator.create_llm()
   messages = strategy.generate_messages(state)
   response = model.generate_sync(messages)
   actions = strategy.process_response(response, state)
   ```

### 9.4 Extending the Test Framework

To extend the Test Framework with new MCP capabilities:

1. **Create Custom Tool Configuration**:
   ```python
   class CustomToolConfiguration(ToolConfiguration):
       """Custom tool configuration with enhanced MCP properties."""
       
       def __init__(self, tool_name, **kwargs):
           super().__init__(tool_name, **kwargs)
           self.custom_mcp_property = kwargs.get("custom_mcp_property")
   ```

2. **Add Custom Metrics Collection**:
   ```python
   class MCPMetricsCollector:
       """Collects MCP-specific metrics during testing."""
       
       def __init__(self):
           self.metrics = {}
           
       def record_generation_metrics(self, model_type, model_name, tokens, latency):
           # Record generation metrics
           
       def record_prompt_metrics(self, strategy_type, prompt_size, tokens):
           # Record prompt metrics
           
       def generate_report(self):
           # Generate metrics report
   ```

3. **Add Custom Analysis**:
   ```python
   class MCPPerformanceAnalyzer:
       """Analyzes MCP performance across test runs."""
       
       def __init__(self, results):
           self.results = results
           
       def analyze_model_performance(self):
           # Analyze model performance
           
       def analyze_strategy_performance(self):
           # Analyze strategy performance
           
       def generate_report(self):
           # Generate analysis report
   ```

## 10. Troubleshooting

### 10.1 Common MCP Issues

1. **Adapter Conversion Errors**:
   - **Symptom**: Error in `prepare_messages` or `prepare_config`
   - **Solution**: Ensure adapter properly converts MCP to provider format
   - **Example**: Implement more robust error handling in adapters

2. **Model Generation Failures**:
   - **Symptom**: Exception during model generation
   - **Solution**: Check model configuration and API access
   - **Example**: Validate API keys and endpoints

3. **Template Rendering Errors**:
   - **Symptom**: Error during template rendering
   - **Solution**: Ensure all required variables are provided
   - **Example**: Add default values for optional variables

4. **Invalid Response Format**:
   - **Symptom**: Error parsing model response
   - **Solution**: Enhance response parsing robustness
   - **Example**: Add fallback parsing strategies

### 10.2 Debugging MCP

To debug MCP issues:

1. **Enable Detailed Logging**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **Inspect MCP Messages**:
   ```python
   messages = strategy.generate_messages(state)
   for msg in messages:
       print(f"Role: {msg.role.value}")
       for content in msg.content:
           print(f"Content: {content}")
   ```

3. **Test Adapter Conversions**:
   ```python
   adapter = model._get_adapter()
   provider_format = adapter.prepare_messages(messages)
   print(f"Provider format: {provider_format}")
   ```

4. **Validate Template Rendering**:
   ```python
   template = PromptLibrary.get_template("template_name")
   rendered = template.render(variables)
   print(f"Rendered template: {rendered}")
   ```

### 10.3 Performance Considerations

When working with MCP, keep these performance considerations in mind:

1. **Message Conversion Overhead**:
   - The adapter conversion process adds computational overhead
   - For high-frequency operations, consider caching common message patterns

2. **Template Rendering Performance**:
   - Complex templates with many conditionals can be expensive to render
   - Consider pre-rendering common templates

3. **Response Parsing Efficiency**:
   - Response parsing can be expensive for complex responses
   - Consider streaming responses when possible

4. **Model Selection Trade-offs**:
   - Larger models provide better reasoning but have higher latency
   - Choose model size based on the complexity of your testing tasks

### 10.4 Compatibility Issues

When encountering compatibility issues:

1. **Model Capability Differences**:
   - Not all models support the same features (images, tools, etc.)
   - Adapters should handle graceful degradation

2. **Version Compatibility**:
   - MCP structures may evolve over time
   - Ensure adapters are updated for API changes

3. **Provider API Changes**:
   - LLM provider APIs frequently change
   - Monitor for breaking changes and update adapters accordingly

4. **Template Compatibility**:
   - Templates may depend on specific model capabilities
   - Use conditional sections to handle model-specific features