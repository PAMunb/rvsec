# rvandroid/uiautomator/uiautomator_main.py

import logging
import argparse
import os
import sys
import time
from typing import Dict, Any

from rvandroid.app import App
from rvandroid.service.llm_uiautomator_service import LLMUIAutomatorService
from rvandroid.model.static import StaticAnalysisData
from rvandroid.parser.static import static_analysis_parser

logger = logging.getLogger(__name__)

def setup_logging():
    """Configure logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('rv_android_uiautomator.log')
        ]
    )

def get_package_name_for_apk(apk_name: str) -> str:
    """
    Get package name for an APK.
    This is a placeholder - implement actual logic to retrieve the package name.
    
    Args:
        apk_name: Name of the APK
        
    Returns:
        Package name for the APK
    """
    # This should be implemented based on how you store/retrieve package names
    # For now, returning a dummy value
    return f"com.example.{apk_name.split('.')[0]}"

def main():
    """Main entry point"""
    setup_logging()
    
    parser = argparse.ArgumentParser(description='RV-Android UIAutomator LLM Tester')
    parser.add_argument('--app-dir', type=str, required=False, help='Directory containing static analysis files')
    parser.add_argument('--apk-name', type=str, required=False, help='Name of the APK')
    parser.add_argument('--model-type', type=str, default='huggingface', help='Type of LLM model to use')
    parser.add_argument('--model-name', type=str, default='Qwen/Qwen2.5-3B-Instruct', help='Name of the model')
    parser.add_argument('--strategy-type', type=str, default='basic', help='Type of prompt strategy')
    parser.add_argument('--device-id', type=str, default='emulator-5554', help='Target device ID')
    parser.add_argument('--duration', type=int, default=3600, help='Test duration in seconds')
    parser.add_argument('--max-actions', type=int, default=1000, help='Maximum number of actions')
    parser.add_argument('--results-dir', type=str, default='results_novo', help='Directory to save results')
    
    args = parser.parse_args()
    
        
    args.apk_name = "cryptoapp.apk"
    args.app_dir = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/"+args.apk_name    
    app = App(os.path.join(args.app_dir, args.apk_name))
    package_name = app.package_name
  
    
    logger.info(f"Starting RV-Android UIAutomator LLM Tester with arguments: {args}")
    
    try:
        # Get package name
        # package_name = get_package_name_for_apk(os.path.join(args.app_dir, args.apk_name))
        
        
        # Load static analysis data
        logger.info(f"Loading static analysis data from {args.app_dir}")
        static_data = static_analysis_parser.read_static_analysis_files(
            args.app_dir, args.apk_name, package_name
        )        
        
        # Initialize service
        logger.info(f"Initializing LLM UIAutomator service")
        service = LLMUIAutomatorService(
            static_data,
            args.model_type,
            args.model_name,
            args.strategy_type,
            args.device_id
        )
        
        # Start testing
        logger.info(f"Starting testing for {args.duration} seconds or {args.max_actions} actions")
        results = service.start_testing(
            args.duration,
            args.max_actions,
            args.results_dir
        )
        
        logger.info(f"Testing completed: {results}")
        
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
        return 1
    
    return 0

# if __name__ == "__main__":
#     sys.exit(main())