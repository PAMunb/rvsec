"""UI Elements information fragment for the prompt system.

This module defines a specialized fragment for extracting and formatting UI element
information from the application state.
"""

from typing import Any, Dict, Optional, List

from rvandroid.llm.constants import FragmentType, StateEntry
from rvandroid.llm.prompt.information.base_fragment import InformationFragment


class Teste001Fragment(InformationFragment):

    def __init__(self, name: str = "teste_001", priority: int = 500):
        super().__init__(name, priority)

    def generate(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> str:
        if not state:
            return "No state information available."
        return "TEXTO DE TESTE 001"

    def should_include(self, state: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> bool:
        return True