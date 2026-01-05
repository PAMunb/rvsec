#!/usr/bin/env python3
"""
Extensive Prototype Execution - Medium Scale
10 APKs, 5 screenshots each, comprehensive parameter grid
Generates CSV results and detailed logs for analysis
"""

import sys
from pathlib import Path
import time
import json
import base64
import xml.etree.ElementTree as ET
import csv
from itertools import product
from datetime import datetime
import logging

# Add module to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rv_agent.simple_validator import create_simple_validator

# Setup detailed logging
def setup_logging():
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = f"extensive_prototype_log_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return log_file

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
        logging.error(f"Error parsing XML {xml_path}: {e}")
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
        'Example: {"coordinates": [540, 960], "element": "OK button", "action": "click", "reasoning": "Primary action button"}'
    ])
    
    return "\n".join(lines)

def run_extensive_prototype():
    """Run extensive prototype testing with comprehensive parameter grid."""
    
    # Setup logging
    log_file = setup_logging()
    
    logging.info("RVAgent Extensive Prototype - Medium Scale Execution")
    logging.info("=" * 70)
    logging.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # COMPREHENSIVE PARAMETER GRID
    temperatures = [0.05, 0.1, 0.15, 0.2, 0.25]  # 5 values
    top_ps = [0.7, 0.8, 0.9]  # 3 values
    top_ks = [20, 30, 40]  # 3 values
    
    parameter_combinations = []
    for temp, top_p, top_k in product(temperatures, top_ps, top_ks):
        parameter_combinations.append({
            "temperature": temp,
            "top_p": top_p,
            "top_k": top_k
        })
    
    logging.info(f"Parameter grid: {len(temperatures)} temps × {len(top_ps)} top_ps × {len(top_ks)} top_ks = {len(parameter_combinations)} combinations")
    
    # Get test data - 10 APKs, 5 screenshots each
    screenshots_dir = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    screenshots_path = Path(screenshots_dir)
    
    # Collect test cases
    test_cases = []
    app_dirs = sorted([d for d in screenshots_path.iterdir() if d.is_dir() and d.name.endswith('.apk')])
    
    for app_dir in app_dirs[:10]:  # First 10 APKs
        png_files = sorted(list(app_dir.glob("*.png")))
        for png_file in png_files[:5]:  # First 5 screenshots per APK
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
    estimated_time = total_tests * 2.5 / 60  # 2.5s per test average
    
    logging.info(f"Test plan:")
    logging.info(f"   Apps: {len(set(tc['app'] for tc in test_cases))}")
    logging.info(f"   Screenshots: {len(test_cases)}")
    logging.info(f"   Parameter combinations: {len(parameter_combinations)}")
    logging.info(f"   Total tests: {total_tests}")
    logging.info(f"   Estimated time: {estimated_time:.1f} minutes")
    
    try:
        # Import LangChain components
        from langchain_ollama import ChatOllama
        from langchain_core.messages import HumanMessage
        
        # Validator
        validator = create_simple_validator(tolerance=50)
        
        # Store all results for CSV
        csv_results = []
        all_results = []
        
        # CSV file setup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_file = f"extensive_prototype_results_{timestamp}.csv"
        
        csv_fieldnames = [
            'execution_id', 'app', 'screenshot', 'temperature', 'top_p', 'top_k',
            'available_elements', 'generated_x', 'generated_y', 'success', 
            'distance', 'closest_x', 'closest_y', 'response_time', 'selected_element',
            'reasoning', 'parsing_success', 'timestamp'
        ]
        
        # Test each parameter combination
        execution_id = 0
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_fieldnames)
            writer.writeheader()
            
            for param_idx, params in enumerate(parameter_combinations, 1):
                logging.info(f"🧪 PARAMETER SET {param_idx}/{len(parameter_combinations)}")
                logging.info(f"   temp={params['temperature']}, top_p={params['top_p']}, top_k={params['top_k']}")
                
                # Create LLM with current parameters
                logging.info("   🤖 Creating client...")
                llm = ChatOllama(
                    model="qwen2.5vl:7b",
                    base_url="http://localhost:11434",
                    temperature=params['temperature'],
                    top_p=params['top_p'], 
                    top_k=params['top_k'],
                    num_predict=300,
                    timeout=120,  # Increased timeout for stability
                    num_ctx=32768
                )
                
                logging.info("   ✅ Client ready")
                
                # Test results for this parameter set
                param_successful = 0
                param_total_time = 0
                
                # Test each case with current parameters
                for case_idx, test_case in enumerate(test_cases, 1):
                    execution_id += 1
                    
                    app_short = test_case['app'].split('.')[-1] if '.' in test_case['app'] else test_case['app']
                    progress = f"{case_idx}/{len(test_cases)}"
                    
                    logging.info(f"   📸 {progress}: {app_short}/{test_case['screenshot']} ({len(test_case['elements'])} elements)")
                    
                    # Initialize CSV row
                    csv_row = {
                        'execution_id': execution_id,
                        'app': test_case['app'],
                        'screenshot': test_case['screenshot'],
                        'temperature': params['temperature'],
                        'top_p': params['top_p'],
                        'top_k': params['top_k'],
                        'available_elements': len(test_case['elements']),
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    try:
                        # Create enhanced prompt
                        prompt = create_enhanced_prompt(test_case['elements'])
                        if not prompt:
                            logging.warning("      No elements found, skipping")
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
                        
                        csv_row['response_time'] = response_time
                        
                        logging.info(f"      ⏱️  Response in {response_time:.1f}s")
                        
                        # Parse coordinates
                        coords = None
                        reasoning = ""
                        element_desc = ""
                        parsing_success = False
                        
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
                                    parsing_success = True
                            
                            # Fallback parsing
                            if not coords:
                                import re
                                coord_matches = re.findall(r'\[(\d+),\s*(\d+)\]', response_text)
                                if coord_matches:
                                    coords = tuple(map(int, coord_matches[0]))
                                    parsing_success = True
                            
                        except Exception as parse_error:
                            logging.warning(f"      JSON parse error: {parse_error}")
                            parsing_success = False
                        
                        csv_row['parsing_success'] = parsing_success
                        csv_row['selected_element'] = element_desc[:100]  # Limit length
                        csv_row['reasoning'] = reasoning[:200]  # Limit length
                        
                        if coords:
                            csv_row['generated_x'] = coords[0]
                            csv_row['generated_y'] = coords[1]
                            
                            # Validate
                            validation_result = validator.validate_coordinates(coords, str(test_case['xml_path']))
                            
                            csv_row['success'] = validation_result['success']
                            csv_row['distance'] = validation_result['distance']
                            
                            if validation_result['closest_element']:
                                csv_row['closest_x'] = validation_result['closest_element'][0]
                                csv_row['closest_y'] = validation_result['closest_element'][1]
                            
                            # Store detailed result
                            result = {
                                'execution_id': execution_id,
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
                                'parsing_success': parsing_success,
                                'timestamp': datetime.now().isoformat()
                            }
                            
                            all_results.append(result)
                            
                            if validation_result['success']:
                                param_successful += 1
                                logging.info(f"      ✅ Success: {coords}, distance: {validation_result['distance']:.0f}px")
                            else:
                                logging.info(f"      ❌ Failed: {coords}, distance: {validation_result['distance']:.0f}px")
                        else:
                            csv_row['success'] = False
                            logging.info(f"      ❌ No coordinates parsed")
                        
                        # Write to CSV immediately
                        writer.writerow(csv_row)
                        csvfile.flush()  # Ensure data is written
                        
                    except Exception as e:
                        logging.error(f"      ❌ Error: {e}")
                        csv_row['success'] = False
                        csv_row['parsing_success'] = False
                        writer.writerow(csv_row)
                        csvfile.flush()
                        continue
                
                # Parameter set summary
                if param_successful > 0:
                    param_success_rate = param_successful / len(test_cases) * 100
                    param_avg_time = param_total_time / len(test_cases)
                    logging.info(f"   📊 Results: {param_successful}/{len(test_cases)} ({param_success_rate:.1f}%) success, {param_avg_time:.1f}s avg")
                else:
                    logging.info(f"   📊 No successful results for this parameter set")
                
                logging.info("")
        
        # Final comprehensive analysis
        logging.info("🏆 EXTENSIVE PROTOTYPE EXECUTION RESULTS")
        logging.info("=" * 80)
        
        if all_results:
            total_success = sum(1 for r in all_results if r['success'])
            total_tests_executed = len(all_results)
            overall_success_rate = total_success / total_tests_executed * 100
            
            total_time = sum(r['response_time'] for r in all_results)
            avg_time = total_time / total_tests_executed
            
            successful_distances = [r['distance'] for r in all_results if r['success']]
            avg_success_distance = sum(successful_distances) / len(successful_distances) if successful_distances else 0
            
            logging.info(f"📈 Overall Success Rate: {total_success}/{total_tests_executed} ({overall_success_rate:.1f}%)")
            logging.info(f"⏱️  Average Response Time: {avg_time:.1f}s")
            logging.info(f"🎯 Average Distance (Success): {avg_success_distance:.1f}px")
            logging.info(f"⚡ Total Execution Time: {total_time/60:.1f} minutes")
            
            # Find best parameter combination
            param_stats = {}
            for params in parameter_combinations:
                param_key = f"T{params['temperature']}_P{params['top_p']}_K{params['top_k']}"
                param_results = [r for r in all_results if r['parameters'] == params]
                if param_results:
                    param_success = sum(1 for r in param_results if r['success'])
                    param_success_rate = param_success / len(param_results) * 100
                    param_avg_time = sum(r['response_time'] for r in param_results) / len(param_results)
                    
                    param_stats[param_key] = {
                        'success_rate': param_success_rate,
                        'avg_time': param_avg_time,
                        'params': params
                    }
            
            # Best parameters
            if param_stats:
                best_param = max(param_stats.items(), key=lambda x: x[1]['success_rate'])
                logging.info(f"\n🏆 BEST PARAMETERS:")
                logging.info(f"   {best_param[0]}: {best_param[1]['success_rate']:.1f}% success, {best_param[1]['avg_time']:.1f}s avg")
                logging.info(f"   temp={best_param[1]['params']['temperature']}, top_p={best_param[1]['params']['top_p']}, top_k={best_param[1]['params']['top_k']}")
            
            # Save comprehensive results
            results_file = f"extensive_prototype_detailed_{timestamp}.json"
            with open(results_file, "w") as f:
                json.dump({
                    'execution_summary': {
                        'start_time': datetime.now().isoformat(),
                        'total_tests': total_tests_executed,
                        'total_success': total_success,
                        'success_rate': overall_success_rate,
                        'avg_response_time': avg_time,
                        'avg_success_distance': avg_success_distance,
                        'total_execution_time_minutes': total_time/60,
                        'best_parameters': best_param[1]['params'] if param_stats else None
                    },
                    'parameter_statistics': param_stats,
                    'detailed_results': all_results
                }, f, indent=2)
            
            logging.info(f"\n💾 Results saved:")
            logging.info(f"   CSV: {csv_file}")
            logging.info(f"   JSON: {results_file}")
            logging.info(f"   LOG: {log_file}")
            
            # Final recommendation
            if overall_success_rate >= 70:
                recommendation = "EXCELLENT - Ready for massive final execution"
            elif overall_success_rate >= 60:
                recommendation = "GOOD - Proceed with final execution"
            elif overall_success_rate >= 50:
                recommendation = "MODERATE - Consider parameter tuning"
            else:
                recommendation = "NEEDS_IMPROVEMENT - More work required"
            
            logging.info(f"\n🚀 RECOMMENDATION: {recommendation}")
            
            return recommendation, all_results, csv_file
        else:
            logging.error("❌ No results generated")
            return "FAILED", [], None
        
    except Exception as e:
        logging.error(f"❌ Extensive prototype execution failed: {e}")
        return "FAILED", [], None

if __name__ == "__main__":
    print("🚀 Starting RVAgent Extensive Prototype Execution...")
    print("📊 This will generate CSV results and detailed logs for analysis")
    recommendation, results, csv_file = run_extensive_prototype()
    print(f"\n✅ Execution completed with recommendation: {recommendation}")
    if csv_file:
        print(f"📈 CSV results available at: {csv_file}")