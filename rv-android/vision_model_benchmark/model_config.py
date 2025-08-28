#!/usr/bin/env python3
"""
Configuration file for vision model benchmarking.
Defines all available models and their specific configurations.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

@dataclass
class ModelConfig:
    """Configuration for a specific vision model."""
    name: str
    full_name: str
    family: str  # gemma, llama, llava, qwen, granite
    size: str    # 2b, 3b, 4b, 7b, 8b, 11b, 12b
    temperature: float = 0.1
    max_tokens: int = 300
    specialized_prompts: Dict[str, str] = field(default_factory=dict)
    known_limitations: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)

# Available models configuration
AVAILABLE_MODELS = {
    "gemma3:4b": ModelConfig(
        name="gemma3:4b",
        full_name="Google Gemma 3 4B",
        family="gemma",
        size="4b",
        temperature=0.1,
        max_tokens=300,
        specialized_prompts={
            "coordinate_validation": """
{ui_elements}

Task: You are testing an Android application. Look at the UI elements listed above and choose ONE interactive element to click on.

IMPORTANT: Use the EXACT coordinates provided in "at position (x, y)" format. Do not estimate coordinates.

Return JSON: {{"coordinates": [x, y], "element": "description", "action": "click"}}
""",
            "visual_generation": """
Analyze this Android application screenshot. Generate coordinates to click on an interactive element.

Return JSON: {{"coordinates": [x, y], "element": "description", "reasoning": "why"}}
""",
            "game_elements": """
This is a game application. Analyze the visual elements and provide coordinates for game interactions.

Look for: {target_element}

Return JSON: {{"coordinates": [x, y], "element": "game_element", "confidence": "high/medium/low"}}
"""
        },
        known_limitations=[
            "Strong center-bias without explicit coordinates",
            "Poor performance on non-DOM elements", 
            "Generates coordinates around (540, 960) frequently"
        ],
        strengths=[
            "Perfect accuracy with explicit coordinates",
            "Excellent visual element recognition",
            "Good at selecting from provided options"
        ]
    ),
    
    "gemma3:12b": ModelConfig(
        name="gemma3:12b",
        full_name="Google Gemma 3 12B", 
        family="gemma",
        size="12b",
        temperature=0.1,
        max_tokens=300,
        specialized_prompts={
            "coordinate_validation": """
{ui_elements}

Task: You are testing an Android application. Look at the UI elements listed above and choose ONE interactive element to click on.

IMPORTANT: Use the EXACT coordinates provided in "at position (x, y)" format. Do not estimate coordinates.

Return JSON: {{"coordinates": [x, y], "element": "description", "action": "click"}}
""",
            "visual_generation": """
Analyze this Android application screenshot. Generate precise coordinates to click on an interactive element.

Consider the screen size (1080x1920) and provide accurate pixel coordinates.

Return JSON: {{"coordinates": [x, y], "element": "description", "reasoning": "spatial analysis"}}
"""
        },
        strengths=[
            "Larger model - potentially better reasoning",
            "May have improved spatial understanding"
        ]
    ),
    
    "llama3.2-vision:11b": ModelConfig(
        name="llama3.2-vision:11b",
        full_name="Meta Llama 3.2 Vision 11B",
        family="llama",
        size="11b", 
        temperature=0.1,
        max_tokens=300,
        specialized_prompts={
            "coordinate_validation": """
{ui_elements}

You are an Android app tester. The UI elements above show exact coordinates for each interactive element.

Select ONE element and use its precise coordinates. Do not estimate - use the exact "at position (x, y)" values.

Response format: {{"coordinates": [x, y], "element": "chosen_element"}}
""",
            "visual_generation": """
Analyze this Android app screenshot (1080x1920 resolution). 

Identify clickable elements and provide precise pixel coordinates. Consider typical Android UI patterns.

Response: {{"coordinates": [x, y], "element": "identified_element", "confidence_score": 0.X}}
"""
        },
        strengths=[
            "Meta's vision model - different training approach",
            "Potentially better spatial reasoning",
            "Different tokenization strategy"
        ]
    ),
    
    "llava-llama3:8b": ModelConfig(
        name="llava-llama3:8b",
        full_name="LLaVA Llama 3 8B",
        family="llava",
        size="8b",
        temperature=0.2,  # Slightly higher for LLaVA
        max_tokens=350,
        specialized_prompts={
            "coordinate_validation": """
{ui_elements}

I'm showing you UI elements from an Android app with their exact coordinates.

Please choose one element and return its exact coordinates. Use the "at position (x, y)" coordinates exactly as shown.

Format: {{"coordinates": [x, y], "element": "selected_element"}}
""",
            "visual_generation": """
Look at this Android app interface. I need you to identify a clickable element and give me pixel coordinates to click it.

The screen is 1080x1920 pixels. Provide coordinates as [x, y] where (0,0) is top-left.

{{"coordinates": [x, y], "element": "what_you_see", "explanation": "why_clickable"}}
""",
            "detailed_analysis": """
Provide a detailed analysis of this Android interface:

1. What type of app is this?
2. What are the main interactive elements?
3. Choose the most important element and provide coordinates.
4. Explain your spatial reasoning.

