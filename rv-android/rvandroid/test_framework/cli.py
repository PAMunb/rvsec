"""
Command line interface for the test framework.

Provides a command line interface for interacting with the test framework,
enabling users to configure, run, and analyze tests.
"""

import argparse
import glob
import json
import os
from typing import List, Dict, Any, Optional

from tqdm import tqdm

from rvandroid.test_framework import (
    TestFramework, TestSuite, ToolConfiguration, create_default_test_suite
)
from rvandroid.test_framework.plateau_analyzer import analyze_plateau


def load_test_suite(config_file: str) -> Optional[TestSuite]:
    """
    Load a test suite from a configuration file.
    
    Args:
        config_file: Path to configuration file
        
    Returns:
        TestSuite if loading succeeds, None otherwise
    """
    try:
        if not os.path.exists(config_file):
            print(f"Error: Configuration file not found: {config_file}")
            return None
            
        with open(config_file, 'r') as f:
            data = json.load(f)
        
        return TestSuite.from_dict(data)
    except Exception as e:
        print(f"Error loading test suite: {str(e)}")
        return None


def run_test_suite(args):
    """
    Run a test suite.
    
    Args:
        args: Command line arguments
    """
    # Initialize test framework
    framework = TestFramework(output_dir=args.output_dir)
    
    # Load test suite if specified
    test_suite = None
    if args.config:
        test_suite = load_test_suite(args.config)
        if not test_suite:
            return
    
    # Resolve app paths
    app_paths = []
    for pattern in args.apps:
        paths = glob.glob(pattern)
        if not paths:
            print(f"Warning: No apps found matching pattern: {pattern}")
        app_paths.extend(paths)
    
    if not app_paths:
        print("Error: No apps found for testing.")
        return
    
    print(f"Found {len(app_paths)} apps for testing:")
    for app in app_paths:
        print(f"  - {os.path.basename(app)}")
    
    # Configure test suite
    test_suite = framework.configure(
        apps=app_paths,
        max_workers=args.workers,
        test_suite=test_suite,
        repetitions=args.repetitions
    )
    
    # Setup progress bar
    test_cases = test_suite.get_test_cases()
    pbar = tqdm(total=len(test_cases), desc="Running tests")
    
    def update_progress(current, total, message):
        pbar.update(1)
        pbar.set_description(f"Running tests: {message}")
    
    # Run test suite
    try:
        results = framework.run(update_progress)
        pbar.close()
        
        # Print summary
        success = sum(1 for r in results if r.status == "completed")
        errors = sum(1 for r in results if r.status == "error")
        
        print("\nTest Execution Summary:")
        print(f"  Total test cases: {len(results)}")
        print(f"  Successful: {success} ({success/len(results)*100:.1f}%)")
        print(f"  Errors: {errors} ({errors/len(results)*100:.1f}%)")
        
        # Analyze results
        if args.analyze:
            print("\nAnalyzing results...")
            analysis = framework.analyze()
            
            print(f"\nAnalysis completed. Report saved to: {framework.analysis_report}")
            
            # Save optimal configurations
            if args.save_optimal:
                config_file = os.path.join(args.output_dir, "optimal_configurations.json")
                framework.save_optimal_configurations(config_file)
                print(f"Optimal configurations saved to: {config_file}")
        
    except KeyboardInterrupt:
        pbar.close()
        print("\nTest execution interrupted.")
    except Exception as e:
        pbar.close()
        print(f"\nError running test suite: {str(e)}")


def create_config(args):
    """
    Create a test suite configuration file.
    
    Args:
        args: Command line arguments
    """
    # Create default test suite
    test_suite = create_default_test_suite()
    
    # Update name and description
    test_suite.name = args.name
    test_suite.description = args.description
    
    # Save configuration
    try:
        test_suite.save_to_file(args.output)
        print(f"Test suite configuration saved to: {args.output}")
    except Exception as e:
        print(f"Error saving configuration: {str(e)}")


