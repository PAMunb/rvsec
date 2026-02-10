# rvandroid/llm/evaluator/runner.py
"""
Main execution script for the LLM evaluation system.

This script provides the entry point for running comprehensive LLM evaluations,
handling initialization, execution, and result reporting.

### Architectural Decisions:
- Implements a simple, direct execution approach without CLI complexity
- Provides comprehensive logging and progress tracking
- Handles graceful error recovery and cleanup
- Supports configurable execution parameters through hardcoded settings
- Generates complete evaluation reports with actionable insights

### Role in the System:
- Acts as the primary execution entry point for LLM evaluation
- Coordinates the complete evaluation workflow from start to finish
- Provides progress monitoring and status reporting
- Handles error conditions gracefully with detailed logging
- Generates comprehensive results for decision making

### Key Considerations:
- Designed for direct execution without command-line complexity
- Provides clear progress indication for long-running evaluations
- Implements robust error handling for production use
- Supports easy modification of evaluation parameters
- Generates actionable results for configuration optimization
"""

import os
import sys
import time
from datetime import datetime
from typing import Optional

# Add the project root to the Python path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from rvandroid.llm.evaluator.evaluator import LLMEvaluator
from rvandroid.llm.evaluator.config import DEFAULT_PROMPTS_DIR
from rvandroid.util.logging.manager import LoggingManager
from rvandroid.util.logging.constants import CONTEXT_COMPONENT


def setup_logging() -> None:
    """Setup logging configuration for the evaluation run."""
    # Configure logging for evaluation
    logging_manager = LoggingManager.get_instance()

    # Set appropriate log level
    import logging
    logging.getLogger().setLevel(logging.INFO)


def print_banner() -> None:
    """Print evaluation banner with system information."""
    print("=" * 80)
    print("         RV-Android LLM Configuration Evaluator")
    print("=" * 80)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()


def print_evaluation_plan() -> None:
    """Print the evaluation plan details."""
    from rvandroid.llm.evaluator.config import (
        MODELS_TO_TEST, STRATEGIES_TO_TEST, TEMPERATURE_VALUES,
        TOP_P_VALUES, MAX_TOKENS_VALUES, TOP_K_VALUES,
        REPETITIONS_PER_CONFIG, WARMUP_RUNS, GENERATION_TIMEOUT
    )

    print("Evaluation Configuration:")
    print(f"  Models: {', '.join(MODELS_TO_TEST)}")
    print(f"  Strategies: {', '.join(STRATEGIES_TO_TEST)}")
    print(f"  Temperature: {TEMPERATURE_VALUES}")
    print(f"  Top-p: {TOP_P_VALUES}")
    print(f"  Max Tokens: {MAX_TOKENS_VALUES}")
    print(f"  Top-k: {TOP_K_VALUES}")
    print(f"  Repetitions: {REPETITIONS_PER_CONFIG}")
    print(f"  Warm-up runs: {WARMUP_RUNS}")
    print(f"  Timeout: {GENERATION_TIMEOUT}s")
    print()


def print_progress_update(current: int, total: int, item_name: str) -> None:
    """
    Print progress update.

    Args:
        current: Current item number
        total: Total items
        item_name: Name of the item being processed
    """
    percentage = (current / total) * 100 if total > 0 else 0
    print(f"Progress: {current}/{total} ({percentage:.1f}%) - {item_name}")


