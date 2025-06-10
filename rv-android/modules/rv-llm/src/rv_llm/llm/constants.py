"""
Constants for the LLM Prompt System - Phase 8 Modern Architecture

### Architectural Overview:
This module defines constant values used throughout the modern prompt system to ensure
consistency and prevent errors due to string mismatches. These constants are designed
to support the factory-based architecture and monitored operations framework.

### Key Architectural Decisions:
- **Type Safety**: Centralized constants prevent string mismatches across components
- **Factory Integration**: Constants designed to work seamlessly with modern factories
- **Monitored Operations**: Comprehensive support for both JCA crypto and generic specifications
- **Template Coordination**: Constants support the modular template system
- **Future Extensibility**: Designed to support new LLM providers and strategy types

### Role in the System:
- Provides type-safe constants for all LLM and prompt strategy components
- Enables consistent configuration across different modules
- Supports both JCA cryptography and generic programming pattern monitoring
- Maintains compatibility with the modern factory pattern architecture
- Defines clear contracts for template and fragment systems
"""
from rv_screen_parser.parser.screen.visitor.visitor_factory import VisitorFactory


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


class PromptStrategyType:
    """
    Constants for prompt strategy types supported by the factory system.
    
    ### Strategy Types:
    - **STANDARD**: Single-action generation with context awareness
    - **BATCH_ACTION**: Multi-action generation with coordination
    - **DEFAULT**: Default strategy for new configurations
    """
    STANDARD = "standard_modular"
    BATCH_ACTION = "batch_action_modular"
    DEFAULT = BATCH_ACTION
    ALL = [STANDARD, BATCH_ACTION]


class ScreenParserType:
    """
    Constants for screen parser types integrated with rv-screen-parser module.
    
    ### Parser Types:
    - **DROIDBOT**: DroidBot-compatible screen parsing
    - **UIAUTOMATOR**: UIAutomator2-based screen parsing
    """
    DROIDBOT = "droidbot"
    UIAUTOMATOR = "uiautomator"


class VisitorType:
    """
    Constants for visitor types from rv-screen-parser visitor factory.
    
    ### Visitor Types:
    - **BASIC**: Basic text extraction visitor
    - **DEFAULT**: Default visitor with standard features
    - **DETAILED**: Enhanced visitor with comprehensive analysis
    """
    BASIC = VisitorFactory.BASIC
    DEFAULT = VisitorFactory.DEFAULT
    DETAILED = VisitorFactory.DETAILED


class FragmentType:
    """
    Constants for information fragment types in the modular prompt system.
    
    ### Fragment Types:
    - **UI_ELEMENTS**: UI element descriptions and interactions
    - **SCREENSHOT**: Screenshot analysis and descriptions
    - **MONITORED_OPERATIONS**: Operations being monitored by specifications
    - **UI_PATTERNS**: Detected UI patterns and navigation hints
    - **HISTORY**: Action history and context information
    """
    UI_ELEMENTS = "ui_elements"
    SCREENSHOT = "screenshot"
    MONITORED_OPERATIONS = "monitored_operations"
    UI_PATTERNS = "ui_patterns"
    HISTORY = "history"


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
    """
    Constants for state dictionary entries in the modern Android testing framework.
    
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


class ComponentType:
    """
    Constants for component types in the modern factory system.
    
    ### Component Types:
    - **LLM**: Language model components created by LLMFactory
    - **PROMPT_STRATEGY**: Prompt strategy components created by PromptStrategyFactory
    - **PARSER**: Screen parser components from rv-screen-parser
    - **VISITOR**: Visitor pattern components for screen analysis
    """
    LLM = "llm"
    PROMPT_STRATEGY = "strategy"
    PARSER = "parser"
    VISITOR = "visitor"


class ContextEntry:
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
