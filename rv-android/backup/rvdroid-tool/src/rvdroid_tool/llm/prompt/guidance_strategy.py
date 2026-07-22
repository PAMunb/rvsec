"""
Guidance Strategy for RVDroid LLM Prompting

### Architectural Overview:
This module implements a specialized prompt strategy for RVDroid strategic guidance.
It creates compact, focused prompts that solicit high-level strategic advice rather
than specific action generation, integrating with rv-llm PromptFramework.

### Key Architectural Decisions:
- Uses rv-llm PromptFramework base classes for consistency
- Implements guidance-specific prompt generation logic
- Creates compact prompts optimized for strategic decision-making
- Integrates with RVDroid template system for guidance

### Role in the System:
- Generates system and user prompts for strategic guidance
- Uses template-based approach for consistency and maintainability
- Provides guidance-specific context processing
- Coordinates with RVDroidGuidanceService for complete pipeline

### Design Patterns:
- Strategy Pattern: Implements specific guidance prompting strategy
- Template Method: Uses template-based prompt generation
- Factory Pattern: Integrates with PromptFramework factory system
"""

import os
from typing import Dict, Any, List

from rv_llm.llm.data_structures import LLMMessage, LLMTextContent
from rv_llm.llm.prompt.base import BasePromptStrategy
from rv_llm.llm.prompt.template import TemplateRepository

from rvdroid_tool.constants import TEMPLATES_DIR


class RVDroidGuidanceStrategy(BasePromptStrategy):
    """
    Specialized prompt strategy for RVDroid strategic guidance generation.
    
    ### Architectural Overview:
    This strategy creates compact, guidance-focused prompts that solicit strategic
    advice for RVDroid testing operations. It differs from action generation strategies
    by focusing on high-level recommendations rather than specific UI actions.
    
    ### Key Features:
    - Compact prompt generation optimized for guidance
    - Template-based approach for consistency
    - Strategic context processing for decision-making
    - Integration with rv-llm PromptFramework patterns
    
    ### Template Integration:
    - Uses guidance-specific templates for system and user prompts
    - Processes RVDroid testing context into guidance-relevant information
    - Maintains compact prompt structure for efficiency
    
    ### Response Expectations:
    - Expects structured JSON responses with guidance decisions
    - Enforces specific guidance types and format constraints
    - Optimizes for strategic rather than tactical recommendations
    """

    def __init__(self, template_dir: str = None):
        """
        Initialize guidance strategy with template repository.
        
        ### Initialization Strategy:
        - Sets up template repository for guidance-specific templates
        - Configures template directory for RVDroid guidance templates
        - Prepares context processing for guidance generation
        
        Args:
            template_dir: Directory containing guidance templates (optional)
        """
        # Use default template directory if not specified
        if template_dir is None:
            # Get template directory relative to this module
            module_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            template_dir = os.path.join(module_dir, TEMPLATES_DIR)
        
        # Initialize template repository
        self.template_repository = TemplateRepository(template_dir)
        
        super().__init__()

    def generate_prompt(self, state: Dict[str, Any], context: Dict[str, Any]) -> List[LLMMessage]:
        """
        Generate guidance-specific prompt messages for LLM interaction.
        
        ### Prompt Generation Strategy:
        - Creates system message with guidance role and constraints
        - Builds user message with compact strategic context
        - Uses template-based approach for consistency and maintainability
        - Optimizes prompt length for guidance efficiency
        
        Args:
            state: Current application/testing state
            context: Additional context for guidance generation
            
        Returns:
            List of LLMMessage objects for guidance generation
        """
        messages = []
        
        # Extract guidance context from state and context
        guidance_context = context.get("guidance_context", {})
        
        # Generate system message for guidance role
        system_content = self._build_system_prompt(guidance_context)
        system_message = LLMMessage(
            role="system",
            content=[LLMTextContent(text=system_content)]
        )
        messages.append(system_message)
        
        # Generate user message with strategic context
        user_content = self._build_user_prompt(guidance_context)
        user_message = LLMMessage(
            role="user", 
            content=[LLMTextContent(text=user_content)]
        )
        messages.append(user_message)
        
        return messages

    def _build_system_prompt(self, context: Dict[str, Any]) -> str:
        """
        Build system prompt for guidance role definition.
        
        ### System Prompt Strategy:
        - Defines role as strategic testing advisor
        - Sets constraints on response format and content
        - Establishes guidance-specific expectations
        - Keeps prompt compact and focused
        
        Args:
            context: Guidance context dictionary
            
        Returns:
            System prompt string for guidance generation
        """
        try:
            # Use template for system guidance prompt
            template = self.template_repository.get_template("templates/system_guidance.xml")
            return template.render(context)
        except Exception as e:
            # Fallback to basic system prompt if template fails
            return (
                "You are a strategic testing advisor for RVDroid Android testing system. "
                "Provide concise strategic guidance for testing optimization. "
                "Respond only in JSON format with guidance_type, suggestion, and reasoning."
            )

    def _build_user_prompt(self, context: Dict[str, Any]) -> str:
        """
        Build user prompt with strategic testing context.
        
        ### User Prompt Strategy:
        - Includes current testing state and performance
        - Provides strategic context for decision-making
        - Maintains compact format for efficiency
        - Uses template-based generation for consistency
        
        Args:
            context: Guidance context dictionary
            
        Returns:
            User prompt string with strategic context
        """
        try:
            # Use template for guidance prompt
            template = self.template_repository.get_template("templates/guidance.xml") 
            return template.render(context)
        except Exception as e:
            # Fallback to basic user prompt if template fails
            return (
                f"Current State: {context.get('current_state', 'unknown')}\n"
                f"Objective: {context.get('test_objective', 'general testing')}\n"
                f"Strategy: {context.get('current_strategy', 'unknown')}\n"
                f"Performance: {context.get('strategy_performance', 'unknown')}\n\n"
                "Provide strategic guidance for testing optimization."
            )

    def get_strategy_name(self) -> str:
        """
        Get strategy name for identification and logging.
        
        Returns:
            Strategy name string
        """
        return "rvdroid_guidance"

    def get_expected_response_format(self) -> str:
        """
        Get expected response format description.
        
        Returns:
            Description of expected JSON response format
        """
        return "JSON with guidance_type, suggestion, and reasoning fields"