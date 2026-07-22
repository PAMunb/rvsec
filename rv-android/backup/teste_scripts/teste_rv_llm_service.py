import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "modules" / "rv-android-core" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-llm" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rvandroid-tool" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-screen-parser" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-static-analysis" / "src"))

# Import necessary modules after path setup
from rv_android_core.util.performance.performance_monitor import PerformanceMonitor
from rv_screen_parser.parser.screen.parser_factory import ParserFactory
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription
from rv_llm.llm.constants import StateEntry
from rv_android_core.domain.app import App
from rv_screen_parser.constants import ScreenParserType
from rv_llm.config.llm_config import LLMConfig
from rv_llm.llm.constants import LLMType, PromptStrategyType, ContextMode
from rv_screen_parser.constants import VisitorType
from rv_llm.llm.ollama_llm import OllamaLLM
from rv_android_core.domain.static import StaticAnalysisData
from rvandroid_tool.llm.service.memory_manager import MemoryManager
from rvandroid_tool.llm.service.transition_manager import TransitionManager
from rvandroid_tool.llm.service.action_service import LLMActionService
import json
import logging
import os
import sys
from typing import Dict, Any, Type

from rv_llm.config import PromptConfig
from rv_screen_parser.parser.screen.visitor.abstract_visitor import AbstractScreenVisitor
from rvandroid_tool.config.tool_config import RvAndroidToolConfig


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

    for noisy_logger in ["rvandroid_core.domain.window", "rvandroid_core.domain.widget",
                         "rv_static_analysis.parser.static", "rvandroid_core.domain.classes"
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


def create_state_from_droidbot_state(droidbot_state_file: str, screenshot_path: str, package: str,
                                     static_data: StaticAnalysisData, visitor: Type[AbstractScreenVisitor]):
    screen_info = read_droidbot_state(droidbot_state_file)
    parser = ParserFactory.create(ScreenParserType.DROIDBOT, visitor)
    screen_description: ScreenDescription = parser.parse_screen(screen_info, static_data)
    state = {
        StateEntry.PACKAGE_NAME: package,
        StateEntry.ACTIVITY: screen_description.activity,
        StateEntry.VIEW_TREE: screen_info[StateEntry.VIEW_TREE],
        StateEntry.SCREENSHOT_PATH: screenshot_path,
        StateEntry.STRUCTURED_SCREEN: screen_description
    }
    return state


def tmp_strategy_with_context_modes(strategy: str, state: Dict[str, Any], static_data: StaticAnalysisData,
                                     visitors: list = None):
    """
    Test a specific strategy with both STATELESS and RICH context modes.
    Also tests different visitors if provided.
    """
    print(f"\n{'=' * 80}")
    print(f"🧪 TESTING STRATEGY: {strategy}")
    print(f"{'=' * 80}")

    if visitors is None:
        visitors = [VisitorType.BASIC, VisitorType.DEFAULT]

    results = []

    for visitor in visitors:
        for context_mode in [ContextMode.STATELESS, ContextMode.RICH]:
            tmp_name = f"{strategy}+{visitor}+{context_mode}"
            print(f"\n🔍 TEST: {tmp_name}")
            print("-" * 60)

            try:
                # Create LLM config (sempre GEMMA 4b)
                llm_config = LLMConfig(
                    llm_type=LLMType.OLLAMA,
                    model=OllamaLLM.GEMMA,  # GEMMA 4b sempre
                    temperature=0.3,
                    max_tokens=800,
                    vision=True
                )

                # Create prompt config
                prompt_config = PromptConfig(
                    strategy_type=strategy,
                    parser_type=ScreenParserType.DROIDBOT,
                    visitor_type=visitor,
                    context_mode=context_mode,
                    context_window_size=5,
                    context_compression=True,
                    include_coverage_timeline=True
                )

                # Create tool config
                tool_config = RvAndroidToolConfig(
                    llm_config=llm_config,
                    prompt_config=prompt_config,
                    debug_mode=True
                )

                print(f"📋 Strategy: {strategy}")
                print(f"📋 Visitor: {visitor} ({'Optimized' if visitor == VisitorType.BASIC else 'Standard'})")
                print(f"📋 Context Mode: {context_mode}")
                print(f"📋 Model: {llm_config.model}")

                # Create service
                service = LLMActionService(
                    static_data=static_data,
                    tool_config=tool_config
                )

                # Add rich context data if needed
                tmp_state = state.copy()
                if context_mode == ContextMode.RICH:
                    tmp_state[StateEntry.RECENT_ITERATIONS] = create_mock_iterations()
                    tmp_state[StateEntry.COVERAGE_METRICS] = {
                        'method_coverage': 45.2,
                        'activity_coverage': 78.0,
                        'mop_method_coverage': 28.7,
                        'unique_errors': 1
                    }
                    tmp_state[StateEntry.MOP_RECENT_ERRORS] = [
                        {
                            'spec': 'CryptoSpec',
                            'class_full_name': 'com.example.crypto.CipherManager',
                            'method': 'createCipher',
                            'message': 'Weak cipher algorithm used',
                            'detected_at': '2025-08-25T11:15:00'
                        }
                    ]

                # Process state and generate actions
                print(f"🚀 Processing state...")
                actions = service.process_state(tmp_state)

                result = {
                    'strategy': strategy,
                    'visitor': visitor,
                    'context_mode': context_mode,
                    'success': True,
                    'actions_count': len(actions),
                    'actions': actions,
                    'error': None
                }

                print(f"✅ SUCCESS: Generated {len(actions)} actions")

                # Show sample actions
                for i, action in enumerate(actions[:3]):  # Show first 3 actions
                    print(f"   Action {i + 1}: {action.get('action_type', 'N/A')} -> {action.get('action_id', 'N/A')}")

                if len(actions) > 3:
                    print(f"   ... and {len(actions) - 3} more actions")

                results.append(result)

            except Exception as e:
                result = {
                    'strategy': strategy,
                    'visitor': visitor,
                    'context_mode': context_mode,
                    'success': False,
                    'actions_count': 0,
                    'actions': [],
                    'error': str(e)
                }

                print(f"❌ FAILED: {e}")
                results.append(result)

    return results


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
                'method_coverage': 18.3,
                'mop_method_coverage': 9.1,
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
                'method_coverage': 32.4,
                'mop_method_coverage': 15.8,
                'unique_errors': 0
            },
            'mop_errors': []
        },
        {
            'activity': 'CryptoActivity',
            'actions_generated': [
                {'explanation': 'opened encryption settings [DM]'},
                {'explanation': 'modified cipher configuration [DM]'}
            ],
            'coverage_metrics': {
                'method_coverage': 45.2,
                'mop_method_coverage': 28.7,
                'unique_errors': 1
            },
            'mop_errors': [
                {'spec': 'CryptoSpec', 'method': 'createCipher', 'message': 'Weak cipher algorithm used'}
            ]
        }
    ]


