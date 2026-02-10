#!/usr/bin/env python3
"""
Manual test script for RVAndroidPolicy direct integration.

This script provides a simple and elegant way to test the RVAndroidPolicy
directly, simulating a normal DroidBot execution but with manual control
(press ENTER to proceed with each action).

The script focuses on testing the policy's communication with the RVAndroid
server and observing the LLM-driven action generation process.
"""

import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

# Setup paths to ensure DroidBot can be imported properly
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from droidbot.device import Device
from droidbot.app import App
from droidbot.device_state import DeviceState
from droidbot.input_event import InputEvent, KeyEvent
from droidbot.rvandroid_policy import RVAndroidPolicy

# === HARDCODED CONFIGURATIONS ===
SERVER_URL = "http://localhost:5000/api/get_actions"
DEVICE_SERIAL = "emulator-5554"
APK_PATH = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/apks_examples/cryptoapp.apk"
OUTPUT_DIR = "/home/pedro/tmp/teste_003"


def setup_logging():
    """Configure logging for clear output."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    # Suppress noisy logs
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)

def find_apk_path() -> str:
    """Find a valid APK path from the hardcoded options."""
    # Try path first
    if os.path.exists(APK_PATH):
        return APK_PATH
    
    print(f"❌ APK not found: {APK_PATH}")
   
    raise FileNotFoundError("No valid APK found in any of the configured paths")

def create_device() -> Device:
    """Create and configure a DroidBot device."""
    print("🔧 Creating device...")
    return Device(
        device_serial=DEVICE_SERIAL,
        is_emulator=True,
        output_dir=OUTPUT_DIR,
        cv_mode=False,
        grant_perm=True,
        enable_accessibility_hard=False,
        humanoid=None,
        ignore_ad=True
    )

def print_state_info(state: DeviceState, action_count: int):
    """Print relevant information about the current state."""
    print(f"\n{'='*60}")
    print(f"📱 ACTION #{action_count}")
    print(f"📱 Activity: {state.foreground_activity or 'Unknown'}")
    print(f"📱 Views count: {len(state.views) if state.views else 0}")
    print(f"📱 State ID: {state.state_str[:20]}..." if state.state_str else "N/A")
    
    # Show some view information if available
    if state.views:
        clickable_views = [v for v in state.views if v.get('clickable', False)]
        print(f"📱 Clickable views: {len(clickable_views)}")
        
        # Show a few examples of interactive elements
        examples = []
        for view in clickable_views[:3]:
            view_text = view.get('text', '')
            view_class = view.get('class', '').split('.')[-1] if view.get('class') else 'Unknown'
            if view_text:
                examples.append(f"{view_class}('{view_text[:20]}')")
            else:
                examples.append(f"{view_class}")
        
        if examples:
            print(f"📱 Example elements: {', '.join(examples)}")
    
    print(f"{'='*60}")

def print_event_info(event: Optional[InputEvent], is_fallback: bool = False):
    """Print information about the generated event."""
    if event is None:
        print("⚠️  No event generated")
        return
    
    event_type = type(event).__name__
    policy_source = "🤖 LLM Policy" if not is_fallback else "🔄 Fallback Policy"
    
    print(f"\n{policy_source} generated: {event_type}")
    
    # Add specific details based on event type
    if hasattr(event, 'view') and event.view:
        view_info = event.view.get('text', '') or event.view.get('resource_id', '') or "Unknown view"
        print(f"   Target: {view_info}")
    elif hasattr(event, 'x') and hasattr(event, 'y'):
        print(f"   Coordinates: ({event.x}, {event.y})")
    
    if hasattr(event, 'text') and event.text:
        print(f"   Text: '{event.text}'")
    
    print(f"   Event details: {event}")

def execute_manual_test():
    """Main execution function with manual control."""
    print("🚀 Starting Manual RVAndroid Policy Test")
    print("=" * 60)
    print("📋 Configuration:")
    print(f"   Server: {SERVER_URL}")
    print(f"   Device: {DEVICE_SERIAL}")
    print(f"   Output: {OUTPUT_DIR}")
    print("=" * 60)
    print()
    print("⚠️  IMPORTANT: Make sure the RVAndroid server is running!")
    print("   Command: python teste_rv_llm_server.py")
    print()
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    try:
        # Find and verify APK
        apk_path = find_apk_path()
        print(f"📱 Using APK: {apk_path}")
        
        # Initialize components
        device = create_device()
        app = App(apk_path, output_dir=OUTPUT_DIR)
        # Enable screenshots for testing multimodal capabilities  
        policy = RVAndroidPolicy(device, app, random_input=True, server_url=SERVER_URL, include_screenshots=True)
        
        print("\n🔌 Setting up device...")
        device.set_up()
        device.connect()
        
        # Enable show touches for better visualization
        device.adb.shell("settings put system show_touches 1")
        print("👆 Show touches enabled")
        
        # Install and start app
        print("📦 Installing app...")
        device.install_app(app)
        print("▶️  Starting app...")
        device.start_app(app)
        
        print("\n🎮 Manual testing mode activated!")
        print("Press ENTER to generate and execute each action...")
        print("Press Ctrl+C to exit")
        print()
        
        action_count = 0
        consecutive_fallbacks = 0
        
        while True:
            try:
                # Wait for user input
                input("⏸️  Press ENTER to continue...")
                action_count += 1
                
                # Get current state
                print("📸 Capturing device state...")
                current_state = device.get_current_state()
                
                if current_state is None:
                    print("❌ Could not capture device state!")
                    continue
                
                # Display state information
                print_state_info(current_state, action_count)
                
                # Generate event using policy
                print("🧠 Asking RVAndroid policy for next action...")
                start_time = time.time()
                
                event = policy.generate_event()
                
                generation_time = time.time() - start_time
                print(f"⏱️  Action generation took {generation_time:.2f}s")
                
                # Check if this was a fallback (we can infer this from policy state)
                is_fallback = policy.consecutive_errors > 0
                
                # Display event information
                print_event_info(event, is_fallback)
                
                if is_fallback:
                    consecutive_fallbacks += 1
                    print(f"⚠️  Consecutive fallbacks: {consecutive_fallbacks}")
                else:
                    consecutive_fallbacks = 0
                
                if event is None:
                    print("⚠️  No action to execute, continuing...")
                    continue
                
                # Execute the event
                print("⚡ Executing action...")
                device.send_event(event)
                
                print("✅ Action executed successfully!")
                
                # Brief pause for better visualization
                time.sleep(1)
                
            except KeyboardInterrupt:
                print("\n👋 User requested exit")
                break
            except Exception as e:
                print(f"\n❌ Error during execution: {e}")
                print("Continuing with next iteration...")
                import traceback
                traceback.print_exc()
                continue
        
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return 1
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Cleanup
        try:
            if 'device' in locals():
                print("\n🔌 Disconnecting device...")
                device.disconnect()
                print("✅ Device disconnected")
        except Exception as e:
            print(f"⚠️  Error during cleanup: {e}")
    
    print("\n🏁 Test completed!")
    return 0

if __name__ == "__main__":
    setup_logging()
    exit_code = execute_manual_test()
    sys.exit(exit_code)