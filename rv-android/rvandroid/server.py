from flask import Flask, request, jsonify
from threading import Thread, Lock
import requests
import logging
import time
from typing import Optional, Dict, Any
from werkzeug.serving import make_server
from werkzeug.exceptions import NotFound, HTTPException

class Server:
    """
    A resilient REST server implementation using Flask.
    
    This server runs in a separate thread and is designed to:
    - Be highly resilient to failures
    - Support graceful shutdown
    - Provide detailed status information
    - Handle errors without affecting the main system
    - Auto-recover from certain failure conditions
    """

    def __init__(self, host: str = 'localhost', port: int = 5000,
                 max_retries: int = 3, retry_delay: float = 5.0):
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

        @self.app.route('/items', methods=['GET'])
        def get_items():
            """Get all items endpoint"""
            try:
                self.logger.info("GET /items endpoint called")
                items = [
                    {"id": 1, "name": "Item 1"},
                    {"id": 2, "name": "Item 2"}
                ]
                return jsonify(items)
            except Exception as e:
                self.logger.error(f"Error in get_items: {e}", exc_info=True)
                raise

        @self.app.route('/items/<int:item_id>', methods=['GET'])
        def get_item(item_id):
            """Get specific item endpoint"""
            try:
                self.logger.info(f"GET /items/{item_id} endpoint called")
                item = {"id": item_id, "name": f"Item {item_id}"}
                return jsonify(item)
            except Exception as e:
                self.logger.error(f"Error in get_item: {e}", exc_info=True)
                raise

        @self.app.route('/items', methods=['POST'])
        def create_item():
            """Create new item endpoint"""
            try:
                self.logger.info("POST /items endpoint called")
                data = request.get_json()
                return jsonify({"message": "Item created", "data": data}), 201
            except Exception as e:
                self.logger.error(f"Error in create_item: {e}", exc_info=True)
                raise
            
        @self.app.route('/generate', methods=['POST'])
        def generate_actions():            
            try:
                self.logger.info("POST /generate endpoint called")
                data = request.get_json()
                return jsonify({"message": "Hello World!!!", "data": data}), 200
            except Exception as e:
                self.logger.error(f"Error in generate_actions: {e}", exc_info=True)
                raise

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