#!/usr/bin/env python3
"""Simple test to instrument a single APK and see the actual error."""

import os
import sys
from pathlib import Path

# Setup paths
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "modules" / "rv-android-core" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-instrumentation" / "src"))
sys.path.insert(0, str(project_root / "modules" / "rv-monitor-generator" / "src"))

from rv_android_core import constants
from rv_android_core.domain.app import App

# Set RVSEC_HOME
parent_directory = os.path.dirname(os.getcwd())
os.environ[constants.ENV_RVSEC_HOME] = parent_directory

# Setup logging
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import after setup
from rv_instrumentation.rvandroid import RVInstrumentation
from rv_instrumentation.config import RVInstrumentationConfig

# Configure instrumentation
config = RVInstrumentationConfig(
    working_dir=os.getcwd(),
    monitor_output_dir="./out/monitors",
    instrumented_dir="./out/instrumented_apks"
)

print("="*60)
print("Testing single APK instrumentation")
print("="*60)

# Create app object for a test APK
test_apk = "./apks/com.amnesica.kryptey_24.apk"
if not os.path.exists(test_apk):
    # Try another one
    test_apk = list(Path("./apks").glob("*.apk"))[0]

print(f"Testing with APK: {test_apk}")

app = App(
    name=os.path.basename(test_apk),
    path=test_apk
)

# Create instrumentation instance
rv_instrumentation = RVInstrumentation(config)

# Try to instrument
try:
    print(f"\nStarting instrumentation of {app.name}...")
    rv_instrumentation.instrument(
        app=app,
        result_dir=config.instrumented_dir,
        force_instrumentation=True
    )
    print(f"✅ Instrumentation successful!")
except Exception as e:
    print(f"\n❌ Instrumentation failed with error:")
    print(f"   Error type: {type(e).__name__}")
    print(f"   Error message: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
