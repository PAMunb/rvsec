"""
Test RV-Agent on ar.rulosoft.mimanganu with all fixes applied.
Simple version that calls modules/rv-agent/example_usage.py directly.
"""

import subprocess
import sys

DEVICE_ID = "emulator-5554"
PACKAGE = "ar.rulosoft.mimanganu"
APK_PATH = "/home/pedro/desenvolvimento/RV_ANDROID/teste_llm/screenshots/ar.rulosoft.mimanganu_75.apk/ar.rulosoft.mimanganu_75.apk"
TIMEOUT = 60

print("=" * 80)
print("TEST: ar.rulosoft.mimanganu with ALL FIXES")
print("=" * 80)
print("Fixes applied:")
print("  ✅ ENTER key action (android_press_enter)")
print("  ✅ Enhanced scroll logging (INFO level)")
print("  ✅ Lowercase action type mappings")
print("=" * 80)

# Install app with permissions
print(f"Installing {PACKAGE}...")
subprocess.run(["adb", "-s", DEVICE_ID, "uninstall", PACKAGE], capture_output=True)
result = subprocess.run(
    ["adb", "-s", DEVICE_ID, "install", "-g", "-r", APK_PATH],
    capture_output=True,
    text=True
)

if result.returncode != 0:
    print(f"❌ Installation failed: {result.stderr}")
    sys.exit(1)

print(f"✅ Installed successfully")
print("=" * 80)

# Run test using example_usage.py
print(f"Starting test (timeout={TIMEOUT}s)...")
result = subprocess.run(
    [
        "poetry", "run", "python",
        "modules/rv-agent/example_usage.py",
        "--package", PACKAGE,
        "--device", DEVICE_ID,
        "--mode", "multimode",
        "--timeout", str(TIMEOUT)
    ],
    timeout=TIMEOUT + 30
)

print("=" * 80)
print("TEST COMPLETED")
print("=" * 80)
sys.exit(result.returncode)
