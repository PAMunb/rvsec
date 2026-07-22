"""
Group 33 — hash key mismatch fix.

Validates that the structural hash function uses UIAutomator2 underscored key names
(resource_id, long_clickable) instead of the hyphenated forms that UIAutomator1 used
(resource-id, long-clickable). Three specific behaviors are covered:

1. resource_id discrimination: two otherwise-identical views that differ only in
   resource_id produce different hashes.
2. long_clickable discrimination: two otherwise-identical views that differ only in
   long_clickable (True vs False) produce different hashes.
3. RVTRACK:HASH_DETAIL emission: when get_or_create_state() creates a NEW state the
   tracking module emits a [RVTRACK:HASH_DETAIL] log line (not emitted on revisits).
"""

import logging
from unittest.mock import MagicMock

import pytest
from rv_agent.agent.dynamic_state_graph import (
    DynamicStateGraph,
    compute_screen_hash_from_description,
)
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_item(resource_id: str = "", long_clickable: bool = False):
    """Return a minimal mock ScreenItem with structural attributes set."""
    item = MagicMock()
    item.view = {
        "class": "android.widget.Button",
        "resource_id": resource_id,
        "package": "com.test.app",
        "clickable": True,
        "scrollable": False,
        "checkable": False,
        "enabled": True,
        "long_clickable": long_clickable,
        "editable": False,
    }
    return item


def _make_desc(items, activity="com.test.app/.MainActivity"):
    """Return a minimal mock ScreenDescription wrapping *items*."""
    desc = MagicMock(spec=ScreenDescription)
    desc.activity = activity
    desc.items = items
    desc.get_all_actions = MagicMock(return_value=[])
    return desc


# ---------------------------------------------------------------------------
# 1. resource_id discrimination
# ---------------------------------------------------------------------------


class TestResourceIdDiscrimination:
    """
    Two views that are structurally identical except for resource_id must hash
    differently.  This verifies that the hash reads view["resource_id"] (the
    UIAutomator2 key) rather than the deprecated hyphenated form "resource-id".
    """

    def test_different_resource_ids_produce_different_hashes(self):
        """Views with distinct resource_id values produce distinct hashes."""
        item_a = _make_item(resource_id="com.test.app:id/button_ok")
        item_b = _make_item(resource_id="com.test.app:id/button_cancel")

        desc_a = _make_desc([item_a])
        desc_b = _make_desc([item_b])

        hash_a = compute_screen_hash_from_description(desc_a)
        hash_b = compute_screen_hash_from_description(desc_b)

        assert hash_a != hash_b, (
            "resource_id='button_ok' and resource_id='button_cancel' must produce "
            "different hashes — if they are equal the hash reads the wrong key"
        )

    def test_same_resource_id_produces_same_hash(self):
        """Sanity check: identical resource_id produces the same hash."""
        item_a = _make_item(resource_id="com.test.app:id/submit")
        item_b = _make_item(resource_id="com.test.app:id/submit")

        desc_a = _make_desc([item_a])
        desc_b = _make_desc([item_b])

        hash_a = compute_screen_hash_from_description(desc_a)
        hash_b = compute_screen_hash_from_description(desc_b)

        assert hash_a == hash_b

    def test_empty_vs_nonempty_resource_id(self):
        """A view with no resource_id hashes differently from one that has it."""
        item_with_id = _make_item(resource_id="com.test.app:id/btn")
        item_without_id = _make_item(resource_id="")

        desc_with = _make_desc([item_with_id])
        desc_without = _make_desc([item_without_id])

        hash_with = compute_screen_hash_from_description(desc_with)
        hash_without = compute_screen_hash_from_description(desc_without)

        assert hash_with != hash_without


# ---------------------------------------------------------------------------
# 2. long_clickable discrimination
# ---------------------------------------------------------------------------


class TestLongClickableDiscrimination:
    """
    Two views that are structurally identical except for long_clickable must hash
    differently.  This verifies that the hash reads view["long_clickable"] (the
    UIAutomator2 key) rather than the deprecated hyphenated form "long-clickable".
    """

    def test_long_clickable_true_vs_false_produce_different_hashes(self):
        """long_clickable=True and long_clickable=False produce distinct hashes."""
        item_lc = _make_item(resource_id="btn", long_clickable=True)
        item_no_lc = _make_item(resource_id="btn", long_clickable=False)

        desc_lc = _make_desc([item_lc])
        desc_no_lc = _make_desc([item_no_lc])

        hash_lc = compute_screen_hash_from_description(desc_lc)
        hash_no_lc = compute_screen_hash_from_description(desc_no_lc)

        assert hash_lc != hash_no_lc, (
            "long_clickable=True and long_clickable=False must produce different "
            "hashes — if they are equal the hash reads the wrong key"
        )

    def test_long_clickable_true_is_stable(self):
        """Same long_clickable=True value produces a consistent hash across calls."""
        item = _make_item(resource_id="btn", long_clickable=True)
        desc = _make_desc([item])

        assert compute_screen_hash_from_description(
            desc
        ) == compute_screen_hash_from_description(desc)


