# rvandroid/llm/prompt/composable_prompt_strategy.py
"""
Composable Prompt Strategy Implementation

This implementation takes a composition-based approach to prompt generation,
allowing flexible assembly of prompt components and easy customization.
It leverages the template system to create prompts that can be adapted
to different models, testing scenarios, and UI patterns.
"""

import logging
from typing import Dict, Any, Optional, Union, List

from rvandroid.llm.prompt.base_prompt_strategy import BasePromptStrategy
from rvandroid.llm.prompt.prompt_template import PromptTemplate, PromptLibrary, TemplateFragment
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.parser.screen.abstract_parser import AbstractScreenParser
from rvandroid.parser.screen.parser_factory import ParserType
from rvandroid.parser.screen.visitor.model import ScreenDescription


class ComposablePromptStrategy(BasePromptStrategy):
    """
    A flexible, composable prompt strategy that allows dynamic assembly of prompt components.
    
    ### Architectural Decisions:
    - Implements component-based approach to prompt generation
    - Uses template system for maximum flexibility and reuse
    - Supports dynamic reconfiguration of prompt components
    - Enables specialized behavior without code duplication
    - Facilitates A/B testing of different prompt formats

    ### Role in the System:
    - Provides a highly customizable prompt generation approach
    - Supports both single and multi-action modes
    - Enables composition of different prompt sections based on context
    - Facilitates experimenting with different prompt structures
    - Serves as a foundation for specialized prompt strategies
    """

    def __init__(self,
                 static_data: Optional[StaticAnalysisData] = None,
                 parser: Union[ParserType, AbstractScreenParser, None] = None,
                 single_action_mode: bool = False,
                 detailed_static_analysis: bool = False,
                 include_screenshots: bool = False,
                 advanced_guidance: bool = False):
        """
        Initialize the composable prompt strategy.

        Args:
            static_data: Static analysis data (optional)
            parser: Parser type or instance
            single_action_mode: Whether to generate prompts for single action mode
            detailed_static_analysis: Whether to include detailed static analysis
            include_screenshots: Whether to include screenshot analysis
            advanced_guidance: Whether to include advanced testing guidelines
        """
        super().__init__(static_data, parser, detailed_static_analysis, include_screenshots)
        
        # Configuration flags
        self.single_action_mode = single_action_mode
        self.advanced_guidance = advanced_guidance
        
        # Create specialized template fragments
        self._create_template_fragments()
        
        self.logger.info(f"ComposablePromptStrategy initialized (single_action_mode={single_action_mode}, "
                        f"detailed_static_analysis={detailed_static_analysis}, "
                        f"include_screenshots={include_screenshots}, "
                        f"advanced_guidance={advanced_guidance})")

    def _create_template_fragments(self):
        """Create specialized template fragments for this strategy."""
        # Add dropdown guidelines fragment
        self.system_template.add_fragment(
            "dropdown_guidelines",
            PromptLibrary.dropdown_guidelines()
        )
        
        # Add form guidelines fragment
        self.system_template.add_fragment(
            "form_guidelines", 
            PromptLibrary.form_guidelines()
        )
        
        # Add advanced guidelines fragment if needed
        if self.advanced_guidance:
            self.system_template.add_fragment(
                "advanced_guidelines",
                PromptLibrary.advanced_guidelines()
            )
            
        # Add specialized fragments for screen types
        form_guidance = """
FORM SCREEN GUIDANCE:
1. First identify all required input fields
2. Fill inputs in logical sequence (top-to-bottom)
3. For dropdowns, click to open, then select value
4. After filling all fields, submit the form
5. Test both valid and invalid input combinations"""

        self.user_template.add_fragment(
            "form_guidance",
            form_guidance
        )
        
        list_guidance = """
LIST SCREEN GUIDANCE:
1. Test scrolling to discover all list items
2. Systematically select items from different positions (top, middle, bottom)
3. If search capability exists, test with various queries
4. Check for sorting/filtering options
5. Verify that list navigation works as expected"""

        self.user_template.add_fragment(
            "list_guidance",
            list_guidance
        )

    def generate_system_prompt(self) -> str:
        """
        Generate a system prompt using the template approach with dynamic components.

        Returns:
            System prompt string
        """
        # Configure exploration goal based on mode
        if self.single_action_mode:
            exploration_goal = ("Systematically exploring ALL parts of the application "
                               "with a focus on depth-first testing of complete workflows")
            response_format = PromptLibrary.single_action_format()
        else:
            exploration_goal = ("Systematically exploring all application states in a logical sequence "
                               "with a balanced approach to breadth and depth")
            response_format = PromptLibrary.multi_action_format()
        
        # Build additional guidelines dynamically
        additional_guidelines = "REVIEW the action history carefully to understand what has already been tested and choose the most logical next action."
        
        if self.single_action_mode:
            additional_guidelines += "\n\nREMEMBER: You MUST suggest only ONE action - the single most important next action to take."
            
        if self.advanced_guidance:
            additional_guidelines += "\n\n{#include advanced_guidelines}"
        
        # Render the template with parameters
        return self.system_template.render({
            "exploration_goal": exploration_goal,
            "response_format": response_format,
            "additional_guidelines": additional_guidelines
        })

    def generate_user_prompt(self, state: Dict[str, Any]) -> str:
        """
        Generate a user prompt using the template approach with dynamic components.

        Args:
            state: Current application state

        Returns:
            User prompt string
        """
        # Use the base class implementation for core functionality
        return super().generate_user_prompt(state)

    def _generate_summary(self, activity: str, screen_description: ScreenDescription, 
                         state: Dict[str, Any]) -> str:
        """
        Generate a summary section with specialized guidance based on screen type.

        Args:
            activity: Current activity name
            screen_description: Parsed screen description
            state: Current application state

        Returns:
            Generated summary string
        """
        summary = f"SUMMARY: You are testing the {activity} screen."
        
        # Detect screen types for specialized guidance
        form_elements = [item for item in screen_description.items
                         if any(t in item.base_description.lower()
                                for t in ["text field", "spinner", "checkbox"])]
        
        buttons = [item for item in screen_description.items
                   if "button" in item.base_description.lower()]
        
        list_items = [item for item in screen_description.items
                     if "list" in item.base_description.lower() or 
                        "recycler" in item.base_description.lower()]
        
        # Identify screen type and add specialized guidance
        screen_type = None
        if form_elements and buttons:
            summary += " This screen appears to contain a form with input fields and buttons."
            
            # Check if this appears to be a login form
            login_related = any(("login" in item.base_description.lower() or
                               "username" in item.base_description.lower() or
                               "password" in item.base_description.lower())
                              for item in form_elements)
            
            if login_related:
                summary += " This appears to be a login form."
                
            screen_type = "form"
            
        elif list_items or (len(screen_description.items) > 5 and 
                            any("view" in item.base_description.lower() for item in screen_description.items)):
            summary += " This appears to be a list or scrollable screen with multiple items."
            screen_type = "list"
            
        elif buttons and len(buttons) > 3:
            summary += " This screen contains multiple buttons/controls that should be systematically tested."
            
        elif "menu" in activity.lower():
            summary += " This appears to be a menu screen with multiple options."
        
        # Add mode-specific instructions
        if self.single_action_mode:
            summary += " Select ONE action from the available options above that would be the most logical next step in testing this screen."
        else:
            summary += " Select 3-5 actions from the available options above that would be most effective for testing this screen."
            
        # Add specialized guidance based on screen type
        if screen_type == "form":
            summary += "\n\n{#include form_guidance}"
        elif screen_type == "list":
            summary += "\n\n{#include list_guidance}"
        
        return summary
    
    def add_template_fragment(self, name: str, content: str, template_type: str = "system") -> None:
        """
        Add a custom template fragment for prompt customization.
        
        Args:
            name: Fragment name
            content: Fragment content
            template_type: Which template to add to ('system' or 'user')
        """
        fragment = TemplateFragment(name, content)
        
        if template_type.lower() == "system":
            self.system_template.add_fragment(name, fragment)
        else:
            self.user_template.add_fragment(name, fragment)
            
        self.logger.info(f"Added custom template fragment '{name}' to {template_type} template")
    
    def customize_exploration_goal(self, goal: str) -> None:
        """
        Customize the exploration goal for this strategy.
        
        Args:
            goal: Custom exploration goal text
        """
        self._exploration_goal = goal
        self.logger.info(f"Customized exploration goal: {goal[:50]}...")
        
    def set_mode(self, single_action: bool) -> None:
        """
        Change the strategy mode.
        
        Args:
            single_action: Whether to use single action mode
        """
        self.single_action_mode = single_action
        self.logger.info(f"Mode changed to {'single action' if single_action else 'multi-action'}")