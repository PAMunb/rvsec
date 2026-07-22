"""
Ranking context for action scoring.

Provides shared context to all Scorers during action ranking.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional, Set

if TYPE_CHECKING:
    from rv_agent.agent.dynamic_state_graph import DynamicStateGraph
    from rv_agent.memory.ui_coverage import UICoverageTracker
    from rv_agent.services.transition_manager import TransitionManager
    from rv_agent.strategies.rvagent_strategy.successor_tracker import SuccessorTracker
    from rv_screen_parser.parser.screen.visitor.model import ScreenDescription


@dataclass
class RankingContext:
    """
    Context shared between all Scorers during action ranking.

    Contains all information needed by Scorers to calculate action scores.
    Scorers are stateless - all state comes from this context.
    """

    screen_desc: "ScreenDescription"
    graph: "DynamicStateGraph"
    ui_coverage: "UICoverageTracker"
    current_state_hash: str
    visited_activities: Set[str]
    transition_manager: Optional["TransitionManager"] = None
    has_untested_inputs: bool = False
    successor_tracker: Optional["SuccessorTracker"] = None
