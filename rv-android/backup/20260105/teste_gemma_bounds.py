#!/usr/bin/env python3
"""
Advanced testing for Gemma coordinate generation with bounding box information.

This script tests if providing explicit coordinate information in prompts
helps Gemma generate more accurate click coordinates.
"""

import base64
import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
from PIL import Image
from ollama import Client


@dataclass 
class UIElement:
    """Represents a UI element with bounds and center point."""
    name: str
    element_type: str
    bounds: Tuple[int, int, int, int]  # left, top, right, bottom
    center: Tuple[int, int]
    text: Optional[str] = None
    
    @property
    def width(self) -> int:
        return self.bounds[2] - self.bounds[0]
    
    @property
    def height(self) -> int:
        return self.bounds[3] - self.bounds[1]


class GemmaBoundsExperiment:
    """Test Gemma with different coordinate representation strategies."""
    
    # Ground truth UI elements for test images
    UI_ELEMENTS = {
        "003.png": [
            UIElement(
                name="dropdown_select",
                element_type="Spinner",
                bounds=(56, 180, 762, 266),
                center=(409, 223),
                text="Select"
            ),
            UIElement(
                name="input_field", 
                element_type="EditText",
                bounds=(56, 270, 762, 350),
                center=(409, 310),
                text="Input text..."
            ),
            UIElement(
                name="generate_button",
                element_type="Button",
                bounds=(32, 346, 786, 430),
                center=(409, 388),
                text="GENERATE HASH"
            )
        ],
        "021.png": [
            UIElement(
                name="secret_key_tab",
                element_type="Tab",
                bounds=(57, 310, 235, 362),
                center=(146, 336),
                text="SECRET KEY"
            ),
            UIElement(
                name="key_pair_tab",
                element_type="Tab",
                bounds=(265, 310, 443, 362),
                center=(354, 336),
                text="KEY PAIR"
            ),
            UIElement(
                name="hash_tab",
                element_type="Tab",
                bounds=(446, 310, 588, 362),
                center=(517, 336),
                text="HASH"
            ),
            UIElement(
                name="hmac_tab",
                element_type="Tab",
                bounds=(591, 310, 733, 362),
                center=(662, 336),
                text="HMAC"
            ),
            UIElement(
                name="execute_button",
                element_type="Button",
                bounds=(32, 775, 787, 859),
                center=(409, 817),
                text="EXECUTE"
            )
        ]
    }
    
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
    
    def create_prompt_strategies(self, elements: List[UIElement], target: str) -> Dict[str, str]:
        """Create different prompt strategies for testing."""
        strategies = {}
        
        # Strategy 1: Explicit bounds and center
        strategies["explicit_bounds"] = f"""
You are analyzing an Android screen with resolution 1080x1920.

UI Elements with exact positions:
{self._format_elements_with_bounds(elements)}

Task: Click on the element named "{target}".
The exact center coordinates are provided above.

Return JSON with the exact center coordinates:
{{"action": "click", "coordinates": [x, y], "target": "{target}"}}
"""
        
        # Strategy 2: Grid-based reference
        strategies["grid_based"] = f"""
Screen divided into a 10x20 grid (each cell is 108x96 pixels).

Elements in grid coordinates:
{self._format_elements_as_grid(elements)}

Target: "{target}"
Convert grid position to pixel coordinates using:
x = col * 108 + 54
y = row * 96 + 48

Return exact pixel coordinates.
"""
        
        # Strategy 3: Percentage-based
        strategies["percentage_based"] = f"""
Screen dimensions: 1080x1920 pixels

Elements as percentages of screen:
{self._format_elements_as_percentages(elements)}

Target: "{target}"
Convert percentage to pixels:
x = percentage_x * 1080 / 100
y = percentage_y * 1920 / 100
"""
        
        # Strategy 4: Relative positioning
        strategies["relative_position"] = f"""
Use these reference points:
- Screen center: (540, 960)
- Top-left: (0, 0)
- Bottom-right: (1080, 1920)

Elements relative to center:
{self._format_elements_relative_to_center(elements)}

Click on "{target}" using the offset from center provided above.
"""
        
        # Strategy 5: OCR-style with text positions
        strategies["ocr_position"] = f"""
Text elements and their click positions:
{self._format_elements_as_text_positions(elements)}

To interact with "{target}", click at the position where its text appears.
Use the EXACT coordinates provided above.
"""
        
        return strategies
    
    def _format_elements_with_bounds(self, elements: List[UIElement]) -> str:
        lines = []
        for elem in elements:
            lines.append(f"""
- {elem.name} ({elem.element_type}):
  Text: "{elem.text}"
  Bounds: [{elem.bounds[0]}, {elem.bounds[1]}, {elem.bounds[2]}, {elem.bounds[3]}]
  Center (click here): ({elem.center[0]}, {elem.center[1]})
  Size: {elem.width}x{elem.height} pixels""")
        return "\n".join(lines)
    
    def _format_elements_as_grid(self, elements: List[UIElement]) -> str:
        lines = []
        for elem in elements:
            col = elem.center[0] // 108
            row = elem.center[1] // 96
            lines.append(f"- {elem.name}: Grid cell ({col}, {row})")
        return "\n".join(lines)
    
    def _format_elements_as_percentages(self, elements: List[UIElement]) -> str:
        lines = []
        for elem in elements:
            x_percent = (elem.center[0] / 1080) * 100
            y_percent = (elem.center[1] / 1920) * 100
            lines.append(f"- {elem.name}: {x_percent:.1f}% horizontal, {y_percent:.1f}% vertical")
        return "\n".join(lines)
    
    def _format_elements_relative_to_center(self, elements: List[UIElement]) -> str:
        lines = []
        screen_center = (540, 960)
        for elem in elements:
            offset_x = elem.center[0] - screen_center[0]
            offset_y = elem.center[1] - screen_center[1]
            lines.append(f"- {elem.name}: {offset_x:+d} pixels horizontal, {offset_y:+d} pixels vertical from center")
        return "\n".join(lines)
    
    def _format_elements_as_text_positions(self, elements: List[UIElement]) -> str:
        lines = []
        for elem in elements:
            if elem.text:
                lines.append(f'- Text "{elem.text}" is clickable at position ({elem.center[0]}, {elem.center[1]})')
        return "\n".join(lines)
    
    def test_strategy(self, image_path: str, strategy_name: str, prompt: str, 
                     expected_coord: Tuple[int, int]) -> Dict[str, Any]:
        """Test a single strategy and return results."""
        self.logger.info(f"Testing strategy: {strategy_name}")
        
        image_base64 = self.get_image_base64(image_path)
        
        messages = [
            {
                "role": "system",
                "content": "You are a precise UI automation assistant. Generate exact coordinates as instructed."
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
                    "temperature": 0.1,  # Lower temperature for more deterministic output
                    "num_predict": 200,
                    "top_p": 0.9,
                    "top_k": 40
                },
                stream=False
            )
            
            elapsed_time = time.time() - start_time
            response_text = response.message.content
            
            # Extract coordinates
            import re
            coord_patterns = [
                r'"coordinates":\s*\[(\d+),\s*(\d+)\]',
                r'\[(\d+),\s*(\d+)\]',
                r'\((\d+),\s*(\d+)\)'
            ]
            
            generated_coord = None
            for pattern in coord_patterns:
                match = re.search(pattern, response_text)
                if match:
                    generated_coord = (int(match.group(1)), int(match.group(2)))
                    break
            
            if generated_coord:
                distance = np.sqrt((generated_coord[0] - expected_coord[0])**2 + 
                                 (generated_coord[1] - expected_coord[1])**2)
                hit = distance < 50
                
                self.logger.info(f"  Generated: {generated_coord}, Expected: {expected_coord}")
                self.logger.info(f"  Distance: {distance:.1f}px, Hit: {hit}")
                
                return {
                    "strategy": strategy_name,
                    "success": True,
                    "generated": generated_coord,
                    "expected": expected_coord,
                    "distance": distance,
                    "hit": hit,
                    "response": response_text[:200],
                    "time": elapsed_time
                }
            else:
                self.logger.error(f"  Failed to extract coordinates from response")
                return {
                    "strategy": strategy_name,
                    "success": False,
                    "error": "No coordinates found",
                    "response": response_text[:200],
                    "time": elapsed_time
                }
                
        except Exception as e:
            self.logger.error(f"  Error: {e}")
            return {
                "strategy": strategy_name,
                "success": False,
                "error": str(e),
                "time": 0
            }
    
    def run_experiment(self, image_name: str, target_element: str):
        """Run all prompt strategies for a given image and target."""
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"Testing: {image_name} -> {target_element}")
        self.logger.info(f"{'='*60}")
        
        image_path = f"tmp_img/{image_name}"
        elements = self.UI_ELEMENTS.get(image_name, [])
        
        if not elements:
            self.logger.error(f"No UI elements defined for {image_name}")
            return
        
        # Find target element
        target = None
        for elem in elements:
            if elem.name == target_element:
                target = elem
                break
        
        if not target:
            self.logger.error(f"Target element {target_element} not found")
            return
        
        # Test each strategy
        strategies = self.create_prompt_strategies(elements, target_element)
        
        experiment_results = {
            "image": image_name,
            "target": target_element,
            "expected_coord": target.center,
            "strategy_results": []
        }
        
        for strategy_name, prompt in strategies.items():
            result = self.test_strategy(image_path, strategy_name, prompt, target.center)
            experiment_results["strategy_results"].append(result)
            time.sleep(1)  # Small delay between requests
        
        self.results.append(experiment_results)
        
        # Print summary
        self.logger.info(f"\n--- Summary for {target_element} ---")
        hits = sum(1 for r in experiment_results["strategy_results"] 
                  if r.get("success") and r.get("hit"))
        total = len(experiment_results["strategy_results"])
        self.logger.info(f"Hit rate: {hits}/{total} ({100*hits/total:.0f}%)")
        
        # Best strategy
        successful_results = [r for r in experiment_results["strategy_results"] 
                            if r.get("success") and "distance" in r]
        if successful_results:
            best = min(successful_results, key=lambda x: x["distance"])
            self.logger.info(f"Best strategy: {best['strategy']} (distance: {best['distance']:.1f}px)")
    
    def generate_report(self):
        """Generate comprehensive report of all experiments."""
        report = {
            "model": self.model,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "experiments": self.results,
            "summary": {}
        }
        
        # Calculate overall statistics
        all_distances = []
        strategy_performance = {}
        
        for exp in self.results:
            for result in exp["strategy_results"]:
                if result.get("success") and "distance" in result:
                    all_distances.append(result["distance"])
                    
                    strategy = result["strategy"]
                    if strategy not in strategy_performance:
                        strategy_performance[strategy] = {"distances": [], "hits": 0, "total": 0}
                    
                    strategy_performance[strategy]["distances"].append(result["distance"])
                    strategy_performance[strategy]["total"] += 1
                    if result.get("hit"):
                        strategy_performance[strategy]["hits"] += 1
        
        # Strategy ranking
        strategy_stats = {}
        for strategy, perf in strategy_performance.items():
            if perf["distances"]:
                strategy_stats[strategy] = {
                    "avg_distance": np.mean(perf["distances"]),
                    "hit_rate": perf["hits"] / perf["total"] if perf["total"] > 0 else 0,
                    "total_tests": perf["total"]
                }
        
        report["summary"] = {
            "total_tests": len(all_distances),
            "overall_avg_distance": np.mean(all_distances) if all_distances else 0,
            "overall_std": np.std(all_distances) if all_distances else 0,
            "strategy_ranking": sorted(strategy_stats.items(), 
                                      key=lambda x: x[1]["avg_distance"])
        }
        
        # Save report
        with open("gemma_bounds_experiment_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        self.logger.info(f"\n{'='*60}")
        self.logger.info("EXPERIMENT SUMMARY")
        self.logger.info(f"{'='*60}")
        
        if strategy_stats:
            self.logger.info("\nStrategy Performance Ranking:")
            for i, (strategy, stats) in enumerate(report["summary"]["strategy_ranking"], 1):
                self.logger.info(f"{i}. {strategy}:")
                self.logger.info(f"   Avg Distance: {stats['avg_distance']:.1f}px")
                self.logger.info(f"   Hit Rate: {stats['hit_rate']*100:.0f}%")
        
        self.logger.info(f"\nReport saved to: gemma_bounds_experiment_report.json")


def main():
    """Run the experiment with different prompt strategies."""
    experiment = GemmaBoundsExperiment()
    
    # Test cases
    test_cases = [
        ("003.png", "dropdown_select"),
        ("003.png", "generate_button"),
        ("021.png", "hash_tab"),
        ("021.png", "execute_button"),
    ]
    
    for image, target in test_cases:
        experiment.run_experiment(image, target)
    
    experiment.generate_report()


if __name__ == "__main__":
    main()