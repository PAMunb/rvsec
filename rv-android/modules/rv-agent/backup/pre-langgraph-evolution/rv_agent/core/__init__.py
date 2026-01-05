"""Core RV-Agent components."""

# Available components (others coming during implementation)
from .coordinate_extractor import extract_clickable_elements_with_coords
from .prompt_formatter import format_ui_elements_for_llm

# Main agent implementation (coming next)
# from .agent import RVAgent
# from .react_engine import ReactEngine
# from .device_adapter import DeviceInterface

__all__ = [
    "extract_clickable_elements_with_coords",
    "format_ui_elements_for_llm",
    # "RVAgent",      # Coming soon
    # "ReactEngine",  # Coming soon
    # "DeviceInterface",  # Coming next
]