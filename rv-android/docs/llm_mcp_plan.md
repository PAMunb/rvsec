# RV-Android Model Context Protocol (MCP) Implementation Plan

## 1. Overview

This document outlines a comprehensive plan for implementing the Model Context Protocol (MCP) in the RV-Android system. The primary goal is to standardize communication between the system and various LLM providers, eliminate model-specific formatting code, reduce duplication, and enable more efficient and consistent prompt template management.

The plan integrates MCP across all LLM implementations, addresses template duplication issues, and enhances the system's ability to work with different LLM providers while maintaining a clean, standardized interface.

This implementation will fully support the system's approach of using different specification sets in separate experiments - specifically, the JCA cryptography-related specifications and general programming specifications (like Iterator hasNext/next validation). Throughout this document, we use the term "monitored operations" to refer to operations being tracked by any specification, without assuming a security-specific context.

### 1.1 Strategic Implementation Approach

The implementation is designed with four key strategic considerations:

1. **Complete replacement** of the current model-specific message format handling
2. **Elimination of duplicate template code** across different prompt strategies
3. **Standardized interface** for all LLM operations
4. **Full code refactoring** without maintaining legacy code or compatibility adapters

This comprehensive approach ensures that:
- We gain immediate consistency benefits across all model implementations
- We establish a clean, centralized system for prompt template management
- We eliminate duplicated code across different strategy implementations
- We create a forward-compatible architecture for future LLM integration
- We maintain support for different monitored operation specification sets
- We adhere to RV-Android code standards including detailed documentation and English-language code/comments

## 2. Architecture and Component Relationships

### 2.1 Current Architecture

The RV-Android system currently handles LLM integration through:

1. **Abstract Language Model Interface** (`rvandroid/llm/llm.py`):
   - Defines base `LanguageModel` class with abstract methods
   - Each LLM provider implements this interface
   - Model-specific adapters handle format conversions manually

2. **Model-Specific Implementations**:
   - `OllamaLLM` (`rvandroid/llm/ollama_llm.py`)
   - `HuggingFaceLLM` (`rvandroid/llm/huggingface_llm.py`)
   - `DSPyLLM` (`rvandroid/llm/dspy_llm.py`)
   - `LangchainLLM` (`rvandroid/llm/langchain_llm.py`)
   - `FrontierLLM` (`rvandroid/llm/frontier_models.py`)

3. **Template System** (`rvandroid/llm/prompt/prompt_template.py`):
   - Implements `PromptTemplate` and `TemplateFragment` for template management
   - Provides string-based template rendering with variables
   - Includes conditional logic and fragment inclusion

4. **Prompt Strategies**:
   - Various strategy implementations with significant code duplication:
     - `BasePromptStrategy` (`rvandroid/llm/prompt/base_prompt_strategy.py`)
     - `SingleActionPromptStrategy` (`rvandroid/llm/prompt/single_action_prompt_strategy.py`)
     - `ComposablePromptStrategy` (`rvandroid/llm/prompt/composable_prompt_strategy.py`)
     - `FlowBasedBatchActionStrategy` (`rvandroid/llm/prompt/flow_based_batch_action_strategy.py`)

5. **Tool Integration**:
   - `rvandroid/tools/rvandroid/tool.py` and `rvandroid/tools/rvdroid/tool.py` use LLM services
   - `LLMActionService` mediates between tools and LLM functionality

### 2.2 Problems with Current Architecture

1. **Model-Specific Format Handling**:
   - Each model implementation manually constructs proper format
   - No standardized message representation
   - Duplicated conversion logic across implementations

2. **Template Duplication**:
   - Similar templates duplicated across strategies
   - No centralized template library
   - Limited reuse of common prompt components

3. **String-Based Templates**:
   - Templates produce raw strings rather than structured data
   - Format conversion happens after template rendering
   - No type safety or validation in template structure

### 2.3 MCP Architecture Overview

The new Model Context Protocol architecture will:

1. **Standardize Message Representation**:
   - Define a consistent message format across all LLM integrations
   - Support rich message content (text, images, structured data)
   - Handle model-specific format conversions through protocol adapters

2. **Centralize Template Management**:
   - Create a hierarchical template library with inheritance
   - Eliminate duplication through fragment reuse
   - Enable composition of templates from reusable components

3. **Enable Structured Template Output**:
   - Generate structured MCP messages instead of raw strings
   - Provide type safety and validation for message format
   - Support rich message content directly in templates

4. **Simplify Model Integration**:
   - Abstract away model-specific formatting details
   - Provide a consistent interface for all LLM interactions
   - Streamline addition of new LLM providers

```
┌─────────────────────────────┐     ┌─────────────────────────────┐
│                             │     │                             │
│      RVAndroid Tool         │     │        RVDroid Tool         │
│                             │     │                             │
└───────────────┬─────────────┘     └───────────────┬─────────────┘
                │                                   │                
                ▼                                   ▼                
┌─────────────────────────────┐     ┌─────────────────────────────┐
│                             │     │                             │
│     LLMActionService        │     │       MemorySystem          │
│                             │     │                             │
└───────────────┬─────────────┘     └───────────────┬─────────────┘
                │                                   │                
                └───────────────┬───────────────────┘                
                                │                                    
                                ▼                                    
                  ┌─────────────────────────────┐                  
                  │                             │                  
                  │       Prompt Strategy       │                  
                  │                             │                  
                  └───────────────┬─────────────┘                  
                                  │                                  
                                  ▼                                  
                  ┌─────────────────────────────┐                  
                  │                             │                  
                  │     MCP Template System     │───┐                
                  │                             │   │                
                  └───────────────┬─────────────┘   │                
                                  │                 │                
                                  ▼                 ▼                
┌─────────────────────────────┐   ┌─────────────────────────────┐   
│                             │   │                             │   
│     LanguageModel (MCP)     │   │     MCP Template Library    │   
│                             │   │                             │   
└───────────────┬─────────────┘   └─────────────────────────────┘   
                │                                                    
                ▼                                                    
┌──────────────────────────────────────────────────────────────┐    
│                                                              │    
│                   MCP Protocol Adapters                      │    
│                                                              │    
└──────────┬──────────────┬───────────────┬───────────────────┘    
           │              │               │                         
           ▼              ▼               ▼                         
┌─────────────────┐ ┌─────────────┐ ┌─────────────────┐            
│                 │ │             │ │                 │            
│ Ollama Adapter  │ │  DSPy Adapter │ │ HuggingFace Adapter │            
│                 │ │             │ │                 │            
└─────────────────┘ └─────────────┘ └─────────────────┘            
```

