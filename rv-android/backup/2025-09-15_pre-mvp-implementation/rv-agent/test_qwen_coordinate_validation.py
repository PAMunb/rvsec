#!/usr/bin/env python3
"""
Qwen 2.5VL 7B Coordinate Validation Test
Based on benchmark results showing Qwen as champion (98.3% success rate)
Tests with real app data from /home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots
"""

import os
import time
import base64
import json
import math
from pathlib import Path

def extract_clickable_from_uiautomator(uiautomator_file):
    """Extract clickable elements from .uiautomator XML file."""
    try:
        import xml.etree.ElementTree as ET
        
        with open(uiautomator_file, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        root = ET.fromstring(xml_content)
        elements = []
        
        # Find all nodes with clickable="true"
        for node in root.iter('node'):
            if node.get('clickable') == 'true':
                bounds_str = node.get('bounds')
                if bounds_str:
                    # Parse bounds: [x1,y1][x2,y2]
                    import re
                    bounds_match = re.findall(r'\[(\d+),(\d+)\]', bounds_str)
                    if len(bounds_match) == 2:
                        x1, y1 = map(int, bounds_match[0])
                        x2, y2 = map(int, bounds_match[1])
                        
                        center_x = (x1 + x2) // 2
                        center_y = (y1 + y2) // 2
                        
                        element = {
                            'center': (center_x, center_y),
                            'bounds': [x1, y1, x2, y2],
                            'text': node.get('text', ''),
                            'resource_id': node.get('resource-id', ''),
                            'class': node.get('class', ''),
                            'content_desc': node.get('content-desc', '')
                        }
                        elements.append(element)
        
        return elements
        
    except Exception as e:
        print(f"Error parsing UIAutomator file {uiautomator_file}: {e}")
        return []

def create_enhanced_description(elements):
    """Create enhanced description with explicit coordinates (winning strategy)."""
    if not elements:
        return "No clickable elements found in this screen."
    
    lines = [
        "Current UI Elements and Available Actions:",
        "The screen contains the following interactive elements with precise coordinates:",
        ""
    ]
    
    for i, element in enumerate(elements, 1):
        bounds_str = f"[{element['bounds'][0]}, {element['bounds'][1]}][{element['bounds'][2]}, {element['bounds'][3]}]"
        
        # Build element description
        desc_parts = []
        if element['text']:
            desc_parts.append(f'"{element["text"]}"')
        if element['content_desc']:
            desc_parts.append(f'desc:"{element["content_desc"]}"')
        if element['class']:
            class_short = element['class'].split('.')[-1]
            desc_parts.append(f'{class_short}')
        
        description = ' '.join(desc_parts) if desc_parts else f'Element{i}'
        
        line = f"- {description} at position ({element['center'][0]}, {element['center'][1]}) - bounds{bounds_str}. Actions: click ({i})"
        lines.append(line)
    
    lines.extend([
        "",
        "Screen resolution: 1080x1920 pixels", 
        "All coordinates are provided as 'at position (x, y)' for precise interaction.",
        "Use the EXACT coordinates shown above for accurate element targeting."
    ])
    
    return "\n".join(lines)

def test_qwen_coordinate_validation():
    """Test Qwen 2.5VL 7B with coordinate validation strategy."""
    
    print("Qwen 2.5VL 7B Coordinate Validation Test")
    print("=" * 55)
    print("🏆 Using benchmark champion model (98.3% success rate)")
    
    # Find test data
    test_data_root = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")
    
    if not test_data_root.exists():
        print(f"❌ Test data directory not found: {test_data_root}")
        return
    
    # Collect test cases
    test_cases = []
    app_dirs = [d for d in test_data_root.iterdir() if d.is_dir()]
    
    for app_dir in sorted(app_dirs)[:3]:  # Test first 3 apps
        png_files = sorted(list(app_dir.glob("*.png")))[:2]  # 2 screenshots per app
        
        for png_file in png_files:
            uiautomator_file = png_file.with_suffix('.uiautomator')
            
            if uiautomator_file.exists():
                elements = extract_clickable_from_uiautomator(uiautomator_file)
                if elements:
                    test_cases.append({
                        'app': app_dir.name,
                        'screenshot': png_file,
                        'uiautomator_file': uiautomator_file,
                        'elements': elements
                    })
    
    if not test_cases:
        print("❌ No valid test cases found (need .png + .uiautomator pairs)")
        return
    
    print(f"📱 Found {len(test_cases)} test cases from {len(set(tc['app'] for tc in test_cases))} apps")
    
    # Test strategies
    strategies = {
        "coordinate_validation": """You are an expert Android UI automation assistant specializing in coordinate-based testing.

TASK: Analyze this Android screenshot and choose ONE interactive element using the EXACT coordinates provided below.

{enhanced_description}

COORDINATE VALIDATION MODE: 
- Use the EXACT coordinates shown in "at position (x, y)" format
- Do not estimate coordinates from the image
- Choose the most suitable element for testing
- Return JSON with exact coordinates

Return JSON format:
{{
  "coordinates": [x, y],
  "element": "chosen_element_description",
  "action": "click",
  "reasoning": "why_this_element_was_chosen"
}}

Example: {{"coordinates": [540, 960], "element": "OK button", "action": "click", "reasoning": "Primary action button for user interaction"}}""",

        "explanatory": """You are an Android UI automation expert. Analyze this screenshot and explain your decision-making process.

{enhanced_description}

ANALYSIS PROCESS:
1. First, describe what you see in the screenshot (app type, main UI elements, layout)
2. Identify all clickable elements you can observe
3. Choose the most suitable element for testing and explain why
4. Describe the exact location and boundaries of this element
5. Use the provided coordinates exactly as shown

RESPONSE FORMAT:
ANALYSIS: [Describe what you see in the screenshot]
ELEMENTS_FOUND: [List the clickable elements you identified]
SELECTED_ELEMENT: [Which element you chose and why]
LOCATION_DESCRIPTION: [Describe where the element is positioned and its boundaries]
ACTION: Click on [element description] at coordinates (x, y)
COORDINATES: (x, y)

Use the EXACT coordinates from "at position (x, y)" shown above."""
    }
    
    try:
        from langchain_ollama import ChatOllama
        from langchain_core.messages import HumanMessage
        
        print("🤖 Creating Qwen 2.5VL 7B client...")
        llm = ChatOllama(
            model="qwen2.5vl:7b",  # Benchmark champion model
            temperature=0.1,  # Low for precision
            base_url="http://localhost:11434"
        )
        
        results = {}
        
        for strategy_name, prompt_template in strategies.items():
            print(f"\n🧪 Testing strategy: {strategy_name.upper()}")
            results[strategy_name] = []
            
            for i, test_case in enumerate(test_cases[:4]):  # Test first 4 cases
                app = test_case['app']
                screenshot = test_case['screenshot']
                elements = test_case['elements']
                
                print(f"   📸 {app}/{screenshot.name} ({i+1}/{min(4, len(test_cases))}) - {len(elements)} elements")
                
                try:
                    # Create enhanced description
                    enhanced_desc = create_enhanced_description(elements)
                    
                    # Fill prompt template
                    prompt = prompt_template.format(enhanced_description=enhanced_desc)
                    
                    # Read and encode image
                    with open(screenshot, "rb") as image_file:
                        image_data = base64.b64encode(image_file.read()).decode('utf-8')
                    
                    # Create message
                    message = HumanMessage(content=[
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
                    ])
                    
                    # Get response
                    start_time = time.time()
                    response = llm.invoke([message])
                    response_time = time.time() - start_time
                    
                    print(f"      ⏱️  Response in {response_time:.1f}s")
                    
                    # Parse coordinates
                    coords = None
                    try:
                        response_text = response.content.strip()
                        
                        if strategy_name == "coordinate_validation":
                            # Try to parse JSON
                            if "{" in response_text and "}" in response_text:
                                json_str = response_text[response_text.find('{'):response_text.rfind('}')+1]
                                parsed = json.loads(json_str)
                                if "coordinates" in parsed:
                                    coords = tuple(parsed["coordinates"])
                        else:
                            # Parse from explanatory format
                            if "COORDINATES:" in response_text:
                                coord_line = [line for line in response_text.split('\n') if 'COORDINATES:' in line][0]
                                coord_part = coord_line.split('COORDINATES:')[1].strip()
                                coord_part = coord_part.replace('(', '').replace(')', '')
                                x, y = map(int, coord_part.split(','))
                                coords = (x, y)
                    except Exception as parse_err:
                        print(f"      ❌ Parse error: {parse_err}")
                        coords = None
                    
                    # Validate accuracy
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
                    
                    # Store result
                    result = {
                        'app': app,
                        'screenshot': str(screenshot),
                        'generated_coords': coords,
                        'closest_element': closest_element['center'] if closest_element else None,
                        'distance': min_distance if min_distance != float('inf') else None,
                        'accuracy': min_distance < 50 if min_distance != float('inf') else False,
                        'response_time': response_time,
                        'raw_response': response.content[:300] + "..." if len(response.content) > 300 else response.content
                    }
                    
                    results[strategy_name].append(result)
                    
                    # Show result
                    if coords:
                        accuracy_symbol = "✅" if result['accuracy'] else "❌"
                        print(f"      {accuracy_symbol} Generated: {coords}, Distance: {min_distance:.0f}px")
                        
                        # Show reasoning for explanatory strategy
                        if strategy_name == "explanatory" and "ANALYSIS:" in response.content:
                            analysis_part = response.content.split("ANALYSIS:")[1].split("\n")[0][:100]
                            print(f"      💭 Analysis: {analysis_part}...")
                    else:
                        print(f"      ❌ Failed to parse coordinates")
                    
                except Exception as e:
                    print(f"      ❌ Error: {e}")
                    continue
        
        # Print summary
        print(f"\n📊 QWEN 2.5VL 7B RESULTS SUMMARY")
        print("=" * 55)
        
        for strategy_name, strategy_results in results.items():
            successful = [r for r in strategy_results if r['generated_coords'] is not None]
            accurate = [r for r in successful if r['accuracy']]
            
            accuracy_rate = len(accurate) / len(successful) * 100 if successful else 0
            avg_distance = sum(r['distance'] for r in successful if r['distance'] is not None) / len(successful) if successful else 0
            avg_time = sum(r['response_time'] for r in strategy_results) / len(strategy_results) if strategy_results else 0
            
            print(f"\n🧪 {strategy_name.upper()}:")
            print(f"   Success rate: {len(successful)}/{len(strategy_results)} ({len(successful)/len(strategy_results)*100:.1f}%)")
            print(f"   Accuracy rate: {len(accurate)}/{len(successful)} ({accuracy_rate:.1f}%)")
            print(f"   Avg distance: {avg_distance:.1f}px")
            print(f"   Avg time: {avg_time:.1f}s")
            
            if accurate:
                print(f"   🎯 Best case: {min(r['distance'] for r in accurate if r['distance'] is not None):.1f}px")
        
        # Save results
        with open("qwen_coordinate_validation_results.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Detailed results saved to: qwen_coordinate_validation_results.json")
        
        return results
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None

if __name__ == "__main__":
    test_qwen_coordinate_validation()