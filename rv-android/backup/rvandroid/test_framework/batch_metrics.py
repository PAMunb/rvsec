"""
Batch Actions Metrics for the test framework.

This module provides metrics collection and processing specific to 
batch action strategies, enabling analysis of batch vs. single action performance.
"""

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Tuple

class BatchMetricsCollector:
    """
    Collects metrics specific to batch action strategy performance.
    
    ### Key Responsibilities:
    - Tracks batch action execution metrics
    - Measures efficiency improvements from batch processing
    - Compares batch vs. single action performance
    - Analyzes MOP relevance in batch operations
    - Provides integration with the test framework results
    """
    
    def __init__(self):
        """Initialize the batch metrics collector."""
        # Basic metrics
        self.total_batch_executions = 0
        self.total_single_actions = 0
        self.successful_batch_executions = 0
        self.successful_single_actions = 0
        
        # Performance metrics
        self.batch_execution_times = []  # Time to execute entire batch
        self.single_action_times = []    # Time per individual action
        self.average_batch_size = 0      # Average actions per batch
        self.llm_call_count = 0          # Number of LLM API calls
        self.llm_token_usage = 0         # Total tokens used
        
        # Efficiency metrics
        self.time_per_effective_action = 0.0  # Total time / successful actions
        self.tokens_per_effective_action = 0.0  # Total tokens / successful actions
        self.llm_overhead_reduction = 0.0  # % reduction in LLM overhead
        
        # MOP-related metrics
        self.batch_mop_triggered_count = 0  # MOPs triggered in batch mode
        self.single_mop_triggered_count = 0  # MOPs triggered in single action mode
        self.batch_mop_coverage = 0.0  # % of MOPs covered in batch mode
        self.single_mop_coverage = 0.0  # % of MOPs covered in single mode
        
        # Pattern-specific metrics
        self.pattern_execution_stats = {}  # Success rates by pattern type
        self.pattern_distributions = {
            "form": 0,
            "list": 0, 
            "tabs": 0,
            "navigation": 0,
            "dialog": 0,
            "unknown": 0
        }
        
        # Batch completion metrics
        self.batch_completion_rates = {}  # % of batch actions completed by pattern type
        self.batch_interruption_reasons = {}  # Reasons for batch interruptions
        
        # Start time for rate calculations
        self.start_time = time.time()
        
    def record_batch_execution(self, batch_data: Dict[str, Any]) -> None:
        """
        Record metrics for a batch execution.
        
        Args:
            batch_data: Data about the batch execution including:
                - pattern_type: Type of UI pattern
                - batch_size: Number of actions in batch
                - execution_time: Time to execute the batch
                - success: Whether batch executed successfully
                - actions_completed: Number of actions completed
                - mops_triggered: Number of MOPs triggered
                - token_usage: Tokens used for batch generation
                - interruption_reason: Reason if batch was interrupted
        """
        self.total_batch_executions += 1
        
        # Extract data with defaults
        pattern_type = batch_data.get("pattern_type", "unknown")
        batch_size = batch_data.get("batch_size", 0)
        execution_time = batch_data.get("execution_time", 0.0)
        success = batch_data.get("success", False)
        actions_completed = batch_data.get("actions_completed", 0)
        mops_triggered = batch_data.get("mops_triggered", 0)
        token_usage = batch_data.get("token_usage", 0)
        interruption_reason = batch_data.get("interruption_reason", None)
        
        # Update basic metrics
        if success:
            self.successful_batch_executions += 1
        
        # Update action counts
        self.total_single_actions += actions_completed
        if success:
            self.successful_single_actions += actions_completed
        
        # Update performance metrics
        self.batch_execution_times.append(execution_time)
        self.llm_call_count += 1
        self.llm_token_usage += token_usage
        
        # Update average batch size
        total_batch_sizes = self.average_batch_size * (self.total_batch_executions - 1)
        self.average_batch_size = (total_batch_sizes + batch_size) / self.total_batch_executions
        
        # Update MOP metrics
        self.batch_mop_triggered_count += mops_triggered
        
        # Update pattern distribution
        if pattern_type in self.pattern_distributions:
            self.pattern_distributions[pattern_type] += 1
        else:
            self.pattern_distributions["unknown"] += 1
        
        # Update pattern success rates
        if pattern_type not in self.pattern_execution_stats:
            self.pattern_execution_stats[pattern_type] = {
                "executions": 0,
                "successes": 0,
                "execution_times": [],
                "batch_sizes": [],
                "mops_triggered": 0
            }
        
        stats = self.pattern_execution_stats[pattern_type]
        stats["executions"] += 1
        if success:
            stats["successes"] += 1
        stats["execution_times"].append(execution_time)
        stats["batch_sizes"].append(batch_size)
        stats["mops_triggered"] += mops_triggered
        
        # Update batch completion rates
        if pattern_type not in self.batch_completion_rates:
            self.batch_completion_rates[pattern_type] = {
                "total_actions": 0,
                "completed_actions": 0
            }
        
        completion_data = self.batch_completion_rates[pattern_type]
        completion_data["total_actions"] += batch_size
        completion_data["completed_actions"] += actions_completed
        
        # Update interruption reasons if applicable
        if not success and interruption_reason:
            if interruption_reason not in self.batch_interruption_reasons:
                self.batch_interruption_reasons[interruption_reason] = 0
            self.batch_interruption_reasons[interruption_reason] += 1
            
    def record_single_action(self, action_data: Dict[str, Any]) -> None:
        """
        Record metrics for a single action execution.
        
        Args:
            action_data: Data about the single action execution including:
                - execution_time: Time to execute the action
                - success: Whether action executed successfully
                - mops_triggered: Number of MOPs triggered
                - token_usage: Tokens used for action generation
        """
        # Extract data with defaults
        execution_time = action_data.get("execution_time", 0.0)
        success = action_data.get("success", False)
        mops_triggered = action_data.get("mops_triggered", 0)
        token_usage = action_data.get("token_usage", 0)
        
        # Update metrics
        self.single_action_times.append(execution_time)
        self.total_single_actions += 1
        if success:
            self.successful_single_actions += 1
        
        # Update MOP metrics
        self.single_mop_triggered_count += mops_triggered
        
        # Update token usage
        self.llm_token_usage += token_usage
        self.llm_call_count += 1
        
    def calculate_metrics(self) -> Dict[str, Any]:
        """
        Calculate derived metrics from collected data.
        
        Returns:
            Dictionary with calculated metrics
        """
        # Calculate time metrics
        avg_batch_time = sum(self.batch_execution_times) / len(self.batch_execution_times) if self.batch_execution_times else 0
        avg_single_time = sum(self.single_action_times) / len(self.single_action_times) if self.single_action_times else 0
        
        # Calculate efficiency metrics
        if self.successful_single_actions > 0:
            # Time per effective action
            total_execution_time = sum(self.batch_execution_times) + sum(self.single_action_times)
            self.time_per_effective_action = total_execution_time / self.successful_single_actions
            
            # Tokens per effective action
            self.tokens_per_effective_action = self.llm_token_usage / self.successful_single_actions
        
        # Calculate LLM overhead reduction
        # If we used single actions for everything, we would have needed one LLM call per action
        if self.total_single_actions > 0:
            single_action_equivalent_calls = self.total_single_actions
            actual_calls = self.llm_call_count
            call_reduction = (single_action_equivalent_calls - actual_calls) / single_action_equivalent_calls
            self.llm_overhead_reduction = call_reduction * 100  # Convert to percentage
        
        # Calculate batch completion rates for each pattern type
        completion_rates = {}
        for pattern, data in self.batch_completion_rates.items():
            if data["total_actions"] > 0:
                rate = (data["completed_actions"] / data["total_actions"]) * 100
                completion_rates[pattern] = rate
            else:
                completion_rates[pattern] = 0.0
        
        # Calculate pattern success rates
        pattern_success_rates = {}
        for pattern, stats in self.pattern_execution_stats.items():
            if stats["executions"] > 0:
                success_rate = (stats["successes"] / stats["executions"]) * 100
                avg_execution_time = sum(stats["execution_times"]) / len(stats["execution_times"])
                avg_batch_size = sum(stats["batch_sizes"]) / len(stats["batch_sizes"])
                
                pattern_success_rates[pattern] = {
                    "success_rate": success_rate,
                    "avg_execution_time": avg_execution_time,
                    "avg_batch_size": avg_batch_size,
                    "mops_triggered": stats["mops_triggered"]
                }
        
        # Calculate overall success rates
        batch_success_rate = (self.successful_batch_executions / self.total_batch_executions) * 100 if self.total_batch_executions > 0 else 0
        action_success_rate = (self.successful_single_actions / self.total_single_actions) * 100 if self.total_single_actions > 0 else 0
        
        # Calculate action throughput (actions per second)
        elapsed_time = time.time() - self.start_time
        action_throughput = self.total_single_actions / elapsed_time if elapsed_time > 0 else 0
        
        # Return calculated metrics
        return {
            # Summary metrics
            "batch_executions": self.total_batch_executions,
            "successful_batch_executions": self.successful_batch_executions,
            "batch_success_rate": batch_success_rate,
            "single_actions": self.total_single_actions,
            "successful_single_actions": self.successful_single_actions,
            "action_success_rate": action_success_rate,
            "average_batch_size": self.average_batch_size,
            
            # Performance metrics
            "avg_batch_execution_time": avg_batch_time,
            "avg_single_action_time": avg_single_time,
            "time_per_effective_action": self.time_per_effective_action,
            "tokens_per_effective_action": self.tokens_per_effective_action,
            "llm_call_count": self.llm_call_count,
            "llm_token_usage": self.llm_token_usage,
            "llm_overhead_reduction": self.llm_overhead_reduction,
            "action_throughput": action_throughput,
            
            # MOP metrics
            "batch_mop_triggered_count": self.batch_mop_triggered_count,
            "single_mop_triggered_count": self.single_mop_triggered_count,
            
            # Pattern metrics
            "pattern_distributions": self.pattern_distributions,
            "pattern_success_rates": pattern_success_rates,
            "batch_completion_rates": completion_rates,
            "batch_interruption_reasons": self.batch_interruption_reasons
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert collector data to dictionary for serialization.
        
        Returns:
            Dictionary with all metrics data
        """
        # Calculate metrics
        metrics = self.calculate_metrics()
        
        # Add raw data for detailed analysis
        metrics["raw_data"] = {
            "batch_execution_times": self.batch_execution_times,
            "single_action_times": self.single_action_times,
            "pattern_execution_stats": self.pattern_execution_stats,
            "batch_completion_rates": self.batch_completion_rates,
        }
        
        return metrics
    
    def save_to_file(self, file_path: str) -> bool:
        """
        Save metrics data to JSON file.
        
        Args:
            file_path: Path to save the metrics
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get metrics dictionary
            metrics = self.to_dict()
            
            # Save to file
            with open(file_path, "w") as f:
                json.dump(metrics, f, indent=2)
                
            return True
        except Exception as e:
            print(f"Error saving batch metrics: {e}")
            return False
            
    @classmethod
    def from_file(cls, file_path: str) -> Optional['BatchMetricsCollector']:
        """
        Load metrics from file.
        
        Args:
            file_path: Path to load metrics from
            
        Returns:
            BatchMetricsCollector instance or None if error
        """
        try:
            # Load from file
            with open(file_path, "r") as f:
                data = json.load(f)
                
            # Create new collector
            collector = cls()
            
            # Restore metrics (partial restoration of critical data)
            collector.total_batch_executions = data.get("batch_executions", 0)
            collector.successful_batch_executions = data.get("successful_batch_executions", 0)
            collector.total_single_actions = data.get("single_actions", 0)
            collector.successful_single_actions = data.get("successful_single_actions", 0)
            collector.average_batch_size = data.get("average_batch_size", 0)
            collector.llm_call_count = data.get("llm_call_count", 0)
            collector.llm_token_usage = data.get("llm_token_usage", 0)
            collector.batch_mop_triggered_count = data.get("batch_mop_triggered_count", 0)
            collector.single_mop_triggered_count = data.get("single_mop_triggered_count", 0)
            
            # Restore raw data if available
            if "raw_data" in data:
                raw_data = data["raw_data"]
                collector.batch_execution_times = raw_data.get("batch_execution_times", [])
                collector.single_action_times = raw_data.get("single_action_times", [])
                collector.pattern_execution_stats = raw_data.get("pattern_execution_stats", {})
                collector.batch_completion_rates = raw_data.get("batch_completion_rates", {})
                
            return collector
        except Exception as e:
            print(f"Error loading batch metrics: {e}")
            return None


@dataclass
class BatchActionMetrics:
    """
    Comprehensive metrics data structure for batch action analysis.
    
    Contains detailed metrics about batch action performance for analysis
    and comparison with single-action approaches.
    """
    # Configuration details
    config_id: str
    tool_name: str
    llm_type: str
    llm_model: str
    strategy_type: str
    
    # Batch execution metrics
    total_batch_executions: int = 0
    successful_batch_executions: int = 0
    batch_success_rate: float = 0.0
    average_batch_size: float = 0.0
    
    # Action execution metrics
    total_actions: int = 0
    successful_actions: int = 0
    action_success_rate: float = 0.0
    
    # Performance metrics
    avg_batch_execution_time: float = 0.0
    avg_single_action_time: float = 0.0
    time_per_effective_action: float = 0.0
    tokens_per_effective_action: float = 0.0
    llm_call_count: int = 0
    llm_token_usage: int = 0
    llm_overhead_reduction: float = 0.0
    action_throughput: float = 0.0
    
    # MOP metrics
    batch_mop_triggered_count: int = 0
    single_mop_triggered_count: int = 0
    mop_coverage: float = 0.0
    
    # Pattern metrics
    pattern_distributions: Dict[str, int] = field(default_factory=dict)
    pattern_success_rates: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    batch_completion_rates: Dict[str, float] = field(default_factory=dict)
    batch_interruption_reasons: Dict[str, int] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BatchActionMetrics':
        """Create metrics object from dictionary data."""
        return cls(**data)
    
    def get_efficiency_score(self) -> float:
        """
        Calculate an efficiency score (0-100) based on performance metrics.
        
        Higher scores indicate more efficient batch processing.
        
        Returns:
            Efficiency score between 0 and 100
        """
        # Calculate score components
        overhead_component = min(100, self.llm_overhead_reduction)
        
        # Time efficiency (lower is better)
        # Scale: 0s per action = 100, 10s per action = 0
        time_component = max(0, 100 - (self.time_per_effective_action * 10))
        
        # Batch success component
        success_component = self.batch_success_rate
        
        # Batch size component (larger is better)
        # Scale: 1 action = 0, 10+ actions = 100
        size_component = min(100, (self.average_batch_size - 1) * 10)
        
        # Combine components with weights
        weighted_score = (
            overhead_component * 0.35 +
            time_component * 0.25 +
            success_component * 0.25 +
            size_component * 0.15
        )
        
        return round(weighted_score, 2)
    
    def get_effectiveness_score(self) -> float:
        """
        Calculate an effectiveness score (0-100) based on output metrics.
        
        Higher scores indicate more effective batch processing in terms of
        successful actions, MOP coverage, and pattern handling.
        
        Returns:
            Effectiveness score between 0 and 100
        """
        # Action success component
        success_component = self.action_success_rate
        
        # MOP coverage component
        mop_component = min(100, self.mop_coverage * 100)
        
        # Pattern success component (average success rate across patterns)
        pattern_rates = [data.get("success_rate", 0) for data in self.pattern_success_rates.values()]
        pattern_component = sum(pattern_rates) / len(pattern_rates) if pattern_rates else 0
        
        # Completion rate component (average completion rate across patterns)
        completion_component = sum(self.batch_completion_rates.values()) / len(self.batch_completion_rates) if self.batch_completion_rates else 0
        
        # Combine components with weights
        weighted_score = (
            success_component * 0.30 +
            mop_component * 0.30 +
            pattern_component * 0.20 +
            completion_component * 0.20
        )
        
        return round(weighted_score, 2)