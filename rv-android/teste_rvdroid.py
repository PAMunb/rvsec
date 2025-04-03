import os
import sys

from rvandroid.app import App
from rvandroid.config.component_configurator import ComponentConfigurator
from rvandroid.domain.static import StaticAnalysisData
from rvandroid.llm.ollama_llm import OllamaLLM
from rvandroid.parser.static import static_analysis_parser
from rvandroid.rvdroid import RVDroidService
from rvandroid.util.logging.manager import LoggingManager


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
    use_llm = False

    # Set up logging
    logger = setup_logging(False)
    logger.info("Starting RVDroid runner")
    logger.info(f"App: {app.name}")
    logger.info(f"Package: {app.package_name}")
    logger.info(f"Device: {device}")
    logger.info(f"Timeout: {timeout} seconds")
    logger.info(f"LLM guidance: {'Enabled' if use_llm else 'Disabled'}")

    try:
        # Initialize service
        service = RVDroidService(device_id=device, static_data=static_data, use_llm=use_llm, preferred_strategy="VisualAwareStrategy")

        # Start testing
        logger.info(f"Starting testing of {app.package_name}")
        result = service.start_testing(
            package_name=app.package_name,
            activity=app.apk.get_main_activity(),
            timeout=timeout,
            llm_guidance=use_llm
        )

        if not result:
            logger.error("Failed to start testing")
            return 1

        # Execute testing loop
        logger.info("Executing testing loop")
        results = service.execute_testing_loop()

        # Process and display results
        logger.info("Testing completed")
        logger.info(f"Actions executed: {results.get('actions_executed', 0)}")
        logger.info(f"New states discovered: {results.get('new_states', 0)}")
        logger.info(f"Elapsed time: {results.get('elapsed_time', 0):.2f} seconds")

        if use_llm:
            logger.info(f"LLM guidance count: {results.get('llm_guidance_count', 0)}")

        # Clean up
        service.cleanup()

        return 0

    except KeyboardInterrupt:
        logger.info("Testing interrupted by user")
        return 0

    except Exception as e:
        logger.error(f"Error during test execution: {e}")
        return 1


def get_ollama(static_data: StaticAnalysisData) -> ComponentConfigurator:
    configurator = ComponentConfigurator(static_data)
    configurator.set_llm(
        llm_type=OllamaLLM.NAME,
        model=OllamaLLM.GEMMA,
        base_url="http://localhost:11434"
    )
    configurator.set_strategy("single_action")
    configurator.set_parser("uiautomator")
    configurator.set_visitor("enhanced")
    return configurator


if __name__ == "__main__":
    screenshots_folder = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    apk = "cryptoapp.apk"
    app_folder = screenshots_folder + "/" + apk

    application = App(os.path.join(app_folder, apk))
    package = application.package_name

    static = static_analysis_parser.read_static_analysis_files(app_folder, apk, package)

    sys.exit(main(application, static))
