# main.py
import argparse
import importlib
import logging
import os
import sys
import time
from argparse import Namespace

from rvandroid.config.configuration import Configuration
from rvandroid.config.configuration_manager import ConfigurationManager
from rvandroid.constants import *
from rvandroid.experiment.experiment_controller import ExperimentController
from rvandroid.experiment.experiment_controller import execute as experiment_execute
from rvandroid.tools.registry import ToolRegistry
from rvandroid.tools.tool_spec import AbstractTool
from rvandroid.util import utils
from rvandroid.util.logging.manager import LoggingManager

available_tools: dict[str, AbstractTool] = {}

program_description = '''
Executes RV-Android experiments using a modular workflow architecture.

Examples:    
$ python main.py --no_window -tools monkey droidbot -r 3 -t 120 300 600 900
$ python main.py --no_window -c PATH_TO_EXECUTION_FILE
$ python main.py --list-tools
'''


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

    if args.list_tools:
        logger.info("Listing available tools")
        for key in available_tools:
            print(f" [{key}] {available_tools[key].description}\n")
        sys.exit(0)

    # Create configuration manager
    config_manager = ConfigurationManager()

    # Load configuration from args
    config_manager.load_from_args(args)

    # Get the selected tools
    selected_tools = get_selected_tools(args)

    logger.info(f"Selected tools for experiment: {[tool.name for tool in selected_tools]}")

    # Store tool names in configuration
    config = Configuration.get_instance()
    config.set("tools", [tool.name for tool in selected_tools])

    # Ensure no_window is set correctly
    config.set("no_window", args.no_window)

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

    # Execute the experiment with the selected tool objects
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
                except Exception as e:
                    logger.error(f"Failed to load tool from {tool_path}: {e}")

    logger.info(f"Loaded {len(available_tools)} tools")


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
    selected_tools = __get_tools(args_tools)

    if len(selected_tools) == 0 and not args.skip_experiment:
        logger.error("No valid tools selected.")
        exit(1)

    logger.info(f"Selected tools: {[tool.name for tool in selected_tools]}")
    return selected_tools


def __get_tools(names: list[str]) -> list[AbstractTool]:
    """
    Get tools by name from the registry.

    Args:
        names: List of tool names

    Returns:
        List of tool instances
    """
    registry = ToolRegistry.get_instance()
    return registry.get_tools(names)


def qualified_name(p):
    """
    Convert a file path to a qualified module name.

    Args:
        p: File path

    Returns:
        Qualified module name
    """
    return p.replace(".py", "").replace("./", "").replace("/", ".")


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
                        help="List of test tools to be used in the experiment. Default: [monkey]. EX: -tools monkey droidbot")
    # List of the execution timeouts in the experiment
    parser.add_argument('-t', nargs='+', default=[60],
                        help='List of the execution timeouts (in seconds) in the experiment. Default: [60]. EX: -t 120 300',
                        type=int)
    # Number of repetitions used in the experiment
    parser.add_argument('-r', default=1, help='Number of repetitions used in the experiment. Default: 1. EX: -r 3',
                        type=int, required=False)
    parser.add_argument('-c', default="", help='Path of the execution memory file (to continue an execution)', type=str)
    parser.add_argument("--no_window", help="Starts emulator with '-no-window'", action="store_true")
    # Enable DEBUG mode.
    parser.add_argument('--debug', help='Run in DEBUG mode (default: false)', dest='debug', action='store_true')
    parser.add_argument("--skip_monitors", help="Skip monitors generation", action="store_true")
    parser.add_argument("--skip_instrument", help="Skip instrumentation", action="store_true")
    parser.add_argument("--skip_experiment", help="Skip experiment execution", action="store_true")
    parser.add_argument("--skip_static_analysis", help="Skip static analysis", action="store_true")

    return parser


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

    # Get configuration instance
    config = Configuration.get_instance()

    # Set configuration values
    config.set("repetitions", 1)
    config.set("timeouts", [60])
    config.set("generate_monitors", True)
    config.set("instrument", True)
    config.set("static_analysis", True)
    config.set("skip_experiment", False)
    config.set("no_window", True)
    config.set("memory_file", "")

    # Get selected tools as objects
    selected_tool_objects = __get_tools(["ape"])

    # Log explicitly for the selected tools
    logger.info(f"Selected tools for local experiment: {[tool.name for tool in selected_tool_objects]}")

    # Store tool names in configuration
    config.set("tools", [tool.name for tool in selected_tool_objects])

    # Print configuration
    config.print_experiment_summary()

    # Execute experiment with the selected tool objects
    logger.info(f"Executing experiment with tools: {[tool.name for tool in selected_tool_objects]}")

    # Create and execute experiment directly using the controller
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
    load_tools()

    # Uncomment the desired execution mode:
    # run_cli()
    run_local()
