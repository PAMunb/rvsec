"""
Constants for the LLM Prompt System

### Architectural Overview:
This module defines constant values used throughout the prompt system to ensure
consistency and prevent errors due to string mismatches. These constants are designed
to support the factory-based architecture and monitored operations framework.

### Key Components:
- **Type Safety**: Centralized constants prevent string mismatches across components
- **Factory Integration**: Constants designed to work seamlessly with component factories
- **Monitored Operations**: Support for JCA crypto and generic programming specifications
- **Template System**: Constants for template roles and fragment types
- **Extensibility**: Support for new LLM providers and strategy types

### Role in the System:
- Provides type-safe constants for all LLM and prompt strategy components
- Enables consistent configuration across different modules
- Supports JCA cryptography and generic programming pattern monitoring
- Maintains compatibility with factory pattern architecture
- Defines clear contracts for template and fragment systems
"""


class LLMType:
    """
    Constants for LLM provider types supported by the factory system.
    
    ### Supported Providers:
    - **OLLAMA**: Local inference using Ollama platform
    - **HUGGINGFACE**: HuggingFace Transformers models  
    - **FRONTIER**: Commercial API providers (OpenAI, Anthropic, etc.)
    """
    OLLAMA = "ollama"
    HUGGINGFACE = "huggingface"
    FRONTIER = "frontier"
    ALL = [OLLAMA, HUGGINGFACE, FRONTIER]


class PromptStrategyType:
    """
    Constants for prompt strategy types supported by the factory system.
    
    ### Strategy Types:
    - **SINGLE**: Single-action generation
    - **BATCH**: Multi-action generation  
    - **VISION**: Multi-modal generation with visual support
    - **MOP_VISION**: Multi-modal generation with monitored operations focus
    - **DEFAULT**: Default strategy for new configurations
    """
    SINGLE = "single"
    BATCH = "batch" 
    VISION = "vision"
    MOP_VISION = "mop_vision"
    DEFAULT = BATCH
    ALL = [SINGLE, BATCH, VISION, MOP_VISION]


class FragmentType:
    """
    Constants for information fragment types in the prompt system.
    
    ### Fragment Types:
    - **UI_ELEMENTS**: UI element descriptions and interactions
    - **SCREENSHOT**: Screenshot analysis and descriptions
    - **MONITORED_OPERATIONS**: Operations being monitored by specifications
    - **UI_PATTERNS**: Detected UI patterns and navigation hints
    - **HISTORY**: Action history and context information
    - **TRANSITION_GUIDANCE**: Guidance for state transitions and navigation
    """
    UI_ELEMENTS = "ui_elements"
    SCREENSHOT = "screenshot"
    MONITORED_OPERATIONS = "monitored_operations"
    UI_PATTERNS = "ui_patterns"
    HISTORY = "history"
    TRANSITION_GUIDANCE = "transition_guidance"


