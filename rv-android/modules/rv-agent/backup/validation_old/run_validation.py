#!/usr/bin/env python3
"""
Main Validation Runner for Gemma3-tools Coordinate Validation

Provides interactive menu to run different validation tests.
Runs with Poetry and logs to files for analysis.
"""

import sys
import os
import logging
from datetime import datetime
from pathlib import Path

# Add the validation directory to Python path
sys.path.append(str(Path(__file__).parent))

from quick_test import quick_test, test_all_strategies
from incremental_test import IncrementalValidator


def setup_logging():
    """Setup logging to file for analysis."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"validation_log_{timestamp}.log"

    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    log_path = f"logs/{log_file}"

    # Setup logging configuration
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler(sys.stdout)
        ]
    )

    logger = logging.getLogger("validation_runner")
    logger.info(f"Logging started. Log file: {log_path}")

    return log_path


def print_banner():
    """Print validation suite banner."""
    print("\n" + "="*70)
    print("🧪 COORDINATE VALIDATION SUITE - GEMMA3-TOOLS")
    print("="*70)
    print("Protótipo para validação de precisão de coordenadas")
    print("Modelo: PetrosStav/gemma3-tools:4b")
    print("Dataset: /home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")
    print("="*70)


def check_prerequisites():
    """Check if prerequisites are available."""
    print("🔍 Checking prerequisites...")

    # Check if dataset exists
    dataset_path = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")
    if not dataset_path.exists():
        print(f"❌ Dataset not found: {dataset_path}")
        return False

    # Check if cryptoapp exists
    cryptoapp_path = dataset_path / "cryptoapp.apk"
    if not cryptoapp_path.exists():
        print(f"❌ Cryptoapp not found: {cryptoapp_path}")
        return False

    # Check if screenshots exist
    screenshots = list(cryptoapp_path.glob("*.png"))
    if not screenshots:
        print(f"❌ No screenshots found in {cryptoapp_path}")
        return False

    print(f"✅ Dataset found with {len(screenshots)} cryptoapp screenshots")

    # Check if XMLs exist
    xmls = list(cryptoapp_path.glob("*.uiautomator"))
    print(f"✅ Found {len(xmls)} XML files")

    return True


def show_menu():
    """Show interactive menu."""
    print("\n📋 VALIDATION OPTIONS:")
    print("1. 🚀 Quick Test (1 screenshot, baseline strategy)")
    print("2. 🔬 Strategy Comparison (1 screenshot, all strategies)")
    print("3. 📈 Incremental Test (gradual increase from 1 to many)")
    print("4. 📊 Full Validation (multiple apps, all strategies)")
    print("5. 🔧 Custom Test (configure your own)")
    print("6. ❓ Show Help")
    print("0. 🚪 Exit")
    print("-" * 50)


def run_quick_test():
    """Run quick test option."""
    print("\n🚀 Running Quick Test...")
    result = quick_test()

    if result and result.get("success", False):
        print("\n✅ Quick test completed successfully!")
        return True
    else:
        print("\n❌ Quick test failed!")
        return False


def run_strategy_comparison():
    """Run strategy comparison option."""
    print("\n🔬 Running Strategy Comparison...")
    results = test_all_strategies()

    successful = sum(1 for r in results.values() if r.get("success", False))
    print(f"\n📊 Strategy comparison completed: {successful}/{len(results)} strategies successful")

    return successful > 0


def run_incremental_test():
    """Run incremental test option."""
    print("\n📈 Running Incremental Test...")
    print("This will start with minimal tests and gradually increase complexity.")

    choice = input("\nProceed? (y/n): ").lower().strip()
    if choice != 'y':
        print("Incremental test cancelled.")
        return False

    validator = IncrementalValidator()
    results = validator.run_incremental_test(
        start_level=0,
        stop_at_failure=False
    )

    levels_completed = len([r for r in results.values() if r.get("successful_tests", 0) > 0])
    print(f"\n📊 Incremental test completed: {levels_completed} levels tested")

    return levels_completed > 0


def run_full_validation():
    """Run full validation option."""
    print("\n📊 Running Full Validation...")
    print("This will test multiple apps with all strategies.")
    print("⚠️  This may take 10-30 minutes depending on model speed.")

    choice = input("\nProceed? (y/n): ").lower().strip()
    if choice != 'y':
        print("Full validation cancelled.")
        return False

    from coordinate_validator import main
    print("Starting full validation...")

    try:
        result = main()
        print("\n✅ Full validation completed!")
        return True
    except Exception as e:
        print(f"\n❌ Full validation failed: {e}")
        return False


def run_custom_test():
    """Run custom test with user configuration."""
    print("\n🔧 Custom Test Configuration")
    print("Available apps:")

    dataset_path = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")
    apps = [d.name for d in dataset_path.iterdir() if d.is_dir() and d.name.endswith('.apk')]

    for i, app in enumerate(apps, 1):
        print(f"  {i}. {app}")

    app_choice = input(f"\nSelect app (1-{len(apps)}): ").strip()
    try:
        selected_app = apps[int(app_choice) - 1]
    except (ValueError, IndexError):
        print("Invalid choice.")
        return False

    strategies = ["baseline", "coordinate_validation", "enhanced_description",
                  "element_priority", "spinner_focused"]

    print("\nAvailable strategies:")
    for i, strategy in enumerate(strategies, 1):
        print(f"  {i}. {strategy}")

    strategy_choice = input(f"\nSelect strategy (1-{len(strategies)}): ").strip()
    try:
        selected_strategy = strategies[int(strategy_choice) - 1]
    except (ValueError, IndexError):
        print("Invalid choice.")
        return False

    samples = input("\nNumber of screenshots to test (1-10): ").strip()
    try:
        num_samples = int(samples)
        if not 1 <= num_samples <= 10:
            raise ValueError()
    except ValueError:
        print("Invalid number.")
        return False

    print(f"\n🔧 Running custom test:")
    print(f"  App: {selected_app}")
    print(f"  Strategy: {selected_strategy}")
    print(f"  Samples: {num_samples}")

    from coordinate_validator import CoordinateValidator

    validator = CoordinateValidator()
    results = validator.validate_dataset(
        dataset_path=str(dataset_path),
        apps=[selected_app],
        strategies=[selected_strategy],
        samples_per_app=num_samples
    )

    if results.get("successful_tests", 0) > 0:
        print("\n✅ Custom test completed successfully!")
        if "strategy_stats" in results:
            stats = results["strategy_stats"][selected_strategy]
            print(f"Hit Rate: {stats['hit_rate']:.1f}%")
            print(f"Avg Distance: {stats['avg_distance']:.1f}px")
        return True
    else:
        print("\n❌ Custom test failed!")
        return False


def show_help():
    """Show help information."""
    print("\n" + "="*60)
    print("📖 VALIDATION SUITE HELP")
    print("="*60)
    print("""
