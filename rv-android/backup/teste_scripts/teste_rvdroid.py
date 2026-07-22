import os
import sys

from rv_android_core.domain.app import App
from rv_android_core.domain.static import StaticAnalysisData
from rv_llm import OllamaLLM
from rv_static_analysis.parser.static import static_analysis_parser
from rvdroid_tool.tools.tool import RVDroidTool
from rv_android_core.util.logging.manager import LoggingManager
from rvdroid_tool.config.tool_config import RVDroidToolConfig
from rv_llm.config.llm_config import LLMConfig
from rv_llm.config.prompt_config import PromptConfig
from rv_llm.llm.constants import LLMType, PromptStrategyType
from rv_android_core.domain.task import Task


def setup_logging(debug: bool = False):
    """Set up logging configuration."""
    logging_manager = LoggingManager.get_instance()

    # Configure output
    logging_manager.configure_output(
        console=True,
        file=False,
        console_level=10 if debug else 20,  # DEBUG (10) or INFO (20)
        file_level=10,  # DEBUG
        json_format=False
    )

    logger = logging_manager.get_logger('teste.rvdroid')
    return logger


def main(app: App, static_data: StaticAnalysisData):
    device = "emulator-5554"
    timeout = 1200
    use_llm = True # Set to True to test LLM guidance

    # Set up logging
    logger = setup_logging(False)
    logger.info("Starting RVDroid test script")
    logger.info(f"App: {app.name}")
    logger.info(f"Package: {app.package_name}")
    logger.info(f"Device: {device}")
    logger.info(f"Timeout: {timeout} seconds")
    logger.info(f"LLM guidance: {'Enabled' if use_llm else 'Disabled'}")

    try:
        # Create RVDroidToolConfig
        tool_config = RVDroidToolConfig(
            device_id=device,
            execution_timeout=timeout,
            llm_enabled=use_llm,
            # Configure LLM and Prompt if LLM is enabled
            llm_config=LLMConfig(
                llm_type=LLMType.OLLAMA,
                llm_model=OllamaLLM.GEMMA,
                temperature=0.2,
                top_p=0.9,
                max_tokens=800,
                vision=True
            ),
            prompt_config=PromptConfig(
                strategy_type=PromptStrategyType.STANDARD # Our GuidanceStrategy
            )
        )

        # Create a dummy Task object
        # In a real scenario, Task would come from the experiment framework
        task = Task(
            id="test_task_1",
            name="Manual RVDroid Test",
            app=app,
            static_data=static_data,  # Add static data to task
            config={"activity": app.apk.get_main_activity(), "timeout": timeout},
            results_dir="./rvdroid_manual_results" # Placeholder results directory
        )

        # Initialize RVDroidTool
        rvdroid_tool = RVDroidTool()
        rvdroid_tool.configure(tool_config)

        # Execute the tool's logic
        rvdroid_tool.execute_tool_specific_logic(task, app)

        logger.info("RVDroid test script completed.")
        return 0

    except KeyboardInterrupt:
        logger.info("Testing interrupted by user")
        return 0

    except Exception as e:
        logger.error(f"Error during test execution: {e}")
        return 1


if __name__ == "__main__":
    screenshots_folder = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples/cryptoapp" # Assuming cryptoapp is a folder
    apk_name = "cryptoapp.apk"
    apk_path = os.path.join(screenshots_folder, apk_name)

    # Ensure the APK exists
    if not os.path.exists(apk_path):
        print(f"Error: APK not found at {apk_path}")
        sys.exit(1)

    application = App(apk_path)
    package = application.package_name

    static = static_analysis_parser.read_static_analysis_files(screenshots_folder, apk_name, package)

    sys.exit(main(application, static))




# Legacy function - remove in future versions
# This function is not used in the new architecture
