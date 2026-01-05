#!/usr/bin/env python3
"""
Test Gemma's ability to identify and click on game elements that are not in DOM.

This test uses a Ludo game screenshot where the board is rendered dynamically
and game elements (board squares, pieces) are not present in the DroidBot state.
Perfect use case for coordinate-based actions.
"""

import base64
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
from PIL import Image, ImageDraw
from ollama import Client


@dataclass
class GameElement:
    """Represents a game element with its position and properties."""
    name: str
    element_type: str
    center: Tuple[int, int]
    description: str
    is_valid_move: bool = True


class LudoGameTester:
    """Test Gemma's ability to understand game mechanics and click on board positions."""
    
    def __init__(self, model: str = "gemma3:4b"):
        self.model = model
        self.client = Client(host="http://localhost:11434")
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        self.results = []
    
    def get_image_base64(self, image_path: str) -> str:
        """Load and encode image as base64."""
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    
    def identify_ludo_elements(self) -> List[GameElement]:
        """Manually identify key game elements visible in the Ludo screenshot."""
        
        elements = []
        
        # Dice area - clearly visible at bottom
        elements.append(GameElement(
            name="dice",
            element_type="DiceRoll",
            center=(140, 1130),
            description="Dice showing 4 dots - click to roll",
            is_valid_move=True
        ))
        
        # Brown player pieces in home (top-left corner)
        brown_home_pieces = [
            (75, 315),   # Top-left brown piece
            (135, 315),  # Top-right brown piece
            (75, 375),   # Bottom-left brown piece
            (135, 375)   # Bottom-right brown piece
        ]
        
        for i, pos in enumerate(brown_home_pieces):
            elements.append(GameElement(
                name=f"brown_piece_{i+1}",
                element_type="GamePiece",
                center=pos,
                description=f"Brown player piece {i+1} in home area",
                is_valid_move=True
            ))
        
        # Example valid board positions for brown player
        # These are estimated positions on the main board track
        board_positions = [
            (75, 585),   # Start position for brown
            (135, 585),  # Next position
            (195, 585),  # Next position
            (255, 585),  # Next position
            (315, 585),  # Next position
        ]
        
        for i, pos in enumerate(board_positions):
            elements.append(GameElement(
                name=f"board_square_{i+1}",
                element_type="BoardSquare",
                center=pos,
                description=f"Board square {i+1} on main track",
                is_valid_move=True
            ))
        
        # Some invalid positions (just for testing)
        elements.append(GameElement(
            name="invalid_position",
            element_type="BoardSquare",
            center=(500, 300),  # Random position in middle
            description="Invalid board position",
            is_valid_move=False
        ))
        
        return elements
    
    def create_ludo_prompts(self) -> Dict[str, str]:
        """Create different prompts for testing Ludo game understanding."""
        
        prompts = {}
        
        # Prompt 1: Basic game understanding
        prompts["basic_game"] = """
You are looking at a Ludo game screenshot. This is a Privacy Friendly Ludo game.

Current situation:
- It's your turn (brown pieces)
- The message says "Please roll dice"
- You can see brown pieces in the home area (top-left)
- Other players have pieces on the board (cyan, yellow, orange)

Your task: Click on the dice to roll it and start your turn.
The dice is visible at the bottom of the screen.

Return coordinates to click on the dice:
{"action": "click", "target": "dice", "coordinates": [x, y]}
"""
        
        # Prompt 2: Strategic game play
        prompts["strategic_play"] = """
You are playing Ludo as the brown player. Analyze the current game state:

GAME ANALYSIS:
- Brown player (you): 4 pieces in home area (top-left corner)
- Cyan player: Has pieces on the board
- Yellow player: Has pieces on the board  
- Orange player: Has pieces on the board
- Current instruction: "Please roll dice"

LUDO RULES REMINDER:
- Click on dice first to roll
- If you roll 6, you can move a piece out of home
- Move pieces clockwise around the board
- Land on opponent pieces to send them back

TASK: Make your first move in this turn.
What should you click on? Provide exact coordinates.

Return: {"action": "click", "target": "dice_or_piece", "coordinates": [x, y], "reasoning": "explanation"}
"""
        
        # Prompt 3: Coordinate precision test
        prompts["coordinate_precision"] = """
Look at this Ludo game board carefully. I need you to identify clickable elements.

VISIBLE ELEMENTS:
1. Dice area (bottom of screen with black dots)
2. Brown pieces in home (top-left corner, 4 circular pieces)
3. Board squares (white circles forming the game track)
4. Other player pieces (cyan, yellow, orange colors)

TASK: Click on the dice to roll it.
Examine the bottom part of the screen where you see a brown square with black dots.
Click precisely in the center of this dice area.

Screen resolution: 1080x1920
Return exact pixel coordinates: {"coordinates": [x, y]}
"""
        
        # Prompt 4: Game state reasoning
        prompts["game_reasoning"] = """
LUDO GAME SITUATION ANALYSIS:

Current Board State:
- Brown player: All pieces in starting home (top-left 2x2 grid)
- Cyan player: Multiple pieces on board, some highlighted
- Yellow player: Multiple pieces on board, some near home
- Orange player: Some pieces on board
- Game message: "It's your turn player - Please roll dice"

GAME RULES:
- Must roll dice before moving
- Need 6 to get pieces out of home
- Move pieces clockwise around outer track
- Goal: Get all pieces to center home area

QUESTION: What is the very first action you should take?
Look at the current game state and identify what needs to be clicked.

Provide coordinates and explanation:
{"action": "click", "coordinates": [x, y], "explanation": "why this action"}
"""
        
        return prompts
    
    def test_ludo_prompt(self, prompt_name: str, prompt: str, 
                        expected_elements: List[GameElement]) -> Dict[str, Any]:
        """Test a single Ludo prompt and evaluate the response."""
        
        self.logger.info(f"Testing prompt: {prompt_name}")
        
        image_path = "tmp_img/ludo_008.png"
        image_base64 = self.get_image_base64(image_path)
        
        messages = [
            {
                "role": "system",
                "content": "You are an expert Ludo game player with perfect vision. Analyze game screenshots and provide precise coordinates for game actions."
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
                    "temperature": 0.2,  # Low for consistent game analysis
                    "num_predict": 300,
                    "top_p": 0.9
                },
                stream=False
            )
            
            elapsed_time = time.time() - start_time
            response_text = response.message.content
            
            self.logger.debug(f"Response: {response_text[:200]}...")
            
            # Extract coordinates
            coordinates = self._extract_coordinates(response_text)
            
            if coordinates:
                # Evaluate coordinate accuracy
                evaluation = self._evaluate_coordinates(coordinates, expected_elements)
                
                result = {
                    "prompt_name": prompt_name,
                    "success": True,
                    "coordinates": coordinates,
                    "evaluation": evaluation,
                    "response_text": response_text,
                    "time": elapsed_time
                }
                
                self.logger.info(f"  Generated: {coordinates}")
                self.logger.info(f"  Evaluation: {evaluation['best_match']['element_name']} - {evaluation['best_match']['distance']:.1f}px")
                
            else:
                result = {
                    "prompt_name": prompt_name,
                    "success": False,
                    "error": "No coordinates extracted",
                    "response_text": response_text,
                    "time": elapsed_time
                }
                self.logger.error(f"  Failed to extract coordinates")
            
            return result
            
        except Exception as e:
            self.logger.error(f"  Error: {e}")
            return {
                "prompt_name": prompt_name,
                "success": False,
                "error": str(e),
                "time": 0
            }
    
    def _extract_coordinates(self, text: str) -> Optional[Tuple[int, int]]:
        """Extract coordinates from LLM response."""
        import re
        
        # Multiple coordinate patterns
        patterns = [
            r'"coordinates":\s*\[(\d+),\s*(\d+)\]',
            r'coordinates.*?(\d+),\s*(\d+)',
            r'\[(\d+),\s*(\d+)\]',
            r'\((\d+),\s*(\d+)\)',
            r'x[:\s]*(\d+).*?y[:\s]*(\d+)',
            r'(\d+)\s*,\s*(\d+)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                for match in matches:
                    x, y = int(match[0]), int(match[1])
                    # Basic sanity check
                    if 0 <= x <= 1080 and 0 <= y <= 1920:
                        return (x, y)
        
        return None
    
    def _evaluate_coordinates(self, coords: Tuple[int, int], 
                            expected_elements: List[GameElement]) -> Dict[str, Any]:
        """Evaluate how close the coordinates are to expected game elements."""
        
        x, y = coords
        distances = []
        
        for element in expected_elements:
            ex, ey = element.center
            distance = np.sqrt((x - ex)**2 + (y - ey)**2)
            distances.append({
                "element_name": element.name,
                "element_type": element.element_type,
                "distance": distance,
                "is_valid_move": element.is_valid_move,
                "element": element
            })
        
        # Sort by distance
        distances.sort(key=lambda x: x["distance"])
        
        best_match = distances[0]
        
        # Determine if it's a reasonable click
        is_reasonable = best_match["distance"] < 100  # Within 100px
        is_on_game_element = best_match["distance"] < 50  # Within 50px of a known element
        
        return {
            "best_match": best_match,
            "is_reasonable": is_reasonable,
            "is_on_game_element": is_on_game_element,
            "all_distances": distances[:3]  # Top 3 closest
        }
    
    def create_visualization(self, coordinates: Tuple[int, int], 
                           expected_elements: List[GameElement],
                           save_path: str):
        """Create a visualization showing generated coordinates vs expected elements."""
        
        # Load original image
        img = Image.open("tmp_img/ludo_008.png")
        draw = ImageDraw.Draw(img)
        
        # Draw expected elements (blue circles)
        for element in expected_elements:
            x, y = element.center
            radius = 20
            # Different colors for different element types
            if element.element_type == "DiceRoll":
                color = "red"
            elif element.element_type == "GamePiece":
                color = "blue"
            else:
                color = "green"
            
            # Draw circle around element
            draw.ellipse([x-radius, y-radius, x+radius, y+radius], 
                        outline=color, width=3)
            
            # Add label
            draw.text((x, y-30), element.name[:10], fill=color)
        
        # Draw generated coordinate (large red X)
        if coordinates:
            x, y = coordinates
            size = 15
            draw.line([x-size, y-size, x+size, y+size], fill="red", width=4)
            draw.line([x-size, y+size, x+size, y-size], fill="red", width=4)
            draw.text((x, y+20), f"GENERATED\n({x},{y})", fill="red")
        
        img.save(save_path)
        self.logger.info(f"Visualization saved to: {save_path}")
    
    def run_ludo_experiment(self):
        """Run comprehensive Ludo game coordinate test."""
        
        self.logger.info("="*60)
        self.logger.info("LUDO GAME COORDINATE EXPERIMENT")
        self.logger.info("="*60)
        
        # Get expected game elements
        expected_elements = self.identify_ludo_elements()
        
        self.logger.info(f"Identified {len(expected_elements)} game elements:")
        for elem in expected_elements[:5]:  # Show first 5
            self.logger.info(f"  - {elem.name}: {elem.center} ({elem.element_type})")
        
        # Create and test prompts
        prompts = self.create_ludo_prompts()
        
        experiment_results = []
        
        for prompt_name, prompt in prompts.items():
            result = self.test_ludo_prompt(prompt_name, prompt, expected_elements)
            experiment_results.append(result)
            
            # Create visualization for successful tests
            if result.get("success") and result.get("coordinates"):
                viz_path = f"ludo_visualization_{prompt_name}.png"
                self.create_visualization(
                    result["coordinates"], 
                    expected_elements, 
                    viz_path
                )
            
            time.sleep(1)  # Delay between tests
        
        # Generate report
        self._generate_ludo_report(experiment_results, expected_elements)
        
        return experiment_results
    
    def _generate_ludo_report(self, results: List[Dict], expected_elements: List[GameElement]):
        """Generate comprehensive report of Ludo experiment."""
        
        self.logger.info("\n" + "="*60)
        self.logger.info("LUDO EXPERIMENT RESULTS")
        self.logger.info("="*60)
        
        successful_tests = [r for r in results if r.get("success")]
        
        self.logger.info(f"Successful tests: {len(successful_tests)}/{len(results)}")
        
        for result in successful_tests:
            eval_data = result.get("evaluation", {})
            best_match = eval_data.get("best_match", {})
            
            self.logger.info(f"\n{result['prompt_name']}:")
            self.logger.info(f"  Coordinates: {result['coordinates']}")
            self.logger.info(f"  Closest element: {best_match.get('element_name', 'unknown')}")
            self.logger.info(f"  Distance: {best_match.get('distance', 0):.1f}px")
            self.logger.info(f"  Valid game element: {eval_data.get('is_on_game_element', False)}")
            self.logger.info(f"  Reasonable click: {eval_data.get('is_reasonable', False)}")
        
        # Overall statistics
        if successful_tests:
            all_distances = [r["evaluation"]["best_match"]["distance"] 
                           for r in successful_tests if "evaluation" in r]
            
            if all_distances:
                avg_distance = np.mean(all_distances)
                min_distance = min(all_distances)
                
                self.logger.info(f"\nOverall Statistics:")
                self.logger.info(f"  Average distance to nearest element: {avg_distance:.1f}px")
                self.logger.info(f"  Best distance: {min_distance:.1f}px")
                
                # Count how many hit actual game elements
                on_target = sum(1 for r in successful_tests 
                              if r.get("evaluation", {}).get("is_on_game_element", False))
                self.logger.info(f"  Direct hits on game elements: {on_target}/{len(successful_tests)}")
        
        # Save detailed results
        report = {
            "experiment_type": "ludo_game_coordinates",
            "model": self.model,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "expected_elements": [
                {
                    "name": elem.name,
                    "type": elem.element_type,
                    "center": elem.center,
                    "description": elem.description
                } for elem in expected_elements
            ],
            "results": results
        }
        
        with open("ludo_experiment_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"\nDetailed report saved to: ludo_experiment_report.json")


def main():
    """Run the Ludo game coordinate experiment."""
    
    tester = LudoGameTester()
    results = tester.run_ludo_experiment()
    
    print(f"\nExperiment completed. {len(results)} tests run.")
    print("Check visualization images and report for detailed analysis.")


if __name__ == "__main__":
    main()