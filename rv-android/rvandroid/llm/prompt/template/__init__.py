"""Template layer for the prompt system.

This package provides the template layer components of the prompt system,
which are responsible for structuring messages and managing templates.
"""

from .prompt_template import PromptTemplate
from .template_repository import TemplateRepository

__all__ = [
    "PromptTemplate",
    "TemplateRepository",
]