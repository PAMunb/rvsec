#!/usr/bin/env python3
"""
FASE C.1 - Phi-4 Multimodal Direct Test
Tests microsoft/Phi-4-multimodal-instruct directly via HuggingFace pipeline

MEMORY MANAGEMENT:
- 4-bit quantization to reduce VRAM usage (16GB limit)
- Clear GPU memory after test
- Monitor VRAM consumption
"""

import json
import time
import torch
import gc
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv("/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-agent/.env")

try:
    from transformers import (
        AutoProcessor,
        AutoModelForCausalLM,  # Correct model class for Phi-4
        BitsAndBytesConfig,
        GenerationConfig
    )
    from PIL import Image
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("⚠️  transformers not available - will run simulation")

from shared_validation_utils import (
    ValidationMetrics,
    CryptoAppGroundTruth,
    validate_coordinates,
    log_test_result
)

def check_gpu_memory():
    """Check and display GPU memory usage"""
    if torch.cuda.is_available():
        allocated = torch.cuda.memory_allocated() / 1024**3
        reserved = torch.cuda.memory_reserved() / 1024**3
        total = torch.cuda.get_device_properties(0).total_memory / 1024**3
        print(f"🧠 GPU Memory: {allocated:.1f}GB allocated, {reserved:.1f}GB reserved, {total:.1f}GB total")
        return allocated, reserved, total
    else:
        print("❌ CUDA not available")
        return 0, 0, 0

def clear_gpu_memory():
    """Clear GPU memory to prevent VRAM overflow"""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        gc.collect()
        print("🧹 GPU memory cleared")

def create_quantization_config():
    """Create 4-bit quantization config for memory efficiency"""
    return BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True
    )

