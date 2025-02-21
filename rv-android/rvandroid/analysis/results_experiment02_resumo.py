import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import json
from typing import Dict, List, Tuple
import numpy as np

class ExperimentAnalyzer:
    """
    A class to analyze the results of Android testing experiment.
    Processes coverage and error data from multiple testing tools.
    """
    
    def __init__(self, coverage_file: str, errors_file: str, summary_file: str, output_dir: str):
        """
        Initialize the analyzer with the experiment data files.
        
        Args:
            coverage_file: Path to the coverage CSV file
            errors_file: Path to the errors CSV file
            summary_file: Path to the summary CSV file
        """
        # Read CSV files with proper data types
        self.coverage_df = pd.read_csv(coverage_file)
        self.errors_df = pd.read_csv(errors_file)
        self.summary_df = pd.read_csv(summary_file)
        
        # Convert coverage columns to numeric, replacing invalid values with NaN
        numeric_columns = ['cov_method', 'cov_act', 'cov_rv_method', 'errors']
        for col in numeric_columns:
            self.summary_df[col] = pd.to_numeric(self.summary_df[col], errors='coerce')
        
        # Remove rows where tool is null
        self.summary_df = self.summary_df.dropna(subset=['tool'])
        
        # Create output directory if it doesn't exist
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def analyze_coverage(self) -> Dict:
        """
        Analyze coverage metrics for each testing tool.
        
        Returns:
            Dictionary containing coverage statistics per tool
        """
        coverage_stats = {}
        
        # Select only numeric columns for analysis
        numeric_columns = ['cov_method', 'cov_act', 'cov_rv_method', 'errors']
        
        # Group by tool and calculate mean coverage metrics
        tool_coverage = self.summary_df.groupby('tool')[numeric_columns].agg({
            'cov_method': 'mean',
            'cov_act': 'mean',
            'cov_rv_method': 'mean',
            'errors': 'sum'
        }).round(2)
        
        coverage_stats['per_tool'] = tool_coverage.to_dict()
        
        # Find best performing tools for each metric
        coverage_stats['best_performers'] = {
            'method_coverage': tool_coverage['cov_method'].idxmax(),
            'activity_coverage': tool_coverage['cov_act'].idxmax(),
            'rv_method_coverage': tool_coverage['cov_rv_method'].idxmax()
        }
        
        return coverage_stats
    
    def analyze_errors(self) -> Dict:
        """
        Analyze error patterns and distributions across tools.
        
        Returns:
            Dictionary containing error analysis results
        """
        error_analysis = {}
        
        # Count errors per tool
        error_counts = self.errors_df['tool'].value_counts().to_dict()
        error_analysis['error_counts'] = error_counts
        
        # Analyze error types
        error_types = self.errors_df.groupby(['tool', 'unique_msg']).size().reset_index()
        error_types.columns = ['tool', 'error_type', 'count']
        
        # Convert to dictionary format for easy saving
        error_types_dict = {}
        for tool in error_types['tool'].unique():
            tool_errors = error_types[error_types['tool'] == tool]
            error_types_dict[tool] = {
                row['error_type']: row['count'] 
                for _, row in tool_errors.iterrows()
            }
        
        error_analysis['error_types'] = error_types_dict
        
        return error_analysis
    
    def _plot_coverage_comparison(self):
        """Create a bar plot comparing coverage metrics across tools"""
        # Select only numeric columns
        numeric_columns = ['cov_method', 'cov_act', 'cov_rv_method']
        coverage_data = self.summary_df.groupby('tool')[numeric_columns].mean()
        
        fig, ax = plt.subplots(figsize=(12, 6))
        bar_width = 0.25
        index = np.arange(len(coverage_data.index))
        
        # Plot bars for each metric
        ax.bar(index - bar_width, coverage_data['cov_method'], 
               bar_width, label='Method Coverage')
        ax.bar(index, coverage_data['cov_act'], 
               bar_width, label='Activity Coverage')
        ax.bar(index + bar_width, coverage_data['cov_rv_method'], 
               bar_width, label='RV Method Coverage')
        
        ax.set_xlabel('Testing Tool')
        ax.set_ylabel('Coverage (%)')
        ax.set_title('Coverage Metrics Comparison by Tool')
        ax.set_xticks(index)
        ax.set_xticklabels(coverage_data.index, rotation=45)
        ax.legend()
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'coverage_comparison.png')
        plt.close()
    
    def _plot_error_distribution(self):
        """Create a plot showing error distribution across tools"""
        error_counts = self.errors_df['tool'].value_counts()
        
        plt.figure(figsize=(10, 6))
        error_counts.plot(kind='bar')
        plt.title('Number of Errors Detected by Each Tool')
        plt.xlabel('Tool')
        plt.ylabel('Number of Errors')
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        plt.savefig(self.output_dir / 'error_distribution.png')
        plt.close()
    
    def _plot_correlation_heatmap(self):
        """Create a correlation heatmap for coverage metrics"""
        # Select only numeric columns
        numeric_columns = ['cov_method', 'cov_act', 'cov_rv_method', 'errors']
        correlation_matrix = self.summary_df[numeric_columns].corr()
        
        plt.figure(figsize=(8, 6))
        sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0)
        plt.title('Correlation between Coverage Metrics and Errors')
        plt.tight_layout()
        
        plt.savefig(self.output_dir / 'correlation_heatmap.png')
        plt.close()
    
    def create_visualizations(self):
        """
        Create and save visualization plots for the analysis.
        """
        # Set style for all plots
        # plt.style.use('seaborn')
        
        # Create each visualization
        print("Creating coverage comparison plot...")
        self._plot_coverage_comparison()
        
        print("Creating error distribution plot...")
        self._plot_error_distribution()
        
        print("Creating correlation heatmap...")
        self._plot_correlation_heatmap()
    
    def save_results(self, results: Dict):
        """
        Save analysis results to JSON and generate a summary report.
        
        Args:
            results: Dictionary containing all analysis results
        """
        # Save raw results as JSON
        with open(self.output_dir / 'analysis_results.json', 'w') as f:
            json.dump(results, f, indent=4)
        
        # Generate and save summary report
        report_content = self._generate_report(results)
        with open(self.output_dir / 'analysis_report.md', 'w') as f:
            f.write(report_content)
    
    def _generate_report(self, results: Dict) -> str:
        """
        Generate a markdown report from the analysis results.
        
        Args:
            results: Dictionary containing analysis results
            
        Returns:
            String containing the markdown report
        """
        report = [
            "# Android Testing Tools Experiment Analysis Report\n",
            "## Coverage Analysis\n",
            "### Best Performing Tools:\n"
        ]
        
        # Add coverage analysis
        for metric, tool in results['coverage']['best_performers'].items():
            report.append(f"- {metric}: {tool}")
        
        report.extend([
            "\n## Error Analysis\n",
            "### Error Distribution:\n"
        ])
        
        # Add error analysis
        for tool, count in results['errors']['error_counts'].items():
            report.append(f"- {tool}: {count} errors")
        
        report.extend([
            "\n## Main Findings\n",
            "1. Coverage Metrics:",
            f"   - Best method coverage: {results['coverage']['best_performers']['method_coverage']}",
            f"   - Best activity coverage: {results['coverage']['best_performers']['activity_coverage']}",
            f"   - Best RV method coverage: {results['coverage']['best_performers']['rv_method_coverage']}",
            "\n2. Error Detection:",
            f"   - Most errors detected by: {max(results['errors']['error_counts'].items(), key=lambda x: x[1])[0]}"
        ])
        
        return '\n'.join(report)

def main():
    """
    Main function to run the analysis.
    """
    try:
        out_dir = "/home/pedro/tmp/results_claude_resumo"
        # Initialize analyzer
        analyzer = ExperimentAnalyzer(
            '/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/exp02_jca_coverage.csv',
            '/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/exp02_jca_errors.csv',
            '/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/exp02_jca_summary.csv',
            out_dir
        )
        
        # Perform analysis
        print("Performing analysis...")
        results = {
            'coverage': analyzer.analyze_coverage(),
            'errors': analyzer.analyze_errors()
        }
        
        # Create visualizations
        print("Creating visualizations...")
        analyzer.create_visualizations()
        
        # Save results
        print("Saving results...")
        analyzer.save_results(results)
        
        print("Analysis completed. Results saved in 'analysis_results' directory.")
        
    except Exception as e:
        print(f"An error occurred during analysis: {str(e)}")
        raise

if __name__ == "__main__":
    main()