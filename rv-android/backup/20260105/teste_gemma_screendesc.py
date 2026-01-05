#!/usr/bin/env python3
"""
Test Gemma with ScreenDescription format including coordinates.

This test uses the exact format from the real system but enriched with
coordinate information to help Gemma understand spatial relationships.
"""

import base64
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
from PIL import Image
from ollama import Client


class GemmaScreenDescTest:
    """Test Gemma with enriched ScreenDescription format."""
    
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
    
    def create_enriched_screen_descriptions(self) -> Dict[str, Dict]:
        """Create enriched screen descriptions with coordinates."""
        
        screens = {}
        
        # Screen 003.png - Message Digest with coordinates
        screens["003_enriched"] = {
            "description": """Current UI Elements and Available Actions:
The current screen has the following UI views and corresponding actions, with action id in parentheses:

 - Text view with text 'Crypto App' at position (540, 107) - bounds[32, 75, 1048, 139].
 - Text view with text 'Message Digest' at position (100, 179) - bounds[57, 164, 143, 194].
 - Dropdown spinner with selected item 'Select' at position (409, 223) - bounds[57, 197, 761, 249] with options: Select, MD2, MD5, SHA-1, SHA-224, and 8 more options [ERR]. Actions: CLICK (1)
 - Editable text field for textPersonName with text 'Input text ...' at position (409, 290) - bounds[57, 265, 761, 315] is assigned to a field [ERR]. Actions: CLICK (2), SET_TEXT (3)
 - Button with text 'GENERATE HASH' at position (409, 382) - bounds[32, 346, 786, 418]. Actions: CLICK (4) [M]
 - System back button at position (72, 1431) - bounds[28, 1387, 116, 1475]. Actions: BACK (5)

Screen resolution: 1080x1920 pixels
Click coordinates are provided as the CENTER point of each element's bounds.""",
            
            "targets": [
                ("dropdown", 1, (409, 223)),
                ("input_field", 2, (409, 290)),
                ("generate_button", 4, (409, 382))
            ]
        }
        
        # Screen 021.png - Cryptography Learning Tool with coordinates  
        screens["021_enriched"] = {
            "description": """Current UI Elements and Available Actions:
The current screen has the following UI views and corresponding actions, with action id in parentheses:

 - Text view with text 'Crypto App' at position (540, 107) - bounds[32, 75, 1048, 139].
 - Container android.widget.ScrollView at position (540, 900) - bounds[0, 160, 1080, 1640]. Actions: SCROLL UP (1), SCROLL DOWN (2)
 - Text view with text 'Cryptography Learning Tool' at position (409, 225) - bounds[112, 201, 706, 249].
 - Text view with text 'SECRET KEY' at position (146, 336) - bounds[57, 310, 235, 362]. Actions: CLICK (3)
 - Text view with text 'KEY PAIR' at position (354, 336) - bounds[265, 310, 443, 362]. Actions: CLICK (4)
 - Text view with text 'HASH' at position (517, 336) - bounds[446, 310, 588, 362]. Actions: CLICK (5) [SELECTED]
 - Text view with text 'HMAC' at position (662, 336) - bounds[591, 310, 733, 362]. Actions: CLICK (6)
 - Text view with text 'Select Algorithm' at position (148, 438) - bounds[57, 418, 239, 458].
 - Dropdown spinner with selected item 'MD5' at position (409, 489) - bounds[57, 462, 761, 516]. Actions: CLICK (7)
 - Editable text field with text 'Text to Hash' at position (409, 579) - bounds[57, 546, 761, 612]. Actions: CLICK (8), SET_TEXT (9)
 - Button with text 'EXECUTE' at position (409, 817) - bounds[32, 775, 786, 859]. Actions: CLICK (10) [M]
 - Text view with text 'Result' at position (112, 964) - bounds[64, 944, 160, 984].
 - System back button at position (72, 1431) - bounds[28, 1387, 116, 1475]. Actions: BACK (11)

Screen resolution: 1080x1920 pixels
Click coordinates are provided as the CENTER point of each element's bounds.""",
            
            "targets": [
                ("secret_key_tab", 3, (146, 336)),
                ("hash_tab", 5, (517, 336)),
                ("hmac_tab", 6, (662, 336)),
                ("execute_button", 10, (409, 817))
            ]
        }
        
        return screens
    
    def create_prompt_variations(self, screen_desc: str, target_name: str, action_id: int) -> Dict[str, str]:
        """Create different prompt variations."""
        
        prompts = {}
        
        # Variation 1: Direct instruction with action ID
        prompts["action_id_direct"] = f"""
{screen_desc}

Task: Click on the element with action ID ({action_id}).
Use the exact center coordinates provided in the description above.

Return JSON format:
{{"action": "click", "action_id": {action_id}, "coordinates": [x, y]}}
"""
        
        # Variation 2: Target by element description
        prompts["element_description"] = f"""
{screen_desc}

Task: Interact with the {target_name} element.
Find the element in the list above and use its center coordinates.

Return the click coordinates as JSON:
{{"action": "click", "target": "{target_name}", "coordinates": [x, y]}}
"""
        
        # Variation 3: Step by step reasoning
        prompts["step_by_step"] = f"""
{screen_desc}

Step-by-step task:
1. Find the {target_name} element in the list above
2. Look at its bounds information: bounds[left, top, right, bottom] 
3. The center coordinates are already calculated and provided as "at position (x, y)"
4. Use EXACTLY those center coordinates

Target element: {target_name}
Return: {{"coordinates": [x, y]}}
"""
        
        # Variation 4: Coordinate validation
        prompts["coordinate_validation"] = f"""
{screen_desc}

Your task is to click on the {target_name}.

IMPORTANT COORDINATE RULES:
- Screen resolution is 1080x1920 pixels
- X coordinates must be between 0 and 1080
- Y coordinates must be between 0 and 1920
- Use the center coordinates provided in "at position (x, y)"

Find {target_name} and return its exact center coordinates.
"""
        
        return prompts
    
    def test_single_prompt(self, image_path: str, prompt: str, expected_coord: Tuple[int, int], 
                          test_name: str) -> Dict[str, Any]:
        """Test a single prompt variation."""
        
        image_base64 = self.get_image_base64(image_path)
        
        messages = [
            {
                "role": "system", 
                "content": "You are a UI automation assistant. Extract coordinates EXACTLY as provided in the screen description."
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
                    "temperature": 0.05,  # Very low for deterministic output
                    "num_predict": 150,
                    "top_p": 0.8
                },
                stream=False
            )
            
            elapsed_time = time.time() - start_time
            response_text = response.message.content
            
            # Extract coordinates with multiple patterns
            import re
            coord_patterns = [
                r'"coordinates":\s*\[(\d+),\s*(\d+)\]',
                r'coordinates.*?(\d+),\s*(\d+)',
                r'\[(\d+),\s*(\d+)\]',
                r'\((\d+),\s*(\d+)\)',
                r'x.*?(\d+).*?y.*?(\d+)',
                r'(\d+),\s*(\d+)'
            ]
            
            generated_coord = None
            for pattern in coord_patterns:
                matches = re.findall(pattern, response_text)
                if matches:
                    # Take the first valid coordinate pair
                    for match in matches:
                        x, y = int(match[0]), int(match[1])
                        if 0 <= x <= 1080 and 0 <= y <= 1920:  # Basic bounds check
                            generated_coord = (x, y)
                            break
                    if generated_coord:
                        break
            
            if generated_coord:
                distance = np.sqrt((generated_coord[0] - expected_coord[0])**2 + 
                                 (generated_coord[1] - expected_coord[1])**2)
                hit = distance < 50
                
                self.logger.info(f"  {test_name}: Generated {generated_coord}, Expected {expected_coord}")
                self.logger.info(f"    Distance: {distance:.1f}px, Hit: {hit}")
                
                return {
                    "test_name": test_name,
                    "success": True,
                    "generated": generated_coord,
                    "expected": expected_coord,
                    "distance": distance,
                    "hit": hit,
                    "response_excerpt": response_text[:150],
                    "time": elapsed_time
                }
                
            else:
                self.logger.error(f"  {test_name}: Failed to extract coordinates")
                self.logger.debug(f"    Response: {response_text[:200]}")
                
                return {
                    "test_name": test_name,
                    "success": False,
                    "error": "No valid coordinates found",
                    "response_excerpt": response_text[:150],
                    "time": elapsed_time
                }
                
        except Exception as e:
            self.logger.error(f"  {test_name}: Error - {e}")
            return {
                "test_name": test_name,
                "success": False,
                "error": str(e),
                "time": 0
            }
    
    def run_screen_test(self, screen_key: str, target_idx: int = 0):
        """Run tests for a specific screen and target."""
        
        screens = self.create_enriched_screen_descriptions()
        screen_info = screens[screen_key]
        
        if target_idx >= len(screen_info["targets"]):
            self.logger.error(f"Target index {target_idx} out of range")
            return
        
        target_name, action_id, expected_coord = screen_info["targets"][target_idx]
        image_path = f"tmp_img/{screen_key.split('_')[0]}.png"
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"Testing: {screen_key} -> {target_name}")
        self.logger.info(f"Expected coordinates: {expected_coord}")
        self.logger.info(f"{'='*60}")
        
        # Create prompt variations
        prompts = self.create_prompt_variations(screen_info["description"], target_name, action_id)
        
        test_results = {
            "screen": screen_key,
            "target": target_name,
            "expected_coord": expected_coord,
            "prompt_results": []
        }
        
        # Test each prompt variation
        for prompt_name, prompt in prompts.items():
            result = self.test_single_prompt(image_path, prompt, expected_coord, prompt_name)
            test_results["prompt_results"].append(result)
            time.sleep(0.5)  # Small delay
        
        self.results.append(test_results)
        
        # Summary for this test
        successful_tests = [r for r in test_results["prompt_results"] if r.get("success")]
        hits = sum(1 for r in successful_tests if r.get("hit"))
        
        self.logger.info(f"\n--- Summary for {target_name} ---")
        self.logger.info(f"Hit Rate: {hits}/{len(successful_tests)} ({100*hits/len(successful_tests):.0f}%)")
        
        if successful_tests:
            best = min(successful_tests, key=lambda x: x.get("distance", float('inf')))
            self.logger.info(f"Best result: {best['test_name']} - {best['distance']:.1f}px")
    
    def run_comprehensive_test(self):
        """Run comprehensive test across multiple screens and targets."""
        
        test_cases = [
            ("003_enriched", 0),  # dropdown
            ("003_enriched", 1),  # input field
            ("003_enriched", 2),  # generate button
            ("021_enriched", 0),  # secret key tab
            ("021_enriched", 2),  # hmac tab
            ("021_enriched", 3),  # execute button
        ]
        
        for screen_key, target_idx in test_cases:
            self.run_screen_test(screen_key, target_idx)
        
        self.generate_final_report()
    
    def generate_final_report(self):
        """Generate comprehensive final report."""
        
        report = {
            "model": self.model,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "test_type": "enriched_screen_description",
            "results": self.results,
            "analysis": {}
        }
        
        # Overall statistics
        all_distances = []
        prompt_performance = {}
        total_hits = 0
        total_tests = 0
        
        for test in self.results:
            for result in test["prompt_results"]:
                if result.get("success") and "distance" in result:
                    distance = result["distance"]
                    all_distances.append(distance)
                    total_tests += 1
                    
                    if result.get("hit"):
                        total_hits += 1
                    
                    # Track prompt performance
                    prompt_type = result["test_name"]
                    if prompt_type not in prompt_performance:
                        prompt_performance[prompt_type] = {
                            "distances": [],
                            "hits": 0,
                            "total": 0
                        }
                    
                    prompt_performance[prompt_type]["distances"].append(distance)
                    prompt_performance[prompt_type]["total"] += 1
                    if result.get("hit"):
                        prompt_performance[prompt_type]["hits"] += 1
        
        # Calculate prompt rankings
        prompt_rankings = []
        for prompt_type, perf in prompt_performance.items():
            if perf["distances"]:
                avg_distance = np.mean(perf["distances"])
                hit_rate = perf["hits"] / perf["total"]
                
                prompt_rankings.append({
                    "prompt_type": prompt_type,
                    "avg_distance": avg_distance,
                    "hit_rate": hit_rate,
                    "total_tests": perf["total"]
                })
        
        # Sort by combination of hit rate and distance
        prompt_rankings.sort(key=lambda x: (-x["hit_rate"], x["avg_distance"]))
        
        report["analysis"] = {
            "total_tests": total_tests,
            "overall_hit_rate": total_hits / total_tests if total_tests > 0 else 0,
            "avg_distance": np.mean(all_distances) if all_distances else 0,
            "distance_std": np.std(all_distances) if all_distances else 0,
            "min_distance": min(all_distances) if all_distances else 0,
            "max_distance": max(all_distances) if all_distances else 0,
            "prompt_rankings": prompt_rankings
        }
        
        # Save detailed report
        with open("gemma_screendesc_experiment.json", "w") as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        self.logger.info(f"\n{'='*60}")
        self.logger.info("FINAL EXPERIMENT RESULTS")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Total Tests: {total_tests}")
        self.logger.info(f"Overall Hit Rate: {report['analysis']['overall_hit_rate']*100:.1f}%")
        self.logger.info(f"Average Distance: {report['analysis']['avg_distance']:.1f}px")
        self.logger.info(f"Best Distance: {report['analysis']['min_distance']:.1f}px")
        self.logger.info(f"Worst Distance: {report['analysis']['max_distance']:.1f}px")
        
        self.logger.info(f"\nPrompt Performance Ranking:")
        for i, ranking in enumerate(report["analysis"]["prompt_rankings"][:3], 1):
            self.logger.info(f"{i}. {ranking['prompt_type']}:")
            self.logger.info(f"   Hit Rate: {ranking['hit_rate']*100:.0f}%")
            self.logger.info(f"   Avg Distance: {ranking['avg_distance']:.1f}px")
        
        self.logger.info(f"\nDetailed report saved to: gemma_screendesc_experiment.json")


def main():
    """Run the enriched ScreenDescription experiment."""
    experiment = GemmaScreenDescTest()
    experiment.run_comprehensive_test()


if __name__ == "__main__":
    main()