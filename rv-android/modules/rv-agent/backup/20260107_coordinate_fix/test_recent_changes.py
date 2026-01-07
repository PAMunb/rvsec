#!/usr/bin/env python3
"""
Test recent changes: exceptions, configurable logging, and ActionNormalizer with LLM.
"""

import sys
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Disable verbose logging from libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def test_exceptions():
    """Test exception hierarchy imports and usage."""
    logger.info("=" * 60)
    logger.info("Test 1: Exception Hierarchy")
    logger.info("=" * 60)

    from rv_agent.domain.exceptions import (
        RVAgentError,
        DeviceError,
        LLMError,
        ValidationError,
    )

    # Test hierarchy
    assert issubclass(DeviceError, RVAgentError), "DeviceError should inherit from RVAgentError"
    assert issubclass(LLMError, RVAgentError), "LLMError should inherit from RVAgentError"
    assert issubclass(ValidationError, RVAgentError), "ValidationError should inherit from RVAgentError"

    # Test instantiation
    try:
        raise DeviceError("Test device error")
    except RVAgentError as e:
        logger.info(f"  DeviceError caught as RVAgentError: {e}")

    try:
        raise LLMError("Test LLM error")
    except RVAgentError as e:
        logger.info(f"  LLMError caught as RVAgentError: {e}")

    logger.info("  Exception hierarchy: OK")
    return True


def test_config_logging():
    """Test configurable logging settings."""
    logger.info("=" * 60)
    logger.info("Test 2: Configurable Logging")
    logger.info("=" * 60)

    import os
    from rv_agent.config.agent_config import RVAgentConfig

    # Test default values
    config = RVAgentConfig(package_name="test.app")
    assert config.log_level == "INFO", f"Expected INFO, got {config.log_level}"
    assert config.verbose_counters == False, f"Expected False, got {config.verbose_counters}"
    logger.info(f"  Default log_level: {config.log_level}")
    logger.info(f"  Default verbose_counters: {config.verbose_counters}")

    # Test get_log_level method
    log_level = config.get_log_level()
    assert log_level == logging.INFO, f"Expected {logging.INFO}, got {log_level}"
    logger.info(f"  get_log_level(): {log_level} (INFO={logging.INFO})")

    # Test get_verbose_counters method
    verbose = config.get_verbose_counters()
    assert verbose == False, f"Expected False, got {verbose}"
    logger.info(f"  get_verbose_counters(): {verbose}")

    # Test env var override (temporarily)
    os.environ["RVAGENT_LOG_LEVEL"] = "DEBUG"
    os.environ["RVAGENT_VERBOSE_COUNTERS"] = "1"

    log_level_override = config.get_log_level()
    verbose_override = config.get_verbose_counters()

    assert log_level_override == logging.DEBUG, f"Expected DEBUG, got {log_level_override}"
    assert verbose_override == True, f"Expected True, got {verbose_override}"
    logger.info(f"  With env override - log_level: {log_level_override} (DEBUG={logging.DEBUG})")
    logger.info(f"  With env override - verbose_counters: {verbose_override}")

    # Clean up env vars
    del os.environ["RVAGENT_LOG_LEVEL"]
    del os.environ["RVAGENT_VERBOSE_COUNTERS"]

    logger.info("  Configurable logging: OK")
    return True


def test_action_normalizer():
    """Test ActionNormalizer coordinate conversion."""
    logger.info("=" * 60)
    logger.info("Test 3: ActionNormalizer")
    logger.info("=" * 60)

    from rv_agent.domain.action import ActionNormalizer, TOOL_TO_ACTION

    normalizer = ActionNormalizer()

    # Test tool mapping
    logger.info(f"  Tool mappings: {len(TOOL_TO_ACTION)} tools")
    for tool, action in TOOL_TO_ACTION.items():
        logger.info(f"    {tool} -> {action}")

    # Test LLM action normalization with coordinate conversion
    llm_action = {
        "tool_name": "android_click",
        "tool_args": {"x": 352, "y": 624}  # Optimized coords (704x1248)
    }

    normalized = normalizer.from_llm(llm_action)

    assert normalized is not None, "Normalized action should not be None"
    assert normalized["action_type"] == "CLICK", f"Expected CLICK, got {normalized['action_type']}"
    assert normalized["source"] == "llm", f"Expected llm source, got {normalized['source']}"

    # Check coordinate conversion: (352, 624) in 704x1248 -> ~(540, 960) in 1080x1920
    expected_x = int(352 * (1080 / 704))  # ~540
    expected_y = int(624 * (1920 / 1248))  # ~960

    assert normalized["x"] == expected_x, f"Expected x={expected_x}, got {normalized['x']}"
    assert normalized["y"] == expected_y, f"Expected y={expected_y}, got {normalized['y']}"
    assert normalized["original_coords"] == (352, 624), f"Original coords mismatch"

    logger.info(f"  LLM action: {llm_action}")
    logger.info(f"  Normalized: action_type={normalized['action_type']}, coords=({normalized['x']}, {normalized['y']})")
    logger.info(f"  Coordinate conversion: ({352}, {624}) -> ({normalized['x']}, {normalized['y']})")
    logger.info(f"  Scale factors: x={normalizer.scale_x:.3f}, y={normalizer.scale_y:.3f}")

    # Test SET_TEXT action
    llm_text_action = {
        "tool_name": "android_type_text",
        "tool_args": {"x": 352, "y": 300, "text": "test@email.com"}
    }
    normalized_text = normalizer.from_llm(llm_text_action)
    assert normalized_text["action_type"] == "SET_TEXT"
    assert normalized_text["text"] == "test@email.com"
    logger.info(f"  SET_TEXT normalization: OK (text='{normalized_text['text']}')")

    # Test algorithm action normalization
    algo_action = {"action_type": "BACK", "x": 0, "y": 0}
    normalized_algo = normalizer.from_algorithm(algo_action)
    assert normalized_algo["source"] == "algorithm"
    logger.info(f"  Algorithm action: source={normalized_algo['source']}")

    logger.info("  ActionNormalizer: OK")
    return True


