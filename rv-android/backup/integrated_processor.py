"""
Integrated processor module for combining static and dynamic analysis results.

This module provides a processor that integrates static analysis data with
runtime coverage data to generate comprehensive metrics for instrumented apps.
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Set, Union

from rvandroid.analysis.results.integrated_metrics import (
    IntegratedMetricsCalculator, IntegratedAnalysisResult, 
    StaticAnalysisMetrics, IntegratedCoverageMetrics, SecurityMetrics
)
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.domain.coverage import LogcatRepository
from rvandroid.parser.log.logcat_parser import parse_logcat_file
from rvandroid.parser.static.static_analysis_parser import StaticAnalysisParser
from rvandroid.util.logging.constants import CONTEXT_COMPONENT, CONTEXT_PHASE
from rvandroid.util.logging.manager import LoggingManager


class IntegratedResultsProcessor:
    """
    Processor for integrating static and dynamic analysis results.
    
    Combines data from static analysis tools (GESDA, GATOR, REACH) with
    runtime coverage data from logcat logs to generate comprehensive metrics
    for instrumented applications.
    
    ### Architectural Decisions:
    - Separates integrated processing from standard results processing
    - Provides specialized handling for static analysis integration
    - Enables detailed security and coverage analysis
    - Supports batch processing across multiple applications
    
    ### Role in the System:
    - Integrates static and dynamic analysis data
    - Generates comprehensive metrics for instrumented apps
    - Provides security-focused analysis and reporting
    - Facilitates evaluation of runtime verification effectiveness
    """
    
    def __init__(self):
        """Initialize the integrated results processor."""
        self.logger = LoggingManager.get_instance().get_logger(
            'analysis.results.integrated_processor',
            {CONTEXT_COMPONENT: 'IntegratedResultsProcessor'}
        )
        self.results = {}  # app_id -> IntegratedAnalysisResult
        
    def process_results(self, results_dir: str, output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Process experiment results from a directory.
        
        Args:
            results_dir: Directory containing results
            output_file: Optional path for output file
            
        Returns:
            Dictionary with processing summary
        """
        self.logger.info(f"Processing integrated results from {results_dir}")
        
        # Ensure directory exists
        if not os.path.exists(results_dir):
            self.logger.error(f"Results directory not found: {results_dir}")
            return {"error": "Results directory not found"}
        
        try:
            # Process app directories
            app_dirs = [d for d in os.listdir(results_dir)
                        if os.path.isdir(os.path.join(results_dir, d)) 
                        and d not in ["logs", "charts"]]
            
            # Process each app directory
            for app_dir in app_dirs:
                app_path = os.path.join(results_dir, app_dir)
                app_id = app_dir
                
                # Process app results
                self._process_app_directory(app_path, app_id)
            
            # Save results to file if specified
            if output_file:
                output_path = output_file
            else:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = os.path.join(results_dir, f"integrated_results_{timestamp}.json")
                
            self._save_results(output_path)
            
            return {
                "output_path": output_path,
                "app_count": len(self.results),
                "success": True
            }
            
        except Exception as e:
            self.logger.error(f"Error processing integrated results: {str(e)}", exc_info=True)
            return {
                "error": str(e),
                "success": False
            }
    
    def _process_app_directory(self, app_dir: str, app_id: str) -> None:
        """
        Process a single app directory.
        
        Args:
            app_dir: App directory path
            app_id: App identifier
        """
        logger = LoggingManager.get_instance().get_logger(
            'analysis.results.integrated_processor',
            {
                CONTEXT_COMPONENT: 'IntegratedResultsProcessor',
                CONTEXT_PHASE: 'process_app_directory',
                'app_dir': app_dir
            }
        )
        
        try:
            # Find logcat files
            logcat_files = [f for f in os.listdir(app_dir) if f.endswith(".logcat")]
            
            # Find static analysis files
            gesda_file = os.path.join(app_dir, f"{app_id}.gesda")
            gator_file = os.path.join(app_dir, f"{app_id}.wtg")
            reach_file = os.path.join(app_dir, f"{app_id}.reach")
            
            static_data = None
            
            # Parse static analysis files if they exist
            if all(os.path.exists(f) for f in [gesda_file, gator_file, reach_file]):
                logger.info(f"Found static analysis files for {app_id}")
                parser = StaticAnalysisParser()
                
                try:
                    static_data = parser.parse_all(
                        None,  # App object not needed for parsing
                        gesda_file,
                        gator_file,
                        reach_file
                    )
                    logger.info(f"Successfully parsed static analysis data for {app_id}")
                except Exception as e:
                    logger.warning(f"Error parsing static analysis files for {app_id}: {str(e)}")
            else:
                logger.info(f"Static analysis files not found for {app_id}")
                
            # Create metrics calculator
            metrics_calculator = IntegratedMetricsCalculator(app_id)
            
            # Set static data if available
            if static_data:
                metrics_calculator.set_static_data(static_data)
                
            # Process logcat files
            if not logcat_files:
                logger.warning(f"No logcat files found in {app_dir}")
                
                # If we have static data, we can still generate metrics
                if static_data:
                    # Calculate metrics with static data only
                    result = metrics_calculator.calculate_metrics()
                    self.results[app_id] = result
                    
                return
                
            # Choose the most recent logcat file (or a specific tool's logcat)
            # For now, we'll just use the first one
            logcat_file = os.path.join(app_dir, logcat_files[0])
            
            # Parse logcat file
            try:
                logcat_data = parse_logcat_file(logcat_file)
                logger.info(f"Successfully parsed logcat data from {logcat_file}")
                
                # Set logcat data
                metrics_calculator.set_logcat_data(logcat_data)
                
                # Calculate integrated metrics
                result = metrics_calculator.calculate_metrics()
                self.results[app_id] = result
                
            except Exception as e:
                logger.warning(f"Error parsing logcat file {logcat_file}: {str(e)}")
                
                # If we have static data, we can still generate metrics
                if static_data:
                    # Calculate metrics with static data only
                    result = metrics_calculator.calculate_metrics()
                    self.results[app_id] = result
                
        except Exception as e:
            logger.error(f"Error processing app directory {app_dir}: {str(e)}", exc_info=True)
    
    def _save_results(self, output_path: str) -> None:
        """
        Save results to a JSON file.
        
        Args:
            output_path: Path to save results
        """
        try:
            # Create directories if they don't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Prepare data for serialization
            data = {
                "timestamp": datetime.now().isoformat(),
                "app_count": len(self.results),
                "apps": {}
            }
            
            # Add app results
            for app_id, result in self.results.items():
                data["apps"][app_id] = result.to_dict()
                
            # Write to file
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)
                
            self.logger.info(f"Saved integrated results to {output_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving integrated results: {str(e)}", exc_info=True)
    
    def get_results(self) -> Dict[str, IntegratedAnalysisResult]:
        """
        Get all integrated analysis results.
        
        Returns:
            Dictionary mapping app_id to IntegratedAnalysisResult
        """
        return self.results


# Convenience function
def process_integrated_results(results_dir: str, output_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Process integrated results from a directory.
    
    This is a convenience function that creates an IntegratedResultsProcessor
    instance and calls its process_results method.
    
    Args:
        results_dir: Directory containing results
        output_file: Optional path for output file
        
    Returns:
        Dictionary with processing summary
    """
    processor = IntegratedResultsProcessor()
    return processor.process_results(results_dir, output_file)