class TemplateRole:
    """
    Constants for template roles in the LLM conversation system.
    
    ### Template Roles:
    - **SYSTEM**: System-level instructions and context
    - **USER**: User prompts and queries
    - **ASSISTANT**: AI assistant responses and actions
    """
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class StateEntry:
    # TODO rever os campos ... tem muitos que nao sao usados ou duplicados ... talvez seja melhor criar uma classe e deixar formal (tipado)
    """
    Constants for state dictionary entries in the Android testing framework.
    
    ### State Information:
    - **Application Context**: Package name, activity, and navigation information
    - **Screen Analysis**: UI structure, patterns, and available actions  
    - **Monitored Operations**: Operations being tracked by specifications
    - **Testing Context**: Action history, memory insights, and navigation paths
    """
    PACKAGE_NAME = "package_name"
    ACTIVITY = "activity"
    VIEW_TREE = "view_tree"
    HASH_SCREEN_CONTENT = "state_str"
    HASH_SCREEN = "structure_str"
    STATIC_DATA = "static_data"
    STRUCTURED_SCREEN = "structured_screen"
    AVAILABLE_ACTIONS = "available_actions"
    SCREENSHOT_PATH = "screenshot_path"
    SCREENSHOT_INFO = "screenshot_info"
    DETECTED_PATTERN = "detected_pattern"
    TRANSITION_GUIDANCE = "transition_guidance"
    MONITORED_OPERATIONS = "monitored_operations"
    FINGERPRINT = "fingerprint"
    PREVIOUS_ACTIVITY = "previous_activity"
    SCREEN_PATTERNS = "screen"
    SCREEN_DESCRIPTION = "screen_description"
    ACTION_HISTORY = "action_history"
    MEMORY_INSIGHTS = "memory_insights"
    NAVIGATION_PATH = "navigation_path"
    ACTIVITY_VISITS = "activity_visits"
    RECENT_ITERATIONS = "recent_iterations"
    TOOL_CONFIG = "tool_config"
    
    # Coverage metrics integration for real-time testing guidance
    COVERAGE_METRICS = "coverage_metrics"
    METHOD_COVERAGE = "method_coverage"           # Percentage of methods called
    ACTIVITY_COVERAGE = "activity_coverage"       # Percentage of activities visited  
    CLASS_COVERAGE = "class_coverage"             # Percentage of classes instantiated
    MOP_COVERAGE_CURRENT = "mop_coverage_current" # Number of MOP methods reached
    MOP_COVERAGE_TOTAL = "mop_coverage_total"     # Total MOP methods available
    MOP_ERRORS_COUNT = "mop_errors_count"         # Number of unique MOP violations
    MOP_RECENT_ERRORS = "mop_recent_errors"       # Recent MOP error details for context


class ContextMode:
    """
    Constants for context enrichment modes in prompt generation.
    
    ### Context Modes:
    - **STATELESS**: Complete context inline with each prompt (default)
    - **RICH**: Extended context with sliding window and compression
    - **DEFAULT**: Default mode for new configurations
    
    ### Context Configuration:
    - **WINDOW_SIZE_DEFAULT**: Default sliding window size for rich context mode
    - **WINDOW_SIZE_MIN**: Minimum allowed window size
    - **WINDOW_SIZE_MAX**: Maximum allowed window size for performance
    - **COMPRESSION_DEFAULT**: Default compression setting for older iterations
    """
    STATELESS = "stateless"
    RICH = "rich"
    DEFAULT = STATELESS
    
    # Context window configuration
    WINDOW_SIZE_DEFAULT = 10
    WINDOW_SIZE_MIN = 1
    WINDOW_SIZE_MAX = 20
    COMPRESSION_DEFAULT = True


# class ComponentType:
#     """
#     Constants for component types in the modern factory system.
#
#     ### Component Types:
#     - **LLM**: Language model components created by LLMFactory
#     - **PROMPT_STRATEGY**: Prompt strategy components created by PromptStrategyFactory
#     - **PARSER**: Screen parser components from rv-screen-parser
#     - **VISITOR**: Visitor pattern components for screen analysis
#     """
#     LLM = "llm"
#     PROMPT_STRATEGY = "strategy"
#     PARSER = "parser"
#     VISITOR = "visitor"


class ContextEntry:
    # TODO verificar como esta sendo usado ... diferencas com StateEntry ... quando usar um ou outro?
    """
    Constants for context dictionary entries in the modern prompt system.
    
    ### Context Information:
    - **Template System**: Template management and rendering context
    - **Application Context**: Package name, activity, and testing parameters
    - **Component Configuration**: LLM, strategy, parser, and visitor configurations
    """
    TEMPLATE = "template"
    APP_PACKAGE = "app_package"
    APP_ACTIVITY = "app_activity"
    ACTION_LIMIT = "action_limit"
    MODEL_TYPE = "model_type"
    MODEL_NAME = "model_name"
    STRATEGY = "strategy"
    PARSER = "parser"
    VISITOR = "visitor"
    TESTING_HISTORY = "testing_history"
    ADDITIONAL_GUIDELINES = "additional_guidelines"
    
    # Context mode configuration
    CONTEXT_MODE = "context_mode"
    CONTEXT_WINDOW_SIZE = "context_window_size"
    CONTEXT_COMPRESSION = "context_compression"
    INCLUDE_COVERAGE_TIMELINE = "include_coverage_timeline"
