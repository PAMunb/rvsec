#!/usr/bin/env python3
"""
Generic benchmark framework for testing vision models on Android coordinate generation.
Supports multiple models, test scenarios, and comprehensive analysis.
"""

import base64
import json
import logging
import re
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import numpy as np

from ollama import Client

# Import configurations
from model_config import (
    AVAILABLE_MODELS, TEST_SCENARIOS, 
    ModelConfig, get_model_config
)

# Import GPU management
from gpu_manager import SimpleGPUManager, test_models_sequentially

# Import existing utilities
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from generic_coordinate_enhancement import (
    read_droidbot_state_direct,
    extract_ui_elements, 
    create_enhanced_description
)

@dataclass
class TestResult:
    """Result of a single test execution."""
    model_name: str
    scenario: str
    apk_name: str
    sample_id: str
    
    # Input data
    elements_count: int
    ui_elements_available: bool
    
    # Generated response
    response_text: str
    response_time: float
    
    # Coordinate analysis
    generated_coords: Optional[Tuple[int, int]]
    expected_coords: Optional[Tuple[int, int]]
    distance: Optional[float]
    hit: Optional[bool]
    
    # Element information
    chosen_element: Optional[Dict[str, Any]]
    
    # Success metrics
    parsing_success: bool
    coordinate_success: bool
    overall_success: bool
    
    # Error information
    error: Optional[str]

@dataclass 
class ModelPerformance:
    """Performance summary for a model."""
    model_name: str
    total_tests: int
    successful_tests: int
    parsing_success_rate: float
    coordinate_success_rate: float
    overall_success_rate: float
    avg_distance: float
    avg_response_time: float
    hit_rate: float
    
    # By scenario
    scenario_performance: Dict[str, Dict[str, float]]
    
    # By app type
    app_type_performance: Dict[str, Dict[str, float]]


class VisionModelBenchmark:
    """Main benchmark framework for vision models."""
    
    def __init__(self, ollama_host: str = "http://localhost:11434"):
        self.client = Client(host=ollama_host)
        self.logger = self._setup_logging()
        self.results: List[TestResult] = []
        
        # Initialize GPU management
        self.gpu_manager = SimpleGPUManager(wait_time=20)
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for benchmark execution."""
        logger = logging.getLogger("VisionModelBenchmark")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def test_single_model(
        self, 
        model_name: str, 
        scenario: str,
        test_samples: List[Tuple[str, str]],  # (state_file, screenshot_file)
        max_samples: int = 5
    ) -> List[TestResult]:
        """Test a single model on a specific scenario."""
        
        model_config = get_model_config(model_name)
        if not model_config:
            self.logger.error(f"Model {model_name} not configured")
            return []
        
        scenario_config = TEST_SCENARIOS.get(scenario)
        if not scenario_config:
            self.logger.error(f"Scenario {scenario} not configured") 
            return []
        
        self.logger.info(f"Testing {model_name} on {scenario} scenario")
        
        # Select test samples
        selected_samples = test_samples[:max_samples]
        results = []
        
        for i, (state_file, screenshot_file) in enumerate(selected_samples, 1):
            self.logger.info(f"  Sample {i}/{len(selected_samples)}: {Path(state_file).stem}")
            
            result = self._test_single_sample(
                model_config=model_config,
                scenario=scenario,
                state_file=state_file,
                screenshot_file=screenshot_file
            )
            
            if result:
                results.append(result)
                self.results.append(result)
            
            # Small delay between requests
            time.sleep(1)
        
        return results
    
    def _test_single_sample(
        self,
        model_config: ModelConfig,
        scenario: str, 
        state_file: str,
        screenshot_file: str
    ) -> Optional[TestResult]:
        """Test a single sample with a specific model and scenario."""
        
        start_time = time.time()
        
        # Initialize result
        result = TestResult(
            model_name=model_config.name,
            scenario=scenario,
            apk_name=Path(state_file).parent.name,
            sample_id=Path(state_file).stem,
            elements_count=0,
            ui_elements_available=False,
            response_text="",
            response_time=0.0,
            generated_coords=None,
            expected_coords=None,
            distance=None,
            hit=None,
            chosen_element=None,
            parsing_success=False,
            coordinate_success=False,
            overall_success=False,
            error=None
        )
        
        try:
            # Load and process state if needed
            ui_elements_desc = ""
            elements = []
            
            scenario_config = TEST_SCENARIOS[scenario]
            if scenario_config["uses_ui_elements"]:
                # Load state and create enhanced description
                state = read_droidbot_state_direct(state_file)
                if not state:
                    result.error = "Failed to load state file"
                    return result
                    
                elements = extract_ui_elements(state)
                if not elements:
                    result.error = "No interactive elements found"
                    return result
                
                ui_elements_desc = create_enhanced_description(elements)
                result.elements_count = len(elements)
                result.ui_elements_available = True
            
            # Load screenshot
            try:
                with open(screenshot_file, 'rb') as f:
                    image_b64 = base64.b64encode(f.read()).decode('utf-8')
            except Exception as e:
                result.error = f"Failed to load screenshot: {e}"
                return result
            
            # Create prompt based on scenario and model
            prompt = self._create_prompt(model_config, scenario, ui_elements_desc)
            
            # Execute model request
            messages = [
                {
                    "role": "system",
                    "content": "You are an expert Android app tester specializing in UI coordinate generation."
                },
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_b64]
                }
            ]
            
            try:
                response = self.client.chat(
                    model=model_config.name,
                    messages=messages,
                    options={
                        "temperature": model_config.temperature,
                        "num_predict": model_config.max_tokens
                    },
                    stream=False
                )
                
                result.response_text = response.message.content
                result.response_time = time.time() - start_time
                result.parsing_success = True
                
            except Exception as e:
                result.error = f"Model request failed: {e}"
                result.response_time = time.time() - start_time
                return result
            
            # Parse response and extract coordinates
            coords = self._extract_coordinates(result.response_text)
            result.generated_coords = coords
            
            if coords and elements:
                # Find best matching expected coordinate
                expected_coords = [elem['center'] for elem in elements]
                distances = [np.sqrt((coords[0] - exp[0])**2 + (coords[1] - exp[1])**2) 
                           for exp in expected_coords]
                
                min_distance = min(distances)
                best_idx = distances.index(min_distance)
                
                result.expected_coords = tuple(expected_coords[best_idx])
                result.distance = min_distance
                result.hit = min_distance < 50  # 50px threshold
                result.chosen_element = elements[best_idx]
                result.coordinate_success = True
                
            elif coords:
                # No elements to compare against (visual generation scenario)
                result.coordinate_success = True
            
            # Overall success assessment
            result.overall_success = (
                result.parsing_success and 
                result.coordinate_success and
                (result.hit is None or result.hit)  # Hit if applicable
            )
            
        except Exception as e:
            result.error = f"Test execution failed: {e}"
            result.response_time = time.time() - start_time
        
        return result
    
    def _create_prompt(self, model_config: ModelConfig, scenario: str, ui_elements: str = "") -> str:
        """Create scenario-specific prompt for a model."""
        
        # Get model-specific prompt template
        prompt_templates = model_config.specialized_prompts
        
        if scenario in prompt_templates:
            template = prompt_templates[scenario]
        else:
            # Fallback to generic template
            template = """
