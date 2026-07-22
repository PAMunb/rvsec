#!/usr/bin/env python3
"""
RVAgent Test 001: HuggingFace Robust Validation
Validação científica robusta baseada nos planos vision (docs/planos/vision/)

Estratégia:
1. Validação INICIAL pequena (2 screenshots, 6 modelos, 48 testes)
2. Execução por modelo (carregar → testar tudo → limpar memória)
3. Ground truth programático vs UI dumps
4. Prompt tuning sistemático
5. Métricas rigorosas baseadas em vision/002_vision.md

Objetivo: Decidir se HuggingFace é viável para RVAgent tools
"""

import json
import time
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import torch
from PIL import Image

# Configuration based on vision plans - DATASET REDUZIDO
CRYPTOAPP_SCREENSHOTS = [
    "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk/001.png"
]

CRYPTOAPP_UI_DUMPS = [
    "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk/001.uiautomator"
]

RESULTS_DIR = Path("validation_results")
RESULTS_DIR.mkdir(exist_ok=True)

@dataclass
class UIElement:
    """UI element from uiautomator dump"""
    text: str
    resource_id: str
    bounds: List[List[int]]
    clickable: bool
    class_name: str

    @property
    def center(self) -> Tuple[int, int]:
        """Calculate center coordinates"""
        x = (self.bounds[0][0] + self.bounds[1][0]) // 2
        y = (self.bounds[0][1] + self.bounds[1][1]) // 2
        return (x, y)

@dataclass
class TestResult:
    """Single test result"""
    model_name: str
    platform: str  # "ollama" or "huggingface"
    scenario: str
    screenshot_id: str

    # Response analysis
    response_text: str
    parsing_success: bool
    generated_coords: Optional[Tuple[int, int]]
    tool_calling_attempted: bool
    tool_calling_success: bool

    # Ground truth validation
    hit: bool
    distance: float
    target_element: Optional[str]
    ground_truth_coords: Optional[Tuple[int, int]]

    # Performance
    response_time: float
    memory_usage: float

    # Quality scores
    ui_understanding_score: float
    coordinate_format_correct: bool

# Models to test (grouped by platform for memory management)
MODELS_TO_TEST = {
    "ollama": [
        "qwen2.5vl:7b",  # Champion from vision/002 (98.3% success)
    ],
    "huggingface": [
        "microsoft/Phi-4-multimodal-instruct", # New 2025 - teste primeiro
        "Qwen/Qwen2.5-VL-7B-Instruct"        # User priority
    ]
}

# Test scenarios (4 scenarios x 2 screenshots = 8 tests per model)
TEST_SCENARIOS = {
    "coordinate_validation": {
        "description": "Use explicit coordinates (vision/001: 100% vs 30%)",
        "prompt_template": """
        Analyze this CryptoApp screenshot. You see these clickable elements:
        {ui_elements_with_coords}

        Task: Choose ONE element and use EXACT coordinates from "at position (x, y)" format.
        This format achieved 100% success rate in validation.

        Return JSON: {{"coordinates": [x, y], "element": "description"}}
        """,
        "expected_success": 0.9,  # Based on vision/001
        "tool_forced": False
    },

    "visual_generation": {
        "description": "Pure visual analysis (more challenging)",
        "prompt_template": """
        Analyze this CryptoApp screenshot and identify the main buttons.
        Focus on: Message Digest, Cipher, Generated buttons.

        Generate coordinates for the most prominent button.
        Return JSON: {{"coordinates": [x, y], "element": "description"}}
        """,
        "expected_success": 0.7,  # More challenging
        "tool_forced": False
    },

    "tool_calling_forced": {
        "description": "Force tool usage (NEW - test tool calling)",
        "prompt_template": """
        You MUST use android_click() tool. Do not just describe, actually call the tool.

        Look at this CryptoApp screenshot and click on the "Message Digest" button.
        Call: android_click(coordinates="at position (x, y)", element_description="Message Digest")
        """,
        "expected_success": 0.5,  # New capability to test
        "tool_forced": True
    },

    "mixed_scenario": {
        "description": "Combine UI structure with visual analysis",
        "prompt_template": """
        Analyze this CryptoApp screenshot. Combine visual analysis with UI structure.

        Available elements: {ui_elements_summary}

        Choose the best element to interact with and provide coordinates.
        Return JSON: {{"coordinates": [x, y], "element": "description", "reasoning": "why"}}
        """,
        "expected_success": 0.6,
        "tool_forced": False
    }
}

