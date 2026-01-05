#!/usr/bin/env python3
"""
Test RVAgent with integrated JSON parser.

Validates that the full RVAgent system works with qwen-vision-tools-v2 model
and JSON parser integration for vision+tools responses.
"""

import logging
from pathlib import Path

from rv_agent.config.agent_config import RVAgentConfig
from rv_agent.core.rv_agent import RVAgent
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Mock device for testing
class MockDevice:
    """Mock Android device for testing."""

    def __init__(self):
        self.actions = []
        self.current_screen = None

    def click(self, x, y):
        """Mock click action."""
        action = {'type': 'click', 'x': x, 'y': y}
        self.actions.append(action)
        print(f"   📱 MOCK DEVICE CLICK: ({x}, {y})")
        return True

    def input_text(self, text):
        """Mock text input action."""
        action = {'type': 'input_text', 'text': text}
        self.actions.append(action)
        print(f"   ⌨️  MOCK DEVICE INPUT_TEXT: '{text}'")
        return True

    def long_click(self, x, y):
        """Mock long click action."""
        action = {'type': 'long_click', 'x': x, 'y': y}
        self.actions.append(action)
        print(f"   📱 MOCK DEVICE LONG_CLICK: ({x}, {y})")
        return True

    def swipe(self, direction, distance='medium'):
        """Mock swipe action."""
        action = {'type': 'swipe', 'direction': direction, 'distance': distance}
        self.actions.append(action)
        print(f"   📱 MOCK DEVICE SWIPE: {direction} ({distance})")
        return True

    def back(self):
        """Mock back button."""
        action = {'type': 'back'}
        self.actions.append(action)
        print(f"   📱 MOCK DEVICE BACK")
        return True

    def home(self):
        """Mock home button."""
        action = {'type': 'home'}
        self.actions.append(action)
        print(f"   📱 MOCK DEVICE HOME")
        return True

    def get_screenshot(self):
        """Get screenshot for current screen."""
        # Use cryptoapp screenshot for testing
        dataset_dir = Path("/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots")
        cryptoapp_dir = dataset_dir / "cryptoapp.apk"

        if cryptoapp_dir.exists():
            screenshot_files = list(cryptoapp_dir.glob("*.png"))
            if screenshot_files:
                return str(screenshot_files[0])

        return None

    def dump_ui_hierarchy(self):
        """Get UI hierarchy XML."""
        # Return minimal valid XML for testing
        return """<?xml version='1.0' encoding='UTF-8' standalone='yes' ?>
<hierarchy rotation="0">
  <node index="0" text="" resource-id="" class="android.widget.FrameLayout"
        package="br.unb.cic.cryptoapp" content-desc="" checkable="false"
        checked="false" clickable="false" enabled="true" focusable="false"
        focused="false" scrollable="false" long-clickable="false"
        password="false" selected="false" bounds="[0,0][1080,1920]">
    <node index="0" text="Input text" resource-id="br.unb.cic.cryptoapp:id/text_input"
          class="android.widget.EditText" bounds="[189,220][891,317]"
          clickable="true" enabled="true" focusable="true"/>
    <node index="1" text="ENCRYPT" resource-id="br.unb.cic.cryptoapp:id/encrypt_button"
          class="android.widget.Button" bounds="[100,500][300,600]"
          clickable="true" enabled="true" focusable="true"/>
  </node>
</hierarchy>"""


def test_integrated_json_parser():
    """Test RVAgent with integrated JSON parser."""

    print("=" * 80)
    print("🧪 TEST RVAGENT - Integrated JSON Parser")
    print("=" * 80)
    print()

    # Create mock device
    device = MockDevice()

    # Create agent configuration (minimal setup for testing)
    config = RVAgentConfig(
        package_name="br.unb.cic.cryptoapp",
        device_id="emulator-5554",
        results_dir="./test_output",
        max_iterations=5  # Minimum 5 iterations for testing
    )

    print(f"📋 Configuration:")
    print(f"   - Model: qwen-vision-tools-v2 (from rv_agent.py)")
    print(f"   - Max iterations: {config.max_iterations}")
    print(f"   - Package: {config.package_name}")
    print()

    # Create agent
    agent = RVAgent(config=config, device=device)

    print("🤖 RVAgent created successfully")
    print()

    print("=" * 80)
    print("🚀 STARTING EXPLORATION (5 iterations)")
    print("=" * 80)
    print()

    try:
        # Run exploration
        result = agent.run()

        print()
        print("=" * 80)
        print("📊 EXPLORATION RESULTS")
        print("=" * 80)
        print()

        print(f"✅ Exploration completed")
        print(f"   - Total iterations: {result.get('total_iterations', 0)}")
        print(f"   - Total actions: {len(device.actions)}")
        print()

        # Show executed actions
        print("📱 Actions executed by mock device:")
        for i, action in enumerate(device.actions, 1):
            print(f"   {i}. {action}")
        print()

        # Check if JSON parser was used
        if len(device.actions) > 0:
            print("✅ SUCCESS: Actions were executed (JSON parser working!)")
            return True
        else:
            print("❌ FAILURE: No actions executed")
            return False

    except Exception as e:
        print()
        print(f"❌ ERROR during exploration: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_integrated_json_parser()

    print()
    print("=" * 80)
    if success:
        print("✅ INTEGRATED JSON PARSER TEST PASSED")
    else:
        print("❌ INTEGRATED JSON PARSER TEST FAILED")
    print("=" * 80)

    exit(0 if success else 1)
