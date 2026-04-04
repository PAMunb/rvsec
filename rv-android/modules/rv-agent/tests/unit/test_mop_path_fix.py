"""
Unit tests for Group 31 (multi-hop MOP path fix).

Verifies PathBuffer.plan_mop_path() cooldown behavior and
TransitionManager.plan_path_to_mop_activity() step-1-only resolution.

Tests:
  (a) Multi-hop path returns only step 1 action with valid coordinates.
  (b) Step 1 failure (no resolvable coords) causes plan_mop_path to return False.
  (c) Cooldown expires after PLAN_COOLDOWN_AFTER_FAILURE iterations.
  (d) Re-planning is allowed after cooldown expires.
  (e) RVTRACK:MOP_RESOLVE is emitted on resolution attempt.
"""

from unittest.mock import MagicMock, patch

from rv_agent.services.transition_manager import TransitionManager
from rv_agent.strategies.rvagent_strategy.path_buffer import (
    PLAN_COOLDOWN_AFTER_FAILURE,
    PathBuffer,
)

# ---------------------------------------------------------------------------
# Shared factories
# ---------------------------------------------------------------------------


def _make_path_buffer(transition_manager=None):
    """Create a minimal PathBuffer with mocked dependencies."""
    successor_tracker = MagicMock()
    successor_tracker.graph = MagicMock()
    successor_tracker.graph.states = {}
    successor_tracker.back_successors = {}

    ui_coverage_tracker = MagicMock()
    ui_coverage_tracker.get_coverage_gap.return_value = 0.0
    ui_coverage_tracker.get_element_count.return_value = 0

    config = MagicMock()

    return PathBuffer(
        transition_manager=transition_manager,
        successor_tracker=successor_tracker,
        ui_coverage_tracker=ui_coverage_tracker,
        config=config,
    )


def _make_possible_action(widget_id, coordinates=(100, 200)):
    """Create a mock ItemAction representing a resolved on-screen widget."""
    action = MagicMock()
    action.widget_id = widget_id
    action.text = f"Button:{widget_id}"
    action.coordinates = coordinates
    action.target_view = {"class": "android.widget.Button"}
    action.id = 42
    return action


def _make_window(window_id, name, activity=""):
    """Create a mock Window object for TransitionManager tests."""
    w = MagicMock()
    w.id = window_id
    w.name = name
    w.activity = activity
    w.widgets = {}
    return w


def _make_method(class_name, reaches_mop=False, directly_reaches_mop=False):
    """Create a mock Method object."""
    m = MagicMock()
    m.class_name = class_name
    m.reaches_mop = reaches_mop
    m.directly_reaches_mop = directly_reaches_mop
    return m


def _make_transition_manager_with_mop(
    source_activity="com.example.ActivityA",
    target_activity="com.example.ActivityB",
    widget_id="btn_mop",
    hop_count=1,
):
    """
    Build a TransitionManager where BFS finds a MOP activity.

    hop_count controls how many intermediate hops separate source from the
    MOP target.  For hop_count=1 the target is a direct neighbor; for
    hop_count=2 there is one intermediate window.
    """
    windows = []
    transitions = []

    # Build window chain: w0 -> (intermediate windows) -> w_target
    source_win_id = "w0"
    source_win = _make_window(source_win_id, source_activity, activity=source_activity)
    windows.append(source_win)

    prev_id = source_win_id
    for hop in range(1, hop_count):
        mid_id = f"w_mid{hop}"
        mid_win = _make_window(
            mid_id, f"Intermediate{hop}", activity=f"com.example.Intermediate{hop}"
        )
        windows.append(mid_win)
        transitions.append(
            {"source": prev_id, "target": mid_id, "widget_id": f"btn_mid{hop}"}
        )
        prev_id = mid_id

    target_win_id = "w_target"
    target_win = _make_window(target_win_id, target_activity, activity=target_activity)
    windows.append(target_win)
    transitions.append(
        {"source": prev_id, "target": target_win_id, "widget_id": widget_id}
    )

    # Static data
    static_data = MagicMock()

    windows_container = MagicMock()
    windows_container.windows = windows
    static_data.windows = windows_container

    classes = MagicMock()
    classes.methods = {
        f"{target_activity}.doSomething": _make_method(
            target_activity, reaches_mop=True
        )
    }
    static_data.classes = classes

    wtg = MagicMock()
    wtg.get_window_transitions = lambda wid: [
        t for t in transitions if t.get("source") == wid
    ]
    static_data.wtg = wtg

    dynamic_graph = MagicMock()
    dynamic_graph.states = {}
    dynamic_graph.transitions = {}

    return TransitionManager(static_data=static_data, dynamic_graph=dynamic_graph)