def parse_uiautomator_dump(dump_file: Path) -> List[UIElement]:
    """Parse UIAutomator dump to extract UI elements (ground truth)"""
    if not dump_file.exists():
        print(f"⚠️ UI dump not found: {dump_file}")
        return []

    try:
        with open(dump_file, 'r') as f:
            xml_content = f.read()

        root = ET.fromstring(xml_content)
        elements = []

        for node in root.findall(".//node"):
            bounds_str = node.get('bounds', '')
            if bounds_str:
                # Parse bounds: "[x1,y1][x2,y2]" -> [[x1,y1], [x2,y2]]
                import re
                coords = re.findall(r'\[(\d+),(\d+)\]', bounds_str)
                if len(coords) == 2:
                    bounds = [[int(coords[0][0]), int(coords[0][1])],
                             [int(coords[1][0]), int(coords[1][1])]]

                    element = UIElement(
                        text=node.get('text', ''),
                        resource_id=node.get('resource-id', ''),
                        bounds=bounds,
                        clickable=node.get('clickable', 'false').lower() == 'true',
                        class_name=node.get('class', '')
                    )
                    elements.append(element)

        return elements

    except Exception as e:
        print(f"❌ Error parsing UI dump {dump_file}: {e}")
        return []

def validate_coordinates_against_ui_dump(predicted_coords: Tuple[int, int],
                                       ui_dump_file: Path) -> Dict:
    """
    Validate coordinates against ground truth UI dump
    Based on vision/003_validacao.md methodology
    """
    ui_elements = parse_uiautomator_dump(ui_dump_file)
    clickable_elements = [e for e in ui_elements if e.clickable]

    if not clickable_elements:
        return {
            "hit": False,
            "distance": 999,
            "target_element": None,
            "ground_truth_coords": None,
            "all_clickable_elements": 0
        }

    # Find closest clickable element (programmatic ground truth)
    best_match = None
    min_distance = float('inf')

    for element in clickable_elements:
        center = element.center
        distance = math.sqrt((predicted_coords[0] - center[0])**2 +
                           (predicted_coords[1] - center[1])**2)

        if distance < min_distance:
            min_distance = distance
            best_match = element

    # Success threshold: 50px (based on vision/002)
    hit = min_distance < 50

    return {
        "hit": hit,
        "distance": min_distance,
        "target_element": best_match.text if best_match else None,
        "ground_truth_coords": best_match.center if best_match else None,
        "all_clickable_elements": len(clickable_elements)
    }

def create_ui_elements_description(ui_elements: List[UIElement]) -> str:
    """Create enhanced description with coordinates (vision/001 approach)"""
    lines = []

    for element in ui_elements:
        if element.clickable and (element.text or element.resource_id):
            center = element.center
            description = element.text or element.resource_id.split('/')[-1]
            line = f"- {description} at position ({center[0]}, {center[1]}) - bounds{element.bounds}"
            lines.append(line)

    return "\n".join(lines)

def extract_coordinates_from_response(response_text: str) -> Optional[Tuple[int, int]]:
    """Extract coordinates from model response (multiple patterns)"""
    import re

    # Multiple coordinate patterns (from vision/002)
    patterns = [
        r'"coordinates":\s*\[(\d+),\s*(\d+)\]',  # JSON format
        r'\[(\d+),\s*(\d+)\]',                   # Array format
        r'(\d+),\s*(\d+)',                       # Simple format
        r'x:\s*(\d+),\s*y:\s*(\d+)',             # Key-value format
        r'\((\d+),\s*(\d+)\)',                   # Parentheses format
        r'position.*?(\d+),\s*(\d+)',            # Natural language
    ]

    for pattern in patterns:
        match = re.search(pattern, response_text)
        if match:
            x, y = int(match.group(1)), int(match.group(2))
            # Validate Android screen bounds
            if 0 <= x <= 1080 and 0 <= y <= 1920:
                return (x, y)

    return None

