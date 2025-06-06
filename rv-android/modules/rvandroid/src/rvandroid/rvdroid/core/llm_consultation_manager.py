# rvandroid/rvdroid/core/llm_consultation_manager.py

"""
LLM consultation management for RVDroid.

This module provides components for managing LLM consultation, including
strategic guidance, action feedback, and directive processing.
"""

import time
from typing import Dict, Any, Optional, List, Tuple

from rv_android_core.parser.screen.visitor.model import ItemAction
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.rvdroid.core.component import Component
from rv_android_core.llm.prompt.framework import PromptFramework
from rv_android_core.llm.constants import ContextEntry, PromptStrategyType, StateEntry
from rv_android_core.util.error.decorators import handle_error
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.performance_monitor import PerformanceMonitor


class LLMConsultationManager(Component):
    """
    Manager for LLM consultation in RVDroid.
    
    ### Architectural Decisions:
    - Separates LLM consultation from core service functionality
    - Provides centralized management of LLM interactions
    - Implements resource-aware LLM usage with adaptive throttling
    - Processes and applies LLM guidance to testing strategies
    - Manages feedback loop from testing to improve guidance
    - Uses unified PromptFramework for consistent LLM interactions
    
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
        self.prompt_framework = None
        self.model = None
        
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
        
        # Get performance monitor
        self.performance_monitor = PerformanceMonitor.get_instance()
        
        # Get error handler
        self.error_handler = ErrorHandler.get_instance()
        
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
        
        # Initialize PromptFramework
        try:
            from rv_android_core.config.component_configurator import ComponentConfigurator
            framework_config = ComponentConfigurator(static_data=self.static_data)
            
            # Configure the framework with appropriate parameters
            self.prompt_framework = PromptFramework.create(framework_config)
            self.model = self.prompt_framework.model
            
            if not self.model:
                raise Exception("Failed to create language model")
                
            self.logger.info(f"Created PromptFramework with model: {self.model.model_name}")
        except Exception as e:
            self.logger.error(f"Failed to initialize PromptFramework: {e}")
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
        if not self.prompt_framework or not self.model:
            self.logger.error("Cannot start: missing PromptFramework or model")
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
        
        # Clean up model if available
        if self.model:
            try:
                if hasattr(self.model, 'cleanup'):
                    self.model.cleanup()
            except Exception as e:
                self.logger.warning(f"Error during model cleanup: {e}")
        
        self.prompt_framework = None
        self.model = None
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
        if not use_llm or not self.prompt_framework:
            self.logger.warning("LLM guidance is disabled or framework not available")
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
            
            # Create enhanced state with guidance context
            enhanced_state = state.copy()
            # Add context_type to state
            enhanced_state["guidance_context_type"] = context_type
            # Add exploration context information
            enhanced_state["exploration_metrics"] = exploration_context.get("metrics", {})
            enhanced_state["memory_stats"] = exploration_context.get("memory_stats", {})
            enhanced_state["identified_patterns"] = exploration_context.get("patterns", {})
            
            # Add prompt context
            prompt_context = self._create_prompt_context(enhanced_state, context_type)
            
            # Measure request time for resource monitoring
            start_time = time.time()
            
            # Use PromptFramework to generate response
            with self.performance_monitor.measure_time("strategic_guidance_generation"):
                response = self.prompt_framework.generate_with_llm(
                    PromptStrategyType.STANDARD, enhanced_state, prompt_context
                )
            
            request_time = time.time() - start_time
            
            # Process response into guidance format
            if not response:
                self.logger.error("No response from LLM for strategic guidance")
                return {"error": "No response from LLM", "directives": []}
            
            # Extract text content from response
            response_text = response.get_text_content() if hasattr(response, 'get_text_content') else str(response)
            
            # Parse directives from response text
            guidance = self._parse_directives_from_response(response_text, context_type)
            
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
            self.error_handler.handle_error(
                e,
                context={
                    "component": "LLMConsultationManager",
                    "function": "get_strategic_guidance",
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
        if not use_llm or not self.prompt_framework:
            self.logger.warning("LLM guidance is disabled or framework not available")
            return {"error": "LLM guidance disabled"}
        
        try:
            # Update statistics
            self.stats["action_feedback_requests"] += 1
            
            # Create enhanced state with action feedback context
            enhanced_state = state.copy()
            enhanced_state["action_data"] = action_data
            enhanced_state["action_result"] = result
            enhanced_state["feedback_request"] = True
            
            # Add prompt context
            prompt_context = self._create_prompt_context(enhanced_state, "action_feedback")
            
            # Measure request time for resource monitoring
            start_time = time.time()
            
            # Use PromptFramework to generate response
            with self.performance_monitor.measure_time("action_feedback_generation"):
                response = self.prompt_framework.generate_with_llm(
                    PromptStrategyType.STANDARD, enhanced_state, prompt_context
                )
            
            request_time = time.time() - start_time
            
            # Process response into feedback format
            if not response:
                self.logger.error("No response from LLM for action feedback")
                return {"error": "No response from LLM", "suggestions": []}
            
            # Extract text content from response
            response_text = response.get_text_content() if hasattr(response, 'get_text_content') else str(response)
            
            # Parse suggestions from response text
            feedback = self._parse_suggestions_from_response(response_text)
            
            # Update resource metrics
            self._update_resource_metrics(request_time)
            
            self.logger.debug(f"Received LLM feedback for action {action_data.get('id')}")
            return feedback
            
        except Exception as e:
            self.logger.error(f"Error getting LLM action feedback: {e}")
            
            # Log error with handler
            self.error_handler.handle_error(
                e,
                context={
                    "component": "LLMConsultationManager",
                    "function": "get_action_feedback",
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
            "resource_metrics": self.get_resource_metrics(),
            "model_name": self.model.model_name if self.model else "unknown"
        }
        
    def _create_prompt_context(self, state: Dict[str, Any], context_type: str) -> Dict[str, Any]:
        """
        Create context dictionary for prompt generation.
        
        Args:
            state: Current application state
            context_type: Type of prompt context
            
        Returns:
            Context dictionary with relevant information
        """
        app_package = state.get(StateEntry.PACKAGE_NAME, "")
        app_activity = state.get(StateEntry.ACTIVITY, "")
        
        context = {
            ContextEntry.APP_PACKAGE: app_package,
            ContextEntry.APP_ACTIVITY: app_activity,
            "context_type": context_type
        }
        
        # Add testing history if available
        if "testing_history" in state:
            context[ContextEntry.TESTING_HISTORY] = state["testing_history"]
            
        # Add guidance-specific context
        if context_type == "exploration":
            context["exploration_focus"] = "monitored_operations"
            if "exploration_metrics" in state:
                context["exploration_metrics"] = state["exploration_metrics"]
                
            # Set RVDroid exploration template
            context[ContextEntry.TEMPLATE] = "rvdroid:exploration"
        elif context_type == "action_feedback":
            context["action_feedback"] = True
            
            # Set RVDroid action feedback template
            context[ContextEntry.TEMPLATE] = "rvdroid:action_feedback"
        elif context_type == "strategy":
            # Set RVDroid strategy template
            context[ContextEntry.TEMPLATE] = "rvdroid:strategy"
        elif context_type == "context_detection":
            # Set RVDroid context detection template
            context[ContextEntry.TEMPLATE] = "rvdroid:context_detection"
        elif context_type == "monitored_operations":
            # Set RVDroid monitored operations template
            context[ContextEntry.TEMPLATE] = "rvdroid:monitored_operations"
        else:
            # For other contexts, use the general template
            context[ContextEntry.TEMPLATE] = "rvdroid:general"
            
        return context
        
    def _parse_directives_from_response(self, response_text: str, context_type: str) -> Dict[str, Any]:
        """
        Parse directives from LLM response text.
        
        Args:
            response_text: Raw response text from LLM
            context_type: Type of guidance context
            
        Returns:
            Guidance dictionary with parsed directives
        """
        directives = []
        insights = []
        
        # Simple parsing - look for sections
        lines = response_text.split('\n')
        current_section = None
        current_item = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for directive section headers
            if line.lower().startswith("directive:") or line.lower().startswith("directive "):
                if current_item and "type" in current_item:
                    directives.append(current_item)
                current_item = {}
                current_section = "directive"
                
                # Try to extract directive type from the header
                if ":" in line:
                    type_part = line.split(":", 1)[1].strip()
                    if " " in type_part:
                        directive_type = type_part.split(" ", 1)[0].lower()
                        if directive_type in ["strategy", "focus", "explore"]:
                            current_item["type"] = directive_type
                
            elif line.lower().startswith("insight:") or line.lower().startswith("insight "):
                if current_item and "type" in current_item:
                    directives.append(current_item)
                current_item = {}
                current_section = "insight"
                
                # Start a new insight
                insight_text = line.split(":", 1)[1].strip() if ":" in line else line
                insights.append(insight_text)
                
            elif current_section == "directive":
                # Process directive details
                if "type:" in line.lower():
                    directive_type = line.split(":", 1)[1].strip().lower()
                    if directive_type in ["strategy", "focus", "explore"]:
                        current_item["type"] = directive_type
                elif "target:" in line.lower() or "name:" in line.lower():
                    key = "target" if "target:" in line.lower() else "name"
                    value = line.split(":", 1)[1].strip()
                    current_item[key] = value
                elif "priority:" in line.lower():
                    try:
                        priority_str = line.split(":", 1)[1].strip()
                        # Handle priorities as words or numbers
                        if priority_str.lower() in ["high", "critical"]:
                            current_item["priority"] = 3
                        elif priority_str.lower() == "medium":
                            current_item["priority"] = 2
                        elif priority_str.lower() == "low":
                            current_item["priority"] = 1
                        else:
                            current_item["priority"] = int(priority_str)
                    except ValueError:
                        current_item["priority"] = 2  # Default to medium
                elif "description:" in line.lower() or ":" not in line:
                    # Either explicit description or just descriptive text
                    description = line.split(":", 1)[1].strip() if ":" in line else line
                    if "description" in current_item:
                        current_item["description"] += " " + description
                    else:
                        current_item["description"] = description
                        
            elif current_section == "insight" and line and ":" not in line.lower():
                # Append to last insight
                if insights:
                    insights[-1] += " " + line
        
        # Add the last item if it exists
        if current_item and "type" in current_item:
            directives.append(current_item)
            
        # Make sure each directive has at least a description
        for directive in directives:
            if "description" not in directive:
                if "target" in directive:
                    directive["description"] = f"Focus on {directive['target']}"
                elif "name" in directive:
                    directive["description"] = f"Use {directive['name']} strategy"
                else:
                    directive["description"] = "LLM directive"
        
        # Create the final guidance dictionary
        guidance = {
            "directives": directives,
            "insights": insights,
            "context_type": context_type,
            "timestamp": time.time()
        }
        
        return guidance
        
    def _parse_suggestions_from_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse suggestions from LLM response text for action feedback.
        
        Args:
            response_text: Raw response text from LLM
            
        Returns:
            Feedback dictionary with parsed suggestions
        """
        suggestions = []
        analysis = ""
        
        # Simple parsing - look for sections
        lines = response_text.split('\n')
        current_section = None
        current_item = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for section headers
            if line.lower().startswith("suggestion:") or line.lower().startswith("suggestion "):
                if current_item and "text" in current_item:
                    suggestions.append(current_item)
                current_item = {}
                current_section = "suggestion"
                
                # Extract suggestion text from the header
                if ":" in line:
                    suggestion_text = line.split(":", 1)[1].strip()
                    current_item["text"] = suggestion_text
                
            elif line.lower().startswith("analysis:") or line.lower().startswith("analysis "):
                if current_item and "text" in current_item:
                    suggestions.append(current_item)
                current_item = {}
                current_section = "analysis"
                
                # Start the analysis text
                analysis_text = line.split(":", 1)[1].strip() if ":" in line else line
                analysis = analysis_text
                
            elif current_section == "suggestion":
                # Process suggestion details
                if "priority:" in line.lower():
                    try:
                        priority_str = line.split(":", 1)[1].strip()
                        # Handle priorities as words or numbers
                        if priority_str.lower() in ["high", "critical"]:
                            current_item["priority"] = 3
                        elif priority_str.lower() == "medium":
                            current_item["priority"] = 2
                        elif priority_str.lower() == "low":
                            current_item["priority"] = 1
                        else:
                            current_item["priority"] = int(priority_str)
                    except ValueError:
                        current_item["priority"] = 2  # Default to medium
                elif ":" not in line:
                    # Continuation of suggestion text
                    if "text" in current_item:
                        current_item["text"] += " " + line
                    else:
                        current_item["text"] = line
                        
            elif current_section == "analysis" and ":" not in line:
                # Append to analysis text
                analysis += " " + line
        
        # Add the last item if it exists
        if current_item and "text" in current_item:
            suggestions.append(current_item)
            
        # Create the feedback dictionary
        feedback = {
            "suggestions": suggestions,
            "analysis": analysis,
            "timestamp": time.time()
        }
        
        return feedback
        
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