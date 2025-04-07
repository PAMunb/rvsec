"""
Correlation analyzer module for test framework.

This module provides functionality for analyzing correlations between
app characteristics and optimal configurations, to help identify which
configurations work best for specific app types.

Note on terminology:
    This module uses "monitored operations" terminology instead of "security"
    to reflect that the system handles both security-specific specifications
    (like cryptography) and general programming specifications (like Iterator usage).
    Monitored operations refer to any operations that have MOP (Monitoring-Oriented
    Programming) specifications associated with them, which can detect errors
    during runtime verification.
"""

import os
import json
import logging
import numpy as np
import re
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict

from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


@dataclass
class CorrelationResult:
    """Represents a correlation between app characteristic and configuration performance."""
    app_characteristic: str  # The app characteristic (e.g., "uses_encryption")
    config_metric: str  # The configuration metric (e.g., "method_coverage")
    config_id: str  # The configuration ID
    correlation_value: float  # Correlation coefficient
    sample_size: int  # Number of samples used
    p_value: Optional[float] = None  # Statistical significance (p-value)
    confidence: str = "medium"  # Confidence level (low, medium, high)
    explanation: str = ""  # Human-readable explanation


@dataclass
class AppCharacteristic:
    """Represents a characteristic of an app."""
    name: str  # Name of the characteristic
    value: Any  # Value of the characteristic (bool, int, float, str)
    category: str  # Category (e.g., "security", "ui", "performance")
    display_name: str  # Human-readable name
    description: str  # Description of what this characteristic means


