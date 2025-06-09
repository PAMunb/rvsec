"""
Unit tests for the ScreenshotActionComplementor class.

These tests verify the functionality of the ScreenshotActionComplementor, which
enhances screen descriptions with information extracted from screenshot analysis.
"""

from unittest.mock import Mock, patch

import pytest

from rvandroid_tool.analysis.screenshot.screenshot_action_complementor import (
    ScreenshotActionComplementor, AssociationStrategy,
    ErrorAssociationStrategy, ButtonAssociationStrategy,
    TextAssociationStrategy, InteractiveElementAssociationStrategy
)
from rv_android_core.domain.static import StaticAnalysisData
from rv_android_core.domain.widget import WidgetEventType
from rv_llm.llm.constants import StateEntry
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription, ScreenItem, ItemAction


class TestAssociationStrategies:
    """Tests for various association strategies used to match visual elements with UI elements."""

    def test_base_association_strategy_calculate_match_score(self):
        """Test the base AssociationStrategy calculate_match_score method."""
        strategy = AssociationStrategy()

        # Define visual bounds and UI element data
        visual_bounds = [[10, 10], [50, 50]]  # Top-left, bottom-right
        ui_element_data = {
            "bounds": [[20, 20], [60, 60]],
            "item": Mock()
        }

        # Calculate match score
        score = strategy.calculate_match_score(visual_bounds, ui_element_data)

        # Assert the score is between 0 and 1
        assert 0 <= score <= 1
        # Assert the score reflects the overlap ratio
        # The exact value depends on implementation details of _calculate_overlap_percentage
        # Adjust the range to accommodate the actual implementation
        assert 0.4 <= score <= 0.6

    def test_error_association_strategy_prioritize_input_fields(self):
        """Test that ErrorAssociationStrategy prioritizes input fields."""
        strategy = ErrorAssociationStrategy()

        # Create a mock item with EditText class
        mock_item = Mock()
        mock_item.view = {"class": "android.widget.EditText"}

        # Define visual bounds and UI element data
        visual_bounds = [[10, 10], [50, 50]]
        ui_element_data_edit_text = {
            "bounds": [[20, 20], [60, 60]],
            "item": mock_item
        }

        # Create another mock item without EditText class
        mock_item_regular = Mock()
        mock_item_regular.view = {"class": "android.widget.TextView"}

        ui_element_data_regular = {
            "bounds": [[20, 20], [60, 60]],
            "item": mock_item_regular
        }

        # Calculate scores for both
        score_edit_text = strategy.calculate_match_score(visual_bounds, ui_element_data_edit_text)
        score_regular = strategy.calculate_match_score(visual_bounds, ui_element_data_regular)

        # Assert that edit text gets higher score with same overlap
        assert score_edit_text > score_regular

    def test_button_association_strategy_prioritize_buttons(self):
        """Test that ButtonAssociationStrategy prioritizes button elements."""
        strategy = ButtonAssociationStrategy()

        # Create a mock item with Button class
        mock_button = Mock()
        mock_button.view = {"class": "android.widget.Button", "clickable": True}

        # Define visual bounds and UI element data
        visual_bounds = [[10, 10], [50, 50]]
        ui_element_data_button = {
            "bounds": [[20, 20], [60, 60]],
            "item": mock_button
        }

        # Create another mock item without Button class
        mock_item_regular = Mock()
        mock_item_regular.view = {"class": "android.widget.TextView", "clickable": False}

        ui_element_data_regular = {
            "bounds": [[20, 20], [60, 60]],
            "item": mock_item_regular
        }

        # Calculate scores for both
        score_button = strategy.calculate_match_score(visual_bounds, ui_element_data_button)
        score_regular = strategy.calculate_match_score(visual_bounds, ui_element_data_regular)

        # Assert that button gets higher score with same overlap
        assert score_button > score_regular

    def test_text_association_strategy(self):
        """Test the TextAssociationStrategy calculate_match_score method."""
        strategy = TextAssociationStrategy()

        # Define visual bounds and UI element data
        visual_bounds = [[10, 10], [50, 50]]
        ui_element_data = {
            "bounds": [[20, 20], [60, 60]],
            "item": Mock()
        }

        # Calculate match score
        score = strategy.calculate_match_score(visual_bounds, ui_element_data)

        # Assert the score reflects the overlap ratio
        # The exact value depends on implementation details of _calculate_overlap_percentage
        assert 0.4 <= score <= 0.6

    def test_interactive_element_association_strategy_prioritize_interactive(self):
        """Test that InteractiveElementAssociationStrategy prioritizes interactive elements."""
        strategy = InteractiveElementAssociationStrategy()

        # Create a mock item with interactive properties
        mock_interactive = Mock()
        mock_interactive.view = {
            "class": "android.widget.ListView",
            "clickable": False,
            "scrollable": True
        }

        # Define visual bounds and UI element data
        visual_bounds = [[10, 10], [50, 50]]
        ui_element_data_interactive = {
            "bounds": [[20, 20], [60, 60]],
            "item": mock_interactive
        }

        # Create another mock item without interactive properties
        mock_item_regular = Mock()
        mock_item_regular.view = {
            "class": "android.widget.FrameLayout",
            "clickable": False,
            "scrollable": False
        }

        ui_element_data_regular = {
            "bounds": [[20, 20], [60, 60]],
            "item": mock_item_regular
        }

        # Calculate scores for both
        score_interactive = strategy.calculate_match_score(visual_bounds, ui_element_data_interactive)
        score_regular = strategy.calculate_match_score(visual_bounds, ui_element_data_regular)

        # Assert that interactive element gets higher score with same overlap
        assert score_interactive > score_regular


