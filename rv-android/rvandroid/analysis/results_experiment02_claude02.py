# Installation requirements for Ubuntu:
# sudo apt-get update
# sudo apt-get install python3-pip python3-dev python3-venv
# python3 -m venv venv
# source venv/bin/activate
# pip install pandas numpy matplotlib seaborn scipy scikit-learn plotly kaleido statsmodels

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from sklearn.preprocessing import StandardScaler
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os

class AndroidTestingAnalyzer:
    def __init__(self, csv_path, output_dir):
        """Initialize the analyzer with the CSV file path."""
        self.df = pd.read_csv(csv_path)
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
    def basic_statistics(self):
        """Calculate basic statistics for coverage metrics."""
        coverage_cols = ['cov_class', 'cov_act', 'cov_method', 'cov_rv_method']
        stats_df = self.df[coverage_cols].describe()
        stats_df.to_csv(f'{self.output_dir}/basic_statistics.csv')
        return stats_df

    def coverage_evolution_by_tool(self):
        """Analyze and visualize coverage evolution over time for each tool."""
        fig = plt.figure(figsize=(15, 10))
        for tool in self.df['tool'].unique():
            tool_data = self.df[self.df['tool'] == tool]
            plt.plot(tool_data['time'] / 3600, tool_data['cov_method'], 
                    label=tool, alpha=0.7)
        
        plt.xlabel('Time (hours)')
        plt.ylabel('Method Coverage (%)')
        plt.title('Coverage Evolution by Testing Tool')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/coverage_evolution.png', dpi=300, bbox_inches='tight')
        plt.close()

    def coverage_plateau_analysis(self):
        """Determine when coverage growth plateaus for each tool."""
        plateau_data = {}
        
        for tool in self.df['tool'].unique():
            tool_data = self.df[self.df['tool'] == tool].copy()
            tool_data = tool_data.sort_values('time')
            
            # Calculate coverage change rate
            tool_data['coverage_change'] = tool_data['cov_method'].diff()
            
            # Use rolling window to smooth the changes
            window_size = 50
            rolling_change = tool_data['coverage_change'].rolling(window=window_size).mean()
            
            # Find where change becomes minimal (less than 0.01%)
            plateau_point = tool_data[rolling_change < 0.01].iloc[0] if len(rolling_change[rolling_change < 0.01]) > 0 else None
            
            if plateau_point is not None:
                plateau_data[tool] = {
                    'plateau_time_minutes': plateau_point['time'] / 60,
                    'coverage_at_plateau': plateau_point['cov_method']
                }
        
        plateau_df = pd.DataFrame(plateau_data).T
        plateau_df.to_csv(f'{self.output_dir}/coverage_plateaus.csv')
        return plateau_df

    def generate_boxplots(self):
        """Generate boxplots comparing coverage metrics across tools."""
        coverage_metrics = ['cov_class', 'cov_act', 'cov_method', 'cov_rv_method']
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 15))
        fig.suptitle('Coverage Distribution by Tool')
        
        for idx, metric in enumerate(coverage_metrics):
            ax = axes[idx // 2, idx % 2]
            sns.boxplot(data=self.df, x='tool', y=metric, ax=ax)
            ax.set_xticklabels(ax.get_xticklabels(), rotation=45)
            ax.set_title(f'{metric} Distribution')
            
        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/coverage_boxplots.png', dpi=300, bbox_inches='tight')
        plt.close()

    def generate_heatmap(self):
        """Generate correlation heatmap between coverage metrics."""
        coverage_metrics = ['cov_class', 'cov_act', 'cov_method', 'cov_rv_method']
        correlation_matrix = self.df[coverage_metrics].corr()
        
        plt.figure(figsize=(10, 8))
        sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', vmin=-1, vmax=1)
        plt.title('Coverage Metrics Correlation')
        plt.tight_layout()
        plt.savefig(f'{self.output_dir}/correlation_heatmap.png', dpi=300, bbox_inches='tight')
        plt.close()

    def method_coverage_analysis(self):
        """Analyze method coverage patterns and unique methods covered by each tool."""
        unique_methods = {}
        
        for tool in self.df['tool'].unique():
            tool_methods = set(self.df[self.df['tool'] == tool]['signature'])
            unique_methods[tool] = len(tool_methods)
            
        # Create Venn diagram-like visualization using plotly
        fig = go.Figure(data=[go.Bar(
            x=list(unique_methods.keys()),
            y=list(unique_methods.values()),
            text=list(unique_methods.values()),
            textposition='auto',
        )])
        
        fig.update_layout(
            title='Unique Methods Covered by Each Tool',
            xaxis_title='Tool',
            yaxis_title='Number of Unique Methods',
            template='plotly_white'
        )
        
        fig.write_image(f'{self.output_dir}/unique_methods_coverage.png')

    def statistical_tests(self):
        """Perform statistical tests to compare tools."""
        results = []
        tools = self.df['tool'].unique()
        
        for metric in ['cov_class', 'cov_act', 'cov_method', 'cov_rv_method']:
            # Perform Kruskal-Wallis H-test
            tool_groups = [self.df[self.df['tool'] == tool][metric] for tool in tools]
            h_stat, p_value = stats.kruskal(*tool_groups)
            
            results.append({
                'metric': metric,
                'test': 'Kruskal-Wallis',
                'statistic': h_stat,
                'p_value': p_value
            })
            
        stats_df = pd.DataFrame(results)
        stats_df.to_csv(f'{self.output_dir}/statistical_tests.csv')
        return stats_df

    def generate_summary_report(self):
        """Generate a comprehensive summary of the analysis findings."""
        basic_stats = self.basic_statistics()
        plateau_data = self.coverage_plateau_analysis()
        statistical_tests = self.statistical_tests()
        
        with open(f'{self.output_dir}/analysis_summary.txt', 'w') as f:
            f.write("Android Testing Analysis Summary\n")
            f.write("================================\n\n")
            
            f.write("1. Basic Coverage Statistics\n")
            f.write(str(basic_stats))
            f.write("\n\n")
            
            f.write("2. Coverage Plateau Analysis\n")
            f.write(str(plateau_data))
            f.write("\n\n")
            
            f.write("3. Statistical Test Results\n")
            f.write(str(statistical_tests))
            f.write("\n\n")
            
            f.write("4. Key Findings\n")
            # Add specific findings based on the analysis
            max_coverage_tool = self.df.groupby('tool')['cov_method'].max().idxmax()
            f.write(f"- Highest method coverage achieved by: {max_coverage_tool}\n")
            
            fastest_plateau = plateau_data['plateau_time_minutes'].idxmin()
            f.write(f"- Fastest tool to reach coverage plateau: {fastest_plateau}\n")

def main():
    file_path = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/exp02_jca_coverage.csv"
    out_dir = "/home/pedro/tmp/results_claude02"
    
    # Example usage
    analyzer = AndroidTestingAnalyzer(file_path, out_dir)
    
    # Generate all analyses
    analyzer.basic_statistics()
    analyzer.coverage_evolution_by_tool()
    analyzer.coverage_plateau_analysis()
    analyzer.generate_boxplots()
    analyzer.generate_heatmap()
    analyzer.method_coverage_analysis()
    analyzer.statistical_tests()
    analyzer.generate_summary_report()
    
    print("Analysis completed. Check the 'analysis_output' directory for results.")

if __name__ == '__main__':
    main()