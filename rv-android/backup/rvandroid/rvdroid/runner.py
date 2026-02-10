# rvandroid/rvdroid/runner.py

"""
RVDroid runner module.

This module serves as the main entry point for the RVDroid testing tool,
providing a command-line interface for test execution.
"""

import argparse
import json
import os
import sys
import time
from typing import Dict, Any, Optional, List

from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.log.logcat_parser import parse_logcat_file
from rvandroid.util.error.error_handler import ErrorHandler
from rvandroid.util.error.decorators import handle_error
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager

from rvandroid.rvdroid.core.config import Config, ConfigKey
from rvandroid.rvdroid.core.coordinator import TestingCoordinator
from rvandroid.rvdroid.core.registry import get_registry
from rvandroid.rvdroid.memory.manager import MemoryManager
from rvandroid.rvdroid.patterns.registry import PatternRegistry
from rvandroid.rvdroid.strategy.manager import StrategyManager
from rvandroid.rvdroid.ui.adapter import UIAdapter


class RVDroidRunner:
    """
    Main entry point for RVDroid testing.
    
    ### Architectural Decisions:
    - Serves as the primary entry point for RVDroid execution
    - Manages command-line interface and configuration loading
    - Delegates to specialized components for testing functionality
    - Coordinates setup, execution, and cleanup of the testing process
    - Provides integration with RV-Android's analysis infrastructure
    
    ### Role in the System:
    - Processes command-line arguments and configuration files
    - Initializes and configures RVDroid components
    - Manages the testing lifecycle
    - Coordinates component interactions
    - Collects and presents test results
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the RVDroid runner.
        
        Args:
            config_path: Optional path to configuration file
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.runner",
            {CONTEXT_COMPONENT: "RVDroidRunner"}
        )
        
        # Initialize error handler
        self.error_handler = ErrorHandler.get_instance()
        
        # Load configuration
        self.config = Config(config_file=config_path)
        
        # Get component registry
        self.registry = get_registry()
        
        # Testing coordinator (initialized later)
        self.coordinator = None
        
        # Command line arguments (set by parse_arguments)
        self.args = None
        
    @handle_error(level="FATAL")
    def initialize(self) -> bool:
        """
        Initialize the RVDroid system.
        
        Returns:
            True if initialization succeeded, False otherwise
        """
        self.logger.info("Initializing RVDroid")
        
        # Check if static analysis is available
        static_data = self._load_static_data()
        
        # Create testing coordinator
        self.coordinator = TestingCoordinator(
            config=self.config.to_dict(),
            static_data=static_data,
            device_id=self.config.get(ConfigKey.DEVICE_ID, "emulator-5554")
        )
        
        # Register coordinator with the registry
        self.registry.register_component(self.coordinator, "TestingCoordinator")
        
        return True
        
    @handle_error(level="FATAL")
    def setup_components(self) -> bool:
        """
        Set up and configure all system components.
        
        Returns:
            True if setup succeeded, False otherwise
        """
        self.logger.info("Setting up RVDroid components")
        
        # Create UI adapter
        ui_adapter = self._create_ui_adapter()
        if not ui_adapter:
            self.logger.error("Failed to create UI adapter")
            return False
            
        # Create memory manager
        memory_manager = self._create_memory_manager()
        if not memory_manager:
            self.logger.error("Failed to create memory manager")
            return False
            
        # Create pattern registry
        pattern_registry = self._create_pattern_registry()
        if not pattern_registry:
            self.logger.error("Failed to create pattern registry")
            return False
            
        # Create strategy manager
        strategy_manager = self._create_strategy_manager()
        if not strategy_manager:
            self.logger.error("Failed to create strategy manager")
            return False
            
        # Create LLM service if enabled
        llm_service = self._create_llm_service()
        
        # Set components in coordinator
        self.coordinator.set_ui_adapter(ui_adapter)
        self.coordinator.set_memory_manager(memory_manager)
        self.coordinator.set_pattern_registry(pattern_registry)
        self.coordinator.set_strategy_manager(strategy_manager)
        
        if llm_service:
            self.coordinator.set_llm_service(llm_service)
            
        # Add dependencies between components
        self.registry.add_dependency("StrategyManager", "MemoryManager")
        self.registry.add_dependency("StrategyManager", "PatternRegistry")
        
        # Initialize all components in the correct order
        if not self.registry.initialize_components():
            self.logger.error("Failed to initialize components")
            return False
            
        return True
    
    @handle_error(level="FATAL")  
    def run(self, package_name: str, activity: Optional[str] = None, 
            timeout: Optional[int] = None, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Run testing on the specified application.
        
        Args:
            package_name: Application package name
            activity: Optional activity to start
            timeout: Optional execution timeout in seconds
            output_dir: Optional output directory
            
        Returns:
            Dictionary with test results
        """
        self.logger.info(f"Starting testing on {package_name}")
        
        # Update timeout if provided
        if timeout:
            self.config.set(ConfigKey.EXECUTION_TIMEOUT, timeout)
            
        # Create output directory if needed
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            self.logger.info(f"Created output directory: {output_dir}")
            
        # Start testing
        if not self.coordinator.start():
            self.logger.error("Failed to start coordinator")
            return {"error": "Failed to start coordinator"}
            
        # Start application testing
        if not self.coordinator.start_testing(package_name, activity):
            self.logger.error(f"Failed to start testing on {package_name}")
            return {"error": f"Failed to start testing on {package_name}"}
            
        # Execute testing loop
        results = self.coordinator.execute_testing_loop()
        
        # Stop coordinator
        self.coordinator.stop()
        
        # Process results if logcat file is available
        if output_dir:
            logcat_file = os.path.join(output_dir, "logcat.txt")
            if os.path.exists(logcat_file):
                self.logger.info(f"Processing logcat file: {logcat_file}")
                logcat_results = self._process_logcat(logcat_file)
                if logcat_results:
                    results.update(logcat_results)
                    
            # Save results to file
            results_file = os.path.join(output_dir, "results.json")
            try:
                with open(results_file, 'w') as f:
                    json.dump(results, f, indent=2)
                self.logger.info(f"Saved results to {results_file}")
            except Exception as e:
                self.logger.error(f"Error saving results: {e}")
                
        return results
        
    @handle_error(level="WARN")
    def shutdown(self) -> None:
        """
        Perform clean shutdown of all components.
        """
        self.logger.info("Shutting down RVDroid")
        
        # Clean up registry components
        if self.registry:
            self.registry.cleanup_components()
            
    def _load_static_data(self) -> Optional[StaticAnalysisData]:
        """
        Load static analysis data.
        
        Returns:
            Static analysis data or None if not available
        """
        # For now, return None as we'll implement this later
        return None
        
    def _create_ui_adapter(self) -> Optional[UIAdapter]:
        """
        Create and configure UI adapter.
        
        Returns:
            UI adapter or None if creation failed
        """
        try:
            # For now, use a placeholder - this will be implemented in the UI module
            from rvandroid.rvdroid.ui.uiautomator import UIAutomator2Adapter
            
            device_id = self.config.get(ConfigKey.DEVICE_ID, "emulator-5554")
            ui_adapter = UIAutomator2Adapter(device_id)
            
            # Register with the registry
            self.registry.register_component(ui_adapter, "UIAdapter")
            
            return ui_adapter
            
        except Exception as e:
            self.logger.error(f"Error creating UI adapter: {e}")
            return None
            
    def _create_memory_manager(self) -> Optional[MemoryManager]:
        """
        Create and configure memory manager.
        
        Returns:
            Memory manager or None if creation failed
        """
        try:
            # For now, use a placeholder - this will be implemented in the Memory module
            from rvandroid.rvdroid.memory.manager import MemoryManager
            
            short_term_capacity = self.config.get(ConfigKey.SHORT_TERM_CAPACITY, 50)
            memory_manager = MemoryManager(short_term_capacity=short_term_capacity)
            
            # Register with the registry
            self.registry.register_component(memory_manager, "MemoryManager")
            
            return memory_manager
            
        except Exception as e:
            self.logger.error(f"Error creating memory manager: {e}")
            return None
            
    def _create_pattern_registry(self) -> Optional[PatternRegistry]:
        """
        Create and configure pattern registry.
        
        Returns:
            Pattern registry or None if creation failed
        """
        try:
            # For now, use a placeholder - this will be implemented in the Patterns module
            from rvandroid.rvdroid.patterns.registry import PatternRegistry
            
            pattern_registry = PatternRegistry()
            
            # Register with the registry
            self.registry.register_component(pattern_registry, "PatternRegistry")
            
            return pattern_registry
            
        except Exception as e:
            self.logger.error(f"Error creating pattern registry: {e}")
            return None
            
    def _create_strategy_manager(self) -> Optional[StrategyManager]:
        """
        Create and configure strategy manager.
        
        Returns:
            Strategy manager or None if creation failed
        """
        try:
            # For now, use a placeholder - this will be implemented in the Strategy module
            from rvandroid.rvdroid.strategy.manager import StrategyManager
            
            preferred_strategy = self.config.get(ConfigKey.PREFERRED_STRATEGY, "MonitoredOperationsFocusedStrategy")
            strategy_manager = StrategyManager(preferred_strategy=preferred_strategy)
            
            # Register with the registry
            self.registry.register_component(strategy_manager, "StrategyManager")
            
            return strategy_manager
            
        except Exception as e:
            self.logger.error(f"Error creating strategy manager: {e}")
            return None
            
    def _create_llm_service(self) -> Optional[Any]:
        """
        Create and configure LLM service if enabled.
        
        Returns:
            LLM service or None if disabled or creation failed
        """
        llm_enabled = self.config.get(ConfigKey.LLM_ENABLED, False)
        if not llm_enabled:
            self.logger.info("LLM integration disabled")
            return None
            
        try:
            # Use the LLM service from the existing llm package
            from rvandroid.llm.language_model import LanguageModel
            llm_model = self.config.get(ConfigKey.LLM_MODEL, "default")
            
            # Create a simple adapter for now
            class LLMServiceAdapter:
                def __init__(self, model_name: str):
                    self.model = LanguageModel.create(model_name)
                    self.name = f"LLMService[{model_name}]"
                    
                def get_strategic_guidance(self, context_type: str, state: Dict[str, Any], 
                                         context: Dict[str, Any]) -> Dict[str, Any]:
                    """Get strategic guidance from LLM."""
                    # This is a placeholder - real implementation will come later
                    return {"directives": []}
                    
                def get_action_feedback(self, action: Dict[str, Any], result: Dict[str, Any],
                                       state: Dict[str, Any]) -> Dict[str, Any]:
                    """Get feedback on action execution."""
                    # This is a placeholder - real implementation will come later
                    return {"suggestions": []}
                    
                def cleanup(self) -> None:
                    """Clean up resources."""
                    pass
                
            llm_service = LLMServiceAdapter(llm_model)
            self.logger.info(f"Created LLM service with model: {llm_model}")
            return llm_service
            
        except Exception as e:
            self.logger.error(f"Error creating LLM service: {e}")
            return None
            
    def _process_logcat(self, logcat_file: str) -> Dict[str, Any]:
        """
        Process logcat file to extract coverage and violations.
        
        Args:
            logcat_file: Path to logcat file
            
        Returns:
            Dictionary with logcat analysis results
        """
        try:
            # Parse logcat file
            repository = parse_logcat_file(logcat_file)
            
            # Create parsed_data dictionary from repository
            parsed_data = {
                "coverage": repository.to_dict() if hasattr(repository, "to_dict") else {},
                "errors": repository.get_errors_dict() if hasattr(repository, "get_errors_dict") else {}
            }
            
            if parsed_data:
                # Extract coverage information
                coverage_data = parsed_data.get("coverage", {})
                method_calls = parsed_data.get("method_calls", [])
                violations = parsed_data.get("violations", [])
                
                # Create result dictionary
                return {
                    "coverage": {
                        "methods_called": len(method_calls) if method_calls else 0,
                        "unique_methods": len(set(method_calls)) if method_calls else 0,
                        **coverage_data
                    },
                    "violations": {
                        "count": len(violations) if violations else 0,
                        "details": violations
                    }
                }
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Error processing logcat file: {e}")
            return {}
            

