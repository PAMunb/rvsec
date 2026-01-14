"""
Multimodal validation framework for rv-agent.

Provides metrics collection, analysis, and reporting for LLM-driven testing.
"""

from .metrics import (
    LLMActionRecord,
    ExplorationRecord,
    SessionMetrics,
    HitClassification,
    ElementBounds,
)
from .hit_classifier import UIElement
from .hit_classifier import HitClassifier, ClassificationResult, parse_ui_elements_from_dump
from .collector import MultimodalMetricsCollector
from .analyzer import MultimodalAnalyzer, AggregatedMetrics

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
