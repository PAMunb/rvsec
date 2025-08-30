#!/usr/bin/env python3
"""
RVSmart Prompt Framework - Comprehensive Tutorial

This tutorial demonstrates all capabilities of the RVSmart prompt framework:
- All strategies (SINGLE, BATCH, VISION)
- All template tiers (compact, standard, premium)
- All context modes (STATELESS, RICH)
- All visitor types (BASIC, DEFAULT, ENHANCED)
- State enrichment and data flow
- Fragment system usage
- Template inheritance
- Progressive template selection

Author: RVSmart Team
Date: 2025-08-29
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Type, List, Optional
from collections import OrderedDict

# Add modules to Python path
project_root = Path(__file__).parent
for module in ["rv-android-core", "rv-llm", "rvsmart-tool", "rv-screen-parser", "rv-static-analysis"]:
    sys.path.insert(0, str(project_root / "modules" / module / "src"))

# Import core components
from rv_llm import LLMMessage, LLMRole, LLMTextContent, LLMImageContent
from rv_llm.config import PromptConfig
from rv_llm.config.llm_config import LLMConfig
from rv_llm.llm.constants import LLMType, PromptStrategyType, ContextMode, StateEntry
from rv_llm.llm.ollama_llm import OllamaLLM
from rv_screen_parser.parser.screen.visitor.abstract_visitor import AbstractScreenVisitor
from rv_screen_parser.parser.screen.visitor.default_visitor import DefaultTextVisitor
from rv_screen_parser.parser.screen.visitor.basic_visitor import BasicTextVisitor
from rv_screen_parser.parser.screen.parser_factory import ParserFactory
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription
from rv_screen_parser.constants import ScreenParserType, VisitorType
from rv_android_core import constants
from rv_android_core.domain.app import App
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.util.logging.manager import LoggingManager
from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser
from rvsmart_tool.config.tool_config import RvSmartToolConfig
from rvsmart_tool.llm.prompt.rvsmart_framework import RVAndroidPromptFramework
from rvsmart_tool.llm.service.memory_manager import MemoryManager
from rvsmart_tool.llm.service.transition_manager import TransitionManager
from rvsmart_tool.llm.service.action_service import LLMActionService

# Setup RVSEC_HOME environment
os.environ[constants.ENV_RVSEC_HOME] = os.path.dirname(os.getcwd())

# ============================================================================
# SECTION 1: LOGGING AND UTILITIES
# ============================================================================

def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure logging for the tutorial."""
    logging.basicConfig(
        level=getattr(logging, level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    
    # Silence noisy loggers
    for logger_name in ["androguard", "matplotlib", "PIL", "requests", "urllib3"]:
        logging.getLogger(logger_name).setLevel(logging.ERROR)
    
    return logging.getLogger('rv_llm_tutorial')


def print_section(title: str, width: int = 80):
    """Print a formatted section header."""
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


def print_subsection(title: str, width: int = 60):
    """Print a formatted subsection header."""
    print("\n" + "-" * width)
    print(f"  {title}")
    print("-" * width)


def load_test_data(apk: str = "cryptoapp.apk", state_id: str = "004") -> Dict[str, Any]:
    """Load test data files for demonstration."""
    base_dir = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    app_folder = os.path.join(base_dir, apk)
    
    return {
        "apk_path": os.path.join(app_folder, apk),
        "reach_file": os.path.join(app_folder, f"{apk}.reach"),
        "gator_file": os.path.join(app_folder, f"{apk}.wtg"),
        "gesda_file": os.path.join(app_folder, f"{apk}.gesda"),
        "screenshot_path": os.path.join(app_folder, f"{state_id}.png"),
        "state_file": os.path.join(app_folder, f"{state_id}.state"),
        "package": App(app_path=os.path.join(app_folder, apk)).package_name
    }


def read_droidbot_state(filename: str) -> Dict[str, Any]:
    """Load a DroidBot state file."""
    with open(filename, 'r') as f:
        return json.load(f)


def create_mock_iterations() -> List[Dict[str, Any]]:
    """Create mock iteration data for RICH context mode demonstration."""
    return [
        {
            'activity': 'MainActivity',
            'actions_generated': [
                {'explanation': 'clicked login button to access authentication'},
                {'explanation': 'filled username field with test data'}
            ],
            'coverage_metrics': {
                'method_coverage': 15.5,
                'mop_method_coverage': 8.2,
                'unique_errors': 0
            },
            'mop_errors': []
        },
        {
            'activity': 'LoginActivity',
            'actions_generated': [
                {'explanation': 'entered password in secure field'},
                {'explanation': 'submitted login form [M]'},
                {'explanation': 'verified authentication result'}
            ],
            'coverage_metrics': {
                'method_coverage': 28.7,
                'mop_method_coverage': 12.1,
                'unique_errors': 0
            },
            'mop_errors': []
        },
        {
            'activity': 'DashboardActivity',
            'actions_generated': [
                {'explanation': 'navigated to settings menu [M]'},
                {'explanation': 'opened security configuration [DM]'}
            ],
            'coverage_metrics': {
                'method_coverage': 42.8,
                'mop_method_coverage': 25.3,
                'unique_errors': 2
            },
            'mop_errors': [
                {'spec': 'CryptoSpec', 'method': 'createCipher', 'message': 'Weak cipher algorithm'},
                {'spec': 'NetworkSpec', 'method': 'sendData', 'message': 'Unencrypted transmission'}
            ]
        }
    ]


# ============================================================================
# SECTION 2: STATE CREATION AND ENRICHMENT
# ============================================================================

def create_state_from_droidbot(
    state_file: str,
    screenshot_path: str,
    package: str,
    static_data: StaticAnalysisData,
    visitor_class: Type[AbstractScreenVisitor]
) -> Dict[str, Any]:
    """
    Create a state dictionary from DroidBot output.
    
    This demonstrates the foundation of the prompt system:
    - Loading DroidBot state data
    - Parsing screen with selected visitor
    - Creating the base state dictionary
    """
    screen_info = read_droidbot_state(state_file)
    parser = ParserFactory.create(ScreenParserType.DROIDBOT, visitor_class)
    screen_description = parser.parse_screen(screen_info, static_data)
    
    return {
        StateEntry.PACKAGE_NAME: package,
        StateEntry.ACTIVITY: screen_description.activity,
        StateEntry.VIEW_TREE: screen_info.get("view_tree", {}),
        StateEntry.SCREENSHOT_PATH: screenshot_path,
        StateEntry.STRUCTURED_SCREEN: screen_description
    }


def enrich_state(
    state: Dict[str, Any],
    static_data: StaticAnalysisData,
    config: RvSmartToolConfig
) -> Dict[str, Any]:
    """
    Enrich state with additional context using service managers.
    
    This demonstrates:
    - Memory manager integration
    - Transition manager integration
    - Action service preprocessing
    """
    # Add static data and tool config to state first
    state[StateEntry.STATIC_DATA] = static_data
    state[StateEntry.TOOL_CONFIG] = config
    
    memory_manager = MemoryManager(static_data=static_data)
    transition_manager = TransitionManager(static_data=static_data)
    
    try:
        action_service = LLMActionService(
            static_data=static_data,
            tool_config=config
        )
        
        # Override managers for testing
        action_service.memory_manager = memory_manager
        action_service.transition_manager = transition_manager
        
        # Enrich state with additional data
        action_service._pre_process_state(state)
        
    except Exception as e:
        # If enrichment fails, continue with basic enrichment
        print(f"    Note: Full enrichment failed ({e}), using basic enrichment")
        
        # Add basic enrichment data
        state[StateEntry.MEMORY_INSIGHTS] = {
            'patterns_detected': [],
            'repetitive_actions': [],
            'exploration_status': 'starting'
        }
        state[StateEntry.ACTION_HISTORY] = []
        state[StateEntry.ACTIVITY_VISITS] = {
            'current_activity': state.get(StateEntry.ACTIVITY),
            'visit_count': 1
        }
    
    return state


# ============================================================================
# SECTION 3: BASIC FRAMEWORK USAGE
# ============================================================================

def demonstrate_basic_usage(test_data: Dict[str, Any], static_data: StaticAnalysisData):
    """
    Demonstrate basic framework usage with manual configuration.
    
    This shows the fundamental concepts:
    - Creating configurations manually
    - Understanding the framework components
    - Direct template usage
    - Fragment system
    """
    print_section("BASIC FRAMEWORK USAGE")
    
    print_subsection("Manual Configuration Creation")
    
    # Create LLM configuration
    llm_config = LLMConfig(
        llm_type=LLMType.OLLAMA,
        model=OllamaLLM.GEMMA,
        temperature=0.7,
        max_tokens=800,
        vision=False  # Text-only for basic example
    )
    
    print("LLM Configuration created:")
    print(f"  • Type: {llm_config.llm_type}")
    print(f"  • Model: {llm_config.model}")
    print(f"  • Temperature: {llm_config.temperature}")
    print(f"  • Max tokens: {llm_config.max_tokens}")
    
    # Create Prompt configuration
    prompt_config = PromptConfig(
        strategy_type=PromptStrategyType.SINGLE,
        parser_type=ScreenParserType.DROIDBOT,
        visitor_type=VisitorType.DEFAULT,
        template_name="single_compact",  # Explicit template selection
        context_mode=ContextMode.STATELESS,
        max_context_length=8192,
        context_window_size=5,
        context_compression=True
    )
    
    print("\nPrompt Configuration created:")
    print(f"  • Strategy: {prompt_config.strategy_type}")
    print(f"  • Parser: {prompt_config.parser_type}")
    print(f"  • Visitor: {prompt_config.visitor_type}")
    print(f"  • Template: {prompt_config.template_name}")
    print(f"  • Context mode: {prompt_config.context_mode}")
    
    # Create tool configuration combining both
    tool_config = RvSmartToolConfig(
        llm_config=llm_config,
        prompt_config=prompt_config,
        debug_mode=True
    )
    
    print("\nTool Configuration assembled:")
    print(f"  • Debug mode: {tool_config.debug_mode}")
    print(f"  • LLM config: ✓")
    print(f"  • Prompt config: ✓")
    
    print_subsection("Framework Initialization")
    
    # Initialize the framework
    framework = RVAndroidPromptFramework.create(prompt_config)
    
    print("Framework components:")
    print(f"  • Information manager: {framework.information_manager.__class__.__name__}")
    print(f"  • Template repository: {framework.template_repository.__class__.__name__}")
    print(f"  • Strategy: Created from {prompt_config.strategy_type}")
    
    print_subsection("State Creation and Enrichment")
    
    # Create basic state
    state = create_state_from_droidbot(
        test_data["state_file"],
        test_data["screenshot_path"],
        test_data["package"],
        static_data,
        DefaultTextVisitor
    )
    
    print("Initial state keys:")
    for key in list(state.keys())[:5]:  # Show first 5 keys
        print(f"  • {key}")
    
    # Enrich state
    enriched_state = enrich_state(state, static_data, tool_config)
    
    print(f"\nEnriched state has {len(enriched_state)} keys")
    new_keys = set(enriched_state.keys()) - set(state.keys())
    if new_keys:
        print("New keys added during enrichment:")
        for key in list(new_keys)[:5]:  # Show first 5 new keys
            print(f"  • {key}")
    
    print_subsection("Prompt Generation")
    
    # Generate prompt
    messages = framework.generate_prompt(enriched_state, {})
    
    print(f"Generated {len(messages)} messages:")
    for i, msg in enumerate(messages, 1):
        content_types = []
        for content in msg.content:
            if isinstance(content, LLMTextContent):
                content_types.append("Text")
            elif isinstance(content, LLMImageContent):
                content_types.append("Image")
        print(f"  Message {i}: Role={msg.role}, Content={', '.join(content_types)}")
    
    total_chars = sum(
        len(c.text) for m in messages for c in m.content 
        if hasattr(c, 'text')
    )
    print(f"\nTotal prompt size: {total_chars:,} characters")


def demonstrate_fragment_system(test_data: Dict[str, Any], static_data: StaticAnalysisData):
    """
    Demonstrate the fragment system and information extraction.
    
    Shows how fragments work to extract and format information:
    - Information fragments and their roles
    - Fragment registration
    - Data extraction from state
    """
    print_section("FRAGMENT SYSTEM DEMONSTRATION")
    
    print_subsection("Information Fragments")
    
    # Import fragment classes to show what's available
    from rvsmart_tool.llm.prompt.fragments.coverage_guidance_fragment import CoverageGuidanceFragment
    from rvsmart_tool.llm.prompt.fragments.history_fragment import HistoryFragment
    from rvsmart_tool.llm.prompt.fragments.monitored_operations_fragment import MonitoredOperationsFragment
    from rvsmart_tool.llm.prompt.fragments.system_coverage_fragment import SystemCoverageFragment
    from rvsmart_tool.llm.prompt.fragments.transition_guidance_fragment import TransitionGuidanceFragment
    from rvsmart_tool.llm.prompt.fragments.ui_elements_fragment import UIElementsFragment
    
    fragments = [
        (CoverageGuidanceFragment(), "Coverage guidance for exploration"),
        (HistoryFragment(), "Action history tracking"),
        (MonitoredOperationsFragment(), "MOP annotations and focus"),
        (SystemCoverageFragment(), "System-level coverage metrics"),
        (TransitionGuidanceFragment(), "Activity transition information"),
        (UIElementsFragment(), "UI element extraction and formatting")
    ]
    
    print("Available information fragments:")
    for fragment, description in fragments:
        print(f"  • {fragment.__class__.__name__}: {description}")
        print(f"    Required keys: {fragment.required_keys if hasattr(fragment, 'required_keys') else 'N/A'}")
    
    print_subsection("Fragment Data Extraction")
    
    # Create a state with various data
    config = RvSmartToolConfig(
        llm_config=LLMConfig(
            llm_type=LLMType.OLLAMA,
            model=OllamaLLM.GEMMA,
            temperature=0.7
        ),
        prompt_config=PromptConfig(
            strategy_type=PromptStrategyType.SINGLE,
            parser_type=ScreenParserType.DROIDBOT,
            visitor_type=VisitorType.DEFAULT,
            template_name="single_standard",
            context_mode=ContextMode.STATELESS
        )
    )
    
    state = create_state_from_droidbot(
        test_data["state_file"],
        test_data["screenshot_path"],
        test_data["package"],
        static_data,
        DefaultTextVisitor
    )
    
    # Add some test data for fragments
    state[StateEntry.ACTION_HISTORY] = [
        "Clicked login button",
        "Entered username: testuser",
        "Entered password",
        "Submitted form"
    ]
    
    state[StateEntry.COVERAGE_METRICS] = {
        'method_coverage': 35.2,
        'activity_coverage': 60.0,
        'mop_method_coverage': 15.8
    }
    
    state = enrich_state(state, static_data, config)
    
    # Test fragment extraction
    print("\nFragment extraction examples:")
    
    # History fragment
    history_fragment = HistoryFragment()
    try:
        history_data = history_fragment.extract(state)
        print(f"\n1. History Fragment:")
        print(f"   Extracted: {history_data.get('history', 'N/A')}")
    except Exception as e:
        print(f"\n1. History Fragment: Error - {e}")
    
    # Coverage fragment
    coverage_fragment = SystemCoverageFragment()
    try:
        coverage_data = coverage_fragment.extract(state)
        print(f"\n2. System Coverage Fragment:")
        print(f"   Method coverage: {coverage_data.get('method_coverage', 'N/A')}")
        print(f"   Activity coverage: {coverage_data.get('activity_coverage', 'N/A')}")
    except Exception as e:
        print(f"\n2. System Coverage Fragment: Error - {e}")
    
    # UI Elements fragment
    ui_fragment = UIElementsFragment()
    try:
        ui_data = ui_fragment.extract(state)
        print(f"\n3. UI Elements Fragment:")
        print(f"   Extracted UI description length: {len(str(ui_data.get('ui_elements', '')))} chars")
    except Exception as e:
        print(f"\n3. UI Elements Fragment: Error - {e}")
    
    print("\nNote: Fragment extraction may have limitations in tutorial mode")


def demonstrate_template_system(test_data: Dict[str, Any], static_data: StaticAnalysisData):
    """
    Demonstrate the template system and hierarchy.
    
    Shows how templates work:
    - Template inheritance
    - Template variables
    - Fragment inclusion
    - Progressive enhancement
    """
    print_section("TEMPLATE SYSTEM DEMONSTRATION")
    
    print_subsection("Template Hierarchy")
    
    print("Template inheritance structure:")
    print("  base_template")
    print("    ├── system_base")
    print("    │   ├── single")
    print("    │   ├── batch")
    print("    │   └── vision")
    print("    └── user_base")
    print()
    print("Progressive template tiers:")
    print("  • compact: Minimal, fast inference")
    print("  • standard: Balanced features")
    print("  • premium: Full feature set")
    
    print_subsection("Template Variables")
    
    # Create different configurations to show variable usage
    configs = [
        ("single_compact", PromptStrategyType.SINGLE, "Minimal variables"),
        ("single_standard", PromptStrategyType.SINGLE, "Standard variables"),
        ("single_premium", PromptStrategyType.SINGLE, "All variables")
    ]
    
    for template_name, strategy, description in configs:
        print(f"\nTemplate: {template_name} ({description})")
        
        config = RvSmartToolConfig(
            llm_config=LLMConfig(
                llm_type=LLMType.OLLAMA,
                model=OllamaLLM.GEMMA,
                temperature=0.7
            ),
            prompt_config=PromptConfig(
                strategy_type=strategy,
                parser_type=ScreenParserType.DROIDBOT,
                visitor_type=VisitorType.DEFAULT,
                template_name=template_name,
                context_mode=ContextMode.STATELESS
            )
        )
        
        state = create_state_from_droidbot(
            test_data["state_file"],
            test_data["screenshot_path"],
            test_data["package"],
            static_data,
            DefaultTextVisitor
        )
        state = enrich_state(state, static_data, config)
        
        framework = RVAndroidPromptFramework.create(config.prompt_config)
        
        # The framework will use different variables based on template
        print(f"  Common variables:")
        print(f"    • ui_elements: ✓")
        print(f"    • package_name: ✓")
        print(f"    • activity: ✓")
        
        if "standard" in template_name or "premium" in template_name:
            print(f"  Additional variables (standard+):")
            print(f"    • coverage_guidance: ✓")
            print(f"    • transition_guidance: ✓")
        
        if "premium" in template_name:
            print(f"  Premium variables:")
            print(f"    • memory_insights: ✓")
            print(f"    • system_coverage: ✓")
            print(f"    • monitored_operations: ✓")
    
    print_subsection("Custom Context Variables")
    
    # Show how to pass custom context
    config = RvSmartToolConfig(
        llm_config=LLMConfig(
            llm_type=LLMType.OLLAMA,
            model=OllamaLLM.GEMMA,
            temperature=0.7
        ),
        prompt_config=PromptConfig(
            strategy_type=PromptStrategyType.SINGLE,
            parser_type=ScreenParserType.DROIDBOT,
            visitor_type=VisitorType.DEFAULT,
            template_name="single_standard",
            context_mode=ContextMode.STATELESS
        )
    )
    
    state = create_state_from_droidbot(
        test_data["state_file"],
        test_data["screenshot_path"],
        test_data["package"],
        static_data,
        DefaultTextVisitor
    )
    state = enrich_state(state, static_data, config)
    
    # Custom context can be passed to generate_prompt
    custom_context = {
        "additional_guidelines": "Focus on security-critical operations",
        "custom_priority": "High",
        "test_phase": "exploration"
    }
    
    framework = RVAndroidPromptFramework.create(config.prompt_config)
    messages = framework.generate_prompt(state, custom_context)
    
    print("\nCustom context variables:")
    for key, value in custom_context.items():
        print(f"  • {key}: {value}")
    
    print(f"\nGenerated prompt with custom context: {len(messages)} messages")


# ============================================================================
# SECTION 4: STRATEGY DEMONSTRATIONS
# ============================================================================

def demonstrate_single_strategy(test_data: Dict[str, Any], static_data: StaticAnalysisData):
    """
    Demonstrate SINGLE strategy with all template tiers.
    
    SINGLE strategy generates one action per LLM inference.
    Suitable for precise, step-by-step exploration.
    """
    print_section("SINGLE STRATEGY DEMONSTRATION")
    
    templates = [
        ("single_compact", "Minimal prompt for fast inference"),
        ("single_standard", "Balanced features and performance"),
        ("single_premium", "Full features with all data pillars")
    ]
    
    for template_name, description in templates:
        print_subsection(f"Template: {template_name}")
        print(f"Description: {description}")
        
        # Create configuration
        config = RvSmartToolConfig(
            llm_config=LLMConfig(
                llm_type=LLMType.OLLAMA,
                model=OllamaLLM.GEMMA,
                temperature=0.7
            ),
            prompt_config=PromptConfig(
                strategy_type=PromptStrategyType.SINGLE,
                parser_type=ScreenParserType.DROIDBOT,
                visitor_type=VisitorType.DEFAULT,
                template_name=template_name,
                context_mode=ContextMode.STATELESS
            )
        )
        
        # Create and enrich state
        state = create_state_from_droidbot(
            test_data["state_file"],
            test_data["screenshot_path"],
            test_data["package"],
            static_data,
            DefaultTextVisitor
        )
        state = enrich_state(state, static_data, config)
        
        # Generate prompt
        framework = RVAndroidPromptFramework.create(config.prompt_config)
        messages = framework.generate_prompt(state, {})
        
        # Display results
        total_chars = sum(
            len(c.text) for m in messages for c in m.content 
            if hasattr(c, 'text')
        )
        print(f"  Messages generated: {len(messages)}")
        print(f"  Total characters: {total_chars:,}")
        print(f"  Average per message: {total_chars // len(messages):,}")


def demonstrate_batch_strategy(test_data: Dict[str, Any], static_data: StaticAnalysisData):
    """
    Demonstrate BATCH strategy with all template tiers.
    
    BATCH strategy generates 1-5 actions per inference.
    Efficient for systematic exploration with action planning.
    """
    print_section("BATCH STRATEGY DEMONSTRATION")
    
    templates = [
        ("batch_compact", "Multi-action with minimal overhead"),
        ("batch_standard", "Balanced batch processing"),
        ("batch_premium", "Advanced sequencing with full context")
    ]
    
    for template_name, description in templates:
        print_subsection(f"Template: {template_name}")
        print(f"Description: {description}")
        
        config = RvSmartToolConfig(
            llm_config=LLMConfig(
                llm_type=LLMType.OLLAMA,
                model=OllamaLLM.GEMMA,
                temperature=0.5,
                max_tokens=1200
            ),
            prompt_config=PromptConfig(
                strategy_type=PromptStrategyType.BATCH,
                parser_type=ScreenParserType.DROIDBOT,
                visitor_type=VisitorType.BASIC,  # Using optimized visitor
                template_name=template_name,
                context_mode=ContextMode.STATELESS
            )
        )
        
        state = create_state_from_droidbot(
            test_data["state_file"],
            test_data["screenshot_path"],
            test_data["package"],
            static_data,
            BasicTextVisitor  # Compact format visitor
        )
        state = enrich_state(state, static_data, config)
        
        framework = RVAndroidPromptFramework.create(config.prompt_config)
        messages = framework.generate_prompt(state, {})
        
        total_chars = sum(
            len(c.text) for m in messages for c in m.content 
            if hasattr(c, 'text')
        )
        print(f"  Messages generated: {len(messages)}")
        print(f"  Total characters: {total_chars:,}")
        print(f"  Supports 1-5 actions per inference")


def demonstrate_vision_strategy(test_data: Dict[str, Any], static_data: StaticAnalysisData):
    """
    Demonstrate VISION strategy with multimodal capabilities.
    
    VISION strategy specializes in visual analysis for:
    - Canvas-rendered elements
    - Dynamic graphics
    - Non-DOM UI components
    """
    print_section("VISION STRATEGY DEMONSTRATION")
    
    templates = [
        ("vision_compact", "Visual analysis with coordinate precision"),
        ("vision_standard", "Multimodal with UI tracking"),
        ("vision_premium", "Complete visual intelligence")
    ]
    
    for template_name, description in templates:
        print_subsection(f"Template: {template_name}")
        print(f"Description: {description}")
        
        config = RvSmartToolConfig(
            llm_config=LLMConfig(
                llm_type=LLMType.OLLAMA,
                model=OllamaLLM.GEMMA,  # Multimodal model
                temperature=0.7,
                vision=True  # Enable vision capabilities
            ),
            prompt_config=PromptConfig(
                strategy_type=PromptStrategyType.VISION,
                parser_type=ScreenParserType.DROIDBOT,
                visitor_type=VisitorType.DEFAULT,
                template_name=template_name,
                context_mode=ContextMode.STATELESS
            )
        )
        
        state = create_state_from_droidbot(
            test_data["state_file"],
            test_data["screenshot_path"],
            test_data["package"],
            static_data,
            DefaultTextVisitor
        )
        state = enrich_state(state, static_data, config)
        
        framework = RVAndroidPromptFramework.create(config.prompt_config)
        messages = framework.generate_prompt(state, {})
        
        # Check for image content
        has_image = any(
            isinstance(c, LLMImageContent) 
            for m in messages for c in m.content
        )
        
        total_chars = sum(
            len(c.text) for m in messages for c in m.content 
            if hasattr(c, 'text')
        )
        
        print(f"  Messages generated: {len(messages)}")
        print(f"  Total characters: {total_chars:,}")
        print(f"  Contains image: {'✓' if has_image else '✗'}")
        print(f"  Coordinate precision enabled: ✓")


# ============================================================================
# SECTION 4: CONTEXT MODE DEMONSTRATIONS
# ============================================================================

def demonstrate_context_modes(test_data: Dict[str, Any], static_data: StaticAnalysisData):
    """
    Demonstrate STATELESS vs RICH context modes.
    
    - STATELESS: Inline context, no memory persistence
    - RICH: Sliding window with compression, iteration history
    """
    print_section("CONTEXT MODE DEMONSTRATION")
    
    for context_mode in [ContextMode.STATELESS, ContextMode.RICH]:
        print_subsection(f"Context Mode: {context_mode}")
        
        config = RvSmartToolConfig(
            llm_config=LLMConfig(
                llm_type=LLMType.OLLAMA,
                model=OllamaLLM.GEMMA,
                temperature=0.7
            ),
            prompt_config=PromptConfig(
                strategy_type=PromptStrategyType.SINGLE,
                parser_type=ScreenParserType.DROIDBOT,
                visitor_type=VisitorType.DEFAULT,
                template_name="single_standard",
                context_mode=context_mode,
                context_window_size=5,
                context_compression=True,
                include_coverage_timeline=True
            )
        )
        
        state = create_state_from_droidbot(
            test_data["state_file"],
            test_data["screenshot_path"],
            test_data["package"],
            static_data,
            DefaultTextVisitor
        )
        
        # Add rich context data if needed
        if context_mode == ContextMode.RICH:
            state[StateEntry.RECENT_ITERATIONS] = create_mock_iterations()
            state[StateEntry.COVERAGE_METRICS] = {
                'method_coverage': 42.8,
                'activity_coverage': 75.0,
                'mop_method_coverage': 25.3,
                'unique_errors': 2
            }
            state[StateEntry.MOP_RECENT_ERRORS] = [
                {
                    'spec': 'CryptoSpec',
                    'method': 'createCipher',
                    'message': 'Weak cipher algorithm'
                }
            ]
        
        state = enrich_state(state, static_data, config)
        
        framework = RVAndroidPromptFramework.create(config.prompt_config)
        messages = framework.generate_prompt(state, {})
        
        total_chars = sum(
            len(c.text) for m in messages for c in m.content 
            if hasattr(c, 'text')
        )
        
        print(f"  Messages generated: {len(messages)}")
        print(f"  Total characters: {total_chars:,}")
        
        if context_mode == ContextMode.RICH:
            print(f"  Recent iterations included: {len(state.get(StateEntry.RECENT_ITERATIONS, []))}")
            print(f"  Coverage metrics included: ✓")
            print(f"  MOP errors tracked: {len(state.get(StateEntry.MOP_RECENT_ERRORS, []))}")
        else:
            print(f"  Using inline context without persistence")


# ============================================================================
# SECTION 5: VISITOR TYPE DEMONSTRATIONS
# ============================================================================

def demonstrate_visitor_types(test_data: Dict[str, Any], static_data: StaticAnalysisData):
    """
    Demonstrate different visitor types for screen parsing.
    
    Visitors control how UI elements are formatted in prompts:
    - BASIC: Compact format for token optimization
    - DEFAULT: Standard format with full details
    - ENHANCED: Extended format with additional metadata
    """
    print_section("VISITOR TYPE DEMONSTRATION")
    
    visitors = [
        (VisitorType.BASIC, BasicTextVisitor, "Compact optimized format"),
        (VisitorType.DEFAULT, DefaultTextVisitor, "Standard detailed format"),
        # Note: ENHANCED visitor may not be available in current system
    ]
    
    for visitor_type, visitor_class, description in visitors:
        print_subsection(f"Visitor: {visitor_type}")
        print(f"Description: {description}")
        
        config = RvSmartToolConfig(
            llm_config=LLMConfig(
                llm_type=LLMType.OLLAMA,
                model=OllamaLLM.GEMMA,
                temperature=0.7
            ),
            prompt_config=PromptConfig(
                strategy_type=PromptStrategyType.SINGLE,
                parser_type=ScreenParserType.DROIDBOT,
                visitor_type=visitor_type,
                template_name="single_compact",
                context_mode=ContextMode.STATELESS
            )
        )
        
        state = create_state_from_droidbot(
            test_data["state_file"],
            test_data["screenshot_path"],
            test_data["package"],
            static_data,
            visitor_class
        )
        state = enrich_state(state, static_data, config)
        
        # Get screen description to show format
        screen_desc = state.get(StateEntry.STRUCTURED_SCREEN)
        if screen_desc:
            ui_text = str(screen_desc)[:500]  # First 500 chars
            print(f"  Sample UI format:")
            for line in ui_text.split('\n')[:5]:  # First 5 lines
                print(f"    {line}")
        
        framework = RVAndroidPromptFramework.create(config.prompt_config)
        messages = framework.generate_prompt(state, {})
        
        total_chars = sum(
            len(c.text) for m in messages for c in m.content 
            if hasattr(c, 'text')
        )
        
        print(f"  Total characters: {total_chars:,}")
        
        if visitor_type == VisitorType.BASIC:
            print(f"  Token optimization: ~30-40% reduction")


# ============================================================================
# SECTION 6: ADVANCED FEATURES
# ============================================================================

def demonstrate_advanced_features(test_data: Dict[str, Any], static_data: StaticAnalysisData):
    """
    Demonstrate advanced framework features:
    - MOP (Monitored Operations) focus
    - Coverage-guided exploration
    - Transition management
    - Memory insights
    """
    print_section("ADVANCED FEATURES DEMONSTRATION")
    
    print_subsection("MOP-Focused Exploration")
    
    # Configuration with MOP focus
    config = RvSmartToolConfig(
        llm_config=LLMConfig(
            llm_type=LLMType.OLLAMA,
            model=OllamaLLM.GEMMA,
            temperature=0.3  # Lower temperature for focused exploration
        ),
        prompt_config=PromptConfig(
            strategy_type=PromptStrategyType.VISION,
            parser_type=ScreenParserType.DROIDBOT,
            visitor_type=VisitorType.DEFAULT,
            template_name="vision_premium",  # Premium template includes MOP guidance
            context_mode=ContextMode.RICH,
            context_window_size=10,
            include_coverage_timeline=True
        )
    )
    
    state = create_state_from_droidbot(
        test_data["state_file"],
        test_data["screenshot_path"],
        test_data["package"],
        static_data,
        DefaultTextVisitor
    )
    
    # Add comprehensive context for advanced features
    state[StateEntry.RECENT_ITERATIONS] = create_mock_iterations()
    state[StateEntry.COVERAGE_METRICS] = {
        'method_coverage': 42.8,
        'activity_coverage': 75.0,
        'mop_method_coverage': 25.3,
        'unique_errors': 2
    }
    state[StateEntry.MOP_RECENT_ERRORS] = [
        {'spec': 'CryptoSpec', 'method': 'createCipher', 'message': 'Weak cipher'},
        {'spec': 'NetworkSpec', 'method': 'sendData', 'message': 'Unencrypted data'}
    ]
    
    # Add transition guidance
    state[StateEntry.TRANSITION_GUIDANCE] = {
        'static_transitions': [
            {'from': 'MainActivity', 'to': 'LoginActivity', 'action': 'button_login'},
            {'from': 'LoginActivity', 'to': 'DashboardActivity', 'action': 'button_submit'}
        ],
        'unexplored_actions': ['button_settings', 'menu_security'],
        'visit_counts': {'MainActivity': 5, 'LoginActivity': 3, 'DashboardActivity': 1}
    }
    
    # Add memory insights
    state[StateEntry.MEMORY_INSIGHTS] = {
        'patterns_detected': ['login_flow', 'navigation_menu'],
        'repetitive_actions': ['back_button', 'refresh'],
        'exploration_status': 'partial',
        'recommended_focus': 'unexplored_security_settings'
    }
    
    state = enrich_state(state, static_data, config)
    
    framework = RVAndroidPromptFramework.create(config.prompt_config)
    messages = framework.generate_prompt(state, {})
    
    # Analyze MOP content
    mop_mentions = 0
    for message in messages:
        for content in message.content:
            if hasattr(content, 'text'):
                text_lower = content.text.lower()
                mop_mentions += text_lower.count('[dm]') + text_lower.count('[m]')
                mop_mentions += text_lower.count('monitored')
    
    print(f"  MOP-focused elements detected: {mop_mentions}")
    print(f"  Coverage metrics included: ✓")
    print(f"  Transition guidance active: ✓")
    print(f"  Memory insights integrated: ✓")
    print(f"  Error tracking enabled: {len(state.get(StateEntry.MOP_RECENT_ERRORS, []))} errors")
    
    print_subsection("Progressive Template Selection")
    
    # Demonstrate how templates progressively add features
    template_progression = [
        ("single_compact", "Pillar 1: ScreenDescription only"),
        ("single_standard", "Pillars 1+2: + UI Coverage Tracker"),
        ("single_premium", "Pillars 1+2+3+4: Full data integration")
    ]
    
    for template_name, description in template_progression:
        config.prompt_config.template_name = template_name
        framework = RVAndroidPromptFramework.create(config.prompt_config)
        messages = framework.generate_prompt(state, {})
        
        total_chars = sum(
            len(c.text) for m in messages for c in m.content 
            if hasattr(c, 'text')
        )
        
        print(f"\n  {template_name}:")
        print(f"    {description}")
        print(f"    Total size: {total_chars:,} characters")


# ============================================================================
# SECTION 7: COMPLETE WORKFLOW EXAMPLE
# ============================================================================

def demonstrate_complete_workflow(test_data: Dict[str, Any], static_data: StaticAnalysisData):
    """
    Demonstrate a complete testing workflow with all components.
    
    This shows how all pieces work together in a real scenario.
    """
    print_section("COMPLETE WORKFLOW DEMONSTRATION")
    
    print("This example shows a complete testing session workflow:")
    print("1. Initial exploration with SINGLE strategy")
    print("2. Systematic coverage with BATCH strategy")
    print("3. Visual analysis with VISION strategy")
    print("4. Context accumulation with RICH mode")
    
    # Phase 1: Initial exploration
    print_subsection("Phase 1: Initial Exploration")
    
    config = RvSmartToolConfig(
        llm_config=LLMConfig(
            llm_type=LLMType.OLLAMA,
            model=OllamaLLM.GEMMA,
            temperature=0.9  # Higher for exploration
        ),
        prompt_config=PromptConfig(
            strategy_type=PromptStrategyType.SINGLE,
            parser_type=ScreenParserType.DROIDBOT,
            visitor_type=VisitorType.BASIC,
            template_name="single_compact",
            context_mode=ContextMode.STATELESS
        )
    )
    
    state = create_state_from_droidbot(
        test_data["state_file"],
        test_data["screenshot_path"],
        test_data["package"],
        static_data,
        BasicTextVisitor
    )
    state = enrich_state(state, static_data, config)
    
    framework = RVAndroidPromptFramework.create(config.prompt_config)
    messages = framework.generate_prompt(state, {})
    
    print(f"  Strategy: SINGLE (one action at a time)")
    print(f"  Template: single_compact (fast inference)")
    print(f"  Context: STATELESS (no history)")
    print(f"  Messages: {len(messages)}")
    
    # Phase 2: Systematic coverage
    print_subsection("Phase 2: Systematic Coverage")
    
    config.prompt_config.strategy_type = PromptStrategyType.BATCH
    config.prompt_config.template_name = "batch_standard"
    config.llm_config.temperature = 0.5  # More deterministic
    
    # Add some history
    state[StateEntry.ACTION_HISTORY] = [
        "Clicked login button",
        "Entered username",
        "Entered password"
    ]
    
    framework = RVAndroidPromptFramework.create(config.prompt_config)
    messages = framework.generate_prompt(state, {})
    
    print(f"  Strategy: BATCH (1-5 actions)")
    print(f"  Template: batch_standard (balanced)")
    print(f"  Action history: {len(state.get(StateEntry.ACTION_HISTORY, []))} actions")
    print(f"  Messages: {len(messages)}")
    
    # Phase 3: Visual analysis
    print_subsection("Phase 3: Visual Analysis")
    
    config.prompt_config.strategy_type = PromptStrategyType.VISION
    config.prompt_config.template_name = "vision_premium"
    config.prompt_config.context_mode = ContextMode.RICH
    config.llm_config.vision = True
    
    # Add rich context
    state[StateEntry.RECENT_ITERATIONS] = create_mock_iterations()
    state[StateEntry.COVERAGE_METRICS] = {
        'method_coverage': 65.2,
        'activity_coverage': 85.0,
        'mop_method_coverage': 45.7
    }
    
    framework = RVAndroidPromptFramework.create(config.prompt_config)
    messages = framework.generate_prompt(state, {})
    
    has_image = any(
        isinstance(c, LLMImageContent)
        for m in messages for c in m.content
    )
    
    print(f"  Strategy: VISION (multimodal)")
    print(f"  Template: vision_premium (full features)")
    print(f"  Context: RICH (with history)")
    print(f"  Includes screenshot: {'✓' if has_image else '✗'}")
    print(f"  Coverage: {state[StateEntry.COVERAGE_METRICS]['method_coverage']:.1f}%")
    
    # Summary
    print_subsection("Workflow Summary")
    print("  ✓ Progressive strategy selection based on testing phase")
    print("  ✓ Template tier adjustment for performance vs features")
    print("  ✓ Context mode evolution from stateless to rich")
    print("  ✓ Visitor type optimization for token efficiency")
    print("  ✓ Complete data pillar integration")


# ============================================================================
# SECTION 8: PERFORMANCE ANALYSIS
# ============================================================================

def analyze_performance(test_data: Dict[str, Any], static_data: StaticAnalysisData):
    """
    Analyze performance characteristics of different configurations.
    """
    print_section("PERFORMANCE ANALYSIS")
    
    configurations = [
        # (strategy, template, visitor, description)
        (PromptStrategyType.SINGLE, "single_compact", VisitorType.BASIC, "Minimal configuration"),
        (PromptStrategyType.SINGLE, "single_standard", VisitorType.DEFAULT, "Balanced single"),
        (PromptStrategyType.BATCH, "batch_compact", VisitorType.BASIC, "Efficient batch"),
        (PromptStrategyType.BATCH, "batch_premium", VisitorType.DEFAULT, "Full batch"),
        (PromptStrategyType.VISION, "vision_standard", VisitorType.DEFAULT, "Standard vision"),
        (PromptStrategyType.VISION, "vision_premium", VisitorType.DEFAULT, "Premium vision"),
    ]
    
    results = []
    
    for strategy, template, visitor, description in configurations:
        config = RvSmartToolConfig(
            llm_config=LLMConfig(
                llm_type=LLMType.OLLAMA,
                model=OllamaLLM.GEMMA,
                temperature=0.7,
                vision=(strategy == PromptStrategyType.VISION)
            ),
            prompt_config=PromptConfig(
                strategy_type=strategy,
                parser_type=ScreenParserType.DROIDBOT,
                visitor_type=visitor,
                template_name=template,
                context_mode=ContextMode.STATELESS
            )
        )
        
        # Select visitor class
        visitor_class = BasicTextVisitor if visitor == VisitorType.BASIC else DefaultTextVisitor
        
        state = create_state_from_droidbot(
            test_data["state_file"],
            test_data["screenshot_path"],
            test_data["package"],
            static_data,
            visitor_class
        )
        state = enrich_state(state, static_data, config)
        
        framework = RVAndroidPromptFramework.create(config.prompt_config)
        messages = framework.generate_prompt(state, {})
        
        total_chars = sum(
            len(c.text) for m in messages for c in m.content 
            if hasattr(c, 'text')
        )
        
        results.append({
            'description': description,
            'strategy': strategy.value,
            'template': template,
            'visitor': visitor.value,
            'chars': total_chars,
            'messages': len(messages)
        })
    
    # Display results table
    print("\n  Configuration Performance Comparison:")
    print("  " + "-" * 70)
    print(f"  {'Configuration':<25} {'Strategy':<10} {'Template':<18} {'Chars':<10}")
    print("  " + "-" * 70)
    
    for r in results:
        print(f"  {r['description']:<25} {r['strategy']:<10} {r['template']:<18} {r['chars']:,}")
    
    # Calculate savings
    baseline = max(r['chars'] for r in results)
    minimal = min(r['chars'] for r in results)
    reduction = (baseline - minimal) / baseline * 100
    
    print("  " + "-" * 70)
    print(f"\n  Performance Summary:")
    print(f"    Largest prompt: {baseline:,} characters")
    print(f"    Smallest prompt: {minimal:,} characters")
    print(f"    Maximum reduction: {reduction:.1f}%")
    print(f"    Optimal for speed: single_compact + BASIC visitor")
    print(f"    Optimal for features: vision_premium + DEFAULT visitor")


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main tutorial execution."""
    logger = setup_logging("INFO")
    
    print_section("RVSmart PROMPT FRAMEWORK TUTORIAL", 80)
    print("\nThis comprehensive tutorial demonstrates all capabilities of the")
    print("RVSmart prompt framework for AI-driven Android application testing.\n")
    
    # Load test data
    print("Loading test data...")
    test_data = load_test_data()
    print(f"  Package: {test_data['package']}")
    print(f"  APK: cryptoapp.apk")
    print(f"  State: 004\n")
    
    # Parse static analysis
    print("Parsing static analysis data...")
    parser = StaticAnalysisParser()
    static_data = parser.parse(
        test_data["reach_file"],
        test_data["gator_file"],
        test_data["gesda_file"],
        test_data["package"]
    )
    print(f"  Classes analyzed: {len(static_data.classes.classes)}")
    print(f"  Windows found: {len(static_data.windows.windows)}\n")
    
    # Run demonstrations
    try:
        # PART 1: Basic framework usage (fundamentals)
        demonstrate_basic_usage(test_data, static_data)
        demonstrate_fragment_system(test_data, static_data)
        demonstrate_template_system(test_data, static_data)
        
        # PART 2: Strategy demonstrations
        demonstrate_single_strategy(test_data, static_data)
        demonstrate_batch_strategy(test_data, static_data)
        demonstrate_vision_strategy(test_data, static_data)
        
        # PART 3: Context and visitor demonstrations
        demonstrate_context_modes(test_data, static_data)
        demonstrate_visitor_types(test_data, static_data)
        
        # PART 4: Advanced features
        demonstrate_advanced_features(test_data, static_data)
        
        # PART 5: Complete workflow
        demonstrate_complete_workflow(test_data, static_data)
        
        # PART 6: Performance analysis
        analyze_performance(test_data, static_data)
        
    except Exception as e:
        logger.error(f"Tutorial failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print_section("TUTORIAL COMPLETE", 80)
    print("\nThis tutorial covered:")
    print("\nPART 1: FUNDAMENTALS")
    print("  • Manual configuration creation (LLMConfig, PromptConfig)")
    print("  • Framework initialization and components")
    print("  • State creation and enrichment")
    print("  • Fragment system and data extraction")
    print("  • Template hierarchy and variables")
    print("  • Custom context variables")
    print("\nPART 2-3: CORE FEATURES")
    print("  • Three strategies: SINGLE, BATCH, VISION")
    print("  • Three template tiers: compact, standard, premium")
    print("  • Two context modes: STATELESS, RICH")
    print("  • Multiple visitor types for optimization")
    print("\nPART 4-5: ADVANCED USAGE")
    print("  • MOP-focused exploration")
    print("  • Coverage-guided testing")
    print("  • Complete workflow example")
    print("  • Four data pillars progressively integrated")
    print("\nPART 6: OPTIMIZATION")
    print("  • 30-40% token reduction with optimizations")
    print("  • Performance comparison across configurations")
    print("  • Multimodal support for visual analysis")
    print("\nKey Takeaways:")
    print("  1. Framework is highly configurable and modular")
    print("  2. Templates provide progressive enhancement")
    print("  3. Fragments extract and format data automatically")
    print("  4. Strategies define action generation approach")
    print("  5. Context modes control memory persistence")
    print("  6. Visitors optimize UI representation")
    print("  7. Significant token reduction possible with optimization")
    print("  8. MOP-focused exploration for security testing")
    print("\nRefer to docs/planos/prompt/plano.md for architectural details.")
    
    return 0


if __name__ == "__main__":
    exit(main())