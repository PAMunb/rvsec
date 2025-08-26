"""
Predefined configuration sets using existing rv-android-core and rv-llm infrastructure.

This module contains manually curated configurations that leverage existing LLMConfig
and ToolConfig classes from the rv-android ecosystem. No validation is performed -
user responsibility for configuration correctness.

### Configuration Strategy:
- **Manual Curation**: User defines meaningful parameter combinations
- **Existing Models**: Uses LLMConfig and ToolConfig from existing modules
- **No Validation**: User responsibility for configuration correctness  
- **Simple Integration**: Direct conversion to Task objects for execution
- **Model Grouping**: Configurations grouped by LLM model for resource optimization
"""

from typing import List, Dict, Any

# Core evaluation configurations covering key testing strategies
EVALUATION_CONFIGS = [
    # Vision Strategy Configurations
    {
        "name": "vision_basic_stateless_gemma",
        "description": "Vision strategy with basic visitor and stateless context using Gemma 3:4B",
        "llm_config": {
            "llm_type": "ollama",
            "model": "gemma3:4b",
            "temperature": 0.3,
            "max_tokens": 800,
            "vision": True,
            "top_p": 0.9,
            "top_k": 40
        },
        "tool_config": {
            "tool_name": "rvandroid",
            "variant": "vision_basic_stateless",
            "additional_params": {
                "strategy": "vision",
                "visitor": "basic", 
                "context_mode": "stateless",
                "timeout": 300
            }
        }
    },
    {
        "name": "vision_default_rich_gemma",
        "description": "Vision strategy with default visitor and rich context using Gemma 3:4B",
        "llm_config": {
            "llm_type": "ollama",
            "model": "gemma3:4b",
            "temperature": 0.3,
            "max_tokens": 800,
            "vision": True,
            "top_p": 0.9,
            "top_k": 40
        },
        "tool_config": {
            "tool_name": "rvandroid",
            "variant": "vision_default_rich",
            "additional_params": {
                "strategy": "vision",
                "visitor": "default",
                "context_mode": "rich",
                "timeout": 300
            }
        }
    },
    {
        "name": "vision_basic_rich_gemma",
        "description": "Vision strategy with basic visitor and rich context using Gemma 3:4B",
        "llm_config": {
            "llm_type": "ollama",
            "model": "gemma3:4b",
            "temperature": 0.3,
            "max_tokens": 800,
            "vision": True,
            "top_p": 0.9,
            "top_k": 40
        },
        "tool_config": {
            "tool_name": "rvandroid",
            "variant": "vision_basic_rich",
            "additional_params": {
                "strategy": "vision",
                "visitor": "basic",
                "context_mode": "rich",
                "timeout": 300
            }
        }
    },
    
    # MOP Vision Strategy Configurations
    {
        "name": "mop_vision_basic_stateless_gemma",
        "description": "MOP Vision strategy with basic visitor and stateless context",
        "llm_config": {
            "llm_type": "ollama", 
            "model": "gemma3:4b",
            "temperature": 0.3,
            "max_tokens": 800,
            "vision": True,
            "top_p": 0.9,
            "top_k": 40
        },
        "tool_config": {
            "tool_name": "rvandroid",
            "variant": "mop_vision_basic_stateless",
            "additional_params": {
                "strategy": "mop_vision",
                "visitor": "basic",
                "context_mode": "stateless",
                "timeout": 300
            }
        }
    },
    {
        "name": "mop_vision_default_rich_gemma",
        "description": "MOP Vision strategy with default visitor and rich context",
        "llm_config": {
            "llm_type": "ollama",
            "model": "gemma3:4b", 
            "temperature": 0.3,
            "max_tokens": 800,
            "vision": True,
            "top_p": 0.9,
            "top_k": 40
        },
        "tool_config": {
            "tool_name": "rvandroid",
            "variant": "mop_vision_default_rich",
            "additional_params": {
                "strategy": "mop_vision",
                "visitor": "default",
                "context_mode": "rich", 
                "timeout": 300
            }
        }
    },
    
    # Standard Strategy Configurations
    {
        "name": "standard_basic_stateless_gemma",
        "description": "Standard strategy with basic visitor and stateless context",
        "llm_config": {
            "llm_type": "ollama",
            "model": "gemma3:4b",
            "temperature": 0.3,
            "max_tokens": 800,
            "vision": False,
            "top_p": 0.9,
            "top_k": 40
        },
        "tool_config": {
            "tool_name": "rvandroid",
            "variant": "standard_basic_stateless",
            "additional_params": {
                "strategy": "standard",
                "visitor": "basic",
                "context_mode": "stateless",
                "timeout": 300
            }
        }
    },
    {
        "name": "standard_default_rich_gemma",
        "description": "Standard strategy with default visitor and rich context",
        "llm_config": {
            "llm_type": "ollama",
            "model": "gemma3:4b",
            "temperature": 0.3,
            "max_tokens": 800,
            "vision": False,
            "top_p": 0.9,
            "top_k": 40
        },
        "tool_config": {
            "tool_name": "rvandroid",
            "variant": "standard_default_rich",
            "additional_params": {
                "strategy": "standard",
                "visitor": "default",
                "context_mode": "rich",
                "timeout": 300
            }
        }
    },

    # Llama 3.2 Vision Configurations  
    {
        "name": "vision_basic_stateless_llama32_vision",
        "description": "Vision strategy with basic visitor using Llama 3.2 11B Vision",
        "llm_config": {
            "llm_type": "ollama",
            "model": "llama3.2:11b-vision",
            "temperature": 0.3,
            "max_tokens": 800,
            "vision": True,
            "top_p": 0.9,
            "top_k": 40
        },
        "tool_config": {
            "tool_name": "rvandroid",
            "variant": "vision_basic_stateless",
            "additional_params": {
                "strategy": "vision",
                "visitor": "basic",
                "context_mode": "stateless",
                "timeout": 300
            }
        }
    },
    {
        "name": "mop_vision_basic_stateless_llama32_vision",
        "description": "MOP Vision strategy using Llama 3.2 11B Vision",
        "llm_config": {
            "llm_type": "ollama",
            "model": "llama3.2:11b-vision",
            "temperature": 0.3,
            "max_tokens": 800,
            "vision": True,
            "top_p": 0.9,
            "top_k": 40
        },
        "tool_config": {
            "tool_name": "rvandroid",
            "variant": "mop_vision_basic_stateless",
            "additional_params": {
                "strategy": "mop_vision",
                "visitor": "basic",
                "context_mode": "stateless",
                "timeout": 300
            }
        }
    },

    # Llama 3.2 Text-Only Configurations
    {
        "name": "standard_basic_stateless_llama32_3b",
        "description": "Standard strategy using fast Llama 3.2 3B text-only model",
        "llm_config": {
            "llm_type": "ollama",
            "model": "llama3.2:3b", 
            "temperature": 0.3,
            "max_tokens": 800,
            "vision": False,
            "top_p": 0.9,
            "top_k": 40
        },
        "tool_config": {
            "tool_name": "rvandroid",
            "variant": "standard_basic_stateless",
            "additional_params": {
                "strategy": "standard",
                "visitor": "basic",
                "context_mode": "stateless",
                "timeout": 300
            }
        }
    },
]


