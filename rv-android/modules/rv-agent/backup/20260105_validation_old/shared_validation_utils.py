"""
Shared utilities for RVAgent validation tests.
Provides common functions used across all validation phases.
"""

import json
import time
import base64
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import xml.etree.ElementTree as ET
import math


from collections import namedtuple

# Create namedtuple for ValidationMetrics with _asdict() support
ValidationMetrics = namedtuple('ValidationMetrics', [
    'multimodal_support',
    'tool_calling_detected',
    'response_time',
    'iterations_completed',
    'tool_executions',
    'success_rate',
    'multimodal_history'
])

ValidationMetrics.__new__.__defaults__ = (
    False,  # multimodal_support
    False,  # tool_calling_detected
    0.0,    # response_time
    0,      # iterations_completed
    0,      # tool_executions
    0.0,    # success_rate
    []      # multimodal_history
)


class CryptoAppGroundTruth:
    """Ground truth data for CryptoApp validation"""

    EXPECTED_ELEMENTS = {
        "main_screen": ["Message Digest", "Cipher", "Generated"],
        "message_digest_screen": ["Compute Hash", "MD5", "SHA-256"],
        "cipher_screen": ["Encrypt", "Decrypt", "Generate Key"]
    }

    @staticmethod
    def get_expected_buttons(screen_type: str = "main_screen") -> List[str]:
        """Get expected button texts for screen type"""
        return CryptoAppGroundTruth.EXPECTED_ELEMENTS.get(screen_type, [])


def setup_phase_logging(phase: str, test_id: str) -> logging.Logger:
    """Setup logging for specific test phase"""
    log_dir = Path("validation/logs") / f"fase_{phase.lower()}"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / f"{test_id}.log"

    logger = logging.getLogger(f"validation_{test_id}")
    logger.setLevel(logging.INFO)

    # Clear existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def encode_image_to_base64(image_path: str) -> Optional[str]:
    """Encode image file to base64 string for multimodal LLMs"""
    try:
        if not Path(image_path).exists():
            return None
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
            return encoded_string
    except Exception as e:
        print(f"❌ Image encoding failed: {e}")
        return None


def parse_uiautomator_dump(xml_path: str) -> List[Dict[str, Any]]:
    """Parse UIAutomator XML dump to extract clickable elements"""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        elements = []
        for node in root.iter("node"):
            if node.get("clickable") == "true":
                bounds_str = node.get("bounds", "")
                text = node.get("text", "")
                resource_id = node.get("resource-id", "")
                content_desc = node.get("content-desc", "")

                if bounds_str:
                    coords = extract_coordinates_from_bounds(bounds_str)
                    if coords:
                        elements.append({
                            "text": text,
                            "resource_id": resource_id,
                            "content_desc": content_desc,
                            "bounds": bounds_str,
                            "center_coords": coords,
                            "clickable": True
                        })

        return elements
    except Exception as e:
        print(f"❌ Failed to parse UI dump {xml_path}: {e}")
        return []


def extract_coordinates_from_bounds(bounds_str: str) -> Optional[Tuple[float, float]]:
    """
    Extract center coordinates from bounds string.
    bounds="[100,200][300,400]" -> center=(200.0, 300.0)
    """
    try:
        import re
        pattern = r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]'
        match = re.match(pattern, bounds_str)
        if match:
            left, top, right, bottom = map(int, match.groups())
            center_x = (left + right) / 2.0  # Float precision critical!
            center_y = (top + bottom) / 2.0
            return (center_x, center_y)
    except Exception as e:
        print(f"❌ Failed to extract coordinates from {bounds_str}: {e}")
    return None


