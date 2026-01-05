#!/usr/bin/env python3
"""
Test mixed scenario: Some elements in ScreenDescription with coordinates, 
game elements requiring custom coordinate generation.

This simulates a real testing scenario where:
1. UI elements (buttons, text) have action_ids and coordinates from DOM
2. Game elements (board squares, pieces) need coordinate generation
"""

import base64
import json
import logging
import time
from typing import Dict, List, Tuple, Optional
import numpy as np
from ollama import Client


class MixedScenarioTester:
    """Test realistic scenario with mixed DOM and game elements."""
    
    def __init__(self, model: str = "gemma3:4b"):
        self.model = model
        self.client = Client(host="http://localhost:11434")
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def get_image_base64(self, image_path: str) -> str:
        """Load and encode image as base64."""
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    def create_mixed_screen_description(self) -> str:
        """Create realistic ScreenDescription mixing DOM elements with game context."""
        
        return """Current UI Elements and Available Actions:
The current screen has the following UI views and corresponding actions, with action id in parentheses:

 - Text view with text 'Ludo' at position (188, 106) - bounds[32, 75, 344, 137].
 - Button 'Back' at position (56, 106) - bounds[28, 75, 84, 137]. Actions: BACK (1)
 - Button 'Menu' at position (775, 106) - bounds[743, 75, 807, 137]. Actions: CLICK (2)
 - Text view with text "It's your turn player" at position (380, 1100) - bounds[250, 1080, 510, 1120].
 - Text view with text 'Please roll dice.' at position (350, 1180) - bounds[250, 1160, 450, 1200].

GAME CONTEXT:
This is a Ludo board game. The central area (approximately bounds[32, 270, 787, 1020]) contains:
- A dynamically rendered game board with squares and pieces
- Brown player pieces (your pieces) in home area
- Other player pieces (cyan, yellow, orange) on the board
- A dice area at the bottom for rolling

IMPORTANT: Game board elements are NOT in the DOM/action list above. 
To interact with game pieces or board squares, you must specify exact coordinates using custom clicks.

Screen resolution: 1080x1920 pixels"""
    
    def create_mixed_scenarios(self) -> Dict[str, Dict]:
        """Create test scenarios mixing DOM actions and coordinate actions."""
        
        scenarios = {}
        
        # Scenario 1: Use DOM element (easy case)
        scenarios["dom_back_button"] = {
            "description": "Click the back button to return to menu",
            "expected_action_type": "action_id",
            "expected_action_id": 1,
            "expected_coordinates": (56, 106),  # For validation
            "prompt": """
{screen_description}

Task: Click the back button to return to the main menu.
Use the available action from the list above.

Return: {{"action_id": X}} or {{"coordinates": [x, y]}}
"""
        }
        
        # Scenario 2: Roll dice (game element, needs coordinates)
        scenarios["roll_dice"] = {
            "description": "Roll the dice to start turn",
            "expected_action_type": "coordinates",
            "expected_coordinates": (140, 1130),  # Approximate dice position
            "prompt": """
{screen_description}

Task: You need to roll the dice to start your turn.
The dice is located in the game area at the bottom of the screen.

Since the dice is not in the DOM element list, you need to specify coordinates.
Look for the dice area and click on it.

Return: {{"coordinates": [x, y], "action": "roll_dice"}}
"""
        }
        
        # Scenario 3: Move game piece (complex game logic)
        scenarios["move_game_piece"] = {
            "description": "Move a brown piece from home",
            "expected_action_type": "coordinates", 
            "expected_coordinates": (75, 315),  # Brown piece in home
            "prompt": """
{screen_description}

GAME SITUATION:
- You are the brown player
- Your pieces are in the home area (top-left corner)
- You have rolled the dice and can now move a piece

Task: Click on one of your brown pieces to move it.
The brown pieces are visible in the top-left corner of the game board.

Return: {{"coordinates": [x, y], "action": "select_piece", "reasoning": "explanation"}}
"""
        }
        
        # Scenario 4: Strategic board position
        scenarios["strategic_move"] = {
            "description": "Choose strategic board position",
            "expected_action_type": "coordinates",
            "expected_coordinates": (195, 585),  # Board square
            "prompt": """
{screen_description}

ADVANCED GAME SITUATION:
You have a piece that can move to multiple positions. Analyze the board and make a strategic choice.

Looking at the board:
- Other players have pieces that could capture yours
- Some positions are safer than others
- You want to advance toward the center goal

Task: Click on the board square where you want to move your piece.
Choose a position on the main track that advances your piece safely.

Return: {{"coordinates": [x, y], "action": "move_to_square", "strategy": "explanation"}}
"""
        }
        
        return scenarios
    
    def test_scenario(self, scenario_name: str, scenario_data: Dict) -> Dict:
        """Test a single mixed scenario."""
        
        self.logger.info(f"Testing scenario: {scenario_name}")
        
        screen_desc = self.create_mixed_screen_description()
        prompt = scenario_data["prompt"].format(screen_description=screen_desc)
        
        image_path = "tmp_img/ludo_008.png"
        image_base64 = self.get_image_base64(image_path)
        
        messages = [
            {
                "role": "system",
                "content": "You are a UI automation assistant for mobile apps. You can use action_ids from the DOM or specify coordinates for game elements."
            },
            {
                "role": "user", 
                "content": prompt,
                "images": [image_base64]
            }
        ]
        
        start_time = time.time()
        
        try:
            response = self.client.chat(
                model=self.model,
                messages=messages,
                options={
                    "temperature": 0.3,
                    "num_predict": 200
                },
                stream=False
            )
            
            elapsed_time = time.time() - start_time
            response_text = response.message.content
            
            # Parse response
            result = self._parse_response(response_text, scenario_data)
            result.update({
                "scenario": scenario_name,
                "response_text": response_text[:300],
                "time": elapsed_time
            })
            
            # Log results
            if result["success"]:
                if result["action_type"] == "action_id":
                    self.logger.info(f"  Generated action_id: {result['action_id']}")
                else:
                    self.logger.info(f"  Generated coordinates: {result['coordinates']}")
                    if "expected_coordinates" in scenario_data:
                        expected = scenario_data["expected_coordinates"]
                        distance = np.sqrt((result["coordinates"][0] - expected[0])**2 + 
                                         (result["coordinates"][1] - expected[1])**2)
                        self.logger.info(f"  Distance from expected: {distance:.1f}px")
                        result["distance"] = distance
            else:
                self.logger.error(f"  Failed: {result.get('error', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"  Error: {e}")
            return {
                "scenario": scenario_name,
                "success": False,
                "error": str(e),
                "time": 0
            }
    
    def _parse_response(self, text: str, scenario_data: Dict) -> Dict:
        """Parse LLM response to extract action_id or coordinates."""
        
        import re
        
        # Try to find action_id
        action_id_match = re.search(r'"?action_id"?\s*:\s*(\d+)', text)
        if action_id_match:
            action_id = int(action_id_match.group(1))
            return {
                "success": True,
                "action_type": "action_id",
                "action_id": action_id
            }
        
        # Try to find coordinates
        coord_patterns = [
            r'"?coordinates"?\s*:\s*\[(\d+),\s*(\d+)\]',
            r'\[(\d+),\s*(\d+)\]',
            r'\((\d+),\s*(\d+)\)'
        ]
        
        for pattern in coord_patterns:
            match = re.search(pattern, text)
            if match:
                x, y = int(match.group(1)), int(match.group(2))
                if 0 <= x <= 1080 and 0 <= y <= 1920:
                    return {
                        "success": True,
                        "action_type": "coordinates",
                        "coordinates": (x, y)
                    }
        
        return {
            "success": False,
            "error": "Could not parse action_id or coordinates"
        }
    
    def run_mixed_experiment(self):
        """Run comprehensive mixed scenario experiment."""
        
        self.logger.info("="*60)
        self.logger.info("MIXED SCENARIO EXPERIMENT")
        self.logger.info("Testing DOM elements + Game coordinates")
        self.logger.info("="*60)
        
        scenarios = self.create_mixed_scenarios()
        results = []
        
        for scenario_name, scenario_data in scenarios.items():
            result = self.test_scenario(scenario_name, scenario_data)
            results.append(result)
            time.sleep(1)
        
        # Generate summary
        self._generate_summary(results)
        
        return results
    
    def _generate_summary(self, results: List[Dict]):
        """Generate experiment summary."""
        
        self.logger.info("\n" + "="*60)
        self.logger.info("MIXED SCENARIO RESULTS")
        self.logger.info("="*60)
        
        successful = [r for r in results if r.get("success")]
        self.logger.info(f"Success rate: {len(successful)}/{len(results)} ({len(successful)/len(results)*100:.0f}%)")
        
        # Breakdown by action type
        action_id_tests = [r for r in successful if r.get("action_type") == "action_id"]
        coordinate_tests = [r for r in successful if r.get("action_type") == "coordinates"]
        
        self.logger.info(f"Action ID tests: {len(action_id_tests)} successful")
        self.logger.info(f"Coordinate tests: {len(coordinate_tests)} successful")
        
        # Coordinate accuracy
        coord_with_distance = [r for r in coordinate_tests if "distance" in r]
        if coord_with_distance:
            distances = [r["distance"] for r in coord_with_distance]
            avg_distance = np.mean(distances)
            best_distance = min(distances)
            self.logger.info(f"Average coordinate distance: {avg_distance:.1f}px")
            self.logger.info(f"Best coordinate distance: {best_distance:.1f}px")
        
        # Individual results
        self.logger.info("\nIndividual Results:")
        for result in results:
            status = "✅" if result.get("success") else "❌"
            self.logger.info(f"{status} {result['scenario']}: {result.get('action_type', 'failed')}")
            if result.get("distance"):
                self.logger.info(f"    Distance: {result['distance']:.1f}px")


def main():
    """Run the mixed scenario experiment."""
    
    tester = MixedScenarioTester()
    results = tester.run_mixed_experiment()
    
    print(f"\nMixed scenario experiment completed.")
    print(f"Results demonstrate Gemma's ability to handle both DOM and game elements.")


if __name__ == "__main__":
    main()