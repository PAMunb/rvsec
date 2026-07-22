"""
Per-step decision-source attribution and trace CSV (fair-test E, INV-AGT-52).

Every executed decision carries exactly one ``decision_source`` from a taxonomy
shared with the APE-RV ``.trace`` field, so a rv-agent run and an aperv run can be
compared row-for-row. Two pieces live here:

- ``attribute_decision_source`` — the pure precedence function. Given the action
  the ranker selected and the scorers that ranked it, it reports which steering
  mechanism decided the pick, using the strict precedence
  ``mop > wtg > menu > form > coverage`` and falling back to ``base`` when no
  steering scorer contributed (which is exactly the pure arm: ``pure_mode`` forces
  every steering flag off, so every scorer that could raise a non-``base`` source
  is excluded from the pipeline). ``component_trigger`` and ``llm`` are decided by
  their own dispatch paths, not by scoring, so they are supplied as an override.

- ``StepTraceWriter`` — appends one CSV row per executed step: the step index, the
  wall-clock offset (``clock=`` in the aperv line), activity, state hash, action,
  the attributed ``decision_source``, and the per-mechanism boosts. Writing is
  lazy (the file and header appear on the first row) and each row is flushed, so a
  run interrupted mid-exploration still leaves a readable trace.

Mapping to the ranker's scorers:

- ``mop``      ← ``MopScorer`` (direct/transitive MOP reachability).
- ``wtg``      ← ``WtgScorer`` or ``MopFrontierScorer`` (both are WTG-navigation
                  boosts — the MOP frontier is a MOP-targeted frontier nav boost,
                  attributed with the WTG family as APE-RV folds it into wtgBoost).
- ``form``     ← ``FormCompletionScorer``.
- ``coverage`` ← ``CoverageDensityScorer``.
- ``menu``     ← reserved for row-compatibility with aperv; rv-agent has no menu
                  scorer, so it never fires here.

``StateMopDensityScorer`` is deliberately NOT an attribution source: it is a flat
per-state scalar applied to every candidate, so it does not explain why one action
was preferred over another on the same screen.
"""

import csv
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from rv_agent.strategies.rvagent_strategy.ranking.context import RankingContext
    from rv_agent.strategies.rvagent_strategy.ranking.scorers import Scorer
    from rv_screen_parser.parser.screen.visitor.model import ItemAction

logger = logging.getLogger(__name__)


# The shared taxonomy (value-identical, lowercased, to the aperv `.trace` field).
# Boost-family values are listed in precedence order; the three trailing values are
# whole-decision channels set by their own paths (trigger dispatch, LLM, base).
DECISION_SOURCES = (
    "mop",
    "wtg",
    "menu",
    "form",
    "coverage",
    "component_trigger",
    "llm",
    "base",
)

# Precedence for boost-family attribution: each entry maps a decision_source to the
# scorer class names whose positive contribution to the selected action implies it.
# Checked top to bottom; the first with a positive contribution wins (INV-AGT-52).
_BOOST_PRECEDENCE = (
    ("mop", ("MopScorer",)),
    ("wtg", ("MopFrontierScorer", "WtgScorer")),
    # "menu" has no rv-agent scorer — kept in the taxonomy for aperv row-compat.
    ("form", ("FormCompletionScorer",)),
    ("coverage", ("CoverageDensityScorer",)),
)


def scorer_boosts(
    action: "ItemAction", context: "RankingContext", scorers: List["Scorer"]
) -> Dict[str, float]:
    """Return the per-mechanism boost the selected action received.

    Keys are the boost-family sources (``mop``, ``wtg``, ``menu``, ``form``,
    ``coverage``); values are the summed contribution of the scorers mapped to
    each source. ``menu`` is always 0.0 (no rv-agent menu scorer). Used both for
    attribution and for the trace row's boost columns.
    """
    by_name = {type(scorer).__name__: scorer for scorer in scorers}
    boosts = {"mop": 0.0, "wtg": 0.0, "menu": 0.0, "form": 0.0, "coverage": 0.0}
    for source, names in _BOOST_PRECEDENCE:
        boosts[source] = sum(
            by_name[name].score(action, context) for name in names if name in by_name
        )
    return boosts


def attribute_decision_source(
    action: "ItemAction",
    context: "RankingContext",
    scorers: List["Scorer"],
    override: Optional[str] = None,
) -> str:
    """Attribute exactly one decision_source to an executed decision.

    Args:
        action: The action the ranker selected.
        context: The ranking context it was scored in.
        scorers: The scorers in the assembled pipeline (``ActionRanker.scorers``).
        override: A whole-decision channel that pre-empts boost attribution —
            ``"llm"`` for an LLM-decided action or ``"component_trigger"`` for a
            stagnation-escape dispatch. When given, it is returned as-is.

    Returns:
        A value from ``DECISION_SOURCES``. Boost-family precedence is
        ``mop > wtg > menu > form > coverage``; ``base`` when no steering scorer
        contributed (the pure arm always attributes ``base``).
    """
    if override:
        return override
    boosts = scorer_boosts(action, context, scorers)
    for source, _names in _BOOST_PRECEDENCE:
        if boosts[source] > 0:
            return source
    return "base"


class StepTraceWriter:
    """Append one CSV row per executed step (fair-test E/F telemetry).

    The file and header are created lazily on the first row and each row is
    flushed, so an interrupted run still leaves a readable, row-complete trace.
    """

    HEADER = (
        "step",
        "clock_ms",
        "activity",
        "state",
        "action",
        "decision_source",
        "mop",
        "wtg",
        "menu",
        "form",
        "coverage",
    )

    def __init__(self, path: str):
        """
        Args:
            path: Destination CSV path. Parent directories are created on the
                first row.
        """
        self.path = Path(path)
        self._fh = None
        self._writer = None

    def _ensure_open(self) -> None:
        if self._writer is None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._fh = open(self.path, "w", newline="", encoding="utf-8")
            self._writer = csv.writer(self._fh)
            self._writer.writerow(self.HEADER)

    def write_row(
        self,
        step: int,
        clock_ms: int,
        activity: str,
        state: str,
        action: str,
        decision_source: str,
        boosts: Optional[Dict[str, float]] = None,
    ) -> None:
        """Write one step's attribution row and flush it.

        Args:
            step: Zero-based step/iteration index.
            clock_ms: Wall-clock offset from run start in milliseconds (``clock=``).
            activity: Foreground activity at the decision.
            state: Screen/state hash.
            action: Action description or signature.
            decision_source: One of ``DECISION_SOURCES``.
            boosts: Per-mechanism boosts from ``scorer_boosts``; missing keys are 0.
        """
        self._ensure_open()
        boosts = boosts or {}
        self._writer.writerow(
            (
                step,
                clock_ms,
                activity,
                state,
                action,
                decision_source,
                boosts.get("mop", 0.0),
                boosts.get("wtg", 0.0),
                boosts.get("menu", 0.0),
                boosts.get("form", 0.0),
                boosts.get("coverage", 0.0),
            )
        )
        self._fh.flush()

    def close(self) -> None:
        """Close the underlying file if it was ever opened."""
        if self._fh is not None:
            self._fh.close()
            self._fh = None
            self._writer = None
