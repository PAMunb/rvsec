"""
Exporters module for test framework.

This module provides functionality for exporting test
results to various formats such as CSV and Excel.

The exports include comprehensive metrics for monitoring-oriented programming (MOP)
and monitored operations, providing detailed insights into specification violations
and coverage across different testing configurations.
"""

import os
import csv
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager


def export_to_csv(results: Dict[str, Any], output_path: str) -> bool:
    """
    Export analysis results to CSV format.
    
    Args:
        results: Analysis results dictionary
        output_path: Path to save the CSV file
        
    Returns:
        True if export succeeded, False otherwise
    """
    logger = LoggingManager.get_instance().get_logger(
        'test_framework.exporters',
        {CONTEXT_COMPONENT: 'CSVExporter'}
    )
    
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Extract configuration comparisons
        comparisons = results.get('configuration_comparisons', {})
        
        # No data to export
        if not comparisons:
            logger.warning("No configuration comparison data to export")
            return False
            
        # Prepare CSV header
        header = [
            'configuration_id', 'result_count', 'app_count', 'error_count',
            'avg_method_coverage', 'avg_activity_coverage', 'avg_mop_method_coverage',
            'avg_mop_error_count', 'avg_mop_unique_errors', 'avg_monitored_operations_triggered',
            'avg_monitored_operations_ratio', 'avg_execution_time', 'overall_score'
        ]
        
        # Prepare CSV data
        csv_data = []
        for config_id, data in comparisons.items():
            row = {
                'configuration_id': config_id,
                'result_count': data.get('result_count', 0),
                'app_count': data.get('app_count', 0),
                'error_count': data.get('error_count', 0)
            }
            
            # Add average metrics
            avg_metrics = data.get('avg_metrics', {})
            for metric in ['avg_method_coverage', 'avg_activity_coverage', 'avg_mop_method_coverage',
                          'avg_mop_error_count', 'avg_mop_unique_errors', 'avg_monitored_operations_triggered',
                          'avg_monitored_operations_ratio', 'avg_execution_time', 'overall_score']:
                row[metric] = avg_metrics.get(metric, 0)
                
            csv_data.append(row)
            
        # Write to CSV
        with open(output_path, 'w', newline='') as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=header)
            writer.writeheader()
            writer.writerows(csv_data)
            
        logger.info(f"Exported {len(csv_data)} rows to {output_path}")
        return True
    except Exception as e:
        logger.error(f"Error exporting to CSV: {str(e)}")
        return False


def export_to_excel(results: Dict[str, Any], output_path: str) -> bool:
    """
    Export analysis results to Excel format.
    
    Args:
        results: Analysis results dictionary
        output_path: Path to save the Excel file
        
    Returns:
        True if export succeeded, False otherwise
    """
    logger = LoggingManager.get_instance().get_logger(
        'test_framework.exporters',
        {CONTEXT_COMPONENT: 'ExcelExporter'}
    )
    
    try:
        # Check for pandas and openpyxl
        import pandas as pd
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Extract comparisons
        comparisons = results.get('configuration_comparisons', {})
        
        # No data to export
        if not comparisons:
            logger.warning("No configuration comparison data to export")
            return False
            
        # Prepare Excel data
        excel_data = []
        for config_id, data in comparisons.items():
            row = {
                'configuration_id': config_id,
                'result_count': data.get('result_count', 0),
                'app_count': data.get('app_count', 0),
                'error_count': data.get('error_count', 0)
            }
            
            # Add average metrics
            avg_metrics = data.get('avg_metrics', {})
            for metric in ['avg_method_coverage', 'avg_activity_coverage', 'avg_mop_method_coverage',
                          'avg_mop_error_count', 'avg_mop_unique_errors', 'avg_monitored_operations_triggered',
                          'avg_monitored_operations_ratio', 'avg_execution_time', 'overall_score']:
                row[metric] = avg_metrics.get(metric, 0)
                
            excel_data.append(row)
            
        # Convert to DataFrame
        df = pd.DataFrame(excel_data)
        
        # Create a writer with formatting
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Write the data
            df.to_excel(writer, sheet_name='Configuration Comparison', index=False)
            
            # Add summary sheet
            summary_data = {
                'Metric': ['Total Configurations', 'Total Applications', 'Total Results', 'Timestamp'],
                'Value': [
                    results.get('total_configs', 0),
                    results.get('total_apps', 0),
                    results.get('total_results', 0),
                    results.get('timestamp', datetime.now().isoformat())
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Add top configurations sheet
            top_configs = results.get('top_configurations', {})
            top_data = []
            
            for metric, configs in top_configs.items():
                for i, config_id in enumerate(configs[:5], 1):
                    comparison = comparisons.get(config_id, {})
                    value = comparison.get('avg_metrics', {}).get(metric, 0)
                    
                    top_data.append({
                        'Metric': metric,
                        'Rank': i,
                        'Configuration': config_id,
                        'Value': value
                    })
                    
            if top_data:
                top_df = pd.DataFrame(top_data)
                top_df.to_excel(writer, sheet_name='Top Configurations', index=False)
            
        logger.info(f"Exported {len(excel_data)} configurations to {output_path}")
        return True
    except ImportError:
        logger.error("Required packages not found. Install pandas and openpyxl for Excel export.")
        return False
    except Exception as e:
        logger.error(f"Error exporting to Excel: {str(e)}")
        return False