#!/usr/bin/env python3
"""
Expanded Validation Test
Tests Qwen 2.5VL 7B with multiple APKs and screenshots for better validation
before running full prototype execution.
"""

import sys
from pathlib import Path

# Add module to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rv_agent.simple_validator import create_simple_validator
import time
import json
import base64

def test_expanded_validation():
    """Test vision model with multiple APKs and screenshots."""
    # Test parameters (best from minimal test)
    temperature = 0.3
    top_p = 0.9
    top_k = 40
    
    print("RVAgent Prototype - Expanded Validation")
    print("3 APKs, 2 screenshots each, 1 parameter set")
    print("=" * 60)
    print(f"Parameters: temp={temperature}, top_p={top_p}, top_k={top_k}")
    print()
    
    # Get test data
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
                test_cases.append({
                    'app': app_dir.name,
                    'screenshot': png_file.name,
                    'image_path': png_file,
                    'xml_path': xml_file
                })
    
    print(f"📱 Testing {len(test_cases)} cases ({len(set(tc['app'] for tc in test_cases))} APKs)")
    
    # Validator
    validator = create_simple_validator(tolerance=50)
    
    try:
        # Import LangChain components
        from langchain_ollama import ChatOllama
        from langchain_core.messages import HumanMessage
        
        print("🤖 Creating Qwen 2.5VL 7B client...")
        
        # Create LLM with test parameters
        llm = ChatOllama(
            model="qwen2.5vl:7b",
            base_url="http://localhost:11434",
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            num_predict=200,
            timeout=60,
            num_ctx=32768  # Large context window
        )
        
        print("✅ Client created")
        print()
        
        # Test each case
        results = []
        successful_tests = 0
        total_distance = 0
        total_time = 0
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"📸 Test {i}/{len(test_cases)}: {test_case['app']}/{test_case['screenshot']}")
            
            # Get ground truth
            ground_truth = validator.extract_clickable_coordinates(str(test_case['xml_path']))
            print(f"   Ground truth: {len(ground_truth)} elements")
            
            if not ground_truth:
                print("   ⚠️  No clickable elements found, skipping")
                continue
            
            try:
                # Create prompt (using successful strategy from previous tests)
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
                
                # Parse coordinates
                coords = None
                response_text = response.content.strip()
                if "COORDINATES:" in response_text:
                    try:
                        coord_part = response_text.split("COORDINATES:")[1].strip()
                        coord_part = coord_part.replace('(', '').replace(')', '')
                        x, y = map(int, coord_part.split(','))
                        coords = (x, y)
                    except:
                        print(f"   ❌ Failed to parse: {response_text[:50]}...")
                
                if coords:
                    # Validate against ground truth
                    validation_result = validator.validate_coordinates(coords, str(test_case['xml_path']))
                    
                    result = {
                        'app': test_case['app'],
                        'screenshot': test_case['screenshot'],
                        'generated_coords': coords,
                        'ground_truth_count': len(ground_truth),
                        'success': validation_result['success'],
                        'distance': validation_result['distance'],
                        'closest_element': validation_result['closest_element'],
                        'response_time': response_time,
                        'raw_response': response.content[:100]
                    }
                    
                    results.append(result)
                    
                    if validation_result['success']:
                        successful_tests += 1
                        total_distance += validation_result['distance']
                        print(f"   ✅ Success: {coords}, distance: {validation_result['distance']:.0f}px")
                    else:
                        print(f"   ❌ Failed: {coords}, distance: {validation_result['distance']:.0f}px")
                else:
                    print(f"   ❌ No coordinates parsed")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
                continue
            
            print()
        
        # Results summary
        print("📊 EXPANDED VALIDATION RESULTS")
        print("=" * 40)
        
        if results:
            success_rate = successful_tests / len(results) * 100
            avg_distance = total_distance / successful_tests if successful_tests > 0 else 0
            avg_time = total_time / len(results)
            
            print(f"📈 Success rate: {successful_tests}/{len(results)} ({success_rate:.1f}%)")
            print(f"📏 Average distance: {avg_distance:.1f}px")
            print(f"⏱️  Average time: {avg_time:.1f}s")
            print(f"🎯 Apps tested: {len(set(r['app'] for r in results))}")
            
            # Show per-app breakdown
            apps = set(r['app'] for r in results)
            for app in sorted(apps):
                app_results = [r for r in results if r['app'] == app]
                app_success = sum(1 for r in app_results if r['success'])
                print(f"   {app}: {app_success}/{len(app_results)} success")
            
            # Save results
            with open("expanded_validation_results.json", "w") as f:
                json.dump(results, f, indent=2)
            print(f"\n💾 Detailed results saved to: expanded_validation_results.json")
            
            # Decision criteria
            print(f"\n🤔 READINESS ASSESSMENT:")
            if success_rate >= 50:
                print(f"✅ SUCCESS RATE ({success_rate:.1f}%) >= 50% → READY for full prototype")
                recommendation = "PROCEED"
            else:
                print(f"⚠️  SUCCESS RATE ({success_rate:.1f}%) < 50% → Need prompt tuning")
                recommendation = "TUNE_PROMPTS"
            
            if avg_distance <= 100:
                print(f"✅ AVG DISTANCE ({avg_distance:.1f}px) <= 100px → Good precision")
            else:
                print(f"⚠️  AVG DISTANCE ({avg_distance:.1f}px) > 100px → Could improve")
            
            if avg_time <= 10:
                print(f"✅ AVG TIME ({avg_time:.1f}s) <= 10s → Acceptable speed")
            else:
                print(f"⚠️  AVG TIME ({avg_time:.1f}s) > 10s → Might be slow for full test")
            
            print(f"\n🚀 RECOMMENDATION: {recommendation}")
            return recommendation, results
        else:
            print("❌ No valid results generated")
            return "FAILED", []
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return "FAILED", []

if __name__ == "__main__":
    recommendation, results = test_expanded_validation()