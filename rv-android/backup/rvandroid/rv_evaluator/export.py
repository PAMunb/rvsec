# rvandroid/llm/evaluator/export.py
"""
Export system for LLM evaluation results and analysis.

This module handles the export of evaluation results to CSV files and
generates comprehensive analysis reports in Markdown format.

### Architectural Decisions:
- Implements comprehensive export functionality for evaluation results
- Provides both detailed and summary data views for analysis
- Generates automated analysis reports with insights and recommendations
- Supports CSV format for easy data manipulation and universal compatibility
- Creates structured Markdown reports for documentation and sharing

### Role in the System:
- Acts as the primary export interface for evaluation results
- Transforms collected metrics into structured output formats
- Generates analytical insights and recommendations
- Provides data export capabilities for external analysis
- Creates documentation artifacts for evaluation results

### Key Considerations:
- Uses CSV format for maximum compatibility and simplicity
- Provides clear data structure and formatting for readability
- Generates actionable insights from statistical analysis
- Supports both technical and summary reporting formats
- Maintains data integrity during export operations
"""

import os
import pandas as pd
from typing import Dict, List, Any, Tuple
from datetime import datetime

from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class ResultsExporter:
    """
    Handles export of evaluation results to CSV and analysis generation.

    Provides comprehensive export functionality including detailed results,
    summary statistics, and automated analysis report generation.
    """

    def __init__(self, output_dir: str = "."):
        """
        Initialize the results exporter.

        Args:
            output_dir: Directory for output files
        """
        self.output_dir = output_dir

        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)

        # Set up logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "llm.evaluator.export",
            {CONTEXT_COMPONENT: "ResultsExporter"}
        )

    def export_all_results(self,
                           detailed_results: List[Dict[str, Any]],
                           summary_results: List[Dict[str, Any]]) -> Tuple[str, str, str]:
        """
        Export all evaluation results including detailed data, summary, and analysis.

        Args:
            detailed_results: List of individual run results
            summary_results: List of aggregated configuration summaries

        Returns:
            Tuple of (detailed_file_path, summary_file_path, analysis_file_path)
        """
        self.logger.info("Starting export of evaluation results")

        # Export detailed results to CSV
        detailed_path = self.export_detailed_results(detailed_results)

        # Export summary results to CSV
        summary_path = self.export_summary_results(summary_results)

        # Generate analysis report
        analysis_path = self.generate_analysis_report(summary_results, detailed_results)

        self.logger.info(f"Export completed. Files generated:")
        self.logger.info(f"  Detailed: {detailed_path}")
        self.logger.info(f"  Summary: {summary_path}")
        self.logger.info(f"  Analysis: {analysis_path}")

        return detailed_path, summary_path, analysis_path

    def export_detailed_results(self, results: List[Dict[str, Any]]) -> str:
        """
        Export detailed results to CSV file.

        Args:
            results: List of individual run results

        Returns:
            Path to exported file
        """
        file_path = os.path.join(self.output_dir, "detailed_results.csv")

        self.logger.info(f"Exporting {len(results)} detailed results to {file_path}")

        # Convert to DataFrame
        df = pd.DataFrame(results)

        # Reorder columns for better readability
        column_order = self._get_detailed_column_order(df.columns.tolist())
        df = df.reindex(columns=column_order)

        # Export to CSV
        df.to_csv(file_path, index=False)

        return file_path

    def export_summary_results(self, results: List[Dict[str, Any]]) -> str:
        """
        Export summary results to CSV files.

        Args:
            results: List of configuration summaries

        Returns:
            Path to main summary file
        """
        main_file_path = os.path.join(self.output_dir, "summary_results.csv")

        self.logger.info(f"Exporting {len(results)} summary results to {main_file_path}")

        # Flatten nested statistics for DataFrame
        flattened_results = self._flatten_summary_results(results)

        # Convert to DataFrame
        df = pd.DataFrame(flattened_results)

        # Sort by overall score (descending)
        if 'overall_score' in df.columns:
            df = df.sort_values('overall_score', ascending=False)

        # Export main summary CSV
        df.to_csv(main_file_path, index=False)

        # Export additional CSV files for different views
        self._create_additional_csv_files(df)

        return main_file_path

    def _create_additional_csv_files(self, df: pd.DataFrame) -> None:
        """
        Create additional CSV files for different data views.

        Args:
            df: Summary DataFrame
        """
        # Top configurations CSV
        if len(df) > 0:
            top_configs_path = os.path.join(self.output_dir, "top_10_configurations.csv")
            top_configs = df.head(10)
            top_configs.to_csv(top_configs_path, index=False)
            self.logger.info(f"Created top configurations file: {top_configs_path}")

        # Rankings by specific metrics
        ranking_metrics = [
            ('tokens_per_second_mean', 'tokens_per_second_ranking.csv'),
            ('generation_latency_ms_mean', 'latency_ranking.csv'),
            ('parsing_success_rate', 'parsing_success_ranking.csv'),
            ('explanation_quality_score_mean', 'quality_ranking.csv'),
            ('overall_success_rate', 'success_rate_ranking.csv')
        ]

        for metric_col, filename in ranking_metrics:
            if metric_col in df.columns:
                # Sort by metric (ascending for latency, descending for others)
                ascending = 'latency' in metric_col.lower()
                ranked_df = df.sort_values(metric_col, ascending=ascending)

                # Select relevant columns for ranking
                ranking_cols = ['model', 'strategy', 'prompt_id', metric_col, 'overall_score']
                ranking_cols = [col for col in ranking_cols if col in ranked_df.columns]

                ranking_path = os.path.join(self.output_dir, filename)
                ranked_df[ranking_cols].head(15).to_csv(ranking_path, index=False)
                self.logger.debug(f"Created ranking file: {ranking_path}")

    def generate_analysis_report(self,
                                 summary_results: List[Dict[str, Any]],
                                 detailed_results: List[Dict[str, Any]]) -> str:
        """
        Generate comprehensive analysis report in Markdown format.

        Args:
            summary_results: List of configuration summaries
            detailed_results: List of individual run results

        Returns:
            Path to generated analysis report
        """
        file_path = os.path.join(self.output_dir, "analysis_report.md")

        self.logger.info(f"Generating analysis report: {file_path}")

        # Create analysis content
        report_content = self._create_analysis_content(summary_results, detailed_results)

        # Write to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(report_content)

        return file_path

    def _get_detailed_column_order(self, columns: List[str]) -> List[str]:
        """
        Define column order for detailed results export.

        Args:
            columns: List of available columns

        Returns:
            Ordered list of columns
        """
        # Define preferred order
        preferred_order = [
            # Configuration columns
            'model', 'strategy', 'prompt_id', 'run_number',
            'temperature', 'top_p', 'max_tokens', 'top_k',

            # Success metrics
            'parsing_success', 'error_occurred', 'timeout_occurred',
            'actions_count', 'error_type',

            # Performance metrics
            'total_duration_ms', 'generation_latency_ms', 'tokens_per_second',
            'input_tokens', 'output_tokens', 'input_output_ratio',

            # Quality metrics
            'response_length_chars', 'explanation_quality_score',

            # Detailed performance
            'load_duration_ms', 'input_tokens_duration_ms', 'output_tokens_duration_ms'
        ]

        # Add any remaining columns not in preferred order
        ordered_columns = []
        for col in preferred_order:
            if col in columns:
                ordered_columns.append(col)

        for col in columns:
            if col not in ordered_columns:
                ordered_columns.append(col)

        return ordered_columns

    def _flatten_summary_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Flatten nested statistics dictionaries for DataFrame export.

        Args:
            results: List of summary results with nested statistics

        Returns:
            List of flattened dictionaries
        """
        flattened = []

        for result in results:
            flat_result = {}

            # Copy configuration values
            config_keys = ['model', 'strategy', 'prompt_id', 'temperature', 'top_p', 'max_tokens', 'top_k']
            for key in config_keys:
                if key in result:
                    flat_result[key] = result[key]

            # Flatten statistics
            for key, value in result.items():
                if key in config_keys:
                    continue

                if isinstance(value, dict):
                    # Flatten nested statistics
                    for stat_key, stat_value in value.items():
                        flat_key = f"{key}_{stat_key}"
                        flat_result[flat_key] = stat_value
                else:
                    flat_result[key] = value

            flattened.append(flat_result)

        return flattened

    def _create_analysis_content(self,
                                 summary_results: List[Dict[str, Any]],
                                 detailed_results: List[Dict[str, Any]]) -> str:
        """
        Create comprehensive analysis report content.

        Args:
            summary_results: Configuration summaries
            detailed_results: Individual run results

        Returns:
            Markdown formatted analysis report
        """
        # Sort summary results by overall score
        sorted_summaries = sorted(summary_results,
                                  key=lambda x: x.get('overall_score', 0),
                                  reverse=True)

        # Generate report sections
        sections = [
            self._create_header_section(),
            self._create_executive_summary(sorted_summaries),
            self._create_ranking_section(sorted_summaries),
            self._create_metric_analysis(sorted_summaries),
            self._create_pattern_analysis(sorted_summaries, detailed_results),
            self._create_recommendations(sorted_summaries),
            self._create_files_section(),
            self._create_appendix_section(sorted_summaries, detailed_results)
        ]

        return '\n\n'.join(sections)

    def _create_header_section(self) -> str:
        """Create report header section."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return f"""# LLM Evaluation Analysis Report

