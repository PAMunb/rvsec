"""
Unit tests for _update_cached_bounds in parse_node.

Tests the bounds-update logic that corrects cached element positions when
the keyboard appears/disappears (elements shift vertically but structural
hash stays the same).

Design ref: D13 (R3-1) in gh26-exploration-strategy/design.md
Scenarios: R3-1-S1 through R3-1-S13
"""

from unittest.mock import MagicMock

from rv_agent.agent.nodes.parse_node import _update_cached_bounds

# -- Helpers ------------------------------------------------------------------


def _make_action(widget_id=None, bounds=None):
    """Create a mock ItemAction with the given widget_id and bounds."""
    action = MagicMock()
    action.widget_id = widget_id
    if bounds is not None:
        action.target_view = {"bounds": bounds, "class": "android.widget.Button"}
    else:
        action.target_view = None
    return action


def _make_item(*actions):
    """Create a mock ScreenItem wrapping the given actions."""
    item = MagicMock()
    item.actions = list(actions)
    return item


def _make_desc(*items):
    """Create a mock ScreenDescription wrapping the given items."""
    desc = MagicMock()
    desc.items = list(items)
    return desc


# -- R3-1-S1: Nested bounds with widget_id match -----------------------------


class TestS1WidgetIdMatchUpdatesBounds:
    """R3-1-S1: nested bounds [[x1,y1],[x2,y2]] with widget_id match."""

    def test_bounds_updated_when_widget_id_matches(self):
        """R3-1-S1: cached bounds replaced with fresh bounds on widget_id match."""
        cached_action = _make_action(
            widget_id="btn_ok", bounds=[[100, 200], [300, 400]]
        )
        cached_desc = _make_desc(_make_item(cached_action))

        fresh_action = _make_action(widget_id="btn_ok", bounds=[[100, 350], [300, 550]])
        fresh_desc = _make_desc(_make_item(fresh_action))

        _update_cached_bounds(cached_desc, fresh_desc)

        assert cached_action.target_view["bounds"] == [[100, 350], [300, 550]]


# -- R3-1-S2: Nested bounds with proximity match -----------------------------


class TestS2ProximityMatch:
    """R3-1-S2: nested bounds with proximity match (no widget_id, centers < 50px)."""

    def test_bounds_updated_when_centers_within_threshold(self):
        """R3-1-S2: actions without widget_id matched by center proximity (<50px)."""
        # Cached center: ((100+300)//2, (200+400)//2) = (200, 300)
        cached_action = _make_action(widget_id=None, bounds=[[100, 200], [300, 400]])
        cached_desc = _make_desc(_make_item(cached_action))

        # Fresh center: ((110+310)//2, (210+410)//2) = (210, 310) — within 50px
        fresh_action = _make_action(widget_id=None, bounds=[[110, 210], [310, 410]])
        fresh_desc = _make_desc(_make_item(fresh_action))

        _update_cached_bounds(cached_desc, fresh_desc)

        assert cached_action.target_view["bounds"] == [[110, 210], [310, 410]]


# -- R3-1-S3: Proximity too far ----------------------------------------------


class TestS3ProximityTooFar:
    """R3-1-S3: centers > 50px apart — bounds NOT updated."""

    def test_bounds_not_updated_when_centers_too_far(self):
        """R3-1-S3: bounds unchanged when center diff exceeds 50px threshold."""
        # Cached center: (200, 300)
        cached_action = _make_action(widget_id=None, bounds=[[100, 200], [300, 400]])
        original_bounds = cached_action.target_view["bounds"]
        cached_desc = _make_desc(_make_item(cached_action))

        # Fresh center: ((500+700)//2, (600+800)//2) = (600, 700) — far away
        fresh_action = _make_action(widget_id=None, bounds=[[500, 600], [700, 800]])
        fresh_desc = _make_desc(_make_item(fresh_action))

        _update_cached_bounds(cached_desc, fresh_desc)

        assert cached_action.target_view["bounds"] is original_bounds


# -- R3-1-S4: Bounds is None -------------------------------------------------


