import logging
import time
from threading import Thread, Lock
from typing import Optional, Dict, Any

import requests
from flask import Flask, request, jsonify
from werkzeug.exceptions import NotFound, HTTPException
from werkzeug.serving import make_server

from rvandroid.llm.service.action_service import LLMActionService


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
        self._setup_logging()

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

    def _setup_logging(self) -> None:
        """Configure server logging"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        # Silence Werkzeug logs
        werkzeug_logger = logging.getLogger('werkzeug')
        werkzeug_logger.setLevel(logging.ERROR)  # ou logging.WARNING

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
            print("**************************** GENERATING ACTIONS ****************************")
            try:
                # Get JSON data from request
                data = request.json
                if not data:
                    self.logger.info("No data provided in the request.")
                    return jsonify({"error": "No state data provided"}), 400

                self.logger.info(f"Received request for app: {data.get('package_name')}")
                print(f"********************* DATA: {data}")

                # Add request timestamp and handling info
                self.logger.debug(f"State has activity: {data.get('activity')}")
                self.logger.debug(f"Processing request at {time.strftime('%Y-%m-%d %H:%M:%S')}")

                # Ensure service is initialized
                if not self.service:
                    self.logger.warning("Service not initialized")
                    return jsonify({"error": "Service not initialized"}), 500

                # Process state and get actions
                actions = self.service.process_state(data)

                # Validate actions format for DroidBot compatibility
                validated_actions = self.validate_actions_for_droidbot(actions)
                
                # Get strategy type and additional metadata
                strategy_type = self.service.get_current_strategy_type()
                # TODO nao acho que faz aqui ... e sim no enricher e bota no state
                pattern_info = self.service.get_detected_pattern_info() if hasattr(self.service, 'get_detected_pattern_info') else None
                
                # Create response with metadata
                response_data = {
                    "actions": validated_actions,
                    "status": "success",
                    "strategy_type": strategy_type
                }
                
                # Add batch metadata if multiple actions are returned
                # IMPROVED LOGIC: Consider ANY multiple actions as a batch operation
                # TODO nao precisa de nenhum tratamento especial ... todas as estrategias devem ser tratadas iguais
                if len(validated_actions) > 1:
                    # Always set strategy_type to batch when returning multiple actions
                    response_data["strategy_type"] = "flow_based_batch_action"
                    
                    # Generate a batch ID if not already present
                    import uuid
                    batch_id = f"batch_{uuid.uuid4().hex[:8]}"
                    response_data["batch_id"] = batch_id
                    
                    # Add pattern metadata if available
                    if pattern_info:
                        pattern_type = pattern_info.get("type", "unknown")
                        # Convert to uppercase if needed to match LLM format
                        if isinstance(pattern_type, str) and pattern_type.islower():
                            pattern_type = pattern_type.upper()
                        response_data["pattern_type"] = pattern_type
                        response_data["pattern_confidence"] = pattern_info.get("confidence", 0.5)
                    else:
                        # Use a default FORM pattern type if no specific pattern detected
                        response_data["pattern_type"] = "FORM"
                        response_data["pattern_confidence"] = 0.7
                        
                    # Log that we're treating this as a batch operation
                    self.logger.info(f"Sending {len(validated_actions)} actions as a batch operation")
                
                response = jsonify(response_data)
                self.logger.info(f"Returning {len(validated_actions)} actions with strategy_type={strategy_type}")

                # Return response
                return response

            except Exception as e:
                self.logger.error(f"Error processing request: {e}", exc_info=True)
                return jsonify({"error": str(e)}), 500

        # TODO deprecated
        @self.app.route('/api/report_batch_error', methods=['POST'])
        def report_batch_error():
            """
            Endpoint to receive batch action execution error reports.
            Used by DroidBot to report errors in batch action execution.
            """
            try:
                # Get JSON data from request
                data = request.json
                if not data:
                    return jsonify({"error": "No error data provided"}), 400
                    
                # Log the error
                batch_id = data.get("batch_id", "unknown")
                action_index = data.get("action_index", -1)
                error_message = data.get("error_message", "Unknown error")
                error_type = data.get("error_type", "Unknown")
                
                self.logger.warning(f"Batch action error reported: " +
                              f"batch_id={batch_id}, action_index={action_index}, " +
                              f"error_type={error_type}, message={error_message}")
                
                # Forward error to the service if it has a batch error handler
                if hasattr(self.service, 'handle_batch_action_error') and callable(getattr(self.service, 'handle_batch_action_error')):
                    self.service.handle_batch_action_error(data)
                
                return jsonify({"status": "error_reported"})
                
            except Exception as e:
                self.logger.error(f"Error processing batch error report: {e}", exc_info=True)
                return jsonify({"error": str(e)}), 500

        # TODO deprecated
        @self.app.route('/api/report_batch_result', methods=['POST'])
        def report_batch_result():
            """
            Endpoint to receive batch action execution results.
            Used by DroidBot to report overall batch execution status.
            """
            try:
                # Get JSON data from request
                data = request.json
                if not data:
                    return jsonify({"error": "No result data provided"}), 400
                    
                # Log the result
                batch_id = data.get("batch_id", "unknown")
                total_actions = data.get("total_actions", 0)
                executed_actions = data.get("executed_actions", 0)
                success_rate = data.get("success_rate", 0)
                strategy_type = data.get("strategy_type", "unknown")
                pattern_type = data.get("pattern_type", "unknown")
                
                self.logger.info(f"Batch result reported: " +
                           f"batch_id={batch_id}, executed={executed_actions}/{total_actions}, " +
                           f"success_rate={success_rate:.2f}, pattern_type={pattern_type}")
                
                # Forward result to the service if it has a batch result handler
                if hasattr(self.service, 'handle_batch_execution_result') and callable(getattr(self.service, 'handle_batch_execution_result')):
                    self.service.handle_batch_execution_result(data)
                
                return jsonify({"status": "result_recorded"})
                
            except Exception as e:
                self.logger.error(f"Error processing batch result report: {e}", exc_info=True)
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

    # TODO rever ... nao acho que deva ser feito aqui ... no service acho q ja tem um tratamento e se nao tiver deve ser levado para la
    def validate_actions_for_droidbot(self, actions):
        """
        Ensure actions are in the format expected by DroidBot
        """
        validated = []
        valid_types = {"click", "long_click", "scroll_up", "scroll_down",
                       "scroll_left", "scroll_right", "scroll", "set_text", "key_event"}

        for action in actions:
            # Ensure required fields
            if "action_type" not in action or not isinstance(action["action_type"], str):
                continue

            action_type = action["action_type"].lower()

            # Validate action type
            if action_type not in valid_types:
                self.logger.warning(f"Invalid action type: {action_type}")
                continue

            # Ensure target is present for view-based actions
            if action_type not in ["key_event"] and "target" not in action:
                self.logger.warning(f"Missing target for action: {action_type}")
                continue

            # Validate params
            if "params" not in action or not isinstance(action["params"], dict):
                action["params"] = {}

            # Add explanation if missing
            if "explanation" not in action or not action["explanation"]:
                action["explanation"] = f"Executing {action_type}"

            # Ensure coordinates are included for UI interactions
            if action_type not in ["key_event"] and "coordinates" not in action:
                # Try to extract coordinates from target if possible
                if "target" in action and isinstance(action["target"], str):
                    target = action["target"]
                    # Check if target is in format "x y"
                    if " " in target and all(part.isdigit() for part in target.split()):
                        x, y = map(int, target.split())
                        action["coordinates"] = (x, y)

            validated.append(action)

        return validated


# Example of how to use the Server class
if __name__ == "__main__":
    server = Server(port=5000)

    try:
        if server.start():
            print("Server started successfully")
            while True:
                time.sleep(5)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server.stop()
