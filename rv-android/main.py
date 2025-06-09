# main.py
"""
RV-Android Main Entry Point - Tool Management and Experiment Delegation

### Architectural Evolution:
This main.py has been updated to focus on tool management while delegating 
experiment execution to the modern rv-experiment module. This maintains 
backward compatibility while enabling progressive migration to the new 
modular architecture.

### Key Responsibilities:
- Tool discovery, loading, and variant registration
- Command-line argument parsing and configuration management
- Tool specification parsing and validation
- Experiment delegation to rv-experiment module via bridge interface
- Fallback to legacy experiment execution if bridge is not available

### Bridge Pattern Implementation:
- Uses rv_experiment.bridge to delegate experiment execution
- Maintains compatibility with existing CLI interface
- Provides graceful fallback to legacy ExperimentController
- Enables progressive migration without breaking existing workflows

### Module Independence:
- Tool management remains in main.py (independent of experiment execution)
- Experiment orchestration delegated to rv-experiment module
- Clear separation of concerns between tool management and experiment coordination
- Maintains existing CLI interface for backward compatibility
"""

import argparse
import importlib
import json
import logging
import os
import sys
import time
from argparse import Namespace
from typing import Dict, Any

from rv_llm.config.configuration import Configuration
from rv_llm.config.configuration_manager import ConfigurationManager
from rv_android_core.constants import *
from rv_llm.llm.ollama_llm import OllamaLLM
from rv_tools.tools.registry import ToolRegistry
from rv_tools.registry.factory import ToolFactory
from rv_android_core.util import utils
from rv_android_core.util.logging.manager import LoggingManager

# Import experiment bridge for delegation to rv-experiment module
try:
    from rv_experiment.bridge import execute_experiment_via_bridge, execute_config_file_via_bridge
    BRIDGE_AVAILABLE = True
except ImportError as e:
    print(f"Warning: rv-experiment bridge not available: {e}")
    print("Falling back to legacy experiment execution")
    BRIDGE_AVAILABLE = False
    # Fallback imports for legacy execution
    from rv_experiment.experiment.experiment_controller import ExperimentController
    from rv_experiment.experiment.experiment_controller import execute as experiment_execute

