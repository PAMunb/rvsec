"""
Constants for the rv-screen-parser module.

### Architectural Overview:
This module defines constant values used throughout the screen parser system to ensure
consistency and prevent errors due to string mismatches. These constants are designed
to support monitored operations in both JCA cryptography and generic programming patterns.

### Key Architectural Decisions:
- **Type Safety**: Centralized constants prevent string mismatches across components
- **Factory Integration**: Constants designed to work seamlessly with parser factories
- **Monitored Operations**: Support for both JCA crypto and generic specifications
- **Clean Separation**: Parser and visitor constants properly separated by responsibility

### Role in the System:
- Provides type-safe constants for screen parser and visitor components
- Enables consistent configuration across different modules
- Maintains compatibility with the modern factory pattern architecture
- Defines clear contracts for parser and visitor types
"""


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
