"""
Unit tests for Group 42: LLM element ID format mismatch fix (D14).

The bug: _track_llm_text_value() in learn_node.py used f"({x},{y})" format for
element IDs when no widget_id was available. This caused a key mismatch with the
algorithm path, which uses the canonical "coords:x,y" format from element_id.py.
The algorithm's has_remaining_values() lookup would never find LLM-recorded values
because the keys differed.

Scenarios:
- R3-1-M1: LLM text value recorded under canonical "coords:x,y" key
- R3-1-M2: algorithm has_remaining_values lookup matches LLM-recorded value
- R3-1-M3: old format "(x,y)" not present in learn_node.py source code
"""

import re
from collections import defaultdict
from pathlib import Path
from unittest.mock import MagicMock

from rv_agent.agent.nodes.learn_node import _track_llm_text_value
from rv_agent.memory.element_id import make_element_id


def _make_agent_with_value_generator():
    """Create a minimal mock agent with a strategy.value_generator that has tested_values."""
    value_generator = MagicMock()
    value_generator.tested_values = defaultdict(list)

    strategy = MagicMock()
    strategy.value_generator = value_generator

    agent = MagicMock()
    agent.strategy = strategy

    return agent, value_generator


def _make_set_text_state(x, y, text, decision_maker="llm"):
    """Build a minimal AgentState dict for a SET_TEXT action from LLM."""
    return {
        "decision_maker": decision_maker,
        "current_action": {
            "action_type": "SET_TEXT",
            "x": x,
            "y": y,
            "text": text,
        },
        "current_item_action": None,
    }


class TestLlmElementIdCanonicalFormat:
    """R3-1-M1: LLM text value recorded under canonical 'coords:x,y' key."""

    def test_text_value_stored_with_canonical_key(self):
        """_track_llm_text_value uses make_element_id producing 'coords:x,y'."""
        agent, vg = _make_agent_with_value_generator()
        state = _make_set_text_state(540, 340, "hello@test.com")

        _track_llm_text_value(agent, state)

        expected_key = make_element_id(540, 340)  # "coords:540,340"
        assert expected_key == "coords:540,340"
        assert expected_key in vg.tested_values
        assert "hello@test.com" in vg.tested_values[expected_key]

    def test_old_format_key_not_created(self):
        """The old f'({x},{y})' key is NOT stored in tested_values."""
        agent, vg = _make_agent_with_value_generator()
        state = _make_set_text_state(100, 200, "password123")

        _track_llm_text_value(agent, state)

        old_key = "(100,200)"
        assert old_key not in vg.tested_values

    def test_multiple_texts_accumulate_under_same_canonical_key(self):
        """Multiple SET_TEXT actions for the same coords accumulate under one key."""
        agent, vg = _make_agent_with_value_generator()

        _track_llm_text_value(agent, _make_set_text_state(300, 400, "first"))
        _track_llm_text_value(agent, _make_set_text_state(300, 400, "second"))

        key = make_element_id(300, 400)
        assert vg.tested_values[key] == ["first", "second"]

    def test_duplicate_text_not_recorded_twice(self):
        """Same text value is not appended again for the same element."""
        agent, vg = _make_agent_with_value_generator()

        _track_llm_text_value(agent, _make_set_text_state(300, 400, "same"))
        _track_llm_text_value(agent, _make_set_text_state(300, 400, "same"))

        key = make_element_id(300, 400)
        assert vg.tested_values[key] == ["same"]