def parse_arguments():
    """
    Parse command line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description='RVDroid Android Testing Tool')
    
    parser.add_argument('--app', required=True, help='Path to APK file')
    parser.add_argument('--package', required=True, help='Package name')
    parser.add_argument('--activity', help='Initial activity to launch (optional)')
    parser.add_argument('--device', default='emulator-5554', help='Device ID (default: emulator-5554)')
    parser.add_argument('--timeout', type=int, default=3600, help='Execution timeout in seconds (default: 3600)')
    parser.add_argument('--output', help='Output directory for results')
    parser.add_argument('--config', help='Path to configuration file')
    parser.add_argument('--llm', action='store_true', help='Use LLM for strategic guidance')
    parser.add_argument('--strategies', help='Comma-separated list of strategies to use')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    return parser.parse_args()


def setup_logging(debug: bool = False):
    """
    Set up logging configuration.
    
    Args:
        debug: Enable debug logging
    
    Returns:
        Logger instance
    """
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
    """
    Main entry point for the RVDroid runner.
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
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
        # Create configuration dictionary
        config_dict = {
            ConfigKey.DEVICE_ID: args.device,
            ConfigKey.EXECUTION_TIMEOUT: args.timeout,
            ConfigKey.LLM_ENABLED: args.llm
        }
        
        # If strategies provided, set preferred strategy
        if args.strategies:
            strategies = args.strategies.split(',')
            if strategies:
                config_dict[ConfigKey.PREFERRED_STRATEGY] = strategies[0]
        
        # Create runner
        runner = RVDroidRunner(config_path=args.config)
        
        # Update configuration with command line options
        for key, value in config_dict.items():
            runner.config.set(key, value)
        
        # Initialize and setup
        if not runner.initialize():
            logger.error("Failed to initialize RVDroid")
            return 1
            
        if not runner.setup_components():
            logger.error("Failed to set up RVDroid components")
            return 1
            
        # Run testing
        results = runner.run(
            package_name=args.package,
            activity=args.activity,
            timeout=args.timeout,
            output_dir=args.output
        )
        
        # Check for errors
        if "error" in results:
            logger.error(f"Testing failed: {results['error']}")
            return 1
            
        # Display results
        logger.info("Testing completed")
        logger.info(f"Actions executed: {results.get('actions_executed', 0)}")
        logger.info(f"New states discovered: {results.get('new_states', 0)}")
        logger.info(f"Elapsed time: {results.get('elapsed_time', 0):.2f} seconds")
        
        if args.llm:
            logger.info(f"LLM guidance count: {results.get('llm_guidance_count', 0)}")
            
        # Check for violations
        violations = results.get("violations", {}).get("count", 0)
        if violations > 0:
            logger.warning(f"Found {violations} specification violations")
            
        # Clean up
        runner.shutdown()
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Testing interrupted by user")
        return 0
        
    except Exception as e:
        logger.error(f"Error during test execution: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())