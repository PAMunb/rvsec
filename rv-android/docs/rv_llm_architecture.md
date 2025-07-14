# RV-LLM Architecture

This document provides a comprehensive overview of the `rv-llm` module, which is responsible for integrating Large Language Models (LLMs) into the RV-Android system.

## 1. Introduction

The `rv-llm` module provides a flexible and extensible framework for generating prompts and interacting with LLMs. It is designed to be a self-contained module with clear boundaries, and it does not have dependencies on other tools or services outside of the `rv-android-core` and `rv-screen-parser` modules.

The key features of the `rv-llm` module are:

*   **Three-Layer Architecture**: A clear separation of concerns between information gathering, template management, and prompt generation strategies.
*   **Configuration Management**: Type-safe configuration for LLMs and prompt generation using Pydantic models.
*   **Extensibility**: The ability to easily add new information fragments, prompt strategies, and templates.
*   **Jinja2-Based Templates**: Powerful and flexible templating using the Jinja2 engine.

## 2. Core Concepts

The `rv-llm` module is built around a few core concepts:

*   **Information Fragments**: These are responsible for collecting and formatting specific pieces of information from the application state, such as UI elements, screenshots, and monitored operations.
*   **Information Manager**: This component coordinates the information fragments and composes the final information to be used in the prompt.
*   **Templates**: These define the structure of the prompt using Jinja2 syntax. They can include variables, conditional logic, and reusable fragments.
*   **Template Repository**: This component manages the templates, loading them from XML files and making them available to the prompt strategies.
*   **Prompt Strategies**: These define the logic for generating the prompt, including which information to include and which template to use.
*   **Prompt Framework**: This is the main entry point for the `rv-llm` module. It coordinates all the other components and provides a simple interface for generating prompts.
*   **Language Model**: This is an abstraction layer for interacting with different LLM backends, such as Ollama, OpenAI, and Anthropic.

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
│ │  StandardStrategy  │  │ BatchActionStrategy│  │ Other          │  │
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

The Information Layer is responsible for collecting and formatting the information that will be used in the prompt. It consists of the following components:

*   **`InformationFragment`**: An abstract base class for all information fragments. Each fragment is responsible for a specific piece of information, such as UI elements, screenshots, or monitored operations.
*   **`InformationManager`**: This class manages the information fragments, including registering, prioritizing, and composing the information from all the fragments.

#### 3.1.1. `InformationFragment`

The `InformationFragment` is an abstract base class that defines the interface for all information fragments. It has two main methods:

*   `generate`: This method is responsible for generating the formatted information from the given state and context.
*   `should_include`: This method determines whether the fragment should be included in the current prompt.

Here is an example of a simple information fragment:

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

The `InformationManager` is responsible for managing the information fragments. It has the following main methods:

*   `register_fragment`: This method registers a new information fragment.
*   `compose_information`: This method composes the information from all the registered fragments.

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

The Template Layer is responsible for defining the structure of the prompt. It uses Jinja2 for templating, which allows for variables, conditional logic, and reusable fragments. The main components are:

*   **`Jinja2Template`**: This class represents a single Jinja2 template. It is responsible for rendering the template with the provided data.
*   **`Jinja2TemplateRepository`**: This class manages the templates, loading them from XML files and making them available to the prompt strategies. It also manages the template fragments, which are reusable pieces of template code.

#### 3.2.1. `Jinja2Template`

The `Jinja2Template` class is a wrapper around a Jinja2 template. It provides a `render` method that takes a dictionary of variables and returns the rendered template.

Here is an example of a simple Jinja2 template:

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

*   **`PromptStrategy`**: An abstract base class for all prompt strategies. Each strategy defines a different way of generating the prompt.
*   **`StandardStrategy`**: A strategy that generates a single action per prompt.
*   **`BatchActionStrategy`**: A strategy that generates a batch of actions per prompt.

#### 3.3.1. `PromptStrategy`

The `PromptStrategy` is an abstract base class that defines the interface for all prompt strategies. It has one main method:

*   `_generate_prompt`: This method is responsible for generating the prompt from the given state and context.

#### 3.3.2. `StandardStrategy`

The `StandardStrategy` is a simple strategy that generates a single action per prompt. It uses a standard template to generate the prompt.

#### 3.3.3. `BatchActionStrategy`

The `BatchActionStrategy` is a more complex strategy that generates a batch of actions per prompt. It uses a batch action template to generate the prompt.

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

The `rv-llm` module uses Pydantic models for configuration, which provides type safety and validation. There are two main configuration classes:

*   **`LLMConfig`**: This class is used to configure the LLM backend, including the model, temperature, and other parameters.
*   **`PromptConfig`**: This class is used to configure the prompt generation, including the prompt strategy, screen parser, and visitor type.

The configuration can be provided as a dictionary or a Pydantic model. The `LLMComponentFactory` is responsible for creating the LLM components based on the provided configuration.

### 4.1. `LLMConfig`

The `LLMConfig` class is used to configure the LLM backend. Here are some of the most important parameters:

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

The `PromptConfig` class is used to configure the prompt generation. Here are some of the most important parameters:

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

The `rv-llm` module is designed to be extensible. You can easily add new information fragments, prompt strategies, and templates.

### 5.1. Adding a New Information Fragment

To add a new information fragment, you need to create a new class that inherits from `InformationFragment` and implement the `generate` method. Then, you need to register the new fragment with the `InformationManager`.

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

To add a new prompt strategy, you need to create a new class that inherits from `PromptStrategy` and implement the `_generate_prompt` method. Then, you can use the new strategy by specifying it in the `PromptConfig`.

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
        # ... your logic to generate the prompt ...
        return []
```

### 5.3. Adding a New Template

To add a new template, you need to create a new XML file with the template content. The template should use Jinja2 syntax for variables and control structures. Then, you can use the new template by specifying it in the context when generating the prompt.

Here is an example of a new template file named `my_template.xml`:

```xml
<template name="my_template">
  <s>You are a testing expert.</s>
  <user>The device is {{ device_info }}. Please suggest a test case.</user>
</template>
```

## 6. Usage Examples

Here is a more comprehensive example of how to use the `PromptFramework` to generate a prompt with a custom information fragment and template.

First, let's define a custom information fragment:

```python
from rv_llm.llm.prompt.information.base_fragment import InformationFragment
from typing import Any, Dict, Optional

class TestInfoFragment(InformationFragment):
    def __init__(self, name: str = "test_info", priority: int = 100):
        super().__init__(name, priority)

    def generate(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Any:
        return f"Test case: {context.get('test_case_name', 'N/A')}"
```

Next, let's create a custom template named `custom_template.xml`:

```xml
<template name="custom_template">
  <s>You are a test automation engineer.</s>
  <user>Please generate a test script for the following test case: {{ test_info }}.</user>
</template>
```

Now, let's use the `PromptFramework` to generate a prompt with the custom fragment and template:

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
