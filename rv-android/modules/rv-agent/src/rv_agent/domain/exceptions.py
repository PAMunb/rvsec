"""
RVAgent exception hierarchy.

Three categories covering all failure modes:
- DeviceError: Device communication failures
- LLMError: LLM service failures
- ValidationError: Invalid data/state
"""


class RVAgentError(Exception):
    """Base exception for rv-agent."""

    pass


class DeviceError(RVAgentError):
    """Device communication or action execution failed."""

    pass


class LLMError(RVAgentError):
    """LLM service unavailable or returned invalid response."""

    pass


class ValidationError(RVAgentError):
    """Invalid action, state, or configuration."""

    pass
