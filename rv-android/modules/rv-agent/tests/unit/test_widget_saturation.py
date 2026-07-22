"""Unit tests for widget-aware saturation thresholds (D8 Bug #4).

Verify that multi-value widgets (EditText, Spinner, SeekBar) use a higher
saturation threshold than single-action widgets (Button), preventing premature
saturation on screens with diverse interactive elements.
"""

import pytest
from rv_agent.domain.screen_node import (
    DEFAULT_SATURATION_THRESHOLD,
    MULTI_VALUE_WIDGETS,
    ScreenNode,
)


class TestEffectiveThreshold:
    """_effective_threshold returns correct threshold per widget type."""

    def test_edittext_returns_multi_value_threshold(self):
        node = ScreenNode(screen_hash="test", activity="test")
        sig = ((300, 500), "set_text")
        node.action_widget_classes[sig] = "android.widget.EditText"
        assert node._effective_threshold(sig) == node.multi_value_threshold

    def test_spinner_returns_multi_value_threshold(self):
        node = ScreenNode(screen_hash="test", activity="test")
        sig = ((400, 600), "click")
        node.action_widget_classes[sig] = "android.widget.Spinner"
        assert node._effective_threshold(sig) == node.multi_value_threshold

    def test_seekbar_returns_multi_value_threshold(self):
        node = ScreenNode(screen_hash="test", activity="test")
        sig = ((500, 700), "click")
        node.action_widget_classes[sig] = "android.widget.SeekBar"
        assert node._effective_threshold(sig) == node.multi_value_threshold

    def test_appcompat_edittext_returns_multi_value_threshold(self):
        node = ScreenNode(screen_hash="test", activity="test")
        sig = ((300, 500), "set_text")
        node.action_widget_classes[sig] = "androidx.appcompat.widget.AppCompatEditText"
        assert node._effective_threshold(sig) == node.multi_value_threshold

    def test_button_returns_default_threshold(self):
        node = ScreenNode(screen_hash="test", activity="test")
        sig = ((200, 400), "click")
        node.action_widget_classes[sig] = "android.widget.Button"
        assert node._effective_threshold(sig) == DEFAULT_SATURATION_THRESHOLD

    def test_checkbox_returns_default_threshold(self):
        node = ScreenNode(screen_hash="test", activity="test")
        sig = ((200, 400), "click")
        node.action_widget_classes[sig] = "android.widget.CheckBox"
        assert node._effective_threshold(sig) == DEFAULT_SATURATION_THRESHOLD

    def test_unknown_widget_returns_default_threshold(self):
        node = ScreenNode(screen_hash="test", activity="test")
        sig = ((100, 200), "click")
        # No widget class recorded
        assert node._effective_threshold(sig) == DEFAULT_SATURATION_THRESHOLD

    def test_empty_widget_class_returns_default_threshold(self):
        node = ScreenNode(screen_hash="test", activity="test")
        sig = ((100, 200), "click")
        node.action_widget_classes[sig] = ""
        assert node._effective_threshold(sig) == DEFAULT_SATURATION_THRESHOLD

    def test_custom_multi_value_threshold(self):
        """Configurable threshold from RVAgentConfig."""
        node = ScreenNode(screen_hash="test", activity="test", multi_value_threshold=6)
        sig = ((300, 500), "set_text")
        node.action_widget_classes[sig] = "android.widget.EditText"
        assert node._effective_threshold(sig) == 6


class TestRecordActionWidgetClass:
    """record_action stores widget class on first recording."""

    def test_stores_widget_class_on_first_call(self):
        node = ScreenNode(screen_hash="test", activity="test")
        sig = ((300, 500), "set_text")
        node.record_action(sig, widget_class="android.widget.EditText")
        assert node.action_widget_classes[sig] == "android.widget.EditText"

    def test_does_not_overwrite_on_subsequent_calls(self):
        node = ScreenNode(screen_hash="test", activity="test")
        sig = ((300, 500), "set_text")
        node.record_action(sig, widget_class="android.widget.EditText")
        node.record_action(sig, widget_class="android.widget.Spinner")
        assert node.action_widget_classes[sig] == "android.widget.EditText"

    def test_empty_widget_class_not_stored(self):
        node = ScreenNode(screen_hash="test", activity="test")
        sig = ((300, 500), "click")
        node.record_action(sig, widget_class="")
        assert sig not in node.action_widget_classes

    def test_no_widget_class_not_stored(self):
        node = ScreenNode(screen_hash="test", activity="test")
        sig = ((300, 500), "click")
        node.record_action(sig)
        assert sig not in node.action_widget_classes


