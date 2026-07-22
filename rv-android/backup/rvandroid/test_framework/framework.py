"""
Main test framework module.

This module provides the main TestFramework class that orchestrates
the entire testing process, from configuration to execution and analysis.
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Set, Tuple

from rvandroid.test_framework.config import (
    TestSuite, TestCase, ToolConfiguration, create_default_test_suite
)
from rvandroid.test_framework.executor import TestRunner, TestResult
from rvandroid.test_framework.analyzer import ResultAnalyzer
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class TestFramework:
    """
    Main test framework class for RV-Android tools optimization.
    
    Orchestrates the entire testing process, including configuration,
    execution, and analysis to identify optimal tool configurations.
    
    ### Key Responsibilities:
    - Manages the complete testing lifecycle
    - Handles test suite configuration and execution
    - Coordinates result analysis and reporting
    - Provides user interface for interacting with the framework
    """
    
    def __init__(self, output_dir: str = "test_framework_results"):
        """
        Initialize the test framework.
        
        Args:
            output_dir: Base directory for framework output
        """
        self.output_dir = output_dir
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = os.path.join(output_dir, f"run_{timestamp}")
        os.makedirs(self.run_dir, exist_ok=True)
        
        # Set up logging
        self.logger = LoggingManager.get_instance().get_logger(
            'test_framework',
            {CONTEXT_COMPONENT: 'TestFramework'}
        )
        
        # Results storage
        self.current_test_suite: Optional[TestSuite] = None
        self.current_results: List[TestResult] = []
        self.analysis_report: Optional[str] = None
        
    def configure(self, 
                 apps: List[str], 
                 test_suite: Optional[TestSuite] = None,
                 repetitions: int = 1) -> TestSuite:
        """
        Configure the test framework.
        
        Args:
            apps: List of paths to APK files to test
            test_suite: Optional custom test suite
            repetitions: Number of repetitions for each test case
            
        Returns:
            Configured test suite
        """
        self.logger.info(f"Configuring test framework with {len(apps)} apps")
        
        # Use provided test suite or create default
        if test_suite:
            self.current_test_suite = test_suite
        else:
            self.current_test_suite = create_default_test_suite()
        
        # Update app paths
        self.current_test_suite.apps = apps
        
        # Set repetitions
        self.current_test_suite.repetitions = repetitions
        
        # Set output directory
        self.current_test_suite.output_dir = self.run_dir
        
        # Save test suite configuration
        config_file = os.path.join(self.run_dir, "test_suite_config.json")
        self.current_test_suite.save_to_file(config_file)
        
        self.logger.info(f"Test suite configured with {len(self.current_test_suite.tool_configurations)} configurations")
        
        return self.current_test_suite
    
    def run(self, progress_callback: Optional[Callable[[int, int, str], None]] = None) -> List[TestResult]:
        """
        Run the configured test suite.
        
        Args:
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of test results
            
        Raises:
            ValueError: If test suite is not configured
        """
        if not self.current_test_suite:
            raise ValueError("Test suite not configured. Call configure() first.")
        
        self.logger.info(f"Starting test suite: {self.current_test_suite.name}")
        
        # Create test runner
        runner = TestRunner(output_dir=self.run_dir)
        
        # Run test suite
        self.current_results = runner.run_test_suite(
            self.current_test_suite,
            progress_callback
        )
        
        # Log summary
        self.logger.info(f"Test suite completed with {len(self.current_results)} results")
        
        return self.current_results
    
    def analyze(self) -> Dict[str, Any]:
        """
        Analyze test results.
        
        Returns:
            Analysis results
            
        Raises:
            ValueError: If no test results are available
        """
        if not self.current_results:
            raise ValueError("No test results available. Call run() first.")
        
        self.logger.info("Analyzing test results")
        
        # Create analyzer
        analyzer = ResultAnalyzer(self.current_results, self.run_dir)
        
        # Generate report
        self.analysis_report = analyzer.generate_report()
        
        # Get analysis results
        analysis_result = analyzer.analyze()
        
        self.logger.info(f"Analysis completed. Report saved to {self.analysis_report}")
        
        return analysis_result
    
    def get_optimal_configurations(self) -> Dict[str, List[ToolConfiguration]]:
        """
        Get optimal tool configurations from analysis results.
        
        Returns:
            Dictionary mapping criteria to lists of tool configurations
            
        Raises:
            ValueError: If analysis has not been performed
        """
        if not self.analysis_report:
            raise ValueError("Analysis not performed. Call analyze() first.")
        
        # Load analysis results
        analysis_file = os.path.join(self.run_dir, "analysis_results.json")
        with open(analysis_file, 'r') as f:
            analysis_result = json.load(f)
        
        best_configs = analysis_result.get("best_configurations", {})
        
        # Convert config IDs to configuration objects
        optimal_configs = {}
        
        # Process overall best configurations
        overall_ids = best_configs.get("overall", [])
        overall_configs = []
        for config_id in overall_ids:
            for config in self.current_test_suite.tool_configurations:
                if config.get_id() == config_id:
                    overall_configs.append(config)
                    break
        
        optimal_configs["overall"] = overall_configs
        
        # Process tool-specific configurations
        by_tool = best_configs.get("by_tool", {})
        tool_configs = {}
        
        for tool_name, config_ids in by_tool.items():
            tool_configs[tool_name] = []
            for config_id in config_ids:
                for config in self.current_test_suite.tool_configurations:
                    if config.get_id() == config_id:
                        tool_configs[tool_name].append(config)
                        break
        
        optimal_configs["by_tool"] = tool_configs
        
        return optimal_configs
    
    def analyze_batch_strategies(self) -> Dict[str, Any]:
        """
        Analyze batch action strategies vs. single action approaches.
        
        Performs a comparative analysis between batch and single action strategies,
        quantifying improvements in efficiency, coverage, and MOP detection.
        
        Returns:
            Batch analysis results
            
        Raises:
            ValueError: If no test results are available
        """
        if not self.current_results:
            raise ValueError("No test results available. Call run() first.")
        
        self.logger.info("Analyzing batch action strategies")
        
        # Create batch analyzer
        from rvandroid.test_framework.batch_analyzer import BatchAnalyzer
        batch_analyzer = BatchAnalyzer(self.current_results, self.run_dir)
        
        # Generate report
        report_file, batch_analysis = batch_analyzer.generate_report()
        
        self.logger.info(f"Batch analysis completed. Report saved to {report_file}")
        
        return batch_analysis
        
    def save_batch_analysis(self, output_file: str) -> str:
        """
        Save batch action analysis results to a JSON file.
        
        Args:
            output_file: Path to save the analysis
            
        Returns:
            Path to saved file
            
        Raises:
            ValueError: If batch analysis has not been performed
        """
        # Run batch analysis if not already done
        batch_analysis = self.analyze_batch_strategies()
        
        # Prepare serializable output (remove chart_files which are just paths)
        output_data = dict(batch_analysis)
        if "chart_files" in output_data:
            del output_data["chart_files"]
        
        # Save to file
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        self.logger.info(f"Batch analysis results saved to {output_file}")
        
        return output_file
        
    def save_optimal_configurations(self, output_file: str) -> str:
        """
        Save optimal configurations to a JSON file.
        
        Args:
            output_file: Path to save configurations
            
        Returns:
            Path to saved file
            
        Raises:
            ValueError: If analysis has not been performed
        """
        if not self.analysis_report:
            raise ValueError("Analysis not performed. Call analyze() first.")
        
        # Get optimal configurations
        optimal_configs = self.get_optimal_configurations()
        
        # Prepare serializable output
        output_data = {
            "timestamp": datetime.now().isoformat(),
            "overall_best": [
                config.to_dict() for config in optimal_configs["overall"]
            ]
        }
        
        # Add tool-specific configurations
        output_data["best_by_tool"] = {
            tool: [config.to_dict() for config in configs]
            for tool, configs in optimal_configs["by_tool"].items()
        }
        
        # Save to file
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        self.logger.info(f"Optimal configurations saved to {output_file}")
        
        return output_file
        
    def get_best_batch_configuration(self) -> Optional[ToolConfiguration]:
        """
        Get the best batch action strategy configuration.
        
        Returns:
            Best batch configuration or None if no batch configurations found
        """
        # Run batch analysis if not already done
        batch_analysis = self.analyze_batch_strategies()
        
        # Get the best batch configuration ID
        best_batch_id = batch_analysis.get("best_batch_config")
        
        if not best_batch_id:
            self.logger.warning("No batch action configurations found in results")
            return None
        
        # Find the matching configuration
        for config in self.current_test_suite.tool_configurations:
            if config.get_id() == best_batch_id:
                return config
                
        return None