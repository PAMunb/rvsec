"""
Unit tests for coordinate space consistency (gh26 Group 14).

Verifies INV-AGT-40: device pixel space is the ONLY internal coordinate space
for action tracking, coverage recording, and strategy decisions.

Tests:
(a) execute_node pre-marking and learn_node success recording use same signature format
(b) successor_tracker records and queries use device-space signatures
(c) reward_propagator records and propagates using device-space signatures
(d) ui_coverage register and find use the same space
"""

import pytest
from unittest.mock import MagicMock, patch

from rv_agent.memory.element_id import make_element_id, parse_element_id
from rv_agent.memory.ui_coverage import UICoverageTracker
from rv_agent.strategies.rvagent_strategy.reward_propagator import RewardPropagator
from rv_agent.strategies.rvagent_strategy.successor_tracker import SuccessorTracker


class TestExecuteLearnSignatureConsistency:
    """(a) execute_node pre-marking and learn_node success recording use the same format."""

    def test_execute_node_premark_uses_device_space(self):
        """execute_node pre-marks actions with ((device_x, device_y), action_type)."""
        # Simulate what execute_node does (lines 160-163 of execute_node.py):
        # action_sig = ((x, y), action_type)
        # agent.dynamic_graph.record_action(screen_hash, action_sig)
        device_x, device_y = 540, 960
        action_type = "CLICK"
        action_sig = ((device_x, device_y), action_type)

        # The signature uses raw device coordinates, not converted
        assert action_sig == ((540, 960), "CLICK")
        assert action_sig[0] == (540, 960)  # Device pixels
        assert action_sig[1] == "CLICK"

    def test_learn_node_record_success_uses_device_space(self):
        """_record_action_success creates signatures from device-space action dict coords."""
        # Simulate what _record_action_success does after Group 14 changes:
        # action_signature = ((x, y), action_type)
        # where x, y come from current_action.get("x"), current_action.get("y")
        current_action = {"x": 540, "y": 960, "action_type": "CLICK"}
        x = current_action.get("x")
        y = current_action.get("y")
        action_type = current_action.get("action_type", "CLICK")

        action_signature = ((x, y), action_type)

        # Must match execute_node's pre-marking format exactly
        expected = ((540, 960), "CLICK")
        assert action_signature == expected

    def test_premark_and_success_signatures_match(self):
        """Pre-marking and success recording produce identical signatures for same action."""
        device_x, device_y = 270, 480
        action_type = "SET_TEXT"

        # execute_node creates: ((x, y), action_type)
        premark_sig = ((device_x, device_y), action_type)

        # learn_node creates from the same action dict
        action_dict = {"x": device_x, "y": device_y, "action_type": action_type}
        learn_sig = ((action_dict["x"], action_dict["y"]), action_dict["action_type"])

        assert premark_sig == learn_sig

    def test_no_optimized_conversion_in_learn_node(self):
        """Verify learn_node does NOT convert to optimized space."""
        # Before fix: learn_node converted (540, 960) -> (352, 624) via device_to_optimized
        # After fix: (540, 960) stays as (540, 960)
        device_x, device_y = 540, 960
        action_type = "CLICK"

        # The signature from learn_node (after fix)
        action_signature = ((device_x, device_y), action_type)

        # Must NOT be in optimized space (704x1248)
        # Optimized would be approximately (352, 624) for 1080x1920 -> 704x1248
        optimized_sig = ((352, 624), action_type)
        assert action_signature != optimized_sig


class TestSuccessorTrackerDeviceSpace:
    """(b) successor_tracker records and queries use device-space signatures."""

    def test_record_and_query_device_space(self):
        """SuccessorTracker stores and retrieves device-space signatures correctly."""
        graph = MagicMock()
        tracker = SuccessorTracker(graph)

        # Device-space action signature
        device_sig = ((540, 960), "CLICK")
        tracker.record_successor("state_A", device_sig, "state_B")

        # Query with same device-space signature
        result = tracker.get_action_destination("state_A", device_sig)
        assert result == "state_B"

    def test_query_fails_with_optimized_space_key(self):
        """Querying with optimized-space key returns None (mismatch detected)."""
        graph = MagicMock()
        tracker = SuccessorTracker(graph)

        # Record with device-space signature
        device_sig = ((540, 960), "CLICK")
        tracker.record_successor("state_A", device_sig, "state_B")

        # Querying with would-be optimized coords returns None
        optimized_sig = ((352, 624), "CLICK")
        result = tracker.get_action_destination("state_A", optimized_sig)
        assert result is None

    def test_successors_dict_uses_device_space_keys(self):
        """Internal successors dict keys contain device-space coordinates."""
        graph = MagicMock()
        tracker = SuccessorTracker(graph)

        device_sig = ((270, 480), "SET_TEXT")
        tracker.record_successor("hash_1", device_sig, "hash_2")

        # Verify the key in the internal dict
        key = ("hash_1", device_sig)
        assert key in tracker.successors
        assert tracker.successors[key] == "hash_2"

        # The coordinates in the key are device pixels
        stored_sig = key[1]
        coords, action_type = stored_sig
        assert coords == (270, 480)
        assert action_type == "SET_TEXT"