# ---------------------------------------------------------------------------
# (a) Multi-hop path returns only step 1 action with valid coordinates
# ---------------------------------------------------------------------------


class TestStepOneOnlyResolution:
    """plan_path_to_mop_activity() returns exactly one action dict (step 1)."""

    def test_two_hop_path_returns_step1_only(self):
        """
        When MOP activity is 2 hops away, only step 1 is returned so that
        subsequent hops can be re-planned after each intermediate screen arrives.

        In the 2-hop factory, the chain is:
            w0 --(btn_mid1)--> w_mid1 --(btn_mop)--> w_target
        Step 1 is the edge from w0, which uses widget_id "btn_mid1".
        The possible_actions list must include that widget so coordinates resolve.
        """
        tm = _make_transition_manager_with_mop(
            source_activity="com.example.ActivityA",
            target_activity="com.example.ActivityC",
            widget_id="btn_mop",  # final-edge widget (not used for step 1)
            hop_count=2,
        )
        # Step 1 widget is "btn_mid1" (generated by _make_transition_manager_with_mop)
        possible_actions = [_make_possible_action("btn_mid1", coordinates=(150, 300))]

        result = tm.plan_path_to_mop_activity(
            "com.example.ActivityA", None, possible_actions=possible_actions
        )

        assert result is not None, "Should return a path when BFS finds a MOP activity"
        assert (
            len(result) == 1
        ), "Only step 1 should be returned regardless of path length"
        assert result[0]["coordinates"] == (150, 300)
        assert result[0]["reaches_mop"] is True

    def test_direct_hop_returns_single_action_with_coords(self):
        """Direct (1-hop) path also returns exactly one action with coordinates."""
        tm = _make_transition_manager_with_mop(
            source_activity="com.example.ActivityA",
            target_activity="com.example.ActivityB",
            widget_id="btn_direct",
            hop_count=1,
        )
        possible_actions = [_make_possible_action("btn_direct", coordinates=(200, 400))]

        result = tm.plan_path_to_mop_activity(
            "com.example.ActivityA", None, possible_actions=possible_actions
        )

        assert result is not None
        assert len(result) == 1
        assert result[0]["coordinates"] == (200, 400)


# ---------------------------------------------------------------------------
# (b) Step 1 failure returns None from plan_path_to_mop_activity
# ---------------------------------------------------------------------------


class TestStepOneFailure:
    """When step 1 cannot be resolved (no coords), plan_path_to_mop_activity returns None."""

    def test_no_matching_possible_action_returns_none(self):
        """
        BFS finds a MOP path but no on-screen action matches the WTG widget_id,
        so the method returns None instead of an unresolvable action dict.
        """
        tm = _make_transition_manager_with_mop(
            widget_id="btn_settings",
            hop_count=1,
        )
        possible_actions = [
            # Different widget_id, no text match either
            _make_possible_action("btn_home", coordinates=(50, 50))
        ]

        result = tm.plan_path_to_mop_activity(
            "com.example.ActivityA", None, possible_actions=possible_actions
        )

        assert result is None

    def test_no_possible_actions_returns_none(self):
        """Without possible_actions, step 1 cannot be resolved."""
        tm = _make_transition_manager_with_mop(hop_count=1)

        result = tm.plan_path_to_mop_activity(
            "com.example.ActivityA", None, possible_actions=None
        )

        assert result is None

    def test_plan_mop_path_returns_false_on_step1_failure(self):
        """
        PathBuffer.plan_mop_path() returns False when TransitionManager fails
        to resolve step 1 and records a cooldown for that activity.
        """
        transition_manager = MagicMock()
        transition_manager.plan_path_to_mop_activity.return_value = None

        pb = _make_path_buffer(transition_manager=transition_manager)

        result = pb.plan_mop_path(
            current_activity="com.example.ActivityA",
            mop_data=None,
            possible_actions=[],
            current_iteration=0,
        )

        assert result is False
        assert not pb.is_active
        # Cooldown must be recorded for this activity
        assert "com.example.ActivityA" in pb._mop_path_cooldown


# ---------------------------------------------------------------------------
# (c) Cooldown expires after PLAN_COOLDOWN_AFTER_FAILURE iterations
# ---------------------------------------------------------------------------


