"""
Unit tests for Group 23: Action Signature Casing (C2 bug fix).

The C2 bug: strategy pre-marks actions with lowercase "click" (from
coords_for_matching which uses WIDGET_EVENT_TO_ACTION_TYPE), but
learn_node._record_action_success() was building signatures with uppercase
"CLICK" (from algorithm_node .upper()). This caused strength lookup to always
miss, returning 0.5 (neutral/untested) instead of the real success rate.

Tests:
(a) Pre-mark + record_action_success with matching lowercase -> strength > 0
(b) Uppercase "CLICK" vs lowercase "click" causes strength = 0.5 (neutral)
(c) End-to-end: pre-mark, record success, StrengthScorer returns non-neutral
"""

from unittest.mock import MagicMock

from rv_agent.domain.screen_node import ScreenNode
from rv_agent.strategies.rvagent_strategy.ranking.scorers import StrengthScorer
from rv_agent.strategies.rvagent_strategy.ranking.context import RankingContext


def _make_node(
    screen_hash: str = "hash_a", activity: str = "TestActivity"
) -> ScreenNode:
    """Create a ScreenNode with default values for testing."""
    return ScreenNode(screen_hash=screen_hash, activity=activity, total_actions=5)


def _make_mock_action(coords=(540, 340), action_type="click"):
    """Create a mock ItemAction with coords_for_matching property."""
    action = MagicMock()
    action.coords_for_matching = (coords, action_type)
    return action


def _make_ranking_context(node: ScreenNode) -> RankingContext:
    """Create a minimal RankingContext pointing to the given node."""
    graph = MagicMock()
    graph.states = {node.screen_hash: node}
    ui_coverage = MagicMock()

    return RankingContext(
        screen_desc=MagicMock(),
        graph=graph,
        ui_coverage=ui_coverage,
        current_state_hash=node.screen_hash,
        visited_activities=set(),
    )


class TestMatchingCasingStrength:
    """(a) When pre-mark and record use the same lowercase casing, strength reflects reality."""

    def test_strength_positive_after_successful_action(self):
        """After pre-marking with lowercase and recording success with lowercase,
        get_action_strength returns > 0 (not the 0.5 neutral default)."""
        node = _make_node()
        signature = ((540, 340), "click")

        # Pre-mark: strategy records action as executed (lowercase from coords_for_matching)
        node.record_action(signature)

        # Record success: learn_node records transition (now lowercase after fix)
        node.record_action_success(signature, success=True)

        strength = node.get_action_strength(signature)
        assert strength > 0, f"Expected strength > 0, got {strength}"
        assert strength == 1.0, "1 success / 1 execution = 1.0"

    def test_strength_zero_after_failed_action(self):
        """After pre-marking and recording failure, strength is 0.0 (not 0.5 neutral)."""
        node = _make_node()
        signature = ((540, 340), "click")

        node.record_action(signature)
        node.record_action_success(signature, success=False)

        strength = node.get_action_strength(signature)
        assert strength == 0.0, "0 successes / 1 execution = 0.0"

    def test_strength_mixed_results(self):
        """After 3 executions with 2 successes, strength = 2/3."""
        node = _make_node()
        signature = ((540, 340), "click")

        # Execute 3 times, 2 successful
        for success in [True, True, False]:
            node.record_action(signature)
            node.record_action_success(signature, success=success)

        strength = node.get_action_strength(signature)
        expected = 2.0 / 3.0
        assert (
            abs(strength - expected) < 0.01
        ), f"Expected ~{expected:.3f}, got {strength:.3f}"