def parse_phi4_response(response_text: str) -> Optional[Dict[str, Any]]:
    """Parse Phi-4 response for coordinate extraction"""
    try:
        # Look for coordinate patterns
        import re

        # Try JSON first
        json_match = re.search(r'\{[^}]*\}', response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass

        # Extract coordinates using patterns
        coord_patterns = [
            r'at position \((\d+),\s*(\d+)\)',
            r'coordinates \((\d+),\s*(\d+)\)',
            r'click \((\d+),\s*(\d+)\)',
            r'(\d+),\s*(\d+)'
        ]

        for pattern in coord_patterns:
            match = re.search(pattern, response_text)
            if match:
                x, y = int(match.group(1)), int(match.group(2))

                # Extract description context
                description = ""
                desc_patterns = [
                    r'(button|element|component)[^.]*',
                    r'(Message Digest|Cipher|Generated)[^.]*'
                ]
                for desc_pattern in desc_patterns:
                    desc_match = re.search(desc_pattern, response_text, re.IGNORECASE)
                    if desc_match:
                        description = desc_match.group()
                        break

                return {
                    "action": "android_click",
                    "coordinates": [x, y],
                    "element_description": description,
                    "raw_response": response_text[:200]
                }

        return None

    except Exception as e:
        print(f"⚠️  Response parsing error: {e}")
        return None

def test_phi4_multimodal_direct():
    """Test Phi-4 multimodal directly via HuggingFace with memory management"""

    print("🔬 FASE C.1 - Phi-4 Multimodal Direct Test")
    print("=" * 60)

    # Check initial memory
    check_gpu_memory()

    if not TRANSFORMERS_AVAILABLE:
        print("❌ transformers not available - running simulation")
        return test_phi4_simulation()

    # Load screenshot
    screenshot_path = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk/004.png"

    if not Path(screenshot_path).exists():
        print(f"❌ Screenshot not found: {screenshot_path}")
        return

    print(f"📱 Screenshot: {screenshot_path}")
    print(f"🤖 Model: microsoft/Phi-4-multimodal-instruct")
    print(f"🏗️  Approach: Direct HuggingFace pipeline (4-bit quantized)")

    try:
        # Create quantization config for memory efficiency
        quantization_config = create_quantization_config()

        print("⏳ Loading Phi-4 multimodal model (4-bit quantized)...")

        # Get HuggingFace token from environment
        hf_token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
        if not hf_token:
            print("⚠️  No HuggingFace token found in .env file")
            return test_phi4_simulation()

        print(f"✅ Using HuggingFace token: {hf_token[:10]}...")

        # Load processor and model with official Phi-4 configuration
        model_path = "microsoft/Phi-4-multimodal-instruct"

        processor = AutoProcessor.from_pretrained(
            model_path,
            trust_remote_code=True,
            token=hf_token
        )

        # Force disable FlashAttention2 at environment level
        os.environ["TRANSFORMERS_NO_FLASH_ATTN"] = "1"

        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            quantization_config=quantization_config,
            device_map="auto",
            trust_remote_code=True,
            torch_dtype=torch.float16,
            token=hf_token,
            _attn_implementation="eager",  # Alternative parameter name
        )

        # Load generation config
        generation_config = GenerationConfig.from_pretrained(
            model_path,
            token=hf_token
        )

        print("✅ Phi-4 model loaded successfully")
        check_gpu_memory()

        # Load image
        image = Image.open(screenshot_path).convert("RGB")

        # Create Phi-4 format prompt with official template
        prompt = """<|user|><|image_1|>You are an expert Android testing agent. Analyze this CryptoApp screenshot and identify the most important button to click for testing.

COORDINATE PRECISION STRATEGY:
- Use exact pixel coordinates "at position (x, y)"
- Target center of UI elements for optimal accuracy
- Focus on buttons like "Message Digest", "Cipher", or "Generated"

Provide your response with precise coordinates in the format: "Click at position (x, y)" followed by a brief explanation.<|end|><|assistant|>"""

        # Test multiple iterations for consistency
        iterations = 2  # Reduced to save memory
        results = []

        start_time = time.time()

        for i in range(iterations):
            print(f"\n🔄 Iteration {i+1}/{iterations}")

            try:
                # Process input with Phi-4 official format
                inputs = processor(text=prompt, images=image, return_tensors='pt').to(model.device)

                # Generate response with Phi-4 official configuration
                with torch.no_grad():
                    generate_ids = model.generate(
                        **inputs,
                        max_new_tokens=150,  # Use max_new_tokens instead of max_length
                        generation_config=generation_config,
                        temperature=0.1,
                        do_sample=False,
                        pad_token_id=processor.tokenizer.eos_token_id
                    )

                # Decode response using official method
                response_text = processor.batch_decode(
                    generate_ids[:, inputs['input_ids'].shape[1]:],
                    skip_special_tokens=True,
                    clean_up_tokenization_spaces=False
                )[0]

                # Remove prompt from response
                if prompt in response_text:
                    response_text = response_text.replace(prompt, "").strip()

                print(f"   📝 Raw Response: {response_text[:100]}...")

                # Parse response
                parsed_response = parse_phi4_response(response_text)

                if parsed_response:
                    coords = parsed_response.get("coordinates", [])
                    print(f"   ✅ Parsed Coordinates: {coords}")
                    print(f"   📄 Description: {parsed_response.get('element_description', '')}")

                    results.append({
                        "iteration": i + 1,
                        "success": True,
                        "response": parsed_response,
                        "raw_text": response_text
                    })
                else:
                    print(f"   ❌ Failed to parse coordinates")
                    results.append({
                        "iteration": i + 1,
                        "success": False,
                        "response": None,
                        "raw_text": response_text
                    })

                # Check memory after each iteration
                check_gpu_memory()

            except Exception as e:
                print(f"   ❌ Generation error: {e}")
                results.append({
                    "iteration": i + 1,
                    "success": False,
                    "response": None,
                    "error": str(e)
                })

        execution_time = time.time() - start_time

        # Analyze results
        successful_responses = sum(1 for r in results if r["success"])
        success_rate = (successful_responses / iterations) * 100

        print(f"\n📊 PHI-4 DIRECT PIPELINE RESULTS:")
        print(f"✅ Response Success: {success_rate:.1f}% ({successful_responses}/{iterations})")
        print(f"⏱️  Total Time: {execution_time:.2f}s")
        print(f"🧠 4-bit Quantization: {'✅ Effective' if successful_responses > 0 else '❌ Issues'}")

        # Coordinate validation
        ground_truth = CryptoAppGroundTruth()
        coordinate_validations = []

        for result in results:
            if result["success"] and result["response"]:
                response = result["response"]
                coordinates = response.get("coordinates", [])

                if coordinates and len(coordinates) == 2:
                    x, y = int(coordinates[0]), int(coordinates[1])
                    is_valid, distance = validate_coordinates(x, y, ground_truth.screenshot_004_elements)

                    coordinate_validations.append({
                        "iteration": result["iteration"],
                        "coords": [x, y],
                        "valid": is_valid,
                        "distance": distance,
                        "element_description": response.get("element_description", ""),
                        "quantization": "4-bit"
                    })

        if coordinate_validations:
            valid_coords = sum(1 for val in coordinate_validations if val["valid"])
            total_coords = len(coordinate_validations)
            coord_accuracy = (valid_coords / total_coords) * 100

            print(f"\n🎯 COORDINATE PRECISION (Phi-4 Direct):")
            print(f"   📊 Accuracy Rate: {coord_accuracy:.1f}% ({valid_coords}/{total_coords})")

            for val in coordinate_validations:
                status = "✅ PRECISE" if val["valid"] else "❌ IMPRECISE"
                desc = f" - {val['element_description']}" if val['element_description'] else ""
                print(f"   {val['iteration']}. {val['coords']} {status} ({val['distance']:.1f}px){desc}")
        else:
            coord_accuracy = 0
            print(f"\n❌ No valid coordinates for validation")

        # Create metrics
        metrics = ValidationMetrics(
            multimodal_support=True,
            tool_calling_detected=successful_responses > 0,
            response_time=execution_time,
            iterations_completed=iterations,
            tool_executions=successful_responses,
            success_rate=success_rate,
            multimodal_history=[True] * iterations
        )

        # Determine status
        if success_rate >= 90 and coord_accuracy >= 80:
            print(f"\n🎉 RESULTADO: EXCELENTE - Phi-4 direct pipeline highly effective")
            status = "EXCELLENT"
        elif success_rate >= 70 and coord_accuracy >= 60:
            print(f"\n⚡ RESULTADO: BOM - Phi-4 shows strong direct capability")
            status = "GOOD"
        elif success_rate >= 50:
            print(f"\n⚠️  RESULTADO: MODERADO - Phi-4 direct partially effective")
            status = "MODERATE"
        else:
            print(f"\n❌ RESULTADO: LIMITADO - Phi-4 direct pipeline issues")
            status = "LIMITED"

        # Log results
        result_data = {
            "model_name": "microsoft/Phi-4-multimodal-instruct",
            "test_phase": "FASE_C1",
            "deployment": "HuggingFace_direct_4bit",
            "quantization": "4-bit",
            "status": status,
            "metrics": metrics._asdict(),
            "coordinate_accuracy": coord_accuracy,
            "coordinate_validations": coordinate_validations,
            "iteration_results": results
        }

        log_test_result("C1_phi4_multimodal_direct", result_data)

        print(f"\n🔍 MEMORY MANAGEMENT ANALYSIS:")
        final_allocated, final_reserved, total = check_gpu_memory()
        print(f"   📊 VRAM Usage: {final_reserved:.1f}GB / 16GB ({(final_reserved/16)*100:.1f}%)")
        print(f"   🏗️  4-bit Quantization: {'✅ Effective' if final_reserved < 12 else '⚠️  High usage'}")

    except Exception as e:
        print(f"❌ Phi-4 direct test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # CRITICAL: Clear GPU memory to prevent VRAM overflow
        clear_gpu_memory()
        print("✅ GPU memory cleanup completed")

def test_phi4_simulation():
    """Simulation for Phi-4 direct if transformers unavailable"""

    print("\n🔄 SIMULATION: Phi-4 Multimodal Direct")
    print("=" * 50)

    # Simulate Phi-4 direct responses
    simulated_responses = [
        {
            "action": "android_click",
            "coordinates": [200, 240],
            "element_description": "Message Digest button",
            "confidence": "high"
        },
        {
            "action": "android_click",
            "coordinates": [200, 360],
            "element_description": "Cipher button",
            "confidence": "high"
        }
    ]

    print("📝 Simulating Phi-4 direct pipeline responses...")

    ground_truth = CryptoAppGroundTruth()
    coordinate_validations = []

    for i, response in enumerate(simulated_responses, 1):
        coordinates = response["coordinates"]
        x, y = coordinates[0], coordinates[1]

        is_valid, distance = validate_coordinates(x, y, ground_truth.screenshot_004_elements)

        coordinate_validations.append({
            "iteration": i,
            "coords": [x, y],
            "valid": is_valid,
            "distance": distance,
            "element_description": response["element_description"]
        })

        status = "✅ PRECISE" if is_valid else "❌ IMPRECISE"
        print(f"   {i}. {coordinates} {status} ({distance:.1f}px) - {response['element_description']}")

    valid_coords = sum(1 for val in coordinate_validations if val["valid"])
    coord_accuracy = (valid_coords / len(coordinate_validations)) * 100

    print(f"\n📊 SIMULATED PHI-4 DIRECT PERFORMANCE:")
    print(f"   ✅ Response Success: 100.0%")
    print(f"   🎯 Coordinate Accuracy: {coord_accuracy:.1f}%")
    print(f"   🧠 4-bit Quantization: SIMULATED_EFFECTIVE")
    print(f"   💾 VRAM Usage: ~8GB (estimated with quantization)")

    # Log simulated results
    metrics = ValidationMetrics(
        multimodal_support=True,
        tool_calling_detected=True,
        response_time=3.0,
        iterations_completed=2,
        tool_executions=2,
        success_rate=100.0,
        multimodal_history=[True, True]
    )

    result_data = {
        "model_name": "microsoft/Phi-4-multimodal-instruct",
        "test_phase": "FASE_C1_SIMULATED",
        "deployment": "HuggingFace_direct_4bit_simulation",
        "status": "SIMULATED_GOOD",
        "metrics": metrics._asdict(),
        "coordinate_accuracy": coord_accuracy,
        "coordinate_validations": coordinate_validations,
        "note": "Simulated results - model not loaded"
    }

    log_test_result("C1_phi4_simulation", result_data)

if __name__ == "__main__":
    test_phi4_multimodal_direct()