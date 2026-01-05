"""
Test ScreenProcessor instantiation in isolation.
"""

import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_screen_processor_instantiation():
    """Test that ScreenProcessor can be instantiated correctly."""
    logger.info("=" * 80)
    logger.info("TEST: ScreenProcessor Instantiation")
    logger.info("=" * 80)

    try:
        from rv_agent.ui.screen_processor import ScreenProcessor
        from rv_agent.core.device_interface import DeviceInterface
        from rv_agent.core.dynamic_state_graph import DynamicStateGraph

        logger.info("Creating DeviceInterface...")
        device = DeviceInterface(device_id="emulator-5554")
        logger.info("✅ DeviceInterface created")

        logger.info("Creating DynamicStateGraph...")
        dynamic_graph = DynamicStateGraph()
        logger.info("✅ DynamicStateGraph created")

        logger.info("Creating ScreenProcessor...")
        screen_processor = ScreenProcessor(
            device=device,
            dynamic_graph=dynamic_graph,
            static_data=None,
            device_dimensions=(1080, 1920),
            optimized_dimensions=(704, 1248),
            max_external_attempts=3
        )
        logger.info("✅ ScreenProcessor created successfully!")

        # Verify parser was created
        logger.info(f"Parser type: {type(screen_processor.parser).__name__}")
        logger.info(f"Parser: {screen_processor.parser}")

        logger.info("=" * 80)
        logger.info("✅ TEST PASSED - ScreenProcessor instantiation working!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ TEST FAILED: {e}", exc_info=True)

if __name__ == "__main__":
    test_screen_processor_instantiation()