def analyze_performance_metrics():
    """Analyze and display PerformanceMonitor metrics after all tests."""
    print(f"\n{'=' * 80}")
    print("📊 PERFORMANCE METRICS ANALYSIS")
    print(f"{'=' * 80}")

    monitor = PerformanceMonitor.get_instance()

    # Get all recorded metrics
    all_metrics = monitor.metrics

    if not all_metrics:
        print("❌ No metrics found in PerformanceMonitor")
        return

    # Group metrics by category
    prompt_metrics = {}
    llm_metrics = {}
    action_metrics = {}
    error_metrics = {}

    for metric in all_metrics:
        name = metric.name
        if name.startswith('prompt_optimization'):
            prompt_metrics[name] = prompt_metrics.get(name, [])
            prompt_metrics[name].append(metric)
        elif name.startswith('llm_'):
            llm_metrics[name] = llm_metrics.get(name, [])
            llm_metrics[name].append(metric)
        elif name.startswith('action_distribution'):
            action_metrics[name] = action_metrics.get(name, [])
            action_metrics[name].append(metric)
        elif any(error_type in name for error_type in ['parsing_errors', 'generation_failures', 'success_rate']):
            error_metrics[name] = error_metrics.get(name, [])
            error_metrics[name].append(metric)

    # Analyze prompt optimization metrics
    if prompt_metrics:
        print(f"\n🎯 PROMPT OPTIMIZATION METRICS:")
        for metric_name, metric_list in prompt_metrics.items():
            if metric_list:
                values = [m.value for m in metric_list]
                avg_value = sum(values) / len(values)
                print(f"   {metric_name}: {avg_value:.2f} avg ({len(values)} samples)")

    # Analyze LLM metrics
    if llm_metrics:
        print(f"\n🤖 LLM PERFORMANCE METRICS:")
        for metric_name, metric_list in llm_metrics.items():
            if metric_list:
                values = [m.value for m in metric_list]
                avg_value = sum(values) / len(values)
                if 'tokens' in metric_name:
                    print(f"   {metric_name}: {avg_value:.0f} avg tokens ({len(values)} samples)")
                elif 'time' in metric_name:
                    print(f"   {metric_name}: {avg_value:.2f}s avg ({len(values)} samples)")

    # Analyze error metrics
    if error_metrics:
        print(f"\n❌ ERROR ANALYSIS METRICS:")
        for metric_name, metric_list in error_metrics.items():
            if metric_list:
                values = [m.value for m in metric_list]
                avg_value = sum(values) / len(values)
                if 'success_rate' in metric_name:
                    print(f"   {metric_name}: {avg_value:.1%} avg ({len(values)} samples)")
                else:
                    print(f"   {metric_name}: {avg_value:.1f} avg ({len(values)} samples)")

    # Analyze action distribution
    if action_metrics:
        print(f"\n🎬 ACTION DISTRIBUTION METRICS:")
        for metric_name, metric_list in action_metrics.items():
            if metric_list:
                values = [m.value for m in metric_list]
                total_actions = sum(values)
                print(f"   {metric_name}: {total_actions} total actions ({len(values)} samples)")

    print(f"\n📈 TOTAL METRICS CAPTURED: {len(all_metrics)}")

    return all_metrics


