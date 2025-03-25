# rvandroid/rvdroid/llm/prompts/prompt_manager.py
"""
Prompt manager for RVDroid LLM integration.

This module provides functionality to manage and generate prompts for
the LLM, handling prompt templates, selection, and optimization.
"""

import json
import os
from typing import Dict, Any, Optional

from rvandroid.util.logging.constants import CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class PromptManager:
    """
    Manages the selection and generation of prompts for LLM interaction.

    ### Architectural Decisions:
    - Separates prompt management from LLM interaction logic
    - Uses template-based approach for flexibility and maintainability
    - Supports dynamic prompt selection based on context
    - Provides prompt optimization mechanisms

    ### Role in the System:
    - Generates appropriate prompts for different guidance needs
    - Tailors prompts based on application context
    - Optimizes prompts for token efficiency
    - Evaluates and improves prompt effectiveness
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
            return self._get_default_templates()

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
            return self._get_default_templates()

    def _get_default_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        Get default prompt templates.

        Returns:
            Dictionary of default prompt templates
        """
        return {
            "exploration": {
                "system": "You are a strategic advisor for mobile app testing. Your goal is to provide guidance on exploring the app efficiently to find potential issues, especially security vulnerabilities.",
                "user": "I am testing an Android app. Current screen: {current_screen}. Interactive elements: {elements_count}. Exploration progress: {progress}. What areas should I focus on exploring next?",
                "max_tokens": 500
            },
            "security": {
                "system": "You are a security advisor for mobile app testing. Your goal is to identify potential security vulnerabilities in the current application state.",
                "user": "I am testing an Android app for security issues. Current screen: {current_screen}. Available operations: {security_operations}. What security aspects should I focus on?",
                "max_tokens": 600
            },
            "action_feedback": {
                "system": "You are an app testing expert. Your goal is to provide feedback on test actions and their results to improve testing effectiveness.",
                "user": "I performed action: {action_description}. Result: {action_result}. Current screen: {current_screen}. Was this a useful test action? What should I try next?",
                "max_tokens": 300
            },
            "strategy": {
                "system": "You are a test strategy expert for mobile apps. Your goal is to recommend the most effective testing strategy for the current exploration state.",
                "user": "I am testing an Android app. Current exploration phase: {exploration_phase}. Current screen: {current_screen}. Progress metrics: {progress_metrics}. What testing strategy would be most effective now?",
                "max_tokens": 300
            },
            "general": {
                "system": "You are an assistant for mobile app testing. Your goal is to provide general guidance to make testing more effective.",
                "user": "I am testing an Android app. Current state: {current_state}. What general guidance can you provide to improve my testing approach?",
                "max_tokens": 400
            }
        }

    def generate_prompt(self, prompt_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a prompt based on type and context.

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
            # Fall back to a simple prompt
            return {
                "system": template["system"],
                "user": f"Provide guidance based on context: {str(context)[:200]}...",
                "max_tokens": template.get("max_tokens", 500)
            }

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

    def optimize_prompt(self, prompt_type: str, success_rate: float) -> None:
        """
        Optimize a prompt based on its success rate.

        Args:
            prompt_type: Type of prompt to optimize
            success_rate: Rate of successful responses (0.0 to 1.0)
        """
        # Update success stats
        if prompt_type in self.prompt_stats:
            self.prompt_stats[prompt_type]["successful_responses"] += 1 if success_rate > 0.5 else 0

            # Calculate overall success rate
            usage_count = self.prompt_stats[prompt_type]["usage_count"]
            successful_responses = self.prompt_stats[prompt_type]["successful_responses"]
            overall_success_rate = successful_responses / usage_count if usage_count > 0 else 0

            self.logger.info(f"Prompt {prompt_type} success rate: {overall_success_rate:.2f}")

    def get_template_info(self) -> Dict[str, Any]:
        """
        Get information about available templates and their usage.

        Returns:
            Dictionary with template information
        """
        template_info = {}

        for template_name, template in self.templates.items():
            # Get stats if available
            stats = self.prompt_stats.get(template_name, {
                "usage_count": 0,
                "token_estimate": 0,
                "successful_responses": 0
            })

            # Calculate success rate
            usage_count = stats["usage_count"]
            successful_responses = stats["successful_responses"]
            success_rate = successful_responses / usage_count if usage_count > 0 else 0

            template_info[template_name] = {
                "usage_count": usage_count,
                "avg_token_estimate": stats["token_estimate"],
                "success_rate": success_rate
            }

        return template_info
