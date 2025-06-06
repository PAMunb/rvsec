"""
Anomaly detector module for test framework.

This module provides functionality for detecting anomalies in test
results, identifying configurations that produce unexpected behavior.
"""

import os
import json
import logging
import numpy as np
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime

from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager


@dataclass
class AnomalyReport:
    """Represents an anomaly report for a specific configuration or app."""
    id: str  # Configuration ID or app name
    type: str  # 'configuration' or 'app'
    metric: str  # Metric that shows anomalous behavior
    expected_value: float  # Expected value based on similar configs/apps
    actual_value: float  # Actual observed value
    deviation: float  # How much it deviates (in standard deviations)
    severity: str  # 'low', 'medium', 'high'
    details: Dict[str, Any]  # Additional details
    explanation: str  # Human-readable explanation


class AnomalyDetector:
    """
    Detector for anomalies in test results.
    
    Identifies configurations and applications that produce unexpected
    behavior or results that significantly deviate from the norm.
    
    ### Key Responsibilities:
    - Detects anomalies in result metrics
    - Identifies configurations with unexpected behavior
    - Flags potential issues for manual review
    - Provides explanations for detected anomalies
    """
    
    def __init__(self, z_threshold: float = 2.0, min_samples: int = 3):
        """
        Initialize the anomaly detector.
        
        Args:
            z_threshold: Z-score threshold for anomaly detection
            min_samples: Minimum number of samples needed for detection
        """
        self.z_threshold = z_threshold
        self.min_samples = min_samples
        
        # Set up logging
        self.logger = LoggingManager.get_instance().get_logger(
            'test_framework.anomaly_detector',
            {CONTEXT_COMPONENT: 'AnomalyDetector'}
        )
    
    def detect_anomalies(self, results: Dict[str, Any]) -> List[AnomalyReport]:
        """
        Detect anomalies in test results.
        
        Args:
            results: Analysis results dictionary from ResultsLoader
            
        Returns:
            List of anomaly reports
        """
        anomalies = []
        
        # No results to analyze
        if not results or 'configuration_comparisons' not in results:
            return anomalies
            
        # Extract configuration comparisons
        comparisons = results.get('configuration_comparisons', {})
        
        # Not enough samples for detection
        if len(comparisons) < self.min_samples:
            self.logger.info(f"Not enough samples for anomaly detection. Need {self.min_samples}, got {len(comparisons)}")
            return anomalies
        
        # Detect configuration anomalies
        config_anomalies = self._detect_configuration_anomalies(comparisons)
        anomalies.extend(config_anomalies)
        
        # Detect app-specific anomalies if app data is available
        if 'app_metrics' in results:
            app_anomalies = self._detect_app_anomalies(results.get('app_metrics', {}), comparisons)
            anomalies.extend(app_anomalies)
        
        # Detect tool-specific anomalies
        tool_anomalies = self._detect_tool_anomalies(comparisons)
        anomalies.extend(tool_anomalies)
        
        # Log anomaly count
        self.logger.info(f"Detected {len(anomalies)} anomalies in {len(comparisons)} configurations")
        
        return anomalies
    
    def _detect_configuration_anomalies(self, comparisons: Dict[str, Dict[str, Any]]) -> List[AnomalyReport]:
        """
        Detect anomalies in configuration metrics.
        
        Args:
            comparisons: Configuration comparison data
            
        Returns:
            List of anomaly reports for configurations
        """
        anomalies = []
        
        # Prepare metrics
        metrics = ['avg_method_coverage', 'avg_activity_coverage', 'avg_mop_method_coverage', 
                   'avg_execution_time', 'overall_score']
        
        # Extract configuration groups by tool and LLM type
        config_groups = self._group_configurations(comparisons)
        
        # For each configuration group
        for group_name, group_configs in config_groups.items():
            # For each metric
            for metric in metrics:
                # Calculate mean and standard deviation for this metric in this group
                values = []
                config_ids = []
                
                for config_id in group_configs:
                    config = comparisons.get(config_id, {})
                    avg_metrics = config.get('avg_metrics', {})
                    if metric in avg_metrics:
                        values.append(avg_metrics[metric])
                        config_ids.append(config_id)
                
                # Skip if not enough values
                if len(values) < self.min_samples:
                    continue
                    
                # Calculate statistics
                mean_value = np.mean(values)
                std_value = np.std(values)
                
                # Skip if standard deviation is too small
                if std_value < 0.001:
                    continue
                
                # Check each configuration for anomalies
                for i, config_id in enumerate(config_ids):
                    value = values[i]
                    z_score = (value - mean_value) / std_value
                    
                    # Check if this is an anomaly
                    if abs(z_score) > self.z_threshold:
                        config = comparisons.get(config_id, {})
                        severity = self._calculate_severity(abs(z_score))
                        
                        # Determine anomaly direction
                        direction = "higher than" if z_score > 0 else "lower than"
                        explanation = (
                            f"Configuration '{config_id}' shows {severity} anomalous behavior in {metric}, "
                            f"with a value {direction} expected for configurations in group '{group_name}'. "
                            f"This configuration performs at {value:.2f}, while the group average is {mean_value:.2f} "
                            f"(std: {std_value:.2f})."
                        )
                        
                        # Add anomaly report
                        anomalies.append(AnomalyReport(
                            id=config_id,
                            type='configuration',
                            metric=metric,
                            expected_value=mean_value,
                            actual_value=value,
                            deviation=z_score,
                            severity=severity,
                            details={
                                'group': group_name,
                                'group_mean': mean_value,
                                'group_std': std_value,
                                'configuration': config
                            },
                            explanation=explanation
                        ))
        
        return anomalies
    
    def _detect_app_anomalies(self, app_metrics: Dict[str, Dict[str, Any]], 
                             comparisons: Dict[str, Dict[str, Any]]) -> List[AnomalyReport]:
        """
        Detect anomalies in app-specific metrics.
        
        Args:
            app_metrics: App-specific metrics
            comparisons: Configuration comparison data
            
        Returns:
            List of anomaly reports for apps
        """
        anomalies = []
        
        # Not enough apps for detection
        if len(app_metrics) < self.min_samples:
            return anomalies
        
        # Metrics to check
        metrics = ['method_coverage', 'activity_coverage', 'mop_method_coverage']
        
        # For each metric
        for metric in metrics:
            # Calculate mean and standard deviation
            values = []
            app_names = []
            
            for app_name, app_data in app_metrics.items():
                if metric in app_data:
                    values.append(app_data[metric])
                    app_names.append(app_name)
            
            # Skip if not enough values
            if len(values) < self.min_samples:
                continue
                
            # Calculate statistics
            mean_value = np.mean(values)
            std_value = np.std(values)
            
            # Skip if standard deviation is too small
            if std_value < 0.001:
                continue
            
            # Check each app for anomalies
            for i, app_name in enumerate(app_names):
                value = values[i]
                z_score = (value - mean_value) / std_value
                
                # Check if this is an anomaly
                if abs(z_score) > self.z_threshold:
                    app_data = app_metrics.get(app_name, {})
                    severity = self._calculate_severity(abs(z_score))
                    
                    # Determine anomaly direction
                    direction = "higher than" if z_score > 0 else "lower than"
                    explanation = (
                        f"App '{app_name}' shows {severity} anomalous behavior in {metric}, "
                        f"with a value {direction} expected compared to other apps. "
                        f"This app performs at {value:.2f}, while the average across apps is {mean_value:.2f} "
                        f"(std: {std_value:.2f})."
                    )
                    
                    # Add anomaly report
                    anomalies.append(AnomalyReport(
                        id=app_name,
                        type='app',
                        metric=metric,
                        expected_value=mean_value,
                        actual_value=value,
                        deviation=z_score,
                        severity=severity,
                        details={
                            'app_data': app_data,
                            'app_mean': mean_value,
                            'app_std': std_value
                        },
                        explanation=explanation
                    ))
        
        return anomalies
    
    def _detect_tool_anomalies(self, comparisons: Dict[str, Dict[str, Any]]) -> List[AnomalyReport]:
        """
        Detect anomalies specifically related to tool performance.
        
        Args:
            comparisons: Configuration comparison data
            
        Returns:
            List of anomaly reports for tool-specific issues
        """
        anomalies = []
        
        # Extract tool-specific data
        tool_data = {}
        
        for config_id, config in comparisons.items():
            # Extract tool from config_id
            tool = config_id.split('_')[0] if '_' in config_id else 'unknown'
            
            if tool not in tool_data:
                tool_data[tool] = {
                    'configs': [],
                    'metrics': {
                        'avg_method_coverage': [],
                        'avg_activity_coverage': [],
                        'avg_mop_method_coverage': [],
                        'avg_execution_time': [],
                        'overall_score': [],
                        'error_count': []
                    }
                }
            
            # Add configuration to tool data
            tool_data[tool]['configs'].append(config_id)
            
            # Add metrics
            avg_metrics = config.get('avg_metrics', {})
            for metric in tool_data[tool]['metrics'].keys():
                if metric != 'error_count':
                    if metric in avg_metrics:
                        tool_data[tool]['metrics'][metric].append(avg_metrics[metric])
                else:
                    tool_data[tool]['metrics']['error_count'].append(config.get('error_count', 0))
        
        # Not enough tools for comparison
        if len(tool_data) < 2:
            return anomalies
        
        # Compare tools
        metrics = ['avg_method_coverage', 'avg_activity_coverage', 'avg_mop_method_coverage', 
                  'avg_execution_time', 'overall_score', 'error_count']
        
        for metric in metrics:
            # Calculate mean for each tool
            tool_means = {}
            tool_stds = {}
            
            for tool, data in tool_data.items():
                values = data['metrics'][metric]
                if len(values) >= self.min_samples:
                    tool_means[tool] = np.mean(values)
                    tool_stds[tool] = np.std(values)
            
            # Skip if not enough tools
            if len(tool_means) < 2:
                continue
                
            # Calculate overall mean and std
            all_means = list(tool_means.values())
            overall_mean = np.mean(all_means)
            overall_std = np.std(all_means)
            
            # Skip if standard deviation is too small
            if overall_std < 0.001:
                continue
            
            # Check each tool for anomalies
            for tool, mean_value in tool_means.items():
                z_score = (mean_value - overall_mean) / overall_std
                
                # Check if this is an anomaly
                if abs(z_score) > self.z_threshold:
                    severity = self._calculate_severity(abs(z_score))
                    
                    # Determine anomaly direction
                    direction = "higher than" if z_score > 0 else "lower than"
                    explanation = (
                        f"Tool '{tool}' shows {severity} anomalous behavior in {metric}, "
                        f"with a value {direction} expected compared to other tools. "
                        f"This tool performs at {mean_value:.2f}, while the average across tools is {overall_mean:.2f} "
                        f"(std: {overall_std:.2f})."
                    )
                    
                    # Add anomaly report
                    anomalies.append(AnomalyReport(
                        id=tool,
                        type='tool',
                        metric=metric,
                        expected_value=overall_mean,
                        actual_value=mean_value,
                        deviation=z_score,
                        severity=severity,
                        details={
                            'tool_data': tool_data[tool],
                            'tool_mean': mean_value,
                            'tool_std': tool_stds.get(tool, 0),
                            'overall_mean': overall_mean,
                            'overall_std': overall_std
                        },
                        explanation=explanation
                    ))
        
        return anomalies
    
    def _group_configurations(self, comparisons: Dict[str, Dict[str, Any]]) -> Dict[str, List[str]]:
        """
        Group configurations by tool and LLM type.
        
        Args:
            comparisons: Configuration comparison data
            
        Returns:
            Dictionary mapping group names to lists of configuration IDs
        """
        groups = {
            'all': list(comparisons.keys())
        }
        
        # Group by tool
        tool_groups = {}
        
        for config_id in comparisons.keys():
            # Extract tool from config_id
            if '_' in config_id:
                tool = config_id.split('_')[0]
                
                if tool not in tool_groups:
                    tool_groups[tool] = []
                    
                tool_groups[tool].append(config_id)
        
        # Add tool groups
        groups.update({f"tool_{tool}": configs for tool, configs in tool_groups.items()})
        
        # Group by LLM type
        llm_groups = {}
        
        for config_id in comparisons.keys():
            # Extract LLM type from config_id
            if '_' in config_id:
                parts = config_id.split('_')
                if len(parts) >= 2:
                    llm_type = parts[1]
                    
                    if llm_type not in llm_groups:
                        llm_groups[llm_type] = []
                        
                    llm_groups[llm_type].append(config_id)
        
        # Add LLM groups
        groups.update({f"llm_{llm_type}": configs for llm_type, configs in llm_groups.items()})
        
        # Group by tool and LLM type
        tool_llm_groups = {}
        
        for config_id in comparisons.keys():
            # Extract tool and LLM type from config_id
            if '_' in config_id:
                parts = config_id.split('_')
                if len(parts) >= 2:
                    tool = parts[0]
                    llm_type = parts[1]
                    group_key = f"{tool}_{llm_type}"
                    
                    if group_key not in tool_llm_groups:
                        tool_llm_groups[group_key] = []
                        
                    tool_llm_groups[group_key].append(config_id)
        
        # Add tool+LLM groups
        groups.update(tool_llm_groups)
        
        return groups
    
    def _calculate_severity(self, z_score: float) -> str:
        """
        Calculate severity based on z-score.
        
        Args:
            z_score: Absolute z-score
            
        Returns:
            Severity level ('low', 'medium', 'high')
        """
        if z_score > 3.0:
            return 'high'
        elif z_score > 2.5:
            return 'medium'
        else:
            return 'low'
    
    def generate_report(self, anomalies: List[AnomalyReport]) -> Dict[str, Any]:
        """
        Generate a summary report of detected anomalies.
        
        Args:
            anomalies: List of anomaly reports
            
        Returns:
            Report dictionary
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_anomalies': len(anomalies),
            'anomalies_by_type': {},
            'anomalies_by_metric': {},
            'anomalies_by_severity': {},
            'anomalies': [self._anomaly_to_dict(a) for a in anomalies]
        }
        
        # Count anomalies by type
        type_counts = {}
        for anomaly in anomalies:
            if anomaly.type not in type_counts:
                type_counts[anomaly.type] = 0
            type_counts[anomaly.type] += 1
        report['anomalies_by_type'] = type_counts
        
        # Count anomalies by metric
        metric_counts = {}
        for anomaly in anomalies:
            if anomaly.metric not in metric_counts:
                metric_counts[anomaly.metric] = 0
            metric_counts[anomaly.metric] += 1
        report['anomalies_by_metric'] = metric_counts
        
        # Count anomalies by severity
        severity_counts = {}
        for anomaly in anomalies:
            if anomaly.severity not in severity_counts:
                severity_counts[anomaly.severity] = 0
            severity_counts[anomaly.severity] += 1
        report['anomalies_by_severity'] = severity_counts
        
        return report
    
    def _anomaly_to_dict(self, anomaly: AnomalyReport) -> Dict[str, Any]:
        """
        Convert an anomaly report to a dictionary.
        
        Args:
            anomaly: Anomaly report
            
        Returns:
            Dictionary representation of the anomaly
        """
        return {
            'id': anomaly.id,
            'type': anomaly.type,
            'metric': anomaly.metric,
            'expected_value': anomaly.expected_value,
            'actual_value': anomaly.actual_value,
            'deviation': anomaly.deviation,
            'severity': anomaly.severity,
            'explanation': anomaly.explanation
        }


# Convenient function
def detect_anomalies(results: Dict[str, Any], z_threshold: float = 2.0) -> Dict[str, Any]:
    """
    Detect anomalies in test results.
    
    Args:
        results: Analysis results dictionary from ResultsLoader
        z_threshold: Z-score threshold for anomaly detection
        
    Returns:
        Anomaly detection report
    """
    detector = AnomalyDetector(z_threshold=z_threshold)
    anomalies = detector.detect_anomalies(results)
    return detector.generate_report(anomalies)