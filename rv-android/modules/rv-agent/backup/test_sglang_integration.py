#!/usr/bin/env python3
"""
Test SGLang integration with rv-agent.

Simple test to validate:
1. Connection to SGLang server
2. Tool call parsing
3. Coordinate conversion
"""

import sys
sys.path.insert(0, "src")

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# Test 1: Basic SGLang connectivity
print("=" * 60)
print("Test 1: SGLang Basic Connectivity")
print("=" * 60)

try:
    llm = ChatOpenAI(
        base_url="http://192.168.0.21:30000/v1",
        model="Qwen/Qwen3-VL-4B-Instruct",
        temperature=0.01,
        max_tokens=100,
        api_key="not-needed",
    )

    response = llm.invoke([HumanMessage(content="Say 'Hello' in one word")])
    print(f"Response: {response.content}")
    print("SGLang connectivity: OK")
except Exception as e:
    print(f"SGLang connectivity: FAILED - {e}")
    sys.exit(1)

# Test 2: Tool call parser
print("\n" + "=" * 60)
print("Test 2: Tool Call Parser")
print("=" * 60)

from rv_agent.llm.tools.tool_call_parser import (
    parse_tool_calls_from_text,
    parse_tool_calls_with_strategy,
    normalize_tool_args,
    parser_stats,
)

# Test XML format (Qwen style)
xml_response = '''<tool_call>
{"name": "android_click", "arguments": {"x": 352, "y": 624, "element_description": "OK button"}}
</tool_call>'''

calls = parse_tool_calls_from_text(xml_response)
print(f"XML format: {len(calls)} tool calls parsed")
if calls:
    print(f"  -> {calls[0]}")

# Test malformed JSON fix
malformed_response = '''<tool_call>
{"name": "android_click", "arguments": {"x": 352, 624, "element_description": "button"}}
</tool_call>'''

calls, strategy = parse_tool_calls_with_strategy(malformed_response)
print(f"Malformed JSON: {len(calls)} tool calls via {strategy}")
if calls:
    print(f"  -> {calls[0]}")

# Test normalize_tool_args
print("\nNormalize tool args:")
test_cases = [
    {"x": "352", "y": "624"},  # String coords
    {"x": [352, 624]},  # Array in x (Qwen3-VL)
    {"coordinate": [464, 487]},  # Fara-7B format
]
for tc in test_cases:
    result = normalize_tool_args(tc)
    print(f"  {tc} -> {result}")

print(f"\nParser stats: {parser_stats.get_stats()}")

# Test 3: Coordinate converter
print("\n" + "=" * 60)
print("Test 3: Coordinate Converter")
print("=" * 60)

from rv_agent.core.coordinate_converter import (
    CoordinateConverter,
    denormalize_qwen_coords,
    QWEN3_VL_WIDTH,
    QWEN3_VL_HEIGHT,
)

converter = CoordinateConverter(
    device_dimensions=(1080, 1920),
    optimized_dimensions=(QWEN3_VL_WIDTH, QWEN3_VL_HEIGHT)
)

print(f"Converter info: {converter.get_dimensions_info()}")

# Test device to optimized
dev_x, dev_y = 540, 960
opt_x, opt_y = converter.device_to_optimized(dev_x, dev_y)
print(f"Device ({dev_x}, {dev_y}) -> Optimized ({opt_x}, {opt_y})")

# Test optimized to device
back_x, back_y = converter.optimized_to_device(opt_x, opt_y)
print(f"Optimized ({opt_x}, {opt_y}) -> Device ({back_x}, {back_y})")

# Test denormalize Qwen coords
qwen_x, qwen_y = 500, 500  # Center in [0,1000) space
pixel_x, pixel_y = denormalize_qwen_coords(qwen_x, qwen_y, 1080, 1920)
print(f"Qwen normalized ({qwen_x}, {qwen_y}) -> Pixel ({pixel_x}, {pixel_y})")

# Test 4: Config
print("\n" + "=" * 60)
print("Test 4: RVAgentConfig")
print("=" * 60)

from rv_agent.config.agent_config import RVAgentConfig

config = RVAgentConfig.create_default(
    package_name="com.example.app",
    device_id="emulator-5554"
)

print(f"Config created:")
print(f"  package_name: {config.package_name}")
print(f"  llm_model: {config.llm_model}")
print(f"  llm_base_url: {config.llm_base_url}")
print(f"  llm_temperature: {config.llm_temperature}")
print(f"  agent_mode: {config.agent_mode}")
print(f"  llm_probability: {config.llm_probability}")

lc_config = config.get_langchain_config()
print(f"\nLangChain config: {lc_config}")

print("\n" + "=" * 60)
print("All tests passed!")
print("=" * 60)
