#!/usr/bin/env python3
"""
RVAgent Phase 0 Prototype - Main Execution Script

Hardcoded prototype execution without CLI for simplicity.
Executes parameter grid search with configurable test parameters.
"""
import sys
import traceback
from pathlib import Path
from datetime import datetime

# Add module to path
sys.path.insert(0, str(Path(__file__).parent))

from config import PrototypeConfig
from prototype_executor import create_prototype_executor
from rv_android_core.util.logging.manager import LoggingManager


def setup_logging():
    """Setup logging for prototype execution."""
    logging_manager = LoggingManager.get_instance()
    
    # Configure console logging
    logging_manager.configure_logging(
        level="INFO",  # Change to DEBUG for verbose output
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    return logging_manager.get_logger("rv_agent.prototype_main")


def validate_environment(config: PrototypeConfig, logger):
    """Validate that the execution environment is ready."""
    logger.info("Validating execution environment...")
    
    # Check screenshots directory
    screenshots_path = Path(config.SCREENSHOTS_DIR)
    if not screenshots_path.exists():
        raise FileNotFoundError(f"Screenshots directory not found: {config.SCREENSHOTS_DIR}")
    
    # Check available apps
    available_apps = config.get_available_apps()
    if len(available_apps) < config.NUM_TEST_APPS:
        raise ValueError(
            f"Not enough apps available. Found {len(available_apps)}, need {config.NUM_TEST_APPS}"
        )
    
    # Verify sample files exist
    sample_app = available_apps[0]
    sample_screenshots = config.random_select_screenshots(sample_app, num_screenshots=1)
    if sample_screenshots:
        try:
            image_path, xml_path = config.get_screenshot_files(sample_app, sample_screenshots[0])
            logger.info(f"Environment validation successful. Sample files found.")
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Sample file validation failed: {e}")
    
    logger.info(f"Environment validated. {len(available_apps)} apps available.")


def main():
    """
    Main prototype execution function.
    
    Hardcoded configuration for Phase 0 prototype simplicity.
    """
    logger = setup_logging()
    
    try:
        logger.info("=" * 80)
        logger.info("RVAgent Phase 0 Prototype - Parameter Grid Search")
        logger.info("=" * 80)
        
        # Initialize configuration (hardcoded for prototype simplicity)
        config = PrototypeConfig(
            # Configurable test parameters (can be modified here)
            NUM_TEST_APPS=10,           # Number of apps to test (default: 10)
            SCREENSHOTS_PER_APP=5,      # Screenshots per app (default: 5)
            TIMEOUT_SECONDS=30,         # Timeout per test (default: 30s)
            
            # Parameter grid (can be customized)
            TEMPERATURES=[0.1, 0.3, 0.7],  # Temperature variations
            TOP_PS=[0.7, 0.9],             # Top-p variations
            TOP_KS=[20, 40],               # Top-k variations
            
            # Vision model configuration (from research)
            PRIMARY_MODEL="qwen2.5vl:7b",  # Champion model (98.3% success)
            COORDINATE_TOLERANCE=50,        # 50px tolerance (research methodology)
            RANDOM_SEED=42                  # For reproducible results
        )
        
        # Validate environment
        validate_environment(config, logger)
        
        # Create and run executor
        executor = create_prototype_executor(config)
        
        logger.info(f"Starting execution of {config.total_tests:,} tests...")
        logger.info(f"Estimated duration: {config.estimated_duration_hours:.1f} hours")
        
        # Execute prototype
        report = executor.run()
        
        # Print results summary
        report.print_summary()
        
        # Save detailed results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"rv_agent_prototype_results_{timestamp}.json"
        executor.save_final_results(results_file)
        
        # Final success message
        logger.info("=" * 80)
        logger.info("RVAgent Phase 0 Prototype completed successfully!")
        logger.info(f"Results saved to: {results_file}")
        logger.info(f"Overall Success Rate: {report.success_rate:.1f}%")
        
        if report.best_parameters:
            logger.info(f"Best Parameters: {report.best_parameters}")
            best_perf = max(report.parameter_performance.values(), key=lambda x: x.success_rate)
            logger.info(f"Best Success Rate: {best_perf.success_rate:.1f}%")
        
        logger.info("=" * 80)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Execution interrupted by user")
        return 1
        
    except Exception as e:
        logger.error(f"Prototype execution failed: {e}")
        logger.error("Full traceback:")
        logger.error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    """
    Direct execution entry point.
    
    Usage:
        cd modules/rv-agent
        python src/rv_agent/prototype_main.py
    """
    sys.exit(main())