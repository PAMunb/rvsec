"""
Strategic Guidance Service for RVDroid Testing

### Architectural Overview:
This module provides strategic guidance for RVDroid's testing process using LLM integration.
It orchestrates the complete guidance pipeline from state analysis to strategic recommendations,
using compact prompts optimized for guidance rather than action generation.

### Key Architectural Decisions:
- Uses rv-llm PromptFramework for template-based prompt generation
- Implements guidance-specific response processing and validation
- Provides structured guidance decisions for strategy adjustment
- Integrates with rv-android-core error handling and performance monitoring

### Role in the System:
- Provides strategic guidance for RVDroid testing components
- Processes application state into guidance-specific prompts
- Validates and structures LLM responses into actionable guidance
- Coordinates with RVDroid strategy and memory systems

### Design Patterns:
- Facade Pattern: Coordinates specialized guidance components
- Strategy Pattern: Uses different guidance strategies based on context
- Template Method: Standardized guidance generation workflow
"""

import json
import time
from typing import Dict, Any, Optional, List

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.error.exceptions import LLMServiceError, LLMResponseError
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.performance.performance_monitor import PerformanceMonitor
from rv_llm.config.llm_config import LLMConfig, PromptConfig
from rv_llm.llm.data_structures import LLMMessage, LLMTextContent
from rv_llm.llm.prompt.framework import PromptFramework

from rvdroid_tool.config.tool_config import RVDroidToolConfig
from rvdroid_tool.constants import (
    GUIDANCE_TYPE_STRATEGIC, GUIDANCE_TYPE_FLOW_CHANGE, GUIDANCE_TYPE_NO_GUIDANCE,
    PERFORMANCE_METRIC_PREFIX, TEMPLATES_DIR
)
from rvdroid_tool.llm.service.llm_manager import RVDroidLLMManager