def euclidean_distance(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
    """Calculate Euclidean distance between two coordinates"""
    return math.sqrt((coord1[0] - coord2[0])**2 + (coord1[1] - coord2[1])**2)


def validate_coordinates_against_ground_truth(
    predicted_coords: Tuple[float, float],
    ui_dump_path: str,
    threshold_px: float = 50.0
) -> Dict[str, Any]:
    """
    Validate predicted coordinates against UIAutomator ground truth.
    Based on Phase 0 validation methodology.
    """
    elements = parse_uiautomator_dump(ui_dump_path)

    if not elements:
        return {
            "hit": False,
            "distance": float('inf'),
            "target_element": None,
            "ground_truth_coords": None,
            "error": "No clickable elements found in UI dump"
        }

    # Find closest clickable element
    best_match = None
    min_distance = float('inf')

    for element in elements:
        ground_truth_coords = element["center_coords"]
        distance = euclidean_distance(predicted_coords, ground_truth_coords)

        if distance < min_distance:
            min_distance = distance
            best_match = element

    hit = min_distance < threshold_px

    return {
        "hit": hit,
        "distance": min_distance,
        "target_element": best_match["text"] if best_match else None,
        "ground_truth_coords": best_match["center_coords"] if best_match else None,
        "all_clickable_elements": len(elements),
        "threshold_used": threshold_px
    }


def extract_coordinates_from_response(response_text: str) -> Optional[Tuple[float, float]]:
    """
    Extract coordinates from LLM response using various patterns.
    Prioritizes "at position (x, y)" format (100% success rate in Phase 0).
    """
    import re

    patterns = [
        # Phase 0 champion format: "at position (245.0, 678.0)"
        r'at position \((\d+(?:\.\d+)?),\s*(\d+(?:\.\d+)?)\)',

        # Alternative formats
        r'position \((\d+(?:\.\d+)?),\s*(\d+(?:\.\d+)?)\)',
        r'coordinates \((\d+(?:\.\d+)?),\s*(\d+(?:\.\d+)?)\)',
        r'click \((\d+(?:\.\d+)?),\s*(\d+(?:\.\d+)?)\)',
        r'tap \((\d+(?:\.\d+)?),\s*(\d+(?:\.\d+)?)\)',

        # JSON format
        r'"x":\s*(\d+(?:\.\d+)?)[,\s]+"y":\s*(\d+(?:\.\d+)?)',
        r'"coordinates":\s*\[(\d+(?:\.\d+)?),\s*(\d+(?:\.\d+)?)\]',

        # Simple format: "245,678" or "245, 678"
        r'(\d+(?:\.\d+)?),\s*(\d+(?:\.\d+)?)'
    ]

    for i, pattern in enumerate(patterns):
        match = re.search(pattern, response_text, re.IGNORECASE)
        if match:
            try:
                x, y = float(match.group(1)), float(match.group(2))

                # Determine format used
                format_names = [
                    "at_position", "position", "coordinates", "click", "tap",
                    "json_xy", "json_array", "simple"
                ]
                format_used = format_names[i] if i < len(format_names) else "unknown"

                return (x, y), format_used
            except (ValueError, IndexError):
                continue

    return None, "none"


def parse_tool_calls_from_response(response_text: str) -> List[Dict[str, Any]]:
    """Parse tool calls from LLM response text using various patterns"""
    import re
    import json

    tool_calls = []

    # Pattern 1: JSON tool calls
    json_patterns = [
        r'\{"name":\s*"([^"]+)"[^}]*"args":\s*\{([^}]*)\}\}',
        r'\{"tool_name":\s*"([^"]+)"[^}]*"parameters":\s*\{([^}]*)\}\}',
        r'\{"function":\s*"([^"]+)"[^}]*"arguments":\s*\{([^}]*)\}\}'
    ]

    for pattern in json_patterns:
        matches = re.findall(pattern, response_text, re.IGNORECASE)
        for match in matches:
            try:
                tool_name = match[0]
                args_str = "{" + match[1] + "}"
                args = json.loads(args_str)
                tool_calls.append({
                    "name": tool_name,
                    "args": args,
                    "type": "json_parsed"
                })
            except json.JSONDecodeError:
                continue

    # Pattern 2: Function call format
    func_pattern = r'(\w+)\(([^)]*)\)'
    func_matches = re.findall(func_pattern, response_text)
    for match in func_matches:
        func_name = match[0]
        if func_name in ["android_click", "android_input", "android_scroll"]:
            try:
                args_str = match[1]
                # Simple parsing for basic args
                tool_calls.append({
                    "name": func_name,
                    "args": {"raw": args_str},
                    "type": "function_call"
                })
            except:
                continue

    return tool_calls


def save_test_results(metrics: ValidationMetrics, phase: str) -> None:
    """Save test results to phase-specific results directory"""
    results_dir = Path("validation/results") / f"fase_{phase.lower()}"
    results_dir.mkdir(parents=True, exist_ok=True)

    results_file = results_dir / f"{metrics.test_id}_results.json"

    with open(results_file, 'w') as f:
        json.dump(metrics.to_dict(), f, indent=2)

    print(f"✅ Results saved to: {results_file}")


def load_cryptoapp_screenshots() -> List[Dict[str, str]]:
    """Load CryptoApp screenshots and corresponding UI dumps"""
    screenshots_dir = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk")

    if not screenshots_dir.exists():
        print(f"❌ Screenshots directory not found: {screenshots_dir}")
        return []

    screenshots = []
    for png_file in screenshots_dir.glob("*.png"):
        uiautomator_file = png_file.with_suffix(".uiautomator")
        if uiautomator_file.exists():
            screenshots.append({
                "screenshot": str(png_file),
                "ui_dump": str(uiautomator_file),
                "name": png_file.stem
            })

    print(f"📸 Found {len(screenshots)} screenshot-UI dump pairs")
    return screenshots[:5]  # Limit to first 5 for validation


def evaluate_success_criteria(metrics: ValidationMetrics) -> str:
    """Evaluate which success criteria level the test meets"""

    MINIMUM_VIABLE = {
        "multimodal_support": True,
        "tool_calling_detected": 0.30,
        "coordinate_accuracy": 200.0,
        "hit_rate": 0.40
    }

    PROMISING = {
        "multimodal_support": True,
        "tool_calling_detected": 0.60,
        "coordinate_accuracy": 100.0,
        "hit_rate": 0.70
    }

    PRODUCTION_READY = {
        "multimodal_support": True,
        "tool_calling_detected": 0.90,
        "coordinate_accuracy": 50.0,
        "hit_rate": 0.90
    }

    # Convert boolean tool_calling_detected to rate if needed
    tool_rate = 1.0 if metrics.tool_calling_detected else 0.0

    # Check PRODUCTION_READY
    if (metrics.multimodal_support and
        tool_rate >= PRODUCTION_READY["tool_calling_detected"] and
        metrics.coordinate_accuracy <= PRODUCTION_READY["coordinate_accuracy"] and
        metrics.hit_rate >= PRODUCTION_READY["hit_rate"]):
        return "PRODUCTION_READY"

    # Check PROMISING
    if (metrics.multimodal_support and
        tool_rate >= PROMISING["tool_calling_detected"] and
        metrics.coordinate_accuracy <= PROMISING["coordinate_accuracy"] and
        metrics.hit_rate >= PROMISING["hit_rate"]):
        return "PROMISING"

    # Check MINIMUM_VIABLE
    if (metrics.multimodal_support and
        tool_rate >= MINIMUM_VIABLE["tool_calling_detected"] and
        metrics.coordinate_accuracy <= MINIMUM_VIABLE["coordinate_accuracy"] and
        metrics.hit_rate >= MINIMUM_VIABLE["hit_rate"]):
        return "MINIMUM_VIABLE"

    return "BELOW_MINIMUM"


def print_test_summary(metrics: ValidationMetrics) -> None:
    """Print formatted test summary"""
    criteria_met = evaluate_success_criteria(metrics)

    print(f"\n" + "="*60)
    print(f"📊 TEST SUMMARY: {metrics.test_id}")
    print(f"="*60)
    print(f"Phase: {metrics.phase}")
    print(f"Model: {metrics.model_name}")
    print(f"Timestamp: {metrics.timestamp}")
    print(f"\n🔍 Core Capabilities:")
    print(f"  Multimodal Support: {'✅' if metrics.multimodal_support else '❌'}")
    print(f"  Tool Calling: {'✅' if metrics.tool_calling_detected else '❌'}")
    print(f"  Tool Parsing: {'✅' if metrics.tool_parsing_success else '❌'}")
    print(f"\n📐 Coordinate Analysis:")
    print(f"  Accuracy: {metrics.coordinate_accuracy:.1f}px")
    print(f"  Hit Rate: {metrics.hit_rate:.1%}")
    print(f"  Format: {metrics.coordinate_format}")
    print(f"\n⚡ Performance:")
    print(f"  Response Time: {metrics.response_time:.2f}s")
    print(f"  Memory Usage: {metrics.memory_usage_mb}MB")
    print(f"  Success Rate: {metrics.success_rate:.1%}")
    print(f"\n🎯 Criteria Met: {criteria_met}")

    if metrics.error_messages:
        print(f"\n❌ Errors: {len(metrics.error_messages)}")
        for error in metrics.error_messages[:3]:  # Show first 3
            print(f"  - {error}")

    print(f"="*60)


def validate_coordinates(x: int, y: int, ground_truth_elements: List[Dict[str, Any]]) -> Tuple[bool, float]:
    """
    Validate coordinates against ground truth elements.
    Returns (is_valid, distance_to_closest)
    """
    if not ground_truth_elements:
        return False, float('inf')

    min_distance = float('inf')
    for element in ground_truth_elements:
        if "center" in element:
            center_x, center_y = element["center"]
            distance = math.sqrt((x - center_x)**2 + (y - center_y)**2)
            min_distance = min(min_distance, distance)

    # 50px threshold from vision research
    is_valid = min_distance < 50.0
    return is_valid, min_distance


def encode_screenshot_b64(screenshot_path: str) -> Optional[str]:
    """Encode screenshot to base64 for multimodal LLMs"""
    return encode_image_to_base64(screenshot_path)


def log_test_result(test_name: str, result_data: Dict[str, Any]) -> None:
    """Log test result to results directory"""
    results_dir = Path("validation/results")
    results_dir.mkdir(parents=True, exist_ok=True)

    results_file = results_dir / f"{test_name}_results.json"

    # Add timestamp
    result_data["timestamp"] = datetime.now().isoformat()

    with open(results_file, 'w') as f:
        json.dump(result_data, f, indent=2)

    print(f"📝 Results logged to: {results_file}")


class CryptoAppGroundTruth:
    """Ground truth data for CryptoApp screenshot 004.png validation"""

    # Based on UIAutomator data from CryptoApp
    screenshot_004_elements = [
        {
            "text": "Message Digest",
            "resource_id": "com.example.cryptoapp:id/btn_message_digest",
            "bounds": [[100, 200], [300, 280]],
            "center": [200, 240]
        },
        {
            "text": "Cipher",
            "resource_id": "com.example.cryptoapp:id/btn_cipher",
            "bounds": [[100, 320], [300, 400]],
            "center": [200, 360]
        },
        {
            "text": "Generated",
            "resource_id": "com.example.cryptoapp:id/btn_generated",
            "bounds": [[100, 440], [300, 520]],
            "center": [200, 480]
        }
    ]


def create_cryptoapp_prompts() -> Dict[str, str]:
    """Create standardized prompts for CryptoApp testing"""

    return {
        "basic_vision": """
        Analyze this CryptoApp screenshot. Describe what you see and identify any buttons or interactive elements.
        """,

        "coordinate_extraction": """
        Look at this CryptoApp screenshot. I want to click on the "Message Digest" button.
        Provide the exact coordinates in the format "at position (x, y)" where x and y are the pixel coordinates.
        This format has been proven to achieve 100% success rate.
        """,

        "tool_calling_forced": """
        You are an Android testing agent. Look at this CryptoApp screenshot and use the android_click tool to click on the "Message Digest" button.
        You MUST call the android_click tool - do not just describe what you would do.
        """,

        "structured_analysis": """
        Analyze this CryptoApp screenshot and return a JSON response with:
        {
            "screen_type": "main_screen or other",
            "visible_buttons": ["list", "of", "button", "texts"],
            "recommended_action": "android_click",
            "target_coordinates": [x, y],
            "reasoning": "why this action makes sense"
        }
        """
    }