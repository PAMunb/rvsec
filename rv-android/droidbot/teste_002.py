#!/usr/bin/env python3
"""
Manual test for DroidBot with RVAndroid policy integration.

This script tests DroidBot functionality with the RVAndroid policy
for standalone testing with a running RVAndroid LLM server.
"""

import json
import shutil
import os
import argparse
import sys
from pathlib import Path

# Setup paths to ensure DroidBot can be imported properly
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from droidbot.device import Device
from droidbot.app import App
from droidbot.device_state import DeviceState
from droidbot.input_event import CompoundEvent
from droidbot.rvandroid_policy import RVAndroidPolicy

HOST = "http://localhost:11434"
MODEL = "llama3.2:1b"
DEFAULT_SERVER_URL = "http://localhost:5000/api/get_actions"

# Parse command line arguments to enable selecting the strategy
def parse_args():
    parser = argparse.ArgumentParser(description='Test DroidBot with RVAndroid policy')
    parser.add_argument('--batch', action='store_true', help='Use batch action strategy')
    parser.add_argument('--server-url', default=DEFAULT_SERVER_URL, help='RVAndroid server URL')
    return parser.parse_args()


def execute(app_path, output_dir=None, use_batch_strategy=True, server_url=DEFAULT_SERVER_URL):
    print("🔧 Setting up device and app...")
    device = create_device(output_dir=output_dir)
    app = App(app_path, output_dir=output_dir)

    print(f"📡 Initializing RVAndroid policy with server: {server_url}")
    # Initialize policy with the specified server URL
    policy = RVAndroidPolicy(device, app, True, server_url=server_url)
    
    # Log strategy mode
    if use_batch_strategy:
        print("*" * 50)
        print("USING BATCH ACTION STRATEGY")
        print("*" * 50)
    else:
        print("*" * 50)
        print("USING SINGLE ACTION STRATEGY")
        print("*" * 50)

    cont = 1
    try:
        device.set_up()
        device.connect()
        
        # Enable show touches for better visualization
        device.adb.shell("settings put system show_touches 1")
        print("Show touches enabled")
        
        device.install_app(app)
        device.start_app(app)
        while (True):
            input("Press ENTER to continue...")
            state = device.get_current_state()
            print(f"state_str={state.state_str}")
            print(f"structure_str={state.structure_str}")
            
            event = policy.generate_event()
            print(f"Generated event: {event}")
            
            # Handle compound events for batch actions differently
            if isinstance(event, CompoundEvent):
                print(f"Executing batch of {len(event.events)} actions")
                
                # Execute each event in the compound event
                for i, sub_event in enumerate(event.events):
                    print(f"  Executing batch action {i+1}/{len(event.events)}: {sub_event}")
                    device.send_event(sub_event)
                    # Brief pause between batch actions for visibility
                    import time
                    time.sleep(1)
            else:
                # Send the event using device.send_event which works with all event types
                device.send_event(event)
            
            # Optional: Take a screenshot after execution
            # img_path = device.take_screenshot()
            # if img_path:
            #     print(f"Screenshot saved at: {img_path}")
            
            # Optional: Save state information for debugging
            # prefix = f"{cont:03}"
            # cont += 1
            # state_file = os.path.join(output_dir, prefix + ".state")
            # with open(state_file, "w") as arquivo:
            #     json.dump(create_message(state), arquivo, indent=3)
            
    except KeyboardInterrupt:
        print("Keyboard interrupt received, stopping execution.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error during execution: {e}")
    finally:
        device.disconnect()
        print("Device disconnected.")


def create_device(device_serial="emulator-5554",
                  is_emulator=True,
                  output_dir="/home/pedro/tmp",
                  cv_mode=False,
                  grant_perm=True,
                  enable_accessibility_hard=False,
                  humanoid=None,
                  ignore_ad=True):
    return Device(
        device_serial=device_serial,
        is_emulator=is_emulator,
        output_dir=output_dir,
        cv_mode=cv_mode,
        grant_perm=grant_perm,
        enable_accessibility_hard=enable_accessibility_hard,
        humanoid=humanoid,
        ignore_ad=ignore_ad)


def create_message(state: DeviceState):
    message = {
        "activity": state.foreground_activity,
        "stack": state.activity_stack,
        "screen_size": {
            "width": state.width,
            "height": state.height
        },
        "view_tree": state.view_tree
    }
    return message


if __name__ == "__main__":
    # Parse command line arguments
    args = parse_args()
    
    # Setup paths
    base_dir = "/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/out/instrumented_apks"
    out_dir = "/home/pedro/tmp/screenshots"
    apk_name = "cryptoapp.apk"
    apk_path = os.path.join(base_dir, apk_name)
    
    # Check if APK exists, try fallback locations
    if not os.path.exists(apk_path):
        fallback_paths = [
            f"../droidbot/resources/droidbotApp.apk",
            f"../droidbot/resources/DroidBoxTests.apk",
            f"droidbot/resources/droidbotApp.apk",
            f"droidbot/resources/DroidBoxTests.apk"
        ]
        
        for fallback in fallback_paths:
            fallback_path = os.path.join(project_root, fallback)
            if os.path.exists(fallback_path):
                apk_path = fallback_path
                print(f"Using fallback APK: {apk_path}")
                break
        else:
            print(f"❌ APK not found at {apk_path}")
            print("Available fallback locations:")
            for fallback in fallback_paths:
                full_path = os.path.join(project_root, fallback)
                exists = "✅" if os.path.exists(full_path) else "❌"
                print(f"  {exists} {full_path}")
            sys.exit(1)
    
    # Create output directory
    os.makedirs(out_dir, exist_ok=True)
    
    print(f"📱 Using APK: {apk_path}")
    print(f"📁 Output directory: {out_dir}")
    print(f"🌐 Server URL: {args.server_url}")
    print(f"📦 Batch mode: {args.batch}")
    print()
    print("🚀 Before running this script, make sure the RVAndroid server is running:")
    print("   python teste_rv_llm_server.py")
    print()
    
    # Run DroidBot with the appropriate strategy
    execute(apk_path, out_dir, use_batch_strategy=args.batch, server_url=args.server_url)