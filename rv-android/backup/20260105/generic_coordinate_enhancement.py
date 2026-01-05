#!/usr/bin/env python3
"""
Generic coordinate enhancement solution for any APK.
Bypasses complex framework validation by directly processing DroidBot state files.
"""

import base64
import json
import logging
import random
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import numpy as np

from ollama import Client

def read_droidbot_state_direct(state_file: str) -> Dict[str, Any]:
    """Directly load and validate DroidBot state file."""
    try:
        with open(state_file, 'r') as f:
            state = json.load(f)
        
        # Check for different DroidBot state formats
        if 'view_tree' not in state and 'views' not in state:
            print(f"No view_tree or views found in {state_file}")
            return None
            
        return state
    except Exception as e:
        print(f"Error reading {state_file}: {e}")
        return None

def extract_ui_elements(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract UI elements with coordinates from DroidBot state."""
    
    elements = []
    
    def process_view(view: Dict[str, Any], parent_bounds=None):
        """Recursively process view hierarchy."""
        
        # Skip invisible elements
        if not view.get('visible', True):
            return
            
        # Extract basic properties - handle DroidBot attribute names
        element = {
            'text': (view.get('text', '') or '').strip(),
            'content_desc': (view.get('content_description', '') or '').strip(),
            'class': (view.get('class', '') or 'Unknown').split('.')[-1],
            'resource_id': view.get('resource_id', '') or '',
            'clickable': view.get('clickable', False),
            'scrollable': view.get('scrollable', False), 
            'checkable': view.get('checkable', False),
            'bounds': view.get('bounds', []),
            'enabled': view.get('enabled', True),
            'focusable': view.get('focusable', False),
            'editable': view.get('editable', False)
        }
        
        # Calculate center coordinates from bounds
        bounds = element['bounds']
        if bounds and len(bounds) == 2:
            try:
                if isinstance(bounds[0], list) and len(bounds[0]) == 2:
                    x1, y1 = bounds[0]
                    x2, y2 = bounds[1]
                elif len(bounds) == 4:  # Sometimes bounds are [x1, y1, x2, y2]
                    x1, y1, x2, y2 = bounds
                else:
                    return
                
                # Skip elements with invalid bounds
                if x2 <= x1 or y2 <= y1:
                    return
                    
                element['center'] = ((x1 + x2) // 2, (y1 + y2) // 2)
                element['width'] = x2 - x1
                element['height'] = y2 - y1
                
                # Only include interactive, text, focusable, or editable elements
                if (element['clickable'] or element['scrollable'] or element['focusable'] or 
                    element['editable'] or element['text'] or element['content_desc']):
                    elements.append(element)
                    
            except (ValueError, TypeError, IndexError):
                pass
        
        # Process children
        for child in view.get('children', []):
            process_view(child, element['bounds'])
    
    # Handle different state formats
    if 'view_tree' in state:
        # Process single view tree
        process_view(state['view_tree'])
    elif 'views' in state:
        # Process multiple views
        for view in state['views']:
            process_view(view)
    
    return elements

def create_enhanced_description(elements: List[Dict[str, Any]]) -> str:
    """Create enhanced description with coordinate information."""
    
    if not elements:
        return "No interactive UI elements found."
    
    lines = [
        "Current UI Elements and Available Actions:",
        "The screen contains the following interactive elements with precise coordinates:"
    ]
    
    action_id = 1
    for element in elements:
        # Create element description
        desc_parts = []
        
        # Add class type
        if element['class']:
            desc_parts.append(element['class'].lower())
        
        # Add text content
        if element['text']:
            desc_parts.append(f'"{element['text']}"')
        elif element['content_desc']:
            desc_parts.append(f'"{element['content_desc']}"')
        
        # Add resource ID if available
        if element['resource_id']:
            id_name = element['resource_id'].split('/')[-1]
            desc_parts.append(f"(id:{id_name})")
        
        # Create base description
        if desc_parts:
            desc = " ".join(desc_parts)
        else:
            desc = f"{element['class']} element"
        
        # Add coordinate information
        center = element['center']
        bounds = element['bounds']
        line = f" - {desc} at position ({center[0]}, {center[1]}) - bounds{bounds}"
        
        # Add available actions
        actions = []
        if element['clickable']:
            actions.append(f"click ({action_id})")
            action_id += 1
        if element['scrollable']:
            actions.append(f"scroll ({action_id})")
            action_id += 1
        if element['checkable']:
            actions.append(f"check/uncheck ({action_id})")
            action_id += 1
        
        if actions:
            line += f". Actions: {', '.join(actions)}"
        
        lines.append(line)
    
    lines.extend([
        "",
        "Screen resolution: 1080x1920 pixels",
        "All coordinates are provided as 'at position (x, y)' for precise interaction.",
        "Use the EXACT coordinates shown above for accurate element targeting."
    ])
    
    return "\n".join(lines)

def test_with_gemma_enhanced(screenshot_file: str, enhanced_desc: str, 
                           elements: List[Dict[str, Any]]) -> Optional[Dict]:
    """Test enhanced description with Gemma."""
    
    client = Client(host="http://localhost:11434")
    
    # Enhanced prompt with coordinate validation
    prompt = f"""
{enhanced_desc}

Task: You are testing an Android application. Look at the UI elements listed above and choose ONE interactive element to click on.

IMPORTANT: Use the EXACT coordinates provided in "at position (x, y)" format. Do not estimate or guess coordinates.

Return your response in this exact JSON format:
{{"coordinates": [x, y], "element": "description_of_chosen_element", "action": "click"}}

Choose an element that looks most interesting or important for testing the app functionality.
"""
    
    # Load screenshot
    try:
        with open(screenshot_file, 'rb') as f:
            image_b64 = base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        print(f"Error loading screenshot: {e}")
        return None
    
    messages = [
        {
            "role": "system",
            "content": "You are an Android UI testing assistant. Always use the EXACT coordinates provided in the element descriptions. Never estimate coordinates from the image."
        },
        {
            "role": "user", 
            "content": prompt,
            "images": [image_b64]
        }
    ]
    
    try:
        response = client.chat(
            model="gemma3:4b",
            messages=messages,
            options={"temperature": 0.1, "num_predict": 200},
            stream=False
        )
        
        response_text = response.message.content
        print(f"Gemma response: {response_text[:200]}...")
        
        # Extract coordinates
        coord_patterns = [
            r'"coordinates":\s*\[(\d+),\s*(\d+)\]',
            r'\[(\d+),\s*(\d+)\]',
            r'(\d+),\s*(\d+)'
        ]
        
        for pattern in coord_patterns:
            match = re.search(pattern, response_text)
            if match:
                generated = (int(match.group(1)), int(match.group(2)))
                
                # Find closest expected coordinate
                expected_coords = [elem['center'] for elem in elements]
                distances = [np.sqrt((generated[0] - exp[0])**2 + (generated[1] - exp[1])**2) 
                           for exp in expected_coords]
                
                min_distance = min(distances)
                best_idx = distances.index(min_distance)
                best_match = expected_coords[best_idx]
                
                # Check if it's a hit (within 50px)
                is_hit = min_distance < 50
                
                return {
                    "generated": generated,
                    "expected": best_match, 
                    "distance": float(min_distance),
                    "hit": bool(is_hit),
                    "response": response_text,
                    "chosen_element": elements[best_idx]
                }
        
        print("❌ No coordinates found in response")
        return None
        
    except Exception as e:
        print(f"❌ Gemma error: {e}")
        return None

def test_single_apk_sample(state_file: str, screenshot_file: str) -> Optional[Dict]:
    """Test coordinate enhancement on a single APK sample."""
    
    print(f"\n{'='*60}")
    print(f"Testing: {Path(state_file).parent.name}/{Path(state_file).name}")
    print(f"{'='*60}")
    
    # Load state
    state = read_droidbot_state_direct(state_file)
    if not state:
        print("❌ Failed to load state")
        return None
    
    # Extract elements
    elements = extract_ui_elements(state)
    if not elements:
        print("❌ No interactive elements found")
        return None
    
    print(f"✅ Found {len(elements)} interactive elements")
    
    # Create enhanced description
    enhanced_desc = create_enhanced_description(elements)
    
    print("📝 Enhanced description preview:")
    print(enhanced_desc[:400] + "..." if len(enhanced_desc) > 400 else enhanced_desc)
    
    # Test with Gemma
    print("\n🤖 Testing with Gemma...")
    result = test_with_gemma_enhanced(screenshot_file, enhanced_desc, elements)
    
    if result:
        print(f"🎯 Generated: {result['generated']}")
        print(f"🎯 Expected: {result['expected']}")
        print(f"📏 Distance: {result['distance']:.1f}px")
        print(f"✅ Hit: {'Yes' if result['hit'] else 'No'}")
        print(f"🎯 Element: {result['chosen_element']['class']} - {result['chosen_element'].get('text', 'no text')}")
        
        return result
    
    return None

def run_comprehensive_test(sample_count: int = 10):
    """Run comprehensive test across multiple APK samples."""
    
    print("🧪 GENERIC COORDINATE ENHANCEMENT TEST")
    print("=" * 60)
    
    # Find sample files
    screenshots_dir = Path("/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/tmp_img/screenshots")
    
    samples = []
    for app_dir in screenshots_dir.iterdir():
        if app_dir.is_dir():
            for png_file in app_dir.glob("*.png"):
                state_file = app_dir / f"{png_file.stem}.state"
                if state_file.exists():
                    samples.append((str(state_file), str(png_file)))
    
    if not samples:
        print("❌ No valid samples found")
        return
    
    # Random sample selection
    test_samples = random.sample(samples, min(sample_count, len(samples)))
    print(f"📊 Testing {len(test_samples)} random samples")
    
    results = []
    success_count = 0
    
    for i, (state_file, screenshot_file) in enumerate(test_samples, 1):
        print(f"\n🔄 Test {i}/{len(test_samples)}")
        
        result = test_single_apk_sample(state_file, screenshot_file)
        if result:
            results.append(result)
            success_count += 1
    
    # Final summary
    if results:
        hit_rate = np.mean([r['hit'] for r in results])
        avg_distance = np.mean([r['distance'] for r in results])
        
        print(f"\n📊 FINAL RESULTS")
        print(f"{'='*40}")
        print(f"Successful tests: {success_count}/{len(test_samples)}")
        print(f"Hit rate: {hit_rate*100:.1f}%")
        print(f"Average distance: {avg_distance:.1f}px")
        print(f"Precision (< 50px): {hit_rate*100:.1f}%")
        
        # Save detailed results
        results_file = Path("generic_test_results.json")
        with open(results_file, 'w') as f:
            json.dump({
                "summary": {
                    "successful_tests": success_count,
                    "total_tests": len(test_samples),
                    "hit_rate": float(hit_rate),
                    "average_distance": float(avg_distance)
                },
                "detailed_results": results
            }, f, indent=2)
        
        print(f"💾 Detailed results saved to: {results_file}")
        
    else:
        print("\n❌ No successful tests completed")

def main():
    """Run the generic coordinate enhancement test."""
    run_comprehensive_test(sample_count=15)

if __name__ == "__main__":
    main()