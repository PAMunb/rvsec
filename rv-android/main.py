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
from rvandroid.experiment import experiment_03
from rvandroid.tools.registry import ToolRegistry
from rvandroid.tools.tool_spec import AbstractTool
from rvandroid.util import utils

available_tools: dict[str, AbstractTool] = {}

program_description = '''
Executes the 'Experiment 03' ... 

Examples:    
$ python main.py --no_window -tools monkey droidbot -r 3 -t 120 300 600 900
$ python main.py --no_window -c PATH_TO_EXECUTION_FILE
$ python main.py --list-tools

'''


def run_cli():
    parser = create_argument_parser()
    args: Namespace = parser.parse_args()

    # Logging configuration
    # log_debug = utils.get_env_or_default(ENV_DEBUG, args.debug, bool)
    # logging.basicConfig(stream=sys.stdout, level=logging.DEBUG if log_debug else logging.INFO)
    # logging.getLogger("androguard").setLevel(logging.ERROR)
    # Get log level from arguments or environment
    log_debug = utils.get_env_or_default(ENV_DEBUG, args.debug, bool)

    # Use LoggingManager to configure logging
    from rvandroid.util.logging_manager import LoggingManager
    logging_manager = LoggingManager.get_instance()

    # Configure root logger through standard logging
    # This will be detected by LoggingManager and it won't add duplicate handlers
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.DEBUG if log_debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Silence specific noisy loggers
    logging.getLogger("androguard").setLevel(logging.ERROR)

    if args.list_tools:
        logging.info(" [Listing available tools] \n")
        for key in available_tools:
            print(" [{0}] {1} \n".format(key, available_tools[key].description))
        sys.exit(0)

    # Create configuration manager
    config_manager = ConfigurationManager()

    # Load configuration from args
    config_manager.load_from_args(args)

    # Get the selected tools
    selected_tools = get_selected_tools(args)

    # Store tool names in configuration
    config = Configuration.get_instance()
    config.set("tools", [tool.name for tool in selected_tools])

    # Print configuration
    config.print_experiment_summary()

    delay = utils.get_env_or_default(ENV_DELAY, 0, int)
    if delay > 0:
        logging.info(f"Sleeping for {delay} seconds ...")
        time.sleep(delay)

    logging.info("############# STARTING EXPERIMENT #############")
    start = time.time()

    # Execute the experiment with the selected tool objects
    experiment_03.execute(tools=selected_tools)

    end = time.time()
    elapsed = end - start
    logging.info("It took {0} to complete".format(utils.to_readable_time(elapsed)))
    logging.info("############# ENDING EXPERIMENT #############")


def load_tools():
    """Load all available tools.

     A tool must be defined in a subdirectory within
     the tools folder, in a python module named tool.py.
     This module must also declare a class named ToolSpec,
     which should inherit from AbstractTool.
    """
    # Get the tool registry
    registry = ToolRegistry.get_instance()
    # Clear any existing tools
    registry.clear()

    # Global available_tools for backward compatibility
    global available_tools
    available_tools = {}

    for subdir, dirs, files in os.walk('.' + os.sep + "rvandroid" + os.sep + "tools"):
        for filename in files:
            if filename == "tool.py":
                tool_module = importlib.import_module(qualified_name(subdir + os.sep + filename))
                tool_class = getattr(tool_module, "ToolSpec")
                tool_instance = tool_class()

                # Add to registry
                registry.register_tool(tool_instance)

                # Also keep in available_tools for backward compatibility
                available_tools[tool_instance.name] = tool_instance


def get_selected_tools(args: Namespace):
    args_tools = utils.get_env_or_default(ENV_TOOLS, args.tools, list[str])
    selected_tools = __get_tools(args_tools)
    if len(selected_tools) == 0 and not args.skip_experiment:
        print("No valid tools selected.")
        exit(1)
    return selected_tools


def __get_tools(names: list[str]) -> list[AbstractTool]:
    """Get tools by name from the registry."""
    registry = ToolRegistry.get_instance()
    return registry.get_tools(names)


def qualified_name(p):
    return p.replace(".py", "").replace("./", "").replace("/", ".")


def create_argument_parser():
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
    # Get log level from arguments or environment
    log_debug = True

    # Use LoggingManager to configure logging
    from rvandroid.util.logging_manager import LoggingManager
    logging_manager = LoggingManager.get_instance()

    # Configure root logger through standard logging
    # This will be detected by LoggingManager and it won't add duplicate handlers
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.DEBUG if log_debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Silence specific noisy loggers
    logging.getLogger("androguard").setLevel(logging.ERROR)

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

    # Get selected tools first as objects
    selected_tool_objects = __get_tools(["ape"])

    # Store tool names in configuration
    config.set("tools", [tool.name for tool in selected_tool_objects])

    # Print configuration
    config.print_experiment_summary()

    # Execute experiment with the selected tool objects
    experiment_03.execute(tools=selected_tool_objects)

    print("FIM DE FESTA!!!")


if __name__ == '__main__':
    load_tools()

    # run_cli()
    run_local()
