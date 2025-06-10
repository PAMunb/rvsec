"""
Experiment Bridge - Integration Interface for Legacy main.py

### Architectural Overview:
This module provides a bridge interface that allows the legacy main.py to delegate 
experiment execution to the modern rv-experiment module while maintaining backward 
compatibility and respecting module independence.

### Key Architectural Decisions:
- **Backward Compatibility**: Maintains compatibility with existing main.py interface
- **Progressive Migration**: Enables gradual migration from legacy to modern architecture
- **Module Independence**: Preserves tool management in main.py while delegating experiments
- **Configuration Translation**: Translates between legacy Configuration and ExperimentConfig

### Role in the System:
- Bridges legacy main.py with modern rv-experiment module
- Provides compatibility layer for existing experiment execution patterns
- Enables progressive migration without breaking existing workflows
- Facilitates configuration translation between old and new systems

### Design Patterns:
- **Bridge Pattern**: Connects legacy interface with modern implementation
- **Adapter Pattern**: Adapts legacy configuration to modern configuration format
- **Facade Pattern**: Simplifies experiment execution interface for main.py
- **Factory Pattern**: Creates appropriate configuration and orchestrator instances
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT, LOG_START, LOG_COMPLETE

from rv_experiment.config import ExperimentConfig, ToolConfiguration
from rv_experiment.orchestrator import ExperimentOrchestrator


class ExperimentBridge:
    """
    Bridge interface for integrating legacy main.py with modern rv-experiment.
    
    ### Architectural Decisions:
    - Provides backward-compatible interface for main.py
    - Translates legacy configuration to modern ExperimentConfig
    - Delegates actual experiment execution to ExperimentOrchestrator
    - Maintains logging and error handling consistency
    
    ### Role in the System:
    - Primary integration point between legacy and modern systems
    - Handles configuration translation and validation
    - Coordinates experiment execution with proper error handling
    - Enables gradual migration while preserving existing functionality
    
    ### Integration Points:
    - Interfaces with legacy Configuration singleton from main.py
    - Translates to modern ExperimentConfig format
    - Delegates execution to ExperimentOrchestrator
    - Maintains compatibility with existing tool management
    """
    
    def __init__(self):
        """Initialize the experiment bridge."""
        # Initialize logging and error handling
        self.logging_manager = LoggingManager.get_instance()
        self.error_handler = ErrorHandler.get_instance()
        self.logger = self.logging_manager.get_logger(
            "rv_experiment.bridge",
            {CONTEXT_COMPONENT: "ExperimentBridge"}
        )
        
        self.logger.info("ExperimentBridge initialized")
    
    def execute_experiment_with_legacy_config(self, 
                                             tools: List[AbstractTool],
                                             legacy_config: Optional[Any] = None) -> bool:
        """
        Execute experiment using legacy configuration format.
        
        Args:
            tools: List of tool instances from main.py
            legacy_config: Legacy Configuration singleton instance
            
        Returns:
            True if experiment completed successfully, False otherwise
        """
        with self.logger.with_context(
            phase="execute_experiment_with_legacy_config",
            tools=[tool.name for tool in tools]
        ):
            self.logger.info(LOG_START.format(
                phase="experiment execution via bridge"
            ))
            
            try:
                # Import Configuration here to avoid circular dependency
                if legacy_config is None:
                    # Try to import and get Configuration singleton
                    try:
                        # This will be the old configuration system
                        from rvandroid.config.configuration import Configuration
                        legacy_config = Configuration.get_instance()
                    except ImportError as e:
                        self.logger.warning(f"Could not import legacy Configuration: {e}")
                        # Create minimal configuration
                        legacy_config = self._create_minimal_config()
                
                # Convert legacy configuration to modern format
                experiment_config = self._convert_legacy_config(legacy_config, tools)
                
                # Validate converted configuration
                experiment_config.validate()
                
                # Create orchestrator and execute
                orchestrator = ExperimentOrchestrator(
                    config=experiment_config,
                    logger=self.logger
                )
                
                # Determine experiment type and execute appropriately
                if len(tools) == 1:
                    success = orchestrator.execute_single_tool_experiment()
                else:
                    success = orchestrator.execute_comparative_experiment()
                
                if success:
                    self.logger.info(LOG_COMPLETE.format(
                        phase="experiment execution via bridge"
                    ))
                else:
                    self.logger.error("Experiment execution failed")
                
                return success
                
            except Exception as e:
                self.error_handler.handle_error(e, {
                    "component": "ExperimentBridge",
                    "operation": "execute_experiment_with_legacy_config",
                    "tools": [tool.name for tool in tools]
                })
                self.logger.error(f"Bridge execution failed: {e}")
                return False
    
    def execute_experiment_with_config_file(self, config_file: str) -> bool:
        """
        Execute experiment using configuration file.
        
        Args:
            config_file: Path to configuration file
            
        Returns:
            True if experiment completed successfully, False otherwise
        """
        with self.logger.with_context(
            phase="execute_experiment_with_config_file",
            config_file=config_file
        ):
            try:
                # Load configuration from file
                if not Path(config_file).exists():
                    raise FileNotFoundError(f"Configuration file not found: {config_file}")
                
                # Determine if it's legacy or modern format
                experiment_config = self._load_and_convert_config_file(config_file)
                
                # Validate configuration
                experiment_config.validate()
                
                # Create orchestrator and execute
                orchestrator = ExperimentOrchestrator(
                    config=experiment_config,
                    logger=self.logger
                )
                
                # Execute as batch experiment (config file implies comprehensive setup)
                success = orchestrator.execute_batch_experiment()
                
                return success
                
            except Exception as e:
                self.error_handler.handle_error(e, {
                    "component": "ExperimentBridge",
                    "operation": "execute_experiment_with_config_file",
                    "config_file": config_file
                })
                self.logger.error(f"Config file execution failed: {e}")
                return False
    
    def _create_minimal_config(self) -> Dict[str, Any]:
        """Create minimal configuration when legacy config is not available."""
        return {
            "repetitions": 1,
            "timeouts": [60],
            "no_window": True,
            "generate_monitors": True,
            "instrument": True,
            "static_analysis": True,
            "skip_experiment": False,
            "tools": ["monkey"]
        }
    
    def _convert_legacy_config(self, legacy_config: Any, tools: List[AbstractTool]) -> ExperimentConfig:
        """
        Convert legacy configuration to modern ExperimentConfig.
        
        Args:
            legacy_config: Legacy Configuration instance
            tools: List of tool instances
            
        Returns:
            Modern ExperimentConfig instance
        """
        try:
            # Extract values from legacy config with fallbacks
            repetitions = getattr(legacy_config, 'get_int', lambda k, d: d)("repetitions", 1)
            timeouts = getattr(legacy_config, 'get_list', lambda k, d: d)("timeouts", [60])
            no_window = getattr(legacy_config, 'get_bool', lambda k, d: d)("no_window", True)
            generate_monitors = getattr(legacy_config, 'get_bool', lambda k, d: d)("generate_monitors", True)
            instrument = getattr(legacy_config, 'get_bool', lambda k, d: d)("instrument", True)
            static_analysis = getattr(legacy_config, 'get_bool', lambda k, d: d)("static_analysis", True)
            skip_experiment = getattr(legacy_config, 'get_bool', lambda k, d: d)("skip_experiment", False)
            
            # Create tool configurations from tool instances
            tool_configs = []
            for tool in tools:
                tool_config = ToolConfiguration(
                    name=tool.name,
                    enabled=True,
                    parameters={}
                )
                
                # Extract tool-specific parameters if available
                if hasattr(tool, 'get_configuration'):
                    tool_params = tool.get_configuration()
                    tool_config.parameters.update(tool_params)
                
                tool_configs.append(tool_config)
            
            # Create experiment configuration
            experiment_config = ExperimentConfig(
                name=f"legacy_experiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                description="Experiment migrated from legacy main.py execution",
                tools=[tool.name for tool in tools],
                tool_configs=tool_configs,
                applications=ApplicationConfiguration(),  # Use defaults
                execution={
                    "repetitions": repetitions,
                    "timeouts": timeouts,
                    "no_window": no_window,
                    "parallel_execution": False,
                    "max_parallel_tasks": 1,
                    "execution_delay": 0,
                    "resource_limits": {}
                },
                processing={
                    "generate_monitors": generate_monitors,
                    "instrument": instrument,
                    "static_analysis": static_analysis,
                    "skip_experiment": skip_experiment,
                    "process_results": True,
                    "generate_reports": True
                }
            )
            
            self.logger.info("Legacy configuration converted to modern format")
            return experiment_config
            
        except Exception as e:
            self.logger.error(f"Error converting legacy configuration: {e}")
            # Return minimal configuration as fallback
            return ExperimentConfig(
                name="fallback_experiment",
                tools=[tool.name for tool in tools],
                tool_configs=[ToolConfiguration(name=tool.name) for tool in tools]
            )
    
    def _load_and_convert_config_file(self, config_file: str) -> ExperimentConfig:
        """
        Load configuration file and convert to modern format if necessary.
        
        Args:
            config_file: Path to configuration file
            
        Returns:
            Modern ExperimentConfig instance
        """
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        # Check if it's already in modern format
        if self._is_modern_config_format(config_data):
            return ExperimentConfig.from_dict(config_data)
        else:
            # Convert legacy format
            return self._convert_legacy_config_dict(config_data)
    
    def _is_modern_config_format(self, config_data: Dict[str, Any]) -> bool:
        """Check if configuration is in modern format."""
        # Modern format has nested structure with 'execution', 'processing', etc.
        modern_keys = ['execution', 'processing', 'applications', 'tool_configs']
        return any(key in config_data for key in modern_keys)
    
    def _convert_legacy_config_dict(self, config_data: Dict[str, Any]) -> ExperimentConfig:
        """
        Convert legacy configuration dictionary to modern format.
        
        Args:
            config_data: Legacy configuration dictionary
            
        Returns:
            Modern ExperimentConfig instance
        """
        # Extract tool configurations
        tools_config = config_data.get("tools", [])
        tool_configs = []
        tool_names = []
        
        for tool_config in tools_config:
            if isinstance(tool_config, str):
                # Simple tool name
                tool_names.append(tool_config)
                tool_configs.append(ToolConfiguration(name=tool_config))
            elif isinstance(tool_config, dict):
                # Detailed tool configuration
                name = tool_config.get("name", "unknown")
                tool_names.append(name)
                
                variants = []
                if "variant" in tool_config:
                    variants.append(tool_config["variant"])
                if "variants" in tool_config:
                    variants.extend(tool_config["variants"])
                
                parameters = tool_config.get("params", {})
                
                tool_configs.append(ToolConfiguration(
                    name=name,
                    variants=variants,
                    parameters=parameters
                ))
        
        # Create modern configuration
        return ExperimentConfig(
            name=config_data.get("name", f"converted_experiment_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
            description=config_data.get("description", "Converted from legacy configuration"),
            tools=tool_names,
            tool_configs=tool_configs,
            execution={
                "repetitions": config_data.get("repetitions", 1),
                "timeouts": config_data.get("timeouts", [60]),
                "no_window": config_data.get("no_window", True),
                "parallel_execution": config_data.get("parallel_execution", False),
                "max_parallel_tasks": config_data.get("max_parallel_tasks", 1),
                "execution_delay": 0,
                "resource_limits": {}
            },
            processing={
                "generate_monitors": config_data.get("generate_monitors", True),
                "instrument": config_data.get("instrument", True),
                "static_analysis": config_data.get("static_analysis", True),
                "skip_experiment": config_data.get("skip_experiment", False),
                "process_results": True,
                "generate_reports": True
            }
        )


# Global bridge instance for easy access from main.py
_bridge_instance: Optional[ExperimentBridge] = None


def get_experiment_bridge() -> ExperimentBridge:
    """
    Get the global experiment bridge instance.
    
    Returns:
        ExperimentBridge instance
    """
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = ExperimentBridge()
    return _bridge_instance


def execute_experiment_via_bridge(tools: List[AbstractTool], 
                                 legacy_config: Optional[Any] = None) -> bool:
    """
    Convenience function for executing experiments via bridge.
    
    Args:
        tools: List of tool instances
        legacy_config: Optional legacy configuration
        
    Returns:
        True if experiment completed successfully, False otherwise
    """
    bridge = get_experiment_bridge()
    return bridge.execute_experiment_with_legacy_config(tools, legacy_config)


def execute_config_file_via_bridge(config_file: str) -> bool:
    """
    Convenience function for executing config file experiments via bridge.
    
    Args:
        config_file: Path to configuration file
        
    Returns:
        True if experiment completed successfully, False otherwise
    """
    bridge = get_experiment_bridge()
    return bridge.execute_experiment_with_config_file(config_file)