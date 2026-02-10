"""
Plateau analyzer module for test framework.

This module provides tools for analyzing plateau in test metrics over time,
helping to identify optimal test durations and diminishing returns.
"""

import json
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from typing import Dict, List, Any, Optional, Tuple

from rvandroid.test_framework.executor import TestResult


class PlateauAnalyzer:
    """
    Analyzer for detecting plateau in test metrics.
    
    Identifies when metrics like coverage reach a plateau,
    helping to determine optimal test durations.
    
    ### Key Responsibilities:
    - Analyzes metrics progression over time
    - Detects plateau points
    - Identifies optimal test durations
    - Generates visualizations for plateau analysis
    """
    
    def __init__(self, results: List[TestResult], output_dir: str = "plateau_analysis"):
        """
        Initialize the plateau analyzer.
        
        Args:
            results: List of test results
            output_dir: Directory for analysis output
        """
        self.results = results
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
    def analyze_by_timeout(self, 
                          timeouts: List[int], 
                          metrics: List[str] = ["method_coverage", "activity_coverage", "mop_method_coverage"]) -> Dict[str, Any]:
        """
        Analyze metrics by timeout to detect plateau.
        
        Args:
            timeouts: List of timeouts to analyze
            metrics: List of metrics to analyze
            
        Returns:
            Dictionary with plateau analysis results
        """
        # Group results by timeout
        results_by_timeout = {}
        for timeout in timeouts:
            results_by_timeout[timeout] = [
                r for r in self.results 
                if r.test_case.tool_config.timeout == timeout and r.status == "completed"
            ]
        
        # Initialize analysis results
        analysis_results = {
            "timeouts": timeouts,
            "metrics": {},
            "plateau_points": {},
            "optimal_timeouts": {}
        }
        
        # Analyze each metric
        for metric in metrics:
            metric_values = []
            
            # Calculate average metric value for each timeout
            for timeout in timeouts:
                timeout_results = results_by_timeout[timeout]
                if not timeout_results:
                    metric_values.append(0.0)
                    continue
                
                # Extract metric value from coverage data
                values = []
                for result in timeout_results:
                    if result.coverage_data and metric in result.coverage_data:
                        values.append(result.coverage_data[metric])
                
                # Calculate average
                avg_value = sum(values) / len(values) if values else 0.0
                metric_values.append(avg_value)
            
            # Store metric values
            analysis_results["metrics"][metric] = metric_values
            
            # Detect plateau
            plateau_point = self._detect_plateau(timeouts, metric_values)
            analysis_results["plateau_points"][metric] = plateau_point
            
            # Find optimal timeout
            optimal_timeout = self._find_optimal_timeout(timeouts, metric_values)
            analysis_results["optimal_timeouts"][metric] = optimal_timeout
        
        # Create visualization
        self._create_plateau_visualization(timeouts, analysis_results)
        
        return analysis_results
    
    def _detect_plateau(self, timeouts: List[int], values: List[float], threshold: float = 0.02) -> Optional[int]:
        """
        Detect plateau point in metrics.
        
        A plateau is detected when the rate of change falls below the threshold.
        
        Args:
            timeouts: List of timeouts
            values: List of metric values
            threshold: Threshold for plateau detection (relative change)
            
        Returns:
            Timeout at which plateau is detected, or None if no plateau
        """
        if len(values) < 2:
            return None
        
        # Calculate rates of change
        rates = []
        for i in range(1, len(values)):
            # Calculate relative change
            if values[i-1] == 0:
                rate = 0.0 if values[i] == 0 else 1.0
            else:
                rate = (values[i] - values[i-1]) / values[i-1]
            rates.append(rate)
        
        # Find first point where rate falls below threshold
        for i, rate in enumerate(rates):
            if abs(rate) < threshold:
                # Return the timeout at this point
                return timeouts[i+1]
        
        # No plateau detected
        return None
    
    def _find_optimal_timeout(self, timeouts: List[int], values: List[float]) -> int:
        """
        Find optimal timeout based on diminishing returns.
        
        Uses the "elbow method" to find the point of diminishing returns.
        
        Args:
            timeouts: List of timeouts
            values: List of metric values
            
        Returns:
            Optimal timeout
        """
        if len(values) < 2:
            return timeouts[-1] if timeouts else 0
        
        # Use simple approach: find where we achieve 90% of maximum value
        max_value = max(values)
        if max_value == 0:
            return timeouts[0]
        
        threshold = 0.9 * max_value
        
        for i, value in enumerate(values):
            if value >= threshold:
                return timeouts[i]
        
        # If no point reaches 90%, return the last timeout
        return timeouts[-1]
    
    def _create_plateau_visualization(self, timeouts: List[int], analysis_results: Dict[str, Any]) -> None:
        """
        Create visualization for plateau analysis.
        
        Args:
            timeouts: List of timeouts
            analysis_results: Plateau analysis results
        """
        # Create figure
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # Plot each metric
        for metric, values in analysis_results["metrics"].items():
            # Plot metric values
            ax.plot(timeouts, values, 'o-', label=f"{metric}")
            
            # Mark plateau point if detected
            plateau_point = analysis_results["plateau_points"].get(metric)
            if plateau_point:
                plateau_index = timeouts.index(plateau_point)
                ax.axvline(x=plateau_point, color='gray', linestyle='--', alpha=0.5)
                ax.plot(plateau_point, values[plateau_index], 'rx', markersize=10)
            
            # Mark optimal timeout
            optimal_timeout = analysis_results["optimal_timeouts"].get(metric)
            if optimal_timeout:
                optimal_index = timeouts.index(optimal_timeout)
                ax.plot(optimal_timeout, values[optimal_index], 'go', markersize=10)
        
        # Set chart properties
        ax.set_xlabel('Timeout (seconds)')
        ax.set_ylabel('Metric Value')
        ax.set_title('Metric Progression Over Time')
        ax.legend()
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # Add annotation
        ax.text(
            0.02, 0.02,
            "Red X: Plateau point\nGreen Circle: Optimal timeout (90% of max)",
            transform=ax.transAxes,
            bbox=dict(facecolor='white', alpha=0.8)
        )
        
        # Save chart
        output_file = os.path.join(self.output_dir, "plateau_analysis.png")
        plt.tight_layout()
        plt.savefig(output_file, dpi=100)
        plt.close(fig)
        
        # Save analysis results
        output_json = os.path.join(self.output_dir, "plateau_analysis.json")
        with open(output_json, 'w') as f:
            json.dump(analysis_results, f, indent=2)


