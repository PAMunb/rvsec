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
from typing import List, Tuple

from rv_llm import LLMConfig
from rv_llm.llm.constants import LLMType

# ===== EXECUTION SETTINGS =====

# Number of repetitions per configuration for statistical significance
REPETITIONS_PER_CONFIG = 5

# Number of warm-up runs to discard (not counted in results)
WARMUP_RUNS = 3

# Timeout for each LLM generation call (seconds)
GENERATION_TIMEOUT = 60

# Default prompts directory (can be overridden)
DEFAULT_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")


# ===== MODEL CONFIGURATION =====

class ModelToTest:
    def __init__(self, name: str, vision=False, think=False):
        self.name = name
        self.vision = vision
        self.think = think


# Models to evaluate (considering 16GB GPU constraint)
# Prioritizing smaller, efficient models that fit in VRAM
MODELS_TO_TEST = [
    # ModelToTest("", False, False),
    # ModelToTest("llama3.2:1b"),
    # ModelToTest("llama3.2:3b"),
    ModelToTest("llama3.2-vision:11b", vision=True),
    ModelToTest("gemma3:4b", vision=True),
    ModelToTest("gemma3:12b", vision=True),
    ModelToTest("llava:7b", vision=True),
    ModelToTest("llava-llama3:8b", vision=True),
    ModelToTest("llava-phi3:3.8b", vision=True),
    # ModelToTest("granite3.2-vision:2b", vision=True),
    # ModelToTest("qwen3:0.6b", think=True),
    # ModelToTest("qwen3:1.7b", think=True),
    # ModelToTest("qwen3:4b", think=True),
    # ModelToTest("qwen3:8b", think=True),
    # ModelToTest("qwen3:14b", think=True),
    # ModelToTest("phi4-mini-reasoning:3.8b"),
    # ModelToTest("phi4-reasoning:14b"),
    # ModelToTest("deepseek-r1:1.5b", think=True),
    # ModelToTest("deepseek-r1:7b", think=True),
    # ModelToTest("deepseek-r1:8b", think=True),
    # ModelToTest("moondream:1.8b", vision=True)
]

# ===== PARAMETER RANGES =====

# Temperature values for testing randomness vs consistency
TEMPERATURE_VALUES = [0.1, 0.5, 0.9]

# Top-p (nucleus sampling) values for token selection
# O top_p (também conhecido como amostragem de núcleo) controla a diversidade do texto gerado de uma maneira diferente da temperatura.
#
# O que faz: Em vez de selecionar apenas a palavra mais provável, o modelo considera um conjunto de palavras cuja probabilidade acumulada atinja o valor de top_p.
#
# Valores baixos (como 0.1) restringem a seleção a um pequeno grupo de palavras mais prováveis.
#
# Valores altos (como 0.9) permitem que o modelo escolha entre um grupo maior de palavras, resultando em mais diversidade.
#
# Faixa de valores: De 0.0 a 1.0.
#
# Valor padrão: Geralmente 0.9. É uma boa opção para balancear diversidade e relevância.
TOP_P_VALUES = [0.3, 0.9] #[0.1, 0.5, 0.9]

# Maximum tokens to generate
# O max_tokens define o limite máximo de tokens (palavras, pontuações, etc.) que o modelo pode gerar na resposta.
#
# O que faz: Ele basicamente controla o tamanho máximo da sua resposta. Se a resposta atinge esse limite, o modelo para de gerar texto, mesmo que a frase não esteja completa.
#
# É útil para evitar que o modelo gere respostas extremamente longas e para controlar os custos (se aplicável) e o tempo de resposta.
#
# Faixa de valores: De 1 a qualquer número inteiro positivo. O limite exato pode depender do modelo em uso e da sua máquina.
#
# Valor padrão: Varia, mas um valor comum pode ser 128.
MAX_TOKENS_VALUES = [300, 500] #[300, 500, 800, 1500]

# Top-k values for token selection (0 means disabled)
# O top_k limita o conjunto de palavras que o modelo pode escolher para a próxima palavra.
#
# O que faz: O modelo só considera as k palavras mais prováveis para continuar a frase.
#
# Se top_k é 1, o modelo sempre escolhe a palavra mais provável (igual a uma temperatura de 0).
#
# Se top_k é 40, ele considera as 40 palavras mais prováveis.
#
# Faixa de valores: De 1 a qualquer número inteiro positivo (mas valores acima de algumas centenas geralmente não são úteis).
#
# Valor padrão: Geralmente 40.
TOP_K_VALUES = [10, 40]

# ===== OUTPUT CONFIGURATION =====

# Output file names (simple naming convention)
DETAILED_RESULTS_FILE = "detailed_results.csv"
SUMMARY_RESULTS_FILE = "summary_results.csv"
ANALYSIS_REPORT_FILE = "analysis_report.md"


# ===== PROMPT CONFIGURATION =====

def get_prompt_pairs(prompts_dir: str = None) -> List[Tuple[str, str, str, str]]:
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
        image_file = f"{prompt_id}_image.txt"

        # Check if corresponding user file exists
        if user_file in files:
            system_path = os.path.join(prompts_dir, system_file)
            user_path = os.path.join(prompts_dir, user_file)
            image_path = os.path.join(prompts_dir, image_file)
            prompt_pairs.append((prompt_id, system_path, user_path, image_path))

    # Sort by prompt ID for consistent ordering
    prompt_pairs.sort(key=lambda x: x[0])

    return prompt_pairs


# ===== OLLAMA CONFIGURATION =====

# Base URL for Ollama API
OLLAMA_BASE_URL = "http://localhost:11434"

# Default Ollama model parameters
DEFAULT_OLLAMA_KWARGS = {
    "base_url": OLLAMA_BASE_URL
}


# ===== EVALUATION CONFIGURATION =====

def generate_all_configurations() -> List[LLMConfig]:
    """
    Generate all possible configuration combinations for testing.

    Returns:
        List of configuration dictionaries for systematic evaluation
    """
    configurations = []

    for model in MODELS_TO_TEST:
        for temperature in TEMPERATURE_VALUES:
            for top_p in TOP_P_VALUES:
                for max_tokens in MAX_TOKENS_VALUES:
                    for top_k in TOP_K_VALUES:
                        config = LLMConfig(
                            llm_type=LLMType.OLLAMA,
                            model=model.name,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            top_p=top_p,
                            top_k=top_k,
                            vision=model.vision,
                            think=model.think
                        )
                        configurations.append(config)

    return configurations
