"""RV-Agent Validation - Validation framework for RV-Agent experiments."""

__version__ = "0.1.0"

from rv_agent_validation.experiment import (
    ExperimentConfig,
    ExperimentRunner,
    CheckpointManager,
    SeedManager,
)
from rv_agent_validation.multimodal import (
    MultimodalMetricsCollector,
    MultimodalAnalyzer,
    SessionMetrics,
    HitClassifier,
)
from rv_agent_validation.preprocessing import (
    InstrumentationWrapper,
    InstrumentationResult,
)

__all__ = [
    # Experiment
    "ExperimentConfig",
    "ExperimentRunner",
    "CheckpointManager",
    "SeedManager",
    # Multimodal
    "MultimodalMetricsCollector",
    "MultimodalAnalyzer",
    "SessionMetrics",
    "HitClassifier",
    # Preprocessing
    "InstrumentationWrapper",
    "InstrumentationResult",
]
