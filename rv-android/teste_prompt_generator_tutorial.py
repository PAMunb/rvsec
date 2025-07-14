#!/usr/bin/env python3

"""
RV-Android New Prompt Architecture Tutorial.

This file presents a comprehensive tutorial of the new RV-Android prompt system,
demonstrating the separated configuration architecture and new component system:
- Separated LLM and prompt configurations
- LLMComponentFactory for component creation
- PromptFramework with PromptConfig
- Multi-instance support
- RvAndroidToolConfig for tool-specific configuration
- Integration with new architecture patterns
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add module paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "modules" / "rv-android-core" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-llm" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rvandroid-tool" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-screen-parser" / "src"))

# Import necessary modules
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.classes import Classes
from rv_android_core.domain.window import Windows
from rv_android_core.domain.wtg import WindowTransitionGraph
from rv_android_core.domain.app import App
from rv_llm.config import LLMConfig, PromptConfig
from rv_llm.llm.constants import LLMType, PromptStrategyType
from rv_llm.llm.prompt.framework import PromptFramework
from rv_llm.llm.prompt.information.fragment_manager import InformationManager
from rv_llm.llm.prompt.information.base_fragment import InformationFragment
from rv_llm.llm.prompt.template.jinja_repository import Jinja2TemplateRepository
from rv_llm.factories.component_factory import LLMComponentFactory
from rv_screen_parser.constants import ScreenParserType, VisitorType
from rvandroid_tool.config.tool_config import RvAndroidToolConfig
from rvandroid_tool.llm.service.action_service import LLMActionService
from rvandroid_tool.llm.service.memory_manager import MemoryManager
from rvandroid_tool.llm.service.transition_manager import TransitionManager


def read_droidbot_state(filename: str) -> Dict[str, Any]:
    """Loads a DroidBot state file."""
    with open(filename, 'r') as file:
        return json.load(file)


def create_complete_tutorial_state(activity_name="MainActivity", package_name="com.example.testapp", 
                                  is_login=False, is_payment=False):
    """
    Creates a complete state with all variables potentially needed by templates.
    """
    state = {
        "package_name": package_name,
        "activity": f"{package_name}.{activity_name}",
        "screen_description": f"Screen of {activity_name} with simulated elements for tutorial."
    }
    
    # Add UI elements information
    if "login" in activity_name.lower() or is_login:
        ui_text = """
UI ELEMENTS:
- Text field: Username (id: username_field)
- Text field: Password (id: password_field)
- Button: Login (id: login_button)
- Button: Cancel (id: cancel_button)
- Link: Forgot password (id: forgot_password)
        """
    elif "payment" in activity_name.lower() or "transfer" in activity_name.lower() or is_payment:
        ui_text = """
UI ELEMENTS:
- Text field: Amount (id: amount_field)
- Text field: Recipient (id: recipient_field)
- Dropdown: Transfer type (id: transfer_type)
- Button: Confirm (id: confirm_button)
- Button: Cancel (id: cancel_button)
        """
    else:
        ui_text = """
UI ELEMENTS:
- Button: Continue (id: continue_button)
- Button: Back (id: back_button)
- List: Main options (id: main_options)
- Item 1: Profile (id: profile_option)
- Item 2: Settings (id: settings_option)
- Item 3: Help (id: help_option)
        """
    
    state["ui_elements"] = ui_text
    state["action_history"] = [
        "Clicked 'Continue' button",
        "Filled 'Name' field",
        "Scrolled down"
    ]
    
    state["ui_patterns"] = ["form", "list"]
    state["transition_guidance"] = {
        "visit_count": 2,
        "recommended_actions": ["Fill all fields", "Test input validation"],
        "avoidable_actions": ["Go back without saving"]
    }
    
    state["static_context"] = """
STATIC CONTEXT:
- Activity implements input validation
- Screen is part of main app flow
- 3 monitored operations exist on this screen
    """
    
    state["testing_history"] = [
        {"action": "Click 'Login'", "result": "Success", "screen": "LoginScreen"},
        {"action": "Empty field validation", "result": "Error shown", "screen": "LoginScreen"}
    ]
    
    state["workflow_guidance"] = """
WORKFLOW GUIDANCE:
1. Complete all required fields
2. Verify input validation
3. Test edge cases (boundary values)
4. Confirm operation
    """
    
    state["detected_pattern"] = "form" if (is_login or is_payment) else "list"
    state["memory_insights"] = """