class TestS4BoundsNone:
    """R3-1-S4: bounds is None — skipped, no crash."""

    def test_none_bounds_skipped(self):
        """R3-1-S4: action with bounds=None is skipped without error."""
        cached_action = MagicMock()
        cached_action.widget_id = "btn_ok"
        cached_action.target_view = {"bounds": None}
        cached_desc = _make_desc(_make_item(cached_action))

        fresh_action = MagicMock()
        fresh_action.widget_id = "btn_ok"
        fresh_action.target_view = {"bounds": None}
        fresh_desc = _make_desc(_make_item(fresh_action))

        _update_cached_bounds(cached_desc, fresh_desc)  # should not raise


# -- R3-1-S5: Bounds is empty list -------------------------------------------


class TestS5BoundsEmptyList:
    """R3-1-S5: bounds is empty list — skipped, no crash."""

    def test_empty_bounds_skipped(self):
        """R3-1-S5: action with bounds=[] is skipped without error."""
        cached_action = _make_action(widget_id="btn_ok", bounds=[])
        cached_desc = _make_desc(_make_item(cached_action))

        fresh_action = _make_action(widget_id="btn_ok", bounds=[])
        fresh_desc = _make_desc(_make_item(fresh_action))

        _update_cached_bounds(cached_desc, fresh_desc)  # should not raise

    def test_single_element_bounds_skipped(self):
        """R3-1-S5 variant: bounds with only 1 element is skipped."""
        cached_action = _make_action(widget_id="btn_ok", bounds=[[10, 20]])
        cached_desc = _make_desc(_make_item(cached_action))

        fresh_action = _make_action(widget_id="btn_ok", bounds=[[10, 20]])
        fresh_desc = _make_desc(_make_item(fresh_action))

        _update_cached_bounds(cached_desc, fresh_desc)  # should not raise


# -- R3-1-S6: Bounds has wrong inner format -----------------------------------


class TestS6MalformedBounds:
    """R3-1-S6: flat ints [100, 200] instead of nested [[100,200],[300,400]]."""

    def test_flat_ints_skipped_via_type_error(self):
        """R3-1-S6: flat int bounds skipped via TypeError catch, no crash."""
        cached_action = _make_action(widget_id="btn_ok", bounds=[100, 200])
        cached_desc = _make_desc(_make_item(cached_action))

        fresh_action = _make_action(widget_id="btn_ok", bounds=[300, 400])
        fresh_desc = _make_desc(_make_item(fresh_action))

        _update_cached_bounds(cached_desc, fresh_desc)  # should not raise

    def test_string_bounds_skipped(self):
        """R3-1-S6 variant: string bounds skipped gracefully."""
        cached_action = _make_action(widget_id="btn_ok", bounds="invalid")
        cached_desc = _make_desc(_make_item(cached_action))

        fresh_action = _make_action(widget_id="btn_ok", bounds="invalid")
        fresh_desc = _make_desc(_make_item(fresh_action))

        _update_cached_bounds(cached_desc, fresh_desc)  # should not raise


# -- R3-1-S7: target_view is None --------------------------------------------


class TestS7TargetViewNone:
    """R3-1-S7: target_view is None — skipped, no crash."""

    def test_none_target_view_skipped(self):
        """R3-1-S7: action with target_view=None is skipped without error."""
        cached_action = _make_action(
            widget_id="btn_ok", bounds=None
        )  # target_view=None
        cached_desc = _make_desc(_make_item(cached_action))

        fresh_action = _make_action(widget_id="btn_ok", bounds=None)
        fresh_desc = _make_desc(_make_item(fresh_action))

        _update_cached_bounds(cached_desc, fresh_desc)  # should not raise

    def test_both_descs_empty_items(self):
        """R3-1-S7 variant: empty items lists on both sides, no crash."""
        cached_desc = _make_desc()
        fresh_desc = _make_desc()

        _update_cached_bounds(cached_desc, fresh_desc)  # should not raise

    def test_fresh_empty_cached_populated(self):
        """R3-1-S7 variant: fresh has no items, cached stays unchanged."""
        cached_action = _make_action(widget_id="btn_ok", bounds=[[10, 20], [30, 40]])
        cached_desc = _make_desc(_make_item(cached_action))
        fresh_desc = _make_desc()

        _update_cached_bounds(cached_desc, fresh_desc)

        assert cached_action.target_view["bounds"] == [[10, 20], [30, 40]]


# -- R3-1-S8: Mixed items ----------------------------------------------------


