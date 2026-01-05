#!/usr/bin/env python3
"""
Simplified approach to test Gemma coordinate enhancement.
Uses existing tested logic from teste_rv_llm_service.py
"""

import base64
import json
import logging
import os
import random
import re
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import numpy as np

# Import from existing working script approach
import sys
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "modules" / "rv-android-core" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-screen-parser" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-llm" / "src"))

from rv_screen_parser.parser.screen.parser_factory import ParserFactory
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription
from rv_screen_parser.constants import ScreenParserType, VisitorType
from rv_android_core.domain.static import StaticAnalysisData
from rv_screen_parser.parser.screen.visitor.basic_visitor import BasicTextVisitor

from ollama import Client


def read_droidbot_state(filename: str) -> Dict[str, Any]:
    """Load DroidBot state from file."""
    with open(filename, 'r') as f:
        return json.load(f)


def create_screen_description_simple(state_file: str) -> ScreenDescription:
    """Create ScreenDescription using simplified approach."""
    try:
        droidbot_state = read_droidbot_state(state_file)
        
        # Create empty static data - matching existing working approach
        static_data = StaticAnalysisData(classes={}, windows={}, wtg={})
        
        # Use the factory correctly
        parser = ParserFactory.create(ScreenParserType.DROIDBOT, BasicTextVisitor)
        screen_desc = parser.parse_screen(droidbot_state, static_data)
        
        return screen_desc
        
    except Exception as e:
        print(f"Error: {e}")
        return None


def enhance_description_with_coordinates(screen_desc: ScreenDescription) -> str:
    """Add coordinate information to screen description."""
    
    if not screen_desc or not screen_desc.items:
        return "No UI elements available."
    
    lines = [
        "Current UI Elements and Available Actions:",
        "The current screen has the following UI views and corresponding actions, with action id in parentheses:"
    ]
    
    for item in screen_desc.items:
        # Start with base description
        line = f" - {item.base_description}"
        
        # Try to add coordinate info from bounds
        if hasattr(item, 'view') and item.view and 'bounds' in item.view:
            bounds = item.view['bounds']
            if bounds and isinstance(bounds, list) and len(bounds) == 2:
                try:
                    x1, y1 = bounds[0]
                    x2, y2 = bounds[1] 
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2
                    line += f" at position ({center_x}, {center_y}) - bounds{bounds}"
                except:
                    pass
        
        # Add actions
        if item.actions:
            action_texts = [f"{action.text} ({action.id})" for action in item.actions]
            line += f". Actions: {', '.join(action_texts)}"
        
        lines.append(line)
    
    lines.extend([
        "",
        "Screen resolution: 1080x1920 pixels",
        "Click coordinates are provided as 'at position (x, y)' for precise targeting."
    ])
    
    return "\n".join(lines)


def test_single_sample(state_file: str, screenshot_file: str):
    """Test a single sample to see if enhancement works."""
    
    print(f"\n{'='*60}")
    print(f"Testing: {Path(screenshot_file).name}")
    print(f"{'='*60}")
    
    # Create screen description
    screen_desc = create_screen_description_simple(state_file)
    
    if not screen_desc:
        print("❌ Failed to create screen description")
        return None
    
    # Create enhanced version
    original = screen_desc.description
    enhanced = enhance_description_with_coordinates(screen_desc)
    
    print("\n📋 Original Description:")
    print(original[:300] + "..." if len(original) > 300 else original)
    
    print("\n✨ Enhanced Description:")
    print(enhanced[:500] + "..." if len(enhanced) > 500 else enhanced)
    
    # Count coordinate mentions
    coord_pattern = r'at position \((\d+), (\d+)\)'
    coordinates = re.findall(coord_pattern, enhanced)
    
    print(f"\n📊 Found {len(coordinates)} coordinate positions:")
    for i, (x, y) in enumerate(coordinates[:5], 1):  # Show first 5
        print(f"  {i}. ({x}, {y})")
    
    # Test a simple prompt with Gemma
    if coordinates:
        print(f"\n🤖 Testing with Gemma...")
        result = test_with_gemma(screenshot_file, enhanced, coordinates)
        return result
    
    return None


def test_with_gemma(screenshot_file: str, enhanced_desc: str, expected_coords: List[Tuple[str, str]]):
    """Test enhanced description with Gemma."""
    
    client = Client(host="http://localhost:11434")
    
    # Simple prompt
    prompt = f"""
{enhanced_desc}

Task: Look at the screen elements above. Choose any interactive element and click on it using the EXACT coordinates provided in "at position (x, y)".

Return JSON: {{"coordinates": [x, y], "element": "name"}}
"""
    
    # Load image
    with open(screenshot_file, 'rb') as f:
        image_b64 = base64.b64encode(f.read()).decode('utf-8')
    
    messages = [
        {
            "role": "system",
            "content": "You are a UI testing assistant. Use coordinates exactly as provided."
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
            options={"temperature": 0.1, "num_predict": 150},
            stream=False
        )
        
        response_text = response.message.content
        print(f"Response: {response_text}")
        
        # Extract coordinates
        coord_patterns = [
            r'"coordinates":\s*\[(\d+),\s*(\d+)\]',
            r'\[(\d+),\s*(\d+)\]'
        ]
        
        for pattern in coord_patterns:
            match = re.search(pattern, response_text)
            if match:
                generated = (int(match.group(1)), int(match.group(2)))
                print(f"Generated: {generated}")
                
                # Find closest expected
                expected_as_int = [(int(x), int(y)) for x, y in expected_coords]
                distances = [np.sqrt((generated[0] - ex[0])**2 + (generated[1] - ex[1])**2) 
                           for ex in expected_as_int]
                
                min_distance = min(distances)
                best_match = expected_as_int[distances.index(min_distance)]
                
                print(f"Best match: {best_match}, Distance: {min_distance:.1f}px")
                print(f"Hit: {'✅' if min_distance < 50 else '❌'}")
                
                return {
                    "generated": generated,
                    "best_match": best_match,
                    "distance": min_distance,
                    "hit": min_distance < 50
                }
        
        print("❌ No coordinates found in response")
        return None
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def main():
    """Run simplified test."""
    
    # Find a few sample files
    screenshots_dir = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/tmp_img/screenshots"
    
    samples = []
    for app_dir in Path(screenshots_dir).iterdir():
        if app_dir.is_dir():
            for png_file in app_dir.glob("*.png"):
                state_file = app_dir / f"{png_file.stem}.state"
                if state_file.exists():
                    samples.append((str(state_file), str(png_file)))
    
    # Test a few samples
    test_samples = random.sample(samples, min(5, len(samples)))
    
    print("🧪 SIMPLIFIED GEMMA COORDINATE ENHANCEMENT TEST")
    print("="*60)
    
    results = []
    for state_file, screenshot_file in test_samples:
        result = test_single_sample(state_file, screenshot_file)
        if result:
            results.append(result)
    
    # Summary
    if results:
        hit_rate = np.mean([r["hit"] for r in results])
        avg_distance = np.mean([r["distance"] for r in results])
        
        print(f"\n📊 SUMMARY")
        print(f"{'='*30}")
        print(f"Tests run: {len(results)}")
        print(f"Hit rate: {hit_rate*100:.0f}%")
        print(f"Avg distance: {avg_distance:.1f}px")
    else:
        print("\n❌ No successful tests")


if __name__ == "__main__":
    main()