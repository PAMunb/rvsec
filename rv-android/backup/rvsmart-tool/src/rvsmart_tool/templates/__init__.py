"""
Templates module for rvandroid-tool.

This module contains tool-specific templates and fragments for monitored operations testing.
Templates are organized by type and registered with the rv-llm PromptFramework during initialization.

### Template Organization:
- **fragments/**: Reusable template fragments for different contexts
- **templates/**: Complete template files for different strategies

### Integration with rv-llm:
Templates from this module are registered with the PromptFramework from rv-llm
during tool initialization to enable proper template resolution and rendering.
"""

import os
from pathlib import Path

# Template directory paths
TEMPLATE_DIR = Path(__file__).parent
FRAGMENTS_DIR = TEMPLATE_DIR / "fragments"
TEMPLATES_DIR = TEMPLATE_DIR / "templates"

def get_template_paths():
    """
    Get template directory paths for registration with PromptFramework.
    
    Returns:
        Dictionary with template directory paths
    """
    return {
        "fragments": str(FRAGMENTS_DIR),
        "templates": str(TEMPLATES_DIR)
    }

def list_available_templates():
    """
    List all available templates for debugging.
    
    Returns:
        Dictionary with lists of available templates and fragments
    """
    templates = []
    fragments = []
    
    if TEMPLATES_DIR.exists():
        templates = [f.name for f in TEMPLATES_DIR.glob("*.xml")]
    
    if FRAGMENTS_DIR.exists():
        fragments = [f.name for f in FRAGMENTS_DIR.glob("*.xml")]
    
    return {
        "templates": templates,
        "fragments": fragments
    }