# rvandroid/experiment/event/processor.py
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Callable, Optional

from rv_android_core.experiment.event.handler import EventHandler
from rv_android_core.experiment.event.models import Event, EventType


class ProcessingMode(Enum):
    """Processing modes for the event processor."""
    SYNCHRONOUS = "sync"
    ASYNCHRONOUS = "async"
    CALLBACK = "callback"


@dataclass
class ProcessingResult:
    """Result of event processing."""
    event: Event
    handler_count: int
    success: bool
    error: Optional[Exception] = None
    processing_time_ms: float = 0.0


class EventProcessor:
    """
    Handles the processing of events with priority and concurrency support.
    
    This class is responsible for:
    - Processing events based on their priority
    - Managing concurrency for event handling
    - Providing both synchronous and asynchronous processing
    - Tracking and reporting processing results
    """

    def __init__(self, max_worker_threads: int = 4):
        """
        Initialize the event processor.
        
        Args:
            max_worker_threads: Maximum number of worker threads for async processing
        """
        self.logger = logging.getLogger(__name__)
        self._worker_pool = ThreadPoolExecutor(
            max_workers=max_worker_threads,
            thread_name_prefix="EventProcessor"
        )
        self._lock = threading.RLock()
        self._active = True

    def process_event(self,
                      event: Event,
                      handlers: List[EventHandler],
                      mode: ProcessingMode = ProcessingMode.SYNCHRONOUS,
                      callback: Optional[Callable[[ProcessingResult], None]] = None) -> Optional[ProcessingResult]:
        """
        Process an event with the given handlers.
        
        Args:
            event: The event to process
            handlers: List of handlers to process the event with
            mode: Processing mode (synchronous, asynchronous, or callback)
            callback: Optional callback for async modes
            
        Returns:
            ProcessingResult if synchronous, None if asynchronous
        """
        if not handlers:
            return ProcessingResult(event=event, handler_count=0, success=True)

        if not self._active and mode != ProcessingMode.SYNCHRONOUS:
            self.logger.warning("Event processor is shutting down, forcing synchronous processing")
            mode = ProcessingMode.SYNCHRONOUS

        # Sort handlers by priority
        sorted_handlers = sorted(handlers)

        # Process based on mode
        if mode == ProcessingMode.SYNCHRONOUS:
            return self._process_sync(event, sorted_handlers)
        elif mode == ProcessingMode.ASYNCHRONOUS:
            self._process_async(event, sorted_handlers, callback)
            return None
        elif mode == ProcessingMode.CALLBACK:
            if not callback:
                raise ValueError("Callback mode requires a callback function")
            self._process_with_callback(event, sorted_handlers, callback)
            return None
        else:
            raise ValueError(f"Unknown processing mode: {mode}")

    def _process_sync(self, event: Event, handlers: List[EventHandler]) -> ProcessingResult:
        """
        Process an event synchronously.
        
        Args:
            event: The event to process
            handlers: Sorted list of handlers
            
        Returns:
            ProcessingResult with processing information
        """
        import time
        start_time = time.time()

        handler_count = 0
        error = None
        success = True

        try:
            for handler in handlers:
                try:
                    if handler.handle(event):
                        handler_count += 1
                except Exception as e:
                    self.logger.error(f"Error in event handler: {e}", exc_info=True)
                    if error is None:
                        error = e
                    success = False
        except Exception as e:
            self.logger.error(f"Error processing event: {e}", exc_info=True)
            error = e
            success = False

        processing_time = (time.time() - start_time) * 1000  # Convert to milliseconds

        return ProcessingResult(
            event=event,
            handler_count=handler_count,
            success=success,
            error=error,
            processing_time_ms=processing_time
        )

    def _process_async(self,
                       event: Event,
                       handlers: List[EventHandler],
                       callback: Optional[Callable[[ProcessingResult], None]]) -> None:
        """
        Process an event asynchronously.
        
        Args:
            event: The event to process
            handlers: Sorted list of handlers
            callback: Optional callback to call after processing
        """

        def _async_process():
            result = self._process_sync(event, handlers)
            if callback:
                try:
                    callback(result)
                except Exception as e:
                    self.logger.error(f"Error in async result callback: {e}", exc_info=True)

        self._worker_pool.submit(_async_process)

    def _process_with_callback(self,
                               event: Event,
                               handlers: List[EventHandler],
                               callback: Callable[[ProcessingResult], None]) -> None:
        """
        Process an event with a callback for the result.
        
        This method is similar to _process_async but guarantees that the callback will be called,
        even if the processing fails.
        
        Args:
            event: The event to process
            handlers: Sorted list of handlers
            callback: Callback to call after processing
        """

        def _callback_process():
            result = None
            try:
                result = self._process_sync(event, handlers)
            except Exception as e:
                self.logger.error(f"Unhandled error in event processing: {e}", exc_info=True)
                result = ProcessingResult(
                    event=event,
                    handler_count=0,
                    success=False,
                    error=e
                )

            try:
                callback(result)
            except Exception as e:
                self.logger.error(f"Error in callback: {e}", exc_info=True)

        self._worker_pool.submit(_callback_process)

    def process_events_by_type(self,
                               event: Event,
                               handlers_by_type: Dict[EventType, List[EventHandler]],
                               mode: ProcessingMode = ProcessingMode.SYNCHRONOUS,
                               callback: Optional[Callable[[ProcessingResult], None]] = None) -> Optional[
        ProcessingResult]:
        """
        Process an event against handlers filtered by event type.
        
        Args:
            event: The event to process
            handlers_by_type: Dictionary mapping event types to their handlers
            mode: Processing mode
            callback: Optional callback for async modes
            
        Returns:
            ProcessingResult if synchronous, None if asynchronous
        """
        handlers = handlers_by_type.get(event.type, [])
        return self.process_event(event, handlers, mode, callback)

    def shutdown(self, wait: bool = True) -> None:
        """
        Shut down the event processor.
        
        Args:
            wait: Whether to wait for pending tasks to complete
        """
        self.logger.info("Shutting down event processor")
        self._active = False
        self._worker_pool.shutdown(wait=wait)
        self.logger.info("Event processor shutdown complete")