def analyze_plateau(results: List[TestResult], 
                   timeouts: List[int], 
                   output_dir: str = "plateau_analysis") -> Dict[str, Any]:
    """
    Convenience function for plateau analysis.
    
    Args:
        results: List of test results
        timeouts: List of timeouts to analyze
        output_dir: Directory for analysis output
        
    Returns:
        Dictionary with plateau analysis results
    """
    analyzer = PlateauAnalyzer(results, output_dir)
    return analyzer.analyze_by_timeout(timeouts)


def detect_plateau(timeouts: List[int], values: List[float], threshold: float = 0.02) -> Optional[int]:
    """
    Detect plateau point in metrics.
    
    A plateau is detected when the rate of change falls below the threshold.
    
    Args:
        timeouts: List of timeouts
        values: List of metric values
        threshold: Threshold for plateau detection (relative change)
        
    Returns:
        Timeout at which plateau is detected, or None if no plateau
    """
    if len(values) < 2:
        return None
    
    # Calculate rates of change
    rates = []
    for i in range(1, len(values)):
        # Calculate relative change
        if values[i-1] == 0:
            rate = 0.0 if values[i] == 0 else 1.0
        else:
            rate = (values[i] - values[i-1]) / values[i-1]
        rates.append(rate)
    
    # Find first point where rate falls below threshold
    for i, rate in enumerate(rates):
        if abs(rate) < threshold:
            # Return the timeout at this point
            return timeouts[i+1]
    
    # No plateau detected
    return None


def find_optimal_timeout(timeouts: List[int], values: List[float]) -> int:
    """
    Find optimal timeout based on diminishing returns.
    
    Uses the "elbow method" to find the point of diminishing returns.
    
    Args:
        timeouts: List of timeouts
        values: List of metric values
        
    Returns:
        Optimal timeout
    """
    if len(values) < 2:
        return timeouts[-1] if timeouts else 0
    
    # Use simple approach: find where we achieve 90% of maximum value
    max_value = max(values)
    if max_value == 0:
        return timeouts[0]
    
    threshold = 0.9 * max_value
    
    for i, value in enumerate(values):
        if value >= threshold:
            return timeouts[i]
    
    # If no point reaches 90%, return the last timeout
    return timeouts[-1]