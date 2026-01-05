#!/usr/bin/env python3
"""
Very simple test to validate data access and basic functionality.
"""
import sys
from pathlib import Path

# Add module to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rv_agent.simple_validator import create_simple_validator


def test_data_access():
    """Test basic data access."""
    print("Testing data access...")
    
    screenshots_dir = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    screenshots_path = Path(screenshots_dir)
    
    if not screenshots_path.exists():
        print(f"✗ Screenshots directory not found: {screenshots_dir}")
        return False
    
    # Get list of apps
    app_dirs = [d for d in screenshots_path.iterdir() if d.is_dir() and d.name.endswith('.apk')]
    print(f"✓ Found {len(app_dirs)} apps")
    
    if not app_dirs:
        print("✗ No app directories found")
        return False
    
    # Test first app
    first_app = app_dirs[0]
    print(f"✓ Testing app: {first_app.name}")
    
    # Find PNG and XML files
    png_files = list(first_app.glob("*.png"))
    xml_files = list(first_app.glob("*.uiautomator"))
    
    print(f"✓ Found {len(png_files)} PNG files")
    print(f"✓ Found {len(xml_files)} XML files")
    
    if not png_files or not xml_files:
        print("✗ Missing PNG or XML files")
        return False
    
    # Test file pair
    first_png = png_files[0]
    first_xml = first_png.with_suffix('.uiautomator')
    
    if first_xml.exists():
        print(f"✓ File pair exists: {first_png.name} + {first_xml.name}")
        return True
    else:
        print(f"✗ XML file missing: {first_xml.name}")
        return False


def test_xml_parsing():
    """Test XML parsing functionality."""
    print("\nTesting XML parsing...")
    
    screenshots_dir = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    screenshots_path = Path(screenshots_dir)
    
    # Get first app and XML file
    app_dirs = [d for d in screenshots_path.iterdir() if d.is_dir() and d.name.endswith('.apk')]
    if not app_dirs:
        print("✗ No apps found")
        return False
    
    first_app = app_dirs[0]
    xml_files = list(first_app.glob("*.uiautomator"))
    
    if not xml_files:
        print("✗ No XML files found")
        return False
    
    first_xml = xml_files[0]
    print(f"✓ Testing XML file: {first_xml.name}")
    
    # Test coordinate extraction
    validator = create_simple_validator()
    coordinates = validator.extract_clickable_coordinates(str(first_xml))
    
    if coordinates:
        print(f"✓ Extracted {len(coordinates)} clickable coordinates")
        print(f"  Sample coordinates: {coordinates[:3]}")
        
        # Test validation with first coordinate (perfect match)
        if coordinates:
            test_coord = coordinates[0]
            result = validator.validate_coordinates(test_coord, str(first_xml))
            print(f"✓ Validation test: success={result['success']}, distance={result['distance']:.1f}px")
            return True
    else:
        print("✗ No coordinates extracted")
        return False


def test_ollama_availability():
    """Test if Ollama is available."""
    print("\nTesting Ollama availability...")
    
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_names = [m['name'] for m in models]
            print(f"✓ Ollama is running with {len(models)} models")
            
            if 'qwen2.5vl:7b' in model_names:
                print("✓ qwen2.5vl:7b model is available")
                return True
            else:
                print("⚠ qwen2.5vl:7b model not found")
                print(f"Available models: {model_names}")
                return False
        else:
            print(f"✗ Ollama responded with status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Ollama not available: {e}")
        return False


def main():
    """Run all simple tests."""
    print("RVAgent Prototype - Simple Validation")
    print("=" * 50)
    
    all_passed = True
    
    if not test_data_access():
        all_passed = False
    
    if not test_xml_parsing():
        all_passed = False
    
    if not test_ollama_availability():
        all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✓ All simple tests passed!")
        print("Ready to try minimal test with LLM.")
    else:
        print("✗ Some tests failed. Fix issues before proceeding.")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())