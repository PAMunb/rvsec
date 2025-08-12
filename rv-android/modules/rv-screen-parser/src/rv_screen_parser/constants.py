"""
Constants for screen parsing and action classification.
"""

from enum import Enum


class ScreenParserType:
    """
    Constants for screen parser types supported by the parser factory system.
    
    ### Supported Parser Types:
    - **DROIDBOT**: DroidBot-compatible screen parsing for monitored operations
    - **UIAUTOMATOR**: UIAutomator2-based screen parsing for monitored operations
    
    ### Usage:
    These constants should be used instead of string literals when configuring
    parsers to ensure type safety and prevent configuration errors.
    """
    DROIDBOT = "droidbot"
    UIAUTOMATOR = "uiautomator"
    ALL = [DROIDBOT, UIAUTOMATOR]


class VisitorType:
    """
    Constants for visitor types supported by the visitor factory system.
    
    ### Supported Visitor Types:
    - **BASIC**: Basic text extraction visitor for monitored operations
    - **DEFAULT**: Default visitor with standard features for monitored operations
    - **DETAILED**: Enhanced visitor with comprehensive analysis for monitored operations
    
    ### Usage:
    These constants should be used instead of string literals when configuring
    visitors to ensure type safety and prevent configuration errors.
    """
    BASIC = "basic"
    DEFAULT = "default"
    DETAILED = "detailed"
    ALL = [BASIC, DEFAULT, DETAILED]

class ActionType(Enum):
    """
    Classification of action types for coordinate conflict resolution.
    
    ### Architectural Purpose:
    - Distinguishes between UI actions requiring coordinates and system actions
    - Enables proper handling of [0,0] coordinates for system operations
    - Supports action validation and processing pipeline decisions
    
    ### Usage Context:
    - UI_ACTION: Standard widget interactions requiring screen coordinates
    - SYSTEM_ACTION: Platform-level operations not tied to specific UI elements
    """
    UI_ACTION = "ui_action"
    SYSTEM_ACTION = "system_action"

class SystemActionType(Enum):
    """
    Specific system action operations supported by the platform.
    
    ### Supported Operations:
    - BACK: Android system back navigation
    - RESTART: Application restart operation
    - HOME: Return to launcher (future extension)
    """
    BACK = "SYSTEM_BACK"
    RESTART = "RESTART_APP"
    HOME = "SYSTEM_HOME"  # Reserved for future use