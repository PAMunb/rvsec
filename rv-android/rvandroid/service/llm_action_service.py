# rvandroid/service/llm_action_service.py
import json
import logging
from typing import Dict, List, Any, Optional

from rvandroid.config.component_config import ComponentConfig
from rvandroid.llm.llm import LanguageModel
from rvandroid.llm.llm_config import LLMConfiguration
from rvandroid.llm.model_factory import ModelFactory
from rvandroid.llm.prompt_strategy_factory import PromptStrategyFactory
from rvandroid.model.static import StaticAnalysisData
from rvandroid.parser.parser_factory import ParserType, ParserFactory

logger = logging.getLogger(__name__)


class LLMActionService:
    """
    Service that processes application state, generates prompts, sends them to LLM,
    and returns suggested actions.
    """

    def __init__(
            self,
            static_data: Optional[StaticAnalysisData] = None,
            model_type: str = "huggingface",
            model_name: str = "microsoft/Phi-3.5-mini-instruct",
            strategy_type: str = "basic",
            parser_type: ParserType = ParserType.DROIDBOT,
            config: Optional[LLMConfiguration] = None,
            component_config: Optional[ComponentConfig] = None,
            **model_kwargs
    ):
        """
        Initialize the LLM action service.

        Args:
            static_data: Static analysis data for the application (optional)
            model_type: Type of model to use
            model_name: Name of the model
            strategy_type: Type of prompt strategy to use
            parser_type: Type of parser to use
            config: LLMConfiguration instance (overrides other parameters if provided)
            component_config: ComponentConfig for customizing components (optional)
            **model_kwargs: Additional arguments for the model constructor
        """
        self.static_data = static_data
        self.component_config = component_config

        # Use config if provided, otherwise use parameters
        if config:
            self.model_type = config.get_model_type()
            self.model_name = config.get_model_name()
            self.strategy_type = config.get_strategy_type()
            self.parser_type = config.get_parser_type()
            self.model_kwargs = config.get_model_kwargs()
            self.max_tokens = config.get_max_tokens()
        else:
            self.model_type = model_type
            self.model_name = model_name
            self.strategy_type = strategy_type
            self.parser_type = parser_type
            self.model_kwargs = model_kwargs
            self.max_tokens = model_kwargs.pop("max_tokens", 800)

        # Set up prompt strategy with custom component config if provided
        if self.component_config:
            self.prompt_strategy = PromptStrategyFactory.create(
                self.strategy_type, self.static_data, parser_type, self.component_config)
        else:
            parser = ParserFactory.create(parser_type)
            self.prompt_strategy = PromptStrategyFactory.create(
                self.strategy_type, self.static_data, parser)

        # Initialize logger but defer LLM initialization until needed
        self.llm: Optional[LanguageModel] = None
        self.logger = logger

        self.logger.info(f"Initialized LLM Action Service with model_type={self.model_type}, "
                         f"model_name={self.model_name}, strategy_type={self.strategy_type}, "
                         f"parser_type={self.parser_type}")

    def _get_llm(self) -> LanguageModel:
        """
        Get (or initialize) the LLM instance.

        Returns:
            LanguageModel instance

        Raises:
            RuntimeError: If LLM initialization fails
        """
        if not self.llm:
            self.logger.info(f"Initializing {self.model_type} LLM with model: {self.model_name}")
            try:
                self.llm = ModelFactory.create(
                    self.model_type,
                    self.model_name,
                    **self.model_kwargs
                )
                self.logger.info(f"Successfully initialized {self.model_type} model")
            except Exception as e:
                self.logger.error(f"Failed to initialize LLM: {e}", exc_info=True)
                raise RuntimeError(f"Could not initialize {self.model_type} model: {str(e)}")

        return self.llm

    def process_state(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process the current application state and return suggested actions.

        Args:
            state: Application state dictionary

        Returns:
            List of action dictionaries

        Raises:
            Exception: If processing fails
        """
        self.logger.info("Processing application state")

        try:
            # Generate prompts using the selected strategy
            messages = self.prompt_strategy.generate_prompts(state)

            self.logger.debug(f"System prompt: {messages[0]['content'][:200]}...")
            self.logger.debug(f"User prompt: {messages[1]['content'][:200]}...")

            # Call the LLM with the generated prompts
            llm = self._get_llm()
            response = llm.generate(messages, max_new_tokens=self.max_tokens)

            self.logger.debug(f"LLM response: {response[:200]}...")

            # Parse the response
            json_response = self._extract_json(response)
            actions = json.loads(json_response)

            # Validate actions
            validated_actions = self._validate_actions(actions)

            self.logger.info(f"Successfully processed state and generated {len(validated_actions)} actions")
            return validated_actions

        except Exception as e:
            self.logger.error(f"Error processing state: {e}", exc_info=True)
            return self._generate_fallback_actions(state)

    def _extract_json(self, text: str) -> str:
        """
        Extract JSON content from text that might contain other content.

        Args:
            text: Text potentially containing JSON

        Returns:
            Extracted JSON string

        Raises:
            ValueError: If no valid JSON can be extracted
        """
        # Look for JSON array
        start_idx = text.find('[')
        end_idx = text.rfind(']')

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_text = text[start_idx:end_idx + 1]
            # Validate that it can be parsed
            try:
                json.loads(json_text)
                return json_text
            except json.JSONDecodeError:
                self.logger.warning("Found array brackets but content isn't valid JSON")

        # Look for JSON object
        start_idx = text.find('{')
        end_idx = text.rfind('}')

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_text = text[start_idx:end_idx + 1]
            try:
                json.loads(json_text)
                return json_text
            except json.JSONDecodeError:
                self.logger.warning("Found object braces but content isn't valid JSON")

        # If we get here, we need to do more aggressive fixing
        # Try to fix common JSON issues
        fixed_text = self._fix_json_text(text)
        if fixed_text:
            return fixed_text

        raise ValueError("No valid JSON found in response")

    def _extract_json(self, text: str) -> str:
        """
        Extract JSON content from text that might contain other content.

        Args:
            text: Text potentially containing JSON

        Returns:
            Extracted JSON string

        Raises:
            ValueError: If no valid JSON can be extracted
        """
        # Look for JSON array
        start_idx = text.find('[')
        end_idx = text.rfind(']')

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_text = text[start_idx:end_idx + 1]
            # Validate that it can be parsed
            try:
                json.loads(json_text)
                return json_text
            except json.JSONDecodeError:
                self.logger.warning("Found array brackets but content isn't valid JSON")

        # Look for JSON object
        start_idx = text.find('{')
        end_idx = text.rfind('}')

        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_text = text[start_idx:end_idx + 1]
            try:
                json.loads(json_text)
                return json_text
            except json.JSONDecodeError:
                self.logger.warning("Found object braces but content isn't valid JSON")

        # If we get here, we need to do more aggressive fixing
        # Try to fix common JSON issues
        fixed_text = self._fix_json_text(text)
        if fixed_text:
            return fixed_text

        raise ValueError("No valid JSON found in response")

    def _fix_json_text(self, text: str) -> str:
        """
        Attempt to fix common JSON formatting issues.

        Args:
            text: Text containing malformed JSON

        Returns:
            Fixed JSON string or empty string if unfixable
        """
        import re

        # Look for JSON-like content
        match = re.search(r'\[\s*\{.*\}\s*\]', text, re.DOTALL)
        if match:
            json_candidate = match.group(0)

            # Try to parse it
            try:
                json.loads(json_candidate)
                return json_candidate
            except json.JSONDecodeError:
                # Still invalid, but we found something JSON-like
                pass

        # More aggressive: extract anything between [ and ] and try to fix it
        if '[' in text and ']' in text:
            start = text.find('[')
            end = text.rfind(']')
            if start < end:
                json_candidate = text[start:end + 1]

                # Common fixes:
                # Fix single quotes to double quotes
                json_candidate = json_candidate.replace("'", '"')
                # Fix unquoted keys
                json_candidate = re.sub(r'(\w+):', r'"\1":', json_candidate)

                try:
                    json.loads(json_candidate)
                    return json_candidate
                except json.JSONDecodeError:
                    pass

        return ""

    def _validate_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate and clean up actions returned by the LLM.

        Args:
            actions: List of action dictionaries

        Returns:
            Validated list of action dictionaries
        """
        valid_actions = []

        # Ensure actions is a list
        if not isinstance(actions, list):
            self.logger.warning(f"Expected list of actions but got: {type(actions)}")
            if isinstance(actions, dict):
                # Single action as a dict - convert to list
                actions = [actions]
            else:
                return valid_actions
        valid_action_types = {'click', 'long_click', 'scroll', 'set_text', 'key_event'}

        for i, action in enumerate(actions):
            if not isinstance(action, dict):
                self.logger.warning(f"Invalid action format at index {i}: {action}")
                continue

            # Check for required fields
            if 'action_type' not in action or 'target' not in action:
                self.logger.warning(f"Invalid action missing required fields at index {i}: {action}")
                continue

            # Normalize action type
            action_type = action['action_type'].lower()
            if action_type not in valid_action_types:
                self.logger.warning(f"Invalid action type at index {i}: {action_type}")
                continue

            # Ensure params is a dictionary
            if 'params' not in action or not isinstance(action['params'], dict):
                action['params'] = {}

            # Add explanation if missing
            if 'explanation' not in action or not action['explanation']:
                action['explanation'] = f"Executing {action_type} on {action['target']}"

            # Add validated action
            valid_actions.append({
                'action_type': action_type,
                'target': action['target'],
                'params': action['params'],
                'explanation': action.get('explanation', '')
            })

        return valid_actions

    def _generate_fallback_actions(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate fallback actions when LLM response parsing fails.

        Args:
            state: Application state dictionary

        Returns:
            List of fallback action dictionaries
        """
        self.logger.info("Generating fallback actions")

        fallback_actions = []

        # Try to find some interactive elements
        if 'view_tree' in state:
            self._extract_clickable_elements(state['view_tree'], fallback_actions)

        # If no elements found, add a random scroll action
        if not fallback_actions:
            fallback_actions.append({
                'action_type': 'scroll',
                'target': '',
                'params': {'direction': 'DOWN'},
                'explanation': 'Fallback scroll action'
            })

        return fallback_actions

    def _extract_clickable_elements(self, view: Dict[str, Any], actions: List[Dict[str, Any]], max_elements: int = 3):
        """
        Extract clickable elements from view tree for fallback actions.

        Args:
            view: View tree dictionary
            actions: List to append actions to
            max_elements: Maximum number of elements to extract
        """
        # Check if this view is clickable
        if (len(actions) < max_elements and
                view.get('clickable', False) and
                view.get('enabled', True) and
                view.get('visible', True)):

            target = view.get('resource_id', '')
            if not target and 'bounds' in view:
                # If no resource_id, use center of bounds
                bounds = view['bounds']
                x = (bounds[0][0] + bounds[1][0]) // 2
                y = (bounds[0][1] + bounds[1][1]) // 2
                target = f"{x} {y}"

            if target:
                actions.append({
                    'action_type': 'click',
                    'target': target,
                    'params': {},
                    'explanation': 'Fallback click on visible element'
                })

        # Recursively process children
        for child in view.get('children', []):
            if len(actions) >= max_elements:
                break
            self._extract_clickable_elements(child, actions, max_elements)

    def cleanup(self):
        """
        Clean up resources used by the service.
        """
        if self.llm:
            try:
                self.llm.clean()
                self.llm = None
                self.logger.info("Cleaned up LLM resources")
            except Exception as e:
                self.logger.warning(f"Error cleaning up LLM: {e}")
