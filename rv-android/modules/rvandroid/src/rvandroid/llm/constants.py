"""Constants for the LLM prompt system.

This module defines constant values used throughout the prompt system to ensure
consistency and prevent errors due to string mismatches.
"""
from rv_android_core.parser.screen.visitor.visitor_factory import VisitorFactory


class LLMType:
    """Constants for LLM types used in the system."""
    OLLAMA = "ollama"
    HUGGINGFACE = "huggingface"
    FRONTIER = "frontier"


# TODO deprecated
# class OllamaModels:
#     """Constants for Ollama model types."""
#     LLAMA3_8B = "llama3:8b"
#     LLAMA3_70B = "llama3:70b"
#     MISTRAL = "mistral:7b"
#     GEMMA = "gemma:7b"
#
#     ALL = [LLAMA3_8B, LLAMA3_70B, MISTRAL, GEMMA]

class PromptStrategyType:
    """Constants for prompt strategy types."""
    STANDARD = "standard_modular"
    BATCH_ACTION = "batch_action_modular"
    DEFAULT = BATCH_ACTION
    ALL = [STANDARD, BATCH_ACTION]


class ScreenParserType:
    """Constants for screen parser types."""
    DROIDBOT = "droidbot"
    UIAUTOMATOR = "uiautomator"


class VisitorType:
    """Constants for visitor types."""
    BASIC = VisitorFactory.BASIC
    DEFAULT = VisitorFactory.DEFAULT
    DETAILED = VisitorFactory.DETAILED


class FragmentType:
    """Constants for information fragment types."""
    UI_ELEMENTS = "ui_elements"
    SCREENSHOT = "screenshot"
    MONITORED_OPERATIONS = "monitored_operations"
    UI_PATTERNS = "ui_patterns"
    HISTORY = "history"


class TemplateRole:
    """Constants for template roles."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class StateEntry:
    """Constants for state dictionary entries."""
    PACKAGE_NAME = "package_name"
    ACTIVITY = "activity"
    VIEW_TREE = "view_tree"
    HASH_SCREEN_CONTENT = "state_str"
    HASH_SCREEN = "structure_str"
    STATIC_DATA = "static_data"
    STRUCTURED_SCREEN = "structured_screen"  # The actual ScreenDescription object
    AVAILABLE_ACTIONS = "available_actions"
    SCREENSHOT_PATH = "screenshot_path"
    SCREENSHOT_INFO = "screenshot_info"
    UI_PATTERNS = "ui_patterns"  # deprecated Dict[PatternType, PatternResult]
    DETECTED_PATTERN = "detected_pattern"  # dict
    TRANSITION_GUIDANCE = "transition_guidance"
    MONITORED_OPERATIONS = "monitored_operations"  # List[str]: list of methods signature (tha reaches_mop or directly_reaches_mop)
    FINGERPRINT = "fingerprint"
    PREVIOUS_ACTIVITY = "previous_activity"
    SCREEN_PATTERNS = "screen"
    SCREEN_DESCRIPTION = "screen_description"  # the ScreenDescription string representation for template rendering
    ACTION_HISTORY = "action_history"  # List of actions taken in the current activity
    MEMORY_INSIGHTS = "memory_insights"
    NAVIGATION_PATH = "navigation_path"
    ACTIVITY_VISITS = "activity_visits"
    RECENT_ITERATIONS = "recent_iterations"


class ComponentType:
    """Constants for component types in ComponentConfigurator."""
    LLM = "llm"
    PROMPT_STRATEGY = "strategy"
    PARSER = "parser"
    VISITOR = "visitor"


class ContextEntry:
    """Constants for context dictionary entries."""
    TEMPLATE = "template"
    ADDITIONAL_GUIDELINES = "additional_guidelines"  # TODO: remove
    APP_PACKAGE = "app_package"
    APP_ACTIVITY = "app_activity"
    TESTING_HISTORY = "testing_history"  # TODO: remove
    ACTION_LIMIT = "action_limit"
    MODEL_TYPE = "model_type"
    MODEL_NAME = "model_name"
    STRATEGY = "strategy"
    PARSER = "parser"
    VISITOR = "visitor"
