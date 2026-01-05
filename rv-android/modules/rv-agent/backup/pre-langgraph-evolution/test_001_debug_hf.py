#!/usr/bin/env python3
"""
Debug HuggingFace model loading for validation
"""

import json
import time
from pathlib import Path
import torch
from PIL import Image
from huggingface_hub import InferenceClient
import os

# Get HF token
HF_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
if not HF_TOKEN:
    print("❌ HUGGINGFACE_TOKEN not found in environment")
    exit(1)

print(f"🔐 Using HF Token: {HF_TOKEN[:10]}...")

# Test image
test_image = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk/001.png"

print(f"🖼️ Loading test image: {test_image}")
if not Path(test_image).exists():
    print(f"❌ Image not found: {test_image}")
    exit(1)

# Simple HuggingFace test
client = InferenceClient(token=HF_TOKEN)

print("🔄 Testing simple HuggingFace client...")
start_time = time.time()

try:
    with open(test_image, "rb") as f:
        image_data = f.read()

    # Test a simple request
    response = client.chat_completion(
        model="microsoft/Phi-4-multimodal-instruct",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What do you see in this image?"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data.hex()}"}}
                ]
            }
        ],
        max_tokens=100
    )

    elapsed = time.time() - start_time
    print(f"✅ Success in {elapsed:.1f}s")
    print(f"📝 Response: {response.choices[0].message.content}")

except Exception as e:
    elapsed = time.time() - start_time
    print(f"❌ Error in {elapsed:.1f}s: {e}")

print("🏁 Debug test completed")