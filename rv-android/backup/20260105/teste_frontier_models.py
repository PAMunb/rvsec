# examples/test_frontier_models.py

import os
import logging
import json
from typing import Dict, Any

from rvandroid.config.llm_config import LLMConfiguration
from rvandroid.model.static import StaticAnalysisData
from rvandroid.service.llm_action_service import LLMActionService
from rvandroid.parser.static import static_analysis_parser

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_sample_state(file_path: str) -> Dict[str, Any]:
    """
    Load a sample DroidBot state from a JSON file.
    
    Args:
        file_path: Path to JSON file
        
    Returns:
        DroidBot state dictionary
    """
    with open(file_path, 'r') as f:
        return json.load(f)

def run_test(config_name: str, state_file: str, app_dir: str, apk_name: str):
    """
    Run a test with a specific configuration.
    
    Args:
        config_name: Name of predefined configuration
        state_file: Path to sample state file
        app_dir: Directory containing static analysis files
        apk_name: Name of the APK
    """
    logger.info(f"Running test with configuration: {config_name}")
    
    # Create configuration
    from rvandroid.llm.llm_config import get_predefined_config
    config_dict = get_predefined_config(config_name)
    config = LLMConfiguration()
    config.update(**config_dict)
    
    logger.info(f"Using configuration: {config}")
    
    # Load static analysis data
    package_name = f"com.example.{apk_name.split('.')[0]}"
    classes, windows, wtg = static_analysis_parser.read_static_analysis_files(
        app_dir, apk_name, package_name
    )
    static_data = StaticAnalysisData(classes, windows, wtg)
    
    # Create service
    service = LLMActionService(static_data, config=config)
    
    # Load state
    state = load_sample_state(state_file)
    
    # Process state
    logger.info("Processing state...")
    actions = service.process_state(state)
    
    # Print results
    logger.info(f"Generated {len(actions)} actions:")
    for i, action in enumerate(actions):
        logger.info(f"Action {i+1}:")
        logger.info(f"  Type: {action['action_type']}")
        logger.info(f"  Target: {action['target']}")
        logger.info(f"  Params: {action['params']}")
        logger.info(f"  Explanation: {action['explanation']}")
    
    logger.info("Test completed successfully")

if __name__ == "__main__":
    # Set API keys from environment variables
    # You should set these in your environment or use the llm_selector tool
    # os.environ["ANTHROPIC_API_KEY"] = "your-api-key"
    # os.environ["OPENAI_API_KEY"] = "your-api-key"
    # os.environ["GOOGLE_API_KEY"] = "your-api-key"
    
    # Replace these with actual paths
    app_dir = "path/to/app/dir"
    apk_name = "example.apk"
    state_file = "path/to/sample_state.json"
    
    # Test with different configurations
    run_test("local", state_file, app_dir, apk_name)
    # run_test("claude", state_file, app_dir, apk_name)
    # run_test("gpt", state_file, app_dir, apk_name)
    # run_test("gemini", state_file, app_dir, apk_name)