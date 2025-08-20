# RV-LLM Architecture

This document provides an overview of the `rv-llm` module, which handles language model integration for the RV-Android system.

## 1. Introduction

The `rv-llm` module provides a framework for generating prompts and interacting with language models. It is a self-contained module with dependencies on `rv-android-core` and `rv-screen-parser`.

Key features include:

*   **Three-Layer Architecture**: Separation of concerns between information gathering, template management, and prompt generation strategies
*   **Configuration Management**: Type-safe configuration for LLMs and prompt generation using Pydantic models
*   **Extensibility**: Support for new information fragments, prompt strategies, and templates
*   **Jinja2-Based Templates**: Template system using Jinja2 engine

## 2. Core Concepts

The `rv-llm` module is built around core concepts:

*   **Information Fragments**: Components responsible for collecting and formatting specific information from application state, such as UI elements, screenshots, and monitored operations
*   **Information Manager**: Coordinates information fragments and composes final information for prompt generation
*   **Templates**: Define prompt structure using Jinja2 syntax
*   **Template Repository**: Manages templates, loading from XML files and providing access to prompt strategies
*   **Prompt Strategies**: Define logic for generating prompts, including information selection and template usage
*   **Prompt Framework**: Main entry point coordinating all components and providing prompt generation interface
*   **Language Model**: Abstraction layer for different LLM backends (Ollama, OpenAI, Anthropic)

## 3. Architecture

The `rv-llm` module follows a three-layer architecture:

```
┌─────────────────────────────────────────────────────────────────────┐
│                           Prompt Framework                          │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│                         Strategy Layer                              │
│ ┌────────────────────┐  ┌────────────────────┐  ┌────────────────┐  │
│ │  SingleStrategy    │  │   BatchStrategy    │  │  VisionStrategy│  │
│ │                    │  │                    │  │ Strategies     │  │
│ └────────────────────┘  └────────────────────┘  └────────────────┘  │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│                         Template Layer                              │
│ ┌────────────────────┐  ┌────────────────────┐  ┌────────────────┐  │
│ │  Jinja2Template    │  │Jinja2TemplateRepo  │  │ XML Templates  │  │
│ │                    │  │                    │  │ with Jinja2    │  │
│ └────────────────────┘  └────────────────────┘  └────────────────┘  │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────────┐
│                        Information Layer                            │
│ ┌────────────────────┐  ┌────────────────────┐  ┌────────────────┐  │
│ │ InformationFragment│  │ InformationManager │  │ Specialized    │  │
│ │                    │  │                    │  │ Fragments      │  │
│ └────────────────────┘  └────────────────────┘  └────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.1. Information Layer

The Information Layer handles collecting and formatting information for prompt generation. Components include:

*   **`InformationFragment`**: Abstract base class for all information fragments, each handling specific information types
*   **`InformationManager`**: Manages information fragments including registration, prioritization, and information composition

#### 3.1.1. `InformationFragment`

The `InformationFragment` abstract base class defines the interface for all information fragments with two main methods:

*   `generate`: Generates formatted information from given state and context
*   `should_include`: Determines whether the fragment should be included in the current prompt

Here is an example of an information fragment:

```python
from rv_llm.llm.prompt.information.base_fragment import InformationFragment
from typing import Any, Dict, Optional

