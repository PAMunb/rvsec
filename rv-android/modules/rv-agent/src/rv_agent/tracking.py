"""
Unified tracking for RVAgent decision logging.

Prefix: [RVTRACK:<CATEGORY>] for easy grep and parsing.
Format: key=value pairs for structured data.

Categories:
    PARSE     - Screen captured (activity, elements, hash)
    ROUTE     - Routing decision (mode, path)
    RANK      - Top actions with scores
    SELECT    - Final selection (action, coords, mode)
    VALIDATE  - Validation result
    EXEC      - Action executed
    STATE     - State/activity changes
    LEARN     - Memory updates, stuck detection
    LLM       - LLM call details (tokens, time)
    NAV       - WTG navigation guidance
    ERROR     - Validation error detection (indicators, confidence, method)
    STRATEGY  - Tier selection and algorithm fast-path decisions
    BACKTRACK - PathBuffer navigation and reactive backtrack events
    REWARD    - Reward propagation events
    COVERAGE  - Coverage-based navigation (PathBuffer Strategy C)

Usage:
    from rv_agent.tracking import track
    track.parse(iter=5, activity=".MainActivity", elements=12, hash="abc123")
    track.select(iter=5, mode="stochastic", action="CLICK", coords=(540,525))

Filtering:
    grep "RVTRACK:RANK" logfile     # All ranking decisions
    grep "RVTRACK:" logfile          # All tracking logs
"""

import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Aggregate counters for experiment metrics (reset per experiment run)
_counters: Dict[str, int] = {
    "backtrack_count": 0,
    "path_buffer_planned": 0,
    "path_buffer_completed": 0,
    "reward_propagation_events": 0,
    "coverage_navigation_events": 0,
}


def get_aggregate_counters() -> Dict[str, int]:
    """Return aggregate counters including computed hit rate."""
    result = dict(_counters)
    planned = _counters["path_buffer_planned"]
    completed = _counters["path_buffer_completed"]
    # hit_rate as integer percentage (0-100) for JSON compatibility
    result["path_buffer_hit_rate_pct"] = (
        int(100 * completed / planned) if planned > 0 else 0
    )
    return result


def reset_counters() -> None:
    """Reset all aggregate counters. Called at experiment start."""
    for key in _counters:
        _counters[key] = 0


def _fmt(category: str, **kwargs) -> str:
    """Format tracking message."""
    parts = [f"{k}={v}" for k, v in kwargs.items() if v is not None]
    return f"[RVTRACK:{category}] {' '.join(parts)}"


def parse(iter: int, activity: str, elements: int, hash: str) -> None:
    """Log screen parsing result."""
    logger.info(
        _fmt("PARSE", iter=iter, activity=activity, elements=elements, hash=hash[:8])
    )


def route(iter: int, mode: str, path: str) -> None:
    """Log routing decision."""
    logger.info(_fmt("ROUTE", iter=iter, mode=mode, path=path))


def rank(iter: int, actions: List[Tuple[Tuple[int, int], float, str]]) -> None:
    """Log top ranked actions. Each tuple: (coords, score, priority_flag)."""
    if not actions:
        logger.info(_fmt("RANK", iter=iter, top="none"))
        return
    top_str = " ".join([f"{c}:{s:.0f}[{p}]" for c, s, p in actions[:5]])
    logger.info(_fmt("RANK", iter=iter, top=f'"{top_str}"'))


def rank_full(
    iter: int, actions: List[Tuple[Tuple[int, int], float, str, str, str]]
) -> None:
    """
    Log ALL ranked actions with component type for calibration analysis.

    Each tuple: (coords, score, priority_flag, component_type, action_type)

    Output format (one line per action):
        [RVTRACK:RANK_FULL] iter=5 idx=0 coords=(540,525) score=260 priority=DM type=Button action=CLICK
        [RVTRACK:RANK_FULL] iter=5 idx=1 coords=(320,480) score=210 priority=M type=EditText action=SET_TEXT
        ...

    Use for weight calibration:
        grep "RVTRACK:RANK_FULL" log | awk to analyze score distribution by component type
    """
    if not actions:
        logger.info(_fmt("RANK_FULL", iter=iter, count=0))
        return

    logger.info(_fmt("RANK_FULL", iter=iter, count=len(actions)))
    for idx, (coords, score, priority, comp_type, action_type) in enumerate(actions):
        logger.info(
            _fmt(
                "RANK_FULL",
                iter=iter,
                idx=idx,
                coords=coords,
                score=f"{score:.0f}",
                priority=priority or "UI",
                type=comp_type,
                action=action_type,
            )
        )


def select(
    iter: int,
    mode: str,
    action: str,
    coords: Tuple[int, int],
    score: float,
    priority: str,
) -> None:
    """Log final action selection."""
    logger.info(
        _fmt(
            "SELECT",
            iter=iter,
            mode=mode,
            action=action,
            coords=coords,
            score=f"{score:.0f}",
            priority=priority,
        )
    )


def validate(
    iter: int,
    passed: bool,
    action: str,
    coords: Tuple[int, int],
    reason: Optional[str] = None,
) -> None:
    """Log validation result."""
    status = "passed" if passed else "failed"
    logger.info(
        _fmt(
            "VALIDATE",
            iter=iter,
            status=status,
            action=action,
            coords=coords,
            reason=reason,
        )
    )


def execution(iter: int, action: str, coords: Tuple[int, int], source: str) -> None:
    """Log action execution."""
    logger.info(_fmt("EXEC", iter=iter, action=action, coords=coords, source=source))


