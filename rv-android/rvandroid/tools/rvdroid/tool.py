# rvandroid/tools/rvdroid/tool.py
"""
RVDroid tool implementation with configuration support.
"""
import os
import json

from rvandroid.app import App
from rvandroid.commands.command import Command
# Import ComponentConfigurator only when needed, not at module level
# from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.experiment.event.bus import EventBus, EventType
from rvandroid.experiment.task.task_model import Task, TaskConfig, TaskResult, TaskStatus
from rvandroid.llm.constants import ScreenParserType
from rvandroid.parser.screen.visitor.visitor_factory import VisitorFactory
from rvandroid.rvdroid.core.service import RVDroidService
from rvandroid.rvdroid.orchestration.lifecycle import LifecycleManager, ExecutionPhase
from rvandroid.rvdroid.orchestration.recovery import RecoveryManager, ErrorSeverity, RecoveryStrategy
from rvandroid.tools.configurable_tool import ConfigurableTool
from rvandroid.tools.registry import ToolRegistry
from rvandroid.parser.static.static_analysis_parser import StaticAnalysisParser
from rvandroid.util.logging.constants import CONTEXT_TASK_ID, CONTEXT_APP_NAME, CONTEXT_TOOL_NAME, CONTEXT_COMPONENT
from rvandroid.util.logging.manager import LoggingManager


