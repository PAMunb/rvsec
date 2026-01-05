#!/usr/bin/env python3
"""
Test logging configuration to understand why diagnostic logs don't appear.
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

def test_logging_levels():
    """Test different logging levels and configurations."""
    import logging
    from rv_android_core.util.logging.manager import LoggingManager
    
    print("=" * 60)
    print("🔍 LOGGING CONFIGURATION TEST")
    print("=" * 60)
    
    # Setup logging manager
    logging_manager = LoggingManager.get_instance()
    logging_manager.configure_output(
        console=True,
        file=False,
        console_level=10,  # DEBUG
        json_format=False
    )
    
    # Test different logger names that our components use
    loggers_to_test = [
        "rvsmart_tool.orchestration",
        "rvsmart_tool.llm.service.action_service",
        "rvsmart_tool.llm.service.state_enricher",
        "test.logger"
    ]
    
    for logger_name in loggers_to_test:
        print(f"\n--- Testing logger: {logger_name} ---")
        
        logger = logging_manager.get_logger(logger_name)
        
        print(f"Logger level: {logger.level}")
        print(f"Logger effective level: {logger.getEffectiveLevel()}")
        print(f"Logger handlers: {len(logger.handlers)}")
        print(f"Logger parent: {logger.parent}")
        
        # Test different log levels
        logger.debug("DEBUG: This is a debug message 🔍")
        logger.info("INFO: This is an info message ℹ️")
        logger.warning("WARNING: This is a warning message ⚠️")
        logger.error("ERROR: This is an error message ❌")
        
        # Test our specific diagnostic patterns
        logger.info("🚀 ACTIONSERVICE INITIALIZATION COMPLETED")
        logger.info("DEBUG_COORD_ENH: Testing coordinate enhancement logging")
        logger.info("🎬 RVSMART TESTORCHESTRATOR EXECUTION START")
        
    # Check root logger configuration
    print(f"\n--- Root logger configuration ---")
    root_logger = logging.getLogger()
    print(f"Root logger level: {root_logger.level}")
    print(f"Root logger handlers: {len(root_logger.handlers)}")
    for i, handler in enumerate(root_logger.handlers):
        print(f"  Handler {i}: {type(handler).__name__} (level: {handler.level})")
        
    # Test specific RVSmart component loggers manually
    print(f"\n--- Manual component logger test ---")
    from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
    
    # Create logger exactly like TestOrchestrator does
    orchestrator_logger = logging_manager.get_logger(
        "rvsmart_tool.orchestration",
        {CONTEXT_COMPONENT: "TestOrchestrator"}
    )
    
    print("TestOrchestrator logger test:")
    orchestrator_logger.info("🎬 MANUAL TEST: TestOrchestrator logging")
    orchestrator_logger.info("DEBUG_COORD_ENH: Manual test coordinate enhancement")
    
    # Create logger exactly like ActionService does
    action_service_logger = logging_manager.get_logger(
        "rvsmart_tool.llm.service.action_service",
        {CONTEXT_COMPONENT: "LLMActionService"}
    )
    
    print("ActionService logger test:")
    action_service_logger.info("🚀 MANUAL TEST: ActionService logging")
    action_service_logger.info("DEBUG_COORD_ENH: Manual test ActionService coordinate enhancement")

def main():
    print("Testing logging configuration to diagnose missing diagnostic logs")
    test_logging_levels()
    
    print("\n" + "=" * 60)
    print("🔍 LOGGING TEST COMPLETED")
    print("   If diagnostic emojis and DEBUG_COORD_ENH appeared above, logging works")
    print("   If they didn't appear, there's a logging configuration issue")
    print("=" * 60)

if __name__ == "__main__":
    main()