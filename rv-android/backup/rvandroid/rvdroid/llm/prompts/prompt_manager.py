"""
Prompt manager for RVDroid LLM integration with MCP support.

This module provides functionality to manage and generate prompts for
the LLM, handling prompt templates, selection, and optimization,
with support for the Model Context Protocol (MCP).
"""

import json
import os
from typing import Dict, Any, Optional, List

from rvandroid.llm.data_structures import LLMMessage, LLMRole, LLMTextContent
from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager
from rvandroid.util.error.error_handler import ErrorHandler


class PromptManager:
    """
    Manages the selection and generation of prompts for LLM interaction with MCP support.

    ### Architectural Decisions:
    - Separates prompt management from LLM interaction logic
    - Uses template-based approach for flexibility and maintainability
    - Supports dynamic prompt selection based on context
    - Provides prompt optimization mechanisms
    - Integrates with MCP data structures for standardized LLM interactions

    ### Role in the System:
    - Generates appropriate prompts for different guidance needs
    - Tailors prompts based on application context
    - Optimizes prompts for token efficiency
    - Evaluates and improves prompt effectiveness
    - Supports both MCP and legacy formats for backward compatibility
    """

    def __init__(self, prompt_dir: Optional[str] = None):
        """
        Initialize the prompt manager.

        Args:
            prompt_dir: Optional directory containing prompt templates
        """
        # Configure logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvdroid.llm.prompts.manager",
            {CONTEXT_COMPONENT: "PromptManager"}
        )

        # Initialize error handler
        self.error_handler = ErrorHandler.get_instance()

        # Load prompt templates
        self.prompt_dir = prompt_dir or os.path.join(
            os.path.dirname(__file__), "templates")
        self.templates = self._load_templates()

        # Prompt statistics for effectiveness tracking
        self.prompt_stats: Dict[str, Dict[str, Any]] = {}

        self.logger.info(f"Loaded {len(self.templates)} prompt templates")

    def _load_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        Load prompt templates from files.

        Returns:
            Dictionary of prompt templates
        """
        templates = {}

        # Default templates if directory doesn't exist
        if not os.path.exists(self.prompt_dir):
            self.logger.warning(f"Prompt directory not found: {self.prompt_dir}")
            templates = self._get_default_templates()
            
            # Try to create the prompts directory and save the default templates
            try:
                os.makedirs(self.prompt_dir, exist_ok=True)
                
                # Save default templates to files
                for template_name, template_data in templates.items():
                    template_path = os.path.join(self.prompt_dir, f"{template_name}.json")
                    with open(template_path, "w") as f:
                        json.dump(template_data, f, indent=2)
                        
                self.logger.info(f"Created default prompt templates in {self.prompt_dir}")
            except Exception as e:
                self.logger.error(f"Error creating default templates: {e}")
                from rvandroid.util.exceptions import RVAndroidError
                error = RVAndroidError(f"Template creation error: {str(e)}")
                self.error_handler.handle_error(
                    error,
                    context={"prompt_dir": self.prompt_dir}
                )
            
            return templates

        try:
            # Load all template files
            for filename in os.listdir(self.prompt_dir):
                if filename.endswith(".json"):
                    template_path = os.path.join(self.prompt_dir, filename)
                    template_name = filename.replace(".json", "")

                    with open(template_path, "r") as f:
                        template = json.load(f)
                        templates[template_name] = template

            if not templates:
                self.logger.warning("No templates found, using defaults")
                return self._get_default_templates()

            return templates

        except Exception as e:
            self.logger.error(f"Error loading templates: {e}")
            from rvandroid.util.exceptions import RVAndroidError
            error = RVAndroidError(f"Template loading error: {str(e)}")
            self.error_handler.handle_error(
                error,
                context={"prompt_dir": self.prompt_dir}
            )
            return self._get_default_templates()

    def _get_default_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        Get default prompt templates.

        Returns:
            Dictionary of default prompt templates
        """
        return {
            "exploration": {
                "system": """You are a strategic advisor for mobile app testing specializing in runtime verification. 
Your goal is to provide clear, actionable guidance for app exploration with a focus on:
1. Areas with monitored methods (API usage, data operations, validation)
2. Unexplored functionality that might reveal specification violations
3. Potential edge cases in user input and API interaction

Format your response with:
1. A brief analysis of the current state
2. Specific actions to try next, prioritized by potential for finding violations
3. IMPORTANT: Include structured directives in this format:
```json
[
  {"type": "explore", "target": "input_validation", "priority": "high"},
  {"type": "strategy", "name": "systematic", "duration": 300},
  {"type": "focus", "target": "data_operations", "priority": "high"}
]
```
Keep your guidance concise, practical and focused on finding specification violations.""",
                "user": """I am testing an Android app with a focus on finding runtime verification violations.

CURRENT SCREEN_PATTERNS:
{current_screen}

INTERACTIVE ELEMENTS: {elements_count}

EXPLORATION PROGRESS: {progress}

EXPLORATION CONTEXT:
{history_summary}

What areas should I focus on exploring next to maximize detection of API misuse and specification violations? Prioritize actions that interact with monitored methods and provide structured directives for my testing strategy.""",
                "max_tokens": 800
            },
            "monitored_operations": {
                "system": """You are a mobile app testing expert specializing in runtime verification. 
Your goal is to analyze the current application state and identify potential operations of interest to monitor, with focus on:
1. API usage patterns
2. Data validation operations
3. Resource management (iterators, streams, connections)
4. Cryptographic operations
5. Input handling
6. State management

Format your response with:
1. Assessment of critical operation likelihood for the current screen
2. Specific areas of interest identified
3. IMPORTANT: Include structured recommendations in this format:
```json
[
  {"interest_level": "high/medium/low", "operation_type": "api_usage", "description": "..."},
  {"test_action": "...", "priority": "high/medium/low", "purpose": "..."}
]
```
Keep your analysis concise, evidence-based, and actionable.""",
                "user": """I need an assessment of potential operations of interest in the current Android app state.

CURRENT SCREEN_PATTERNS:
{current_screen}

MONITORED OPERATIONS:
{monitored_operations}

STATIC ANALYSIS INSIGHTS:
{monitored_ops_insights}

Based on this information, what operations of interest might exist in the current screen, and what specific tests should I perform to detect potential specification violations?""",
                "max_tokens": 800
            },
            "action_feedback": {
                "system": """You are an expert in mobile app test optimization.
Your goal is to provide feedback on testing actions to improve test effectiveness, with focus on:
1. Coverage efficiency (how well the action explores new functionality)
2. Potential for revealing specification violations (how relevant the action is for monitoring)
3. Next action recommendations based on the result

Format your response with:
1. Brief assessment of the action's effectiveness
2. Specific suggestions for follow-up actions
3. IMPORTANT: Include structured suggestions in this format:
```json
[
  {"text": "suggested next action", "priority": "high/medium/low", "reason": "..."},
  {"text": "alternative action", "priority": "high/medium/low", "reason": "..."}
]
```
Keep your feedback concise, specific, and focused on improving testing efficiency.""",
                "user": """I need feedback on a test action I performed.

ACTION: {action_description}
RESULT: {action_result}

CURRENT SCREEN_PATTERNS AFTER ACTION:
{current_screen}

Was this a useful test action? What should I try next to effectively continue testing, especially for finding specification violations and API misuse?""",
                "max_tokens": 500
            },
            "strategy": {
                "system": """You are a test strategy optimization expert for mobile apps.
Your goal is to recommend the most effective testing approach based on the current exploration phase and app state.

Testing strategies to consider:
1. Random - useful for initial exploration
2. Systematic - methodical coverage of all UI elements
3. Model-based - using app structure knowledge to guide testing
4. MonitoredMethod-focused - prioritizing components with monitored operations
5. Greedy - focusing on areas that previously revealed issues

Format your response with:
1. Assessment of current exploration progress
2. Recommended strategy with clear rationale
3. IMPORTANT: Include a structured strategy directive in this format:
```json
{
  "strategy": "strategy_name",
  "rationale": "explanation for this strategy",
  "duration": seconds_to_apply,
  "focus_areas": ["area1", "area2"]
}
```
Keep your recommendation concise and tailored to the current exploration state.""",
                "user": """I need a testing strategy recommendation.

CURRENT EXPLORATION PHASE: {exploration_phase}

CURRENT SCREEN_PATTERNS:
{current_screen}

PROGRESS METRICS:
{progress_metrics}

RECENT ACTIONS:
{recent_actions}

What testing strategy would be most effective now to maximize testing efficiency and detection of specification violations?""",
                "max_tokens": 500
            },
            "context_detection": {
                "system": """You are a mobile app context analysis expert.
Your goal is to analyze the current screen and identify the functional context (e.g., login, data entry, API interaction) of the app.

Key contexts to identify:
1. Authentication (login/registration screens)
2. Transaction processing (payments, data submissions)
3. Data handling (personal information entry, storage)
4. API interaction (external services, remote operations)
5. Settings/configuration screens
6. Content creation/editing
7. Navigation/browsing

Format your response with:
1. Identified primary context with confidence level
2. Secondary contexts if present
3. IMPORTANT: Include a structured context assessment in this format:
```json
{
  "primary_context": "context_name",
  "confidence": 0.0-1.0,
  "secondary_contexts": ["context_name1", "context_name2"],
  "interest_level": "high/medium/low"
}
```
Keep your analysis concise, evidence-based and focused on the functional context.""",
                "user": """I need to identify the functional context of the current screen in this Android app.

SCREEN_PATTERNS DETAILS:
{screen_description}

ELEMENT TEXTS:
{element_texts}

Based on these details, what is the functional context of this screen (e.g., login, data entry, settings, etc.)? Provide your confidence level and indicate if this context likely contains monitored operations of interest.""",
                "max_tokens": 400
            },
            "general": {
                "system": """You are an assistant for mobile app testing with runtime verification.
Your goal is to provide general guidance to make testing more effective, with focus on:
1. Best practices for detecting specification violations
2. Coverage optimization techniques
3. Strategy adaptation based on exploration progress

Format your response with:
1. General assessment of the testing approach
2. Specific recommendations for improvement
3. IMPORTANT: Include structured directives in this format:
```json
[
  {"type": "approach", "description": "...", "priority": "high/medium/low"},
  {"type": "focus", "target": "...", "rationale": "..."}
]
```
Keep your guidance concise, practical, and focused on improving testing efficiency.""",
                "user": """I need general guidance for my current mobile app testing approach.

CURRENT STATE:
{current_state}

TESTING STATISTICS:
- Screens explored: {screens_explored}
- Actions executed: {actions_executed}
- Monitored operations identified: {monitored_areas}
- Exploration phase: {exploration_phase}

What general guidance can you provide to improve my testing approach, especially for finding specification violations and API misuse?""",
                "max_tokens": 600
            }
        }

    def generate_prompt(self, prompt_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a prompt based on type and context in legacy format.

        Args:
            prompt_type: Type of prompt to generate
            context: Context information for prompt generation

        Returns:
            Dictionary with system and user prompts
        """
        # Get template for prompt type
        template = self.templates.get(prompt_type)
        if not template:
            self.logger.warning(f"Template not found for {prompt_type}, using general template")
            template = self.templates.get("general", self._get_default_templates()["general"])

        # Record prompt creation for stats
        if prompt_type not in self.prompt_stats:
            self.prompt_stats[prompt_type] = {
                "usage_count": 0,
                "token_estimate": 0,
                "successful_responses": 0
            }
        self.prompt_stats[prompt_type]["usage_count"] += 1

        try:
            # Format template with context using safe formatting
            system_prompt = self._safe_format(template["system"], context)
            user_prompt = self._safe_format(template["user"], context)

            # Estimate token usage (rough approximation)
            token_estimate = (len(system_prompt) + len(user_prompt)) // 4
            self.prompt_stats[prompt_type]["token_estimate"] = token_estimate

            # Set max tokens for response
            max_tokens = template.get("max_tokens", 500)

            return {
                "system": system_prompt,
                "user": user_prompt,
                "max_tokens": max_tokens
            }

        except Exception as e:
            self.logger.error(f"Error generating prompt: {e}")
            from rvandroid.util.exceptions import RVAndroidError
            error = RVAndroidError(f"Prompt generation error: {str(e)}")
            self.error_handler.handle_error(
                error,
                context={"prompt_type": prompt_type}
            )
            # Fall back to a simple prompt
            return {
                "system": template["system"],
                "user": f"Provide guidance based on context: {str(context)[:200]}...",
                "max_tokens": template.get("max_tokens", 500)
            }

    def generate_llm_messages(self, prompt_type: str, context: Dict[str, Any]) -> List[LLMMessage]:
        """
        Generate prompts in LLM format based on type and context.

        Args:
            prompt_type: Type of prompt to generate
            context: Context information for prompt generation

        Returns:
            List of LLMMessage objects for the conversation
        """
        # Get formatted prompts
        prompt_dict = self.generate_prompt(prompt_type, context)
        
        # Convert to MCP messages
        messages = []
        
        # System message
        if "system" in prompt_dict:
            messages.append(LLMMessage(
                role=LLMRole.SYSTEM,
                content=[LLMTextContent(text=prompt_dict["system"])]
            ))
            
        # User message
        if "user" in prompt_dict:
            messages.append(LLMMessage(
                role=LLMRole.USER,
                content=[LLMTextContent(text=prompt_dict["user"])]
            ))
            
        return messages

    def _safe_format(self, template_str: str, context: Dict[str, Any]) -> str:
        """
        Safely format a template string with context values.

        Args:
            template_str: Template string with placeholders
            context: Context dictionary for formatting

        Returns:
            Formatted string
        """
        # Replace placeholders with context values
        result = template_str

        for key, value in context.items():
            placeholder = "{" + key + "}"
            if placeholder in result:
                # Convert value to string and limit length
                value_str = str(value)
                if len(value_str) > 1000:
                    value_str = value_str[:1000] + "..."

                result = result.replace(placeholder, value_str)

        return result

    def get_max_tokens(self, prompt_type: str) -> int:
        """
        Get the maximum tokens for a prompt type.

        Args:
            prompt_type: Type of prompt

        Returns:
            Maximum tokens for the prompt type
        """
        template = self.templates.get(prompt_type)
        if not template:
            return 500
        return template.get("max_tokens", 500)