class TestCooldownExpiry:
    """_mop_path_cooldown expires after PLAN_COOLDOWN_AFTER_FAILURE iterations."""

    def test_cooldown_blocks_planning_within_window(self):
        """
        After a failure at iteration 0, planning the same activity is blocked
        until PLAN_COOLDOWN_AFTER_FAILURE iterations have passed.
        """
        transition_manager = MagicMock()
        # First call fails; subsequent calls would succeed if not blocked
        transition_manager.plan_path_to_mop_activity.return_value = None

        pb = _make_path_buffer(transition_manager=transition_manager)
        activity = "com.example.MainActivity"

        # Trigger failure at iteration 0
        pb.plan_mop_path(activity, None, [], current_iteration=0)
        assert activity in pb._mop_path_cooldown

        # Now let the next call succeed (so the block is observable)
        transition_manager.plan_path_to_mop_activity.return_value = [
            {
                "action_type": "CLICK",
                "action_id": 1,
                "widget_id": "btn1",
                "target_activity": "com.example.TargetActivity",
                "text": "Navigate",
                "reaches_mop": True,
                "directly_reaches_mop": False,
                "coordinates": (100, 200),
                "target_view": {},
            }
        ]

        # Within cooldown window — should still return False
        for delta in range(PLAN_COOLDOWN_AFTER_FAILURE):
            result = pb.plan_mop_path(activity, None, [], current_iteration=delta)
            assert result is False, f"Expected False at delta={delta} (within cooldown)"

    def test_cooldown_constant_value(self):
        """PLAN_COOLDOWN_AFTER_FAILURE is 3 as documented in Group 31."""
        assert PLAN_COOLDOWN_AFTER_FAILURE == 3

    def test_cooldown_entry_records_failure_iteration(self):
        """The cooldown dict maps activity to the iteration of the failure."""
        transition_manager = MagicMock()
        transition_manager.plan_path_to_mop_activity.return_value = None

        pb = _make_path_buffer(transition_manager=transition_manager)
        activity = "com.example.ActivityX"

        pb.plan_mop_path(activity, None, [], current_iteration=10)

        assert pb._mop_path_cooldown[activity] == 10


# ---------------------------------------------------------------------------
# (d) Re-planning is allowed after cooldown
# ---------------------------------------------------------------------------


class TestCooldownReplanningAllowed:
    """After PLAN_COOLDOWN_AFTER_FAILURE iterations the activity can be re-planned."""

    def _make_good_action_dict(self):
        return [
            {
                "action_type": "CLICK",
                "action_id": 5,
                "widget_id": "btn_mop",
                "target_activity": "com.example.TargetActivity",
                "text": "Navigate to TargetActivity",
                "reaches_mop": True,
                "directly_reaches_mop": False,
                "coordinates": (300, 500),
                "target_view": {"class": "android.widget.Button"},
            }
        ]

    def test_replanning_succeeds_after_cooldown_expires(self):
        """
        At iteration PLAN_COOLDOWN_AFTER_FAILURE (or later), the cooldown entry
        is removed and plan_mop_path() can succeed.
        """
        transition_manager = MagicMock()
        transition_manager.plan_path_to_mop_activity.return_value = None

        pb = _make_path_buffer(transition_manager=transition_manager)
        activity = "com.example.ActivityY"
        failure_iter = 5

        # Trigger failure
        pb.plan_mop_path(activity, None, [], current_iteration=failure_iter)
        assert activity in pb._mop_path_cooldown

        # Now the transition manager will succeed on next attempt
        transition_manager.plan_path_to_mop_activity.return_value = (
            self._make_good_action_dict()
        )

        # Attempt exactly at cooldown expiry boundary
        expiry_iter = failure_iter + PLAN_COOLDOWN_AFTER_FAILURE
        result = pb.plan_mop_path(activity, None, [], current_iteration=expiry_iter)

        assert result is True, (
            f"Re-planning should succeed at iteration {expiry_iter} "
            f"(failure at {failure_iter}, cooldown={PLAN_COOLDOWN_AFTER_FAILURE})"
        )
        # Cooldown entry must be cleared
        assert activity not in pb._mop_path_cooldown
        assert pb.is_active

    def test_cooldown_removed_after_successful_replan(self):
        """Once cooldown expires and planning succeeds, the entry is gone."""
        transition_manager = MagicMock()
        transition_manager.plan_path_to_mop_activity.return_value = None

        pb = _make_path_buffer(transition_manager=transition_manager)
        activity = "com.example.ActivityZ"

        pb.plan_mop_path(activity, None, [], current_iteration=0)

        transition_manager.plan_path_to_mop_activity.return_value = (
            self._make_good_action_dict()
        )

        pb.plan_mop_path(
            activity, None, [], current_iteration=PLAN_COOLDOWN_AFTER_FAILURE
        )

        assert activity not in pb._mop_path_cooldown

    def test_different_activities_have_independent_cooldowns(self):
        """Cooldown for one activity does not block a different activity."""
        transition_manager = MagicMock()
        transition_manager.plan_path_to_mop_activity.return_value = None

        pb = _make_path_buffer(transition_manager=transition_manager)

        activity_a = "com.example.ActivityA"
        activity_b = "com.example.ActivityB"

        # Trigger failure only for A
        pb.plan_mop_path(activity_a, None, [], current_iteration=0)
        assert activity_a in pb._mop_path_cooldown
        assert activity_b not in pb._mop_path_cooldown

        # Now B can plan successfully
        transition_manager.plan_path_to_mop_activity.return_value = [
            {
                "action_type": "CLICK",
                "action_id": 1,
                "widget_id": "btn_b",
                "target_activity": "com.example.TargetB",
                "text": "Go",
                "reaches_mop": True,
                "directly_reaches_mop": False,
                "coordinates": (100, 200),
                "target_view": {},
            }
        ]
        result = pb.plan_mop_path(activity_b, None, [], current_iteration=0)
        assert result is True


