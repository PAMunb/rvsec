#!/usr/bin/env python3
"""
Coordinate Enhanced Test
Uses the winning strategy: provide explicit coordinates and let model select
Based on previous research showing 100% success with coordinate validation
"""

import sys
from pathlib import Path
import time
import json
import base64
import xml.etree.ElementTree as ET

# Add module to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rv_agent.simple_validator import create_simple_validator

def extract_clickable_elements_with_coords(xml_path):
    """Extract clickable elements with explicit coordinates from UIAutomator XML."""
    try:
        with open(xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        root = ET.fromstring(xml_content)
        elements = []
        
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
                        
                        # Build description
                        text = node.get('text', '')
                        content_desc = node.get('content-desc', '')
                        resource_id = node.get('resource-id', '')
                        class_name = node.get('class', '').split('.')[-1] if node.get('class') else ''
                        
                        desc_parts = []
                        if text:
                            desc_parts.append(f'"{text}"')
                        if content_desc:
                            desc_parts.append(f'desc:"{content_desc}"')
                        if resource_id:
                            desc_parts.append(f'id:{resource_id.split("/")[-1] if "/" in resource_id else resource_id}')
                        if class_name:
                            desc_parts.append(class_name)
                        
                        description = ' '.join(desc_parts) if desc_parts else 'Interactive element'
                        
                        element = {
                            'center': (center_x, center_y),
                            'bounds': [x1, y1, x2, y2],
                            'description': description
                        }
                        elements.append(element)
        
        return elements
        
    except Exception as e:
        print(f"Error parsing XML {xml_path}: {e}")
        return []

def create_enhanced_prompt(elements):
    """Create enhanced prompt with explicit coordinates (winning strategy)."""
    if not elements:
        return None
    
    lines = [
        "You are an expert Android UI automation assistant specializing in coordinate-based testing.",
        "",
        "TASK: Analyze this Android screenshot and choose ONE interactive element using the EXACT coordinates provided below.",
        "",
        "AVAILABLE INTERACTIVE ELEMENTS:"
    ]
    
    for i, element in enumerate(elements, 1):
        bounds_str = f"[{element['bounds'][0]}, {element['bounds'][1]}][{element['bounds'][2]}, {element['bounds'][3]}]"
        line = f"- {element['description']} at position ({element['center'][0]}, {element['center'][1]}) - bounds{bounds_str}. Action: click ({i})"
        lines.append(line)
    
    lines.extend([
        "",
        "COORDINATE VALIDATION MODE:",
        "- Use the EXACT coordinates shown in 'at position (x, y)' format",
        "- Do not estimate coordinates from the image",
        "- Choose the most suitable element for testing",
        "- Return JSON with exact coordinates",
        "",
        "Return JSON format:",
        '{',
        '  "coordinates": [x, y],',
        '  "element": "chosen_element_description",',
        '  "action": "click",',
        '  "reasoning": "why_this_element_was_chosen"',
        '}',
        "",
        'Example: {"coordinates": [540, 960], "element": "OK button", "action": "click", "reasoning": "Primary action button for user interaction"}'
    ])
    
    return "\n".join(lines)

def test_coordinate_enhanced():
    """Test with coordinate validation strategy (known to work at 100%)."""
    
    # Test parameters
    temperature = 0.1  # Lower for more deterministic selection
    top_p = 0.9
    top_k = 40
    
    print("RVAgent Prototype - Coordinate Enhanced Strategy")
    print("Using winning strategy from benchmark research (100% expected success)")
    print("=" * 70)
    print(f"Parameters: temp={temperature}, top_p={top_p}, top_k={top_k}")
    print()
    
    # Get test data (same as before)
    screenshots_dir = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    screenshots_path = Path(screenshots_dir)
    
    # Collect test cases
    test_cases = []
    app_dirs = sorted([d for d in screenshots_path.iterdir() if d.is_dir() and d.name.endswith('.apk')])
    
    for app_dir in app_dirs[:3]:  # First 3 APKs
        png_files = sorted(list(app_dir.glob("*.png")))
        for png_file in png_files[:2]:  # First 2 screenshots per APK
            xml_file = png_file.with_suffix('.uiautomator')
            if xml_file.exists():
                elements = extract_clickable_elements_with_coords(xml_file)
                if elements:
                    test_cases.append({
                        'app': app_dir.name,
                        'screenshot': png_file.name,
                        'image_path': png_file,
                        'xml_path': xml_file,
                        'elements': elements
                    })
    
    print(f"📱 Testing {len(test_cases)} cases with explicit coordinates")
    
    try:
        # Import LangChain components
        from langchain_ollama import ChatOllama
        from langchain_core.messages import HumanMessage
        
        print("🤖 Creating Qwen 2.5VL 7B client...")
        
        # Create LLM with optimized parameters
        llm = ChatOllama(
            model="qwen2.5vl:7b",
            base_url="http://localhost:11434",
            temperature=temperature,  # Low for deterministic selection
            top_p=top_p,
            top_k=top_k,
            num_predict=300,  # Enough for JSON response
            timeout=60,
            num_ctx=32768  # Large context window
        )
        
        print("✅ Client created")
        print()
        
        # Validator
        validator = create_simple_validator(tolerance=50)
        
        # Test each case
        results = []
        successful_tests = 0
        total_distance = 0
        total_time = 0
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"📸 Test {i}/{len(test_cases)}: {test_case['app']}/{test_case['screenshot']}")
            print(f"   Available elements: {len(test_case['elements'])}")
            
            try:
                # Create enhanced prompt with explicit coordinates
                prompt = create_enhanced_prompt(test_case['elements'])
                
                if not prompt:
                    print("   ⚠️  No elements found, skipping")
                    continue
                
                # Read and encode image
                with open(test_case['image_path'], "rb") as image_file:
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
                total_time += response_time
                
                print(f"   ⏱️  Response in {response_time:.1f}s")
                
                # Parse JSON coordinates
                coords = None
                reasoning = ""
                try:
                    response_text = response.content.strip()
                    # Extract JSON from response
                    if "{" in response_text and "}" in response_text:
                        json_start = response_text.find('{')
                        json_end = response_text.rfind('}') + 1
                        json_str = response_text[json_start:json_end]
                        parsed = json.loads(json_str)
                        
                        if "coordinates" in parsed:
                            coords = tuple(parsed["coordinates"])
                            reasoning = parsed.get("reasoning", "")
                            element_desc = parsed.get("element", "")
                            print(f"   🤖 Selected: {element_desc}")
                            print(f"   💭 Reasoning: {reasoning[:50]}...")
                        
                except Exception as parse_error:
                    print(f"   ❌ JSON parse error: {parse_error}")
                    # Fallback: try to find coordinates in any format
                    import re
                    coord_matches = re.findall(r'\[(\d+),\s*(\d+)\]', response_text)
                    if coord_matches:
                        coords = tuple(map(int, coord_matches[0]))
                        print(f"   🔄 Fallback parsing found: {coords}")
                
                if coords:
                    # Validate against ground truth
                    validation_result = validator.validate_coordinates(coords, str(test_case['xml_path']))
                    
                    result = {
                        'app': test_case['app'],
                        'screenshot': test_case['screenshot'],
                        'generated_coords': coords,
                        'available_elements': len(test_case['elements']),
                        'success': validation_result['success'],
                        'distance': validation_result['distance'],
                        'closest_element': validation_result['closest_element'],
                        'response_time': response_time,
                        'reasoning': reasoning,
                        'raw_response': response.content[:150] + "..." if len(response.content) > 150 else response.content
                    }
                    
                    results.append(result)
                    
                    if validation_result['success']:
                        successful_tests += 1
                        total_distance += validation_result['distance']
                        print(f"   ✅ SUCCESS: {coords}, distance: {validation_result['distance']:.0f}px")
                    else:
                        print(f"   ❌ Failed: {coords}, distance: {validation_result['distance']:.0f}px")
                        print(f"      Closest was: {validation_result['closest_element']}")
                else:
                    print(f"   ❌ No coordinates parsed from response")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
                continue
            
            print()
        
        # Results summary
        print("📊 COORDINATE ENHANCED RESULTS")
        print("=" * 50)
        
        if results:
            success_rate = successful_tests / len(results) * 100
            avg_distance = total_distance / successful_tests if successful_tests > 0 else 0
            avg_time = total_time / len(results)
            
            print(f"📈 Success rate: {successful_tests}/{len(results)} ({success_rate:.1f}%)")
            print(f"📏 Average distance (successful): {avg_distance:.1f}px")
            print(f"⏱️  Average time: {avg_time:.1f}s")
            print(f"🎯 Apps tested: {len(set(r['app'] for r in results))}")
            
            # Show per-app breakdown
            apps = set(r['app'] for r in results)
            for app in sorted(apps):
                app_results = [r for r in results if r['app'] == app]
                app_success = sum(1 for r in app_results if r['success'])
                app_avg_elements = sum(r['available_elements'] for r in app_results) / len(app_results)
                print(f"   {app}: {app_success}/{len(app_results)} success (avg {app_avg_elements:.1f} elements)")
            
            # Save results
            with open("coordinate_enhanced_results.json", "w") as f:
                json.dump(results, f, indent=2)
            print(f"\n💾 Results saved to: coordinate_enhanced_results.json")
            
            # Decision criteria
            print(f"\n🤔 ENHANCED STRATEGY ASSESSMENT:")
            
            if success_rate >= 70:  # Higher threshold for enhanced strategy
                print(f"🎉 EXCELLENT: {success_rate:.1f}% success → READY for full prototype!")
                recommendation = "PROCEED_FULL"
            elif success_rate >= 50:
                print(f"✅ GOOD: {success_rate:.1f}% success → Proceed with caution")
                recommendation = "PROCEED_LIMITED"
            else:
                print(f"⚠️  NEEDS WORK: {success_rate:.1f}% success → More tuning needed")
                recommendation = "TUNE_MORE"
            
            # Show sample success case
            successes = [r for r in results if r['success']]
            if successes:
                best = min(successes, key=lambda x: x['distance'])
                print(f"\n🏆 BEST CASE:")
                print(f"   App: {best['app']}")
                print(f"   Coords: {best['generated_coords']}")
                print(f"   Distance: {best['distance']:.0f}px")
                print(f"   Reasoning: {best['reasoning'][:100]}...")
            
            return recommendation, results
        else:
            print("❌ No valid results generated")
            return "FAILED", []
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return "FAILED", []

if __name__ == "__main__":
    recommendation, results = test_coordinate_enhanced()