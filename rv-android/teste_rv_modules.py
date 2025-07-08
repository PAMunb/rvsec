import os
import logging
import sys
from pathlib import Path

from rv_android_core.domain.app import App
from rv_monitor_generator import RuntimeVerificationGenerator, RVGeneratorConfig
from rv_instrumentation import RVInstrumentation, RVInstrumentationConfig
from rv_static_analysis import RVStaticAnalysisConfig, StaticAnalyzer
from rvandroid.util.logging.manager import LoggingManager


def setup_logging(debug: bool = True):
    """Set up logging configuration."""
    # Setup basic logging first
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )

    # Get the logging manager
    logging_manager = LoggingManager.get_instance()

    # Configure output to show all rvandroid logs including module logs
    logging_manager.configure_output(
        console=True,
        file=False,
        console_level=10 if debug else 20,  # DEBUG (10) or INFO (20)
        file_level=10,  # DEBUG
        json_format=False
    )

    return logging_manager.get_logger('teste.rv_monitor')


def generate_monitors(rvsec_root, specs_dir, output_dir):
    print(f"Generating monitors for specs in {specs_dir} and saving to {output_dir}")
    config = RVGeneratorConfig(
        rvsec_root=rvsec_root,
        mop_specs_dir=specs_dir
    )

    generator = RuntimeVerificationGenerator(config)

    generator.generate_monitors(
        output_dir=output_dir
    )

def instrument(apks_dir, rvsec_root, monitor_output_dir, instrumented_dir):
    # Create configuration
    config = RVInstrumentationConfig(
        rvsec_root=rvsec_root,
        monitor_output_dir=monitor_output_dir,
        instrumented_dir=instrumented_dir
    )

    # Initialize instrumentation engine
    instrumentation = RVInstrumentation(config)

    # Instrument APKs
    errors = instrumentation.instrument_apks(
        apks_dir=apks_dir,
        results_dir=instrumented_dir
    )

    # Check results
    if not errors:
        print("All APKs instrumented successfully")
    else:
        print(f"Instrumentation failed for {len(errors)} APKs")
        for error in errors:
            print(f"Error: {error}")

def static_analysis(apk, specs_dir, rt_jar, rvsec_root, instrumented_dir):
    config = RVStaticAnalysisConfig(
        rvsec_root=rvsec_root,
        rt_jar=rt_jar,
        mop_dir=specs_dir,
        output_dir=instrumented_dir
    )
    app = App(apk)

    analyzer = StaticAnalyzer(app, config, output_dir=instrumented_dir)

    result = analyzer.analyze()

    # Process results
    if result and result.success:
        print("Static analysis completed successfully")

        # Get metrics
        metrics = analyzer.get_metrics()
        print(f"Execution times: {result.execution_times}")
        print(f"Metrics: {metrics}")
    else:
        print(f"Static analysis failed: {result.errors if result else 'Unknown error'}")


if __name__ == '__main__':
    logger = setup_logging()

    RVSEC_DIR = os.path.join(os.getcwd(), os.path.abspath(".."))
    MOP_BASE_DIR = os.path.join(RVSEC_DIR, "rvsec-mop", "src", "main", "resources")
    MOP_JCA_DIR = os.path.join(MOP_BASE_DIR, "jca")
    MOP_GENERIC_DIR = os.path.join(MOP_BASE_DIR, "generic")
    specs_mini = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/specs_mini"
    rt_jar = os.path.join(Path.home(), ".sdkman", "candidates", "java", "8.0.302-open", "jre", "lib", "rt.jar")

    apks_dir = "/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples"
    apk_name = "cryptoapp.apk"
    apk = os.path.join(apks_dir, apk_name)
    monitors_output_dir = "output/monitors/jca"
    instrumented_dir = "output/instrumented"
    instrumented_apk = ""

    generate_monitors(RVSEC_DIR, specs_mini, monitors_output_dir)
    instrument(apks_dir, RVSEC_DIR, monitors_output_dir, instrumented_dir)
    static_analysis(apk, specs_mini, rt_jar, RVSEC_DIR, instrumented_dir)
