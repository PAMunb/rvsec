"""
Data structures for RVAgent prototype testing.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import json

@dataclass
class LLMMetrics:
    """Comprehensive LLM performance metrics from Ollama."""
    timestamp: float
    model_name: str
    prompt_tokens: int
    output_tokens: int
    total_tokens: int
    prompt_duration: float  # nanoseconds
    output_duration: float  # nanoseconds  
    total_duration: float   # nanoseconds
    load_duration: float    # nanoseconds
    temperature: float
    top_p: float
    top_k: int
    
    @property
    def tokens_per_second_input(self) -> float:
        """Calculate input tokens per second."""
        if self.prompt_duration > 0:
            return self.prompt_tokens / (self.prompt_duration / 1e9)
        return 0.0
        
    @property 
    def tokens_per_second_output(self) -> float:
        """Calculate output tokens per second."""
        if self.output_duration > 0:
            return self.output_tokens / (self.output_duration / 1e9)
        return 0.0

@dataclass
class TestResult:
    """Single test execution result."""
    # Test Identification
    app_name: str
    screenshot_id: str
    test_index: int  # Sequential test number
    
    # Model Configuration
    model_name: str
    temperature: float
    top_p: float
    top_k: int
    
    # Test Execution
    timestamp: datetime
    execution_time: float  # seconds
    timeout_occurred: bool = False
    error: Optional[str] = None
    
    # Coordinate Validation Results
    success: bool = False
    generated_coordinates: Optional[Tuple[int, int]] = None
    closest_ground_truth: Optional[Tuple[int, int]] = None
    distance_to_closest: float = float('inf')
    tolerance: int = 50
    
    # LLM Performance Metrics
    llm_metrics: Optional[LLMMetrics] = None
    
    # Additional Context
    ground_truth_count: int = 0  # Number of clickable elements found
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            'app_name': self.app_name,
            'screenshot_id': self.screenshot_id,
            'test_index': self.test_index,
            'model_name': self.model_name,
            'temperature': self.temperature,
            'top_p': self.top_p,
            'top_k': self.top_k,
            'timestamp': self.timestamp.isoformat(),
            'execution_time': self.execution_time,
            'timeout_occurred': self.timeout_occurred,
            'error': self.error,
            'success': self.success,
            'generated_coordinates': self.generated_coordinates,
            'closest_ground_truth': self.closest_ground_truth,
            'distance_to_closest': self.distance_to_closest,
            'tolerance': self.tolerance,
            'ground_truth_count': self.ground_truth_count
        }
        
        # Add LLM metrics if available
        if self.llm_metrics:
            result['llm_metrics'] = {
                'prompt_tokens': self.llm_metrics.prompt_tokens,
                'output_tokens': self.llm_metrics.output_tokens,
                'total_tokens': self.llm_metrics.total_tokens,
                'total_duration_ms': self.llm_metrics.total_duration / 1e6,
                'tokens_per_second_input': self.llm_metrics.tokens_per_second_input,
                'tokens_per_second_output': self.llm_metrics.tokens_per_second_output
            }
            
        return result

@dataclass
class ParameterCombination:
    """Parameter combination for grid search."""
    temperature: float
    top_p: float
    top_k: int
    
    def __str__(self) -> str:
        return f"temp={self.temperature}_p={self.top_p}_k={self.top_k}"

@dataclass
class ParameterPerformance:
    """Performance metrics for a parameter combination."""
    combination: ParameterCombination
    total_tests: int = 0
    successful_tests: int = 0
    avg_execution_time: float = 0.0
    avg_distance: float = 0.0
    avg_tokens_used: float = 0.0
    avg_tokens_per_second: float = 0.0
    timeout_count: int = 0
    error_count: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_tests == 0:
            return 0.0
        return (self.successful_tests / self.total_tests) * 100

@dataclass
class PrototypeReport:
    """Comprehensive prototype execution report."""
    # Execution Summary
    start_time: datetime
    end_time: Optional[datetime] = None
    total_tests: int = 0
    successful_tests: int = 0
    timeout_tests: int = 0
    error_tests: int = 0
    
    # Performance Metrics
    avg_execution_time: float = 0.0
    total_tokens_used: int = 0
    avg_tokens_per_test: float = 0.0
    
    # Parameter Analysis
    parameter_performance: Dict[str, ParameterPerformance] = field(default_factory=dict)
    best_parameters: Optional[ParameterCombination] = None
    worst_parameters: Optional[ParameterCombination] = None
    
    # Test Configuration
    config_summary: Dict[str, Any] = field(default_factory=dict)
    
    # Detailed Results
    all_results: List[TestResult] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Overall success rate percentage."""
        if self.total_tests == 0:
            return 0.0
        return (self.successful_tests / self.total_tests) * 100
    
    @property
    def total_duration(self) -> float:
        """Total execution duration in seconds."""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    def add_result(self, result: TestResult):
        """Add a test result to the report."""
        self.all_results.append(result)
        self.total_tests += 1
        
        if result.success:
            self.successful_tests += 1
        if result.timeout_occurred:
            self.timeout_tests += 1
        if result.error:
            self.error_tests += 1
            
        # Update parameter performance
        param_key = str(ParameterCombination(result.temperature, result.top_p, result.top_k))
        if param_key not in self.parameter_performance:
            self.parameter_performance[param_key] = ParameterPerformance(
                combination=ParameterCombination(result.temperature, result.top_p, result.top_k)
            )
            
        perf = self.parameter_performance[param_key]
        perf.total_tests += 1
        if result.success:
            perf.successful_tests += 1
        if result.timeout_occurred:
            perf.timeout_count += 1
        if result.error:
            perf.error_count += 1
            
        # Update averages (incremental calculation)
        n = perf.total_tests
        perf.avg_execution_time = ((perf.avg_execution_time * (n-1)) + result.execution_time) / n
        perf.avg_distance = ((perf.avg_distance * (n-1)) + result.distance_to_closest) / n
        
        if result.llm_metrics:
            perf.avg_tokens_used = ((perf.avg_tokens_used * (n-1)) + result.llm_metrics.total_tokens) / n
            perf.avg_tokens_per_second = ((perf.avg_tokens_per_second * (n-1)) + 
                                        result.llm_metrics.tokens_per_second_output) / n
    
    def finalize(self):
        """Finalize report calculations."""
        if not self.all_results:
            return
            
        # Update overall metrics
        self.avg_execution_time = sum(r.execution_time for r in self.all_results) / len(self.all_results)
        
        # Calculate token metrics
        valid_metrics = [r.llm_metrics for r in self.all_results if r.llm_metrics]
        if valid_metrics:
            self.total_tokens_used = sum(m.total_tokens for m in valid_metrics)
            self.avg_tokens_per_test = self.total_tokens_used / len(valid_metrics)
        
        # Find best/worst parameters
        if self.parameter_performance:
            sorted_params = sorted(self.parameter_performance.values(), 
                                 key=lambda x: x.success_rate, reverse=True)
            self.best_parameters = sorted_params[0].combination
            self.worst_parameters = sorted_params[-1].combination
            
        self.end_time = datetime.now()
    
    def save_to_json(self, file_path: str):
        """Save report to JSON file."""
        report_data = {
            'summary': {
                'start_time': self.start_time.isoformat(),
                'end_time': self.end_time.isoformat() if self.end_time else None,
                'total_duration_minutes': self.total_duration / 60,
                'total_tests': self.total_tests,
                'successful_tests': self.successful_tests,
                'success_rate': self.success_rate,
                'timeout_tests': self.timeout_tests,
                'error_tests': self.error_tests,
                'avg_execution_time': self.avg_execution_time,
                'total_tokens_used': self.total_tokens_used,
                'avg_tokens_per_test': self.avg_tokens_per_test
            },
            'best_parameters': {
                'temperature': self.best_parameters.temperature,
                'top_p': self.best_parameters.top_p,
                'top_k': self.best_parameters.top_k,
                'success_rate': max(p.success_rate for p in self.parameter_performance.values())
            } if self.best_parameters else None,
            'parameter_performance': {
                key: {
                    'temperature': perf.combination.temperature,
                    'top_p': perf.combination.top_p,
                    'top_k': perf.combination.top_k,
                    'success_rate': perf.success_rate,
                    'total_tests': perf.total_tests,
                    'avg_execution_time': perf.avg_execution_time,
                    'avg_tokens_used': perf.avg_tokens_used,
                    'timeout_count': perf.timeout_count,
                    'error_count': perf.error_count
                }
                for key, perf in self.parameter_performance.items()
            },
            'config': self.config_summary,
            'detailed_results': [result.to_dict() for result in self.all_results]
        }
        
        with open(file_path, 'w') as f:
            json.dump(report_data, f, indent=2)
    
    def print_summary(self):
        """Print summary report to console."""
        print("\n" + "=" * 80)
        print("RVAgent Phase 0 Prototype - Execution Summary")
        print("=" * 80)
        
        print(f"Total Tests: {self.total_tests:,}")
        print(f"Successful Tests: {self.successful_tests:,} ({self.success_rate:.1f}%)")
        print(f"Timeout Tests: {self.timeout_tests:,}")
        print(f"Error Tests: {self.error_tests:,}")
        print(f"Total Duration: {self.total_duration/3600:.1f} hours")
        print(f"Avg Execution Time: {self.avg_execution_time:.2f}s")
        print(f"Total Tokens Used: {self.total_tokens_used:,}")
        
        if self.best_parameters:
            print(f"\nBest Parameters: {self.best_parameters}")
            best_perf = max(self.parameter_performance.values(), key=lambda x: x.success_rate)
            print(f"Best Success Rate: {best_perf.success_rate:.1f}%")
            
        print("\nTop 3 Parameter Combinations:")
        sorted_params = sorted(self.parameter_performance.values(), 
                             key=lambda x: x.success_rate, reverse=True)[:3]
        for i, perf in enumerate(sorted_params, 1):
            print(f"{i}. {perf.combination} - {perf.success_rate:.1f}% success")
        
        print("=" * 80)