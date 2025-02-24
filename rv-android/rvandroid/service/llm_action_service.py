# rvandroid/service/llm_action_service.py
import json
import logging
from typing import Dict, List, Any, Optional

from rvandroid.model.static import StaticAnalysisData
from rvandroid.llm.llm import LanguageModel
from rvandroid.llm.model_factory import ModelFactory
from rvandroid.llm.prompt_strategy import PromptStrategyFactory


class LLMActionService:
    """
    Service that processes DroidBot state, generates prompts, sends them to LLM,
    and returns suggested actions.
    """
    
    def __init__(
            self, 
            static_data: StaticAnalysisData, 
            model_type: str = "huggingface",
            model_name: str = "microsoft/Phi-3.5-mini-instruct",
            strategy_type: str = "basic",
            **model_kwargs
        ):
        """
        Initialize the LLM action service.
        
        Args:
            static_data: Static analysis data for the application
            model_type: Type of model to use ('huggingface', 'ollama', 'langchain', 'dspy')
            model_name: Name of the model
            strategy_type: Type of prompt strategy to use ('basic', 'langchain', 'dspy')
            **model_kwargs: Additional arguments for the model
        """
        self.static_data = static_data
        self.model_type = model_type
        self.model_name = model_name
        self.model_kwargs = model_kwargs
        self.strategy_type = strategy_type
        
        self.prompt_strategy = PromptStrategyFactory.create(strategy_type, static_data)
        self.llm: Optional[LanguageModel] = None
        self.logger = logging.getLogger(__name__)
        
    def _get_llm(self) -> LanguageModel:
        """
        Get (or initialize) the LLM instance.
        
        Returns:
            LanguageModel instance
        """
        if not self.llm:
            self.logger.info(f"Initializing {self.model_type} LLM with model: {self.model_name}")
            self.llm = ModelFactory.create(
                self.model_type, 
                self.model_name, 
                **self.model_kwargs
            )
        return self.llm
    
    def process_state(self, state: Dict) -> List[Dict[str, Any]]:
        """
        Process the current DroidBot state and return suggested actions.
        
        Args:
            state: DroidBot state dictionary
            
        Returns:
            List of action dictionaries
        """
        self.logger.info("Processing DroidBot state")
        
        try:
            # Generate prompts using the selected strategy
            messages = self.prompt_strategy.generate_prompts(state)
            
            self.logger.debug(f"System prompt: {messages[0]['content']}")
            self.logger.debug(f"User prompt: {messages[1]['content']}")
            
            # Call the LLM with the generated prompts
            llm = self._get_llm()
            response = llm.generate(messages)
            
            self.logger.debug(f"LLM response: {response}")
            
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
        """
        # Look for JSON array
        start_idx = text.find('[')
        end_idx = text.rfind(']')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            return text[start_idx:end_idx+1]
        
        # Look for JSON object
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            return text[start_idx:end_idx+1]
            
        raise ValueError("No valid JSON found in response")
    
    def _validate_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate and clean up actions returned by the LLM.
        
        Args:
            actions: List of action dictionaries
            
        Returns:
            Validated list of action dictionaries
        """
        valid_actions = []
        
        for action in actions:
            # Check for required fields
            if 'action_type' not in action or 'target' not in action:
                self.logger.warning(f"Invalid action missing required fields: {action}")
                continue
                
            # Normalize action type
            action_type = action['action_type'].lower()
            if action_type not in ['click', 'long_click', 'scroll', 'set_text', 'key_event']:
                self.logger.warning(f"Invalid action type: {action_type}")
                continue
                
            # Ensure params is a dictionary
            if 'params' not in action or not isinstance(action['params'], dict):
                action['params'] = {}
                
            # Add validated action
            valid_actions.append({
                'action_type': action_type,
                'target': action['target'],
                'params': action['params'],
                'explanation': action.get('explanation', '')
            })
            
        return valid_actions
    
    def _generate_fallback_actions(self, state: Dict) -> List[Dict[str, Any]]:
        """
        Generate fallback actions when LLM response parsing fails.
        
        Args:
            state: DroidBot state dictionary
            
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
    
    def _extract_clickable_elements(self, view: Dict, actions: List[Dict[str, Any]], max_elements: int = 3):
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