def analyze_results(args):
    """
    Analyze results from a previous test run.
    
    Args:
        args: Command line arguments
    """
    # Validate directory exists
    if not os.path.exists(args.results_dir):
        print(f"Error: Results directory not found: {args.results_dir}")
        return
        
    print(f"Analyzing results from directory: {args.results_dir}")
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    try:
        # For now, we'll just print a message about manual analysis
        # In the future, this could be implemented to load test results from files
        print(f"To analyze results properly, please run tests with --analyze flag.")
        print(f"Manual analysis options:")
        print(f"1. Check the HTML report in the results directory")
        print(f"2. View JSON analysis data in the results directory")
        print(f"3. Use the plateau command for timeout analysis")
    except Exception as e:
        print(f"Error analyzing results: {str(e)}")


def run_plateau_analysis(args):
    """
    Run plateau analysis on results.
    
    Args:
        args: Command line arguments
    """
    # Validate arguments
    if not os.path.exists(args.results_dir):
        print(f"Error: Results directory not found: {args.results_dir}")
        return
    
    if not args.timeouts:
        print("Error: No timeouts specified for plateau analysis.")
        return
    
    print(f"Running plateau analysis with timeouts: {args.timeouts}")
    
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    try:
        # Since we cannot directly access test results from files yet,
        # provide instructions for running plateau analysis
        print("\nPlateau Analysis Instructions:")
        print("1. Run tests with multiple timeout configurations first")
        print("   Example: python run_test_framework.py run --apps example.apk --config plateau_config_example.json")
        print("\n2. View the results in the output directory:")
        print(f"   {args.output_dir}")
        print("\n3. After implementing file loading in the future, this command will:")
        print("   - Analyze how metrics change across different timeouts")
        print("   - Detect plateaus in coverage and other metrics")
        print("   - Generate visualizations showing optimal timeout values")
        print("   - Recommend optimal timeouts for different configurations")
    except Exception as e:
        print(f"Error running plateau analysis: {str(e)}")


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="RV-Android Test Framework CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Run command
    run_parser = subparsers.add_parser("run", help="Run a test suite")
    run_parser.add_argument(
        "--apps", "-a", nargs="+", required=True,
        help="APK files or glob patterns to test"
    )
    run_parser.add_argument(
        "--config", "-c", 
        help="Path to test suite configuration file"
    )
    run_parser.add_argument(
        "--output-dir", "-o", default="test_results",
        help="Directory for test results"
    )
    run_parser.add_argument(
        "--workers", "-w", type=int, default=1,
        help="Maximum number of parallel test executions"
    )
    run_parser.add_argument(
        "--repetitions", "-r", type=int, default=1,
        help="Number of repetitions for each test case"
    )
    run_parser.add_argument(
        "--analyze", "-A", action="store_true",
        help="Analyze results after execution"
    )
    run_parser.add_argument(
        "--save-optimal", "-S", action="store_true",
        help="Save optimal configurations after analysis"
    )
    
    # Create config command
    config_parser = subparsers.add_parser("create-config", help="Create a test suite configuration")
    config_parser.add_argument(
        "--name", "-n", default="Default Test Suite",
        help="Name of the test suite"
    )
    config_parser.add_argument(
        "--description", "-d", default="",
        help="Description of the test suite"
    )
    config_parser.add_argument(
        "--output", "-o", default="test_suite_config.json",
        help="Output file for configuration"
    )
    
    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze results from a previous test run")
    analyze_parser.add_argument(
        "--results-dir", "-r", required=True,
        help="Directory containing test results"
    )
    analyze_parser.add_argument(
        "--output-dir", "-o", default="analysis_results",
        help="Directory for analysis output"
    )
    
    # Add plateau analysis command
    plateau_parser = subparsers.add_parser("plateau", help="Analyze metric plateau for different timeouts")
    plateau_parser.add_argument(
        "--results-dir", "-r", required=True,
        help="Directory containing test results"
    )
    plateau_parser.add_argument(
        "--timeouts", "-t", type=int, nargs="+", default=[60, 120, 180, 300, 600],
        help="Timeouts to analyze (in seconds)"
    )
    plateau_parser.add_argument(
        "--output-dir", "-o", default="plateau_analysis",
        help="Directory for analysis output"
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Execute command
    if args.command == "run":
        run_test_suite(args)
    elif args.command == "create-config":
        create_config(args)
    elif args.command == "analyze":
        analyze_results(args)
    elif args.command == "plateau":
        run_plateau_analysis(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()