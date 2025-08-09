# rv_evaluator/export.py
"""
Simplified results export for LLM evaluations.

Generates only three essential reports:
1. detailed_results.csv - Raw data from each execution
2. summary_by_config.csv - Aggregated stats per configuration  
3. summary_by_model.csv - Aggregated stats per model

This focused approach eliminates report proliferation while providing
all necessary data for analysis and decision-making.
"""

import os
import pandas as pd
from typing import Dict, List, Any, Tuple

from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager


class ResultsExporter:
    """
    Exports evaluation results to three essential CSV files.
    
    Provides a clean, focused approach to result reporting without
    generating unnecessary duplicate files.
    """

    def __init__(self, output_dir: str = "."):
        """
        Initialize the ResultsExporter.

        Args:
            output_dir: Directory for output files
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_evaluator.export",
            {CONTEXT_COMPONENT: "ResultsExporter"}
        )

    def export_all_results(self,
                           detailed_results: List[Dict[str, Any]],
                           summary_results: List[Dict[str, Any]]) -> Tuple[str, str, str]:
        """
        Export all evaluation results to three essential files.

        Args:
            detailed_results: Individual run results
            summary_results: Configuration summaries

        Returns:
            Tuple of (detailed_file, summary_config_file, summary_model_file)
        """
        self.logger.info("Exporting evaluation results to 3 essential files")

        detailed_path = self._export_detailed_results(detailed_results)
        summary_config_path = self._export_summary_by_config(summary_results)
        summary_model_path = self._export_summary_by_model(summary_results)

        self.logger.info("Export completed")
        self.logger.info(f"  📊 Detailed:      {detailed_path}")
        self.logger.info(f"  📈 By Config:     {summary_config_path}")
        self.logger.info(f"  📋 By Model:      {summary_model_path}")

        return detailed_path, summary_config_path, summary_model_path

    def _export_detailed_results(self, results: List[Dict[str, Any]]) -> str:
        """
        Export detailed run-by-run results.

        Args:
            results: Individual run results

        Returns:
            Path to detailed results file
        """
        file_path = os.path.join(self.output_dir, "detailed_results.csv")
        self.logger.info(f"Exporting {len(results)} detailed results")

        if not results:
            # Create empty file with headers
            pd.DataFrame().to_csv(file_path, index=False)
            return file_path

        df = pd.DataFrame(results)
        
        # Define preferred column order for readability
        preferred_columns = [
            # Configuration identifiers
            'model', 'prompt_id', 'run_number', 'temperature', 'top_p', 'max_tokens', 'top_k',
            
            # Success metrics
            'success', 'error_occurred', 'timeout_occurred', 'error_type',
            
            # Core performance metrics
            'total_duration_ms', 'tokens_per_second', 'input_tokens', 'output_tokens', "load_duration_ms",
            "input_tokens_duration_ms", "output_tokens_duration_ms",
            
            # Timing
            'execution_time_s'
        ]
        
        # Arrange columns: preferred first, then any remaining
        available_columns = [col for col in preferred_columns if col in df.columns]
        remaining_columns = [col for col in df.columns if col not in available_columns]
        column_order = available_columns + remaining_columns
        
        df = df.reindex(columns=column_order)
        df.to_csv(file_path, index=False)

        return file_path

    def _export_summary_by_config(self, results: List[Dict[str, Any]]) -> str:
        """
        Export summary statistics by configuration.
        
        Each row represents a unique configuration (model + temperature + prompt).

        Args:
            results: Configuration summary results

        Returns:
            Path to summary by config file
        """
        file_path = os.path.join(self.output_dir, "summary_by_config.csv")
        self.logger.info(f"Exporting {len(results)} configuration summaries")

        if not results:
            pd.DataFrame().to_csv(file_path, index=False)
            return file_path

        # Flatten nested statistics
        flattened_results = self._flatten_summary_results(results)
        df = pd.DataFrame(flattened_results)
        
        # Sort by overall score (best first)
        if 'overall_score' in df.columns:
            df = df.sort_values('overall_score', ascending=False)
        
        # Define essential columns for config-level summary
        essential_columns = [
            # Configuration identifiers
            'model', 'prompt_id', 'temperature', 'top_p', 'max_tokens', 'top_k',
            
            # Key metrics
            'overall_score', 'success_rate', 'total_runs',
            
            # Performance stats
            'tokens_per_second_mean', 'tokens_per_second_std_dev',
            'total_duration_ms_mean', 'total_duration_ms_std_dev',
            
            # Token usage
            'input_tokens_mean', 'output_tokens_mean',
            
            # Error rates
            'error_rate', 'timeout_rate'
        ]
        
        # Keep only available essential columns
        df_filtered = df[[col for col in essential_columns if col in df.columns]]
        df_filtered.to_csv(file_path, index=False)

        return file_path

    def _export_summary_by_model(self, results: List[Dict[str, Any]]) -> str:
        """
        Export summary statistics aggregated by model.
        
        Each row represents a model with averages across all its configurations.

        Args:
            results: Configuration summary results

        Returns:
            Path to summary by model file
        """
        file_path = os.path.join(self.output_dir, "summary_by_model.csv")
        
        if not results:
            pd.DataFrame().to_csv(file_path, index=False)
            return file_path

        # Group results by model
        flattened_results = self._flatten_summary_results(results)
        df = pd.DataFrame(flattened_results)
        
        if df.empty:
            df.to_csv(file_path, index=False)
            return file_path

        # Group by model and calculate averages
        model_summaries = []
        
        for model in df['model'].unique():
            model_data = df[df['model'] == model]
            
            model_summary = {
                'model': model,
                'total_configurations': len(model_data),
                'total_runs': model_data['total_runs'].sum() if 'total_runs' in model_data else 0,
            }
            
            # Average key metrics across configurations
            numeric_metrics = [
                'overall_score', 'success_rate', 'tokens_per_second_mean',
                'total_duration_ms_mean', 'input_tokens_mean', 'output_tokens_mean',
                'error_rate', 'timeout_rate'
            ]
            
            for metric in numeric_metrics:
                if metric in model_data.columns:
                    model_summary[f'{metric}_avg'] = model_data[metric].mean()
                else:
                    model_summary[f'{metric}_avg'] = 0.0
            
            model_summaries.append(model_summary)
        
        # Create DataFrame and sort by average overall score
        model_df = pd.DataFrame(model_summaries)
        if 'overall_score_avg' in model_df.columns:
            model_df = model_df.sort_values('overall_score_avg', ascending=False)
        
        model_df.to_csv(file_path, index=False)
        self.logger.info(f"Exported summaries for {len(model_summaries)} models")

        return file_path

    def _flatten_summary_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Flatten nested statistics dictionaries.

        Converts {"metric": {"mean": 10, "std_dev": 2}} to {"metric_mean": 10, "metric_std_dev": 2}

        Args:
            results: Summary results with nested statistics

        Returns:
            Flattened dictionaries
        """
        flattened = []
        
        for result in results:
            flat_result = {}
            
            for key, value in result.items():
                if isinstance(value, dict):
                    # Flatten nested statistics
                    for stat_key, stat_value in value.items():
                        flat_result[f"{key}_{stat_key}"] = stat_value
                else:
                    flat_result[key] = value
                    
            flattened.append(flat_result)
            
        return flattened