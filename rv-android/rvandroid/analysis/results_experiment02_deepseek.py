import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from scipy.stats import linregress
import os

# Configuration for high-quality plots
# plt.style.use('seaborn')
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 12

# Function to load the CSV data
def load_data(filepath):
    """
    Load the experiment data from a CSV file.
    """
    return pd.read_csv(filepath)

# Function to calculate basic statistics
def calculate_basic_stats(df):
    """
    Calculate basic statistics for coverage metrics.
    """
    stats = df[['cov_class', 'cov_act', 'cov_method', 'cov_rv_method']].describe()
    return stats

# Function to analyze coverage growth over time
def analyze_coverage_growth(df, tool):
    """
    Analyze how coverage grows over time for a specific tool.
    """
    tool_data = df[df['tool'] == tool]
    time_intervals = np.arange(0, tool_data['time'].max() + 1, 60)  # Group by minute
    coverage_data = []

    for interval in time_intervals:
        interval_data = tool_data[tool_data['time'] <= interval]
        if not interval_data.empty:
            coverage_data.append({
                'time': interval,
                'cov_class': interval_data['cov_class'].max(),
                'cov_act': interval_data['cov_act'].max(),
                'cov_method': interval_data['cov_method'].max(),
                'cov_rv_method': interval_data['cov_rv_method'].max()
            })

    return pd.DataFrame(coverage_data)

# Function to plot coverage growth over time
def plot_coverage_growth(coverage_data, tool):
    """
    Plot coverage growth over time for a specific tool.
    """
    plt.figure(figsize=(10, 6))
    plt.plot(coverage_data['time'] / 60, coverage_data['cov_class'], label='Class Coverage')
    plt.plot(coverage_data['time'] / 60, coverage_data['cov_act'], label='Activity Coverage')
    plt.plot(coverage_data['time'] / 60, coverage_data['cov_method'], label='Method Coverage')
    plt.plot(coverage_data['time'] / 60, coverage_data['cov_rv_method'], label='RV Method Coverage')
    plt.xlabel('Time (minutes)')
    plt.ylabel('Coverage (%)')
    plt.title(f'Coverage Growth Over Time for {tool}')
    plt.legend()
    plt.grid(True)
    plt.savefig(f'{tool}_coverage_growth.png', bbox_inches='tight')
    plt.show()

# Function to determine when coverage plateaus
def find_coverage_plateau(coverage_data, threshold=0.1):
    """
    Determine the time when coverage growth plateaus.
    """
    for i in range(1, len(coverage_data)):
        if all(abs(coverage_data.iloc[i][['cov_class', 'cov_act', 'cov_method', 'cov_rv_method']] -
                   coverage_data.iloc[i-1][['cov_class', 'cov_act', 'cov_method', 'cov_rv_method']]) < threshold):
            return coverage_data.iloc[i]['time'] / 60  # Return time in minutes
    return None

# Function to generate a summary of findings
def generate_summary(df):
    """
    Generate a summary of the analysis.
    """
    summary = {}
    tools = df['tool'].unique()

    for tool in tools:
        coverage_data = analyze_coverage_growth(df, tool)
        plateau_time = find_coverage_plateau(coverage_data)
        summary[tool] = {
            'max_cov_class': coverage_data['cov_class'].max(),
            'max_cov_act': coverage_data['cov_act'].max(),
            'max_cov_method': coverage_data['cov_method'].max(),
            'max_cov_rv_method': coverage_data['cov_rv_method'].max(),
            'plateau_time': plateau_time
        }

    return summary

# Main function to execute the analysis
def main(filepath):
    """
    Main function to load data, analyze, and generate plots.
    """
    df = load_data(filepath)
    print("Basic Statistics:")
    print(calculate_basic_stats(df))

    tools = df['tool'].unique()
    for tool in tools:
        coverage_data = analyze_coverage_growth(df, tool)
        plot_coverage_growth(coverage_data, tool)
        plateau_time = find_coverage_plateau(coverage_data)
        print(f"{tool} coverage plateaus at {plateau_time:.2f} minutes.")

    summary = generate_summary(df)
    print("\nSummary of Findings:")
    for tool, stats in summary.items():
        print(f"{tool}: {stats}")

# Entry point
if __name__ == '__main__':
    # Replace 'your_data.csv' with the path to your CSV file
    file_path = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/exp02_jca_coverage.csv"
    main(file_path)