def check_tool_calling_in_response(response_text: str) -> Tuple[bool, bool]:
    """Check if response attempted and succeeded in tool calling"""
    attempted = any(keyword in response_text.lower() for keyword in [
        'android_click', 'click(', 'tool', 'function', 'call'
    ])

    # Tool calling success: contains proper function call format
    success = bool(re.search(r'android_click\s*\(.*coordinates.*\)', response_text, re.IGNORECASE))

    return attempted, success

def calculate_ui_understanding_score(response_text: str, ui_elements: List[UIElement]) -> float:
    """Score how well the model understood the UI (0-1)"""
    score = 0.0

    # Check for CryptoApp specific understanding
    cryptoapp_buttons = ['message digest', 'cipher', 'generated']
    found_buttons = sum(1 for button in cryptoapp_buttons
                       if button in response_text.lower())
    score += found_buttons / len(cryptoapp_buttons) * 0.4

    # Check for UI elements mentioned
    clickable_elements = [e for e in ui_elements if e.clickable and e.text]
    if clickable_elements:
        found_elements = sum(1 for element in clickable_elements
                           if element.text.lower() in response_text.lower())
        score += (found_elements / len(clickable_elements)) * 0.4

    # Check for coordinate format understanding
    if "at position" in response_text.lower():
        score += 0.2

    return min(score, 1.0)

def test_ollama_model(model_name: str, scenario: str, screenshot_path: Path,
                     ui_dump_path: Path) -> TestResult:
    """Test Ollama model (baseline comparison)"""
    try:
        from langchain_ollama import ChatOllama
        from langchain_core.messages import HumanMessage
        import base64

        print(f"  🔄 Testing Ollama {model_name} - {scenario}")

        # Load model
        start_time = time.time()
        llm = ChatOllama(
            model=model_name,
            temperature=0.25,  # Based on vision/002 optimal
            base_url="http://localhost:11434"
        )

        # Load UI elements for prompt
        ui_elements = parse_uiautomator_dump(ui_dump_path)

        # Prepare prompt based on scenario
        scenario_config = TEST_SCENARIOS[scenario]
        if "ui_elements_with_coords" in scenario_config["prompt_template"]:
            ui_description = create_ui_elements_description(ui_elements)
            prompt = scenario_config["prompt_template"].format(
                ui_elements_with_coords=ui_description
            )
        elif "ui_elements_summary" in scenario_config["prompt_template"]:
            ui_summary = f"{len([e for e in ui_elements if e.clickable])} clickable elements"
            prompt = scenario_config["prompt_template"].format(
                ui_elements_summary=ui_summary
            )
        else:
            prompt = scenario_config["prompt_template"]

        # Encode and send image
        with open(screenshot_path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode('utf-8')

        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_base64}"}}
            ]
        )

        # Generate response
        response = llm.invoke([message])
        response_time = time.time() - start_time
        response_text = response.content

        # Parse response
        generated_coords = extract_coordinates_from_response(response_text)
        parsing_success = generated_coords is not None

        # Tool calling analysis
        tool_attempted, tool_success = check_tool_calling_in_response(response_text)

        # Validate against ground truth
        validation_result = {"hit": False, "distance": 999, "target_element": None,
                           "ground_truth_coords": None, "all_clickable_elements": 0}
        if generated_coords:
            validation_result = validate_coordinates_against_ui_dump(generated_coords, ui_dump_path)

        # Calculate scores
        ui_score = calculate_ui_understanding_score(response_text, ui_elements)
        coordinate_format_correct = "at position" in response_text.lower()

        return TestResult(
            model_name=model_name,
            platform="ollama",
            scenario=scenario,
            screenshot_id=screenshot_path.stem,
            response_text=response_text[:500],  # Truncate for storage
            parsing_success=parsing_success,
            generated_coords=generated_coords,
            tool_calling_attempted=tool_attempted,
            tool_calling_success=tool_success,
            hit=validation_result["hit"],
            distance=validation_result["distance"],
            target_element=validation_result["target_element"],
            ground_truth_coords=validation_result["ground_truth_coords"],
            response_time=response_time,
            memory_usage=0.0,  # Ollama manages memory
            ui_understanding_score=ui_score,
            coordinate_format_correct=coordinate_format_correct
        )

    except Exception as e:
        print(f"  ❌ Ollama test failed: {e}")
        return TestResult(
            model_name=model_name, platform="ollama", scenario=scenario,
            screenshot_id=screenshot_path.stem, response_text=f"ERROR: {e}",
            parsing_success=False, generated_coords=None, tool_calling_attempted=False,
            tool_calling_success=False, hit=False, distance=999, target_element=None,
            ground_truth_coords=None, response_time=0, memory_usage=0,
            ui_understanding_score=0, coordinate_format_correct=False
        )

