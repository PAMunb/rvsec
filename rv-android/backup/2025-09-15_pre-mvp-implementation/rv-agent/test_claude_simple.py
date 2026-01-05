#!/usr/bin/env python3
"""
Simple Claude API Test using direct HTTP requests (avoiding client issues)
"""

import os
import sys
import json
import csv
import time
import base64
import requests
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
    
    for i, element in enumerate(elements[:15]):  # Limit to 15 elements
        text = element['text'][:50] if element['text'] else f"Element_{i+1}"
        coords = element['coordinates']
        lines.append(f"{i+1}. '{text}' at position ({coords[0]}, {coords[1]})")
    
    lines.extend([
        "",
        "Return JSON format:",
        '{"coordinates": [x, y], "element": "description", "action": "click"}'
    ])
    
    return "\n".join(lines)

def test_claude_vision_http(image_path: str, uiautomator_path: str, temperature: float = 0.05) -> Dict[str, Any]:
    """Test Claude's vision using direct HTTP API calls."""
    
    # Get API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key or api_key == 'your_api_key_here':
        return {'error': 'API key not configured'}
    
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
    
    # Prepare HTTP request
    headers = {
        'Content-Type': 'application/json',
        'x-api-key': api_key,
        'anthropic-version': '2023-06-01'
    }
    
    payload = {
        'model': 'claude-3-5-sonnet-20241022',
        'max_tokens': 200,
        'temperature': temperature,
        'messages': [
            {
                'role': 'user',
                'content': [
                    {
                        'type': 'image',
                        'source': {
                            'type': 'base64',
                            'media_type': 'image/png',
                            'data': image_base64
                        }
                    },
                    {
                        'type': 'text',
                        'text': prompt
                    }
                ]
            }
        ]
    }
    
    # Call Claude API via HTTP
    start_time = time.time()
    try:
        response = requests.post(
            'https://api.anthropic.com/v1/messages',
            headers=headers,
            json=payload,
            timeout=30
        )
        
        response_time = time.time() - start_time
        
        if response.status_code != 200:
            return {
                'success': False,
                'coordinates': None,
                'distance': None,
                'response_time': response_time,
                'parsing_success': False,
                'available_elements': len(elements),
                'raw_response': f"HTTP {response.status_code}: {response.text}",
                'error': f'API error: {response.status_code}'
            }
        
        response_data = response.json()
        response_text = response_data['content'][0]['text']
        
        # Parse JSON response
        try:
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
                    'element_description': result.get('element', 'Unknown'),
                    'api_cost': response_data.get('usage', {})
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
            'error': f'Request failed: {e}'
        }

def run_claude_test():
    """Run Claude API test with 3 apps × 5 screenshots."""
    
    # Optimal parameters from Qwen testing
    TEMPERATURE = 0.05
    
    # Test data directory
    data_dir = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")
    
    if not data_dir.exists():
        print(f"❌ Data directory not found: {data_dir}")
        return
    
    # Find first 3 APK directories
    apk_dirs = [d for d in data_dir.iterdir() if d.is_dir()][:3]
    
    if not apk_dirs:
        print("❌ No APK directories found")
        return
    
    print(f"🚀 Starting Claude API test with {len(apk_dirs)} apps")
    print(f"📊 Parameters: Temperature={TEMPERATURE}")
    print("💰 Using HTTP requests to avoid client issues")
    print("=" * 60)
    
    # CSV output
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    csv_file = f"claude_http_results_{timestamp}.csv"
    
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'app', 'screenshot', 'success', 'distance', 'response_time', 
            'parsing_success', 'available_elements', 'coordinates_x', 
            'coordinates_y', 'element_description', 'temperature', 'error'
        ])
        
        total_tests = 0
        successful_tests = 0
        total_cost = 0
        
        for app_dir in apk_dirs:
            app_name = app_dir.name
            print(f"\n📱 Testing app: {app_name}")
            
            # Find first 5 screenshots
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
                result = test_claude_vision_http(
                    str(screenshot), 
                    str(uiautomator_file), 
                    TEMPERATURE
                )
                
                if result.get('success'):
                    successful_tests += 1
                    status = "✅"
                    distance = result.get('distance', 0)
                    print(f"      {status} Success! Distance: {distance:.1f}px, Time: {result.get('response_time', 0):.1f}s")
                    
                    # Track API cost
                    cost_info = result.get('api_cost', {})
                    if cost_info:
                        print(f"         💰 Usage: {cost_info}")
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
                f.flush()
    
    # Final summary
    success_rate = (successful_tests / total_tests) * 100 if total_tests > 0 else 0
    
    print(f"\n🏆 CLAUDE HTTP API TEST SUMMARY:")
    print(f"   Total tests: {total_tests}")
    print(f"   Successful: {successful_tests} ({success_rate:.1f}%)")
    print(f"   Failed: {total_tests - successful_tests}")
    print(f"   Results saved to: {csv_file}")
    
    # Comparison with Qwen results (72.1%)
    if success_rate >= 65:
        recommendation = "🎉 EXCELLENT - Claude matches Qwen performance!"
    elif success_rate >= 50:
        recommendation = "✅ GOOD - Claude is viable for RVAgent"
    elif success_rate >= 35:
        recommendation = "⚠️  MODERATE - Claude needs optimization"
    else:
        recommendation = "❌ POOR - Qwen significantly outperforms Claude"
    
    print(f"   Recommendation: {recommendation}")
    print(f"   Qwen baseline: 72.1% success rate")
    
    return {
        'total_tests': total_tests,
        'success_rate': success_rate,
        'csv_file': csv_file
    }

if __name__ == "__main__":
    print("🔬 Claude HTTP API Test for RVAgent Phase 0 Validation")
    print("Using direct HTTP requests to avoid client issues")
    print("Optimal parameters from Qwen testing: T=0.05")
    print()
    
    results = run_claude_test()
    
    if results:
        print(f"\n✅ Test completed. Analysis available in: {results['csv_file']}")
        print("💰 Check logs for API usage costs")
    else:
        print("\n❌ Test failed to complete")