Analyze this Android application screenshot and provide coordinates for interaction.

{ui_elements}

Return JSON: {{"coordinates": [x, y], "element": "description"}}
"""
        
        # Format with UI elements if available
        return template.format(ui_elements=ui_elements)
    
    def _extract_coordinates(self, response_text: str) -> Optional[Tuple[int, int]]:
        """Extract coordinates from model response."""
        
        coord_patterns = [
            r'"coordinates":\s*\[(\d+),\s*(\d+)\]',
            r'\[(\d+),\s*(\d+)\]',
            r'(\d+),\s*(\d+)',
            r'x:\s*(\d+),\s*y:\s*(\d+)',
            r'\((\d+),\s*(\d+)\)',
            r'position.*?(\d+),\s*(\d+)',
        ]
        
        for pattern in coord_patterns:
            match = re.search(pattern, response_text)
            if match:
                try:
                    x, y = int(match.group(1)), int(match.group(2))
                    # Sanity check for Android screen bounds
                    if 0 <= x <= 1080 and 0 <= y <= 1920:
                        return (x, y)
                except ValueError:
                    continue
        
        return None
    
    def run_comprehensive_benchmark(
        self,
        models_to_test: Optional[List[str]] = None,
        scenarios_to_test: Optional[List[str]] = None,
        samples_per_scenario: int = 3
    ) -> Dict[str, ModelPerformance]:
        """Run comprehensive benchmark across models and scenarios."""
        
        if models_to_test is None:
            models_to_test = list(AVAILABLE_MODELS.keys())
        
        if scenarios_to_test is None:
            scenarios_to_test = list(TEST_SCENARIOS.keys())
        
        self.logger.info("Starting comprehensive vision model benchmark")
        self.logger.info(f"Models: {models_to_test}")
        self.logger.info(f"Scenarios: {scenarios_to_test}")
        
        # Find test samples
        test_samples = self._find_test_samples()
        if not test_samples:
            self.logger.error("No test samples found")
            return {}
        
        # Use sequential model testing with GPU management
        def test_model_scenarios(model_name: str):
            """Test a single model across all scenarios."""
            model_results = []
            
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"TESTING MODEL: {model_name}")
            self.logger.info(f"{'='*60}")
            
            for scenario in scenarios_to_test:
                try:
                    results = self.test_single_model(
                        model_name=model_name,
                        scenario=scenario,
                        test_samples=test_samples,
                        max_samples=samples_per_scenario
                    )
                    model_results.extend(results)
                except Exception as e:
                    self.logger.error(f"Failed testing {model_name} on {scenario}: {e}")
            
            return model_results
        
        # Run sequential testing with GPU management
        test_models_sequentially(
            models=models_to_test,
            test_function=test_model_scenarios,
            gpu_manager=self.gpu_manager
        )
        
        # Analyze results
        return self.analyze_results()
    
    def _find_test_samples(self) -> List[Tuple[str, str]]:
        """Find available test samples (state + screenshot pairs)."""
        
        screenshots_dir = Path("/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/tmp_img/screenshots")
        
        samples = []
        for app_dir in screenshots_dir.iterdir():
            if app_dir.is_dir():
                for png_file in app_dir.glob("*.png"):
                    state_file = app_dir / f"{png_file.stem}.state"
                    if state_file.exists():
                        samples.append((str(state_file), str(png_file)))
        
        return samples
    
    def analyze_results(self) -> Dict[str, ModelPerformance]:
        """Analyze benchmark results and create performance summaries."""
        
        if not self.results:
            return {}
        
        # Group results by model
        model_results = {}
        for result in self.results:
            if result.model_name not in model_results:
                model_results[result.model_name] = []
            model_results[result.model_name].append(result)
        
        # Calculate performance metrics for each model
        performances = {}
        
        for model_name, results in model_results.items():
            total_tests = len(results)
            successful_tests = sum(1 for r in results if r.overall_success)
            parsing_successes = sum(1 for r in results if r.parsing_success)
            coordinate_successes = sum(1 for r in results if r.coordinate_success)
            
            # Distance and hit metrics (only for successful coordinate extractions)
            successful_coords = [r for r in results if r.coordinate_success and r.distance is not None]
            avg_distance = np.mean([r.distance for r in successful_coords]) if successful_coords else 0
            hit_rate = np.mean([r.hit for r in successful_coords if r.hit is not None]) if successful_coords else 0
            
            # Response time
            avg_response_time = np.mean([r.response_time for r in results])
            
            # Performance by scenario
            scenario_perf = {}
            for scenario in set(r.scenario for r in results):
                scenario_results = [r for r in results if r.scenario == scenario]
                if scenario_results:
                    scenario_successful = sum(1 for r in scenario_results if r.overall_success)
                    scenario_coords = [r for r in scenario_results if r.coordinate_success and r.distance is not None]
                    scenario_perf[scenario] = {
                        "success_rate": scenario_successful / len(scenario_results),
                        "avg_distance": np.mean([r.distance for r in scenario_coords]) if scenario_coords else 0,
                        "hit_rate": np.mean([r.hit for r in scenario_coords if r.hit is not None]) if scenario_coords else 0
                    }
            
            # Performance by app type (simplified)
            app_perf = {}
            for apk_name in set(r.apk_name for r in results):
                app_results = [r for r in results if r.apk_name == apk_name]
                if app_results:
                    app_successful = sum(1 for r in app_results if r.overall_success)
                    app_coords = [r for r in app_results if r.coordinate_success and r.distance is not None]
                    app_perf[apk_name] = {
                        "success_rate": app_successful / len(app_results),
                        "avg_distance": np.mean([r.distance for r in app_coords]) if app_coords else 0
                    }
            
            performances[model_name] = ModelPerformance(
                model_name=model_name,
                total_tests=total_tests,
                successful_tests=successful_tests,
                parsing_success_rate=parsing_successes / total_tests if total_tests > 0 else 0,
                coordinate_success_rate=coordinate_successes / total_tests if total_tests > 0 else 0,
                overall_success_rate=successful_tests / total_tests if total_tests > 0 else 0,
                avg_distance=avg_distance,
                avg_response_time=avg_response_time,
                hit_rate=hit_rate,
                scenario_performance=scenario_perf,
                app_type_performance=app_perf
            )
        
        return performances
    
    def save_results(self, output_dir: str = "benchmark_results"):
        """Save benchmark results and analysis to files."""
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Save raw results
        raw_results = [asdict(result) for result in self.results]
        with open(output_path / "raw_results.json", 'w') as f:
            json.dump(raw_results, f, indent=2, default=str)
        
        # Save performance analysis
        performances = self.analyze_results()
        performance_data = {name: asdict(perf) for name, perf in performances.items()}
        
        with open(output_path / "performance_analysis.json", 'w') as f:
            json.dump(performance_data, f, indent=2, default=str)
        
        self.logger.info(f"Results saved to {output_path}")
        
        return performances