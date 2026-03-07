package br.unb.cic.rvsmart.core;

import br.unb.cic.rvsmart.output.RvTrack;
import br.unb.cic.rvsmart.strategy.ActionSelector;
import br.unb.cic.rvsmart.strategy.InputValueGenerator;
import br.unb.cic.rvsmart.strategy.PlateauDetector;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.Collections;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for AgentLoop utility methods and component integration.
 * Full loop testing requires Android runtime — these test extracted logic
 * and component wiring at the unit level.
 */
class AgentLoopTest {

    @BeforeEach
    void setUp() {
        RvTrack.logEnabled = false;
    }

    // --- LLM coordinate boundary protection (task 4.5) ---

    @Test
    void testStatusBarYCoordinateIsInBoundaryZone() {
        assertTrue(AgentLoop.isInBoundaryZone(50, 1920),
                "Y=50 should be in status bar boundary (top 5% of 1920)");
    }

    @Test
    void testNavBarYCoordinateIsInBoundaryZone() {
        assertTrue(AgentLoop.isInBoundaryZone(1850, 1920),
                "Y=1850 should be in nav bar boundary (bottom 6% of 1920)");
    }

    @Test
    void testValidYCoordinateIsNotInBoundaryZone() {
        assertFalse(AgentLoop.isInBoundaryZone(500, 1920),
                "Y=500 should not be in boundary zone");
    }

    @Test
    void testBoundaryEdgeCasesStatusBar() {
        assertTrue(AgentLoop.isInBoundaryZone(95, 1920),
                "Y=95 should be in status bar (< 96)");
        assertFalse(AgentLoop.isInBoundaryZone(96, 1920),
                "Y=96 should NOT be in status bar (>= 96)");
    }

    @Test
    void testBoundaryEdgeCasesNavBar() {
        assertTrue(AgentLoop.isInBoundaryZone(1805, 1920),
                "Y=1805 should be in nav bar (> 1804.8)");
        assertFalse(AgentLoop.isInBoundaryZone(1804, 1920),
                "Y=1804 should NOT be in nav bar (<= 1804.8)");
    }

    // --- Integration tests (task 5.3) ---

    @Test
    void testUICoverageTrackerGapDecreasesAfterInteractions() {
        UICoverageTracker tracker = new UICoverageTracker();
        ScreenItem item1 = new ScreenItem("Button", "pkg:id/btn1", null, null, null,
                "com.example", true, false, false, true, false, false, 0);
        ScreenItem item2 = new ScreenItem("Button", "pkg:id/btn2", null, null, null,
                "com.example", true, false, false, true, false, false, 0);

        tracker.registerScreenElements("hash1", Arrays.asList(item1, item2));
        float gapBefore = tracker.getCoverageGap("hash1");
        assertEquals(1.0f, gapBefore, 0.01f, "Full gap before any interaction");

        tracker.recordInteraction("hash1", "res:pkg:id/btn1");
        float gapAfter = tracker.getCoverageGap("hash1");
        assertEquals(0.5f, gapAfter, 0.01f, "Half gap after one of two interactions");
    }

    @Test
    void testPlateauBoostsStochasticInActionSelector() {
        Config config = Config.defaults();
        config.setSeed(42);
        PlateauDetector detector = new PlateauDetector();
        ActionSelector selector = new ActionSelector(config);

        // No plateau initially
        assertFalse(detector.isPlateauDetected());
        assertFalse(selector.isPlateauActive());

        // Simulate 10 no-progress iterations to trigger plateau
        for (int i = 0; i < 10; i++) {
            detector.recordIteration(false, false);
        }
        assertTrue(detector.isPlateauDetected());

        // Wire plateau state to selector (as AgentLoop does)
        selector.setPlateauActive(detector.isPlateauDetected());
        assertTrue(selector.isPlateauActive());

        // New screen clears plateau
        detector.recordIteration(true, false);
        assertFalse(detector.isPlateauDetected());
        selector.setPlateauActive(detector.isPlateauDetected());
        assertFalse(selector.isPlateauActive());
    }

    @Test
    void testInputValueGeneratorContextAwareValues() {
        InputValueGenerator gen = new InputValueGenerator();

        // Email field
        ScreenItem emailItem = new ScreenItem("EditText", "id/email", null, null, null,
                "com.example", false, false, false, true, false, true,
                0, "email address", 0);
        String emailValue = gen.generateInput(emailItem);
        assertEquals("test@test.com", emailValue, "Email field should get email value");

        // Password field
        ScreenItem passItem = new ScreenItem("EditText", "id/password", null, null, null,
                "com.example", false, false, false, true, false, true,
                0, "enter password", 0);
        String passValue = gen.generateInput(passItem);
        assertEquals("Test1234!", passValue, "Password field should get password value");

        // Generic field
        ScreenItem genericItem = new ScreenItem("EditText", "id/search", null, null, null,
                "com.example", false, false, false, true, false, true,
                0, "search", 0);
        String genericValue = gen.generateInput(genericItem);
        assertEquals("test", genericValue, "Generic field should get 'test' value");
    }
}