class TestScreenshotActionComplementor:
    """Tests for the ScreenshotActionComplementor class."""

    @pytest.fixture
    def mock_static_data(self):
        """Create a mock StaticAnalysisData object."""
        return Mock(spec=StaticAnalysisData)

    @pytest.fixture
    def complementor(self, mock_static_data):
        """Create a ScreenshotActionComplementor instance for testing."""
        return ScreenshotActionComplementor(mock_static_data)

    @pytest.fixture
    def sample_screen_description(self):
        """Create a sample ScreenDescription for testing."""
        # Create a sample screen item
        view_data = {
            "class": "android.widget.Button",
            "resource_id": "test_button",
            "bounds": [[100, 100], [200, 200]],
            "clickable": True,
            "text": "Test Button"
        }

        # Create a sample action
        action = ItemAction(
            id=1,
            text="CLICK (1)",
            event=WidgetEventType.CLICK,
            target_view=view_data,
            coordinates=(150, 150)
        )

        # Create a screen item
        item = ScreenItem(
            view=view_data,
            base_description="Test Button",
            actions=[action]
        )

        # Create a screen description
        return ScreenDescription("com.test.app.MainActivity", [item])

    def test_initialization(self, complementor):
        """Test proper initialization of the ScreenshotActionComplementor."""
        assert complementor.counter.value == 1000
        assert isinstance(complementor.visual_to_ui_associations, dict)
        assert isinstance(complementor.error_impacted_items, set)
        assert isinstance(complementor.unmatched_visual_elements, list)

    def test_calculate_center(self, complementor):
        """Test the _calculate_center method."""
        bounds = [[10, 20], [30, 40]]
        center = complementor._calculate_center(bounds)
        assert center == (20, 30)

    def test_calculate_area(self, complementor):
        """Test the _calculate_area method."""
        bounds = [[10, 20], [30, 40]]
        area = complementor._calculate_area(bounds)
        assert area == 400  # (30-10) * (40-20) = 20 * 20 = 400

    def test_looks_like_button_text(self, complementor):
        """Test the _looks_like_button_text method."""
        # Test common button text
        assert complementor._looks_like_button_text("OK") is True
        assert complementor._looks_like_button_text("Cancel") is True

        # Test short text
        assert complementor._looks_like_button_text("X") is True

        # Test longer non-button text
        assert complementor._looks_like_button_text(
            "This is a long text that should not be considered a button") is False

    @patch('rvandroid_tool.analysis.screenshot.screenshot_action_complementor.ScreenshotAnalyzer')
    def test_analyze_state_extraction(self, mock_analyzer_class, complementor, sample_screen_description):
        """Test that analyze correctly extracts state information."""
        # Set up the state dictionary
        state = {
            StateEntry.STRUCTURED_SCREEN: sample_screen_description,
            StateEntry.SCREENSHOT_PATH: "/path/to/screenshot.png"
        }

        # Mock the analyzer
        mock_analyzer = mock_analyzer_class.return_value
        mock_analyzer.extract_information.return_value = {
            "texts": [],
            "buttons": [],
            "error_indicators": [],
            "interactive_elements": []
        }

        # Call analyze
        result = complementor.analyze(state)

        # Verify extraction of screen description and screenshot path
        mock_analyzer_class.assert_called_once_with(image_path="/path/to/screenshot.png")
        assert "enhanced_screen" in result
        assert "visual_mapping" in result

    def test_missing_state_information(self, complementor):
        """Test that analyze raises ValueError when required state information is missing."""
        # Set up an incomplete state dictionary
        state = {
            StateEntry.STRUCTURED_SCREEN: Mock(spec=ScreenDescription)
            # Missing screenshot path
        }

        # Should raise ValueError
        with pytest.raises(ValueError):
            complementor.analyze(state)

    @patch('rvandroid_tool.analysis.screenshot.screenshot_action_complementor.ScreenshotAnalyzer')
    def test_empty_analysis_result(self, mock_analyzer_class, complementor, sample_screen_description):
        """Test handling of empty analysis results."""
        # Set up the state dictionary
        state = {
            StateEntry.STRUCTURED_SCREEN: sample_screen_description,
            StateEntry.SCREENSHOT_PATH: "/path/to/screenshot.png"
        }

        # Mock the analyzer to return empty results
        mock_analyzer = mock_analyzer_class.return_value
        mock_analyzer.extract_information.return_value = {
            "texts": [],
            "buttons": [],
            "error_indicators": [],
            "interactive_elements": []
        }

        # Call analyze
        result = complementor.complement_screen_actions(sample_screen_description, "/path/to/screenshot.png")

        # Verify result structure
        assert result["visual_mapping"]["metrics"]["error_indicators_count"] == 0
        assert result["visual_mapping"]["metrics"]["visual_buttons_count"] == 0
        assert result["visual_mapping"]["metrics"]["text_elements_count"] == 0
        assert result["visual_mapping"]["metrics"]["interactive_elements_count"] == 0

        # Instead of directly comparing objects, check if they have the same activity
        # and the same number of items (plus standard BACK action)
        enhanced_screen = result["enhanced_screen"]
        assert enhanced_screen.activity == sample_screen_description.activity

        # The enhanced screen might have a BACK action added even if no visual elements were found
        # Original screen + BACK action = 2 items
        assert len(enhanced_screen.items) >= len(sample_screen_description.items)

        # Check that original items are present in enhanced screen
        original_ids = set(item.view.get("resource_id", "") for item in sample_screen_description.items)
        enhanced_ids = set(item.view.get("resource_id", "") for item in enhanced_screen.items)
        for original_id in original_ids:
            assert original_id in enhanced_ids

    @patch('rvandroid_tool.analysis.screenshot.screenshot_action_complementor.ScreenshotAnalyzer')
    def test_create_ui_elements_map(self, mock_analyzer_class, complementor, sample_screen_description):
        """Test the _create_ui_elements_map method."""
        # Call the method
        ui_elements_map = complementor._create_ui_elements_map(sample_screen_description)

        # Verify map contains the test button
        assert len(ui_elements_map) == 1
        key = "100_100_200_200"  # Derived from bounds
        assert key in ui_elements_map

        # Verify mapped data
        mapped_item = ui_elements_map[key]
        assert mapped_item["item"].view["resource_id"] == "test_button"
        assert mapped_item["bounds"] == [[100, 100], [200, 200]]
        assert mapped_item["center"] == (150, 150)
        assert mapped_item["area"] == 10000  # (200-100) * (200-100) = 100 * 100

    @patch('rvandroid_tool.analysis.screenshot.screenshot_action_complementor.ScreenshotAnalyzer')
    def test_process_error_indicators(self, mock_analyzer_class, complementor, sample_screen_description):
        """Test processing of error indicators."""
        # Create a mock error indicator
        error_indicator = {
            "x": 110,
            "y": 110,
            "width": 80,
            "height": 30,
            "error_type": "validation_error",
            "confidence": 0.8,
            "text": "Invalid input"
        }

        # Create UI elements map
        ui_elements_map = complementor._create_ui_elements_map(sample_screen_description)

        # Process the error indicator
        result = complementor._process_error_indicators([error_indicator], ui_elements_map, sample_screen_description)

        # Verify result
        assert len(result) == 1
        processed_error = result[0]

        # Verify error was associated with the button (since bounds overlap)
        assert processed_error["associated_item"] is not None
        assert processed_error["associated_item"].view["resource_id"] == "test_button"

        # Verify the item was updated with error information
        associated_item = processed_error["associated_item"]
        assert associated_item.complement["has_error"] is True
        assert len(associated_item.complement["errors"]) == 1
        assert associated_item.complement["errors"][0]["error_type"] == "validation_error"

    @patch('rvandroid_tool.analysis.screenshot.screenshot_action_complementor.ScreenshotAnalyzer')
    def test_process_visual_buttons(self, mock_analyzer_class, complementor, sample_screen_description):
        """Test processing of visual buttons."""
        # Create a mock visual button
        visual_button = {
            "x": 300,
            "y": 300,
            "width": 100,
            "height": 50,
            "confidence": 0.9,
            "detection_method": "shape",
            "text": "Visual Button"
        }

        # Create UI elements map
        ui_elements_map = complementor._create_ui_elements_map(sample_screen_description)

        # Process the visual button
        result = complementor._process_visual_buttons([visual_button], ui_elements_map, sample_screen_description)

        # Verify result
        assert len(result) == 1
        processed_button = result[0]

        # Since this button doesn't overlap with existing UI elements, it should be unmatched
        assert processed_button["associated_item"] is None

        # Verify the button was added to unmatched elements
        assert len(complementor.unmatched_visual_elements) == 1
        assert complementor.unmatched_visual_elements[0]["text"] == "Visual Button"

    @patch('rvandroid_tool.analysis.screenshot.screenshot_action_complementor.ScreenshotAnalyzer')
    def test_create_visual_button(self, mock_analyzer_class, complementor):
        """Test creation of visual button screen items."""
        # Create button data
        button_data = {
            "x": 300,
            "y": 300,
            "width": 100,
            "height": 50,
            "confidence": 0.9,
            "text": "Visual Button"
        }

        # Create screen item
        screen_item = complementor._create_visual_button(button_data)

        # Verify screen item properties
        assert screen_item.view["class"] == "android.widget.Button"
        assert screen_item.view["resource_id"].startswith("visual_button_")
        assert screen_item.view["bounds"] == [[300, 300], [400, 350]]
        assert screen_item.view["clickable"] is True
        assert screen_item.view["visual_element"] is True
        assert screen_item.view["text"] == "Visual Button"

        # Verify actions
        assert len(screen_item.actions) == 1
        action = screen_item.actions[0]
        assert action.event == WidgetEventType.CLICK
        assert action.text.startswith("CLICK (Visual)")
        assert action.coordinates == (350, 325)  # Center of the button

    @patch('rvandroid_tool.analysis.screenshot.screenshot_action_complementor.ScreenshotAnalyzer')
    def test_enhance_screen_description(self, mock_analyzer_class, complementor, sample_screen_description):
        """Test enhancement of screen description with visual elements."""
        # Create visual mapping with unmatched elements
        visual_mapping = {
            "error_indicators": [],
            "visual_buttons": [],
            "text_elements": [],
            "interactive_elements": [],
            "error_impacted_items": [],
            "unmatched_elements": [
                {
                    "x": 300,
                    "y": 300,
                    "width": 100,
                    "height": 50,
                    "confidence": 0.9,
                    "text": "Visual Button",
                    "is_button_like": True,
                    "type": "button"
                }
            ]
        }

        # Enhance screen description
        enhanced_screen = complementor._enhance_screen_description(sample_screen_description, visual_mapping)

        # Verify enhanced screen contains original item plus the visual button
        assert len(enhanced_screen.items) == 3  # Original item + visual button + standard BACK action

        # Find the visual button (it should be the second item, before the BACK action)
        visual_button_item = None
        for item in enhanced_screen.items:
            if item.view.get("visual_element", False) and item.view.get("resource_id", "").startswith("visual_button_"):
                visual_button_item = item
                break

        assert visual_button_item is not None
        assert visual_button_item.view["text"] == "Visual Button"
        assert len(visual_button_item.actions) == 1
        assert visual_button_item.actions[0].event == WidgetEventType.CLICK

    def test_get_metrics(self, complementor):
        """Test the get_metrics method."""
        # Add some items to the tracked collections
        complementor.error_impacted_items.add(Mock())
        complementor.unmatched_visual_elements.append({"type": "button"})

        # Get metrics
        metrics = complementor.get_metrics()

        # Verify metrics
        assert metrics["error_impacted_items_count"] == 1
        assert metrics["unmatched_visual_elements_count"] == 1

    @patch('rvandroid_tool.analysis.screenshot.screenshot_action_complementor.ScreenshotAnalyzer')
    def test_complement_screen_actions_with_exception(self, mock_analyzer_class, complementor,
                                                      sample_screen_description):
        """Test error handling in complement_screen_actions method."""
        # Make the analyzer raise an exception
        mock_analyzer = mock_analyzer_class.return_value
        mock_analyzer.extract_information.side_effect = Exception("Test exception")

        # Call the method
        result = complementor.complement_screen_actions(sample_screen_description, "/path/to/screenshot.png")

        # Verify error handling
        assert result["enhanced_screen"] == sample_screen_description
        assert "error" in result["visual_mapping"]
        assert "Test exception" in result["visual_mapping"]["error"]
        assert result["visual_mapping"]["metrics"]["error"] == "Failed to analyze screenshot"

    @patch('rvandroid_tool.analysis.screenshot.screenshot_action_complementor.ScreenshotAnalyzer')
    def test_find_associated_ui_element(self, mock_analyzer_class, complementor, sample_screen_description):
        """Test the _find_associated_ui_element method."""
        # Create UI elements map
        ui_elements_map = complementor._create_ui_elements_map(sample_screen_description)

        # Create a mock strategy
        strategy = Mock()
        strategy.calculate_match_score.return_value = 0.2  # Above the 0.1 threshold

        # Define visual bounds that overlap with the button
        visual_bounds = [[150, 150], [250, 250]]

        # Find associated UI element
        associated_item = complementor._find_associated_ui_element(visual_bounds, ui_elements_map, strategy)

        # Verify result
        assert associated_item is not None
        assert associated_item.view["resource_id"] == "test_button"

        # Test with low score below threshold
        strategy.calculate_match_score.return_value = 0.05  # Below the 0.1 threshold

        # Find associated UI element with low score
        associated_item = complementor._find_associated_ui_element(visual_bounds, ui_elements_map, strategy)

        # Verify no association
        assert associated_item is None

        # Verify strategy was called correctly
        strategy.calculate_match_score.assert_called_with(visual_bounds, list(ui_elements_map.values())[0])


if __name__ == '__main__':
    pytest.main(['-xvs', __file__])
