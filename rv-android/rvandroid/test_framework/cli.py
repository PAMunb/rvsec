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
from rvandroid.test_framework.config_validator import validate_configurations
from rvandroid.test_framework.config_generator import (
    create_minimal_test_suite, create_plateau_test_suite, create_comparative_test_suite,
    ConfigurationGenerator
)
from rvandroid.util.logging.manager import LoggingManager

# Configure logging
logging_manager = LoggingManager.get_instance()
logger = logging_manager.get_logger("test_framework.cli")


def load_test_suite(config_file: str, validate: bool = True, skip_invalid: bool = False) -> Optional[TestSuite]:
    """
    Load a test suite from a configuration file.
    
    Args:
        config_file: Path to configuration file
        validate: Whether to validate configurations after loading
        skip_invalid: Whether to remove invalid configurations instead of returning None
        
    Returns:
        TestSuite if loading succeeds, None otherwise
    """
    try:
        if not os.path.exists(config_file):
            logger.error(f"Error: Configuration file not found: {config_file}")
            return None
            
        with open(config_file, 'r') as f:
            data = json.load(f)
        
        test_suite = TestSuite.from_dict(data)
        
        # Validate configurations if requested
        if validate:
            invalid_configs = validate_configurations(test_suite.tool_configurations)
            if invalid_configs:
                logger.warning(f"Warning: {len(invalid_configs)} invalid configurations detected in {config_file}:")
                for config_id, errors in invalid_configs.items():
                    logger.warning(f"  - {config_id}:")
                    for error in errors:
                        logger.warning(f"      * {error}")
                
                if skip_invalid:
                    # Remove invalid configurations
                    valid_configs = [
                        config for config in test_suite.tool_configurations
                        if config.get_id() not in invalid_configs
                    ]
                    test_suite.tool_configurations = valid_configs
                    logger.info(f"Removed {len(invalid_configs)} invalid configurations. Remaining: {len(valid_configs)}")
                else:
                    logger.info("Use --skip-invalid to remove invalid configurations and continue.")
                    return None
        
        return test_suite
    except Exception as e:
        logger.error(f"Error loading test suite: {str(e)}")
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
        test_suite = load_test_suite(args.config, validate=True, skip_invalid=args.skip_invalid)
        if not test_suite:
            logger.error("Test suite loading failed.")
            return
    
    # Resolve APK paths from command line if provided
    app_paths = []
    
    if args.apks_dir:
        for directory in args.apks_dir:
            # Find all APK files in the specified directories
            apk_pattern = os.path.join(directory, "*.apk")
            apk_paths = glob.glob(apk_pattern)
            
            if not apk_paths:
                logger.warning(f"No APK files found in directory: {directory}")
            else:
                # For each APK found, verify it has the necessary static analysis files
                for apk_path in apk_paths:
                    if os.path.isfile(apk_path):
                        app_paths.append(apk_path)
        
        if app_paths:
            logger.info(f"Found {len(app_paths)} APK files from specified directories:")
            for app in app_paths:
                logger.debug(f"  - {app}")
    
    # If no APKs specified on command line but config file has apps, use those
    if not app_paths and test_suite and test_suite.apps:
        app_paths = test_suite.apps
        logger.info(f"Using {len(app_paths)} APK paths from configuration file:")
        for app in app_paths:
            logger.debug(f"  - {app}")
    
    # Check if we have any APKs to test
    if not app_paths:
        logger.error("No APK files found for testing. Specify directories with --apks-dir or apps in the configuration file.")
        return
    
    # Configure test suite
    test_suite = framework.configure(
        apps=app_paths,
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
                
        # Analyze batch strategies
        if args.analyze_batch:
            print("\nAnalyzing batch action strategies...")
            try:
                batch_analysis = framework.analyze_batch_strategies()
                print("\nBatch analysis completed.")
                
                # Find best batch configuration
                best_batch_config = framework.get_best_batch_configuration()
                if best_batch_config:
                    print(f"\nBest batch strategy configuration: {best_batch_config.get_id()}")
                    print(f"  Tool: {best_batch_config.tool_name}")
                    print(f"  LLM: {best_batch_config.llm_type}/{best_batch_config.llm_model}")
                    print(f"  Strategy: {best_batch_config.strategy_type}")
                
                # Show key improvements
                if "improvements" in batch_analysis:
                    improvements = batch_analysis["improvements"]
                    print("\nKey improvements from batch processing:")
                    for metric, value in improvements.items():
                        # Format metric name for display
                        display_name = metric.replace('_', ' ').title()
                        print(f"  {display_name}: {value:.1f}%")
                
                # Save batch analysis results
                if args.save_batch:
                    batch_file = os.path.join(args.output_dir, "batch_analysis_results.json")
                    framework.save_batch_analysis(batch_file)
                    print(f"\nBatch analysis results saved to: {batch_file}")
            except Exception as e:
                print(f"\nError analyzing batch strategies: {str(e)}")
        
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
    try:
        # Choose the right generator based on the configuration type
        if args.type == "default":
            test_suite = create_comparative_test_suite()
        elif args.type == "minimal":
            test_suite = create_minimal_test_suite()
        elif args.type == "plateau":
            timeouts = [int(t) for t in args.timeouts.split(",")]
            test_suite = create_plateau_test_suite(args.tool, timeouts)
        elif args.type == "custom":
            # Create a generator
            generator = ConfigurationGenerator()
            
            # Generate custom configurations
            llm_types = args.llm_types.split(",") if args.llm_types else ["ollama"]
            tools = args.tools.split(",") if args.tools else ["rvandroid", "rvdroid"]
            
            # Generate models dictionary
            models = {}
            if args.models:
                for model_spec in args.models.split(";"):
                    llm_type, model_list = model_spec.split(":")
                    models[llm_type] = model_list.split(",")
            else:
                # Default models
                models = {
                    "ollama": ["llama3.2:3b"],
                    "dspy": ["meta-llama/Meta-Llama-3.1-8B-Instruct"]
                }
            
            # Get strategies
            strategies = args.strategies.split(",") if args.strategies else ["composable_single_action"]
            
            # Get visitors
            visitors = args.visitors.split(",") if args.visitors else ["enhanced"]
            
            # Generate all combinations
            configs = generator.generate_all_combinations(
                tools=tools,
                llm_types=llm_types,
                models=models,
                strategy_types=strategies,
                visitor_types=visitors
            )
            
            # Create test suite
            test_suite = TestSuite(
                name=args.name,
                description=args.description,
                tool_configurations=configs,
                apps=[],
                output_dir="test_results",
                repetitions=1
            )
        else:
            print(f"Unknown configuration type: {args.type}")
            return
            
        # Update name and description
        if args.name:
            test_suite.name = args.name
        
        if args.description:
            test_suite.description = args.description
        
        # Validate the configurations
        invalid_configs = validate_configurations(test_suite.tool_configurations)
        if invalid_configs:
            print(f"Warning: {len(invalid_configs)} invalid configurations detected:")
            for config_id, errors in invalid_configs.items():
                print(f"  - {config_id}:")
                for error in errors:
                    print(f"      * {error}")
            
            if args.skip_invalid:
                # Remove invalid configurations
                valid_configs = [
                    config for config in test_suite.tool_configurations
                    if config.get_id() not in invalid_configs
                ]
                test_suite.tool_configurations = valid_configs
                print(f"Removed {len(invalid_configs)} invalid configurations. Remaining: {len(valid_configs)}")
            else:
                print("Aborting. Use --skip-invalid to remove invalid configurations.")
                return
        
        # Ensure we have a valid output path
        if not args.output:
            args.output = "test_suite_config.json"  # Default name if empty
            
        # Save configuration (TestSuite.save_to_file will create directories as needed)
        test_suite.save_to_file(args.output)
        print(f"Test suite configuration saved to: {args.output}")
        print(f"Generated {len(test_suite.tool_configurations)} valid configurations.")
    except Exception as e:
        print(f"Error creating configuration: {str(e)}")


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
        # Import the results loader
        from rvandroid.test_framework.results_loader import ResultsLoader
        
        # Initialize the loader
        loader = ResultsLoader(args.results_dir)
        
        # Load and analyze results
        print("Loading and analyzing results...")
        results = loader.load_and_analyze()
        
        if results.get("status") == "No results found":
            print("No valid test results found in the specified directory.")
            return
            
        # Output basic statistics
        print("\nAnalysis Summary:")
        print(f"  Total results: {results['total_results']}")
        print(f"  Total configurations: {results['total_configs']}")
        print(f"  Total applications: {results['total_apps']}")
        
        # Show top configurations
        print("\nTop Configurations:")
        top_configs = results.get('top_configurations', {})
        for metric, configs in top_configs.items():
            print(f"  {metric}:")
            for i, config_id in enumerate(configs[:3], 1):
                comparison = results['configuration_comparisons'][config_id]
                value = comparison['avg_metrics'].get(metric, 0)
                print(f"    {i}. {config_id}: {value:.2f}")
        
        # Detect anomalies if requested
        if args.detect_anomalies:
            print("\nDetecting anomalies in results...")
            from rvandroid.test_framework.anomaly_detector import detect_anomalies
            
            anomaly_threshold = args.anomaly_threshold if args.anomaly_threshold else 2.0
            anomaly_report = detect_anomalies(results, z_threshold=anomaly_threshold)
            
            # Add to results for dashboard
            results['anomaly_report'] = anomaly_report
            
            # Show anomaly summary
            print(f"\nAnomaly Detection Summary:")
            print(f"  Total anomalies: {anomaly_report['total_anomalies']}")
            
            if anomaly_report['total_anomalies'] > 0:
                # By type
                print("  Anomalies by type:")
                for type_name, count in anomaly_report['anomalies_by_type'].items():
                    print(f"    {type_name}: {count}")
                
                # By severity
                print("  Anomalies by severity:")
                for severity, count in anomaly_report['anomalies_by_severity'].items():
                    print(f"    {severity}: {count}")
                
                # Show top anomalies
                print("\nTop anomalies:")
                # Sort by severity and deviation
                sorted_anomalies = sorted(
                    anomaly_report['anomalies'], 
                    key=lambda x: (
                        0 if x['severity'] == 'high' else 1 if x['severity'] == 'medium' else 2,
                        abs(x['deviation'])
                    ), 
                    reverse=True
                )
                
                for anomaly in sorted_anomalies[:5]:  # Show top 5
                    print(f"  - {anomaly['explanation']}")
                
                # Save anomaly report
                anomaly_file = os.path.join(args.output_dir, "anomaly_report.json")
                with open(anomaly_file, 'w') as f:
                    json.dump(anomaly_report, f, indent=2)
                print(f"\nAnomaly report saved to: {anomaly_file}")
            else:
                print("  No anomalies detected with the current threshold.")
        
        # Analyze correlations if requested
        if args.analyze_correlations:
            print("\nAnalyzing correlations between app characteristics and configurations...")
            from rvandroid.test_framework.correlation_analyzer import analyze_correlations
            
            correlation_report = analyze_correlations(results)
            
            # Add to results for dashboard
            results['correlation_report'] = correlation_report
            
            # Show correlation summary
            print(f"\nCorrelation Analysis Summary:")
            print(f"  Total correlations: {correlation_report['total_correlations']}")
            print(f"  Apps analyzed: {correlation_report['app_count']}")
            
            if correlation_report['total_correlations'] > 0:
                # Show top correlations
                print("\nTop correlations:")
                for i, corr in enumerate(correlation_report['top_correlations'][:5], 1):
                    print(f"  {i}. {corr['explanation']}")
                
                # Show recommendations
                if correlation_report['recommendations']:
                    print("\nConfiguration recommendations:")
                    for char_name, recs in list(correlation_report['recommendations'].items())[:3]:
                        print(f"  For apps with {char_name.replace('_', ' ')}:")
                        for rec in recs[:2]:
                            print(f"    - {rec['config_id']}: {rec['explanation']}")
                
                # App-specific recommendations
                if correlation_report['app_recommendations']:
                    print("\nApp-specific recommendations:")
                    for app_name, recs in list(correlation_report['app_recommendations'].items())[:3]:
                        print(f"  {app_name}:")
                        for rec in recs[:2]:
                            print(f"    - {rec['config_id']}: {rec['reason']}")
                
                # Save correlation report
                corr_file = os.path.join(args.output_dir, "correlation_report.json")
                with open(corr_file, 'w') as f:
                    json.dump(correlation_report, f, indent=2)
                print(f"\nDetailed correlation report saved to: {corr_file}")
            else:
                print("  No significant correlations found in the results.")
        
        # Generate interactive dashboard if requested
        if args.dashboard:
            print("\nGenerating interactive dashboard...")
            try:
                from rvandroid.test_framework.dashboard import generate_dashboard, launch_dashboard
                
                dashboard_file = generate_dashboard(results, args.output_dir)
                
                if dashboard_file:
                    print(f"Dashboard generated at: {dashboard_file}")
                    
                    # Launch dashboard in browser if requested
                    if args.launch_dashboard:
                        launch_dashboard(dashboard_file)
                        print("Dashboard opened in browser.")
                else:
                    print("Error generating dashboard.")
            except ImportError:
                print("Dashboard module not available. Skipping dashboard generation.")
        
        # Save analysis results
        output_file = os.path.join(args.output_dir, "analysis_results.json")
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nDetailed analysis results saved to: {output_file}")
        
        # Generate visualizations if needed
        if args.visualize:
            # Import visualization module
            try:
                from rvandroid.test_framework.visualization import generate_visualizations
                
                print("\nGenerating visualizations...")
                vis_path = os.path.join(args.output_dir, "visualizations")
                os.makedirs(vis_path, exist_ok=True)
                
                generate_visualizations(results, vis_path)
                print(f"Visualizations saved to: {vis_path}")
            except ImportError:
                print("Visualization module not available. Skipping visualization generation.")
        
        # Export to CSV if needed
        if args.export_csv:
            try:
                # Determine which CSV exporter to use
                if args.enhanced_export:
                    from rvandroid.test_framework.spreadsheet_exporter import export_to_enhanced_csv
                    
                    print("\nExporting results to enhanced CSV files...")
                    csv_path = os.path.join(args.output_dir, "results_export.csv")
                    
                    success = export_to_enhanced_csv(results, csv_path)
                    if success:
                        print(f"Enhanced CSV exports saved to directory: {args.output_dir}")
                    else:
                        print("Error exporting to enhanced CSV.")
                else:
                    from rvandroid.test_framework.exporters import export_to_csv
                    
                    print("\nExporting results to CSV...")
                    csv_path = os.path.join(args.output_dir, "results_export.csv")
                    
                    export_to_csv(results, csv_path)
                    print(f"CSV export saved to: {csv_path}")
            except ImportError as e:
                print(f"CSV exporter module not available: {str(e)}. Skipping CSV export.")
                
        # Export to Excel if needed
        if args.export_xlsx:
            try:
                # Determine which Excel exporter to use
                if args.enhanced_export:
                    from rvandroid.test_framework.spreadsheet_exporter import export_to_enhanced_excel
                    
                    print("\nExporting results to enhanced Excel workbook...")
                    xlsx_path = os.path.join(args.output_dir, "results_export.xlsx")
                    
                    success = export_to_enhanced_excel(results, xlsx_path)
                    if success:
                        print(f"Enhanced Excel export saved to: {xlsx_path}")
                    else:
                        print("Error exporting to enhanced Excel.")
                else:
                    from rvandroid.test_framework.exporters import export_to_excel
                    
                    print("\nExporting results to Excel...")
                    xlsx_path = os.path.join(args.output_dir, "results_export.xlsx")
                    
                    export_to_excel(results, xlsx_path)
                    print(f"Excel export saved to: {xlsx_path}")
            except ImportError as e:
                print(f"Excel exporter module not available: {str(e)}. Skipping Excel export.")
                
        # Perform batch analysis if requested
        if args.batch_analysis:
            try:
                # Initialize the test framework with the results directory
                from rvandroid.test_framework.framework import TestFramework
                from rvandroid.test_framework.results_loader import ResultsLoader
                from rvandroid.test_framework.batch_analyzer import BatchAnalyzer
                
                print("\nAnalyzing batch action strategies...")
                
                # Initialize the framework
                framework = TestFramework(output_dir=args.output_dir)
                
                # Load the results using the loader
                loader = ResultsLoader(args.results_dir)
                test_results = loader.load_test_results()
                
                if not test_results:
                    print("No valid test results found for batch analysis.")
                    return
                
                # Use the batch analyzer directly
                batch_analyzer = BatchAnalyzer(test_results, args.output_dir)
                report_file, batch_analysis = batch_analyzer.generate_report()
                
                print(f"\nBatch analysis completed. Report saved to: {report_file}")
                
                # Save batch analysis results
                batch_output = os.path.join(args.output_dir, args.batch_output)
                with open(batch_output, 'w') as f:
                    # Remove chart files from JSON (they're just paths)
                    output_data = dict(batch_analysis)
                    if "chart_files" in output_data:
                        del output_data["chart_files"]
                    json.dump(output_data, f, indent=2)
                
                print(f"Batch analysis results saved to: {batch_output}")
                
                # Show key improvements
                if "improvements" in batch_analysis:
                    improvements = batch_analysis["improvements"]
                    print("\nKey improvements from batch processing:")
                    for metric, value in improvements.items():
                        # Format metric name for display
                        display_name = metric.replace('_', ' ').title()
                        print(f"  {display_name}: {value:.1f}%")
                
                # Show best patterns
                if "pattern_effectiveness" in batch_analysis and "best_by_effectiveness" in batch_analysis["pattern_effectiveness"]:
                    best_patterns = batch_analysis["pattern_effectiveness"]["best_by_effectiveness"]
                    if best_patterns:
                        print("\nMost effective UI patterns:")
                        for i, pattern in enumerate(best_patterns[:3], 1):
                            print(f"  {i}. {pattern.title()}")
                
            except Exception as e:
                print(f"Error performing batch analysis: {str(e)}")
    except Exception as e:
        print(f"Error analyzing results: {str(e)}")




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
        "--apks-dir", "-a", nargs="+",
        help="Directory containing APK files and related static analysis files (optional if config file has apps defined)"
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
    run_parser.add_argument(
        "--analyze-batch", "-B", action="store_true",
        help="Analyze batch action strategies and compare with single action approaches"
    )
    run_parser.add_argument(
        "--save-batch", "-b", action="store_true",
        help="Save batch analysis results after analysis"
    )
    run_parser.add_argument(
        "--skip-invalid", "-s", action="store_true",
        help="Skip invalid configurations instead of aborting"
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
    config_parser.add_argument(
        "--type", "-t", default="default", choices=["default", "minimal", "plateau", "custom"],
        help="Type of configuration to generate: default (comparative), minimal, plateau, or custom"
    )
    config_parser.add_argument(
        "--skip-invalid", "-s", action="store_true",
        help="Skip invalid configurations instead of aborting"
    )
    
    # Plateau-specific options
    config_parser.add_argument(
        "--timeouts", default="60,120,180,300,600",
        help="Comma-separated list of timeouts for plateau analysis (e.g., '60,120,300')"
    )
    config_parser.add_argument(
        "--tool", default="rvandroid", choices=["rvandroid", "rvdroid"],
        help="Tool to use for plateau analysis"
    )
    
    # Custom configuration options
    config_parser.add_argument(
        "--tools", 
        help="Comma-separated list of tools to include (e.g., 'rvandroid,rvdroid')"
    )
    config_parser.add_argument(
        "--llm-types", 
        help="Comma-separated list of LLM types to include (e.g., 'ollama,dspy')"
    )
    config_parser.add_argument(
        "--models", 
        help="LLM models specification (e.g., 'ollama:llama3.2:3b,gemma3:4b;dspy:meta-llama/Meta-Llama-3.1-8B-Instruct')"
    )
    config_parser.add_argument(
        "--strategies", 
        help="Comma-separated list of strategies (e.g., 'basic,composable_single_action')"
    )
    config_parser.add_argument(
        "--visitors", 
        help="Comma-separated list of visitors (e.g., 'basic,enhanced')"
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
    analyze_parser.add_argument(
        "--visualize", "-v", action="store_true",
        help="Generate visualizations for result analysis"
    )
    analyze_parser.add_argument(
        "--export-csv", "-e", action="store_true",
        help="Export results to CSV format"
    )
    analyze_parser.add_argument(
        "--export-xlsx", "-x", action="store_true",
        help="Export results to Excel format"
    )
    analyze_parser.add_argument(
        "--enhanced-export", "-E", action="store_true",
        help="Use enhanced export with more detailed spreadsheets"
    )
    analyze_parser.add_argument(
        "--detect-anomalies", "-a", action="store_true",
        help="Detect anomalies in test results"
    )
    analyze_parser.add_argument(
        "--anomaly-threshold", "-t", type=float, default=2.0,
        help="Z-score threshold for anomaly detection (default: 2.0)"
    )
    analyze_parser.add_argument(
        "--analyze-correlations", "-c", action="store_true",
        help="Analyze correlations between app characteristics and configurations"
    )
    analyze_parser.add_argument(
        "--dashboard", "-d", action="store_true",
        help="Generate interactive dashboard for result visualization"
    )
    analyze_parser.add_argument(
        "--launch-dashboard", "-l", action="store_true",
        help="Launch dashboard in web browser after generation"
    )
    analyze_parser.add_argument(
        "--batch-analysis", "-b", action="store_true",
        help="Analyze batch action strategies and compare with single action approaches"
    )
    analyze_parser.add_argument(
        "--batch-output", default="batch_analysis_results.json",
        help="Output file for batch analysis results"
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
    else:
        parser.print_help()


if __name__ == "__main__":
    main()