# ---------------------------------------------------------------------------
# (e) RVTRACK:MOP_RESOLVE is emitted on resolution attempt
# ---------------------------------------------------------------------------


class TestMopResolveTracking:
    """track.mop_resolve() is called whenever plan_mop_path() makes an attempt."""

    def test_tracking_emitted_on_failure(self):
        """
        When TransitionManager returns None (unresolvable), mop_resolve is
        called with resolved=False and a non-zero cooldown.
        """
        transition_manager = MagicMock()
        transition_manager.plan_path_to_mop_activity.return_value = None

        pb = _make_path_buffer(transition_manager=transition_manager)

        with patch(
            "rv_agent.strategies.rvagent_strategy.path_buffer.track"
        ) as mock_track:
            pb.plan_mop_path("com.example.ActivityA", None, [], current_iteration=1)

            mock_track.mop_resolve.assert_called_once_with(
                iter=1,
                target_activity="com.example.ActivityA",
                resolved=False,
                cooldown_remaining=PLAN_COOLDOWN_AFTER_FAILURE,
                step=1,
            )

    def test_tracking_emitted_on_success(self):
        """
        When TransitionManager returns a valid action, mop_resolve is called
        with resolved=True and cooldown_remaining=0.
        """
        good_action = [
            {
                "action_type": "CLICK",
                "action_id": 7,
                "widget_id": "btn_ok",
                "target_activity": "com.example.TargetActivity",
                "text": "Navigate",
                "reaches_mop": True,
                "directly_reaches_mop": False,
                "coordinates": (250, 400),
                "target_view": {"class": "android.widget.Button"},
            }
        ]
        transition_manager = MagicMock()
        transition_manager.plan_path_to_mop_activity.return_value = good_action

        pb = _make_path_buffer(transition_manager=transition_manager)

        with patch(
            "rv_agent.strategies.rvagent_strategy.path_buffer.track"
        ) as mock_track:
            result = pb.plan_mop_path(
                "com.example.ActivityA", None, [], current_iteration=3
            )

            assert result is True
            mock_track.mop_resolve.assert_called_once_with(
                iter=3,
                target_activity="com.example.ActivityA",
                resolved=True,
                cooldown_remaining=0,
                step=1,
            )

    def test_tracking_emitted_during_cooldown(self):
        """
        When an activity is still in cooldown, mop_resolve is called with
        resolved=False and the remaining cooldown count.
        """
        transition_manager = MagicMock()
        transition_manager.plan_path_to_mop_activity.return_value = None

        pb = _make_path_buffer(transition_manager=transition_manager)
        activity = "com.example.CooldownActivity"

        # Trigger initial failure at iteration 0
        pb.plan_mop_path(activity, None, [], current_iteration=0)

        # Attempt again at iteration 1 (still in cooldown, 2 remaining)
        with patch(
            "rv_agent.strategies.rvagent_strategy.path_buffer.track"
        ) as mock_track:
            pb.plan_mop_path(activity, None, [], current_iteration=1)

            mock_track.mop_resolve.assert_called_once_with(
                iter=1,
                target_activity=activity,
                resolved=False,
                cooldown_remaining=2,
                step=0,
            )
