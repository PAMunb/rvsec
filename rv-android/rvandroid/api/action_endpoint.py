# rvandroid/api/action_endpoint.py

import json
import logging
from typing import Dict, Any

from flask import Flask, request, jsonify
from rvandroid.service.llm_action_service import LLMActionService
from rvandroid.model.static import StaticAnalysisData
from rvandroid.parser.static import static_analysis_parser

app = Flask(__name__)
logger = logging.getLogger(__name__)

# Global service instance to be initialized
action_service = None

@app.route('/api/get_actions', methods=['POST'])
def get_actions():
    """
    Endpoint to receive DroidBot state and return suggested actions.
    """
    try:
        # Get JSON data from request
        data = request.json
        if not data:
            return jsonify({"error": "No state data provided"}), 400
            
        logger.info(f"Received request for app: {data.get('package_name')}")
        
        # Ensure service is initialized
        if not action_service:
            return jsonify({"error": "Service not initialized"}), 500
            
        # Process state and get actions
        actions = action_service.process_state(data)
        
        # Return response
        return jsonify({
            "actions": actions,
            "status": "success"
        })
        
    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

def init_service(
        app_dir: str, 
        apk_name: str, 
        model_type: str,
        model_name: str,
        strategy_type: str,
        **model_kwargs
    ):
    """
    Initialize the action service with static analysis data.
    
    Args:
        app_dir: Directory containing static analysis files
        apk_name: Name of the APK
        model_type: Type of model to use
        model_name: Name of the model to use
        strategy_type: Type of prompt strategy to use
        **model_kwargs: Additional arguments for model initialization
    """
    global action_service
    
    logger.info(f"Initializing service for app: {apk_name}")
    
    try:
        # Load static analysis data
        package_name = get_package_name_for_apk(apk_name)
        classes, windows, wtg = static_analysis_parser.read_static_analysis_files(
            app_dir, apk_name, package_name
        )
        
        static_data = StaticAnalysisData(classes, windows, wtg)
        
        # Initialize service
        action_service = LLMActionService(
            static_data, 
            model_type, 
            model_name,
            strategy_type,
            **model_kwargs
        )
        
        logger.info("Service initialization complete")
        
    except Exception as e:
        logger.error(f"Error initializing service: {e}", exc_info=True)
        raise

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

def start_server(host: str = '0.0.0.0', port: int = 5000):
    """
    Start the Flask server.
    
    Args:
        host: Host to listen on
        port: Port to listen on
    """
    app.run(host=host, port=port)