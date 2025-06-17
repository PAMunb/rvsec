import logging
import os
import sys

from rv_android_core import constants
from rv_android_core.util.logging.manager import LoggingManager
from rv_experiment.config import ExperimentConfig, ToolConfiguration
from rv_experiment.experiment.experiment_controller import execute_with_config


def setup_logging(debug: bool = True):
    """Set up logging configuration."""
    # Setup basic logging first
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )

    # Get the logging manager
    logging_manager = LoggingManager.get_instance()

    # Configure output to show all rvandroid logs including module logs
    logging_manager.configure_output(
        console=True,
        file=False,
        console_level=10 if debug else 20,  # DEBUG (10) or INFO (20)
        file_level=10,  # DEBUG
        json_format=False
    )

    return logging_manager.get_logger('teste.rv_experiment')


def tmp_001():
    # Create tool configurations
    tools = [
        ToolConfiguration(name="monkey")
        # ToolConfiguration(name="ape")
    ]

    # Create experiment configuration
    config = ExperimentConfig(
        name="basic_experiment",
        description="Basic experiment",
        tool_configs=tools,
        repetitions=1,
        timeouts=[60],
        specification_set="custom",
        apk_dir="./apks_examples/",
        apk_patterns=["*.apk"]
    )
    config.custom_specs_dir = "./specs_mini"
    config.generate_monitors = False
    config.instrument_apks = False
    config.run_static_analysis = False
    config.no_window = True

    # Validate configuration
    config.validate()

    # Execute experiment
    execute_with_config(config)


if __name__ == '__main__':
    current_directory = os.getcwd()
    parent_directory = os.path.dirname(current_directory)
    os.environ[constants.ENV_RVSEC_HOME] = parent_directory

    logger = setup_logging()

    tmp_001()
