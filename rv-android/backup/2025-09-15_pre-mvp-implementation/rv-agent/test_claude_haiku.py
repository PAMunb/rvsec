#!/usr/bin/env python3
"""
Claude Haiku Test - Testing the cheapest Claude model for cost-effectiveness
Claude 3.5 Haiku is the fastest and most affordable option
"""

import os
import sys
import json
import csv
import time
import base64
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    import anthropic
except ImportError:
    print("❌ Error: anthropic package not found. Install with: poetry add anthropic")
    sys.exit(1)

def extract_uiautomator_elements(xml_content: str) -> List[Dict[str, Any]]:
    """Extract clickable elements from UIAutomator XML."""
    try:
        root = ET.fromstring(xml_content)
        elements = []
        
        def traverse_node(node, path=""):
            if node.get('clickable') == 'true' and node.get('bounds'):
                bounds = node.get('bounds', '')
                text = node.get('text', '') or node.get('content-desc', '') or node.get('resource-id', '')
                
                # Parse bounds [x1,y1][x2,y2] to center coordinates
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

def encode_image_base64(image_path: str) -> str:
    """Encode image to base64 for Claude API."""
    with open(image_path, 'rb') as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def create_enhanced_prompt(elements: List[Dict]) -> str:
    """Create the coordinate validation enhanced prompt that achieved great results."""
    
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
    
    for i, element in enumerate(elements[:15]):  # Limit to 15 elements for context
        text = element['text'][:50] if element['text'] else f"Element_{i+1}"
        coords = element['coordinates']
        lines.append(f"{i+1}. '{text}' at position ({coords[0]}, {coords[1]})")
    
    lines.extend([
        "",
        "Return JSON format:",
        '{"coordinates": [x, y], "element": "description", "action": "click"}'
    ])
    
    return "\n".join(lines)