def run_evaluation(prompts_dir: Optional[str] = None,
                   output_dir: str = ".") -> bool:
    """
    Run the complete LLM evaluation process.

    Args:
        prompts_dir: Directory containing prompt files (optional)
        output_dir: Directory for output files

    Returns:
        True if evaluation completed successfully, False otherwise
    """
    logger = LoggingManager.get_instance().get_logger(
        "llm.evaluator.runner",
        {CONTEXT_COMPONENT: "EvaluationRunner"}
    )

    logger.info("Starting LLM evaluation")

    try:
        # Initialize evaluator
        print("Initializing evaluator...")
        evaluator = LLMEvaluator(prompts_dir=prompts_dir, output_dir=output_dir)

        # Check if prompts were loaded
        if not evaluator.prompt_pairs:
            print("ERROR: No prompt pairs found!")
            print(f"Expected prompt files in: {prompts_dir or DEFAULT_PROMPTS_DIR}")
            print("Files should be named: 001_system.txt, 001_user.txt, etc.")
            return False

        print(f"Loaded {len(evaluator.prompt_pairs)} prompt pairs")
        print("Prompt pairs found:")
        for prompt_id, system_file, user_file in evaluator.prompt_pairs:
            print(f"  - {prompt_id}: {os.path.basename(system_file)}, {os.path.basename(user_file)}")
        print()

        # Run evaluation
        print("Starting evaluation...")
        print("This may take a significant amount of time depending on the number of configurations.")
        print("Progress will be logged to show current status.")
        print()

        start_time = time.time()

        # Execute evaluation
        detailed_file, summary_file, analysis_file = evaluator.run_evaluation()

        elapsed_time = time.time() - start_time

        # Print results
        print("=" * 80)
        print("EVALUATION COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print(f"Total execution time: {elapsed_time:.1f} seconds ({elapsed_time / 60:.1f} minutes)")
        print()
        print("Generated files:")
        print(f"  📊 Detailed Results: {detailed_file}")
        print(f"  📈 Summary Results:  {summary_file}")
        print(f"  📝 Analysis Report:  {analysis_file}")
        print()

        # Print evaluation summary
        summary = evaluator.get_evaluation_summary()
        if summary.get("status") == "completed":
            best_config = summary["best_configuration"]
            print("🏆 BEST CONFIGURATION:")
            print(f"   Model: {best_config['model']}")
            print(f"   Strategy: {best_config['strategy']}")
            print(f"   Temperature: {best_config['temperature']}")
            print(f"   Overall Score: {best_config['overall_score']:.1f}/100")
            print(f"   Success Rate: {best_config['success_rate']:.1%}")
            print()
            print(f"📊 OVERALL STATISTICS:")
            print(f"   Total configurations tested: {summary['total_configurations']}")
            print(f"   Total runs executed: {summary['total_runs']}")
            print(f"   Average success rate: {summary['average_success_rate']:.1%}")
            print(f"   Models tested: {', '.join(summary['models_tested'])}")
            print(f"   Strategies tested: {', '.join(summary['strategies_tested'])}")

        print()
        print("Next steps:")
        print("1. Review the detailed results Excel file for comprehensive data")
        print("2. Check the summary results for ranked configurations")
        print("3. Read the analysis report for insights and recommendations")
        print("4. Use the best configuration for your production testing")

        return True

    except KeyboardInterrupt:
        print("\nEvaluation interrupted by user")
        logger.info("Evaluation interrupted by user")
        return False

    except Exception as e:
        print(f"\nEvaluation failed with error: {e}")
        logger.error(f"Evaluation failed: {e}", exc_info=True)
        return False


def main() -> None:
    """Main execution function."""
    # Setup
    setup_logging()
    print_banner()
    print_evaluation_plan()

    # Configuration
    # Modify these paths as needed
    prompts_dir = None  # Will use default prompts directory
    output_dir = "."  # Current directory

    # You can override the directories here:
    # prompts_dir = "/path/to/your/prompts"
    # output_dir = "/path/to/your/output"

    print("Configuration:")
    print(f"  Prompts directory: {prompts_dir or DEFAULT_PROMPTS_DIR}")
    print(f"  Output directory: {output_dir}")
    print()

    # Verify prompts directory exists
    prompts_path = prompts_dir or DEFAULT_PROMPTS_DIR
    if not os.path.exists(prompts_path):
        print(f"ERROR: Prompts directory does not exist: {prompts_path}")
        print()
        print("Please create the prompts directory and add your prompt files:")
        print("  001_system.txt - First system prompt")
        print("  001_user.txt   - First user prompt")
        print("  002_system.txt - Second system prompt")
        print("  002_user.txt   - Second user prompt")
        print("  ... etc.")
        sys.exit(1)

    # Check for prompt files
    prompt_files = [f for f in os.listdir(prompts_path) if f.endswith('_system.txt') or f.endswith('_user.txt')]
    if not prompt_files:
        print(f"ERROR: No prompt files found in: {prompts_path}")
        print()
        print("Expected files like:")
        print("  001_system.txt")
        print("  001_user.txt")
        print("  002_system.txt")
        print("  002_user.txt")
        sys.exit(1)

    print(f"Found {len(prompt_files)} prompt files")
    print()

    # Run evaluation
    success = run_evaluation(prompts_dir=prompts_dir, output_dir=output_dir)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()