def test_huggingface_model(model_name: str, scenario: str, screenshot_path: Path,
                          ui_dump_path: Path) -> TestResult:
    """Test HuggingFace model with quantization"""
    try:
        from transformers import (AutoProcessor, LlavaForConditionalGeneration,
                                BitsAndBytesConfig, Qwen2VLForConditionalGeneration,
                                AutoModelForCausalLM)

        print(f"  🔄 Testing HuggingFace {model_name} - {scenario}")

        start_time = time.time()

        # Quantization config for GPU memory management
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_quant_type="nf4"
        )

        # Load model based on type
        if "llava" in model_name.lower():
            processor = AutoProcessor.from_pretrained(model_name)
            model = LlavaForConditionalGeneration.from_pretrained(
                model_name,
                quantization_config=quantization_config,
                device_map="auto",
                torch_dtype=torch.bfloat16
            )
        elif "qwen" in model_name.lower():
            processor = AutoProcessor.from_pretrained(model_name)
            model = Qwen2VLForConditionalGeneration.from_pretrained(
                model_name,
                quantization_config=quantization_config,
                device_map="auto",
                torch_dtype=torch.bfloat16
            )
        else:
            # Generic approach for other models
            processor = AutoProcessor.from_pretrained(model_name)
            model = AutoModelForCausalLM.from_pretrained(
                model_name,
                quantization_config=quantization_config,
                device_map="auto",
                torch_dtype=torch.bfloat16
            )

        # Load UI elements for prompt
        ui_elements = parse_uiautomator_dump(ui_dump_path)

        # Prepare prompt (HuggingFace format)
        scenario_config = TEST_SCENARIOS[scenario]
        if "ui_elements_with_coords" in scenario_config["prompt_template"]:
            ui_description = create_ui_elements_description(ui_elements)
            prompt_text = scenario_config["prompt_template"].format(
                ui_elements_with_coords=ui_description
            )
        elif "ui_elements_summary" in scenario_config["prompt_template"]:
            ui_summary = f"{len([e for e in ui_elements if e.clickable])} clickable elements"
            prompt_text = scenario_config["prompt_template"].format(
                ui_elements_summary=ui_summary
            )
        else:
            prompt_text = scenario_config["prompt_template"]

        # Format for specific model types
        if "llava" in model_name.lower():
            full_prompt = f"USER: <image>\n{prompt_text}\nASSISTANT:"
        else:
            full_prompt = prompt_text

        # Load and process image
        image = Image.open(screenshot_path)
        inputs = processor(full_prompt, image, return_tensors="pt")

        # Move to same device as model
        device = next(model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}

        # Generate response
        with torch.no_grad():
            output = model.generate(
                **inputs,
                max_new_tokens=300,
                temperature=0.25,
                do_sample=True
            )

        response_text = processor.decode(output[0], skip_special_tokens=True)

        # Extract assistant response (remove prompt)
        if "ASSISTANT:" in response_text:
            response_text = response_text.split("ASSISTANT:")[-1].strip()

        response_time = time.time() - start_time

        # Check VRAM usage
        memory_usage = 0
        if torch.cuda.is_available():
            memory_usage = torch.cuda.memory_allocated() / 1024**3

        # Parse response
        generated_coords = extract_coordinates_from_response(response_text)
        parsing_success = generated_coords is not None

        # Tool calling analysis
        tool_attempted, tool_success = check_tool_calling_in_response(response_text)

        # Validate against ground truth
        validation_result = {"hit": False, "distance": 999, "target_element": None,
                           "ground_truth_coords": None, "all_clickable_elements": 0}
        if generated_coords:
            validation_result = validate_coordinates_against_ui_dump(generated_coords, ui_dump_path)

        # Calculate scores
        ui_score = calculate_ui_understanding_score(response_text, ui_elements)
        coordinate_format_correct = "at position" in response_text.lower()

        # Cleanup memory
        del model, processor
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        return TestResult(
            model_name=model_name,
            platform="huggingface",
            scenario=scenario,
            screenshot_id=screenshot_path.stem,
            response_text=response_text[:500],
            parsing_success=parsing_success,
            generated_coords=generated_coords,
            tool_calling_attempted=tool_attempted,
            tool_calling_success=tool_success,
            hit=validation_result["hit"],
            distance=validation_result["distance"],
            target_element=validation_result["target_element"],
            ground_truth_coords=validation_result["ground_truth_coords"],
            response_time=response_time,
            memory_usage=memory_usage,
            ui_understanding_score=ui_score,
            coordinate_format_correct=coordinate_format_correct
        )

    except Exception as e:
        print(f"  ❌ HuggingFace test failed: {e}")
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return TestResult(
            model_name=model_name, platform="huggingface", scenario=scenario,
            screenshot_id=screenshot_path.stem, response_text=f"ERROR: {e}",
            parsing_success=False, generated_coords=None, tool_calling_attempted=False,
            tool_calling_success=False, hit=False, distance=999, target_element=None,
            ground_truth_coords=None, response_time=0, memory_usage=0,
            ui_understanding_score=0, coordinate_format_correct=False
        )

