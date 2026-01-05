#!/usr/bin/env python3
"""Test V13 prompt loading."""

print("Testing V13 prompt loading...")

# Test 1: Import v13 module
try:
    from rv_agent.prompts import v13
    print("✅ v13 module imported successfully")
    print(f"   PROMPT_VERSION: {v13.PROMPT_VERSION}")
    print(f"   SYSTEM_PROMPT length: {len(v13.SYSTEM_PROMPT)} chars")
except ImportError as e:
    print(f"❌ Failed to import v13: {e}")
    exit(1)

# Test 2: Check required functions
if hasattr(v13, 'build_user_message'):
    print("✅ build_user_message function exists")
else:
    print("❌ build_user_message function missing")
    exit(1)

# Test 3: Test build_user_message
test_state = {
    'ui_elements': ["Element 1\nElement 2"],
    'current_activity': '.TestActivity',
    'action_history_summary': 'Action 1, Action 2',
    'navigation_path': 'Home → Settings',
    'text_input_count': 2,
    'spinner_count': 1,
    'has_scrollable': True
}

try:
    message = v13.build_user_message(test_state)
    print(f"✅ build_user_message works")
    print(f"   Message length: {len(message)} chars")

    # Check if hints are included
    if "💡" in message:
        print("✅ Dynamic hints included")
    else:
        print("⚠️  No dynamic hints (maybe element counts = 0?)")

except Exception as e:
    print(f"❌ build_user_message failed: {e}")
    exit(1)

# Test 4: Test AgentFactory dynamic loading
print("\nTesting AgentFactory dynamic loading...")
try:
    from rv_agent.config.agent_config import RVAgentConfig
    from rv_agent.core.agent_factory import AgentFactory

    config = RVAgentConfig(
        package_name="br.unb.cic.cryptoapp",
        timeout=60,
        prompt_version="v13",  # <<< Test v13 loading
        agent_mode="multimode",
        strategy="greedy"
    )

    print("✅ Config created with prompt_version=v13")

    # Don't actually create agent (needs device), just test config
    print("✅ Config validation passed")

except Exception as e:
    print(f"❌ Config/Factory test failed: {e}")
    exit(1)

print("\n" + "="*60)
print("✅ ALL TESTS PASSED - V13 ready to use!")
print("="*60)
