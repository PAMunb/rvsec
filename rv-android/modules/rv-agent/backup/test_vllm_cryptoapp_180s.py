#!/usr/bin/env python3
"""
Quick validation test of vLLM integration with CryptoApp.
180 second timeout test to validate zero loop rate.
"""

import os
import sys
import json
import time
import base64
from pathlib import Path
from openai import OpenAI

def test_vllm_with_cryptoapp_screenshots():
    """Test vLLM with real CryptoApp screenshots."""

    print("\n" + "=" * 80)
    print("vLLM Integration Test - CryptoApp Screenshots (180s)")
    print("=" * 80)

    # Find screenshots
    screenshot_dir = Path("/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/modules/rv-agent/screenshots")

    if not screenshot_dir.exists():
        print(f"❌ Screenshot directory not found: {screenshot_dir}")
        return False

    screenshots = sorted([f for f in screenshot_dir.glob("*.png")])[:5]  # Test first 5

    if not screenshots:
        print(f"❌ No screenshots found in {screenshot_dir}")
        return False

    print(f"\nFound {len(screenshots)} screenshots to test")
    print(f"vLLM Server: http://localhost:8000/v1")
    print(f"Model: Qwen3-VL-4B-FP8")
    print(f"Timeout: 180 seconds total\n")

    # Create OpenAI client for vLLM
    client = OpenAI(
        base_url="http://localhost:8000/v1",
        api_key="EMPTY"
    )

    # Test metrics
    results = {
        "total_calls": 0,
        "successful_calls": 0,
        "failed_calls": 0,
        "loop_count": 0,  # finish_reason='length'
        "total_tokens": 0,
        "total_time": 0.0,
        "responses": []
    }

    start_time = time.time()

    for i, screenshot_path in enumerate(screenshots):
        if time.time() - start_time > 180:
            print(f"\n⏱️  Timeout reached (180s)")
            break

        print(f"\n{'='*80}")
        print(f"Test {i+1}/{len(screenshots)}: {screenshot_path.name}")
        print("="*80)

        # Read screenshot
        with open(screenshot_path, 'rb') as f:
            screenshot_b64 = base64.b64encode(f.read()).decode('utf-8')

        # Call LLM
        try:
            call_start = time.time()

            response = client.chat.completions.create(
                model="./models/qwen3-vl-4b-fp8",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Describe this Android app screen briefly. What UI elements do you see?"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{screenshot_b64}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.6,
                top_p=0.95,
                max_tokens=2048,
                timeout=30.0,
                extra_body={
                    "top_k": 20,
                    "repetition_penalty": 1.1
                }
            )

            call_time = time.time() - call_start

            # Extract response
            content = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason
            tokens = response.usage.total_tokens

            # Update metrics
            results["total_calls"] += 1
            results["successful_calls"] += 1
            results["total_tokens"] += tokens
            results["total_time"] += call_time

            if finish_reason == 'length':
                results["loop_count"] += 1
                print(f"⚠️  WARNING: finish_reason='length' (possible loop)")
            else:
                print(f"✅ finish_reason='{finish_reason}'")

            print(f"Response: {content[:200]}...")
            print(f"Tokens: {tokens}, Time: {call_time:.2f}s")

            results["responses"].append({
                "screenshot": screenshot_path.name,
                "finish_reason": finish_reason,
                "tokens": tokens,
                "time": call_time,
                "content_preview": content[:100]
            })

        except Exception as e:
            results["total_calls"] += 1
            results["failed_calls"] += 1
            print(f"❌ Error: {e}")

    # Print summary
    print("\n" + "=" * 80)
    print("TEST RESULTS")
    print("=" * 80)

    print(f"\nCalls:")
    print(f"  Total: {results['total_calls']}")
    print(f"  Successful: {results['successful_calls']}")
    print(f"  Failed: {results['failed_calls']}")

    if results['total_calls'] > 0:
        success_rate = (results['successful_calls'] / results['total_calls']) * 100
        loop_rate = (results['loop_count'] / results['total_calls']) * 100

        print(f"\nMetrics:")
        print(f"  Success rate: {success_rate:.1f}%")
        print(f"  Loop rate: {loop_rate:.1f}%")
        print(f"  Total tokens: {results['total_tokens']}")
        print(f"  Total time: {results['total_time']:.2f}s")
        print(f"  Avg tokens/call: {results['total_tokens']/results['total_calls']:.0f}")
        print(f"  Avg time/call: {results['total_time']/results['total_calls']:.2f}s")

        print(f"\n{'='*80}")
        print("VALIDATION")
        print("=" * 80)

        if loop_rate == 0.0:
            print("✅ PASS: Zero loop rate (no token repetition)")
        else:
            print(f"❌ FAIL: Loop rate {loop_rate:.1f}% (expected 0%)")

        if success_rate >= 85.0:
            print(f"✅ PASS: Success rate {success_rate:.1f}% >= 85%")
        else:
            print(f"⚠️  WARNING: Success rate {success_rate:.1f}% < 85%")

    # Save results
    output_file = Path(__file__).parent / "vllm_cryptoapp_180s_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {output_file}")

    return results['loop_count'] == 0


if __name__ == "__main__":
    success = test_vllm_with_cryptoapp_screenshots()
    sys.exit(0 if success else 1)
