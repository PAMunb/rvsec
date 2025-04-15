# rvandroid/rvdroid/llm/service/llm_manager.py
"""
Resource-aware LLM manager for RVDroid.

This module provides a manager for LLM operations that adapts based on
system resource availability, implementing throttling and optimization
strategies to maintain system stability.
"""

import time
from typing import Dict, Any, List, Optional

from rvandroid.domain.static import StaticAnalysisData
from rvandroid.rvdroid.orchestration.resources import ResourceManager
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class ResourceAwareLLMManager:
    """
    Resource-aware manager for LLM operations that integrates with the
    ResourceManager to provide adaptive behavior based on system resources.

    ### Architectural Decisions:
    - Integrates LLM service with resource management
    - Implements adaptive strategies for resource conservation
    - Provides centralized control for LLM operations
    - Adds metrics collection for evaluation

    ### Role in the System:
    - Mediates between system components and LLM service
    - Manages LLM operation frequency based on resource availability
    - Optimizes context preparation based on resource constraints
    - Handles fallback mechanisms when resources are limited
    """

    def __init__(self, static_data: Optional[StaticAnalysisData] = None,
                 model_type: str = "ollama", model_name: str = "mistral:7b"):
        """
        Initialize the resource-aware LLM manager.

        Args:
            static_data: Optional static analysis data
            model_type: Type of LLM to use
            model_name: Name of the model to use
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.llm.service.manager",
            {CONTEXT_COMPONENT: "ResourceAwareLLMManager"}
        )

        # Initialize the resource manager
        self.resource_manager = ResourceManager()
        
        # Start resource monitoring
        self.resource_manager.start_monitoring()

        # Initialize LLM service (lazy initialization)
        self.static_data = static_data
        self.model_type = model_type
        self.model_name = model_name
        self._llm_service = None
        
        # LLM operation metrics
        self.operation_metrics = {
            "total_queries": 0,
            "throttled_queries": 0,
            "cache_hits": 0,
            "average_response_time": 0,
            "error_count": 0,
            "last_query_time": 0
        }
        
        # Operation throttling settings
        self.min_query_interval = 10  # Minimum seconds between queries
        self.adaptive_interval = True  # Adjust interval based on resources
        
        self.logger.info(f"Initialized resource-aware LLM manager with {model_type}/{model_name}")

    @property
    def llm_service(self):
        """Lazy initialization of LLM service."""
        if self._llm_service is None:
            from rvandroid.rvdroid.llm.llm_service import LLMService
            self.logger.info("Initializing LLM service")
            self._llm_service = LLMService(
                static_data=self.static_data,
                model_type=self.model_type,
                model_name=self.model_name
            )
        return self._llm_service

    def get_strategic_guidance(self, query_type: str, state_data: Dict[str, Any],
                              exploration_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get strategic guidance with resource awareness.

        Args:
            query_type: Type of guidance to request
            state_data: Current application state data
            exploration_context: Additional context about the exploration status

        Returns:
            Dictionary with strategic guidance
        """
        # Check if we should throttle this operation
        if self._should_throttle_llm_operation():
            self.operation_metrics["throttled_queries"] += 1
            self.logger.info(f"Throttling {query_type} guidance request due to resource constraints")
            
            # Use cached result if available
            cache_key = self._generate_cache_key(query_type, state_data)
            if hasattr(self.llm_service, 'query_cache') and cache_key in self.llm_service.query_cache:
                self.operation_metrics["cache_hits"] += 1
                return self.llm_service.query_cache[cache_key]["result"]
            
            # Otherwise return fallback guidance
            return self._generate_fallback_guidance(query_type)
        
        # Measure response time
        start_time = time.time()
        
        try:
            # Optimize context based on resource status
            optimized_context = self._optimize_context(exploration_context)
            
            # Get guidance from LLM service
            result = self.llm_service.get_strategic_guidance(
                query_type, state_data, optimized_context
            )
            
            # Update metrics
            self.operation_metrics["total_queries"] += 1
            self.operation_metrics["last_query_time"] = time.time()
            
            # Update average response time
            response_time = time.time() - start_time
            avg_time = self.operation_metrics["average_response_time"]
            total_queries = self.operation_metrics["total_queries"]
            
            if total_queries > 1:
                self.operation_metrics["average_response_time"] = (
                    (avg_time * (total_queries - 1) + response_time) / total_queries
                )
            else:
                self.operation_metrics["average_response_time"] = response_time
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting strategic guidance: {e}")
            self.operation_metrics["error_count"] += 1
            return self._generate_fallback_guidance(query_type)

    def get_action_feedback(self, action_data: Dict[str, Any], result: Dict[str, Any],
                           state_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get action feedback with resource awareness.

        Args:
            action_data: Data about the action that was executed
            result: Result of the action execution
            state_data: Current application state data

        Returns:
            Dictionary with action feedback
        """
        # Check if we should throttle this operation
        if self._should_throttle_llm_operation():
            self.operation_metrics["throttled_queries"] += 1
            self.logger.info("Throttling action feedback request due to resource constraints")
            
            # Return minimal feedback
            return {
                "feedback": "Resource constraints prevent detailed feedback",
                "suggestions": []
            }
        
        try:
            # Get feedback from LLM service
            result = self.llm_service.get_action_feedback(
                action_data, result, state_data
            )
            
            # Update metrics
            self.operation_metrics["total_queries"] += 1
            self.operation_metrics["last_query_time"] = time.time()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting action feedback: {e}")
            self.operation_metrics["error_count"] += 1
            
            # Return minimal feedback on error
            return {
                "feedback": "Error getting feedback",
                "suggestions": []
            }

    def get_exploration_strategy(self, state_data: Dict[str, Any],
                                exploration_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get exploration strategy with resource awareness.

        Args:
            state_data: Current application state data
            exploration_history: History of exploration states and actions

        Returns:
            Dictionary with exploration strategy
        """
        # Check if we should throttle this operation
        if self._should_throttle_llm_operation():
            self.operation_metrics["throttled_queries"] += 1
            self.logger.info("Throttling strategy request due to resource constraints")
            
            # Return default strategy
            return {
                "strategy": "random",
                "rationale": "Using random strategy due to resource constraints",
                "duration": 300
            }
        
        try:
            # Optimize history based on resource status
            optimized_history = self._optimize_history(exploration_history)
            
            # Get strategy from LLM service
            result = self.llm_service.get_exploration_strategy(
                state_data, optimized_history
            )
            
            # Update metrics
            self.operation_metrics["total_queries"] += 1
            self.operation_metrics["last_query_time"] = time.time()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting exploration strategy: {e}")
            self.operation_metrics["error_count"] += 1
            
            # Return default strategy on error
            return {
                "strategy": "random",
                "rationale": "Using random strategy due to error",
                "duration": 300
            }

    def interpret_security_context(self, state_data: Dict[str, Any],
                                  security_operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Interpret security context with resource awareness.

        Args:
            state_data: Current application state data
            security_operations: List of security operations available in current state

        Returns:
            Dictionary with security context interpretation
        """
        # Check if we should throttle this operation
        if self._should_throttle_llm_operation():
            self.operation_metrics["throttled_queries"] += 1
            self.logger.info("Throttling security context interpretation due to resource constraints")
            
            # Return default interpretation
            return {
                "risk_level": "unknown",
                "recommendations": []
            }
        
        try:
            # Optimize security operations based on resource status
            optimized_operations = security_operations
            if len(security_operations) > 10 and self.resource_manager.resource_status["throttling_level"] >= 1:
                # Prioritize directly reaching operations if there are many
                optimized_operations = [
                    op for op in security_operations 
                    if op.get("directly_reaches_mop", False)
                ]
                # Include some non-direct ones if needed
                if len(optimized_operations) < 5:
                    remaining = 5 - len(optimized_operations)
                    non_direct = [
                        op for op in security_operations 
                        if not op.get("directly_reaches_mop", False)
                    ][:remaining]
                    optimized_operations.extend(non_direct)
            
            # Get interpretation from LLM service
            result = self.llm_service.interpret_security_context(
                state_data, optimized_operations
            )
            
            # Update metrics
            self.operation_metrics["total_queries"] += 1
            self.operation_metrics["last_query_time"] = time.time()
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error interpreting security context: {e}")
            self.operation_metrics["error_count"] += 1
            
            # Return default interpretation on error
            return {
                "risk_level": "unknown",
                "recommendations": []
            }

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get metrics about LLM operations.

        Returns:
            Dictionary with operation metrics
        """
        # Add resource metrics
        metrics = self.operation_metrics.copy()
        
        # Add resource information
        resource_status = self.resource_manager.get_resource_status()
        metrics["resource_status"] = {
            "memory_usage": f"{resource_status['memory_usage'] * 100:.1f}%",
            "cpu_usage": f"{resource_status['cpu_usage'] * 100:.1f}%",
            "throttling_level": resource_status["throttling_level"]
        }
        
        # Add throttling stats
        metrics["throttling_percentage"] = (
            (metrics["throttled_queries"] / metrics["total_queries"]) * 100
            if metrics["total_queries"] > 0 else 0
        )
        
        return metrics

    def _should_throttle_llm_operation(self) -> bool:
        """
        Determine if LLM operations should be throttled.

        Returns:
            True if operation should be throttled, False otherwise
        """
        # Check resource-based throttling
        if self.resource_manager.should_throttle_operation("llm_query"):
            return True
            
        # Check time-based throttling
        current_time = time.time()
        elapsed = current_time - self.operation_metrics["last_query_time"]
        
        # Get minimum interval based on resource status
        if self.adaptive_interval:
            # Adjust interval based on throttling level
            # throttling_level = self.resource_manager.resource_status["throttling_level"]
            throttling_level = self.resource_manager.throttling_level
            if throttling_level == 1:
                min_interval = self.min_query_interval * 1.5
            elif throttling_level == 2:
                min_interval = self.min_query_interval * 3
            elif throttling_level == 3:
                min_interval = self.min_query_interval * 5
            else:
                min_interval = self.min_query_interval
        else:
            min_interval = self.min_query_interval
            
        return elapsed < min_interval

    def _optimize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimize context based on resource constraints.

        Args:
            context: Exploration context

        Returns:
            Optimized context
        """
        # Make a copy to avoid modifying the original
        optimized = context.copy()
        
        # Check throttling level
        throttling_level = self.resource_manager.resource_status["throttling_level"]
        
        if throttling_level >= 2:
            # Reduce history items for moderate and heavy throttling
            if "history" in optimized:
                # Keep only recent history under resource pressure
                if len(optimized["history"]) > 3:
                    optimized["history"] = optimized["history"][-3:]
                    
            # Simplify metrics
            if "metrics" in optimized and isinstance(optimized["metrics"], dict):
                # Keep only essential metrics
                essential_metrics = ["states_explored", "activity_coverage"]
                optimized["metrics"] = {
                    k: v for k, v in optimized["metrics"].items() 
                    if k in essential_metrics
                }
                
        if throttling_level >= 3:
            # For heavy throttling, minimize context further
            if "history" in optimized:
                # Keep only the most recent item
                if optimized["history"]:
                    optimized["history"] = [optimized["history"][-1]]
                    
        return optimized

    def _optimize_history(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Optimize history based on resource constraints.

        Args:
            history: Exploration history

        Returns:
            Optimized history
        """
        # Check throttling level
        throttling_level = self.resource_manager.resource_status["throttling_level"]
        
        if throttling_level == 0:
            # No optimization needed
            return history
            
        # For light throttling, keep last 5 items
        if throttling_level == 1 and len(history) > 5:
            return history[-5:]
            
        # For moderate throttling, keep last 3 items
        if throttling_level == 2 and len(history) > 3:
            return history[-3:]
            
        # For heavy throttling, keep only the last item
        if throttling_level == 3 and len(history) > 1:
            return history[-1:]
            
        return history

    def _generate_cache_key(self, query_type: str, state_data: Dict[str, Any]) -> str:
        """
        Generate a cache key for a query.

        Args:
            query_type: Type of guidance requested
            state_data: Current application state data

        Returns:
            Cache key string
        """
        # Use state fingerprint and activity for the key
        fingerprint = state_data.get("fingerprint", "unknown")
        activity = state_data.get("activity", "unknown")
        
        return f"{query_type}:{fingerprint}:{activity}"

    def _generate_fallback_guidance(self, query_type: str) -> Dict[str, Any]:
        """
        Generate fallback guidance when throttling prevents LLM query.

        Args:
            query_type: Type of guidance requested

        Returns:
            Dictionary with fallback guidance
        """
        if query_type == "exploration":
            return {
                "query_type": "exploration",
                "guidance": "Continue systematic exploration of UI elements.",
                "directives": [
                    {"type": "explore", "target": "interactive_elements", "priority": "high"}
                ],
                "timestamp": time.time()
            }
        elif query_type == "security":
            return {
                "query_type": "security",
                "guidance": "Focus on input fields and authentication flows.",
                "directives": [
                    {"type": "focus", "target": "input_fields", "priority": "high"}
                ],
                "timestamp": time.time()
            }
        else:
            return {
                "query_type": query_type,
                "guidance": "Continue with current exploration approach.",
                "directives": [
                    {"type": "explore", "target": "all", "priority": "medium"}
                ],
                "timestamp": time.time()
            }

    def cleanup(self) -> None:
        """Clean up resources."""
        # Stop resource monitoring
        self.resource_manager.cleanup()
        
        # Clean up LLM service if initialized
        if self._llm_service:
            self._llm_service.cleanup()
            
        self.logger.info("Resource-aware LLM manager cleaned up")