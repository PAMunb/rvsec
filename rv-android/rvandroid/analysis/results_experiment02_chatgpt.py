# Install required libraries (Run the following commands on Ubuntu terminal):
# sudo apt update
# sudo apt install python3-pip
# pip3 install pandas matplotlib seaborn numpy

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

def load_data(file_path):
    """
    Load the CSV file into a pandas DataFrame.
    """
    return pd.read_csv(file_path)

def basic_statistics(df):
    """
    Perform basic statistical analysis on the coverage columns.
    """
    stats = df[['cov_class', 'cov_act', 'cov_method', 'cov_rv_method']].describe()
    return stats

def coverage_over_time(df, tool_name):
    """
    Plot the coverage over time for a specific tool.
    """
    df_tool = df[df['tool'] == tool_name]
    
    plt.figure(figsize=(10, 6))
    
    # Plot the coverage of classes, activities, methods, and special methods over time
    plt.plot(df_tool['time'], df_tool['cov_class'], label='Cov Class', alpha=0.7)
    plt.plot(df_tool['time'], df_tool['cov_act'], label='Cov Act', alpha=0.7)
    plt.plot(df_tool['time'], df_tool['cov_method'], label='Cov Method', alpha=0.7)
    plt.plot(df_tool['time'], df_tool['cov_rv_method'], label='Cov RV Method', alpha=0.7)
    
    plt.xlabel('Time (seconds)', fontsize=12)
    plt.ylabel('Coverage (%)', fontsize=12)
    plt.title(f'Coverage over Time - {tool_name}', fontsize=14)
    plt.legend()
    plt.grid(True)
    
    plt.tight_layout()
    plt.xticks(rotation=45)  # Rotate x labels for better visibility
    plt.show()

def find_stopping_point(df, tool_name, threshold=1):
    """
    Find the point where the coverage stops growing significantly (threshold in percentage).
    """
    df_tool = df[df['tool'] == tool_name]
    
    coverage_increase = df_tool['cov_class'].diff().abs()
    stopping_point = df_tool[coverage_increase < threshold].iloc[0]['time']  # Find the first time when change is less than threshold
    return stopping_point

def generate_plots(df, tools):
    """
    Generate various plots for coverage over time for all tools.
    """
    for tool in tools:
        coverage_over_time(df, tool)
        tool_data = df[df['tool'] == tool]
        tool_data.to_csv(f'{tool}_coverage_data.csv', index=False)  # Save the data used for the plot

def coverage_statistics(df):
    """
    Calculate and print the average coverage values for each tool and class of coverage.
    """
    coverage_means = df.groupby('tool')[['cov_class', 'cov_act', 'cov_method', 'cov_rv_method']].mean()
    print("Average Coverage per Tool:")
    print(coverage_means)
    
def summary(df):
    """
    Provide a summary of the experiment findings.
    """
    tools = df['tool'].unique()
    print(f"Number of tools used: {len(tools)}")
    
    for tool in tools:
        stopping_point = find_stopping_point(df, tool)
        print(f"Tool: {tool} - Coverage stops growing significantly at {stopping_point} seconds.")
    
    coverage_statistics(df)

def main(file_path):
    """
    Main function to execute the analysis and generate reports.
    """
    # Load data
    df = load_data(file_path)
    
    # Get the unique tools used in the experiment
    tools = df['tool'].unique()
    
    # Generate basic statistics
    stats = basic_statistics(df)
    print("Basic Statistics:")
    print(stats)
    
    # Generate plots for each tool
    generate_plots(df, tools)
    
    # Summary of findings
    summary(df)

# Run the script with the following structure:
if __name__ == '__main__':
    # Specify the path to your CSV file here
    file_path = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/exp02_jca_coverage.csv"
    main(file_path)