APP MEMORY INSIGHTS:
- 2 screens visited previously in this session
- Common navigation pattern: Login -> Home -> This screen
- Most visited screens: Home (5x), Settings (2x), Login (3x)
    """
    
    state["testing_context"] = {
        "session_duration": "00:15:23",
        "coverage": {"activities": "45%", "code": "38%", "transitions": "29%"},
        "monitored_operations_found": 7,
        "focus_areas": ["input_validation", "permission_usage", "data_handling"]
    }
    
    state["app_metadata"] = {
        "app_name": package_name.split(".")[-1].capitalize(),
        "version": "1.2.3",
        "sdk_target": 33,
        "permissions": ["INTERNET", "CAMERA", "READ_EXTERNAL_STORAGE"]
    }
    
    state["additional_guidelines"] = "Prioritize testing input validation and security."
    state["exploration_status"] = "In progress - 45% of app explored"
    state["security_considerations"] = "Verify secure use of crypto APIs"
    
    return state


###################################################################################
# SECTION 1: NEW ARCHITECTURE BASICS
###################################################################################

def tutorial_section_1():
    """
    Section 1: New Architecture Basics.
    
    This section demonstrates:
    - Separated LLMConfig and PromptConfig
    - LLMComponentFactory usage
    - PromptFramework with PromptConfig
    - Basic prompt generation with new architecture
    """
    print("\n" + "=" * 80)
    print("SECTION 1: NEW ARCHITECTURE BASICS")
    print("=" * 80)

    print("\n1.1: Separated Configuration Architecture")
    print("-" * 50)

    print("The new architecture separates LLM and prompt concerns:")
    print("- LLMConfig: LLM backend configuration (model, temperature, etc.)")
    print("- PromptConfig: Prompt generation configuration (strategy, parser, visitor)")
    print("- LLMComponentFactory: Creates components from configurations")

    # Create LLM configuration
    print("\nCreating LLM configuration...")
    llm_config = LLMConfig(
        llm_type=LLMType.OLLAMA,
        model="llama3.2:3b",
        temperature=0.2,
        max_tokens=800,
        base_url="http://localhost:11434"
    )

    print(f"LLM Configuration:")
    print(f"- Type: {llm_config.llm_type}")
    print(f"- Model: {llm_config.model}")
    print(f"- Temperature: {llm_config.temperature}")
    print(f"- Max tokens: {llm_config.max_tokens}")

    # Create prompt configuration
    print("\nCreating prompt configuration...")
    prompt_config = PromptConfig(
        strategy_type=PromptStrategyType.BATCH_ACTION,
        parser_type=ScreenParserType.DROIDBOT,
        visitor_type=VisitorType.DETAILED,
        max_context_length=8192
    )

    print(f"Prompt Configuration:")
    print(f"- Strategy: {prompt_config.strategy_type}")
    print(f"- Parser: {prompt_config.parser_type}")
    print(f"- Visitor: {prompt_config.visitor_type}")
    print(f"- Max context: {prompt_config.max_context_length}")

    print("\n1.2: Component Factory Usage")
    print("-" * 50)

    print("Using LLMComponentFactory to create components...")
    
    # Create LLM backend
    try:
        llm = LLMComponentFactory.create_llm(llm_config)
        print(f"Created LLM: {llm.__class__.__name__}")
    except Exception as e:
        print(f"LLM creation (expected in tutorial): {e}")

    # Create prompt strategy
    try:
        strategy = LLMComponentFactory.create_strategy(prompt_config)
        print(f"Created strategy: {strategy.__class__.__name__}")
    except Exception as e:
        print(f"Strategy creation (expected in tutorial): {e}")

    # Show supported types
    print(f"\nSupported LLM types: {LLMComponentFactory.get_supported_llm_types()}")
    print(f"Supported strategies: {LLMComponentFactory.get_supported_strategy_types()}")

    print("\n1.3: PromptFramework with PromptConfig")
    print("-" * 50)

    print("Creating PromptFramework with PromptConfig...")
    try:
        framework = PromptFramework.create(prompt_config)
        print("PromptFramework created successfully")
        print(f"Framework strategy: {framework.strategy.name if hasattr(framework, 'strategy') else 'N/A'}")
    except Exception as e:
        print(f"Framework creation (expected in tutorial): {e}")
        print("This is expected in tutorial environment - showing concept")

    print("\n1.4: Basic Prompt Generation")
    print("-" * 50)

    print("Generating prompt with new architecture...")
    state = create_complete_tutorial_state("MainActivity", "com.example.newapp")
    
    try:
        if 'framework' in locals():
            messages = framework.generate_prompt(state)
            print(f"Generated {len(messages)} messages")
            
            for i, msg in enumerate(messages):
                print(f"\nMessage {i+1} - Role: {msg.role}")
                for content in msg.content:
                    text = content.text if hasattr(content, 'text') else str(content)
                    if len(text) > 200:
                        text = text[:200] + "... (truncated)"
                    print(f"Content: {text}")
    except Exception as e:
        print(f"Prompt generation (expected in tutorial): {e}")

    print("\n1.5: Key Architectural Changes")
    print("-" * 50)

    print("""
KEY CHANGES FROM OLD ARCHITECTURE:

1. Configuration Separation:
   OLD: Single config with mixed concerns
   NEW: LLMConfig + PromptConfig with clear separation

2. Component Creation:
   OLD: Direct instantiation with complex parameters
   NEW: LLMComponentFactory with type-safe creation

3. Framework Initialization:
   OLD: PromptFramework.create(configurator)
   NEW: PromptFramework.create(prompt_config)

4. Multi-instance Support:
   OLD: Single global configuration
   NEW: Independent configurations per instance

5. Type Safety:
   OLD: String-based configuration
   NEW: Constants and validation for all configuration
""")


###################################################################################
# SECTION 2: MULTI-INSTANCE CONFIGURATION
###################################################################################

def tutorial_section_2():
    """
    Section 2: Multi-Instance Configuration.
    
    This section demonstrates:
    - Multiple independent configurations
    - RvAndroidToolConfig usage
    - Parallel service instances
    - Configuration isolation
    """
    print("\n" + "=" * 80)
    print("SECTION 2: MULTI-INSTANCE CONFIGURATION")
    print("=" * 80)

    print("\n2.1: Independent LLM Configurations")
    print("-" * 50)

    print("Creating multiple independent LLM configurations...")
    
    # Configuration 1: Ollama with batch actions
    llm_config_1 = LLMConfig(
        llm_type=LLMType.OLLAMA,
        model="llama3.2:3b",
        temperature=0.2,
        max_tokens=800
    )

    # Configuration 2: Different settings
    llm_config_2 = LLMConfig(
        llm_type=LLMType.OLLAMA,
        model="qwen2.5:7b",
        temperature=0.7,
        max_tokens=1200
    )

    # Configuration 3: Conservative settings
    llm_config_3 = LLMConfig(
        llm_type=LLMType.OLLAMA,
        model="llama3.2:1b",
        temperature=0.1,
        max_tokens=500
    )

    configs = [llm_config_1, llm_config_2, llm_config_3]
    
    print(f"Created {len(configs)} independent LLM configurations:")
    for i, config in enumerate(configs, 1):
        print(f"  Config {i}: {config.model} (temp={config.temperature}, tokens={config.max_tokens})")

    print("\n2.2: RvAndroidToolConfig Usage")
    print("-" * 50)

    print("Creating tool-specific configurations...")
    
    tool_configs = []
    for i, llm_config in enumerate(configs, 1):
        tool_config = RvAndroidToolConfig(
            parser_type=ScreenParserType.DROIDBOT,
            visitor_type=VisitorType.DETAILED if i == 1 else VisitorType.BASIC,
            llm_config=llm_config
        )
        tool_configs.append(tool_config)
        
        print(f"Tool Config {i}:")
        print(f"  - Parser: {tool_config.parser_type}")
        print(f"  - Visitor: {tool_config.visitor_type}")
        print(f"  - LLM Model: {tool_config.llm_config.model}")

    print("\n2.3: Template Registration")
    print("-" * 50)

    print("Demonstrating template registration with tool config...")
    
    # Create a sample tool config
    sample_tool_config = RvAndroidToolConfig(
        parser_type=ScreenParserType.DROIDBOT,
        visitor_type=VisitorType.DETAILED,
        llm_config=llm_config_1
    )
    
    # Get template paths
    template_paths = sample_tool_config.get_template_paths()
    print(f"Template paths: {template_paths}")
    
    # Get parser parameters
    parser_params = sample_tool_config.get_parser_parameters()
    print(f"Parser parameters: {parser_params}")

    # Show how templates would be registered
    print("\nTemplate registration process:")
    print("1. Tool config provides template paths")
    print("2. PromptFramework registers templates from those paths")
    print("3. Templates become available for prompt generation")

    print("\n2.4: Multi-Instance Service Creation")
    print("-" * 50)

    print("Creating multiple LLMActionService instances...")
    
    # Create static data for demonstration
    static_data = StaticAnalysisData(
        classes=Classes(),
        windows=Windows(),
        wtg=WindowTransitionGraph()
    )
    
    services = []
    for i, (llm_config, tool_config) in enumerate(zip(configs, tool_configs), 1):
        try:
            service = LLMActionService(
                static_data=static_data,
                config=llm_config,
                app_package="com.example.testapp",
                tool_config=tool_config
            )
            services.append(service)
            print(f"Service {i}: Created with {llm_config.model}")
        except Exception as e:
            print(f"Service {i}: Creation failed (expected in tutorial): {e}")

    print(f"\nTotal services created: {len(services)}")
    print("Each service operates independently with its own configuration")

    print("\n2.5: Configuration Isolation")
    print("-" * 50)

    print("""
