#!/usr/bin/env python3
"""
Test Gemma coordinate generation on games and dynamically rendered elements.
These elements are NOT in the DOM/ScreenDescription and require custom coordinates.
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

def test_game_elements():
    """Test coordinate generation for game elements that aren't in DOM."""
    
    client = Client(host="http://localhost:11434")
    
    # Test cases for different games
    game_tests = [
        {
            "name": "Privacy Friendly Ludo",
            "apk": "org.secuso.privacyfriendlyludo_5.apk",
            "screenshot": "012.png",  # Game board visible
            "elements_to_test": [
                {"name": "dice_area", "description": "Click on dice to roll", "expected_region": (50, 150, 200, 300)},
                {"name": "game_piece", "description": "Click on your game piece to move", "expected_region": (300, 600, 800, 1000)},
                {"name": "board_square", "description": "Click on valid move square", "expected_region": (200, 400, 600, 800)}
            ]
        },
        {
            "name": "Hex Game", 
            "apk": "com.sam.hex_16.apk",
            "screenshot": "016.png",  # Hex board
            "elements_to_test": [
                {"name": "hex_cell", "description": "Click on empty hex cell to place stone", "expected_region": (200, 400, 880, 1200)},
                {"name": "game_board", "description": "Click center of hex board", "expected_region": (300, 500, 780, 1000)}
            ]
        },
        {
            "name": "Privacy Friendly Dicer",
            "apk": "org.secuso.privacyfriendlydicer_8.apk", 
            "screenshot": "005.png",  # Dice interface
            "elements_to_test": [
                {"name": "dice_face", "description": "Click on dice to roll", "expected_region": (200, 400, 880, 1400)},
                {"name": "roll_area", "description": "Click anywhere to roll dice", "expected_region": (100, 300, 980, 1600)}
            ]
        }
    ]
    
    print("🎮 TESTING GEMMA ON GAME ELEMENTS")
    print("=" * 60)
    
    results = []
    
    for game in game_tests:
        print(f"\n🎯 Testing: {game['name']}")
        print(f"APK: {game['apk']}")
        
        screenshot_path = f"/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/tmp_img/screenshots/{game['apk']}/{game['screenshot']}"
        
        if not Path(screenshot_path).exists():
            print(f"❌ Screenshot not found: {screenshot_path}")
            continue
            
        # Load screenshot
        try:
            with open(screenshot_path, 'rb') as f:
                image_b64 = base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            print(f"❌ Error loading screenshot: {e}")
            continue
        
        # Test each game element
        for element in game['elements_to_test']:
            print(f"\n  🔍 Testing: {element['name']}")
            
            # Create game-specific prompt
            prompt = create_game_prompt(game, element)
            
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert game tester. Analyze game screenshots and provide precise coordinates for game interactions."
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
                    options={"temperature": 0.3, "num_predict": 200},
                    stream=False
                )
                
                response_text = response.message.content
                print(f"    Response: {response_text[:100]}...")
                
                # Extract coordinates
                coords = extract_coordinates(response_text)
                
                if coords:
                    # Check if coordinates are in expected region
                    expected = element['expected_region']
                    is_in_region = (expected[0] <= coords[0] <= expected[2] and 
                                  expected[1] <= coords[1] <= expected[3])
                    
                    # Calculate distance from region center
                    region_center = ((expected[0] + expected[2]) // 2, (expected[1] + expected[3]) // 2)
                    distance = np.sqrt((coords[0] - region_center[0])**2 + (coords[1] - region_center[1])**2)
                    
                    result = {
                        "game": game['name'],
                        "element": element['name'],
                        "generated_coords": coords,
                        "expected_region": expected,
                        "region_center": region_center,
                        "distance_from_center": distance,
                        "in_expected_region": is_in_region,
                        "response": response_text
                    }
                    
                    results.append(result)
                    
                    print(f"    Generated: {coords}")
                    print(f"    Expected Region: {expected}")
                    print(f"    Distance from center: {distance:.1f}px")
                    print(f"    In region: {'✅' if is_in_region else '❌'}")
                else:
                    print(f"    ❌ No coordinates extracted from response")
                    
            except Exception as e:
                print(f"    ❌ Error testing element: {e}")
    
    # Summary
    if results:
        in_region_count = sum(1 for r in results if r['in_expected_region'])
        avg_distance = np.mean([r['distance_from_center'] for r in results])
        
        print(f"\n📊 GAME ELEMENTS SUMMARY")
        print(f"{'='*40}")
        print(f"Tests completed: {len(results)}")
        print(f"In expected region: {in_region_count}/{len(results)} ({in_region_count/len(results)*100:.1f}%)")
        print(f"Average distance from region center: {avg_distance:.1f}px")
        
        # Save results
        with open("game_elements_test_results.json", 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"💾 Detailed results saved to: game_elements_test_results.json")
        
        return results
    
    return []

def create_game_prompt(game_info: Dict, element_info: Dict) -> str:
    """Create game-specific prompt for coordinate generation."""
    
    game_prompts = {
        "Privacy Friendly Ludo": f"""
GAME: Privacy Friendly Ludo
CONTEXT: This is a digital board game where players move pieces around a board.

VISUAL ANALYSIS NEEDED:
Look for: {element_info['description']}

The game board is dynamically rendered and elements are NOT in the DOM.
You need to visually analyze the screenshot to find game elements.

TASK: {element_info['description']}
Provide exact pixel coordinates for the action.

Return JSON: {{"coordinates": [x, y], "element": "{element_info['name']}", "confidence": "high/medium/low"}}
""",
        
        "Hex Game": f"""
GAME: Hex Strategy Game
CONTEXT: This is a hex-based board game with hexagonal cells.

VISUAL ANALYSIS NEEDED:
Look for: {element_info['description']}

The hex board is dynamically rendered with individual clickable hex cells.
Analyze the visual pattern to identify clickable areas.

TASK: {element_info['description']}
Choose coordinates that would result in a successful game action.

Return JSON: {{"coordinates": [x, y], "element": "{element_info['name']}", "reasoning": "why this location"}}
""",

        "Privacy Friendly Dicer": f"""
GAME: Digital Dice Application
CONTEXT: This app simulates rolling dice with visual feedback.

VISUAL ANALYSIS NEEDED:
Look for: {element_info['description']}

The dice are rendered as visual elements that respond to touch.
Find the area where touching would trigger a dice roll.

TASK: {element_info['description']}
Provide coordinates for the touch area.

Return JSON: {{"coordinates": [x, y], "element": "{element_info['name']}", "action": "touch"}}
"""
    }
    
    return game_prompts.get(game_info['name'], f"Analyze the game screenshot and {element_info['description']}. Return coordinates in JSON format.")

def extract_coordinates(response_text: str) -> Optional[Tuple[int, int]]:
    """Extract coordinates from Gemma response."""
    
    coord_patterns = [
        r'"coordinates":\s*\[(\d+),\s*(\d+)\]',
        r'\[(\d+),\s*(\d+)\]',
        r'(\d+),\s*(\d+)',
        r'x:\s*(\d+),\s*y:\s*(\d+)',
        r'\((\d+),\s*(\d+)\)'
    ]
    
    for pattern in coord_patterns:
        match = re.search(pattern, response_text)
        if match:
            return (int(match.group(1)), int(match.group(2)))
    
    return None

def test_mixed_scenario():
    """Test scenario with both DOM elements and game elements."""
    
    print(f"\n🎭 MIXED SCENARIO TEST (DOM + Game Elements)")
    print("=" * 60)
    
    # Use a game that has both UI buttons AND game elements
    ludo_screenshot = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/tmp_img/screenshots/org.secuso.privacyfriendlyludo_5.apk/012.png"
    ludo_state = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/tmp_img/screenshots/org.secuso.privacyfriendlyludo_5.apk/012.state"
    
    if not Path(ludo_screenshot).exists() or not Path(ludo_state).exists():
        print("❌ Ludo files not found for mixed scenario test")
        return
    
    # Load state to get DOM elements
    try:
        with open(ludo_state, 'r') as f:
            state = json.load(f)
    except:
        print("❌ Could not load state file")
        return
    
    # Load screenshot
    try:
        with open(ludo_screenshot, 'rb') as f:
            image_b64 = base64.b64encode(f.read()).decode('utf-8')
    except:
        print("❌ Could not load screenshot")
        return
    
    client = Client(host="http://localhost:11434")
    
    # Mixed prompt with both DOM and game elements
    mixed_prompt = """
MIXED SCENARIO: Ludo Game with UI Controls

AVAILABLE ACTIONS:
1. DOM ELEMENTS (from UI hierarchy):
   - Back button (UI element)
   - Settings/Menu buttons (UI elements)
   
2. GAME ELEMENTS (visually rendered, not in DOM):
   - Dice area (click to roll dice)
   - Game pieces (click to move)
   - Board squares (valid move destinations)

TASK: You need to make strategic game moves. Choose between:
a) Interact with a UI element (use action description)
b) Interact with a game element (provide pixel coordinates)

Prioritize game actions over UI actions for better gameplay.

Return JSON with ONE action:
{
  "action_type": "ui" or "game",
  "target": "element description",
  "coordinates": [x, y] (if game element),
  "reasoning": "why this action"
}
"""
    
    messages = [
        {
            "role": "system",
            "content": "You are a game testing assistant. Handle both UI elements and game elements appropriately."
        },
        {
            "role": "user",
            "content": mixed_prompt,
            "images": [image_b64]
        }
    ]
    
    try:
        response = client.chat(
            model="gemma3:4b",
            messages=messages,
            options={"temperature": 0.2, "num_predict": 300},
            stream=False
        )
        
        response_text = response.message.content
        print(f"Mixed scenario response:\n{response_text}")
        
        # Try to extract action info
        try:
            # Look for JSON response
            json_match = re.search(r'\{[^}]*\}', response_text, re.DOTALL)
            if json_match:
                action_data = json.loads(json_match.group(0))
                print(f"\nParsed action: {action_data}")
                
                if action_data.get('action_type') == 'game' and 'coordinates' in action_data:
                    coords = action_data['coordinates']
                    print(f"Game coordinates: {coords}")
                    
                    # Validate if coordinates are reasonable for game area
                    if 50 <= coords[0] <= 1030 and 200 <= coords[1] <= 1700:
                        print("✅ Coordinates are in reasonable game area")
                    else:
                        print("⚠️ Coordinates seem outside typical game area")
                        
        except json.JSONDecodeError:
            print("❌ Could not parse JSON response")
            
    except Exception as e:
        print(f"❌ Error in mixed scenario test: {e}")

def main():
    """Run comprehensive game elements testing."""
    
    print("🧪 COMPREHENSIVE GAME ELEMENTS TESTING")
    print("=" * 70)
    
    # Test individual game elements
    game_results = test_game_elements()
    
    # Test mixed scenario
    test_mixed_scenario()
    
    if game_results:
        print(f"\n🎯 FINAL ANALYSIS")
        print("=" * 40)
        
        # Group by game
        games = {}
        for result in game_results:
            game_name = result['game']
            if game_name not in games:
                games[game_name] = []
            games[game_name].append(result)
        
        for game_name, results in games.items():
            in_region = sum(1 for r in results if r['in_expected_region'])
            avg_dist = np.mean([r['distance_from_center'] for r in results])
            
            print(f"{game_name}:")
            print(f"  Success rate: {in_region}/{len(results)} ({in_region/len(results)*100:.1f}%)")
            print(f"  Avg distance: {avg_dist:.1f}px")

if __name__ == "__main__":
    main()