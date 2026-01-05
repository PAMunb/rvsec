#!/usr/bin/env python3
"""
Main runner for vision model benchmarks.
Executes tests and generates comprehensive reports.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from benchmark_framework import VisionModelBenchmark
from model_config import AVAILABLE_MODELS, TEST_SCENARIOS, list_available_models
from report_generator import BenchmarkReportGenerator

def run_quick_test(models: Optional[List[str]] = None) -> None:
    """Run a quick test with minimal samples."""
    
    print("🚀 QUICK VISION MODEL BENCHMARK")
    print("=" * 60)
    
    benchmark = VisionModelBenchmark()
    
    if models is None:
        # Test a subset of models for quick feedback
        models = ["gemma3:4b", "llama3.2-vision:11b", "qwen2.5vl:7b"]
    
    scenarios = ["coordinate_validation", "visual_generation"]
    
    performances = benchmark.run_comprehensive_benchmark(
        models_to_test=models,
        scenarios_to_test=scenarios,
        samples_per_scenario=2  # Quick test
    )
    
    # Save results
    benchmark.save_results("quick_test_results")
    
    # Generate quick report
    report_gen = BenchmarkReportGenerator(performances, benchmark.results)
    report_gen.generate_summary_report("quick_test_results/summary_report.md")
    
    print("\n✅ Quick test completed!")
    print("📊 Check 'quick_test_results/' for detailed analysis")

def run_comprehensive_benchmark(
    models: Optional[List[str]] = None,
    scenarios: Optional[List[str]] = None,
    samples_per_scenario: int = 3
) -> None:
    """Run comprehensive benchmark across all specified models and scenarios."""
    
    print("🧪 COMPREHENSIVE VISION MODEL BENCHMARK")
    print("=" * 70)
    
    if models is None:
        models = list_available_models()
        print(f"📱 Testing all {len(models)} available models")
    else:
        print(f"📱 Testing {len(models)} specified models")
    
    if scenarios is None:
        scenarios = list(TEST_SCENARIOS.keys())
        print(f"🎯 Testing all {len(scenarios)} scenarios")
    else:
        print(f"🎯 Testing {len(scenarios)} specified scenarios")
    
    print(f"📊 {samples_per_scenario} samples per scenario")
    print(f"🔢 Total tests: {len(models) * len(scenarios) * samples_per_scenario}")
    
    # Run benchmark
    benchmark = VisionModelBenchmark()
    
    try:
        performances = benchmark.run_comprehensive_benchmark(
            models_to_test=models,
            scenarios_to_test=scenarios,
            samples_per_scenario=samples_per_scenario
        )
        
        # Save results
        benchmark.save_results("comprehensive_results")
        
        # Generate comprehensive reports
        report_gen = BenchmarkReportGenerator(performances, benchmark.results)
        
        # Generate all report types
        report_gen.generate_summary_report("comprehensive_results/summary_report.md")
        report_gen.generate_detailed_report("comprehensive_results/detailed_report.md")
        report_gen.generate_comparison_tables("comprehensive_results/comparison_tables.md")
        report_gen.save_performance_charts("comprehensive_results/")
        
        print("\n✅ Comprehensive benchmark completed!")
        print("📊 Check 'comprehensive_results/' for all analysis files")
        
        # Print quick summary
        print(f"\n🏆 QUICK SUMMARY")
        print("=" * 30)
        
        if performances:
            # Sort by overall success rate
            sorted_models = sorted(
                performances.items(), 
                key=lambda x: x[1].overall_success_rate, 
                reverse=True
            )
            
            print("Top 3 models by success rate:")
            for i, (name, perf) in enumerate(sorted_models[:3], 1):
                print(f"  {i}. {name}: {perf.overall_success_rate*100:.1f}% success, {perf.avg_distance:.1f}px avg distance")
        
    except KeyboardInterrupt:
        print("\n⚠️ Benchmark interrupted by user")
        # Still try to save partial results
        if benchmark.results:
            benchmark.save_results("interrupted_results")
            print("💾 Partial results saved to 'interrupted_results/'")
    
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        # Save partial results if available
        if benchmark.results:
            benchmark.save_results("error_results")
            print("💾 Partial results saved to 'error_results/'")

def run_model_comparison(model1: str, model2: str) -> None:
    """Run head-to-head comparison between two models."""
    
    print(f"⚔️ MODEL COMPARISON: {model1} vs {model2}")
    print("=" * 60)
    
    benchmark = VisionModelBenchmark()
    
    models = [model1, model2]
    scenarios = ["coordinate_validation", "visual_generation"]
    
    performances = benchmark.run_comprehensive_benchmark(
        models_to_test=models,
        scenarios_to_test=scenarios,
        samples_per_scenario=3
    )
    
    # Save results
    benchmark.save_results(f"comparison_{model1.replace(':', '_')}_vs_{model2.replace(':', '_')}")
    
    # Generate comparison report
    report_gen = BenchmarkReportGenerator(performances, benchmark.results)
    report_gen.generate_head_to_head_report(
        model1, model2, 
        f"comparison_{model1.replace(':', '_')}_vs_{model2.replace(':', '_')}/head_to_head.md"
    )
    
    print(f"\n✅ Comparison completed!")
    print(f"📊 Results saved with detailed head-to-head analysis")

def run_scenario_analysis(scenario: str, models: Optional[List[str]] = None) -> None:
    """Run detailed analysis of a specific scenario across models."""
    
    print(f"🎯 SCENARIO ANALYSIS: {scenario}")
    print("=" * 50)
    
    if scenario not in TEST_SCENARIOS:
        print(f"❌ Unknown scenario: {scenario}")
        print(f"Available: {list(TEST_SCENARIOS.keys())}")
        return
    
    benchmark = VisionModelBenchmark()
    
    if models is None:
        models = list_available_models()
    
    performances = benchmark.run_comprehensive_benchmark(
        models_to_test=models,
        scenarios_to_test=[scenario],
        samples_per_scenario=5  # More samples for detailed analysis
    )
    
    # Save results
    benchmark.save_results(f"scenario_analysis_{scenario}")
    
    # Generate scenario-specific report
    report_gen = BenchmarkReportGenerator(performances, benchmark.results)
    report_gen.generate_scenario_analysis_report(
        scenario, 
        f"scenario_analysis_{scenario}/analysis.md"
    )
    
    print(f"\n✅ Scenario analysis completed!")

def main():
    """Main entry point with command-line interface."""
    
    parser = argparse.ArgumentParser(description="Vision Model Benchmark Runner")
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Quick test command
    quick_parser = subparsers.add_parser('quick', help='Run quick test with subset of models')
    quick_parser.add_argument('--models', nargs='+', help='Specific models to test')
    
    # Comprehensive benchmark command
    comp_parser = subparsers.add_parser('comprehensive', help='Run comprehensive benchmark')
    comp_parser.add_argument('--models', nargs='+', help='Specific models to test')
    comp_parser.add_argument('--scenarios', nargs='+', help='Specific scenarios to test')
    comp_parser.add_argument('--samples', type=int, default=3, help='Samples per scenario')
    
    # Model comparison command
    compare_parser = subparsers.add_parser('compare', help='Compare two models head-to-head')
    compare_parser.add_argument('model1', help='First model to compare')
    compare_parser.add_argument('model2', help='Second model to compare')
    
    # Scenario analysis command
    scenario_parser = subparsers.add_parser('scenario', help='Analyze specific scenario')
    scenario_parser.add_argument('scenario', help='Scenario to analyze')
    scenario_parser.add_argument('--models', nargs='+', help='Specific models to test')
    
    # List available options
    list_parser = subparsers.add_parser('list', help='List available models and scenarios')
    
    args = parser.parse_args()
    
    if args.command == 'quick':
        run_quick_test(args.models)
    
    elif args.command == 'comprehensive':
        run_comprehensive_benchmark(
            models=args.models,
            scenarios=args.scenarios, 
            samples_per_scenario=args.samples
        )
    
    elif args.command == 'compare':
        if args.model1 not in AVAILABLE_MODELS:
            print(f"❌ Unknown model: {args.model1}")
            return
        if args.model2 not in AVAILABLE_MODELS:
            print(f"❌ Unknown model: {args.model2}")
            return
        run_model_comparison(args.model1, args.model2)
    
    elif args.command == 'scenario':
        run_scenario_analysis(args.scenario, args.models)
    
    elif args.command == 'list':
        print("📱 AVAILABLE MODELS:")
        for model_name, config in AVAILABLE_MODELS.items():
            print(f"  {model_name} - {config.full_name} ({config.size})")
        
        print(f"\n🎯 AVAILABLE SCENARIOS:")
        for scenario_name, config in TEST_SCENARIOS.items():
            print(f"  {scenario_name} - {config['description']}")
    
    else:
        parser.print_help()

if __name__ == "__main__":
    main()