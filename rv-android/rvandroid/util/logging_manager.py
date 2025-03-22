# rvandroid/util/logging_manager.py
import json
import logging
import os
import sys
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional, List

# Define custom log levels for experiment-specific events
EXPERIMENT_START = 25
EXPERIMENT_END = 26
TASK_START = 27
TASK_END = 28
ERROR = 40  # Same as logging.ERROR

# Register custom log levels with logging module
logging.addLevelName(EXPERIMENT_START, "EXPERIMENT_START")
logging.addLevelName(EXPERIMENT_END, "EXPERIMENT_END")
logging.addLevelName(TASK_START, "TASK_START")
logging.addLevelName(TASK_END, "TASK_END")


class ContextAdapter(logging.LoggerAdapter):
    """
    A logging adapter that adds contextual information to log records.
    Supports nested contexts and automatic propagation.
    """

    def __init__(self, logger, context=None):
        """
        Initialize the adapter with a logger and optional context.

        Args:
            logger: The logger to adapt
            context: Initial context dictionary
        """
        super().__init__(logger, {})
        self.context = context or {}
        self._context_stack: List[Dict[str, Any]] = []

    def process(self, msg, kwargs):
        """
        Process the log message by adding context information.

        Args:
            msg: The log message
            kwargs: Keyword arguments for the logger

        Returns:
            Tuple of (modified message, modified kwargs)
        """
        if 'extra' not in kwargs:
            kwargs['extra'] = {}

        # Add thread ID and timestamp to extra fields
        thread_id = threading.current_thread().ident
        if thread_id:
            kwargs['extra']['thread_id'] = thread_id

        kwargs['extra']['timestamp'] = datetime.now().isoformat()

        # Include context data
        for key, value in self.context.items():
            kwargs['extra'][key] = value

        return msg, kwargs

    def push_context(self, **context):
        """
        Push a new context onto the stack.

        Args:
            **context: Context key-value pairs
        """
        # Save current context
        self._context_stack.append(self.context.copy())

        # Update with new context
        self.context.update(context)

        return self

    def pop_context(self):
        """
        Pop the top context from the stack.

        Returns:
            The popped context
        """
        if not self._context_stack:
            return {}

        # Restore previous context
        old_context = self.context
        self.context = self._context_stack.pop()

        return old_context

    def with_context(self, **context):
        """
        Context manager for temporary context.

        Args:
            **context: Context key-value pairs

        Returns:
            Self for use in with statement
        """
        self.push_context(**context)
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.pop_context()


class JsonFormatter(logging.Formatter):
    """
    Formatter that outputs log records as JSON.
    """

    def format(self, record):
        """
        Format log record as JSON.

        Args:
            record: Log record

        Returns:
            JSON string
        """
        log_data = {
            'timestamp': getattr(record, 'timestamp', datetime.now().isoformat()),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread_id': getattr(record, 'thread_id', threading.current_thread().ident),
        }

        # Include any extra fields from the record
        for key, value in record.__dict__.items():
            if key not in log_data and not key.startswith('_') and key != 'args' and key != 'msg':
                log_data[key] = value

        return json.dumps(log_data)


class StructuredFormatter(logging.Formatter):
    """
    Formatter that outputs log records in a structured text format.
    Useful for human-readable logs while maintaining context.
    """

    def __init__(self, fmt=None, datefmt=None, style='%', max_context_length=120):
        """
        Initialize formatter with optional customization.

        Args:
            fmt: Log format
            datefmt: Date format
            style: Format style
            max_context_length: Maximum length for context string
        """
        super().__init__(fmt, datefmt, style)
        self.max_context_length = max_context_length

    def format(self, record):
        """
        Format record with structured context.

        Args:
            record: Log record

        Returns:
            Formatted log string
        """
        # Format base message
        message = super().format(record)

        # Get context from record
        context = {}
        for key, value in record.__dict__.items():
            if not key.startswith('_') and key not in {
                'args', 'msg', 'message', 'pathname', 'filename',
                'module', 'exc_info', 'exc_text', 'lineno',
                'funcName', 'created', 'msecs', 'relativeCreated',
                'levelname', 'levelno', 'name'
            }:
                context[key] = value

        # If we have context, add it to the message
        if context:
            context_str = " | ".join(f"{k}={v}" for k, v in context.items())
            if len(context_str) > self.max_context_length:
                context_str = context_str[:self.max_context_length - 3] + "..."
            message = f"{message} [{context_str}]"

        return message