def test_llm_with_normalizer():
    """Test LLM client integration with ActionNormalizer."""
    logger.info("=" * 60)
    logger.info("Test 4: LLM + ActionNormalizer Integration")
    logger.info("=" * 60)

    from rv_agent.config.agent_config import RVAgentConfig
    from rv_agent.llm.llm_client import LLMClient
    from rv_agent.domain.action import ActionNormalizer
    from rv_agent.prompts import v12 as prompt_module
    from rv_screen_parser.parser.screen.visitor.model import ScreenDescription

    # Create config
    config = RVAgentConfig(
        package_name="test.package",
        agent_mode="multimode",
        llm_base_url="http://192.168.0.21:30000/v1"
    )

    # Initialize components
    client = LLMClient(config, prompt_module)
    normalizer = ActionNormalizer()

    # Create mock screen
    screen_desc = ScreenDescription(activity="com.test.MainActivity", items=[])

    # Minimal base64 PNG (1x1 pixel)
    screenshot_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

    ui_text = """
    UI Elements (optimized 704x1248):
    1. [Button] "Login" at (352, 800) - clickable
    2. [EditText] "Username" at (352, 400) - editable
    3. [EditText] "Password" at (352, 550) - editable
    """

    logger.info("  Calling LLM...")
    start = time.perf_counter()

    result = client.generate_action(
        screen_description=screen_desc,
        screenshot_b64=screenshot_b64,
        ui_elements_text=ui_text,
        iteration=1,
        last_action_summary="App started"
    )

    elapsed = time.perf_counter() - start
    logger.info(f"  LLM response in {elapsed:.2f}s")
    logger.info(f"  Success: {result.get('success')}")
    logger.info(f"  Parser strategy: {result.get('parser_strategy')}")

    response = result.get("response")
    if not response:
        logger.error("  No response from LLM!")
        return False

    # Extract tool calls
    tool_calls = getattr(response, "tool_calls", []) or []
    logger.info(f"  Tool calls: {len(tool_calls)}")

    if not tool_calls:
        logger.warning("  No tool calls - checking content for fallback parsing")
        if response.content:
            logger.info(f"  Content preview: {response.content[:200]}...")
        return False

    # Convert first tool call using ActionNormalizer
    first_tool = tool_calls[0]
    llm_action = {
        "tool_name": first_tool.get("name", ""),
        "tool_args": first_tool.get("args", {})
    }

    logger.info(f"  Raw tool call: {llm_action}")

    normalized = normalizer.from_llm(llm_action)

    if normalized:
        logger.info(f"  Normalized action:")
        logger.info(f"    action_type: {normalized['action_type']}")
        logger.info(f"    coords: ({normalized['x']}, {normalized['y']})")
        logger.info(f"    text: '{normalized.get('text', '')}'")
        logger.info(f"    source: {normalized['source']}")
        logger.info(f"    original_coords: {normalized.get('original_coords')}")
        logger.info("  LLM + ActionNormalizer: OK")
        return True
    else:
        logger.error(f"  Failed to normalize action: {llm_action}")
        return False


if __name__ == "__main__":
    results = {}

    # Test 1: Exceptions
    try:
        results["exceptions"] = test_exceptions()
    except Exception as e:
        logger.error(f"Test 1 failed: {e}")
        results["exceptions"] = False

    # Test 2: Config logging
    try:
        results["config_logging"] = test_config_logging()
    except Exception as e:
        logger.error(f"Test 2 failed: {e}")
        results["config_logging"] = False

    # Test 3: ActionNormalizer
    try:
        results["action_normalizer"] = test_action_normalizer()
    except Exception as e:
        logger.error(f"Test 3 failed: {e}")
        results["action_normalizer"] = False

    # Test 4: LLM + Normalizer (requires SGLang server)
    try:
        results["llm_normalizer"] = test_llm_with_normalizer()
    except Exception as e:
        logger.error(f"Test 4 failed: {e}")
        results["llm_normalizer"] = False

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)

    all_passed = True
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        logger.info(f"  {test_name}: {status}")
        if not passed:
            all_passed = False

    logger.info("=" * 60)
    logger.info(f"Overall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")

    sys.exit(0 if all_passed else 1)
