# rv_android_core/util/error/context.py
"""
ErrorContext class for fluent context building and auto-introspection.

This module provides enhanced context management capabilities for the ErrorHandler,
enabling cleaner error handling patterns through fluent API design and automatic
context extraction via introspection.
"""

import inspect
from typing import Dict, Any, Optional


class ErrorContext:
    """
    Enhanced error context that can auto-introspect caller information for cleaner error handling.
    
    ### Architectural Decisions:
    - Provides automatic context extraction through introspection
    - Supports both explicit and implicit context building
    - Enables fluent API for context construction
    - Maintains backward compatibility with manual context dictionaries
    
    ### Role in the System:
    - Reduces boilerplate code in error handling scenarios
    - Provides consistent context information across the framework
    - Enables Spring-like error handling patterns through auto-introspection
    - Facilitates debugging by capturing relevant execution context automatically
    
    ### Usage Patterns:
    
    1. **Fluent Building**:
    ```python
    context = ErrorContext().with_component("TaskExecutor").with_phase("execution")
    error_handler.handle_error(exception, context)
    ```
    
    2. **Auto-introspection**:
    ```python
    context = ErrorContext(auto_introspect=True).with_data(task_id=task.id)
    # Automatically captures caller class, method, file, line
    ```
    
    3. **Direct Handling**:
    ```python
    ErrorContext().with_component("Parser").handle(exception, error_handler)
    ```
    """
    
    def __init__(self, auto_introspect: bool = True, **kwargs):
        """
        Initialize error context with optional auto-introspection.
        
        Args:
            auto_introspect: Whether to automatically capture caller information
            **kwargs: Initial context data
        """
        self._context = kwargs.copy()
        self._auto_introspect = auto_introspect
    
    def with_component(self, component: str) -> 'ErrorContext':
        """
        Add component information to the context.
        
        Args:
            component: Name of the component where the error occurred
            
        Returns:
            Self for method chaining
        """
        self._context['component'] = component
        return self
    
    def with_phase(self, phase: str) -> 'ErrorContext':
        """
        Add phase/operation information to the context.
        
        Args:
            phase: Name of the operation or phase being executed
            
        Returns:
            Self for method chaining
        """
        self._context['phase'] = phase
        return self
    
    def with_data(self, **kwargs) -> 'ErrorContext':
        """
        Add arbitrary context data.
        
        Args:
            **kwargs: Additional context key-value pairs
            
        Returns:
            Self for method chaining
        """
        self._context.update(kwargs)
        return self
    
    def disable_introspection(self) -> 'ErrorContext':
        """
        Disable automatic introspection for this context.
        
        Returns:
            Self for method chaining
        """
        self._auto_introspect = False
        return self
    
    def enable_introspection(self) -> 'ErrorContext':
        """
        Enable automatic introspection for this context.
        
        Returns:
            Self for method chaining
        """
        self._auto_introspect = True
        return self
    
    def build(self, frame_offset: int = 2) -> Dict[str, Any]:
        """
        Build the final context dictionary with optional introspection.
        
        Args:
            frame_offset: Number of stack frames to skip for introspection
            
        Returns:
            Complete context dictionary
        """
        context = self._context.copy()
        
        if self._auto_introspect:
            # Auto-introspect caller information
            try:
                frame = inspect.currentframe()
                for _ in range(frame_offset):
                    frame = frame.f_back
                    if frame is None:
                        break
                
                if frame:
                    context.setdefault('caller_function', frame.f_code.co_name)
                    context.setdefault('caller_filename', frame.f_code.co_filename.split('/')[-1])
                    context.setdefault('caller_line', frame.f_lineno)
                    
                    # Try to extract class name if method call
                    if 'self' in frame.f_locals:
                        obj = frame.f_locals['self']
                        context.setdefault('caller_class', obj.__class__.__name__)
                        # Auto-detect component from class name if not provided
                        if 'component' not in context:
                            context['component'] = obj.__class__.__name__
            except Exception:
                # Introspection failed, continue without it
                pass
        
        return context
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary format for backward compatibility.
        
        Returns:
            Context dictionary
        """
        return self.build()
    
    def handle(self, error: Exception, error_handler) -> bool:
        """
        Handle the error directly using the provided error handler.
        
        Args:
            error: Exception to handle
            error_handler: ErrorHandler instance to use
            
        Returns:
            True if error was handled, False otherwise
        """
        context = self.build(frame_offset=3)
        return error_handler.handle_error(error, context)
    
    def __str__(self) -> str:
        """String representation of the context."""
        context = self.build()
        component = context.get('component', 'Unknown')
        phase = context.get('phase', 'Unknown')
        return f"ErrorContext(component='{component}', phase='{phase}')"
    
    def __repr__(self) -> str:
        """Detailed string representation of the context."""
        context = self.build()
        return f"ErrorContext({context})"