CONFIGURATION ISOLATION BENEFITS:

1. Independent Settings:
   - Each instance has its own LLM model, temperature, etc.
   - Changes to one instance don't affect others
   - Parallel execution with different strategies

2. Experiment Scenarios:
   - Compare different models on same app
   - Test temperature variations
   - Evaluate strategy effectiveness

3. Resource Management:
   - Each instance manages its own memory
   - Independent template caching
   - Separate error handling

4. Scalability:
   - Easy to add/remove instances
   - Load balancing across instances
   - Fault tolerance through redundancy

Example Usage:
```python
# Conservative instance for production
conservative_service = LLMActionService(
    config=LLMConfig(temperature=0.1, max_tokens=500),
    tool_config=RvAndroidToolConfig(visitor_type=VisitorType.BASIC)
)

# Experimental instance for research
experimental_service = LLMActionService(
    config=LLMConfig(temperature=0.8, max_tokens=1500),
    tool_config=RvAndroidToolConfig(visitor_type=VisitorType.DETAILED)
)
```
""")


###################################################################################
# SECTION 3: PROMPT CONFIGURATION SYSTEM
###################################################################################

def tutorial_section_3():
    """
    Section 3: Prompt Configuration System.
    
    This section demonstrates:
    - PromptConfig in detail
    - Strategy configuration
    - Parser and visitor configuration
    - Template management
    """
    print("\n" + "=" * 80)
    print("SECTION 3: PROMPT CONFIGURATION SYSTEM")
    print("=" * 80)

    print("\n3.1: PromptConfig in Detail")
    print("-" * 50)

    print("Creating detailed prompt configurations...")
    
    # Standard configuration
    standard_config = PromptConfig(
        strategy_type=PromptStrategyType.STANDARD,
        parser_type=ScreenParserType.DROIDBOT,
        visitor_type=VisitorType.BASIC,
        max_context_length=4096
    )

    # Batch action configuration
    batch_config = PromptConfig(
        strategy_type=PromptStrategyType.BATCH_ACTION,
        parser_type=ScreenParserType.DROIDBOT,
        visitor_type=VisitorType.DETAILED,
        max_context_length=8192
    )

    configs = [standard_config, batch_config]
    
    print("Created prompt configurations:")
    for i, config in enumerate(configs, 1):
        print(f"  Config {i}:")
        print(f"    - Strategy: {config.strategy_type}")
        print(f"    - Parser: {config.parser_type}")
        print(f"    - Visitor: {config.visitor_type}")
        print(f"    - Max context: {config.max_context_length}")

    print("\n3.2: Strategy Configuration")
    print("-" * 50)

    print("Available strategy types:")
    for strategy in PromptStrategyType.ALL:
        print(f"  - {strategy}")

    print("\nStrategy characteristics:")
    print(f"  - {PromptStrategyType.STANDARD}: Single action generation")
    print(f"  - {PromptStrategyType.BATCH_ACTION}: Multiple action generation")
    print(f"  - Default: {PromptStrategyType.DEFAULT}")

    print("\n3.3: Parser and Visitor Configuration")
    print("-" * 50)

    print("Available parser types:")
    for parser in ScreenParserType.ALL:
        print(f"  - {parser}")

    print("\nAvailable visitor types:")
    for visitor in VisitorType.ALL:
        print(f"  - {visitor}")

    print("\nConfiguration combinations:")
    combinations = [
        (ScreenParserType.DROIDBOT, VisitorType.BASIC, "Fast parsing, basic info"),
        (ScreenParserType.DROIDBOT, VisitorType.DETAILED, "Comprehensive parsing"),
        (ScreenParserType.DROIDBOT, VisitorType.DETAILED, "Advanced analysis"),
    ]
    
    for parser, visitor, description in combinations:
        print(f"  - {parser} + {visitor}: {description}")

    print("\n3.4: Template Management")
    print("-" * 50)

    print("Template system with PromptConfig:")
    print("1. PromptConfig specifies strategy type")
    print("2. Strategy determines required template")
    print("3. Template repository resolves template path")
    print("4. Jinja2 renders template with variables")

    print("\nTemplate resolution process:")
    print("- standard_modular → templates/standard_modular.xml")
    print("- batch_action_modular → templates/batch_action_modular.xml")
    print("- Custom strategies can use custom templates")

    print("\n3.5: Configuration Validation")
    print("-" * 50)

    print("Creating configuration with validation...")
    
    try:
        # Valid configuration
        valid_config = PromptConfig(
            strategy_type=PromptStrategyType.STANDARD,
            parser_type=ScreenParserType.DROIDBOT,
            visitor_type=VisitorType.DETAILED
        )
        print("✓ Valid configuration created successfully")
    except Exception as e:
        print(f"✗ Configuration validation failed: {e}")

    # Show validation features
    print("\nValidation features:")
    print("- Strategy type validation against available strategies")
    print("- Parser type validation against supported parsers")
    print("- Visitor type validation against supported visitors")
    print("- Max context length validation (positive integer)")
    print("- Cross-field validation for compatible combinations")

    print("\n3.6: Configuration Serialization")
    print("-" * 50)

    print("Configuration serialization capabilities:")
    
    # Demonstrate serialization
    config_dict = standard_config.model_dump()
    print(f"Serialized config: {config_dict}")

    # Show how to recreate from dict
    print("\nRecreating from serialized data:")
    try:
        recreated_config = PromptConfig(**config_dict)
        print("✓ Configuration recreated successfully")
        print(f"  Strategy: {recreated_config.strategy_type}")
        print(f"  Parser: {recreated_config.parser_type}")
    except Exception as e:
        print(f"✗ Recreation failed: {e}")

    print("\nSerialization benefits:")
    print("- Save configurations to files")
    print("- Load configurations from experiments")
    print("- Network transmission of configurations")
    print("- Configuration versioning and history")


###################################################################################
# SECTION 4: TOOL CONFIGURATION INTEGRATION
###################################################################################

def tutorial_section_4():
    """
    Section 4: Tool Configuration Integration.
    
    This section demonstrates:
    - RvAndroidToolConfig advanced features
    - Integration with LLMActionService
    - Template registration process
    - Configuration factory methods
    """
    print("\n" + "=" * 80)
    print("SECTION 4: TOOL CONFIGURATION INTEGRATION")
    print("=" * 80)

    print("\n4.1: RvAndroidToolConfig Advanced Features")
    print("-" * 50)

    print("Creating advanced tool configuration...")
    
    # Create LLM config
    llm_config = LLMConfig(
        llm_type=LLMType.OLLAMA,
        model="llama3.2:3b",
        temperature=0.3,
        max_tokens=1000
    )

    # Create tool config with additional parameters
    tool_config = RvAndroidToolConfig(
        parser_type=ScreenParserType.DROIDBOT,
        visitor_type=VisitorType.DETAILED,
        llm_config=llm_config,
        kwargs={
            "parser_timeout": 30,
            "visitor_max_depth": 5,
            "custom_setting": "value"
        }
    )

    print(f"Tool configuration created:")
    print(f"  - Parser: {tool_config.parser_type}")
    print(f"  - Visitor: {tool_config.visitor_type}")
    print(f"  - LLM Model: {tool_config.llm_config.model}")
    print(f"  - Additional kwargs: {len(tool_config.kwargs)}")

    print("\n4.2: Factory Methods")
    print("-" * 50)

    print("Using factory methods to create configurations...")
    
    # Factory method creation
    factory_config = RvAndroidToolConfig.from_llm_config(
        llm_config=llm_config,
        parser_type=ScreenParserType.DROIDBOT,
        visitor_type=VisitorType.DETAILED,
        custom_param="test_value"
    )

    print(f"Factory-created config:")
    print(f"  - Parser: {factory_config.parser_type}")
    print(f"  - Visitor: {factory_config.visitor_type}")
    print(f"  - LLM Model: {factory_config.llm_config.model}")

    print("\n4.3: Parameter Extraction")
    print("-" * 50)

    print("Extracting parameters for different components...")
    
    # Get parser parameters
    parser_params = tool_config.get_parser_parameters()
    print(f"Parser parameters: {parser_params}")

    # Get template paths
    template_paths = tool_config.get_template_paths()
    print(f"Template paths: {template_paths}")

    # Show how parameters are used
    print("\nParameter usage:")
    print("- Parser parameters → Screen parser initialization")
    print("- Template paths → PromptFramework template registration")
    print("- LLM config → LLM backend initialization")

    print("\n4.4: Template Registration Process")
    print("-" * 50)

    print("Demonstrating template registration...")
    
    # Create a mock PromptFramework for demonstration
    class MockPromptFramework:
        def __init__(self):
            self.registered_fragments = []
            self.registered_templates = []
            
        def register_fragment_directory(self, path):
            self.registered_fragments.append(path)
            print(f"  ✓ Registered fragment directory: {path}")
            
        def register_template_directory(self, path):
            self.registered_templates.append(path)
            print(f"  ✓ Registered template directory: {path}")

    mock_framework = MockPromptFramework()
    
    # Register templates
    print("Registering templates with framework...")
    try:
        tool_config.register_templates_with_framework(mock_framework)
        print(f"Registration complete:")
        print(f"  - Fragment dirs: {len(mock_framework.registered_fragments)}")
        print(f"  - Template dirs: {len(mock_framework.registered_templates)}")
    except Exception as e:
        print(f"Template registration (expected in tutorial): {e}")

    print("\n4.5: Integration with LLMActionService")
    print("-" * 50)

    print("Integrating tool config with LLMActionService...")
    
    # Create static data
    static_data = StaticAnalysisData(
        classes=Classes(),
        windows=Windows(),
        wtg=WindowTransitionGraph()
    )
    
    # Create service with tool config
    try:
        service = LLMActionService(
            static_data=static_data,
            config=llm_config,
            app_package="com.example.integrationtest",
            tool_config=tool_config
        )
        print("✓ LLMActionService created with tool config")
        print("  - Service configured with separated concerns")
        print("  - LLM backend configured independently")
        print("  - Parser/visitor configured in tool config")
        print("  - Templates registered automatically")
    except Exception as e:
        print(f"Service creation (expected in tutorial): {e}")

    print("\n4.6: Configuration String Representation")
    print("-" * 50)

    print("Configuration string representations:")
    
    # Show string representations
    print(f"Tool config string: {str(tool_config)}")
    print(f"Tool config repr: {repr(tool_config)}")
    
    # Show dictionary representation
    config_dict = tool_config.to_dict()
    print(f"Dictionary representation keys: {list(config_dict.keys())}")

    print("\nString representation benefits:")
    print("- Easy debugging and logging")
    print("- Clear configuration identification")
    print("- Comparison between configurations")
    print("- Configuration audit trails")


###################################################################################
# SECTION 5: PRACTICAL USAGE PATTERNS
###################################################################################

def tutorial_section_5():
    """
    Section 5: Practical Usage Patterns.
    
    This section demonstrates:
    - Common configuration patterns
    - Error handling strategies
    - Performance considerations
    - Testing approaches
    """
    print("\n" + "=" * 80)
    print("SECTION 5: PRACTICAL USAGE PATTERNS")
    print("=" * 80)

    print("\n5.1: Common Configuration Patterns")
    print("-" * 50)

    print("Demonstrating common configuration patterns...")
    
    # Pattern 1: Development configuration
    dev_config = {
        "llm": LLMConfig(
            llm_type=LLMType.OLLAMA,
            model="llama3.2:1b",  # Smaller model for development
            temperature=0.1,      # Deterministic for testing
            max_tokens=500        # Faster responses
        ),
        "tool": lambda llm_cfg: RvAndroidToolConfig(
            parser_type=ScreenParserType.DROIDBOT,
            visitor_type=VisitorType.BASIC,  # Basic for speed
            llm_config=llm_cfg
        )
    }

    # Pattern 2: Production configuration
    prod_config = {
        "llm": LLMConfig(
            llm_type=LLMType.OLLAMA,
            model="llama3.2:3b",  # Larger model for quality
            temperature=0.2,      # Balanced creativity
            max_tokens=800        # Comprehensive responses
        ),
        "tool": lambda llm_cfg: RvAndroidToolConfig(
            parser_type=ScreenParserType.DROIDBOT,
            visitor_type=VisitorType.DETAILED,  # Detailed for quality
            llm_config=llm_cfg
        )
    }

    # Pattern 3: Research configuration
    research_config = {
        "llm": LLMConfig(
            llm_type=LLMType.OLLAMA,
            model="qwen2.5:7b",   # Large model for research
            temperature=0.5,      # Creative for exploration
            max_tokens=1200       # Long responses
        ),
        "tool": lambda llm_cfg: RvAndroidToolConfig(
            parser_type=ScreenParserType.DROIDBOT,
            visitor_type=VisitorType.DETAILED,  # Enhanced for research
            llm_config=llm_cfg
        )
    }

    configs = [
        ("Development", dev_config),
        ("Production", prod_config),
        ("Research", research_config)
    ]

    for name, config in configs:
        llm_cfg = config["llm"]
        tool_cfg = config["tool"](llm_cfg)
        print(f"\n{name} Configuration:")
        print(f"  - Model: {llm_cfg.model}")
        print(f"  - Temperature: {llm_cfg.temperature}")
        print(f"  - Visitor: {tool_cfg.visitor_type}")

    print("\n5.2: Error Handling Strategies")
    print("-" * 50)

    print("Implementing robust error handling...")
    
    def create_robust_service(llm_config, tool_config, app_package):
        """Create service with comprehensive error handling."""
        try:
            static_data = StaticAnalysisData(
        classes=Classes(),
        windows=Windows(),
        wtg=WindowTransitionGraph()
    )
            service = LLMActionService(
                static_data=static_data,
                config=llm_config,
                app_package=app_package,
                tool_config=tool_config
            )
            return service, None
        except Exception as e:
            error_msg = f"Service creation failed: {e}"
            print(f"✗ {error_msg}")
            return None, error_msg

    # Test error handling
    print("Testing error handling patterns...")
    
    # Valid configuration
    valid_llm = LLMConfig(llm_type=LLMType.OLLAMA, model="llama3.2:3b")
    valid_tool = RvAndroidToolConfig(
        parser_type=ScreenParserType.DROIDBOT,
        visitor_type=VisitorType.BASIC,
        llm_config=valid_llm
    )
    
    service, error = create_robust_service(valid_llm, valid_tool, "com.example.test")
    if service:
        print("✓ Valid configuration handled successfully")
    else:
        print(f"✗ Error with valid config: {error}")

    print("\nError handling best practices:")
    print("- Validate configurations before use")
    print("- Provide meaningful error messages")
    print("- Implement graceful fallbacks")
    print("- Log errors for debugging")
    print("- Use try-catch blocks around component creation")

    print("\n5.3: Performance Considerations")
    print("-" * 50)

    print("Performance optimization strategies...")
    
    # Performance tips
    performance_tips = [
        ("Model Selection", "Use smaller models for development, larger for production"),
        ("Temperature Settings", "Lower temperature (0.1-0.3) for faster, more deterministic responses"),
        ("Token Limits", "Set appropriate max_tokens to balance quality and speed"),
        ("Visitor Types", "Use BASIC visitor for speed, DETAILED for quality"),
        ("Context Length", "Reduce max_context_length for faster processing"),
        ("Caching", "Enable template caching for repeated operations"),
        ("Parallelization", "Use multiple instances for concurrent processing")
    ]

    for category, tip in performance_tips:
        print(f"  - {category}: {tip}")

    print("\nPerformance monitoring:")
    print("- Measure response times for different configurations")
    print("- Monitor memory usage with multiple instances")
    print("- Track token usage and costs")
    print("- Profile template rendering performance")

    print("\n5.4: Testing Approaches")
    print("-" * 50)

    print("Testing strategies for the new architecture...")
    
    # Unit testing approach
    print("Unit Testing:")
    print("- Test configuration creation and validation")
    print("- Test component factory methods")
    print("- Test configuration serialization/deserialization")
    print("- Mock external dependencies (LLM providers)")

    # Integration testing approach
    print("\nIntegration Testing:")
    print("- Test full service creation pipeline")
    print("- Test template registration process")
    print("- Test prompt generation with real configurations")
    print("- Test multi-instance scenarios")

    # Configuration testing
    print("\nConfiguration Testing:")
    print("- Test all supported LLM types")
    print("- Test all strategy combinations")
    print("- Test parser/visitor combinations")
    print("- Test edge cases and error conditions")

    print("\n5.5: Migration from Old Architecture")
    print("-" * 50)

    print("Migration strategies from old architecture...")
    
    migration_steps = [
        "1. Identify current ComponentConfigurator usage",
        "2. Extract LLM settings into LLMConfig",
        "3. Extract prompt settings into PromptConfig",
        "4. Replace PromptFramework.create(configurator) with PromptFramework.create(prompt_config)",
        "5. Update service creation to use separated configs",
        "6. Test thoroughly with new architecture",
        "7. Remove old ComponentConfigurator dependencies"
    ]

    for step in migration_steps:
        print(f"  {step}")

    print("\nMigration benefits:")
    print("- Cleaner separation of concerns")
    print("- Better type safety")
    print("- Easier testing and debugging")
    print("- Support for multi-instance scenarios")
    print("- More flexible configuration options")


###################################################################################
# SECTION 6: ADVANCED SCENARIOS
###################################################################################

def tutorial_section_6():
    """
    Section 6: Advanced Scenarios.
    
    This section demonstrates:
    - Complex multi-instance setups
    - Custom configuration patterns
    - Integration with external systems
    - Advanced prompt customization
    """
    print("\n" + "=" * 80)
    print("SECTION 6: ADVANCED SCENARIOS")
    print("=" * 80)

    print("\n6.1: Complex Multi-Instance Setup")
    print("-" * 50)

    print("Setting up complex multi-instance scenario...")
    
    # Create different configurations for different purposes
    instances = []
    
    # Instance 1: Conservative for critical operations
    conservative_llm = LLMConfig(
        llm_type=LLMType.OLLAMA,
        model="llama3.2:1b",
        temperature=0.1,
        max_tokens=400
    )
    conservative_tool = RvAndroidToolConfig(
        parser_type=ScreenParserType.DROIDBOT,
        visitor_type=VisitorType.BASIC,
        llm_config=conservative_llm
    )
    instances.append(("Conservative", conservative_llm, conservative_tool))

    # Instance 2: Balanced for general use
    balanced_llm = LLMConfig(
        llm_type=LLMType.OLLAMA,
        model="llama3.2:3b",
        temperature=0.2,
        max_tokens=800
    )
    balanced_tool = RvAndroidToolConfig(
        parser_type=ScreenParserType.DROIDBOT,
        visitor_type=VisitorType.DETAILED,
        llm_config=balanced_llm
    )
    instances.append(("Balanced", balanced_llm, balanced_tool))

    # Instance 3: Experimental for research
    experimental_llm = LLMConfig(
        llm_type=LLMType.OLLAMA,
        model="qwen2.5:7b",
        temperature=0.6,
        max_tokens=1200
    )
    experimental_tool = RvAndroidToolConfig(
        parser_type=ScreenParserType.DROIDBOT,
        visitor_type=VisitorType.DETAILED,
        llm_config=experimental_llm
    )
    instances.append(("Experimental", experimental_llm, experimental_tool))

    print(f"Created {len(instances)} instance configurations:")
    for name, llm_cfg, tool_cfg in instances:
        print(f"  {name}: {llm_cfg.model} (temp={llm_cfg.temperature}, visitor={tool_cfg.visitor_type})")

    print("\n6.2: Custom Configuration Patterns")
    print("-" * 50)

    print("Implementing custom configuration patterns...")
    
    # Custom configuration builder
    class ConfigurationBuilder:
        def __init__(self):
            self.llm_config = None
            self.tool_config = None
            
        def with_llm(self, llm_type, model, **kwargs):
            self.llm_config = LLMConfig(
                llm_type=llm_type,
                model=model,
                **kwargs
            )
            return self
            
        def with_tool(self, parser_type, visitor_type, **kwargs):
            if not self.llm_config:
                raise ValueError("LLM config must be set before tool config")
            self.tool_config = RvAndroidToolConfig(
                parser_type=parser_type,
                visitor_type=visitor_type,
                llm_config=self.llm_config,
                **kwargs
            )
            return self
            
        def build(self):
            if not self.llm_config or not self.tool_config:
                raise ValueError("Both LLM and tool configs must be set")
            return self.llm_config, self.tool_config

    # Use the builder
    try:
        builder = ConfigurationBuilder()
        llm_cfg, tool_cfg = (builder
                           .with_llm(LLMType.OLLAMA, "llama3.2:3b", temperature=0.3)
                           .with_tool(ScreenParserType.DROIDBOT, VisitorType.DETAILED)
                           .build())
        print("✓ Custom configuration builder worked")
        print(f"  Built config: {llm_cfg.model} + {tool_cfg.visitor_type}")
    except Exception as e:
        print(f"✗ Builder failed: {e}")

    print("\n6.3: Configuration Profiles")
    print("-" * 50)

    print("Implementing configuration profiles...")
    
    # Profile-based configuration
    CONFIGURATION_PROFILES = {
        "development": {
            "llm": {
                "llm_type": LLMType.OLLAMA,
                "model": "llama3.2:1b",
                "temperature": 0.1,
                "max_tokens": 400
            },
            "tool": {
                "parser_type": ScreenParserType.DROIDBOT,
                "visitor_type": VisitorType.BASIC
            }
        },
        "production": {
            "llm": {
                "llm_type": LLMType.OLLAMA,
                "model": "llama3.2:3b",
                "temperature": 0.2,
                "max_tokens": 800
            },
            "tool": {
                "parser_type": ScreenParserType.DROIDBOT,
                "visitor_type": VisitorType.DETAILED
            }
        },
        "research": {
            "llm": {
                "llm_type": LLMType.OLLAMA,
                "model": "qwen2.5:7b",
                "temperature": 0.5,
                "max_tokens": 1200
            },
            "tool": {
                "parser_type": ScreenParserType.DROIDBOT,
                "visitor_type": VisitorType.DETAILED
            }
        }
    }

    def create_from_profile(profile_name):
        """Create configuration from profile."""
        if profile_name not in CONFIGURATION_PROFILES:
            raise ValueError(f"Unknown profile: {profile_name}")
        
        profile = CONFIGURATION_PROFILES[profile_name]
        
        llm_config = LLMConfig(**profile["llm"])
        tool_config = RvAndroidToolConfig(
            llm_config=llm_config,
            **profile["tool"]
        )
        
        return llm_config, tool_config

    # Test profile creation
    for profile_name in CONFIGURATION_PROFILES:
        try:
            llm_cfg, tool_cfg = create_from_profile(profile_name)
            print(f"✓ {profile_name}: {llm_cfg.model} + {tool_cfg.visitor_type}")
        except Exception as e:
            print(f"✗ {profile_name}: {e}")

    print("\n6.4: Dynamic Configuration Adjustment")
    print("-" * 50)

    print("Implementing dynamic configuration adjustment...")
    
    # Configuration adjuster
    class ConfigurationAdjuster:
        def __init__(self, base_llm_config, base_tool_config):
            self.base_llm = base_llm_config
            self.base_tool = base_tool_config
            
        def adjust_for_performance(self):
            """Adjust configuration for better performance."""
            adjusted_llm = LLMConfig(
                llm_type=self.base_llm.llm_type,
                model="llama3.2:1b",  # Smaller model
                temperature=0.1,      # Lower temperature
                max_tokens=400        # Fewer tokens
            )
            adjusted_tool = RvAndroidToolConfig(
                parser_type=self.base_tool.parser_type,
                visitor_type=VisitorType.BASIC,  # Basic visitor
                llm_config=adjusted_llm
            )
            return adjusted_llm, adjusted_tool
            
        def adjust_for_quality(self):
            """Adjust configuration for better quality."""
            adjusted_llm = LLMConfig(
                llm_type=self.base_llm.llm_type,
                model="qwen2.5:7b",   # Larger model
                temperature=0.3,      # Moderate temperature
                max_tokens=1200       # More tokens
            )
            adjusted_tool = RvAndroidToolConfig(
                parser_type=self.base_tool.parser_type,
                visitor_type=VisitorType.DETAILED,  # Detailed visitor
                llm_config=adjusted_llm
            )
            return adjusted_llm, adjusted_tool

    # Test dynamic adjustment
    base_llm = LLMConfig(llm_type=LLMType.OLLAMA, model="llama3.2:3b")
    base_tool = RvAndroidToolConfig(
        parser_type=ScreenParserType.DROIDBOT,
        visitor_type=VisitorType.BASIC,
        llm_config=base_llm
    )
    
    adjuster = ConfigurationAdjuster(base_llm, base_tool)
    
    perf_llm, perf_tool = adjuster.adjust_for_performance()
    quality_llm, quality_tool = adjuster.adjust_for_quality()
    
    print(f"Performance config: {perf_llm.model} + {perf_tool.visitor_type}")
    print(f"Quality config: {quality_llm.model} + {quality_tool.visitor_type}")

    print("\n6.5: Integration Patterns")
    print("-" * 50)

    print("Advanced integration patterns...")
    
    integration_patterns = [
        "Configuration Management Service",
        "Multi-tenant Configuration",
        "Configuration Versioning",
        "Runtime Configuration Updates",
        "Configuration Monitoring",
        "A/B Testing with Configurations",
        "Configuration Rollback",
        "Configuration Validation Pipeline"
    ]

    for pattern in integration_patterns:
        print(f"  - {pattern}")

    print("\nIntegration benefits:")
    print("- Centralized configuration management")
    print("- Easy deployment of configuration changes")
    print("- Configuration drift detection")
    print("- Audit trail for configuration changes")
    print("- Automated configuration testing")


###################################################################################
# SECTION 7: QUICK REFERENCE
###################################################################################

def tutorial_section_7():
    """
    Section 7: Quick Reference.
    
    This section provides:
    - Quick start code examples
    - Common patterns cheat sheet
    - Troubleshooting guide
    - Migration checklist
    """
    print("\n" + "=" * 80)
    print("SECTION 7: QUICK REFERENCE")
    print("=" * 80)

    print("\n7.1: Quick Start Examples")
    print("-" * 50)

    print("Essential code patterns for new architecture:")
    
    print("\n# Basic Setup")
    print("""