def create_basic_config_set() -> List[Dict[str, Any]]:
    """
    Create basic configuration set for quick evaluation.
    
    Includes essential configurations covering main strategies and models
    for rapid testing and validation.
    
    Returns:
        List of basic configurations
    """
    basic_configs = [
        # Core configurations for basic evaluation
        next(c for c in EVALUATION_CONFIGS if c["name"] == "vision_basic_stateless_gemma"),
        next(c for c in EVALUATION_CONFIGS if c["name"] == "mop_vision_basic_stateless_gemma"),
        next(c for c in EVALUATION_CONFIGS if c["name"] == "standard_basic_stateless_gemma"),
        next(c for c in EVALUATION_CONFIGS if c["name"] == "standard_basic_stateless_llama32_3b"),
    ]
    
    return basic_configs


def create_extended_config_set() -> List[Dict[str, Any]]:
    """
    Create extended configuration set for comprehensive evaluation.
    
    Includes all available configurations for thorough testing
    across different strategies, visitors, context modes, and models.
    
    Returns:
        List of all evaluation configurations
    """
    return EVALUATION_CONFIGS.copy()


def create_timeout_variation_set(base_configs: List[Dict[str, Any]], timeouts: List[int]) -> List[Dict[str, Any]]:
    """
    Create configuration variations with different timeout values.
    
    Useful for timeout optimization experiments and plateau analysis.
    
    Args:
        base_configs: Base configurations to vary
        timeouts: List of timeout values to test
        
    Returns:
        Expanded configuration list with timeout variations
    """
    timeout_configs = []
    
    for base_config in base_configs:
        for timeout in timeouts:
            # Create copy with modified timeout
            timeout_config = base_config.copy()
            timeout_config["name"] = f"{base_config['name']}_timeout_{timeout}"
            timeout_config["description"] = f"{base_config['description']} (timeout: {timeout}s)"
            
            # Update tool config with new timeout
            tool_config = timeout_config["tool_config"].copy()
            tool_config["additional_params"] = tool_config["additional_params"].copy()
            tool_config["additional_params"]["timeout"] = timeout
            timeout_config["tool_config"] = tool_config
            
            timeout_configs.append(timeout_config)
    
    return timeout_configs


def save_configuration_set(configs: List[Dict[str, Any]], output_path: str) -> None:
    """
    Save configuration set to JSON file for framework execution.
    
    Args:
        configs: Configuration list to save
        output_path: Output file path
    """
    import json
    
    with open(output_path, 'w') as f:
        json.dump(configs, f, indent=2)


def load_configuration_set(config_path: str) -> List[Dict[str, Any]]:
    """
    Load configuration set from JSON file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        List of configurations
    """
    import json
    
    with open(config_path, 'r') as f:
        return json.load(f)


# Configuration set factories for common scenarios
BASIC_CONFIG_SET = create_basic_config_set()
EXTENDED_CONFIG_SET = create_extended_config_set()

# Timeout variation examples  
TIMEOUT_OPTIMIZATION_SET = create_timeout_variation_set(
    BASIC_CONFIG_SET,
    [120, 180, 240, 300, 360, 420, 480]
)