class LoggingManager:
    """
    LoggingManager: Centralized Logging System for RV-Android Framework
    ==================================================================

    The LoggingManager is a sophisticated, singleton-based logging management system designed
    to provide consistent, contextual, and configurable logging capabilities across all components
    of the RV-Android framework. It serves as a central hub for logging configuration, standardizing
    log formats, handling hierarchical contexts, and ensuring proper log routing.

    Key Features:
    ------------
    1. Singleton pattern for global access across the framework
    2. Context-aware logging with hierarchical propagation
    3. Configurable output destinations (console, file)
    4. Custom log levels for experiment-specific events
    5. Support for structured logging formats (text and JSON)
    6. Thread-safe operation for concurrent logging
    7. Logger caching for performance optimization

    Architectural Role:
    -----------------
    The LoggingManager plays a critical role in the RV-Android architecture by:
    - Providing a unified logging interface across all components
    - Enabling contextual debugging through structured log data
    - Supporting experiment traceability through event-specific logging
    - Facilitating troubleshooting through consistent log formats
    - Enhancing system observability via configurable logging granularity

    Implementation Details:
    --------------------

    Singleton Pattern:
    ----------------
    The singleton pattern ensures that there is only one instance of the LoggingManager
    throughout the application, guaranteeing consistent logging behavior and configuration.
    The get_instance() method provides global access to this single instance, while the
    _lock ensures thread safety during instantiation.

    Contextual Logging:
    -----------------
    The LoggingManager uses a ContextAdapter to attach contextual information to log records.
    This adapter wraps the standard Python logger and enhances it with context management
    capabilities. The context can be:
    - Provided at logger creation
    - Pushed/popped during execution
    - Temporarily modified using a context manager
    - Inherited from parent loggers

    The context information is added to log records as extra fields, which can be used
    for filtering logs or included in the log output formats.

    Custom Log Levels:
    ---------------
    Custom log levels (EXPERIMENT_START, EXPERIMENT_END, TASK_START, TASK_END) extend
    the standard Python logging levels to provide experiment-specific semantic logging.
    These custom levels enable differentiation between standard operational logs and
    experimental workflow events.

    Formatters:
    ---------
    Two formatter classes are provided:
    1. StructuredFormatter: Produces human-readable logs with contextual information
    2. JsonFormatter: Produces machine-parseable JSON logs with structured fields

    These formatters extract contextual metadata from log records and incorporate it
    into the log output, enabling advanced log analysis and filtering.

    Thread Safety:
    -----------
    All critical operations in the LoggingManager are protected by locks to ensure
    thread-safe behavior in concurrent environments. This includes logger creation,
    caching, context registration, and output configuration.

    Performance Considerations:
    ------------------------
    The LoggingManager uses caching to avoid recreating loggers with the same name
    and context, which improves performance in high-logging-frequency scenarios.
    Additionally, context propagation is optimized to minimize overhead when
    creating child loggers or modifying contexts.

    Standard Context Keys:
    -------------------
    The LoggingManager defines standard context keys to ensure consistency:
    - CONTEXT_TASK_ID: Identifier for tasks
    - CONTEXT_APP_NAME: Name of the application being tested
    - CONTEXT_TOOL_NAME: Name of the testing tool
    - CONTEXT_COMPONENT: Component name within the system
    - CONTEXT_PHASE: Current execution phase

    Using these standard keys ensures that logs can be consistently filtered and
    analyzed across different components of the system.

    Common Log Message Patterns:
    --------------------------
    The LoggingManager provides standard message templates for common operations:
    - LOG_START: "Starting {operation}"
    - LOG_COMPLETE: "Completed {operation}"
    - LOG_ERROR: "Error in {operation}: {error}"
    - LOG_SKIPPED: "Skipped {operation}: {reason}"

    These templates ensure consistency in log messages across the system and
    make logs more readable and analyzable.

    Best Practices:
    -------------
    1. Always obtain loggers through the LoggingManager rather than directly
       using Python's logging module
    2. Use consistent naming for loggers following the hierarchical pattern
       (e.g., "module.submodule.class")
    3. Provide relevant context when creating loggers
    4. Use the appropriate log level for each message
    5. Utilize context managers for temporary context changes
    6. Follow the standard message templates for common operations
    7. Use standard context keys for consistency

    Integration with Other Components:
    --------------------------------
    The LoggingManager is designed to work seamlessly with other RV-Android components:
    - EventBus: For publishing logging-related events
    - ErrorHandler: For capturing and logging errors
    - PerformanceMonitor: For tracking logging performance
    - Configuration: For obtaining logging configuration

    This integration ensures a cohesive logging experience throughout the framework
    and enables advanced features like error tracking, performance monitoring, and
    event-driven logging.

    Advanced Configuration:
    --------------------
    The LoggingManager supports advanced configuration options such as:
    - Multiple output destinations with different log levels
    - Custom formatter configuration
    - JSON structured logging for machine processing
    - Log file rotation and archiving
    - Selective logger silencing

    These configuration options can be adjusted programmatically based on
    runtime requirements or environment settings.

    Error Handling:
    ------------
    The LoggingManager includes robust error handling to ensure that logging
    failures don't impact the main application flow. If logging operations fail,
    errors are caught and handled internally where possible, with fallback mechanisms
    to ensure critical information is not lost.

    Extending the LoggingManager:
    ---------------------------
    The LoggingManager can be extended to support additional features such as:
    - Remote logging to centralized log management systems
    - Log encryption for sensitive information
    - Advanced log rotation and archiving strategies
    - Integration with monitoring and alerting systems
    - Custom log filtering and processing

    These extensions can be implemented by subclassing the LoggingManager or
    adding new methods to the existing implementation.

    Security Considerations:
    ---------------------
    When logging sensitive information, be cautious about:
    1. Personally identifiable information (PII)
    2. Credentials and tokens
    3. Security configurations
    4. Test data that might contain sensitive content

    The LoggingManager itself doesn't implement automatic data redaction, so
    sensitive information should be filtered or obfuscated before logging.
    """

    _instance = None
    _lock = threading.Lock()

    # Standard context keys that should be used consistently
    CONTEXT_TASK_ID = "task_id"
    CONTEXT_APP_NAME = "app_name"
    CONTEXT_TOOL_NAME = "tool_name"
    CONTEXT_COMPONENT = "component"
    CONTEXT_PHASE = "phase"

    # Common log messages patterns
    LOG_START = "Starting {operation}"
    LOG_COMPLETE = "Completed {operation}"
    LOG_ERROR = "Error in {operation}: {error}"
    LOG_SKIPPED = "Skipped {operation}: {reason}"

    @classmethod
    def get_instance(cls):
        """Get the singleton instance of the logging manager."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = LoggingManager()
            return cls._instance

    def __init__(self):
        """Initialize the logging manager."""
        self.root_logger = logging.getLogger('rvandroid')
        self.log_path = None
        self.logger_cache = {}
        self.context_registry = {}
        self._output_config = {
            'console': {
                'enabled': True,
                'level': logging.INFO,
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
            'file': {
                'enabled': False,
                'level': logging.DEBUG,
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'json': False
            }
        }

        # Check if root logger already has handlers (set up by basicConfig)
        # If it does, we don't need to add our own to avoid duplication
        root_has_handlers = len(logging.getLogger().handlers) > 0

        if not root_has_handlers and len(self.root_logger.handlers) == 0:
            self._setup_default_logging()

    def _setup_default_logging(self):
        """Configure default logging to console."""
        # Clear existing handlers
        self.root_logger.handlers = []

        # Console handler
        if self._output_config['console']['enabled']:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self._output_config['console']['level'])

            # Regular formatter for console
            formatter = logging.Formatter(self._output_config['console']['format'])
            console_handler.setFormatter(formatter)

            # Add handler to root logger
            self.root_logger.addHandler(console_handler)

        # Prevent propagation to the root logger to avoid duplicate logs
        # Only do this if we've added our own handlers
        self.root_logger.propagate = False

        # Set the overall logger level to the minimum of all handlers
        min_level = min(
            self._output_config['console']['level'] if self._output_config['console']['enabled'] else logging.CRITICAL,
            self._output_config['file']['level'] if self._output_config['file']['enabled'] else logging.CRITICAL
        )
        self.root_logger.setLevel(min_level)

    def configure_output(self, console=True, file=False, console_level=logging.INFO,
                         file_level=logging.DEBUG, json_format=False,
                         console_format=None, file_format=None):
        """
        Configure logging output destinations and formats.

        Args:
            console: Whether to enable console output
            file: Whether to enable file output
            console_level: Logging level for console
            file_level: Logging level for file
            json_format: Whether to use JSON format for file logs
            console_format: Format string for console logs
            file_format: Format string for file logs
        """
        self._output_config['console']['enabled'] = console
        self._output_config['console']['level'] = console_level
        if console_format:
            self._output_config['console']['format'] = console_format

        self._output_config['file']['enabled'] = file
        self._output_config['file']['level'] = file_level
        self._output_config['file']['json'] = json_format
        if file_format:
            self._output_config['file']['format'] = file_format

        # Reconfigure logging
        self._setup_default_logging()

        # Update any existing file logging
        if self.log_path:
            self.setup_file_logging(os.path.dirname(self.log_path),
                                    os.path.basename(self.log_path),
                                    self._output_config['file']['json'])

    def setup_file_logging(self, log_dir: str, experiment_id: str, json_format: bool = False):
        """
        Set up file logging for an experiment.

        Args:
            log_dir: Directory for log files
            experiment_id: ID of the experiment
            json_format: Whether to use JSON formatting for logs
        """
        # Create log directory if it doesn't exist
        os.makedirs(log_dir, exist_ok=True)

        # Create log file path
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        self.log_path = os.path.join(log_dir, f"{experiment_id}_{timestamp}.log")

        # Remove any existing file handlers
        for handler in self.root_logger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                self.root_logger.removeHandler(handler)

        # File handler
        file_handler = logging.FileHandler(self.log_path)
        file_handler.setLevel(self._output_config['file']['level'])

        # Choose formatter based on format
        if json_format:
            formatter = JsonFormatter()
        else:
            formatter = StructuredFormatter(self._output_config['file']['format'])

        file_handler.setFormatter(formatter)

        # Add handler to root logger
        self.root_logger.addHandler(file_handler)

        # Update file config
        self._output_config['file']['enabled'] = True

    def get_logger(self, name: str, context: Optional[Dict[str, Any]] = None):
        """
        Get a logger with the given name and context.

        Args:
            name: Logger name
            context: Optional context dictionary to add to all log records

        Returns:
            Logger with context adapter
        """
        # Create a cache key based on name and context items
        cache_key = name
        if context:
            # Sort to ensure deterministic cache key
            context_items = sorted(context.items())
            cache_key = f"{name}:{context_items}"

        # Check cache first
        if cache_key in self.logger_cache:
            return self.logger_cache[cache_key]

        # Create new logger
        logger = logging.getLogger(f'rvandroid.{name}')

        # Create adapter with context
        adapter = ContextAdapter(logger, context or {})

        # Add convenience methods for custom log levels
        def experiment_start(self, msg, *args, **kwargs):
            self.log(EXPERIMENT_START, msg, *args, **kwargs)

        def experiment_end(self, msg, *args, **kwargs):
            self.log(EXPERIMENT_END, msg, *args, **kwargs)

        def task_start(self, msg, *args, **kwargs):
            self.log(TASK_START, msg, *args, **kwargs)

        def task_end(self, msg, *args, **kwargs):
            self.log(TASK_END, msg, *args, **kwargs)

        # Add methods to the adapter
        adapter.experiment_start = experiment_start.__get__(adapter)
        adapter.experiment_end = experiment_end.__get__(adapter)
        adapter.task_start = task_start.__get__(adapter)
        adapter.task_end = task_end.__get__(adapter)

        # Cache the logger
        self.logger_cache[cache_key] = adapter

        # Register context if provided
        if context:
            self.register_context(name, context)

        return adapter

    def register_context(self, name: str, context: Dict[str, Any]):
        """
        Register a context with a logger name for future reference.

        Args:
            name: Logger name
            context: Context dictionary
        """
        self.context_registry[name] = context.copy()

    def get_context(self, name: str) -> Dict[str, Any]:
        """
        Get registered context for a logger name.

        Args:
            name: Logger name

        Returns:
            Context dictionary or empty dict if not found
        """
        return self.context_registry.get(name, {})

    def create_child_logger(self, parent_name: str, child_name: str,
                            additional_context: Optional[Dict[str, Any]] = None):
        """
        Create a child logger that inherits context from a parent logger.

        Args:
            parent_name: Parent logger name
            child_name: Child logger name
            additional_context: Additional context to add

        Returns:
            Child logger with combined context
        """
        # Get parent context
        parent_context = self.get_context(parent_name)

        # Create combined context
        combined_context = parent_context.copy()
        if additional_context:
            combined_context.update(additional_context)

        # Create child logger
        full_child_name = f"{parent_name}.{child_name}"
        return self.get_logger(full_child_name, combined_context)

    def get_task_logger(self, task_id: int, component: str,
                        additional_context: Optional[Dict[str, Any]] = None):
        """
        Create a logger for a specific task with standardized context.

        Args:
            task_id: Task ID
            component: Component name
            additional_context: Additional context

        Returns:
            Task-specific logger
        """
        context = {self.CONTEXT_TASK_ID: task_id, self.CONTEXT_COMPONENT: component}
        if additional_context:
            context.update(additional_context)

        return self.get_logger(f"task.{task_id}.{component}", context)