class TestS8MixedItems:
    """R3-1-S8: mixed items (one with widget_id, one without) update independently."""

    def test_widget_id_updates_proximity_too_far_unchanged(self):
        """R3-1-S8: widget_id match updates, proximity fails when too far."""
        cached_with_id = _make_action(
            widget_id="input_name", bounds=[[50, 100], [200, 150]]
        )
        # center = ((50+200)//2, (300+350)//2) = (125, 325)
        cached_no_id = _make_action(widget_id=None, bounds=[[50, 300], [200, 350]])
        cached_desc = _make_desc(_make_item(cached_with_id), _make_item(cached_no_id))

        fresh_with_id = _make_action(
            widget_id="input_name", bounds=[[50, 200], [200, 250]]
        )
        # fresh center = ((50+200)//2, (400+450)//2) = (125, 425) — diff_y=100 > 50
        fresh_no_id = _make_action(widget_id=None, bounds=[[50, 400], [200, 450]])
        fresh_desc = _make_desc(_make_item(fresh_with_id), _make_item(fresh_no_id))

        _update_cached_bounds(cached_desc, fresh_desc)

        assert cached_with_id.target_view["bounds"] == [[50, 200], [200, 250]]
        assert cached_no_id.target_view["bounds"] == [
            [50, 300],
            [200, 350],
        ]  # unchanged

    def test_both_paths_update_when_within_threshold(self):
        """R3-1-S8: both widget_id and proximity paths update when conditions are met."""
        cached_with_id = _make_action(
            widget_id="btn_submit", bounds=[[100, 500], [300, 550]]
        )
        # center = ((100+300)//2, (600+700)//2) = (200, 650)
        cached_no_id = _make_action(widget_id=None, bounds=[[100, 600], [300, 700]])
        cached_desc = _make_desc(_make_item(cached_with_id), _make_item(cached_no_id))

        fresh_with_id = _make_action(
            widget_id="btn_submit", bounds=[[100, 550], [300, 600]]
        )
        # fresh center = ((100+300)//2, (630+730)//2) = (200, 680) — diff 30 < 50
        fresh_no_id = _make_action(widget_id=None, bounds=[[100, 630], [300, 730]])
        fresh_desc = _make_desc(_make_item(fresh_with_id), _make_item(fresh_no_id))

        _update_cached_bounds(cached_desc, fresh_desc)

        assert cached_with_id.target_view["bounds"] == [[100, 550], [300, 600]]
        assert cached_no_id.target_view["bounds"] == [[100, 630], [300, 730]]


# -- R3-1-S9: Bounds identical -----------------------------------------------


class TestS9BoundsIdentical:
    """R3-1-S9: identical bounds between cached and fresh — no mutation."""

    def test_no_mutation_when_bounds_identical_widget_id(self):
        """R3-1-S9: widget_id match with identical bounds — no replacement."""
        original_bounds = [[100, 200], [300, 400]]
        cached_action = _make_action(widget_id="btn_ok", bounds=original_bounds)
        cached_desc = _make_desc(_make_item(cached_action))

        fresh_action = _make_action(widget_id="btn_ok", bounds=[[100, 200], [300, 400]])
        fresh_desc = _make_desc(_make_item(fresh_action))

        _update_cached_bounds(cached_desc, fresh_desc)

        assert cached_action.target_view["bounds"] is original_bounds

    def test_no_mutation_when_bounds_identical_proximity(self):
        """R3-1-S9: proximity match with identical bounds — no replacement."""
        original_bounds = [[100, 200], [300, 400]]
        cached_action = _make_action(widget_id=None, bounds=original_bounds)
        cached_desc = _make_desc(_make_item(cached_action))

        fresh_action = _make_action(widget_id=None, bounds=[[100, 200], [300, 400]])
        fresh_desc = _make_desc(_make_item(fresh_action))

        _update_cached_bounds(cached_desc, fresh_desc)

        assert cached_action.target_view["bounds"] is original_bounds


# -- R3-1-S10: Multiple actions per item --------------------------------------


