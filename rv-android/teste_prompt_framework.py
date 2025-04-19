#!/usr/bin/env python3

"""
RV-Android Prompt Framework Test.

Este arquivo contém exemplos simplificados de como usar o framework de prompts
refatorado do RV-Android.
"""

import json
import logging
import os
import sys
from typing import Dict, Any, Optional

from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.llm.constants import PromptStrategyType, StateEntry
from rvandroid.llm.ollama_llm import OllamaLLM
from rvandroid.llm.data_structures import MCPConfiguration
from rvandroid.llm.prompt.framework import PromptFramework
from rvandroid.llm.prompt.information.fragment_manager import InformationManager
from rvandroid.llm.prompt.information.fragments.monitored_operations_fragment import MonitoredOperationsFragment
from rvandroid.llm.prompt.information.fragments.screenshot_fragment import ScreenshotFragment
from rvandroid.llm.prompt.information.fragments.ui_elements_fragment import UIElementsFragment
from rvandroid.llm.prompt.information.fragments.ui_pattern_fragment import UIPatternFragment
from rvandroid.llm.prompt.template.xml_repository import XMLTemplateRepository


# Helper functions for loading data

def read_droidbot_state(filename: str) -> Dict[str, Any]:
    """Loads a DroidBot state file."""
    with open(filename, 'r') as file:
        return json.load(file)


