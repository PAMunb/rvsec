#!/usr/bin/env python3
"""
Full Prototype Execution
Based on successful coordinate enhanced strategy (50% success rate validated)
Executes comprehensive testing with multiple parameter combinations
"""

import sys
from pathlib import Path
import time
import json
import base64
import xml.etree.ElementTree as ET
from itertools import product
from datetime import datetime

# Add module to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rv_agent.simple_validator import create_simple_validator

def extract_clickable_elements_with_coords(xml_path):
    """Extract clickable elements with explicit coordinates."""
    try:
        with open(xml_path, 'r', encoding='utf-8') as f:
            xml_content = f.read()
        
        root = ET.fromstring(xml_content)
        elements = []
        
        for node in root.iter('node'):
            if node.get('clickable') == 'true':
                bounds_str = node.get('bounds')
                if bounds_str:
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
    """Create enhanced prompt with explicit coordinates."""
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
        'Example: {"coordinates": [540, 960], "element": "OK button", "action": "click", "reasoning": "Primary action button"}'
    ])
    
    return "\n".join(lines)

def run_full_prototype():
    """Run comprehensive prototype testing."""
    
    print("RVAgent Prototype - Full Execution")
    print("=" * 50)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Parameter combinations (limited set for initial prototype)
    parameter_combinations = [
        # Optimized parameters from validation
        {"temperature": 0.1, "top_p": 0.9, "top_k": 40},
        # Alternative conservative set
        {"temperature": 0.05, "top_p": 0.8, "top_k": 30},
        # Slightly more creative set
        {"temperature": 0.2, "top_p": 0.9, "top_k": 50},
    ]
    
    # Get test data
    screenshots_dir = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    screenshots_path = Path(screenshots_dir)
    
    # Collect test cases (expand to more apps and screenshots)
    test_cases = []
    app_dirs = sorted([d for d in screenshots_path.iterdir() if d.is_dir() and d.name.endswith('.apk')])
    
    for app_dir in app_dirs[:5]:  # First 5 APKs (increased from 3)
        png_files = sorted(list(app_dir.glob("*.png")))
        for png_file in png_files[:3]:  # First 3 screenshots per APK (increased from 2)
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
    
    total_tests = len(test_cases) * len(parameter_combinations)
    print(f"📱 Test plan:")
    print(f"   Apps: {len(set(tc['app'] for tc in test_cases))}")
    print(f"   Screenshots: {len(test_cases)}")
    print(f"   Parameter sets: {len(parameter_combinations)}")
    print(f"   Total tests: {total_tests}")
    print(f"   Estimated time: {total_tests * 2.5 / 60:.1f} minutes")
    print()
    
    try:
        # Import LangChain components
        from langchain_ollama import ChatOllama
        from langchain_core.messages import HumanMessage
        
        # Validator
        validator = create_simple_validator(tolerance=50)
        
        # Store all results
        all_results = []
        
        # Test each parameter combination
        for param_idx, params in enumerate(parameter_combinations, 1):
            print(f"🧪 PARAMETER SET {param_idx}/{len(parameter_combinations)}")
            print(f"   temp={params['temperature']}, top_p={params['top_p']}, top_k={params['top_k']}")
            
            # Create LLM with current parameters
            print("   🤖 Creating client...")
            llm = ChatOllama(
                model="qwen2.5vl:7b",
                base_url="http://localhost:11434",
                temperature=params['temperature'],
                top_p=params['top_p'], 
                top_k=params['top_k'],
                num_predict=300,
                timeout=90,  # Increased timeout
                num_ctx=32768
            )
            
            print("   ✅ Client ready")
            
            # Test results for this parameter set
            param_results = []
            param_successful = 0
            param_total_time = 0
            
            # Test each case with current parameters
            for case_idx, test_case in enumerate(test_cases, 1):
                progress = f"{case_idx}/{len(test_cases)}"
                app_short = test_case['app'].split('.')[-1] if '.' in test_case['app'] else test_case['app']
                print(f"   📸 {progress}: {app_short}/{test_case['screenshot']} ({len(test_case['elements'])} elements)", end="")
                
                try:
                    # Create enhanced prompt
                    prompt = create_enhanced_prompt(test_case['elements'])
                    if not prompt:
                        print(" - No elements, skip")
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
                    param_total_time += response_time
                    
                    print(f" - {response_time:.1f}s", end="")
                    
                    # Parse coordinates
                    coords = None
                    reasoning = ""
                    element_desc = ""
                    
                    try:
                        response_text = response.content.strip()
                        # Extract JSON
                        if "{" in response_text and "}" in response_text:
                            json_start = response_text.find('{')
                            json_end = response_text.rfind('}') + 1
                            json_str = response_text[json_start:json_end]
                            parsed = json.loads(json_str)
                            
                            if "coordinates" in parsed:
                                coords = tuple(parsed["coordinates"])
                                reasoning = parsed.get("reasoning", "")
                                element_desc = parsed.get("element", "")
                        
                        # Fallback parsing
                        if not coords:
                            import re
                            coord_matches = re.findall(r'\[(\d+),\s*(\d+)\]', response_text)
                            if coord_matches:
                                coords = tuple(map(int, coord_matches[0]))
                        
                    except Exception as parse_error:
                        pass  # Will be handled below
                    
                    if coords:
                        # Validate
                        validation_result = validator.validate_coordinates(coords, str(test_case['xml_path']))
                        
                        result = {
                            'app': test_case['app'],
                            'screenshot': test_case['screenshot'],
                            'parameters': params.copy(),
                            'generated_coords': coords,
                            'available_elements': len(test_case['elements']),
                            'success': validation_result['success'],
                            'distance': validation_result['distance'],
                            'closest_element': validation_result['closest_element'],
                            'response_time': response_time,
                            'reasoning': reasoning,
                            'selected_element': element_desc,
                            'timestamp': datetime.now().isoformat()
                        }
                        
                        param_results.append(result)
                        all_results.append(result)
                        
                        if validation_result['success']:
                            param_successful += 1
                            print(f" - ✅ {validation_result['distance']:.0f}px")
                        else:
                            print(f" - ❌ {validation_result['distance']:.0f}px")
                    else:
                        print(f" - ❌ No coords")
                    
                except Exception as e:
                    print(f" - ❌ Error: {e}")
                    continue
            
            # Parameter set summary
            if param_results:
                param_success_rate = param_successful / len(param_results) * 100
                param_avg_time = param_total_time / len(param_results)
                print(f"   📊 Results: {param_successful}/{len(param_results)} ({param_success_rate:.1f}%) success, {param_avg_time:.1f}s avg")
            else:
                print(f"   📊 No results generated")
            
            print()
        
        # Final comprehensive analysis
        print("🏆 FULL PROTOTYPE EXECUTION RESULTS")
        print("=" * 60)
        
        if all_results:
            total_success = sum(1 for r in all_results if r['success'])
            total_tests_executed = len(all_results)
            overall_success_rate = total_success / total_tests_executed * 100
            
            total_time = sum(r['response_time'] for r in all_results)
            avg_time = total_time / total_tests_executed
            
            successful_distances = [r['distance'] for r in all_results if r['success']]
            avg_success_distance = sum(successful_distances) / len(successful_distances) if successful_distances else 0
            
            print(f"📈 Overall Success Rate: {total_success}/{total_tests_executed} ({overall_success_rate:.1f}%)")
            print(f"⏱️  Average Response Time: {avg_time:.1f}s")
            print(f"🎯 Average Distance (Success): {avg_success_distance:.1f}px")
            print(f"⚡ Total Execution Time: {total_time/60:.1f} minutes")
            
            # Parameter comparison
            print(f"\n📊 PARAMETER COMPARISON:")
            for params in parameter_combinations:
                param_results = [r for r in all_results if r['parameters'] == params]
                if param_results:
                    param_success = sum(1 for r in param_results if r['success'])
                    param_success_rate = param_success / len(param_results) * 100
                    param_avg_time = sum(r['response_time'] for r in param_results) / len(param_results)
                    
                    print(f"   temp={params['temperature']}, top_p={params['top_p']}, top_k={params['top_k']}: "
                          f"{param_success_rate:.1f}% success, {param_avg_time:.1f}s avg")
            
            # App breakdown
            print(f"\n📱 APP BREAKDOWN:")
            apps = set(r['app'] for r in all_results)
            for app in sorted(apps):
                app_results = [r for r in all_results if r['app'] == app]
                app_success = sum(1 for r in app_results if r['success'])
                app_success_rate = app_success / len(app_results) * 100
                app_avg_elements = sum(r['available_elements'] for r in app_results) / len(app_results)
                app_short = app.split('.')[-1] if '.' in app else app
                print(f"   {app_short}: {app_success}/{len(app_results)} ({app_success_rate:.1f}%) - {app_avg_elements:.1f} avg elements")
            
            # Save comprehensive results
            results_file = f"full_prototype_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(results_file, "w") as f:
                json.dump({
                    'execution_summary': {
                        'start_time': datetime.now().isoformat(),
                        'total_tests': total_tests_executed,
                        'total_success': total_success,
                        'success_rate': overall_success_rate,
                        'avg_response_time': avg_time,
                        'avg_success_distance': avg_success_distance,
                        'total_execution_time_minutes': total_time/60
                    },
                    'detailed_results': all_results
                }, f, indent=2)
            
            print(f"\n💾 Comprehensive results saved to: {results_file}")
            
            # Final recommendation
            print(f"\n🤔 PROTOTYPE ASSESSMENT:")
            
            if overall_success_rate >= 60:
                print(f"🎉 EXCELLENT ({overall_success_rate:.1f}%): Ready for RVAgent implementation!")
                recommendation = "IMPLEMENT_RVAGENT"
            elif overall_success_rate >= 40:
                print(f"✅ GOOD ({overall_success_rate:.1f}%): Viable with improvements")
                recommendation = "IMPLEMENT_WITH_IMPROVEMENTS"
            elif overall_success_rate >= 25:
                print(f"⚠️  MODERATE ({overall_success_rate:.1f}%): Needs significant tuning")
                recommendation = "MAJOR_IMPROVEMENTS_NEEDED"
            else:
                print(f"❌ POOR ({overall_success_rate:.1f}%): Back to drawing board")
                recommendation = "REDESIGN_NEEDED"
            
            print(f"\n🚀 FINAL RECOMMENDATION: {recommendation}")
            
            return recommendation, all_results
        else:
            print("❌ No results generated")
            return "FAILED", []
        
    except Exception as e:
        print(f"❌ Prototype execution failed: {e}")
        return "FAILED", []

if __name__ == "__main__":
    print("🚀 Starting RVAgent Full Prototype Execution...")
    recommendation, results = run_full_prototype()
    print(f"\n✅ Execution completed with recommendation: {recommendation}")