### 2.4 Component Relationships

The MCP implementation will touch several key components:

1. **MCP Core Components**:
   - `MCPMessage`: Standard message representation
   - `MCPRole`: Message role enumeration (system, user, assistant, tool)
   - `MCPContent`: Content structure with support for text, images, etc.
   - `MCPConfiguration`: Model-specific configuration parameters

2. **Language Model Interface**:
   - Updated `LanguageModel` interface using MCP
   - Model factory for creating appropriate model instances
   - Registry for available models

3. **Protocol Adapters**:
   - Adapters for each supported LLM provider
   - Bidirectional conversion between MCP and model-specific formats
   - Configuration mapping between MCP and model parameters

4. **Template System Components**:
   - MCP-aware `PromptTemplate` generating structured messages
   - Template library with hierarchical organization
   - Fragment repository for reusable components
   - Template composition utilities

5. **Strategy Integration**:
   - Updated prompt strategies using MCP templates
   - Refactored strategies to eliminate duplication
   - Strategy factory with configuration support

### 2.5 Integration with Test Framework

The MCP implementation will be integrated with the RV-Android Test Framework in a transparent manner:

1. **Seamless Integration**:
   - MCP will work "behind the scenes" without requiring changes to the Test Framework
   - Existing test configurations (TestSuite, ToolConfiguration, TestCase) will continue to work
   - No need to modify configuration files or test scripts

2. **Configuration Adaptation**:
   - Implement adapters to translate Test Framework configurations into MCP configurations
   - Preserve the existing API for test definition and execution
   - Ensure backward compatibility with existing test configurations

3. **Performance Metrics Collection**:
   - Integrate MCP-specific metrics with the Test Framework's analytics
   - Track and compare the performance of different MCP configurations
   - Analyze the impact of MCP implementation on testing effectiveness

4. **Test Framework Usage**:
   - Leverage existing Test Framework for comparative evaluation of MCP approaches
   - Use the framework's visualization and reporting capabilities for MCP analysis
   - Enable A/B testing between legacy and MCP-based implementations during transition

### 2.6 Template Versioning System

The MCP implementation will include a comprehensive template versioning system:

1. **Semantic Versioning**:
   - Templates will follow semantic versioning (MAJOR.MINOR.PATCH)
   - MAJOR: Incremented for incompatible changes
   - MINOR: Incremented for backward-compatible additions
   - PATCH: Incremented for backward-compatible fixes

2. **Template Storage and Retrieval**:
   - Templates stored in a hierarchical structure
   - Centralized repository for authorized templates
   - Version history tracking for each template
   - Ability to retrieve specific versions

3. **Template Derivation**:
   - Create new template versions derived from existing ones
   - Inheritance mechanism to extend base templates
   - Override capabilities for customization
   - Clear tracking of template lineage

4. **Template Selection**:
   - Runtime selection of template versions
   - Default to latest compatible version
   - Explicit version pinning when needed
   - Compatibility checking between templates and fragments

5. **Fragment Versioning**:
   - Independent versioning for template fragments
   - Compatibility tracking between templates and fragments
   - Fragment composition with version awareness
   - Reusable fragment library across template versions

## 3. Implementation Plan

### Phase 1: Core MCP Infrastructure (Week 1)

#### 3.1.1 Define MCP Data Structures

- [ ] Create `MCPMessage` class representing structured messages
- [ ] Define `MCPRole` enumeration (system, user, assistant, tool)
- [ ] Implement `MCPContent` for different content types (text, image, etc.)
- [ ] Create `MCPMessageList` for managing conversation history
- [ ] Implement `MCPConfiguration` for model parameters

```python
# mcp_data_structures.py

"""
Core data structures for the Model Context Protocol (MCP).

This module defines the fundamental data structures used in the MCP system,
providing a standardized representation of messages exchanged with language models.

Key Components:
- MCPRole: Enumeration of possible message roles
- MCPContent classes: Structured content representation
- MCPMessage: Standard message format
- MCPConfiguration: Model configuration parameters

The MCP system provides a unified interface for all language model interactions,
supporting both general programming and cryptography-specific monitored operations.

Author: RV-Android Team
"""

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
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop: Optional[List[str]] = None
```

#### 3.1.2 Create Protocol Adapter Framework

- [ ] Define `MCPAdapter` abstract base class
- [ ] Implement adapter registry for model type mapping
- [ ] Create validation utilities for MCP messages
- [ ] Implement serialization/deserialization for MCP structures

