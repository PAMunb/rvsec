#!/usr/bin/env python3
"""
Test if WARNING level diagnostic messages appear correctly.
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

def test_warning_logging():
    """Test if warning-level diagnostic messages appear."""
    from rv_android_core.util.logging.manager import LoggingManager
    from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
    
    print("=" * 60)
    print("🔍 WARNING LEVEL DIAGNOSTIC TEST")
    print("=" * 60)
    
    # Setup logging manager
    logging_manager = LoggingManager.get_instance()
    logging_manager.configure_output(
        console=True,
        file=False,
        console_level=10,  # DEBUG
        json_format=False
    )
    
    # Create logger exactly like our components do
    logger = logging_manager.get_logger(
        "test.diagnostic.logger",
        {CONTEXT_COMPONENT: "TestComponent"}
    )
    
    print("\n📋 Testing diagnostic warning messages:")
    print("-" * 40)
    
    # Test our specific diagnostic patterns with WARNING level
    logger.warning("🚀 ACTIONSERVICE INITIALIZATION COMPLETED")
    logger.warning("DEBUG_COORD_ENH: ActionService initialized with vision=True")
    logger.warning("🎬 RVSMART TESTORCHESTRATOR EXECUTION START")
    logger.warning("🔍 DEBUG_COORD_ENH: Starting vision context configuration")
    logger.warning("🧠 STATEENRICHER: Creating processing context")
    logger.warning("DEBUG_COORD_ENH: Processing context created - keys: ['vision_enabled']")
    logger.warning("🔄 PHASE 2: Pre-processing state")
    logger.warning("🎯 ACTIONSERVICE: Processing pipeline completed successfully")
    
    print("\n" + "=" * 60)
    print("✅ WARNING DIAGNOSTIC TEST COMPLETED")
    print("   If you see emojis and DEBUG_COORD_ENH messages above,")
    print("   then the logging configuration is fixed!")
    print("=" * 60)

def main():
    test_warning_logging()
    return 0

if __name__ == "__main__":
    sys.exit(main())