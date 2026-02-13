"""Template layer for the prompt system.

This package provides the template layer components of the prompt system,
which are responsible for structuring messages and managing templates.

### Architectural Decision:
- Modern implementation using Jinja2TemplateRepository
- Legacy PromptTemplate and TemplateRepository moved to backup
- Follows the established architectural pattern from rv-android-core
"""

from .jinja_repository import Jinja2TemplateRepository
from .jinja_template import Jinja2Template, FragmentDictLoader

__all__ = [
    "Jinja2TemplateRepository",
    "Jinja2Template", 
    "FragmentDictLoader",
]