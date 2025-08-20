"""
LLM Action Service with Unified Configuration Architecture

This module orchestrates the AI-driven test action generation system using unified
configuration management, eliminating parameter duplication and providing consistent
component initialization across the entire service.

### Architectural Overview:
This service coordinates the entire process of generating testing actions from the
current application state using unified configuration that combines LLM backend
configuration with prompt strategy configuration through composition.

### Key Features:
- Unified Configuration: Single configuration source for all service components
- Composition Architecture: Uses composed configurations instead of parameter duplication
- Strategy Integration: Full support for prompt strategies (BATCH_ACTION, STANDARD)
- Component Coordination: Orchestrates specialized components with consistent configuration
- Memory Integration: History-aware decision-making through memory systems

### Design Principles:
- Facade Pattern: Coordinates specialized components through unified interface
- Single Responsibility: Delegates specialized functions to dedicated components
- Dependency Injection: Configurable through dependency injection patterns
- Unified Framework: Standardized LLM interactions through PromptFramework
- Consistent Processing: All LLM responses processed in standardized format

### Integration Strategy:
- Receives unified RvAndroidToolConfig containing all necessary configuration
- Extracts LLM and prompt configurations from unified configuration
- Initializes all specialized components with appropriate configuration
- Provides unified interface for state processing and action generation
"""

from typing import Any, Dict, List

from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.event.bus import EventBus
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import LLMServiceError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.performance.performance_monitor import PerformanceMonitor
from rv_llm.llm.constants import ContextEntry, StateEntry, ContextMode
from rvandroid_tool.llm.prompt.rvandroid_framework import RVAndroidPromptFramework
from rvandroid_tool.config.tool_config import RvAndroidToolConfig
from rvandroid_tool.llm.service.action_generator import ActionGenerator
from rvandroid_tool.llm.service.llm_manager import LLMManager
from rvandroid_tool.llm.service.memory_manager import MemoryManager
from rvandroid_tool.llm.service.response_processor import ResponseProcessor
from rvandroid_tool.llm.service.state_enricher import StateEnricher
from rvandroid_tool.llm.service.transition_manager import TransitionManager


