import os
import logging
import sys

from rv_monitor_generator import RuntimeVerificationGenerator, RVGeneratorConfig
from rv_android_core.util.logging.manager import LoggingManager


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

    return logging_manager.get_logger('teste.rv_monitor')


def tmp_001(rvsec_root, specs_dir):

    # Create configuration
    config = RVGeneratorConfig(
        rvsec_root=rvsec_root,
        mop_specs_dir=specs_dir
    )
    print(f"Summary: {config.get_configuration_summary()}")

    # Initialize generator
    print("About to create RuntimeVerificationGenerator...")
    generator = RuntimeVerificationGenerator(config)
    print("RuntimeVerificationGenerator created.")

    # Generate monitors for specific specification set
    generated = generator.generate_monitors(
        output_dir="output/monitors/jca"
    )

    if generated:
        print("All monitors generated successfully")
    else:
        print(f"Monitor generation failed")


if __name__ == '__main__':
    logger = setup_logging()

    RVSEC_DIR = os.path.join(os.getcwd(), os.path.abspath(".."))
    MOP_BASE_DIR = os.path.join(RVSEC_DIR, "rvsec-mop", "src", "main", "resources")
    MOP_JCA_DIR = os.path.join(MOP_BASE_DIR, "jca")
    MOP_GENERIC_DIR = os.path.join(MOP_BASE_DIR, "generic")
    specs_mini = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/specs_mini"

    logger.debug("teste 123")
    tmp_001(RVSEC_DIR, specs_mini)