def tmp_run(static_data, state):
    llm_config = LLMConfig(
        llm_type=LLMType.OLLAMA,
        model=OllamaLLM.GEMMA,
        temperature=0.3,
        max_tokens=800,
        vision=True
    )
    prompt_config = PromptConfig(
        strategy_type=PromptStrategyType.VISION,
        parser_type=ScreenParserType.DROIDBOT,
        visitor_type=VisitorType.BASIC,
        context_mode=ContextMode.STATELESS,
        context_window_size=5,
        context_compression=True,
        include_coverage_timeline=True
    )
    tool_config = RvAndroidToolConfig(
        llm_config=llm_config,
        prompt_config=prompt_config
    )

    service = LLMActionService(
        static_data=static_data,
        tool_config=tool_config
    )

    actions = service.process_state(state)
    print(actions)


if __name__ == '__main__':
    # Configuração de logging
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    for noisy_logger in ["androguard", "matplotlib", "PIL", "requests", "urllib3"]:
        logging.getLogger(noisy_logger).setLevel(logging.ERROR)

    # Caminhos para dados do app
    screenshots_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    apk = "cryptoapp.apk"
    prefix = "004"  # Change to test different states: "001", "009", "015"
    app_folder = os.path.join(screenshots_folder, apk)
    droidbot_state_file = os.path.join(app_folder, f"{prefix}.state")
    screenshot_file = os.path.join(app_folder, f"{prefix}.png")

    print(f"🎯 COMPREHENSIVE LLM SERVICE TEST")
    print(f"{'=' * 80}")
    print(f"📋 Configuration:")
    print(f"  • APK: {apk}")
    print(f"  • State: {prefix}")
    print(f"  • Screenshot: {screenshot_file}")
    print(f"  • DroidBot State: {droidbot_state_file}")

    # Load app and static analysis
    app = App(os.path.join(app_folder, apk))
    package = app.package_name
    print(f"  • Package: {package}")

    # Load static analysis data
    from rv_static_analysis.parser.static.static_analysis_parser import StaticAnalysisParser

    static_analysis_parser = StaticAnalysisParser()
    static_data = static_analysis_parser.read_static_analysis_files(app_folder, apk, package)
    print(f"  • Static data loaded successfully")


    # Load DroidBot state
    state = read_droidbot_state(droidbot_state_file)
    state[StateEntry.SCREENSHOT_PATH] = screenshot_file  # Add screenshot path
    print(f"  • DroidBot state loaded successfully")

    tmp_run(static_data, state)
    exit(1)

    # Clear PerformanceMonitor for fresh metrics
    monitor = PerformanceMonitor.get_instance()
    print(f"  • PerformanceMonitor initialized")

    print(f"\n🚀 RUNNING COMPREHENSIVE TESTS")
    print(f"Testing VISION and MOP_VISION strategies with BASIC/DEFAULT visitors")
    print(f"All tests use GEMMA 4b model with vision capabilities")

    all_results = []

    # Test 1: VISION Strategy
    vision_results = tmp_strategy_with_context_modes(
        PromptStrategyType.VISION,
        state,
        static_data,
        visitors=[VisitorType.BASIC, VisitorType.DEFAULT]  # Test both visitors
    )
    all_results.extend(vision_results)

    # Test 2: MOP_VISION Strategy 
    mop_vision_results = tmp_strategy_with_context_modes(
        PromptStrategyType.MOP_VISION,
        state,
        static_data,
        visitors=[VisitorType.BASIC, VisitorType.DEFAULT]  # Test both visitors
    )
    all_results.extend(mop_vision_results)

    # Analyze all results
    print(f"\n{'=' * 80}")
    print("📊 COMPREHENSIVE TEST RESULTS SUMMARY")
    print(f"{'=' * 80}")

    successful_tests = [r for r in all_results if r['success']]
    failed_tests = [r for r in all_results if not r['success']]

    print(f"✅ Successful tests: {len(successful_tests)}/{len(all_results)}")
    print(f"❌ Failed tests: {len(failed_tests)}")

    if successful_tests:
        print(f"\n📈 SUCCESS BREAKDOWN:")
        for result in successful_tests:
            print(
                f"   ✅ {result['strategy']} + {result['visitor']} + {result['context_mode']}: {result['actions_count']} actions")

        # Analyze optimization impact
        basic_results = [r for r in successful_tests if r['visitor'] == VisitorType.BASIC]
        default_results = [r for r in successful_tests if r['visitor'] == VisitorType.DEFAULT]

        if basic_results and default_results:
            basic_avg = sum(r['actions_count'] for r in basic_results) / len(basic_results)
            default_avg = sum(r['actions_count'] for r in default_results) / len(default_results)

            print(f"\n🎯 VISITOR COMPARISON:")
            print(f"   BASIC (Optimized) average: {basic_avg:.1f} actions")
            print(f"   DEFAULT (Standard) average: {default_avg:.1f} actions")

    if failed_tests:
        print(f"\n❌ FAILED TESTS:")
        for result in failed_tests:
            print(f"   ❌ {result['strategy']} + {result['visitor']} + {result['context_mode']}: {result['error']}")

    # Analyze PerformanceMonitor metrics
    analyze_performance_metrics()

    print(f"\n🎉 COMPREHENSIVE LLM SERVICE TEST COMPLETED!")
    print(f"📊 All metrics captured in PerformanceMonitor for analysis")
    print(f"💡 TIP: Check optimization impact in metrics above")