class TestAlgorithmLookupMatchesLlmKey:
    """R3-1-M2: algorithm has_remaining_values lookup matches LLM-recorded value."""

    def test_algorithm_finds_llm_recorded_value(self):
        """After LLM records a text, algorithm lookup on the same element_id finds it."""
        agent, vg = _make_agent_with_value_generator()
        x, y = 540, 340
        text = "test_input"

        # LLM records a value
        _track_llm_text_value(agent, _make_set_text_state(x, y, text))

        # Algorithm looks up with the same canonical key
        canonical_key = make_element_id(x, y)
        tested = vg.tested_values.get(canonical_key, [])
        assert text in tested, (
            f"Algorithm lookup with key '{canonical_key}' should find LLM-recorded "
            f"value '{text}', but tested_values={dict(vg.tested_values)}"
        )

    def test_get_tested_count_reflects_llm_entries(self):
        """Counting tested values for a canonical key includes LLM-recorded entries."""
        agent, vg = _make_agent_with_value_generator()

        _track_llm_text_value(agent, _make_set_text_state(100, 200, "val1"))
        _track_llm_text_value(agent, _make_set_text_state(100, 200, "val2"))

        key = make_element_id(100, 200)
        assert len(vg.tested_values[key]) == 2


class TestOldFormatNotInSource:
    """R3-1-M3: old format '(x,y)' not present in learn_node.py source code."""

    def test_no_parenthesized_coordinate_format_in_learn_node(self):
        """The old f'({x},{y})' pattern must not appear in the learn_node source."""
        learn_node_path = Path(__file__).resolve().parents[2] / (
            "src/rv_agent/agent/nodes/learn_node.py"
        )
        source = learn_node_path.read_text()

        # Match patterns like f"({x},{y})" or f'({x},{y})' that build element IDs
        # from coordinate variables. This is the exact bug pattern being fixed.
        old_pattern = re.compile(r'f["\']?\(\{[xy]\}\s*,\s*\{[xy]\}\)["\']?')
        matches = old_pattern.findall(source)

        assert matches == [], (
            f"Found old-format element ID pattern(s) in learn_node.py: {matches}. "
            "All coordinate-based element IDs should use make_element_id()."
        )


class TestEdgeCases:
    """Edge cases for _track_llm_text_value."""

    def test_widget_id_takes_precedence_over_coordinates(self):
        """When item_action has widget_id, it is used instead of coordinates."""
        agent, vg = _make_agent_with_value_generator()
        item_action = MagicMock()
        item_action.widget_id = "com.app:id/email_field"

        state = _make_set_text_state(100, 200, "user@test.com")
        state["current_item_action"] = item_action

        _track_llm_text_value(agent, state)

        assert "com.app:id/email_field" in vg.tested_values
        assert "user@test.com" in vg.tested_values["com.app:id/email_field"]
        # Coordinate key should NOT be created when widget_id is available
        assert make_element_id(100, 200) not in vg.tested_values

    def test_non_llm_decision_maker_skipped(self):
        """Actions from algorithm decision_maker are not tracked."""
        agent, vg = _make_agent_with_value_generator()
        state = _make_set_text_state(100, 200, "text", decision_maker="algorithm")

        _track_llm_text_value(agent, state)

        assert len(vg.tested_values) == 0

    def test_non_text_action_skipped(self):
        """CLICK actions are not tracked as text values."""
        agent, vg = _make_agent_with_value_generator()
        state = {
            "decision_maker": "llm",
            "current_action": {"action_type": "CLICK", "x": 100, "y": 200},
            "current_item_action": None,
        }

        _track_llm_text_value(agent, state)

        assert len(vg.tested_values) == 0

    def test_missing_coordinates_skipped(self):
        """When no widget_id and no coordinates, tracking is skipped gracefully."""
        agent, vg = _make_agent_with_value_generator()
        state = {
            "decision_maker": "llm",
            "current_action": {"action_type": "SET_TEXT", "text": "hello"},
            "current_item_action": None,
        }

        _track_llm_text_value(agent, state)

        assert len(vg.tested_values) == 0

    def test_text_change_action_type_also_tracked(self):
        """TEXT_CHANGE action type is tracked the same as SET_TEXT."""
        agent, vg = _make_agent_with_value_generator()
        state = {
            "decision_maker": "llm",
            "current_action": {
                "action_type": "text_change",
                "x": 50,
                "y": 60,
                "text": "new_val",
            },
            "current_item_action": None,
        }

        _track_llm_text_value(agent, state)

        key = make_element_id(50, 60)
        assert "new_val" in vg.tested_values[key]
