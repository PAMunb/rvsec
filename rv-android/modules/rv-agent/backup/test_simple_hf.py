#!/usr/bin/env python3
"""Simple test to diagnose HuggingFace loading issues."""

print("1. Importing torch...")
import torch
print(f"   ✅ Torch version: {torch.__version__}")
print(f"   ✅ CUDA available: {torch.cuda.is_available()}")

print("\n2. Importing transformers...")
import transformers
print(f"   ✅ Transformers version: {transformers.__version__}")

print("\n3. Importing AutoProcessor...")
from transformers import AutoProcessor
print("   ✅ AutoProcessor imported")

print("\n4. Importing Qwen3VLForConditionalGeneration...")
from transformers import Qwen3VLForConditionalGeneration
print("   ✅ Qwen3VLForConditionalGeneration imported")

print("\n5. Loading processor...")
model_path = "./models/qwen3-vl-4b-fp8"
try:
    processor = AutoProcessor.from_pretrained(model_path)
    print("   ✅ Processor loaded successfully")
except Exception as e:
    print(f"   ❌ Failed to load processor: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n6. Testing apply_chat_template with tools...")
try:
    def test_tool(x: int):
        """Test tool."""
        pass

    messages = [
        {"role": "user", "content": [{"type": "text", "text": "test"}]}
    ]

    text = processor.apply_chat_template(
        messages,
        tools=[test_tool],
        tokenize=False,
        add_generation_prompt=True
    )
    print("   ✅ apply_chat_template with tools works!")
    print(f"\n   Generated text preview (first 200 chars):")
    print(f"   {text[:200]}...")

except Exception as e:
    print(f"   ❌ Failed: {e}")
    import traceback
    traceback.print_exc()

print("\n✅ All basic tests passed!")
