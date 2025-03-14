# rvandroid/llm/prompt/prompt_template.py
"""
Module for template-based prompt generation.
Provides a flexible, composable approach to generate prompts for LLMs.
"""

from typing import Dict, List, Any, Callable


class PromptTemplate:
    """
    Represents a template for generating prompts with variable content.
    Uses a composition-based approach for flexibility.
    """

    def __init__(self, template_text: str, required_variables: List[str] = None):
        """
        Initialize a prompt template.

        Args:
            template_text: The template text with placeholders
            required_variables: List of variable names required for this template
        """
        self.template_text = template_text
        self.required_variables = required_variables or []
        self.transformers: Dict[str, Callable] = {}

    def add_transformer(self, variable: str, transform_func: Callable) -> 'PromptTemplate':
        """
        Add a transformation function for a variable.

        Args:
            variable: Variable name to transform
            transform_func: Function to transform the variable value

        Returns:
            Self for method chaining
        """
        self.transformers[variable] = transform_func
        return self

    def render(self, variables: Dict[str, Any]) -> str:
        """
        Render the template with the provided variables.

        Args:
            variables: Dictionary of variable names and values

        Returns:
            Rendered template string

        Raises:
            ValueError: If a required variable is missing
        """
        # Check for required variables
        missing = [var for var in self.required_variables if var not in variables]
        if missing:
            raise ValueError(f"Missing required variables: {', '.join(missing)}")

        # Apply transformers to variables
        processed_vars = {}
        for var_name, var_value in variables.items():
            if var_name in self.transformers:
                processed_vars[var_name] = self.transformers[var_name](var_value)
            else:
                processed_vars[var_name] = var_value

        # Perform template substitution
        result = self.template_text
        for var_name, var_value in processed_vars.items():
            placeholder = f"{{{var_name}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(var_value))

        return result


class PromptLibrary:
    """
    A collection of reusable prompt templates for different scenarios.
    Provides standard templates that can be customized by derived classes.
    """

    @staticmethod
    def system_base_template() -> PromptTemplate:
        """
        Basic system prompt template that defines the LLM's role.

        Returns:
            PromptTemplate for system prompt
        """
        template = """You are an Android UI testing expert. Your task is to analyze the current app state and suggest the MOST EFFECTIVE NEXT ACTIONS to take for testing the application thoroughly.

Focus on:
1. {exploration_goal}
2. Maximizing code coverage by targeting untested UI elements
3. Prioritizing testing of methods of interest that directly or indirectly affect operations defined in formal specifications
4. Testing complete workflows from start to finish

{response_format}

{additional_guidelines}

DO NOT include any additional text outside of the JSON array. Your response must be valid JSON that can be parsed directly."""

        return PromptTemplate(
            template,
            required_variables=["exploration_goal", "response_format"]
        )

    @staticmethod
    def user_base_template() -> PromptTemplate:
        """
        Basic user prompt template.

        Returns:
            PromptTemplate for user prompt
        """
        template = """Current Activity: {activity}

{static_context}

Current UI Elements and Available Actions:
{ui_elements}

{action_history}

{summary}"""

        return PromptTemplate(
            template,
            required_variables=["activity", "ui_elements"]
        )

    @staticmethod
    def single_action_format() -> str:
        """
        Format instructions for single action responses.

        Returns:
            Formatting instruction string
        """
        return """Your response MUST follow this schema - a JSON array with EXACTLY ONE object inside:
[
  {
    "action_id": "5",  
    "params": {},  
    "explanation": "Detailed explanation of why this action was chosen as the next step"
  }
]

YOUR RESPONSE MUST CONTAIN EXACTLY ONE ACTION. DO NOT SUGGEST MULTIPLE ACTIONS OR A SEQUENCE OF ACTIONS."""

    @staticmethod
    def multi_action_format() -> str:
        """
        Format instructions for multiple action responses.

        Returns:
            Formatting instruction string
        """
        return """Your response must be a valid JSON array of actions following this schema:
[
  {
    "action_id": "5",  
    "params": {},  
    "explanation": "Detailed explanation of why this action was chosen"
  },
  {
    "action_id": "8",  
    "params": {"text": "example@email.com"},  
    "explanation": "Detailed explanation for this action"
  }
]"""

    @staticmethod
    def dropdown_guidelines() -> str:
        """
        Guidelines for dropdown interaction.

        Returns:
            Dropdown interaction guidelines
        """
        return """DROPDOWN INTERACTION RULES:
1. For dropdown spinners, you MUST first CLICK the dropdown to open it before scrolling
2. The correct sequence is: CLICK dropdown → THEN scroll to find option → THEN click to select"""

    @staticmethod
    def form_guidelines() -> str:
        """
        Guidelines for form testing.

        Returns:
            Form testing guidelines
        """
        return """FORM TESTING WORKFLOW:
1. ALWAYS fill forms in a SEQUENTIAL, LOGICAL ORDER before submitting them
2. For forms with dropdowns/spinners, first click and select from dropdown, then fill other fields, then click action buttons
3. For forms with input fields and buttons, fill ALL required inputs first, THEN click the action/submit button
4. When a form appears to be completely filled, CLICK THE ACTION BUTTON to complete the workflow
5. COMPLETE WORKFLOWS - After filling all required inputs, proceed to action buttons to test the functionality"""
   