# ---------------------------------------------------------------------------
# 3. RVTRACK:HASH_DETAIL emission
# ---------------------------------------------------------------------------


class TestHashDetailTracking:
    """
    get_or_create_state() must emit a [RVTRACK:HASH_DETAIL] log line when a NEW
    state is inserted into the graph.  The line must NOT be emitted on subsequent
    visits to the same hash (only the first visit creates the node).
    """

    def test_hash_detail_emitted_for_new_state(self, caplog):
        """RVTRACK:HASH_DETAIL appears in logs when a new state is created."""
        graph = DynamicStateGraph()
        desc = _make_desc([_make_item(resource_id="btn1")])

        with caplog.at_level(logging.INFO, logger="rv_agent.tracking"):
            graph.get_or_create_state(
                screen_hash="aabbccddeeff",
                activity="com.test.app/.MainActivity",
                screen_desc=desc,
            )

        assert any(
            "RVTRACK:HASH_DETAIL" in record.message for record in caplog.records
        ), "Expected [RVTRACK:HASH_DETAIL] in log output when a new state is created"

    def test_hash_detail_not_emitted_on_revisit(self, caplog):
        """RVTRACK:HASH_DETAIL is NOT emitted when an existing state is revisited."""
        graph = DynamicStateGraph()
        desc = _make_desc([_make_item(resource_id="btn1")])

        # First visit — creates the node and should emit HASH_DETAIL
        graph.get_or_create_state(
            screen_hash="aabbccddeeff",
            activity="com.test.app/.MainActivity",
            screen_desc=desc,
        )

        # Second visit onwards — must not emit HASH_DETAIL again
        with caplog.at_level(logging.INFO, logger="rv_agent.tracking"):
            caplog.clear()
            graph.get_or_create_state(
                screen_hash="aabbccddeeff",
                activity="com.test.app/.MainActivity",
                screen_desc=desc,
            )

        assert not any(
            "RVTRACK:HASH_DETAIL" in record.message for record in caplog.records
        ), "RVTRACK:HASH_DETAIL must NOT be emitted for revisited states"

    def test_hash_detail_contains_state_hash(self, caplog):
        """HASH_DETAIL log line includes the first 8 chars of the state hash."""
        graph = DynamicStateGraph()
        desc = _make_desc([_make_item(resource_id="btn1")])
        state_hash = "deadbeef1234"

        with caplog.at_level(logging.INFO, logger="rv_agent.tracking"):
            graph.get_or_create_state(
                screen_hash=state_hash,
                activity="com.test.app/.MainActivity",
                screen_desc=desc,
            )

        detail_lines = [
            r.message for r in caplog.records if "RVTRACK:HASH_DETAIL" in r.message
        ]
        assert detail_lines, "Expected at least one RVTRACK:HASH_DETAIL line"
        # tracking.py emits state_hash[:8] as the hash= field
        assert (
            state_hash[:8] in detail_lines[0]
        ), f"Expected hash prefix '{state_hash[:8]}' in HASH_DETAIL line: {detail_lines[0]}"

    def test_hash_detail_emitted_per_unique_state(self, caplog):
        """Each distinct state hash produces its own HASH_DETAIL line."""
        graph = DynamicStateGraph()
        desc_a = _make_desc([_make_item(resource_id="btn_a")])
        desc_b = _make_desc([_make_item(resource_id="btn_b")])

        with caplog.at_level(logging.INFO, logger="rv_agent.tracking"):
            graph.get_or_create_state("hash000000aa", "Activity", desc_a)
            graph.get_or_create_state("hash000000bb", "Activity", desc_b)

        detail_lines = [
            r.message for r in caplog.records if "RVTRACK:HASH_DETAIL" in r.message
        ]
        assert (
            len(detail_lines) == 2
        ), f"Expected 2 RVTRACK:HASH_DETAIL lines (one per new state), got {len(detail_lines)}"
