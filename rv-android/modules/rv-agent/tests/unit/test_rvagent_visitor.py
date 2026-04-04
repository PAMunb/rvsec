"""
Unit tests for RVAgentVisitor.

Tests MOP marker enrichment, widget matching, and WTG integration
using real static analysis data from fixtures.
"""

from pathlib import Path

import pytest
from rv_agent.ui.rvagent_visitor import RVAgentVisitor
from rv_android_core.domain.static import StaticAnalysisData
from rv_screen_parser.constants import ScreenParserType
from rv_screen_parser.parser.screen.parser_factory import ParserFactory
from rv_screen_parser.parser.screen.uiautomator.uiautomator_parser import (
    UIAutomator2Parser,
)
from rv_static_analysis.parser.static.static_analysis_parser import parse_file

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def fixtures_path():
    """Path to test fixtures."""
    return Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def static_analysis_path(fixtures_path):
    """Path to static analysis fixtures."""
    return fixtures_path / "static_analysis" / "cryptoapp"


@pytest.fixture
def screenshots_path(fixtures_path):
    """Path to screenshot fixtures."""
    return fixtures_path / "screenshots" / "cryptoapp"


@pytest.fixture
def static_data(static_analysis_path) -> StaticAnalysisData:
    """Load real static analysis data from unified JSON."""
    json_file = str(static_analysis_path / "cryptoapp.apk.json")
    return parse_file(json_file, "br.unb.cic.cryptoapp")


@pytest.fixture
def main_activity_xml(screenshots_path):
    """Load MainActivity UI dump."""
    xml_path = screenshots_path / "001.uiautomator.xml"
    return xml_path.read_text()


@pytest.fixture
def cipher_activity_xml(screenshots_path):
    """Load CipherActivity UI dump (003.xml)."""
    xml_path = screenshots_path / "003.uiautomator.xml"
    return xml_path.read_text()


# =============================================================================
# Test: Initialization
# =============================================================================


class TestRVAgentVisitorInit:
    """Test RVAgentVisitor initialization."""

    def test_init_with_static_data(self, static_data):
        """Visitor initializes with static analysis data."""
        visitor = RVAgentVisitor(static_data, "br.unb.cic.cryptoapp.MainActivity")

        assert visitor.static_info is static_data
        assert visitor.wtg is not None
        assert visitor.window is not None
        assert "MainActivity" in visitor.window.name

    def test_init_without_static_data(self):
        """Visitor initializes gracefully without static data."""
        visitor = RVAgentVisitor(None, "com.example.MainActivity")

        assert visitor.static_info is None
        assert visitor.wtg is None
        assert visitor.window is None

    def test_init_with_partial_activity_match(self, static_data):
        """Visitor finds window with partial activity match."""
        # Use just the class name without full package
        visitor = RVAgentVisitor(static_data, "MainActivity")

        # Should still find the window via partial match
        assert visitor.window is not None

    def test_mop_stats_initialized(self, static_data):
        """MOP stats are initialized to zero."""
        visitor = RVAgentVisitor(static_data, "br.unb.cic.cryptoapp.MainActivity")

        stats = visitor.get_mop_statistics()
        assert stats["total_actions"] == 0
        assert stats["mop_enriched"] == 0
        assert stats["direct_mop"] == 0
        assert stats["transitive_mop"] == 0


# =============================================================================
# Test: Window Matching
# =============================================================================


class TestWindowMatching:
    """Test activity to static window matching."""

    def test_exact_match_main_activity(self, static_data):
        """Exact match on MainActivity."""
        visitor = RVAgentVisitor(static_data, "br.unb.cic.cryptoapp.MainActivity")

        assert visitor.window is not None
        assert "MainActivity" in visitor.window.name

    def test_exact_match_cipher_activity(self, static_data):
        """Exact match on CipherActivity."""
        visitor = RVAgentVisitor(
            static_data, "br.unb.cic.cryptoapp.cipher.CipherActivity"
        )

        assert visitor.window is not None
        assert "CipherActivity" in visitor.window.name

    def test_exact_match_message_digest_activity(self, static_data):
        """Exact match on MessageDigestActivity."""
        visitor = RVAgentVisitor(
            static_data, "br.unb.cic.cryptoapp.messagedigest.MessageDigestActivity"
        )

        assert visitor.window is not None
        assert "MessageDigestActivity" in visitor.window.name

    def test_no_match_unknown_activity(self, static_data):
        """No match for unknown activity."""
        visitor = RVAgentVisitor(static_data, "com.unknown.UnknownActivity")

        assert visitor.window is None


