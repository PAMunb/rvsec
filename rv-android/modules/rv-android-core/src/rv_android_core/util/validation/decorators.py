"""
Validation decorators for RV-Android Core.

This module provides decorators that enable Pydantic models to maintain
backwards compatibility with positional arguments while providing modern
validation capabilities.
"""

import functools
import inspect
from typing import Any, Callable, Dict, List, Type, TypeVar, cast

from pydantic import BaseModel

from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from .config import get_validation_config

T = TypeVar('T', bound=BaseModel)


def validated_model(positional_fields: List[str]) -> Callable[[Type[T]], Type[T]]:
    """
    Decorator that enables Pydantic models to accept both positional and named arguments.
    
    This decorator maintains full backwards compatibility while enabling comprehensive
    validation through Pydantic. It allows existing code to continue using positional
    arguments while new code can benefit from named parameters and validation.
    
    ### Architectural Decisions:
    - Provides transparent backwards compatibility for existing constructors
    - Maps positional arguments to named parameters automatically
    - Integrates with the validation configuration system
    - Maintains error handling and logging standards
    
    ### Role in the System:
    - Enables gradual migration to validated models
    - Preserves existing calling patterns during transition
    - Provides consistent validation across all system models
    - Supports development vs production validation strategies
    
    Args:
        positional_fields: List of field names in positional order
        
    Returns:
        Decorator function that transforms the class
        
    Usage:
        ```python
        @validated_model(['code', 'stdout', 'stderr'])
        class CommandResult(BaseValidatedModel):
            code: int = Field(..., description="Exit code from command execution")
            stdout: str = Field(default="", description="Standard output")
            stderr: str = Field(default="", description="Standard error output")
        
        # Both work seamlessly:
        result1 = CommandResult(0, "success", "")                    # Legacy style
        result2 = CommandResult(code=0, stdout="success", stderr="") # Modern style
        ```
    """
    
    def decorator(cls: Type[T]) -> Type[T]:
        """
        Transform a Pydantic model class to support positional arguments.
        
        Args:
            cls: The Pydantic model class to transform
            
        Returns:
            The transformed class with positional argument support
        """
        # Store original init for validation configuration
        original_init = cls.__init__
        
        # Set up logging for the decorator
        logging_manager = LoggingManager.get_instance()
        logger = logging_manager.get_logger(
            f'rv_android_core.util.validation.decorators.{cls.__name__}',
            {CONTEXT_COMPONENT: 'ValidationDecorator'}
        )
        
        # Get error handler for comprehensive error management
        error_handler = ErrorHandler.get_instance()
        
        @functools.wraps(original_init)
        def __init__(self, *args, **kwargs):
            """
            Enhanced constructor supporting both positional and named arguments.
            
            Args:
                *args: Positional arguments mapped to field names
                **kwargs: Named arguments passed directly to Pydantic
            """
            config = get_validation_config()
            
            try:
                # Map positional arguments to named parameters
                if args:
                    # Ensure we don't exceed available field mappings
                    num_positional = min(len(args), len(positional_fields))
                    
                    for i in range(num_positional):
                        field_name = positional_fields[i]
                        
                        # Check for conflicts between positional and named args
                        if field_name in kwargs:
                            raise ValueError(
                                f"Argument '{field_name}' specified both positionally "
                                f"(position {i}) and as keyword argument"
                            )
                        
                        kwargs[field_name] = args[i]
                    
                    # Handle excess positional arguments
                    if len(args) > len(positional_fields):
                        excess_args = args[len(positional_fields):]
                        logger.warning(
                            f"Excess positional arguments ignored in {cls.__name__}: {excess_args}"
                        )
                
                # Log validation activity if enabled
                if config.log_validation_events:
                    logger.debug(
                        f"Constructing {cls.__name__} with {len(args)} positional "
                        f"and {len(kwargs)} named arguments"
                    )
                
                # Call the original constructor (preserves BaseValidatedModel logic)
                original_init(self, **kwargs)
                
            except Exception as e:
                # Use error handler for comprehensive error management
                context = {
                    'class_name': cls.__name__,
                    'positional_args_count': len(args),
                    'named_args_count': len(kwargs),
                    'positional_fields': positional_fields
                }
                
                if not error_handler.handle_error(e, context):
                    # Re-raise if not handled by error system
                    raise
        
        # Replace the constructor
        cls.__init__ = __init__
        
        # Add metadata for introspection
        cls._positional_fields = positional_fields
        cls._is_validated_model = True
        
        # Log successful decoration
        # logger.debug(f"Applied validation decorator to {cls.__name__}")
        
        return cls
    
    return decorator


def get_positional_fields(cls: Type[BaseModel]) -> List[str]:
    """
    Get the positional field mapping for a validated model class.
    
    Args:
        cls: The model class to inspect
        
    Returns:
        List of field names in positional order, or empty list if not a validated model
    """
    return getattr(cls, '_positional_fields', [])


def is_validated_model(cls: Type) -> bool:
    """
    Check if a class is a validated model with positional argument support.
    
    Args:
        cls: The class to check
        
    Returns:
        True if the class is a validated model, False otherwise
    """
    return getattr(cls, '_is_validated_model', False)


def create_constructor_mapping(cls: Type[BaseModel]) -> Dict[str, Any]:
    """
    Create a mapping of constructor information for a validated model.
    
    Args:
        cls: The model class to analyze
        
    Returns:
        Dictionary with constructor mapping information
    """
    if not is_validated_model(cls):
        return {}
    
    return {
        'class_name': cls.__name__,
        'positional_fields': get_positional_fields(cls),
        'model_fields': list(cls.model_fields.keys()) if hasattr(cls, 'model_fields') else [],
        'supports_positional': True,
        'supports_named': True
    }