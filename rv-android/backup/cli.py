"""
Command-line interface for RV-Android experiments.

This module provides command-line entry points for executing RV-Android experiments
using both the standard and enhanced experiment controllers.
"""
import argparse
import logging
import sys
from typing import List

from rvandroid.config.configuration import Configuration
from rvandroid.experiment.enhanced_experiment_controller import execute_enhanced
from rvandroid.experiment.experiment_controller import execute
from rvandroid.experiment.orchestration.interfaces import OrchestrationMode
from rvandroid.tools.registry import ToolRegistry
from rvandroid.util.logging.manager import LoggingManager


def parse_args():
    """
    Parse command-line arguments for experiment execution.
    
    Returns:
        Parsed command-line arguments
    """
    parser = argparse.ArgumentParser(description='Run RV-Android experiments')
    parser.add_argument('--enhanced', action='store_true', help='Use enhanced experiment controller')
    parser.add_argument('--repetitions', type=int, default=1, help='Number of repetitions')
    parser.add_argument('--timeouts', type=int, nargs='+', default=[60], help='Timeouts in seconds')
    parser.add_argument('--tools', type=str, nargs='+', default=['monkey'], help='Tools to use')
    parser.add_argument('--memory-file', type=str, default='', help='Memory file for resumption')
    parser.add_argument('--no-generate-monitors', action='store_true', help='Skip monitor generation')
    parser.add_argument('--no-instrument', action='store_true', help='Skip instrumentation')
    parser.add_argument('--no-static-analysis', action='store_true', help='Skip static analysis')
    parser.add_argument('--skip-experiment', action='store_true', help='Skip experiment execution')
    parser.add_argument('--no-window', action='store_true', help='Run emulator in headless mode')
    parser.add_argument('--orchestration-mode', type=str, default='sequential',
                      choices=['sequential', 'parallel', 'adaptive', 'priority_based'],
                      help='Orchestration mode when using enhanced controller (default: sequential)')
    parser.add_argument('--log-level', type=str, default='info',
                      choices=['debug', 'info', 'warning', 'error', 'critical'],
                      help='Logging level')
    
    return parser.parse_args()


def setup_logging(level_name):
    """
    Set up logging with the specified level.
    
    Args:
        level_name: Name of the logging level
    """
    level_map = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL
    }
    
    level = level_map.get(level_name.lower(), logging.INFO)
    
    # Get the logging manager and configure root logger
    logging_manager = LoggingManager.get_instance()
    logging_manager.configure_root_logger(level)


def get_orchestration_mode(mode_name):
    """
    Get the orchestration mode enum value from its name.
    
    Args:
        mode_name: Name of the orchestration mode
    
    Returns:
        OrchestrationMode enum value
    """
    mode_map = {
        'sequential': OrchestrationMode.SEQUENTIAL,
        'parallel': OrchestrationMode.PARALLEL,
        'adaptive': OrchestrationMode.ADAPTIVE,
        'priority': OrchestrationMode.PRIORITY
    }
    
    return mode_map.get(mode_name.lower(), OrchestrationMode.PARALLEL)


def main():
    """Main entry point for the command-line interface."""
    # Parse command-line arguments
    args = parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    
    # Get logger for this module
    logging_manager = LoggingManager.get_instance()
    logger = logging_manager.get_logger('experiment_workflow.cli', {'function': 'main'})
    
    logger.info("Starting RV-Android experiment from CLI")
    
    # Configure experiment
    config = Configuration.get_instance()
    config.set("repetitions", args.repetitions)
    config.set("timeouts", args.timeouts)
    config.set("tools", args.tools)
    config.set("memory_file", args.memory_file)
    config.set("generate_monitors", not args.no_generate_monitors)
    config.set("instrument", not args.no_instrument)
    config.set("static_analysis", not args.no_static_analysis)
    config.set("skip_experiment", args.skip_experiment)
    config.set("no_window", args.no_window)
    
    # Handle orchestration mode for enhanced controller
    if args.enhanced:
        orchestration_mode = get_orchestration_mode(args.orchestration_mode)
        config.set("orchestration_mode", orchestration_mode.name)
    
    # Get tools from registry
    registry = ToolRegistry.get_instance()
    tools = registry.get_tools(args.tools)
    
    logger.info(f"Using {'enhanced' if args.enhanced else 'standard'} experiment controller")
    
    # Execute experiment
    if args.enhanced:
        result = execute_enhanced(tools)
    else:
        result = execute(tools)
    
    logger.info(f"Experiment completed with result: {result}")
    return 0


if __name__ == "__main__":
    sys.exit(main())