"""
RV-Android Usage Guide
======================

RV-Android is a modular testing framework for Android applications with runtime verification
capabilities. This guide explains how to run experiments, configure the system, and use the 
various tool variants.

Basic Usage
----------
The main entry point for RV-Android is the `main.py` script, which can be used to run 
experiments with various testing tools and configurations:

   # Basic usage with a single tool
   python main.py --no_window -tools monkey -r 1 -t 60

   # Using multiple tools with 3 repetitions and different timeouts
   python main.py --no_window -tools monkey droidbot:dfs_greedy -r 3 -t 120 300 600 900

Command-Line Arguments
---------------------
-tools              List of testing tools to use in the experiment (default: monkey)
-t                  List of execution timeouts in seconds (default: [60])
-r                  Number of repetitions (default: 1)
-c                  Path to an execution memory file or configuration JSON
--no_window         Start emulator without GUI window
--debug             Enable debug logging
--list-tools        Display available tools and their variants
--skip_monitors     Skip monitor generation
--skip_instrument   Skip instrumentation
--skip_experiment   Skip experiment execution
--skip_static_analysis  Skip static analysis

Tool Specification Format
------------------------
Tools can be specified with variants and parameters using the following format:
tool_name[:variant1][:variant2][@param1=value1,param2=value2]

Examples:
- monkey                           Use the default Monkey tool
- droidbot:dfs_greedy              Use DroidBot with the dfs_greedy variant
- rvandroid:llama:single_action    Use RVAndroid with the llama and single_action variants
- rvandroid@model=gpt-4,strategy=composable  Use RVAndroid with custom parameters

Available Tool Variants
----------------------
1. DroidBot Variants:
  - dfs_naive, dfs_greedy, bfs_naive, bfs_greedy
  Example: python main.py -tools droidbot:dfs_greedy

2. RVAndroid Variants:
  - LLM Variants: llama, gpt4, claude
  - Strategy Variants: single_action, composable
  - Batch Strategy Variants: batch, llama_batch, gpt4_batch
  Example: python main.py -tools rvandroid:llama:single_action
  Example: python main.py -tools rvandroid:llama_batch
  Example: python main.py -tools rvandroid@model=gpt-4,strategy=composable

3. RVDroid Variants:
  - llm_enabled: Enables LLM-guided testing
  - detailed_ui: Uses detailed UI parser
  Example: python main.py -tools rvdroid:llm_enabled

4. Monkey Variants:
  - fixed_seed: Uses a fixed seed (42)
  - low_throttle: Uses lower throttle value (50)
  Example: python main.py -tools monkey:fixed_seed

5. FastBot Variants:
  - fast: Uses low throttle (50)
  - slow: Uses high throttle (500)
  Example: python main.py -tools fastbot:fast

Configuration Files
------------------
Instead of specifying all parameters via command line, you can use a JSON configuration file:

   python main.py -c experiment_config.json

Configuration file example:
{
   "repetitions": 3,
   "timeouts": [60, 120, 300],
   "no_window": true,
   "tools": [
       {
           "name": "monkey",
           "variant": "fixed_seed"
       },
       {
           "name": "droidbot",
           "variant": "dfs_greedy",
           "params": {
               "count": "1000"
           }
       },
       {
           "name": "rvandroid",
           "variants": ["llama", "batch"],
           "params": {
               "temperature": 0.2
           }
       }
   ]
}

Batch Action Strategy
--------------------
The batch action strategy is a new feature that generates sequences of related actions based on UI patterns,
rather than generating single actions. This reduces LLM overhead and improves testing efficiency.

The batch strategy automatically detects UI patterns like forms and lists, and generates appropriate
sequences of actions to interact with them. For example:
- For forms: Fill in all fields, then submit
- For lists: Scroll the list, then click on items
- For tabs: Navigate through tab elements systematically

To use the batch action strategy:
   python main.py --no_window -tools rvandroid:batch
   python main.py --no_window -tools rvandroid:llama_batch
   python main.py --no_window -tools rvandroid@use_batch_strategy=true

Continuing Experiments with Memory Files
---------------------------------------
To continue an interrupted experiment, use the memory file option:

   python main.py -c path/to/execution_memory.json

Environment Variables
-------------------
The following environment variables can be used to override command-line arguments:
RV_TOOLS              Comma-separated list of tools
RV_REPETITIONS        Number of repetitions
RV_TIMEOUTS           Space-separated list of timeouts
RV_MEMORY_FILE        Path to memory file
RV_SKIP_MONITORS      Skip monitor generation (true/false)
RV_SKIP_INSTRUMENT    Skip instrumentation (true/false)
RV_SKIP_STATIC_ANALYSIS Skip static analysis (true/false)
RV_SKIP_EXPERIMENT    Skip experiment execution (true/false)
RV_NO_WINDOW          Start emulator without window (true/false)
RV_DEBUG              Enable debug mode (true/false)
RV_HUMANOID_URL       URL for Humanoid service
RV_RVANDROID_URL      URL for RVAndroid service

Examples:
RV_TOOLS="rvandroid:llama_batch" RV_NO_WINDOW=true python main.py

Advanced Usage
-------------
1. Running with multiple LLM-guided tools:
  python main.py --no_window -tools rvandroid:llama rvandroid:gpt4 -r 2 -t 300 600

2. Custom configuration for RVAndroid:
  python main.py --no_window -tools rvandroid@model=llama3.2:3b,temperature=0.1,strategy=composable

3. Running only on pre-instrumented apps:
  python main.py --skip_monitors --skip_instrument -tools monkey -r 1 -t 120

4. Comparing multiple tool variants:
  python main.py -tools rvandroid:llama:single_action rvandroid:llama_batch -r 3 -t 300

5. Comparing batch vs. single action strategies:
  python main.py -tools rvandroid:batch rvandroid:single_action -r 3 -t 300
"""

