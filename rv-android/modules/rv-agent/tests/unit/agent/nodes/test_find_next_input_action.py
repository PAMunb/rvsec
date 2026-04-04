"""
Unit tests for sequential fallback input finding in algorithm_node.

Tests _find_next_input_action() which iterates through available actions
on the current screen looking for the first TEXT_CHANGE (set_text) action.
Used as fallback when spatial association finds no match.
"""

from unittest.mock import MagicMock

from rv_agent.agent.nodes.algorithm_node import _find_next_input_action


def _make_item_action(action_type="set_text"):
    """Create a mock ItemAction with the given action type."""
    action = MagicMock()
    action.action_type = action_type
    action.id = 1
    return action


def _make_screen_item(actions):
    """Create a mock ScreenItem with given actions."""
    item = MagicMock()
    item.actions = actions
    return item


def _make_screen_description(items):
    """Create a mock ScreenDescription with given items."""
    desc = MagicMock()
    desc.items = items
    return desc


class TestFindNextInputAction:
    """Tests for _find_next_input_action sequential fallback."""

    def test_text_change_available(self):
        """Screen has set_text action -> returns (action, item) tuple."""
        action = _make_item_action(action_type="set_text")
        item = _make_screen_item([action])
        screen_desc = _make_screen_description([item])

        state = {"screen_description": screen_desc}

        result = _find_next_input_action(state)

        assert result is not None
        returned_action, returned_item = result
        assert returned_action == action
        assert returned_item == item

    def test_no_text_change_returns_none(self):
        """No set_text actions -> None."""
        click_action = _make_item_action(action_type="click")
        scroll_action = _make_item_action(action_type="scroll_down")
        item = _make_screen_item([click_action, scroll_action])
        screen_desc = _make_screen_description([item])

        state = {"screen_description": screen_desc}

        result = _find_next_input_action(state)

        assert result is None

    def test_screen_description_missing_returns_none(self):
        """No screen_description in state -> None."""
        state = {}

        result = _find_next_input_action(state)

        assert result is None

    def test_screen_description_none_returns_none(self):
        """screen_description is None -> None."""
        state = {"screen_description": None}

        result = _find_next_input_action(state)

        assert result is None

    def test_multiple_items_returns_first_set_text(self):
        """Multiple items, first set_text in second item -> returns that one."""
        click_action = _make_item_action(action_type="click")
        item1 = _make_screen_item([click_action])

        text_action = _make_item_action(action_type="set_text")
        item2 = _make_screen_item([text_action])

        screen_desc = _make_screen_description([item1, item2])

        state = {"screen_description": screen_desc}

        result = _find_next_input_action(state)

        assert result is not None
        returned_action, returned_item = result
        assert returned_action == text_action
        assert returned_item == item2

    def test_empty_items_returns_none(self):
        """Screen with no items -> None."""
        screen_desc = _make_screen_description([])

        state = {"screen_description": screen_desc}

        result = _find_next_input_action(state)

        assert result is None