class AppInfoFragment(InformationFragment):
    def __init__(self, name: str = "app_info", priority: int = 100):
        super().__init__(name, priority)

    def generate(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        package_name = state.get("package_name", "N/A")
        activity_name = state.get("activity_name", "N/A")
        return f"App: {package_name}, Activity: {activity_name}"
```

#### 3.1.2. `InformationManager`

The `InformationManager` manages information fragments with main methods:

*   `register_fragment`: Registers a new information fragment
*   `compose_information`: Composes information from all registered fragments

Here is an example of how to use the `InformationManager`:

```python
from rv_llm.llm.prompt.information.fragment_manager import InformationManager

# Create an information manager
manager = InformationManager()

# Register the AppInfoFragment
manager.register_fragment(AppInfoFragment())

# Compose the information
state = {"package_name": "com.example.app", "activity_name": "MainActivity"}
info = manager.compose_information(state)

# Print the information
print(info)
```

### 3.2. Template Layer

The Template Layer defines prompt structure using Jinja2 templating. Main components are:

*   **`Jinja2Template`**: Represents a single Jinja2 template and handles rendering with provided data
*   **`Jinja2TemplateRepository`**: Manages templates by loading from XML files and providing access to prompt strategies, including template fragment management

#### 3.2.1. `Jinja2Template`

The `Jinja2Template` class wraps a Jinja2 template and provides a `render` method that accepts a dictionary of variables and returns the rendered template.

Here is an example of a Jinja2 template:

```xml
<template name="simple_template">
  <s>You are a helpful assistant.</s>
  <user>The current application is {{ app_info }}.</user>
</template>
```

#### 3.2.2. `Jinja2TemplateRepository`

The `Jinja2TemplateRepository` is responsible for managing the templates. It loads the templates from XML files in a specified directory. It also manages template fragments, which are reusable pieces of template code that can be included in other templates.

Here is an example of how to use the `Jinja2TemplateRepository`:

```python
from rv_llm.llm.prompt.template.jinja_repository import Jinja2TemplateRepository

# Create a template repository
repo = Jinja2TemplateRepository(template_dir="/path/to/templates")

# Create messages from a template
variables = {"app_info": "App: com.example.app, Activity: MainActivity"}
messages = repo.create_messages("simple_template", variables)

# Print the messages
for message in messages:
    print(f"Role: {message['role']}")
    print(f"Content: {message['content']}")
```

### 3.3. Strategy Layer

The Strategy Layer is responsible for defining the logic for generating the prompt. It uses the information from the Information Layer and the templates from the Template Layer to create the final prompt. The main components are:

*   **`PromptStrategy`**: An abstract base class for all prompt strategies.
*   **`SingleStrategy`**: A strategy that generates a single action per prompt.
*   **`BatchStrategy`**: A strategy that generates multiple actions per prompt.
*   **`VisionStrategy`**: A strategy that uses multimodal capabilities for screenshot analysis and coordinate-based actions.

#### 3.3.1. `PromptStrategy`

The `PromptStrategy` is an abstract base class that defines the interface for all prompt strategies. It has one main method:

*   `_generate_prompt`: This method is responsible for generating the prompt from the given state and context.

#### 3.3.2. `SingleStrategy`

The `SingleStrategy` generates a single action per prompt, suitable for focused testing scenarios. It uses compact templates optimized for single-action generation.

#### 3.3.3. `BatchStrategy`

The `BatchStrategy` generates multiple related actions per prompt, ideal for completing workflows like form submission or navigation sequences.

#### 3.3.4. `VisionStrategy`

The `VisionStrategy` utilizes multimodal LLM capabilities to analyze screenshots alongside UI descriptions. It supports three action types: standard UI actions, text input, and custom coordinate-based actions for elements not described in the UI tree.

Here is an example of how to use a prompt strategy:

```python
from rv_llm.config import PromptConfig
from rv_llm.llm.prompt.framework import PromptFramework

# Create a prompt configuration with the batch action strategy
config = PromptConfig(strategy_type="batch_action")

# Create a prompt framework
framework = PromptFramework.create(config)

# Generate the prompt
state = {"screen_description": "This is the main screen of the application."}
prompt = framework.generate_prompt(state)
```

## 4. Configuration

The `rv-llm` module uses Pydantic models for configuration. There are two main configuration classes:

*   **`LLMConfig`**: This class is used to configure the LLM backend.
*   **`PromptConfig`**: This class is used to configure the prompt generation.

The configuration can be provided as a dictionary or a Pydantic model. The `LLMComponentFactory` is responsible for creating the LLM components based on the provided configuration.

### 4.0. Variant System Integration

The `rv-llm` module integrates with the RV-Android variant system to provide predefined LLM and prompt configurations. The variant system allows tools to define multiple named configurations that users can select from, eliminating the need to manually specify all LLM parameters.

#### Integration with RVAndroid Tool Variants

The `rvandroid-tool` module uses the variant system to provide predefined LLM configurations:

```python
# Example variant configurations in rvandroid-tool
variants = {
    "default": {
        "llm_type": "ollama",
        "llm_model": "llama3.2",
        "prompt_strategy": "single"
    },
    "openai_gpt4": {
        "llm_type": "frontier", 
        "llm_model": "gpt-4",
        "prompt_strategy": "batch"
    },
    "vision": {
        "llm_type": "ollama",
        "llm_model": "gemma",
        "prompt_strategy": "vision"
    }
}
```

Users can then specify variants in experiment configurations:
```bash
# CLI usage with variants
poetry run python -m rv_experiment run --tools "rvandroid:openai_gpt4"
poetry run python -m rv_experiment run --tools "rvandroid:vision"
```

#### Configuration Creation Flow

The variant system creates LLM configurations through the following flow:

1. **Variant Resolution**: Tool registry resolves variant name to parameter dictionary
2. **Configuration Factory**: `RvAndroidToolConfig.create_from_variant()` creates typed configuration
3. **Component Creation**: `LLMComponentFactory` creates LLM and prompt components
4. **Framework Initialization**: `PromptFramework.create()` uses the configuration

This provides clean separation between variant definition (tool-specific) and configuration usage (framework-agnostic).

### 4.1. `LLMConfig`

The `LLMConfig` class is used to configure the LLM backend. Here are some of the parameters:

*   `llm_type`: The type of LLM provider (e.g., "ollama", "openai").
*   `model`: The name of the model to use.
*   `temperature`: The sampling temperature.
*   `max_tokens`: The maximum number of tokens to generate.

Here is an example of how to create an `LLMConfig` object:

```python
from rv_llm.config import LLMConfig

config = LLMConfig(
    llm_type="ollama",
    model="llama3",
    temperature=0.5,
    max_tokens=1000
)
```

### 4.2. `PromptConfig`

The `PromptConfig` class is used to configure the prompt generation. Here are some of the parameters:

*   `strategy_type`: The type of prompt strategy to use (e.g., "standard", "batch_action").
*   `parser_type`: The type of screen parser to use.
*   `visitor_type`: The type of visitor to use for screen element extraction.

Here is an example of how to create a `PromptConfig` object:

```python
from rv_llm.config import PromptConfig

config = PromptConfig(
    strategy_type="batch_action",
    parser_type="droidbot",
    visitor_type="detailed"
)
```

## 5. Extensibility

The `rv-llm` module is designed to be extensible. You can add new information fragments, prompt strategies, and templates.

### 5.1. Adding a New Information Fragment

To add a new information fragment, create a new class that inherits from `InformationFragment` and implement the `generate` method. Then, register the new fragment with the `InformationManager`.

Here is an example of how to create and register a new information fragment:

```python
from rv_llm.llm.prompt.information.base_fragment import InformationFragment
from rv_llm.llm.prompt.information.fragment_manager import InformationManager
from typing import Any, Dict, Optional

# Create a new information fragment
class DeviceInfoFragment(InformationFragment):
    def __init__(self, name: str = "device_info", priority: int = 100):
        super().__init__(name, priority)

    def generate(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        return f"Device: {state.get('device_model', 'N/A')}, OS: {state.get('os_version', 'N/A')}"

# Create an information manager
manager = InformationManager()

# Register the new fragment
manager.register_fragment(DeviceInfoFragment())
```

### 5.2. Adding a New Prompt Strategy

To add a new prompt strategy, create a new class that inherits from `PromptStrategy` and implement the `_generate_prompt` method. Then, use the new strategy by specifying it in the `PromptConfig`.

Here is an example of how to create a new prompt strategy:

```python
from rv_llm.llm.prompt.strategy.base_strategy import PromptStrategy
from typing import Any, Dict, List, Optional

class MyStrategy(PromptStrategy):
    DEFAULT_TEMPLATE = "my_template"

    def _generate_prompt(
        self,
        state: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, str]]:
        # ... logic to generate the prompt ...
        return []
```

### 5.3. Adding a New Template

To add a new template, create a new XML file with the template content. The template should use Jinja2 syntax. Then, use the new template by specifying it in the context when generating the prompt.

Here is an example of a new template file named `my_template.xml`:

```xml
<template name="my_template">
  <s>You are a testing expert.</s>
  <user>The device is {{ device_info }}. Please suggest a test case.</user>
</template>
```

## 6. Usage Examples

Here is an example of how to use the `PromptFramework` to generate a prompt with a custom information fragment and template.

First, define a custom information fragment:

```python
from rv_llm.llm.prompt.information.base_fragment import InformationFragment
from typing import Any, Dict, Optional

class TestInfoFragment(InformationFragment):
    def __init__(self, name: str = "test_info", priority: int = 100):
        super().__init__(name, priority)

    def generate(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        return f"Test case: {context.get('test_case_name', 'N/A')}"
```

Next, create a custom template named `custom_template.xml`:

```xml
<template name="custom_template">
  <s>You are a test automation engineer.</s>
  <user>Please generate a test script for the following test case: {{ test_info }}.</user>
</template>
```

Now, use the `PromptFramework` to generate a prompt with the custom fragment and template:

```python
from rv_llm.config import PromptConfig
from rv_llm.llm.prompt.framework import PromptFramework

# Create a prompt configuration
config = PromptConfig(strategy_type="standard")

# Create a prompt framework
framework = PromptFramework.create(config)

# Register the custom information fragment
framework.register_information_fragment(TestInfoFragment())

# Create a state and context
state = {}
context = {"test_case_name": "Login with valid credentials"}

# Generate the prompt
prompt = framework.generate_prompt(state, context)

# Print the prompt
for message in prompt:
    print(f"Role: {message.role}")
    print(f"Content: {message.content}")
```

## Appendix: `rvandroid-tool` Prompt Framework Implementation

The `rvandroid-tool` module provides a concrete implementation of the prompt framework, tailored for Android testing. This implementation demonstrates how the abstract concepts of the `rv-llm` module are realized in a practical application.

### Framework Initialization

The `RVAndroidPromptFramework` class serves as the entry point for the prompt generation system in `rvandroid-tool`. Its `create` method orchestrates the initialization of the framework, including:

*   **Strategy Registration**: The `SingleStrategy`, `BatchStrategy`, and `VisionStrategy` are registered with the `LLMComponentFactory`. This allows the framework to create instances of these strategies without being tightly coupled to their implementations.
*   **Fragment Registration**: A set of Android-specific information fragments are registered with the `InformationManager`. These fragments are responsible for extracting data from the testing environment, such as UI elements (`UIElementsFragment`), testing history (`HistoryFragment`), monitored operations (`MonitoredOperationsFragment`), and transition guidance (`TransitionGuidanceFragment`).
*   **Template Registration**: The framework registers the directories containing the Jinja2 templates and template fragments. This allows the `Jinja2TemplateRepository` to load and manage the templates used by the prompt strategies.

### Information Fragments

The `rvandroid-tool` implementation includes several specialized information fragments:

*   **`UIElementsFragment`**: Extracts and formats information about the UI elements on the current screen.
*   **`ScreenshotFragment`**: Processes and includes screenshots in the prompt, if the LLM supports image input.
*   **`HistoryFragment`**: Provides the LLM with the history of previously executed actions.
*   **`MonitoredOperationsFragment`**: Includes information about security-related operations that have been monitored during the test.
*   **`TransitionGuidanceFragment`**: Offers guidance to the LLM on which screens to explore next.

### Prompt Strategies

The framework implements three main prompt strategies:

*   **`SingleStrategy`**: This strategy generates a prompt that asks the LLM for a single action to execute.
*   **`BatchStrategy`**: This strategy generates a prompt that asks the LLM for multiple related actions to execute. This is useful for testing scenarios that involve a sequence of related actions, such as filling out a form.
*   **`VisionStrategy`**: This strategy leverages multimodal LLM capabilities to analyze screenshots and generate actions based on visual analysis, including custom coordinate-based actions for elements not described in the UI tree.

### Templates

The `rvandroid-tool` uses a modular system of Jinja2 templates and template fragments. The templates are defined in XML files and can include other fragments. This allows for a high degree of flexibility and reuse in the construction of prompts.

The templates use a fragment-based architecture where `single.xml`, `batch.xml`, and `vision.xml` templates extend a base template (`system_base.xml`) and include strategy-specific fragments to construct prompts for their respective strategies.
