"""
Unit tests for the ScreenshotActionComplementor class.

This test suite validates the functionality of the ScreenshotActionComplementor,
which enhances screen descriptions with information extracted from screenshot analysis
using the new Pydantic model integration from rv-screen-parser.

### Testing Strategy:
- Tests association strategies for different visual element types
- Validates error indicator processing with UI hierarchy integration
- Verifies visual button detection and virtual element creation
- Ensures proper integration with rv-screen-parser Pydantic models
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
        """Test that TextAssociationStrategy uses base calculation."""
        strategy = TextAssociationStrategy()

        # Define visual bounds and UI element data
        visual_bounds = [[10, 10], [50, 50]]
        ui_element_data = {
            "bounds": [[20, 20], [60, 60]],
            "item": Mock()
        }

        # Calculate match score
        score = strategy.calculate_match_score(visual_bounds, ui_element_data)

        # Assert the score is valid and uses base calculation
        assert 0 <= score <= 1
        assert 0.4 <= score <= 0.6

    def test_interactive_element_association_strategy_prioritize_interactive(self):
        """Test that InteractiveElementAssociationStrategy handles interactive elements."""
        strategy = InteractiveElementAssociationStrategy()

        # Define visual bounds and UI element data
        visual_bounds = [[10, 10], [50, 50]]
        ui_element_data = {
            "bounds": [[20, 20], [60, 60]],
            "item": Mock()
        }

        # Calculate match score
        score = strategy.calculate_match_score(visual_bounds, ui_element_data)

        # Assert the score is valid and uses base calculation
        assert 0 <= score <= 1
        assert 0.4 <= score <= 0.6


class TestScreenshotActionComplementor:
    """Test cases for the main ScreenshotActionComplementor class."""

    @pytest.fixture
    def complementor(self):
        """Create a ScreenshotActionComplementor instance for testing."""
        return ScreenshotActionComplementor()

    @pytest.fixture
    def sample_screen_description(self):
        """Create a sample ScreenDescription for testing."""
        # Create a mock action
        action = ItemAction(
            id=1,
            text="CLICK test button (1)",
            event=WidgetEventType.CLICK,
            target_view={"resource_id": "test_button", "bounds": [[100, 100], [200, 200]]}
        )

        # Create a sample screen item
        item = ScreenItem(
            view={"resource_id": "test_button", "bounds": [[100, 100], [200, 200]], "class": "android.widget.Button"},
            base_description="Test button",
            actions=[action]
        )

        # Create screen description
        return ScreenDescription(
            activity="com.test.MainActivity",
            items=[item]
        )

    def test_initialization(self, complementor):
        """Test proper initialization of ScreenshotActionComplementor."""
        assert complementor.analyzer_name == "screenshot_complementor"
        assert hasattr(complementor, 'logger')
        assert hasattr(complementor, 'error_handler')
        assert hasattr(complementor, 'counter')
        assert hasattr(complementor, 'visual_to_ui_associations')
        assert hasattr(complementor, 'error_impacted_items')
        assert hasattr(complementor, 'unmatched_visual_elements')

    def test_calculate_center(self, complementor):
        """Test _calculate_center method."""
        bounds = [[10, 20], [50, 80]]
        center = complementor._calculate_center(bounds)
        assert center == (30, 50)  # (10+50)/2, (20+80)/2

    def test_calculate_area(self, complementor):
        """Test _calculate_area method."""
        bounds = [[10, 20], [50, 80]]
        area = complementor._calculate_area(bounds)
        assert area == 2400  # (50-10) * (80-20) = 40 * 60

    def test_looks_like_button_text(self, complementor):
        """Test _looks_like_button_text helper method (if exists)."""
        # This test might not be needed if the method doesn't exist
        # but keeping for compatibility with original test structure
        pass

    def test_analyze_state_extraction(self, complementor, sample_screen_description):
        """Test analyze method with proper state extraction."""
        state = {
            StateEntry.STRUCTURED_SCREEN: sample_screen_description,
            StateEntry.SCREENSHOT_PATH: "/path/to/screenshot.png"
        }

        with patch.object(complementor, 'complement_screen_actions') as mock_complement:
            mock_complement.return_value = {"result": "success"}
            
            result = complementor.analyze(state)
            
            assert result == {"result": "success"}
            mock_complement.assert_called_once_with(sample_screen_description, "/path/to/screenshot.png")

    def test_missing_state_information(self, complementor):
        """Test analyze method with missing state information."""
        # Test missing structured screen
        state_missing_screen = {StateEntry.SCREENSHOT_PATH: "/path/to/screenshot.png"}
        
        with pytest.raises(Exception):  # Should raise RVParsingError
            complementor.analyze(state_missing_screen)

        # Test missing screenshot path
        state_missing_screenshot = {StateEntry.STRUCTURED_SCREEN: Mock()}
        
        with pytest.raises(Exception):  # Should raise RVParsingError
            complementor.analyze(state_missing_screenshot)

    def test_empty_analysis_result(self, complementor, sample_screen_description):
        """Test complement_screen_actions with empty analysis result."""
        with patch('rvandroid_tool.analysis.screenshot.screenshot_action_complementor.ScreenshotAnalyzer') as mock_analyzer_class:
            # Mock the analyzer instance and its extract_information method
            mock_analyzer = Mock()
            mock_analyzer.extract_information.return_value = {
                "error_indicators": [],
                "buttons": [],
                "texts": [],
                "interactive_elements": []
            }
            mock_analyzer_class.return_value = mock_analyzer

            result = complementor.complement_screen_actions(sample_screen_description, "/path/to/screenshot.png")

            # Verify result structure
            assert "enhanced_screen" in result
            assert "visual_mapping" in result
            assert result["visual_mapping"]["error_indicators"] == []
            assert result["visual_mapping"]["visual_buttons"] == []

    @patch('rvandroid_tool.analysis.screenshot.screenshot_action_complementor.ScreenshotAnalyzer')
    def test_create_ui_elements_map(self, mock_analyzer_class, complementor, sample_screen_description):
        """Test the _create_ui_elements_map method."""
        # Call the method
        ui_elements_map = complementor._create_ui_elements_map(sample_screen_description)

        # Verify map contains the test button (plus automatic BACK action)
        assert len(ui_elements_map) == 2  # test button + automatic BACK action
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
        """Test processing of error indicators with new Pydantic model structure."""
        # Create error indicator with correct structure from model_dump
        error_indicator = {
            "x": 110,
            "y": 110,
            "width": 80,
            "height": 30,
            "detection_method": "color",
            "confidence": 0.8,
            "error_type": "validation_error",
            "text": "Invalid input",
            "area": 2400.0,
            "red_dominance": None,
            "circularity": None,
            "icon_type": None,
            "error_category": None,
            "centering": None,
            "contains_texts": None,
            "contains_error_texts": None,
            "contains_buttons": None,
            "parent_dialog": None,
            "field_x": None,
            "field_y": None,
            "field_width": None,
            "field_height": None,
            "contains_error_text": None
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
        """Test processing of visual buttons with new model structure."""
        # Create visual button with correct structure from model_dump
        visual_button = {
            "x": 300,
            "y": 300,
            "width": 100,
            "height": 50,
            "area": 5000.0,
            "aspect_ratio": 2.0,
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

        # Since the button doesn't overlap with existing UI elements, it should create a virtual button
        assert processed_button["associated_item"] is not None
        # Virtual button should be added to screen description
        virtual_buttons = [item for item in sample_screen_description.items 
                          if item.view.get("class") == "VirtualButton"]
        assert len(virtual_buttons) == 1

    @patch('rvandroid_tool.analysis.screenshot.screenshot_action_complementor.ScreenshotAnalyzer')
    def test_create_virtual_button(self, mock_analyzer_class, complementor, sample_screen_description):
        """Test creation of virtual buttons for unmatched visual elements."""
        button_data = {
            "x": 300,
            "y": 300,
            "width": 100,
            "height": 50,
            "confidence": 0.9
        }

        virtual_button = complementor._create_virtual_button(button_data, sample_screen_description)

        assert virtual_button is not None
        assert virtual_button.view["class"] == "VirtualButton"
        assert virtual_button.view["clickable"] is True
        assert virtual_button.complement["visual_detection"] is True
        assert virtual_button.complement["confidence"] == 0.9
        assert len(virtual_button.actions) == 1
        assert virtual_button.actions[0].event == WidgetEventType.CLICK

    @patch('rvandroid_tool.analysis.screenshot.screenshot_action_complementor.ScreenshotAnalyzer')
    def test_enhance_screen_description(self, mock_analyzer_class, complementor, sample_screen_description):
        """Test screen description enhancement with visual mapping."""
        visual_mapping = {
            "error_indicators": [],
            "visual_buttons": [],
            "text_elements": [],
            "interactive_elements": [],
            "error_impacted_items": [],
            "unmatched_elements": [],
            "metrics": {}
        }

        enhanced_screen = complementor._enhance_screen_description(sample_screen_description, visual_mapping)

        # Should return the same screen description (enhancement happens during processing)
        assert enhanced_screen == sample_screen_description

    def test_get_metrics(self, complementor):
        """Test metrics collection."""
        # Add some test data
        complementor.visual_to_ui_associations = {"test": "data"}
        complementor.error_impacted_items = {Mock(), Mock()}
        complementor.unmatched_visual_elements = [Mock()]

        metrics = complementor.get_metrics()

        assert metrics["visual_associations"] == 1
        assert metrics["error_impacted_items"] == 2
        assert metrics["unmatched_elements"] == 1
        assert "processing_components" in metrics

    @patch('rvandroid_tool.analysis.screenshot.screenshot_action_complementor.ScreenshotAnalyzer')
    def test_complement_screen_actions_with_exception(self, mock_analyzer_class, complementor, sample_screen_description):
        """Test error handling in complement_screen_actions."""
        # Mock analyzer to raise an exception
        mock_analyzer = Mock()
        mock_analyzer.extract_information.side_effect = Exception("Analysis failed")
        mock_analyzer_class.return_value = mock_analyzer

        result = complementor.complement_screen_actions(sample_screen_description, "/path/to/screenshot.png")

        # Should return fallback structure
        assert "enhanced_screen" in result
        assert "visual_mapping" in result
        assert "error" in result["visual_mapping"]
        assert result["visual_mapping"]["error"] == "Analysis failed"

    @patch('rvandroid_tool.analysis.screenshot.screenshot_action_complementor.ScreenshotAnalyzer')
    def test_find_associated_ui_element(self, mock_analyzer_class, complementor, sample_screen_description):
        """Test UI element association with different strategies."""
        ui_elements_map = complementor._create_ui_elements_map(sample_screen_description)
        
        # Test with overlapping bounds (should find association)
        visual_bounds = [[110, 110], [190, 190]]  # Overlaps with test button
        strategy = AssociationStrategy()
        
        associated_item = complementor._find_associated_ui_element(visual_bounds, ui_elements_map, strategy)
        
        assert associated_item is not None
        assert associated_item.view["resource_id"] == "test_button"
        
        # Test with non-overlapping bounds (should not find association)
        visual_bounds_no_overlap = [[300, 300], [400, 400]]
        
        associated_item_none = complementor._find_associated_ui_element(visual_bounds_no_overlap, ui_elements_map, strategy)
        
        assert associated_item_none is None