Response: {{"app_type": "...", "elements": [...], "chosen_coords": [x, y], "reasoning": "..."}}
"""
        },
        strengths=[
            "LLaVA architecture - specialized for vision",
            "Strong image understanding capabilities",
            "Good at detailed visual analysis"
        ]
    ),
    
    "qwen2.5vl:3b": ModelConfig(
        name="qwen2.5vl:3b",
        full_name="Qwen 2.5 Vision Language 3B",
        family="qwen", 
        size="3b",
        temperature=0.1,
        max_tokens=300,
        specialized_prompts={
            "coordinate_validation": """
{ui_elements}

这是一个Android应用的UI元素列表，包含精确坐标。

请选择一个交互元素并使用其确切的"at position (x, y)"坐标。

返回: {{"coordinates": [x, y], "element": "selected_element"}}
""",
            "visual_generation": """
分析这个Android应用截图 (1080x1920像素)。

识别可点击元素并提供精确的像素坐标。

返回: {{"coordinates": [x, y], "element": "识别的元素", "confidence": "置信度"}}
""",
            "english_prompt": """
{ui_elements}

You are testing an Android application. Select one UI element and use its exact coordinates.

Return: {{"coordinates": [x, y], "element": "chosen_element"}}
"""
        },
        strengths=[
            "Chinese model - different training data",
            "Compact but efficient",
            "May have different spatial reasoning patterns"
        ]
    ),
    
    "qwen2.5vl:7b": ModelConfig(
        name="qwen2.5vl:7b", 
        full_name="Qwen 2.5 Vision Language 7B",
        family="qwen",
        size="7b",
        temperature=0.1,
        max_tokens=300,
        specialized_prompts={
            "coordinate_validation": """
{ui_elements}

You are testing an Android application. The UI elements above contain exact coordinates.

Select ONE element and return its precise "at position (x, y)" coordinates.

JSON response: {{"coordinates": [x, y], "element": "selected_element"}}
""",
            "visual_generation": """
Analyze this Android app screenshot. The screen resolution is 1080x1920 pixels.

Find clickable UI elements and provide accurate pixel coordinates.

Response: {{"coordinates": [x, y], "element": "found_element", "analysis": "visual reasoning"}}
"""
        },
        strengths=[
            "Larger Qwen model",
            "Improved reasoning capabilities", 
            "Better multilingual understanding"
        ]
    ),
    
    "granite3.2-vision:2b": ModelConfig(
        name="granite3.2-vision:2b",
        full_name="IBM Granite 3.2 Vision 2B",
        family="granite",
        size="2b",
        temperature=0.15,
        max_tokens=280,
        specialized_prompts={
            "coordinate_validation": """
{ui_elements}

Android UI Testing Task:
- Above are UI elements with exact coordinates
- Choose one element for interaction 
- Use the precise "at position (x, y)" coordinates

Output: {{"coordinates": [x, y], "element": "chosen_element"}}
""",
            "visual_generation": """
Visual Analysis Task: Android App Screenshot

Screen: 1080x1920 pixels
Goal: Locate interactive element and provide click coordinates

Analysis: {{"coordinates": [x, y], "element": "detected_element", "rationale": "decision_process"}}
""",
            "business_context": """
You are a QA engineer testing an Android application for enterprise deployment.

Analyze the interface professionally and identify the most critical element to test first.

Report: {{"coordinates": [x, y], "element": "business_critical_element", "test_priority": "high/medium/low"}}
"""
        },
        strengths=[
            "IBM enterprise-focused model",
            "Compact and efficient",
            "Business-oriented reasoning"
        ]
    )
}

def get_model_config(model_name: str) -> Optional[ModelConfig]:
    """Get configuration for a specific model."""
    return AVAILABLE_MODELS.get(model_name)

def get_models_by_family(family: str) -> List[ModelConfig]:
    """Get all models from a specific family."""
    return [config for config in AVAILABLE_MODELS.values() if config.family == family]

def get_models_by_size() -> Dict[str, List[ModelConfig]]:
    """Group models by size."""
    size_groups = {}
    for config in AVAILABLE_MODELS.values():
        if config.size not in size_groups:
            size_groups[config.size] = []
        size_groups[config.size].append(config)
    return size_groups

def list_available_models() -> List[str]:
    """List all available model names."""
    return list(AVAILABLE_MODELS.keys())

# Test configurations for different scenarios
TEST_SCENARIOS = {
    "coordinate_validation": {
        "name": "Coordinate Validation",
        "description": "Test accuracy when explicit coordinates are provided",
        "uses_ui_elements": True,
        "success_criteria": {
            "hit_rate": 0.8,  # 80% minimum
            "avg_distance": 50.0  # 50px maximum
        }
    },
    
    "visual_generation": {
        "name": "Visual Coordinate Generation", 
        "description": "Test ability to generate coordinates from visual analysis only",
        "uses_ui_elements": False,
        "success_criteria": {
            "hit_rate": 0.3,  # 30% minimum (challenging)
            "avg_distance": 200.0  # 200px maximum
        }
    },
    
    "game_elements": {
        "name": "Game Elements",
        "description": "Test performance on non-DOM game elements",
        "uses_ui_elements": False,
        "success_criteria": {
            "hit_rate": 0.2,  # 20% minimum (very challenging)
            "avg_distance": 300.0  # 300px maximum
        }
    },
    
    "mixed_scenario": {
        "name": "Mixed DOM/Visual",
        "description": "Test hybrid scenarios with both DOM and visual elements",
        "uses_ui_elements": True,
        "success_criteria": {
            "hit_rate": 0.6,  # 60% minimum
            "avg_distance": 100.0  # 100px maximum
        }
    }
}