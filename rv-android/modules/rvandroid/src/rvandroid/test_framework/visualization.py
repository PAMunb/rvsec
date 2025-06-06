"""
Visualization module for test framework.

This module provides functionality for visualizing test
results in various formats such as charts and graphs.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager


def generate_visualizations(results: Dict[str, Any], output_dir: str) -> List[str]:
    """
    Generate visualizations for test results.
    
    Args:
        results: Analysis results dictionary
        output_dir: Directory to save visualizations
        
    Returns:
        List of generated visualization file paths
    """
    logger = LoggingManager.get_instance().get_logger(
        'test_framework.visualization',
        {CONTEXT_COMPONENT: 'Visualization'}
    )
    
    generated_files = []
    
    try:
        # Check for matplotlib and seaborn
        import matplotlib.pyplot as plt
        import seaborn as sns
        import numpy as np
        import pandas as pd
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Set styling
        sns.set(style="whitegrid")
        plt.rcParams.update({'font.size': 12})
        
        # Extract configuration comparisons
        comparisons = results.get('configuration_comparisons', {})
        
        # No data to visualize
        if not comparisons:
            logger.warning("No configuration comparison data to visualize")
            return generated_files
            
        # Prepare DataFrame from comparisons
        config_data = []
        for config_id, data in comparisons.items():
            row = {
                'configuration_id': config_id,
                'result_count': data.get('result_count', 0),
                'app_count': data.get('app_count', 0),
                'error_count': data.get('error_count', 0)
            }
            
            # Add average metrics
            avg_metrics = data.get('avg_metrics', {})
            for metric in ['avg_method_coverage', 'avg_activity_coverage', 'avg_mop_method_coverage',
                          'avg_execution_time', 'overall_score']:
                row[metric] = avg_metrics.get(metric, 0)
                
            # Extract tool and model information from config_id
            if '_' in config_id:
                parts = config_id.split('_')
                if len(parts) >= 2:
                    row['tool'] = parts[0]
                    if len(parts) >= 3:
                        row['llm_type'] = parts[1]
                        row['model'] = '_'.join(parts[2:])
                    else:
                        row['llm_type'] = 'unknown'
                        row['model'] = parts[1] if len(parts) > 1 else 'unknown'
                else:
                    row['tool'] = 'unknown'
                    row['llm_type'] = 'unknown'
                    row['model'] = 'unknown'
            else:
                row['tool'] = 'unknown'
                row['llm_type'] = 'unknown'
                row['model'] = 'unknown'
                
            config_data.append(row)
            
        # Convert to DataFrame
        df = pd.DataFrame(config_data)
        
        # 1. Generate bar chart for overall performance by tool
        fig, ax = plt.subplots(figsize=(12, 8))
        tool_performance = df.groupby('tool')['overall_score'].mean().reset_index()
        sns.barplot(x='tool', y='overall_score', data=tool_performance, ax=ax)
        ax.set_title('Average Overall Performance by Tool')
        ax.set_xlabel('Tool')
        ax.set_ylabel('Average Overall Score')
        
        # Save the figure
        tool_perf_path = os.path.join(output_dir, 'tool_performance.png')
        fig.savefig(tool_perf_path, bbox_inches='tight')
        plt.close(fig)
        generated_files.append(tool_perf_path)
        
        # 2. Generate coverage comparison chart
        fig, ax = plt.subplots(figsize=(14, 8))
        
        # Melt the DataFrame to get it in the right format for a grouped bar chart
        metrics = ['avg_method_coverage', 'avg_activity_coverage', 'avg_mop_method_coverage']
        melted_df = pd.melt(df, 
                            id_vars=['configuration_id', 'tool'], 
                            value_vars=metrics,
                            var_name='Metric', 
                            value_name='Value')
        
        # Group by tool and metric
        tool_metrics = melted_df.groupby(['tool', 'Metric'])['Value'].mean().reset_index()
        
        # Create the grouped bar chart
        sns.barplot(x='tool', y='Value', hue='Metric', data=tool_metrics, ax=ax)
        ax.set_title('Coverage Metrics by Tool')
        ax.set_xlabel('Tool')
        ax.set_ylabel('Average Value')
        ax.legend(title='Metric')
        
        # Save the figure
        coverage_path = os.path.join(output_dir, 'coverage_comparison.png')
        fig.savefig(coverage_path, bbox_inches='tight')
        plt.close(fig)
        generated_files.append(coverage_path)
        
        # 3. Generate LLM type comparison
        if 'llm_type' in df.columns and len(df['llm_type'].unique()) > 1:
            fig, ax = plt.subplots(figsize=(14, 8))
            
            # Group by LLM type
            llm_performance = df.groupby(['llm_type', 'tool'])['overall_score'].mean().reset_index()
            
            # Create the grouped bar chart
            sns.barplot(x='llm_type', y='overall_score', hue='tool', data=llm_performance, ax=ax)
            ax.set_title('Overall Performance by LLM Type and Tool')
            ax.set_xlabel('LLM Type')
            ax.set_ylabel('Average Overall Score')
            ax.legend(title='Tool')
            
            # Save the figure
            llm_path = os.path.join(output_dir, 'llm_comparison.png')
            fig.savefig(llm_path, bbox_inches='tight')
            plt.close(fig)
            generated_files.append(llm_path)
        
        # 4. Generate scatter plot of execution time vs coverage
        fig, ax = plt.subplots(figsize=(10, 8))
        
        scatter = ax.scatter(df['avg_execution_time'], 
                             df['avg_method_coverage'],
                             c=df['overall_score'], 
                             cmap='viridis', 
                             alpha=0.7,
                             s=100)
        
        # Add colorbar
        cbar = plt.colorbar(scatter)
        cbar.set_label('Overall Score')
        
        # Add labels
        ax.set_title('Execution Time vs Method Coverage')
        ax.set_xlabel('Average Execution Time (s)')
        ax.set_ylabel('Average Method Coverage (%)')
        
        # Add grid
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # Save the figure
        scatter_path = os.path.join(output_dir, 'time_vs_coverage.png')
        fig.savefig(scatter_path, bbox_inches='tight')
        plt.close(fig)
        generated_files.append(scatter_path)
        
        # 5. Generate heatmap of correlation between metrics
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Select numeric columns
        numeric_cols = ['avg_method_coverage', 'avg_activity_coverage', 'avg_mop_method_coverage',
                       'avg_execution_time', 'overall_score', 'error_count']
        
        # Calculate correlation matrix
        corr_matrix = df[numeric_cols].corr()
        
        # Create heatmap
        sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', ax=ax)
        ax.set_title('Correlation Between Metrics')
        
        # Save the figure
        heatmap_path = os.path.join(output_dir, 'metrics_correlation.png')
        fig.savefig(heatmap_path, bbox_inches='tight')
        plt.close(fig)
        generated_files.append(heatmap_path)
        
        # 6. Generate combined visualization with top performers
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Top Performers Analysis', fontsize=16)
        
        # Top performers by method coverage
        top_method = df.nlargest(5, 'avg_method_coverage')
        sns.barplot(x='configuration_id', y='avg_method_coverage', data=top_method, ax=axes[0, 0])
        axes[0, 0].set_title('Top Method Coverage')
        axes[0, 0].set_xticklabels(axes[0, 0].get_xticklabels(), rotation=45, ha='right')
        
        # Top performers by activity coverage
        top_activity = df.nlargest(5, 'avg_activity_coverage')
        sns.barplot(x='configuration_id', y='avg_activity_coverage', data=top_activity, ax=axes[0, 1])
        axes[0, 1].set_title('Top Activity Coverage')
        axes[0, 1].set_xticklabels(axes[0, 1].get_xticklabels(), rotation=45, ha='right')
        
        # Top performers by MOP method coverage
        top_mop = df.nlargest(5, 'avg_mop_method_coverage')
        sns.barplot(x='configuration_id', y='avg_mop_method_coverage', data=top_mop, ax=axes[1, 0])
        axes[1, 0].set_title('Top MOP Method Coverage')
        axes[1, 0].set_xticklabels(axes[1, 0].get_xticklabels(), rotation=45, ha='right')
        
        # Top performers by overall score
        top_overall = df.nlargest(5, 'overall_score')
        sns.barplot(x='configuration_id', y='overall_score', data=top_overall, ax=axes[1, 1])
        axes[1, 1].set_title('Top Overall Scores')
        axes[1, 1].set_xticklabels(axes[1, 1].get_xticklabels(), rotation=45, ha='right')
        
        # Adjust layout
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        # Save the figure
        top_path = os.path.join(output_dir, 'top_performers.png')
        fig.savefig(top_path, bbox_inches='tight')
        plt.close(fig)
        generated_files.append(top_path)
        
        # Generate index HTML file
        generate_html_index(generated_files, output_dir)
        generated_files.append(os.path.join(output_dir, 'index.html'))
        
        logger.info(f"Generated {len(generated_files)} visualization files")
        return generated_files
    except ImportError as e:
        logger.error(f"Required visualization packages not found: {str(e)}")
        logger.error("Install matplotlib, seaborn, numpy, and pandas for visualizations")
        return generated_files
    except Exception as e:
        logger.error(f"Error generating visualizations: {str(e)}")
        return generated_files


def generate_html_index(image_files: List[str], output_dir: str) -> str:
    """
    Generate an HTML index file for the visualizations.
    
    Args:
        image_files: List of image file paths
        output_dir: Directory containing the images
        
    Returns:
        Path to the generated HTML file
    """
    # Create HTML content
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>RV-Android Test Framework Analysis</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                line-height: 1.6;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background-color: #fff;
                padding: 20px;
                border-radius: 5px;
                box-shadow: 0 0 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                text-align: center;
                margin-bottom: 30px;
            }
            h2 {
                color: #444;
                margin-top: 30px;
            }
            .visualization {
                margin-bottom: 40px;
                text-align: center;
            }
            .visualization img {
                max-width: 100%;
                height: auto;
                border: 1px solid #ddd;
                border-radius: 4px;
                box-shadow: 0 0 5px rgba(0,0,0,0.1);
            }
            .caption {
                margin-top: 10px;
                font-style: italic;
                color: #666;
            }
            .footer {
                margin-top: 40px;
                text-align: center;
                font-size: 0.8em;
                color: #777;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>RV-Android Test Framework Analysis</h1>
            <p>
                This report contains visualizations generated from the test results
                to help understand the performance and characteristics of different
                LLM configurations.
            </p>
    """
    
    # Add each visualization
    for image_file in image_files:
        if not os.path.exists(image_file):
            continue
            
        filename = os.path.basename(image_file)
        name_without_ext = os.path.splitext(filename)[0].replace('_', ' ').title()
        
        html_content += f"""
            <div class="visualization">
                <h2>{name_without_ext}</h2>
                <img src="{filename}" alt="{name_without_ext}">
                <p class="caption">Figure: {name_without_ext}</p>
            </div>
        """
    
    # Add footer and close tags
    html_content += f"""
            <div class="footer">
                <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>RV-Android Test Framework</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Write to file
    output_path = os.path.join(output_dir, 'index.html')
    with open(output_path, 'w') as f:
        f.write(html_content)
        
    return output_path