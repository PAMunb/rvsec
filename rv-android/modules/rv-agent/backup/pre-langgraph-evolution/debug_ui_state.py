"""
Debug UI state structure to understand coordinate extraction.
"""
import sys
from pathlib import Path

# Add path for direct import during development
sys.path.insert(0, str(Path(__file__).parent / "src"))

from rv_agent.core.device_adapter import DeviceInterface

def debug_ui_state():
    """Debug UI state structure."""

    print("🔍 DEBUGGING: UI State Structure")
    print("=" * 50)

    try:
        device = DeviceInterface()
        connected = device.connect_to_device()
        if not connected:
            print("❌ Failed to connect")
            return

        launched = device.launch_app("br.unb.cic.cryptoapp")
        if not launched:
            print("❌ Failed to launch app")
            return

        ui_state = device.get_current_ui_state()

        print(f"UI State keys: {list(ui_state.keys())}")
        print(f"Element count: {ui_state.get('element_count', 0)}")

        clickable_elements = ui_state.get('clickable_elements', [])
        print(f"Clickable elements count: {len(clickable_elements)}")

        if clickable_elements:
            print("\nFirst element structure:")
            first_element = clickable_elements[0]
            print(f"Keys: {list(first_element.keys())}")
            for key, value in first_element.items():
                if isinstance(value, str) and len(value) > 100:
                    print(f"{key}: {str(value)[:100]}...")
                else:
                    print(f"{key}: {value}")

        print("\nFormatted elements sample:")
        formatted = ui_state.get('formatted_elements', '')
        print(formatted[:500] + "..." if len(formatted) > 500 else formatted)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_ui_state()