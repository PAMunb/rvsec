#!/usr/bin/env python3
"""
Quick benchmark runner to test a subset of models and get initial results.
Uses the diverse app screenshots available in tmp_img/screenshots.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmark_framework import VisionModelBenchmark
from report_generator import BenchmarkReportGenerator
from model_config import list_available_models

def main():
    """Run quick benchmark test."""
    
    print("🚀 QUICK VISION MODEL BENCHMARK")
    print("=" * 60)
    print("Testing coordinate generation across diverse Android applications")
    print()
    
    # Check available screenshots
    screenshots_dir = Path("/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/tmp_img/screenshots")
    
    if not screenshots_dir.exists():
        print(f"❌ Screenshots directory not found: {screenshots_dir}")
        return
    
    # Count available apps
    app_dirs = [d for d in screenshots_dir.iterdir() if d.is_dir()]
    total_samples = 0
    for app_dir in app_dirs:
        samples = list(app_dir.glob("*.png"))
        states = [app_dir / f"{png.stem}.state" for png in samples]
        valid_samples = [png for png, state in zip(samples, states) if state.exists()]
        total_samples += len(valid_samples)
    
    print(f"📱 Found {len(app_dirs)} different applications")
    print(f"📊 Total screenshots with state files: {total_samples}")
    print()
    
    # Select models for quick test
    all_models = list_available_models()
    print(f"🤖 Available models: {len(all_models)}")
    for model in all_models:
        print(f"   - {model}")
    print()
    
    # Quick test with representative models
    test_models = [
        "gemma3:4b",           # Our baseline - best known performer
        "gemma3:12b",          # Larger Gemma version
        "llama3.2-vision:11b", # Meta's vision model
        "qwen2.5vl:7b",        # Qwen's larger model
        "granite3.2-vision:2b" # IBM's efficient model
    ]
    
    # Filter to only available models
    available_test_models = [m for m in test_models if m in all_models]
    
    print(f"🎯 Testing {len(available_test_models)} representative models:")
    for model in available_test_models:
        print(f"   - {model}")
    print()
    
    # Test scenarios
    scenarios = ["coordinate_validation", "visual_generation"]
    print(f"📋 Test scenarios:")
    for scenario in scenarios:
        print(f"   - {scenario}")
    print()
    
    print(f"⚙️ Configuration:")
    print(f"   - 3 samples per scenario per model")
    print(f"   - Total tests: {len(available_test_models)} × {len(scenarios)} × 3 = {len(available_test_models) * len(scenarios) * 3}")
    print()
    
    # Confirm execution
    response = input("🚦 Start benchmark? (y/N): ").lower()
    if response != 'y':
        print("❌ Benchmark cancelled")
        return
    
    print("\n🏁 Starting benchmark...")
    print("=" * 60)
    
    # Initialize benchmark
    benchmark = VisionModelBenchmark()
    
    try:
        # Run comprehensive benchmark
        performances = benchmark.run_comprehensive_benchmark(
            models_to_test=available_test_models,
            scenarios_to_test=scenarios,
            samples_per_scenario=3
        )
        
        # Save results
        output_dir = "quick_benchmark_results"
        benchmark.save_results(output_dir)
        
        if performances:
            # Generate reports
            report_gen = BenchmarkReportGenerator(performances, benchmark.results)
            
            # Generate all reports
            report_gen.generate_summary_report(f"{output_dir}/summary_report.md")
            report_gen.generate_detailed_report(f"{output_dir}/detailed_report.md")
            report_gen.generate_comparison_tables(f"{output_dir}/comparison_tables.md")
            
            try:
                report_gen.save_performance_charts(f"{output_dir}/")
                print("📊 Performance charts generated")
            except Exception as e:
                print(f"⚠️ Could not generate charts: {e}")
            
            print(f"\n✅ Benchmark completed successfully!")
            print(f"📁 Results saved to: {output_dir}/")
            print()
            
            # Print quick summary
            print("🏆 QUICK SUMMARY")
            print("=" * 30)
            
            # Sort by overall success rate
            sorted_models = sorted(
                performances.items(), 
                key=lambda x: x[1].overall_success_rate, 
                reverse=True
            )
            
            print("Model Rankings:")
            for i, (name, perf) in enumerate(sorted_models, 1):
                emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📍"
                print(f"  {emoji} {i}. {name}")
                print(f"      Success: {perf.overall_success_rate*100:.1f}%")
                print(f"      Distance: {perf.avg_distance:.1f}px")
                print(f"      Speed: {perf.avg_response_time:.2f}s")
                print()
            
            # Best performers by category
            best_success = max(performances.items(), key=lambda x: x[1].overall_success_rate)
            best_accuracy = min(performances.items(), key=lambda x: x[1].avg_distance if x[1].avg_distance > 0 else float('inf'))
            best_speed = min(performances.items(), key=lambda x: x[1].avg_response_time)
            
            print("Category Winners:")
            print(f"  🎯 Best Success Rate: {best_success[0]} ({best_success[1].overall_success_rate*100:.1f}%)")
            print(f"  📏 Best Accuracy: {best_accuracy[0]} ({best_accuracy[1].avg_distance:.1f}px)")
            print(f"  ⚡ Fastest: {best_speed[0]} ({best_speed[1].avg_response_time:.2f}s)")
            print()
            
            print("📋 Next Steps:")
            print("  1. Review detailed reports for analysis")
            print("  2. Run comprehensive benchmark with all models")
            print("  3. Test specific scenarios in detail")
            print("  4. Compare top performers head-to-head")
            
        else:
            print("❌ No performance results generated")
    
    except KeyboardInterrupt:
        print("\n⚠️ Benchmark interrupted by user")
        if benchmark.results:
            benchmark.save_results("interrupted_quick_results")
            print("💾 Partial results saved")
    
    except Exception as e:
        print(f"\n❌ Benchmark failed: {e}")
        if benchmark.results:
            benchmark.save_results("error_quick_results")
            print("💾 Partial results saved")

if __name__ == "__main__":
    main()