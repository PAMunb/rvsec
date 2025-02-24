# rvandroid/main_llm_server.py

import argparse
import logging
import os
import sys

from rvandroid.api.action_endpoint import init_service, start_server
from rvandroid.llm.model_factory import ModelFactory

def setup_logging(log_level: str = 'INFO'):
    """
    Set up logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")
    
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('llm_server.log')
        ]
    )

def main():
    """Main entry point for the LLM server."""
    parser = argparse.ArgumentParser(description='RV-Android LLM Action Server')
    
    parser.add_argument('--app-dir', type=str, required=True,
                        help='Directory containing static analysis files')
    parser.add_argument('--apk-name', type=str, required=True,
                        help='Name of the APK being tested')
    
    # Get available model types and models
    model_types = ModelFactory.get_available_types().keys()
    all_models = {}
    for model_type in model_types:
        all_models[model_type] = ModelFactory.get_available_models(model_type)[model_type]
    
    # Model arguments
    parser.add_argument('--model-type', type=str, default='huggingface',
                        choices=list(model_types),
                        help='Type of model to use')
    parser.add_argument('--model-name', type=str,
                        help='Name of the model to use (default depends on model type)')
    
    # Prompt strategy argument
    parser.add_argument('--strategy', type=str, default='basic',
                        choices=['basic', 'langchain', 'dspy'],
                        help='Prompt strategy to use')
    
    # Server arguments
    parser.add_argument('--host', type=str, default='0.0.0.0',
                        help='Host to listen on')
    parser.add_argument('--port', type=int, default=5000,
                        help='Port to listen on')
    parser.add_argument('--log-level', type=str, default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Logging level')
    
    # LangChain and DSPy specific arguments
    parser.add_argument('--provider', type=str, default='ollama',
                        choices=['ollama', 'huggingface'],
                        help='Model provider for LangChain or DSPy')
    parser.add_argument('--base-url', type=str, default='http://localhost:11434',
                        help='Base URL for Ollama API')
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    try:
        # Set default model name if not provided
        if not args.model_name:
            if args.model_type == 'huggingface':
                args.model_name = 'microsoft/Phi-3.5-mini-instruct'
            elif args.model_type == 'ollama':
                args.model_name = 'llama3.2:3b'
            elif args.model_type == 'langchain':
                args.model_name = 'llama3.2:3b'
            elif args.model_type == 'dspy':
                args.model_name = 'phi3.5:3.8b'
        
        # Log startup information
        logger.info(f"Starting RV-Android LLM Action Server")
        logger.info(f"App directory: {args.app_dir}")
        logger.info(f"APK name: {args.apk_name}")
        logger.info(f"Model type: {args.model_type}")
        logger.info(f"Model name: {args.model_name}")
        logger.info(f"Prompt strategy: {args.strategy}")
        logger.info(f"Host: {args.host}")
        logger.info(f"Port: {args.port}")
        
        # Prepare extra parameters for model initialization
        model_kwargs = {}
        if args.model_type in ['langchain', 'dspy']:
            model_kwargs['provider'] = args.provider
            model_kwargs['base_url'] = args.base_url
        
        # Initialize service
        init_service(
            args.app_dir, 
            args.apk_name, 
            args.model_type,
            args.model_name,
            args.strategy,
            **model_kwargs
        )
        
        # Start server
        logger.info(f"Starting server on {args.host}:{args.port}")
        start_server(args.host, args.port)
        
    except Exception as e:
        logger.error(f"Error starting server: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()