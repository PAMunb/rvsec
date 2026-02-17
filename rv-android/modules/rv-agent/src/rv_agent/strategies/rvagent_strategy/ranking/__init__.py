"""
Action ranking system for RVAgent strategy.

Provides a modular scoring system for action prioritization.

Active Scorers (7 total):
  Prioritization: MopScorer, WtgScorer, SaturationScorer, ComponentPriorityScorer, StrengthScorer
  Penalties: SystemElementFilter, VisitationPenaltyScorer

Deprecated (kept for backwards compatibility):
  GradualDecayScorer -> replaced by SaturationScorer + VisitationPenaltyScorer
  ExecutionCountScorer -> replaced by StrengthScorer
"""

from rv_agent.strategies.rvagent_strategy.ranking.context import RankingContext
from rv_agent.strategies.rvagent_strategy.ranking.action_ranker import ActionRanker, ScoredAction
from rv_agent.strategies.rvagent_strategy.ranking.scorers import (
    Scorer,
    MopScorer,
    WtgScorer,
    GradualDecayScorer,  # Deprecated
    ExecutionCountScorer,  # Deprecated
    ComponentPriorityScorer,
    SystemElementFilter,
    SaturationScorer,
    VisitationPenaltyScorer,
    StrengthScorer,
)

__all__ = [
    "RankingContext",
    "ActionRanker",
    "ScoredAction",
    "Scorer",
    # Active scorers
    "MopScorer",
    "WtgScorer",
    "SaturationScorer",
    "ComponentPriorityScorer",
    "StrengthScorer",
    "SystemElementFilter",
    "VisitationPenaltyScorer",
    # Deprecated (kept for compatibility)
    "GradualDecayScorer",
    "ExecutionCountScorer",
]
