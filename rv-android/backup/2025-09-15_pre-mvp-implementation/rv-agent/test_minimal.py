#!/usr/bin/env python3
"""
Minimal test for RVAgent prototype - 1 app, 1 screenshot, 1 parameter combination.

Ultra-simple test to validate the pipeline before running full grid search.
"""
import sys
from pathlib import Path
from datetime import datetime

# Add module to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rv_agent.config import PrototypeConfig
from rv_agent.prototype_executor import create_prototype_executor
from rv_android_core.util.logging.manager import LoggingManager


def setup_logging():
    """Setup simple console logging."""
    logging_manager = LoggingManager.get_instance()
    logging_manager.configure_logging(
        level="INFO",
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    return logging_manager.get_logger("rv_agent.test_minimal")


def main():
    """Run minimal test with 1 app, 1 screenshot, 1 parameter combination."""
    logger = setup_logging()
    
    print("=" * 60)
    print("RVAgent Prototype - MINIMAL TEST")
    print("1 app, 1 screenshot, 1 parameter combination, 60s timeout")
    print("=" * 60)
    
    try:
        # Minimal configuration
        config = PrototypeConfig(
            # MINIMAL TEST PARAMETERS
            NUM_TEST_APPS=1,            # Just 1 app
            SCREENSHOTS_PER_APP=1,      # Just 1 screenshot
            TIMEOUT_SECONDS=60,         # 1 minute timeout
            
            # SINGLE PARAMETER VALUES (no grid search)
            TEMPERATURES=[0.3],         # Just 1 temperature
            TOP_PS=[0.9],              # Just 1 top_p
            TOP_KS=[40],               # Just 1 top_k
            
            # Standard configuration
            PRIMARY_MODEL="qwen2.5vl:7b",
            COORDINATE_TOLERANCE=50,
            RANDOM_SEED=42
        )
        
        print(f"Total tests: {config.total_tests}")
        print(f"Estimated duration: {config.estimated_duration_hours * 60:.1f} minutes")
        print()
        
        # Show which app will be tested
        available_apps = config.get_available_apps()
        selected_apps = config.random_select_apps(1)
        sample_screenshots = config.random_select_screenshots(selected_apps[0], 1)
        
        print(f"Selected app: {selected_apps[0]}")
        print(f"Selected screenshot: {sample_screenshots[0]}")
        print(f"Parameters: temp=0.3, top_p=0.9, top_k=40")
        print()
        
        # Verify files exist
        image_path, xml_path = config.get_screenshot_files(selected_apps[0], sample_screenshots[0])
        print(f"Image file: {Path(image_path).name} ({'✓' if Path(image_path).exists() else '✗'})")
        print(f"XML file: {Path(xml_path).name} ({'✓' if Path(xml_path).exists() else '✗'})")
        print()
        
        # Ask for confirmation
        response = input("Proceed with minimal test? (y/n): ").strip().lower()
        if response != 'y':
            print("Test cancelled.")
            return 0
        
        print("Starting minimal test execution...")
        print("-" * 60)
        
        # Execute test
        executor = create_prototype_executor(config)
        report = executor.run()
        
        # Show results
        print("-" * 60)
        print("MINIMAL TEST RESULTS")
        print("-" * 60)
        
        if report.all_results:
            result = report.all_results[0]
            
            print(f"App: {result.app_name}")
            print(f"Screenshot: {result.screenshot_id}")
            print(f"Model: {result.model_name}")
            print(f"Parameters: temp={result.temperature}, top_p={result.top_p}, top_k={result.top_k}")
            print()
            
            print(f"Success: {'✓' if result.success else '✗'}")
            print(f"Execution Time: {result.execution_time:.2f}s")
            print(f"Timeout: {'Yes' if result.timeout_occurred else 'No'}")
            
            if result.error:
                print(f"Error: {result.error}")
            
            if result.generated_coordinates:
                print(f"Generated Coordinates: {result.generated_coordinates}")
                print(f"Closest Ground Truth: {result.closest_ground_truth}")
                print(f"Distance: {result.distance_to_closest:.1f}px")
                print(f"Tolerance: {result.tolerance}px")
                print(f"Ground Truth Elements: {result.ground_truth_count}")
            
            if result.llm_metrics:
                m = result.llm_metrics
                print()
                print("LLM Metrics:")
                print(f"  Input Tokens: {m.prompt_tokens}")
                print(f"  Output Tokens: {m.output_tokens}")
                print(f"  Total Duration: {m.total_duration / 1e9:.2f}s")
                print(f"  Tokens/sec (output): {m.tokens_per_second_output:.1f}")
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"minimal_test_results_{timestamp}.json"
        executor.save_final_results(results_file)
        
        print()
        print("-" * 60)
        print(f"✓ Minimal test completed successfully!")
        print(f"Results saved to: {results_file}")
        
        if report.all_results and report.all_results[0].success:
            print("✓ Pipeline working correctly - ready for full grid search!")
        else:
            print("⚠ Test failed - check configuration before full run")
        
        print("-" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"Minimal test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())