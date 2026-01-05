#!/usr/bin/env python3
"""
Overnight Final Execution - Massive Scale
All APKs, 15-20 screenshots each, comprehensive parameter grid
For final production validation and optimal parameter determination
"""

import sys
from pathlib import Path
import time
import json
import base64
import xml.etree.ElementTree as ET
import csv
import pandas as pd
from itertools import product
from datetime import datetime
import logging
import argparse

# Add module to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rv_agent.simple_validator import create_simple_validator

def setup_logging(log_level="INFO"):
    """Setup comprehensive logging for overnight execution."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = f"overnight_execution_log_{timestamp}.log"
    
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    # Also log to a progress file for monitoring
    progress_file = f"overnight_progress_{timestamp}.log"
    progress_handler = logging.FileHandler(progress_file)
    progress_handler.setLevel(logging.INFO)
    progress_formatter = logging.Formatter('%(asctime)s - %(message)s')
    progress_handler.setFormatter(progress_formatter)
    
    progress_logger = logging.getLogger('progress')
    progress_logger.addHandler(progress_handler)
    progress_logger.setLevel(logging.INFO)
    
    return log_file, progress_file

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

def run_overnight_execution(max_screenshots=20, extended_params=True, test_mode=False):
    """Run comprehensive overnight execution."""
    
    # Setup logging
    log_file, progress_file = setup_logging()
    progress_logger = logging.getLogger('progress')
    
    logging.info("RVAgent Overnight Execution - Massive Scale")
    logging.info("=" * 80)
    logging.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    progress_logger.info("OVERNIGHT_EXECUTION_STARTED")
    
    if test_mode:
        logging.info("🧪 TEST MODE: Running limited test for validation")
        max_screenshots = 3
        extended_params = False
    
    # MASSIVE PARAMETER GRID
    if extended_params:
        temperatures = [0.01, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5]  # 9 values
        top_ps = [0.6, 0.7, 0.8, 0.9, 0.95]  # 5 values
        top_ks = [10, 20, 30, 40, 50, 60]  # 6 values
        # Total: 9 × 5 × 6 = 270 parameter combinations
    else:
        # Focused grid around optimal region
        temperatures = [0.1, 0.15, 0.2, 0.25, 0.3]  # 5 values
        top_ps = [0.8, 0.9, 0.95]  # 3 values
        top_ks = [30, 40, 50]  # 3 values
        # Total: 5 × 3 × 3 = 45 parameter combinations
    
    parameter_combinations = []
    for temp, top_p, top_k in product(temperatures, top_ps, top_ks):
        parameter_combinations.append({
            "temperature": temp,
            "top_p": top_p,
            "top_k": top_k
        })
    
    logging.info(f"Parameter grid: {len(temperatures)} temps × {len(top_ps)} top_ps × {len(top_ks)} top_ks = {len(parameter_combinations)} combinations")
    
    # Get test data - ALL APKs, multiple screenshots each
    screenshots_dir = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots"
    screenshots_path = Path(screenshots_dir)
    
    # Collect ALL available test cases
    test_cases = []
    app_dirs = sorted([d for d in screenshots_path.iterdir() if d.is_dir() and d.name.endswith('.apk')])
    
    logging.info(f"Discovering test cases from {len(app_dirs)} apps...")
    
    for app_dir in app_dirs:  # ALL APKs
        png_files = sorted(list(app_dir.glob("*.png")))
        screenshots_to_use = min(len(png_files), max_screenshots)
        
        app_cases = 0
        for png_file in png_files[:screenshots_to_use]:  # Up to max_screenshots per APK
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
                    app_cases += 1
        
        logging.info(f"   {app_dir.name}: {app_cases}/{screenshots_to_use} valid cases")
    
    total_tests = len(test_cases) * len(parameter_combinations)
    estimated_time = total_tests * 2.5 / 3600  # 2.5s per test average, convert to hours
    
    logging.info(f"MASSIVE TEST PLAN:")
    logging.info(f"   Apps: {len(set(tc['app'] for tc in test_cases))}")
    logging.info(f"   Screenshots: {len(test_cases)}")
    logging.info(f"   Parameter combinations: {len(parameter_combinations)}")
    logging.info(f"   Total tests: {total_tests:,}")
    logging.info(f"   Estimated time: {estimated_time:.1f} hours")
    
    progress_logger.info(f"TEST_PLAN: {len(test_cases)} cases × {len(parameter_combinations)} params = {total_tests:,} tests")
    
    if not test_mode and total_tests > 50000:
        logging.warning(f"⚠️  MASSIVE EXECUTION: {total_tests:,} tests will take ~{estimated_time:.1f} hours")
        response = input("Continue with massive execution? (y/N): ")
        if response.lower() != 'y':
            logging.info("Execution cancelled by user")
            return "CANCELLED", [], None
    
    try:
        # Import LangChain components
        from langchain_ollama import ChatOllama
        from langchain_core.messages import HumanMessage
        
        # Validator
        validator = create_simple_validator(tolerance=50)
        
        # Store all results for CSV
        all_results = []
        
        # CSV file setup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_file = f"overnight_results_{timestamp}.csv"
        
        csv_fieldnames = [
            'execution_id', 'app', 'screenshot', 'temperature', 'top_p', 'top_k',
            'available_elements', 'generated_x', 'generated_y', 'success', 
            'distance', 'closest_x', 'closest_y', 'response_time', 'selected_element',
            'reasoning', 'parsing_success', 'timestamp', 'param_combination_id'
        ]
        
        # Test each parameter combination
        execution_id = 0
        start_time = time.time()
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=csv_fieldnames)
            writer.writeheader()
            
            for param_idx, params in enumerate(parameter_combinations, 1):
                param_start_time = time.time()
                
                logging.info(f"🧪 PARAMETER SET {param_idx}/{len(parameter_combinations)}")
                logging.info(f"   temp={params['temperature']}, top_p={params['top_p']}, top_k={params['top_k']}")
                progress_logger.info(f"PARAM_SET_{param_idx}: T{params['temperature']}_P{params['top_p']}_K{params['top_k']}")
                
                # Create LLM with current parameters
                logging.info("   🤖 Creating client...")
                llm = ChatOllama(
                    model="qwen2.5vl:7b",
                    base_url="http://localhost:11434",
                    temperature=params['temperature'],
                    top_p=params['top_p'], 
                    top_k=params['top_k'],
                    num_predict=300,
                    timeout=150,  # Increased timeout for overnight stability
                    num_ctx=32768
                )
                
                logging.info("   ✅ Client ready")
                
                # Test results for this parameter set
                param_successful = 0
                param_total_time = 0
                param_results = []
                
                # Test each case with current parameters
                for case_idx, test_case in enumerate(test_cases, 1):
                    execution_id += 1
                    
                    app_short = test_case['app'].split('.')[-1] if '.' in test_case['app'] else test_case['app']
                    progress = f"{case_idx}/{len(test_cases)}"
                    
                    if case_idx % 100 == 0 or case_idx % 10 == 0:  # Log every 10th case, every 100th with detail
                        detail_level = "detailed" if case_idx % 100 == 0 else "brief"
                        logging.info(f"   📸 {progress}: {app_short}/{test_case['screenshot']} ({len(test_case['elements'])} elements)")
                        progress_logger.info(f"CASE_{execution_id}: {app_short}/{test_case['screenshot']}")
                    
                    # Initialize CSV row
                    csv_row = {
                        'execution_id': execution_id,
                        'app': test_case['app'],
                        'screenshot': test_case['screenshot'],
                        'temperature': params['temperature'],
                        'top_p': params['top_p'],
                        'top_k': params['top_k'],
                        'available_elements': len(test_case['elements']),
                        'timestamp': datetime.now().isoformat(),
                        'param_combination_id': param_idx
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
                        case_start_time = time.time()
                        response = llm.invoke([message])
                        response_time = time.time() - case_start_time
                        param_total_time += response_time
                        
                        csv_row['response_time'] = response_time
                        
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
                            
                            # Store detailed result for analysis
                            result = {
                                'execution_id': execution_id,
                                'app': test_case['app'],
                                'screenshot': test_case['screenshot'],
                                'parameters': params.copy(),
                                'param_combination_id': param_idx,
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
                            
                            param_results.append(result)
                            all_results.append(result)
                            
                            if validation_result['success']:
                                param_successful += 1
                        else:
                            csv_row['success'] = False
                        
                        # Write to CSV immediately
                        writer.writerow(csv_row)
                        csvfile.flush()  # Ensure data is written immediately
                        
                    except Exception as e:
                        logging.error(f"      ❌ Error in case {execution_id}: {e}")
                        csv_row['success'] = False
                        csv_row['parsing_success'] = False
                        writer.writerow(csv_row)
                        csvfile.flush()
                        continue
                
                # Parameter set summary
                param_elapsed = time.time() - param_start_time
                total_elapsed = time.time() - start_time
                
                if param_results:
                    param_success_rate = param_successful / len(param_results) * 100
                    param_avg_time = param_total_time / len(param_results)
                    
                    logging.info(f"   📊 Set Results: {param_successful}/{len(param_results)} ({param_success_rate:.1f}%) success")
                    logging.info(f"   ⏱️  Set Time: {param_elapsed/60:.1f}min, Total: {total_elapsed/60:.1f}min")
                    
                    progress_logger.info(f"PARAM_SET_{param_idx}_COMPLETE: {param_success_rate:.1f}% success, {param_elapsed/60:.1f}min")
                else:
                    logging.warning(f"   📊 No results for parameter set {param_idx}")
                    progress_logger.info(f"PARAM_SET_{param_idx}_FAILED: No results")
                
                # Save intermediate results every 10 parameter sets
                if param_idx % 10 == 0:
                    intermediate_file = f"overnight_intermediate_{param_idx}_{timestamp}.json"
                    with open(intermediate_file, "w") as f:
                        json.dump({
                            'completed_param_sets': param_idx,
                            'total_param_sets': len(parameter_combinations),
                            'progress_percent': (param_idx / len(parameter_combinations)) * 100,
                            'total_elapsed_hours': total_elapsed / 3600,
                            'results_so_far': len(all_results),
                            'current_results': all_results
                        }, f, indent=2)
                    logging.info(f"   💾 Intermediate results saved: {intermediate_file}")
        
        # Final comprehensive analysis
        total_elapsed = time.time() - start_time
        
        logging.info("🏆 OVERNIGHT EXECUTION COMPLETED")
        logging.info("=" * 100)
        progress_logger.info("OVERNIGHT_EXECUTION_COMPLETED")
        
        if all_results:
            total_success = sum(1 for r in all_results if r['success'])
            total_tests_executed = len(all_results)
            overall_success_rate = total_success / total_tests_executed * 100
            
            total_time = sum(r['response_time'] for r in all_results)
            avg_time = total_time / total_tests_executed
            
            successful_distances = [r['distance'] for r in all_results if r['success']]
            avg_success_distance = sum(successful_distances) / len(successful_distances) if successful_distances else 0
            
            logging.info(f"📈 Overall Success Rate: {total_success:,}/{total_tests_executed:,} ({overall_success_rate:.1f}%)")
            logging.info(f"⏱️  Average Response Time: {avg_time:.1f}s")
            logging.info(f"🎯 Average Distance (Success): {avg_success_distance:.1f}px")
            logging.info(f"⚡ Total Execution Time: {total_elapsed/3600:.1f} hours")
            logging.info(f"🚀 Tests per Hour: {total_tests_executed/(total_elapsed/3600):.0f}")
            
            # Find optimal parameters using comprehensive analysis
            param_analysis = {}
            for param_combo in parameter_combinations:
                param_key = f"T{param_combo['temperature']}_P{param_combo['top_p']}_K{param_combo['top_k']}"
                param_results_filtered = [r for r in all_results if r['parameters'] == param_combo]
                
                if param_results_filtered:
                    param_success = sum(1 for r in param_results_filtered if r['success'])
                    param_success_rate = param_success / len(param_results_filtered) * 100
                    param_avg_time = sum(r['response_time'] for r in param_results_filtered) / len(param_results_filtered)
                    param_avg_distance = sum(r['distance'] for r in param_results_filtered if r['success']) / max(param_success, 1)
                    
                    param_analysis[param_key] = {
                        'success_rate': param_success_rate,
                        'avg_time': param_avg_time,
                        'avg_distance': param_avg_distance,
                        'total_tests': len(param_results_filtered),
                        'params': param_combo
                    }
            
            # Find best parameters by success rate
            if param_analysis:
                best_params = max(param_analysis.items(), key=lambda x: x[1]['success_rate'])
                logging.info(f"\n🏆 OPTIMAL PARAMETERS IDENTIFIED:")
                logging.info(f"   {best_params[0]}: {best_params[1]['success_rate']:.1f}% success")
                logging.info(f"   Params: temp={best_params[1]['params']['temperature']}, top_p={best_params[1]['params']['top_p']}, top_k={best_params[1]['params']['top_k']}")
                logging.info(f"   Avg time: {best_params[1]['avg_time']:.1f}s, Avg distance: {best_params[1]['avg_distance']:.1f}px")
                
                progress_logger.info(f"OPTIMAL_PARAMS: {best_params[0]} - {best_params[1]['success_rate']:.1f}% success")
            
            # Save comprehensive final results
            final_results_file = f"overnight_final_results_{timestamp}.json"
            with open(final_results_file, "w") as f:
                json.dump({
                    'execution_summary': {
                        'start_time': datetime.now().isoformat(),
                        'total_tests': total_tests_executed,
                        'total_success': total_success,
                        'success_rate': overall_success_rate,
                        'avg_response_time': avg_time,
                        'avg_success_distance': avg_success_distance,
                        'total_execution_time_hours': total_elapsed/3600,
                        'tests_per_hour': total_tests_executed/(total_elapsed/3600),
                        'optimal_parameters': best_params[1]['params'] if param_analysis else None
                    },
                    'parameter_analysis': param_analysis,
                    'detailed_results': all_results
                }, f, indent=2)
            
            # Generate CSV analysis summary
            analysis_csv = f"overnight_analysis_{timestamp}.csv"
            with open(analysis_csv, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['param_combination', 'temperature', 'top_p', 'top_k', 'success_rate', 'avg_time', 'avg_distance', 'total_tests']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for param_key, stats in param_analysis.items():
                    writer.writerow({
                        'param_combination': param_key,
                        'temperature': stats['params']['temperature'],
                        'top_p': stats['params']['top_p'],
                        'top_k': stats['params']['top_k'],
                        'success_rate': stats['success_rate'],
                        'avg_time': stats['avg_time'],
                        'avg_distance': stats['avg_distance'],
                        'total_tests': stats['total_tests']
                    })
            
            logging.info(f"\n💾 Final Results Saved:")
            logging.info(f"   Raw data CSV: {csv_file}")
            logging.info(f"   Analysis CSV: {analysis_csv}")
            logging.info(f"   Detailed JSON: {final_results_file}")
            logging.info(f"   Execution log: {log_file}")
            logging.info(f"   Progress log: {progress_file}")
            
            # Final recommendation
            if overall_success_rate >= 75:
                recommendation = "PRODUCTION_READY"
            elif overall_success_rate >= 65:
                recommendation = "PRODUCTION_READY_WITH_OPTIMIZATION"
            elif overall_success_rate >= 50:
                recommendation = "PRODUCTION_VIABLE"
            else:
                recommendation = "NEEDS_IMPROVEMENT"
            
            logging.info(f"\n🚀 FINAL RECOMMENDATION: {recommendation}")
            progress_logger.info(f"FINAL_RECOMMENDATION: {recommendation}")
            
            return recommendation, all_results, csv_file
        else:
            logging.error("❌ No results generated")
            progress_logger.info("EXECUTION_FAILED: No results generated")
            return "FAILED", [], None
        
    except Exception as e:
        logging.error(f"❌ Overnight execution failed: {e}")
        progress_logger.info(f"EXECUTION_FAILED: {e}")
        return "FAILED", [], None

def main():
    """Main entry point with command line arguments."""
    parser = argparse.ArgumentParser(description='RVAgent Overnight Execution')
    parser.add_argument('--max-screenshots', type=int, default=20, help='Max screenshots per app (default: 20)')
    parser.add_argument('--extended-params', action='store_true', help='Use extended parameter grid (270 combinations vs 45)')
    parser.add_argument('--test-mode', action='store_true', help='Run in test mode (limited execution)')
    
    args = parser.parse_args()
    
    print("🌙 RVAgent Overnight Execution - Massive Scale Validation")
    print("=" * 70)
    
    if args.test_mode:
        print("🧪 Running in TEST MODE")
    elif args.extended_params:
        print("🔬 Using EXTENDED parameter grid (270 combinations)")
    else:
        print("🎯 Using FOCUSED parameter grid (45 combinations)")
    
    print(f"📸 Max screenshots per app: {args.max_screenshots}")
    print()
    
    recommendation, results, csv_file = run_overnight_execution(
        max_screenshots=args.max_screenshots,
        extended_params=args.extended_params,
        test_mode=args.test_mode
    )
    
    print(f"\n✅ Overnight execution completed with recommendation: {recommendation}")
    if csv_file:
        print(f"📊 Results available in: {csv_file}")

if __name__ == "__main__":
    main()