```python
# mcp_adapter.py

"""
Model Context Protocol (MCP) Adapter Framework.

This module defines the adapter framework for converting between the standardized
MCP format and model-specific formats. Each supported language model has a dedicated
adapter implementation that handles the bidirectional conversion of messages and
configuration parameters.

Key Components:
- MCPAdapter: Abstract base class for all model adapters
- AdapterRegistry: Registration system for available adapters
- Validation utilities for MCP message structures

The adapter system enables the RV-Android framework to communicate with diverse
language models while maintaining a consistent interface focused on monitored
operations testing.

Author: RV-Android Team
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from rvandroid.util.error.error_handler import ErrorHandler
from rvandroid.util.logging.manager import LoggingManager

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

#### 3.1.3 Update Language Model Interface

- [ ] Modify `LanguageModel` to use MCP structures
- [ ] Implement basic error handling and validation
- [ ] Create model factory using adapter registry
- [ ] Update model configuration system

```python
# language_model.py

"""
MCP-based Language Model interface.

This module defines the standardized interface for all language model implementations
in the RV-Android system. All model-specific details are abstracted away through the
MCP adapter system, providing a clean and consistent API.

Key Components:
- LanguageModel: Abstract base class for all model implementations
- ModelFactory: Factory for creating appropriate model instances
- ModelRegistry: Registry of available model implementations

This implementation supports testing with different monitored operation specifications
(both general programming and cryptography-specific) through a common interface.

Author: RV-Android Team
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from rvandroid.util.decorators import log_method_call, measure_time

class LanguageModel(ABC):
    """Base class for language model implementations using MCP"""
    
    def __init__(self, model_name: str, **kwargs):
        self.model_name = model_name
        self.adapter = self._get_adapter()
        self.config = self._get_default_config()
        self.config.update(kwargs)
    
    @abstractmethod
    def _get_adapter(self) -> MCPAdapter:
        """Get the appropriate MCP adapter for this model"""
        pass
    
    @abstractmethod
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration parameters for this model"""
        pass
    
    @abstractmethod
    async def generate(self, 
                      messages: List[MCPMessage], 
                      config: Optional[MCPConfiguration] = None) -> MCPMessage:
        """Generate a response using the language model"""
        pass
    
    @abstractmethod
    def generate_sync(self, 
                     messages: List[MCPMessage], 
                     config: Optional[MCPConfiguration] = None) -> MCPMessage:
        """Generate a response synchronously"""
        pass
```

### Phase 2: Implement MCP Adapters (Week 2)

#### 3.2.1 Ollama Adapter

- [ ] Implement `OllamaAdapter` for Ollama API
- [ ] Handle message format conversion for Ollama
- [ ] Map MCP configuration to Ollama parameters
- [ ] Implement response parsing and validation
- [ ] Update `OllamaLLM` to use the adapter
- [ ] Use Ollama Community library to avoid warning logs

#### 3.2.2 DSPy Adapter

- [ ] Create `DSPyAdapter` for DSPy integration
- [ ] Implement message conversion for DSPy modules
- [ ] Handle DSPy-specific configuration parameters
- [ ] Implement response processing
- [ ] Update `DSPyLLM` to use the adapter

#### 3.2.3 HuggingFace Adapter

- [ ] Develop `HuggingFaceAdapter` for Transformer models
- [ ] Implement conversion to HF chat template format
- [ ] Map configuration parameters appropriately
- [ ] Handle response generation and parsing
- [ ] Update `HuggingFaceLLM` to use the adapter

#### 3.2.4 Additional Adapters

- [ ] Implement `LangchainAdapter` for Langchain integration
- [ ] Create `FrontierAdapter` for frontier models
- [ ] Add support for OpenAI-compatible APIs
- [ ] Implement adapter for Anthropic Claude models
- [ ] Create adapters for other supported models

### Phase 3: MCP-Based Template System (Week 3)

#### 3.3.1 MCP Template Core

- [ ] Create MCP-aware `PromptTemplate` class
- [ ] Implement template rendering to MCP messages
- [ ] Develop variable substitution for MCP content
- [ ] Create conditional processing for MCP templates
- [ ] Implement fragment inclusion for MCP templates

```python
# Example MCP template system
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class TemplateFragment:
    name: str
    content: Any
    version: str = "1.0"
    
    def render(self, variables: Dict[str, Any]) -> Any:
        """Render the fragment with the given variables"""
        # Implementation depends on content type
        pass

class MCPPromptTemplate:
    """Template for generating MCP messages"""
    
    def __init__(self, 
                 template_data: Dict[str, Any],
                 parent: Optional['MCPPromptTemplate'] = None):
        self.template_data = template_data
        self.parent = parent
        self.required_vars = template_data.get("required_vars", [])
        self.fragments = template_data.get("fragments", {})
        
    def render(self, variables: Dict[str, Any]) -> List[MCPMessage]:
        """Render the template into MCP messages"""
        self._validate_variables(variables)
        
        # Process inheritance
        if self.parent:
            base_messages = self.parent.render(variables)
        else:
            base_messages = []
            
        # Process template sections
        messages = self._process_messages(self.template_data.get("messages", []), variables)
        
        # Merge with base messages as appropriate
        return self._merge_messages(base_messages, messages)
    
    def _validate_variables(self, variables: Dict[str, Any]) -> None:
        """Validate that all required variables are present"""
        missing = [var for var in self.required_vars if var not in variables]
        if missing:
            raise ValueError(f"Missing required variables: {', '.join(missing)}")
    
    def _process_messages(self, 
                         message_templates: List[Dict[str, Any]],
                         variables: Dict[str, Any]) -> List[MCPMessage]:
        """Process message templates into MCP messages"""
        # Implementation for processing messages
        pass
    
    def _merge_messages(self, 
                       base: List[MCPMessage], 
                       new: List[MCPMessage]) -> List[MCPMessage]:
        """Merge base messages with new messages"""
        # Implementation for message merging
        pass