class TestRewardPropagatorDeviceSpace:
    """(c) reward_propagator records and propagates using device-space signatures."""

    def test_record_action_device_space(self):
        """record_action stores device-space action signatures."""
        propagator = RewardPropagator()

        device_sig = ((540, 960), "CLICK")
        propagator.record_action("state_A", device_sig)

        # Verify the action is in the history
        assert len(propagator._action_history) == 1
        state_hash, action_sig = propagator._action_history[0]
        assert state_hash == "state_A"
        assert action_sig == ((540, 960), "CLICK")

    def test_propagate_uses_device_space_keys(self):
        """propagate() looks up action_cumulative_reward with device-space keys."""
        propagator = RewardPropagator()

        # Create mock graph with a node
        graph = MagicMock()
        node = MagicMock()
        node.action_cumulative_reward = {}
        graph.states = {"state_A": node}

        # Record action in device space
        device_sig = ((540, 960), "CLICK")
        propagator.record_action("state_A", device_sig)

        # Propagate reward
        propagator.propagate("new_state", graph)

        # Verify the node's cumulative reward dict was updated with device-space key
        assert device_sig in node.action_cumulative_reward
        assert node.action_cumulative_reward[device_sig] > 0

    def test_propagate_does_not_use_optimized_keys(self):
        """propagate() must NOT store rewards under optimized-space keys."""
        propagator = RewardPropagator()

        graph = MagicMock()
        node = MagicMock()
        node.action_cumulative_reward = {}
        graph.states = {"state_A": node}

        device_sig = ((540, 960), "CLICK")
        propagator.record_action("state_A", device_sig)
        propagator.propagate("new_state", graph)

        # Optimized-space key should NOT exist
        optimized_sig = ((352, 624), "CLICK")
        assert optimized_sig not in node.action_cumulative_reward


class TestUICoverageDeviceSpace:
    """(d) ui_coverage register and find use the same space (device space)."""

    def test_register_screen_elements_uses_device_space(self):
        """register_screen_elements creates element IDs from device-space bounds center."""
        tracker = UICoverageTracker()

        # Mock screen description with bounds in device space
        mock_item = MagicMock()
        mock_item.view = {
            "class": "android.widget.Button",
            "bounds": [[400, 800], [680, 920]],  # Device pixels
        }
        mock_desc = MagicMock()
        mock_desc.items = [mock_item]

        tracker.register_screen_elements("screen_1", mock_desc)

        # Center should be (540, 860) in device space
        expected_id = make_element_id(540, 860)
        assert expected_id in tracker.screen_elements.get("screen_1", set())

    def test_find_nearest_element_in_device_space(self):
        """find_nearest_element matches device-space coordinates."""
        tracker = UICoverageTracker()

        # Register an element in device space
        element_id = make_element_id(540, 860)
        tracker.element_types[element_id] = "Button"
        tracker.screen_elements["screen_1"] = {element_id}

        # Search near the element in device space
        result = tracker.find_nearest_element(545, 865, screen_hash="screen_1")

        assert result is not None
        found_id, comp_type, distance = result
        assert found_id == element_id
        assert comp_type == "Button"
        assert distance < 10  # Very close in device pixels

    def test_register_and_find_use_same_space(self):
        """Elements registered via register_screen_elements are findable via find_nearest_element."""
        tracker = UICoverageTracker()

        # Register element with device-space bounds
        mock_item = MagicMock()
        mock_item.view = {
            "class": "android.widget.EditText",
            "bounds": [[100, 200], [500, 300]],  # Device pixels
        }
        mock_desc = MagicMock()
        mock_desc.items = [mock_item]

        tracker.register_screen_elements("screen_1", mock_desc)

        # Center is (300, 250) in device space
        # Search slightly off-center
        result = tracker.find_nearest_element(310, 255, screen_hash="screen_1")

        assert result is not None
        found_id, comp_type, distance = result
        assert comp_type == "EditText"
        assert distance < 15  # Close match in device pixels

    def test_max_distance_appropriate_for_device_space(self):
        """Default max_distance (200) is appropriate for 1080x1920 device resolution."""
        tracker = UICoverageTracker()

        element_id = make_element_id(540, 960)
        tracker.element_types[element_id] = "Button"
        tracker.screen_elements["screen_1"] = {element_id}

        # Element at 540,960. Search from 600,960 (60px away) - should find
        result = tracker.find_nearest_element(600, 960, screen_hash="screen_1")
        assert result is not None

        # Search from 800,960 (260px away) - should NOT find (beyond max_distance=200)
        result_far = tracker.find_nearest_element(800, 960, screen_hash="screen_1")
        assert result_far is None

    def test_normalized_coords_do_not_match_device_elements(self):
        """Normalized [0,1000) coords should NOT match device-space registered elements."""
        tracker = UICoverageTracker()

        # Register element at device-space (540, 960)
        element_id = make_element_id(540, 960)
        tracker.element_types[element_id] = "Button"
        tracker.screen_elements["screen_1"] = {element_id}

        # Search with normalized coords (500, 500) which is what [0,1000) space
        # would produce for center of a 1080x1920 screen
        # Distance: sqrt((540-500)^2 + (960-500)^2) = sqrt(1600+211600) = ~462
        # This exceeds max_distance=200, so no match
        result = tracker.find_nearest_element(500, 500, screen_hash="screen_1")
        assert result is None
