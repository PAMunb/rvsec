#!/usr/bin/env python3
"""
Entry point for rv-evaluator module.

This module provides a simple interface to run LLM evaluations systematically.
It tests different LLM configurations and generates comprehensive reports.

Usage:
    python -m rv_evaluator [--prompts-dir DIR] [--output-dir DIR]

Examples:
    python -m rv_evaluator
    python -m rv_evaluator --output-dir ./results
    python -m rv_evaluator --prompts-dir ./my_prompts --output-dir ./my_results
"""

import argparse
import os
import sys
import time
from datetime import datetime
from typing import Optional

from rv_android_core.util.logging.constants import CONTEXT_COMPONENT
from rv_android_core.util.logging.manager import LoggingManager
from .config import DEFAULT_PROMPTS_DIR, get_prompt_pairs
from .evaluator import LLMEvaluator


def setup_logging() -> None:
    """Configure logging for the evaluation."""
    logging_manager = LoggingManager.get_instance()
    
    import logging
    logging.getLogger().setLevel(logging.INFO)


def print_banner() -> None:
    """Print evaluation banner."""
    print("=" * 60)
    print("           RV-Android LLM Evaluator")
    print("=" * 60)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()


def validate_directories(prompts_dir: str, output_dir: str) -> bool:
    """
    Validate input and output directories.
    
    Args:
        prompts_dir: Directory containing prompt files
        output_dir: Directory for output files
        
    Returns:
        True if directories are valid, False otherwise
    """
    # Check prompts directory
    if not os.path.exists(prompts_dir):
        print(f"ERROR: Prompts directory does not exist: {prompts_dir}")
        return False
    
    # Check for prompt files
    try:
        prompt_pairs = get_prompt_pairs(prompts_dir)
        if not prompt_pairs:
            print(f"ERROR: No valid prompt pairs found in: {prompts_dir}")
            print("Expected files like: 001_system.txt, 001_user.txt, etc.")
            return False
        print(f"Found {len(prompt_pairs)} prompt pairs")
    except Exception as e:
        print(f"ERROR: Failed to load prompts: {e}")
        return False
    
    # Create output directory if needed
    os.makedirs(output_dir, exist_ok=True)
    
    return True


def run_evaluation(prompts_dir: str, output_dir: str) -> bool:
    """
    Run the complete evaluation process.
    
    Args:
        prompts_dir: Directory containing prompt files
        output_dir: Directory for output files
        
    Returns:
        True if successful, False otherwise
    """
    logger = LoggingManager.get_instance().get_logger(
        "rv_evaluator.main",
        {CONTEXT_COMPONENT: "MainEvaluator"}
    )
    
    try:
        print("Initializing evaluator...")
        evaluator = LLMEvaluator(prompts_dir=prompts_dir, output_dir=output_dir)
        
        print(f"Configuration loaded:")
        print(f"  - Prompt pairs: {len(evaluator.prompt_pairs)}")
        print(f"  - Output directory: {output_dir}")
        print()
        
        start_time = time.time()
        
        print("Starting evaluation...")
        print("This may take several minutes depending on configurations.")
        print()
        
        detailed_file, summary_config_file, summary_model_file = evaluator.run_evaluation()
        
        elapsed_time = time.time() - start_time
        
        print("=" * 60)
        print("EVALUATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print(f"Total time: {elapsed_time:.1f}s ({elapsed_time/60:.1f}min)")
        print()
        print("Generated files:")
        print(f"  📊 Detailed Results:     {detailed_file}")
        print(f"  📈 Summary by Config:    {summary_config_file}")
        print(f"  📋 Summary by Model:     {summary_model_file}")
        print()
        
        logger.info(f"Evaluation completed successfully in {elapsed_time:.1f}s")
        return True
        
    except KeyboardInterrupt:
        print("\nEvaluation interrupted by user")
        logger.info("Evaluation interrupted by user")
        return False
        
    except Exception as e:
        print(f"\nEvaluation failed: {e}")
        logger.error(f"Evaluation failed: {e}", exc_info=True)
        return False


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description="Run LLM configuration evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m rv_evaluator
  python -m rv_evaluator --output-dir ./results
  python -m rv_evaluator --prompts-dir ./custom_prompts
        """
    )
    
    parser.add_argument(
        "--prompts-dir",
        default=None,
        help=f"Directory containing prompt files (default: {DEFAULT_PROMPTS_DIR})"
    )
    
    parser.add_argument(
        "--output-dir", 
        default=".",
        help="Output directory for results (default: current directory)"
    )
    
    return parser


def main():
    """Main entry point."""
    setup_logging()
    print_banner()
    
    parser = create_parser()
    args = parser.parse_args()
    
    prompts_dir = args.prompts_dir or DEFAULT_PROMPTS_DIR
    output_dir = args.output_dir
    
    print("Configuration:")
    print(f"  Prompts directory: {prompts_dir}")
    print(f"  Output directory:  {output_dir}")
    print()
    
    if not validate_directories(prompts_dir, output_dir):
        sys.exit(1)
    
    success = run_evaluation(prompts_dir, output_dir)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()