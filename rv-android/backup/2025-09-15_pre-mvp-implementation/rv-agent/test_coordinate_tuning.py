#!/usr/bin/env python3
"""
Coordinate Precision Tuning Test
Tests different prompt strategies to improve coordinate accuracy.
"""

import os
import time
import base64
from pathlib import Path
import json
import xml.etree.ElementTree as ET
import math

def extract_clickable_elements_from_xml(xml_path):
    """Extract clickable elements from XML file."""
    if not xml_path.exists():
        return []
    
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        clickable_elements = []
        for elem in root.iter():
            if elem.get('clickable') == 'true':
                bounds = elem.get('bounds')
                if bounds:
                    # Parse bounds: [x1,y1][x2,y2]
                    bounds_parts = bounds.replace('[', '').replace(']', ',').split(',')
                    if len(bounds_parts) >= 4:
                        x1, y1, x2, y2 = map(int, bounds_parts[:4])
                        center_x = (x1 + x2) // 2
                        center_y = (y1 + y2) // 2
                        
                        element_info = {
                            'center': (center_x, center_y),
                            'bounds': (x1, y1, x2, y2),
                            'text': elem.get('text', ''),
                            'resource_id': elem.get('resource-id', ''),
                            'class': elem.get('class', ''),
                            'content_desc': elem.get('content-desc', '')
                        }
                        clickable_elements.append(element_info)
        
        return clickable_elements
    except Exception as e:
        print(f"Error parsing XML: {e}")
        return []