program_description = '''
Executes RV-Android experiments using a modular workflow architecture.

Examples:    
$ python main.py --no_window -tools monkey droidbot:dfs_greedy -r 3 -t 120 300 600 900
$ python main.py --no_window -tools rvandroid:llama@strategy=single_action
$ python main.py --no_window -c PATH_TO_EXECUTION_FILE
$ python main.py --list-tools

Enhanced Mode Examples:
$ python main.py --enhanced -tools monkey -r 1 -t 60
$ python main.py --enhanced --orchestration-mode PARALLEL -tools droidbot -r 2 -t 120 300
'''


# main.py (continued)
def run_cli():
    """
    Run the command-line interface version of the RV-Android system.

    Parses command-line arguments, configures logging, sets up the environment,
    and executes the experiment based on provided configuration.
    """
    parser = create_argument_parser()
    args: Namespace = parser.parse_args()

    # Get log level from arguments or environment
    log_debug = utils.get_env_or_default(ENV_DEBUG, args.debug, bool)

    # Use LoggingManager to configure logging
    logging_manager = LoggingManager.get_instance()
    logger = logging_manager.get_logger("main", {"component": "CLI"})

    # Configure root logger through LoggingManager
    logging_manager.configure_output(
        console=True,
        file=True,
        console_level=logging.DEBUG if log_debug else logging.INFO,
        file_level=logging.DEBUG,
        console_format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Silence specific noisy loggers
    logging.getLogger("androguard").setLevel(logging.ERROR)

    logger.info("Starting RV-Android CLI")

    # Load tools
    load_tools()

    # Create configuration manager
    config_manager = ConfigurationManager()

    # Check if we're listing tools
    if args.list_tools:
        logger.info("Listing available tools and variants")
        list_available_tools()
        sys.exit(0)

    # Load configuration from file if specified
    if args.c:
        if os.path.exists(args.c):
            logger.info(f"Loading configuration from file: {args.c}")
            experiment_config = load_experiment_config(args.c)
            if not experiment_config:
                logger.error("Failed to load configuration file")
                sys.exit(1)

            # Execute experiment with loaded configuration via bridge
            if BRIDGE_AVAILABLE:
                success = execute_config_file_via_bridge(args.c)
                if success:
                    logger.info("Experiment completed successfully via rv-experiment bridge")
                    sys.exit(0)
                else:
                    logger.error("Experiment failed via rv-experiment bridge")
                    sys.exit(1)
            else:
                # Fallback to legacy execution
                execute_with_config(experiment_config)
                sys.exit(0)
        else:
            logger.error(f"Configuration file not found: {args.c}")
            sys.exit(1)

    # Load configuration from args
    config_manager.load_from_args(args)

    # Process tool specifications
    selected_tools = get_selected_tools(args)

    logger.info(f"Selected tools for experiment: {[tool.name for tool in selected_tools]}")

    # Store tool names in configuration
    config = Configuration.get_instance()
    config.set("tools", [tool.name for tool in selected_tools])

    # Ensure no_window is set correctly
    config.set("no_window", args.no_window)

    # Set enhanced experiment options if provided
    config.set("use_enhanced_controller", args.enhanced)
    if args.enhanced:
        config.set("orchestration_mode", args.orchestration_mode)
        logger.info(f"Enhanced controller enabled with orchestration mode: {args.orchestration_mode}")

    logger.info(f"Configuration no_window: {config.get_bool('no_window', False)}")

    # Print configuration
    config.print_experiment_summary()

    delay = utils.get_env_or_default(ENV_DELAY, 0, int)
    if delay > 0:
        logger.info(f"Sleeping for {delay} seconds before starting experiment")
        time.sleep(delay)

    logger.info("############# STARTING EXPERIMENT #############")
    start = time.time()

    # Log explicitly for the tools used
    logger.info(f"Executing experiment with tools: {[tool.name for tool in selected_tools]}")

    # Determine which controller to use
    use_enhanced = config.get_bool("use_enhanced_controller", False)

    # Execute experiment using rv-experiment bridge or fallback to legacy
    if BRIDGE_AVAILABLE:
        logger.info("Using rv-experiment bridge for modern experiment execution")
        success = execute_experiment_via_bridge(tools=selected_tools)
        if not success:
            logger.error("Experiment execution failed via bridge")
            sys.exit(1)
    else:
        logger.info("Using legacy experiment controller")
        # Execute experiment using the standard controller
        experiment_execute(tools=selected_tools)

    end = time.time()
    elapsed = end - start
    logger.info(f"It took {utils.to_readable_time(elapsed)} to complete")
    logger.info("############# ENDING EXPERIMENT #############")


def load_tools():
    """
    Load all available tools from tool directories.

    A tool must be defined in a subdirectory within
    the tools folder, in a python module named tool.py.
    This module must also declare a class named ToolSpec,
    which should inherit from AbstractTool.
    """
    # Set up logging
    logging_manager = LoggingManager.get_instance()
    logger = logging_manager.get_logger("main.load_tools", {"component": "ToolLoader"})

    # Get the tool registry
    registry = ToolRegistry.get_instance()
    # Clear any existing tools
    registry.clear()

    # Global available_tools for backward compatibility
    global available_tools
    available_tools = {}

    logger.info("Loading available tools")
    tools_dir = '.' + os.sep + "rvandroid" + os.sep + "tools"
    for subdir, dirs, files in os.walk(tools_dir):
        for filename in files:
            if filename == "tool.py":
                tool_path = os.path.join(subdir, filename)
                try:
                    tool_module = importlib.import_module(qualified_name(tool_path))
                    tool_class = getattr(tool_module, "ToolSpec")
                    tool_instance = tool_class()

                    # Add to registry
                    registry.register_tool(tool_instance)

                    # Also keep in available_tools for backward compatibility
                    available_tools[tool_instance.name] = tool_instance
                    logger.debug(f"Loaded tool: {tool_instance.name}")

                    # Register default variants if tool is configurable
                    register_default_variants(tool_instance)

                except Exception as e:
                    logger.error(f"Failed to load tool from {tool_path}: {e}")

    logger.info(f"Loaded {len(available_tools)} tools")


# TODO: atualizar variantes
def register_default_variants(tool):
    """
    Register default variants for a tool based on its type.

    Args:
        tool: Tool instance
    """
    registry = ToolRegistry.get_instance()
    logger = logging.getLogger("main.register_variants")

    if tool.name == "droidbot":
        # Register DroidBot policies as variants
        policies = ["dfs_naive", "dfs_greedy", "bfs_naive", "bfs_greedy"]
        for policy in policies:
            registry.register_variant(tool.name, policy, {"policy": policy})
            logger.debug(f"Registered variant '{policy}' for tool '{tool.name}'")

    elif tool.name == "rvandroid":
        # Register RVAndroid LLM variants
        registry.register_variant(tool.name, "llama", {
            "llm": {
                "model_type": OllamaLLM.NAME,
                "model_name": OllamaLLM.LLAMA
            },
            "strategy": {"type": "single_action"},
            "parser": {"type": "uiautomator_detailed"},
            "visitor": {"type": "enhanced"}
        })

        registry.register_variant(tool.name, "gpt4", {
            "llm": {
                "model_type": "openai",
                "model_name": "gpt-4"
            }
        })

        registry.register_variant(tool.name, "claude", {
            "llm": {
                "model_type": "anthropic",
                "model_name": "claude-3-opus-20240229"
            }
        })

        # Register strategy variants
        registry.register_variant(tool.name, "single_action", {
            "strategy": {"type": "single_action"},
            "use_batch_strategy": False
        })

        registry.register_variant(tool.name, "composable", {
            "strategy": {"type": "composable"},
            "use_batch_strategy": False
        })

        # Register batch strategy variants
        registry.register_variant(tool.name, "batch", {
            "use_batch_strategy": True
        })

        # Register combined variants
        registry.register_variant(tool.name, "llama_batch", {
            "llm": {
                "model_type": OllamaLLM.NAME,
                "model_name": OllamaLLM.LLAMA
            },
            "strategy": {"type": "single_action"},
            "parser": {"type": "uiautomator_detailed"},
            "visitor": {"type": "enhanced"},
            "use_batch_strategy": True
        })

        registry.register_variant(tool.name, "gpt4_batch", {
            "llm": {
                "model_type": "openai",
                "model_name": "gpt-4"
            },
            "use_batch_strategy": True
        })

        logger.debug(f"Registered LLM, strategy and batch variants for tool '{tool.name}'")

    elif tool.name == "rvdroid":
        # Register RVDroid variants
        registry.register_variant(tool.name, "llm_enabled", {
            "use_llm": True
        })

        # Register parser variants
        registry.register_variant(tool.name, "detailed_ui", {
            "parser": {"type": "uiautomator_detailed"}
        })

        logger.debug(f"Registered variants for tool '{tool.name}'")

    elif tool.name == "monkey":
        # Register Monkey variants
        registry.register_variant(tool.name, "fixed_seed", {
            "seed": 42
        })

        registry.register_variant(tool.name, "low_throttle", {
            "throttle": 50
        })

        logger.debug(f"Registered variants for tool '{tool.name}'")

    elif tool.name == "fastbot":
        # Register FastBot variants
        registry.register_variant(tool.name, "fast", {
            "throttle": 50
        })

        registry.register_variant(tool.name, "slow", {
            "throttle": 500
        })

        logger.debug(f"Registered variants for tool '{tool.name}'")


def list_available_tools():
    """
    List all available tools and their variants.
    """
    registry = ToolRegistry.get_instance()
    tools = registry.get_all_tools()

    print("\nAvailable Tools:")
    print("===============")

    for tool in tools:
        print(f"\n[{tool.name}] {tool.description}")

        # List variants if any
        if tool.name in registry.variants and len(registry.variants[tool.name]) > 1:
            print("\nVariants:")
            for variant in registry.variants[tool.name]:
                if variant != "default":
                    print(f"  - {variant}")

            print("\nUsage examples:")
            if tool.name == "droidbot":
                print(f"  python main.py -tools {tool.name}:dfs_greedy")
            elif tool.name == "rvandroid":
                print(f"  python main.py -tools {tool.name}:llama:single_action")
                print(f"  python main.py -tools {tool.name}@model=gpt-4,strategy=composable")

        print("\n" + "-" * 50)


def get_selected_tools(args: Namespace):
    """
    Get the tools selected by the user either from command line or environment.

    Args:
        args: Command-line arguments

    Returns:
        List of selected tool instances
    """
    logging_manager = LoggingManager.get_instance()
    logger = logging_manager.get_logger("main.get_selected_tools", {"component": "ToolSelector"})

    args_tools = utils.get_env_or_default(ENV_TOOLS, args.tools, list[str])
    selected_tools = []

    for tool_spec in args_tools:
        try:
            # Create tool from specification
            tool = ToolFactory.create_tool_from_spec(tool_spec)
            selected_tools.append(tool)
            logger.info(f"Selected tool from specification: {tool_spec}")
        except ValueError as e:
            logger.error(f"Error processing tool specification '{tool_spec}': {e}")
            exit(1)

    if len(selected_tools) == 0 and not args.skip_experiment:
        logger.error("No valid tools selected.")
        exit(1)

    logger.info(f"Selected tools: {[tool.name for tool in selected_tools]}")
    return selected_tools


def load_experiment_config(config_file: str) -> Dict[str, Any]:
    """
    Load experiment configuration from a JSON file.

    Args:
        config_file: Path to configuration file

    Returns:
        Configuration dictionary or None if loading failed
    """
    logger = logging.getLogger("main.load_config")

    try:
        with open(config_file, 'r') as f:
            config = json.load(f)

        return config
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing configuration file: {e}")
        return None
    except Exception as e:
        logger.error(f"Error loading configuration file: {e}")
        return None


def execute_with_config(config: Dict[str, Any]):
    """
    Execute experiment with the provided configuration.

    Args:
        config: Configuration dictionary
    """
    logger = logging.getLogger("main.execute_with_config")

    # Extract experiment parameters
    repetitions = config.get("repetitions", 1)
    timeouts = config.get("timeouts", [60])
    no_window = config.get("no_window", True)
    use_enhanced = config.get("use_enhanced_controller", False)
    orchestration_mode = config.get("orchestration_mode", "PARALLEL")

    # Process tools configurations
    tools_config = config.get("tools", [])
    selected_tools = []

    for tool_config in tools_config:
        tool_name = tool_config.get("name")
        if not tool_name:
            logger.error("Tool configuration missing 'name' field")
            continue

        # Process variants
        variants = []
        if "variant" in tool_config:
            variants.append(tool_config["variant"])
        if "variants" in tool_config:
            variants.extend(tool_config["variants"])

        params = tool_config.get("params", {})

        try:
            # Create tool with configuration
            tool = ToolFactory.create_configured_tool(tool_name, variants, params)
            selected_tools.append(tool)
        except ValueError as e:
            logger.error(f"Error creating tool '{tool_name}': {e}")

    if not selected_tools:
        logger.error("No valid tools found in configuration")
        return

    # Configure experiment
    config_obj = Configuration.get_instance()
    config_obj.set("repetitions", repetitions)
    config_obj.set("timeouts", timeouts)
    config_obj.set("no_window", no_window)
    config_obj.set("tools", [tool.name for tool in selected_tools])
    config_obj.set("use_enhanced_controller", use_enhanced)
    config_obj.set("orchestration_mode", orchestration_mode)

    # Execute experiment
    logger.info(f"Executing experiment with tools: {[tool.name for tool in selected_tools]}")

    # Execute experiment using rv-experiment bridge or fallback to legacy
    if BRIDGE_AVAILABLE:
        logger.info("Using rv-experiment bridge for modern experiment execution")
        success = execute_experiment_via_bridge(tools=selected_tools)
        if not success:
            logger.error("Experiment execution failed via bridge")
            return
    else:
        logger.info("Using legacy experiment controller")
        # Execute experiment using the standard controller
        experiment_execute(tools=selected_tools)


def create_argument_parser():
    """
    Create the argument parser for command-line options.

    Returns:
        Configured argument parser
    """
    # Start catching arguments
    parser = argparse.ArgumentParser(description=program_description, formatter_class=argparse.RawTextHelpFormatter)
    # list available tools
    parser.add_argument("--list-tools", help="list available tools", action="store_true")
    # List of test tools to be used in the experiment
    parser.add_argument('-tools', nargs='+', default=['monkey'],
                        help="List of test tools to be used in the experiment with optional variants. "
                             "Format: tool_name[:variant1][:variant2][@param1=value1,param2=value2]\n"
                             "Examples: droidbot:dfs_greedy, rvandroid:llama:single_action")
    # List of the execution timeouts in the experiment
    parser.add_argument('-t', nargs='+', default=[60],
                        help='List of the execution timeouts (in seconds) in the experiment. Default: [60]. EX: -t 120 300',
                        type=int)
    # Number of repetitions used in the experiment
    parser.add_argument('-r', default=1, help='Number of repetitions used in the experiment. Default: 1. EX: -r 3',
                        type=int, required=False)
    parser.add_argument('-c', default="", help='Path of the execution memory file or configuration JSON', type=str)
    parser.add_argument("--no_window", help="Starts emulator with '-no-window'", action="store_true")
    # Enable DEBUG mode.
    parser.add_argument('--debug', help='Run in DEBUG mode (default: false)', dest='debug', action='store_true')
    parser.add_argument("--skip_monitors", help="Skip monitors generation", action="store_true")
    parser.add_argument("--skip_instrument", help="Skip instrumentation", action="store_true")
    parser.add_argument("--skip_experiment", help="Skip experiment execution", action="store_true")
    parser.add_argument("--skip_static_analysis", help="Skip static analysis", action="store_true")

    # Add options for enhanced experiment controller
    parser.add_argument("--enhanced", help="Use the enhanced experiment controller", action="store_true")
    parser.add_argument("--orchestration-mode",
                        choices=["SEQUENTIAL", "PARALLEL", "ADAPTIVE", "PRIORITY_BASED"],
                        default="SEQUENTIAL",
                        help="Orchestration mode for the enhanced controller (default: SEQUENTIAL)")

    return parser


def qualified_name(p):
    """
    Convert a file path to a qualified module name.

    Args:
        p: File path

    Returns:
        Qualified module name
    """
    return p.replace(".py", "").replace("./", "").replace("/", ".")


def get_tools_obj(names: list[str], logger: logging.Logger):
    selected_tool_objects = []
    tool_name = ""
    try:
        for tool_name in names:
            tool_obj = ToolFactory.create_tool_from_spec(tool_name)
            selected_tool_objects.append(tool_obj)
    except ValueError:
        logger.error(f"Tool '{tool_name}' not found")

    return selected_tool_objects


# from main_tracker import track_modules
# @track_modules()
def run_local():
    """
    Runs a local experiment with predefined configuration settings.

    Configures logging, sets up experiment parameters, selects tools, and executes the experiment
    using the Configuration system. Specifically sets up an experiment with the 'ape' tool,
    configures various experiment settings, and runs the experiment.

    Logs are output to stdout with DEBUG level, and Androguard logs are set to ERROR level.
    Prints an experiment summary and a completion message after execution.
    """
    # Set up logging using LoggingManager
    logging_manager = LoggingManager.get_instance()
    logger = logging_manager.get_logger("main.run_local", {"component": "LocalExperiment"})

    # Configure logging
    logging_manager.configure_output(
        console=True,
        file=True,
        console_level=logging.DEBUG,
        file_level=logging.DEBUG,
        console_format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Silence specific noisy loggers
    logging.getLogger("androguard").setLevel(logging.ERROR)
    logging.getLogger("matplotlib").setLevel(logging.ERROR)
    logging.getLogger("PIL").setLevel(logging.ERROR)

    logger.info("Starting local experiment with predefined configuration")

    # Load tools
    load_tools()

    # Get configuration instance
    config = Configuration.get_instance()

    # Set configuration values
    config.set("repetitions", 2)
    config.set("timeouts", [60, 120])
    config.set("generate_monitors", True)
    config.set("instrument", True)
    config.set("static_analysis", True)
    config.set("skip_experiment", False)
    config.set("no_window", True)
    config.set("memory_file", "")

    # ape = OK
    # ares
    # droidbot
    #   - droidbot:dfs_naive
    #   - droidbot:dfs_greedy
    #   - droidbot:bfs_naive
    #   - droidbot:bfs_greedy
    # droidmate = OK
    # fastbot = OK
    # humanoid
    # monkey = OK
    # qtesting (DOCKER)
    # rvandroid
    # rvdroid

    # Get selected tools as objects
    selected_tool_objects = get_tools_obj(["ape", "monkey"], logger)

    # Log explicitly for the selected tools
    logger.info(f"Selected tools for local experiment: {[tool.name for tool in selected_tool_objects]}")

    # Store tool names in configuration
    config.set("tools", [tool.name for tool in selected_tool_objects])

    # Print configuration
    config.print_experiment_summary()

    # Execute experiment with the selected tool objects
    logger.info(f"Executing experiment with tools: {[tool.name for tool in selected_tool_objects]}")

    # Execute experiment using rv-experiment bridge or fallback to legacy
    if BRIDGE_AVAILABLE:
        logger.info("Using rv-experiment bridge for modern local experiment execution")
        success = execute_experiment_via_bridge(tools=selected_tool_objects)
        if not success:
            logger.error("Local experiment execution failed via bridge")
            return
    else:
        logger.info("Instantiating legacy experiment controller")
        # Create and execute experiment with standard controller
        controller = ExperimentController()
        controller.execute(
            repetitions=config.get_int("repetitions", 1),
            timeouts=config.get_list("timeouts", [60]),
            tools=selected_tool_objects,
            memory_file=config.get_str("memory_file", ""),
            generate_monitors=config.get_bool("generate_monitors", True),
            instrument=config.get_bool("instrument", True),
            static_analysis=config.get_bool("static_analysis", True),
            skip_experiment=config.get_bool("skip_experiment", False),
            no_window=config.get_bool("no_window", True)
        )

    logger.info("Local experiment completed successfully")


if __name__ == '__main__':
    # Register models to resolve circular import issue
    from rv_llm.llm import register_models

    register_models()

    load_tools()

    # Use CLI by default
    # run_cli()

    # Uncomment for local testing:
    run_local()
