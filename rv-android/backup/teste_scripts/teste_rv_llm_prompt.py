#!/usr/bin/env python3
"""
Simple test for prompt generation with RVSmart framework.

Tests the prompt generation system with:
- Templates in rvsmart-tool
- RvSmartToolConfig for configuration
- Template registration with PromptFramework
- Clean LLMConfig integration
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Type

# Add the modules to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "modules" / "rv-android-core" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-llm" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rvsmart-tool" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-screen-parser" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-static-analysis" / "src"))

# Import after path setup
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
from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser
from rvsmart_tool.config.tool_config import RvSmartToolConfig
from rvsmart_tool.llm.prompt.rvsmart_framework import RVAndroidPromptFramework
from rvsmart_tool.llm.service.memory_manager import MemoryManager
from rvsmart_tool.llm.service.transition_manager import TransitionManager
from rvsmart_tool.llm.service.action_service import LLMActionService

# Setup RVSEC_HOME before importing modules
current_directory = os.getcwd()
parent_directory = os.path.dirname(current_directory)
os.environ[constants.ENV_RVSEC_HOME] = parent_directory


def setup_logging(debug: bool = True):
    """Set up logging configuration."""
    from rv_android_core.util.logging.manager import LoggingManager

    # Setup basic logging first
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )

    # Silence noisy third-party loggers
    for noisy_logger in ["androguard", "matplotlib", "PIL", "requests", "urllib3"]:
        logging.getLogger(noisy_logger).setLevel(logging.ERROR)

    for noisy_logger in ["rvandroid_core.domain.window", "rvandroid_core.domain.widget", "rv_static_analysis.parser.static", "rvandroid_core.domain.classes"
                         "rv_android_core.util.utils.read_json"]:
        logging.getLogger(noisy_logger).setLevel(logging.INFO)

    # Get the logging manager
    logging_manager = LoggingManager.get_instance()
    logging_manager.configure_output(
        console=True,
        file=False,
        console_level=10 if debug else 20,
        file_level=10,
        json_format=False
    )

    return logging_manager.get_logger('teste_rv_llm_prompt')


def read_droidbot_state(filename: str) -> Dict[str, Any]:
    """Loads a DroidBot state file."""
    with open(filename, 'r') as file:
        return json.load(file)


def enrich_state(state, static_data: StaticAnalysisData, config: RvSmartToolConfig):
    memory_manager = MemoryManager(static_data=static_data)
    transition_manager = TransitionManager(static_data=static_data)
    llm_service = LLMActionService(
        static_data=static_data,
        tool_config=config
    )

    # Override service's managers with our instances for testing
    llm_service.memory_manager = memory_manager
    llm_service.transition_manager = transition_manager

    llm_service._pre_process_state(state)
    return state


def create_state_from_droidbot_state(droidbot_state_file: str, screenshot_path: str, package: str,
                                     static_data: StaticAnalysisData, visitor: Type[AbstractScreenVisitor]):
    screen_info = read_droidbot_state(droidbot_state_file)
    parser = ParserFactory.create(ScreenParserType.DROIDBOT, visitor)
    screen_description: ScreenDescription = parser.parse_screen(screen_info, static_data)
    print(screen_description)
    exit(1)
    state = {
        StateEntry.PACKAGE_NAME: package,
        StateEntry.ACTIVITY: screen_description.activity,
        StateEntry.VIEW_TREE: screen_info.get(StateEntry.VIEW_TREE, screen_info.get("view_tree", {})),
        StateEntry.SCREENSHOT_PATH: screenshot_path,
        StateEntry.STRUCTURED_SCREEN: screen_description
    }
    return state


def create_mock_iterations():
    """Create mock iteration data for rich context testing."""
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
                {'explanation': 'navigated to settings menu [M]'}
            ],
            'coverage_metrics': {
                'method_coverage': 35.2,
                'mop_method_coverage': 18.5,
                'unique_errors': 1
            },
            'mop_errors': [
                {'spec': 'NetworkSpec', 'method': 'sendData', 'message': 'Unencrypted transmission detected'}
            ]
        },
        {
            'activity': 'SettingsActivity',
            'actions_generated': [
                {'explanation': 'opened encryption settings [DM]'},
                {'explanation': 'modified cipher configuration [DM]'}
            ],
            'coverage_metrics': {
                'method_coverage': 42.8,
                'mop_method_coverage': 25.3,
                'unique_errors': 2
            },
            'mop_errors': [
                {'spec': 'CryptoSpec', 'method': 'createCipher', 'message': 'Weak cipher algorithm used'}
            ]
        }
    ]


def tmp_mop_vision_strategy(droidbot_state_file: str, screenshot_path: str, package: str, static_data: StaticAnalysisData):
    """Test MOP Vision strategy specifically."""
    print("============================================================")
    print("🧪 TESTING MOP VISION STRATEGY")
    print("============================================================")
    
    # Create Vision prompt config with MOP focus via context
    prompt_config = PromptConfig(
        strategy_type=PromptStrategyType.VISION,  # Use VISION strategy (MOP_VISION was consolidated)
        parser_type=ScreenParserType.DROIDBOT,
        visitor_type=VisitorType.DEFAULT,
        template_name="vision_premium",  # NEW: Use progressive template
        max_context_length=8192,
        context_mode=ContextMode.STATELESS,
        context_window_size=10,
        context_compression=True,
        include_coverage_timeline=False
    )
    
    # Create LLM config
    llm_config = LLMConfig(
        llm_type=LLMType.OLLAMA,
        model=OllamaLLM.GEMMA,  # Use multimodal GEMMA model
        temperature=0.7
    )
    
    # Create tool config
    tool_config = RvSmartToolConfig(
        llm_config=llm_config,
        prompt_config=prompt_config,
        debug_mode=True
    )
    
    # Initialize framework
    framework = RVAndroidPromptFramework.create(prompt_config)
    
    # Parse state file using existing method
    from rv_screen_parser.parser.screen.visitor.default_visitor import DefaultTextVisitor
    state = create_state_from_droidbot_state(
        droidbot_state_file, screenshot_path, package, static_data, DefaultTextVisitor
    )
    
    # Add MOP-specific data for verification
    print(f"🔧 MOP Strategy Configuration:")
    print(f"  • Strategy Type: {prompt_config.strategy_type}")
    print(f"  • LLM Model: {llm_config.model}")
    print(f"  • Context Mode: {prompt_config.context_mode}")
    
    # Generate prompt
    print(f"\n🚀 Generating prompt with MOP Vision strategy...")
    messages = framework.generate_prompt(state, {})
    
    print(f"✅ SUCCESS: Generated {len(messages)} messages using VISION strategy with premium template")
    print(f"📋 Strategy: {prompt_config.strategy_type}")
    print(f"📊 State keys: {list(state.keys())}")
    
    # Verify MOP-specific template was used
    for i, message in enumerate(messages, 1):
        print(f"\n📄 MESSAGE {i}: {message.role}")
        for j, content in enumerate(message.content, 1):
            if hasattr(content, 'text'):
                # Check if MOP-specific instructions are present
                if 'monitored operations' in content.text.lower() or 'mop' in content.text.lower() or '[dm]' in content.text.lower():
                    print(f"  ✅ Content {j}: Contains MOP-specific instructions")
                else:
                    print(f"  📝 Content {j}: Standard content ({len(content.text)} chars)")
            elif hasattr(content, 'url'):
                print(f"  🖼️ Content {j}: Image - {content.url}")
    
    print(f"\n🔍 Generated prompt: {len(messages)} messages\n")
    
    # Display messages with detailed formatting
    for i, message in enumerate(messages, 1):
        print("─" * 40)
        print(f"MESSAGE {i}: {message.role} ({len(message.content)} content items)")
        print("─" * 40)
        
        for content in message.content:
            if hasattr(content, 'text'):
                print(f"[TEXT: {content.text[:500]}...]" if len(content.text) > 500 else f"[TEXT: {content.text}]")
            elif hasattr(content, 'url'):
                print(f"[IMAGE: {content.url}]")
    
    return messages

def tmp_context_mode(droidbot_state_file, screenshot_path, package, static_data, context_mode: str):
    """Test prompt generation with specific context mode."""
    print(f"\n{'='*60}")
    print(f"🧪 TESTING CONTEXT MODE: {context_mode}")
    print(f"{'='*60}")
    
    llm_config = LLMConfig(
        llm_type=LLMType.OLLAMA,
        model=OllamaLLM.GEMMA,
        vision=True,
        temperature=0.3,
        max_tokens=800
    )
    
    # Create prompt config with context mode settings
    prompt_config = PromptConfig(
        strategy_type=PromptStrategyType.VISION,
        parser_type=ScreenParserType.DROIDBOT,
        visitor_type=VisitorType.BASIC,
        template_name="vision_standard",  # NEW: Use progressive template
        max_context_length=500,
        # Context mode configuration
        context_mode=context_mode,
        context_window_size=5,
        context_compression=True,
        include_coverage_timeline=True
    )
    
    tool_config = RvSmartToolConfig(
        llm_config=llm_config,
        prompt_config=prompt_config
    )

    basic_state = create_state_from_droidbot_state(droidbot_state_file, screenshot_path, package, static_data, DefaultTextVisitor)
    
    # Add mock iterations for rich context testing
    if context_mode == ContextMode.RICH:
        basic_state[StateEntry.RECENT_ITERATIONS] = create_mock_iterations()
        # Add some coverage metrics for testing
        basic_state[StateEntry.COVERAGE_METRICS] = {
            'method_coverage': 42.8,
            'activity_coverage': 75.0,
            'mop_method_coverage': 25.3,
            'unique_errors': 2
        }
        basic_state[StateEntry.MOP_RECENT_ERRORS] = [
            {
                'spec': 'CryptoSpec',
                'class_full_name': 'com.example.crypto.CipherManager',
                'method': 'createCipher',
                'message': 'Weak cipher algorithm used',
                'detected_at': '2025-08-18T10:30:00'
            }
        ]
    
    state = enrich_state(basic_state, static_data, tool_config)

    setup_logging(True)

    framework = RVAndroidPromptFramework.create(prompt_config)

    prompt = framework.generate_prompt(state)
    
    # Print context mode info
    print(f"📋 Context Mode: {context_mode}")
    print(f"📊 State keys: {list(state.keys())}")
    if context_mode == ContextMode.RICH:
        print(f"🔄 Recent iterations: {len(state.get(StateEntry.RECENT_ITERATIONS, []))}")
        print(f"📈 Coverage metrics: {bool(state.get(StateEntry.COVERAGE_METRICS))}")
        print(f"⚠️  MOP errors: {len(state.get(StateEntry.MOP_RECENT_ERRORS, []))}")
    
    print(f"\n🔍 Generated prompt: {len(prompt)} messages")
    
    for i, msg in enumerate(prompt):
        print(f"\n{'─'*40}")
        print(f"MESSAGE {i+1}: {msg.role} ({len(msg.content)} content items)")
        print(f"{'─'*40}")
        
        for j, content in enumerate(msg.content):
            if isinstance(content, LLMTextContent):
                print(f"[TEXT: {content.text}]")
                # # Show first and last few lines of text content
                # lines = content.text.strip().split('\n')
                # if len(lines) <= 10:
                #     print(content.text)
                # else:
                #     print('\n'.join(lines[:5]))
                #     print(f"\n... [{len(lines) - 10} lines omitted] ...\n")
                #     print('\n'.join(lines[-5:]))
            elif isinstance(content, LLMImageContent):
                print(f"[IMAGE: {content.url}]")
            else:
                print(f"[CONTENT: {type(content)}]")
    
    return prompt


def tmp_both_context_modes(droidbot_state_file, screenshot_path, package, static_data):
    """Test both STATELESS and RICH context modes."""
    print("🚀 CONTEXT MODE COMPARISON TEST")
    print("Testing Vision strategy with both context modes\n")
    
    # Test STATELESS mode (default)
    stateless_prompt = tmp_context_mode(
        droidbot_state_file, screenshot_path, package, static_data,
        ContextMode.STATELESS
    )
    
    # Test RICH mode  
    rich_prompt = tmp_context_mode(
        droidbot_state_file, screenshot_path, package, static_data,
        ContextMode.RICH
    )
    
    # Compare results
    print(f"\n{'='*60}")
    print("📊 COMPARISON SUMMARY")
    print(f"{'='*60}")
    print(f"STATELESS mode:")
    print(f"  • Messages: {len(stateless_prompt)}")
    print(f"  • Total content items: {sum(len(msg.content) for msg in stateless_prompt)}")
    
    print(f"\nRICH mode:")
    print(f"  • Messages: {len(rich_prompt)}")
    print(f"  • Total content items: {sum(len(msg.content) for msg in rich_prompt)}")
    
    # Calculate text length difference
    stateless_text = ""
    rich_text = ""
    
    for msg in stateless_prompt:
        for content in msg.content:
            if isinstance(content, LLMTextContent):
                stateless_text += content.text
                
    for msg in rich_prompt:
        for content in msg.content:
            if isinstance(content, LLMTextContent):
                rich_text += content.text
    
    print(f"\nText length comparison:")
    print(f"  • STATELESS: {len(stateless_text)} characters")
    print(f"  • RICH: {len(rich_text)} characters")
    print(f"  • Difference: {len(rich_text) - len(stateless_text):+d} characters")
    
    if len(rich_text) > len(stateless_text):
        print("  ✅ RICH mode provides additional context as expected")
    else:
        print("  ⚠️  RICH mode has similar or less content")
    
    return stateless_prompt, rich_prompt

def tmp_all_optimization_scenarios(droidbot_state_file, screenshot_path, package, static_data):
    """
    Comprehensive test of ALL strategies, visitors, and context modes to validate prompt optimizations.
    This function tests every possible combination to ensure our optimizations work correctly.
    """
    print("🚀 COMPREHENSIVE OPTIMIZATION VALIDATION TEST")
    print("=" * 80)
    print("Testing ALL strategies, visitors, and context modes")
    print("Validating: BasicTextVisitor optimization, Memory format, Templates XML")
    print("=" * 80)
    
    # All available strategies (MOP_VISION was consolidated into VISION)
    strategies = [
        PromptStrategyType.SINGLE,
        PromptStrategyType.BATCH, 
        PromptStrategyType.VISION
    ]
    
    # All available visitors 
    visitors = [
        (VisitorType.BASIC, BasicTextVisitor, "BASIC (Optimized)"),
        (VisitorType.DEFAULT, DefaultTextVisitor, "DEFAULT"),
        # Note: DETAILED visitor may not exist in current system
    ]
    
    # All available context modes
    context_modes = [
        (ContextMode.STATELESS, "STATELESS"),
        (ContextMode.RICH, "RICH")
    ]
    
    results = []
    tmp_count = 0
    success_count = 0
    
    for strategy in strategies:
        for visitor_type, visitor_class, visitor_name in visitors:
            for context_mode, context_name in context_modes:
                tmp_count += 1
                
                print(f"\n🧪 TEST {tmp_count}: {strategy} + {visitor_name} + {context_name}")
                print("-" * 60)
                
                try:
                    # Create configurations
                    llm_config = LLMConfig(
                        llm_type=LLMType.OLLAMA,
                        model=OllamaLLM.GEMMA,
                        vision=True,
                        temperature=0.3,
                        max_tokens=800
                    )
                    
                    # Map strategies to progressive templates
                    template_mapping = {
                        PromptStrategyType.SINGLE: "single_compact",
                        PromptStrategyType.BATCH: "batch_standard", 
                        PromptStrategyType.VISION: "vision_premium"
                    }
                    
                    prompt_config = PromptConfig(
                        strategy_type=strategy,
                        parser_type=ScreenParserType.DROIDBOT,
                        visitor_type=visitor_type,
                        template_name=template_mapping[strategy],  # NEW: Use progressive templates
                        max_context_length=8192,
                        context_mode=context_mode,
                        context_window_size=5,
                        context_compression=True,
                        include_coverage_timeline=True
                    )
                    
                    tool_config = RvSmartToolConfig(
                        llm_config=llm_config,
                        prompt_config=prompt_config,
                        debug_mode=True
                    )
                    
                    # Create state with specific visitor
                    state = create_state_from_droidbot_state(
                        droidbot_state_file, screenshot_path, package, static_data, visitor_class
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
                                'class_full_name': 'com.example.crypto.CipherManager',
                                'method': 'createCipher',
                                'message': 'Weak cipher algorithm used',
                                'detected_at': '2025-08-25T10:30:00'
                            }
                        ]
                    
                    # Enrich state
                    state = enrich_state(state, static_data, tool_config)
                    
                    # Generate prompt
                    framework = RVAndroidPromptFramework.create(prompt_config)
                    messages = framework.generate_prompt(state, {})
                    
                    # Analyze results
                    total_text = ""
                    total_chars = 0
                    has_mop_content = False
                    has_optimized_format = False
                    
                    for message in messages:
                        for content in message.content:
                            if hasattr(content, 'text'):
                                text = content.text
                                total_text += text
                                total_chars += len(text)
                                
                                # Check for MOP-specific content
                                if any(marker in text.lower() for marker in ['[dm]', '[m]', 'monitored operations', 'javamop']):
                                    has_mop_content = True
                                
                                # Check for optimized formats (compact BasicTextVisitor)
                                if visitor_type == VisitorType.BASIC:
                                    # Look for compact format: Button {text}, Text field {placeholder}
                                    if any(pattern in text for pattern in ['Button {', 'Text field', 'Text {', 'Checkbox (', 'Switch (']):
                                        has_optimized_format = True
                    
                    result = {
                        'strategy': strategy,
                        'visitor': visitor_name,
                        'context_mode': context_name,
                        'success': True,
                        'messages': len(messages),
                        'total_chars': total_chars,
                        'has_mop_content': has_mop_content,
                        'has_optimized_format': has_optimized_format,
                        'error': None
                    }
                    
                    results.append(result)
                    success_count += 1
                    
                    # Print summary
                    print(f"✅ SUCCESS")
                    print(f"   Messages: {len(messages)}")
                    print(f"   Total characters: {total_chars:,}")
                    print(f"   MOP content detected: {'✅' if has_mop_content else '❌'}")
                    if visitor_type == VisitorType.BASIC:
                        print(f"   Optimized format detected: {'✅' if has_optimized_format else '❌'}")
                    
                    # Show sample content for key optimizations
                    if visitor_type == VisitorType.BASIC and has_optimized_format:
                        print(f"   🎯 OPTIMIZATION VERIFIED: BasicTextVisitor using compact format")
                        
                except Exception as e:
                    result = {
                        'strategy': strategy,
                        'visitor': visitor_name, 
                        'context_mode': context_name,
                        'success': False,
                        'messages': 0,
                        'total_chars': 0,
                        'has_mop_content': False,
                        'has_optimized_format': False,
                        'error': str(e)
                    }
                    
                    results.append(result)
                    print(f"❌ FAILED: {e}")
    
    # Generate comprehensive summary
    print(f"\n{'='*80}")
    print("📊 COMPREHENSIVE OPTIMIZATION VALIDATION RESULTS")  
    print(f"{'='*80}")
    print(f"Total tests: {tmp_count}")
    print(f"Successful: {success_count}")
    print(f"Failed: {tmp_count - success_count}")
    print(f"Success rate: {(success_count/tmp_count)*100:.1f}%")
    
    # Analyze optimization effectiveness
    basic_visitor_tests = [r for r in results if 'BASIC' in r['visitor'] and r['success']]
    default_visitor_tests = [r for r in results if 'DEFAULT' in r['visitor'] and r['success']]
    
    if basic_visitor_tests and default_visitor_tests:
        avg_basic_chars = sum(r['total_chars'] for r in basic_visitor_tests) / len(basic_visitor_tests)
        avg_default_chars = sum(r['total_chars'] for r in default_visitor_tests) / len(default_visitor_tests)
        
        if avg_default_chars > 0:
            reduction = (avg_default_chars - avg_basic_chars) / avg_default_chars * 100
            print(f"\n🎯 BASICVISITOR OPTIMIZATION IMPACT:")
            print(f"   Average chars (DEFAULT visitor): {avg_default_chars:,.0f}")
            print(f"   Average chars (BASIC visitor): {avg_basic_chars:,.0f}")
            print(f"   Character reduction: {reduction:+.1f}%")
            
            if reduction > 0:
                print(f"   ✅ OPTIMIZATION CONFIRMED: BasicTextVisitor reduces prompt size")
            else:
                print(f"   ⚠️  OPTIMIZATION ISSUE: BasicTextVisitor not reducing size as expected")
    
    # Strategy-specific analysis
    print(f"\n📋 STRATEGY BREAKDOWN:")
    for strategy in strategies:
        strategy_results = [r for r in results if r['strategy'] == strategy and r['success']]
        if strategy_results:
            avg_chars = sum(r['total_chars'] for r in strategy_results) / len(strategy_results)
            mop_coverage = sum(1 for r in strategy_results if r['has_mop_content'])
            print(f"   {strategy}: {len(strategy_results)}/{len([r for r in results if r['strategy'] == strategy])} tests passed")
            print(f"      Average chars: {avg_chars:,.0f}")
            print(f"      MOP content: {mop_coverage}/{len(strategy_results)} tests")
    
    # Template optimization validation
    vision_premium_results = [r for r in results if r['strategy'] == PromptStrategyType.VISION and r['success']]
    if vision_premium_results:
        print(f"\n🎯 TEMPLATE OPTIMIZATION (VISION_PREMIUM):")
        avg_chars = sum(r['total_chars'] for r in vision_premium_results) / len(vision_premium_results)
        print(f"   Tests passed: {len(vision_premium_results)}")
        print(f"   Average chars: {avg_chars:,.0f}")
        print(f"   All had MOP content: {all(r['has_mop_content'] for r in vision_premium_results)}")
    
    # Failed tests analysis
    failed_results = [r for r in results if not r['success']]
    if failed_results:
        print(f"\n❌ FAILED TESTS ANALYSIS:")
        for result in failed_results:
            print(f"   {result['strategy']} + {result['visitor']} + {result['context_mode']}: {result['error']}")
    
    print(f"\n✅ OPTIMIZATION VALIDATION COMPLETE!")
    print(f"   Results show impact of optimizations across all strategies and configurations")
    
    return results

def save_prompt(prompt: list[LLMMessage], out_dir, prefix):
    for message in prompt:
        text = ""
        image = ""
        for content in message.content:
            if isinstance(content, LLMTextContent):
                text += content.text
            elif isinstance(content, LLMImageContent):
                image += content.encoded_string

        if LLMRole.USER == message.role:
            suffix = "_user.txt"
        else: # LLMRole.SYSTEM == message.role:
            suffix = "_system.txt"

        with open(os.path.join(out_dir, prefix + suffix)  , "w") as file:
            file.write(text)

        if image:
            with open(os.path.join(out_dir, prefix + "_image.txt")  , "w") as file:
                file.write(image)


def simple_test():
    """Simple test with hardcoded configuration for quick testing."""
    print("=" * 60)
    print("🚀 SIMPLE PROMPT GENERATION TEST")
    print("=" * 60)
    
    # Hardcoded test configuration - modify as needed
    screenshots_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    apk = "cryptoapp.apk"
    prefix = "001"  # Use an existing state file
    
    # File paths
    app_folder = os.path.join(screenshots_folder, apk)
    reach_file = os.path.join(app_folder, apk + ".reach")
    gator_file = os.path.join(app_folder, apk + ".wtg")
    gesda_file = os.path.join(app_folder, apk + ".gesda")
    screenshot_path = os.path.join(app_folder, prefix + ".png")
    droidbot_state_file = os.path.join(app_folder, prefix + ".state")
    
    print(f"📂 Test files:")
    print(f"  • APK: {apk}")
    print(f"  • State: {prefix}")
    print(f"  • Screenshot: {screenshot_path}")
    
    # Create App and get package name
    app = App(app_path=os.path.join(app_folder, apk))
    package = app.package_name
    print(f"  • Package: {package}")
    
    # Parse static analysis data
    print("\n📊 Parsing static analysis data...")
    static_analysis_parser = StaticAnalysisParser()
    static_data = static_analysis_parser.parse(reach_file, gator_file, gesda_file, package)
    print(f"  ✅ Static data parsed")
    
    # Create configurations - SIMPLE HARDCODED CONFIG
    print("\n⚙️ Creating configuration...")
    llm_config = LLMConfig(
        llm_type=LLMType.OLLAMA,
        model=OllamaLLM.GEMMA,  # Using GEMMA model
        temperature=0.7
    )
    
    prompt_config = PromptConfig(
        strategy_type=PromptStrategyType.SINGLE,  # Simple single strategy
        parser_type=ScreenParserType.DROIDBOT,
        visitor_type=VisitorType.DEFAULT,
        template_name="single_compact",  # Using compact template
        context_mode=ContextMode.STATELESS
    )
    
    tool_config = RvSmartToolConfig(
        llm_config=llm_config,
        prompt_config=prompt_config,
        debug_mode=True
    )
    
    print(f"  • Strategy: {prompt_config.strategy_type}")
    print(f"  • Template: {prompt_config.template_name}")
    print(f"  • Visitor: {prompt_config.visitor_type}")
    print(f"  • Model: {llm_config.model}")
    
    # Create state from DroidBot file
    print("\n🔄 Processing state...")
    state = create_state_from_droidbot_state(
        droidbot_state_file, screenshot_path, package, static_data, DefaultTextVisitor
    )
    
    # Enrich state
    state = enrich_state(state, static_data, tool_config)
    print(f"  ✅ State enriched with {len(state)} keys")
    
    # Initialize framework
    print("\n🏗️ Initializing framework...")
    framework = RVAndroidPromptFramework.create(prompt_config)
    print(f"  ✅ Framework created")
    
    # Generate prompt
    print("\n📝 Generating prompt...")
    messages = framework.generate_prompt(state, {})
    
    print(f"\n✅ SUCCESS! Generated {len(messages)} messages")
    print("\n📄 Message details:")
    for i, message in enumerate(messages, 1):
        print(f"  Message {i}: Role={message.role}, Content items={len(message.content)}")
        for j, content in enumerate(message.content, 1):
            if hasattr(content, 'text'):
                print(f"    - Text content: {len(content.text)} chars")
            elif hasattr(content, 'url'):
                print(f"    - Image content: {content.url}")
    
    # Calculate total size
    total_chars = sum(
        len(content.text) for message in messages 
        for content in message.content 
        if hasattr(content, 'text')
    )
    print(f"\n📊 Total prompt size: {total_chars:,} characters")
    
    return messages


if __name__ == '__main__':
    setup_logging(True)
    
    try:
        # Run simple test
        messages = simple_test()
        
        print("\n" + "=" * 60)
        print("✅ Test completed successfully!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