class TestS10MultipleActionsPerItem:
    """R3-1-S10: multiple actions per item — all updated independently."""

    def test_three_actions_per_item_all_updated(self):
        """R3-1-S10: item with 3 actions, each different widget_ids."""
        a1 = _make_action(widget_id="w1", bounds=[[0, 0], [100, 100]])
        a2 = _make_action(widget_id="w2", bounds=[[200, 200], [300, 300]])
        a3 = _make_action(widget_id="w3", bounds=[[400, 400], [500, 500]])
        cached_desc = _make_desc(_make_item(a1, a2, a3))

        f1 = _make_action(widget_id="w1", bounds=[[0, 50], [100, 150]])
        f2 = _make_action(widget_id="w2", bounds=[[200, 250], [300, 350]])
        f3 = _make_action(widget_id="w3", bounds=[[400, 450], [500, 550]])
        fresh_desc = _make_desc(_make_item(f1, f2, f3))

        _update_cached_bounds(cached_desc, fresh_desc)

        assert a1.target_view["bounds"] == [[0, 50], [100, 150]]
        assert a2.target_view["bounds"] == [[200, 250], [300, 350]]
        assert a3.target_view["bounds"] == [[400, 450], [500, 550]]

    def test_multiple_items_multiple_actions(self):
        """R3-1-S10 variant: 2 items with 2 actions each — all independently updated."""
        a1 = _make_action(widget_id="w1", bounds=[[0, 0], [100, 100]])
        # center = ((200+300)//2, (200+300)//2) = (250, 250)
        a2 = _make_action(widget_id=None, bounds=[[200, 200], [300, 300]])
        a3 = _make_action(widget_id="w2", bounds=[[400, 400], [500, 500]])
        cached_desc = _make_desc(_make_item(a1, a2), _make_item(a3))

        f1 = _make_action(widget_id="w1", bounds=[[0, 50], [100, 150]])
        # fresh center = ((200+300)//2, (220+320)//2) = (250, 270), diff=20 < 50
        f2 = _make_action(widget_id=None, bounds=[[200, 220], [300, 320]])
        f3 = _make_action(widget_id="w2", bounds=[[400, 450], [500, 550]])
        fresh_desc = _make_desc(_make_item(f1, f2), _make_item(f3))

        _update_cached_bounds(cached_desc, fresh_desc)

        assert a1.target_view["bounds"] == [[0, 50], [100, 150]]
        assert a2.target_view["bounds"] == [[200, 220], [300, 320]]
        assert a3.target_view["bounds"] == [[400, 450], [500, 550]]


# -- R3-1-S11: Proximity threshold boundary (exactly 50px) -------------------


class TestS11ProximityThresholdBoundary:
    """R3-1-S11: centers exactly 50px apart — NOT matched (strict <)."""

    def test_exactly_50px_x_not_matched(self):
        """R3-1-S11: 50px X diff is NOT < 50, so no match."""
        # Cached center: (200, 300)
        cached_action = _make_action(widget_id=None, bounds=[[100, 200], [300, 400]])
        original_bounds = cached_action.target_view["bounds"]
        cached_desc = _make_desc(_make_item(cached_action))

        # Fresh center: (250, 300) — X diff = 50, exactly at threshold
        fresh_action = _make_action(widget_id=None, bounds=[[150, 200], [350, 400]])
        fresh_desc = _make_desc(_make_item(fresh_action))

        _update_cached_bounds(cached_desc, fresh_desc)

        assert cached_action.target_view["bounds"] is original_bounds

    def test_exactly_50px_y_not_matched(self):
        """R3-1-S11: 50px Y diff is NOT < 50, so no match."""
        # Cached center: (200, 300)
        cached_action = _make_action(widget_id=None, bounds=[[100, 200], [300, 400]])
        original_bounds = cached_action.target_view["bounds"]
        cached_desc = _make_desc(_make_item(cached_action))

        # Fresh center: (200, 350) — Y diff = 50, exactly at threshold
        fresh_action = _make_action(widget_id=None, bounds=[[100, 250], [300, 450]])
        fresh_desc = _make_desc(_make_item(fresh_action))

        _update_cached_bounds(cached_desc, fresh_desc)

        assert cached_action.target_view["bounds"] is original_bounds


# -- R3-1-S12: Proximity threshold just within (49px) -------------------------


