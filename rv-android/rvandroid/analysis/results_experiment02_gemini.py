import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

def analyze_coverage(df):
    """
    Analyzes coverage metrics across tools and time.
    """

    # Coverage over time
    plt.figure(figsize=(12, 6))
    sns.lineplot(x='time', y='cov_method', hue='tool', data=df)
    plt.title('Method Coverage Over Time')
    plt.xlabel('Time (seconds)')
    plt.ylabel('Method Coverage (%)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('coverage_over_time.png')

    # Coverage by tool
    plt.figure(figsize=(8, 6))
    sns.boxplot(x='tool', y='cov_method', data=df)
    plt.title('Method Coverage by Tool')
    plt.xlabel('Tool')
    plt.ylabel('Method Coverage (%)')
    plt.tight_layout()
    plt.savefig('coverage_by_tool.png')

def analyze_apks(df, top_n=10):
    """
    Analyzes coverage for top and bottom performing APKs.
    """

    apk_coverage = df.groupby('apk')['cov_method'].mean().sort_values(ascending=False)

    # Top APKs
    top_apks = apk_coverage.head(top_n)
    print("Top APKs:\n", top_apks)

    # Bottom APKs
    bottom_apks = apk_coverage.tail(top_n)
    print("\nBottom APKs:\n", bottom_apks)

    # Plotting
    plt.figure(figsize=(10, 6))
    top_apks.plot(kind='bar', color='green', label='Top')
    bottom_apks.plot(kind='bar', color='red', label='Bottom')
    plt.title('Average Method Coverage for Top/Bottom APKs')
    plt.xlabel('APK')
    plt.ylabel('Method Coverage (%)')
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()
    plt.savefig('top_bottom_apks.png')

def coverage_growth(df):
    """
    Determines time at which coverage plateaus.
    """

    coverage_changes = df.groupby(['tool', 'time'])['cov_method'].mean().reset_index()
    coverage_changes['diff'] = coverage_changes.groupby('tool')['cov_method'].diff()

    plateau_times = {}
    for tool in df['tool'].unique():
        tool_data = coverage_changes[coverage_changes['tool'] == tool]
        plateau_time = tool_data[tool_data['diff'] < 0.1]['time'].min()  # Threshold of 0.1% change
        plateau_times[tool] = plateau_time

    print("\nCoverage Plateau Times:\n", plateau_times)

def generate_summary(df):
    """
    Generates a summary of findings.
    """

    summary = "Android Test Coverage Analysis Summary\n\n"

    # Tool comparison
    summary += "Tool Comparison:\n"
    for tool in df['tool'].unique():
        avg_coverage = df[df['tool'] == tool]['cov_method'].mean()
        summary += f"- {tool}: Average Coverage = {avg_coverage:.2f}%\n"

    # APK analysis
    summary += "\nAPK Analysis:\n"
    top_apks = df.groupby('apk')['cov_method'].mean().nlargest(10)
    summary += "Top APKs:\n" + top_apks.to_string() + "\n"
    bottom_apks = df.groupby('apk')['cov_method'].mean().nsmallest(10)
    summary += "Bottom APKs:\n" + bottom_apks.to_string() + "\n"

    # Coverage plateau
    summary += "\nCoverage Plateau:\n"
    coverage_changes = df.groupby(['tool', 'time'])['cov_method'].mean().reset_index()
    coverage_changes['diff'] = coverage_changes.groupby('tool')['cov_method'].diff()
    for tool in df['tool'].unique():
        tool_data = coverage_changes[coverage_changes['tool'] == tool]
        plateau_time = tool_data[tool_data['diff'] < 0.1]['time'].min()
        summary += f"- {tool}: Coverage plateaus at {plateau_time} seconds.\n"

    return summary

if __name__ == "__main__":
    # Path to the CSV file with the results
    file_path = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/exp02_jca_coverage.csv"
    out_dir = "/home/pedro/tmp/results_gemini"
    
    # Load data
    df = pd.read_csv(file_path)

    # Create results directory
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    # Perform analysis
    analyze_coverage(df)
    analyze_apks(df)
    coverage_growth(df)
    summary = generate_summary(df)

    # Save summary
    with open(out_dir+'/summary.txt', 'w') as f:
        f.write(summary)

    print("Analysis complete. Results saved to 'results' directory.")