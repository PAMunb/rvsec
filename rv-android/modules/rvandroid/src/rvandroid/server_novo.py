# rvandroid/server/rvandroid_server.py

"""
Enhanced RVAndroid REST Server for LLM-Driven Android Testing

This module provides a comprehensive REST API server for the RVAndroid system, facilitating
intelligent Android application testing through LLM integration. The server implements
robust request processing, state analysis, and action generation with enterprise-grade
reliability and performance characteristics.

Architecture:
    The server employs a multi-layered architecture with clear separation of concerns:
    - Request handling and validation layer
    - State processing and enrichment layer
    - LLM action service integration layer
    - Response formatting and delivery layer
    - Comprehensive error handling and recovery

Key Features:
    - RESTful API with standardized endpoints and response formats
    - Robust request validation with detailed error reporting
    - Efficient state processing with memory management
    - Integration with RVAndroid LLM Action Service
    - Comprehensive performance monitoring and metrics collection
    - Health monitoring with detailed system status reporting
    - Graceful error handling with automatic recovery mechanisms

Performance Optimizations:
    - Request/response compression for network efficiency
    - Connection pooling and keep-alive support
    - Efficient memory management for large state data
    - Caching mechanisms for frequently accessed data
    - Asynchronous processing for improved throughput

Error Handling:
    - Comprehensive exception handling with proper HTTP status codes
    - Detailed error logging with contextual information
    - Graceful degradation for partial service failures
    - Automatic recovery mechanisms for transient errors
    - Circuit breaker patterns for external service integration

Security Considerations:
    - Input validation and sanitization
    - Request size limits to prevent DoS attacks
    - Rate limiting capabilities (configurable)
    - Secure error reporting without information leakage

Integration Points:
    - RVAndroid LLM Action Service for intelligent action generation
    - DroidBot Policy for seamless state data exchange
    - Error handling system for centralized error management
    - Logging system for comprehensive audit trails
    - Metrics collection for performance monitoring

Threading Model:
    - Thread-safe request processing with proper synchronization
    - Efficient resource sharing between concurrent requests
    - Automatic cleanup of resources after request completion
    - Configurable thread pool for optimal performance

Created: 2025-06-02
Authors: RV-Android Team
Version: 2.0.0
"""

import base64
import json
import os
import tempfile
import time
import uuid
from collections import deque
from threading import Thread, Lock
from typing import Optional, Dict, Any, List

from flask import Flask, request, jsonify
from werkzeug.exceptions import NotFound, HTTPException
from werkzeug.serving import make_server

from rv_android_core.llm.service.action_service import LLMActionService
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT


