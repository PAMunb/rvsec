"""Unified LLM consultation manager for RVDroid.

This module provides a new implementation of the LLM consultation manager
that uses the unified prompt framework for generating guidance.
"""

import time
from typing import Dict, Any, Optional, List, Tuple

from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.llm.constants import ContextEntry, PromptStrategyType
from rvandroid.llm.prompt.framework import PromptFramework
from rvandroid.llm.prompt.information.fragments.history_fragment import HistoryFragment
from rvandroid.llm.prompt.information.fragments.monitored_operations_fragment import MonitoredOperationsFragment
from rvandroid.llm.prompt.information.fragments.ui_elements_fragment import UIElementsFragment
from rvandroid.llm.prompt.information.fragments.ui_pattern_fragment import UIPatternFragment
from rvandroid.llm.service.state_enricher import StateEnricher
from rvandroid.rvdroid.core.component import Component
from rvandroid.util.error.decorators import handle_error
from rvandroid.util.error.error_handler import ErrorHandler
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class UnifiedConsultationManager(Component):
    """Manager for LLM consultation in RVDroid using the unified prompt framework.
    
    This implementation uses the new prompt framework with XML templates
    and organized fragments to provide more consistent and maintainable
    LLM consultation capabilities.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the unified LLM consultation manager.
        
        Args:
            config: Optional configuration dictionary.
        """
        super().__init__("UnifiedConsultationManager", config)
        
        # Extract configuration
        self.static_data = config.get("static_data") if config else None
        self.memory_system = config.get("memory_system")
        
        # Create configuration
        self.component_config = ComponentConfigurator()
        
        # Initialize components
        self.state_enricher = None
        self.framework = None
        
        # LLM usage settings
        self.guidance_interval = config.get("guidance_interval", 60)  # Default: once per minute
        self.last_llm_guidance_time = 0
        self.last_llm_guidance = None
        
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
        """Initialize the LLM consultation manager.
        
        Returns:
            True if initialization succeeded, False otherwise.
        """
        self.logger.info("Initializing unified LLM consultation manager")
        
        # Check if LLM should be enabled
        use_llm = self.config.get("use_llm", True)
        if not use_llm:
            self.logger.info("LLM guidance is disabled in configuration")
            self.initialized = True
            return True
        
        try:
            # Set up LLM configuration
            model_type = self.config.get("model_type", "ollama")
            model_name = self.config.get("model_name", "llama3:8b")
            
            # Configure the component configurator
            self.component_config.set_llm(model_type, model_name)
            
            # Create state enricher
            self.state_enricher = StateEnricher(self.static_data, self.component_config)
            
            # Create prompt framework
            self.framework = PromptFramework.create(self.component_config)
            
            # Add custom fragments if needed
            history_fragment = HistoryFragment()
            self.framework.register_information_fragment(history_fragment)
            
            self.logger.info(f"Initialized unified LLM consultation manager with {model_type}:{model_name}")
            self.initialized = True
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize unified LLM consultation manager: {e}", exc_info=True)
            self.error_handler.handle_error(e, context={"component": "UnifiedConsultationManager"})
            return False
    
    @handle_error(level="ERROR")
    def get_strategic_guidance(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        """Get strategic guidance for the current testing state.
        
        Args:
            state: The current application state.
            context: Additional context information.
            
        Returns:
            Strategic guidance as a string.
        """
        self.logger.info("Getting strategic guidance")
        self.stats["strategic_guidance_requests"] += 1
        
        # Check if we should throttle requests
        current_time = time.time()
        if current_time - self.last_llm_guidance_time < self.guidance_interval:
            # If recently requested, return the last guidance
            if self.last_llm_guidance:
                self.logger.info("Using cached strategic guidance due to throttling")
                return self.last_llm_guidance
        
        # Update last guidance time
        self.last_llm_guidance_time = current_time
        
        try:
            # Create context for strategic guidance
            strategic_context = {
                ContextEntry.TEMPLATE: "strategic_guidance",
                "testing_progress": context.get("testing_progress", "Unknown"),
                "covered_areas": context.get("covered_areas", "Unknown"),
                "unexplored_areas": context.get("unexplored_areas", "Unknown")
            }
            
            # Enrich state
            enriched_state = self.state_enricher.enrich_state(state)
            
            # Generate guidance using framework
            response = self.framework.generate_with_llm(
                PromptStrategyType.STANDARD, 
                enriched_state, 
                strategic_context
            )
            
            if response:
                guidance = response.get_text_content() if hasattr(response, "get_text_content") else str(response)
                
                # Cache the guidance
                self.last_llm_guidance = guidance
                
                # Update stats
                self.stats["successful_guidance_requests"] += 1
                
                return guidance
            else:
                self.logger.error("Failed to get strategic guidance: Empty response")
                self.stats["failed_guidance_requests"] += 1
                return "Unable to generate strategic guidance at this time."
                
        except Exception as e:
            self.logger.error(f"Failed to get strategic guidance: {e}", exc_info=True)
            self.error_handler.handle_error(e, context={"component": "UnifiedConsultationManager"})
            self.stats["failed_guidance_requests"] += 1
            return "Error generating strategic guidance."
    
    @handle_error(level="ERROR")
    def get_action_feedback(self, state: Dict[str, Any], action: Dict[str, Any], result: Dict[str, Any]) -> str:
        """Get feedback on a testing action and its result.
        
        Args:
            state: The current application state.
            action: The testing action that was performed.
            result: The result of the action.
            
        Returns:
            Feedback on the action and result as a string.
        """
        self.logger.info("Getting action feedback")
        self.stats["action_feedback_requests"] += 1
        
        try:
            # Create context for action feedback
            feedback_context = {
                ContextEntry.TEMPLATE: "action_feedback",
                "previous_action": str(action),
                "action_result": str(result),
                "action_success": result.get("success", False)
            }
            
            # Enrich state
            enriched_state = self.state_enricher.enrich_state(state)
            
            # Generate feedback using framework
            response = self.framework.generate_with_llm(
                PromptStrategyType.STANDARD, 
                enriched_state, 
                feedback_context
            )
            
            if response:
                feedback = response.get_text_content() if hasattr(response, "get_text_content") else str(response)
                
                # Update stats
                self.stats["successful_guidance_requests"] += 1
                
                return feedback
            else:
                self.logger.error("Failed to get action feedback: Empty response")
                self.stats["failed_guidance_requests"] += 1
                return "Unable to generate action feedback at this time."
                
        except Exception as e:
            self.logger.error(f"Failed to get action feedback: {e}", exc_info=True)
            self.error_handler.handle_error(e, context={"component": "UnifiedConsultationManager"})
            self.stats["failed_guidance_requests"] += 1
            return "Error generating action feedback."
    
    @handle_error(level="ERROR")
    def get_directives_for_state(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get directives for handling the current application state.
        
        Args:
            state: The current application state.
            
        Returns:
            List of directives for handling the state.
        """
        try:
            # Enrich state
            enriched_state = self.state_enricher.enrich_state(state)
            
            # Create context for directives
            directive_context = {
                ContextEntry.TEMPLATE: "state_directives",
                ContextEntry.ADDITIONAL_GUIDELINES: (
                    "Provide specific directives for handling this application state. "
                    "Each directive should include an action type, target, and priority."
                )
            }
            
            # Generate directives using framework
            response = self.framework.generate_with_llm(
                PromptStrategyType.BATCH_ACTION, 
                enriched_state, 
                directive_context
            )
            
            if response:
                directives_text = response.get_text_content() if hasattr(response, "get_text_content") else str(response)
                
                # Parse directives from response
                directives = self._parse_directives(directives_text)
                
                # Update stats
                self.stats["total_directives_applied"] += len(directives)
                
                return directives
            else:
                self.logger.error("Failed to get directives: Empty response")
                return []
                
        except Exception as e:
            self.logger.error(f"Failed to get directives: {e}", exc_info=True)
            self.error_handler.handle_error(e, context={"component": "UnifiedConsultationManager"})
            return []
    
    def _parse_directives(self, directives_text: str) -> List[Dict[str, Any]]:
        """Parse directives from LLM response text.
        
        Args:
            directives_text: Text response from LLM.
            
        Returns:
            List of parsed directive dictionaries.
        """
        directives = []
        
        try:
            # Try to parse as JSON
            import json
            
            # Find JSON array in the response
            import re
            json_match = re.search(r'\[\s*{.*}\s*\]', directives_text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group(0)
                parsed_directives = json.loads(json_str)
                
                # Validate and clean up directives
                for directive in parsed_directives:
                    if "action_type" in directive and "target" in directive:
                        directives.append(directive)
            else:
                self.logger.warning("Could not find JSON array in directives response")
                
        except json.JSONDecodeError:
            self.logger.warning("Failed to parse directives as JSON, using fallback parser")
            
            # Fallback: simple line-based parsing
            lines = directives_text.strip().split("\n")
            current_directive = {}
            
            for line in lines:
                line = line.strip()
                
                # Check for directive start indicators
                if line.startswith("- ") or line.startswith("* ") or line.startswith("1. "):
                    # Save previous directive if it exists
                    if current_directive and "action_type" in current_directive and "target" in current_directive:
                        directives.append(current_directive)
                    
                    # Start new directive
                    current_directive = {}
                
                # Parse key-value pairs
                if ":" in line:
                    parts = line.split(":", 1)
                    key = parts[0].strip().lower().replace(" ", "_")
                    value = parts[1].strip()
                    
                    if key in ["action_type", "target", "priority", "description"]:
                        current_directive[key] = value
            
            # Add the last directive if it exists
            if current_directive and "action_type" in current_directive and "target" in current_directive:
                directives.append(current_directive)
        
        except Exception as e:
            self.logger.error(f"Error parsing directives: {e}", exc_info=True)
        
        return directives
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about LLM consultation usage.
        
        Returns:
            Dictionary of usage statistics.
        """
        return self.stats.copy()
    
    def cleanup(self) -> None:
        """Clean up resources used by the consultation manager."""
        self.logger.info("Cleaning up unified consultation manager")
        
        # Clean up framework if needed
        if self.framework and hasattr(self.framework, "model") and self.framework.model:
            if hasattr(self.framework.model, "cleanup"):
                try:
                    self.framework.model.cleanup()
                except Exception as e:
                    self.logger.warning(f"Error cleaning up model: {e}")