"""
Experiment Runner - DI-Ready Entry Point

### Architectural Overview:
This module provides the main entry point for RV-Android experiments, implementing
a DI-ready architecture with simplified orchestration system, factory pattern,
standardized directory structure, and comprehensive error handling.

### Key Architectural Decisions:
- **DI-Ready Design**: Prepared for dependency injection container integration
- **Factory Pattern**: Uses factories for component creation and configuration
- **Standardized Structure**: Uses ./out/ directory structure consistently
- **Monitored Operations Support**: Handles both JCA crypto and generic specifications
- **Error Recovery**: Comprehensive error handling with graceful degradation

### Role in the System:
- Primary entry point for experiment execution
- Provides clean experiment orchestration and management
- Enables both CLI and programmatic usage patterns
- Supports configuration templates and batch processing
- Coordinates experiment lifecycle and resource management

### Design Patterns:
- **Factory Pattern**: Component creation through factory injection
- **Builder Pattern**: Configuration building through templates
- **Command Pattern**: Experiment execution as commands
- **Observer Pattern**: Progress tracking and event notification
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.exceptions import ConfigurationError

from .config import SimpleExperimentConfig
from .simplified_orchestrator import SimplifiedOrchestrator
from .directory_manager import ExperimentDirectoryManager
from .di.interfaces import IExperimentOrchestrator, IDirectoryManager
from .di.providers import ConfigurationProvider, DependencyRegistry
from .di.lifecycle import ComponentLifecycleManager


class ExperimentRunner:
    """
    Experiment runner implementing DI-ready architecture.
    
    ### Architectural Overview:
    This runner implements experiment execution using the simplified orchestrator,
    factory pattern, and standardized directory structure. It provides both CLI
    and programmatic interfaces with comprehensive error handling and progress tracking.
    
    ### Key Architectural Decisions:
    - **DI Integration**: Ready for dependency injection container integration
    - **Factory Pattern**: Uses factories for all component creation
    - **Configuration Management**: Supports multiple configuration sources
    - **Error Recovery**: Comprehensive error handling with recovery strategies
    - **Progress Tracking**: Real-time experiment progress monitoring
    
    ### Role in the System:
    - Primary interface for experiment execution
    - Provides clean separation between configuration and execution
    - Supports both interactive and automated experiment scenarios
    - Enables batch processing and template generation
    - Coordinates component lifecycle and resource management
    """
    
    def __init__(self, config_provider: Optional[ConfigurationProvider] = None,
                 dependency_registry: Optional[DependencyRegistry] = None,
                 logger=None):
        """
        Initialize experiment runner with DI-ready architecture.
        
        ### Initialization Strategy:
        - Sets up logging and error handling infrastructure
        - Initializes configuration provider and dependency registry
        - Prepares component lifecycle manager for future DI integration
        - Creates directory manager for standardized structure
        
        Args:
            config_provider: Optional configuration provider for DI injection
            dependency_registry: Optional dependency registry for DI injection
            logger: Optional logger instance for DI container injection
        """
        # DI-ready logging setup
        if logger:
            self.logger = logger
        else:
            logging_manager = LoggingManager.get_instance()
            self.logger = logging_manager.get_logger(
                "rv_experiment.experiment_runner",
                {CONTEXT_COMPONENT: "ExperimentRunner"}
            )
        
        # Set up error handling
        self.error_handler = ErrorHandler.get_instance()
        
        # Component setup
        self.config_provider = config_provider or ConfigurationProvider()
        self.dependency_registry = dependency_registry or DependencyRegistry()
        self.lifecycle_manager = ComponentLifecycleManager(logger=self.logger)
        
        # Initialize directory manager
        self.directory_manager = ExperimentDirectoryManager(logger=self.logger)
        
        # Runner state
        self.current_orchestrator: Optional[IExperimentOrchestrator] = None
        self.execution_history: List[Dict[str, Any]] = []
        
        self.logger.info("ExperimentRunner initialized")
    
    @ErrorHandler.handle_errors(
        component="ExperimentRunner",
        phase="run_experiment_from_config",
    )
    def run_experiment_from_config(self, config: SimpleExperimentConfig) -> bool:
        """
        Run experiment using simplified configuration.
        
        ### Execution Strategy:
        - Validates experiment configuration comprehensively
        - Creates DI-ready orchestrator with factory injection
        - Executes experiment with progress tracking and error handling
        - Provides comprehensive result reporting and cleanup
        
        Args:
            config: Simplified experiment configuration
            
        Returns:
            True if experiment completed successfully, False otherwise
        """
        try:
            self.logger.info(f"Starting experiment: {config.experiment_id}")
            
            # Validate configuration
            config.validate()
            
            # Create experiment directory
            exp_dir = self.directory_manager.create_experiment_directory(
                config.experiment_id,
                config.specification_set
            )
            
            # Create orchestrator with dependency injection
            self.current_orchestrator = SimplifiedOrchestrator(
                config=config,
                directory_manager=self.directory_manager,
                logger=self.logger
            )
            
            # Register orchestrator with lifecycle manager
            self.lifecycle_manager.register_component(
                name="orchestrator",
                component=self.current_orchestrator,
                config=config.to_dict()
            )
            
            # Initialize and start orchestrator
            if not self.lifecycle_manager.initialize_all():
                self.logger.error("Failed to initialize experiment components")
                return False
            
            if not self.lifecycle_manager.start_all():
                self.logger.error("Failed to start experiment components")
                return False
            
            # Execute experiment
            execution_start = datetime.now()
            success = self.current_orchestrator.execute()
            execution_end = datetime.now()
            
            # Record execution history
            execution_record = {
                "experiment_id": config.experiment_id,
                "specification_set": config.specification_set,
                "started_at": execution_start.isoformat(),
                "completed_at": execution_end.isoformat(),
                "duration_seconds": (execution_end - execution_start).total_seconds(),
                "success": success,
                "tools": [tool["name"] for tool in config.tools],
                "results_summary": self.current_orchestrator.get_results_summary() if success else None
            }
            
            self.execution_history.append(execution_record)
            
            # Save execution record
            self._save_execution_record(exp_dir, execution_record)
            
            # Stop components gracefully
            self.lifecycle_manager.stop_all()
            
            if success:
                self.logger.info(f"Experiment completed successfully: {config.experiment_id}")
            else:
                self.logger.error(f"Experiment failed: {config.experiment_id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Experiment execution failed: {e}")
            
            # Attempt graceful cleanup
            if self.current_orchestrator:
                try:
                    self.current_orchestrator.stop_experiment()
                except Exception:
                    pass
            
            try:
                self.lifecycle_manager.stop_all()
            except Exception:
                pass
            
            return False
    
    @ErrorHandler.handle_errors(
        component="ExperimentRunner",
        phase="run_from_file",
    )
    def run_from_file(self, config_file: str) -> bool:
        """
        Run experiment from configuration file.
        
        Args:
            config_file: Path to configuration file (JSON or YAML)
            
        Returns:
            True if experiment completed successfully, False otherwise
        """
        try:
            config_path = Path(config_file)
            if not config_path.exists():
                raise ConfigurationError(f"Configuration file not found: {config_file}")
            
            self.logger.info(f"Loading experiment configuration from: {config_file}")
            
            # Load configuration
            with open(config_path, 'r') as f:
                if config_path.suffix.lower() == '.json':
                    config_data = json.load(f)
                elif config_path.suffix.lower() in ['.yml', '.yaml']:
                    import yaml
                    config_data = yaml.safe_load(f)
                else:
                    # Try JSON as default
                    config_data = json.load(f)
            
            # Create configuration instance
            config = SimpleExperimentConfig.from_dict(config_data)
            
            # Run experiment
            return self.run_experiment_from_config(config)
            
        except Exception as e:
            self.logger.error(f"Failed to run experiment from file {config_file}: {e}")
            return False
    
    def run_batch_experiments(self, config_files: List[str]) -> Dict[str, bool]:
        """
        Run multiple experiments in sequence.
        
        Args:
            config_files: List of configuration file paths
            
        Returns:
            Dictionary mapping config file to success status
        """
        results = {}
        
        self.logger.info(f"Starting batch experiment execution: {len(config_files)} experiments")
        
        for config_file in config_files:
            self.logger.info(f"Running experiment from: {config_file}")
            
            try:
                success = self.run_from_file(config_file)
                results[config_file] = success
                
                if success:
                    self.logger.info(f"✓ Experiment completed: {config_file}")
                else:
                    self.logger.error(f"✗ Experiment failed: {config_file}")
                    
            except Exception as e:
                self.logger.error(f"✗ Experiment error {config_file}: {e}")
                results[config_file] = False
        
        # Report batch results
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        
        self.logger.info(f"Batch execution completed: {successful}/{total} experiments successful")
        
        return results
    
    def create_template_config(self, template_type: str = "basic", 
                             output_file: Optional[str] = None) -> SimpleExperimentConfig:
        """
        Create template configuration for common scenarios.
        
        Args:
            template_type: Type of template ("basic", "advanced", "llm")
            output_file: Optional file to save template configuration
            
        Returns:
            Created template configuration
        """
        self.logger.info(f"Creating {template_type} template configuration")
        
        if template_type == "basic":
            config = SimpleExperimentConfig.create_basic_template()
        elif template_type == "advanced":
            config = SimpleExperimentConfig.create_advanced_template()
        elif template_type == "llm":
            config = SimpleExperimentConfig.create_llm_template()
        else:
            raise ValueError(f"Unknown template type: {template_type}")
        
        # Save template if requested
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                json.dump(config.to_dict(), f, indent=2)
            
            self.logger.info(f"Template configuration saved to: {output_file}")
        
        return config
    
    def _save_execution_record(self, experiment_dir: Path, 
                             execution_record: Dict[str, Any]) -> None:
        """
        Save execution record to experiment directory.
        
        Args:
            experiment_dir: Experiment directory path
            execution_record: Execution record to save
        """
        try:
            record_file = experiment_dir / "execution_record.json"
            with open(record_file, 'w') as f:
                json.dump(execution_record, f, indent=2, default=str)
            
            self.logger.debug(f"Execution record saved: {record_file}")
            
        except Exception as e:
            self.logger.warning(f"Failed to save execution record: {e}")
    
    def get_execution_history(self) -> List[Dict[str, Any]]:
        """
        Get execution history for this runner session.
        
        Returns:
            List of execution records
        """
        return self.execution_history.copy()
    
    def get_progress(self) -> Optional[Dict[str, Any]]:
        """
        Get current experiment progress if running.
        
        Returns:
            Progress information or None if no experiment running
        """
        if self.current_orchestrator:
            return self.current_orchestrator.get_progress()
        return None
    
    def stop_current_experiment(self) -> bool:
        """
        Stop currently running experiment gracefully.
        
        Returns:
            True if stopped successfully, False otherwise
        """
        if self.current_orchestrator:
            try:
                self.logger.info("Stopping current experiment")
                result = self.current_orchestrator.stop_experiment()
                self.lifecycle_manager.stop_all()
                return result
            except Exception as e:
                self.logger.error(f"Failed to stop experiment: {e}")
                return False
        return True


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create command line argument parser for experiment runner.
    
    Returns:
        Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description="RV-Android Experiment Runner - DI-Ready Architecture",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run single experiment
  python -m rv_experiment.experiment_runner --config config.json
  
  # Run batch experiments
  python -m rv_experiment.experiment_runner --batch config1.json config2.json
  
  # Create template configuration
  python -m rv_experiment.experiment_runner --template basic --output basic_config.json
  
  # Create LLM-focused template
  python -m rv_experiment.experiment_runner --template llm --output llm_config.json
        """
    )
    
    # Main operation modes
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--config", "-c",
        type=str,
        help="Run single experiment from configuration file"
    )
    group.add_argument(
        "--batch", "-b",
        nargs="+",
        help="Run multiple experiments from configuration files"
    )
    group.add_argument(
        "--template", "-t",
        choices=["basic", "advanced", "llm"],
        help="Create template configuration"
    )
    
    # Template options
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output file for template configuration"
    )
    
    # Logging options
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Enable quiet mode (errors only)"
    )
    
    return parser


def main():
    """
    Main entry point for experiment runner CLI.
    
    ### CLI Strategy:
    - Provides comprehensive command line interface for all runner features
    - Supports single experiment execution, batch processing, and template generation
    - Enables different logging levels and output configurations
    - Demonstrates clean architectural patterns through CLI usage
    """
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Set up logging level
    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.quiet:
        import logging
        logging.getLogger().setLevel(logging.ERROR)
    
    # Create experiment runner
    runner = ExperimentRunner()
    
    try:
        if args.config:
            # Single experiment
            success = runner.run_from_file(args.config)
            sys.exit(0 if success else 1)
            
        elif args.batch:
            # Batch experiments
            results = runner.run_batch_experiments(args.batch)
            failed_count = sum(1 for success in results.values() if not success)
            sys.exit(failed_count)
            
        elif args.template:
            # Template creation
            output_file = args.output or f"{args.template}_config.json"
            config = runner.create_template_config(args.template, output_file)
            print(f"Template configuration created: {output_file}")
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\nExperiment interrupted by user")
        runner.stop_current_experiment()
        sys.exit(130)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()