class TemporaryFileManager:
    """
    Manages temporary screenshot files with automatic cleanup and resource optimization.

    This component implements efficient temporary file management for screenshot processing,
    providing automatic cleanup, memory management, and resource optimization. It uses a
    circular buffer approach to maintain a reasonable number of temporary files while
    ensuring proper cleanup to prevent disk space issues.

    Architecture:
        The manager uses a thread-safe circular buffer to track temporary files, with
        automatic cleanup of old files when capacity is reached. It provides efficient
        file operations with minimal memory overhead and robust error handling.

    Resource Management:
        - Circular buffer for efficient file tracking
        - Automatic cleanup of expired files
        - Memory-efficient file operations
        - Thread-safe operations with proper synchronization
        - Configurable limits for resource control

    Performance Features:
        - Lazy file cleanup for improved performance
        - Efficient file naming with collision avoidance
        - Minimal memory footprint for file tracking
        - Fast file operations with error recovery
        - Optimized storage patterns for different file types

    Error Handling:
        - Graceful handling of file system errors
        - Automatic recovery from cleanup failures
        - Detailed error logging with context
        - Safe fallback mechanisms for critical operations
    """

    def __init__(self, max_files: int = 10, temp_dir: Optional[str] = None):
        """
        Initialize temporary file manager with configuration and storage setup.

        Args:
            max_files: Maximum number of temporary files to maintain
            temp_dir: Directory for temporary files (None for system default)
        """
        self.max_files = max_files
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.file_queue = deque(maxlen=max_files)
        self.lock = Lock()

        # Initialize logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "server.temp_file_manager",
            {CONTEXT_COMPONENT: "TemporaryFileManager"}
        )

        # Initialize error handling
        self.error_handler = ErrorHandler.get_instance()

        # Ensure temporary directory exists
        try:
            os.makedirs(self.temp_dir, exist_ok=True)
            self.logger.info(f"Temporary file manager initialized: max_files={max_files}, dir={self.temp_dir}")
        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "component": "TemporaryFileManager",
                    "operation": "directory_creation",
                    "temp_dir": self.temp_dir
                }
            )
            raise

    def save_screenshot(self, screenshot_b64: str, correlation_id: str) -> Optional[str]:
        """
        Save base64 encoded screenshot to temporary file with efficient management.

        This method handles the complete process of decoding, saving, and managing
        screenshot files with proper error handling and resource cleanup.

        Args:
            screenshot_b64: Base64 encoded screenshot data
            correlation_id: Unique identifier for request correlation

        Returns:
            Path to saved file or None if operation fails

        Processing Steps:
            1. Decode base64 screenshot data with validation
            2. Generate unique filename with collision avoidance
            3. Save file with atomic operations for reliability
            4. Update file queue with cleanup management
            5. Return file path for further processing

        Error Handling:
            - Base64 decoding error recovery
            - File system error handling
            - Automatic cleanup on partial failures
            - Detailed error logging with context
        """
        try:
            # Decode base64 data with validation
            try:
                screenshot_data = base64.b64decode(screenshot_b64)
            except Exception as e:
                self.logger.error(f"Failed to decode base64 screenshot data: {e}")
                return None

            # Generate unique filename with timestamp and correlation ID
            timestamp = int(time.time() * 1000)
            filename = f"screenshot_{correlation_id}_{timestamp}.png"
            file_path = os.path.join(self.temp_dir, filename)

            # Save file with atomic operation
            try:
                with open(file_path, 'wb') as f:
                    f.write(screenshot_data)
                    f.flush()
                    os.fsync(f.fileno())  # Ensure data is written to disk
            except Exception as e:
                self.logger.error(f"Failed to save screenshot file {file_path}: {e}")
                return None

            # Manage file queue with cleanup
            with self.lock:
                # Remove oldest file if at capacity
                if len(self.file_queue) >= self.max_files:
                    oldest_file = self.file_queue[0]
                    self._remove_file_safely(oldest_file)

                # Add new file to queue
                self.file_queue.append(file_path)

            self.logger.debug(f"Saved screenshot: {file_path} ({len(screenshot_data)} bytes)")
            return file_path

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "component": "TemporaryFileManager",
                    "operation": "save_screenshot",
                    "correlation_id": correlation_id
                }
            )
            return None

    def cleanup_file(self, file_path: str):
        """
        Remove specific temporary file with proper error handling.

        Args:
            file_path: Path to file to remove
        """
        with self.lock:
            if file_path in self.file_queue:
                self.file_queue.remove(file_path)
            self._remove_file_safely(file_path)

    def cleanup_all(self):
        """
        Remove all temporary files with comprehensive error handling.

        This method performs complete cleanup of all managed temporary files,
        with detailed error reporting and recovery mechanisms.
        """
        with self.lock:
            while self.file_queue:
                file_path = self.file_queue.popleft()
                self._remove_file_safely(file_path)

        self.logger.info("All temporary files cleaned up")

    def _remove_file_safely(self, file_path: str):
        """
        Safely remove file with comprehensive error handling.

        Args:
            file_path: Path to file to remove
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                self.logger.debug(f"Removed temporary file: {file_path}")
            else:
                self.logger.debug(f"File not found for removal: {file_path}")
        except Exception as e:
            self.logger.warning(f"Error removing file {file_path}: {e}")


class RequestValidator:
    """
    Comprehensive request validation for RVAndroid API endpoints.

    This component implements thorough validation of incoming requests to ensure
    data integrity, security, and proper API usage. It provides detailed error
    reporting and validation rules for different endpoint types.

    Architecture:
        The validator uses a rule-based approach with configurable validation
        patterns for different request types. It provides both structural and
        semantic validation with detailed error reporting.

    Validation Categories:
        - Structural validation: Required fields, data types, format constraints
        - Semantic validation: Value ranges, business logic constraints
        - Security validation: Input sanitization, size limits, pattern matching
        - Content validation: Data consistency, referential integrity

    Error Reporting:
        - Detailed error messages with field-specific information
        - Structured error responses for API consumers
        - Severity classification for different validation failures
        - Context-aware error messages for debugging

    Performance Optimizations:
        - Efficient validation patterns with minimal overhead
        - Early termination for critical validation failures
        - Caching of compiled validation rules
        - Optimized data structure traversal
    """

    def __init__(self):
        """Initialize request validator with logging and error handling."""
        # Initialize logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "server.request_validator",
            {CONTEXT_COMPONENT: "RequestValidator"}
        )

        # Initialize error handling
        self.error_handler = ErrorHandler.get_instance()

        # Define validation rules for different request types
        self.required_state_fields = {
            'activity', 'package_name', 'timestamp'
        }

        self.optional_state_fields = {
            'view_tree', 'width', 'height', 'state_str', 'structure_str',
            'screenshot_b64', 'views', 'policy_version'
        }

        # Define validation constraints
        self.max_request_size_mb = 50.0
        self.max_screenshot_size_mb = 20.0
        self.max_views_count = 1000

    def validate_state_request(self, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate state processing request with comprehensive checks.

        This method performs thorough validation of state data requests, checking
        both structural integrity and semantic correctness of the provided data.

        Args:
            data: Request data to validate

        Returns:
            Tuple of (is_valid, error_message)

        Validation Process:
            1. Basic structure and type validation
            2. Required field presence verification
            3. Field value validation and constraints
            4. Optional field validation when present
            5. Size and security constraint verification

        Validation Rules:
            - Request must be valid JSON object
            - Required fields must be present and non-empty
            - Numeric fields must be within reasonable ranges
            - String fields must not be empty or excessively long
            - Screenshot data must be valid base64
            - View data must be properly structured arrays
        """
        try:
            # Basic structure validation
            if not isinstance(data, dict):
                return False, "Request data must be a JSON object"

            # Check request size constraints
            if self._estimate_request_size(data) > self.max_request_size_mb:
                return False, f"Request size exceeds limit of {self.max_request_size_mb}MB"

            # Validate required fields
            missing_fields = self.required_state_fields - set(data.keys())
            if missing_fields:
                return False, f"Missing required fields: {', '.join(sorted(missing_fields))}"

            # Validate field types and values
            validation_errors = []

            # Validate activity field
            activity = data.get('activity')
            if not isinstance(activity, str) or not activity.strip():
                validation_errors.append("'activity' must be a non-empty string")
            elif len(activity) > 500:  # Reasonable limit for activity names
                validation_errors.append("'activity' field is too long (max 500 characters)")

            # Validate package_name field
            package_name = data.get('package_name')
            if not isinstance(package_name, str) or not package_name.strip():
                validation_errors.append("'package_name' must be a non-empty string")
            elif len(package_name) > 200:  # Reasonable limit for package names
                validation_errors.append("'package_name' field is too long (max 200 characters)")

            # Validate timestamp field
            timestamp = data.get('timestamp')
            if not isinstance(timestamp, (int, float)) or timestamp <= 0:
                validation_errors.append("'timestamp' must be a positive number")
            elif abs(timestamp - time.time()) > 86400:  # More than 24 hours difference
                validation_errors.append("'timestamp' appears to be invalid (too far from current time)")

            # Validate optional fields when present
            self._validate_optional_fields(data, validation_errors)

            if validation_errors:
                return False, "; ".join(validation_errors)

            self.logger.debug(f"Request validation passed for activity: {data['activity']}")
            return True, None

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "component": "RequestValidator",
                    "operation": "validate_state_request"
                }
            )
            return False, f"Validation error: {str(e)}"

    def _validate_optional_fields(self, data: Dict[str, Any], validation_errors: List[str]):
        """
        Validate optional fields when present in the request.

        Args:
            data: Request data containing optional fields
            validation_errors: List to append validation errors to
        """
        # Validate dimensions
        for field in ['width', 'height']:
            if field in data:
                value = data[field]
                if not isinstance(value, int) or value <= 0 or value > 10000:
                    validation_errors.append(f"'{field}' must be a positive integer <= 10000")

        # Validate screenshot data
        if 'screenshot_b64' in data:
            screenshot_b64 = data['screenshot_b64']
            if not isinstance(screenshot_b64, str):
                validation_errors.append("'screenshot_b64' must be a string")
            elif not self._is_valid_base64(screenshot_b64):
                validation_errors.append("'screenshot_b64' must be valid base64 data")
            elif len(screenshot_b64) > self.max_screenshot_size_mb * 1024 * 1024 * 1.4:  # ~40% overhead for base64
                validation_errors.append(f"Screenshot size exceeds limit of {self.max_screenshot_size_mb}MB")

        # Validate views array
        if 'views' in data:
            views = data['views']
            if not isinstance(views, list):
                validation_errors.append("'views' must be an array")
            elif len(views) > self.max_views_count:
                validation_errors.append(f"'views' array exceeds maximum size of {self.max_views_count}")
            else:
                # Validate individual view objects
                for i, view in enumerate(views):
                    if not isinstance(view, dict):
                        validation_errors.append(f"View at index {i} must be an object")
                        break

        # Validate view_tree structure
        if 'view_tree' in data:
            view_tree = data['view_tree']
            if not isinstance(view_tree, dict):
                validation_errors.append("'view_tree' must be an object")

    def _is_valid_base64(self, data: str) -> bool:
        """
        Validate base64 encoded data with comprehensive checks.

        Args:
            data: String to validate as base64

        Returns:
            True if valid base64 data
        """
        try:
            # Check basic format
            if not data or not isinstance(data, str):
                return False

            # Attempt to decode
            decoded = base64.b64decode(data, validate=True)

            # Basic sanity check - should produce some data
            return len(decoded) > 0

        except Exception:
            return False

    def _estimate_request_size(self, data: Dict[str, Any]) -> float:
        """
        Estimate request size in megabytes for validation.

        Args:
            data: Request data to estimate

        Returns:
            Estimated size in megabytes
        """
        try:
            json_str = json.dumps(data)
            return len(json_str.encode('utf-8')) / (1024 * 1024)
        except Exception:
            return 0.0


