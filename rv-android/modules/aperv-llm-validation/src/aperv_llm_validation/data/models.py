"""Core data models for the APE-RV LLM validation pipeline."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum


@dataclass(frozen=True)
class Widget:
    """Represents a clickable UI element parsed from UIAutomator XML."""

    class_name: str
    text: str
    content_desc: str
    resource_id: str
    bounds: tuple[int, int, int, int]  # left, top, right, bottom
    clickable: bool
    long_clickable: bool
    editable: bool
    checkable: bool
    enabled: bool

    @property
    def center(self) -> tuple[int, int]:
        left, top, right, bottom = self.bounds
        return ((left + right) // 2, (top + bottom) // 2)

    @property
    def area(self) -> int:
        left, top, right, bottom = self.bounds
        return (right - left) * (bottom - top)

    @property
    def width(self) -> int:
        return self.bounds[2] - self.bounds[0]

    @property
    def height(self) -> int:
        return self.bounds[3] - self.bounds[1]

    @property
    def has_semantic_info(self) -> bool:
        """Widget has text, content_desc, or resource_id (not a generic container)."""
        return bool(self.text or self.content_desc or self.resource_id)


class MatchStep(str, Enum):
    """Which step of the 5-step algorithm produced the result."""

    BACK = "back"
    BOUNDS_MATCH = "bounds_match"
    LONG_CLICK_RETRY = "long_click_retry"
    EUCLIDEAN_MATCH = "euclidean_match"
    NO_MATCH = "no_match"


class NoMatchCategory(str, Enum):
    """Root cause classification for no_match results."""

    BOUNDARY_REJECTION = "boundary_rejection"
    EDGE_MISS = "edge_miss"
    TOLERANCE_MISS = "tolerance_miss"
    GAP = "gap"
    TYPE_MISMATCH = "type_mismatch"
    FEW_WIDGETS = "few_widgets"
    STALE_MODEL = "stale_model"  # assigned post-hoc during reasoning analysis


@dataclass(frozen=True)
class ParsedAction:
    """Result of parsing an LLM response into an action."""

    action_type: str  # click, long_click, type_text, back, select_action
    x: int = 0  # Qwen normalized [0, 1000) — 0 for non-coordinate actions
    y: int = 0
    text: str | None = None  # for type_text
    reasoning: str | None = None
    parse_level: str = "native"  # native, xml_tag, inline_json
    element_id: int | None = None  # for SoM/action_list variants


@dataclass(frozen=True)
class MatchResult:
    """Full result of matching an LLM action against widgets."""

    matched: bool
    step: MatchStep
    widget: Widget | None
    action_type: str
    pixel_x: int
    pixel_y: int
    qwen_x: int
    qwen_y: int
    distance_to_nearest: float  # pixels, center-to-point
    nearest_widget: Widget | None
    classification: NoMatchCategory | None = None  # filled by evaluator via classifier


@dataclass(frozen=True)
class EvaluationResult:
    """One row of evaluation output — one LLM call."""

    screenshot_id: str
    app_name: str
    prompt_variant: str
    repetition: int
    # LLM interaction
    tool_call_success: bool
    parse_level: str
    tokens_in: int
    tokens_out: int
    latency_ms: int
    # Matching
    match_result: MatchResult
    reasoning: str | None = None
    # Quality guardrails (computed from match_result)
    widget_class: str | None = None  # class of matched widget
    is_container: bool = False  # matched widget is generic container
    has_text: bool = False  # matched widget has text/content_desc


@dataclass
class PromptConfig:
    """Configuration for a prompt variant."""

    name: str
    description: str
    build_system_message: Callable[..., str]
    build_widget_list: Callable[..., str]
    build_tool_schema: Callable[..., list[dict]]
    # Metadata
    uses_coordinates: bool = True  # False for SoM/action_list
    uses_element_id: bool = False  # True for SoM/action_list


@dataclass
class EvaluatorConfig:
    """Configuration for the evaluation engine."""

    sglang_url: str = ""
    model: str = ""
    temperature: float = 0.3
    resize_mode: str = "max_edge"  # max_edge | smart_resize | raw
    screenshots_dir: str = ""
    cache_dir: str = ".cache"
    output_dir: str = "results"
    seed: int = 42
    use_cache: bool = True
    max_screenshots: int | None = None