class LLMActionService:
    """
    Orchestrates the AI-driven test action generation system with unified configuration.
    
    This service coordinates the entire process of generating testing actions from the
    current application state, using unified configuration to ensure consistent behavior
    across all components.
    
    ### Architecture Overview:
    The service acts as a coordinator between multiple specialized components:
    - LLM backend management through LLMManager
    - Prompt generation through RVAndroidPromptFramework
    - State processing through specialized processors
    - Action generation through ActionGenerator
    
    ### Configuration Strategy:
    Uses composition to access both LLM and prompt configurations from the unified
    tool configuration, eliminating parameter duplication and ensuring configuration
    consistency.
    
    ### Component Initialization:
    1. Extract configurations from unified tool config
    2. Initialize LLM manager with backend configuration
    3. Create prompt framework with strategy configuration
    4. Initialize specialized processors with appropriate configurations
    
    ### Role in the System:
    - Provides unified interface for state processing and action generation
    - Coordinates flow between state analysis, LLM interaction, and action generation
    - Maintains consistent configuration across all specialized components
    - Enables history-aware decision-making through memory integration
    """

    @ErrorHandler.handle_errors(
        component="LLMActionService",
        operation="__init__"
    )
    def __init__(
            self,
            static_data: StaticAnalysisData,
            tool_config: RvAndroidToolConfig,
            **model_kwargs
    ):
        """
        Initialize LLM action service with unified configuration.
        
        This service orchestrates LLM-based action generation for Android testing,
        using unified configuration to ensure consistent behavior across all components.
        
        ### Architecture Overview:
        The service acts as a coordinator between multiple specialized components:
        - LLM backend management through LLMManager
        - Prompt generation through RVAndroidPromptFramework
        - State processing through specialized processors
        - Action generation through ActionGenerator
        
        ### Configuration Strategy:
        Uses composition to access both LLM and prompt configurations from the
        unified tool configuration, eliminating parameter duplication and
        ensuring configuration consistency.
        
        ### Component Initialization:
        1. Extract configurations from unified tool config
        2. Initialize LLM manager with backend configuration
        3. Create prompt framework with strategy configuration
        4. Initialize specialized processors with appropriate configurations
        
        Args:
            static_data: Static analysis data for the target application
            tool_config: Unified configuration containing LLM and prompt settings
            **model_kwargs: Additional model-specific parameters
            
        Raises:
            LLMServiceError: If service initialization fails
        """
        # Initialize logging with proper context
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            "rvandroid_tool.llm.service.action_service",
            {CONTEXT_COMPONENT: "LLMActionService"}
        )
        self.logger.info("Initializing LLM Action Service ...")

        # Initialize event bus for lifecycle events
        self.event_bus = EventBus.get_instance()
        
        # Subscribe to coverage events from CoverageTracker for real-time testing guidance
        self.subscribe_to_event_bus()

        # Initialize coverage tracking state
        self.current_coverage_metrics = {}
        self.recent_mop_errors = []  # Recent MOP errors for testing context

        # Initialize performance monitoring
        self.performance_monitor = PerformanceMonitor.get_instance()

        # Store parameters
        self.tool_config = tool_config
        self.static_data = static_data

        # Extract configurations
        self.llm_config = tool_config.llm_config
        self.prompt_config = tool_config.prompt_config
        
        # Extract context mode configuration
        self.context_mode = getattr(self.prompt_config, 'context_mode', ContextMode.STATELESS)
        self.context_window_size = getattr(self.prompt_config, 'context_window_size', ContextMode.WINDOW_SIZE_DEFAULT)
        self.context_compression = getattr(self.prompt_config, 'context_compression', ContextMode.COMPRESSION_DEFAULT)
        self.include_coverage_timeline = getattr(self.prompt_config, 'include_coverage_timeline', False)
        
        # Initialize iteration history for RICH context mode
        self.iteration_history = []  # List to store recent iterations for sliding window
        

        # Initialize LLM manager with backend configuration
        self.llm_manager = LLMManager(self.llm_config, **model_kwargs)

        # Initialize RVAndroid prompt framework with complete registration
        self.prompt_framework = RVAndroidPromptFramework.create(self.prompt_config)

        # Initialize specialized processors
        self.state_enricher = StateEnricher(static_data=static_data, config=self.prompt_config)
        self.response_processor = ResponseProcessor(config=self.llm_config)
        self.action_generator = ActionGenerator(config=self.llm_config, static_data=static_data)

        # Initialize coordination components
        self.transition_manager = TransitionManager(static_data)
        self.memory_manager = MemoryManager(static_data)

        # Log successful initialization
        self.logger.info(
            f"LLM Action Service initialized - "
            f"Backend: {self.llm_config.llm_type}:{self.llm_config.model}, "
            f"Strategy: {self.prompt_config.strategy_type}, "
            f"Parser: {self.prompt_config.parser_type}, "
            f"Visitor: {self.prompt_config.visitor_type}, "
            f"Context Mode: {self.context_mode} (window_size={self.context_window_size})"
        )

    def subscribe_to_event_bus(self):
        from rv_android_core.event.models import EventType
        self.event_bus.subscribe(
            EventType.COVERAGE_UPDATED,
            self._on_coverage_updated,
            filter_fn=lambda event: hasattr(event, 'source') and event.source == "CoverageTracker"
        )
        self.event_bus.subscribe(
            EventType.MOP_ERROR_DETECTED,
            self._on_mop_error_detected,
            filter_fn=lambda event: hasattr(event, 'source') and event.source == "CoverageTracker"
        )

    @ErrorHandler.handle_errors(
        component="LLMActionService",
        operation="process_state"
    )
    def process_state(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process application state and generate testing actions.
        
        This method orchestrates the entire action generation pipeline using
        unified configuration and specialized components.
        
        ### Processing Pipeline:
        1. Enrich state with additional information
        2. Generate context-aware prompt using RVAndroidPromptFramework
        3. Process LLM response into structured actions
        4. Update memory with interaction history
        5. Return generated actions for execution
        
        Args:
            state: Current application state to process
            
        Returns:
            List of generated actions for execution
            
        Raises:
            LLMServiceError: If state processing fails
        """
        with self.performance_monitor.measure_time("process_state"):
            try:
                # Pre-process state with complete enrichment pipeline
                self._pre_process_state(state)

                # Create prompt context
                prompt_context = self._create_prompt_context(state)

                # Generate prompt messages using unified framework
                messages = self.prompt_framework.generate_prompt(state, prompt_context)


                print(f"****************** Messages: {len(messages)}")
                for msg in messages:
                    print(f"\n *** Message: {msg.role}")
                    for content in msg.content:
                        from rv_llm.llm.data_structures import LLMImageContent, LLMTextContent
                        if isinstance(content, LLMTextContent):
                            print(f"   - Text Content:\n{content.text}")
                        elif isinstance(content, LLMImageContent):
                            print(f"   - Image Content: {content.url}")
                        else:
                            print(f"   - Content: {content}")


                # Process LLM interaction
                llm_response = self.llm_manager.generate(messages)

                # Check if response is valid
                if not llm_response:
                    self.logger.error("No response from LLM")
                    return []

                # Extract response content
                response_text = llm_response.content if hasattr(llm_response, 'content') else str(llm_response)

                # Process response into action descriptions
                actions, errors = self.response_processor.process_response(response_text, state)

                # Report any errors
                for error in errors:
                    self.logger.warning(f"Response parsing issue: {error}")

                # Generate executable actions
                generated_actions = self.action_generator.create_actions(actions, state)

                # Update memory with interaction history
                self.memory_manager.record_actions(state, generated_actions)

                # Log processing results
                self.logger.info(
                    f"Processed state - Generated {len(generated_actions)} actions "
                    f"using strategy: {self.prompt_config.strategy_type}"
                )

                # Record iteration for RICH context mode
                if self.context_mode == ContextMode.RICH:
                    self._record_iteration(state, generated_actions, response_text)

                # Record LLM event
                # self.event_bus.publish_llm_event(llm_response, generated_actions)

                return [action.to_droidbot_format() for action in generated_actions]

            except Exception as e:
                self.logger.error(f"State processing failed: {e}")
                raise LLMServiceError(f"State processing failed: {e}")

    @ErrorHandler.handle_errors(
        component="LLMActionService",
        operation="get_configuration_info"
    )
    def get_configuration_info(self) -> Dict[str, Any]:
        """
        Get current service configuration information.
        
        Returns:
            Dictionary containing configuration details
        """
        return {
            "llm_backend": f"{self.llm_config.llm_type}:{self.llm_config.model}",
            "prompt_strategy": self.prompt_config.strategy_type,
            "parser_type": self.prompt_config.parser_type,
            "visitor_type": self.prompt_config.visitor_type,
            "server_port": self.tool_config.server_port,
            "debug_mode": self.tool_config.debug_mode
        }

    def _pre_process_state(self, state: Dict[str, Any]) -> bool:
        """
        Pre-process the state using context mode routing.
        
        This method routes state pre-processing based on the configured context mode:
        - STATELESS: Uses standard enrichment with MemoryManager and TransitionManager  
        - RICH: Uses sliding window context with raw iteration history
        
        Args:
            state: Current application state
            
        Returns:
            bool: True if a transition (to other screen) was detected, False otherwise
        """
        self.logger.info(f"Pre-processing state: {state.get(StateEntry.ACTIVITY, 'unknown')} (mode: {self.context_mode})")

        # Initialize state with basic information
        self._initialize_state(state)

        # Route based on context mode
        if self.context_mode == ContextMode.RICH:
            return self._pre_process_state_rich(state)
        else:
            return self._pre_process_state_stateless(state)

    def _pre_process_state_stateless(self, state: Dict[str, Any]) -> bool:
        """
        Pre-process state using STATELESS context mode.
        
        Uses the existing enrichment pipeline with MemoryManager, TransitionManager,
        and other specialized components for context-aware processing.
        
        Args:
            state: Current application state
            
        Returns:
            bool: True if a transition was detected, False otherwise
        """
        # Enrich state with additional information
        self.state_enricher.enrich_state(state)

        # Update transitions with current state information
        transition_detected = self.transition_manager.update(state)

        # Update memory with current state information
        self.memory_manager.update(state)

        # Enrich state with historical information
        self.memory_manager.enrich_state_with_history(state)

        # Add transition guidance to state
        transition_guidance = self.transition_manager.get_transition_guidance(state)
        state[StateEntry.TRANSITION_GUIDANCE] = transition_guidance
        
        # Add real-time coverage metrics to state for AI decision-making
        if self.current_coverage_metrics:
            state[StateEntry.COVERAGE_METRICS] = self.current_coverage_metrics
            
            # Add individual metrics for template convenience
            metrics = self.current_coverage_metrics
            state[StateEntry.METHOD_COVERAGE] = metrics.get("method_coverage", 0.0)
            state[StateEntry.ACTIVITY_COVERAGE] = metrics.get("activity_coverage", 0.0)
            state[StateEntry.MOP_COVERAGE_CURRENT] = metrics.get("called_methods", 0)
            state[StateEntry.MOP_COVERAGE_TOTAL] = metrics.get("mop_method_coverage", 0.0)
            state[StateEntry.MOP_ERRORS_COUNT] = metrics.get("unique_errors", 0)
        
        # Add recent MOP errors for testing context
        if self.recent_mop_errors:
            state[StateEntry.MOP_RECENT_ERRORS] = self.recent_mop_errors[-3:]  # Last 3 errors for context

        return transition_detected

    def _pre_process_state_rich(self, state: Dict[str, Any]) -> bool:
        """
        Pre-process state using RICH context mode.
        
        Uses sliding window approach with raw iteration history, bypassing the
        traditional enrichment services (MemoryManager, TransitionManager) and 
        instead providing direct context through recent iterations.
        
        Args:
            state: Current application state
            
        Returns:
            bool: Always False (no transition detection in RICH mode)
        """
        # Only basic state enrichment (screen parsing, action decoding)
        self.state_enricher.enrich_state(state)
        
        # Add real-time coverage metrics to state for AI decision-making
        if self.current_coverage_metrics:
            state[StateEntry.COVERAGE_METRICS] = self.current_coverage_metrics
            
            # Add individual metrics for template convenience
            metrics = self.current_coverage_metrics
            state[StateEntry.METHOD_COVERAGE] = metrics.get("method_coverage", 0.0)
            state[StateEntry.ACTIVITY_COVERAGE] = metrics.get("activity_coverage", 0.0)
            state[StateEntry.CLASS_COVERAGE] = metrics.get("class_coverage", 0.0)
            state[StateEntry.MOP_COVERAGE_CURRENT] = metrics.get("called_methods", 0)
            state[StateEntry.MOP_COVERAGE_TOTAL] = metrics.get("mop_method_coverage", 0.0)
            state[StateEntry.MOP_ERRORS_COUNT] = metrics.get("unique_errors", 0)
        
        # Add recent MOP errors for testing context
        if self.recent_mop_errors:
            state[StateEntry.MOP_RECENT_ERRORS] = self.recent_mop_errors[-3:]  # Last 3 errors for context

        # Prepare sliding window context
        sliding_window_context = self._prepare_sliding_window(state)
        state[StateEntry.RECENT_ITERATIONS] = sliding_window_context
        
        self.logger.debug(f"RICH context prepared with {len(sliding_window_context)} iterations")
        
        # No transition detection in RICH mode (handled by sliding window)
        return False

    def _initialize_state(self, state: Dict[str, Any]):
        """Initialize state with basic information.

        Args:
            state: Current application state
        """
        app_package = state.get(StateEntry.PACKAGE_NAME, "unknown")
        app_activity = state.get(StateEntry.ACTIVITY, "unknown").replace("/", "")
        state[StateEntry.PACKAGE_NAME] = app_package
        state[StateEntry.ACTIVITY] = app_activity
        # Add static data if available (may be None in test scenarios)
        if hasattr(self, 'static_data') and self.static_data:
            state[StateEntry.STATIC_DATA] = self.static_data
        state[StateEntry.TOOL_CONFIG] = self.tool_config

    def _create_prompt_context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create context dictionary for prompt generation.

        Args:
            state: Current application state.

        Returns:
            Context dictionary with relevant information.
        """
        return {
            ContextEntry.APP_PACKAGE: state.get(StateEntry.PACKAGE_NAME, ""),
            ContextEntry.APP_ACTIVITY: state.get(StateEntry.ACTIVITY, ""),
            ContextEntry.ADDITIONAL_GUIDELINES: state.get(ContextEntry.ADDITIONAL_GUIDELINES, ""),
            ContextEntry.TESTING_HISTORY: state.get("testing_history", "")
        }

    @ErrorHandler.handle_errors(
        component="LLMActionService",
        operation="cleanup"
    )
    def cleanup(self):
        """Clean up service resources."""
        try:
            # Clean up specialized components
            if hasattr(self, 'llm_manager'):
                self.llm_manager.cleanup()

            if hasattr(self, 'memory_manager'):
                self.memory_manager.cleanup()

            self.logger.info("LLMActionService cleanup completed")

        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            raise LLMServiceError(f"Service cleanup failed: {e}")

    def _on_coverage_updated(self, event) -> None:
        """
        Handle coverage updates from CoverageTracker.
        
        Processes coverage metrics updates to provide testing context for
        action generation decisions.
        
        Args:
            event: Coverage update event with metrics data
        """
        try:
            self.current_coverage_metrics = event.data.coverage_metrics
            self.logger.debug(f"Coverage updated: {self.current_coverage_metrics}")
        except Exception as e:
            self.logger.warning(f"Error processing coverage update: {e}")

    def _on_mop_error_detected(self, event) -> None:
        """
        Handle MOP error detection events from CoverageTracker.
        
        Processes MOP violation detection events to maintain testing context.
        Stores recent violations to inform subsequent testing decisions.
        
        Args:
            event: MOP error detection event with violation details
        """
        try:
            error_data = event.data.error_log
            
            # Add timestamp for context relevance
            import datetime
            error_context = {
                **error_data,
                "detected_at": datetime.datetime.now().isoformat()
            }
            
            # Add to recent errors list (keep last 5 for context)
            self.recent_mop_errors.append(error_context)
            if len(self.recent_mop_errors) > 5:
                self.recent_mop_errors.pop(0)
            
            # Log MOP violation for analysis
            self.logger.info(
                f"MOP VIOLATION DETECTED: {error_data.get('spec', 'unknown')} "
                f"in {error_data.get('class_full_name', 'unknown')}.{error_data.get('method', 'unknown')} "
                f"- {error_data.get('message', 'no message')}"
            )
            
        except Exception as e:
            self.logger.error(f"Error processing MOP error detection: {e}", exc_info=True)

    def _prepare_sliding_window(self, current_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Prepare sliding window context from iteration history.
        
        Creates a sliding window of recent iterations with compression for older entries.
        The window provides direct context of recent interactions without processing
        through memory managers.
        
        Args:
            current_state: Current application state
            
        Returns:
            List of iteration contexts in reverse chronological order (most recent first)
        """
        if not self.iteration_history:
            return []
        
        # Get recent iterations within window size
        recent_count = min(len(self.iteration_history), self.context_window_size)
        recent_iterations = self.iteration_history[-recent_count:]
        
        # Apply compression if enabled and we have older iterations
        if self.context_compression and len(recent_iterations) > 3:
            compressed_window = []
            
            # Always include the most recent 2 iterations uncompressed
            for iteration in recent_iterations[-2:]:
                compressed_window.append(iteration)
            
            # Compress older iterations (keep every 2nd iteration)
            older_iterations = recent_iterations[:-2]
            for i, iteration in enumerate(older_iterations):
                if i % 2 == 0:  # Keep every 2nd iteration
                    compressed_iteration = self._compress_iteration(iteration)
                    compressed_window.insert(0, compressed_iteration)
            
            return compressed_window
        
        return list(reversed(recent_iterations))  # Most recent first

    def _compress_iteration(self, iteration: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compress an iteration by reducing detail while preserving key information.
        
        Args:
            iteration: Full iteration data
            
        Returns:
            Compressed iteration with essential information
        """
        compressed = {
            "iteration_number": iteration.get("iteration_number", 0),
            "screen_description_summary": self._summarize_screen_description(
                iteration.get("screen_description", "")
            ),
            "actions_executed": [
                {
                    "action_type": action.get("action_type", "unknown"),
                    "target": action.get("target", "unknown")
                }
                for action in iteration.get("actions_executed", [])[:2]  # Only first 2 actions
            ],
            "coverage_progress": {
                "method_coverage": iteration.get("coverage_before", {}).get("method_coverage", 0.0),
                "activity_coverage": iteration.get("coverage_before", {}).get("activity_coverage", 0.0)
            }
        }
        
        return compressed

    def _summarize_screen_description(self, full_description: str) -> str:
        """
        Create a summary of screen description for compressed iterations.
        
        Args:
            full_description: Full screen description text
            
        Returns:
            Summarized description (first 200 characters + activity info)
        """
        if not full_description or len(full_description) <= 200:
            return full_description
        
        # Extract activity information if present
        activity_info = ""
        if "Activity:" in full_description:
            activity_start = full_description.find("Activity:")
            activity_end = full_description.find("\n", activity_start)
            if activity_end != -1:
                activity_info = full_description[activity_start:activity_end] + "\n"
        
        # Take first 200 characters and add activity info
        summary = full_description[:200] + "..."
        if activity_info:
            summary = activity_info + summary
            
        return summary

    def _record_iteration(self, state: Dict[str, Any], actions: List, llm_response: str):
        """
        Record iteration data for RICH context mode sliding window.
        
        Stores the current interaction for use in future context windows,
        including screen description, generated actions, and coverage data.
        
        Args:
            state: Current application state
            actions: Generated actions from this iteration
            llm_response: Raw LLM response text
        """
        try:
            # Create iteration record
            iteration_data = {
                "iteration_number": len(self.iteration_history) + 1,
                "screen_description": state.get(StateEntry.SCREEN_DESCRIPTION, ""),
                "actions_executed": [
                    {
                        "action_type": getattr(action, 'action_type', 'unknown'),
                        "target": getattr(action, 'target', 'unknown'),
                        "coordinates": getattr(action, 'coordinates', None),
                        "text": getattr(action, 'text', None),
                        "parameters": getattr(action, 'parameters', {})
                    }
                    for action in actions
                ],
                "coverage_before": {
                    "method_coverage": state.get(StateEntry.METHOD_COVERAGE, 0.0),
                    "activity_coverage": state.get(StateEntry.ACTIVITY_COVERAGE, 0.0),
                    "class_coverage": state.get(StateEntry.CLASS_COVERAGE, 0.0),
                    "mop_method_coverage": state.get(StateEntry.MOP_COVERAGE_TOTAL, 0.0)
                },
                "llm_response": llm_response[:500] + "..." if len(llm_response) > 500 else llm_response,
                "timestamp": self._get_current_timestamp()
            }
            
            # Add to iteration history
            self.iteration_history.append(iteration_data)
            
            # Maintain window size limit (keep extra buffer for compression algorithm)
            max_history = self.context_window_size + 5  # Buffer for compression flexibility
            if len(self.iteration_history) > max_history:
                self.iteration_history = self.iteration_history[-max_history:]
            
            self.logger.debug(f"Recorded iteration {iteration_data['iteration_number']} for RICH context")
            
        except Exception as e:
            self.logger.warning(f"Failed to record iteration for RICH context: {e}")

    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        import datetime
        return datetime.datetime.now().isoformat()
