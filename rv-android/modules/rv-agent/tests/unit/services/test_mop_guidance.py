"""
Unit tests for MOP-specific navigation guidance in NavigationGuidance.

Tests the MOP enrichment of format_for_llm() when StaticAnalysisData is
available, and graceful degradation when it is not. Uses mocks to isolate
NavigationGuidance from TransitionManager and StaticAnalysisData internals.
"""

from unittest.mock import MagicMock

from rv_agent.services.navigation_guidance import (
    NavigationGuidance,
    ExplorationContext,
    MopDescription,
)


def _make_transition_manager(with_static_data=True, mop_methods=None):
    """
    Create a mock TransitionManager with optional StaticAnalysisData.

    Args:
        with_static_data: If True, attach mock StaticAnalysisData with
            classes containing MOP methods.
        mop_methods: Dict mapping method signature to (name, class_name,
            reaches_mop, directly_reaches_mop). If None, a default set
            of MOP methods is used.
    """
    tm = MagicMock()

    if not with_static_data:
        tm.static_data = None
        return tm

    # Build mock static_data with classes
    static_data = MagicMock()

    # Default MOP methods if not provided
    if mop_methods is None:
        mop_methods = {
            "com.example.CryptoHelper.doEncrypt(String)": (
                "doEncrypt",
                "com.example.CryptoHelper",
                True,
                True,
            ),
            "com.example.MainActivity.onClick(View)": (
                "onClick",
                "com.example.MainActivity",
                True,
                False,
            ),
        }

    # Build methods dict with Method-like mocks
    methods_dict = {}
    for sig, (name, class_name, reaches, directly) in mop_methods.items():
        method = MagicMock()
        method.name = name
        method.class_name = class_name
        method.reaches_mop = reaches
        method.directly_reaches_mop = directly
        method.signature = sig
        methods_dict[sig] = method

    static_data.classes.methods = methods_dict
    tm.static_data = static_data

    return tm


def _make_widget_with_events(widget_id, event_signatures):
    """
    Create a mock widget with events that have the given signatures.

    Args:
        widget_id: Widget ID string.
        event_signatures: List of method signature strings for the widget events.
    """
    widget = MagicMock()
    widget.widget_id = widget_id
    events = []
    for sig in event_signatures:
        event = MagicMock()
        event.signature = sig
        events.append(event)
    widget.events = events
    return widget


class TestFormatForLlmWithMopData:
    """Tests for format_for_llm() MOP enrichment when StaticAnalysisData is available."""

    def test_format_for_llm_with_mop_data(self):
        """format_for_llm returns non-empty guidance with MOP descriptions
        when StaticAnalysisData provides MOP method information."""
        tm = _make_transition_manager(with_static_data=True)

        # Set up widget lookup to return a widget with a MOP event
        widget = _make_widget_with_events(
            "widget_123", ["com.example.CryptoHelper.doEncrypt(String)"]
        )
        tm._find_widget_globally.return_value = widget

        guidance = NavigationGuidance(transition_manager=tm)

        context = ExplorationContext(
            has_guidance=True,
            priority_targets=["com.example.EncryptActivity"],
            suggested_actions=[
                {
                    "widget_id": "widget_123",
                    "action_text": "Encrypt",
                    "action_type": "click",
                    "target_activity": "com.example.EncryptActivity",
                }
            ],
            mop_descriptions=[
                MopDescription(
                    element_text="Encrypt",
                    method_name="doEncrypt",
                    class_name="CryptoHelper",
                    directly_reaches=True,
                )
            ],
        )

        result = guidance.format_for_llm(context)

        assert result.startswith("Navigation guidance:")
        assert "Encrypt" in result
        assert "doEncrypt" in result
        assert "directly calls" in result
        assert "monitored operation" in result

    def test_format_for_llm_without_static_data(self):
        """format_for_llm returns empty string when no static data is available
        and context has no guidance."""
        tm = _make_transition_manager(with_static_data=False)
        guidance = NavigationGuidance(transition_manager=tm)

        context = ExplorationContext(has_guidance=False)
        result = guidance.format_for_llm(context)

        assert result == ""

    def test_format_for_llm_with_transitive_mop(self):
        """format_for_llm shows 'reaches' for transitive MOP methods."""
        tm = _make_transition_manager(with_static_data=True)
        guidance = NavigationGuidance(transition_manager=tm)

        context = ExplorationContext(
            has_guidance=True,
            mop_descriptions=[
                MopDescription(
                    element_text="Settings",
                    method_name="onClick",
                    class_name="MainActivity",
                    directly_reaches=False,
                )
            ],
        )

        result = guidance.format_for_llm(context)

        assert "reaches" in result
        assert "directly calls" not in result
        assert "monitored operation" in result
        assert "Settings" in result

    def test_format_for_llm_limits_mop_descriptions_to_3(self):
        """format_for_llm limits MOP descriptions to at most 3 entries."""
        tm = _make_transition_manager(with_static_data=True)
        guidance = NavigationGuidance(transition_manager=tm)

        descriptions = [
            MopDescription(
                element_text=f"Element{i}",
                method_name=f"method{i}",
                class_name=f"Class{i}",
                directly_reaches=True,
            )
            for i in range(5)
        ]

        context = ExplorationContext(has_guidance=True, mop_descriptions=descriptions)

        result = guidance.format_for_llm(context)

        # Only 3 should appear
        assert "Element0" in result
        assert "Element1" in result
        assert "Element2" in result
        assert "Element3" not in result
        assert "Element4" not in result