class TestS12ProximityJustWithin:
    """R3-1-S12: centers 49px apart — matched and updated."""

    def test_49px_x_diff_matched(self):
        """R3-1-S12: 49px X diff IS < 50, so match occurs."""
        # Cached center: (200, 300)
        cached_action = _make_action(widget_id=None, bounds=[[100, 200], [300, 400]])
        cached_desc = _make_desc(_make_item(cached_action))

        # Fresh center: (249, 300) — X diff = 49 < 50
        fresh_action = _make_action(widget_id=None, bounds=[[149, 200], [349, 400]])
        fresh_desc = _make_desc(_make_item(fresh_action))

        _update_cached_bounds(cached_desc, fresh_desc)

        assert cached_action.target_view["bounds"] == [[149, 200], [349, 400]]

    def test_49px_y_diff_matched(self):
        """R3-1-S12: 49px Y diff IS < 50, so match occurs."""
        # Cached center: (200, 300)
        cached_action = _make_action(widget_id=None, bounds=[[100, 200], [300, 400]])
        cached_desc = _make_desc(_make_item(cached_action))

        # Fresh center: (200, 349) — Y diff = 49 < 50
        fresh_action = _make_action(widget_id=None, bounds=[[100, 249], [300, 449]])
        fresh_desc = _make_desc(_make_item(fresh_action))

        _update_cached_bounds(cached_desc, fresh_desc)

        assert cached_action.target_view["bounds"] == [[100, 249], [300, 449]]


# -- R3-1-S13: Integration — parse_ui_node reuses cached desc ----------------


class TestS13ParseUiNodeIntegration:
    """R3-1-S13: parse_ui_node reuses cached desc on same hash, no crash."""

    def test_parse_ui_node_cached_reuse_no_crash(self):
        """R3-1-S13: when screen_hash == previous_hash, _update_cached_bounds
        is called and does not crash — parse_ui_node returns valid data."""
        from rv_agent.agent.nodes.parse_node import parse_ui_node

        # Build mock agent
        agent = MagicMock()
        agent.config.package_name = "br.unb.cic.cryptoapp"
        agent.config.error_detection_enabled = False

        # Build cached screen desc with nested bounds
        cached_action = _make_action(
            widget_id="btn_ok", bounds=[[100, 200], [300, 400]]
        )
        cached_item = _make_item(cached_action)
        cached_screen_desc = _make_desc(cached_item)
        agent._cached_screen_desc = cached_screen_desc

        # Build fresh parse result — same hash triggers cache reuse
        fresh_action = _make_action(widget_id="btn_ok", bounds=[[100, 250], [300, 450]])
        fresh_item = _make_item(fresh_action)
        fresh_screen_desc = _make_desc(fresh_item)

        screen_hash = "abc123"
        agent.screen_processor.parse_current_screen.return_value = {
            "screen_hash": screen_hash,
            "activity": ".messagedigest.MessageDigestActivity",
            "screen_description": fresh_screen_desc,
            "ui_elements_text": "Button: OK (100, 200)",
            "is_external": False,
            "external_navigation_count": 0,
            "ui_xml": "<xml>...</xml>",
        }

        # State: previous hash == current hash -> triggers cached reuse
        state = {
            "iteration": 2,
            "previous_screen_hash": screen_hash,
            "external_navigation_count": 0,
        }

        result = parse_ui_node(agent, state)

        # Should not crash and should return the cached desc with updated bounds
        assert result["current_screen_hash"] == screen_hash
        assert result["screen_description"] is cached_screen_desc
        # Bounds should be updated from fresh parse
        assert cached_action.target_view["bounds"] == [[100, 250], [300, 450]]

    def test_parse_ui_node_new_hash_creates_cache(self):
        """R3-1-S13 variant: new screen hash creates cache (no _update_cached_bounds)."""
        from rv_agent.agent.nodes.parse_node import parse_ui_node

        agent = MagicMock()
        agent.config.package_name = "br.unb.cic.cryptoapp"
        agent.config.error_detection_enabled = False
        agent._cached_screen_desc = None  # no cache yet

        fresh_action = _make_action(widget_id="btn_ok", bounds=[[100, 200], [300, 400]])
        fresh_screen_desc = _make_desc(_make_item(fresh_action))

        agent.screen_processor.parse_current_screen.return_value = {
            "screen_hash": "new_hash",
            "activity": ".MainActivity",
            "screen_description": fresh_screen_desc,
            "ui_elements_text": "Button: OK (100, 200)",
            "is_external": False,
            "external_navigation_count": 0,
            "ui_xml": "<xml>...</xml>",
        }

        state = {
            "iteration": 0,
            "previous_screen_hash": None,
            "external_navigation_count": 0,
        }

        result = parse_ui_node(agent, state)

        assert result["current_screen_hash"] == "new_hash"
        assert result["screen_description"] is fresh_screen_desc
        # Cache should now be set
        assert agent._cached_screen_desc is fresh_screen_desc
