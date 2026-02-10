"""
Dashboard module for test framework.

This module provides a web-based dashboard for interactive exploration
of test results and analysis.
"""

import os
import json
import logging
import base64
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import webbrowser
from pathlib import Path

from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class Dashboard:
    """
    Web-based dashboard for interactive result exploration.
    
    Provides a HTML/JavaScript dashboard for visualizing test results,
    with interactive charts and filtering capabilities.
    
    ### Key Responsibilities:
    - Generates a self-contained HTML dashboard
    - Provides interactive exploration of test results
    - Enables filtering and comparison of configurations
    - Visualizes metrics, correlations, and anomalies
    """
    
    def __init__(self):
        """Initialize the dashboard generator."""
        # Set up logging
        self.logger = LoggingManager.get_instance().get_logger(
            'test_framework.dashboard',
            {CONTEXT_COMPONENT: 'Dashboard'}
        )
        
        # Define template directories
        self.template_dir = os.path.join(os.path.dirname(__file__), 'dashboard_templates')
        
    def generate_dashboard(self, results: Dict[str, Any], output_dir: str) -> str:
        """
        Generate an interactive dashboard for test results.
        
        Args:
            results: Analysis results dictionary
            output_dir: Directory to save the dashboard files
            
        Returns:
            Path to the main dashboard HTML file
        """
        try:
            # Create output directory
            os.makedirs(output_dir, exist_ok=True)
            
            # Create dashboard dir in output_dir if it doesn't exist
            dashboard_dir = os.path.join(output_dir, 'dashboard')
            os.makedirs(dashboard_dir, exist_ok=True)
            
            # Check if template directory exists or use built-in templates
            if not os.path.exists(self.template_dir):
                # Use built-in templates
                template_html = self._get_embedded_template_html()
                template_css = self._get_embedded_template_css()
                template_js = self._get_embedded_template_js()
            else:
                # Read templates from files
                with open(os.path.join(self.template_dir, 'template.html'), 'r') as f:
                    template_html = f.read()
                    
                with open(os.path.join(self.template_dir, 'styles.css'), 'r') as f:
                    template_css = f.read()
                    
                with open(os.path.join(self.template_dir, 'dashboard.js'), 'r') as f:
                    template_js = f.read()
            
            # Prepare data for the dashboard
            dashboard_data = self._prepare_dashboard_data(results)
            
            # Serialize data to JSON
            data_json = json.dumps(dashboard_data)
            
            # Replace placeholders in templates
            html = template_html.replace('{{DASHBOARD_TITLE}}', dashboard_data.get('title', 'Test Results Dashboard'))
            html = html.replace('{{DASHBOARD_DESCRIPTION}}', dashboard_data.get('description', ''))
            html = html.replace('{{DASHBOARD_STYLES}}', template_css)
            html = html.replace('{{DASHBOARD_SCRIPT}}', template_js)
            html = html.replace('{{DASHBOARD_DATA}}', data_json)
            
            # Write HTML file
            dashboard_file = os.path.join(dashboard_dir, 'index.html')
            with open(dashboard_file, 'w') as f:
                f.write(html)
            
            # Copy visualization images if they exist
            vis_dir = os.path.join(output_dir, 'visualizations')
            if os.path.exists(vis_dir):
                dashboard_vis_dir = os.path.join(dashboard_dir, 'visualizations')
                os.makedirs(dashboard_vis_dir, exist_ok=True)
                
                # Copy all PNG files
                for file in os.listdir(vis_dir):
                    if file.endswith('.png'):
                        src_file = os.path.join(vis_dir, file)
                        dst_file = os.path.join(dashboard_vis_dir, file)
                        
                        # Read source file and write to destination
                        with open(src_file, 'rb') as src:
                            with open(dst_file, 'wb') as dst:
                                dst.write(src.read())
            
            self.logger.info(f"Dashboard generated at: {dashboard_file}")
            return dashboard_file
            
        except Exception as e:
            self.logger.error(f"Error generating dashboard: {str(e)}")
            return ""
    
    def _prepare_dashboard_data(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare data for dashboard visualization.
        
        Args:
            results: Analysis results dictionary
            
        Returns:
            Processed data for dashboard
        """
        dashboard_data = {
            'title': 'RV-Android Test Framework Results',
            'description': f'Analysis generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_configs': results.get('total_configs', 0),
                'total_apps': results.get('total_apps', 0),
                'total_results': results.get('total_results', 0)
            },
            'configurations': [],
            'metrics': [],
            'top_performers': {},
            'tools': [],
            'correlations': [],
            'anomalies': [],
            'recommendations': []
        }
        
        # Extract configuration data
        comparisons = results.get('configuration_comparisons', {})
        for config_id, data in comparisons.items():
            config_entry = {
                'id': config_id,
                'metrics': data.get('avg_metrics', {}),
                'app_count': data.get('app_count', 0),
                'error_count': data.get('error_count', 0),
                'result_count': data.get('result_count', 0)
            }
            
            # Extract tool and other components from config_id
            parts = config_id.split('_') if '_' in config_id else [config_id]
            config_entry['tool'] = parts[0] if len(parts) > 0 else ''
            config_entry['llm_type'] = parts[1] if len(parts) > 1 else ''
            config_entry['llm_model'] = '_'.join(parts[2:]) if len(parts) > 2 else ''
            
            dashboard_data['configurations'].append(config_entry)
        
        # Extract metric names
        if dashboard_data['configurations']:
            metrics = list(dashboard_data['configurations'][0].get('metrics', {}).keys())
            dashboard_data['metrics'] = [
                {'id': m, 'name': m.replace('avg_', '').replace('_', ' ').title()} 
                for m in metrics
            ]
        
        # Extract top performers
        top_configs = results.get('top_configurations', {})
        for metric, configs in top_configs.items():
            dashboard_data['top_performers'][metric] = configs[:5]
        
        # Extract tool data
        tool_metrics = {}
        for config in dashboard_data['configurations']:
            tool = config.get('tool', '')
            if tool:
                if tool not in tool_metrics:
                    tool_metrics[tool] = {
                        'id': tool,
                        'config_count': 0,
                        'app_count': 0,
                        'error_count': 0,
                        'metrics': {m: [] for m in metrics} if 'metrics' in locals() else {}
                    }
                
                # Update counts
                tool_metrics[tool]['config_count'] += 1
                tool_metrics[tool]['app_count'] += config.get('app_count', 0)
                tool_metrics[tool]['error_count'] += config.get('error_count', 0)
                
                # Update metrics
                for metric, value in config.get('metrics', {}).items():
                    if metric in tool_metrics[tool]['metrics']:
                        tool_metrics[tool]['metrics'][metric].append(value)
        
        # Calculate average metrics for tools
        for tool_id, tool_data in tool_metrics.items():
            avg_metrics = {}
            for metric, values in tool_data['metrics'].items():
                if values:
                    avg_metrics[metric] = sum(values) / len(values)
            
            tool_data['avg_metrics'] = avg_metrics
            dashboard_data['tools'].append(tool_data)
        
        # Add correlation data if available
        correlation_report = results.get('correlation_report', {})
        if correlation_report:
            correlations = correlation_report.get('top_correlations', [])
            dashboard_data['correlations'] = correlations
            
            # Add recommendations
            recommendations = correlation_report.get('recommendations', {})
            for char_name, recs in recommendations.items():
                for rec in recs:
                    rec_entry = {
                        'characteristic': char_name,
                        'config_id': rec.get('config_id', ''),
                        'correlation': rec.get('correlation', 0),
                        'confidence': rec.get('confidence', ''),
                        'explanation': rec.get('explanation', '')
                    }
                    dashboard_data['recommendations'].append(rec_entry)
        
        # Add anomaly data if available
        anomaly_report = results.get('anomaly_report', {})
        if anomaly_report:
            anomalies = anomaly_report.get('anomalies', [])
            dashboard_data['anomalies'] = anomalies
        
        return dashboard_data
    
    def _get_embedded_template_html(self) -> str:
        """
        Get the embedded HTML template for the dashboard.
        
        Returns:
            HTML template as string
        """
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{DASHBOARD_TITLE}}</title>
    <style>
        {{DASHBOARD_STYLES}}
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.7.1/dist/chart.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.0.0"></script>
</head>
<body>
    <div class="dashboard">
        <header>
            <h1>{{DASHBOARD_TITLE}}</h1>
            <p>{{DASHBOARD_DESCRIPTION}}</p>
        </header>
        
        <nav id="dashboard-nav">
            <ul>
                <li><a href="#summary" class="active">Summary</a></li>
                <li><a href="#configurations">Configurations</a></li>
                <li><a href="#metrics">Metrics</a></li>
                <li><a href="#tools">Tools</a></li>
                <li><a href="#correlations">Correlations</a></li>
                <li><a href="#anomalies">Anomalies</a></li>
                <li><a href="#recommendations">Recommendations</a></li>
            </ul>
        </nav>
        
        <main>
            <section id="summary" class="dashboard-section active">
                <h2>Summary</h2>
                <div class="summary-stats">
                    <div class="stat-card" id="total-configs">
                        <h3>Total Configurations</h3>
                        <div class="stat-value">-</div>
                    </div>
                    <div class="stat-card" id="total-apps">
                        <h3>Total Apps</h3>
                        <div class="stat-value">-</div>
                    </div>
                    <div class="stat-card" id="total-results">
                        <h3>Total Results</h3>
                        <div class="stat-value">-</div>
                    </div>
                </div>
                
                <div class="chart-container">
                    <h3>Top Performers by Metric</h3>
                    <div id="top-performers-chart-container">
                        <select id="top-performers-metric">
                            <!-- Will be populated by JavaScript -->
                        </select>
                        <div class="chart-wrapper">
                            <canvas id="top-performers-chart"></canvas>
                        </div>
                    </div>
                </div>
                
                <div class="chart-container">
                    <h3>Tool Comparison</h3>
                    <div id="tool-comparison-container">
                        <select id="tool-comparison-metric">
                            <!-- Will be populated by JavaScript -->
                        </select>
                        <div class="chart-wrapper">
                            <canvas id="tool-comparison-chart"></canvas>
                        </div>
                    </div>
                </div>
                
                <!-- Only show if visualizations exist -->
                <div id="visualizations-container">
                    <h3>Visualizations</h3>
                    <div class="visualizations-grid" id="visualizations-grid">
                        <!-- Will be populated by JavaScript if visualizations exist -->
                    </div>
                </div>
            </section>
            
            <section id="configurations" class="dashboard-section">
                <h2>Configurations</h2>
                
                <div class="filter-bar">
                    <div class="filter-group">
                        <label for="config-filter-tool">Tool:</label>
                        <select id="config-filter-tool">
                            <option value="all">All</option>
                            <!-- Will be populated by JavaScript -->
                        </select>
                    </div>
                    <div class="filter-group">
                        <label for="config-filter-llm">LLM Type:</label>
                        <select id="config-filter-llm">
                            <option value="all">All</option>
                            <!-- Will be populated by JavaScript -->
                        </select>
                    </div>
                    <div class="filter-group">
                        <label for="config-filter-metric">Sort by:</label>
                        <select id="config-filter-metric">
                            <!-- Will be populated by JavaScript -->
                        </select>
                    </div>
                    <div class="filter-group">
                        <label for="config-filter-order">Order:</label>
                        <select id="config-filter-order">
                            <option value="desc">Highest First</option>
                            <option value="asc">Lowest First</option>
                        </select>
                    </div>
                </div>
                
                <div class="configurations-grid" id="configurations-grid">
                    <!-- Will be populated by JavaScript -->
                </div>
            </section>
            
            <section id="metrics" class="dashboard-section">
                <h2>Metrics Comparison</h2>
                
                <div class="filter-bar">
                    <div class="filter-group">
                        <label for="metrics-filter-configs">Configurations:</label>
                        <select id="metrics-filter-configs" multiple>
                            <!-- Will be populated by JavaScript -->
                        </select>
                    </div>
                    <div class="filter-group">
                        <button id="metrics-filter-reset">Reset Selection</button>
                    </div>
                </div>
                
                <div class="chart-container">
                    <div class="chart-wrapper">
                        <canvas id="metrics-comparison-chart"></canvas>
                    </div>
                </div>
                
                <div class="chart-container">
                    <h3>Success Rate vs. Coverage</h3>
                    <div class="chart-wrapper">
                        <canvas id="success-vs-coverage-chart"></canvas>
                    </div>
                </div>
            </section>
            
            <section id="tools" class="dashboard-section">
                <h2>Tool Analysis</h2>
                
                <div class="tools-grid" id="tools-grid">
                    <!-- Will be populated by JavaScript -->
                </div>
                
                <div class="chart-container">
                    <h3>Metrics by Tool</h3>
                    <div id="tool-metrics-container">
                        <select id="tool-metrics-metric">
                            <!-- Will be populated by JavaScript -->
                        </select>
                        <div class="chart-wrapper">
                            <canvas id="tool-metrics-chart"></canvas>
                        </div>
                    </div>
                </div>
            </section>
            
            <section id="correlations" class="dashboard-section">
                <h2>Correlations</h2>
                
                <div class="correlations-table-container">
                    <table class="correlations-table" id="correlations-table">
                        <thead>
                            <tr>
                                <th>App Characteristic</th>
                                <th>Configuration</th>
                                <th>Metric</th>
                                <th>Correlation</th>
                                <th>Confidence</th>
                            </tr>
                        </thead>
                        <tbody>
                            <!-- Will be populated by JavaScript -->
                        </tbody>
                    </table>
                </div>
                
                <div class="chart-container">
                    <h3>Top Correlations</h3>
                    <div class="chart-wrapper">
                        <canvas id="correlations-chart"></canvas>
                    </div>
                </div>
            </section>
            
            <section id="anomalies" class="dashboard-section">
                <h2>Anomalies</h2>
                
                <div class="anomalies-table-container">
                    <table class="anomalies-table" id="anomalies-table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Type</th>
                                <th>Metric</th>
                                <th>Expected Value</th>
                                <th>Actual Value</th>
                                <th>Deviation</th>
                                <th>Severity</th>
                            </tr>
                        </thead>
                        <tbody>
                            <!-- Will be populated by JavaScript -->
                        </tbody>
                    </table>
                </div>
                
                <div class="chart-container">
                    <h3>Anomalies by Type</h3>
                    <div class="chart-wrapper">
                        <canvas id="anomalies-by-type-chart"></canvas>
                    </div>
                </div>
                
                <div class="chart-container">
                    <h3>Anomalies by Severity</h3>
                    <div class="chart-wrapper">
                        <canvas id="anomalies-by-severity-chart"></canvas>
                    </div>
                </div>
            </section>
            
            <section id="recommendations" class="dashboard-section">
                <h2>Recommendations</h2>
                
                <div class="recommendations-container" id="recommendations-container">
                    <!-- Will be populated by JavaScript -->
                </div>
            </section>
        </main>
        
        <footer>
            <p>RV-Android Test Framework Dashboard | Generated: <span id="generation-time"></span></p>
        </footer>
    </div>
    
    <script>
        // Dashboard data
        const dashboardData = {{DASHBOARD_DATA}};
        
        // Dashboard logic
        {{DASHBOARD_SCRIPT}}
    </script>
</body>
</html>
"""
    
    def _get_embedded_template_css(self) -> str:
        """
        Get the embedded CSS template for the dashboard.
        
        Returns:
            CSS template as string
        """
        return """
/* Reset and base styles */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.6;
    color: #333;
    background-color: #f5f5f5;
}

.dashboard {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
}

/* Header styles */
header {
    background-color: #1a73e8;
    color: white;
    padding: 20px;
    text-align: center;
}

header h1 {
    font-size: 28px;
    margin-bottom: 10px;
}

header p {
    font-size: 16px;
    opacity: 0.9;
}

/* Navigation styles */
nav {
    background-color: white;
    border-bottom: 1px solid #ddd;
    position: sticky;
    top: 0;
    z-index: 100;
}

nav ul {
    display: flex;
    list-style: none;
    padding: 0 20px;
    overflow-x: auto;
}

nav ul li {
    margin-right: 10px;
}

nav ul li a {
    display: block;
    padding: 15px 20px;
    color: #333;
    text-decoration: none;
    border-bottom: 3px solid transparent;
    font-weight: 500;
    white-space: nowrap;
}

nav ul li a:hover {
    color: #1a73e8;
}

nav ul li a.active {
    color: #1a73e8;
    border-bottom-color: #1a73e8;
}

/* Main content styles */
main {
    flex: 1;
    padding: 20px;
    max-width: 1400px;
    margin: 0 auto;
    width: 100%;
}

.dashboard-section {
    display: none;
    animation: fadeIn 0.3s ease-in-out;
}

.dashboard-section.active {
    display: block;
}

@keyframes fadeIn {
    0% { opacity: 0; }
    100% { opacity: 1; }
}

h2 {
    margin-bottom: 20px;
    color: #333;
    font-size: 24px;
    padding-bottom: 10px;
    border-bottom: 1px solid #eee;
}

h3 {
    margin-bottom: 15px;
    color: #444;
    font-size: 20px;
}

/* Summary section styles */
.summary-stats {
    display: flex;
    justify-content: space-between;
    margin-bottom: 30px;
    flex-wrap: wrap;
}

.stat-card {
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    padding: 20px;
    flex: 1;
    margin: 0 10px 20px;
    min-width: 200px;
    text-align: center;
}

.stat-card h3 {
    font-size: 16px;
    margin-bottom: 10px;
    color: #666;
}

.stat-value {
    font-size: 36px;
    font-weight: 700;
    color: #1a73e8;
}

/* Chart container styles */
.chart-container {
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    padding: 20px;
    margin-bottom: 30px;
}

.chart-container h3 {
    margin-bottom: 20px;
    padding-bottom: 10px;
    border-bottom: 1px solid #eee;
}

.chart-wrapper {
    width: 100%;
    height: 400px;
    position: relative;
}

/* Filter bar styles */
.filter-bar {
    display: flex;
    margin-bottom: 20px;
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    padding: 15px;
    flex-wrap: wrap;
}

.filter-group {
    margin-right: 20px;
    margin-bottom: 10px;
}

.filter-group label {
    display: block;
    margin-bottom: 5px;
    font-weight: 500;
    color: #666;
}

.filter-group select, .filter-group input {
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    min-width: 150px;
}

.filter-group select[multiple] {
    height: 120px;
}

.filter-group button {
    padding: 8px 16px;
    background-color: #1a73e8;
    color: white;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-weight: 500;
    margin-top: 24px;
}

.filter-group button:hover {
    background-color: #1558b3;
}

/* Configurations grid styles */
.configurations-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.config-card {
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    padding: 20px;
    transition: transform 0.2s ease;
}

.config-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 5px 15px rgba(0,0,0,0.1);
}

.config-card h3 {
    margin-bottom: 15px;
    padding-bottom: 10px;
    border-bottom: 1px solid #eee;
    font-size: 18px;
}

.config-card-details {
    margin-bottom: 15px;
}

.config-card-detail {
    display: flex;
    justify-content: space-between;
    margin-bottom: 5px;
}

.detail-label {
    color: #666;
    font-weight: 500;
}

.detail-value {
    font-weight: 600;
}

.config-card-metrics {
    margin-top: 15px;
}

.metric-item {
    display: flex;
    justify-content: space-between;
    margin-bottom: 8px;
}

.metric-bar {
    background-color: #f0f0f0;
    height: 6px;
    border-radius: 3px;
    margin-top: 5px;
    position: relative;
    overflow: hidden;
}

.metric-fill {
    position: absolute;
    top: 0;
    left: 0;
    height: 100%;
    background-color: #1a73e8;
}

/* Tools grid styles */
.tools-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}

.tool-card {
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    padding: 20px;
}

.tool-card h3 {
    margin-bottom: 15px;
    padding-bottom: 10px;
    border-bottom: 1px solid #eee;
    font-size: 18px;
}

/* Table styles */
.correlations-table-container, .anomalies-table-container {
    overflow-x: auto;
    margin-bottom: 30px;
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    padding: 20px;
}

table {
    width: 100%;
    border-collapse: collapse;
}

th, td {
    padding: 12px 15px;
    text-align: left;
    border-bottom: 1px solid #ddd;
}

th {
    background-color: #f9f9f9;
    color: #333;
    font-weight: 600;
}

tbody tr:hover {
    background-color: #f5f5f5;
}

/* Recommendations styles */
.recommendations-container {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 20px;
}

.recommendation-card {
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    padding: 20px;
}

.recommendation-card h3 {
    margin-bottom: 15px;
    padding-bottom: 10px;
    border-bottom: 1px solid #eee;
    font-size: 18px;
}

.recommendation-card .confidence {
    display: inline-block;
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 14px;
    font-weight: 600;
    margin-top: 10px;
}

.confidence.high {
    background-color: #d4edda;
    color: #155724;
}

.confidence.medium {
    background-color: #fff3cd;
    color: #856404;
}

.confidence.low {
    background-color: #f8d7da;
    color: #721c24;
}

/* Visualizations grid */
.visualizations-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
    gap: 20px;
}

.visualization-card {
    background-color: white;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    padding: 20px;
    text-align: center;
}

.visualization-card h4 {
    margin-bottom: 15px;
    color: #444;
}

.visualization-image {
    max-width: 100%;
    height: auto;
    border: 1px solid #eee;
    border-radius: 4px;
}

/* Footer styles */
footer {
    background-color: #333;
    color: white;
    text-align: center;
    padding: 20px;
    margin-top: 40px;
}

/* Responsive adjustments */
@media (max-width: 768px) {
    .summary-stats {
        flex-direction: column;
    }
    
    .stat-card {
        width: 100%;
        margin: 0 0 20px 0;
    }
    
    .filter-bar {
        flex-direction: column;
    }
    
    .filter-group {
        width: 100%;
        margin-right: 0;
    }
    
    .configurations-grid, .tools-grid, .recommendations-container {
        grid-template-columns: 1fr;
    }
}
"""
    
    def _get_embedded_template_js(self) -> str:
        """
        Get the embedded JavaScript template for the dashboard.
        
        Returns:
            JavaScript template as string
        """
        return """
// Initialize dashboard when DOM is fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Set up navigation
    setupNavigation();
    
    // Display dashboard data
    displayDashboardData(dashboardData);
    
    // Set generation time
    document.getElementById('generation-time').textContent = new Date(dashboardData.timestamp).toLocaleString();
});

// Set up navigation between dashboard sections
function setupNavigation() {
    const navLinks = document.querySelectorAll('#dashboard-nav a');
    const sections = document.querySelectorAll('.dashboard-section');
    
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            // Remove active class from all links and sections
            navLinks.forEach(l => l.classList.remove('active'));
            sections.forEach(s => s.classList.remove('active'));
            
            // Add active class to clicked link and corresponding section
            this.classList.add('active');
            const targetId = this.getAttribute('href').substring(1);
            document.getElementById(targetId).classList.add('active');
        });
    });
}

// Display dashboard data in the UI
function displayDashboardData(data) {
    // Display summary statistics
    document.getElementById('total-configs').querySelector('.stat-value').textContent = 
        data.summary.total_configs;
    document.getElementById('total-apps').querySelector('.stat-value').textContent = 
        data.summary.total_apps;
    document.getElementById('total-results').querySelector('.stat-value').textContent = 
        data.summary.total_results;
    
    // Populate metrics dropdown for top performers chart
    populateMetricsDropdown(data.metrics, 'top-performers-metric');
    
    // Create top performers chart with default metric
    if (data.metrics.length > 0) {
        createTopPerformersChart(data, data.metrics[0].id);
        
        // Update chart when metric changes
        document.getElementById('top-performers-metric').addEventListener('change', function() {
            createTopPerformersChart(data, this.value);
        });
    }
    
    // Populate metrics dropdown for tool comparison chart
    populateMetricsDropdown(data.metrics, 'tool-comparison-metric');
    
    // Create tool comparison chart with default metric
    if (data.metrics.length > 0 && data.tools.length > 0) {
        createToolComparisonChart(data, data.metrics[0].id);
        
        // Update chart when metric changes
        document.getElementById('tool-comparison-metric').addEventListener('change', function() {
            createToolComparisonChart(data, this.value);
        });
    }
    
    // Show visualizations if they exist
    checkForVisualizations();
    
    // Populate configurations section
    populateConfigurationsSection(data);
    
    // Populate metrics comparison section
    populateMetricsSection(data);
    
    // Populate tools section
    populateToolsSection(data);
    
    // Populate correlations section
    populateCorrelationsSection(data);
    
    // Populate anomalies section
    populateAnomaliesSection(data);
    
    // Populate recommendations section
    populateRecommendationsSection(data);
}

// Populate metrics dropdown
function populateMetricsDropdown(metrics, dropdownId) {
    const dropdown = document.getElementById(dropdownId);
    dropdown.innerHTML = '';
    
    metrics.forEach(metric => {
        const option = document.createElement('option');
        option.value = metric.id;
        option.textContent = metric.name;
        dropdown.appendChild(option);
    });
}

// Create top performers chart
function createTopPerformersChart(data, metricId) {
    const topPerformers = data.top_performers[metricId] || [];
    
    if (topPerformers.length === 0) {
        document.getElementById('top-performers-chart-container').innerHTML = 
            '<p>No data available for this metric.</p>';
        return;
    }
    
    const canvas = document.getElementById('top-performers-chart');
    const ctx = canvas.getContext('2d');
    
    // Clear any existing chart
    if (canvas.chart) {
        canvas.chart.destroy();
    }
    
    // Get configuration data for top performers
    const chartData = [];
    const chartLabels = [];
    
    topPerformers.forEach(configId => {
        const config = data.configurations.find(c => c.id === configId);
        if (config) {
            chartLabels.push(config.id);
            chartData.push(config.metrics[metricId] || 0);
        }
    });
    
    // Create new chart
    canvas.chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: chartLabels,
            datasets: [{
                label: getMetricName(data.metrics, metricId),
                data: chartData,
                backgroundColor: 'rgba(26, 115, 232, 0.7)',
                borderColor: 'rgba(26, 115, 232, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            }
        }
    });
}

// Create tool comparison chart
function createToolComparisonChart(data, metricId) {
    if (data.tools.length === 0) {
        document.getElementById('tool-comparison-container').innerHTML = 
            '<p>No tool data available.</p>';
        return;
    }
    
    const canvas = document.getElementById('tool-comparison-chart');
    const ctx = canvas.getContext('2d');
    
    // Clear any existing chart
    if (canvas.chart) {
        canvas.chart.destroy();
    }
    
    // Get tool data for comparison
    const chartData = [];
    const chartLabels = [];
    
    data.tools.forEach(tool => {
        chartLabels.push(tool.id);
        chartData.push(tool.avg_metrics[metricId] || 0);
    });
    
    // Create new chart
    canvas.chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: chartLabels,
            datasets: [{
                label: getMetricName(data.metrics, metricId),
                data: chartData,
                backgroundColor: 'rgba(153, 102, 255, 0.7)',
                borderColor: 'rgba(153, 102, 255, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true
                }
            },
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            }
        }
    });
}

// Check for visualization images
function checkForVisualizations() {
    // Test if images exist at the expected paths
    const visualizations = [
        { id: 'tool_performance', name: 'Tool Performance' },
        { id: 'coverage_comparison', name: 'Coverage Comparison' },
        { id: 'time_vs_coverage', name: 'Time vs Coverage' },
        { id: 'metrics_correlation', name: 'Metrics Correlation' },
        { id: 'top_performers', name: 'Top Performers' },
        { id: 'llm_comparison', name: 'LLM Comparison' }
    ];
    
    const container = document.getElementById('visualizations-grid');
    container.innerHTML = '';
    
    let hasVisualizations = false;
    
    visualizations.forEach(vis => {
        const imagePath = `visualizations/${vis.id}.png`;
        
        // Create an image element to test if the image exists
        const img = new Image();
        img.src = imagePath;
        
        img.onload = function() {
            // Image exists, add it to the grid
            const card = document.createElement('div');
            card.className = 'visualization-card';
            
            const title = document.createElement('h4');
            title.textContent = vis.name;
            
            const image = document.createElement('img');
            image.src = imagePath;
            image.alt = vis.name;
            image.className = 'visualization-image';
            
            card.appendChild(title);
            card.appendChild(image);
            container.appendChild(card);
            
            hasVisualizations = true;
            document.getElementById('visualizations-container').style.display = 'block';
        };
        
        img.onerror = function() {
            // Try alternative file name patterns
            const altImagePath = `visualizations/${vis.name.toLowerCase().replace(/\\s+/g, '_')}.png`;
            
            const altImg = new Image();
            altImg.src = altImagePath;
            
            altImg.onload = function() {
                // Alternative image exists
                const card = document.createElement('div');
                card.className = 'visualization-card';
                
                const title = document.createElement('h4');
                title.textContent = vis.name;
                
                const image = document.createElement('img');
                image.src = altImagePath;
                image.alt = vis.name;
                image.className = 'visualization-image';
                
                card.appendChild(title);
                card.appendChild(image);
                container.appendChild(card);
                
                hasVisualizations = true;
                document.getElementById('visualizations-container').style.display = 'block';
            };
        };
    });
    
    // Hide visualizations section if no images exist
    if (!hasVisualizations) {
        document.getElementById('visualizations-container').style.display = 'none';
    }
}

// Populate configurations section
function populateConfigurationsSection(data) {
    // Populate filter dropdowns
    populateConfigFilters(data);
    
    // Display configuration cards
    displayConfigurationCards(data.configurations);
    
    // Set up filter events
    setupConfigFilters(data);
}

// Populate configuration filter dropdowns
function populateConfigFilters(data) {
    // Tool filter
    const toolFilter = document.getElementById('config-filter-tool');
    const tools = [...new Set(data.configurations.map(c => c.tool))].filter(Boolean);
    
    toolFilter.innerHTML = '<option value="all">All</option>';
    tools.forEach(tool => {
        const option = document.createElement('option');
        option.value = tool;
        option.textContent = tool;
        toolFilter.appendChild(option);
    });
    
    // LLM type filter
    const llmFilter = document.getElementById('config-filter-llm');
    const llmTypes = [...new Set(data.configurations.map(c => c.llm_type))].filter(Boolean);
    
    llmFilter.innerHTML = '<option value="all">All</option>';
    llmTypes.forEach(llm => {
        const option = document.createElement('option');
        option.value = llm;
        option.textContent = llm;
        llmFilter.appendChild(option);
    });
    
    // Metric filter
    populateMetricsDropdown(data.metrics, 'config-filter-metric');
}

// Display configuration cards
function displayConfigurationCards(configurations, filters = {}) {
    const grid = document.getElementById('configurations-grid');
    grid.innerHTML = '';
    
    // Apply filters
    let filteredConfigs = [...configurations];
    
    if (filters.tool && filters.tool !== 'all') {
        filteredConfigs = filteredConfigs.filter(c => c.tool === filters.tool);
    }
    
    if (filters.llm && filters.llm !== 'all') {
        filteredConfigs = filteredConfigs.filter(c => c.llm_type === filters.llm);
    }
    
    // Sort by metric if specified
    if (filters.metric) {
        filteredConfigs.sort((a, b) => {
            const valueA = (a.metrics[filters.metric] || 0);
            const valueB = (b.metrics[filters.metric] || 0);
            
            return filters.order === 'asc' ? valueA - valueB : valueB - valueA;
        });
    }
    
    // Create cards for each configuration
    filteredConfigs.forEach(config => {
        const card = document.createElement('div');
        card.className = 'config-card';
        
        // Card header
        const header = document.createElement('h3');
        header.textContent = config.id;
        card.appendChild(header);
        
        // Card details
        const details = document.createElement('div');
        details.className = 'config-card-details';
        
        // Tool, LLM type, app count
        if (config.tool) {
            details.appendChild(createConfigDetail('Tool', config.tool));
        }
        
        if (config.llm_type) {
            details.appendChild(createConfigDetail('LLM Type', config.llm_type));
        }
        
        if (config.llm_model) {
            details.appendChild(createConfigDetail('LLM Model', config.llm_model));
        }
        
        details.appendChild(createConfigDetail('Apps Tested', config.app_count));
        details.appendChild(createConfigDetail('Success Rate', 
            config.app_count > 0 
                ? `${Math.round((config.app_count - config.error_count) / config.app_count * 100)}%`
                : 'N/A'
        ));
        
        card.appendChild(details);
        
        // Metrics
        const metrics = document.createElement('div');
        metrics.className = 'config-card-metrics';
        
        Object.entries(config.metrics).forEach(([key, value]) => {
            metrics.appendChild(createMetricItem(key, value));
        });
        
        card.appendChild(metrics);
        grid.appendChild(card);
    });
    
    // Show message if no configurations match filters
    if (filteredConfigs.length === 0) {
        const message = document.createElement('p');
        message.textContent = 'No configurations match the selected filters.';
        grid.appendChild(message);
    }
}

// Create a configuration detail item
function createConfigDetail(label, value) {
    const detail = document.createElement('div');
    detail.className = 'config-card-detail';
    
    const labelEl = document.createElement('span');
    labelEl.className = 'detail-label';
    labelEl.textContent = label + ':';
    
    const valueEl = document.createElement('span');
    valueEl.className = 'detail-value';
    valueEl.textContent = value;
    
    detail.appendChild(labelEl);
    detail.appendChild(valueEl);
    
    return detail;
}

// Create a metric item with bar
function createMetricItem(key, value) {
    const item = document.createElement('div');
    item.className = 'metric-item';
    
    // Get display name for metric
    const metricName = key.replace('avg_', '').replace('_', ' ');
    
    const label = document.createElement('span');
    label.textContent = metricName.charAt(0).toUpperCase() + metricName.slice(1) + ':';
    
    const valueEl = document.createElement('span');
    valueEl.textContent = typeof value === 'number' ? value.toFixed(2) : value;
    
    item.appendChild(label);
    item.appendChild(valueEl);
    
    // Add progress bar for percentage metrics
    if (key.includes('coverage') || key.includes('score')) {
        const bar = document.createElement('div');
        bar.className = 'metric-bar';
        
        const fill = document.createElement('div');
        fill.className = 'metric-fill';
        fill.style.width = `${Math.min(100, value)}%`;
        
        bar.appendChild(fill);
        item.appendChild(bar);
    }
    
    return item;
}

// Set up configuration filter events
function setupConfigFilters(data) {
    const toolFilter = document.getElementById('config-filter-tool');
    const llmFilter = document.getElementById('config-filter-llm');
    const metricFilter = document.getElementById('config-filter-metric');
    const orderFilter = document.getElementById('config-filter-order');
    
    // Function to apply all filters
    const applyFilters = () => {
        const filters = {
            tool: toolFilter.value,
            llm: llmFilter.value,
            metric: metricFilter.value,
            order: orderFilter.value
        };
        
        displayConfigurationCards(data.configurations, filters);
    };
    
    // Add change event listeners
    toolFilter.addEventListener('change', applyFilters);
    llmFilter.addEventListener('change', applyFilters);
    metricFilter.addEventListener('change', applyFilters);
    orderFilter.addEventListener('change', applyFilters);
}

// Populate metrics comparison section
function populateMetricsSection(data) {
    // Populate configuration selection
    const configSelect = document.getElementById('metrics-filter-configs');
    configSelect.innerHTML = '';
    
    data.configurations.forEach(config => {
        const option = document.createElement('option');
        option.value = config.id;
        option.textContent = config.id;
        configSelect.appendChild(option);
    });
    
    // Create initial chart with all configurations
    createMetricsComparisonChart(data);
    
    // Add reset button event
    document.getElementById('metrics-filter-reset').addEventListener('click', function() {
        configSelect.selectedIndex = -1;
        createMetricsComparisonChart(data);
    });
    
    // Add change event for configuration selection
    configSelect.addEventListener('change', function() {
        createMetricsComparisonChart(data);
    });
    
    // Create success vs coverage scatter plot
    createSuccessVsCoverageChart(data);
}

// Create metrics comparison chart
function createMetricsComparisonChart(data) {
    const canvas = document.getElementById('metrics-comparison-chart');
    const ctx = canvas.getContext('2d');
    
    // Clear any existing chart
    if (canvas.chart) {
        canvas.chart.destroy();
    }
    
    // Get selected configurations
    const configSelect = document.getElementById('metrics-filter-configs');
    const selectedOptions = Array.from(configSelect.selectedOptions);
    const selectedConfigs = selectedOptions.map(option => option.value);
    
    // Filter configurations
    let configs = data.configurations;
    if (selectedConfigs.length > 0) {
        configs = configs.filter(c => selectedConfigs.includes(c.id));
    } else {
        // If none selected, limit to top 5 by overall score
        configs = [...configs].sort((a, b) => {
            return (b.metrics.overall_score || 0) - (a.metrics.overall_score || 0);
        }).slice(0, 5);
    }
    
    // Prepare chart data
    const labels = data.metrics.map(m => m.name);
    const datasets = configs.map(config => {
        // Generate a color based on the config id
        const color = stringToColor(config.id);
        
        return {
            label: config.id,
            data: data.metrics.map(m => config.metrics[m.id] || 0),
            backgroundColor: `${color}33`,
            borderColor: color,
            borderWidth: 2
        };
    });
    
    // Create radar chart
    canvas.chart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    beginAtZero: true,
                    min: 0,
                    max: 100
                }
            },
            plugins: {
                legend: {
                    position: 'top'
                }
            }
        }
    });
}

// Create success vs coverage scatter plot
function createSuccessVsCoverageChart(data) {
    const canvas = document.getElementById('success-vs-coverage-chart');
    const ctx = canvas.getContext('2d');
    
    // Clear any existing chart
    if (canvas.chart) {
        canvas.chart.destroy();
    }
    
    // Prepare chart data
    const chartData = data.configurations.map(config => {
        const successRate = config.app_count > 0 
            ? (config.app_count - config.error_count) / config.app_count * 100
            : 0;
            
        const coverage = config.metrics.avg_method_coverage || 0;
        
        return {
            x: coverage,
            y: successRate,
            r: 10, // bubble size
            config: config.id
        };
    });
    
    // Create bubble chart
    canvas.chart = new Chart(ctx, {
        type: 'bubble',
        data: {
            datasets: [{
                label: 'Configurations',
                data: chartData,
                backgroundColor: chartData.map(d => `${stringToColor(d.config)}80`),
                borderColor: chartData.map(d => stringToColor(d.config)),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Method Coverage (%)'
                    },
                    min: 0,
                    max: 100
                },
                y: {
                    title: {
                        display: true,
                        text: 'Success Rate (%)'
                    },
                    min: 0,
                    max: 100
                }
            },
            plugins: {
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const d = context.raw;
                            return `${d.config}: Coverage: ${d.x.toFixed(2)}%, Success: ${d.y.toFixed(2)}%`;
                        }
                    }
                }
            }
        }
    });
}

// Populate tools section
function populateToolsSection(data) {
    // Display tool cards
    displayToolCards(data.tools);
    
    // Create tool metrics chart
    if (data.metrics.length > 0 && data.tools.length > 0) {
        populateMetricsDropdown(data.metrics, 'tool-metrics-metric');
        createToolMetricsChart(data, data.metrics[0].id);
        
        // Update chart when metric changes
        document.getElementById('tool-metrics-metric').addEventListener('change', function() {
            createToolMetricsChart(data, this.value);
        });
    }
}

// Display tool cards
function displayToolCards(tools) {
    const grid = document.getElementById('tools-grid');
    grid.innerHTML = '';
    
    tools.forEach(tool => {
        const card = document.createElement('div');
        card.className = 'tool-card';
        
        // Card header
        const header = document.createElement('h3');
        header.textContent = tool.id;
        card.appendChild(header);
        
        // Card details
        const details = document.createElement('div');
        details.className = 'config-card-details';
        
        details.appendChild(createConfigDetail('Configurations', tool.config_count));
        details.appendChild(createConfigDetail('Apps Tested', tool.app_count));
        details.appendChild(createConfigDetail('Success Rate', 
            tool.app_count > 0 
                ? `${Math.round((tool.app_count - tool.error_count) / tool.app_count * 100)}%`
                : 'N/A'
        ));
        
        card.appendChild(details);
        
        // Metrics
        const metrics = document.createElement('div');
        metrics.className = 'config-card-metrics';
        
        Object.entries(tool.avg_metrics).forEach(([key, value]) => {
            metrics.appendChild(createMetricItem(key, value));
        });
        
        card.appendChild(metrics);
        grid.appendChild(card);
    });
}

// Create tool metrics chart
function createToolMetricsChart(data, metricId) {
    const canvas = document.getElementById('tool-metrics-chart');
    const ctx = canvas.getContext('2d');
    
    // Clear any existing chart
    if (canvas.chart) {
        canvas.chart.destroy();
    }
    
    // Get configuration data for each tool
    const chartData = {};
    
    data.configurations.forEach(config => {
        if (config.tool) {
            if (!chartData[config.tool]) {
                chartData[config.tool] = [];
            }
            
            chartData[config.tool].push(config.metrics[metricId] || 0);
        }
    });
    
    // Prepare datasets
    const labels = Object.keys(chartData);
    const datasets = [];
    
    for (const tool in chartData) {
        const values = chartData[tool];
        
        // Calculate statistics
        const min = Math.min(...values);
        const max = Math.max(...values);
        const avg = values.reduce((a, b) => a + b, 0) / values.length;
        const q1 = calculatePercentile(values, 25);
        const median = calculatePercentile(values, 50);
        const q3 = calculatePercentile(values, 75);
        
        datasets.push({
            label: tool,
            data: [{
                min: min,
                q1: q1,
                median: median,
                q3: q3,
                max: max,
                avg: avg
            }],
            backgroundColor: `${stringToColor(tool)}80`,
            borderColor: stringToColor(tool),
            borderWidth: 1
        });
    }
    
    // Create box plot chart
    canvas.chart = new Chart(ctx, {
        type: 'boxplot',
        data: {
            labels: ['Metric Distribution by Tool'],
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                title: {
                    display: true,
                    text: getMetricName(data.metrics, metricId)
                }
            }
        }
    });
}

// Populate correlations section
function populateCorrelationsSection(data) {
    // Display correlations table
    displayCorrelationsTable(data.correlations);
    
    // Create correlations chart
    createCorrelationsChart(data.correlations);
}

// Display correlations table
function displayCorrelationsTable(correlations) {
    const tableBody = document.querySelector('#correlations-table tbody');
    tableBody.innerHTML = '';
    
    if (correlations.length === 0) {
        const row = document.createElement('tr');
        const cell = document.createElement('td');
        cell.colSpan = 5;
        cell.textContent = 'No correlation data available.';
        cell.style.textAlign = 'center';
        row.appendChild(cell);
        tableBody.appendChild(row);
        return;
    }
    
    correlations.forEach(corr => {
        const row = document.createElement('tr');
        
        // App characteristic
        const charCell = document.createElement('td');
        charCell.textContent = formatCharacteristicName(corr.app_characteristic);
        row.appendChild(charCell);
        
        // Configuration
        const configCell = document.createElement('td');
        configCell.textContent = corr.config_id;
        row.appendChild(configCell);
        
        // Metric
        const metricCell = document.createElement('td');
        metricCell.textContent = formatMetricName(corr.config_metric);
        row.appendChild(metricCell);
        
        // Correlation
        const corrCell = document.createElement('td');
        corrCell.textContent = typeof corr.correlation_value === 'number' 
            ? corr.correlation_value.toFixed(2) 
            : corr.correlation_value;
        row.appendChild(corrCell);
        
        // Confidence
        const confidenceCell = document.createElement('td');
        confidenceCell.textContent = corr.confidence.charAt(0).toUpperCase() + corr.confidence.slice(1);
        confidenceCell.className = corr.confidence.toLowerCase();
        row.appendChild(confidenceCell);
        
        tableBody.appendChild(row);
    });
}

// Create correlations chart
function createCorrelationsChart(correlations) {
    if (correlations.length === 0) {
        return;
    }
    
    const canvas = document.getElementById('correlations-chart');
    const ctx = canvas.getContext('2d');
    
    // Clear any existing chart
    if (canvas.chart) {
        canvas.chart.destroy();
    }
    
    // Group correlations by characteristic
    const charCorrelations = {};
    
    correlations.slice(0, 10).forEach(corr => {
        const char = formatCharacteristicName(corr.app_characteristic);
        
        if (!charCorrelations[char]) {
            charCorrelations[char] = [];
        }
        
        charCorrelations[char].push({
            config: corr.config_id,
            value: corr.correlation_value || 0
        });
    });
    
    // Prepare chart data
    const labels = Object.keys(charCorrelations);
    const datasets = [];
    
    // Create a dataset for each unique configuration
    const configs = new Set();
    
    for (const char in charCorrelations) {
        charCorrelations[char].forEach(c => configs.add(c.config));
    }
    
    configs.forEach(config => {
        // Generate color for this config
        const color = stringToColor(config);
        
        const data = labels.map(char => {
            const match = charCorrelations[char].find(c => c.config === config);
            return match ? match.value : 0;
        });
        
        datasets.push({
            label: config,
            data: data,
            backgroundColor: `${color}80`,
            borderColor: color,
            borderWidth: 1
        });
    });
    
    // Create grouped bar chart
    canvas.chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    ticks: {
                        autoSkip: false,
                        maxRotation: 45,
                        minRotation: 45
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Correlation Value'
                    },
                    min: -1,
                    max: 1
                }
            },
            plugins: {
                legend: {
                    position: 'top'
                },
                title: {
                    display: true,
                    text: 'Top Correlations by App Characteristic'
                }
            }
        }
    });
}

// Populate anomalies section
function populateAnomaliesSection(data) {
    // Display anomalies table
    displayAnomaliesTable(data.anomalies);
    
    // Create anomalies by type chart
    createAnomaliesByTypeChart(data.anomalies);
    
    // Create anomalies by severity chart
    createAnomaliesBySeverityChart(data.anomalies);
}

// Display anomalies table
function displayAnomaliesTable(anomalies) {
    const tableBody = document.querySelector('#anomalies-table tbody');
    tableBody.innerHTML = '';
    
    if (!anomalies || anomalies.length === 0) {
        const row = document.createElement('tr');
        const cell = document.createElement('td');
        cell.colSpan = 7;
        cell.textContent = 'No anomalies detected.';
        cell.style.textAlign = 'center';
        row.appendChild(cell);
        tableBody.appendChild(row);
        return;
    }
    
    anomalies.forEach(anomaly => {
        const row = document.createElement('tr');
        
        // ID
        const idCell = document.createElement('td');
        idCell.textContent = anomaly.id;
        row.appendChild(idCell);
        
        // Type
        const typeCell = document.createElement('td');
        typeCell.textContent = anomaly.type.charAt(0).toUpperCase() + anomaly.type.slice(1);
        row.appendChild(typeCell);
        
        // Metric
        const metricCell = document.createElement('td');
        metricCell.textContent = formatMetricName(anomaly.metric);
        row.appendChild(metricCell);
        
        // Expected value
        const expectedCell = document.createElement('td');
        expectedCell.textContent = typeof anomaly.expected_value === 'number' 
            ? anomaly.expected_value.toFixed(2) 
            : anomaly.expected_value;
        row.appendChild(expectedCell);
        
        // Actual value
        const actualCell = document.createElement('td');
        actualCell.textContent = typeof anomaly.actual_value === 'number' 
            ? anomaly.actual_value.toFixed(2) 
            : anomaly.actual_value;
        row.appendChild(actualCell);
        
        // Deviation
        const deviationCell = document.createElement('td');
        deviationCell.textContent = typeof anomaly.deviation === 'number' 
            ? anomaly.deviation.toFixed(2) 
            : anomaly.deviation;
        row.appendChild(deviationCell);
        
        // Severity
        const severityCell = document.createElement('td');
        severityCell.textContent = anomaly.severity.charAt(0).toUpperCase() + anomaly.severity.slice(1);
        severityCell.className = anomaly.severity.toLowerCase();
        row.appendChild(severityCell);
        
        tableBody.appendChild(row);
    });
}

// Create anomalies by type chart
function createAnomaliesByTypeChart(anomalies) {
    if (!anomalies || anomalies.length === 0) {
        return;
    }
    
    const canvas = document.getElementById('anomalies-by-type-chart');
    const ctx = canvas.getContext('2d');
    
    // Clear any existing chart
    if (canvas.chart) {
        canvas.chart.destroy();
    }
    
    // Count anomalies by type
    const typeCount = {};
    
    anomalies.forEach(anomaly => {
        const type = anomaly.type.charAt(0).toUpperCase() + anomaly.type.slice(1);
        
        if (!typeCount[type]) {
            typeCount[type] = 0;
        }
        
        typeCount[type]++;
    });
    
    // Prepare chart data
    const labels = Object.keys(typeCount);
    const data = labels.map(type => typeCount[type]);
    
    // Generate colors
    const colors = labels.map(stringToColor);
    
    // Create pie chart
    canvas.chart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors.map(c => `${c}80`),
                borderColor: colors,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right'
                }
            }
        }
    });
}

// Create anomalies by severity chart
function createAnomaliesBySeverityChart(anomalies) {
    if (!anomalies || anomalies.length === 0) {
        return;
    }
    
    const canvas = document.getElementById('anomalies-by-severity-chart');
    const ctx = canvas.getContext('2d');
    
    // Clear any existing chart
    if (canvas.chart) {
        canvas.chart.destroy();
    }
    
    // Count anomalies by severity
    const severityCount = {};
    
    anomalies.forEach(anomaly => {
        const severity = anomaly.severity.charAt(0).toUpperCase() + anomaly.severity.slice(1);
        
        if (!severityCount[severity]) {
            severityCount[severity] = 0;
        }
        
        severityCount[severity]++;
    });
    
    // Prepare chart data
    const labels = Object.keys(severityCount);
    const data = labels.map(severity => severityCount[severity]);
    
    // Define severity colors
    const severityColors = {
        'High': '#dc3545',
        'Medium': '#ffc107',
        'Low': '#28a745'
    };
    
    // Get colors for each severity
    const colors = labels.map(severity => severityColors[severity] || stringToColor(severity));
    
    // Create pie chart
    canvas.chart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors.map(c => `${c}80`),
                borderColor: colors,
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right'
                }
            }
        }
    });
}

// Populate recommendations section
function populateRecommendationsSection(data) {
    const container = document.getElementById('recommendations-container');
    container.innerHTML = '';
    
    if (!data.recommendations || data.recommendations.length === 0) {
        const message = document.createElement('p');
        message.textContent = 'No recommendations available.';
        container.appendChild(message);
        return;
    }
    
    // Group recommendations by characteristic
    const charRecommendations = {};
    
    data.recommendations.forEach(rec => {
        const char = rec.characteristic;
        
        if (!charRecommendations[char]) {
            charRecommendations[char] = [];
        }
        
        charRecommendations[char].push(rec);
    });
    
    // Create a card for each characteristic
    for (const char in charRecommendations) {
        const card = document.createElement('div');
        card.className = 'recommendation-card';
        
        // Card header
        const header = document.createElement('h3');
        header.textContent = formatCharacteristicName(char);
        card.appendChild(header);
        
        // Recommendations list
        const list = document.createElement('ul');
        
        charRecommendations[char].forEach(rec => {
            const item = document.createElement('li');
            
            const configSpan = document.createElement('strong');
            configSpan.textContent = rec.config_id;
            
            item.appendChild(configSpan);
            item.appendChild(document.createTextNode(': ' + 
                rec.explanation.substring(rec.explanation.indexOf(':') + 1).trim()));
            
            // Add confidence badge
            const confidence = document.createElement('span');
            confidence.className = 'confidence ' + rec.confidence.toLowerCase();
            confidence.textContent = rec.confidence.charAt(0).toUpperCase() + rec.confidence.slice(1);
            item.appendChild(confidence);
            
            list.appendChild(item);
        });
        
        card.appendChild(list);
        container.appendChild(card);
    }
}

// Utility function: Get metric name from ID
function getMetricName(metrics, metricId) {
    const metric = metrics.find(m => m.id === metricId);
    return metric ? metric.name : metricId;
}

// Utility function: Format characteristic name
function formatCharacteristicName(name) {
    if (!name) return '';
    return name.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
}

// Utility function: Format metric name
function formatMetricName(name) {
    if (!name) return '';
    return name.replace('avg_', '').replace('_', ' ')
        .split(' ').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
}

// Utility function: Generate color from string
function stringToColor(str) {
    if (!str) return '#1a73e8';
    
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    
    let color = '#';
    for (let i = 0; i < 3; i++) {
        const value = (hash >> (i * 8)) & 0xFF;
        color += ('00' + value.toString(16)).substr(-2);
    }
    
    return color;
}

// Utility function: Calculate percentile
function calculatePercentile(arr, percentile) {
    if (arr.length === 0) return 0;
    
    const sorted = [...arr].sort((a, b) => a - b);
    const pos = (sorted.length - 1) * percentile / 100;
    const base = Math.floor(pos);
    const rest = pos - base;
    
    if (sorted[base + 1] !== undefined) {
        return sorted[base] + rest * (sorted[base + 1] - sorted[base]);
    }
    
    return sorted[base];
}
"""
    
    def launch_dashboard(self, dashboard_file: str) -> bool:
        """
        Open the dashboard in a web browser.
        
        Args:
            dashboard_file: Path to the dashboard HTML file
            
        Returns:
            True if browser was launched, False otherwise
        """
        try:
            # Convert to file URL
            dashboard_url = Path(dashboard_file).absolute().as_uri()
            
            # Open in browser
            webbrowser.open(dashboard_url)
            
            self.logger.info(f"Dashboard opened in browser: {dashboard_url}")
            return True
        except Exception as e:
            self.logger.error(f"Error launching dashboard: {str(e)}")
            return False


# Convenient functions
def generate_dashboard(results: Dict[str, Any], output_dir: str) -> str:
    """
    Generate an interactive dashboard for test results.
    
    Args:
        results: Analysis results dictionary
        output_dir: Directory to save the dashboard files
        
    Returns:
        Path to the main dashboard HTML file
    """
    dashboard = Dashboard()
    return dashboard.generate_dashboard(results, output_dir)


def launch_dashboard(dashboard_file: str) -> bool:
    """
    Open the dashboard in a web browser.
    
    Args:
        dashboard_file: Path to the dashboard HTML file
        
    Returns:
        True if browser was launched, False otherwise
    """
    dashboard = Dashboard()
    return dashboard.launch_dashboard(dashboard_file)