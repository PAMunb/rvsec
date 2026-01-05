#!/usr/bin/env python3
"""
Visual debugging tool for investigating Gemma's coordinate handling in vision-based prompts.

This script systematically tests how Gemma generates coordinates for Android UI elements,
with visual overlays showing LLM-selected actions and accuracy metrics.
"""

import base64
import json
import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import numpy as np

# Image processing and visualization
from PIL import Image, ImageDraw, ImageFont
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Circle, Rectangle
# from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
# import tkinter as tk

# Ollama client
from ollama import Client

# Add modules to path if needed
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "modules" / "rv-llm" / "src"))


@dataclass
class CoordinateMetrics:
    """Metrics for analyzing coordinate accuracy."""
    pixel_distance: float
    hit_successful: bool
    relative_error: float  # Error as percentage of screen size
    element_bounds: Optional[Tuple[int, int, int, int]] = None
    confidence: float = 0.0


@dataclass
class TestResult:
    """Result of a single coordinate test."""
    test_id: str
    image_path: str
    image_size: Dict[str, List[int]]
    prompt_type: str
    llm_response: str
    coordinates_generated: List[Tuple[int, int]]
    expected_coordinates: Optional[List[Tuple[int, int]]]
    metrics: List[CoordinateMetrics]
    timing: Dict[str, float]
    model_config: Dict[str, Any]