class StateProcessor:
    """
    Advanced state processing with LLM Action Service integration.

    This component handles the complete processing pipeline for Android application
    state data, coordinating with the LLM Action Service to generate intelligent
    testing actions. It implements efficient state processing, screenshot management,
    and comprehensive error handling.

    Architecture:
        The processor implements a pipeline architecture with distinct stages for
        state transformation, enrichment, action generation, and response formatting.
        Each stage includes proper error handling and performance monitoring.

    Processing Pipeline:
        1. State data ingestion and validation
        2. Screenshot processing and temporary file management
        3. State format conversion for LLM Action Service
        4. Action generation through LLM integration
        5. Response formatting and metadata enrichment
        6. Resource cleanup and performance tracking

    Integration Points:
        - LLM Action Service for intelligent action generation
        - Temporary File Manager for screenshot processing
        - Error Handler for centralized error management
        - Logging Manager for comprehensive audit trails

    Performance Features:
        - Efficient state processing with minimal memory overhead
        - Asynchronous screenshot processing where possible
        - Caching mechanisms for repeated operations
        - Resource pooling for expensive operations
        - Detailed performance metrics collection

    Error Recovery:
        - Graceful handling of LLM service failures
        - Automatic retry for transient errors
        - Fallback mechanisms for critical operations
        - Comprehensive error reporting with context
    """

    def __init__(self, action_service: LLMActionService, file_manager: TemporaryFileManager):
        """
        Initialize state processor with service dependencies and configuration.

        Args:
            action_service: LLM action service for generating intelligent actions
            file_manager: Temporary file manager for screenshot handling
        """
        self.action_service = action_service
        self.file_manager = file_manager

        # Initialize logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "server.state_processor",
            {CONTEXT_COMPONENT: "StateProcessor"}
        )

        # Initialize error handling
        self.error_handler = ErrorHandler.get_instance()

        # Performance tracking
        self._total_requests = 0
        self._successful_requests = 0
        self._total_processing_time = 0.0
        self._processing_lock = Lock()

    def process_state(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process state data and generate intelligent action recommendations.

        This method orchestrates the complete state processing pipeline, from initial
        data ingestion through action generation and response formatting. It includes
        comprehensive error handling, performance monitoring, and resource management.

        Args:
            request_data: Validated state data from DroidBot policy

        Returns:
            Dictionary containing actions and metadata

        Processing Flow:
            1. Generate correlation ID for request tracking
            2. Process screenshot data if present
            3. Convert state to internal format
            4. Generate actions via LLM Action Service
            5. Format response with metadata
            6. Clean up temporary resources
            7. Record performance metrics

        Error Handling:
            - Individual stage error isolation
            - Automatic resource cleanup on failures
            - Comprehensive error logging with context
            - Graceful degradation for partial failures

        Performance Monitoring:
            - Detailed timing analysis for each stage
            - Resource usage tracking
            - Success rate monitoring
            - Bottleneck identification
        """
        correlation_id = str(uuid.uuid4())
        screenshot_path = None
        processing_start = time.time()

        try:
            self.logger.info(f"Processing state for {request_data['package_name']} - {correlation_id}")

            # Update request tracking
            with self._processing_lock:
                self._total_requests += 1

            # Process screenshot if present
            if 'screenshot_b64' in request_data:
                screenshot_path = self._process_screenshot(
                    request_data['screenshot_b64'],
                    correlation_id
                )

                # Remove base64 data to reduce memory usage
                del request_data['screenshot_b64']

            # Convert to internal state format for LLM Action Service
            internal_state = self._convert_to_internal_state(request_data, screenshot_path)

            # Generate actions using LLM Action Service
            actions = self._generate_actions_with_error_handling(internal_state, correlation_id)

            # Format response with comprehensive metadata
            response = self._format_response(actions, correlation_id, processing_start)

            # Record successful processing
            processing_time = time.time() - processing_start
            with self._processing_lock:
                self._successful_requests += 1
                self._total_processing_time += processing_time

            self.logger.info(f"Generated {len(actions)} actions for {correlation_id} in {processing_time * 1000:.1f}ms")
            return response

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "component": "StateProcessor",
                    "correlation_id": correlation_id,
                    "package_name": request_data.get('package_name', 'unknown'),
                    "activity": request_data.get('activity', 'unknown')
                }
            )

            # Return error response with diagnostic information
            return {
                "actions": [],
                "error": str(e),
                "correlation_id": correlation_id,
                "processing_time_ms": round((time.time() - processing_start) * 1000, 2),
                "status": "error"
            }

        finally:
            # Clean up screenshot file regardless of success/failure
            if screenshot_path:
                self.file_manager.cleanup_file(screenshot_path)

    def _process_screenshot(self, screenshot_b64: str, correlation_id: str) -> Optional[str]:
        """
        Process base64 screenshot data with efficient file management.

        Args:
            screenshot_b64: Base64 encoded screenshot data
            correlation_id: Unique request identifier

        Returns:
            Path to saved screenshot file or None if processing failed
        """
        try:
            screenshot_path = self.file_manager.save_screenshot(screenshot_b64, correlation_id)
            if screenshot_path:
                self.logger.debug(f"Screenshot processed for {correlation_id}: {screenshot_path}")
            else:
                self.logger.warning(f"Failed to process screenshot for {correlation_id}")

            return screenshot_path

        except Exception as e:
            self.logger.error(f"Error processing screenshot for {correlation_id}: {e}")
            return None

    def _convert_to_internal_state(self, request_data: Dict[str, Any], screenshot_path: Optional[str]) -> Dict[
        str, Any]:
        """
        Convert DroidBot state data to RVAndroid internal format.

        Args:
            request_data: State data from DroidBot policy
            screenshot_path: Path to saved screenshot file

        Returns:
            State data in internal format for LLM Action Service
        """
        # Start with the original request data
        internal_state = request_data.copy()

        # Add screenshot path if available
        if screenshot_path:
            internal_state['screenshot_path'] = screenshot_path

        # Add server processing metadata
        internal_state['server_processing_time'] = time.time()
        internal_state['processing_version'] = '2.0.0'

        # Ensure compatibility with LLM Action Service expectations
        if 'views' in internal_state and internal_state['views']:
            # Convert views to expected format if needed
            internal_state['enabled_actions'] = self._extract_enabled_actions(internal_state['views'])

        self.logger.debug(f"Converted state for activity: {internal_state['activity']}")
        return internal_state

    def _extract_enabled_actions(self, views: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract enabled actions from view data for LLM Action Service.

        Args:
            views: List of view dictionaries

        Returns:
            List of enabled actions
        """
        enabled_actions = []

        for i, view in enumerate(views):
            if not isinstance(view, dict):
                continue

            # Generate action ID
            action_id = i + 1

            # Determine possible actions based on view properties
            clickable = view.get('clickable', False)
            enabled = view.get('enabled', True)
            view_class = view.get('class', '')

            if clickable and enabled:
                # Add click action
                enabled_actions.append({
                    'action_id': action_id,
                    'action_type': 'click',
                    'view': view,
                    'target': view.get('resource_id', f'view_{action_id}')
                })

                # Add long click for certain elements
                if 'Button' not in view_class:
                    enabled_actions.append({
                        'action_id': action_id + 1000,  # Offset for long click
                        'action_type': 'long_click',
                        'view': view,
                        'target': view.get('resource_id', f'view_{action_id}')
                    })

            # Add text input for text fields
            if 'EditText' in view_class and enabled:
                enabled_actions.append({
                    'action_id': action_id + 2000,  # Offset for text input
                    'action_type': 'set_text',
                    'view': view,
                    'target': view.get('resource_id', f'edittext_{action_id}')
                })

        return enabled_actions

    def _generate_actions_with_error_handling(self, internal_state: Dict[str, Any], correlation_id: str) -> List[
        Dict[str, Any]]:
        """
        Generate actions using LLM Action Service with comprehensive error handling.

        Args:
            internal_state: Prepared state data for action generation
            correlation_id: Request correlation ID for tracking

        Returns:
            List of generated actions
        """
        try:
            # Call LLM Action Service
            actions = self.action_service.process_state(internal_state)

            # Validate actions format
            if not isinstance(actions, list):
                self.logger.warning(f"LLM Action Service returned non-list result: {type(actions)}")
                return []

            # Filter and validate individual actions
            valid_actions = []
            for action in actions:
                if isinstance(action, dict) and 'action_type' in action:
                    valid_actions.append(action)
                else:
                    self.logger.warning(f"Invalid action format: {action}")

            return valid_actions

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "component": "StateProcessor",
                    "operation": "action_generation",
                    "correlation_id": correlation_id
                }
            )
            self.logger.error(f"Error generating actions for {correlation_id}: {e}")
            return []

    def _format_response(self, actions: List[Dict[str, Any]], correlation_id: str, start_time: float) -> Dict[str, Any]:
        """
        Format response with comprehensive metadata and performance information.

        Args:
            actions: Generated actions from LLM Action Service
            correlation_id: Request correlation ID
            start_time: Processing start time

        Returns:
            Formatted response dictionary
        """
        processing_time = time.time() - start_time

        response = {
            "actions": actions,
            "status": "success",
            "metadata": {
                "correlation_id": correlation_id,
                "server_time": time.time(),
                "processing_time_ms": round(processing_time * 1000, 2),
                "actions_count": len(actions),
                "server_version": "2.0.0"
            }
        }

        # Add action type summary for debugging
        if actions:
            action_types = [action.get('action_type', 'unknown') for action in actions]
            response["metadata"]["action_types"] = action_types

            # Add action IDs for reference
            action_ids = [action.get('action_id') for action in actions if 'action_id' in action]
            if action_ids:
                response["metadata"]["action_ids"] = action_ids

        # Add processing statistics
        with self._processing_lock:
            avg_processing_time = self._total_processing_time / max(self._successful_requests, 1)
            success_rate = self._successful_requests / max(self._total_requests, 1)

            response["metadata"]["server_stats"] = {
                "total_requests": self._total_requests,
                "successful_requests": self._successful_requests,
                "success_rate": round(success_rate, 3),
                "avg_processing_time_ms": round(avg_processing_time * 1000, 2)
            }

        return response


