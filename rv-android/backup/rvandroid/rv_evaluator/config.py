# rvandroid/llm/evaluator/config.py
"""
Configuration constants and settings for the LLM evaluator system.

This module centralizes all configuration parameters for the LLM evaluation framework,
including model specifications, parameter ranges, and execution settings.

### Architectural Decisions:
- Implements hardcoded configuration approach for simplicity and reproducibility
- Provides centralized parameter management for systematic testing
- Supports multiple model types and parameter combinations
- Enables easy modification of evaluation parameters without code changes
- Maintains clear separation between configuration and execution logic

### Role in the System:
- Acts as the single source of truth for evaluation parameters
- Defines model configurations and parameter ranges for testing
- Specifies execution settings and timeout values
- Provides template configurations for consistent testing
- Enables systematic exploration of parameter space

### Key Considerations:
- GPU memory constraint of 8GB limits model selection
- Temperature and other parameters chosen for meaningful comparison
- Prompt directory structure supports external prompt management
- Timeout settings balance thoroughness with practical execution time
- Repetition count ensures statistical significance
"""

import os
from typing import List, Dict, Any, Tuple

# ===== EXECUTION SETTINGS =====

# Number of repetitions per configuration for statistical significance
REPETITIONS_PER_CONFIG = 2

# Number of warm-up runs to discard (not counted in results)
WARMUP_RUNS = 2

# Timeout for each LLM generation call (seconds)
GENERATION_TIMEOUT = 30

# Default prompts directory (can be overridden)
DEFAULT_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")

# ===== MODEL CONFIGURATION =====

# Models to evaluate (considering 8GB GPU constraint)
# Prioritizing smaller, efficient models that fit in VRAM
MODELS_TO_TEST = [
    # "llama3.2:3b",  # ~2GB VRAM - Fast and efficient
    # "gemma2:2b",  # ~1.5GB VRAM - Very lightweight
    # "phi3.5:3.8b",  # ~2.5GB VRAM - Microsoft's efficient model
    # "qwen2.5:3b",  # ~2GB VRAM - Alibaba's model
    # "deepseek-r1:1.5b",  # ~1GB VRAM - Extremely lightweight

    # "deepseek-r1:1.5B",
    "falcon3:1b",
    # "falcon3:3b",
    "gemma3:1b",
    # "gemma3:4b",
    "granite3.3:2b",
    "llama3.2:1b",
    # "llama3.2:3b",
    # "phi4-mini-reasoning:3.8b",
    "phi4-mini:latest",
    "qwen3:0.6b",
    # "qwen3:1.7b",
    # "qwen3:4b"
]

# ===== PARAMETER RANGES =====

# Temperature values for testing randomness vs consistency
TEMPERATURE_VALUES = [0.1, 0.2, 0.3]

# Top-p (nucleus sampling) values for token selection
TOP_P_VALUES = [0.7, 0.9, 1.0]

# Maximum tokens to generate
MAX_TOKENS_VALUES = [300, 500, 800]

# Top-k values for token selection (0 means disabled)
TOP_K_VALUES = [0, 20, 40, 80]

# ===== STRATEGY CONFIGURATION =====

# Prompt strategies to test
# TODO: remover, os prompts ja estao prontos, nao precisa gerar
STRATEGIES_TO_TEST = [
    # "standard_modular",  # StandardStrategy - single action
    "batch_action_modular"  # BatchActionStrategy - multiple actions
]

# ===== OUTPUT CONFIGURATION =====

# Output file names (simple naming convention)
DETAILED_RESULTS_FILE = "detailed_results.csv"
SUMMARY_RESULTS_FILE = "summary_results.csv"
ANALYSIS_REPORT_FILE = "analysis_report.md"


# ===== PROMPT CONFIGURATION =====

def get_prompt_pairs(prompts_dir: str = None) -> List[Tuple[str, str, str]]:
    """
    Get all available prompt pairs from the prompts directory.

    Args:
        prompts_dir: Directory containing prompt files (optional)

    Returns:
        List of tuples (prompt_id, system_file, user_file)
    """
    if prompts_dir is None:
        prompts_dir = DEFAULT_PROMPTS_DIR

    if not os.path.exists(prompts_dir):
        raise FileNotFoundError(f"Prompts directory not found: {prompts_dir}")

    prompt_pairs = []
    files = os.listdir(prompts_dir)

    # Find all system prompt files and match with user prompts
    system_files = [f for f in files if f.endswith('_system.txt')]

    for system_file in system_files:
        # Extract prompt ID from filename (e.g., "001_system.txt" -> "001")
        prompt_id = system_file.replace('_system.txt', '')
        user_file = f"{prompt_id}_user.txt"

        # Check if corresponding user file exists
        if user_file in files:
            system_path = os.path.join(prompts_dir, system_file)
            user_path = os.path.join(prompts_dir, user_file)
            prompt_pairs.append((prompt_id, system_path, user_path))

    # Sort by prompt ID for consistent ordering
    prompt_pairs.sort(key=lambda x: x[0])

    return prompt_pairs


# ===== OLLAMA CONFIGURATION =====

# Base URL for Ollama API
OLLAMA_BASE_URL = "http://192.168.0.20:11434"

# Default Ollama model parameters
DEFAULT_OLLAMA_KWARGS = {
    "base_url": OLLAMA_BASE_URL
}


# ===== EVALUATION CONFIGURATION =====

def generate_all_configurations() -> List[Dict[str, Any]]:
    """
    Generate all possible configuration combinations for testing.

    Returns:
        List of configuration dictionaries for systematic evaluation
    """
    configurations = []

    for model in MODELS_TO_TEST:
        for strategy in STRATEGIES_TO_TEST:
            for temperature in TEMPERATURE_VALUES:
                for top_p in TOP_P_VALUES:
                    for max_tokens in MAX_TOKENS_VALUES:
                        for top_k in TOP_K_VALUES:
                            config = {
                                "model": model,
                                "strategy": strategy,
                                "temperature": temperature,
                                "top_p": top_p,
                                "max_tokens": max_tokens,
                                "top_k": top_k
                            }
                            configurations.append(config)

    return configurations


# ===== METRICS CONFIGURATION =====

# Metrics to calculate and export
METRICS_TO_COLLECT = [
    # Performance metrics
    "total_duration_ms",
    "load_duration_ms",
    "input_tokens",
    "input_tokens_duration_ms",
    "output_tokens",
    "output_tokens_duration_ms",

    # Derived metrics
    "tokens_per_second",
    "input_output_ratio",
    "generation_latency_ms",

    # Quality metrics
    "parsing_success",
    "response_length_chars",
    "actions_count",
    "explanation_quality_score",

    # Error metrics
    "error_occurred",
    "error_type",
    "timeout_occurred"
]

# Statistical metrics to calculate for summary
SUMMARY_STATISTICS = [
    "mean",
    "median",
    "std_dev",
    "min",
    "max",
    "success_rate"
]
