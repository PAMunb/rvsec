#!/usr/bin/env python3
"""
Generic solution for enhancing Gemma coordinate accuracy across any APK.

This experiment:
1. Uses existing ScreenDescription generation
2. Enhances action text with coordinate information  
3. Tests across multiple APKs to find universal patterns
4. Develops generic enhancement strategy for rvandroid-tool
"""

import base64
import json
import logging
import os
import random
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import numpy as np

# Add project modules to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "modules" / "rv-android-core" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-screen-parser" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-llm" / "src"))

from rv_screen_parser.parser.screen.parser_factory import ParserFactory
from rv_screen_parser.parser.screen.visitor.model import ScreenDescription
from rv_screen_parser.constants import ScreenParserType, VisitorType
from rv_android_core.domain.static import StaticAnalysisData
from rv_llm.llm.constants import StateEntry
from ollama import Client


@dataclass
class CoordinateTestResult:
    """Result of a coordinate test on an APK."""
    apk_name: str
    screenshot_file: str
    state_file: str
    original_description: str
    enhanced_description: str
    test_results: List[Dict[str, Any]]
    avg_distance: Optional[float]
    hit_rate: Optional[float]


class GenericGemmaEnhancer:
    """Generic solution for enhancing Gemma coordinate accuracy."""
    
    def __init__(self, model: str = "gemma3:4b"):
        self.model = model
        self.client = Client(host="http://localhost:11434")
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Results storage
        self.all_results: List[CoordinateTestResult] = []
    
    def discover_test_samples(self, screenshots_dir: str, max_samples: int = 20) -> List[Dict[str, str]]:
        """Discover test samples from screenshots directory."""
        samples = []
        screenshots_path = Path(screenshots_dir)
        
        # Get all APK directories
        apk_dirs = [d for d in screenshots_path.iterdir() if d.is_dir()]
        
        for apk_dir in apk_dirs:
            apk_name = apk_dir.name
            
            # Find screenshot/state pairs
            png_files = list(apk_dir.glob("*.png"))
            
            for png_file in png_files:
                state_file = apk_dir / f"{png_file.stem}.state"
                
                if state_file.exists():
                    samples.append({
                        "apk_name": apk_name,
                        "screenshot": str(png_file),
                        "state": str(state_file),
                        "screenshot_name": png_file.name
                    })
        
        # Randomly sample to limit test size
        if len(samples) > max_samples:
            samples = random.sample(samples, max_samples)
        
        self.logger.info(f"Discovered {len(samples)} test samples from {len(apk_dirs)} APKs")
        return samples
    
    def load_droidbot_state(self, state_file: str) -> Dict[str, Any]:
        """Load DroidBot state from file."""
        with open(state_file, 'r') as f:
            return json.load(f)
    
    def create_screen_description(self, state_file: str) -> ScreenDescription:
        """Create ScreenDescription using existing parsing logic."""
        try:
            droidbot_state = self.load_droidbot_state(state_file)
            
            # Create minimal static data with required fields
            static_data = StaticAnalysisData(
                classes={},
                windows={},
                wtg={}
            )
            
            # Use BasicVisitor for consistent, simple output
            parser = ParserFactory.create(ScreenParserType.DROIDBOT, VisitorType.BASIC)
            screen_description = parser.parse_screen(droidbot_state, static_data)
            
            return screen_description
            
        except Exception as e:
            self.logger.error(f"Error creating screen description: {e}")
            return None
    
    def enhance_screen_description_text(self, screen_desc: ScreenDescription) -> str:
        """Enhance the screen description text with coordinate information."""
        
        if not screen_desc or not screen_desc.items:
            return "No UI elements found."
        
        # Start with the standard header
        enhanced_lines = [
            "Current UI Elements and Available Actions:",
            "The current screen has the following UI views and corresponding actions, with action id in parentheses:"
        ]
        
        # Process each item and enhance with coordinates
        for item in screen_desc.items:
            # Start with base description
            line_parts = [f" - {item.base_description}"]
            
            # Add coordinate information if available from view data
            if item.view and 'bounds' in item.view:
                bounds = item.view['bounds']
                if bounds and isinstance(bounds, list) and len(bounds) == 2:
                    try:
                        x1, y1 = bounds[0]
                        x2, y2 = bounds[1]
                        center_x = (x1 + x2) // 2
                        center_y = (y1 + y2) // 2
                        
                        # Add position information
                        line_parts.append(f" at position ({center_x}, {center_y})")
                        line_parts.append(f" - bounds{bounds}")
                    except (TypeError, IndexError, ValueError):
                        pass
            
            # Add actions with enhanced format
            if item.actions:
                action_texts = []
                for action in item.actions:
                    action_text = f"{action.text} ({action.id})"
                    action_texts.append(action_text)
                
                if action_texts:
                    line_parts.append(f". Actions: {', '.join(action_texts)}")
            
            enhanced_lines.append("".join(line_parts))
        
        # Add coordinate usage instructions
        enhanced_lines.extend([
            "",
            "Screen resolution: 1080x1920 pixels",
            "Use coordinates provided as 'at position (x, y)' for precise element targeting."
        ])
        
        return "\n".join(enhanced_lines)
    
    def create_coordinate_test_prompts(self) -> Dict[str, str]:
        """Create different prompt variations for testing."""
        
        prompts = {}
        
        # Strategy 1: Use provided coordinates directly
        prompts["use_provided_coords"] = """
{screen_description}

Task: Look at the screen elements above and their coordinates.
Choose an interactive element and click on it using the EXACT coordinates provided in "at position (x, y)".

Return JSON with the coordinates you choose:
{{"action": "click", "coordinates": [x, y], "element": "description_of_element"}}
"""
        
        # Strategy 2: Coordinate validation approach
        prompts["coordinate_validation"] = """
{screen_description}

COORDINATE RULES:
- Screen is 1080x1920 pixels
- Each element has coordinates "at position (x, y)"  
- Use EXACTLY these coordinates, do not calculate or estimate
- X must be 0-1080, Y must be 0-1920

Task: Select any clickable element and use its provided coordinates.
Return: {{"coordinates": [x, y]}}
"""
        
        # Strategy 3: Step-by-step reasoning  
        prompts["step_by_step"] = """
{screen_description}

Step-by-step instructions:
1. Look at the list of UI elements above
2. Find an element with available actions (CLICK, SET_TEXT, etc.)
3. Note its coordinates given as "at position (x, y)"
4. Use EXACTLY those coordinates

Example: If you see "Button at position (540, 800)", use coordinates [540, 800].

Select an element and return its coordinates.
"""
        
        # Strategy 4: Natural interaction
        prompts["natural_interaction"] = """
{screen_description}

You are testing this Android app screen. Look at the available elements and their precise coordinates.

Choose what you think is the most important element to interact with first.
Use the exact coordinates provided for that element.

Return: {{"action": "click", "coordinates": [x, y], "reasoning": "why you chose this element"}}
"""
        
        return prompts
    
    def extract_coordinates_from_response(self, response: str) -> Optional[Tuple[int, int]]:
        """Extract coordinates from LLM response."""
        patterns = [
            r'"coordinates":\s*\[(\d+),\s*(\d+)\]',
            r'coordinates.*?(\d+),\s*(\d+)',
            r'\[(\d+),\s*(\d+)\]',
            r'\((\d+),\s*(\d+)\)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response)
            if match:
                x, y = int(match.group(1)), int(match.group(2))
                if 0 <= x <= 1080 and 0 <= y <= 1920:
                    return (x, y)
        
        return None
    
    def get_expected_coordinates_from_description(self, enhanced_desc: str) -> List[Tuple[int, int]]:
        """Extract all coordinate positions mentioned in description."""
        coordinates = []
        pattern = r'at position \((\d+), (\d+)\)'
        matches = re.findall(pattern, enhanced_desc)
        
        for match in matches:
            x, y = int(match[0]), int(match[1])
            coordinates.append((x, y))
        
        return coordinates
    
    def test_single_prompt_on_sample(self, sample: Dict[str, str], 
                                   prompt_name: str, prompt_template: str) -> Dict[str, Any]:
        """Test a single prompt on a single sample."""
        
        # Create enhanced screen description
        screen_desc = self.create_screen_description(sample["state"])
        if not screen_desc:
            return {"error": "Failed to create screen description"}
        
        enhanced_desc = self.enhance_screen_description_text(screen_desc)
        prompt = prompt_template.format(screen_description=enhanced_desc)
        
        # Get expected coordinates from description
        expected_coords = self.get_expected_coordinates_from_description(enhanced_desc)
        
        if not expected_coords:
            return {"error": "No coordinates found in description"}
        
        # Load image
        with open(sample["screenshot"], 'rb') as f:
            image_b64 = base64.b64encode(f.read()).decode('utf-8')
        
        # Test with Gemma
        messages = [
            {
                "role": "system",
                "content": "You are a UI automation assistant. Use coordinates exactly as provided in the screen description."
            },
            {
                "role": "user", 
                "content": prompt,
                "images": [image_b64]
            }
        ]
        
        start_time = time.time()
        
        try:
            response = self.client.chat(
                model=self.model,
                messages=messages,
                options={
                    "temperature": 0.1,
                    "num_predict": 200
                },
                stream=False
            )
            
            response_time = time.time() - start_time
            response_text = response.message.content
            
            # Extract generated coordinates
            generated_coords = self.extract_coordinates_from_response(response_text)
            
            if generated_coords:
                # Find closest expected coordinate
                distances = []
                for exp_coord in expected_coords:
                    distance = np.sqrt((generated_coords[0] - exp_coord[0])**2 + 
                                     (generated_coords[1] - exp_coord[1])**2)
                    distances.append(distance)
                
                min_distance = min(distances)
                best_match_idx = distances.index(min_distance)
                best_match_coord = expected_coords[best_match_idx]
                
                return {
                    "success": True,
                    "generated": generated_coords,
                    "expected_best_match": best_match_coord,
                    "distance": min_distance,
                    "hit": min_distance < 50,  # Within 50px considered hit
                    "response": response_text[:200],
                    "time": response_time
                }
            else:
                return {
                    "success": False,
                    "error": "No coordinates extracted",
                    "response": response_text[:200],
                    "time": response_time
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "time": 0
            }
    
    def test_sample_with_all_prompts(self, sample: Dict[str, str]) -> CoordinateTestResult:
        """Test a single sample with all prompt strategies."""
        
        self.logger.info(f"Testing {sample['apk_name']}/{sample['screenshot_name']}")
        
        # Create enhanced description
        screen_desc = self.create_screen_description(sample["state"])
        if not screen_desc:
            return None
        
        original_desc = screen_desc.description
        enhanced_desc = self.enhance_screen_description_text(screen_desc)
        
        # Test all prompts
        prompts = self.create_coordinate_test_prompts()
        test_results = []
        
        for prompt_name, prompt_template in prompts.items():
            result = self.test_single_prompt_on_sample(sample, prompt_name, prompt_template)
            result["prompt_name"] = prompt_name
            test_results.append(result)
            
            time.sleep(0.5)  # Small delay between tests
        
        # Calculate aggregate metrics
        successful_tests = [r for r in test_results if r.get("success")]
        
        if successful_tests:
            avg_distance = np.mean([r["distance"] for r in successful_tests])
            hit_rate = np.mean([r["hit"] for r in successful_tests])
        else:
            avg_distance = None
            hit_rate = None
        
        return CoordinateTestResult(
            apk_name=sample["apk_name"],
            screenshot_file=sample["screenshot"],
            state_file=sample["state"],
            original_description=original_desc,
            enhanced_description=enhanced_desc,
            test_results=test_results,
            avg_distance=avg_distance,
            hit_rate=hit_rate
        )
    
    def run_comprehensive_experiment(self, screenshots_dir: str, max_samples: int = 10):
        """Run comprehensive experiment across multiple APKs."""
        
        self.logger.info("="*80)
        self.logger.info("COMPREHENSIVE GEMMA COORDINATE EXPERIMENT")
        self.logger.info("="*80)
        
        # Discover test samples
        samples = self.discover_test_samples(screenshots_dir, max_samples)
        
        if not samples:
            self.logger.error("No test samples found!")
            return
        
        # Test each sample
        for sample in samples:
            result = self.test_sample_with_all_prompts(sample)
            
            if result:
                self.all_results.append(result)
                
                # Log immediate results
                if result.hit_rate is not None:
                    self.logger.info(f"  {result.apk_name}: Hit Rate {result.hit_rate*100:.0f}%, "
                                   f"Avg Distance {result.avg_distance:.1f}px")
                else:
                    self.logger.info(f"  {result.apk_name}: All tests failed")
        
        # Generate final analysis
        self.generate_comprehensive_analysis()
    
    def generate_comprehensive_analysis(self):
        """Generate comprehensive analysis of all results."""
        
        if not self.all_results:
            self.logger.error("No results to analyze!")
            return
        
        self.logger.info("\n" + "="*80)
        self.logger.info("COMPREHENSIVE ANALYSIS")
        self.logger.info("="*80)
        
        # Overall statistics
        successful_apks = [r for r in self.all_results if r.hit_rate is not None]
        total_apks = len(self.all_results)
        
        self.logger.info(f"APKs tested: {total_apks}")
        self.logger.info(f"APKs with successful tests: {len(successful_apks)}")
        
        if successful_apks:
            overall_hit_rate = np.mean([r.hit_rate for r in successful_apks])
            overall_avg_distance = np.mean([r.avg_distance for r in successful_apks])
            
            self.logger.info(f"Overall hit rate: {overall_hit_rate*100:.1f}%")
            self.logger.info(f"Overall average distance: {overall_avg_distance:.1f}px")
        
        # Strategy analysis
        strategy_performance = {}
        
        for result in successful_apks:
            for test in result.test_results:
                if test.get("success"):
                    strategy = test["prompt_name"]
                    if strategy not in strategy_performance:
                        strategy_performance[strategy] = {
                            "distances": [],
                            "hits": 0,
                            "total": 0
                        }
                    
                    strategy_performance[strategy]["distances"].append(test["distance"])
                    strategy_performance[strategy]["total"] += 1
                    if test["hit"]:
                        strategy_performance[strategy]["hits"] += 1
        
        # Strategy ranking
        self.logger.info(f"\nStrategy Performance Ranking:")
        strategy_rankings = []
        
        for strategy, perf in strategy_performance.items():
            if perf["total"] > 0:
                hit_rate = perf["hits"] / perf["total"]
                avg_distance = np.mean(perf["distances"])
                
                strategy_rankings.append({
                    "strategy": strategy,
                    "hit_rate": hit_rate,
                    "avg_distance": avg_distance,
                    "tests": perf["total"]
                })
        
        # Sort by hit rate first, then by distance
        strategy_rankings.sort(key=lambda x: (-x["hit_rate"], x["avg_distance"]))
        
        for i, ranking in enumerate(strategy_rankings, 1):
            self.logger.info(f"{i}. {ranking['strategy']}:")
            self.logger.info(f"   Hit Rate: {ranking['hit_rate']*100:.0f}%")
            self.logger.info(f"   Avg Distance: {ranking['avg_distance']:.1f}px")
            self.logger.info(f"   Tests: {ranking['tests']}")
        
        # Best performing APKs
        self.logger.info(f"\nBest Performing APKs:")
        successful_apks.sort(key=lambda x: (-x.hit_rate, x.avg_distance))
        
        for result in successful_apks[:5]:
            self.logger.info(f"- {result.apk_name}: {result.hit_rate*100:.0f}% hit rate, "
                           f"{result.avg_distance:.1f}px avg distance")
        
        # Save detailed report
        self.save_detailed_report()
    
    def save_detailed_report(self):
        """Save detailed JSON report."""
        
        report = {
            "model": self.model,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "experiment_type": "generic_coordinate_enhancement",
            "total_apks": len(self.all_results),
            "successful_apks": len([r for r in self.all_results if r.hit_rate is not None]),
            "results": []
        }
        
        for result in self.all_results:
            report["results"].append({
                "apk_name": result.apk_name,
                "screenshot_file": os.path.basename(result.screenshot_file),
                "hit_rate": result.hit_rate,
                "avg_distance": result.avg_distance,
                "test_results": [
                    {
                        "prompt_name": test["prompt_name"],
                        "success": test.get("success", False),
                        "distance": test.get("distance"),
                        "hit": test.get("hit"),
                        "error": test.get("error")
                    } for test in result.test_results
                ]
            })
        
        with open("gemma_generic_solution_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"\nDetailed report saved to: gemma_generic_solution_report.json")


def main():
    """Run the comprehensive generic solution experiment."""
    
    # Configuration
    screenshots_dir = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/tmp_img/screenshots"
    max_samples = 15  # Test 15 samples for comprehensive analysis
    
    # Run experiment
    enhancer = GenericGemmaEnhancer()
    enhancer.run_comprehensive_experiment(screenshots_dir, max_samples)
    
    print("\nGeneric solution experiment completed!")
    print("Check the generated report for detailed findings.")


if __name__ == "__main__":
    main()