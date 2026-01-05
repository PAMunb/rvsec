#!/usr/bin/env python3
"""
Simple Vision Test - Quick validation of model capability
"""

import os
import time
import base64
from pathlib import Path

def test_simple_vision():
    """Quick test with one screenshot."""
    
    print("Simple Vision Model Test")
    print("=" * 40)
    
    # Find one test screenshot
    workspace_root = Path("../..").resolve()
    screenshots = list(workspace_root.glob("screenshot_*.png"))
    
    if not screenshots:
        print("❌ No screenshots found")
        return
        
    test_image = screenshots[0]
    print(f"📱 Testing with: {test_image.name}")
    
    try:
        from langchain_ollama import ChatOllama
        from langchain_core.messages import HumanMessage
        
        print("🤖 Creating Qwen 2.5VL 7B client...")
        llm = ChatOllama(
            model="qwen2.5vl:7b",  # Benchmark champion
            temperature=0.1,
            base_url="http://localhost:11434"
        )
        
        # Read and encode image
        with open(test_image, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
        
        # Simple description prompt
        prompt = """Describe this Android screenshot in 2-3 sentences. 
What type of screen is this and what can you see?"""

        message = HumanMessage(content=[
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
        ])
        
        print("🔍 Sending request...")
        start_time = time.time()
        response = llm.invoke([message])
        response_time = time.time() - start_time
        
        print(f"✅ Response received in {response_time:.1f}s")
        print(f"📝 Description:\n{response.content}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_simple_vision()