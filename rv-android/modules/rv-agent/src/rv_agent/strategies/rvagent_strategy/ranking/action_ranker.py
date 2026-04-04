"""
Action ranking system for priority-based action selection.

Orchestrates multiple Scorers to calculate action priorities and select
the best action based on combined scores.
"""

import logging
import math
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from rv_agent.strategies.rvagent_strategy.ranking.context import RankingContext
    from rv_agent.strategies.rvagent_strategy.ranking.scorers import Scorer
    from rv_screen_parser.parser.screen.visitor.model import ItemAction


logger = logging.getLogger(__name__)


@dataclass
class ScoredAction:
    """Action with its calculated score."""

    action: "ItemAction"
    score: float


class ActionRanker:
    """
    Orchestrates multiple Scorers to rank and select actions.

    Combines scores from all registered Scorers to determine action priority.
    Supports both deterministic and stochastic (Gumbel-max) selection.
    """

    def __init__(self, scorers: List["Scorer"]):
        """
        Initialize with a list of Scorers.

        Args:
            scorers: List of Scorer instances to use for ranking
        """
        self.scorers = scorers

    def rank(
        self, actions: List["ItemAction"], context: "RankingContext"
    ) -> List[ScoredAction]:
        """
        Rank actions by combined score from all Scorers.

        Args:
            actions: Actions to rank
            context: Shared ranking context

        Returns:
            List of ScoredAction sorted by score (highest first)
        """
        scored = []
        for action in actions:
            total_score = sum(scorer.score(action, context) for scorer in self.scorers)
            scored.append(ScoredAction(action=action, score=total_score))

        scored.sort(key=lambda x: -x.score)
        return scored

    def score_action(self, action: "ItemAction", context: "RankingContext") -> float:
        """
        Calculate total score for a single action.

        Args:
            action: Action to score
            context: Shared ranking context

        Returns:
            Total score from all scorers
        """
        return sum(scorer.score(action, context) for scorer in self.scorers)

    def select_best(
        self, actions: List["ItemAction"], context: "RankingContext"
    ) -> Optional["ItemAction"]:
        """
        Select the action with highest score (deterministic).

        Args:
            actions: Actions to choose from
            context: Shared ranking context

        Returns:
            Highest-scored action, or None if no actions
        """
        if not actions:
            return None

        ranked = self.rank(actions, context)
        if not ranked:
            return None

        selected = ranked[0]
        logger.debug(f"ActionRanker: Selected action with score {selected.score:.1f}")
        return selected.action

    def select_stochastic(
        self,
        actions: List["ItemAction"],
        context: "RankingContext",
        temperature: float = 1.0,
    ) -> Optional["ItemAction"]:
        """
        Select action using Gumbel-max trick for stochastic selection.

        Adds Gumbel noise to scores, maintaining preference for high-priority
        actions while allowing occasional selection of lower-priority actions.
        Higher temperature increases randomness.

        Args:
            actions: Actions to choose from
            context: Shared ranking context
            temperature: Controls randomness (higher = more random)

        Returns:
            Selected action, or None if no actions
        """
        if not actions:
            return None

        ranked = self.rank(actions, context)
        if not ranked:
            return None

        if len(ranked) == 1:
            return ranked[0].action

        perturbed = []
        for scored in ranked:
            u = random.uniform(0.001, 0.999)
            gumbel_noise = -math.log(-math.log(u))
            perturbed_score = scored.score + gumbel_noise * temperature
            perturbed.append((perturbed_score, scored.action))

        selected = max(perturbed, key=lambda x: x[0])
        logger.debug(f"ActionRanker: Stochastic selection (temp={temperature})")
        return selected[1]