**Generated:** {timestamp}

This report provides a comprehensive analysis of LLM model configurations evaluated for Android testing action generation. The evaluation compared different models, strategies, and parameters across multiple prompt scenarios.

---"""

    def _create_executive_summary(self, sorted_summaries: List[Dict[str, Any]]) -> str:
        """Create executive summary section."""
        if not sorted_summaries:
            return "## Executive Summary\n\nNo evaluation results available."

        total_configs = len(sorted_summaries)
        best_config = sorted_summaries[0]

        # Calculate averages
        avg_success_rate = sum(config.get('overall_success_rate', 0) for config in sorted_summaries) / total_configs
        avg_score = sum(config.get('overall_score', 0) for config in sorted_summaries) / total_configs

        return f"""## Executive Summary

- **Total Configurations Evaluated:** {total_configs}
- **Average Success Rate:** {avg_success_rate:.1%}
- **Average Overall Score:** {avg_score:.1f}/100

### Best Performing Configuration
- **Model:** {best_config.get('model', 'Unknown')}
- **Strategy:** {best_config.get('strategy', 'Unknown')}
- **Temperature:** {best_config.get('temperature', 'Unknown')}
- **Overall Score:** {best_config.get('overall_score', 0):.1f}/100
- **Success Rate:** {best_config.get('overall_success_rate', 0):.1%}

