"""
Metrics dataclasses for multimodal validation.

Defines structured records for LLM actions and exploration tracking.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Tuple, List
import time


class HitClassification(Enum):
    """Classification of click accuracy relative to target element."""

    HIT = "hit"                    # Click inside target element bounds
    NEAR_MISS = "near_miss"        # Click hit another interactive element
    UI_MISS = "ui_miss"            # Click hit non-interactive UI (text, image)
    EMPTY_MISS = "empty_miss"      # Click hit empty screen area


@dataclass
class ElementBounds:
    """Bounds of a UI element."""

    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def center(self) -> Tuple[int, int]:
        return (
            (self.left + self.right) // 2,
            (self.top + self.bottom) // 2
        )

    def contains(self, x: int, y: int) -> bool:
        """Check if point (x, y) is inside bounds."""
        return (self.left <= x <= self.right and
                self.top <= y <= self.bottom)

    def distance_to(self, x: int, y: int) -> float:
        """Calculate distance from point to nearest edge if outside, 0 if inside."""
        if self.contains(x, y):
            return 0.0

        # Find nearest point on rectangle
        nearest_x = max(self.left, min(x, self.right))
        nearest_y = max(self.top, min(y, self.bottom))

        return ((x - nearest_x) ** 2 + (y - nearest_y) ** 2) ** 0.5


@dataclass
class UIElement:
    """Representation of a UI element for hit classification."""

    bounds: ElementBounds
    element_type: str           # Button, EditText, TextView, ImageView, etc.
    text: str = ""
    resource_id: str = ""
    is_clickable: bool = False
    is_editable: bool = False

    @property
    def is_interactive(self) -> bool:
        """Check if element is interactive (clickable or editable)."""
        return self.is_clickable or self.is_editable


@dataclass
class LLMActionRecord:
    """
    Record of a single LLM-generated action with accuracy metrics.

    Tracks coordinates, classification, performance, and context.
    """

    # Timing
    timestamp: float = field(default_factory=time.time)
    iteration: int = 0

    # Coordinates
    raw_coords: Tuple[int, int] = (0, 0)          # [0, 1000) from LLM
    device_coords: Tuple[int, int] = (0, 0)       # Pixels after conversion

    # Classification
    target_element: Optional[ElementBounds] = None
    hit_classification: HitClassification = HitClassification.EMPTY_MISS
    distance_to_target: float = 0.0               # Distance to intended target
    distance_to_nearest: float = 0.0              # Distance to any element hit
    hit_element_type: str = ""                    # Type of element actually hit

    # Performance
    latency_ms: float = 0.0
    tokens_input: int = 0
    tokens_output: int = 0

    # Parsing
    tool_name: str = ""                           # android_click, android_type_text, etc.
    tool_args: dict = field(default_factory=dict)
    parser_strategy: str = ""                     # native, xml, fallback

    # Context
    activity: str = ""
    screen_hash: str = ""

    @property
    def total_tokens(self) -> int:
        return self.tokens_input + self.tokens_output

    @property
    def is_hit(self) -> bool:
        return self.hit_classification == HitClassification.HIT


@dataclass
class ExplorationRecord:
    """
    Record of exploration progress at each iteration.

    Tracks activity discovery and stuck detection.
    """

    timestamp: float = field(default_factory=time.time)
    iteration: int = 0

    # Activity tracking
    activity: str = ""
    is_new_activity: bool = False
    actions_since_last_new: int = 0               # Efficiency metric
    total_activities_discovered: int = 0

    # Stuck detection
    screen_hash: str = ""
    is_stuck: bool = False
    stuck_iterations: int = 0                     # Consecutive same-state iterations
    stuck_recovered: Optional[bool] = None        # None if not stuck, True/False after

    # Action info
    action_type: str = ""                         # CLICK, SET_TEXT, BACK, etc.
    action_source: str = ""                       # llm, algorithm


@dataclass
class SessionMetrics:
    """
    Aggregated metrics for a complete validation session.
    """

    # Session info
    app_package: str = ""
    agent_mode: str = ""                          # pure_algorithm, llm_only, multimode
    timeout_seconds: int = 0
    seed: int = 0
    start_time: float = field(default_factory=time.time)
    end_time: float = 0.0

    # LLM metrics
    llm_actions: List[LLMActionRecord] = field(default_factory=list)
    total_llm_calls: int = 0
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    total_latency_ms: float = 0.0

    # Hit rate metrics
    total_clicks: int = 0
    hits: int = 0
    near_misses: int = 0
    ui_misses: int = 0
    empty_misses: int = 0

    # Exploration metrics
    exploration_records: List[ExplorationRecord] = field(default_factory=list)
    total_activities: int = 0                     # From static analysis
    activities_discovered: int = 0
    total_iterations: int = 0

    # Stuck metrics
    stuck_events: int = 0
    stuck_recovered: int = 0
    stuck_failed: int = 0

    @property
    def duration_seconds(self) -> float:
        if self.end_time > 0:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    @property
    def hit_rate(self) -> float:
        if self.total_clicks == 0:
            return 0.0
        return self.hits / self.total_clicks

    @property
    def tool_call_rate(self) -> float:
        if self.total_llm_calls == 0:
            return 0.0
        return self.total_clicks / self.total_llm_calls

    @property
    def activity_coverage(self) -> float:
        if self.total_activities == 0:
            return 0.0
        return self.activities_discovered / self.total_activities

    @property
    def avg_latency_ms(self) -> float:
        if self.total_llm_calls == 0:
            return 0.0
        return self.total_latency_ms / self.total_llm_calls

    @property
    def tokens_per_action(self) -> float:
        if self.total_clicks == 0:
            return 0.0
        return (self.total_tokens_input + self.total_tokens_output) / self.total_clicks

    @property
    def actions_per_activity(self) -> float:
        if self.activities_discovered == 0:
            return float('inf')
        return self.total_iterations / self.activities_discovered

    @property
    def stuck_recovery_rate(self) -> float:
        if self.stuck_events == 0:
            return 1.0  # No stuck events = perfect
        return self.stuck_recovered / self.stuck_events
