"""
Predefined configuration sets for test framework evaluation.

This module provides curated test configurations using the existing rv-platform
ToolConfig infrastructure. All configurations use the same patterns that work
in rv-experiment, ensuring compatibility and correct behavior.

### Design Principles:
- Uses rv-platform ToolConfig directly (no custom structures)
- Leverages existing RVAndroid tool variants from registry
- Parameters override variant defaults as needed
- User responsibility for configuration correctness
- System automatically groups by model for parallel execution
"""

from typing import List, Dict, Any
from rv_platform.config.platform_config import ToolConfig


def get_basic_evaluation_configs() -> List[ToolConfig]:
    """
    Get basic evaluation configurations for quick testing.
    
    These configurations cover essential test scenarios with
    minimal variations for rapid evaluation.
    
    Returns:
        List of ToolConfig instances for basic evaluation
    """
    return [
        # Vision strategy with default settings
        ToolConfig(
            name="rvandroid",
            variants=["vision"],  # Uses predefined vision variant
            parameters={}  # Use all defaults from variant
        ),
        
        # Vision with MOP strategy
        ToolConfig(
            name="rvandroid",
            variants=["vision"],
            parameters={
                "prompt_strategy": "mop_vision",
                "ui_coverage_enabled": True,
                "temperature": 0.7,
                "max_actions": 3
            }
        ),
        
        # Standard strategy for comparison
        ToolConfig(
            name="rvandroid",
            variants=["default"],
            parameters={
                "prompt_strategy": "single",
                "context_mode": "stateless"
            }
        )
    ]


def get_extended_evaluation_configs() -> List[ToolConfig]:
    """
    Get extended evaluation configurations for comprehensive testing.
    
    These configurations provide thorough coverage of different
    strategies, context modes, and model combinations.
    
    Returns:
        List of ToolConfig instances for extended evaluation
    """
    configs = []
    
    # Vision strategy variations
    vision_variations = [
        # Basic vision
        {"prompt_strategy": "vision"},
        # Vision with MOP
        {"prompt_strategy": "mop_vision", "ui_coverage_enabled": True},
        # Vision with different temperatures
        {"prompt_strategy": "vision", "temperature": 0.3},
        {"prompt_strategy": "vision", "temperature": 0.7},
    ]
    
    for params in vision_variations:
        configs.append(ToolConfig(
            name="rvandroid",
            variants=["vision"],
            parameters=params
        ))
    
    # Context mode variations with vision_ctx variant
    context_variations = [
        # Rich context with compression
        {"context_window_size": 10, "context_compression": True},
        # Rich context without compression
        {"context_window_size": 5, "context_compression": False},
        # Larger context window
        {"context_window_size": 15, "context_compression": True},
    ]
    
    for params in context_variations:
        configs.append(ToolConfig(
            name="rvandroid",
            variants=["vision_ctx"],  # Uses variant with rich context
            parameters=params
        ))
    
    # Different model configurations
    model_configs = [
        # Default with different models (override model in params)
        {
            "llm_model": "llama3.2:3b",
            "context_mode": "rich",
            "temperature": 0.5
        },
        {
            "llm_model": "llama3.2:11b-vision", 
            "vision": True,
            "prompt_strategy": "vision",
            "temperature": 0.3
        },
        {
            "llm_model": "gemma3:4b",  # Gemma is multimodal
            "vision": True,
            "prompt_strategy": "mop_vision",
            "ui_coverage_enabled": True
        }
    ]
    
    for params in model_configs:
        configs.append(ToolConfig(
            name="rvandroid",
            variants=["default"],  # Start from default, override with params
            parameters=params
        ))
    
    return configs


def get_timeout_variation_configs(base_configs: List[ToolConfig] = None) -> List[ToolConfig]:
    """
    Create timeout variations of base configurations.
    
    This is handled by the test framework at task generation time,
    but we provide this helper for explicit timeout testing.
    
    Args:
        base_configs: Base configurations to vary (uses basic if None)
        
    Returns:
        List of ToolConfig instances with timeout variations
    """
    if base_configs is None:
        base_configs = get_basic_evaluation_configs()
    
    # Timeout variations are handled at framework level
    # This function is mainly for documentation purposes
    return base_configs


def get_model_comparison_configs() -> List[ToolConfig]:
    """
    Get configurations for comparing different models with same strategy.
    
    Useful for evaluating model performance differences while
    keeping other parameters constant.
    
    Returns:
        List of ToolConfig instances for model comparison
    """
    models = [
        "gemma3:4b",
        "llama3.2:3b", 
        "llama3.2:11b-vision"
    ]
    
    configs = []
    
    # Same strategy, different models
    for model in models:
        # Vision strategy comparison
        configs.append(ToolConfig(
            name="rvandroid",
            variants=["vision"],
            parameters={
                "llm_model": model,
                "prompt_strategy": "vision",
                "temperature": 0.3,
                "max_tokens": 500
            }
        ))
        
        # MOP Vision comparison (if model supports vision)
        if "vision" in model or model == "gemma3:4b":  # Gemma is multimodal
            configs.append(ToolConfig(
                name="rvandroid",
                variants=["vision"],
                parameters={
                    "llm_model": model,
                    "prompt_strategy": "mop_vision",
                    "ui_coverage_enabled": True,
                    "temperature": 0.7
                }
            ))
    
    return configs


def get_all_evaluation_configs() -> List[ToolConfig]:
    """
    Get all evaluation configurations combined.
    
    Returns:
        Complete list of all evaluation configurations
    """
    all_configs = []
    all_configs.extend(get_basic_evaluation_configs())
    all_configs.extend(get_extended_evaluation_configs())
    all_configs.extend(get_model_comparison_configs())
    return all_configs


# Test configurations for validation - 2 mop_vision configs with different context modes
TEST_VALIDATION_CONFIGS = [
    # MOP Vision with stateless context - single test
    ToolConfig(
        name="rvandroid",
        variants=["vision"],
        parameters={
            "prompt_strategy": "mop_vision",
            "context_mode": "stateless", 
            "context_window_size": 5,
            "ui_coverage_enabled": True,
            "temperature": 0.7,
            "max_actions": 3,
            "llm_model": "gemma3:4b"
        }
    )
]

# Keep original configs for compatibility
TEST_EXPERIMENT_CONFIGS = TEST_VALIDATION_CONFIGS