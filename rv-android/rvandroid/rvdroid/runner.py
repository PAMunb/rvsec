# rvandroid/rvdroid/runner.py
"""
Runner module for RVDroid.

Provides a command-line entry point for running RVDroid tests
independently of the main RV-Android framework.
"""

import argparse
import sys
import time
from typing import Dict, Any

from rvandroid.rvdroid.core.service import RVDroidService
from rvandroid.parser.log.logcat_parser import parse_logcat_file
from rvandroid.util.logging.manager import LoggingManager


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='RVDroid Android Testing Tool')

    parser.add_argument('--app', required=True, help='Path to APK file')
    parser.add_argument('--package', required=True, help='Package name')
    parser.add_argument('--activity', help='Initial activity to launch (optional)')
    parser.add_argument('--device', default='emulator-5554', help='Device ID (default: emulator-5554)')
    parser.add_argument('--timeout', type=int, default=3600, help='Execution timeout in seconds (default: 3600)')
    parser.add_argument('--output', help='Output directory for results')
    parser.add_argument('--llm', action='store_true', help='Use LLM for strategic guidance')
    parser.add_argument('--strategies', help='Comma-separated list of strategies to use')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')

    return parser.parse_args()


def setup_logging(debug: bool = False):
    """Set up logging configuration."""
    logging_manager = LoggingManager.get_instance()

    # Configure output
    logging_manager.configure_output(
        console=True,
        file=True,
        console_level=10 if debug else 20,  # DEBUG (10) or INFO (20)
        file_level=10,  # DEBUG
        json_format=False
    )

    logger = logging_manager.get_logger('rvdroid.runner')
    return logger


def main():
    """Main entry point for the RVDroid runner."""
    # Parse arguments
    args = parse_arguments()

    # Set up logging
    logger = setup_logging(args.debug)
    logger.info("Starting RVDroid runner")
    logger.info(f"App: {args.app}")
    logger.info(f"Package: {args.package}")
    logger.info(f"Device: {args.device}")
    logger.info(f"Timeout: {args.timeout} seconds")
    logger.info(f"LLM guidance: {'Enabled' if args.llm else 'Disabled'}")

    try:
        # Initialize service
        service = RVDroidService(device_id=args.device, use_llm=args.llm)

        # Start testing
        logger.info(f"Starting testing of {args.package}")
        result = service.start_testing(
            package_name=args.package,
            activity=args.activity,
            timeout=args.timeout,
            llm_guidance=args.llm
        )

        if not result:
            logger.error("Failed to start testing")
            return 1

        # Execute testing loop
        logger.info("Executing testing loop")
        results = service.execute_testing_loop()

        # Process and display results
        logger.info("Testing completed")
        logger.info(f"Actions executed: {results.get('actions_executed', 0)}")
        logger.info(f"New states discovered: {results.get('new_states', 0)}")
        logger.info(f"Elapsed time: {results.get('elapsed_time', 0):.2f} seconds")

        if args.llm:
            logger.info(f"LLM guidance count: {results.get('llm_guidance_count', 0)}")

        # Clean up
        service.cleanup()

        return 0

    except KeyboardInterrupt:
        logger.info("Testing interrupted by user")
        return 0

    except Exception as e:
        logger.error(f"Error during test execution: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())