The evaluation reveals significant performance variations across different configurations, with clear winners emerging based on success rates, response quality, and generation speed."""

    def _create_ranking_section(self, sorted_summaries: List[Dict[str, Any]]) -> str:
        """Create overall ranking section."""
        content = ["## Overall Configuration Rankings"]

        for i, config in enumerate(sorted_summaries[:10], 1):
            model = config.get('model', 'Unknown')
            strategy = config.get('strategy', 'Unknown')
            temp = config.get('temperature', 'Unknown')
            score = config.get('overall_score', 0)
            success_rate = config.get('overall_success_rate', 0)

            content.append(f"**{i}. {model} | {strategy} | T={temp}**")
            content.append(f"   - Overall Score: {score:.1f}/100")
            content.append(f"   - Success Rate: {success_rate:.1%}")
            content.append("")

        return '\n'.join(content)

    def _create_metric_analysis(self, sorted_summaries: List[Dict[str, Any]]) -> str:
        """Create detailed metric analysis section."""
        if not sorted_summaries:
            return "## Metric Analysis\n\nNo data available for analysis."

        content = ["## Detailed Metric Analysis"]

        # Performance analysis
        content.append("### Performance Metrics")
        self._analyze_performance_metrics(sorted_summaries, content)

        # Quality analysis
        content.append("\n### Quality Metrics")
        self._analyze_quality_metrics(sorted_summaries, content)

        # Reliability analysis
        content.append("\n### Reliability Metrics")
        self._analyze_reliability_metrics(sorted_summaries, content)

        return '\n'.join(content)

    def _analyze_performance_metrics(self, summaries: List[Dict[str, Any]], content: List[str]) -> None:
        """Analyze performance-related metrics."""
        # Find best performers for speed
        speed_ranking = sorted(summaries,
                               key=lambda x: x.get('tokens_per_second', {}).get('mean', 0),
                               reverse=True)

        if speed_ranking:
            fastest = speed_ranking[0]
            content.append(
                f"- **Fastest Generation:** {fastest.get('model')} ({fastest.get('tokens_per_second', {}).get('mean', 0):.1f} tokens/sec)")

        # Find lowest latency
        latency_ranking = sorted(summaries,
                                 key=lambda x: x.get('generation_latency_ms', {}).get('mean', float('inf')))

        if latency_ranking:
            lowest_latency = latency_ranking[0]
            content.append(
                f"- **Lowest Latency:** {lowest_latency.get('model')} ({lowest_latency.get('generation_latency_ms', {}).get('mean', 0):.0f}ms)")

    def _analyze_quality_metrics(self, summaries: List[Dict[str, Any]], content: List[str]) -> None:
        """Analyze quality-related metrics."""
        # Find best explanation quality
        quality_ranking = sorted(summaries,
                                 key=lambda x: x.get('explanation_quality_score', {}).get('mean', 0),
                                 reverse=True)

        if quality_ranking:
            best_quality = quality_ranking[0]
            content.append(
                f"- **Best Explanation Quality:** {best_quality.get('model')} (Score: {best_quality.get('explanation_quality_score', {}).get('mean', 0):.2f})")

        # Analyze action counts
        action_counts = [config.get('actions_count', {}).get('mean', 0) for config in summaries]
        if action_counts:
            avg_actions = sum(action_counts) / len(action_counts)
            content.append(f"- **Average Actions Generated:** {avg_actions:.1f}")

    def _analyze_reliability_metrics(self, summaries: List[Dict[str, Any]], content: List[str]) -> None:
        """Analyze reliability-related metrics."""
        # Find most reliable (highest success rate)
        reliability_ranking = sorted(summaries,
                                     key=lambda x: x.get('overall_success_rate', 0),
                                     reverse=True)

        if reliability_ranking:
            most_reliable = reliability_ranking[0]
            content.append(
                f"- **Most Reliable:** {most_reliable.get('model')} ({most_reliable.get('overall_success_rate', 0):.1%} success rate)")

        # Error analysis
        error_rates = [config.get('error_rate', 0) for config in summaries]
        if error_rates:
            avg_error_rate = sum(error_rates) / len(error_rates)
            content.append(f"- **Average Error Rate:** {avg_error_rate:.1%}")

    def _create_pattern_analysis(self,
                                 summaries: List[Dict[str, Any]],
                                 detailed_results: List[Dict[str, Any]]) -> str:
        """Create pattern analysis section."""
        content = ["## Pattern Analysis"]

        # Model comparison
        content.append("### Model Performance Patterns")
        self._analyze_model_patterns(summaries, content)

        # Strategy comparison
        content.append("\n### Strategy Performance Patterns")
        self._analyze_strategy_patterns(summaries, content)

        # Parameter impact
        content.append("\n### Parameter Impact Analysis")
        self._analyze_parameter_patterns(summaries, content)

        return '\n'.join(content)

    def _analyze_model_patterns(self, summaries: List[Dict[str, Any]], content: List[str]) -> None:
        """Analyze patterns by model type."""
        model_groups = {}
        for config in summaries:
            model = config.get('model', 'Unknown')
            if model not in model_groups:
                model_groups[model] = []
            model_groups[model].append(config)

        for model, configs in model_groups.items():
            avg_score = sum(c.get('overall_score', 0) for c in configs) / len(configs)
            avg_success = sum(c.get('overall_success_rate', 0) for c in configs) / len(configs)
            content.append(
                f"- **{model}:** Avg Score {avg_score:.1f}, Success Rate {avg_success:.1%} ({len(configs)} configs)")

    def _analyze_strategy_patterns(self, summaries: List[Dict[str, Any]], content: List[str]) -> None:
        """Analyze patterns by strategy type."""
        strategy_groups = {}
        for config in summaries:
            strategy = config.get('strategy', 'Unknown')
            if strategy not in strategy_groups:
                strategy_groups[strategy] = []
            strategy_groups[strategy].append(config)

        for strategy, configs in strategy_groups.items():
            avg_score = sum(c.get('overall_score', 0) for c in configs) / len(configs)
            avg_actions = sum(c.get('actions_count', {}).get('mean', 0) for c in configs) / len(configs)
            content.append(f"- **{strategy}:** Avg Score {avg_score:.1f}, Avg Actions {avg_actions:.1f}")

    def _analyze_parameter_patterns(self, summaries: List[Dict[str, Any]], content: List[str]) -> None:
        """Analyze patterns by parameter values."""
        # Temperature analysis
        temp_groups = {}
        for config in summaries:
            temp = config.get('temperature', 'Unknown')
            if temp not in temp_groups:
                temp_groups[temp] = []
            temp_groups[temp].append(config)

        content.append("**Temperature Impact:**")
        for temp in sorted(temp_groups.keys()):
            configs = temp_groups[temp]
            avg_score = sum(c.get('overall_score', 0) for c in configs) / len(configs)
            content.append(f"- T={temp}: Avg Score {avg_score:.1f}")

    def _create_recommendations(self, sorted_summaries: List[Dict[str, Any]]) -> str:
        """Create recommendations section."""
        if not sorted_summaries:
            return "## Recommendations\n\nNo data available for recommendations."

        content = ["## Recommendations"]

        # Overall best configuration
        best = sorted_summaries[0]
        content.append("### Primary Recommendation")
        content.append(
            f"For optimal performance, use **{best.get('model')}** with **{best.get('strategy')}** strategy and temperature **{best.get('temperature')}**.")
        content.append(
            f"This configuration achieved an overall score of **{best.get('overall_score', 0):.1f}/100** with a **{best.get('overall_success_rate', 0):.1%}** success rate.")

        # Alternative recommendations
        content.append("\n### Alternative Configurations")
        for i, config in enumerate(sorted_summaries[1:4], 2):
            content.append(
                f"{i}. **{config.get('model')}** | {config.get('strategy')} | T={config.get('temperature')} (Score: {config.get('overall_score', 0):.1f})")

        # Specialized recommendations
        content.append("\n### Specialized Use Cases")

        # Speed-optimized
        speed_best = max(sorted_summaries, key=lambda x: x.get('tokens_per_second', {}).get('mean', 0))
        content.append(f"- **For Speed:** {speed_best.get('model')} with {speed_best.get('strategy')} strategy")

        # Quality-optimized
        quality_best = max(sorted_summaries, key=lambda x: x.get('explanation_quality_score', {}).get('mean', 0))
        content.append(f"- **For Quality:** {quality_best.get('model')} with {quality_best.get('strategy')} strategy")

        return '\n'.join(content)

    def _create_files_section(self) -> str:
        """Create section describing generated files."""
        return """## Generated Files