class TestWidgetAwareSaturationRate:
    """get_saturation_rate uses per-widget thresholds."""

    def test_mixed_widgets_partial_saturation(self):
        """EditText (threshold=4) + Button (threshold=2), both executed 2x.

        Button is saturated (2 >= 2), EditText is NOT (2 < 4).
        Saturation = 1 saturated / 2 total = 0.5.
        """
        node = ScreenNode(screen_hash="test", activity="test")
        node.total_actions = 2

        button_sig = ((200, 400), "click")
        edittext_sig = ((300, 500), "set_text")

        # Record both actions twice with widget class
        node.record_action(button_sig, widget_class="android.widget.Button")
        node.record_action(button_sig, widget_class="android.widget.Button")
        node.record_action(edittext_sig, widget_class="android.widget.EditText")
        node.record_action(edittext_sig, widget_class="android.widget.EditText")

        rate = node.get_saturation_rate()
        assert rate == pytest.approx(0.5)

    def test_cryptoapp_scenario(self):
        """CryptoApp: Spinner + EditText + Button, each executed 2x.

        With widget-aware thresholds (default multi_value=4):
        - Button (threshold=2): 2 >= 2 -> saturated
        - Spinner (threshold=4): 2 < 4 -> NOT saturated
        - EditText (threshold=4): 2 < 4 -> NOT saturated
        Saturation = 1/3 = 0.333
        """
        node = ScreenNode(screen_hash="test", activity="test")
        node.total_actions = 3

        spinner_sig = ((100, 300), "click")
        edittext_sig = ((300, 500), "set_text")
        button_sig = ((500, 700), "click")

        # Execute each twice
        for sig, cls in [
            (spinner_sig, "android.widget.Spinner"),
            (edittext_sig, "android.widget.EditText"),
            (button_sig, "android.widget.Button"),
        ]:
            node.record_action(sig, widget_class=cls)
            node.record_action(sig, widget_class=cls)

        rate = node.get_saturation_rate()
        assert rate == pytest.approx(1.0 / 3.0)

    def test_all_widgets_fully_saturated(self):
        """All widgets executed enough times -> 1.0."""
        node = ScreenNode(screen_hash="test", activity="test")
        node.total_actions = 2

        button_sig = ((200, 400), "click")
        edittext_sig = ((300, 500), "set_text")

        # Button: 2x (threshold=2), EditText: 4x (threshold=4)
        node.record_action(button_sig, widget_class="android.widget.Button")
        node.record_action(button_sig, widget_class="android.widget.Button")
        for _ in range(4):
            node.record_action(edittext_sig, widget_class="android.widget.EditText")

        rate = node.get_saturation_rate()
        assert rate == 1.0

    def test_no_widget_class_uses_default_threshold(self):
        """Actions without widget class use DEFAULT_SATURATION_THRESHOLD=2."""
        node = ScreenNode(screen_hash="test", activity="test")
        node.total_actions = 2

        sig1 = ((100, 200), "click")
        sig2 = ((300, 400), "click")

        # Both executed twice, no widget class
        node.record_action(sig1)
        node.record_action(sig1)
        node.record_action(sig2)
        node.record_action(sig2)

        rate = node.get_saturation_rate()
        assert rate == 1.0

    def test_system_actions_excluded_from_saturation(self):
        """System actions (BACK, RESTART) excluded from numerator (D8 Bug #2)."""
        node = ScreenNode(screen_hash="test", activity="test")
        node.total_actions = 2

        real_sig = ((200, 400), "click")
        back_sig = ((0, 0), "back")

        node.record_action(real_sig, widget_class="android.widget.Button")
        node.record_action(real_sig, widget_class="android.widget.Button")
        node.record_action(back_sig)
        node.record_action(back_sig)

        rate = node.get_saturation_rate()
        # Only 1 real action saturated / 2 total = 0.5
        assert rate == pytest.approx(0.5)


class TestIsActionSaturated:
    """is_action_saturated uses per-widget threshold when no explicit threshold."""

    def test_edittext_not_saturated_at_2(self):
        """EditText with 2 executions is NOT saturated (threshold=4)."""
        node = ScreenNode(screen_hash="test", activity="test")
        sig = ((300, 500), "set_text")
        node.action_widget_classes[sig] = "android.widget.EditText"
        node.action_execution_counts[sig] = 2
        assert not node.is_action_saturated(sig)

    def test_edittext_saturated_at_4(self):
        """EditText with 4 executions IS saturated (threshold=4)."""
        node = ScreenNode(screen_hash="test", activity="test")
        sig = ((300, 500), "set_text")
        node.action_widget_classes[sig] = "android.widget.EditText"
        node.action_execution_counts[sig] = 4
        assert node.is_action_saturated(sig)

    def test_button_saturated_at_2(self):
        """Button with 2 executions IS saturated (threshold=2)."""
        node = ScreenNode(screen_hash="test", activity="test")
        sig = ((200, 400), "click")
        node.action_widget_classes[sig] = "android.widget.Button"
        node.action_execution_counts[sig] = 2
        assert node.is_action_saturated(sig)

    def test_explicit_threshold_overrides_widget(self):
        """Explicit threshold parameter overrides per-widget logic."""
        node = ScreenNode(screen_hash="test", activity="test")
        sig = ((300, 500), "set_text")
        node.action_widget_classes[sig] = "android.widget.EditText"
        node.action_execution_counts[sig] = 2
        # Explicit threshold=2 overrides EditText's default of 4
        assert node.is_action_saturated(sig, threshold=2)


class TestMultiValueWidgetsSet:
    """Verify MULTI_VALUE_WIDGETS contains expected widget classes."""

    @pytest.mark.parametrize(
        "widget_class",
        [
            "EditText",
            "TextInputEditText",
            "AppCompatEditText",
            "AutoCompleteTextView",
            "AppCompatAutoCompleteTextView",
            "MultiAutoCompleteTextView",
            "Spinner",
            "AppCompatSpinner",
            "SeekBar",
            "AppCompatSeekBar",
            "RatingBar",
            "AppCompatRatingBar",
            "NumberPicker",
        ],
    )
    def test_widget_in_multi_value_set(self, widget_class):
        assert widget_class in MULTI_VALUE_WIDGETS

    @pytest.mark.parametrize(
        "widget_class",
        ["Button", "ImageButton", "CheckBox", "Switch", "ToggleButton", "TextView"],
    )
    def test_widget_not_in_multi_value_set(self, widget_class):
        assert widget_class not in MULTI_VALUE_WIDGETS
