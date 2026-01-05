#!/usr/bin/env python3
"""
Quick setup validation script for RVAgent prototype.

Tests basic functionality before running full grid search.
"""
import sys
from pathlib import Path

# Add module to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rv_agent.config import PrototypeConfig
from rv_agent.llm_integration import create_vision_client
from rv_agent.coordinate_validator import create_coordinate_validator


def test_configuration():
    """Test configuration loading and validation."""
    print("Testing configuration...")
    
    config = PrototypeConfig(
        NUM_TEST_APPS=2,
        SCREENSHOTS_PER_APP=2,
        TIMEOUT_SECONDS=10
    )
    
    print(f"✓ Configuration loaded")
    print(f"  Total tests would be: {config.total_tests}")
    print(f"  Estimated duration: {config.estimated_duration_hours:.1f} hours")
    
    return config


def test_data_availability(config):
    """Test that screenshot data is available."""
    print("\nTesting data availability...")
    
    try:
        available_apps = config.get_available_apps()
        print(f"✓ Found {len(available_apps)} apps")
        
        if len(available_apps) >= 2:
            sample_app = available_apps[0]
            screenshots = config.random_select_screenshots(sample_app, 2)
            print(f"✓ Sample app '{sample_app}' has {len(screenshots)} screenshots")
            
            # Test file access
            image_path, xml_path = config.get_screenshot_files(sample_app, screenshots[0])
            print(f"✓ Sample files accessible:")
            print(f"  Image: {Path(image_path).name}")
            print(f"  XML: {Path(xml_path).name}")
            
            return True
        else:
            print(f"✗ Need at least 2 apps, found {len(available_apps)}")
            return False
            
    except Exception as e:
        print(f"✗ Data availability test failed: {e}")
        return False


def test_coordinate_validator(config):
    """Test coordinate validation functionality."""
    print("\nTesting coordinate validator...")
    
    try:
        validator = create_coordinate_validator(config)
        
        # Get sample XML file
        apps = config.get_available_apps()
        if apps:
            sample_app = apps[0]
            screenshots = config.random_select_screenshots(sample_app, 1)
            if screenshots:
                _, xml_path = config.get_screenshot_files(sample_app, screenshots[0])
                
                # Test coordinate extraction
                coordinates = validator.extract_clickable_coordinates(xml_path)
                print(f"✓ Extracted {len(coordinates)} clickable coordinates")
                
                if coordinates:
                    # Test validation with first coordinate (should be perfect match)
                    test_coord = coordinates[0]
                    result = validator.validate_coordinates(test_coord, xml_path)
                    print(f"✓ Coordinate validation: {result['success']} (distance: {result['distance']:.1f}px)")
                    
                    return True
                else:
                    print("✗ No clickable coordinates found")
                    return False
            
    except Exception as e:
        print(f"✗ Coordinate validator test failed: {e}")
        return False


def test_vision_client(config):
    """Test vision client creation (without actual LLM call)."""
    print("\nTesting vision client...")
    
    try:
        client = create_vision_client(config)
        print("✓ Vision client created successfully")
        
        # Test coordinate parsing
        test_responses = [
            "COORDINATES: (500, 300)",
            "The coordinates are (250, 150)",
            "X: 400, Y: 200"
        ]
        
        for response in test_responses:
            coords = client._parse_coordinates_from_response(response)
            if coords:
                print(f"✓ Parsed '{response}' -> {coords}")
            else:
                print(f"✗ Failed to parse '{response}'")
        
        return True
        
    except Exception as e:
        print(f"✗ Vision client test failed: {e}")
        return False


def main():
    """Run all setup validation tests."""
    print("RVAgent Prototype - Setup Validation")
    print("=" * 40)
    
    all_passed = True
    
    # Test configuration
    config = test_configuration()
    if not config:
        all_passed = False
    
    # Test data availability
    if not test_data_availability(config):
        all_passed = False
    
    # Test coordinate validator
    if not test_coordinate_validator(config):
        all_passed = False
    
    # Test vision client
    if not test_vision_client(config):
        all_passed = False
    
    print("\n" + "=" * 40)
    if all_passed:
        print("✓ All tests passed! Ready to run prototype.")
        print("\nTo run the full prototype:")
        print("  poetry run python src/rv_agent/prototype_main.py")
        return 0
    else:
        print("✗ Some tests failed. Please fix issues before running prototype.")
        return 1


if __name__ == "__main__":
    sys.exit(main())