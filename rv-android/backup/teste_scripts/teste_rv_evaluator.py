#!/usr/bin/env python3
"""
Manual test for rv-experiment integration with rv-platform.

This test validates that rv-experiment CLI maintains backward compatibility
while internally using rv-platform for task execution.
"""

import os
import sys
import subprocess
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

from rv_evaluator.config import ModelToTest

# Setup RVSEC_HOME before importing modules
current_directory = os.getcwd()
parent_directory = os.path.dirname(current_directory)

# Add the modules to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "modules" / "rv-android-core" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-platform" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-experiment" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-tools" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-coverage" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-static-analysis" / "src"))

# Import constants after path setup
from rv_android_core import constants
from rv_llm.llm.ollama_llm import OllamaLLM
# Add RV-Android to path (adjust as needed for your setup)
# sys.path.insert(0, '/path/to/rv-android')

from rv_evaluator.evaluator import LLMEvaluator
from rv_evaluator import config

# Set RVSEC_HOME environment variable
os.environ[constants.ENV_RVSEC_HOME] = parent_directory


def setup_logging(debug: bool = True):
    """Set up logging configuration."""
    import logging
    from rv_android_core.util.logging.manager import LoggingManager

    # Setup basic logging first
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )

    # Silence noisy third-party loggers for clean CLI output
    for noisy_logger in ["androguard", "matplotlib", "PIL", "requests", "urllib3"]:
        logging.getLogger(noisy_logger).setLevel(logging.ERROR)

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

    return logging_manager.get_logger('teste_rv_evaluator')


def quick_evaluation():
    """Run a quick evaluation with minimal configurations for testing."""
    print("=== QUICK EVALUATION MODE ===")

    try:
        evaluator = LLMEvaluator(
            prompts_dir="/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-evaluator/src/rv_evaluator/prompts",
            output_dir="./quick_results"
        )

        detailed_file, summary_file, analysis_file = evaluator.run_evaluation()

        print(f"\nQuick evaluation completed!")
        print(f"Results saved to: ./quick_results/")

        # # Show quick summary
        # summary = evaluator.get_evaluation_summary()
        # if summary.get("status") == "completed":
        #     best = summary["best_configuration"]
        #     print(f"\nBest config: {best['model']} | {best['strategy']} | T={best['temperature']}")
        #     print(f"Score: {best['overall_score']:.1f}/100")

    finally:
        print("FIM DE FESTA!!!")


def full_evaluation():
    """Run a comprehensive evaluation with all configured settings."""
    print("=== FULL EVALUATION MODE ===")

    # Create timestamped output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"./evaluation_results_{timestamp}"

    evaluator = LLMEvaluator(
        prompts_dir="./prompts",
        output_dir=output_dir
    )

    print(f"Starting full evaluation...")
    print(f"Results will be saved to: {output_dir}")

    detailed_file, summary_file, analysis_file = evaluator.run_evaluation()

    print(f"\nFull evaluation completed!")
    print(f"Detailed results: {detailed_file}")
    print(f"Summary results: {summary_file}")
    print(f"Analysis report: {analysis_file}")

    return output_dir


if __name__ == "__main__":
    setup_logging(True)

    quick_evaluation()
