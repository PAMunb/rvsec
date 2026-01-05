"""
Compara diferentes modelos de visão para ver qual reconhece a imagem corretamente.
"""

import base64
import sys
from pathlib import Path

# Add rv-agent to path
rv_agent_path = str(Path(__file__).parent.parent / "src")
sys.path.insert(0, rv_agent_path)

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage


def encode_image_to_base64(image_path: str) -> str:
    """Encode image to base64."""
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
        return encoded_string


def test_model(model_name: str, image_base64: str) -> str:
    """Test a specific model with the image."""

    print(f"\n🧪 Testing model: {model_name}")
    print("-" * 40)

    try:
        llm = ChatOllama(model=model_name, temperature=0.1)

        message = HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": "Describe this Android app screenshot. What app is this and what buttons do you see?"
                },
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{image_base64}"}
                }
            ]
        )

        response = llm.invoke([message])

        print(f"📝 Response:")
        print(response.content[:300] + "..." if len(response.content) > 300 else response.content)

        # Quick analysis
        response_lower = response.content.lower()

        correct_indicators = []
        if "crypto" in response_lower:
            correct_indicators.append("✅ Recognizes 'Crypto'")
        if "message digest" in response_lower:
            correct_indicators.append("✅ Sees 'MESSAGE DIGEST'")
        if "cipher" in response_lower:
            correct_indicators.append("✅ Sees 'CIPHER'")
        if "generated" in response_lower:
            correct_indicators.append("✅ Sees 'GENERATED'")

        wrong_indicators = []
        if "calculator" in response_lower:
            wrong_indicators.append("❌ Thinks it's a calculator")
        if "numbers" in response_lower or "digits" in response_lower:
            wrong_indicators.append("❌ Sees numbers/digits")

        print(f"🔍 Analysis:")
        for indicator in correct_indicators:
            print(f"  {indicator}")
        for indicator in wrong_indicators:
            print(f"  {indicator}")

        score = len(correct_indicators) - len(wrong_indicators)
        print(f"📊 Score: {score}/4")

        return response.content

    except Exception as e:
        print(f"❌ Error: {e}")
        return ""


def main():
    """Compare different vision models."""

    print("🔍 Model Comparison Test")
    print("=" * 50)

    screenshot_path = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk/001.png"

    if not Path(screenshot_path).exists():
        print(f"❌ Screenshot not found: {screenshot_path}")
        return

    print(f"📸 Testing image: {screenshot_path}")

    # Encode image once
    try:
        image_base64 = encode_image_to_base64(screenshot_path)
        print(f"✅ Image encoded successfully")
    except Exception as e:
        print(f"❌ Failed to encode image: {e}")
        return

    # Models to test
    models_to_test = [
        "PetrosStav/gemma3-tools:4b",  # Current problematic model
        "llama3.2-vision:latest",      # Alternative vision model
        # "qwen2.5vl:7b",               # Phase 0 champion (if available)
    ]

    results = {}

    for model in models_to_test:
        try:
            response = test_model(model, image_base64)
            results[model] = response
        except Exception as e:
            print(f"❌ Model {model} failed: {e}")
            results[model] = None

    # Summary
    print("\n" + "=" * 60)
    print("📊 COMPARISON SUMMARY")
    print("=" * 60)

    for model, response in results.items():
        if response:
            response_lower = response.lower()
            if "crypto" in response_lower and "message digest" in response_lower:
                print(f"✅ {model}: CORRECT recognition")
            elif "calculator" in response_lower:
                print(f"❌ {model}: WRONG (sees calculator)")
            else:
                print(f"⚠️ {model}: UNCLEAR recognition")
        else:
            print(f"💥 {model}: FAILED to respond")

    print("\n🔬 CONCLUSION:")
    print("If Gemma3-tools consistently sees a calculator instead of the Crypto app,")
    print("we need to either:")
    print("1. Switch to a different vision model")
    print("2. Find a different version of Gemma3-tools")
    print("3. Use a different approach for image input")


if __name__ == "__main__":
    main()