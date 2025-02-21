# Required Ubuntu packages and Python libraries:
# sudo apt-get update
# sudo apt-get install python3-pip python3-dev python3-venv
# python3 -m venv venv
# source venv/bin/activate
# pip install pandas numpy matplotlib seaborn scipy statsmodels scikit-learn tabulate

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from statsmodels.stats.multicomp import pairwise_tukeyhsd
from sklearn.linear_model import LinearRegression
from datetime import datetime
import os
from tabulate import tabulate
import json

class AndroidTestAnalysis:
    def __init__(self, csv_path, output_dir="results"):
        """
        Initialize the analysis with the input CSV file and output directory.
        
        Args:
            csv_path (str): Path to the CSV file containing the test results
            output_dir (str): Directory to store analysis results
        """
        self.csv_path = csv_path
        self.output_dir = output_dir
        self.create_output_dirs()
        
        # Read and preprocess the data
        self.df = pd.read_csv(csv_path)
        self.preprocess_data()
        
    def create_output_dirs(self):
        """Create necessary output directories for storing results."""
        directories = [
            self.output_dir,
            f"{self.output_dir}/plots",
            f"{self.output_dir}/data",
            f"{self.output_dir}/reports"
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            
    def preprocess_data(self):
        """Preprocess the data for analysis."""
        # Convert time to minutes for better readability
        self.df['time_minutes'] = self.df['time'] / 60
        
        # Create unique method identifier
        self.df['method_id'] = self.df['class'] + '.' + self.df['signature']
        
    def basic_statistics(self):
        """
        Calculate basic statistics for coverage metrics.
        Returns a DataFrame with statistical measures.
        """
        coverage_cols = ['cov_class', 'cov_act', 'cov_method', 'cov_rv_method']
        stats_df = self.df[coverage_cols].agg(['mean', 'std', 'min', 'max', 'median'])
        
        # Save statistics to CSV
        stats_df.to_csv(f"{self.output_dir}/data/basic_statistics.csv")
        return stats_df
    
    def coverage_saturation_analysis(self, coverage_type='cov_method', window_size=10):
        """
        Analyze when coverage growth saturates for each tool and APK.
        
        Args:
            coverage_type (str): Type of coverage to analyze
            window_size (int): Window size for moving average calculation
        
        Returns:
            DataFrame with saturation points
        """
        saturation_results = []
        
        for tool in self.df['tool'].unique():
            for apk in self.df['apk'].unique():
                data = self.df[(self.df['tool'] == tool) & (self.df['apk'] == apk)].copy()
                if len(data) == 0:
                    continue
                    
                data = data.sort_values('time_minutes')
                coverage = data[coverage_type].values
                
                # Calculate moving average of coverage growth
                growth_rate = np.gradient(coverage)
                smooth_growth = pd.Series(growth_rate).rolling(window=window_size).mean()
                
                # Find saturation point (where growth rate becomes very small)
                threshold = 0.01  # 1% change
                saturation_idx = np.where(abs(smooth_growth) < threshold)[0]
                
                if len(saturation_idx) > 0:
                    saturation_time = data.iloc[saturation_idx[0]]['time_minutes']
                    final_coverage = data.iloc[-1][coverage_type]
                else:
                    saturation_time = data.iloc[-1]['time_minutes']
                    final_coverage = data.iloc[-1][coverage_type]
                
                saturation_results.append({
                    'tool': tool,
                    'apk': apk,
                    'saturation_time_minutes': saturation_time,
                    'final_coverage': final_coverage
                })
        
        saturation_df = pd.DataFrame(saturation_results)
        saturation_df.to_csv(f"{self.output_dir}/data/coverage_saturation.csv", index=False)
        return saturation_df
    
    def plot_coverage_over_time(self, coverage_type='cov_method'):
        """
        Create various plots showing coverage evolution over time.
        
        Args:
            coverage_type (str): Type of coverage to plot
        """
        # 1. Line plot for each tool (averaged across APKs)
        plt.figure(figsize=(12, 6))
        for tool in self.df['tool'].unique():
            tool_data = self.df[self.df['tool'] == tool]
            plt.plot(tool_data['time_minutes'], tool_data[coverage_type], label=tool, alpha=0.7)
        
        plt.xlabel('Time (minutes)')
        plt.ylabel(f'Coverage ({coverage_type})')
        plt.title(f'Coverage Evolution Over Time by Tool')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/plots/coverage_evolution_by_tool.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        # 2. Box plot comparing final coverage across tools
        plt.figure(figsize=(10, 6))
        sns.boxplot(data=self.df, x='tool', y=coverage_type)
        plt.xticks(rotation=45)
        plt.title(f'Final Coverage Distribution by Tool')
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/plots/coverage_distribution_by_tool.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        # 3. Heatmap of coverage by tool and APK
        final_coverage = self.df.groupby(['tool', 'apk'])[coverage_type].last().unstack()
        plt.figure(figsize=(12, 8))
        sns.heatmap(final_coverage, annot=True, cmap='YlOrRd', fmt='.1f')
        plt.title(f'Final Coverage Heatmap (Tool vs APK)')
        plt.tight_layout()
        plt.savefig(f"{self.output_dir}/plots/coverage_heatmap.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def statistical_tests(self, coverage_type='cov_method'):
        """
        Perform statistical tests to compare tools.
        
        Args:
            coverage_type (str): Type of coverage to analyze
        
        Returns:
            dict with statistical test results
        """
        # 1. One-way ANOVA
        tools = self.df['tool'].unique()
        tool_groups = [group[coverage_type].values for name, group in self.df.groupby('tool')]
        f_statistic, p_value = stats.f_oneway(*tool_groups)
        
        # 2. Tukey's HSD test
        tukey = pairwise_tukeyhsd(self.df[coverage_type], self.df['tool'])
        
        results = {
            'anova': {
                'f_statistic': f_statistic,
                'p_value': p_value
            },
            'tukey_hsd': str(tukey)
        }
        
        # Save results
        with open(f"{self.output_dir}/data/statistical_tests.json", 'w') as f:
            json.dump(results, f, indent=4)
        
        return results
    
    def generate_report(self):
        """
        Generate a comprehensive markdown report of the analysis.
        """
        report = []
        
        # 1. Basic Statistics
        report.append("# Android Test Coverage Analysis Report\n")
        report.append(f"Analysis performed on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        
        # 2. Basic Statistics
        report.append("## Basic Statistics\n")
        basic_stats = self.basic_statistics()
        report.append("Coverage statistics across all tools and APKs:\n")
        report.append(f"```\n{basic_stats.to_markdown()}\n```\n")
        
        # 3. Coverage Saturation Analysis
        report.append("## Coverage Saturation Analysis\n")
        saturation_df = self.coverage_saturation_analysis()
        report.append("Average saturation times by tool:\n")
        avg_saturation = saturation_df.groupby('tool')['saturation_time_minutes'].mean()
        report.append(f"```\n{avg_saturation.to_markdown()}\n```\n")
        
        # 4. Statistical Analysis
        report.append("## Statistical Analysis\n")
        stats_results = self.statistical_tests()
        report.append("### ANOVA Test Results\n")
        report.append(f"F-statistic: {stats_results['anova']['f_statistic']:.4f}\n")
        report.append(f"p-value: {stats_results['anova']['p_value']:.4f}\n")
        
        report.append("### Tukey's HSD Test Results\n")
        report.append(f"```\n{stats_results['tukey_hsd']}\n```\n")
        
        # 5. Key Findings
        report.append("## Key Findings\n")
        
        # Save report
        with open(f"{self.output_dir}/reports/analysis_report.md", 'w') as f:
            f.write('\n'.join(report))

def main():
    """
    Main function to run the analysis.
    Usage: python script.py
    """
    file_path = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/exp02_jca_coverage.csv"
    out_dir = "/home/pedro/tmp/results_claude_01"
    
    # Initialize analysis
    analysis = AndroidTestAnalysis(file_path, out_dir)
    
    # Generate all plots
    coverage_types = ['cov_class', 'cov_act', 'cov_method', 'cov_rv_method']
    for coverage_type in coverage_types:
        analysis.plot_coverage_over_time(coverage_type)
    
    # Perform statistical analysis
    analysis.statistical_tests()
    
    # Generate final report
    analysis.generate_report()

if __name__ == "__main__":
    main()