from typing import List, Optional

from rv_android_core.tools.abstract_tool import AbstractTool
from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from rv_tools import ToolRegistry


class ExperimentToolRegistry:
    _instance: Optional['ExperimentToolRegistry'] = None

    @classmethod
    def get_instance(cls) -> 'ExperimentToolRegistry':
        """
        Get the singleton instance of the tool registry.

        Returns:
            ToolRegistry instance
        """
        if cls._instance is None:
            cls._instance = ExperimentToolRegistry()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """
        Reset the singleton instance for testing purposes.
        """
        cls._instance = None

    def __init__(self):
        """
        Initialize the registry with rv-android-core infrastructure.
        """
        # Set up standardized logging
        logging_manager = LoggingManager.get_instance()
        self.logger = logging_manager.get_logger(
            "rv_experiment.tools",
            {CONTEXT_COMPONENT: "ExperimentToolRegistry"}
        )

        # Initialize error handler
        # TODO usar
        # self.error_handler = ErrorHandler.get_instance()

        # Initialize experiment tool registry
        self.registry = ToolRegistry.get_instance()

        self.logger.info("Experiment tool registry initialized")

    def register_external_tools(self):
        """
        Register external tools in the rv-tools registry.

        This function respects module hierarchy by registering tools from
        modules that depend on rv-tools (not vice versa).
        """
        try:

            # Register RVAndroid tool
            try:
                from rvandroid_tool.tools.rvandroid.tool import RVAndroidTool
                self.registry.register_tool_class(RVAndroidTool)
                self.logger.info("Successfully registered RVAndroid tool in tools registry")
            except ImportError as e:
                self.logger.warning(f"RVAndroid tool not available: {e}")
            except Exception as e:
                self.logger.error(f"Failed to register RVAndroid tool: {e}")

        except ImportError as e:
            self.logger.error(f"rv-tools registry not available: {e}")
        except Exception as e:
            self.logger.error(f"Failed to access tool registry: {e}")
            import traceback
            traceback.print_exc()

    def get_all_tools(self) -> List[AbstractTool]:
        return self.registry.get_all_tools()

    def get_tool_variants(self, name: str) -> list[str]:
        return self.registry.get_tool_variants(name)