class GuidanceDecision:
    """
    Structured representation of strategic guidance from LLM.
    
    ### Data Structure:
    Encapsulates guidance decisions with type safety and validation,
    providing clear interfaces for guidance application in RVDroid components.
    """
    
    def __init__(self, guidance_type: str, suggestion: str, reasoning: str):
        """
        Initialize guidance decision with validation.
        
        Args:
            guidance_type: Type of guidance (STRATEGIC_ADVICE, FLOW_CHANGE, NO_GUIDANCE)
            suggestion: Concrete suggestion or recommendation
            reasoning: Explanation for the guidance decision
        """
        self.guidance_type = guidance_type
        self.suggestion = suggestion
        self.reasoning = reasoning
        self.timestamp = time.time()
        
        # Validate guidance type
        valid_types = [GUIDANCE_TYPE_STRATEGIC, GUIDANCE_TYPE_FLOW_CHANGE, GUIDANCE_TYPE_NO_GUIDANCE]
        if guidance_type not in valid_types:
            raise ValueError(f"Invalid guidance_type: {guidance_type}. Must be one of {valid_types}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert guidance decision to dictionary representation."""
        return {
            "guidance_type": self.guidance_type,
            "suggestion": self.suggestion,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp
        }
        
    def is_actionable(self) -> bool:
        """Check if guidance requires action from RVDroid components."""
        return self.guidance_type in [GUIDANCE_TYPE_STRATEGIC, GUIDANCE_TYPE_FLOW_CHANGE]


class RVDroidGuidanceService:
    """
    Strategic guidance service for RVDroid testing operations.
    
    ### Architectural Overview:
    This service orchestrates the complete guidance pipeline, from state analysis
    to strategic recommendations. It uses the rv-llm framework for LLM integration
    while providing guidance-specific functionality tailored for RVDroid.
    
    ### Key Features:
    - Guidance-specific prompt generation using PromptFramework
    - Compact, strategic prompts optimized for guidance (not actions)
    - Structured response processing and validation
    - Performance monitoring for guidance effectiveness
    - Integration with RVDroid memory and strategy systems
    
    ### Integration Strategy:
    - Uses RVDroidLLMManager for LLM backend management
    - Leverages rv-llm PromptFramework for template-based prompts
    - Integrates with rv-android-core utilities for error handling and logging
    - Provides guidance decisions for RVDroid strategy adjustment
    """

    @ErrorHandler.handle_errors(
        component="RVDroidGuidanceService",
        operation="initialization"
    )
    def __init__(self, tool_config: RVDroidToolConfig):
        """
        Initialize strategic guidance service for RVDroid.
        
        ### Initialization Strategy:
        - Creates RVDroidLLMManager with guidance-specific configuration
        - Initializes PromptFramework with guidance templates
        - Sets up performance monitoring and logging infrastructure
        - Prepares guidance-specific response processing
        
        Args:
            tool_config: RVDroidToolConfig with LLM and prompt configuration
            
        Raises:
            ConfigurationError: If tool configuration is invalid
            LLMServiceError: If service initialization fails
        """
        # Validate configuration
        is_valid, error_msg = tool_config.validate()
        if not is_valid:
            raise LLMServiceError(f"Invalid tool configuration: {error_msg}")
            
        self.tool_config = tool_config
        self.llm_config = tool_config.llm_config
        self.prompt_config = tool_config.prompt_config
        
        # Initialize logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid_tool.llm.service.guidance_service",
            {CONTEXT_COMPONENT: "RVDroidGuidanceService"}
        )
        
        # Initialize performance monitoring
        self.performance_monitor = PerformanceMonitor.get_instance()
        
        # Initialize LLM manager if guidance is enabled
        self.llm_manager: Optional[RVDroidLLMManager] = None
        if tool_config.llm_enabled:
            self.llm_manager = RVDroidLLMManager(self.llm_config)
            
            # Initialize prompt framework for guidance
            self.prompt_framework = PromptFramework.create(self.prompt_config)
            
            self.logger.info("RVDroid guidance service initialized with LLM support")
        else:
            self.prompt_framework = None
            self.logger.info("RVDroid guidance service initialized without LLM support")

    @ErrorHandler.handle_errors(
        component="RVDroidGuidanceService",
        operation="strategic_guidance"
    )
    def get_strategic_guidance(
        self,
        current_state_description: str,
        test_objective: str,
        strategy_context: Dict[str, Any],
        history_summary: Optional[str] = None
    ) -> GuidanceDecision:
        """
        Generate strategic guidance based on current testing context.
        
        ### Guidance Generation Strategy:
        - Creates compact, guidance-specific prompts
        - Focuses on strategic advice rather than specific actions
        - Processes LLM responses into structured guidance decisions
        - Validates guidance type and content before returning
        
        Args:
            current_state_description: Description of current application state
            test_objective: Current testing objective or goal
            strategy_context: Context about current testing strategy and performance
            history_summary: Optional summary of recent testing history
            
        Returns:
            GuidanceDecision with strategic recommendation
            
        Raises:
            LLMServiceError: If guidance generation fails
            LLMResponseError: If LLM response is invalid
        """
        # Return no guidance if LLM is disabled
        if not self.tool_config.llm_enabled or not self.llm_manager:
            self.logger.debug("LLM guidance disabled, returning NO_GUIDANCE")
            return GuidanceDecision(
                GUIDANCE_TYPE_NO_GUIDANCE,
                "",
                "LLM guidance is disabled by configuration"
            )
        
        with self.performance_monitor.measure_time(f"{PERFORMANCE_METRIC_PREFIX}_guidance_total"):
            try:
                # Create guidance context
                guidance_context = self._create_guidance_context(
                    current_state_description,
                    test_objective,
                    strategy_context,
                    history_summary
                )
                
                # Generate guidance prompt
                messages = self._generate_guidance_prompt(guidance_context)
                
                # Get LLM response
                llm_response = self.llm_manager.generate_guidance(messages)
                
                # Process response into guidance decision
                guidance_decision = self._process_guidance_response(llm_response.content)
                
                # Log guidance result
                self.logger.info(
                    f"Generated guidance: {guidance_decision.guidance_type} - "
                    f"{guidance_decision.suggestion[:50]}..."
                )
                
                return guidance_decision
                
            except Exception as e:
                self.logger.error(f"Strategic guidance generation failed: {e}")
                raise LLMServiceError(f"Guidance generation failed: {e}") from e

    def _create_guidance_context(
        self,
        current_state: str,
        test_objective: str,
        strategy_context: Dict[str, Any],
        history_summary: Optional[str]
    ) -> Dict[str, Any]:
        """
        Create compact context for guidance prompt generation.
        
        ### Context Strategy:
        - Focuses on strategic information relevant for guidance
        - Keeps context compact to optimize prompt efficiency
        - Includes key metrics and performance indicators
        - Provides sufficient context for strategic decisions
        
        Args:
            current_state: Current application state description
            test_objective: Testing objective or goal
            strategy_context: Strategy performance and context
            history_summary: Optional recent history summary
            
        Returns:
            Dictionary with guidance context information
        """
        context = {
            "current_state": current_state,
            "test_objective": test_objective,
            "current_strategy": strategy_context.get("current_strategy", "unknown"),
            "strategy_performance": strategy_context.get("performance_summary", ""),
            "coverage_status": strategy_context.get("coverage_summary", ""),
            "recent_progress": strategy_context.get("progress_summary", ""),
            "bottlenecks": strategy_context.get("identified_bottlenecks", []),
            "history_summary": history_summary or ""
        }
        
        return context

    def _generate_guidance_prompt(self, context: Dict[str, Any]) -> List[LLMMessage]:
        """
        Generate compact guidance prompt using PromptFramework.
        
        ### Prompt Strategy:
        - Uses template-based prompt generation for consistency
        - Creates compact prompts optimized for guidance
        - Includes essential context without unnecessary detail
        - Enforces structured JSON response format
        
        Args:
            context: Guidance context dictionary
            
        Returns:
            List of LLMMessage objects for guidance generation
        """
        # Use PromptFramework to generate guidance messages
        # The framework will use the guidance strategy and templates
        messages = self.prompt_framework.generate_prompt(
            state={"guidance_context": context},
            context=context
        )
        
        return messages

    def _process_guidance_response(self, response_text: str) -> GuidanceDecision:
        """
        Process LLM response into structured guidance decision.
        
        ### Response Processing Strategy:
        - Extracts JSON from potentially wrapped responses
        - Validates guidance type and required fields
        - Creates structured GuidanceDecision object
        - Handles parsing errors gracefully
        
        Args:
            response_text: Raw response text from LLM
            
        Returns:
            Validated GuidanceDecision object
            
        Raises:
            LLMResponseError: If response cannot be parsed or is invalid
        """
        if not response_text or not response_text.strip():
            self.logger.warning("Empty LLM response for guidance")
            return GuidanceDecision(
                GUIDANCE_TYPE_NO_GUIDANCE,
                "",
                "LLM returned empty response"
            )
        
        try:
            # Extract JSON from potentially wrapped response
            json_str = self._extract_json_from_response(response_text)
            
            # Parse JSON response
            response_data = json.loads(json_str)
            
            # Extract and validate guidance fields
            guidance_type = response_data.get("guidance_type")
            suggestion = response_data.get("suggestion", "")
            reasoning = response_data.get("reasoning", "")
            
            # Validate guidance type
            valid_types = [GUIDANCE_TYPE_STRATEGIC, GUIDANCE_TYPE_FLOW_CHANGE, GUIDANCE_TYPE_NO_GUIDANCE]
            if guidance_type not in valid_types:
                raise ValueError(f"Invalid guidance_type: {guidance_type}")
            
            # Create guidance decision
            return GuidanceDecision(guidance_type, suggestion, reasoning)
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse guidance response as JSON: {e}")
            self.logger.debug(f"Raw response: {response_text}")
            raise LLMResponseError(f"Invalid JSON response from LLM: {e}")
            
        except ValueError as e:
            self.logger.error(f"Invalid guidance data: {e}")
            self.logger.debug(f"Raw response: {response_text}")
            raise LLMResponseError(f"Invalid guidance data: {e}")
            
        except Exception as e:
            self.logger.error(f"Unexpected error processing guidance response: {e}")
            self.logger.debug(f"Raw response: {response_text}")
            raise LLMResponseError(f"Unexpected error processing guidance: {e}")

    def _extract_json_from_response(self, response_text: str) -> str:
        """
        Extract JSON content from potentially wrapped LLM response.
        
        ### Extraction Strategy:
        - Handles responses wrapped in markdown code blocks
        - Extracts pure JSON content for parsing
        - Falls back to raw response if no wrapping detected
        
        Args:
            response_text: Raw response text from LLM
            
        Returns:
            Extracted JSON string
        """
        # Look for JSON wrapped in markdown code blocks
        json_start = response_text.find('```json')
        json_end = response_text.rfind('```')
        
        if json_start != -1 and json_end != -1 and json_end > json_start:
            # Extract JSON from markdown wrapper
            return response_text[json_start + len('```json'):json_end].strip()
        else:
            # Use raw response if no wrapper found
            return response_text.strip()

    @ErrorHandler.handle_errors(
        component="RVDroidGuidanceService",
        operation="cleanup"
    )
    def cleanup(self) -> None:
        """
        Clean up guidance service resources.
        
        ### Cleanup Strategy:
        - Safely disposes of LLM manager resources
        - Handles cleanup errors gracefully
        - Logs cleanup operations for monitoring
        """
        try:
            if self.llm_manager:
                self.llm_manager.cleanup()
                
            self.logger.info("RVDroid guidance service cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Guidance service cleanup failed: {e}")
            raise LLMServiceError(f"Guidance service cleanup failed: {e}")