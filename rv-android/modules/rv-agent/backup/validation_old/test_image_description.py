"""
Teste simples para verificar se o modelo recebe a imagem corretamente.
Apenas pede para descrever detalhadamente um screenshot Android.
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


def test_image_description():
    """Test if model can see and describe Android screenshot."""

    print("🔍 Simple Image Description Test")
    print("=" * 50)

    # Path to test screenshot
    screenshot_path = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/cryptoapp.apk/001.png"

    if not Path(screenshot_path).exists():
        print(f"❌ Screenshot not found: {screenshot_path}")
        return

    print(f"📸 Testing image: {screenshot_path}")

    # Initialize model
    print("🧠 Initializing Gemma3-tools...")
    llm = ChatOllama(
        model="PetrosStav/gemma3-tools:4b",
        temperature=0.1
    )

    # Encode image
    print("🖼️ Encoding image to base64...")
    try:
        image_base64 = encode_image_to_base64(screenshot_path)
        print(f"✅ Image encoded successfully ({len(image_base64)} chars)")
    except Exception as e:
        print(f"❌ Failed to encode image: {e}")
        return

    # Create multimodal message
    print("💬 Creating multimodal prompt...")

    message = HumanMessage(
        content=[
            {
                "type": "text",
                "text": """Please describe this Android application screenshot in detail.

Focus on:
1. What app this appears to be
2. What UI elements you can see (buttons, text fields, labels, etc.)
3. The layout and structure
4. Any text content visible
5. Colors and visual design

Be very specific and detailed about what you observe."""
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{image_base64}"
                }
            }
        ]
    )

    # Get response
    print("🤖 Requesting description from model...")
    print("-" * 50)

    try:
        response = llm.invoke([message])

        print("📝 MODEL RESPONSE:")
        print("=" * 50)
        print(response.content)
        print("=" * 50)

        # Analyze response
        response_text = response.content.lower()

        print("🔍 ANALYSIS:")
        print("-" * 30)

        if "android" in response_text:
            print("✅ Mentions Android")
        else:
            print("❌ Does not mention Android")

        if "button" in response_text:
            print("✅ Identifies buttons")
        else:
            print("❌ Does not identify buttons")

        if "crypto" in response_text or "digest" in response_text:
            print("✅ Recognizes crypto app content")
        else:
            print("❌ Does not recognize crypto app content")

        if "message digest" in response_text:
            print("✅ Sees 'MESSAGE DIGEST' text")
        else:
            print("❌ Does not see 'MESSAGE DIGEST' text")

        # Check if it's actually seeing the UI
        ui_indicators = ["button", "text", "interface", "screen", "app", "application"]
        ui_count = sum(1 for indicator in ui_indicators if indicator in response_text)

        print(f"📊 UI terminology count: {ui_count}/6")

        if ui_count >= 3:
            print("✅ Likely seeing actual UI elements")
        else:
            print("❌ May not be seeing UI properly")

    except Exception as e:
        print(f"❌ Model request failed: {e}")
        return

    print("\n🏁 Test completed!")


if __name__ == "__main__":
    test_image_description()