# =============================================================================
# Test: Widget Matching
# =============================================================================


class TestWidgetMatching:
    """Test runtime node to static widget matching."""

    def test_static_window_has_widgets(self, static_data):
        """Static window contains expected widgets."""
        visitor = RVAgentVisitor(static_data, "br.unb.cic.cryptoapp.MainActivity")

        assert visitor.window is not None
        assert len(visitor.window.widgets) > 0

        # Check for expected button widgets by name
        button_names = [w.name for w in visitor.window.widgets.values()]
        assert "buttonMessageDigest" in button_names
        assert "buttonCipher" in button_names
        assert "buttonGenerated" in button_names

    def test_get_widget_by_name(self, static_data):
        """Window.get_widget_by_name finds widgets correctly."""
        visitor = RVAgentVisitor(static_data, "br.unb.cic.cryptoapp.MainActivity")

        widget = visitor.window.get_widget_by_name("buttonMessageDigest")

        assert widget is not None
        assert widget.name == "buttonMessageDigest"

    def test_widget_has_events(self, static_data):
        """Widgets have associated events."""
        visitor = RVAgentVisitor(static_data, "br.unb.cic.cryptoapp.MainActivity")

        widget = visitor.window.get_widget_by_name("buttonMessageDigest")

        assert widget is not None
        # Widgets should have events defined from GESDA
        assert hasattr(widget, "events") or hasattr(widget, "listeners")

    def test_no_match_returns_none(self, static_data):
        """No match returns None and updates stats."""
        visitor = RVAgentVisitor(static_data, "br.unb.cic.cryptoapp.MainActivity")

        node_data = {
            "resource-id": "br.unb.cic.cryptoapp:id/nonexistent_widget",
            "text": "",
            "bounds": "[(0, 0), (100, 100)]",
        }

        widget = visitor.find_matching_widget(node_data)

        assert widget is None
        assert visitor.mop_stats["widgets_not_matched"] == 1

    def test_cache_key_generation(self, static_data):
        """Cache key is generated correctly."""
        visitor = RVAgentVisitor(static_data, "br.unb.cic.cryptoapp.MainActivity")

        node_data = {
            "resource-id": "br.unb.cic.cryptoapp:id/buttonCipher",
            "text": "CIPHER",
            "bounds": "[(0, 336), (1080, 462)]",
        }

        cache_key = visitor._generate_cache_key(node_data)

        assert "buttonCipher" in cache_key
        assert "CIPHER" in cache_key


# =============================================================================
# Test: MOP Enrichment
# =============================================================================