def run_model_tests(model_name: str, platform: str) -> List[TestResult]:
    """Run all tests for a single model (optimized memory usage)"""
    print(f"\n🔄 Testing {platform.upper()} model: {model_name}")
    print("=" * 60)

    results = []

    # Test all scenarios and screenshots for this model
    for scenario in TEST_SCENARIOS.keys():
        for i, (screenshot_path, ui_dump_path) in enumerate(zip(CRYPTOAPP_SCREENSHOTS, CRYPTOAPP_UI_DUMPS)):
            screenshot_file = Path(screenshot_path)
            ui_dump_file = Path(ui_dump_path)

            print(f"  📸 Screenshot {i+1}: {scenario}")

            if platform == "ollama":
                result = test_ollama_model(model_name, scenario, screenshot_file, ui_dump_file)
            else:  # huggingface
                result = test_huggingface_model(model_name, scenario, screenshot_file, ui_dump_file)

            results.append(result)

            # Brief summary
            status = "✅" if result.hit else "❌"
            print(f"    {status} Hit: {result.hit}, Distance: {result.distance:.1f}px, "
                  f"Tools: {result.tool_calling_attempted}, Time: {result.response_time:.1f}s")

    return results

def analyze_model_performance(model_name: str, results: List[TestResult]) -> Dict:
    """Analyze performance for a single model"""
    if not results:
        return {}

    # Calculate metrics
    total_tests = len(results)
    hits = sum(1 for r in results if r.hit)
    parsing_successes = sum(1 for r in results if r.parsing_success)
    tool_attempts = sum(1 for r in results if r.tool_calling_attempted)
    tool_successes = sum(1 for r in results if r.tool_calling_success)

    avg_distance = sum(r.distance for r in results if r.distance < 999) / max(1, hits)
    avg_response_time = sum(r.response_time for r in results) / total_tests
    avg_memory = sum(r.memory_usage for r in results) / total_tests
    avg_ui_understanding = sum(r.ui_understanding_score for r in results) / total_tests

    coordinate_format_correct = sum(1 for r in results if r.coordinate_format_correct)

    analysis = {
        "model_name": model_name,
        "platform": results[0].platform,
        "total_tests": total_tests,

        # Core metrics
        "hit_rate": hits / total_tests,
        "parsing_success_rate": parsing_successes / total_tests,
        "tool_calling_rate": tool_attempts / total_tests,
        "tool_success_rate": tool_successes / max(1, tool_attempts),

        # Quality metrics
        "avg_distance": avg_distance,
        "avg_response_time": avg_response_time,
        "avg_memory_usage": avg_memory,
        "ui_understanding_score": avg_ui_understanding,
        "coordinate_format_correct_rate": coordinate_format_correct / total_tests,

        # Performance by scenario
        "scenario_performance": {}
    }

    # Analyze by scenario
    for scenario in TEST_SCENARIOS.keys():
        scenario_results = [r for r in results if r.scenario == scenario]
        if scenario_results:
            scenario_hits = sum(1 for r in scenario_results if r.hit)
            analysis["scenario_performance"][scenario] = {
                "hit_rate": scenario_hits / len(scenario_results),
                "avg_distance": sum(r.distance for r in scenario_results if r.distance < 999) / max(1, scenario_hits),
                "tool_calling_rate": sum(1 for r in scenario_results if r.tool_calling_attempted) / len(scenario_results)
            }

    return analysis