```

#### 3.3.2 Template Library System

- [ ] Implement `PromptLibrary` for template storage and retrieval
- [ ] Create hierarchical organization for templates
- [ ] Develop template inheritance system
- [ ] Implement template version management using semantic versioning
- [ ] Create utilities for template creation and modification

```python
# Example template library
class PromptLibrary:
    """Library for storing and retrieving prompt templates"""
    
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        self.templates = {}
        self.fragments = {}
        self._initialize_base_templates()
        self._initialize_fragments()
    
    def _initialize_base_templates(self):
        """Initialize base templates"""
        # Implementation for loading base templates
        pass
    
    def _initialize_fragments(self):
        """Initialize common fragments"""
        # Implementation for loading fragments
        pass
    
    def get_template(self, name: str, version: str = None) -> MCPPromptTemplate:
        """Get a template by name and optional version"""
        if name not in self.templates:
            raise ValueError(f"Template '{name}' not found")
            
        if version is None:
            # Return latest version
            latest_version = self._get_latest_version(name)
            return self.templates[name][latest_version]
        
        if version not in self.templates[name]:
            raise ValueError(f"Version '{version}' of template '{name}' not found")
            
        return self.templates[name][version]
    
    def _get_latest_version(self, name: str) -> str:
        """Get the latest version of a template"""
        if name not in self.templates or not self.templates[name]:
            raise ValueError(f"Template '{name}' not found or has no versions")
            
        # Sort versions semantically and return the latest
        versions = list(self.templates[name].keys())
        # Semantic versioning comparison logic here
        return versions[-1]
    
    def register_template(self, name: str, template: MCPPromptTemplate, version: str):
        """Register a template in the library with version"""
        if name not in self.templates:
            self.templates[name] = {}
            
        # Validate semantic version format
        self._validate_semantic_version(version)
            
        self.templates[name][version] = template
        
    def get_fragment(self, name: str, version: str = None) -> TemplateFragment:
        """Get a fragment by name and optional version"""
        if name not in self.fragments:
            raise ValueError(f"Fragment '{name}' not found")
            
        if version is None:
            # Return latest version
            latest_version = self._get_latest_fragment_version(name)
            return self.fragments[name][latest_version]
        
        if version not in self.fragments[name]:
            raise ValueError(f"Version '{version}' of fragment '{name}' not found")
            
        return self.fragments[name][version]
    
    def _get_latest_fragment_version(self, name: str) -> str:
        """Get the latest version of a fragment"""
        if name not in self.fragments or not self.fragments[name]:
            raise ValueError(f"Fragment '{name}' not found or has no versions")
            
        # Sort versions semantically and return the latest
        versions = list(self.fragments[name].keys())
        # Semantic versioning comparison logic here
        return versions[-1]
    
    def register_fragment(self, name: str, fragment: TemplateFragment, version: str):
        """Register a fragment in the library with version"""
        if name not in self.fragments:
            self.fragments[name] = {}
            
        # Validate semantic version format
        self._validate_semantic_version(version)
            
        self.fragments[name][version] = fragment
        
    def _validate_semantic_version(self, version: str) -> None:
        """Validate that a version string follows semantic versioning"""
        import re
        pattern = r'^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$'
        if not re.match(pattern, version):
            raise ValueError(f"Invalid semantic version: {version}")
        
    def derive_template(self, name: str, base_name: str, base_version: str = None,
                       modifications: Dict[str, Any] = None) -> MCPPromptTemplate:
        """Create a new template version derived from an existing one"""
        # Get base template
        base_template = self.get_template(base_name, base_version)
        
        # Calculate new version (increment minor by default)
        if base_version is None:
            base_version = self._get_latest_version(base_name)
        
        # Parse version components
        major, minor, patch = map(int, base_version.split('.', 3)[:3])
        new_version = f"{major}.{minor + 1}.0"
        
        # Create derived template
        derived_data = dict(base_template.template_data)
        
        # Apply modifications
        if modifications:
            for key, value in modifications.items():
                if key in derived_data:
                    derived_data[key] = value
                    
        # Create and register new template
        derived_template = MCPPromptTemplate(derived_data, parent=base_template)
        self.register_template(name, derived_template, new_version)
        
        return derived_template
```

#### 3.3.3 Fragment Repository

- [ ] Create a repository of common template fragments
- [ ] Implement system prompt fragments
- [ ] Develop screen description fragments
- [ ] Create action generation fragments
- [ ] Implement UI pattern-specific fragments
- [ ] Create error handling fragments

```python
# Example fragment initialization
def initialize_core_fragments():
    library = PromptLibrary.get_instance()
    
    # System role fragments
    library.register_fragment(
        name="system_introduction",
        fragment=TemplateFragment(
            name="system_introduction",
            content=[
                MCPTextContent(
                    text="You are an AI assistant helping to test Android applications by generating appropriate UI actions."
                )
            ]
        ),
        version="1.0.0"
    )
    
    # Form pattern fragments
    library.register_fragment(
        name="form_pattern_instructions",
        fragment=TemplateFragment(
            name="form_pattern_instructions",
            content=[
                MCPTextContent(
                    text="This screen contains a form with input fields. Focus on properly filling out the form by:"
                         "\n1. Filling required fields first"
                         "\n2. Using appropriate values based on field types"
                         "\n3. Submitting the form after filling required fields"
                )
            ]
        ),
        version="1.0.0"
    )
    
    # List pattern fragments
    library.register_fragment(
        name="list_pattern_instructions",
        fragment=TemplateFragment(
            name="list_pattern_instructions",
            content=[
                MCPTextContent(
                    text="This screen contains a scrollable list. Consider these actions:"
                         "\n1. Scroll to explore more items"
                         "\n2. Click on items to navigate to details"
                         "\n3. Look for search or filter options"
                )
            ]
        ),
        version="1.0.0"
    )