class TestMOPEnrichment:
    """Test MOP marker enrichment on actions."""

    def test_methods_have_reaches_mop_flags(self, static_data):
        """Methods in static_data have reaches_mop flags from reachability section."""
        # Verify methods are loaded with MOP flags
        assert static_data.classes is not None
        assert len(static_data.classes.methods) > 0

        # Find methods that reach MOP
        mop_methods = [m for m in static_data.classes.methods.values() if m.reaches_mop]
        assert len(mop_methods) > 0, "Expected some methods to reach MOP"

        # Find methods that directly reach MOP
        direct_mop_methods = [
            m for m in static_data.classes.methods.values() if m.directly_reaches_mop
        ]
        assert (
            len(direct_mop_methods) > 0
        ), "Expected some methods to directly reach MOP"

    def test_main_activity_lifecycle_reaches_mop(self, static_data):
        """MainActivity lifecycle methods reach MOP transitively."""
        # onCreate reaches MOP through activity lifecycle chains
        sig = "<br.unb.cic.cryptoapp.MainActivity: void onCreate(android.os.Bundle)>"
        method = static_data.classes.methods.get(sig)

        assert method is not None, f"Method {sig} not found"
        assert method.reaches_mop is True

    def test_main_activity_navigation_does_not_reach_mop(self, static_data):
        """MainActivity button callbacks are navigation-only (no MOP)."""
        # showScreenMessageDigest just calls startActivity() — doesn't reach JCA
        sig = "<br.unb.cic.cryptoapp.MainActivity: void showScreenMessageDigest(android.view.View)>"
        method = static_data.classes.methods.get(sig)

        assert method is not None, f"Method {sig} not found"
        assert method.reaches_mop is False

    def test_cipher_activity_callback_reaches_mop(self, static_data):
        """CipherActivity onClick callback should reach MOP."""
        sig = "<br.unb.cic.cryptoapp.cipher.CipherActivity$1: void onClick(android.view.View)>"
        method = static_data.classes.methods.get(sig)

        assert method is not None, f"Method {sig} not found"
        assert method.reaches_mop is True

    def test_hash_method_directly_reaches_mop(self, static_data):
        """MessageDigestUtil.hash directly reaches MOP (calls MessageDigest APIs)."""
        sig = "<br.unb.cic.cryptoapp.messagedigest.MessageDigestUtil: java.lang.String hash(byte[],java.lang.String)>"
        method = static_data.classes.methods.get(sig)

        assert method is not None, f"Method {sig} not found"
        assert method.reaches_mop is True
        assert method.directly_reaches_mop is True

    def test_mop_stats_initialized_to_zero(self, static_data):
        """MOP stats start at zero."""
        visitor = RVAgentVisitor(static_data, "br.unb.cic.cryptoapp.MainActivity")

        stats = visitor.get_mop_statistics()
        assert stats["total_actions"] == 0
        assert stats["mop_enriched"] == 0
        assert stats["direct_mop"] == 0
        assert stats["transitive_mop"] == 0

    def test_main_activity_has_no_mop_enrichment(self, static_data, main_activity_xml):
        """MainActivity buttons are navigation-only — no MOP enrichment."""
        parser = UIAutomator2Parser(visitor_class=RVAgentVisitor)

        screen_desc = parser.parse(
            main_activity_xml,
            static_data=static_data,
            activity="br.unb.cic.cryptoapp.MainActivity",
        )

        # MainActivity button handlers (showScreenCipher, showScreenMessageDigest, etc.)
        # call startActivity() which doesn't create CG edges to target activities.
        # No actions should have MOP markers on this screen.
        for item in screen_desc.items:
            for action in item.actions:
                assert action.reaches_mop is False
                assert action.directly_reaches_mop is False

    def test_no_mop_without_static_data(self, main_activity_xml):
        """Without static data, no MOP enrichment occurs."""
        parser = UIAutomator2Parser(visitor_class=RVAgentVisitor)

        screen_desc = parser.parse(
            main_activity_xml,
            static_data=None,
            activity="br.unb.cic.cryptoapp.MainActivity",
        )

        # All actions should have reaches_mop=False
        for item in screen_desc.items:
            for action in item.actions:
                assert action.reaches_mop is False
                assert action.directly_reaches_mop is False


# =============================================================================
# Test: WTG Transitions
# =============================================================================


class TestWTGTransitions:
    """Test WTG transition retrieval."""

    def test_get_transitions_from_main_activity(self, static_data):
        """Get available transitions from MainActivity."""
        visitor = RVAgentVisitor(static_data, "br.unb.cic.cryptoapp.MainActivity")

        # WTG should have transitions from MainActivity
        transitions = visitor.get_wtg_transitions()

        # MainActivity has buttons that navigate to other activities
        # The WTG should reflect these
        assert isinstance(transitions, list)

    def test_no_transitions_without_wtg(self):
        """No transitions when WTG is not available."""
        visitor = RVAgentVisitor(None, "com.example.MainActivity")

        transitions = visitor.get_wtg_transitions()

        assert transitions == []

    def test_no_transitions_without_window(self, static_data):
        """No transitions when static_window is None."""
        visitor = RVAgentVisitor(static_data, "com.unknown.UnknownActivity")

        transitions = visitor.get_wtg_transitions()

        assert transitions == []