class CorrelationAnalyzer:
    """
    Analyzer for correlations between app characteristics and configuration performance.
    
    Identifies which configurations work best for specific app types,
    and provides recommendations based on app analysis. Includes specific focus on
    monitored operations characteristics such as cryptography, iterator usage, and I/O operations.
    
    ### Key Responsibilities:
    - Analyzes correlations between app characteristics and config performance
    - Identifies optimal configurations for different app types
    - Provides recommendations based on app characteristics including monitored operations
    - Tracks characteristics related to operations that have MOP specifications
    - Generates reports on app-configuration correlations
    """
    
    def __init__(self, min_samples: int = 5):
        """
        Initialize the correlation analyzer.
        
        Args:
            min_samples: Minimum number of samples needed for correlation analysis
        """
        self.min_samples = min_samples
        
        # Set up logging
        self.logger = LoggingManager.get_instance().get_logger(
            'test_framework.correlation_analyzer',
            {CONTEXT_COMPONENT: 'CorrelationAnalyzer'}
        )
        
        # Common app characteristics to check
        self.common_characteristics = [
            AppCharacteristic(
                name="uses_encryption",
                value=None,
                category="monitored_operations",
                display_name="Uses Encryption APIs",
                description="App uses encryption-related APIs that may have monitored specifications"
            ),
            AppCharacteristic(
                name="uses_network",
                value=None,
                category="connectivity",
                display_name="Uses Network",
                description="App uses network-related APIs"
            ),
            AppCharacteristic(
                name="uses_location",
                value=None,
                category="privacy",
                display_name="Uses Location",
                description="App uses location-related APIs"
            ),
            AppCharacteristic(
                name="uses_camera",
                value=None,
                category="hardware",
                display_name="Uses Camera",
                description="App uses camera-related APIs"
            ),
            AppCharacteristic(
                name="uses_audio",
                value=None,
                category="hardware",
                display_name="Uses Audio",
                description="App uses audio-related APIs"
            ),
            AppCharacteristic(
                name="uses_database",
                value=None,
                category="storage",
                display_name="Uses Database",
                description="App uses database-related APIs (e.g., SQLite)"
            ),
            AppCharacteristic(
                name="complex_ui",
                value=None,
                category="ui",
                display_name="Complex UI",
                description="App has a complex user interface"
            ),
            AppCharacteristic(
                name="activity_count",
                value=None,
                category="structure",
                display_name="Activity Count",
                description="Number of activities in the app"
            ),
            AppCharacteristic(
                name="method_count",
                value=None,
                category="structure",
                display_name="Method Count",
                description="Number of methods in the app"
            ),
            AppCharacteristic(
                name="has_mop_specs",
                value=None,
                category="monitoring",
                display_name="Has MOP Specs",
                description="App has specifications for monitored operations"
            ),
            AppCharacteristic(
                name="has_iterator_operations",
                value=None,
                category="monitored_operations",
                display_name="Uses Iterators",
                description="App uses Iterator-related APIs that may have monitored specifications"
            ),
            AppCharacteristic(
                name="has_io_operations",
                value=None,
                category="monitored_operations",
                display_name="Uses I/O Operations",
                description="App uses I/O operations that may have monitored specifications"
            ),
            AppCharacteristic(
                name="monitored_operations_density",
                value=None,
                category="monitoring",
                display_name="Monitored Operations Density",
                description="Ratio of methods with monitored operations to total methods"
            )
        ]
    
    def extract_app_characteristics(self, results: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Extract characteristics from apps based on analysis results.
        
        Args:
            results: Analysis results dictionary from ResultsLoader
            
        Returns:
            Dictionary mapping app names to their characteristics
        """
        app_characteristics = {}
        
        # Check if we have app-specific data
        if 'app_metrics' not in results:
            # Try to infer from the configuration data
            app_characteristics = self._infer_app_characteristics_from_configs(results)
        else:
            # Extract from app metrics
            app_metrics = results.get('app_metrics', {})
            
            for app_name, app_data in app_metrics.items():
                characteristics = {}
                
                # Basic metrics
                characteristics['activity_count'] = app_data.get('activity_count', 0)
                characteristics['method_count'] = app_data.get('method_count', 0)
                characteristics['has_mop_specs'] = app_data.get('mop_spec_count', 0) > 0
                
                # Try to extract other characteristics from static analysis data
                static_data = app_data.get('static_analysis', {})
                
                # Monitored operations - Cryptography
                characteristics['uses_encryption'] = (
                    static_data.get('uses_encryption', False) or
                    self._check_api_usage(static_data, ['javax.crypto', 'java.security'])
                )
                
                # Network usage
                characteristics['uses_network'] = (
                    static_data.get('uses_network', False) or
                    self._check_api_usage(static_data, ['java.net', 'okhttp', 'retrofit'])
                )
                
                # Location usage
                characteristics['uses_location'] = (
                    static_data.get('uses_location', False) or
                    self._check_api_usage(static_data, ['android.location'])
                )
                
                # Camera usage
                characteristics['uses_camera'] = (
                    static_data.get('uses_camera', False) or
                    self._check_api_usage(static_data, ['android.hardware.camera'])
                )
                
                # Audio usage
                characteristics['uses_audio'] = (
                    static_data.get('uses_audio', False) or
                    self._check_api_usage(static_data, ['android.media.AudioManager', 'android.media.MediaPlayer'])
                )
                
                # Database usage
                characteristics['uses_database'] = (
                    static_data.get('uses_database', False) or
                    self._check_api_usage(static_data, ['android.database.sqlite', 'androidx.room'])
                )
                
                # Iterator operations - monitored operations
                characteristics['has_iterator_operations'] = (
                    static_data.get('has_iterator_operations', False) or
                    self._check_api_usage(static_data, ['java.util.Iterator', 'java.util.ListIterator'])
                )
                
                # I/O operations - monitored operations
                characteristics['has_io_operations'] = (
                    static_data.get('has_io_operations', False) or
                    self._check_api_usage(static_data, ['java.io', 'java.nio', 'android.os.FileObserver'])
                )
                
                # Monitored operations density
                if 'mop_spec_count' in app_data and 'method_count' in app_data and app_data['method_count'] > 0:
                    characteristics['monitored_operations_density'] = app_data['mop_spec_count'] / app_data['method_count']
                else:
                    characteristics['monitored_operations_density'] = 0.0
                
                # UI complexity
                ui_data = static_data.get('ui_components', {})
                layout_count = ui_data.get('layout_count', 0)
                widget_count = ui_data.get('widget_count', 0)
                
                # Consider UI complex if it has many layouts or widgets
                characteristics['complex_ui'] = layout_count > 10 or widget_count > 30
                
                # Add to app characteristics
                app_characteristics[app_name] = characteristics
        
        return app_characteristics
    
    def _infer_app_characteristics_from_configs(self, results: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Infer app characteristics from configuration results.
        Used when direct app data is not available.
        
        Args:
            results: Analysis results dictionary
            
        Returns:
            Dictionary mapping app names to their characteristics
        """
        app_characteristics = {}
        
        # Get configuration comparisons
        comparisons = results.get('configuration_comparisons', {})
        
        # Extract app names from results
        app_names = set()
        
        # Collect app names from result directories
        for config_id, data in comparisons.items():
            # Recursively check all fields for app names
            self._collect_app_names(data, app_names)
        
        # For each app, infer characteristics
        for app_name in app_names:
            # Default characteristics with dummy values
            characteristics = {
                'activity_count': 0,
                'method_count': 0,
                'has_mop_specs': False,
                'uses_encryption': False,
                'uses_network': False,
                'uses_location': False,
                'uses_camera': False,
                'uses_audio': False,
                'uses_database': False,
                'complex_ui': False,
                'has_iterator_operations': False,
                'has_io_operations': False,
                'monitored_operations_density': 0.0
            }
            
            # Try to infer characteristics from app name and other data
            if any(term in app_name.lower() for term in ['crypt', 'secure', 'password', 'key']):
                characteristics['uses_encryption'] = True
            
            if any(term in app_name.lower() for term in ['net', 'http', 'web', 'fetch']):
                characteristics['uses_network'] = True
                
            if any(term in app_name.lower() for term in ['location', 'map', 'gps']):
                characteristics['uses_location'] = True
                
            if any(term in app_name.lower() for term in ['camera', 'photo', 'image']):
                characteristics['uses_camera'] = True
                
            if any(term in app_name.lower() for term in ['audio', 'sound', 'music', 'player']):
                characteristics['uses_audio'] = True
                
            if any(term in app_name.lower() for term in ['db', 'data', 'store']):
                characteristics['uses_database'] = True
            
            # Try to infer iterator usage from app name
            if any(term in app_name.lower() for term in ['list', 'iterator', 'collection']):
                characteristics['has_iterator_operations'] = True
                
            # Try to infer I/O operations from app name
            if any(term in app_name.lower() for term in ['file', 'io', 'storage', 'read', 'write']):
                characteristics['has_io_operations'] = True
                
            # Add to app characteristics
            app_characteristics[app_name] = characteristics
        
        return app_characteristics
    
    def _collect_app_names(self, data: Any, app_names: Set[str]):
        """
        Recursively collect app names from result data.
        
        Args:
            data: Data to search
            app_names: Set to add app names to
        """
        if isinstance(data, dict):
            for key, value in data.items():
                if key == 'app_name' and isinstance(value, str):
                    app_names.add(value)
                else:
                    self._collect_app_names(value, app_names)
        elif isinstance(data, list):
            for item in data:
                self._collect_app_names(item, app_names)
    
    def _check_api_usage(self, static_data: Dict[str, Any], api_prefixes: List[str]) -> bool:
        """
        Check if an app uses specific APIs based on static analysis data.
        
        Args:
            static_data: Static analysis data
            api_prefixes: List of API prefixes to check
            
        Returns:
            True if any of the APIs are used, False otherwise
        """
        # Check imports
        imports = static_data.get('imports', [])
        if imports:
            for api_prefix in api_prefixes:
                if any(imp.startswith(api_prefix) for imp in imports):
                    return True
        
        # Check method calls
        method_calls = static_data.get('method_calls', [])
        if method_calls:
            for api_prefix in api_prefixes:
                if any(call.startswith(api_prefix) for call in method_calls):
                    return True
        
        return False
    
    def analyze_correlations(self, results: Dict[str, Any], 
                            app_characteristics: Optional[Dict[str, Dict[str, Any]]] = None) -> List[CorrelationResult]:
        """
        Analyze correlations between app characteristics and configuration performance.
        
        Args:
            results: Analysis results dictionary from ResultsLoader
            app_characteristics: Dictionary mapping app names to their characteristics (optional)
            
        Returns:
            List of correlation results
        """
        correlations = []
        
        # Extract app characteristics if not provided
        if app_characteristics is None:
            app_characteristics = self.extract_app_characteristics(results)
        
        # No app characteristics available
        if not app_characteristics:
            self.logger.warning("No app characteristics available for correlation analysis")
            return correlations
        
        # Get configuration comparisons
        comparisons = results.get('configuration_comparisons', {})
        
        # No configurations available
        if not comparisons:
            self.logger.warning("No configuration comparisons available for correlation analysis")
            return correlations
        
        # Extract metrics to correlate
        metrics = [
            'avg_method_coverage',
            'avg_activity_coverage',
            'avg_mop_method_coverage',
            'avg_mop_error_count',
            'avg_mop_unique_errors',
            'avg_monitored_operations_triggered',
            'avg_monitored_operations_ratio',
            'avg_execution_time',
            'overall_score'
        ]
        
        # For each configuration, analyze correlation with app characteristics
        for config_id, config_data in comparisons.items():
            # For each metric
            for metric in metrics:
                # For each app characteristic
                for char_name in app_characteristics[list(app_characteristics.keys())[0]].keys():
                    # Get app-specific performance for this config
                    app_performance = self._get_app_performance(results, config_id, metric)
                    
                    # Get characteristic values
                    char_values = {}
                    for app_name, chars in app_characteristics.items():
                        if app_name in app_performance and char_name in chars:
                            char_values[app_name] = chars[char_name]
                    
                    # Skip if not enough samples
                    if len(char_values) < self.min_samples:
                        continue
                    
                    # Calculate correlation
                    correlation_value, p_value = self._calculate_correlation(
                        list(char_values.values()), 
                        [app_performance[app] for app in char_values.keys()]
                    )
                    
                    # Skip if correlation is too low
                    if abs(correlation_value) < 0.3:
                        continue
                    
                    # Calculate confidence
                    confidence = self._calculate_confidence(correlation_value, p_value, len(char_values))
                    
                    # Generate explanation
                    explanation = self._generate_correlation_explanation(
                        char_name, metric, config_id, correlation_value, confidence
                    )
                    
                    # Add correlation result
                    correlations.append(CorrelationResult(
                        app_characteristic=char_name,
                        config_metric=metric,
                        config_id=config_id,
                        correlation_value=correlation_value,
                        sample_size=len(char_values),
                        p_value=p_value,
                        confidence=confidence,
                        explanation=explanation
                    ))
        
        # Sort correlations by absolute correlation value
        correlations.sort(key=lambda x: abs(x.correlation_value), reverse=True)
        
        self.logger.info(f"Found {len(correlations)} correlations between app characteristics and configurations")
        
        return correlations
    
    def _get_app_performance(self, results: Dict[str, Any], config_id: str, metric: str) -> Dict[str, float]:
        """
        Get app-specific performance for a configuration and metric.
        
        Args:
            results: Analysis results dictionary
            config_id: Configuration ID
            metric: Metric name
            
        Returns:
            Dictionary mapping app names to performance values
        """
        app_performance = {}
        
        # Try to get from app metrics
        app_metrics = results.get('app_metrics', {})
        
        if app_metrics:
            for app_name, app_data in app_metrics.items():
                config_metrics = app_data.get('config_metrics', {})
                if config_id in config_metrics and metric in config_metrics[config_id]:
                    app_performance[app_name] = config_metrics[config_id][metric]
        
        # If no app metrics, try to infer from config results
        if not app_performance:
            # Try to find reconstructed results
            reconstructed_results = results.get('reconstructed_results', [])
            
            if reconstructed_results:
                for result in reconstructed_results:
                    if result.get('config_id') == config_id:
                        app_name = result.get('app_name')
                        if app_name and 'metrics' in result:
                            app_performance[app_name] = result['metrics'].get(metric, 0)
        
        return app_performance
    
    def _calculate_correlation(self, x_values: List[Any], y_values: List[float]) -> Tuple[float, Optional[float]]:
        """
        Calculate correlation between two sets of values.
        
        Args:
            x_values: List of x values (characteristic values)
            y_values: List of y values (performance values)
            
        Returns:
            Tuple of (correlation coefficient, p-value)
        """
        try:
            # Convert non-numeric values to numeric
            x_numeric = []
            for val in x_values:
                if isinstance(val, bool):
                    x_numeric.append(1 if val else 0)
                elif isinstance(val, (int, float)):
                    x_numeric.append(val)
                else:
                    # Skip non-numeric values
                    return 0.0, None
            
            # Skip if all values are the same
            if len(set(x_numeric)) <= 1 or len(set(y_values)) <= 1:
                return 0.0, None
            
            # Calculate Pearson correlation
            from scipy.stats import pearsonr
            correlation, p_value = pearsonr(x_numeric, y_values)
            
            return correlation, p_value
        except Exception as e:
            self.logger.error(f"Error calculating correlation: {str(e)}")
            return 0.0, None
    
    def _calculate_confidence(self, correlation: float, p_value: Optional[float], sample_size: int) -> str:
        """
        Calculate confidence level based on correlation and p-value.
        
        Args:
            correlation: Correlation coefficient
            p_value: P-value
            sample_size: Number of samples
            
        Returns:
            Confidence level ("low", "medium", "high")
        """
        # Check absolute correlation
        abs_corr = abs(correlation)
        
        # High confidence for strong correlations with low p-value and good sample size
        if abs_corr > 0.7 and (p_value is None or p_value < 0.05) and sample_size >= 10:
            return "high"
        
        # Medium confidence for moderate correlations with reasonable p-value and sample size
        elif abs_corr > 0.5 and (p_value is None or p_value < 0.1) and sample_size >= 7:
            return "medium"
        
        # Low confidence for other cases
        else:
            return "low"
    
    def _generate_correlation_explanation(self, characteristic: str, metric: str, config_id: str, 
                                         correlation: float, confidence: str) -> str:
        """
        Generate a human-readable explanation for a correlation.
        
        Args:
            characteristic: App characteristic name
            metric: Configuration metric name
            config_id: Configuration ID
            correlation: Correlation coefficient
            confidence: Confidence level
            
        Returns:
            Human-readable explanation
        """
        # Format characteristic name
        char_display = characteristic.replace('_', ' ').title()
        
        # Format metric name
        metric_display = metric.replace('avg_', '').replace('_', ' ').title()
        
        # Format direction
        if correlation > 0:
            direction = "positive"
            effect = "increases"
        else:
            direction = "negative"
            effect = "decreases"
        
        # Format strength
        abs_corr = abs(correlation)
        if abs_corr > 0.7:
            strength = "strong"
        elif abs_corr > 0.5:
            strength = "moderate"
        else:
            strength = "weak"
        
        # Generate explanation
        explanation = (
            f"There is a {strength} {direction} correlation (r={correlation:.2f}, {confidence} confidence) "
            f"between '{char_display}' and '{metric_display}' for configuration '{config_id}'. "
            f"This suggests that when apps {characteristic.replace('_', ' ')}, "
            f"this configuration {effect} {metric_display.lower()}."
        )
        
        return explanation
    
    def generate_recommendations(self, correlations: List[CorrelationResult], 
                               app_characteristics: Dict[str, Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate configuration recommendations based on correlations.
        
        Args:
            correlations: List of correlation results
            app_characteristics: Dictionary mapping app names to their characteristics
            
        Returns:
            Dictionary mapping app characteristics to recommended configurations
        """
        recommendations = {}
        
        # Group correlations by app characteristic
        by_characteristic = defaultdict(list)
        for corr in correlations:
            by_characteristic[corr.app_characteristic].append(corr)
        
        # Generate recommendations for each characteristic
        for char_name, corrs in by_characteristic.items():
            # Skip if not enough correlations
            if len(corrs) < 3:
                continue
                
            char_recommendations = []
            
            # Sort correlations by metric importance
            metric_priority = {
                'overall_score': 1,
                'avg_method_coverage': 2,
                'avg_activity_coverage': 3,
                'avg_mop_method_coverage': 4,  # Monitored operations method coverage
                'avg_mop_error_count': 5,      # Number of monitored operations violations detected
                'avg_mop_unique_errors': 6,    # Number of unique monitored operations violations
                'avg_execution_time': 7
            }
            
            sorted_corrs = sorted(corrs, key=lambda x: (
                0 if x.confidence == "high" else 1 if x.confidence == "medium" else 2,
                metric_priority.get(x.config_metric, 99),
                -abs(x.correlation_value)
            ))
            
            # Get top correlations
            top_corrs = sorted_corrs[:5]
            
            # Find positive correlations with overall score
            positive_score_corrs = [
                c for c in corrs 
                if c.config_metric == 'overall_score' and c.correlation_value > 0
            ]
            
            # Sort by correlation value
            positive_score_corrs.sort(key=lambda x: x.correlation_value, reverse=True)
            
            # Add top configurations
            for corr in positive_score_corrs[:3]:
                # Skip already added
                if any(r['config_id'] == corr.config_id for r in char_recommendations):
                    continue
                    
                # Add recommendation
                char_recommendations.append({
                    'config_id': corr.config_id,
                    'correlation': corr.correlation_value,
                    'confidence': corr.confidence,
                    'metric': corr.config_metric,
                    'explanation': f"Recommended for apps with {char_name.replace('_', ' ')} "
                                  f"(correlation: {corr.correlation_value:.2f}, {corr.confidence} confidence)"
                })
            
            # Add remaining unique recommendations
            for corr in top_corrs:
                # Skip already added
                if any(r['config_id'] == corr.config_id for r in char_recommendations):
                    continue
                    
                # Add recommendation
                char_recommendations.append({
                    'config_id': corr.config_id,
                    'correlation': corr.correlation_value,
                    'confidence': corr.confidence,
                    'metric': corr.config_metric,
                    'explanation': f"May improve {corr.config_metric.replace('avg_', '').replace('_', ' ')} "
                                  f"for apps with {char_name.replace('_', ' ')}"
                })
            
            # Add to recommendations
            if char_recommendations:
                recommendations[char_name] = char_recommendations
        
        return recommendations
    
    def generate_app_specific_recommendations(self, app_name: str, app_char: Dict[str, Any],
                                           recommendations: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Generate recommendations for a specific app based on its characteristics.
        
        Args:
            app_name: Name of the app
            app_char: App characteristics dictionary
            recommendations: Dictionary of recommendations by characteristic
            
        Returns:
            List of recommended configurations for the app
        """
        app_recommendations = []
        
        # For each characteristic that applies to this app
        for char_name, value in app_char.items():
            # Skip if not a boolean or is False
            if not isinstance(value, bool) or not value:
                continue
                
            # Skip if no recommendations for this characteristic
            if char_name not in recommendations:
                continue
                
            # Add recommendations for this characteristic
            for recommendation in recommendations[char_name]:
                # Skip if already added
                if any(r['config_id'] == recommendation['config_id'] for r in app_recommendations):
                    continue
                    
                # Add to app recommendations
                app_recommendations.append({
                    'config_id': recommendation['config_id'],
                    'reason': f"Based on app characteristic: {char_name.replace('_', ' ')}",
                    'confidence': recommendation['confidence'],
                    'explanation': recommendation['explanation']
                })
        
        # Sort by confidence
        app_recommendations.sort(
            key=lambda x: 0 if x['confidence'] == "high" else 1 if x['confidence'] == "medium" else 2
        )
        
        return app_recommendations
    
    def generate_report(self, correlations: List[CorrelationResult], 
                       app_characteristics: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a comprehensive report on correlations and recommendations.
        
        Args:
            correlations: List of correlation results
            app_characteristics: Dictionary mapping app names to their characteristics
            
        Returns:
            Report dictionary
        """
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_correlations': len(correlations),
            'app_count': len(app_characteristics),
            'characteristic_correlations': {},
            'config_correlations': {},
            'recommendations': {},
            'app_recommendations': {},
            'top_correlations': []
        }
        
        # Skip if no correlations
        if not correlations:
            return report
        
        # Generate recommendations
        recommendations = self.generate_recommendations(correlations, app_characteristics)
        report['recommendations'] = recommendations
        
        # Generate app-specific recommendations
        app_recommendations = {}
        for app_name, app_char in app_characteristics.items():
            app_recs = self.generate_app_specific_recommendations(app_name, app_char, recommendations)
            if app_recs:
                app_recommendations[app_name] = app_recs
        report['app_recommendations'] = app_recommendations
        
        # Group correlations by characteristic
        by_characteristic = defaultdict(list)
        for corr in correlations:
            by_characteristic[corr.app_characteristic].append(self._correlation_to_dict(corr))
        report['characteristic_correlations'] = dict(by_characteristic)
        
        # Group correlations by configuration
        by_config = defaultdict(list)
        for corr in correlations:
            by_config[corr.config_id].append(self._correlation_to_dict(corr))
        report['config_correlations'] = dict(by_config)
        
        # Add top correlations
        top_correlations = []
        for corr in sorted(correlations, key=lambda x: abs(x.correlation_value), reverse=True)[:20]:
            top_correlations.append(self._correlation_to_dict(corr))
        report['top_correlations'] = top_correlations
        
        return report
    
    def _correlation_to_dict(self, correlation: CorrelationResult) -> Dict[str, Any]:
        """
        Convert a correlation result to a dictionary.
        
        Args:
            correlation: Correlation result
            
        Returns:
            Dictionary representation of the correlation
        """
        return {
            'app_characteristic': correlation.app_characteristic,
            'config_metric': correlation.config_metric,
            'config_id': correlation.config_id,
            'correlation_value': correlation.correlation_value,
            'sample_size': correlation.sample_size,
            'p_value': correlation.p_value,
            'confidence': correlation.confidence,
            'explanation': correlation.explanation
        }


# Convenient function
def analyze_correlations(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze correlations between app characteristics and configuration performance.
    
    Args:
        results: Analysis results dictionary from ResultsLoader
        
    Returns:
        Correlation analysis report
    """
    analyzer = CorrelationAnalyzer()
    app_characteristics = analyzer.extract_app_characteristics(results)
    correlations = analyzer.analyze_correlations(results, app_characteristics)
    return analyzer.generate_report(correlations, app_characteristics)