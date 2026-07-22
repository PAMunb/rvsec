"""
Node-level exploration policies (INV-AGT-51).

Three off-by-default policies applied by the LangGraph learn node, ported from
APE-RV branch ``mop-fairtest``:

- **idle-timeout cap** (``idle_timeout_cap`` seconds): bounded wait on an idle
  (unchanged) screen. Once the screen has stayed unchanged for longer than the
  cap, the agent escapes (forces a BACK). Port of APE-RV's bounded
  wait-for-package (``Config.maxIdleTimeoutMs``), which relaunches after ~10 s.
- **dynamic epsilon** (``dynamic_epsilon``): exploration randomness adapts to the
  CURRENT state's coverage gap rather than staying fixed —
  ``min_epsilon + (max_epsilon - min_epsilon) * coverage_gap`` (port of
  ``SataAgent.computeDynamicEpsilon``; bounds are APE-RV's Config defaults). A
  fresh, unexplored state gets maximum randomness; a fully-covered state gets the
  minimum. It drives the strategy's ``stochastic_probability``.
- **per-activity action budget** (``activity_budget_enabled``): an activity that
  consumed its per-run action budget (``base + per_widget * widgets``) is
  deprioritized (the agent leaves it via a BACK). The budget is frozen on the
  activity's first visit and, matching APE-RV, is never recalculated or reset.

Each policy is gated by its own config flag; with all three off this object is
inert and the learn node behaves byte-identically to the base policy. Every
escape / deprioritization increments a per-guard telemetry counter (INV-AGT-51).
"""

import logging
from typing import TYPE_CHECKING, Dict, Optional

from rv_agent import tracking as track

if TYPE_CHECKING:
    from rv_agent.config.agent_config import RVAgentConfig

logger = logging.getLogger(__name__)


class NodeExplorationPolicy:
    """Hold per-run state for the three node-level guards/caps (INV-AGT-51)."""

    # Ported APE-RV Config defaults. Kept as constants (not config fields) —
    # they are the fixed bounds/coefficients of the ported formulas, not tuning
    # knobs the arms vary; the arm-defining switch is each policy's own flag.
    MIN_EPSILON = 0.02
    MAX_EPSILON = 0.15
    ACTIVITY_BASE_BUDGET = 50
    ACTIVITY_BUDGET_PER_WIDGET = 5

    def __init__(self, config: "RVAgentConfig"):
        self.config = config
        # Wall-clock time the current unchanged screen went idle (None = no
        # active idle interval). Only consulted when idle_timeout_cap > 0.
        self._idle_since: Optional[float] = None
        # Per-activity forward-move counts and frozen budgets (monotonic per run,
        # never reset — matches APE-RV ActivityBudgetTracker).
        self._activity_counts: Dict[str, int] = {}
        self._activity_budgets: Dict[str, int] = {}

    def effective_epsilon(self, base_epsilon: float, coverage_gap: float) -> float:
        """Return the exploration epsilon for the current coverage gap.

        With ``dynamic_epsilon`` off, returns ``base_epsilon`` unchanged. With it
        on, returns ``min + (max - min) * clamp(coverage_gap)`` — higher gap
        (more untested widgets) means more randomization.
        """
        if not self.config.dynamic_epsilon:
            return base_epsilon
        gap = 0.0 if coverage_gap < 0.0 else (1.0 if coverage_gap > 1.0 else coverage_gap)
        return self.MIN_EPSILON + (self.MAX_EPSILON - self.MIN_EPSILON) * gap

    def check_idle(self, now: float, screen_changed: bool, iteration: int) -> bool:
        """Report whether the idle-timeout cap fired (agent should escape).

        Tracks how long the screen has stayed unchanged. Returns True exactly
        once each time the idle interval exceeds ``idle_timeout_cap`` seconds,
        restarting the clock and counting the escape. Disabled (cap <= 0) or a
        screen change resets the interval and returns False.
        """
        cap = self.config.idle_timeout_cap
        if cap <= 0:
            self._idle_since = None
            return False
        if screen_changed or self._idle_since is None:
            self._idle_since = now
            return False
        if now - self._idle_since >= cap:
            self._idle_since = now  # restart the clock after firing
            track.idle_timeout_wait(iter=iteration, cap=cap)
            return True
        return False

    def register_activity(self, activity: Optional[str], widget_count: int) -> None:
        """Freeze an activity's action budget on its first visit (idempotent)."""
        if activity and activity not in self._activity_budgets:
            self._activity_budgets[activity] = (
                self.ACTIVITY_BASE_BUDGET
                + self.ACTIVITY_BUDGET_PER_WIDGET * max(0, widget_count)
            )

    def record_and_check_budget(self, activity: Optional[str], iteration: int) -> bool:
        """Record one action on ``activity`` and report budget exhaustion.

        With ``activity_budget_enabled`` off, returns False without recording.
        With it on, increments the activity's monotonic action count and returns
        True (counting the deprioritization) once the count reaches the frozen
        per-activity budget.
        """
        if not self.config.activity_budget_enabled or not activity:
            return False
        self._activity_counts[activity] = self._activity_counts.get(activity, 0) + 1
        budget = self._activity_budgets.get(activity, self.ACTIVITY_BASE_BUDGET)
        if self._activity_counts[activity] >= budget:
            track.activity_budget_deprioritized(
                iter=iteration, activity=activity, budget=budget
            )
            return True
        return False