```

#### 3.3.4 Template Composition Utilities

- [ ] Create utilities for template composition
- [ ] Implement fragment composition functions
- [ ] Develop template merging capabilities
- [ ] Implement template extension patterns
- [ ] Create template validation utilities

### Phase 4: Strategy Refactoring (Week 4)

#### 3.4.1 Base Strategy Refactoring

- [ ] Update `BasePromptStrategy` to use MCP templates
- [ ] Refactor common prompt generation logic
- [ ] Implement strategy configuration via MCP
- [ ] Create utilities for strategy composition
- [ ] Develop unified handling of model responses

```python
# Example refactored BasePromptStrategy
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class BasePromptStrategy(ABC):
    """Base class for prompt strategies using MCP"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.library = PromptLibrary.get_instance()
        self._initialize_templates()
    
    @abstractmethod
    def _initialize_templates(self):
        """Initialize templates needed by this strategy"""
        pass
    
    def generate_messages(self, context: Dict[str, Any]) -> List[MCPMessage]:
        """Generate MCP messages for the given context"""
        system_messages = self._generate_system_messages(context)
        user_messages = self._generate_user_messages(context)
        
        # Combine messages
        return system_messages + user_messages
    
    def _generate_system_messages(self, context: Dict[str, Any]) -> List[MCPMessage]:
        """Generate system messages"""
        # Implementation for generating system messages
        template = self.library.get_template("system_base")
        return template.render(context)
    
    def _generate_user_messages(self, context: Dict[str, Any]) -> List[MCPMessage]:
        """Generate user messages"""
        # Implementation for generating user messages
        template = self.library.get_template("user_base")
        return template.render(context)
    
    def process_response(self, response: MCPMessage, context: Dict[str, Any]) -> Any:
        """Process the model response"""
        # Implementation for processing the response
        pass
```

#### 3.4.2 Single Action Strategy Refactoring

- [ ] Update `SingleActionPromptStrategy` to use MCP
- [ ] Refactor action generation logic
- [ ] Implement template specialization for action types
- [ ] Create context enrichment for action generation
- [ ] Develop response processing for actions

#### 3.4.3 Composable Strategy Refactoring

- [ ] Refactor `ComposablePromptStrategy` to use MCP
- [ ] Implement composable message generation
- [ ] Create specialized templates for composition
- [ ] Develop composition utilities for MCP messages
- [ ] Update response processing for composed actions

#### 3.4.4 Flow-Based Batch Strategy Refactoring

- [ ] Update `FlowBasedBatchActionStrategy` to use MCP
- [ ] Refactor pattern detection integration
- [ ] Implement specialized templates for batch actions
- [ ] Create response processing for batch sequences
- [ ] Develop validation for batch action sequences

### Phase 5: Tool Integration (Week 5)

#### 3.5.1 LLM Service Refactoring

- [ ] Update `LLMActionService` to use MCP
- [ ] Refactor service initialization with MCP models
- [ ] Implement MCP-based prompt generation
- [ ] Update response processing for MCP messages
- [ ] Create utilities for service configuration

#### 3.5.2 RVAndroid Tool Integration

- [ ] Update `ToolSpec` in `rvandroid/tools/rvandroid/tool.py`
- [ ] Refactor tool configuration for MCP
- [ ] Implement MCP-aware service creation
- [ ] Update execution logic for MCP compatibility
- [ ] Create logging and debugging for MCP operations

#### 3.5.3 RVDroid Tool Integration

- [ ] Update `RVDroidTool` in `rvandroid/tools/rvdroid/tool.py`
- [ ] Refactor tool initialization for MCP
- [ ] Implement MCP integration with UIAutomator
- [ ] Update memory system integration for MCP
- [ ] Create consistency checks for MCP operations

#### 3.5.4 Test Framework Integration

- [ ] Create transparent integration with the existing Test Framework
- [ ] Implement configuration adapters to convert Test Framework configurations to MCP configurations
- [ ] Ensure backward compatibility with existing test configurations
- [ ] Add MCP-specific performance metrics collection
- [ ] Enable comparative analysis between different MCP configurations

### Phase 6: Documentation and Configuration (Week 6)

#### 3.6.1 MCP Documentation

- [ ] Create comprehensive MCP architecture documentation
- [ ] Develop adapter implementation guides
- [ ] Create template system documentation
- [ ] Write migration guides for existing code
- [ ] Develop best practices documentation

#### 3.6.2 Template Migration Guide

- [ ] Document templates to fragment mapping
- [ ] Create guide for refactoring duplicated templates
- [ ] Develop pattern-specific template guidelines
- [ ] Write documentation for template composition
- [ ] Create examples of MCP template usage

#### 3.6.3 Configuration and Dependencies

- [ ] Create comprehensive dependency specification
- [ ] Document Python package requirements with version constraints
- [ ] Document system requirements (Ubuntu/Linux packages)
- [ ] Provide installation instructions for all dependencies
- [ ] Create adapter-specific dependency documentation

## 4. Detailed Component Specifications

### 4.1 MCP Core Components

#### 4.1.1 MCPMessage

The `MCPMessage` class represents a structured message in a conversation:

- **Properties**:
  - `role`: Role of the message (system, user, assistant, tool)
  - `content`: List of content items (text, images, etc.)
  - `name`: Optional name for the message sender
  - `tool_calls`: Optional list of tool calls
  - `tool_call_id`: Optional ID for tool call responses

- **Methods**:
  - `to_dict()`: Convert to dictionary representation
  - `from_dict(data)`: Create from dictionary
  - `validate()`: Validate message structure
  - `get_text_content()`: Get combined text content

#### 4.1.2 MCPAdapter

The `MCPAdapter` abstract class defines the interface for model-specific adapters:

- **Methods**:
  - `prepare_messages(messages)`: Convert MCP messages to model format
  - `prepare_config(config)`: Convert MCP configuration to model parameters
  - `parse_response(response)`: Parse model response into MCP message
  - `validate_request(messages, config)`: Validate request compatibility

- **Properties**:
  - `model_type`: Type of model this adapter supports
  - `capabilities`: Supported capabilities (image input, function calling, etc.)
  - `config_mappings`: Mapping from MCP config to model parameters

#### 4.1.3 MCPConfiguration

The `MCPConfiguration` class represents model configuration parameters:

- **Properties**:
  - `temperature`: Controls randomness (0.0 to 2.0)
  - `max_tokens`: Maximum tokens in response
  - `top_p`: Controls diversity via nucleus sampling
  - `frequency_penalty`: Penalizes frequent tokens
  - `presence_penalty`: Penalizes repeated tokens
  - `stop`: List of stop sequences

- **Methods**:
  - `to_dict()`: Convert to dictionary representation
  - `from_dict(data)`: Create from dictionary
  - `merge(other)`: Merge with another configuration
  - `validate()`: Validate configuration parameters

### 4.2 Template System Components

#### 4.2.1 MCPPromptTemplate

The `MCPPromptTemplate` class generates MCP messages from templates:

- **Properties**:
  - `template_data`: Template definition data
  - `parent`: Optional parent template
  - `required_vars`: Variables required for rendering
  - `fragments`: Fragment definitions for this template
  - `version`: Semantic version of this template

- **Methods**:
  - `render(variables)`: Render template with variables
  - `render_section(section, variables)`: Render specific section
  - `include_fragment(name, variables)`: Include fragment in rendering
  - `process_conditionals(content, variables)`: Process conditional sections
  - `create_derived(name, modifications, version_increment)`: Create a new derived template

#### 4.2.2 TemplateFragment

The `TemplateFragment` class represents reusable template components:

- **Properties**:
  - `name`: Unique name for the fragment
  - `content`: Fragment content (text, structured data)
  - `version`: Fragment version for compatibility

- **Methods**:
  - `render(variables)`: Render the fragment with variables
  - `validate()`: Validate fragment structure
  - `to_dict()`: Convert to dictionary representation
  - `from_dict(data)`: Create from dictionary
  - `create_derived(modifications, version_increment)`: Create a new derived fragment

#### 4.2.3 PromptLibrary

The `PromptLibrary` class manages templates and fragments:

- **Properties**:
  - `templates`: Dictionary of named templates with version history
  - `fragments`: Dictionary of named fragments with version history
  - `categories`: Organizational categories for templates

- **Methods**:
  - `get_template(name, version)`: Get template by name and optional version
  - `register_template(name, template, version)`: Register a template with version
  - `get_fragment(name, version)`: Get fragment by name and optional version
  - `register_fragment(name, fragment, version)`: Register a fragment with version
  - `get_templates_by_category(category)`: Get templates in a category
  - `derive_template(name, base_name, base_version, modifications)`: Create a derived template
  - `derive_fragment(name, base_name, base_version, modifications)`: Create a derived fragment

### 4.3 Strategy Components

#### 4.3.1 MCP-Aware Strategy Base

The updated `BasePromptStrategy` will include:

- **Initialization**:
  - Load templates from the PromptLibrary
  - Configure strategy parameters
  - Initialize model configuration

- **Template Management**:
  - Access templates through the library
  - Manage template specialization
  - Apply strategy-specific template modifications

- **Message Generation**:
  - Create structured MCP messages
  - Apply appropriate role assignments
  - Handle message ordering and organization

- **Response Processing**:
  - Parse model responses with MCP adapters
  - Extract relevant information from responses
  - Process structured response formats

#### 4.3.2 Strategy Specializations

Each specialized strategy will implement:

- **Template Specialization**:
  - `SingleActionPromptStrategy`: Templates for individual actions
  - `ComposablePromptStrategy`: Templates for flexible composition
  - `FlowBasedBatchActionStrategy`: Templates for batch sequences

- **Context Management**:
  - Strategy-specific context enrichment
  - Appropriate variable binding
  - Context-aware template selection

- **Response Handling**:
  - Strategy-specific response parsing
  - Action extraction based on strategy goals
  - Validation and error handling

### 4.4 Test Framework Integration Components

#### 4.4.1 Configuration Adapter

The `TestFrameworkConfigAdapter` will handle the translation of Test Framework configurations to MCP:

- **Properties**:
  - `tool_config`: Reference to the Test Framework's ToolConfiguration
  - `mcp_config`: Generated MCPConfiguration for use with MCP

- **Methods**:
  - `convert_to_mcp_config()`: Convert TestFramework config to MCP config
  - `convert_from_mcp_config(mcp_config)`: Update TestFramework config from MCP config
  - `get_appropriate_adapter()`: Determine which MCP adapter to use
  - `get_appropriate_templates()`: Determine which templates to use

#### 4.4.2 MCP Metrics Collector

The `MCPMetricsCollector` will collect performance metrics for MCP:

- **Properties**:
  - `metrics`: Dictionary of collected metrics
  - `adapter_metrics`: Adapter-specific performance statistics
  - `template_metrics`: Template-specific performance statistics

- **Methods**:
  - `collect_adapter_metrics(adapter, operation, time)`: Record adapter performance
  - `collect_template_metrics(template, render_time)`: Record template performance
  - `generate_report()`: Generate performance report
  - `export_to_test_framework()`: Export metrics to Test Framework format

## a5. Dependencies and Installation

### 5.1 System Requirements

- **Operating System**: Ubuntu 22.04 LTS or later
- **Python**: 3.9 or later
- **RAM**: 16GB minimum (32GB recommended)
- **CPU**: 4+ cores recommended
- **Disk Space**: 20GB for base installation (more for model storage)

### 5.2 Python Dependencies

```
# Core dependencies
pip install -r requirements.txt

# Python package requirements
pandas>=1.5.3
numpy>=1.24.3
pydantic>=2.0.0
pillow>=9.5.0
requests>=2.31.0
aiohttp>=3.8.5
```

### 5.3 System Dependencies (Ubuntu/Debian)

```bash
# Install required system packages
sudo apt update
sudo apt install -y \
  python3-dev \
  python3-pip \
  python3-venv \
  build-essential \
  libffi-dev \
  libssl-dev
```

### 5.4 Model-Specific Dependencies

#### 5.4.1 Ollama Dependencies

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Python dependencies
pip install ollama-community>=0.1.2
```

#### 5.4.2 HuggingFace Dependencies

```bash
# Python dependencies
pip install transformers>=4.31.0
pip install torch>=2.0.1
pip install accelerate>=0.21.0
```

#### 5.4.3 DSPy Dependencies

```bash
# Python dependencies
pip install dspy-ai>=2.3.0
```

#### 5.4.4 Langchain Dependencies

```bash
# Python dependencies
pip install langchain>=0.0.267
pip install langchain-openai>=0.0.2
```

### 5.5 Installation Steps

1. **Clone the repository**:
   ```bash
   git clone https://github.com/your-org/rv-android.git
   cd rv-android
   ```

2. **Create a virtual environment** (optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install system dependencies**:
   ```bash
   sudo apt update
   sudo apt install -y python3-dev python3-pip python3-venv build-essential libffi-dev libssl-dev
   ```

5. **Install model-specific dependencies** (based on your needs):
   ```bash
   # For Ollama
   curl -fsSL https://ollama.com/install.sh | sh
   pip install ollama-community>=0.1.2
   
   # For HuggingFace
   pip install transformers>=4.31.0 torch>=2.0.1 accelerate>=0.21.0
   
   # For DSPy
   pip install dspy-ai>=2.3.0
   
   # For Langchain
   pip install langchain>=0.0.267 langchain-openai>=0.0.2
   ```

6. **Verify installation**:
   ```bash
   python -c "from rvandroid.mcp.mcp_data_structures import MCPMessage; print('MCP successfully installed')"
   ```

## 6. Migration Strategy

### 6.1 Template Migration

The migration of templates from string-based to MCP-based will follow these steps:

1. **Template Analysis**:
   - Identify common patterns across templates
   - Extract shared components into fragments
   - Create a hierarchy of template specialization

2. **Fragment Extraction**:
   - Extract common system prompts
   - Create fragments for UI pattern instructions
   - Develop fragments for response formatting
   - Implement fragments for contextual information

3. **Template Refactoring**:
   - Replace string templates with MCP templates
   - Implement hierarchical template structure
   - Utilize fragment inclusion for reusability
   - Apply conditional processing for MCP templates

4. **Template Library Integration**:
   - Organize templates into coherent categories
   - Implement version management for templates
   - Create a registry for template discovery
   - Develop utilities for template management

### 6.2 Model Migration

The migration of language model implementations will include:

1. **Adapter Implementation**:
   - Create adapters for each model type
   - Implement bidirectional format conversion
   - Handle model-specific configuration mapping
   - Develop response parsing for each model

2. **Model Interface Update**:
   - Refactor `LanguageModel` interface for MCP
   - Implement MCP-based request handling
   - Create factory for model instantiation
   - Develop configuration management for models

3. **Response Handling**:
   - Implement consistent response parsing
   - Create type-safe response representation
   - Develop error handling for model responses
   - Implement usage tracking for models

### 6.3 Strategy Migration

The migration of prompt strategies will involve:

1. **Base Strategy Refactoring**:
   - Update `BasePromptStrategy` for MCP
   - Implement common template loading
   - Create unified message generation
   - Develop standard response processing

2. **Specialized Strategy Updates**:
   - Refactor each strategy to use MCP templates
   - Eliminate duplicated template code
   - Implement strategy-specific template handling
   - Create specialized response processing

3. **Tool Integration**:
   - Update tool implementations for MCP
   - Refactor service initialization
   - Implement MCP-based execution
   - Create consistent logging and monitoring

### 6.4 Test Framework Integration

The transparent integration with the existing Test Framework will follow these steps:

1. **Configuration Adaptation**:
   - Create configuration adapters that translate between Test Framework and MCP formats
   - Ensure all ToolConfiguration parameters are properly mapped to MCPConfiguration
   - Maintain backward compatibility for existing test suites

2. **Service Integration**:
   - Modify the service layer to use MCP internally while presenting the same interface to the Test Framework
   - Implement the necessary conversions between Test Framework data structures and MCP data structures
   - Ensure consistent error handling and logging

3. **Performance Metrics**:
   - Extend the Test Framework's metrics collection to include MCP-specific metrics
   - Implement metrics exporters that provide insights into MCP performance
   - Enable comparative analysis between different MCP configurations

## 7. Key Advantages and Benefits

### 7.1 Standardization Benefits

1. **Consistent Message Format**:
   - Same format across all model implementations
   - Type-safe message representation
   - Standardized role and content handling
   - Consistent tool call representation

2. **Simplified Model Integration**:
   - Adapter-based model support
   - Clean separation of model-specific details
   - Streamlined addition of new models
   - Consistent configuration handling

3. **Improved Template Management**:
   - Centralized template library
   - Hierarchical template organization
   - Fragment-based reusability
   - Version-controlled templates

### 7.2 Development Productivity

1. **Reduced Duplication**:
   - Elimination of duplicate template code
   - Centralized format handling
   - Shared components across strategies
   - Reusable fragments for common patterns

2. **Enhanced Maintainability**:
   - Cleaner architecture with clear responsibilities
   - Consistent interfaces across components
   - Simplified debugging and troubleshooting
   - Better separation of concerns

3. **Improved Extensibility**:
   - Easy addition of new model support
   - Simplified template specialization
   - Streamlined strategy development
   - Modular component architecture

### 7.3 Runtime Benefits

1. **Type Safety and Validation**:
   - Structured message validation
   - Type-safe content handling
   - Configuration parameter validation
   - Error detection before model invocation

2. **Enhanced Capabilities**:
   - Standardized support for tool usage
   - Consistent handling of image inputs
   - Structured message capabilities
   - Format-agnostic function calling

3. **Debugging and Monitoring**:
   - Consistent logging across models
   - Structured message inspection
   - Enhanced error reporting
   - Uniform usage tracking

## 8. Risks and Mitigations

### 8.1 Migration Risks

1. **Breaking Changes**:
   - **Risk**: Complete removal of legacy code may disrupt ongoing experiments
   - **Mitigation**: Implement comprehensive testing, clearly communicate timing of changes, and coordinate with research team schedule

2. **Performance Impact**:
   - **Risk**: Additional abstraction may impact performance
   - **Mitigation**: Optimize critical paths, implement caching, and minimize overhead in format conversions

3. **Integration Complexity**:
   - **Risk**: Integration with multiple tools may be complex
   - **Mitigation**: Create phased rollout plan, implement tool-specific tests, and thorough validation for monitored operations

4. **Specification Support**:
   - **Risk**: Changes could impact support for different specification sets
   - **Mitigation**: Ensure all template changes preserve references to monitored operations in a generic way

### 8.2 Implementation Challenges

1. **Model-Specific Quirks**:
   - **Risk**: Some models may have unique formatting requirements
   - **Mitigation**: Design flexible adapter system, implement model-specific handling where needed, and test with diverse models

2. **Template Complexity**:
   - **Risk**: Complex templates may be difficult to migrate
   - **Mitigation**: Create template migration utilities, implement detailed validation, and provide migration assistance tools

3. **Backward Compatibility**:
   - **Risk**: Existing code may rely on string-based templates
   - **Mitigation**: Provide transition utilities, implement compatibility layers where needed, and clear documentation

### 8.3 Risk Management

1. **Phased Implementation**:
   - Implement core components first
   - Validate with selected models before full rollout
   - Migrate strategies iteratively
   - Test thoroughly at each phase, ensuring monitored operations tracking is preserved

2. **Documentation and Code Standards**:
   - Maintain detailed class and method documentation in English
   - Follow existing documentation standards as seen in EventBus, ExecutionManager, and TaskExecutor
   - Add detailed architectural comments at critical points
   - Comply with RV-Android code style guidelines
   - Leverage existing components like error_handler.py and logging.manager.py

3. **Existing Utility Integration**:
   - Integrate with rvandroid/util/error/error_handler.py for error management
   - Use rvandroid/util/logging/manager.py for consistent logging
   - Apply appropriate decorators from rvandroid/util/decorators.py
   - Leverage other existing utility components

## 9. Future Directions

### 9.1 Advanced Template Features

1. **Template Parameterization**:
   - Advanced parameter-based template generation
   - Dynamic template composition
   - Context-aware template selection
   - Template optimization based on usage patterns

2. **Interactive Templates**:
   - Templates that adapt based on interactions
   - Progressive template refinement
   - Feedback-based template improvements
   - A/B testing for template effectiveness

### 9.2 Enhanced Model Capabilities

1. **Multimodal Support**:
   - Structured support for image analysis
   - Audio input/output capabilities
   - Video frame processing
   - Document analysis integration

2. **Advanced Reasoning**:
   - Structured reasoning templates
   - Multi-step reasoning chains
   - Tool-augmented reasoning
   - Verification and validation workflows

### 9.3 Performance Optimization

1. **Caching and Optimization**:
   - Implement response caching for templates
   - Optimize message serialization
   - Improve adapter performance
   - Implement batch processing optimizations

2. **Resource Management**:
   - Dynamic model loading based on requirements
   - Intelligent resource allocation
   - Memory optimization for large models
   - Load balancing across models

## 10. Conclusion

The Model Context Protocol (MCP) implementation represents a significant architectural improvement for the RV-Android system. By standardizing the interface between the system and language models, eliminating duplicate code, and enhancing template management, this initiative will result in a more maintainable, extensible, and robust system.

The plan outlined here provides a comprehensive roadmap for implementing MCP across all aspects of the system while addressing the specific challenge of template duplication. By following this phased approach, the team can achieve a complete transformation of the LLM integration layer, with full replacement of legacy code rather than maintaining backward compatibility adapters.

The resulting architecture will support both specification sets used in experiments (JCA cryptography-related and general programming specifications) through the generic concept of "monitored operations." All code and documentation will follow RV-Android standards with detailed English-language comments at architectural decision points, leveraging existing utility components like error handlers, logging systems, and decorators.

This MCP implementation will not only solve current challenges but also provide a strong foundation for future enhancements, making it easier to incorporate new models and capabilities as they become available while maintaining the system's ability to test applications with different specification sets.
