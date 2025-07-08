from typing import Optional
from pydantic import Field

from rv_android_core.util.validation.base import BaseValidatedModel
from rv_android_core.util.validation.decorators import validated_model
from rv_android_core.util.logging.constants import LOG_LEVEL_DEBUG
from rv_android_core.constants import FORMAT_JSON


@validated_model(['enabled', 'log_level', 'max_samples', 'export_enabled', 'export_format'])
class PerformanceMonitorConfig(BaseValidatedModel):
    """
    Configuration for performance monitoring capabilities.
    
    Controls performance monitoring behavior during experiment execution
    to balance observability with execution overhead.
    
    ### Architectural Role:
    - Provides centralized configuration for performance monitoring
    - Integrates with CLI argument parsing
    - Supports serialization for configuration persistence
    - Enables monitoring overhead control
    
    ### Integration Points:
    - Used by PerformanceMonitor singleton configuration
    - Passed from rv-experiment to rv-platform
    - Configured via CLI arguments
    - Supports export and logging control
    """
    enabled: bool = Field(default=True, description="Enable/disable performance monitoring")
    log_level: str = Field(default=LOG_LEVEL_DEBUG, description="Logging level for performance monitoring")
    max_samples: int = Field(default=1000, description="Maximum number of samples to collect")
    export_enabled: bool = Field(default=False, description="Enable/disable export of performance data")
    export_format: str = Field(default=FORMAT_JSON, description="Format for performance data export")
    
    @classmethod
    def from_cli_args(cls, args) -> 'PerformanceMonitorConfig':
        """
        Create configuration from CLI arguments.
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            PerformanceMonitorConfig instance
        """
        return cls(
            enabled=not getattr(args, 'disable_performance_monitor', False),
            log_level=getattr(args, 'performance_monitor_level', LOG_LEVEL_DEBUG),
            max_samples=getattr(args, 'performance_monitor_max_samples', 1000),
            export_enabled=getattr(args, 'performance_export_enabled', False),
            export_format=getattr(args, 'performance_export_format', FORMAT_JSON)
        )
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary for serialization."""
        return self.model_dump()