```python
from rv_llm.config import LLMConfig, PromptConfig
from rv_llm.llm.constants import LLMType, PromptStrategyType
from rv_screen_parser.constants import ScreenParserType, VisitorType
from rvandroid_tool.config.tool_config import RvAndroidToolConfig
from rvandroid_tool.llm.service.action_service import LLMActionService

# Create configurations
llm_config = LLMConfig(
    llm_type=LLMType.OLLAMA,
    model="llama3.2:3b",
    temperature=0.2,
    max_tokens=800
)

tool_config = RvAndroidToolConfig(
    parser_type=ScreenParserType.DROIDBOT,
    visitor_type=VisitorType.DETAILED,
    llm_config=llm_config
)

# Create service
service = LLMActionService(
    static_data=static_data,
    config=llm_config,
    app_package="com.example.app",
    tool_config=tool_config
)

# Process state
actions = service.process_state(state)
```
""")

    print("\n# Multi-Instance Setup")
    print("""
```python
# Create multiple configurations
configs = []
for i in range(3):
    llm_config = LLMConfig(
        llm_type=LLMType.OLLAMA,
        model=f"llama3.2:{i+1}b",
        temperature=0.2 + (i * 0.1)
    )
    
    tool_config = RvAndroidToolConfig(
        parser_type=ScreenParserType.DROIDBOT,
        visitor_type=VisitorType.DETAILED,
        llm_config=llm_config
    )
    
    configs.append((llm_config, tool_config))

# Create services
services = []
for llm_cfg, tool_cfg in configs:
    service = LLMActionService(
        static_data=static_data,
        config=llm_cfg,
        app_package="com.example.app",
        tool_config=tool_cfg
    )
    services.append(service)
```
""")

    print("\n7.2: Configuration Patterns Cheat Sheet")
    print("-" * 50)

    patterns = [
        ("Development", "llama3.2:1b, temp=0.1, BASIC visitor"),
        ("Production", "llama3.2:3b, temp=0.2, DETAILED visitor"),
        ("Research", "qwen2.5:7b, temp=0.5, ENHANCED visitor"),
        ("Performance", "Small model, low temp, basic parsing"),
        ("Quality", "Large model, moderate temp, detailed parsing"),
        ("Conservative", "Low temp, small context, basic features"),
        ("Experimental", "High temp, large context, all features")
    ]

    for name, config in patterns:
        print(f"  {name}: {config}")

    print("\n7.3: Common Configuration Values")
    print("-" * 50)

    print("LLM Types:")
    print(f"  - {LLMType.OLLAMA}: Local Ollama server")
    print(f"  - {LLMType.HUGGINGFACE}: HuggingFace models")
    print(f"  - {LLMType.FRONTIER}: Commercial APIs")

    print("\nStrategy Types:")
    print(f"  - {PromptStrategyType.STANDARD}: Single action")
    print(f"  - {PromptStrategyType.BATCH_ACTION}: Multiple actions")

    print("\nParser Types:")
    print(f"  - {ScreenParserType.DROIDBOT}: DroidBot parser")

    print("\nVisitor Types:")
    print(f"  - {VisitorType.BASIC}: Fast, basic info")
    print(f"  - {VisitorType.DETAILED}: Comprehensive info")
    print(f"  - {VisitorType.DETAILED}: Advanced analysis")

    print("\n7.4: Troubleshooting Guide")
    print("-" * 50)

    troubleshooting = [
        ("Configuration validation errors", "Check constants usage, verify required fields"),
        ("Service creation fails", "Verify static_data, check LLM connectivity"),
        ("Template not found", "Check template registration, verify paths"),
        ("Strategy errors", "Verify strategy type constants, check imports"),
        ("Parser errors", "Check parser type constants, verify visitor compatibility"),
        ("Multi-instance issues", "Ensure independent configurations, check resource limits"),
        ("Performance issues", "Use smaller models, reduce context length, optimize visitor"),
        ("Memory issues", "Limit concurrent instances, use basic visitor, clear caches")
    ]

    for issue, solution in troubleshooting:
        print(f"  {issue}:")
        print(f"    → {solution}")

    print("\n7.5: Migration Checklist")
    print("-" * 50)

    checklist = [
        "☐ Replace ComponentConfigurator with separated configs",
        "☐ Create LLMConfig for LLM backend settings",
        "☐ Create PromptConfig for prompt generation settings",
        "☐ Update PromptFramework.create() calls",
        "☐ Replace single config with LLMConfig + RvAndroidToolConfig",
        "☐ Update service creation to use new parameters",
        "☐ Test all configuration combinations",
        "☐ Verify template registration works",
        "☐ Test multi-instance scenarios",
        "☐ Update error handling for new exceptions",
        "☐ Verify performance with new architecture",
        "☐ Remove old ComponentConfigurator references"
    ]

    for item in checklist:
        print(f"  {item}")

    print("\n7.6: Key Differences Summary")
    print("-" * 50)

    print("OLD vs NEW Architecture:")
    print("""
