# rvandroid/rvdroid/core/llm_consultation_manager.py

"""
LLM consultation management for RVDroid.

This module provides components for managing LLM consultation, including
strategic guidance, action feedback, and directive processing.
"""

import time
from typing import Dict, Any, Optional, List, Tuple

from rvandroid.parser.screen.visitor.model import ItemAction
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.rvdroid.core.component import Component
from rvandroid.rvdroid.llm.llm_service import LLMService
from rvandroid.util.error.decorators import handle_error
from rvandroid.util.error.error_handler import ErrorHandler
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class LLMConsultationManager(Component):
    """
    Manager for LLM consultation in RVDroid.
    
    ### Architectural Decisions:
    - Separates LLM consultation from core service functionality
    - Provides centralized management of LLM interactions
    - Implements resource-aware LLM usage with adaptive throttling
    - Processes and applies LLM guidance to testing strategies
    - Manages feedback loop from testing to improve guidance
    
    ### Role in the System:
    - Provides strategic guidance for test exploration
    - Processes action feedback to improve testing
    - Manages LLM resource usage to prevent system overload
    - Applies LLM directives to various testing components
    - Enables intelligent, adaptive testing behaviors
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the LLM consultation manager.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__("LLMConsultationManager", config)
        
        # Extract configuration
        self.static_data = config.get("static_data") if config else None
        self.memory_system = config.get("memory_system")
        self.strategy_balancer = config.get("strategy_balancer")
        
        # Initialize components
        self.llm_manager = None
        self.llm_service = None
        
        # LLM usage settings
        self.guidance_interval = config.get("guidance_interval", 60)  # Default: once per minute
        self.last_llm_guidance_time = 0
        self.last_llm_guidance = None
        
        # Resource monitoring
        self.resource_metrics = {
            "memory_usage": 0.0,
            "cpu_usage": 0.0,
            "throttling_level": 0,
            "request_count": 0,
            "last_latency": 0
        }
        
        # Statistics
        self.stats = {
            "strategic_guidance_requests": 0,
            "action_feedback_requests": 0,
            "successful_guidance_requests": 0,
            "failed_guidance_requests": 0,
            "total_directives_applied": 0
        }
        
    @handle_error(level="ERROR")
    def initialize(self) -> bool:
        """
        Initialize the LLM consultation manager.
        
        Returns:
            True if initialization succeeded, False otherwise
        """
        self.logger.info("Initializing LLM consultation manager")
        
        # Check if LLM should be enabled
        use_llm = self.config.get("use_llm", True)
        if not use_llm:
            self.logger.info("LLM guidance is disabled in configuration")
            self.initialized = True
            return True
        
        # Initialize LLM manager based on availability
        try:
            # Try to use the MCP implementation first
            try:
                from rvandroid.mcp.service.llm_manager import ResourceAwareLLMManager as MCPResourceManager
                self.logger.info("Using MCP-based LLM manager")
                self.llm_manager = MCPResourceManager(self.static_data)
            except ImportError:
                # Fall back to legacy implementation
                self.logger.warning("MCP LLM manager not available, falling back to legacy implementation")
                from rvandroid.rvdroid.llm.service.llm_manager import ResourceAwareLLMManager
                self.llm_manager = ResourceAwareLLMManager(self.static_data)
                
            # Get LLM service from manager
            self.llm_service = self.llm_manager.llm_service if self.llm_manager else None
            
            if not self.llm_service:
                raise Exception("Failed to get LLM service from manager")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize LLM components: {e}")
            # Create a minimal LLM service directly if manager fails
            try:
                self.llm_service = LLMService(self.static_data)
                self.logger.info("Created basic LLM service as fallback")
            except Exception as e2:
                self.logger.error(f"Failed to create fallback LLM service: {e2}")
                return False
        
        # Reset statistics and tracking
        self.last_llm_guidance_time = 0
        self.last_llm_guidance = None
        self.stats = {
            "strategic_guidance_requests": 0,
            "action_feedback_requests": 0,
            "successful_guidance_requests": 0,
            "failed_guidance_requests": 0,
            "total_directives_applied": 0
        }
        
        self.initialized = True
        return True
        
    @handle_error(level="ERROR")
    def start(self) -> bool:
        """
        Start the LLM consultation manager.
        
        Returns:
            True if start succeeded, False otherwise
        """
        if not self.initialized:
            self.logger.error("Cannot start: LLM consultation manager not initialized")
            return False
            
        # Check if LLM should be enabled
        use_llm = self.config.get("use_llm", True)
        if not use_llm:
            self.logger.info("LLM guidance is disabled, skipping start")
            self.running = True
            return True
            
        self.logger.info("Starting LLM consultation manager")
        
        # Verify required components
        if not self.llm_service and not self.llm_manager:
            self.logger.error("Cannot start: missing LLM service or manager")
            return False
            
        self.running = True
        return True
        
    @handle_error(level="ERROR")
    def stop(self) -> bool:
        """
        Stop the LLM consultation manager.
        
        Returns:
            True if stop succeeded, False otherwise
        """
        if not self.running:
            self.logger.warning("LLM consultation manager is not running")
            return True
            
        self.logger.info("Stopping LLM consultation manager")
        
        self.running = False
        return True
        
    @handle_error(level="ERROR")
    def cleanup(self) -> None:
        """
        Clean up LLM consultation manager resources.
        """
        self.logger.info("Cleaning up LLM consultation manager")
        
        # Clean up LLM manager if available
        if self.llm_manager:
            try:
                if hasattr(self.llm_manager, 'cleanup'):
                    self.llm_manager.cleanup()
            except Exception as e:
                self.logger.warning(f"Error during LLM manager cleanup: {e}")
        
        # Clean up LLM service if available and not managed by manager
        if self.llm_service and not self.llm_manager:
            try:
                if hasattr(self.llm_service, 'cleanup'):
                    self.llm_service.cleanup()
            except Exception as e:
                self.logger.warning(f"Error during LLM service cleanup: {e}")
        
        self.llm_manager = None
        self.llm_service = None
        self.last_llm_guidance = None
        
        self.initialized = False
        self.running = False
        
    @handle_error(level="WARN")
    def get_strategic_guidance(self, context_type: str, state: Dict[str, Any], 
                             exploration_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get strategic guidance from LLM for testing.
        
        Args:
            context_type: Type of guidance context ("exploration", "exploitation", etc.)
            state: Current application state
            exploration_context: Additional context for guidance
            
        Returns:
            Guidance dictionary with directives and insights
        """
        if not self.running:
            self.logger.warning("LLM consultation manager is not running")
            return {"error": "LLM consultation manager not running"}
        
        # Check if LLM is enabled
        use_llm = self.config.get("use_llm", True)
        if not use_llm or not self.llm_manager:
            self.logger.warning("LLM guidance is disabled or manager not available")
            return {"error": "LLM guidance disabled"}
            
        # Check throttling interval
        current_time = time.time()
        time_since_last_guidance = current_time - self.last_llm_guidance_time
        if time_since_last_guidance < self.guidance_interval:
            self.logger.debug(f"Throttling LLM guidance (last request: {time_since_last_guidance:.1f}s ago)")
            # Return the last guidance if available
            if self.last_llm_guidance:
                return self.last_llm_guidance
            else:
                return {"throttled": True, "directives": []}
        
        try:
            # Update statistics
            self.stats["strategic_guidance_requests"] += 1
            
            # Get guidance from LLM manager
            start_time = time.time()
            guidance = self.llm_manager.get_strategic_guidance(context_type, state, exploration_context)
            request_time = time.time() - start_time
            
            # Store guidance and timestamp
            self.last_llm_guidance = guidance
            self.last_llm_guidance_time = current_time
            
            # Update resource metrics
            self._update_resource_metrics(request_time)
            
            # Update statistics
            self.stats["successful_guidance_requests"] += 1
            
            self.logger.info(f"Received strategic guidance from LLM ({len(guidance.get('directives', []))} directives)")
            return guidance
            
        except Exception as e:
            self.logger.error(f"Error getting LLM strategic guidance: {e}")
            self.stats["failed_guidance_requests"] += 1
            
            # Log error with handler
            error_handler = ErrorHandler.get_instance()
            error_handler.handle_error(
                "llm_strategic_guidance_error", 
                str(e),
                context={
                    "context_type": context_type,
                    "phase": "strategic_guidance"
                }
            )
            
            # Return empty guidance
            return {"error": str(e), "directives": []}
            
    @handle_error(level="WARN")
    def get_action_feedback(self, action_data: Dict[str, Any], result: Dict[str, Any],
                          state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get feedback from LLM about an executed action.
        
        Args:
            action_data: Information about the executed action
            result: Execution result
            state: Current application state
            
        Returns:
            Feedback dictionary with suggestions and insights
        """
        if not self.running:
            self.logger.warning("LLM consultation manager is not running")
            return {"error": "LLM consultation manager not running"}
        
        # Check if LLM is enabled
        use_llm = self.config.get("use_llm", True)
        if not use_llm or not self.llm_manager:
            self.logger.warning("LLM guidance is disabled or manager not available")
            return {"error": "LLM guidance disabled"}
        
        try:
            # Update statistics
            self.stats["action_feedback_requests"] += 1
            
            # Get feedback from LLM manager
            start_time = time.time()
            feedback = self.llm_manager.get_action_feedback(action_data, result, state)
            request_time = time.time() - start_time
            
            # Update resource metrics
            self._update_resource_metrics(request_time)
            
            self.logger.debug(f"Received LLM feedback for action {action_data.get('id')}")
            return feedback
            
        except Exception as e:
            self.logger.error(f"Error getting LLM action feedback: {e}")
            
            # Log error with handler
            error_handler = ErrorHandler.get_instance()
            error_handler.handle_error(
                "llm_action_feedback_error", 
                str(e),
                context={
                    "action_id": action_data.get("id", "unknown"),
                    "phase": "action_feedback"
                }
            )
            
            # Return empty feedback
            return {"error": str(e), "suggestions": []}
            
    @handle_error(level="WARN")
    def apply_directives(self, directives: List[Dict[str, Any]]) -> bool:
        """
        Apply directives from LLM to testing components.
        
        Args:
            directives: List of directives from LLM
            
        Returns:
            True if directives were applied successfully, False otherwise
        """
        if not self.running:
            self.logger.warning("LLM consultation manager is not running")
            return False
            
        if not directives:
            self.logger.debug("No directives to apply")
            return True
            
        directives_applied = 0
        for directive in directives:
            try:
                directive_type = directive.get("type", "")
                
                if directive_type == "strategy":
                    # Apply strategy directive
                    if self._apply_strategy_directive(directive):
                        directives_applied += 1
                        
                elif directive_type == "focus":
                    # Apply focus directive
                    if self._apply_focus_directive(directive):
                        directives_applied += 1
                        
                elif directive_type == "explore":
                    # Apply exploration directive
                    if self._apply_exploration_directive(directive):
                        directives_applied += 1
                        
                else:
                    self.logger.warning(f"Unknown directive type: {directive_type}")
                    
            except Exception as e:
                self.logger.error(f"Error applying directive {directive}: {e}")
                
        # Update statistics
        self.stats["total_directives_applied"] += directives_applied
        
        self.logger.info(f"Applied {directives_applied}/{len(directives)} LLM directives")
        return directives_applied > 0
        
    def get_last_guidance(self) -> Optional[Dict[str, Any]]:
        """
        Get the most recent LLM guidance.
        
        Returns:
            Last guidance dictionary or None if not available
        """
        return self.last_llm_guidance
        
    def get_resource_metrics(self) -> Dict[str, Any]:
        """
        Get resource usage metrics for LLM.
        
        Returns:
            Dictionary with resource metrics
        """
        # Try to get metrics from manager first
        if self.llm_manager and hasattr(self.llm_manager, 'get_metrics'):
            try:
                return self.llm_manager.get_metrics()
            except Exception as e:
                self.logger.warning(f"Error getting metrics from LLM manager: {e}")
                
        # Fall back to internal metrics
        return {
            "resource_status": self.resource_metrics,
            "request_stats": {
                "guidance_requests": self.stats["strategic_guidance_requests"],
                "feedback_requests": self.stats["action_feedback_requests"],
                "success_rate": (self.stats["successful_guidance_requests"] / 
                               max(1, self.stats["strategic_guidance_requests"]))
            }
        }
        
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get LLM usage statistics.
        
        Returns:
            Dictionary with usage statistics
        """
        return {
            **self.stats,
            "last_guidance_time": self.last_llm_guidance_time,
            "time_since_last_guidance": time.time() - self.last_llm_guidance_time if self.last_llm_guidance_time > 0 else 0,
            "resource_metrics": self.get_resource_metrics()
        }
        
    def _apply_strategy_directive(self, directive: Dict[str, Any]) -> bool:
        """
        Apply a strategy directive to the strategy balancer.
        
        Args:
            directive: Strategy directive
            
        Returns:
            True if directive was applied successfully, False otherwise
        """
        strategy_name = directive.get("name", "")
        if not strategy_name or not self.strategy_balancer:
            return False
            
        try:
            # Convert strategy name to class name format
            if not strategy_name.endswith("Strategy"):
                strategy_name = f"{strategy_name.capitalize()}Strategy"
                
            # Handle naming consistency - map legacy names to current names
            if strategy_name in ["SecurityFocusedStrategy", "SecurityfocusedStrategy", 
                               "MonitoredMethodFocusedStrategy", "MonitoredmethodfocusedStrategy"]:
                strategy_name = "SpecificationFocusedStrategy"
                
            # Update strategy balancer weights
            for strategy_info in self.strategy_balancer.strategies:
                strategy = strategy_info["strategy"]
                if strategy.__class__.__name__ == strategy_name:
                    strategy_info["weight"] *= 2.0  # Boost this strategy
                    self.logger.info(f"Boosted strategy weight for {strategy_name}")
                else:
                    strategy_info["weight"] *= 0.8  # Reduce others
                    
            # Normalize weights
            if hasattr(self.strategy_balancer, '_normalize_weights'):
                self.strategy_balancer._normalize_weights()
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error applying strategy directive: {e}")
            return False
            
    def _apply_focus_directive(self, directive: Dict[str, Any]) -> bool:
        """
        Apply a focus directive to the memory system.
        
        Args:
            directive: Focus directive
            
        Returns:
            True if directive was applied successfully, False otherwise
        """
        target = directive.get("target", "")
        if not target or not self.memory_system:
            return False
            
        try:
            # Update focus areas for exploration through memory system
            if hasattr(self.memory_system, 'exploration_optimizer'):
                # Adjust exploration parameters
                if "security" in target.lower() or "crypto" in target.lower() or "monitored" in target.lower():
                    # Support legacy "security" term and new "monitored method" terminology
                    if hasattr(self.memory_system.exploration_optimizer, 'exploration_parameters'):
                        # New parameter structure
                        self.memory_system.exploration_optimizer.exploration_parameters["monitored_method_factor"] = 0.8
                        # Check if we have specific focus on crypto vs general API
                        if "crypto" in target.lower():
                            self.memory_system.exploration_optimizer.exploration_parameters["crypto_spec_factor"] = 0.8
                        elif "api" in target.lower():
                            self.memory_system.exploration_optimizer.exploration_parameters["general_api_factor"] = 0.8
                        else:
                            # Balanced approach to both types
                            self.memory_system.exploration_optimizer.exploration_parameters["crypto_spec_factor"] = 0.6
                            self.memory_system.exploration_optimizer.exploration_parameters["general_api_factor"] = 0.6
                    else:
                        # Backward compatibility
                        self.memory_system.exploration_optimizer.security_focus_factor = 0.8
                elif "diversity" in target.lower():
                    if hasattr(self.memory_system.exploration_optimizer, 'exploration_parameters'):
                        self.memory_system.exploration_optimizer.exploration_parameters["breadth_factor"] = 0.8
                        self.memory_system.exploration_optimizer.exploration_parameters["novelty_factor"] = 0.8
                    else:
                        # Backward compatibility
                        self.memory_system.exploration_optimizer.diversity_factor = 0.8
                elif "exploration" in target.lower():
                    if hasattr(self.memory_system.exploration_optimizer, 'exploration_parameters'):
                        self.memory_system.exploration_optimizer.exploration_parameters["randomization_factor"] = 0.4
                    else:
                        # Backward compatibility
                        self.memory_system.exploration_optimizer.exploration_factor = 0.8
                        
                return True
                
        except Exception as e:
            self.logger.error(f"Error applying focus directive: {e}")
            return False
            
    def _apply_exploration_directive(self, directive: Dict[str, Any]) -> bool:
        """
        Apply an exploration directive to the memory system.
        
        Args:
            directive: Exploration directive
            
        Returns:
            True if directive was applied successfully, False otherwise
        """
        target = directive.get("target", "")
        if not target or not self.memory_system:
            return False
            
        try:
            # Update exploration phase
            if hasattr(self.memory_system, 'exploration_optimizer'):
                # Use our enhanced phase-based approach if available
                if hasattr(self.memory_system.exploration_optimizer, 'exploration_phases'):
                    if "initial" in target.lower() or "exploration" in target.lower():
                        self.memory_system.exploration_optimizer._transition_to_phase("initial_exploration")
                    elif "targeted" in target.lower() or "security" in target.lower() or "monitored" in target.lower():
                        self.memory_system.exploration_optimizer._transition_to_phase("targeted_exploration")
                    elif "deep" in target.lower() or "exploitation" in target.lower():
                        self.memory_system.exploration_optimizer._transition_to_phase("deep_exploration")
                    elif "coverage" in target.lower() or "optimize" in target.lower():
                        self.memory_system.exploration_optimizer._transition_to_phase("coverage_optimization")
                    elif "regression" in target.lower() or "revisit" in target.lower():
                        self.memory_system.exploration_optimizer._transition_to_phase("regression_testing")
                else:
                    # Backward compatibility
                    if "exploration" in target.lower():
                        self.memory_system.exploration_optimizer.exploration_phase = "exploration"
                        self.memory_system.exploration_optimizer._adjust_parameters_for_phase("exploration")
                    elif "exploitation" in target.lower():
                        self.memory_system.exploration_optimizer.exploration_phase = "exploitation"
                        self.memory_system.exploration_optimizer._adjust_parameters_for_phase("exploitation")
                    elif "security" in target.lower():
                        self.memory_system.exploration_optimizer.exploration_phase = "security_focus"
                        self.memory_system.exploration_optimizer._adjust_parameters_for_phase("security_focus")
                        
                return True
                
        except Exception as e:
            self.logger.error(f"Error applying exploration directive: {e}")
            return False
            
    def _update_resource_metrics(self, request_time: float) -> None:
        """
        Update internal resource metrics based on request time.
        
        Args:
            request_time: Time taken for LLM request in seconds
        """
        # Update request metrics
        self.resource_metrics["request_count"] += 1
        self.resource_metrics["last_latency"] = request_time
        
        # Try to get metrics from manager
        if self.llm_manager and hasattr(self.llm_manager, 'get_metrics'):
            try:
                manager_metrics = self.llm_manager.get_metrics()
                
                # Check if using MCP or legacy format for resource metrics
                if 'resource_status' in manager_metrics:
                    # Legacy format
                    status = manager_metrics['resource_status']
                    self.resource_metrics["memory_usage"] = status.get("memory_usage", 0.0)
                    self.resource_metrics["cpu_usage"] = status.get("cpu_usage", 0.0)
                    self.resource_metrics["throttling_level"] = status.get("throttling_level", 0)
                else:
                    # MCP format may have different structure
                    # Try to extract metrics from different formats
                    resource_status = manager_metrics.get('resources', manager_metrics)
                    self.resource_metrics["memory_usage"] = resource_status.get("memory_usage", 0.0)
                    self.resource_metrics["cpu_usage"] = resource_status.get("cpu_usage", 0.0)
                    self.resource_metrics["throttling_level"] = resource_status.get("throttling_level", 0)
                    
            except Exception as metrics_error:
                # Don't let metrics logging failure break the main functionality
                self.logger.warning(f"Error getting resource metrics: {metrics_error}")
                
        # Simple adaptive throttling based on request time
        # Longer requests may indicate system is under load
        if request_time > 5.0:  # More than 5 seconds
            # Increase guidance interval to reduce load
            self.guidance_interval = min(300, self.guidance_interval * 1.5)  # Max: 5 minutes
            self.logger.info(f"Increasing LLM guidance interval to {self.guidance_interval:.1f}s due to high latency")
        elif request_time < 2.0 and self.guidance_interval > 60:  # Fast response and currently throttled
            # Gradually reduce guidance interval
            self.guidance_interval = max(60, self.guidance_interval * 0.9)  # Min: 1 minute
            self.logger.info(f"Decreasing LLM guidance interval to {self.guidance_interval:.1f}s due to good performance")