🚀 Quick Test:
   Tests with 1 screenshot using baseline strategy.
   Best for: First-time verification that everything works.

🔬 Strategy Comparison:
   Tests 1 screenshot with all 5 prompt strategies.
   Best for: Understanding which strategy works best.

📈 Incremental Test:
   Starts with minimal test and gradually increases complexity.
   Best for: Systematic evaluation from simple to complex.

📊 Full Validation:
   Tests multiple apps with all strategies (complete dataset).
   Best for: Final comprehensive evaluation.

🔧 Custom Test:
   Configure your own test parameters.
   Best for: Focused testing of specific scenarios.

Strategies Available:
- baseline: Simple prompt without coordinates
- coordinate_validation: Provides exact XML coordinates (Phase 0 method)
- enhanced_description: Rich descriptions with spatial hints
- element_priority: Prioritizes untested elements and spinners
- spinner_focused: Special focus on dropdown/spinner elements

Output Files:
- validation_results_*.json: Detailed metrics
- incremental_*.json: Incremental test results
- Raw logs show LLM explanations and decisions
""")


def main():
    """Main interactive validation runner."""
    print_banner()

    if not check_prerequisites():
        print("\n❌ Prerequisites check failed!")
        print("Please ensure dataset is available and accessible.")
        return 1

    while True:
        show_menu()
        choice = input("Select option (0-6): ").strip()

        if choice == "0":
            print("\n👋 Goodbye!")
            break
        elif choice == "1":
            run_quick_test()
        elif choice == "2":
            run_strategy_comparison()
        elif choice == "3":
            run_incremental_test()
        elif choice == "4":
            run_full_validation()
        elif choice == "5":
            run_custom_test()
        elif choice == "6":
            show_help()
        else:
            print("❌ Invalid option. Please choose 0-6.")

        input("\nPress Enter to continue...")

    return 0


if __name__ == "__main__":
    sys.exit(main())