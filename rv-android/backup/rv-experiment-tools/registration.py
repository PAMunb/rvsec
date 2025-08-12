"""
Tool registration system for experiment execution.

This module manages the registration and availability of testing tools
within the experiment execution environment.
"""

from typing import Dict, Type, List, Optional
from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.util.error.error_handler import ErrorHandler
from rv_android_core.util.logging.manager import LoggingManager
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.error.exceptions import ToolRegistrationError

# TODO rever essa class inteira ... nao eh assim que vamos registrar a ferramenta ... ela nem esta registrada desse jeito
# olhe alguns exemplos para entender:
# modules/rv-tools/src/rv_tools/registry/registry.py
# modules/rv-tools/src/rv_tools/builtin/ape/tool.py
# modules/rv-tools/src/rv_tools/builtin/monkey/tool.py

class ToolRegistrationManager:
    """
    Manages registration and retrieval of testing tools for experiment execution.
    
    ### Architectural Role:
    - Provides centralized tool registry for experiment coordination
    - Handles dynamic tool loading and availability checking
    - Supports conditional registration based on module availability
    - Integrates with rv-android-core error handling infrastructure
    
    ### Registration Strategy:
    - Tools register themselves during module import
    - Failed registrations are logged but don't halt system initialization
    - Registry supports tool variants and configuration parameters
    """
    
    _instance: Optional['ToolRegistrationManager'] = None
    
    def __init__(self):
        """Initialize tool registration manager."""
        self.registered_tools: Dict[str, Type[AbstractTool]] = {}
        
        # Initialize logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_experiment.tools.registration",
            {CONTEXT_COMPONENT: "ToolRegistrationManager"}
        )

    @classmethod
    def get_instance(cls) -> 'ToolRegistrationManager':
        """Get singleton instance of tool registration manager."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @ErrorHandler.handle_errors(
        component="ToolRegistrationManager",
        operation="register_tool"
    )
    def register_tool(self, name: str, tool_class: Type[AbstractTool]) -> None:
        """
        Register a testing tool for experiment use.
        
        Args:
            name: Tool identifier name
            tool_class: AbstractTool implementation class
            
        Raises:
            ToolRegistrationError: When tool registration fails validation
        """
        if not issubclass(tool_class, AbstractTool):
            raise ToolRegistrationError(f"Tool {name} must extend AbstractTool")
            
        if not hasattr(tool_class, 'TOOL_SPEC') or tool_class.TOOL_SPEC is None:
            raise ToolRegistrationError(f"Tool {name} missing required TOOL_SPEC")
            
        self.registered_tools[name] = tool_class
        self.logger.info(f"Registered tool: {name} ({tool_class.__name__})")

    def get_tool_class(self, name: str) -> Optional[Type[AbstractTool]]:
        """Get tool class by name."""
        return self.registered_tools.get(name)

    def get_available_tools(self) -> List[str]:
        """Get list of available tool names."""
        return list(self.registered_tools.keys())
