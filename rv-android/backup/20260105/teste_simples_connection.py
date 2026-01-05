#!/usr/bin/env python3
"""
Teste simples de conexão UIAutomator.
"""

import sys
from pathlib import Path

# Setup paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "modules" / "rv-android-core" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-uiautomator" / "src"))

from rv_uiautomator import UIAutomator2Adapter
import subprocess

def main():
    print("🔍 Testando conexão UIAutomator simples...")
    
    # Check emulator first
    try:
        result = subprocess.run(['adb', 'devices'], capture_output=True, text=True, timeout=10)
        print(f"ADB devices output:\n{result.stdout}")
        
        if 'emulator-5554' not in result.stdout:
            print("❌ Emulator not detected!")
            return 1
            
    except Exception as e:
        print(f"❌ ADB check failed: {e}")
        return 1
    
    # Test UIAutomator connection
    try:
        print("🔌 Creating UIAutomator2Adapter...")
        adapter = UIAutomator2Adapter("emulator-5554")
        
        print("📞 Attempting connection...")
        success = adapter.connect("emulator-5554")
        print(f"Connection result: {success}")
        
        if success:
            print("✅ Connection successful!")
            
            # Try to get state
            print("📋 Trying to get UI state...")
            state = adapter.get_ui_state()
            print(f"State keys: {list(state.keys()) if state else 'None'}")
            
            # Try screenshot
            print("📸 Trying screenshot...")
            screenshot_path = adapter.take_screenshot()
            print(f"Screenshot: {screenshot_path}")
            
        else:
            print("❌ Connection failed!")
            return 1
            
    except Exception as e:
        print(f"❌ UIAutomator test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("✅ Simple connection test completed!")
    return 0

if __name__ == "__main__":
    sys.exit(main())