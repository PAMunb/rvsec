# rvandroid/util/logging/formatters.py
import json
import logging
import threading
from datetime import datetime


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
            'module': getattr(record, 'module', None) or record.name,
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
                'levelname', 'levelno', 'name',
                'stack_info', 'taskName', 'thread', 'threadName',
                'process', 'processName', 'asctime'
            }:
                context[key] = value

        # If we have context, add it to the message
        if context:
            context_str = " | ".join(f"{k}={v}" for k, v in context.items())
            if len(context_str) > self.max_context_length:
                context_str = context_str[:self.max_context_length - 3] + "..."
            message = f"{message} [{context_str}]"

        return message
   