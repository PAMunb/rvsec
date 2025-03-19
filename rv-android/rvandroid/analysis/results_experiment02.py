from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
from statsmodels.formula.api import ols


class TestCoverageAnalyzer:
    def __init__(self, file_path):
        """
        Initializes the analyzer with the CSV results file.
        
        Args:
            file_path (str): Path to the CSV file with experiment results
        """
        self.df = pd.read_csv(file_path)
        self.prepare_data()

    def prepare_data(self):
        """Prepares data for analysis, converting types and creating auxiliary columns."""
        # Convert numeric columns
        numeric_columns = ['timeout', 'time', 'cov_class', 'cov_method', 'cov_rv_method']
        for col in numeric_columns:
            if col in self.df.columns:
                self.df[col] = pd.to_numeric(self.df[col], errors='coerce')

        # Extract app name from APK field (removing extension and path)
        self.df['app_name'] = self.df['apk'].apply(lambda x: Path(x).stem)

        # Create a column for the class package
        self.df['package'] = self.df['class'].apply(lambda x: x.split('.')[-2] if len(x.split('.')) > 1 else 'default')

    def statistical_summary(self):
        """
        Generates a basic statistical summary of the data.
        
        Returns:
            DataFrame: Statistical summary of coverage metrics
        """
        print("Statistical summary of coverage metrics:")
        metrics = ['cov_class', 'cov_method', 'cov_rv_method']
        return self.df[metrics].describe()

    def coverage_by_tool(self):
        """
        Analyzes the final coverage achieved by each tool.
        
        Returns:
            DataFrame: Average final coverage by tool
        """
        # Group by APK and tool, and get the maximum coverage values
        final_coverage = self.df.groupby(['apk', 'tool']).agg({
            'cov_class': 'max',
            'cov_method': 'max',
            'cov_rv_method': 'max'
        }).reset_index()

        # Calculate the average for each tool
        avg_by_tool = final_coverage.groupby('tool').agg({
            'cov_class': ['mean', 'std'],
            'cov_method': ['mean', 'std'],
            'cov_rv_method': ['mean', 'std']
        })

        return avg_by_tool

    def plot_coverage_by_tool(self):
        """Plots bar charts comparing the coverage achieved by each tool."""
        final_coverage = self.df.groupby(['apk', 'tool']).agg({
            'cov_class': 'max',
            'cov_method': 'max',
            'cov_rv_method': 'max'
        }).reset_index()

        fig, axes = plt.subplots(1, 3, figsize=(18, 6))

        metrics = ['cov_class', 'cov_method', 'cov_rv_method']
        titles = ['Class Coverage', 'Method Coverage', 'Special Method Coverage']

        for i, (metric, title) in enumerate(zip(metrics, titles)):
            sns.barplot(x='tool', y=metric, data=final_coverage, ax=axes[i])
            axes[i].set_title(title)
            axes[i].set_xlabel('Tool')
            axes[i].set_ylabel('Coverage (%)')
            axes[i].grid(axis='y', linestyle='--', alpha=0.7)

        plt.tight_layout()
        plt.savefig('coverage_by_tool.png')
        plt.close()

        return "Chart saved as 'coverage_by_tool.png'"

    def coverage_evolution_over_time(self):
        """
        Analyzes how coverage evolves over time for each tool.
        Plots graphs showing the coverage evolution for a selected application.
        """
        # Select an application for demonstration
        analyzed_app = self.df['apk'].unique()[0]
        app_df = self.df[self.df['apk'] == analyzed_app].copy()

        # Sort by time and reset index
        app_df = app_df.sort_values(by=['tool', 'time']).reset_index(drop=True)

        # For better visualization, we can group into time intervals
        app_df['time_bin'] = pd.cut(app_df['time'], bins=20)

        fig, axes = plt.subplots(1, 3, figsize=(18, 6))

        metrics = ['cov_class', 'cov_method', 'cov_rv_method']
        titles = ['Class Coverage Evolution',
                  'Method Coverage Evolution',
                  'Special Method Coverage Evolution']

        for i, (metric, title) in enumerate(zip(metrics, titles)):
            for tool_name, tool_group in app_df.groupby('tool'):
                axes[i].plot(tool_group['time'], tool_group[metric],
                             label=tool_name, marker='o', linestyle='-', markersize=3)

            axes[i].set_title(f"{title}\nApplication: {Path(analyzed_app).stem}")
            axes[i].set_xlabel('Time (seconds)')
            axes[i].set_ylabel('Coverage (%)')
            axes[i].grid(True, linestyle='--', alpha=0.7)
            axes[i].legend()

        plt.tight_layout()
        plt.savefig('coverage_evolution_time.png')
        plt.close()

        return "Chart saved as 'coverage_evolution_time.png'"

    def variance_analysis(self):
        """
        Performs analysis of variance (ANOVA) to check if there are
        significant differences between tools.
        
        Returns:
            dict: ANOVA results for each coverage metric
        """
        results = {}

        # Get maximum coverage values for each APK and tool combination
        final_coverage = self.df.groupby(['apk', 'tool']).agg({
            'cov_class': 'max',
            'cov_method': 'max',
            'cov_rv_method': 'max'
        }).reset_index()

        metrics = ['cov_class', 'cov_method', 'cov_rv_method']

        for metric in metrics:
            model = ols(f'{metric} ~ C(tool)', data=final_coverage).fit()
            anova_table = sm.stats.anova_lm(model, typ=2)
            results[metric] = anova_table

        return results

    def post_hoc_tests(self):
        """
        Performs post-hoc tests to compare tools pairwise.
        
        Returns:
            dict: Results of Tukey HSD tests for each metric
        """
        from statsmodels.stats.multicomp import pairwise_tukeyhsd

        results = {}

        # Get maximum coverage values for each APK and tool combination
        final_coverage = self.df.groupby(['apk', 'tool']).agg({
            'cov_class': 'max',
            'cov_method': 'max',
            'cov_rv_method': 'max'
        }).reset_index()

        metrics = ['cov_class', 'cov_method', 'cov_rv_method']

        for metric in metrics:
            tukey = pairwise_tukeyhsd(endog=final_coverage[metric],
                                      groups=final_coverage['tool'],
                                      alpha=0.05)
            results[metric] = tukey

        return results

    def time_efficiency_analysis(self):
        """
        Analyzes the efficiency of tools in terms of coverage over time.
        Calculates the coverage rate per second.
        
        Returns:
            DataFrame: Coverage growth rate per second for each tool
        """
        # For each APK and tool combination, find the time to reach
        # 25%, 50%, 75% and 100% of maximum coverage
        results = []

        for (apk, tool), group in self.df.groupby(['apk', 'tool']):
            # Sort by time
            group = group.sort_values('time')

            for metric in ['cov_class', 'cov_method', 'cov_rv_method']:
                max_coverage = group[metric].max()

                if max_coverage > 0:  # Avoid division by zero
                    # Times to reach different coverage levels
                    t25 = group[group[metric] >= 0.25 * max_coverage]['time'].min() if any(
                        group[metric] >= 0.25 * max_coverage) else np.nan
                    t50 = group[group[metric] >= 0.50 * max_coverage]['time'].min() if any(
                        group[metric] >= 0.50 * max_coverage) else np.nan
                    t75 = group[group[metric] >= 0.75 * max_coverage]['time'].min() if any(
                        group[metric] >= 0.75 * max_coverage) else np.nan
                    t100 = group[group[metric] >= 0.99 * max_coverage]['time'].min() if any(
                        group[metric] >= 0.99 * max_coverage) else np.nan

                    # Coverage rate per second
                    rate = max_coverage / t100 if not np.isnan(t100) and t100 > 0 else np.nan

                    results.append({
                        'apk': apk,
                        'app_name': Path(apk).stem,
                        'tool': tool,
                        'metric': metric,
                        'max_coverage': max_coverage,
                        'time_25pct': t25,
                        'time_50pct': t50,
                        'time_75pct': t75,
                        'time_100pct': t100,
                        'coverage_rate_per_second': rate
                    })

        df_efficiency = pd.DataFrame(results)

        # Plot coverage rates per second
        plt.figure(figsize=(12, 8))

        for i, metric in enumerate(['cov_class', 'cov_method', 'cov_rv_method']):
            plt.subplot(1, 3, i + 1)
            metric_data = df_efficiency[df_efficiency['metric'] == metric]

            sns.boxplot(x='tool', y='coverage_rate_per_second', data=metric_data)
            plt.title(f'Coverage Rate per Second\n({metric})')
            plt.xlabel('Tool')
            plt.ylabel('Coverage % / second')
            plt.grid(axis='y', linestyle='--', alpha=0.7)

        plt.tight_layout()
        plt.savefig('coverage_rate_per_second.png')
        plt.close()

        return df_efficiency.groupby(['tool', 'metric']).agg({
            'coverage_rate_per_second': ['mean', 'std', 'min', 'max'],
            'time_50pct': ['mean', 'std'],
            'time_100pct': ['mean', 'std']
        })

    def covered_packages_analysis(self):
        """
        Analyzes which packages were covered by each tool.
        
        Returns:
            DataFrame: Statistics about packages covered by each tool
        """
        # Count how many unique methods each tool exercised in each package
        methods_by_package = self.df.groupby(['tool', 'package', 'apk']).agg({
            'method': 'nunique'
        }).reset_index()

        # Visualize the 10 most exercised packages for each tool
        plt.figure(figsize=(15, 10))

        # Get a specific APK for analysis
        analyzed_app = self.df['apk'].unique()[0]
        app_data = methods_by_package[methods_by_package['apk'] == analyzed_app]

        tools = app_data['tool'].unique()
        n_tools = len(tools)

        for i, tool_name in enumerate(tools):
            plt.subplot(1, n_tools, i + 1)

            tool_data = app_data[app_data['tool'] == tool_name]
            top_packages = tool_data.sort_values('method', ascending=False).head(10)

            sns.barplot(x='method', y='package', data=top_packages)
            plt.title(f'Top 10 Packages - {tool_name}\n({Path(analyzed_app).stem})')
            plt.xlabel('Number of Unique Methods')
            plt.grid(axis='x', linestyle='--', alpha=0.7)

        plt.tight_layout()
        plt.savefig('packages_by_tool.png')
        plt.close()

        # Comparative analysis between tools
        package_comparison = methods_by_package.pivot_table(
            index=['apk', 'package'],
            columns='tool',
            values='method',
            aggfunc='sum',
            fill_value=0
        ).reset_index()

        # Calculate how many packages each tool exercised exclusively
        exclusive_packages = {}
        for tool_name in self.df['tool'].unique():
            exclusive_packages[tool_name] = []

            for _, row in package_comparison.iterrows():
                other_tools = [t for t in self.df['tool'].unique() if t != tool_name]

                if row[tool_name] > 0 and all(row[t] == 0 for t in other_tools):
                    exclusive_packages[tool_name].append((row['apk'], row['package']))

        # Count how many packages each tool exercised exclusively
        exclusive_counts = {tool: len(packages) for tool, packages in exclusive_packages.items()}

        return {
            'methods_by_package': methods_by_package,
            'exclusive_packages': exclusive_counts
        }

    def method_complexity_analysis(self):
        """
        Analyzes the relationship between coverage and method complexity.
        Uses signature length as a proxy for complexity.
        
        Returns:
            dict: Statistics and correlations about method complexity
        """
        # Create a column to represent complexity
        self.df['complexity'] = self.df['signature'].apply(len)

        # Calculate correlation between complexity and coverage metrics
        correlations = {}
        for tool_name, group in self.df.groupby('tool'):
            corr = group[['complexity', 'cov_class', 'cov_method', 'cov_rv_method']].corr()
            correlations[tool_name] = corr.loc['complexity', ['cov_class', 'cov_method', 'cov_rv_method']]

        # Plot complexity distribution for each tool
        plt.figure(figsize=(10, 6))
        for tool_name, group in self.df.groupby('tool'):
            sns.kdeplot(group['complexity'], label=tool_name)

        plt.title('Method Complexity Distribution by Tool')
        plt.xlabel('Complexity (Signature Length)')
        plt.ylabel('Density')
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.savefig('method_complexity.png')
        plt.close()

        return correlations

    def generate_coverage_heatmap(self):
        """
        Generates a heatmap showing the final coverage for each APK and tool combination.
        """
        # Get maximum coverage values for each APK and tool combination
        final_coverage = self.df.groupby(['app_name', 'tool']).agg({
            'cov_class': 'max',
            'cov_method': 'max',
            'cov_rv_method': 'max'
        }).reset_index()

        # Create a heatmap for each metric
        metrics = ['cov_class', 'cov_method', 'cov_rv_method']
        titles = ['Class Coverage (%)', 'Method Coverage (%)', 'Special Method Coverage (%)']

        fig, axes = plt.subplots(1, 3, figsize=(20, 8))

        for i, (metric, title) in enumerate(zip(metrics, titles)):
            # Pivot the table to the appropriate format for the heatmap
            pivot = final_coverage.pivot(index='app_name', columns='tool', values=metric)

            # Create the heatmap
            sns.heatmap(pivot, annot=True, fmt='.1f', cmap='YlGnBu', ax=axes[i])
            axes[i].set_title(title)
            axes[i].set_xlabel('Tool')
            axes[i].set_ylabel('Application')

        plt.tight_layout()
        plt.savefig('coverage_heatmap.png')
        plt.close()

        return "Heatmap saved as 'coverage_heatmap.png'"

    def run_complete_analysis(self, output_directory="analysis_results"):
        """
        Runs all analyses and saves the results in a specific directory.
        
        Args:
            output_directory (str): Directory to save the results
        
        Returns:
            dict: Summary of results from all analyses
        """
        import os

        # Create output directory if it doesn't exist
        os.makedirs(output_directory, exist_ok=True)

        # Redirect graphic outputs to the directory
        os.chdir(output_directory)

        results = {}

        print("Running complete statistical analysis...")

        # Basic statistics
        results['statistical_summary'] = self.statistical_summary()
        results['coverage_by_tool'] = self.coverage_by_tool()

        # Graphs
        print(self.plot_coverage_by_tool())
        print(self.coverage_evolution_over_time())
        print(self.generate_coverage_heatmap())

        # Advanced statistical analyses
        results['variance_analysis'] = self.variance_analysis()
        results['post_hoc_tests'] = self.post_hoc_tests()
        results['time_efficiency'] = self.time_efficiency_analysis()
        results['package_analysis'] = self.covered_packages_analysis()
        results['method_complexity'] = self.method_complexity_analysis()

        # Save a summary in CSV format
        results['coverage_by_tool'].to_csv('coverage_by_tool.csv')

        print(f"Complete analysis finished. Results saved in '{output_directory}'")
        return results


# Example usage of the analyzer
if __name__ == "__main__":
    # Path to the CSV file with the results
    file_path = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/exp02_jca_coverage.csv"
    out_dir = "/home/pedro/tmp/results"

    # Create the analyzer
    analyzer = TestCoverageAnalyzer(file_path)

    # Run the complete analysis
    results = analyzer.run_complete_analysis(out_dir)

    # To run individual analyses:
    # print(analyzer.statistical_summary())
    # print(analyzer.coverage_by_tool())
    # analyzer.plot_coverage_by_tool()
    # analyzer.coverage_evolution_over_time()
