#!/usr/bin/env python3
"""
Minimal LLM test - 1 screenshot with vision model coordinate generation.
"""
import sys
import time
from pathlib import Path
from datetime import datetime

# Add module to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rv_agent.simple_validator import create_simple_validator


def test_vision_model():
    """Test vision model coordinate generation."""
    # Test parameters
    temperature = 0.3
    top_p = 0.9
    top_k = 40
    
    print("Testing vision model coordinate generation...")
    print(f"Parameters: temp={temperature}, top_p={top_p}, top_k={top_k}, timeout=60s")
    print()
    
    # Get test data
    screenshots_dir = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    screenshots_path = Path(screenshots_dir)
    
    # Use first available app and screenshot
    app_dirs = [d for d in screenshots_path.iterdir() if d.is_dir() and d.name.endswith('.apk')]
    first_app = app_dirs[0]
    png_files = list(first_app.glob("*.png"))
    
    test_image = png_files[0]
    test_xml = test_image.with_suffix('.uiautomator')
    
    print(f"App: {first_app.name}")
    print(f"Screenshot: {test_image.name}")
    print(f"Image path: {test_image}")
    print(f"XML path: {test_xml}")
    print()
    
    # Show ground truth
    validator = create_simple_validator(tolerance=50)
    ground_truth = validator.extract_clickable_coordinates(str(test_xml))
    print(f"Ground truth: {len(ground_truth)} clickable elements")
    for i, coord in enumerate(ground_truth[:5]):
        print(f"  {i+1}. {coord}")
    print()
    
    try:
        # Import LangChain components
        from langchain_ollama import ChatOllama
        from langchain_core.messages import HumanMessage
        
        print("Creating ChatOllama client...")
        
        # Create LLM with test parameters
        llm = ChatOllama(
            model="qwen2.5vl:7b",
            base_url="http://localhost:11434",
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            num_predict=200,
            timeout=60,
            # Configure for larger context window (125K available)
            num_ctx=32768  # Use 32K context for better reasoning
        )
        
        print("✓ LLM client created")
        
        # Create vision prompt
        prompt = """You are an expert Android UI automation assistant. 

Analyze this Android app screenshot and identify a clickable UI element that would be good for testing.

Please respond with ONLY the coordinates in this exact format:
COORDINATES: (x, y)

Where x and y are the pixel coordinates of the center of a clickable element.

Choose an element that is:
1. Clearly clickable (button, menu item, etc.)
2. Visible and not obscured
3. Not a system UI element (status bar, navigation bar)
4. Likely to be functionally important for testing

Respond only with the coordinate format shown above, nothing else."""

        # Read and encode image
        import base64
        
        with open(test_image, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Create message with encoded image
        message = HumanMessage(content=[
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
        ])
        
        print("Sending request to vision model...")
        start_time = time.time()
        
        # Generate response
        response = llm.invoke([message])
        
        execution_time = time.time() - start_time
        print(f"✓ Response received in {execution_time:.2f}s")
        print()
        
        # Show response
        print("Raw response:")
        print(response.content)
        print()
        
        # Parse coordinates
        generated_coords = parse_coordinates(response.content)
        
        if generated_coords:
            print(f"✓ Parsed coordinates: {generated_coords}")
            
            # Validate against ground truth
            result = validator.validate_coordinates(generated_coords, str(test_xml))
            
            print(f"✓ Validation result:")
            print(f"  Success: {result['success']}")
            print(f"  Distance to closest: {result['distance']:.1f}px")
            print(f"  Tolerance: {result['tolerance']}px")
            print(f"  Closest element: {result['closest_element']}")
            print()
            
            if result['success']:
                print("🎉 SUCCESS! Vision model generated valid coordinates!")
            else:
                print(f"⚠ PARTIAL SUCCESS: Coordinates generated but {result['distance']:.1f}px from nearest element")
                
            return True
            
        else:
            print("✗ Failed to parse coordinates from response")
            return False
            
    except Exception as e:
        print(f"✗ Vision model test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def parse_coordinates(response: str):
    """Parse coordinates from LLM response."""
    import re
    
    # Try multiple patterns
    patterns = [
        r'COORDINATES:\s*\((\d+),\s*(\d+)\)',
        r'\((\d+),\s*(\d+)\)',
        r'(\d+),\s*(\d+)',
        r'x:\s*(\d+).*y:\s*(\d+)',
        r'X:\s*(\d+).*Y:\s*(\d+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response, re.IGNORECASE)
        if match:
            x, y = int(match.group(1)), int(match.group(2))
            if 0 <= x <= 2000 and 0 <= y <= 3000:  # Sanity check
                return (x, y)
    
    return None


def main():
    """Run minimal LLM test."""
    print("RVAgent Prototype - Minimal LLM Test")
    print("1 app, 1 screenshot, 1 parameter combination")
    print("=" * 60)
    
    try:
        success = test_vision_model()
        
        print("=" * 60)
        if success:
            print("✅ MINIMAL TEST PASSED!")
            print("Vision model pipeline is working correctly.")
            print("Ready for full grid search execution.")
        else:
            print("❌ MINIMAL TEST FAILED!")
            print("Check configuration before running full prototype.")
        print("=" * 60)
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        return 1


if __name__ == "__main__":
    sys.exit(main())