The evaluation produced the following output files:

### CSV Data Files
- **`detailed_results.csv`**: Complete results for every individual run with all metrics
- **`summary_results.csv`**: Configuration summaries ranked by overall performance
- **`top_10_configurations.csv`**: Top 10 best performing configurations
- **`tokens_per_second_ranking.csv`**: Configurations ranked by generation speed
- **`latency_ranking.csv`**: Configurations ranked by response latency (lowest first)
- **`parsing_success_ranking.csv`**: Configurations ranked by parsing success rate
- **`quality_ranking.csv`**: Configurations ranked by explanation quality
- **`success_rate_ranking.csv`**: Configurations ranked by overall success rate

### Analysis Files
- **`analysis_report.md`**: This comprehensive analysis report

### How to Use the Files
1. **For overall ranking**: Check `summary_results.csv` or `top_10_configurations.csv`
2. **For specific metrics**: Use the specialized ranking CSV files
3. **For detailed analysis**: Review individual runs in `detailed_results.csv`
4. **For insights**: Read the recommendations in this analysis report

All CSV files can be opened in Excel, Google Sheets, or any data analysis tool."""

    def _create_appendix_section(self,
                                 summaries: List[Dict[str, Any]],
                                 detailed_results: List[Dict[str, Any]]) -> str:
        """Create appendix section with technical details."""
        content = ["## Appendix"]

        content.append("### Evaluation Methodology")
        content.append(f"- **Total Configurations:** {len(summaries)}")
        content.append(f"- **Total Runs:** {len(detailed_results)}")
        content.append("- **Repetitions per Configuration:** 10")
        content.append("- **Warm-up Runs:** 2 (excluded from results)")
        content.append("- **Timeout:** 30 seconds per generation")

        content.append("\n### Scoring Methodology")
        content.append("The overall score (0-100) is calculated based on:")
        content.append("- **Success Rates (40%):** Parsing success, error rates")
        content.append("- **Performance (30%):** Generation speed, latency")
        content.append("- **Quality (20%):** Explanation quality, action relevance")
        content.append("- **Consistency (10%):** Low standard deviation across runs")

        content.append("\n### File Formats")
        content.append("- **CSV files:** Universal format compatible with Excel, Google Sheets, Python pandas, R, etc.")
        content.append("- **Markdown report:** Human-readable analysis with insights and recommendations")
        content.append("- **UTF-8 encoding:** Ensures compatibility across different systems")

        return '\n'.join(content)