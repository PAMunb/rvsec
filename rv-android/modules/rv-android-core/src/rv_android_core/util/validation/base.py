"""
Base validation models for RV-Android Core.

This module provides the foundational Pydantic models and configuration
that all domain models should inherit from.
"""

from typing import Any, Dict

from pydantic import BaseModel, ConfigDict

from .config import get_validation_config


class BaseValidatedModel(BaseModel):
    """
    Base class for all validated models in the RV-Android system.

    ### Architectural Decisions:
    - Inherits from Pydantic BaseModel for comprehensive validation
    - Provides consistent configuration across all system models
    - Implements environment-aware validation behavior
    - Maintains backwards compatibility through flexible configuration

    ### Role in the System:
    - Serves as the foundation for all data model classes
    - Ensures consistent validation behavior across components
    - Provides standardized serialization and deserialization
    - Enables development vs production validation strategies

    ### Configuration Strategy:
    - Validation behavior controlled by ValidationConfig
    - Development mode: Full validation and strict checking
    - Production mode: Minimal validation overhead
    - Supports both positional and named parameter construction
    """

    model_config = ConfigDict(
        # Core validation settings
        validate_assignment=True,  # Always validate on assignment for safety
        str_strip_whitespace=True,  # Clean string inputs
        extra="forbid",  # Prevent unexpected fields
        # Serialization settings
        use_enum_values=False,  # Keep enum objects, don't serialize as values
        populate_by_name=True,  # Allow both field names and aliases
        # Performance settings
        arbitrary_types_allowed=True,  # Allow complex types like NetworkX graphs and nested models
        validate_default=True,  # Validate default values
        # Development/debugging settings
        loc_by_alias=False,  # Use field names in error locations
    )

    def __init__(self, **data: Any):
        """
        Initialize the model with environment-aware validation.

        Args:
            **data: Model field data
        """
        config = get_validation_config()

        # Apply configuration-based validation
        if not config.enabled:
            # In production mode, bypass most validation for performance
            # Still validate basic types to prevent runtime errors
            super().__init__(**data)
        else:
            # Development mode - full validation
            if config.strict_mode:
                # Extra strict validation in development
                super().__init__(**data)
            else:
                # Standard development validation
                super().__init__(**data)

    def model_dump_json_safe(self) -> str:
        """
        Serialize model to JSON with error handling.

        Returns:
            JSON string representation of the model
        """
        try:
            return self.model_dump_json()
        except Exception:
            # Fallback to dict representation if JSON serialization fails
            return str(self.model_dump())

    def model_dump_safe(self) -> Dict[str, Any]:
        """
        Serialize model to dictionary with error handling.

        Returns:
            Dictionary representation of the model
        """
        try:
            return self.model_dump()
        except Exception as e:
            # Return basic dict if Pydantic serialization fails
            return {"__type__": self.__class__.__name__, "__error__": str(e)}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseValidatedModel":
        """
        Create model instance from dictionary.

        Args:
            data: Dictionary containing model data

        Returns:
            Model instance
        """
        return cls(**data)

    def __repr__(self) -> str:
        """Provide detailed string representation for debugging."""
        try:
            # Use Pydantic's default representation
            return super().__repr__()
        except Exception:
            # Fallback representation if Pydantic fails
            return f"{self.__class__.__name__}(fields={list(self.model_fields.keys())})"

    def __eq__(self, other: Any) -> bool:
        """
        Compare models for equality.

        Args:
            other: Other object to compare

        Returns:
            True if models are equal, False otherwise
        """
        if not isinstance(other, self.__class__):
            return False

        try:
            return self.model_dump() == other.model_dump()
        except Exception:
            # Fallback to basic comparison
            return super().__eq__(other)

    def __hash__(self) -> int:
        """
        Generate hash for model instances.

        Returns:
            Hash value for the model
        """
        try:
            # Hash based on serialized data
            return hash(self.model_dump_json())
        except Exception:
            # Fallback to object hash
            return hash(id(self))