class GemmaCoordinateTester:
    """Visual debugging tool for Gemma coordinate generation."""
    
    # Test image paths
    IMAGES = {
        "simple": "tmp_img/003.png",
        "dropdown": "tmp_img/004.png", 
        "errors": "tmp_img/009.png",
        "tabs": "tmp_img/021.png"
    }
    
    # Known UI element coordinates (manually measured for validation)
    GROUND_TRUTH = {
        "003.png": {
            "dropdown": (409, 223),  # Center of "Select" dropdown
            "input_field": (409, 290),  # Center of input field
            "generate_button": (409, 382),  # Center of GENERATE HASH button
        },
        "004.png": {
            "MD2": (100, 262),
            "MD5": (100, 358),
            "SHA-1": (100, 454),
            "SHA-256": (100, 646),
        },
        "009.png": {
            "error_dropdown": (687, 223),  # Red error indicator
            "error_input": (790, 290),  # Red error indicator
        },
        "021.png": {
            "secret_key_tab": (146, 336),
            "key_pair_tab": (354, 336),
            "hash_tab": (517, 336),  # Currently selected
            "hmac_tab": (660, 336),
            "execute_button": (409, 810),
        }
    }
    
    def __init__(self, model: str = "gemma3:4b", debug: bool = True):
        """Initialize the tester with Ollama client and visualization setup."""
        self.model = model
        self.debug = debug
        
        # Setup logging
        logging.basicConfig(
            level=logging.DEBUG if debug else logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Initialize Ollama client
        self.client = Client(host="http://localhost:11434")
        self.logger.info(f"Initialized Ollama client with model: {model}")
        
        # Results storage
        self.test_results: List[TestResult] = []
        
        # Matplotlib setup
        plt.rcParams['figure.figsize'] = (16, 8)
        
    def get_image_base64(self, image_path: str, resize_to: Optional[Tuple[int, int]] = None) -> str:
        """Load and encode image, optionally resizing."""
        img = Image.open(image_path)
        original_size = img.size
        
        if resize_to:
            img = img.resize(resize_to, Image.Resampling.LANCZOS)
            self.logger.debug(f"Resized image from {original_size} to {resize_to}")
        
        # Convert to base64
        import io
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return encoded
    
    def create_test_prompts(self) -> Dict[str, Dict[str, str]]:
        """Create specific test prompts for each screenshot."""
        prompts = {}
        
        # Prompt for 003.png - Simple interface
        prompts["003_simple"] = {
            "system": "You are an Android UI testing assistant. Analyze the screenshot and generate precise click actions with exact pixel coordinates. The screen resolution is clearly visible in the image.",
            "user": """Look at this Android cryptography app screenshot. Generate actions to test the hash functionality:
1. Click on the dropdown that shows "Select" to open the algorithm selection
2. Click on the text input field below it
3. Click the blue "GENERATE HASH" button at the bottom

Return a JSON response with exact pixel coordinates:
{
  "actions": [
    {"action": "click", "coordinates": [x, y], "target": "dropdown_select"},
    {"action": "click", "coordinates": [x, y], "target": "input_field"},
    {"action": "click", "coordinates": [x, y], "target": "generate_button"}
  ]
}

Be precise with coordinates - look at the actual pixel positions in the image."""
        }
        
        # Prompt for 004.png - Dropdown expanded
        prompts["004_dropdown"] = {
            "system": "You are analyzing an Android screen with an expanded dropdown menu showing cryptographic hash algorithms.",
            "user": """The dropdown is open showing a list of hash algorithms. Each item in the list is approximately 96 pixels tall.
Generate the exact coordinates to click on these items:
1. Click on "MD5" (second item)
2. Click on "SHA-256" (fifth item)

The list starts at approximately y=166 and each item is centered horizontally around x=400.

Return JSON with precise pixel coordinates:
{
  "actions": [
    {"action": "click", "coordinates": [x, y], "target": "MD5"},
    {"action": "click", "coordinates": [x, y], "target": "SHA-256"}
  ]
}"""
        }
        
        # Prompt for 009.png - Error indicators
        prompts["009_errors"] = {
            "system": "You are analyzing an Android screen with red error indicator circles containing exclamation marks.",
            "user": """There are two red circular error indicators visible on the screen:
1. One to the right of the dropdown selector (near coordinates around x=687)
2. One to the right of the input field (near coordinates around x=790)

Generate coordinates to click on the CENTER of each red error circle:
{
  "actions": [
    {"action": "click", "coordinates": [x, y], "target": "error_dropdown"},
    {"action": "click", "coordinates": [x, y], "target": "error_input"}
  ]
}

The red circles are approximately 40 pixels in diameter. Click in their center."""
        }
        
        # Prompt for 021.png - Tabbed interface
        prompts["021_tabs"] = {
            "system": "You are testing a tabbed interface in an Android cryptography app. The screen shows 4 tabs at the top.",
            "user": """The screen has 4 tabs: SECRET KEY, KEY PAIR, HASH (selected with blue underline), HMAC.
The tabs are evenly distributed horizontally across the screen (width ~820 pixels).

Generate coordinates to:
1. Click on "SECRET KEY" tab (leftmost)
2. Click on "HMAC" tab (rightmost)
3. Click the blue "EXECUTE" button

The tabs are at approximately y=336, and the button is at y=810.

Return precise coordinates:
{
  "actions": [
    {"action": "click", "coordinates": [x, y], "target": "secret_key_tab"},
    {"action": "click", "coordinates": [x, y], "target": "hmac_tab"},
    {"action": "click", "coordinates": [x, y], "target": "execute_button"}
  ]
}"""
        }
        
        return prompts
    
    def parse_llm_response(self, response: str) -> List[Tuple[int, int]]:
        """Extract coordinates from LLM response."""
        coordinates = []
        
        try:
            # Try to parse as JSON
            import re
            
            # Find JSON in response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                
                if "actions" in data:
                    for action in data["actions"]:
                        if "coordinates" in action:
                            coords = action["coordinates"]
                            if isinstance(coords, list) and len(coords) == 2:
                                coordinates.append((int(coords[0]), int(coords[1])))
                                self.logger.debug(f"Extracted coordinates: {coords} for {action.get('target', 'unknown')}")
        except Exception as e:
            self.logger.error(f"Failed to parse LLM response: {e}")
            
            # Fallback: try to find coordinate patterns
            import re
            coord_pattern = r'\[(\d+),\s*(\d+)\]'
            matches = re.findall(coord_pattern, response)
            for match in matches:
                coordinates.append((int(match[0]), int(match[1])))
                self.logger.debug(f"Extracted coordinates via regex: ({match[0]}, {match[1]})")
        
        return coordinates
    
    def calculate_metrics(self, generated: Tuple[int, int], 
                         expected: Optional[Tuple[int, int]], 
                         image_size: Tuple[int, int]) -> CoordinateMetrics:
        """Calculate accuracy metrics for generated coordinates."""
        if expected is None:
            return CoordinateMetrics(
                pixel_distance=0,
                hit_successful=False,
                relative_error=0,
                confidence=0
            )
        
        # Calculate Euclidean distance
        distance = np.sqrt((generated[0] - expected[0])**2 + (generated[1] - expected[1])**2)
        
        # Calculate relative error as percentage of screen diagonal
        screen_diagonal = np.sqrt(image_size[0]**2 + image_size[1]**2)
        relative_error = (distance / screen_diagonal) * 100
        
        # Consider it a hit if within 50 pixels
        hit_successful = distance < 50
        
        # Calculate confidence based on distance
        confidence = max(0, 1 - (distance / 100))
        
        return CoordinateMetrics(
            pixel_distance=distance,
            hit_successful=hit_successful,
            relative_error=relative_error,
            confidence=confidence
        )
    
    def visualize_results(self, image_path: str, 
                         generated_coords: List[Tuple[int, int]],
                         expected_coords: Optional[Dict[str, Tuple[int, int]]] = None,
                         save_path: Optional[str] = None):
        """Visualize results with overlays on the screenshot."""
        # Load image
        img = Image.open(image_path)
        
        # Create figure with subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
        
        # Show original image
        ax1.imshow(img)
        ax1.set_title("Original Screenshot")
        ax1.axis('off')
        
        # Show image with overlays
        ax2.imshow(img)
        ax2.set_title("With Coordinate Overlays")
        ax2.axis('off')
        
        # Add generated coordinates (red circles)
        for i, (x, y) in enumerate(generated_coords):
            circle = Circle((x, y), 20, color='red', fill=False, linewidth=2, label=f"Generated {i+1}")
            ax2.add_patch(circle)
            ax2.text(x, y-30, f"G{i+1}: ({x},{y})", color='red', fontsize=8, ha='center')
        
        # Add expected coordinates if available (blue squares)
        if expected_coords:
            for label, (x, y) in expected_coords.items():
                rect = Rectangle((x-20, y-20), 40, 40, color='blue', fill=False, linewidth=2)
                ax2.add_patch(rect)
                ax2.text(x, y+30, f"E: {label[:10]}", color='blue', fontsize=8, ha='center')
        
        # Draw lines between generated and expected if both exist
        if expected_coords and generated_coords:
            expected_list = list(expected_coords.values())
            for i, gen_coord in enumerate(generated_coords[:len(expected_list)]):
                exp_coord = expected_list[i] if i < len(expected_list) else None
                if exp_coord:
                    ax2.plot([gen_coord[0], exp_coord[0]], [gen_coord[1], exp_coord[1]], 
                            'g--', alpha=0.5, linewidth=1)
                    
                    # Calculate and show distance
                    distance = np.sqrt((gen_coord[0] - exp_coord[0])**2 + (gen_coord[1] - exp_coord[1])**2)
                    mid_x = (gen_coord[0] + exp_coord[0]) / 2
                    mid_y = (gen_coord[1] + exp_coord[1]) / 2
                    ax2.text(mid_x, mid_y, f"{distance:.1f}px", color='green', fontsize=8, ha='center',
                            bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.7))
        
        # Add legend
        ax2.legend(loc='upper right', fontsize=8)
        
        plt.tight_layout()
        
        # Always save instead of showing interactively
        if not save_path:
            save_path = f"visualization_{image_path.replace('/', '_')}_{int(time.time())}.png"
        
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
        self.logger.info(f"Saved visualization to {save_path}")
        plt.close()  # Close the figure to free memory
        
        return fig
    
    def test_single_prompt(self, image_name: str, prompt_name: str, 
                          resize_to: Optional[Tuple[int, int]] = None,
                          temperature: float = 0.3,
                          max_tokens: int = 800) -> TestResult:
        """Run a single test with specific image and prompt."""
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"Testing: {prompt_name} on {image_name}")
        self.logger.info(f"{'='*60}")
        
        # Get image path
        image_path = self.IMAGES.get(image_name.split('_')[0], image_name)
        if not os.path.exists(image_path):
            self.logger.error(f"Image not found: {image_path}")
            return None
        
        # Get image and encode
        image_base64 = self.get_image_base64(image_path, resize_to)
        
        # Get original image size
        with Image.open(image_path) as img:
            original_size = img.size
        
        # Get prompt
        prompts = self.create_test_prompts()
        prompt = prompts.get(prompt_name)
        if not prompt:
            self.logger.error(f"Prompt not found: {prompt_name}")
            return None
        
        # Create messages for Ollama
        messages = [
            {"role": "system", "content": prompt["system"]},
            {"role": "user", "content": prompt["user"], "images": [image_base64]}
        ]
        
        # Call Gemma
        start_time = time.time()
        try:
            response = self.client.chat(
                model=self.model,
                messages=messages,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens,
                    "top_p": 0.9,
                    "top_k": 40
                },
                stream=False
            )
            
            elapsed_time = time.time() - start_time
            
            # Extract response
            response_text = response.message.content
            self.logger.debug(f"LLM Response:\n{response_text}")
            
            # Parse coordinates
            generated_coords = self.parse_llm_response(response_text)
            self.logger.info(f"Generated coordinates: {generated_coords}")
            
            # Get expected coordinates
            image_filename = os.path.basename(image_path)
            expected_coords = self.GROUND_TRUTH.get(image_filename, {})
            
            # Calculate metrics
            metrics = []
            for i, gen_coord in enumerate(generated_coords):
                exp_list = list(expected_coords.values())
                exp_coord = exp_list[i] if i < len(exp_list) else None
                metric = self.calculate_metrics(gen_coord, exp_coord, original_size)
                metrics.append(metric)
                
                if exp_coord:
                    self.logger.info(f"Coordinate {i+1}: Generated {gen_coord}, Expected {exp_coord}, "
                                   f"Distance: {metric.pixel_distance:.1f}px, "
                                   f"Hit: {metric.hit_successful}")
            
            # Create result
            result = TestResult(
                test_id=f"{prompt_name}_{int(time.time())}",
                image_path=image_path,
                image_size={
                    "original": list(original_size),
                    "tested": list(resize_to) if resize_to else list(original_size)
                },
                prompt_type=prompt_name,
                llm_response=response_text,
                coordinates_generated=generated_coords,
                expected_coordinates=list(expected_coords.values()) if expected_coords else None,
                metrics=metrics,
                timing={
                    "total_time": elapsed_time,
                    "prompt_eval_count": response.prompt_eval_count if hasattr(response, 'prompt_eval_count') else 0,
                    "eval_count": response.eval_count if hasattr(response, 'eval_count') else 0
                },
                model_config={
                    "model": self.model,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
            )
            
            self.test_results.append(result)
            
            # Visualize if in debug mode
            if self.debug:
                self.visualize_results(image_path, generated_coords, expected_coords)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error during test: {e}")
            return None
    
    def test_image_sizes(self, image_name: str, prompt_name: str):
        """Test the same image/prompt with different sizes."""
        self.logger.info(f"\n{'#'*60}")
        self.logger.info(f"IMAGE SIZE COMPARISON TEST")
        self.logger.info(f"{'#'*60}")
        
        sizes = [
            ("original", None),
            ("896x896", (896, 896)),
            ("896xH_aspect", None),  # Will calculate to maintain aspect ratio
        ]
        
        results = []
        for size_name, resize_to in sizes:
            if size_name == "896xH_aspect":
                # Calculate height to maintain aspect ratio
                image_path = self.IMAGES.get(image_name.split('_')[0], image_name)
                with Image.open(image_path) as img:
                    orig_w, orig_h = img.size
                    new_h = int(896 * (orig_h / orig_w))
                    resize_to = (896, new_h)
            
            self.logger.info(f"\nTesting size: {size_name} -> {resize_to}")
            result = self.test_single_prompt(image_name, prompt_name, resize_to)
            
            if result:
                results.append((size_name, result))
                
                # Calculate average accuracy
                if result.metrics:
                    avg_distance = np.mean([m.pixel_distance for m in result.metrics])
                    hit_rate = np.mean([m.hit_successful for m in result.metrics])
                    self.logger.info(f"Size {size_name}: Avg distance: {avg_distance:.1f}px, "
                                   f"Hit rate: {hit_rate*100:.0f}%")
        
        return results
    
    def run_systematic_tests(self):
        """Run all systematic tests."""
        test_cases = [
            ("simple", "003_simple"),
            ("dropdown", "004_dropdown"),
            ("errors", "009_errors"),
            ("tabs", "021_tabs"),
        ]
        
        self.logger.info("\n" + "="*80)
        self.logger.info("RUNNING SYSTEMATIC COORDINATE TESTS")
        self.logger.info("="*80)
        
        for image_name, prompt_name in test_cases:
            # Test with original size
            self.test_single_prompt(image_name, prompt_name)
            
            # Small delay between tests
            time.sleep(1)
        
        # Generate summary report
        self.generate_report()
    
    def generate_report(self, output_file: str = "gemma_coordinate_test_report.json"):
        """Generate a comprehensive test report."""
        if not self.test_results:
            self.logger.warning("No test results to report")
            return
        
        report = {
            "model": self.model,
            "total_tests": len(self.test_results),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "summary": {},
            "detailed_results": []
        }
        
        # Calculate summary statistics
        all_distances = []
        all_hits = []
        
        for result in self.test_results:
            if result.metrics:
                all_distances.extend([m.pixel_distance for m in result.metrics])
                all_hits.extend([m.hit_successful for m in result.metrics])
            
            # Add to detailed results
            report["detailed_results"].append({
                "test_id": result.test_id,
                "prompt_type": result.prompt_type,
                "image_size": result.image_size,
                "coordinates_count": len(result.coordinates_generated),
                "avg_distance": np.mean([m.pixel_distance for m in result.metrics]) if result.metrics else None,
                "hit_rate": np.mean([m.hit_successful for m in result.metrics]) if result.metrics else None,
                "timing": result.timing
            })
        
        # Summary statistics
        if all_distances:
            report["summary"] = {
                "avg_pixel_distance": float(np.mean(all_distances)),
                "std_pixel_distance": float(np.std(all_distances)),
                "min_pixel_distance": float(np.min(all_distances)),
                "max_pixel_distance": float(np.max(all_distances)),
                "overall_hit_rate": float(np.mean(all_hits)),
                "total_coordinates_tested": len(all_distances)
            }
        
        # Save report
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info("TEST REPORT SUMMARY")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Total tests run: {report['total_tests']}")
        
        if report["summary"]:
            self.logger.info(f"Average pixel distance: {report['summary']['avg_pixel_distance']:.1f}px")
            self.logger.info(f"Hit rate: {report['summary']['overall_hit_rate']*100:.1f}%")
            self.logger.info(f"Distance range: {report['summary']['min_pixel_distance']:.1f} - "
                           f"{report['summary']['max_pixel_distance']:.1f}px")
        
        self.logger.info(f"Report saved to: {output_file}")


def main():
    """Main execution function."""
    print("="*80)
    print("GEMMA COORDINATE TESTING TOOL")
    print("="*80)
    
    # Create tester instance
    tester = GemmaCoordinateTester(debug=True)
    
    # Menu for interactive testing
    while True:
        print("\nSelect test option:")
        print("1. Test single image/prompt")
        print("2. Test image size variations")
        print("3. Run all systematic tests")
        print("4. Generate report")
        print("5. Exit")
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == "1":
            # Single test
            print("\nAvailable images:")
            for key, path in tester.IMAGES.items():
                print(f"  - {key}: {path}")
            image = input("Enter image name: ").strip()
            
            print("\nAvailable prompts:")
            prompts = tester.create_test_prompts()
            for key in prompts.keys():
                print(f"  - {key}")
            prompt = input("Enter prompt name: ").strip()
            
            tester.test_single_prompt(image, prompt)
            
        elif choice == "2":
            # Size variation test
            image = input("Enter image name: ").strip()
            prompt = input("Enter prompt name: ").strip()
            tester.test_image_sizes(image, prompt)
            
        elif choice == "3":
            # Run all tests
            tester.run_systematic_tests()
            
        elif choice == "4":
            # Generate report
            tester.generate_report()
            
        elif choice == "5":
            print("Exiting...")
            break
        
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    main()