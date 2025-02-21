# Required Ubuntu packages and Python dependencies installation:
"""
# Ubuntu system packages
sudo apt-get update
sudo apt-get install python3-pip python3-venv

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install required Python packages
pip install pandas numpy matplotlib seaborn scipy statsmodels kneed plotly kaleido markdown
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from kneed import KneeLocator
import markdown
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

class AndroidTestingAnalyzer:
    def __init__(self, coverage_file: str, errors_file: str, output_dir: str):
        """
        Initialize the analyzer with input files and output directory.
        
        Args:
            coverage_file (str): Path to the coverage CSV file
            errors_file (str): Path to the errors CSV file
            output_dir (str): Path to the output directory
        """
        self.coverage_df = pd.read_csv(coverage_file)
        self.errors_df = pd.read_csv(errors_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set style for matplotlib
        # plt.style.use('seaborn')
        sns.set_palette("husl")
        
    def basic_statistics(self):
        """Calculate basic statistics for coverage and errors."""
        stats_dict = {
            'total_executions': len(self.coverage_df),
            'unique_apks': len(self.coverage_df['apk'].unique()),
            'total_errors': len(self.errors_df),
            'unique_errors': len(self.errors_df['unique_msg'].unique()),
            'tools_used': list(self.coverage_df['tool'].unique()),
            'avg_coverage_class': self.coverage_df['cov_class'].mean(),
            'avg_coverage_method': self.coverage_df['cov_method'].mean(),
            'avg_coverage_activity': self.coverage_df['cov_act'].mean()
        }
        return stats_dict

    def analyze_coverage_plateau(self):
        """
        Analyze when coverage growth plateaus for each tool and APK combination.
        Returns dictionary with plateau times.
        """
        plateau_times = {}
        
        for tool in self.coverage_df['tool'].unique():
            for apk in self.coverage_df['apk'].unique():
                df_filtered = self.coverage_df[
                    (self.coverage_df['tool'] == tool) & 
                    (self.coverage_df['apk'] == apk)
                ].sort_values('time')
                
                if len(df_filtered) < 10:  # Skip if not enough data points
                    continue
                
                # Use the Kneed algorithm to find the elbow point
                time_normalized = df_filtered['time'].values / 3600  # Convert to hours
                coverage_normalized = df_filtered['cov_method'].values
                
                try:
                    kneedle = KneeLocator(
                        time_normalized, 
                        coverage_normalized,
                        S=1.0, 
                        curve='concave', 
                        direction='increasing'
                    )
                    if kneedle.knee is not None:
                        plateau_times[f"{tool}_{apk}"] = kneedle.knee
                except:
                    continue
                    
        return plateau_times

    def plot_coverage_over_time(self):
        """Generate plots showing coverage progression over time for each tool."""
        plt.figure(figsize=(12, 8))
        
        for tool in self.coverage_df['tool'].unique():
            tool_data = self.coverage_df[self.coverage_df['tool'] == tool]
            plt.plot(
                tool_data['time'] / 3600,  # Convert to hours
                tool_data['cov_method'].rolling(window=50).mean(),
                label=tool,
                alpha=0.7
            )
        
        plt.xlabel('Time (hours)')
        plt.ylabel('Method Coverage (%)')
        plt.title('Coverage Progress Over Time by Tool')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'coverage_over_time.png', dpi=300, bbox_inches='tight')
        plt.close()

    def plot_error_distribution(self):
        """Generate plots showing error distribution by tool and specification."""
        # Error count by tool
        plt.figure(figsize=(10, 6))
        error_by_tool = self.errors_df['tool'].value_counts()
        error_by_tool.plot(kind='bar')
        plt.title('Number of Errors Found by Each Tool')
        plt.xlabel('Tool')
        plt.ylabel('Number of Errors')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(self.output_dir / 'errors_by_tool.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Error types distribution
        plt.figure(figsize=(12, 6))
        error_by_spec = self.errors_df['spec'].value_counts()
        error_by_spec.plot(kind='bar')
        plt.title('Distribution of Error Types')
        plt.xlabel('Specification')
        plt.ylabel('Count')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(self.output_dir / 'error_types.png', dpi=300, bbox_inches='tight')
        plt.close()

    def analyze_apk_performance(self):
        """Analyze APK performance in terms of coverage and errors."""
        apk_stats = []
        
        for apk in self.coverage_df['apk'].unique():
            apk_coverage = self.coverage_df[self.coverage_df['apk'] == apk]
            apk_errors = self.errors_df[self.errors_df['apk'] == apk]
            
            stats = {
                'apk': apk,
                'max_coverage': apk_coverage['cov_method'].max(),
                'error_count': len(apk_errors),
                'unique_error_count': len(apk_errors['unique_msg'].unique())
            }
            apk_stats.append(stats)
            
        return pd.DataFrame(apk_stats)

    def generate_report(self):
        """Generate a comprehensive markdown report with findings."""
        basic_stats = self.basic_statistics()
        plateau_times = self.analyze_coverage_plateau()
        apk_performance = self.analyze_apk_performance()
        
        # Create plots
        self.plot_coverage_over_time()
        self.plot_error_distribution()
        
        report = f"""# Android Testing Analysis Report
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Basic Statistics
- Total test executions: {basic_stats['total_executions']:,}
- Number of unique APKs tested: {basic_stats['unique_apks']}
- Total errors found: {basic_stats['total_errors']:,}
- Unique errors found: {basic_stats['unique_errors']:,}
- Tools used: {', '.join(basic_stats['tools_used'])}

## Coverage Analysis
![Coverage Over Time](coverage_over_time.png)

Average coverage metrics:
- Class coverage: {basic_stats['avg_coverage_class']:.2f}%
- Method coverage: {basic_stats['avg_coverage_method']:.2f}%
- Activity coverage: {basic_stats['avg_coverage_activity']:.2f}%

### Coverage Plateau Analysis
The following tool-APK combinations reached their coverage plateau at:
"""
        
        for combo, time in plateau_times.items():
            tool, apk = combo.split('_', 1)
            report += f"- {tool} testing {apk}: {time:.2f} hours\n"
            
        report += """
## Error Analysis
![Errors by Tool](errors_by_tool.png)
![Error Types](error_types.png)

### APK Performance Summary
"""
        
        # Add APK performance table
        apk_performance_sorted = apk_performance.sort_values('error_count', ascending=False)
        report += apk_performance_sorted.to_markdown()
        
        # Save report
        with open(self.output_dir / 'analysis_report.md', 'w') as f:
            f.write(report)

def main():
    """Main function to run the analysis."""
    base_dir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android"
    coverage_file = base_dir + "/exp02_jca_coverage.csv"
    errors_file = base_dir + "/exp02_jca_errors.csv"
    output_dir = "/home/pedro/tmp/results_claude_try03"
    
    analyzer = AndroidTestingAnalyzer(
        coverage_file,
        errors_file,
        output_dir
    )
    
    analyzer.generate_report()
    print(f"Analysis complete. Report saved in {output_dir}")

if __name__ == "__main__":
    main()