class RVDroidTool(ConfigurableTool):
    """
    A specialized tool implementation for RVDroid, a UIAutomator2-based testing tool integrated with RV-Android.

    ### Architectural Decisions:
    - Extends ConfigurableTool for standardized configuration handling
    - Integrates with ComponentConfigurator for flexible AI configuration
    - Provides a modular interface to UIAutomator2-based testing

    ### Role in the System:
    - Serves as the main entry point for UIAutomator2-based testing in RV-Android
    - Integrates AI-guided testing with UIAutomator2 capabilities
    - Provides a bridge between RV-Android and UIAutomator2 testing
    - Enables intelligent, adaptive test exploration in native Android environments
    """

    def __init__(self):
        """Initialize the RVDroid tool with default configuration."""
        super().__init__(
            "rvdroid",
            "UIAutomator2-based Android testing tool with AI-guided exploration",
            "br.unb.cic.rvsec"
        )

        # Default configuration
        self.config = {
            "use_llm": False,  # Default to no LLM guidance
            "preferred_strategy": "VisualAwareStrategy",
            "use_screenshot_analysis": True,
            "screenshot_analysis_level": "standard",
        }
        
        # We'll initialize component_config lazily
        self.component_config = None

    def configure_tool_specific(self, config):
        """Configure RVDroid-specific parameters."""
        # Update parameters if specified
        if "use_llm" in config:
            self.config["use_llm"] = bool(config["use_llm"])
            
        if "preferred_strategy" in config:
            self.config["preferred_strategy"] = config["preferred_strategy"]
            
        if "use_screenshot_analysis" in config:
            self.config["use_screenshot_analysis"] = bool(config["use_screenshot_analysis"])
            
        if "screenshot_analysis_level" in config:
            self.config["screenshot_analysis_level"] = config["screenshot_analysis_level"]

    def execute_tool_specific_logic(self, task: Task, app: App):
        """Execute RVDroid with the configured parameters."""
        # Set up logging using LoggingManager
        logging_manager = LoggingManager.get_instance()
        logger = logging_manager.get_logger(
            'tools.rvdroid',
            {
                CONTEXT_TASK_ID: task.id,
                CONTEXT_APP_NAME: app.name,
                CONTEXT_TOOL_NAME: self.name,
                CONTEXT_COMPONENT: 'RVDroidTool'
            }
        )

        # Get event bus for publishing events
        event_bus = EventBus.get_instance()
        
        # Log execution configuration
        logger.info(f"Executing {self.name} with configuration: {self.config}")
        
        # Initialize component_config if not already done
        if self.component_config is None:
            # Import here to avoid circular import
            from rvandroid.config.component_configurator import ComponentConfigurator
            self.component_config = ComponentConfigurator()
            # Set defaults
            self.component_config.set_parser(ScreenParserType.DROIDBOT)
            self.component_config.set_visitor(VisitorFactory.DEFAULT)
            
        logger.info(f"RVDroid tool initialized with configuration: {self.component_config.describe_configuration()}")

        # Publish tool start event
        event_bus.publish_task_event(
            EventType.TOOL_STARTED,
            task_id=task.id,
            details={"tool": "rvdroid"},
            source="RVDroidTool"
        )

        try:
            # Get static analysis data if not provided
            static_data = task.static_data
            if not static_data and app.path:
                # Load static data from pre-generated files (using the same file pattern)
                app_path = app.path
                app_dir = os.path.dirname(app_path)
                app_basename = os.path.basename(app_path)
                
                # Construct paths to static analysis files
                # Try both formats: app_basename.extension and app_basename.apk.extension
                gesda_file = os.path.join(app_dir, f"{app_basename}.gesda")
                gator_file = os.path.join(app_dir, f"{app_basename}.wtg")
                reach_file = os.path.join(app_dir, f"{app_basename}.reach")
                
                # Check if files exist, if not try alternate format with .apk
                if not os.path.isfile(gesda_file):
                    gesda_file = os.path.join(app_dir, f"{app_basename}.apk.gesda")
                if not os.path.isfile(gator_file):
                    gator_file = os.path.join(app_dir, f"{app_basename}.apk.wtg")
                if not os.path.isfile(reach_file):
                    reach_file = os.path.join(app_dir, f"{app_basename}.apk.reach")
                
                # Check if the files exist
                if os.path.isfile(gesda_file):
                    logger.info(f"Found existing static analysis files for {app_basename}")
                    
                    # Parse the static analysis data
                    parser = StaticAnalysisParser()
                    
                    # Print detailed debug info
                    logger.info(f"Static analysis files for parsing:")
                    logger.info(f"  GESDA: {gesda_file} (exists: {os.path.isfile(gesda_file)})")
                    logger.info(f"  GATOR: {gator_file} (exists: {os.path.isfile(gator_file)})")
                    logger.info(f"  REACH: {reach_file} (exists: {os.path.isfile(reach_file)})")
                    
                    # Use empty strings instead of None for missing files
                    reach_file_path = reach_file if os.path.isfile(reach_file) else ""
                    gator_file_path = gator_file if os.path.isfile(gator_file) else ""
                    
                    try:
                        # Try parsing with all files
                        static_data = parser.parse(
                            reach_file=reach_file_path,
                            gator_file=gator_file_path,
                            gesda_file=gesda_file,
                            package=app.package_name
                        )
                    except Exception as e:
                        logger.error(f"Error parsing with reach file: {str(e)}")
                        logger.info("Trying to parse without reach file")
                        
                        # Fallback: try parsing without reach file
                        try:
                            static_data = parser.parse(
                                reach_file="",
                                gator_file=gator_file_path,
                                gesda_file=gesda_file,
                                package=app.package_name
                            )
                        except Exception as fallback_error:
                            logger.error(f"Fallback error: {str(fallback_error)}")
                            # Last resort: create minimal static data
                            from rvandroid.domain.classes import Classes
                            from rvandroid.domain.window import Windows
                            from rvandroid.domain.wtg import WindowTransitionGraph
                            static_data = StaticAnalysisData(Classes(), Windows(), WindowTransitionGraph())
                    logger.info(f"Successfully loaded static analysis data for {app_basename}")
                else:
                    logger.warning(f"No static analysis files found for {app_basename}")

            # Get service configuration parameters with fallbacks
            device_id = task.config.device_id if hasattr(task.config, 'device_id') else "emulator-5554"
            timeout = task.config.timeout if hasattr(task.config, 'timeout') else 300
            use_llm = self.config.get("use_llm", True)
            preferred_strategy = self.config.get("preferred_strategy", "VisualAwareStrategy")
            use_screenshot_analysis = self.config.get("use_screenshot_analysis", True)
            
            # Lazily initialize the component configurator if needed
            if self.component_config is None:
                # Import here to avoid circular import
                from rvandroid.config.component_configurator import ComponentConfigurator
                self.component_config = ComponentConfigurator()
                # Set defaults
                self.component_config.set_parser("uiautomator")
                self.component_config.set_visitor("enhanced")
            
            # Create RVDroid service with configured options
            service = RVDroidService(
                static_data=static_data,
                config=self.component_config,
                device_id=device_id,
                use_llm=use_llm,
                preferred_strategy=preferred_strategy,
                use_screenshot_analysis=use_screenshot_analysis,
                execution_timeout=timeout
            )

            # Prepare UIAutomator2 server setup
            logger.info("Starting UIAutomator2 server")

            # Start UIAutomator2 server and initialize
            start_server_cmd = Command("adb", [
                "-s", 
                task.config.device_id, 
                "shell",
                "am",
                "instrument",
                "-w",
                "io.appium.uiautomator2.server.test/androidx.test.runner.AndroidJUnitRunner"
            ])
            start_server_cmd.invoke()

            # Start RVDroid testing
            with open(task.result.trace_file, "wb") as trace_file:
                # Start the app and begin testing
                if service.start_testing(app.package_name):
                    logger.info(f"Successfully started testing {app.package_name}")
                    
                    # Execute the main testing loop
                    results = service.execute_testing_loop()
                    
                    # Write results to trace file
                    import json
                    trace_file.write(json.dumps(results, default=str).encode('utf-8'))
                    
                    # Stop testing and cleanup
                    service.stop_testing()
                else:
                    logger.error(f"Failed to start testing for {app.package_name}")
                    trace_file.write(b"ERROR: Failed to start testing")

            # Process results and generate coverage information
            service.process_results(task.result.logcat_file)

            # Cleanup resources
            service.cleanup()

            logger.info("RVDroid execution completed successfully")

        except Exception as e:
            logger.error(f"Error running RVDroid tool: {e}", exc_info=True)
            raise
        finally:
            # Publish tool end event
            event_bus.publish_task_event(
                EventType.TOOL_STOPPED,
                task_id=task.id,
                details={"tool": "rvdroid"},
                source="RVDroidTool"
            )

            # Ensure UIAutomator2 server is stopped
            try:
                stop_server_cmd = Command("adb", [
                    "-s", 
                    task.config.device_id,
                    "shell",
                    "am",
                    "force-stop",
                    "io.appium.uiautomator2.server"
                ])
                stop_server_cmd.invoke()
            except Exception as e:
                logger.warning(f"Error stopping UIAutomator2 server: {e}")


# Register the tool with the registry
ToolRegistry.get_instance().register_tool(RVDroidTool())