# =============================================================================
# Test: Integration with Parser
# =============================================================================


class TestParserIntegration:
    """Test RVAgentVisitor integration with UIAutomator2Parser."""

    def test_parse_main_activity_screen(self, static_data, main_activity_xml):
        """Parse MainActivity screen — navigation buttons have no MOP markers."""
        parser = UIAutomator2Parser(visitor_class=RVAgentVisitor)

        screen_desc = parser.parse(
            main_activity_xml,
            static_data=static_data,
            activity="br.unb.cic.cryptoapp.MainActivity",
        )

        assert screen_desc is not None
        assert len(screen_desc.items) > 0

        # MainActivity buttons navigate via startActivity() — no CG edge to
        # target activities, so no MOP enrichment on this screen.
        for item in screen_desc.items:
            for action in item.actions:
                assert action.reaches_mop is False
                assert action.directly_reaches_mop is False

    def test_parse_without_static_data(self, main_activity_xml):
        """Parse screen without static data (graceful degradation)."""
        parser = UIAutomator2Parser(visitor_class=RVAgentVisitor)

        screen_desc = parser.parse(
            main_activity_xml,
            static_data=None,
            activity="br.unb.cic.cryptoapp.MainActivity",
        )

        assert screen_desc is not None
        assert len(screen_desc.items) > 0

        # No MOP markers without static data
        for item in screen_desc.items:
            for action in item.actions:
                assert action.reaches_mop is False
                assert action.directly_reaches_mop is False

    def test_parse_using_factory(self, static_data, main_activity_xml):
        """Parse using ParserFactory with custom visitor."""
        parser = ParserFactory.create(
            ScreenParserType.UIAUTOMATOR, visitor_class=RVAgentVisitor
        )

        screen_desc = parser.parse(
            main_activity_xml,
            static_data=static_data,
            activity="br.unb.cic.cryptoapp.MainActivity",
        )

        assert screen_desc is not None
        assert len(screen_desc.items) > 0


# =============================================================================
# Test: Static Data Validation
# =============================================================================


class TestStaticDataValidation:
    """Validate that static analysis data is loaded correctly."""

    def test_classes_loaded(self, static_data):
        """Classes are loaded from unified JSON."""
        assert static_data.classes is not None
        assert len(static_data.classes.methods) > 0

    def test_windows_loaded(self, static_data):
        """Windows are loaded from unified JSON."""
        assert static_data.windows is not None
        assert len(static_data.windows.windows) > 0

    def test_wtg_loaded(self, static_data):
        """WTG is loaded from unified JSON."""
        assert static_data.wtg is not None

    def test_main_activity_has_widgets(self, static_data):
        """MainActivity ACTIVITY window has expected button widgets."""
        main_window = None
        for window in static_data.windows.windows:
            # Match the ACTIVITY window, not the OptionsMenu subwindow
            if window.name == "br.unb.cic.cryptoapp.MainActivity":
                main_window = window
                break

        assert main_window is not None
        assert len(main_window.widgets) > 0

        # Check for expected buttons
        widget_names = [w.name for w in main_window.widgets.values()]
        assert "buttonMessageDigest" in widget_names
        assert "buttonCipher" in widget_names
        assert "buttonGenerated" in widget_names

    def test_methods_have_mop_flags(self, static_data):
        """Methods have reaches_mop flags set."""
        # Find a method we know reaches MOP
        hash_signature = "<br.unb.cic.cryptoapp.messagedigest.MessageDigestUtil: java.lang.String hash(byte[],java.lang.String)>"

        method = static_data.classes.methods.get(hash_signature)

        if method:
            # This method directly calls MessageDigest APIs
            assert method.reaches_mop is True
            assert method.directly_reaches_mop is True
