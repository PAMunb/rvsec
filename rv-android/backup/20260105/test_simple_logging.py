#!/usr/bin/env python3
"""
Simple logging test to verify diagnostic messages appear.
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

def test_simple_logging():
    """Test if diagnostic logs appear with simple configuration."""
    import logging
    from rv_android_core.util.logging.manager import LoggingManager
    from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
    
    print("=" * 60)
    print("🔍 SIMPLE LOGGING TEST")
    print("=" * 60)
    
    # Setup logging manager
    logging_manager = LoggingManager.get_instance()
    logging_manager.configure_output(
        console=True,
        file=False,
        console_level=10,  # DEBUG
        json_format=False
    )
    
    print("\n📋 Testing different diagnostic messages...")
    print("=" * 60)
    
    # Create logger exactly like TestOrchestrator does
    orchestrator_logger = logging_manager.get_logger(
        "rvsmart_tool.orchestration",
        {CONTEXT_COMPONENT: "TestOrchestrator"}
    )
    
    print("1. TestOrchestrator diagnostic messages:")
    orchestrator_logger.info("🎬 RVSMART TESTORCHESTRATOR EXECUTION START")
    orchestrator_logger.info("✅ Device connection established: emulator-5554")
    orchestrator_logger.info("🔄 STARTING SINGLE TEST CYCLE")
    
    # Create logger exactly like ActionService does
    action_service_logger = logging_manager.get_logger(
        "rvsmart_tool.llm.service.action_service",
        {CONTEXT_COMPONENT: "LLMActionService"}
    )
    
    print("\n2. ActionService diagnostic messages:")
    action_service_logger.info("🚀 ACTIONSERVICE INITIALIZATION COMPLETED")
    action_service_logger.info("🎯 ACTIONSERVICE: Starting state processing pipeline")
    action_service_logger.info("DEBUG_COORD_ENH: Processing context created")
    
    # Create logger exactly like StateEnricher does
    state_enricher_logger = logging_manager.get_logger(
        "rvsmart_tool.llm.service.state_enricher",
        {CONTEXT_COMPONENT: "StateEnricher"}
    )
    
    print("\n3. StateEnricher diagnostic messages:")
    state_enricher_logger.info("🔧 STATEENRICHER INITIALIZATION")
    state_enricher_logger.info("DEBUG_COORD_ENH: Vision detected from llm_config.vision = True")
    state_enricher_logger.info("🧠 STATEENRICHER: Creating processing context")
    
    print("\n" + "=" * 60)
    print("📊 LOGGING TEST SUMMARY:")
    print("   If you see emoji and DEBUG_COORD_ENH messages above,")
    print("   then the logging system works but components aren't")
    print("   calling the logger methods during initialization/execution.")
    print("=" * 60)

def main():
    test_simple_logging()
    return 0

if __name__ == "__main__":
    sys.exit(main())