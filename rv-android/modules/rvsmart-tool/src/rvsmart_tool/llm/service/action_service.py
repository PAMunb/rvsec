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
- Receives unified RvSmartToolConfig containing all necessary configuration
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
from rv_android_core.constants import UI_COVERAGE_CONSTANTS
from rvsmart_tool.constants import (
    PARSING_ERROR_COUNTER,
    ACTION_GENERATION_COUNTER,
    METRICS_COLLECTION_ENABLED
)
from rvsmart_tool.llm.prompt.rvsmart_framework import RVAndroidPromptFramework
from rvsmart_tool.config.tool_config import RvSmartToolConfig
from rvsmart_tool.llm.service.action_generator import ActionGenerator
from rvsmart_tool.llm.service.llm_manager import LLMManager
from rvsmart_tool.llm.service.memory_manager import MemoryManager
from rvsmart_tool.llm.service.response_processor import ResponseProcessor
from rvsmart_tool.llm.service.state_enricher import StateEnricher
from rvsmart_tool.llm.service.ui_coverage_integration import UICoverageIntegration
from rvsmart_tool.llm.service.transition_manager import TransitionManager


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
            tool_config: RvSmartToolConfig
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
            "rvsmart_tool.llm.service.action_service",
            {CONTEXT_COMPONENT: "LLMActionService"}
        )
        self.logger.info("Initializing LLM Action Service ...")

        # Initialize event bus for lifecycle events
        self.event_bus = EventBus.get_instance()
        
        # Subscribe to coverage events from CoverageTracker for real-time testing guidance
        self.subscribe_to_event_bus()

        # Initialize system coverage tracking state (from rv-coverage events)
        self.current_coverage_metrics = {}
        self.recent_mop_errors = []  # Recent MOP errors for testing context
        
        # Initialize UI coverage tracker integration (distinct from system coverage)
        from rvsmart_tool.core.memory.ui_coverage_tracker import UICoverageTracker
        self.ui_coverage_tracker = UICoverageTracker()
        self.ui_coverage_integration = UICoverageIntegration(self.ui_coverage_tracker)

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
        self.llm_manager = LLMManager(self.llm_config)

        # Initialize RVAndroid prompt framework with complete registration
        self.prompt_framework = RVAndroidPromptFramework.create(self.prompt_config)

        # Initialize specialized processors
        # COORDINATE_ENH_FIX: Pass tool_config to StateEnricher so it can access llm_config.vision
        try:
            self.logger.warning("🔧 DEBUG_COORD_ENH: Initializing StateEnricher...")
            self.state_enricher = StateEnricher(static_data=static_data, config=tool_config)
            self.logger.warning("✅ DEBUG_COORD_ENH: StateEnricher initialized successfully")
        except Exception as se_error:
            self.logger.error(f"❌ StateEnricher initialization failed: {se_error}")
            raise

        try:
            self.logger.warning("🔧 Initializing ResponseProcessor...")
            self.response_processor = ResponseProcessor(config=self.llm_config)
            self.logger.warning("✅ ResponseProcessor initialized successfully")
        except Exception as rp_error:
            self.logger.error(f"❌ ResponseProcessor initialization failed: {rp_error}")
            raise

        try:
            self.logger.warning("🔧 Initializing ActionGenerator...")
            self.action_generator = ActionGenerator(config=self.llm_config, static_data=static_data)
            self.logger.warning("✅ ActionGenerator initialized successfully")
        except Exception as ag_error:
            self.logger.error(f"❌ ActionGenerator initialization failed: {ag_error}")
            raise

        # Initialize coordination components
        try:
            self.logger.warning("🔧 Initializing TransitionManager...")
            self.transition_manager = TransitionManager(static_data)
            self.logger.warning("✅ TransitionManager initialized successfully")
        except Exception as tm_error:
            self.logger.error(f"❌ TransitionManager initialization failed: {tm_error}")
            raise

        try:
            self.logger.warning("🔧 Initializing MemoryManager...")
            self.memory_manager = MemoryManager(static_data)
            self.logger.warning("✅ MemoryManager initialized successfully")
        except Exception as mm_error:
            self.logger.error(f"❌ MemoryManager initialization failed: {mm_error}")
            raise

        # Log successful initialization
        self.logger.warning("🚀 ACTIONSERVICE INITIALIZATION COMPLETED")
        self.logger.info(f"   Backend: {self.llm_config.llm_type}:{self.llm_config.model}")
        self.logger.info(f"   Strategy: {self.prompt_config.strategy_type}")
        self.logger.info(f"   Parser: {self.prompt_config.parser_type}")
        self.logger.info(f"   Visitor: {self.prompt_config.visitor_type}")
        self.logger.info(f"   Context Mode: {self.context_mode} (window_size={self.context_window_size})")
        
        # Debug vision capabilities
        if hasattr(self.llm_config, 'vision'):
            self.logger.info(f"   Vision enabled: {self.llm_config.vision}")
            self.logger.warning(f"DEBUG_COORD_ENH: ActionService initialized with vision={self.llm_config.vision}")
        else:
            self.logger.warning("   Vision capability not available in llm_config")
            
        # Debug StateEnricher configuration
        self.logger.info(f"   StateEnricher type: {type(self.state_enricher).__name__}")
        self.logger.info(f"   StateEnricher config: {type(self.state_enricher.config).__name__ if self.state_enricher.config else 'None'}")

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
    def process_state(self, state: Dict[str, Any]):
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
            List of GeneratedAction objects for UIAutomator execution
            
        Raises:
            LLMServiceError: If state processing fails
        """
        self.logger.warning("🎯 ACTIONSERVICE: Starting state processing pipeline")
        self.logger.info(f"   State activity: {state.get('activity', 'Unknown')}")
        self.logger.info(f"   State keys: {list(state.keys()) if state else 'None'}")
        
        with self.performance_monitor.measure_time("process_state"):
            try:
                # DETAILED_LOG: Interaction context analysis
                self.logger.warning("📋 PHASE 1: Logging interaction context")
                self._log_interaction_context(state)
                
                # Pre-process state with context mode routing (STATELESS vs RICH)
                # STATELESS: Uses MemoryManager + TransitionManager for enrichment
                # RICH: Uses sliding window context with raw iteration history 
                self.logger.warning("🔄 PHASE 2: Pre-processing state")
                self._pre_process_state(state)

                # DEBUG_COORD_ENH: Create processing context for coordinate enhancement
                self.logger.warning("🧠 PHASE 3: Creating processing context for coordinate enhancement")
                self.logger.warning("DEBUG_COORD_ENH: Calling state_enricher.create_processing_context()")
                processing_context = self.state_enricher.create_processing_context()
                self.logger.warning(f"DEBUG_COORD_ENH: Processing context created - {processing_context}")
                self.logger.warning(f"DEBUG_COORD_ENH: Processing context type: {type(processing_context)}")
                self.logger.warning(f"DEBUG_COORD_ENH: Processing context keys: {list(processing_context.keys()) if processing_context else 'Empty'}")

                # Create prompt context dictionary for RVAndroidPromptFramework
                self.logger.info("📝 PHASE 4: Creating prompt context")
                prompt_context = self._create_prompt_context(state)
                self.logger.info(f"   Prompt context keys before merge: {list(prompt_context.keys())}")
                
                # DEBUG_COORD_ENH: Merge processing context into prompt context
                self.logger.warning("DEBUG_COORD_ENH: Merging processing context into prompt context")
                if processing_context:
                    original_keys = set(prompt_context.keys())
                    prompt_context.update(processing_context)
                    new_keys = set(prompt_context.keys()) - original_keys
                    self.logger.warning(f"DEBUG_COORD_ENH: Added new keys to prompt context: {new_keys}")
                    self.logger.warning(f"DEBUG_COORD_ENH: Final prompt context keys: {list(prompt_context.keys())}")
                    if 'vision_enabled' in prompt_context:
                        self.logger.warning(f"DEBUG_COORD_ENH: vision_enabled = {prompt_context['vision_enabled']} successfully added to prompt context")
                else:
                    self.logger.warning("⚠️ DEBUG_COORD_ENH: No processing context to merge - coordinate enhancement may not work")

                # Generate prompt messages using strategy-specific framework (BATCH_ACTION, STANDARD, MOP_VISION)
                # The framework selects fragments based on strategy configuration and builds complete prompt
                self.logger.info("🎨 PHASE 5: Generating prompt messages")
                self.logger.info(f"   Framework type: {type(self.prompt_framework).__name__}")
                self.logger.info(f"   Strategy: {self.prompt_config.strategy_type}")
                self.logger.warning(f"DEBUG_COORD_ENH: About to call prompt_framework.generate_prompt() with vision_enabled={prompt_context.get('vision_enabled', 'Not found')}")
                
                messages = self.prompt_framework.generate_prompt(state, prompt_context)
                
                self.logger.info(f"✅ Generated {len(messages) if messages else 0} prompt messages")
                self.logger.warning("DEBUG_COORD_ENH: Prompt generation completed - messages contain coordinate enhancement context")
                for message in messages:
                    print(f"\n=========== MESSAGE: {message.role}")
                    for content in message.content:
                        print(f"\n  - {content}")
                print("============================")


                # Process LLM interaction with performance tracking
                self.logger.warning("🤖 PHASE 6: Processing LLM interaction")
                self.logger.info(f"   LLM type: {self.llm_config.llm_type}:{self.llm_config.model}")
                self.logger.info(f"   Vision enabled: {getattr(self.llm_config, 'vision', 'Not available')}")
                
                with self.performance_monitor.measure_time(
                    "llm_generation", 
                    {"strategy": self.prompt_config.strategy_type}
                ):
                    llm_response = self.llm_manager.generate(messages)
                    
                self.logger.info(f"✅ LLM response received - Type: {type(llm_response).__name__}")

                # Check if response is valid
                if not llm_response:
                    self.logger.error("No response from LLM")
                    return []

                # Extract response content
                response_text = llm_response.content if hasattr(llm_response, 'content') else str(llm_response)

                # Parse LLM response into structured action descriptions using strategy-specific parser
                # Different strategies produce different response formats (JSON, XML, structured text)
                actions, errors = self.response_processor.process_response(response_text, state)

                # Report parsing errors for prompt optimization analysis
                if METRICS_COLLECTION_ENABLED and errors:
                    self.performance_monitor.record_metric(
                        name=PARSING_ERROR_COUNTER,
                        value=len(errors),
                        unit="errors",
                        context={"strategy": self.prompt_config.strategy_type}
                    )
                
                for error in errors:
                    self.logger.warning(f"Response parsing issue: {error}")

                # Convert action descriptions to executable DroidBot actions with UI element mapping
                # Maps action_id from parsed actions to actual UI elements from visitor patterns
                self.logger.warning("⚙️ PHASE 8: Converting to executable actions")
                self.logger.info(f"   ActionGenerator type: {type(self.action_generator).__name__}")
                self.logger.info(f"   Input actions count: {len(actions) if actions else 0}")
                
                generated_actions = self.action_generator.create_actions(actions, state)
                
                self.logger.info(f"✅ Generated {len(generated_actions) if generated_actions else 0} executable actions")
                for i, action in enumerate(generated_actions or []):
                    self.logger.info(f"   Action {i+1}: {getattr(action, 'text', str(action))}")

                # Update memory with interaction history
                self.memory_manager.record_actions(state, generated_actions)

                # Record UI interactions in UICoverageTracker
                # Record UI interactions using standardized parameter order
                self._record_ui_interactions(state, generated_actions)
                
                # Log structured metrics for strategy comparison with optimization tracking and error analysis
                self._log_action_generation_metrics(generated_actions, state, llm_response, actions, errors)

                # Record iteration for RICH context mode
                if self.context_mode == ContextMode.RICH:
                    self._record_iteration(state, generated_actions, response_text)

                # RVSmart adaptation: Return GeneratedAction objects directly for UIAutomator execution
                self.logger.info(f"🎯 ACTIONSERVICE: Processing pipeline completed successfully")
                self.logger.info(f"   Final result: {len(generated_actions) if generated_actions else 0} actions ready for execution")
                self.logger.warning("DEBUG_COORD_ENH: Actions generated with coordinate enhancement pipeline - ready for UIAutomator")
                
                return generated_actions

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
            # "server_port": getattr(self.tool_config, 'server_port', 8080),  # Optional attribute
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
        self.logger.info(f"🔄 ACTIONSERVICE: Pre-processing state")
        self.logger.info(f"   Activity: {state.get(StateEntry.ACTIVITY, 'unknown')}")
        self.logger.info(f"   Context mode: {self.context_mode}")
        self.logger.info(f"   StateEnricher available: {'Yes' if self.state_enricher else 'No'}")

        # Initialize state with basic information
        self.logger.warning("📊 Initializing state with basic information")
        self._initialize_state(state)

        # Route based on context mode
        if self.context_mode == ContextMode.RICH:
            self.logger.warning("🔀 Routing to RICH context mode processing")
            return self._pre_process_state_rich(state)
        else:
            self.logger.warning("🔀 Routing to STATELESS context mode processing")
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
        self.logger.warning("📈 STATELESS MODE: Starting state enrichment")
        
        # Enrich state with additional information
        self.logger.warning("🔍 Calling state_enricher.enrich_state()")
        self.state_enricher.enrich_state(state)
        self.logger.warning("✅ State enrichment completed")

        # Update transitions and memory (STATELESS mode specific)
        transition_detected = self.transition_manager.update(state)
        self.memory_manager.update(state)
        self.memory_manager.enrich_state_with_history(state)

        # Add transition guidance to state
        transition_guidance = self.transition_manager.get_transition_guidance(state)
        state[StateEntry.TRANSITION_GUIDANCE] = transition_guidance
        
        # Add coverage metrics using shared method
        self._add_coverage_metrics_to_state(state)

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
        
        # Add coverage metrics using shared method
        self._add_coverage_metrics_to_state(state)

        # Apply UI coverage annotations to screen elements if UI tracker available
        self.ui_coverage_integration.apply_ui_coverage_annotations(state)

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
                    "target": action.get("target", action.get("text", "unknown"))  # Fallback to text if target not available
                }
                for action in iteration.get("actions_executed", [])[:2]  # Only first 2 actions
            ],
            "coverage_progress": {
                "method_coverage": iteration.get("coverage_before", {}).get("method_coverage", 0.0),
                "activity_coverage": iteration.get("coverage_before", {}).get("activity_coverage", 0.0),
                "mop_method_coverage": iteration.get("coverage_before", {}).get("mop_method_coverage", 0.0),
                "mop_errors_unique": iteration.get("coverage_before", {}).get("unique_errors", 0)
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

    @ErrorHandler.handle_errors(component="LLMActionService", phase="ui_interaction_recording")
    def _record_ui_interactions(self, state: Dict[str, Any], generated_actions: List) -> None:
        """
        Record UI interactions in UICoverageTracker for systematic testing.
        
        This method processes generated actions to record UI element interactions
        for coverage analysis and systematic testing guidance.
        
        Args:
            generated_actions: List of generated actions from LLM
            state: Current application state for context
        """
        if not self.ui_coverage_tracker:
            return
            
        try:
            for action in generated_actions:
                # Create action data for UI coverage integration
                action_data = {
                    'action_type': getattr(action, 'action_type', 'unknown'),
                    'item': action  # Full action object
                }
                
                # Record interaction using UI coverage integration
                self.ui_coverage_integration.record_action_interaction(action_data, state)
                
        except Exception as e:
            self.logger.error(f"Error recording UI interactions: {e}")

    @ErrorHandler.handle_errors(component="LLMActionService", phase="metrics_logging")
    def _log_action_generation_metrics(self, generated_actions: List, state: Dict[str, Any], llm_response=None, 
                                     parsed_actions: List = None, parsing_errors: List = None) -> None:
        """
        Log structured metrics for strategy performance comparison and prompt optimization tracking.
        
        This method provides comprehensive metrics logging to support strategy comparison
        and performance analysis across different configurations. It integrates with the
        TaskExecutor's PerformanceMonitor system to provide unified metrics collection
        for prompt optimization analysis.
        
        ### Architectural Integration:
        The method leverages the existing TaskExecutor context hierarchy to automatically
        inherit base context (task_id, apk_name, tool_name, repetition, timeout) while
        adding prompt optimization specific metrics for before/after comparison analysis.
        
        ### Error Analysis Integration:
        Captures critical error metrics for prompt tuning analysis:
        - Parsing errors: JSON malformed, structure invalid
        - Action generation errors: Invalid action_id, unmappable actions  
        - Success rates: Parsed vs generated action ratios
        - Error patterns: Common failure modes for prompt improvement
        
        Args:
            generated_actions: List of generated actions from LLM
            state: Current application state for context
            llm_response: LLM response object containing token metrics (optional)
            parsed_actions: List of parsed action descriptions from response processor (optional)
            parsing_errors: List of parsing errors encountered (optional)
        """
        try:
            # Count monitored operations related actions for quality validation
            direct_mop_actions = sum(1 for action in generated_actions 
                                   if getattr(action, 'directly_reaches_mop', False))
            indirect_mop_actions = sum(1 for action in generated_actions 
                                     if getattr(action, 'reaches_mop', False) and 
                                        not getattr(action, 'directly_reaches_mop', False))
            
            # Calculate action type distribution for prompt tuning analysis
            action_types = {}
            for action in generated_actions:
                action_type = getattr(action, 'action_type', 'unknown')
                action_types[action_type] = action_types.get(action_type, 0) + 1
            
            # Extract UI elements metrics for optimization validation
            screen_description = state.get(StateEntry.STRUCTURED_SCREEN)
            ui_elements_total = len(screen_description.items) if screen_description and hasattr(screen_description, 'items') else 0
            ui_elements_actionable = len([item for item in screen_description.items 
                                        if item.actions]) if screen_description and hasattr(screen_description, 'items') else 0
            
            # Calculate error metrics for prompt tuning analysis
            parsing_error_count = len(parsing_errors) if parsing_errors else 0
            parsed_action_count = len(parsed_actions) if parsed_actions else 0
            generated_action_count = len(generated_actions)
            
            # Action generation success rate (parsed actions that became executable actions)
            action_generation_success_rate = (generated_action_count / max(parsed_action_count, 1)) if parsed_action_count > 0 else 1.0
            
            # Overall success rate (successful actions from LLM response)
            total_success_rate = action_generation_success_rate if parsing_error_count == 0 else (generated_action_count / max(parsed_action_count + parsing_error_count, 1))
            
            # Create prompt optimization context for metrics
            optimization_context = {
                "strategy": self.prompt_config.strategy_type,
                "visitor": self.prompt_config.visitor_type,
                "parser": self.prompt_config.parser_type,
                "activity": state.get(StateEntry.ACTIVITY, 'unknown'),
                "context_mode": self.context_mode,
                "optimization_phase": "after"  # Default to after optimization
            }
            
            # Record prompt optimization specific metrics in PerformanceMonitor
            # These metrics integrate with TaskExecutor context automatically
            if llm_response:
                # Input tokens - critical for optimization tracking
                input_tokens = getattr(llm_response, 'input_tokens', 0)
                if input_tokens > 0:
                    self.performance_monitor.record_metric(
                        name="prompt_optimization_input_tokens",
                        value=input_tokens,
                        unit="tokens",
                        context=optimization_context
                    )
                
                # Output tokens - for response size tracking
                output_tokens = getattr(llm_response, 'output_tokens', 0)
                if output_tokens > 0:
                    self.performance_monitor.record_metric(
                        name="prompt_optimization_output_tokens",
                        value=output_tokens,
                        unit="tokens",
                        context=optimization_context
                    )
                
                # Generation time efficiency - from LLM response timing
                generation_time = getattr(llm_response, 'generation_time', 0.0)
                if generation_time > 0:
                    self.performance_monitor.record_metric(
                        name="prompt_optimization_generation_time",
                        value=generation_time,
                        unit="seconds",
                        context=optimization_context
                    )
                    
                    # Tokens per second efficiency metric
                    if input_tokens > 0:
                        tokens_per_second = input_tokens / max(generation_time, 0.001)
                        self.performance_monitor.record_metric(
                            name="prompt_optimization_tokens_per_second",
                            value=tokens_per_second,
                            unit="tokens_per_second",
                            context=optimization_context
                        )
            
            # UI Coverage metrics for optimization validation
            self.performance_monitor.record_metric(
                name="ui_coverage_elements_total",
                value=ui_elements_total,
                unit="elements",
                context=optimization_context
            )
            
            self.performance_monitor.record_metric(
                name="ui_coverage_actionable_elements",
                value=ui_elements_actionable,
                unit="elements",
                context=optimization_context
            )
            
            # Monitored operations detection metrics for quality validation
            self.performance_monitor.record_metric(
                name="mop_detection_direct_actions",
                value=direct_mop_actions,
                unit="actions",
                context=optimization_context
            )
            
            self.performance_monitor.record_metric(
                name="mop_detection_indirect_actions",
                value=indirect_mop_actions,
                unit="actions",
                context=optimization_context
            )
            
            # Action distribution metrics for prompt tuning
            for action_type, count in action_types.items():
                self.performance_monitor.record_metric(
                    name=f"action_distribution_{action_type.lower()}",
                    value=count,
                    unit="actions",
                    context=optimization_context
                )
            
            # Critical error metrics for prompt tuning analysis
            self.performance_monitor.record_metric(
                name="prompt_parsing_errors",
                value=parsing_error_count,
                unit="errors",
                context=optimization_context
            )
            
            self.performance_monitor.record_metric(
                name="prompt_parsed_actions",
                value=parsed_action_count,
                unit="actions",
                context=optimization_context
            )
            
            self.performance_monitor.record_metric(
                name="prompt_action_generation_success_rate",
                value=action_generation_success_rate,
                unit="percentage",
                context=optimization_context
            )
            
            self.performance_monitor.record_metric(
                name="prompt_total_success_rate",
                value=total_success_rate,
                unit="percentage",
                context=optimization_context
            )
            
            # Action loss metric (parsed actions that failed to become executable)
            action_loss_count = parsed_action_count - generated_action_count
            if action_loss_count > 0:
                self.performance_monitor.record_metric(
                    name="prompt_action_generation_failures",
                    value=action_loss_count,
                    unit="actions",
                    context=optimization_context
                )
            
            # Get current coverage context for traditional logging
            coverage_metrics = self.current_coverage_metrics
            mop_violations_count = len(self.recent_mop_errors)
            
            # Log structured performance metrics (traditional format with error analysis)
            self.logger.info(
                "Action generation metrics",
                extra={
                    'metrics_type': 'action_generation',
                    'strategy_name': self.prompt_config.strategy_type,
                    'llm_backend': f"{self.llm_config.llm_type}:{self.llm_config.model}",
                    'total_actions': len(generated_actions),
                    'direct_mop_actions': direct_mop_actions,
                    'indirect_mop_actions': indirect_mop_actions,
                    'mop_action_ratio': (direct_mop_actions + indirect_mop_actions) / max(1, len(generated_actions)),
                    'action_types': action_types,
                    'activity': state.get(StateEntry.ACTIVITY, 'unknown'),
                    'current_method_coverage': coverage_metrics.get('method_coverage', 0.0) if coverage_metrics else 0.0,
                    'current_activity_coverage': coverage_metrics.get('activity_coverage', 0.0) if coverage_metrics else 0.0,
                    'mop_violations_found': mop_violations_count,
                    'context_mode': self.context_mode,
                    'parser_type': self.prompt_config.parser_type,
                    'visitor_type': self.prompt_config.visitor_type,
                    'ui_elements_total': ui_elements_total,
                    'ui_elements_actionable': ui_elements_actionable,
                    # Error analysis metrics for prompt tuning
                    'parsing_errors': parsing_error_count,
                    'parsed_actions': parsed_action_count,
                    'action_generation_success_rate': action_generation_success_rate,
                    'total_success_rate': total_success_rate,
                    'action_generation_failures': action_loss_count
                }
            )
            
            # Traditional format for backwards compatibility with error metrics
            error_summary = f" | Errors: {parsing_error_count} parsing" if parsing_error_count > 0 else ""
            if action_loss_count > 0:
                error_summary += f", {action_loss_count} generation failures"
                
            self.logger.info(
                f"Processed state - Generated {len(generated_actions)}/{parsed_action_count} actions "
                f"(MOP: {direct_mop_actions}+{indirect_mop_actions}) "
                f"| Success rate: {total_success_rate:.1%}"
                f"{error_summary} "
                f"| Strategy: {self.prompt_config.strategy_type}"
            )
            
        except Exception as e:
            self.logger.error(f"Error logging action generation metrics: {e}")

    @ErrorHandler.handle_errors(component="LLMActionService", phase="strategy_performance_logging")
    def log_strategy_performance(self, strategy_name: str, session_metrics: Dict[str, Any]) -> None:
        """
        Log strategy performance metrics for comparative analysis.
        
        This method provides comprehensive performance logging for strategy comparison,
        including efficiency metrics and violation discovery rates.
        
        Args:
            strategy_name: Name of the strategy being evaluated
            session_metrics: Dictionary containing session performance data
        """
        try:
            # Calculate derived metrics
            duration_hours = session_metrics.get('session_duration', 0) / 3600
            violations_per_hour = (
                session_metrics.get('mop_violations', 0) / duration_hours 
                if duration_hours > 0 else 0.0
            )
            
            coverage_improvement = (
                session_metrics.get('final_coverage', 0.0) - 
                session_metrics.get('initial_coverage', 0.0)
            )
            
            # Log comprehensive strategy performance
            self.logger.info(
                "Strategy performance summary",
                extra={
                    'metrics_type': 'strategy_performance',
                    'strategy_name': strategy_name,
                    'llm_backend': f"{self.llm_config.llm_type}:{self.llm_config.model}",
                    'session_duration_minutes': session_metrics.get('session_duration', 0) / 60,
                    'total_actions': session_metrics.get('total_actions', 0),
                    'mop_violations_found': session_metrics.get('mop_violations', 0),
                    'violations_per_hour': violations_per_hour,
                    'coverage_elements_tested': session_metrics.get('coverage_elements', 0),
                    'coverage_improvement': coverage_improvement,
                    'final_method_coverage': session_metrics.get('final_method_coverage', 0.0),
                    'final_activity_coverage': session_metrics.get('final_activity_coverage', 0.0),
                    'success_rate': session_metrics.get('success_rate', 0.0),
                    'parser_type': self.prompt_config.parser_type,
                    'visitor_type': self.prompt_config.visitor_type,
                    'context_mode': self.context_mode
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error logging strategy performance: {e}")

    def _log_interaction_context(self, state: Dict[str, Any]) -> None:
        """
        Log detailed interaction context for analysis and debugging.
        
        This method provides comprehensive logging of interaction context including
        iteration number, UI coverage tracking, memory state, and historical progression.
        """
        try:
            # Get current interaction number
            current_activity = state.get(StateEntry.ACTIVITY, "unknown")
            
            # Get iteration number from memory manager
            iteration_number = getattr(self.memory_manager, 'get_current_iteration', lambda: len(self.iteration_history) + 1)()
            if hasattr(self.memory_manager, 'memory_instances') and current_activity in self.memory_manager.memory_instances:
                memory_state = self.memory_manager.memory_instances[current_activity]
                visit_count = memory_state.visit_count
            else:
                visit_count = 1
                
            # Get UI coverage stats if available
            ui_coverage_stats = {}
            if self.ui_coverage_tracker:
                ui_coverage_stats = {
                    "total_interactions": sum(self.ui_coverage_tracker.tested_elements.values()),
                    "unique_elements": len(self.ui_coverage_tracker.tested_elements),
                    "screen_states": len(self.ui_coverage_tracker.screen_elements)
                }
            
            # Get current coverage metrics
            current_coverage = {
                "method_coverage": state.get(StateEntry.METHOD_COVERAGE, 0.0),
                "activity_coverage": state.get(StateEntry.ACTIVITY_COVERAGE, 0.0), 
                "mop_coverage": state.get(StateEntry.MOP_COVERAGE_TOTAL, 0.0)
            }
            
            # Get memory insights
            memory_insights = state.get(StateEntry.MEMORY_INSIGHTS, "No insights available")
            action_history = state.get(StateEntry.ACTION_HISTORY, "No history available")
            
            # Log comprehensive interaction context
            self.logger.info("DETAILED_LOG: ================== INTERACTION CONTEXT ==================")
            self.logger.info(f"DETAILED_LOG: Interaction #{iteration_number}")
            self.logger.info(f"DETAILED_LOG: Activity: {current_activity} (Visit #{visit_count})")
            self.logger.info(f"DETAILED_LOG: Strategy: {self.prompt_config.strategy_type}")
            self.logger.info(f"DETAILED_LOG: Context Mode: {self.context_mode}")
            self.logger.info(f"DETAILED_LOG: --- COVERAGE METRICS ---")
            self.logger.info(f"DETAILED_LOG: Method Coverage: {current_coverage['method_coverage']:.2f}%")
            self.logger.info(f"DETAILED_LOG: Activity Coverage: {current_coverage['activity_coverage']:.2f}%")
            self.logger.info(f"DETAILED_LOG: MOP Coverage: {current_coverage['mop_coverage']:.2f}%")
            self.logger.info(f"DETAILED_LOG: --- UI COVERAGE TRACKER ---")
            if ui_coverage_stats:
                self.logger.info(f"DETAILED_LOG: Total UI Interactions: {ui_coverage_stats['total_interactions']}")
                self.logger.info(f"DETAILED_LOG: Unique Elements: {ui_coverage_stats['unique_elements']}")
                self.logger.info(f"DETAILED_LOG: Screen States: {ui_coverage_stats['screen_states']}")
            else:
                self.logger.info("DETAILED_LOG: UI Coverage Tracker: Not available")
            self.logger.info(f"DETAILED_LOG: --- MEMORY STATE ---")
            self.logger.info(f"DETAILED_LOG: Memory Insights: {memory_insights[:200]}...")
            self.logger.info(f"DETAILED_LOG: Action History: {action_history[:200]}...")
            self.logger.info("DETAILED_LOG: ================== END INTERACTION CONTEXT ==================")
            
        except Exception as e:
            self.logger.error(f"Error logging interaction context: {e}")

    def _add_coverage_metrics_to_state(self, state: Dict[str, Any]) -> None:
        """
        Add coverage metrics to state using shared logic.
        
        This method consolidates the coverage metrics addition logic that was
        duplicated between STATELESS and RICH context modes.
        
        Args:
            state: Current application state to enrich with coverage metrics
        """
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
