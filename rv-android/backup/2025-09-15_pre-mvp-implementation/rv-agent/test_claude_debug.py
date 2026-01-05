#!/usr/bin/env python3
"""
Claude API Debug Test - Show raw responses
"""

import os
import json
import time
import base64
from pathlib import Path
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

load_dotenv()

try:
    import anthropic
except ImportError:
    print("❌ Error: anthropic package not found")
    exit(1)

def extract_uiautomator_elements(xml_content: str):
    """Extract clickable elements from UIAutomator XML."""
    try:
        root = ET.fromstring(xml_content)
        elements = []
        
        def traverse_node(node, path=""):
            if node.get('clickable') == 'true' and node.get('bounds'):
                bounds = node.get('bounds', '')
                text = node.get('text', '') or node.get('content-desc', '') or node.get('resource-id', '')
                
                if bounds and '[' in bounds:
                    try:
                        parts = bounds.replace('[', '').replace(']', ',').split(',')
                        if len(parts) >= 4:
                            x1, y1, x2, y2 = map(int, parts[:4])
                            center_x = (x1 + x2) // 2
                            center_y = (y1 + y2) // 2
                            
                            elements.append({
                                'text': text,
                                'bounds': bounds,
                                'coordinates': [center_x, center_y],
                                'class': node.get('class', ''),
                                'path': path
                            })
                    except ValueError:
                        pass
            
            for i, child in enumerate(node):
                traverse_node(child, f"{path}/{i}")
        
        traverse_node(root)
        return elements
    
    except ET.ParseError as e:
        print(f"❌ XML parsing error: {e}")
        return []

def create_enhanced_prompt(elements):
    """Create the coordinate validation enhanced prompt."""
    
    if not elements:
        return "No clickable elements found. Return: {'error': 'no_elements'}"
    
    lines = [
        "COORDINATE VALIDATION MODE:",
        "- Analyze this Android app screenshot",
        "- Use the EXACT coordinates shown below in 'at position (x, y)' format", 
        "- Do not estimate coordinates from the image - use the provided coordinates",
        "- Choose the most suitable element for testing this app",
        "- Return valid JSON format only",
        "",
        "Available elements with exact coordinates:"
    ]
    
    for i, element in enumerate(elements[:10]):  # Limit to 10 for debugging
        text = element['text'][:30] if element['text'] else f"Element_{i+1}"
        coords = element['coordinates']
        lines.append(f"{i+1}. '{text}' at position ({coords[0]}, {coords[1]})")
    
    lines.extend([
        "",
        "Return JSON format:",
        '{"coordinates": [x, y], "element": "description", "action": "click"}'
    ])
    
    return "\n".join(lines)

def test_single_claude(image_path: str, uiautomator_path: str):
    """Test a single case and show debug output."""
    
    # Get API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key or api_key == 'your_api_key_here':
        print("❌ API key not configured")
        return
    
    print(f"🧪 Testing: {image_path}")
    print(f"📄 UIAutomator: {uiautomator_path}")
    
    # Initialize Claude client
    try:
        client = anthropic.Anthropic(api_key=api_key)
        print("✅ Client initialized successfully")
    except Exception as e:
        print(f"❌ Client error: {e}")
        return
    
    # Load UIAutomator XML
    try:
        with open(uiautomator_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        elements = extract_uiautomator_elements(xml_content)
        print(f"📊 Found {len(elements)} clickable elements")
    except Exception as e:
        print(f"❌ UIAutomator error: {e}")
        return
    
    if not elements:
        print("❌ No clickable elements found")
        return
    
    # Show first few elements
    print("🎯 First 5 elements:")
    for i, elem in enumerate(elements[:5]):
        coords = elem['coordinates']
        text = elem['text'][:50] if elem['text'] else 'No text'
        print(f"   {i+1}. ({coords[0]}, {coords[1]}) - '{text}'")
    
    # Encode image
    try:
        with open(image_path, 'rb') as image_file:
            image_base64 = base64.b64encode(image_file.read()).decode('utf-8')
        print("✅ Image encoded successfully")
    except Exception as e:
        print(f"❌ Image encoding error: {e}")
        return
    
    # Create prompt
    prompt = create_enhanced_prompt(elements)
    print(f"\n📝 PROMPT:")
    print("=" * 50)
    print(prompt)
    print("=" * 50)
    
    # Call Claude
    print("\n🤖 Calling Claude API...")
    start_time = time.time()
    
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=200,
            temperature=0.05,
            messages=[
                {
                    "role": "user", 
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )
        
        response_time = time.time() - start_time
        response_text = response.content[0].text
        
        print(f"⏱️  Response time: {response_time:.1f}s")
        print(f"\n📋 CLAUDE'S RAW RESPONSE:")
        print("=" * 50)
        print(response_text)
        print("=" * 50)
        
        # Try to parse JSON
        try:
            # Try to extract JSON from Claude's response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                print(f"\n🔍 Extracted JSON: {json_str}")
                result = json.loads(json_str)
            else:
                result = json.loads(response_text)
                
            print(f"\n✅ JSON parsed successfully!")
            print(f"🎯 Coordinates: {result.get('coordinates', 'Not found')}")
            print(f"🔍 Element: {result.get('element', 'Not found')}")
            
            if 'coordinates' in result and len(result['coordinates']) == 2:
                predicted = result['coordinates']
                # Find nearest element
                min_distance = float('inf')
                nearest_element = None
                
                for element in elements:
                    actual = element['coordinates']
                    distance = ((predicted[0] - actual[0]) ** 2 + (predicted[1] - actual[1]) ** 2) ** 0.5
                    if distance < min_distance:
                        min_distance = distance
                        nearest_element = element
                
                print(f"🎯 Distance to nearest element: {min_distance:.1f}px")
                if nearest_element:
                    print(f"📍 Nearest element: '{nearest_element['text'][:50]}' at {nearest_element['coordinates']}")
                
                if min_distance <= 50:
                    print("🎉 SUCCESS - Acceptable distance!")
                else:
                    print("❌ FAILURE - Distance too large")
                    
            else:
                print("❌ Invalid coordinate format")
        
        except json.JSONDecodeError as e:
            print(f"\n❌ JSON parsing failed: {e}")
            print("💡 Claude didn't return valid JSON")
    
    except Exception as e:
        print(f"❌ API call failed: {e}")

if __name__ == "__main__":
    print("🔬 Claude API Debug Test")
    print("Testing first available image/uiautomator pair")
    print()
    
    # Find first test case
    data_dir = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")
    
    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir}")
        exit(1)
    
    apk_dirs = [d for d in data_dir.iterdir() if d.is_dir()]
    
    if not apk_dirs:
        print("❌ No APK directories found")
        exit(1)
    
    # Test first available case
    for app_dir in apk_dirs:
        screenshots = list(app_dir.glob("*.png"))
        for screenshot in screenshots:
            uiautomator_file = screenshot.with_suffix('.uiautomator')
            if uiautomator_file.exists():
                print(f"📱 App: {app_dir.name}")
                test_single_claude(str(screenshot), str(uiautomator_file))
                exit(0)
    
    print("❌ No valid test cases found")