def test_coordinate_prompts():
    """Test different prompt strategies for coordinate precision."""
    
    print("Coordinate Precision Tuning Test")
    print("=" * 50)
    
    # Define different prompt strategies
    prompts = {
        "basic": """You are an expert Android UI automation assistant. 

Analyze this Android app screenshot and identify a clickable UI element that would be good for testing.

Please respond with ONLY the coordinates in this exact format:
COORDINATES: (x, y)

Where x and y are the pixel coordinates of the center of a clickable element.

Choose an element that is:
1. Clearly clickable (button, menu item, etc.)
2. Visible and not obscured
3. Not a system UI element (status bar, navigation bar)
4. Likely to be functionally important for testing

Respond only with the coordinate format shown above, nothing else.""",

        "detailed": """You are a precise Android UI automation assistant specializing in accurate coordinate detection.

TASK: Analyze this Android screenshot and identify the exact pixel coordinates of ONE clickable element.

INSTRUCTIONS:
1. Look carefully at the image and identify all visible clickable elements
2. Choose the most prominent clickable element (button, menu item, icon, etc.)
3. Calculate the EXACT CENTER COORDINATES of this element
4. Ignore system UI elements (status bar, navigation buttons)
5. Provide coordinates as precise pixel values

RESPONSE FORMAT (exact format required):
COORDINATES: (x, y)

Where:
- x = horizontal pixel position from left edge
- y = vertical pixel position from top edge
- Both values should be integers

EXAMPLE: COORDINATES: (540, 960)

Respond with ONLY the coordinates in the exact format above.""",

        "step_by_step": """You are an Android UI analysis expert. Analyze this screenshot step-by-step.

STEP 1: Identify all clickable elements you can see (buttons, icons, menu items, text fields, etc.)

STEP 2: Select the most important/prominent clickable element for testing

STEP 3: Determine the exact center coordinates of this element

STEP 4: Provide coordinates in the required format

Focus on precision - measure the element boundaries carefully and find the exact center point.

Avoid system UI elements like status bar or navigation bar.

REQUIRED RESPONSE FORMAT:
COORDINATES: (x, y)

Replace x and y with the exact integer pixel coordinates of the element center.""",

        "visual_grid": """You are an Android UI coordinate detection specialist.

Analyze this Android screenshot using a mental grid system:

1. Examine the entire screen systematically
2. Identify clickable UI elements (buttons, icons, menu items, etc.)
3. For the most prominent clickable element:
   - Estimate its left and right boundaries
   - Estimate its top and bottom boundaries  
   - Calculate the center point: ((left + right) / 2, (top + bottom) / 2)

Important: Be very precise with pixel measurements. The screen has specific dimensions and each pixel matters for automation accuracy.

Exclude system UI elements (status bar, navigation bar).

OUTPUT FORMAT (exact format):
COORDINATES: (x, y)

Where x and y are the exact integer pixel coordinates of the element's center.""",

        "explanatory": """You are an Android UI automation expert. Analyze this screenshot and explain your decision-making process.

ANALYSIS PROCESS:
1. First, describe what you see in the screenshot (app type, main UI elements, layout)
2. Identify all clickable elements you can observe
3. Choose the most suitable element for testing and explain why
4. Describe the exact location and boundaries of this element
5. Calculate the center coordinates

RESPONSE FORMAT:
ANALYSIS: [Describe what you see in the screenshot]
ELEMENTS_FOUND: [List the clickable elements you identified]
SELECTED_ELEMENT: [Which element you chose and why]
LOCATION_DESCRIPTION: [Describe where the element is positioned and its boundaries]
ACTION: Click on [element description] at coordinates (x, y)
COORDINATES: (x, y)

This explanation helps us understand your reasoning and validate the coordinate accuracy.

Example:
ANALYSIS: This is a settings screen with multiple menu items
ELEMENTS_FOUND: Profile button, Settings menu, Back arrow
SELECTED_ELEMENT: Profile button - most prominent and functionally important
LOCATION_DESCRIPTION: Large button in center area, roughly from x=200 to x=600, y=800 to y=900
ACTION: Click on Profile button at coordinates (400, 850)
COORDINATES: (400, 850)"""
    }
    
    # Find test screenshots and XML files
    workspace_root = Path("../..").resolve()
    test_data = []
    
    screenshot_files = sorted(list(workspace_root.glob("screenshot_*.png")))[:5]  # Test with 5 screenshots
    
    for screenshot_path in screenshot_files:
        # Look for corresponding XML file
        xml_name = screenshot_path.name.replace('.png', '.xml')
        xml_path = workspace_root / xml_name
        
        if xml_path.exists():
            elements = extract_clickable_elements_from_xml(xml_path)
            if elements:
                test_data.append({
                    'screenshot': screenshot_path,
                    'xml_path': xml_path,
                    'elements': elements
                })
    
    if not test_data:
        print("❌ No test data found (need screenshot + XML pairs)")
        return
    
    print(f"📱 Found {len(test_data)} test cases with ground truth")
    
    try:
        from langchain_ollama import ChatOllama
        from langchain_core.messages import HumanMessage
        
        llm = ChatOllama(
            model="llama3.2-vision:11b",
            temperature=0.1,
            base_url="http://localhost:11434"
        )
        
        results = {}
        
        for prompt_name, prompt_text in prompts.items():
            print(f"\n🧪 Testing prompt strategy: {prompt_name.upper()}")
            results[prompt_name] = []
            
            for i, test_case in enumerate(test_data):
                screenshot_path = test_case['screenshot']
                elements = test_case['elements']
                
                print(f"   📸 {screenshot_path.name} ({i+1}/{len(test_data)})")
                
                try:
                    # Read and encode image
                    with open(screenshot_path, "rb") as image_file:
                        image_data = base64.b64encode(image_file.read()).decode('utf-8')
                    
                    # Create message
                    message = HumanMessage(content=[
                        {"type": "text", "text": prompt_text},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
                    ])
                    
                    # Get response
                    start_time = time.time()
                    response = llm.invoke([message])
                    response_time = time.time() - start_time
                    
                    # Parse coordinates
                    coords = None
                    try:
                        response_text = response.content.strip()
                        if "COORDINATES:" in response_text:
                            coord_part = response_text.split("COORDINATES:")[1].strip()
                            # Extract (x, y) format
                            coord_part = coord_part.replace('(', '').replace(')', '')
                            x, y = map(int, coord_part.split(','))
                            coords = (x, y)
                    except:
                        pass
                    
                    # Calculate accuracy
                    min_distance = float('inf')
                    closest_element = None
                    
                    if coords and elements:
                        for element in elements:
                            distance = math.sqrt(
                                (coords[0] - element['center'][0]) ** 2 + 
                                (coords[1] - element['center'][1]) ** 2
                            )
                            if distance < min_distance:
                                min_distance = distance
                                closest_element = element
                    
                    result = {
                        'screenshot': str(screenshot_path),
                        'generated_coords': coords,
                        'closest_element': closest_element['center'] if closest_element else None,
                        'distance': min_distance if min_distance != float('inf') else None,
                        'accuracy': min_distance < 50 if min_distance != float('inf') else False,
                        'response_time': response_time,
                        'raw_response': response.content
                    }
                    
                    results[prompt_name].append(result)
                    
                    if coords:
                        accuracy_symbol = "✅" if result['accuracy'] else "❌"
                        print(f"      {accuracy_symbol} Generated: {coords}, Distance: {min_distance:.0f}px")
                    else:
                        print(f"      ❌ Failed to parse coordinates")
                    
                except Exception as e:
                    print(f"      ❌ Error: {e}")
                    continue
        
        # Analyze results
        print(f"\n📊 RESULTS SUMMARY")
        print("=" * 50)
        
        for prompt_name, prompt_results in results.items():
            successful = [r for r in prompt_results if r['generated_coords'] is not None]
            accurate = [r for r in successful if r['accuracy']]
            
            accuracy_rate = len(accurate) / len(successful) * 100 if successful else 0
            avg_distance = sum(r['distance'] for r in successful if r['distance'] is not None) / len(successful) if successful else 0
            avg_time = sum(r['response_time'] for r in prompt_results) / len(prompt_results) if prompt_results else 0
            
            print(f"\n{prompt_name.upper()}:")
            print(f"  Success rate: {len(successful)}/{len(prompt_results)} ({len(successful)/len(prompt_results)*100:.1f}%)")
            print(f"  Accuracy rate: {len(accurate)}/{len(successful)} ({accuracy_rate:.1f}%)")
            print(f"  Avg distance: {avg_distance:.1f}px")
            print(f"  Avg time: {avg_time:.1f}s")
        
        # Save detailed results
        with open("coordinate_tuning_results.json", "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Detailed results saved to: coordinate_tuning_results.json")
        
        return results
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    test_coordinate_prompts()