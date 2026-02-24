"""
Multimodal validation framework for rv-agent.

Provides metrics collection, analysis, and reporting for LLM-driven testing.
"""

from .analyzer import AggregatedMetrics, MultimodalAnalyzer
from .collector import MultimodalMetricsCollector
from .hit_classifier import (
    ClassificationResult,
    HitClassifier,
    UIElement,
    parse_ui_elements_from_dump,
)
from .metrics import (
    ElementBounds,
    ExplorationRecord,
    HitClassification,
    LLMActionRecord,
    SessionMetrics,
)

__all__ = [
    # Metrics
    "LLMActionRecord",
    "ExplorationRecord",
    "SessionMetrics",
    "HitClassification",
    "ElementBounds",
    "UIElement",
    # Hit classification
    "HitClassifier",
    "ClassificationResult",
    "parse_ui_elements_from_dump",
    # Collection
    "MultimodalMetricsCollector",
    # Analysis
    "MultimodalAnalyzer",
    "AggregatedMetrics",
]