def state(
    iter: int,
    changed: bool,
    activity_from: Optional[str] = None,
    activity_to: Optional[str] = None,
    hash: Optional[str] = None,
) -> None:
    """Log state change."""
    if changed:
        logger.info(
            _fmt(
                "STATE",
                iter=iter,
                changed=True,
                from_activity=activity_from,
                to_activity=activity_to,
                hash=hash[:8] if hash else None,
            )
        )
    else:
        logger.info(_fmt("STATE", iter=iter, changed=False))


def learn(
    iter: int,
    stuck: bool,
    memory_updated: bool,
    stuck_reason: Optional[str] = None,
    error_detected: bool = False,
) -> None:
    """Log learning/memory update."""
    logger.info(
        _fmt(
            "LEARN",
            iter=iter,
            stuck=stuck,
            memory_updated=memory_updated,
            stuck_reason=stuck_reason,
            error_detected=error_detected,
        )
    )


def llm(
    iter: int,
    tokens_in: int,
    tokens_out: int,
    time_ms: int,
    tool_calls: int,
    success: bool,
) -> None:
    """Log LLM call details."""
    logger.info(
        _fmt(
            "LLM",
            iter=iter,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            time_ms=time_ms,
            tool_calls=tool_calls,
            success=success,
        )
    )


def nav(
    iter: int,
    wtg_available: bool,
    unvisited_targets: int = 0,
    suggested_action_id: Optional[int] = None,
) -> None:
    """Log WTG navigation guidance."""
    logger.info(
        _fmt(
            "NAV",
            iter=iter,
            wtg=wtg_available,
            unvisited=unvisited_targets,
            suggested=suggested_action_id,
        )
    )


def saturation(iter: int, state_hash: str, rate: float, threshold: float) -> None:
    """Log saturation metrics for a state."""
    logger.info(
        _fmt(
            "SATURATION",
            iter=iter,
            state=state_hash[:8],
            rate=f"{rate:.2f}",
            threshold=f"{threshold:.2f}",
        )
    )


def strength(
    iter: int,
    action: str,
    coords: Tuple[int, int],
    strength_val: float,
    executions: int,
    successes: int,
) -> None:
    """Log action strength metrics."""
    logger.info(
        _fmt(
            "STRENGTH",
            iter=iter,
            action=action,
            coords=coords,
            strength=f"{strength_val:.2f}",
            exec=executions,
            succ=successes,
        )
    )


def scroll(iter: int, container_type: str, direction: str, reason: str) -> None:
    """Log scroll action for dynamic content."""
    logger.info(
        _fmt(
            "SCROLL",
            iter=iter,
            container=container_type,
            direction=direction,
            reason=reason,
        )
    )


def backtrack(
    iter: int,
    from_state: Optional[str] = None,
    to_state: Optional[str] = None,
    reason: Optional[str] = None,
    strategy: Optional[str] = None,
    remaining_steps: Optional[int] = None,
    target_hash: Optional[str] = None,
) -> None:
    """
    Log backtrack event.

    Two usage patterns:
    - Reactive (learn_node): from_state, to_state, reason
    - Proactive (PathBuffer): strategy, remaining_steps, target_hash
    """
    _counters["backtrack_count"] += 1
    logger.info(
        _fmt(
            "BACKTRACK",
            iter=iter,
            from_state=from_state[:8] if from_state else None,
            to_state=to_state[:8] if to_state else None,
            reason=reason,
            strategy=strategy,
            remaining=remaining_steps,
            target=target_hash[:8] if target_hash else None,
        )
    )


def error(
    iter: int,
    indicators_count: int,
    confidence: float,
    method: str,
    filtered_by_size: int = 0,
    filtered_by_region: int = 0,
    filtered_by_count: bool = False,
) -> None:
    """Log validation error detection event."""
    logger.info(
        _fmt(
            "ERROR",
            iter=iter,
            indicators=indicators_count,
            confidence=f"{confidence:.2f}",
            method=method,
            filtered_size=filtered_by_size,
            filtered_region=filtered_by_region,
            filtered_count=filtered_by_count,
        )
    )


def score_detail(iter: int, coords: Tuple[int, int], scorer: str, score: float) -> None:
    """Log individual scorer contribution (for debugging)."""
    logger.info(
        _fmt(
            "SCORE_DETAIL",
            iter=iter,
            coords=coords,
            scorer=scorer,
            score=f"{score:.0f}",
        )
    )


def strategy(iter: int, mode: str, action_type: str, reason: str) -> None:
    """Log strategy tier selection or algorithm fast-path decision."""
    logger.info(
        _fmt("STRATEGY", iter=iter, mode=mode, action=action_type, reason=reason)
    )


def reward_propagation(
    iter: int, reward_type: str, reward_value: float, steps_propagated: int
) -> None:
    """Log reward propagation event."""
    _counters["reward_propagation_events"] += 1
    logger.info(
        _fmt(
            "REWARD",
            iter=iter,
            type=reward_type,
            value=f"{reward_value:.1f}",
            steps=steps_propagated,
        )
    )


def coverage_navigation(
    iter: int, target_hash: str, exploration_potential: float, hops: int
) -> None:
    """Log coverage-based navigation (PathBuffer Strategy C)."""
    _counters["coverage_navigation_events"] += 1
    logger.info(
        _fmt(
            "COVERAGE",
            iter=iter,
            target=target_hash[:8],
            potential=f"{exploration_potential:.1f}",
            hops=hops,
        )
    )


def path_buffer_planned(strategy_name: str) -> None:
    """Record that a path was planned (for hit rate tracking)."""
    _counters["path_buffer_planned"] += 1
    logger.debug(f"[RVTRACK:PATH_BUFFER] planned strategy={strategy_name}")


def path_buffer_completed() -> None:
    """Record that a buffered path was fully consumed (for hit rate tracking)."""
    _counters["path_buffer_completed"] += 1
    logger.debug("[RVTRACK:PATH_BUFFER] completed")
