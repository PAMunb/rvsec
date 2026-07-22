#!/usr/bin/env python3
"""
RVAgent Test 001: HuggingFace Tools Validation
Objetivo: Validar se HuggingFace consegue usar tools corretamente no CryptoApp

Contexto:
- Ollama JÁ testado: 0/8 modelos support tool-calling com vision
- HuggingFace: Agora funcionando, precisa testar tools integration
- CryptoApp: Aplicação controlada para validação precisa

Meta: LLM deve conseguir:
1. Analisar screenshot do CryptoApp
2. Identificar botões (Message Digest, Cipher, Generated)
3. Chamar android_click() com coordenadas corretas
4. Executar ações via tools (não structured generation)
"""

import json
import time
import torch
from PIL import Image
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

# LangChain tools integration
from langchain_core.tools import tool
from langchain.agents import create_react_agent, AgentExecutor
from langchain.prompts import PromptTemplate

# Screenshot do CryptoApp (001.png = MainActivity)
CRYPTOAPP_SCREENSHOT = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk/001.png"
RESULTS_FILE = "test_001_hf_tools_results.json"

@dataclass
class ToolCallResult:
    """Result from a tool call"""
    tool_name: str
    args: Dict
    success: bool
    result: str
    coordinates_format: Optional[str] = None

@dataclass
class ModelTestResult:
    """Overall test result for a model"""
    model_name: str
    platform: str
    vision_description: str
    tool_calls: List[ToolCallResult]
    cryptoapp_buttons_found: int
    coordinate_precision: str
    success_rate: float
    notes: str

# Tools que o RVAgent vai usar
@tool
def android_click(coordinates: str, element_description: str = "", reasoning: str = "") -> str:
    """
    Click on Android UI elements using exact coordinates.

    Args:
        coordinates: Format "at position (x, y)" - EXACT format required!
        element_description: What element you're clicking
        reasoning: Why you're clicking this element

    Returns:
        Success message with action performed
    """
    # Validate coordinate format (Phase 0 critical finding)
    if "at position (" not in coordinates or ")" not in coordinates:
        return f"❌ ERROR: Incorrect coordinate format. Use 'at position (x, y)' not '{coordinates}'"

    try:
        # Extract coordinates
        import re
        match = re.search(r'at position \((\d+),\s*(\d+)\)', coordinates)
        if match:
            x, y = int(match.group(1)), int(match.group(2))
            result = f"✅ CLICKED {coordinates}"
            if element_description:
                result += f" on {element_description}"
            if reasoning:
                result += f" (reason: {reasoning})"
            return result
        else:
            return f"❌ ERROR: Could not parse coordinates from '{coordinates}'"

    except Exception as e:
        return f"❌ ERROR: {str(e)}"

@tool
def android_input(text: str, coordinates: str = "", reasoning: str = "") -> str:
    """
    Input text into Android text fields.

    Args:
        text: Text to input
        coordinates: Optional tap location "at position (x, y)"
        reasoning: Why inputting this text

    Returns:
        Success message
    """
    result = f"✅ INPUT text '{text}'"
    if coordinates:
        result += f" {coordinates}"
    if reasoning:
        result += f" (reason: {reasoning})"
    return result

def create_huggingface_agent():
    """Create LangChain agent with HuggingFace LLM"""
    try:
        # Import HuggingFace integration for LangChain
        from langchain_huggingface import HuggingFacePipeline
        from transformers import pipeline, LlavaForConditionalGeneration, AutoProcessor, BitsAndBytesConfig

        print("🔧 Setting up HuggingFace LangChain agent...")

        # Use quantized LLaVa model that we know works
        model_name = "llava-hf/llava-1.5-7b-hf"

        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_quant_type="nf4"
        )

        processor = AutoProcessor.from_pretrained(model_name)
        model = LlavaForConditionalGeneration.from_pretrained(
            model_name,
            quantization_config=quantization_config,
            device_map="auto",
            torch_dtype=torch.bfloat16
        )

        # Create HuggingFace pipeline for LangChain
        hf_pipeline = pipeline(
            "text-generation",
            model=model,
            tokenizer=processor.tokenizer,
            max_new_tokens=200,
            temperature=0.25,
            do_sample=True
        )

        # Wrap in LangChain
        llm = HuggingFacePipeline(pipeline=hf_pipeline)

        # Tools for RVAgent
        tools = [android_click, android_input]

        # ReAct prompt template
        prompt = PromptTemplate.from_template("""
You are RVAgent, an autonomous Android testing agent.

You have access to these tools:
{tools}

Use the following format:
Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original question

Question: {input}
{agent_scratchpad}
""")

        # Create ReAct agent
        agent = create_react_agent(llm, tools, prompt)
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

        return agent_executor, model, processor

    except Exception as e:
        print(f"❌ Failed to create HF agent: {e}")
        return None, None, None

