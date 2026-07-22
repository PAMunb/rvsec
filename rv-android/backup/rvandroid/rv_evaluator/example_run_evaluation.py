# example_run_evaluation.py
"""
Example script for running LLM evaluation with custom settings.

This script demonstrates how to run the LLM evaluator with different
configurations and settings for various use cases.
"""

import os
import sys
from datetime import datetime

from rvandroid.llm.ollama_llm import OllamaLLM
# Add RV-Android to path (adjust as needed for your setup)
# sys.path.insert(0, '/path/to/rv-android')

from rvandroid.rv_evaluator.evaluator import LLMEvaluator
from rvandroid.rv_evaluator import config


def quick_evaluation():
    """Run a quick evaluation with minimal configurations for testing."""
    print("=== QUICK EVALUATION MODE ===")

    # Temporarily modify config for quick testing
    original_models = config.MODELS_TO_TEST
    original_repetitions = config.REPETITIONS_PER_CONFIG
    original_temp_values = config.TEMPERATURE_VALUES

    # Quick settings
    config.MODELS_TO_TEST = [OllamaLLM.QWEN, OllamaLLM.LLAMA]  # Test only 2 models
    config.REPETITIONS_PER_CONFIG = 1  # Fewer repetitions
    config.TEMPERATURE_VALUES = [0.2, 0.7]  # Test only 2 temperatures
    config.TOP_P_VALUES = [1.0]
    config.MAX_TOKENS_VALUES = [800]
    config.TOP_K_VALUES = [0]

    try:
        evaluator = LLMEvaluator(
            prompts_dir="./prompts",
            output_dir="./quick_results"
        )

        detailed_file, summary_file, analysis_file = evaluator.run_evaluation()

        print(f"\nQuick evaluation completed!")
        print(f"Results saved to: ./quick_results/")

        # Show quick summary
        summary = evaluator.get_evaluation_summary()
        if summary.get("status") == "completed":
            best = summary["best_configuration"]
            print(f"\nBest config: {best['model']} | {best['strategy']} | T={best['temperature']}")
            print(f"Score: {best['overall_score']:.1f}/100")

    finally:
        # Restore original config
        config.MODELS_TO_TEST = original_models
        config.REPETITIONS_PER_CONFIG = original_repetitions
        config.TEMPERATURE_VALUES = original_temp_values


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


def custom_model_evaluation():
    """Run evaluation with custom model selection."""
    print("=== CUSTOM MODEL EVALUATION ===")

    # Define custom models to test
    custom_models = [
        "llama3.2:3b",
        "phi3.5:3.8b",
        "qwen2.5:3b"
    ]

    # Temporarily override config
    original_models = config.MODELS_TO_TEST
    config.MODELS_TO_TEST = custom_models

    try:
        evaluator = LLMEvaluator(
            prompts_dir="./prompts",
            output_dir="./custom_model_results"
        )

        print(f"Testing models: {', '.join(custom_models)}")

        detailed_file, summary_file, analysis_file = evaluator.run_evaluation()

        print(f"\nCustom model evaluation completed!")

    finally:
        # Restore original config
        config.MODELS_TO_TEST = original_models


def parameter_sensitivity_analysis():
    """Run evaluation focusing on parameter sensitivity."""
    print("=== PARAMETER SENSITIVITY ANALYSIS ===")

    # Test wide range of temperatures with single model
    original_models = config.MODELS_TO_TEST
    original_temps = config.TEMPERATURE_VALUES

    config.MODELS_TO_TEST = ["llama3.2:3b"]  # Focus on one model
    config.TEMPERATURE_VALUES = [0.1, 0.2, 0.3, 0.5, 0.7, 0.9]  # Wide range

    try:
        evaluator = LLMEvaluator(
            prompts_dir="./prompts",
            output_dir="./parameter_analysis"
        )

        print("Analyzing temperature sensitivity...")

        detailed_file, summary_file, analysis_file = evaluator.run_evaluation()

        print(f"\nParameter analysis completed!")
        print("Check the analysis report for temperature impact insights.")

    finally:
        # Restore original config
        config.MODELS_TO_TEST = original_models
        config.TEMPERATURE_VALUES = original_temps


def create_example_prompts():
    """Create example prompt files if they don't exist."""
    prompts_dir = "./prompts"

    if not os.path.exists(prompts_dir):
        os.makedirs(prompts_dir)
        print(f"Created prompts directory: {prompts_dir}")

    # Example prompt 1 - Simple
    system_1 = """You are an Android testing assistant. Analyze the screen and suggest ONE testing action.

Respond with JSON format:
{
  "actions": [
    {
      "action_id": 1,
      "params": {},
      "explanation": "Why this action was chosen"
    }
  ]
}"""

    user_1 = """Current screen: Login page

Available actions:
1. CLICK Login Button
2. SET_TEXT Username Field  
3. SET_TEXT Password Field
4. CLICK Register Link

Choose the best action and respond in JSON format."""

    # Example prompt 2 - Detailed
    system_2 = """You are an advanced Android testing assistant. Analyze the application state and recommend testing actions that maximize coverage and discover issues.

Consider:
- Input validation testing
- Edge cases and error conditions  
- User flow progression
- Security considerations

Respond with JSON containing an actions array. Each action needs action_id, params object, and explanation."""

    user_2 = """Comprehensive Analysis:

Activity: PaymentActivity
Package: com.banking.app

Available actions:
1. SET_TEXT Amount Field (required, decimal)
2. SET_TEXT Recipient Field (required, email/phone)
3. CLICK Pay Button (disabled until valid input)
4. CLICK Back Button
5. SELECT Payment Method Dropdown

Current state: Empty form, validation active

Select strategic action for thorough testing."""

    # Write example prompts
    prompts = [
        ("001_system.txt", system_1),
        ("001_user.txt", user_1),
        ("002_system.txt", system_2),
        ("002_user.txt", user_2)
    ]

    for filename, content in prompts:
        filepath = os.path.join(prompts_dir, filename)
        if not os.path.exists(filepath):
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Created example prompt: {filename}")

    print(f"\nExample prompts created in {prompts_dir}/")
    print("You can modify these prompts for your specific use case.")


def main():
    """Main execution function with menu options."""
    print("LLM Configuration Evaluator")
    print("=" * 50)

    # Check if prompts exist
    if not os.path.exists("./prompts") or not any(f.endswith('_system.txt') for f in os.listdir("./prompts")):
        print("No prompts found. Creating example prompts...")
        create_example_prompts()
        print()

    print("Select evaluation mode:")
    print("1. Quick evaluation (fast, minimal configs)")
    print("2. Full evaluation (comprehensive, all configs)")
    print("3. Custom model evaluation")
    print("4. Parameter sensitivity analysis")
    print("5. Create example prompts")
    print("0. Exit")

    choice = input("\nEnter choice (0-5): ").strip()

    if choice == "1":
        quick_evaluation()
    elif choice == "2":
        full_evaluation()
    elif choice == "3":
        custom_model_evaluation()
    elif choice == "4":
        parameter_sensitivity_analysis()
    elif choice == "5":
        create_example_prompts()
    elif choice == "0":
        print("Exiting...")
    else:
        print("Invalid choice. Please run again.")


if __name__ == "__main__":
    main()