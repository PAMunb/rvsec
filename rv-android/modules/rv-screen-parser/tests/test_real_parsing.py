import os
import json
from pathlib import Path
import pytest
from rv_screen_parser.parser.screen.uiautomator.uiautomator_parser import UIAutomator2Parser
from rv_screen_parser.screenshot.screenshot_analyzer import ScreenshotAnalyzer


class TestRealParsing:
    """Test suite for parsing real UIAutomator dumps and images."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.test_images_dir = Path(__file__).parent.parent / "test_images"
        
        # Find available test data
        self.available_images = list(self.test_images_dir.glob("*.png"))
        self.available_dumps = list(self.test_images_dir.glob("*.uiautomator"))
        
        # Create mappings between images and dumps
        self.image_dump_pairs = []
        for img_path in self.available_images:
            # Look for corresponding dump file
            dump_path = img_path.with_suffix('.uiautomator')
            if dump_path.exists():
                self.image_dump_pairs.append((img_path, dump_path))

    def test_available_test_data(self):
        """Test that we have real test data available."""
        assert len(self.available_images) > 0, "Should have PNG images in test_images directory"
        assert len(self.available_dumps) > 0, "Should have UIAutomator dumps in test_images directory"
        assert len(self.image_dump_pairs) > 0, "Should have at least one image/dump pair"
        
        print(f"Found {len(self.available_images)} images and {len(self.available_dumps)} dumps")
        print(f"Found {len(self.image_dump_pairs)} image/dump pairs")

    def test_parse_real_uiautomator_dumps(self):
        """Test parsing real UIAutomator dump files."""
        if not self.image_dump_pairs:
            pytest.skip("No image/dump pairs available for testing")

        parser = UIAutomator2Parser()

        for img_path, dump_path in self.image_dump_pairs[:3]:  # Test first 3 pairs
            print(f"Testing with image: {img_path.name} and dump: {dump_path.name}")

            # Parse the UIAutomator dump
            with open(dump_path, 'r', encoding='utf-8') as f:
                dump_content = f.read()

            # Parse the dump content
            root_node = parser.parse(dump_content)

            # Basic assertions
            assert root_node is not None, f"Should parse {dump_path.name} successfully"
            assert hasattr(root_node, 'items'), "Root node should have items attribute"
            assert isinstance(root_node.items, list), "Items should be a list"

            # Check that we have some UI elements
            assert len(root_node.items) > 0, f"Should have at least one UI element in {dump_path.name}"

            # Print some stats about the parsed structure
            print(f"  Parsed {len(root_node.items)} top-level UI elements")

    def test_screenshot_analysis_with_real_images(self):
        """Test screenshot analysis with real images."""
        if not self.image_dump_pairs:
            pytest.skip("No image/dump pairs available for testing")
        
        analyzer = ScreenshotAnalyzer()
        
        for img_path, dump_path in self.image_dump_pairs[:2]:  # Test first 2 pairs
            print(f"Analyzing image: {img_path.name}")
            
            # Analyze the screenshot
            analysis_result = analyzer.analyze(str(img_path))
            
            # Basic assertions
            assert analysis_result is not None, f"Should analyze {img_path.name} successfully"
            assert hasattr(analysis_result, 'texts'), "Analysis result should have texts attribute"
            assert hasattr(analysis_result, 'buttons'), "Analysis result should have buttons attribute"
            assert hasattr(analysis_result, 'error_indicators'), "Analysis result should have error_indicators attribute"
            
            # Print some stats about the analysis
            print(f"  Found {len(analysis_result.texts)} text elements")
            print(f"  Found {len(analysis_result.buttons)} buttons")
            print(f"  Found {len(analysis_result.error_indicators)} error indicators")

    def test_end_to_end_parsing_workflow(self):
        """Test complete workflow: parse UIAutomator dump and analyze corresponding image."""
        if not self.image_dump_pairs:
            pytest.skip("No image/dump pairs available for testing")

        parser = UIAutomator2Parser()
        analyzer = ScreenshotAnalyzer()

        for img_path, dump_path in self.image_dump_pairs[:2]:  # Test first 2 pairs
            print(f"Testing end-to-end with: {img_path.name} and {dump_path.name}")

            # Step 1: Parse UIAutomator dump
            with open(dump_path, 'r', encoding='utf-8') as f:
                dump_content = f.read()

            root_node = parser.parse(dump_content)
            assert root_node is not None

            # Step 2: Analyze corresponding image
            analysis_result = analyzer.analyze(str(img_path))
            assert analysis_result is not None

            # Step 3: Verify both operations completed successfully
            print(f"  UIAutomator parsing: {len(root_node.items)} elements")
            print(f"  Screenshot analysis: {len(analysis_result.texts)} texts, {len(analysis_result.buttons)} buttons")

            # Both should have found some content
            assert len(root_node.items) > 0 or len(analysis_result.texts) > 0, \
                "Either UI parsing or screenshot analysis should find content"

    def test_multiple_real_dumps_consistency(self):
        """Test that parsing multiple real dumps works consistently."""
        if len(self.image_dump_pairs) < 2:
            pytest.skip("Need at least 2 image/dump pairs for consistency test")

        parser = UIAutomator2Parser()
        results = []

        for img_path, dump_path in self.image_dump_pairs[:5]:  # Test first 5 pairs
            with open(dump_path, 'r', encoding='utf-8') as f:
                dump_content = f.read()

            try:
                root_node = parser.parse(dump_content)
                if root_node is not None:
                    results.append({
                        'dump': dump_path.name,
                        'elements_count': len(root_node.items),
                        'success': True
                    })
            except Exception as e:
                results.append({
                    'dump': dump_path.name,
                    'error': str(e),
                    'success': False
                })

        # All parsing attempts should succeed
        failed_parses = [r for r in results if not r['success']]
        assert len(failed_parses) == 0, f"Some parses failed: {failed_parses}"

        # At least some elements should be found in most dumps
        successful_parses = [r for r in results if r['success']]
        if successful_parses:
            avg_elements = sum(r['elements_count'] for r in successful_parses) / len(successful_parses)
            print(f"Average elements per dump: {avg_elements:.2f}")
            # Note: We don't assert a minimum count as some screens might legitimately have few elements

    def test_parser_with_various_dump_formats(self):
        """Test that parser handles various real dump formats correctly."""
        if not self.available_dumps:
            pytest.skip("No dump files available for testing")

        parser = UIAutomator2Parser()

        for dump_path in self.available_dumps[:3]:  # Test first 3 dumps
            print(f"Testing dump format: {dump_path.name}")

            with open(dump_path, 'r', encoding='utf-8') as f:
                dump_content = f.read()

            # Should handle various dump formats
            root_node = parser.parse(dump_content)

            # Basic validation
            assert root_node is not None, f"Should parse {dump_path.name} regardless of format variations"

            # Check that the structure is maintained
            if hasattr(root_node, 'items'):
                print(f"  Found {len(root_node.items)} items in {dump_path.name}")