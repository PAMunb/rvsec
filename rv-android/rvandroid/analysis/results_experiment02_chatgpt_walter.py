#!/usr/bin/env python3
"""
Script: experiment_analysis.py

Description:
    This script analyzes experimental results from testing Android applications
    using various tools (e.g., monkey, droidbot, droidmate, ape). The input CSV
    file should have the following columns:
        apk, rep, timeout, tool, time, class, method, signature,
        cov_class, cov_act, cov_method, cov_rv_method

    The analysis includes:
        - Basic descriptive statistics.
        - Advanced analysis such as detecting when the coverage metrics plateau.
        - Generation of high-quality plots suitable for scientific articles.
          (Several plot types are generated so you can choose the ones that suit your needs.)
        - Saving of aggregated CSV files used for plotting.
        - A summary report of the key findings.

Setup Instructions (Ubuntu):
    1. Update your package list and install Python3 and pip:
         sudo apt update
         sudo apt install python3 python3-pip

    2. Install the required Python libraries:
         pip3 install pandas numpy matplotlib seaborn

Usage:
    python3 experiment_analysis.py --input path/to/results.csv --output_folder analysis_output

"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import argparse

# Increase the DPI for high-quality plots (e.g., for publication)
plt.rcParams['figure.dpi'] = 300

def load_data(file_path):
    """
    Load CSV data into a pandas DataFrame.
    """
    try:
        df = pd.read_csv(file_path)
        print(f"Data loaded from {file_path}. Shape: {df.shape}")
        return df
    except Exception as e:
        print(f"Error loading data: {e}")
        raise

def compute_descriptive_statistics(df):
    """
    Compute and display basic descriptive statistics for the coverage columns.
    """
    coverage_columns = ['cov_class', 'cov_act', 'cov_method', 'cov_rv_method']
    stats = df[coverage_columns].describe()
    print("Descriptive Statistics for Coverage Columns:")
    print(stats)
    return stats

def plot_coverage_time_series(df, coverage_col, output_folder):
    """
    Plot the coverage over time for each testing tool.
    The data is aggregated by taking the maximum coverage per minute.
    Saves both the aggregated CSV and the plot.
    """
    # Create a new column representing time in minutes (rounded down)
    df['time_min'] = (df['time'] / 60).astype(int)
    # Aggregate: for each tool and minute, get the maximum coverage observed
    agg_df = df.groupby(['tool', 'time_min'])[coverage_col].max().reset_index()
   
    # Save the aggregated data to CSV
    agg_csv = os.path.join(output_folder, f"{coverage_col}_aggregated.csv")
    agg_df.to_csv(agg_csv, index=False)
    print(f"Aggregated data for {coverage_col} saved to {agg_csv}")
   
    # Create the line plot (with markers) using seaborn
    plt.figure(figsize=(12, 8))
    sns.lineplot(data=agg_df, x='time_min', y=coverage_col, hue='tool', marker="o")
    plt.xlabel("Time (minutes)")
    plt.ylabel(f"{coverage_col} (%)")
    plt.title(f"{coverage_col} Over Time")
    plt.xticks(rotation=45)
    plt.tight_layout()
   
    # Save the plot to a PNG file
    plot_file = os.path.join(output_folder, f"{coverage_col}_time_series.png")
    plt.savefig(plot_file, dpi=300)
    plt.close()
    print(f"Plot saved to {plot_file}")

def detect_plateau_time(tool_df, coverage_col, tolerance=0.01):
    """
    Detect the time (in seconds) at which the coverage for a given tool and
    coverage metric reaches within (1 - tolerance) of its maximum value.
    The first time this happens is considered the 'plateau' time.
   
    Parameters:
        tool_df: DataFrame filtered for a specific tool.
        coverage_col: Column name for the coverage metric.
        tolerance: Acceptable percentage difference (e.g., 0.01 for 1%).
   
    Returns:
        Plateau time in seconds, or None if not detected.
    """
    tool_df = tool_df.sort_values('time')
    max_cov = tool_df[coverage_col].max()
    threshold_value = (1 - tolerance) * max_cov
    plateau_df = tool_df[tool_df[coverage_col] >= threshold_value]
    if plateau_df.empty:
        return None
    plateau_time = plateau_df['time'].iloc[0]
    return plateau_time

def advanced_analysis(df, output_folder, tolerance=0.01):
    """
    Perform advanced analysis:
        - Aggregate coverage data per minute and compute incremental gains.
        - Detect plateau times for each tool and each coverage metric.
   
    Saves the aggregated data and incremental gain plots.
   
    Returns:
        A dictionary with plateau times for each tool and coverage metric.
    """
    plateau_results = {}
    coverage_metrics = ['cov_class', 'cov_act', 'cov_method', 'cov_rv_method']
    # Create a time in minutes column
    df['time_min'] = (df['time'] / 60).astype(int)
   
    for tool in df['tool'].unique():
        plateau_results[tool] = {}
        tool_df = df[df['tool'] == tool].sort_values('time')
        for cov in coverage_metrics:
            # Aggregate: for each minute, get the maximum coverage observed
            agg_df = tool_df.groupby('time_min')[cov].max().reset_index().sort_values('time_min')
            # Compute incremental gain (difference in coverage between successive minutes)
            agg_df[f'{cov}_diff'] = agg_df[cov].diff()
           
            # Save the aggregated data to CSV
            agg_csv = os.path.join(output_folder, f"{tool}_{cov}_aggregated.csv")
            agg_df.to_csv(agg_csv, index=False)
            print(f"Aggregated data for {tool} - {cov} saved to {agg_csv}")
           
            # Plot the incremental gain over time
            plt.figure(figsize=(12, 8))
            sns.lineplot(data=agg_df, x='time_min', y=f'{cov}_diff', marker="o")
            plt.xlabel("Time (minutes)")
            plt.ylabel(f"Incremental Gain in {cov} (%)")
            plt.title(f"Incremental Gain of {cov} Over Time for {tool}")
            plt.xticks(rotation=45)
            plt.tight_layout()
            plot_file = os.path.join(output_folder, f"{tool}_{cov}_incremental_gain.png")
            plt.savefig(plot_file, dpi=300)
            plt.close()
            print(f"Incremental gain plot for {tool} - {cov} saved to {plot_file}")
           
            # Detect plateau time for this tool and coverage metric
            plateau_time = detect_plateau_time(tool_df, cov, tolerance)
            plateau_results[tool][cov] = plateau_time
    return plateau_results

def generate_summary(df, plateau_results, output_folder, tolerance=0.01):
    """
    Generate a summary report of the analysis.
    The summary includes descriptive statistics and the detected plateau times
    for each tool and coverage metric.
   
    The report is saved as a text file in the output folder.
    """
    summary_lines = []
    summary_lines.append("Experiment Analysis Summary")
    summary_lines.append("=" * 50)
    summary_lines.append("\nDescriptive Statistics for Coverage Metrics:\n")
   
    coverage_columns = ['cov_class', 'cov_act', 'cov_method', 'cov_rv_method']
    stats = df[coverage_columns].describe()
    summary_lines.append(stats.to_string())
    summary_lines.append("\n\nPlateau Times (when coverage reaches within {:.0%} of maximum):\n".format(1 - tolerance))
   
    for tool in plateau_results:
        summary_lines.append(f"Tool: {tool}")
        for cov, plateau_time in plateau_results[tool].items():
            if plateau_time is not None:
                minutes = plateau_time / 60.0
                summary_lines.append(f"  {cov}: Plateau reached at ~{minutes:.2f} minutes")
            else:
                summary_lines.append(f"  {cov}: Plateau time not detected")
        summary_lines.append("")
   
    summary_text = "\n".join(summary_lines)
    summary_file = os.path.join(output_folder, "analysis_summary.txt")
    with open(summary_file, "w") as f:
        f.write(summary_text)
    print(f"Summary report saved to {summary_file}")

def main(input, output_folder):
    # Create the output folder if it doesn't already exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
   
    # Load the CSV data
    df = load_data(input)
   
    # Compute and display basic descriptive statistics
    print("Basic Descriptive Statistics:")
    compute_descriptive_statistics(df)
   
    # Generate time series plots for each coverage metric
    coverage_metrics = ['cov_class', 'cov_act', 'cov_method', 'cov_rv_method']
    for cov in coverage_metrics:
        print(f"Generating time series plot for {cov}...")
        plot_coverage_time_series(df, cov, output_folder)
   
    # Perform advanced analysis: incremental gains and plateau detection
    print("Performing advanced analysis: incremental gains and plateau detection...")
    plateau_results = advanced_analysis(df, output_folder, tolerance=0.01)
   
    # Generate and save the summary report
    print("Generating summary report...")
    generate_summary(df, plateau_results, output_folder, tolerance=0.01)

if __name__ == "__main__":
    # parser = argparse.ArgumentParser(description="Analyze experimental results from Android app testing.")
    # parser.add_argument("--input", type=str, required=True, help="Path to the CSV file with experiment results.")
    # parser.add_argument("--output_folder", type=str, required=True, help="Folder to save analysis outputs (plots, CSVs, summary).")
    # args = parser.parse_args()
    file_path = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/exp02_jca_coverage.csv"
    out_dir = "/home/pedro/tmp/results_chatgpt_walter"
    main(file_path, out_dir)