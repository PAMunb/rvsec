import time
from threading import Thread, Lock
from typing import Optional, Dict, Any

import requests
from flask import Flask, request, jsonify
from werkzeug.exceptions import NotFound, HTTPException
from werkzeug.serving import make_server

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
            Uses the refactored LLMActionService to process state and generate actions.
            """
            try:
                # Get JSON data from request
                data = request.json
                if not data:
                    self.logger.info("No data provided in the request.")
                    return jsonify({"error": "No state data provided"}), 400

                self.logger.info(f"Received request for app: {data.get('package_name')}")

                # Add request timestamp and handling info
                self.logger.debug(f"State has activity: {data.get('activity')}")
                self.logger.debug(f"Processing request at {time.strftime('%Y-%m-%d %H:%M:%S')}")

                # Ensure service is initialized
                if not self.service:
                    self.logger.warning("Service not initialized")
                    return jsonify({"error": "Service not initialized"}), 500

                # Process state and get actions
                actions = self.service.process_state(data)

                # Create response with metadata
                response_data = {
                    "actions": actions,
                    "status": "success"
                }

                response = jsonify(response_data)
                self.logger.info(f"Returning {len(actions)} actions")

                # Return response
                return response

            except Exception as e:
                self.logger.error(f"Error processing request: {e}", exc_info=True)
                return jsonify({"error": str(e)}), 500

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
