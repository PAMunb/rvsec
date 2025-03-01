#!/usr/bin/env python3
# rvandroid/tools/llm_selector.py

import argparse
import json
import os
from typing import Dict, Any

from rvandroid.llm.llm_config import get_predefined_config


def get_available_models_and_strategies():
    """
    Get available models and strategies.
    
    Returns:
        Dictionary of available models and strategies
    """
    from rvandroid.llm.model_factory import ModelFactory
    from rvandroid.llm.prompt.prompt_strategy_factory import PromptStrategyFactory

    models = ModelFactory.get_available_models()
    strategies = list(PromptStrategyFactory.get_available_strategies().keys())

    return {
        "models": models,
        "strategies": strategies
    }


def save_config(config: Dict[str, Any], config_file: str = "llm_config.json"):
    """
    Save configuration to a file.
    
    Args:
        config: Configuration dictionary
        config_file: Path to save configuration
    """
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"Configuration saved to {config_file}")


def set_environment(config: Dict[str, Any]):
    """
    Set environment variables from configuration.
    
    Args:
        config: Configuration dictionary
    """
    os.environ["RV_MODEL_TYPE"] = config["model_type"]
    os.environ["RV_MODEL_NAME"] = config["model_name"]
    os.environ["RV_STRATEGY_TYPE"] = config["strategy_type"]

    if "model_kwargs" in config:
        os.environ["RV_MODEL_KWARGS"] = json.dumps(config["model_kwargs"])

    print("Environment variables set:")
    print(f"  RV_MODEL_TYPE={config['model_type']}")
    print(f"  RV_MODEL_NAME={config['model_name']}")
    print(f"  RV_STRATEGY_TYPE={config['strategy_type']}")


def main():
    parser = argparse.ArgumentParser(description="RV-Android LLM Configuration Selector")

    parser.add_argument("--list", action="store_true", help="List available models and strategies")
    parser.add_argument("--use", type=str, help="Use a predefined configuration (local, ollama, claude, gpt, gemini)")
    parser.add_argument("--model-type", type=str, help="Set model type")
    parser.add_argument("--model-name", type=str, help="Set model name")
    parser.add_argument("--strategy", type=str, help="Set prompt strategy")
    parser.add_argument("--api-key", type=str, help="Set API key for cloud models")
    parser.add_argument("--save", type=str, help="Save configuration to file")

    args = parser.parse_args()

    if args.list:
        available = get_available_models_and_strategies()
        print("Available model types:")
        for model_type, models in available["models"].items():
            print(f"  {model_type}:")
            for model in models:
                print(f"    - {model}")

        print("\nAvailable strategies:")
        for strategy in available["strategies"]:
            print(f"  - {strategy}")
        return

    # Initialize configuration
    config = {}

    # Load predefined configuration
    if args.use:
        try:
            config = get_predefined_config(args.use)
            print(f"Using predefined configuration: {args.use}")
        except ValueError as e:
            print(f"Error: {e}")
            return

    # Override with command line arguments
    if args.model_type:
        config["model_type"] = args.model_type

    if args.model_name:
        config["model_name"] = args.model_name

    if args.strategy:
        config["strategy_type"] = args.strategy

    if args.api_key:
        if "model_kwargs" not in config:
            config["model_kwargs"] = {}
        config["model_kwargs"]["api_key"] = args.api_key

    # Ensure we have required fields
    required_fields = ["model_type", "model_name", "strategy_type"]
    missing_fields = [field for field in required_fields if field not in config]

    if missing_fields:
        print(f"Error: Missing required fields: {', '.join(missing_fields)}")
        print("Please use --use or specify --model-type, --model-name, and --strategy")
        return

    # Save configuration if requested
    if args.save:
        save_config(config, args.save)

    # Always set environment variables
    set_environment(config)


if __name__ == "__main__":
    main()