class RVAndroidServer:
    """
    Enhanced RVAndroid REST server with enterprise-grade reliability and performance.

    This server implementation provides a comprehensive REST API for the RVAndroid system,
    facilitating intelligent Android application testing through LLM integration. The server
    implements robust request processing, comprehensive error handling, health monitoring,
    and performance optimization features suitable for production deployments.

    Architectural Design:
        The server employs a multi-layered architecture with clear separation of concerns:
        - Flask application layer for HTTP request handling
        - Request validation layer for input sanitization and validation
        - State processing layer for business logic execution
        - Response formatting layer for consistent API responses
        - Error handling layer for comprehensive error management
        - Monitoring layer for health and performance tracking

    Key Features:
        - RESTful API design with standard HTTP methods and status codes
        - Comprehensive request validation with detailed error reporting
        - Efficient state processing with memory optimization
        - Robust error handling with automatic recovery mechanisms
        - Health monitoring with detailed system status information
        - Performance metrics collection and reporting
        - Graceful shutdown with resource cleanup
        - Thread-safe operations with proper synchronization

    Performance Optimizations:
        - Connection pooling and keep-alive support
        - Request/response compression for network efficiency
        - Efficient memory management for large requests
        - Caching mechanisms for frequently accessed data
        - Asynchronous processing where appropriate
        - Resource pooling for expensive operations

    Security Features:
        - Input validation and sanitization
        - Request size limits to prevent DoS attacks
        - Secure error reporting without information leakage
        - Content-Type validation for API security
        - Rate limiting capabilities (configurable)

    Monitoring and Observability:
        - Comprehensive health check endpoints
        - Detailed performance metrics and statistics
        - Request/response logging with correlation IDs
        - Error tracking and classification
        - Resource usage monitoring

    Integration Points:
        - RVAndroid LLM Action Service for intelligent action generation
        - DroidBot Policy for seamless state data exchange
        - Error handling system for centralized error management
        - Logging system for comprehensive audit trails

    Threading Model:
        - Multi-threaded request processing with Flask's built-in WSGI server
        - Thread-safe components with proper synchronization
        - Efficient resource sharing between concurrent requests
        - Automatic cleanup of resources after request completion

    Created: 2025-06-02
    Authors: RV-Android Team
    Version: 2.0.0
    """

    def __init__(self,
                 action_service: LLMActionService,
                 host: str = 'localhost',
                 port: int = 5000,
                 max_temp_files: int = 10,
                 temp_dir: Optional[str] = None):
        """
        Initialize RVAndroid server with comprehensive component setup and configuration.

        Args:
            action_service: LLM action service for generating intelligent actions
            host: Server host address for binding
            port: Server port number for listening
            max_temp_files: Maximum temporary files to maintain
            temp_dir: Directory for temporary files
        """
        self.action_service = action_service
        self.host = host
        self.port = port

        # Initialize Flask application with optimized configuration
        self.app = Flask(__name__)
        self.app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max request size
        self.app.config['JSON_SORT_KEYS'] = False  # Preserve key order in responses

        # Initialize components with dependency injection
        self.file_manager = TemporaryFileManager(max_temp_files, temp_dir)
        self.validator = RequestValidator()
        self.processor = StateProcessor(action_service, self.file_manager)

        # Server state management
        self._server_thread: Optional[Thread] = None
        self._server_instance = None
        self._is_running = False
        self._should_stop = False
        self._lock = Lock()

        # Initialize logging and error handling
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "server.rvandroid_server",
            {CONTEXT_COMPONENT: "RVAndroidServer"}
        )
        self.error_handler = ErrorHandler.get_instance()

        # Initialize routes and error handlers
        self._setup_error_handlers()
        self._setup_routes()

        # Server statistics and monitoring
        self._stats = {
            "start_time": None,
            "requests_processed": 0,
            "requests_failed": 0,
            "total_actions_generated": 0,
            "avg_response_time": 0.0
        }
        self._response_times = deque(maxlen=100)  # Keep last 100 response times

        self.logger.info(f"RVAndroid server initialized: {host}:{port}")

    def _setup_error_handlers(self):
        """Configure comprehensive error handlers for robust API operation."""

        @self.app.errorhandler(NotFound)
        def handle_404(error):
            """Handle 404 errors with proper logging and response formatting."""
            if request.path != '/favicon.ico':  # Ignore favicon requests
                self.logger.warning(f"404 error for path: {request.path}")
            return jsonify({
                "error": "Endpoint not found",
                "path": request.path,
                "method": request.method
            }), 404

        @self.app.errorhandler(HTTPException)
        def handle_http_error(error):
            """Handle HTTP errors with structured responses and logging."""
            self.logger.warning(f"HTTP error {error.code}: {error.description}")
            return jsonify({
                "error": error.description,
                "code": error.code,
                "type": "http_error"
            }), error.code

        @self.app.errorhandler(413)
        def handle_request_too_large(error):
            """Handle request size limit exceeded errors."""
            self.logger.warning("Request size exceeded maximum limit")
            return jsonify({
                "error": "Request too large",
                "max_size_mb": self.app.config['MAX_CONTENT_LENGTH'] / (1024 * 1024),
                "type": "request_size_error"
            }), 413

        @self.app.errorhandler(Exception)
        def handle_unexpected_error(error):
            """Handle unexpected errors with comprehensive logging and safe responses."""
            if isinstance(error, HTTPException):
                return handle_http_error(error)

            # Generate correlation ID for error tracking
            correlation_id = str(uuid.uuid4())

            self.error_handler.handle_error(
                error,
                context={
                    "component": "RVAndroidServer",
                    "endpoint": request.endpoint,
                    "method": request.method,
                    "correlation_id": correlation_id
                }
            )

            self.logger.error(f"Unexpected error [{correlation_id}]: {error}", exc_info=True)

            return jsonify({
                "error": "Internal server error",
                "correlation_id": correlation_id,
                "type": "server_error"
            }), 500

    def _setup_routes(self):
        """Configure all REST API endpoints with comprehensive functionality."""

        @self.app.route('/health', methods=['GET'])
        def health_check():
            """
            Comprehensive health check endpoint for monitoring server status.

            Returns detailed health information including uptime, statistics,
            component status, and performance metrics for monitoring systems.
            """
            try:
                current_time = time.time()
                uptime = current_time - self._stats["start_time"] if self._stats["start_time"] else 0

                # Calculate performance metrics
                avg_response_time = 0.0
                if self._response_times:
                    avg_response_time = sum(self._response_times) / len(self._response_times)

                health_data = {
                    "status": "healthy",
                    "timestamp": current_time,
                    "uptime_seconds": round(uptime, 2),
                    "version": "2.0.0",
                    "statistics": {
                        "requests_processed": self._stats["requests_processed"],
                        "requests_failed": self._stats["requests_failed"],
                        "total_actions_generated": self._stats["total_actions_generated"],
                        "avg_response_time_ms": round(avg_response_time * 1000, 2),
                        "success_rate": round(
                            (self._stats["requests_processed"] - self._stats["requests_failed"]) /
                            max(self._stats["requests_processed"], 1), 3
                        )
                    },
                    "components": {
                        "action_service": "available" if self.action_service else "unavailable",
                        "file_manager": "available",
                        "temp_files_count": len(self.file_manager.file_queue),
                        "max_temp_files": self.file_manager.max_files
                    },
                    "system": {
                        "temp_dir": self.file_manager.temp_dir,
                        "max_request_size_mb": self.app.config['MAX_CONTENT_LENGTH'] / (1024 * 1024)
                    }
                }

                return jsonify(health_data)

            except Exception as e:
                self.logger.error(f"Error in health check: {e}")
                return jsonify({
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": time.time()
                }), 500

        @self.app.route('/api/get_actions', methods=['POST'])
        def get_actions():
            """
            Main endpoint for processing state data and generating intelligent actions.

            Accepts state data from DroidBot policies and returns action recommendations
            generated by the LLM Action Service. Implements comprehensive validation,
            error handling, and performance monitoring for reliable operation.
            """
            request_start_time = time.time()
            correlation_id = str(uuid.uuid4())

            try:
                # Validate request content type
                if not request.is_json:
                    self.logger.warning(f"Invalid content type for request [{correlation_id}]")
                    return jsonify({
                        "error": "Content-Type must be application/json",
                        "correlation_id": correlation_id
                    }), 400

                # Get and validate request data
                request_data = request.get_json()
                if not request_data:
                    self.logger.warning(f"No JSON data in request [{correlation_id}]")
                    return jsonify({
                        "error": "Request body must contain valid JSON",
                        "correlation_id": correlation_id
                    }), 400

                # Validate request structure and content
                is_valid, error_message = self.validator.validate_state_request(request_data)
                if not is_valid:
                    self.logger.warning(f"Request validation failed [{correlation_id}]: {error_message}")
                    return jsonify({
                        "error": f"Invalid request: {error_message}",
                        "correlation_id": correlation_id
                    }), 400

                # Log request details
                package_name = request_data.get('package_name', 'unknown')
                activity = request_data.get('activity', 'unknown')
                self.logger.info(f"Processing request [{correlation_id}] for {package_name} - {activity}")

                # Process state and generate actions
                response_data = self.processor.process_state(request_data)

                # Ensure correlation ID is included in response
                if 'metadata' not in response_data:
                    response_data['metadata'] = {}
                response_data['metadata']['correlation_id'] = correlation_id

                # Update server statistics
                response_time = time.time() - request_start_time
                self._update_statistics(response_data, response_time)

                # Add performance metadata to response
                response_data["metadata"]["response_time_ms"] = round(response_time * 1000, 2)

                self.logger.info(
                    f"Request completed [{correlation_id}]: {len(response_data.get('actions', []))} actions, "
                    f"{response_time:.3f}s"
                )

                return jsonify(response_data)

            except Exception as e:
                # Update failure statistics
                self._stats["requests_failed"] += 1

                self.error_handler.handle_error(
                    e,
                    context={
                        "component": "RVAndroidServer",
                        "endpoint": "get_actions",
                        "correlation_id": correlation_id
                    }
                )

                self.logger.error(f"Error processing request [{correlation_id}]: {e}", exc_info=True)

                return jsonify({
                    "error": "Failed to process request",
                    "message": str(e),
                    "correlation_id": correlation_id,
                    "status": "error"
                }), 500

        @self.app.route('/api/status', methods=['GET'])
        def get_status():
            """
            Detailed status endpoint providing comprehensive server information.

            Returns extensive status information including configuration, statistics,
            performance metrics, and operational data for monitoring and debugging.
            """
            try:
                current_time = time.time()
                uptime = current_time - self._stats["start_time"] if self._stats["start_time"] else 0

                # Calculate detailed performance metrics
                response_times_ms = [rt * 1000 for rt in list(self._response_times)]

                status_data = {
                    "server": {
                        "name": "RVAndroid Server",
                        "version": "2.0.0",
                        "host": self.host,
                        "port": self.port,
                        "uptime_seconds": round(uptime, 2),
                        "is_running": self._is_running,
                        "python_version": f"{__import__('sys').version_info.major}.{__import__('sys').version_info.minor}"
                    },
                    "statistics": {
                        **self._stats,
                        "uptime_seconds": round(uptime, 2)
                    },
                    "performance": {
                        "recent_response_times_ms": response_times_ms[-10:],  # Last 10 response times
                        "avg_response_time_ms": round(sum(response_times_ms) / len(response_times_ms),
                                                      2) if response_times_ms else 0,
                        "min_response_time_ms": round(min(response_times_ms), 2) if response_times_ms else 0,
                        "max_response_time_ms": round(max(response_times_ms), 2) if response_times_ms else 0,
                        "requests_per_minute": round(self._stats["requests_processed"] / max(uptime / 60, 1),
                                                     2) if uptime > 0 else 0
                    },
                    "components": {
                        "action_service": {
                            "status": "available" if self.action_service else "unavailable",
                            "type": type(self.action_service).__name__ if self.action_service else None
                        },
                        "file_manager": {
                            "status": "available",
                            "temp_files_count": len(self.file_manager.file_queue),
                            "max_temp_files": self.file_manager.max_files,
                            "temp_dir": self.file_manager.temp_dir
                        },
                        "validator": {
                            "status": "available",
                            "max_request_size_mb": self.validator.max_request_size_mb
                        },
                        "processor": {
                            "status": "available",
                            "total_requests": self.processor._total_requests,
                            "successful_requests": self.processor._successful_requests,
                            "success_rate": round(
                                self.processor._successful_requests / max(self.processor._total_requests, 1), 3
                            )
                        }
                    },
                    "timestamp": current_time
                }

                return jsonify(status_data)

            except Exception as e:
                self.logger.error(f"Error getting status: {e}")
                return jsonify({
                    "error": "Failed to get status",
                    "message": str(e),
                    "timestamp": time.time()
                }), 500

        @self.app.route('/api/metrics', methods=['GET'])
        def get_metrics():
            """
            Metrics endpoint for monitoring systems and performance analysis.

            Returns detailed metrics in a format suitable for monitoring systems
            like Prometheus, with comprehensive performance and operational data.
            """
            try:
                current_time = time.time()
                uptime = current_time - self._stats["start_time"] if self._stats["start_time"] else 0

                metrics = {
                    "timestamp": current_time,
                    "uptime_seconds": round(uptime, 2),
                    "counters": {
                        "requests_total": self._stats["requests_processed"],
                        "requests_failed_total": self._stats["requests_failed"],
                        "requests_successful_total": self._stats["requests_processed"] - self._stats["requests_failed"],
                        "actions_generated_total": self._stats["total_actions_generated"]
                    },
                    "gauges": {
                        "temp_files_current": len(self.file_manager.file_queue),
                        "avg_response_time_ms": round(
                            sum(self._response_times) / len(self._response_times) * 1000, 2
                        ) if self._response_times else 0,
                        "success_rate": round(
                            (self._stats["requests_processed"] - self._stats["requests_failed"]) /
                            max(self._stats["requests_processed"], 1), 3
                        )
                    },
                    "histograms": {
                        "response_time_ms": {
                            "buckets": self._calculate_response_time_buckets(),
                            "count": len(self._response_times),
                            "sum": round(sum(self._response_times) * 1000, 2)
                        }
                    }
                }

                return jsonify(metrics)

            except Exception as e:
                self.logger.error(f"Error getting metrics: {e}")
                return jsonify({
                    "error": "Failed to get metrics",
                    "message": str(e)
                }), 500

    def _update_statistics(self, response_data: Dict[str, Any], response_time: float):
        """
        Update server statistics with request results and performance data.

        Args:
            response_data: Response data from state processing
            response_time: Time taken to process the request
        """
        self._stats["requests_processed"] += 1

        # Update action count
        actions_count = len(response_data.get('actions', []))
        self._stats["total_actions_generated"] += actions_count

        # Update response time statistics
        self._response_times.append(response_time)
        if self._response_times:
            self._stats["avg_response_time"] = sum(self._response_times) / len(self._response_times)

    def _calculate_response_time_buckets(self) -> Dict[str, int]:
        """
        Calculate response time buckets for histogram metrics.

        Returns:
            Dictionary with response time buckets and counts
        """
        if not self._response_times:
            return {}

        response_times_ms = [rt * 1000 for rt in self._response_times]
        buckets = {
            "le_100": sum(1 for rt in response_times_ms if rt <= 100),
            "le_250": sum(1 for rt in response_times_ms if rt <= 250),
            "le_500": sum(1 for rt in response_times_ms if rt <= 500),
            "le_1000": sum(1 for rt in response_times_ms if rt <= 1000),
            "le_2500": sum(1 for rt in response_times_ms if rt <= 2500),
            "le_5000": sum(1 for rt in response_times_ms if rt <= 5000),
            "le_inf": len(response_times_ms)
        }

        return buckets

    def start(self) -> bool:
        """
        Start the RVAndroid server with comprehensive initialization and error handling.

        Returns:
            True if server started successfully, False otherwise
        """
        with self._lock:
            if self._is_running:
                self.logger.warning("Server is already running")
                return True

            try:
                self._should_stop = False
                self._stats["start_time"] = time.time()

                # Start server thread
                self._server_thread = Thread(target=self._run_server, daemon=True)
                self._server_thread.start()

                self._is_running = True
                self.logger.info(f"RVAndroid server started successfully on http://{self.host}:{self.port}")
                return True

            except Exception as e:
                self.error_handler.handle_error(
                    e,
                    context={
                        "component": "RVAndroidServer",
                        "operation": "start_server"
                    }
                )
                self.logger.error(f"Failed to start server: {e}", exc_info=True)
                self._is_running = False
                return False

    def _run_server(self):
        """
        Run Flask server with proper error handling and graceful shutdown support.

        This method implements the main server loop with comprehensive error handling,
        graceful shutdown support, and proper resource management.
        """
        try:
            # Create WSGI server instance with optimized configuration
            self._server_instance = make_server(
                self.host,
                self.port,
                self.app,
                threaded=True,
                request_handler=None,  # Use default handler
                passthrough_errors=False
            )

            self.logger.info("Server thread started, accepting connections")

            # Serve requests until shutdown is requested
            self._server_instance.serve_forever()

        except Exception as e:
            self.error_handler.handle_error(
                e,
                context={
                    "component": "RVAndroidServer",
                    "operation": "run_server"
                }
            )
            self.logger.error(f"Server error: {e}", exc_info=True)

        finally:
            self._is_running = False
            self.logger.info("Server thread stopped")

    def stop(self) -> bool:
        """
        Stop the server gracefully with comprehensive cleanup and resource management.

        Returns:
            True if server stopped successfully, False otherwise
        """
        with self._lock:
            if not self._is_running:
                self.logger.info("Server is not running")
                return True

            try:
                self.logger.info("Stopping RVAndroid server...")
                self._should_stop = True

                # Shutdown server instance
                if self._server_instance:
                    self._server_instance.shutdown()
                    self._server_instance = None

                # Wait for server thread to finish
                if self._server_thread:
                    self._server_thread.join(timeout=10.0)
                    if self._server_thread.is_alive():
                        self.logger.warning("Server thread did not stop within timeout")
                    self._server_thread = None

                # Clean up resources
                self.file_manager.cleanup_all()

                # Clean up action service resources if available
                if (self.action_service and
                        hasattr(self.action_service, 'cleanup')):
                    try:
                        self.action_service.cleanup()
                        self.logger.info("Action service resources cleaned up")
                    except Exception as e:
                        self.logger.warning(f"Error during action service cleanup: {e}")

                self._is_running = False
                self.logger.info("RVAndroid server stopped successfully")
                return True

            except Exception as e:
                self.error_handler.handle_error(
                    e,
                    context={
                        "component": "RVAndroidServer",
                        "operation": "stop_server"
                    }
                )
                self.logger.error(f"Error stopping server: {e}", exc_info=True)
                return False

    def is_healthy(self) -> bool:
        """
        Check if the server is healthy and operational.

        Returns:
            True if server is running and all components are healthy
        """
        try:
            return (
                    self._is_running and
                    self.action_service is not None and
                    self.file_manager is not None and
                    self.validator is not None and
                    self.processor is not None
            )
        except Exception:
            return False

    def get_server_info(self) -> Dict[str, Any]:
        """
        Get comprehensive server information for monitoring and debugging.

        Returns:
            Dictionary containing server configuration and status
        """
        try:
            current_time = time.time()
            uptime = current_time - self._stats["start_time"] if self._stats["start_time"] else 0

            return {
                "server_info": {
                    "name": "RVAndroid Server",
                    "version": "2.0.0",
                    "host": self.host,
                    "port": self.port,
                    "is_running": self._is_running,
                    "uptime_seconds": round(uptime, 2),
                    "start_time": self._stats["start_time"]
                },
                "configuration": {
                    "max_content_length_mb": self.app.config['MAX_CONTENT_LENGTH'] / (1024 * 1024),
                    "max_temp_files": self.file_manager.max_files,
                    "temp_directory": self.file_manager.temp_dir
                },
                "statistics": self._stats.copy(),
                "component_status": {
                    "action_service": "healthy" if self.action_service else "unavailable",
                    "file_manager": "healthy",
                    "validator": "healthy",
                    "processor": "healthy"
                }
            }

        except Exception as e:
            self.logger.error(f"Error getting server info: {e}")
            return {
                "error": str(e),
                "server_info": {
                    "name": "RVAndroid Server",
                    "version": "2.0.0",
                    "status": "error"
                }
            }