class TestNavigationGuidanceEnabledState:
    """Tests for is_enabled based on StaticAnalysisData availability."""

    def test_navigation_guidance_enabled_with_static_data(self):
        """is_enabled returns True when TransitionManager (with static data) is provided."""
        tm = _make_transition_manager(with_static_data=True)
        guidance = NavigationGuidance(transition_manager=tm)

        assert guidance.is_enabled is True

    def test_navigation_guidance_disabled_without_static_data(self):
        """is_enabled returns False when TransitionManager is None."""
        guidance = NavigationGuidance(transition_manager=None)

        assert guidance.is_enabled is False

    def test_navigation_guidance_disabled_with_none_transition_manager(self):
        """is_enabled returns False when transition_manager is explicitly None."""
        guidance = NavigationGuidance(transition_manager=None)

        assert guidance.is_enabled is False
        assert guidance.transition_manager is None


class TestCollectMopDescriptions:
    """Tests for _collect_mop_descriptions internal method."""

    def test_collect_mop_descriptions_with_mop_widget(self):
        """_collect_mop_descriptions returns descriptions for widgets with MOP events."""
        tm = _make_transition_manager(with_static_data=True)

        widget = _make_widget_with_events(
            "widget_123", ["com.example.CryptoHelper.doEncrypt(String)"]
        )
        tm._find_widget_globally.return_value = widget

        guidance = NavigationGuidance(transition_manager=tm)

        actions = [
            {
                "widget_id": "widget_123",
                "action_text": "Encrypt",
            }
        ]

        descriptions = guidance._collect_mop_descriptions(actions)

        assert len(descriptions) == 1
        assert descriptions[0].element_text == "Encrypt"
        assert descriptions[0].method_name == "doEncrypt"
        assert descriptions[0].class_name == "CryptoHelper"
        assert descriptions[0].directly_reaches is True

    def test_collect_mop_descriptions_without_static_data(self):
        """_collect_mop_descriptions returns empty list when no static data."""
        tm = _make_transition_manager(with_static_data=False)
        guidance = NavigationGuidance(transition_manager=tm)

        actions = [{"widget_id": "widget_123", "action_text": "Encrypt"}]
        descriptions = guidance._collect_mop_descriptions(actions)

        assert descriptions == []

    def test_collect_mop_descriptions_no_widget_found(self):
        """_collect_mop_descriptions returns empty list when widget not found."""
        tm = _make_transition_manager(with_static_data=True)
        tm._find_widget_globally.return_value = None

        guidance = NavigationGuidance(transition_manager=tm)

        actions = [{"widget_id": "widget_missing", "action_text": "Missing"}]
        descriptions = guidance._collect_mop_descriptions(actions)

        assert descriptions == []

    def test_collect_mop_descriptions_non_mop_method(self):
        """_collect_mop_descriptions skips methods that do not reach MOP."""
        non_mop_methods = {
            "com.example.Utils.formatText(String)": (
                "formatText",
                "com.example.Utils",
                False,
                False,
            ),
        }
        tm = _make_transition_manager(
            with_static_data=True, mop_methods=non_mop_methods
        )

        widget = _make_widget_with_events(
            "widget_456", ["com.example.Utils.formatText(String)"]
        )
        tm._find_widget_globally.return_value = widget

        guidance = NavigationGuidance(transition_manager=tm)

        actions = [{"widget_id": "widget_456", "action_text": "Format"}]
        descriptions = guidance._collect_mop_descriptions(actions)

        assert descriptions == []