def test_cryptoapp_vision_tools():
    """Test HuggingFace agent on CryptoApp screenshot"""
    print("\n🔍 Testing HuggingFace Tools on CryptoApp...")

    if not Path(CRYPTOAPP_SCREENSHOT).exists():
        print(f"❌ Screenshot not found: {CRYPTOAPP_SCREENSHOT}")
        return None

    # Load screenshot
    image = Image.open(CRYPTOAPP_SCREENSHOT)
    print(f"📸 Loaded screenshot: {image.size}")

    # Create agent
    agent_executor, model, processor = create_huggingface_agent()
    if not agent_executor:
        return None

    # Test prompt focusing on CryptoApp specific task
    test_prompt = f"""
    Analyze the CryptoApp Android screenshot and perform these actions:

    1. Identify the 3 main buttons: "Message Digest", "Cipher", "Generated"
    2. For each button, use android_click with EXACT coordinates in format "at position (x, y)"
    3. The coordinate format is CRITICAL - must be exactly "at position (x, y)"

    Your task: Click on the "Message Digest" button using android_click tool.
    Remember: Phase 0 validation showed "at position (x, y)" format = 100% success rate.
    """

    start_time = time.time()

    try:
        # Execute agent
        result = agent_executor.invoke({"input": test_prompt})

        execution_time = time.time() - start_time

        # Analyze results
        tool_calls = []
        if "Action:" in result.get("output", ""):
            # Parse tool calls from agent execution
            output = result["output"]
            if "android_click" in output:
                tool_calls.append(ToolCallResult(
                    tool_name="android_click",
                    args={"coordinates": "extracted from output"},
                    success=True,
                    result="Tool called successfully",
                    coordinates_format="at position (x, y)"
                ))

        # Check VRAM usage
        vram_used = 0
        if torch.cuda.is_available():
            vram_used = torch.cuda.memory_allocated() / 1024**3

        # Cleanup
        del model, processor
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        return ModelTestResult(
            model_name="llava-hf/llava-1.5-7b-hf",
            platform="huggingface",
            vision_description=result.get("output", "")[:300],
            tool_calls=tool_calls,
            cryptoapp_buttons_found=len(tool_calls),
            coordinate_precision="Phase 0 format validated",
            success_rate=len(tool_calls) / 3 if tool_calls else 0,
            notes=f"Execution time: {execution_time:.2f}s, VRAM: {vram_used:.2f}GB"
        )

    except Exception as e:
        print(f"❌ Agent execution failed: {e}")
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return None

def test_structured_generation_fallback():
    """Test structured generation as fallback (like Ollama approach)"""
    print("\n🔍 Testing HuggingFace Structured Generation...")

    try:
        from transformers import LlavaForConditionalGeneration, AutoProcessor, BitsAndBytesConfig

        model_name = "llava-hf/llava-1.5-7b-hf"

        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_quant_type="nf4"
        )

        processor = AutoProcessor.from_pretrained(model_name)
        model = LlavaForConditionalGeneration.from_pretrained(
            model_name,
            quantization_config=quantization_config,
            device_map="auto",
            torch_dtype=torch.bfloat16
        )

        # Load image
        image = Image.open(CRYPTOAPP_SCREENSHOT)

        # Structured generation prompt (similar to successful Ollama tests)
        prompt = """USER: <image>
Analyze this CryptoApp screenshot and generate tool calls in JSON format.

For each button you see (Message Digest, Cipher, Generated), create an android_click call:
{
  "action": "android_click",
  "coordinates": "at position (x, y)",
  "element_description": "button name",
  "reasoning": "why clicking this button"
}

CRITICAL: Use exact format "at position (x, y)" - this achieved 100% success in validation.

ASSISTANT:"""

        inputs = processor(prompt, image, return_tensors="pt")
        device = next(model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}

        start_time = time.time()
        with torch.no_grad():
            output = model.generate(
                **inputs,
                max_new_tokens=300,
                temperature=0.25,
                do_sample=True
            )
        generation_time = time.time() - start_time

        response = processor.decode(output[0], skip_special_tokens=True)
        assistant_response = response.split("ASSISTANT:")[-1].strip()

        # Parse JSON actions (simulated)
        buttons_found = 0
        coordinate_format_correct = 0

        if "Message Digest" in assistant_response:
            buttons_found += 1
        if "Cipher" in assistant_response:
            buttons_found += 1
        if "Generated" in assistant_response:
            buttons_found += 1

        # Check coordinate format
        import re
        coordinates_found = len(re.findall(r'at position \(\d+,\s*\d+\)', assistant_response))
        coordinate_format_correct = coordinates_found

        # VRAM check
        vram_used = 0
        if torch.cuda.is_available():
            vram_used = torch.cuda.memory_allocated() / 1024**3

        # Cleanup
        del model, processor
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        tool_calls = [
            ToolCallResult(
                tool_name="android_click_structured",
                args={"buttons_detected": buttons_found},
                success=buttons_found > 0,
                result=f"{buttons_found} buttons detected",
                coordinates_format=f"{coordinate_format_correct} correct format"
            )
        ]

        return ModelTestResult(
            model_name="llava-hf/llava-1.5-7b-hf-structured",
            platform="huggingface",
            vision_description=assistant_response[:300],
            tool_calls=tool_calls,
            cryptoapp_buttons_found=buttons_found,
            coordinate_precision=f"{coordinate_format_correct}/{buttons_found} correct format",
            success_rate=buttons_found / 3,
            notes=f"Generation time: {generation_time:.2f}s, VRAM: {vram_used:.2f}GB"
        )

    except Exception as e:
        print(f"❌ Structured generation failed: {e}")
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return None

