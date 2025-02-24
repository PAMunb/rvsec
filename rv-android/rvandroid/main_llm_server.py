# rvandroid/main_llm_server.py

import argparse
import logging
import os
import sys

from rvandroid.api.action_endpoint import init_service, start_server
from rvandroid.llm.huggingface import HuggingFaceLLM

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
    parser.add_argument('--model', type=str, default=HuggingFaceLLM.PHI,
                        choices=HuggingFaceLLM.models(),
                        help='HuggingFace model to use')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                        help='Host to listen on')
    parser.add_argument('--port', type=int, default=5000,
                        help='Port to listen on')
    parser.add_argument('--log-level', type=str, default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Logging level')
    
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    try:
        # Log startup information
        logger.info(f"Starting RV-Android LLM Action Server")
        logger.info(f"App directory: {args.app_dir}")
        logger.info(f"APK name: {args.apk_name}")
        logger.info(f"Model: {args.model}")
        logger.info(f"Host: {args.host}")
        logger.info(f"Port: {args.port}")
        
        # Initialize service
        init_service(args.app_dir, args.apk_name, args.model)
        
        # Start server
        logger.info(f"Starting server on {args.host}:{args.port}")
        start_server(args.host, args.port)
        
    except Exception as e:
        logger.error(f"Error starting server: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()