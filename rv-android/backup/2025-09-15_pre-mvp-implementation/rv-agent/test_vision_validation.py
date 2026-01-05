#!/usr/bin/env python3
"""
Vision Model Validation Test
Testa a capacidade do modelo de visão de descrever imagens e identificar dimensões.
Usado para qualificar o modelo antes dos testes de coordenadas.
"""

import os
import time
import base64
from pathlib import Path
import json

def test_vision_description():
    """Test vision model's ability to describe screenshots."""
    
    print("Vision Model Validation - Image Description Test")
    print("=" * 60)
    
    # Find test screenshots (look in workspace root)
    workspace_root = Path("../..").resolve()
    screenshot_patterns = [
        "screenshot_*.png",
        "tmp_img/*.png", 
        "visualization_*.png"
    ]
    
    screenshots = []
    for pattern in screenshot_patterns:
        screenshots.extend(workspace_root.glob(pattern))
    
    if not screenshots:
        print("❌ No screenshots found for testing")
        return
        
    # Limit to 30-50 screenshots as requested
    test_screenshots = sorted(screenshots)[:30]
    print(f"📱 Found {len(test_screenshots)} screenshots for validation")
    
    try:
        # Import LangChain components
        from langchain_ollama import ChatOllama
        from langchain_core.messages import HumanMessage
        
        print("🤖 Creating ChatOllama client...")
        llm = ChatOllama(
            model="llama3.2-vision:11b",
            temperature=0.1,
            base_url="http://localhost:11434"
        )
        
        results = []
        
        for i, screenshot_path in enumerate(test_screenshots, 1):
            print(f"\n📸 Testing screenshot {i}/{len(test_screenshots)}: {screenshot_path.name}")
            
            try:
                # Read and encode image
                with open(screenshot_path, "rb") as image_file:
                    image_data = base64.b64encode(image_file.read()).decode('utf-8')
                
                # Create description prompt
                description_prompt = """Analyze this Android screenshot and provide:

1. SCREEN DESCRIPTION: What type of screen/app is this? What are the main UI elements?
2. IMAGE DIMENSIONS: What are the width and height dimensions you perceive for this image?
3. KEY ELEMENTS: List the most important clickable elements you can see (buttons, icons, text fields, etc.)
4. LAYOUT ASSESSMENT: How is the content organized? (top bar, main content, bottom navigation, etc.)

Please be specific and detailed in your analysis."""

                # Create message with encoded image
                message = HumanMessage(content=[
                    {"type": "text", "text": description_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_data}"}}
                ])
                
                print(f"🔍 Sending analysis request...")
                start_time = time.time()
                response = llm.invoke([message])
                response_time = time.time() - start_time
                
                # Store result
                result = {
                    "screenshot": str(screenshot_path),
                    "file_size_kb": screenshot_path.stat().st_size / 1024,
                    "response_time_s": round(response_time, 2),
                    "description": response.content,
                    "success": True
                }
                
                results.append(result)
                
                print(f"✅ Analysis completed in {response_time:.1f}s")
                print(f"📝 Response preview: {response.content[:100]}...")
                
            except Exception as e:
                print(f"❌ Error analyzing {screenshot_path.name}: {e}")
                result = {
                    "screenshot": str(screenshot_path),
                    "error": str(e),
                    "success": False
                }
                results.append(result)
                continue
        
        # Save results
        results_file = "vision_validation_results.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Print summary
        successful = sum(1 for r in results if r.get("success", False))
        total_time = sum(r.get("response_time_s", 0) for r in results if r.get("success", False))
        avg_time = total_time / successful if successful > 0 else 0
        
        print(f"\n🎯 VALIDATION SUMMARY")
        print(f"   Screenshots tested: {len(results)}")
        print(f"   Successful analyses: {successful}")
        print(f"   Failed analyses: {len(results) - successful}")
        print(f"   Average response time: {avg_time:.1f}s")
        print(f"   Results saved to: {results_file}")
        
        if successful > 0:
            print(f"\n📊 SAMPLE ANALYSIS:")
            sample = next(r for r in results if r.get("success", False))
            print(f"   File: {Path(sample['screenshot']).name}")
            print(f"   Size: {sample['file_size_kb']:.1f} KB")
            print(f"   Time: {sample['response_time_s']}s")
            print(f"   Description: {sample['description'][:200]}...")
        
        return results
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("💡 Try: poetry install --extras ollama")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None

if __name__ == "__main__":
    test_vision_description()