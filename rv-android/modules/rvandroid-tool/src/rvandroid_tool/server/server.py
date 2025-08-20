import os
import tempfile
import time
import uuid
from threading import Thread, Lock
from typing import Optional, Dict, Any

import requests
from flask import Flask, request, jsonify
from werkzeug.exceptions import NotFound, HTTPException
from werkzeug.serving import make_server
from werkzeug.datastructures import FileStorage

from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rvandroid_tool.llm.service.action_service import LLMActionService


class Server:
    """
    A resilient and flexible REST server implementation designed for integrating AI-driven test automation.

    ### Architectural Decisions:
    - Implements a robust, thread-safe REST server using Flask
    - Provides a non-blocking, event-driven server architecture
    - Supports graceful startup, shutdown, and error recovery mechanisms
    - Enables dynamic service configuration and endpoint management

    ### Role in the System:
    - Acts as the primary communication interface for AI-driven test automation
    - Provides endpoints for receiving application state and returning suggested actions
    - Manages the lifecycle of AI service interactions
    - Supports real-time communication between testing tools and AI action generation
    - Enables centralized coordination of test automation workflows

    ### Key Considerations:
    - Implements comprehensive error handling and recovery strategies
    - Supports configurable server parameters (host, port, retry mechanisms)
    - Provides health check and status monitoring capabilities
    - Manages server thread lifecycle with thread-safe mechanisms
    - Ensures reliable communication between testing components

    ### Integration Strategy:
    - Deeply integrated with LLM action service and testing frameworks
    - Compatible with various testing tools and automation platforms
    - Supports dynamic endpoint configuration
    - Enables flexible service initialization and shutdown
    - Provides standardized communication protocols for test automation

    ### Performance and Scalability:
    - Designed for low-latency, high-throughput service interactions
    - Implements automatic retry and recovery mechanisms
    - Supports concurrent request handling
    - Minimizes resource overhead during server operations
    - Adaptable to different testing complexity and scale requirements
    """

    def __init__(self, service: LLMActionService, host: str = 'localhost', port: int = 5000,
                 max_retries: int = 3, retry_delay: float = 5.0):
        self.service = service
        # Basic configuration
        self.host = host
        self.port = port
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        # Initialize Flask app
        self.app = Flask(__name__)

        # Server state management
        self._server_thread: Optional[Thread] = None
        self._server_instance = None
        self._is_running = False
        self._should_stop = False
        self._lock = Lock()

        # Setup logging
        self.logging_manager = LoggingManager.get_instance()
        self.logger = self.logging_manager.get_logger(
            'rvandroid_tool.server',
            {CONTEXT_COMPONENT: 'Server'}
        )
        # TODO usar error handler (de exceptions) modules/rv-android-core/src/rv_android_core/util/error/error_handler.py

        # Initialize routes and error handlers
        self._setup_error_handlers()
        self._setup_routes()

        # Error stats
        self._error_count = 0
        self._last_error_time = None
        self._status: Dict[str, Any] = {
            "start_time": None,
            "restart_count": 0,
            "last_error": None
        }

    def _setup_error_handlers(self) -> None:
        """Configure error handlers"""

        @self.app.errorhandler(NotFound)
        def handle_404(error):
            """Handle 404 errors separately"""
            if request.path == '/favicon.ico':
                return '', 404  # Silently handle favicon requests
            return jsonify({"error": "Resource not found"}), 404

        @self.app.errorhandler(HTTPException)
        def handle_http_error(error):
            """Handle HTTP errors"""
            return jsonify({"error": str(error.description)}), error.code

        @self.app.errorhandler(Exception)
        def handle_error(error):
            """Handle all other exceptions"""
            if isinstance(error, HTTPException):
                return handle_http_error(error)

            self._error_count += 1
            self._last_error_time = time.time()
            self._status["last_error"] = str(error)
            self.logger.error(f"Unexpected error occurred: {error}", exc_info=True)
            return jsonify({"error": "Internal server error"}), 500

    def _setup_routes(self) -> None:
        """Configure all REST endpoints"""

        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            return jsonify({
                "status": "healthy",
                "uptime": time.time() - self._status["start_time"] if self._status["start_time"] else 0,
                "stats": self._status
            })

        @self.app.route('/api/get_actions', methods=['POST'])
        def get_actions():
            """
            Endpoint to receive application state and return suggested actions.
            
            Supports both JSON and multipart requests with screenshot files.
            Screenshots are temporarily saved, processed by LLM, then cleaned up.
            """
            screenshot_path = None
            try:
                # Handle different request types
                if request.is_json:
                    # JSON request without screenshot
                    data = request.json
                    if not data:
                        self.logger.info("No data provided in the request.")
                        return jsonify({"error": "No state data provided"}), 400
                elif request.content_type and 'multipart/form-data' in request.content_type:
                    # Multipart request with potential screenshot
                    self.logger.debug("Processing multipart/form-data request")
                    try:
                        # Check if state data is in form field
                        if 'state' in request.form:
                            import json
                            state_json = request.form['state']
                            self.logger.debug(f"Found state in form field, length: {len(state_json)}")
                            data = json.loads(state_json)
                        else:
                            self.logger.error("No 'state' field found in multipart form data")
                            return jsonify({"error": "No state data provided in form"}), 400
                        
                        if not data:
                            self.logger.error("Parsed state data is empty")
                            return jsonify({"error": "State data is empty"}), 400
                            
                    except json.JSONDecodeError as json_error:
                        self.logger.error(f"Invalid JSON in state field: {json_error}")
                        return jsonify({"error": f"Invalid JSON format: {str(json_error)}"}), 400
                    except Exception as e:
                        self.logger.error(f"Failed to parse multipart state data: {e}")
                        return jsonify({"error": "Failed to parse multipart request"}), 400
                else:
                    return jsonify({"error": "Unsupported content type"}), 400

                self.logger.info(f"Received request for app: {data.get('package_name')}")
                self.logger.debug(f"State has activity: {data.get('activity')}")
                self.logger.debug(f"Processing request at {time.strftime('%Y-%m-%d %H:%M:%S')}")

                # Handle screenshot if present
                if 'screenshot' in request.files:
                    screenshot_file = request.files['screenshot']
                    if screenshot_file and screenshot_file.filename:
                        screenshot_path = self._save_screenshot_to_temp(screenshot_file)
                        if screenshot_path:
                            data['screenshot_path'] = screenshot_path
                            self.logger.debug(f"Screenshot saved to: {screenshot_path}")

                # Ensure service is initialized
                if not self.service:
                    self.logger.warning("Service not initialized")
                    return jsonify({"error": "Service not initialized"}), 500

                # Process state and get actions with fallback
                try:
                    actions = self.service.process_state(data)
                    status = "success"
                    self.logger.info(f"LLM service generated {len(actions)} actions")
                except Exception as e:
                    self.logger.warning(f"LLM processing failed: {e}, using fallback actions")
                    # Generate fallback actions when LLM processing fails
                    actions = self._generate_fallback_actions(data)
                    status = "fallback"
                
                # Ensure actions is never None
                if actions is None:
                    self.logger.warning("Actions is None, generating emergency fallback")
                    actions = self._generate_emergency_fallback()
                    status = "emergency_fallback"

                # Log action details for debugging
                if actions:
                    for i, action in enumerate(actions):
                        self.logger.debug(f"Action {i}: {action}")

                # Create response with metadata
                response_data = {
                    "actions": actions,
                    "status": status
                }

                response = jsonify(response_data)
                self.logger.info(f"Returning {len(actions)} actions with status: {status}")

                # Return response
                return response

            except Exception as e:
                self.logger.error(f"Error processing request: {e}", exc_info=True)
                return jsonify({"error": str(e)}), 500
            finally:
                # Cleanup temporary screenshot file
                if screenshot_path and os.path.exists(screenshot_path):
                    try:
                        os.remove(screenshot_path)
                        self.logger.debug(f"Cleaned up temporary screenshot: {screenshot_path}")
                    except Exception as cleanup_error:
                        self.logger.warning(f"Failed to cleanup screenshot {screenshot_path}: {cleanup_error}")

    def start(self) -> bool:
        """
        Start the server in a separate thread.
        
        Returns:
            bool: True if server started successfully, False otherwise
        """
        with self._lock:
            if self._is_running:
                self.logger.warning("Server is already running")
                return True

            try:
                self._should_stop = False
                self._server_thread = Thread(target=self._run_server_with_recovery)
                self._server_thread.daemon = True
                self._server_thread.start()
                self._status["start_time"] = time.time()
                self._is_running = True
                self.logger.info(f"Server started successfully on http://{self.host}:{self.port}")
                return True
            except Exception as e:
                self.logger.error(f"Failed to start server: {e}", exc_info=True)
                self._is_running = False
                return False

    def _run_server_with_recovery(self) -> None:
        """
        Run server with automatic recovery on failures.
        Implements retry logic and graceful error handling.
        """
        retry_count = 0

        while not self._should_stop and retry_count < self.max_retries:
            try:
                self._server_instance = make_server(self.host, self.port, self.app)
                self._server_instance.serve_forever()
            except Exception as e:
                retry_count += 1
                self._status["restart_count"] += 1
                self.logger.error(f"Server error (attempt {retry_count}/{self.max_retries}): {e}", exc_info=True)

                if retry_count < self.max_retries and not self._should_stop:
                    self.logger.info(f"Attempting restart in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    self.logger.critical("Server failed to recover after maximum retries")
                    break

    def _generate_fallback_actions(self, state_data: dict) -> list:
        """Generate fallback actions when LLM processing fails."""
        try:
            # Try to use ActionGenerator directly for fallback
            if self.service and hasattr(self.service, 'action_generator'):
                fallback_actions = self.service.action_generator.generate_fallback_actions(state_data)
                return [action.to_droidbot_format() for action in fallback_actions]
        except Exception as e:
            self.logger.warning(f"ActionGenerator fallback failed: {e}")
        
        # If ActionGenerator fails, generate simple fallback
        return self._generate_emergency_fallback()
    
    def _generate_emergency_fallback(self) -> list:
        """Generate basic emergency fallback actions."""
        return [{
            "event_type": "scroll",
            "direction": "down",
            "view": {
                "x": 540,
                "y": 960,
                "width": 100,
                "height": 100
            }
        }]

    def stop(self) -> bool:
        """
        Stop the server gracefully.
        
        Returns:
            bool: True if server stopped successfully, False otherwise
        """
        with self._lock:
            if not self._is_running:
                return True

            try:
                self._should_stop = True
                if self._server_instance:
                    self._server_instance.shutdown()
                    self._server_instance = None

                if self._server_thread:
                    self._server_thread.join(timeout=5.0)
                    self._server_thread = None

                # Clean up service resources if available
                if self.service and hasattr(self.service, 'model') and hasattr(self.service.model, 'cleanup'):
                    try:
                        self.logger.info("Cleaning up LLM resources")
                        self.service.model.cleanup()
                    except Exception as cleanup_error:
                        self.logger.warning(f"Error during LLM cleanup: {cleanup_error}")

                self._is_running = False
                self.logger.info("Server stopped successfully")
                return True
            except Exception as e:
                self.logger.error(f"Error stopping server: {e}", exc_info=True)
                return False

    def is_running(self) -> bool:
        """
        Check if the server is currently running.
        
        Returns:
            bool: True if server is running, False otherwise
        """
        return self._is_running

    def is_healthy(self) -> bool:
        """
        Check if the server is healthy.
        
        Returns:
            bool: True if server is running and healthy
        """
        try:
            response = requests.get(f"http://{self.host}:{self.port}/health")
            return response.status_code == 200
        except:
            return False

    def _save_screenshot_to_temp(self, screenshot_file: FileStorage) -> Optional[str]:
        """
        Save uploaded screenshot file to temporary directory.
        
        ### Screenshot Processing Strategy:
        - Creates unique temporary file with proper extension
        - Saves screenshot data to temporary location  
        - Returns file path for processing by StateEnricher
        - File will be cleaned up after LLM processing completes
        
        Args:
            screenshot_file: FileStorage object containing screenshot data
            
        Returns:
            Path to temporary screenshot file or None if save failed
        """
        try:
            # Generate unique temporary filename
            file_extension = '.png'  # Default to PNG
            if screenshot_file.filename:
                # Extract extension from original filename
                _, ext = os.path.splitext(screenshot_file.filename)
                if ext.lower() in ['.png', '.jpg', '.jpeg']:
                    file_extension = ext.lower()
            
            # Create temporary file with unique name
            temp_filename = f"rvandroid_screenshot_{uuid.uuid4().hex}{file_extension}"
            temp_path = os.path.join(tempfile.gettempdir(), temp_filename)
            
            # Save screenshot data to temporary file
            screenshot_file.save(temp_path)
            
            self.logger.debug(f"Screenshot saved to temporary file: {temp_path}")
            return temp_path
            
        except Exception as e:
            self.logger.error(f"Failed to save screenshot to temporary file: {e}")
            return None