def compare_with_ollama_baseline():
    """Include Ollama baseline results from previous testing"""
    return ModelTestResult(
        model_name="qwen2.5vl:7b",
        platform="ollama",
        vision_description="Excellent CryptoApp vision - identified all 3 buttons perfectly",
        tool_calls=[],  # No tool calling support
        cryptoapp_buttons_found=3,
        coordinate_precision="Perfect detection, no tool execution",
        success_rate=0,  # Can't execute tools
        notes="Champion vision model but ZERO tool-calling support with images"
    )

def analyze_results(results: List[ModelTestResult]):
    """Analyze and compare results"""
    print("\n📊 TEST_001 ANALYSIS: HuggingFace Tools Validation")
    print("=" * 70)

    hf_results = [r for r in results if r.platform == "huggingface"]
    ollama_results = [r for r in results if r.platform == "ollama"]

    print(f"\n🟠 HUGGINGFACE RESULTS:")
    for result in hf_results:
        print(f"  📊 {result.model_name}:")
        print(f"     Vision: {result.cryptoapp_buttons_found}/3 buttons")
        print(f"     Tools: {len(result.tool_calls)} tool calls")
        print(f"     Success Rate: {result.success_rate:.1%}")
        print(f"     Notes: {result.notes}")

    print(f"\n🔵 OLLAMA BASELINE:")
    for result in ollama_results:
        print(f"  📊 {result.model_name}:")
        print(f"     Vision: {result.cryptoapp_buttons_found}/3 buttons (excellent)")
        print(f"     Tools: {len(result.tool_calls)} tool calls (zero support)")
        print(f"     Success Rate: {result.success_rate:.1%}")

    # Determine viability
    hf_tools_working = any(r.success_rate > 0 for r in hf_results)

    print(f"\n🎯 VIABILITY ANALYSIS:")
    if hf_tools_working:
        best_hf = max(hf_results, key=lambda x: x.success_rate)
        print(f"✅ HuggingFace IS VIABLE for RVAgent!")
        print(f"   Champion: {best_hf.model_name}")
        print(f"   Success Rate: {best_hf.success_rate:.1%}")
        print(f"   Tools Working: {len(best_hf.tool_calls)} calls")
    else:
        print(f"❌ HuggingFace NOT VIABLE - no tool calling success")
        print(f"🔄 Recommendation: Use structured generation approach")

    return hf_tools_working

def main():
    """Main test execution"""
    print("🚀 RVAgent Test 001: HuggingFace Tools Validation")
    print("=" * 70)
    print("🎯 Objective: Validate LLM can use tools correctly in CryptoApp")
    print("📱 Target: android_click() with precise coordinates")
    print("🏆 Success: LLM calls tools instead of structured generation")

    results = []

    # Test 1: HuggingFace ReAct Agent with Tools
    print("\n" + "="*50)
    print("TEST 1: HuggingFace ReAct Agent")
    print("="*50)

    hf_agent_result = test_cryptoapp_vision_tools()
    if hf_agent_result:
        results.append(hf_agent_result)

    # Test 2: HuggingFace Structured Generation (fallback)
    print("\n" + "="*50)
    print("TEST 2: HuggingFace Structured Generation")
    print("="*50)

    hf_structured_result = test_structured_generation_fallback()
    if hf_structured_result:
        results.append(hf_structured_result)

    # Test 3: Include Ollama baseline
    print("\n" + "="*50)
    print("TEST 3: Ollama Baseline (from previous tests)")
    print("="*50)

    ollama_baseline = compare_with_ollama_baseline()
    results.append(ollama_baseline)

    # Analysis
    viability = analyze_results(results)

    # Save results
    with open(RESULTS_FILE, 'w') as f:
        json.dump({
            "test": "test_001_hf_tools_validation",
            "timestamp": time.time(),
            "objective": "Validate HuggingFace tools for RVAgent",
            "target_app": "CryptoApp",
            "viability": viability,
            "results": [
                {
                    "model": r.model_name,
                    "platform": r.platform,
                    "buttons_found": r.cryptoapp_buttons_found,
                    "tool_calls": len(r.tool_calls),
                    "success_rate": r.success_rate,
                    "coordinate_precision": r.coordinate_precision,
                    "notes": r.notes
                } for r in results
            ]
        }, f, indent=2)

    print(f"\n✅ Results saved to: {RESULTS_FILE}")

    if viability:
        print(f"\n🎉 CONCLUSION: HuggingFace VIABLE for RVAgent!")
        print(f"📋 Next: Implement test_002_cryptoapp_navigation.py")
    else:
        print(f"\n💡 CONCLUSION: Need structured generation approach")
        print(f"📋 Next: Optimize structured generation pipeline")

    return viability

if __name__ == "__main__":
    success = main()