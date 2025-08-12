"""
Server lifecycle management for DroidBot integration.

This module provides context manager for robust HTTP server lifecycle
during RVAndroid tool execution.
"""

import time
import requests
from typing import Optional
from contextlib import contextmanager
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.error.exceptions import ServerLifecycleError # TODO existe essa excecao? se nao existir tem criar/registrar handler no error_handler.py
from rvandroid_tool.constants import DEFAULT_SERVER_PORT, SERVER_STARTUP_TIMEOUT, SERVER_SHUTDOWN_TIMEOUT


class ServerLifecycleManager:
    """
    Manages HTTP server lifecycle for DroidBot communication.
    
    ### Architectural Role:
    - Provides context manager pattern for server resource management
    - Handles server startup, health checking, and graceful shutdown
    - Integrates with rv-android-core error handling and logging
    - Ensures proper cleanup on both success and failure scenarios
    
    ### Server Management Strategy:
    - Uses context manager protocol for automatic resource cleanup
    - Implements health check with timeout for startup verification
    - Provides graceful shutdown with configurable timeout
    - Handles race conditions and port conflicts
    """

    def __init__(self, service, port: int = DEFAULT_SERVER_PORT):
        """
        Initialize server lifecycle manager.
        
        Args:
            service: LLM action service for request handling
            port: HTTP server port number
        """
        self.service = service
        self.port = port
        self.server: Optional['Server'] = None
        
        # Initialize logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rvandroid_tool.server.lifecycle",
            {CONTEXT_COMPONENT: "ServerLifecycleManager"}
        )

    @ErrorHandler.handle_errors(
        component="ServerLifecycleManager",
        operation="enter"
    )
    def __enter__(self):
        """
        Start server and verify readiness.
        
        ### Startup Process:
        - Initialize server with configured service and port
        - Start server in background thread
        - Verify server readiness with health check
        - Handle startup failures with proper cleanup
        
        Returns:
            Server instance ready for requests
            
        Raises:
            ServerLifecycleError: When server startup fails
        """
        from .server import Server
        
        self.logger.info(f"Starting server on port {self.port}")
        
        try:
            self.server = Server(self.service, port=self.port)
            self.server.start()
            
            # Verify server readiness
            self._wait_for_server_ready()
            
            self.logger.info("Server started successfully")
            return self.server
            
        except Exception as e:
            if self.server:
                self.server.stop()
            raise ServerLifecycleError(f"Failed to start server: {e}") from e

    @ErrorHandler.handle_errors(
        component="ServerLifecycleManager",
        operation="exit"
    )
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Stop server and cleanup resources.
        
        ### Shutdown Process:
        - Initiate graceful server shutdown
        - Wait for shutdown completion with timeout
        - Log shutdown status and any errors
        - Ensure cleanup regardless of shutdown success
        
        Args:
            exc_type: Exception type if context exited with exception
            exc_val: Exception value if context exited with exception
            exc_tb: Exception traceback if context exited with exception
        """
        if self.server:
            self.logger.info("Stopping server")
            try:
                self.server.stop()
                self._wait_for_server_shutdown()
                self.logger.info("Server stopped successfully")
            except Exception as e:
                self.logger.error(f"Error during server shutdown: {e}")
            finally:
                self.server = None

    def _wait_for_server_ready(self) -> None:
        """
        Wait for server to become ready with health check.
        
        ### Health Check Strategy:
        - Attempts HTTP requests to server health endpoint
        - Uses exponential backoff for retry timing
        - Enforces startup timeout to prevent indefinite waiting
        - Provides detailed logging for debugging startup issues
        
        Raises:
            ServerLifecycleError: When server doesn't become ready within timeout
        """
        start_time = time.time()
        retry_count = 0
        
        while time.time() - start_time < SERVER_STARTUP_TIMEOUT:
            try:
                response = requests.get(f"http://localhost:{self.port}/health", timeout=1)
                if response.status_code == 200:
                    self.logger.debug(f"Server ready after {retry_count} retries")
                    return
            except requests.RequestException:
                pass
            
            retry_count += 1
            time.sleep(min(0.1 * (2 ** retry_count), 1.0))  # Exponential backoff, max 1s
        
        raise ServerLifecycleError(
            f"Server not ready within {SERVER_STARTUP_TIMEOUT}s timeout"
        )

    def _wait_for_server_shutdown(self) -> None:
        """
        Wait for server shutdown completion.
        
        ### Shutdown Verification:
        - Monitors server thread status
        - Enforces shutdown timeout
        - Logs shutdown progress for debugging
        """
        if not self.server:
            return
            
        start_time = time.time()
        while (self.server.is_running() and 
               time.time() - start_time < SERVER_SHUTDOWN_TIMEOUT):
            time.sleep(0.1)
        
        if self.server.is_running():
            self.logger.warning(
                f"Server shutdown timeout after {SERVER_SHUTDOWN_TIMEOUT}s"
            )