def prepare_state_from_droidbot(droidbot_state: Dict[str, Any], screenshot_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Prepares a state dictionary in the format expected by the prompt framework,
    from a DroidBot state.
    """
    activity = droidbot_state.get("activity", "")
    if "/" in activity:
        # Extract the short activity name from the full name
        package_activity = activity.split("/")
        if len(package_activity) > 1:
            activity = package_activity[1]
            if activity.startswith("."):
                activity = activity[1:]  # Remove leading dot
    
    # Extract package name
    package_name = droidbot_state.get("view_tree", {}).get("package", "")
    if not package_name and "/" in droidbot_state.get("activity", ""):
        package_name = droidbot_state.get("activity", "").split("/")[0]
    
    # Process the view tree to extract components
    view_tree = droidbot_state.get("view_tree", {})
    
    # Extract components from tree structure if needed
    components = []
    if "children" in view_tree:
        # This is a hierarchical tree structure; we need to flatten it
        def extract_components(node, depth=0):
            if not node:
                return []
            
            # Add the current node as a component with depth info
            node_copy = node.copy()
            node_copy["depth"] = depth
            node_copy["type"] = node.get("class", "").split(".")[-1]  # Extract last part of class name
            
            # Add clickable and enabled for UI interaction
            components.append(node_copy)
            
            # Process children
            children = node.get("children", [])
            for child in children:
                extract_components(child, depth + 1)
        
        # Start extraction from the root
        extract_components(view_tree)
        
        # Create a modified view tree with components at the top level
        modified_view_tree = {
            "package": package_name,
            "activity": activity,
            "class": view_tree.get("class", "android.widget.FrameLayout"),
            "components": components
        }
        
        # Use the modified tree
        view_tree = modified_view_tree
    
    # Prepare basic state
    state = {
        StateEntry.PACKAGE_NAME: package_name,
        StateEntry.ACTIVITY: activity,
        StateEntry.SCREEN: view_tree,
    }
    
    # Add screenshot path if provided
    if screenshot_path and os.path.exists(screenshot_path):
        state[StateEntry.SCREENSHOT_PATH] = screenshot_path
    
    # Print debug info about the created state
    print(f"State created with activity: {activity}, package: {package_name}")
    print(f"Screen has {len(components)} components")
    if components:
        print(f"First component type: {components[0].get('type', 'unknown')}")

    return state


# Example 1: Using PromptFramework directly with a mock model
def example_001():
    """
    Basic example of using PromptFramework with a mock model.
    Demonstrates prompt generation using the default template.
    """
    print("\n=== EXAMPLE 1: Using PromptFramework with mock model ===")
    
    # Create the strategy registry
    from rvandroid.llm.prompt.strategy.strategy_registry import StrategyRegistry
    from rvandroid.llm.prompt.strategy.strategies.standard_strategy import StandardStrategy
    
    # Create components
    info_manager = InformationManager()
    template_repo = XMLTemplateRepository()
    strategy_registry = StrategyRegistry()
    
    # Add a standard strategy
    standard_strategy = StandardStrategy(
        information_manager=info_manager,
        template_repository=template_repo
    )
    strategy_registry.register_strategy(standard_strategy)
    
    # Create the framework
    framework = PromptFramework(
        information_manager=info_manager,
        template_repository=template_repo,
        strategy_registry=strategy_registry,
        model=None               # No real model
    )
    
    # Basic example state
    state = {
        StateEntry.PACKAGE_NAME: "br.unb.cic.cryptoapp",
        StateEntry.ACTIVITY: "br.unb.cic.cryptoapp.MainActivity",
        StateEntry.SCREEN_DESCRIPTION: "Initial screen of the Crypto App application with three buttons: MESSAGE DIGEST, CIPHER, and GENERATED.",
    }
    
    # Additional context
    context = {
        "exploration_focus": "monitored_operations"
    }
    
    # Generate prompt using standard strategy
    messages = framework.generate_prompt(PromptStrategyType.STANDARD, state, context)
    
    print(f"Generated {len(messages)} messages for the LLM")
    for i, message in enumerate(messages):
        role = message.get("role", "unknown")
        content = message.get("content", "")
        print(f"\nMessage {i+1} ({role}):")
        # Show more content in the output for better analysis
        if len(content) > 1000:
            print(f"{content[:1000]}...[truncated]")
        else:
            print(content)


# Example 2: Using the framework with real DroidBot data
def example_002(droidbot_state_file: str, screenshot_file: Optional[str] = None):
    """
    Demonstrates using PromptFramework with real DroidBot data.
    Uses information fragments to extract data from the state.
    """
    print("\n=== EXAMPLE 2: PromptFramework with real DroidBot data ===")
    
    # Load DroidBot state
    droidbot_state = read_droidbot_state(droidbot_state_file)
    
    # Prepare state for the framework
    state = prepare_state_from_droidbot(droidbot_state, screenshot_file)
    
    # Create information fragments
    info_manager = InformationManager()
    info_manager.register_fragments([
        UIElementsFragment(),
        UIPatternFragment(),
        MonitoredOperationsFragment(),
    ])
    
    # Add screenshot fragment if available
    if screenshot_file and os.path.exists(screenshot_file):
        info_manager.register_fragment(ScreenshotFragment())
    
    # Create template repository
    template_repo = XMLTemplateRepository()
    
    # Create the strategy registry
    from rvandroid.llm.prompt.strategy.strategy_registry import StrategyRegistry
    from rvandroid.llm.prompt.strategy.strategies.standard_strategy import StandardStrategy
    
    # Create registry
    strategy_registry = StrategyRegistry()
    
    # Add a standard strategy
    standard_strategy = StandardStrategy(
        information_manager=info_manager,
        template_repository=template_repo
    )
    strategy_registry.register_strategy(standard_strategy)
    
    # Configure framework manually
    framework = PromptFramework(
        information_manager=info_manager,
        template_repository=template_repo,
        strategy_registry=strategy_registry,
        model=None               # No real model
    )
    
    # Generate prompt using standard strategy
    messages = framework.generate_prompt(PromptStrategyType.STANDARD, state, {})
    
    print(f"\nGenerated {len(messages)} messages for the LLM")
    for i, message in enumerate(messages):
        role = message.get("role", "unknown")
        content = message.get("content", "")
        print(f"\nMessage {i+1} ({role}):")
        # Show more content in the output for better analysis
        if len(content) > 1000:
            print(f"{content[:1000]}...[truncated]")
        else:
            print(content)


# Example 3: Using the framework with Ollama
def example_003(droidbot_state_file: str, should_execute: bool = False):
    """
    Demonstrates how to use the framework with an Ollama model.
    By default, doesn't execute the real model call (should_execute=False).
    """
    print("\n=== EXAMPLE 3: Using the framework with Ollama model ===")
    
    if not should_execute:
        print("Simulation mode - not calling real model.")
        print("To actually execute, call the function with should_execute=True")
        return
    
    # Load DroidBot state
    droidbot_state = read_droidbot_state(droidbot_state_file)
    
    # Prepare state for the framework
    state = prepare_state_from_droidbot(droidbot_state)
    
    # Create model configuration
    config = MCPConfiguration(
        model_name=OllamaLLM.LLAMA,
        model_type="ollama",
        temperature=0.2,
        max_tokens=800
    )
    
    try:
        # Create the Ollama model
        ollama_model = OllamaLLM(
            model_name=OllamaLLM.LLAMA,
            temperature=0.2,
            max_tokens=800,
            api_base="http://localhost:11434"
        )
        
        # Create the components
        info_manager = InformationManager()
        template_repo = XMLTemplateRepository()
        
        # Create the strategy registry
        from rvandroid.llm.prompt.strategy.strategy_registry import StrategyRegistry
        from rvandroid.llm.prompt.strategy.strategies.standard_strategy import StandardStrategy
        
        # Create registry
        strategy_registry = StrategyRegistry()
        
        # Add a standard strategy
        standard_strategy = StandardStrategy(
            information_manager=info_manager,
            template_repository=template_repo
        )
        strategy_registry.register_strategy(standard_strategy)
        
        # Create framework with model
        framework = PromptFramework(
            information_manager=info_manager,
            template_repository=template_repo,
            strategy_registry=strategy_registry,
            model=ollama_model
        )
        
        # Context for exploration
        context = {
            "template": "rvdroid:exploration",
            "elements_count": "3 interactive elements", 
            "progress": "Beginning exploration",
            "history_summary": "First screen of the application."
        }
        
        # Generate prompt and send to model
        print("Sending prompt to Ollama model...")
        response = framework.generate_with_llm(PromptStrategyType.STANDARD, state, context)
        
        if response:
            print("\nModel response:")
            print(response)
        else:
            print("Could not get response from model.")
    
    except Exception as e:
        print(f"Error using Ollama model: {e}")


# Example 4: Using Batch Action Strategy
def example_004(droidbot_state_file: str, screenshot_file: Optional[str] = None):
    """
    Demonstrates using BatchActionStrategy for generating multiple related actions.
    Shows how to use the template system with different strategies.
    """
    print("\n=== EXAMPLE 4: Using Batch Action Strategy ===")
    
    # Load DroidBot state
    droidbot_state = read_droidbot_state(droidbot_state_file)
    
    # Prepare state for the framework
    state = prepare_state_from_droidbot(droidbot_state, screenshot_file)
    
    # Create information fragments
    info_manager = InformationManager()
    info_manager.register_fragments([
        UIElementsFragment(),
        UIPatternFragment(),
        MonitoredOperationsFragment(),
    ])
    
    # Add screenshot fragment if available
    if screenshot_file and os.path.exists(screenshot_file):
        info_manager.register_fragment(ScreenshotFragment())
    
    # Create template repository
    template_repo = XMLTemplateRepository()
    
    # Create the strategy registry
    from rvandroid.llm.prompt.strategy.strategy_registry import StrategyRegistry
    from rvandroid.llm.prompt.strategy.strategies.standard_strategy import StandardStrategy
    from rvandroid.llm.prompt.strategy.strategies.batch_action_strategy import BatchActionStrategy
    
    # Create registry
    strategy_registry = StrategyRegistry()
    
    # Add both standard and batch action strategies
    standard_strategy = StandardStrategy(
        information_manager=info_manager,
        template_repository=template_repo
    )
    strategy_registry.register_strategy(standard_strategy)
    
    batch_strategy = BatchActionStrategy(
        information_manager=info_manager,
        template_repository=template_repo
    )
    strategy_registry.register_strategy(batch_strategy)
    
    # Configure framework manually
    framework = PromptFramework(
        information_manager=info_manager,
        template_repository=template_repo,
        strategy_registry=strategy_registry,
        model=None               # No real model
    )
    
    # Generate prompt using batch action strategy
    messages = framework.generate_prompt(PromptStrategyType.BATCH_ACTION, state, {})
    
    print(f"\nGenerated {len(messages)} messages for the LLM")
    for i, message in enumerate(messages):
        role = message.get("role", "unknown")
        content = message.get("content", "")
        print(f"\nMessage {i+1} ({role}):")
        # Show more content in the output for better analysis
        if len(content) > 100000:
            print(f"{content[:100000]}...[truncated]")
        else:
            print(content)


# Example 5: Using Custom Information Fragments
def example_005():
    """
    Demonstrates how to create and use custom information fragments
    for specialized domain knowledge.
    """
    print("\n=== EXAMPLE 5: Using Custom Information Fragments ===")
    
    # Create a custom information fragment
    from rvandroid.llm.prompt.information.base_fragment import InformationFragment
    
    class CustomDataFragment(InformationFragment):
        """Custom fragment for including specialized data information."""
        
        def __init__(self, name: str = "data_usage", priority: int = 150):
            super().__init__(name, priority)
        
        def generate(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
            """Generate information about data usage in the current state."""
            activity = state.get(StateEntry.ACTIVITY, "unknown")
            
            # This would normally analyze real data from the state
            # For this example, we're just generating static information
            return f"""
DATA USAGE ANALYSIS:
- Current activity ({activity}) accesses user data
- Sensitive data fields detected: email, password
- Data is transmitted over HTTPS
- No data leakage detected in this screen
- Monitor carefully when sending data to server
            """
        
        def should_include(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> bool:
            """Determine if this fragment should be included (e.g., only include for data-related screens)."""
            # In a real implementation, we would check for data-related screens
            # For this example, always include
            return True
    
    # Create components
    info_manager = InformationManager()
    template_repo = XMLTemplateRepository()
    
    # Register standard fragments
    info_manager.register_fragments([
        UIElementsFragment(),
        UIPatternFragment(),
    ])
    
    # Register our custom fragment
    info_manager.register_fragment(CustomDataFragment())
    
    # Create the strategy registry
    from rvandroid.llm.prompt.strategy.strategy_registry import StrategyRegistry
    from rvandroid.llm.prompt.strategy.strategies.standard_strategy import StandardStrategy
    
    # Create registry
    strategy_registry = StrategyRegistry()
    
    # Add a standard strategy
    standard_strategy = StandardStrategy(
        information_manager=info_manager,
        template_repository=template_repo
    )
    strategy_registry.register_strategy(standard_strategy)
    
    # Create the framework
    framework = PromptFramework(
        information_manager=info_manager,
        template_repository=template_repo,
        strategy_registry=strategy_registry,
        model=None               # No real model
    )
    
    # Create a sample state
    state = {
        StateEntry.PACKAGE_NAME: "com.example.secureapp",
        StateEntry.ACTIVITY: "com.example.secureapp.LoginActivity",
        StateEntry.SCREEN_DESCRIPTION: """
Login screen with:
- Username field (EditText)
- Password field (EditText, password mode)
- Login button
- Remember me checkbox
- Forgot password link
        """,
    }
    
    # Generate prompt using standard strategy
    messages = framework.generate_prompt(PromptStrategyType.STANDARD, state, {})
    
    print(f"\nGenerated {len(messages)} messages for the LLM")
    for i, message in enumerate(messages):
        role = message.get("role", "unknown")
        content = message.get("content", "")
        print(f"\nMessage {i+1} ({role}):")
        # Show more content in the output for better analysis
        if len(content) > 1000:
            print(f"{content[:1000]}...[truncated]")
        else:
            print(content)


# Example 6: Using Template Variables and Fragments
def example_006():
    """
    Demonstrates how to use the template system with variables and fragments.
    This example creates a custom template that uses system_base and includes fragments.
    """
    print("\n=== EXAMPLE 6: Using Template Variables and Fragments ===")
    
    # Create a custom template file (in memory)
    custom_template_content = """<?xml version="1.0" encoding="UTF-8"?>
    <template name="custom_template" version="1.0" extends="system_base">
      <metadata>
        <description>Custom template for demonstration</description>
        <created>2025-04-18</created>
        <author>Example Author</author>
      </metadata>
      <variables>
        <required>screen_elements</required>
        <optional>additional_guidelines</optional>
      </variables>
      <roles>
        <s>
          <variable name="strategy_specific_instructions">
            <![CDATA[
    Your task is to analyze the current state for potential security vulnerabilities.
    Focus specifically on:
    - Input validation
    - Authentication mechanisms
    - Data transmission
    - Storage of sensitive information
            ]]>
          </variable>
          <variable name="response_format_instructions">
            <![CDATA[
    {#include standard_format}
            ]]>
          </variable>
          <variable name="additional_guidelines">
            <![CDATA[
    SECURITY TESTING GUIDELINES:
    - Test all input fields with potential SQL injection
    - Try bypassing authentication when possible
    - Check for information leakage in error messages
    - Test for improper session management
            ]]>
          </variable>
        </s>
        <user><![CDATA[
    Current Activity: {activity}
    
    Security Analysis Context:
    - Application handles sensitive user data
    - Previous vulnerabilities found in similar screens
    - Focus on authentication bypass and data leakage
    
    Current UI Elements:
    {screen_elements}
    
    Your task is to identify the single most critical security test for this screen.
    {#if additional_guidelines}
    
    {additional_guidelines}{#endif}
        ]]></user>
      </roles>
    </template>
    """
    
    # For a real example, we would write this to a file
    # Here we'll simulate template loading
    
    # Create components for our example
    info_manager = InformationManager()
    info_manager.register_fragments([UIElementsFragment(), UIPatternFragment()])
    
    # Create template repository
    # In a real implementation, we'd load the custom template from a file
    # Here we'll just create a base repository and pretend it has our custom template
    template_repo = XMLTemplateRepository()
    
    # Create strategy registry
    from rvandroid.llm.prompt.strategy.strategy_registry import StrategyRegistry
    from rvandroid.llm.prompt.strategy.strategies.standard_strategy import StandardStrategy
    
    # Create registry and standard strategy
    strategy_registry = StrategyRegistry()
    standard_strategy = StandardStrategy(
        information_manager=info_manager,
        template_repository=template_repo
    )
    strategy_registry.register_strategy(standard_strategy)
    
    # Create framework
    framework = PromptFramework(
        information_manager=info_manager,
        template_repository=template_repo,
        strategy_registry=strategy_registry
    )
    
    # Sample state
    state = {
        StateEntry.PACKAGE_NAME: "com.example.bankapp",
        StateEntry.ACTIVITY: "com.example.bankapp.TransferActivity",
        StateEntry.SCREEN_DESCRIPTION: """
Money transfer screen with:
- Amount field (EditText, numeric)
- Recipient account field (EditText)
- Transfer button
- Cancel button
        """,
    }
    
    # Context to specify our custom template
    # In a real implementation, the template would be loaded from the repository
    # Here we'll note that with this special context that would normally specify the template name
    context = {
        "template": "custom_template",  # This would normally select our custom template
        "additional_guidelines": "For this specific banking app, pay extra attention to input validation on the amount field."
    }
    
    # Generate messages
    # Note: In this example, the custom template won't actually be used since we didn't register it
    # This is just to demonstrate the concept
    messages = framework.generate_prompt(PromptStrategyType.STANDARD, state, context)
    
    print(f"\nGenerated {len(messages)} messages for the LLM")
    print("NOTE: This example demonstrates the concept but doesn't actually use the custom template")
    print("      since we didn't register it with the repository. In a real implementation, the")
    print("      template would be loaded from a file.")
    
    for i, message in enumerate(messages):
        role = message.get("role", "unknown")
        content = message.get("content", "")
        print(f"\nMessage {i+1} ({role}):")
        # Show more content in the output for better analysis
        if len(content) > 1000:
            print(f"{content[:1000]}...[truncated]")
        else:
            print(content)


if __name__ == "__main__":
    # Configure logging with DEBUG level to see more details
    logging.basicConfig(level=logging.DEBUG, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Define paths to files
    screenshot_dir = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshot_novo/cryptoapp.apk"
    droidbot_state_file = os.path.join(screenshot_dir, "001.state")
    screenshot_file = os.path.join(screenshot_dir, "001.png")
    
    # Check if files exist
    if not os.path.exists(droidbot_state_file):
        print(f"State file not found: {droidbot_state_file}")
        sys.exit(1)
    
    # Run examples
    # example_001()
    # example_002(droidbot_state_file, screenshot_file)
    # example_003(droidbot_state_file, should_execute=False)  # Set to True to run with real model
    example_004(droidbot_state_file, screenshot_file)
    # example_005()
    # example_006()
    
    # Example 7: Using modular templates with fragment inclusion
    # print("\n=== EXAMPLE 7: Using modular templates with fragment inclusion ===")
    # print("NOTE: This test requires the modular templates and fragments to be available in the repository.")
    # print("Check if the following files exist:")
    # print("\nTemplates:")
    # print("- /templates/system_base.xml - Base template with shared structure")
    # print("- /templates/standard_modular.xml - Standard template that extends system_base")
    # print("- /templates/batch_action_modular.xml - Batch action template that extends system_base")
    # print("\nSystem Fragments:")
    # print("- /fragments/system_intro.xml - Introduction for system prompts")
    # print("- /fragments/system_guidelines.xml - Common guidelines for all strategies")
    # print("- /fragments/standard_instructions.xml - Instructions specific to standard strategy")
    # print("- /fragments/standard_format.xml - JSON format for standard responses")
    # print("- /fragments/batch_instructions.xml - Instructions specific to batch actions")
    # print("- /fragments/batch_format.xml - JSON format for batch responses")
    # print("- /fragments/batch_guidelines.xml - Additional guidelines for batch actions")
    # print("\nUser Fragments:")
    # print("- /fragments/user_base.xml - Common elements for all user prompts")
    # print("- /fragments/standard_summary.xml - Summary for standard strategy")
    # print("- /fragments/batch_ui_pattern_detection.xml - UI pattern identification for batch strategy")
    # print("- /fragments/batch_critical_task.xml - Critical task definition for batch strategy")
    # print("\nUI Pattern Fragments:")
    # print("- /fragments/ui_patterns/form_pattern.xml - Form pattern guidance")
    # print("- /fragments/ui_patterns/list_pattern.xml - List pattern guidance")
    #
    # print("\nThese modular templates demonstrate inheritance and fragment inclusion features of the system.")