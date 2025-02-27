# rvandroid/service/llm_uiautomator_service.py

import logging
import json
import os
from typing import Dict, Any, List, Optional

from rvandroid.model.static import StaticAnalysisData
from rvandroid.uiautomator.llm_tester import LLMTester

logger = logging.getLogger(__name__)

class LLMUIAutomatorService:
    """
    Service that manages LLM-based testing with UIAutomator.
    This replaces the previous LLMActionService that was used with DroidBot.
    """
    
    def __init__(
            self,
            static_data: StaticAnalysisData,
            model_type: str,
            model_name: str,
            strategy_type: str,
            device_id: str = "emulator-5554",
            **model_kwargs
        ):
        """
        Initialize the LLM UIAutomator service
        
        Args:
            static_data: Static analysis data for the application
            model_type: Type of model to use ('huggingface', 'ollama', etc.)
            model_name: Name of the model
            strategy_type: Type of prompt strategy to use
            device_id: Target device ID
            **model_kwargs: Additional arguments for model initialization
        """
        self.logger = logging.getLogger(__name__)
        self.static_data = static_data
        self.model_type = model_type
        self.model_name = model_name
        self.strategy_type = strategy_type
        self.device_id = device_id
        self.model_kwargs = model_kwargs
        
        self.logger.info(f"Initialized LLM UIAutomator Service with model: {model_name}")
    
    def start_testing(self, 
                     duration_seconds: int = 120, 
                     max_actions: int = 10000000,
                     results_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Start the testing process
        
        Args:
            duration_seconds: Maximum duration in seconds
            max_actions: Maximum number of actions to execute
            results_dir: Directory to save results
            
        Returns:
            Dictionary with testing results
        """
        self.logger.info(f"Starting LLM-based testing for {duration_seconds} seconds or {max_actions} actions")
        
        # Create the tester
        tester = LLMTester(
            self.static_data,
            self.model_type,
            self.model_name,
            self.strategy_type,
            self.device_id,
            max_actions,
            **self.model_kwargs
        )
        
        # Run the testing
        results = tester.run(duration_seconds)
        
        # Save results if directory provided
        if results_dir:
            os.makedirs(results_dir, exist_ok=True)
            results_file = os.path.join(results_dir, "llm_test_results.json")
            
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            self.logger.info(f"Results saved to {results_file}")
        
        return results