def run_validation():
    """Main validation function - optimized by model execution"""
    print("🚀 RVAgent HuggingFace Robust Validation")
    print("=" * 70)
    print("📋 Plan: 6 models × 4 scenarios × 2 screenshots = 48 tests")
    print("🎯 Based on vision/002_vision.md scientific methodology")
    print("🏆 Goal: Determine if HuggingFace is viable for RVAgent tools")

    # Check prerequisites
    missing_files = []
    for screenshot_path in CRYPTOAPP_SCREENSHOTS:
        if not Path(screenshot_path).exists():
            missing_files.append(screenshot_path)

    for ui_dump_path in CRYPTOAPP_UI_DUMPS:
        if not Path(ui_dump_path).exists():
            missing_files.append(ui_dump_path)

    if missing_files:
        print(f"❌ Missing required files:")
        for file in missing_files:
            print(f"   - {file}")
        print("Please ensure CryptoApp screenshots and UI dumps are available")
        return

    all_results = []
    model_analyses = []

    # Test Ollama models first (baseline)
    print(f"\n{'='*70}")
    print("🔵 TESTING OLLAMA MODELS (Baseline)")
    print("="*70)

    for model_name in MODELS_TO_TEST["ollama"]:
        model_results = run_model_tests(model_name, "ollama")
        all_results.extend(model_results)

        analysis = analyze_model_performance(model_name, model_results)
        model_analyses.append(analysis)

        print(f"\n📊 {model_name} Analysis:")
        print(f"   Hit Rate: {analysis['hit_rate']:.1%}")
        print(f"   Tool Calling: {analysis['tool_calling_rate']:.1%}")
        print(f"   Avg Distance: {analysis['avg_distance']:.1f}px")

    # Test HuggingFace models
    print(f"\n{'='*70}")
    print("🟠 TESTING HUGGINGFACE MODELS")
    print("="*70)

    for model_name in MODELS_TO_TEST["huggingface"]:
        model_results = run_model_tests(model_name, "huggingface")
        all_results.extend(model_results)

        analysis = analyze_model_performance(model_name, model_results)
        model_analyses.append(analysis)

        print(f"\n📊 {model_name} Analysis:")
        print(f"   Hit Rate: {analysis['hit_rate']:.1%}")
        print(f"   Tool Calling: {analysis['tool_calling_rate']:.1%}")
        print(f"   Avg Distance: {analysis['avg_distance']:.1f}px")
        print(f"   Memory: {analysis['avg_memory_usage']:.1f}GB")

    # Comparative analysis
    generate_comparative_analysis(model_analyses, all_results)

