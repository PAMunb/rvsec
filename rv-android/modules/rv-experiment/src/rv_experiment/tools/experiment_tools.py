"""
External tool registration for rv-experiment execution.

This module provides comprehensive external tool registration using constants
and modern architecture patterns. All legacy code has been removed.
"""

from typing import List, Optional

from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_tools import ToolRegistry

from rv_experiment.constants import (
    EXTERNAL_TOOL_RVANDROID,
    EXTERNAL_TOOL_RVDROID,
    EXTERNAL_TOOL_RVAGENT,
    TOOL_REGISTRATION_SUCCESS,
    TOOL_REGISTRATION_FAILED,
    TOOL_REGISTRATION_IMPORT_ERROR
)


class ExperimentToolRegistry:
    """
    External tool registration system for experiment execution.
    
    Manages registration of tools from modules that depend on rv-tools,
    respecting module hierarchy and architectural boundaries.
    """
    
    _instance: Optional['ExperimentToolRegistry'] = None

    @classmethod
    def get_instance(cls) -> 'ExperimentToolRegistry':
        """Get singleton instance of tool registry."""
        if cls._instance is None:
            cls._instance = ExperimentToolRegistry()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance for testing."""
        cls._instance = None

    def __init__(self):
        """Initialize registry with rv-android-core infrastructure."""
        # Set up logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_experiment.tools",
            {CONTEXT_COMPONENT: "ExperimentToolRegistry"}
        )
        
        # Initialize error handler
        self.error_handler = ErrorHandler.get_instance()

        # Get rv-tools registry instance
        self.registry = ToolRegistry.get_instance()
        
        
        # Track if external tools have been registered to prevent duplicates
        self._external_tools_registered = False

        self.logger.info("Experiment tool registry initialized")
        
        # Automatically register external tools on first initialization
        self.register_external_tools()

    @ErrorHandler.handle_errors(
        component="ExperimentToolRegistry",
        operation="register_external_tools"
    )
    def register_external_tools(self) -> None:
        """
        Register all external tools respecting module hierarchy.
        
        Registers tools from modules that depend on rv-tools:
        - rvandroid-tool (module 10 > rv-tools module 8)
        - rvdroid-tool (module 11 > rv-tools module 8)
        
        This method is idempotent - it can be called multiple times safely.
        """
        # Check if already registered to prevent duplicates
        if self._external_tools_registered:
            self.logger.debug("External tools already registered, skipping")
            return
            
        self.logger.info("Starting external tools registration")
        
        # Register RVAndroid tool
        self._register_rvandroid_tool()

        # Register RVDroid tool
        self._register_rvdroid_tool()

        # Register RVAgent tool
        self._register_rvagent_tool()

        # Mark as registered
        self._external_tools_registered = True
        
        # Log registration summary
        self._log_registration_summary()
        
        self.logger.info("External tools registration completed")

    def _register_rvandroid_tool(self) -> None:
        """Register RVAndroid tool with comprehensive error handling."""
        try:
            from rvandroid_tool.tools.rvandroid.tool import RVAndroidTool
            self.registry.register_tool_class(RVAndroidTool)
            
            self.logger.info(TOOL_REGISTRATION_SUCCESS.format(EXTERNAL_TOOL_RVANDROID))
        except ImportError as e:
            self.logger.warning(TOOL_REGISTRATION_IMPORT_ERROR.format(
                EXTERNAL_TOOL_RVANDROID.title(), e
            ))
        except Exception as e:
            self.logger.error(TOOL_REGISTRATION_FAILED.format(EXTERNAL_TOOL_RVANDROID, e))
            import traceback
            traceback.print_exc()

    def _register_rvdroid_tool(self) -> None:
        """Register RVDroid tool with comprehensive error handling."""
        try:
            from rvdroid_tool.tools.tool import RVDroidTool
            self.registry.register_tool_class(RVDroidTool)
            self.logger.info(TOOL_REGISTRATION_SUCCESS.format(EXTERNAL_TOOL_RVDROID))
        except ImportError as e:
            self.logger.warning(TOOL_REGISTRATION_IMPORT_ERROR.format(
                EXTERNAL_TOOL_RVDROID.title(), e
            ))
        except Exception as e:
            self.logger.error(TOOL_REGISTRATION_FAILED.format(EXTERNAL_TOOL_RVDROID, e))
            import traceback
            traceback.print_exc()

    def _register_rvagent_tool(self) -> None:
        """Register RVAgent tool with comprehensive error handling."""
        try:
            from rvagent_tool.tools.rvagent.tool import RVAgentTool
            self.registry.register_tool_class(RVAgentTool)
            self.logger.info(TOOL_REGISTRATION_SUCCESS.format(EXTERNAL_TOOL_RVAGENT))
        except ImportError as e:
            self.logger.warning(TOOL_REGISTRATION_IMPORT_ERROR.format(
                EXTERNAL_TOOL_RVAGENT.title(), e
            ))
        except Exception as e:
            self.logger.error(TOOL_REGISTRATION_FAILED.format(EXTERNAL_TOOL_RVAGENT, e))
            import traceback
            traceback.print_exc()

    def _log_registration_summary(self) -> None:
        """Log comprehensive registration summary."""
        try:
            registered_tools = self.registry.get_all_tools()
            tool_names = [tool.name for tool in registered_tools]
            self.logger.info(f"Total registered tools: {len(tool_names)}")
            self.logger.info(f"Available tools: {', '.join(sorted(tool_names))}")
            
            # Log variant information for external tools
            for tool_name in [EXTERNAL_TOOL_RVANDROID, EXTERNAL_TOOL_RVDROID, EXTERNAL_TOOL_RVAGENT]:
                if self.registry.has_tool(tool_name):
                    variants = self.registry.get_tool_variants(tool_name)
                    self.logger.info(f"{tool_name} variants: {', '.join(variants)}")
                    
        except Exception as e:
            self.logger.warning(f"Failed to generate registration summary: {e}")

    def get_all_tools(self) -> List[AbstractTool]:
        """Get all registered tools."""
        return self.registry.get_all_tools()

    def get_tool_variants(self, name: str) -> List[str]:
        """Get variants for specific tool."""
        return self.registry.get_tool_variants(name)
        
    def has_tool(self, tool_name: str) -> bool:
        """Check if tool is registered."""
        return self.registry.has_tool(tool_name)
        
    def get_registry_info(self) -> dict:
        """Get comprehensive registry information."""
        return self.registry.get_registry_info()