OLD:
- ComponentConfigurator for all configuration
- Single mixed configuration object
- PromptFramework.create(configurator)
- Strategy selection through configurator
- Global configuration approach

NEW:
- LLMConfig + PromptConfig separation
- LLMComponentFactory for component creation
- PromptFramework.create(prompt_config)
- Strategy specified in PromptConfig
- Multi-instance support with independent configs
- RvAndroidToolConfig for tool-specific settings
""")

    print("\nMigration Benefits:")
    print("- Cleaner separation of concerns")
    print("- Better type safety with constants")
    print("- Multi-instance support")
    print("- Easier testing and debugging")
    print("- More flexible configuration options")
    print("- Better error handling and validation")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # List of available sections
    sections = [
        "1: New Architecture Basics",
        "2: Multi-Instance Configuration", 
        "3: Prompt Configuration System",
        "4: Tool Configuration Integration",
        "5: Practical Usage Patterns",
        "6: Advanced Scenarios",
        "7: Quick Reference"
    ]

    print("=" * 80)
    print("RV-ANDROID NEW PROMPT ARCHITECTURE TUTORIAL".center(80))
    print("=" * 80)
    print("\nAvailable sections:")
    for i, section in enumerate(sections, 1):
        print(f"  {i}. {section}")

    print("\nTo run all sections, execute without arguments.")
    print("To run a specific section, provide the section number as argument.")
    print("Example: python teste_prompt_generator_tutorial.py 1")

    # Determine which sections to run
    if len(sys.argv) > 1:
        section_funcs = [
            tutorial_section_1,
            tutorial_section_2,
            tutorial_section_3,
            tutorial_section_4,
            tutorial_section_5,
            tutorial_section_6,
            tutorial_section_7
        ]

        try:
            section_num = int(sys.argv[1])
            if 1 <= section_num <= 7:
                print(f"\nRunning section {section_num} only...\n")
                section_funcs[section_num - 1]()
            else:
                print(f"Invalid section: {section_num}. Choose 1-7.")
        except ValueError:
            print(f"Invalid argument: {sys.argv[1]}. Use number 1-7.")
    else:
        # Run all sections
        section_funcs = [
            tutorial_section_1,
            tutorial_section_2,
            tutorial_section_3,
            tutorial_section_4,
            tutorial_section_5,
            tutorial_section_6,
            tutorial_section_7
        ]
        
        for i, section_func in enumerate(section_funcs, 1):
            try:
                section_func()
                if i < len(section_funcs):
                    print("\n" + "=" * 40 + " SECTION SEPARATOR " + "=" * 40)
            except Exception as e:
                print(f"Error in section {i}: {e}")

    print("\n" + "=" * 80)
    print("TUTORIAL COMPLETED".center(80))
    print("=" * 80)