class TestCasingMismatchBug:
    """(b) Demonstrate the old bug: uppercase vs lowercase causes neutral strength."""

    def test_uppercase_record_misses_lowercase_premark(self):
        """OLD BUG: pre-mark with lowercase "click", record_action_success with
        uppercase "CLICK" -> different keys in dict -> strength returns 0.5 (untested).
        """
        node = _make_node()
        lowercase_sig = ((540, 340), "click")
        uppercase_sig = ((540, 340), "CLICK")

        # Pre-mark: strategy uses lowercase (from coords_for_matching)
        node.record_action(lowercase_sig)

        # OLD behavior: learn_node used uppercase from action dict (before fix)
        # This records success under a DIFFERENT key
        node.record_action_success(uppercase_sig, success=True)

        # Lookup with lowercase (as StrengthScorer would via coords_for_matching)
        strength = node.get_action_strength(lowercase_sig)

        # Bug: execution count is 1 (from record_action), but success count is 0
        # because success was recorded under uppercase key.
        # strength = 0 successes / 1 execution = 0.0
        assert (
            strength == 0.0
        ), f"Expected 0.0 (bug: success recorded under wrong key), got {strength}"

    def test_uppercase_success_invisible_to_lowercase_lookup(self):
        """Success recorded under uppercase key is invisible to lowercase lookup."""
        node = _make_node()
        lowercase_sig = ((540, 340), "click")
        uppercase_sig = ((540, 340), "CLICK")

        node.record_action(lowercase_sig)
        node.record_action_success(uppercase_sig, success=True)

        # The uppercase key has its own success count
        assert node.action_success_counts.get(uppercase_sig, 0) == 1
        # But the lowercase key has zero successes
        assert node.action_success_counts.get(lowercase_sig, 0) == 0

    def test_untested_signature_returns_neutral(self):
        """An action signature with zero executions returns 0.5 (neutral)."""
        node = _make_node()
        never_executed_sig = ((999, 999), "click")

        strength = node.get_action_strength(never_executed_sig)
        assert strength == 0.5, f"Untested actions should return 0.5, got {strength}"


class TestStrengthScorerEndToEnd:
    """(c) End-to-end: pre-mark on ScreenNode, record success, verify StrengthScorer."""

    def test_scorer_returns_nonzero_after_successful_action(self):
        """StrengthScorer returns weight * 1.0 for action with 100% success rate."""
        node = _make_node()
        signature = ((540, 340), "click")

        # Pre-mark and record success (both lowercase, matching fix)
        node.record_action(signature)
        node.record_action_success(signature, success=True)

        # Create scorer and context
        scorer = StrengthScorer()  # Default weight = 50.0
        context = _make_ranking_context(node)
        mock_action = _make_mock_action(coords=(540, 340), action_type="click")

        score = scorer.score(mock_action, context)

        # strength = 1.0, weight = 50.0 -> score = 50.0 + 0.0 (no cumulative reward)
        expected = 50.0
        assert score == expected, f"Expected {expected}, got {score}"

    def test_scorer_returns_neutral_for_untested_action(self):
        """StrengthScorer returns weight * 0.5 for action never executed."""
        node = _make_node()

        scorer = StrengthScorer()  # Default weight = 50.0
        context = _make_ranking_context(node)
        mock_action = _make_mock_action(coords=(100, 200), action_type="click")

        score = scorer.score(mock_action, context)

        # Untested: strength = 0.5, weight = 50.0 -> score = 25.0
        expected = 25.0
        assert score == expected, f"Expected {expected}, got {score}"

    def test_scorer_distinguishes_successful_from_failed(self):
        """StrengthScorer gives higher score to successful action than failed one."""
        node = _make_node()
        success_sig = ((100, 100), "click")
        failure_sig = ((200, 200), "click")

        # Record one success and one failure
        node.record_action(success_sig)
        node.record_action_success(success_sig, success=True)

        node.record_action(failure_sig)
        node.record_action_success(failure_sig, success=False)

        scorer = StrengthScorer()
        context = _make_ranking_context(node)

        success_action = _make_mock_action(coords=(100, 100), action_type="click")
        failure_action = _make_mock_action(coords=(200, 200), action_type="click")

        success_score = scorer.score(success_action, context)
        failure_score = scorer.score(failure_action, context)

        # success: 50.0 * 1.0 = 50.0, failure: 50.0 * 0.0 = 0.0
        assert success_score > failure_score, (
            f"Successful action score ({success_score}) should be > "
            f"failed action score ({failure_score})"
        )

    def test_scorer_with_casing_mismatch_returns_neutral(self):
        """Demonstrates: if casing mismatch existed, scorer would return neutral (25.0)."""
        node = _make_node()
        lowercase_sig = ((540, 340), "click")
        uppercase_sig = ((540, 340), "CLICK")

        # Pre-mark with lowercase, but success recorded under uppercase (old bug)
        node.record_action(lowercase_sig)
        node.record_action_success(uppercase_sig, success=True)

        scorer = StrengthScorer()
        context = _make_ranking_context(node)
        mock_action = _make_mock_action(coords=(540, 340), action_type="click")

        score = scorer.score(mock_action, context)

        # Bug effect: execution count = 1, success count = 0 -> strength = 0.0
        # score = 50.0 * 0.0 = 0.0 (even worse than neutral 25.0)
        assert (
            score == 0.0
        ), f"With casing mismatch, score should be 0.0 (0 successes), got {score}"
