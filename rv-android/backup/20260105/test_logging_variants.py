#!/usr/bin/env python3
"""
Test different logging message variants to identify filtering.
"""

import os
import sys
from pathlib import Path

# Setup paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "modules" / "rv-android-core" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rvsmart-tool" / "src"))

# Environment setup
from rv_android_core import constants
parent_directory = os.path.dirname(os.getcwd())
os.environ[constants.ENV_RVSEC_HOME] = parent_directory

def test_logging_variants():
    """Test different message types to identify what gets filtered."""
    import logging
    from rv_android_core.util.logging.manager import LoggingManager
    from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
    
    print("=" * 60)
    print("LOGGING VARIANTS TEST")
    print("=" * 60)
    
    # Setup logging manager
    logging_manager = LoggingManager.get_instance()
    logging_manager.configure_output(
        console=True,
        file=False,
        console_level=10,  # DEBUG
        json_format=False
    )
    
    # Create logger
    logger = logging_manager.get_logger(
        "test.logger",
        {CONTEXT_COMPONENT: "TestComponent"}
    )
    
    print("\nTesting different message variants:")
    print("-" * 40)
    
    # Test basic messages
    print("1. Basic messages:")
    logger.info("Simple info message")
    logger.warning("Simple warning message")
    logger.error("Simple error message")
    
    # Test messages with special characters
    print("\n2. Messages with special characters:")
    logger.info("Message with emoji: 🚀")
    logger.info("Message with unicode: →")
    logger.info("Message with DEBUG_COORD_ENH prefix")
    
    # Test specific diagnostic patterns
    print("\n3. Diagnostic patterns:")
    logger.info("RVSMART TESTORCHESTRATOR EXECUTION START")
    logger.info("ACTIONSERVICE INITIALIZATION COMPLETED")
    logger.info("DEBUG_COORD_ENH: Testing coordinate enhancement")
    
    # Test with different log levels
    print("\n4. Different log levels:")
    logger.debug("DEBUG: This is a debug message")
    logger.info("INFO: This is an info message")
    logger.warning("WARNING: This is a warning message")
    logger.error("ERROR: This is an error message")
    
    # Test standard Python logging directly
    print("\n5. Direct Python logging:")
    logging.info("Direct Python logging.info")
    logging.warning("Direct Python logging.warning")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETED - Check which messages appeared above")
    print("=" * 60)

def main():
    test_logging_variants()
    return 0

if __name__ == "__main__":
    sys.exit(main())