def test_claude_haiku(image_path: str, uiautomator_path: str, temperature: float = 0.05) -> Dict[str, Any]:
    """Test Claude Haiku's vision capabilities with coordinate validation."""
    
    # Initialize Claude client
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key or api_key == 'your_api_key_here':
        return {'error': 'API key not configured'}
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
    except Exception as e:
        return {'error': f'Client initialization failed: {e}'}
    
    # Load and parse UIAutomator XML
    try:
        with open(uiautomator_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
    except Exception as e:
        return {'error': f'Failed to read UIAutomator file: {e}'}
    
    elements = extract_uiautomator_elements(xml_content)
    if not elements:
        return {'error': 'No clickable elements found'}
    
    # Encode image
    try:
        image_base64 = encode_image_base64(image_path)
    except Exception as e:
        return {'error': f'Failed to encode image: {e}'}
    
    # Create prompt
    prompt = create_enhanced_prompt(elements)
    
    # Call Claude API with Haiku model
    start_time = time.time()
    try:
        response = client.messages.create(
            model="claude-3-5-haiku-20241022",  # Using Haiku - fastest and cheapest
            max_tokens=200,
            temperature=temperature,
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
        
        # Parse JSON response - extract JSON from Claude's response
        try:
            # Try to find JSON in the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                result = json.loads(json_str)
            else:
                # Try direct parsing
                result = json.loads(response_text)
            
            if 'coordinates' in result and len(result['coordinates']) == 2:
                # Calculate distance to nearest element
                predicted = result['coordinates']
                min_distance = float('inf')
                
                for element in elements:
                    actual = element['coordinates']
                    distance = ((predicted[0] - actual[0]) ** 2 + (predicted[1] - actual[1]) ** 2) ** 0.5
                    if distance < min_distance:
                        min_distance = distance
                
                return {
                    'success': True,
                    'coordinates': predicted,
                    'distance': min_distance,
                    'response_time': response_time,
                    'parsing_success': True,
                    'available_elements': len(elements),
                    'raw_response': response_text,
                    'element_description': result.get('element', 'Unknown')
                }
            else:
                return {
                    'success': False,
                    'coordinates': None,
                    'distance': None,
                    'response_time': response_time,
                    'parsing_success': False,
                    'available_elements': len(elements),
                    'raw_response': response_text,
                    'error': 'Invalid coordinates format'
                }
        
        except json.JSONDecodeError:
            return {
                'success': False,
                'coordinates': None,
                'distance': None,
                'response_time': response_time,
                'parsing_success': False,
                'available_elements': len(elements),
                'raw_response': response_text,
                'error': 'JSON parsing failed'
            }
    
    except Exception as e:
        return {
            'success': False,
            'coordinates': None,
            'distance': None,
            'response_time': time.time() - start_time,
            'parsing_success': False,
            'available_elements': len(elements),
            'raw_response': str(e),
            'error': f'API call failed: {e}'
        }

def run_claude_haiku_test():
    """Run Claude Haiku test with 3 apps × 5 screenshots using optimal parameters."""
    
    # Optimal parameters discovered from testing
    TEMPERATURE = 0.05
    
    # Test data directory
    data_dir = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")
    
    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir}")
        return
    
    # Find all APK directories
    apk_dirs = [d for d in data_dir.iterdir() if d.is_dir()][:3]  # Limit to 3 apps
    
    if not apk_dirs:
        print("❌ No APK directories found")
        return
    
    print(f"🚀 Starting Claude Haiku test with {len(apk_dirs)} apps")
    print(f"💰 Using Claude 3.5 Haiku - The most cost-effective model")
    print(f"📊 Parameters: Temperature={TEMPERATURE}")
    print("=" * 60)
    
    # CSV output
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    csv_file = f"claude_haiku_results_{timestamp}.csv"
    
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'app', 'screenshot', 'success', 'distance', 'response_time', 
            'parsing_success', 'available_elements', 'coordinates_x', 
            'coordinates_y', 'element_description', 'temperature', 'error'
        ])
        
        total_tests = 0
        successful_tests = 0
        total_response_time = 0
        total_distance = 0
        
        for app_dir in apk_dirs:
            app_name = app_dir.name
            print(f"\n📱 Testing app: {app_name}")
            
            # Find screenshot files (limit to 5)
            screenshots = list(app_dir.glob("*.png"))[:5]
            
            for screenshot in screenshots:
                # Find corresponding UIAutomator file
                uiautomator_file = screenshot.with_suffix('.uiautomator')
                
                if not uiautomator_file.exists():
                    print(f"   ⚠️  UIAutomator file not found: {uiautomator_file.name}")
                    continue
                
                total_tests += 1
                print(f"   🧪 Testing: {screenshot.name}")
                
                # Run test
                result = test_claude_haiku(
                    str(screenshot), 
                    str(uiautomator_file), 
                    TEMPERATURE
                )
                
                total_response_time += result.get('response_time', 0)
                
                if result.get('success'):
                    successful_tests += 1
                    status = "✅"
                    distance = result.get('distance', 0)
                    total_distance += distance
                    print(f"      {status} Success! Distance: {distance:.1f}px, Time: {result.get('response_time', 0):.1f}s")
                else:
                    status = "❌"
                    error = result.get('error', 'Unknown error')
                    print(f"      {status} Failed: {error}")
                
                # Write to CSV
                coords = result.get('coordinates', [None, None])
                writer.writerow([
                    app_name,
                    screenshot.name,
                    result.get('success', False),
                    result.get('distance'),
                    result.get('response_time'),
                    result.get('parsing_success', False),
                    result.get('available_elements', 0),
                    coords[0] if coords else None,
                    coords[1] if coords else None,
                    result.get('element_description', ''),
                    TEMPERATURE,
                    result.get('error', '')
                ])
                f.flush()  # Ensure data is written immediately
    
    # Final summary
    success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
    avg_response_time = total_response_time / total_tests if total_tests > 0 else 0
    avg_distance = total_distance / successful_tests if successful_tests > 0 else 0
    
    print(f"\n🏆 CLAUDE HAIKU TEST SUMMARY:")
    print(f"   Total tests: {total_tests}")
    print(f"   Successful: {successful_tests} ({success_rate:.1f}%)")
    print(f"   Failed: {total_tests - successful_tests}")
    print(f"   Average response time: {avg_response_time:.1f}s")
    print(f"   Average distance (when successful): {avg_distance:.1f}px")
    print(f"   Results saved to: {csv_file}")
    
    # Cost comparison
    print(f"\n💰 COST COMPARISON:")
    print(f"   Haiku 3.5: ~$0.0008/image (80% cheaper than Sonnet)")
    print(f"   Sonnet 3.5: ~$0.003/image")
    print(f"   Qwen 2.5VL: Free (local)")
    
    # Recommendation based on results
    if success_rate >= 90:
        recommendation = "🎉 EXCELLENT - Haiku matches Sonnet at 80% lower cost!"
    elif success_rate >= 70:
        recommendation = "✅ GOOD - Haiku is cost-effective for production"
    elif success_rate >= 50:
        recommendation = "⚠️  MODERATE - Consider Haiku for non-critical paths"
    else:
        recommendation = "❌ POOR - Use Sonnet for accuracy or Qwen for cost"
    
    print(f"   Recommendation: {recommendation}")
    
    return {
        'total_tests': total_tests,
        'success_rate': success_rate,
        'avg_response_time': avg_response_time,
        'avg_distance': avg_distance,
        'csv_file': csv_file
    }

if __name__ == "__main__":
    print("🔬 Claude Haiku Test for RVAgent Phase 0 Validation")
    print("Testing the most cost-effective Claude model")
    print("Haiku 3.5: 80% cheaper, 2x faster than Sonnet")
    print()
    
    results = run_claude_haiku_test()
    
    if results:
        print(f"\n✅ Test completed. Analysis available in: {results['csv_file']}")
        print("📊 Compare with Sonnet (100%) and Qwen (72.1%) results")
    else:
        print("\n❌ Test failed to complete")