def generate_comparative_analysis(model_analyses: List[Dict], all_results: List[TestResult]):
    """Generate final comparative analysis and recommendations"""
    print(f"\n{'='*70}")
    print("📊 COMPARATIVE ANALYSIS")
    print("="*70)

    # Sort by hit rate
    sorted_analyses = sorted(model_analyses, key=lambda x: x['hit_rate'], reverse=True)

    print(f"\n🏆 RANKING BY HIT RATE:")
    for i, analysis in enumerate(sorted_analyses, 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}º"
        print(f"  {emoji} {analysis['model_name']} ({analysis['platform']})")
        print(f"     Hit Rate: {analysis['hit_rate']:.1%}")
        print(f"     Tool Calling: {analysis['tool_calling_rate']:.1%}")
        print(f"     Avg Distance: {analysis['avg_distance']:.1f}px")
        print(f"     Response Time: {analysis['avg_response_time']:.1f}s")

    # Platform comparison
    ollama_analyses = [a for a in model_analyses if a['platform'] == 'ollama']
    hf_analyses = [a for a in model_analyses if a['platform'] == 'huggingface']

    if ollama_analyses and hf_analyses:
        ollama_avg = sum(a['hit_rate'] for a in ollama_analyses) / len(ollama_analyses)
        hf_avg = sum(a['hit_rate'] for a in hf_analyses) / len(hf_analyses)

        print(f"\n🆚 PLATFORM COMPARISON:")
        print(f"   Ollama Average: {ollama_avg:.1%}")
        print(f"   HuggingFace Average: {hf_avg:.1%}")

        winner = "HuggingFace" if hf_avg > ollama_avg else "Ollama"
        print(f"   Winner: {winner}")

    # Success criteria evaluation
    print(f"\n🎯 SUCCESS CRITERIA EVALUATION:")

    criteria = {
        "minimum_viable": {"hit_rate": 0.5, "tool_calling_rate": 0.25},
        "promising": {"hit_rate": 0.7, "tool_calling_rate": 0.5},
        "excellent": {"hit_rate": 0.9, "tool_calling_rate": 0.8}
    }

    for analysis in sorted_analyses:
        print(f"\n  📋 {analysis['model_name']}:")
        for level, thresholds in criteria.items():
            hit_ok = analysis['hit_rate'] >= thresholds['hit_rate']
            tool_ok = analysis['tool_calling_rate'] >= thresholds['tool_calling_rate']
            status = "✅" if hit_ok and tool_ok else "❌"
            print(f"     {status} {level}: Hit {analysis['hit_rate']:.1%} >= {thresholds['hit_rate']:.1%}, "
                  f"Tools {analysis['tool_calling_rate']:.1%} >= {thresholds['tool_calling_rate']:.1%}")

    # Final recommendation
    best_overall = sorted_analyses[0]
    best_hf = next((a for a in sorted_analyses if a['platform'] == 'huggingface'), None)

    print(f"\n🎯 FINAL RECOMMENDATION:")
    print(f"   Champion Overall: {best_overall['model_name']} ({best_overall['platform']})")
    if best_hf:
        print(f"   Best HuggingFace: {best_hf['model_name']}")
        print(f"   HF Viability: {'✅ VIABLE' if best_hf['hit_rate'] > 0.5 else '❌ NOT VIABLE'}")

    # Save results
    save_results(model_analyses, all_results)

def save_results(model_analyses: List[Dict], all_results: List[TestResult]):
    """Save detailed results to files"""

    # Summary results
    summary = {
        "validation_type": "initial_hf_robust_validation",
        "total_tests": len(all_results),
        "models_tested": len(model_analyses),
        "timestamp": time.time(),
        "model_rankings": sorted(model_analyses, key=lambda x: x['hit_rate'], reverse=True)
    }

    with open(RESULTS_DIR / "initial_validation_summary.json", 'w') as f:
        json.dump(summary, f, indent=2)

    # Detailed model results
    with open(RESULTS_DIR / "model_by_model_results.json", 'w') as f:
        json.dump(model_analyses, f, indent=2)

    # Raw test results
    raw_results = []
    for result in all_results:
        raw_results.append({
            "model_name": result.model_name,
            "platform": result.platform,
            "scenario": result.scenario,
            "screenshot_id": result.screenshot_id,
            "hit": result.hit,
            "distance": result.distance,
            "parsing_success": result.parsing_success,
            "tool_calling_attempted": result.tool_calling_attempted,
            "tool_calling_success": result.tool_calling_success,
            "response_time": result.response_time,
            "memory_usage": result.memory_usage,
            "ui_understanding_score": result.ui_understanding_score,
            "coordinate_format_correct": result.coordinate_format_correct,
            "response_sample": result.response_text[:200]
        })

    with open(RESULTS_DIR / "raw_test_results.json", 'w') as f:
        json.dump(raw_results, f, indent=2)

    print(f"\n✅ Results saved to {RESULTS_DIR}/")
    print(f"   📄 initial_validation_summary.json")
    print(f"   📄 model_by_model_results.json")
    print(f"   📄 raw_test_results.json")

if __name__ == "__main__":
    run_validation()