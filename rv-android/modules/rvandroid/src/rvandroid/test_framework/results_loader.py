"""
Results loader module for test framework.

This module provides functionality for loading and processing
test results from previous test runs for analysis.
"""

import os
import json
import glob
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
from datetime import datetime
from dataclasses import asdict

from rv_android_core.test_framework.config import TestCase, TestSuite, ToolConfiguration
from rv_android_core.test_framework.executor import TestResult
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager


class ResultsLoader:
    """
    Loader for test results from previous runs.
    
    Loads and processes test results from previous test runs
    for analysis and comparison.
    
    ### Key Responsibilities:
    - Discovers result files in specified directories
    - Loads and deserializes test results
    - Groups results by test suite, tool, and app
    - Provides structured access to loaded results
    """
    
    def __init__(self, base_dir: str = "test_results"):
        """
        Initialize the results loader.
        
        Args:
            base_dir: Base directory for test results
        """
        self.base_dir = base_dir
        
        # Set up logging
        self.logger = LoggingManager.get_instance().get_logger(
            'test_framework.results_loader',
            {CONTEXT_COMPONENT: 'ResultsLoader'}
        )
        
        # Results storage
        self.loaded_results: List[TestResult] = []
        self.test_suites: Dict[str, List[TestResult]] = {}
        
    def discover_results(self) -> List[str]:
        """
        Discover result directories in the base directory.
        
        Returns:
            List of result directory paths
        """
        result_dirs = []
        
        # Find all potential result directories
        for item in os.listdir(self.base_dir):
            item_path = os.path.join(self.base_dir, item)
            
            # Check if it's a directory
            if os.path.isdir(item_path):
                # Check if it contains analysis_results.json
                if os.path.exists(os.path.join(item_path, "analysis_results.json")):
                    result_dirs.append(item_path)
                else:
                    # Check subdirectories for run directories
                    for subitem in os.listdir(item_path):
                        subitem_path = os.path.join(item_path, subitem)
                        if os.path.isdir(subitem_path) and os.path.exists(os.path.join(subitem_path, "analysis_results.json")):
                            result_dirs.append(subitem_path)
        
        self.logger.info(f"Discovered {len(result_dirs)} result directories")
        return result_dirs
    
    def load_results(self, result_dirs: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Load test results from specified directories.
        
        Args:
            result_dirs: List of result directory paths. If None, discover results.
            
        Returns:
            List of loaded result data
        """
        if result_dirs is None:
            result_dirs = self.discover_results()
        
        loaded_data = []
        
        for result_dir in result_dirs:
            try:
                # Load analysis results
                analysis_file = os.path.join(result_dir, "analysis_results.json")
                if os.path.exists(analysis_file):
                    with open(analysis_file, 'r') as f:
                        analysis_data = json.load(f)
                        
                    # Add result directory to data
                    analysis_data['result_dir'] = result_dir
                    
                    # Check for test suite configuration
                    config_file = os.path.join(result_dir, "test_suite_config.json")
                    if os.path.exists(config_file):
                        with open(config_file, 'r') as f:
                            analysis_data['test_suite'] = json.load(f)
                    
                    loaded_data.append(analysis_data)
                    self.logger.info(f"Loaded analysis results from {result_dir}")
            except Exception as e:
                self.logger.error(f"Error loading results from {result_dir}: {str(e)}")
        
        self.logger.info(f"Loaded {len(loaded_data)} result sets")
        return loaded_data
    
    def reconstruct_results(self, analysis_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Reconstruct test results from analysis data.
        
        Args:
            analysis_data: List of analysis data dictionaries
            
        Returns:
            List of reconstructed result data
        """
        reconstructed_results = []
        
        for data in analysis_data:
            try:
                # Extract result directory
                result_dir = data.get('result_dir', '')
                
                # Extract test suite
                test_suite_data = data.get('test_suite')
                
                # Extract configuration metrics
                config_metrics = data.get('configuration_metrics', {})
                
                # Reconstruct results for each configuration
                for config_id, metrics in config_metrics.items():
                    # Find result directories for this configuration
                    config_dirs = glob.glob(os.path.join(result_dir, f"*{config_id}*"))
                    
                    for config_dir in config_dirs:
                        # Extract app name from directory name
                        dir_name = os.path.basename(config_dir)
                        app_name = dir_name.split('_')[0] if '_' in dir_name else ''
                        
                        # Find logcat file
                        logcat_files = glob.glob(os.path.join(config_dir, "logcat*.txt"))
                        logcat_file = logcat_files[0] if logcat_files else None
                        
                        # Find trace file
                        trace_files = glob.glob(os.path.join(config_dir, "trace*.txt"))
                        trace_file = trace_files[0] if trace_files else None
                        
                        # Create result data
                        result_data = {
                            'config_id': config_id,
                            'app_name': app_name,
                            'result_dir': config_dir,
                            'logcat_file': logcat_file,
                            'trace_file': trace_file,
                            'metrics': metrics,
                        }
                        
                        # Add test suite data if available
                        if test_suite_data:
                            result_data['test_suite'] = test_suite_data
                        
                        reconstructed_results.append(result_data)
            except Exception as e:
                self.logger.error(f"Error reconstructing results: {str(e)}")
        
        self.logger.info(f"Reconstructed {len(reconstructed_results)} test results")
        return reconstructed_results
    
    def group_results_by_config(self, results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group results by configuration ID.
        
        Args:
            results: List of result data
            
        Returns:
            Dictionary mapping configuration IDs to lists of results
        """
        grouped_results = {}
        
        for result in results:
            config_id = result.get('config_id')
            if config_id:
                if config_id not in grouped_results:
                    grouped_results[config_id] = []
                grouped_results[config_id].append(result)
        
        return grouped_results
    
    def group_results_by_app(self, results: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group results by app name.
        
        Args:
            results: List of result data
            
        Returns:
            Dictionary mapping app names to lists of results
        """
        grouped_results = {}
        
        for result in results:
            app_name = result.get('app_name')
            if app_name:
                if app_name not in grouped_results:
                    grouped_results[app_name] = []
                grouped_results[app_name].append(result)
        
        return grouped_results
    
    def compare_configurations(self, results: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Compare metrics across different configurations.
        
        Args:
            results: List of result data
            
        Returns:
            Dictionary with configuration comparison data
        """
        comparisons = {}
        
        # Group results by configuration
        grouped_by_config = self.group_results_by_config(results)
        
        # Calculate average metrics for each configuration
        for config_id, config_results in grouped_by_config.items():
            # Extract metrics
            metrics_list = [r.get('metrics', {}) for r in config_results]
            
            # Calculate averages
            avg_metrics = {}
            for key in ['avg_method_coverage', 'avg_activity_coverage', 'avg_mop_method_coverage', 
                        'avg_execution_time', 'overall_score']:
                values = [m.get(key, 0) for m in metrics_list if key in m]
                avg_metrics[key] = sum(values) / len(values) if values else 0
            
            # Count apps and errors
            app_count = len(set(r.get('app_name', '') for r in config_results))
            error_count = sum(m.get('failed_tests', 0) for m in metrics_list)
            
            # Store comparison data
            comparisons[config_id] = {
                'avg_metrics': avg_metrics,
                'app_count': app_count,
                'error_count': error_count,
                'result_count': len(config_results)
            }
        
        return comparisons
    
    def load_test_results(self, result_dirs: Optional[List[str]] = None) -> List[TestResult]:
        """
        Load raw TestResult objects from specified directories.
        
        This method loads the original TestResult objects needed for advanced analysis
        such as batch strategy analysis.
        
        Args:
            result_dirs: List of result directory paths. If None, discover results.
            
        Returns:
            List of TestResult objects
        """
        if result_dirs is None:
            result_dirs = self.discover_results()
        
        test_results = []
        
        for result_dir in result_dirs:
            try:
                # Look for test_suite_config.json
                config_file = os.path.join(result_dir, "test_suite_config.json")
                if not os.path.exists(config_file):
                    self.logger.warning(f"No test suite configuration found in {result_dir}")
                    continue
                
                # Load test suite configuration
                with open(config_file, 'r') as f:
                    test_suite_data = json.load(f)
                
                # Create TestSuite object
                test_suite = TestSuite.from_dict(test_suite_data)
                
                # Look for result directories
                app_result_dirs = []
                for item in os.listdir(result_dir):
                    item_path = os.path.join(result_dir, item)
                    if os.path.isdir(item_path) and not item.startswith('.'):
                        app_result_dirs.append(item_path)
                
                # Process each result directory
                for app_dir in app_result_dirs:
                    dir_name = os.path.basename(app_dir)
                    
                    # Try to extract test case info from directory name
                    parts = dir_name.split('_')
                    if len(parts) < 3:
                        continue
                    
                    app_name = parts[0]
                    config_id = '_'.join(parts[1:])
                    
                    # Find the matching tool configuration
                    tool_config = None
                    for config in test_suite.tool_configurations:
                        if config.get_id() == config_id:
                            tool_config = config
                            break
                    
                    if not tool_config:
                        self.logger.warning(f"Configuration not found for {config_id}")
                        continue
                    
                    # Find the app path
                    app_path = None
                    for app in test_suite.apps:
                        if app_name in app:
                            app_path = app
                            break
                    
                    if not app_path:
                        self.logger.warning(f"App path not found for {app_name}")
                        # Use a placeholder
                        app_path = f"/path/to/{app_name}.apk"
                    
                    # Create test case
                    test_case = TestCase(
                        app_path=app_path,
                        tool_config=tool_config,
                        result_dir=app_dir
                    )
                    
                    # Look for result.json
                    result_file = os.path.join(app_dir, "result.json")
                    if not os.path.exists(result_file):
                        self.logger.warning(f"No result file found in {app_dir}")
                        continue
                    
                    # Load result data
                    with open(result_file, 'r') as f:
                        result_data = json.load(f)
                    
                    # Create TestResult object
                    result = TestResult(
                        test_case=test_case,
                        status=result_data.get("status", "unknown"),
                        execution_time=result_data.get("execution_time", 0),
                        start_time=result_data.get("start_time", ""),
                        end_time=result_data.get("end_time", ""),
                        error_message=result_data.get("error_message", ""),
                        output_dir=app_dir
                    )
                    
                    # Load coverage data if available
                    coverage_file = os.path.join(app_dir, "coverage_data.json")
                    if os.path.exists(coverage_file):
                        with open(coverage_file, 'r') as f:
                            result.coverage_data = json.load(f)
                    
                    # Load error data if available
                    error_file = os.path.join(app_dir, "error_data.json")
                    if os.path.exists(error_file):
                        with open(error_file, 'r') as f:
                            result.error_data = json.load(f)
                    
                    # Look for batch metrics
                    batch_file = os.path.join(app_dir, "batch_metrics.json")
                    if os.path.exists(batch_file):
                        with open(batch_file, 'r') as f:
                            result.batch_metrics = json.load(f)
                    
                    test_results.append(result)
                    
            except Exception as e:
                self.logger.error(f"Error loading test results from {result_dir}: {str(e)}")
        
        self.logger.info(f"Loaded {len(test_results)} test results")
        return test_results
    
    def load_and_analyze(self, result_dirs: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Load and analyze results from specified directories.
        
        Args:
            result_dirs: List of result directory paths. If None, discover results.
            
        Returns:
            Dictionary with analysis results
        """
        # Load results
        analysis_data = self.load_results(result_dirs)
        
        # No results found
        if not analysis_data:
            return {"status": "No results found"}
        
        # Reconstruct results
        reconstructed_results = self.reconstruct_results(analysis_data)
        
        # Group results
        by_config = self.group_results_by_config(reconstructed_results)
        by_app = self.group_results_by_app(reconstructed_results)
        
        # Compare configurations
        comparisons = self.compare_configurations(reconstructed_results)
        
        # Identify top configurations
        top_configs = {}
        for metric in ['avg_method_coverage', 'avg_activity_coverage', 'avg_mop_method_coverage', 'overall_score']:
            sorted_configs = sorted(
                comparisons.items(),
                key=lambda x: x[1]['avg_metrics'].get(metric, 0),
                reverse=(metric != 'avg_execution_time')
            )
            top_configs[metric] = [config_id for config_id, _ in sorted_configs[:5]]
        
        # Create analysis result
        result = {
            "timestamp": datetime.now().isoformat(),
            "total_results": len(reconstructed_results),
            "total_configs": len(by_config),
            "total_apps": len(by_app),
            "top_configurations": top_configs,
            "configuration_comparisons": comparisons
        }
        
        return result


# Convenient functions
def load_results(result_dirs: Optional[List[str]] = None, base_dir: str = "test_results") -> Dict[str, Any]:
    """
    Load and analyze results from previous test runs.
    
    Args:
        result_dirs: List of result directory paths. If None, discover results.
        base_dir: Base directory for test results
        
    Returns:
        Dictionary with analysis results
    """
    loader = ResultsLoader(base_dir)
    return loader.load_and_analyze(result_dirs)