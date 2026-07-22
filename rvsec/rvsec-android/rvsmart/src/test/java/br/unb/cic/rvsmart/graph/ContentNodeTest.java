package br.unb.cic.rvsmart.graph;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class ContentNodeTest {

    @Test
    void testDefaultSaturationThresholdIs4() {
        ContentNode node = new ContentNode("hash1", "Activity1");
        node.setTotalActions(1);
        // Need 4 executions to saturate a normal action (with some successes to keep base threshold)
        node.recordAction("click@100,200", "Button");
        node.recordActionSuccess("click@100,200", true); // 1 success keeps rate <50% after 3+ execs
        node.recordAction("click@100,200", "Button");
        node.recordAction("click@100,200", "Button");
        assertTrue(node.getSaturationRate() < 1.0, "3 executions should not saturate with threshold=4");
        node.recordAction("click@100,200", "Button");
        assertEquals(1.0, node.getSaturationRate(), 0.01, "4 executions should saturate with threshold=4");
    }

    @Test
    void testMultiValueThresholdIs6() {
        ContentNode node = new ContentNode("hash1", "Activity1");
        node.setTotalActions(1);
        // EditText uses multi-value threshold of 6 (with some successes to keep base threshold)
        node.recordAction("set_text@100,200", "EditText");
        node.recordActionSuccess("set_text@100,200", true); // 1 success keeps rate <50% after 3+ execs
        for (int i = 1; i < 5; i++) {
            node.recordAction("set_text@100,200", "EditText");
        }
        assertTrue(node.getSaturationRate() < 1.0, "5 executions should not saturate EditText with threshold=6");
        node.recordAction("set_text@100,200", "EditText");
        assertEquals(1.0, node.getSaturationRate(), 0.01, "6 executions should saturate EditText with threshold=6");
    }

    @Test
    void testSaturationRateReturnsZeroForEmptyScreen() {
        ContentNode node = new ContentNode("hash1", "Activity1");
        node.setTotalActions(0);
        assertEquals(0.0f, node.getSaturationRate(), 0.01,
                "Empty screen (0 actions) should have saturation 0.0, not 1.0");
    }

    @Test
    void testAdaptiveThreshold_zeroSuccessesSaturatesAtHalfThreshold() {
        ContentNode node = new ContentNode("hash1", "Activity1");
        node.setTotalActions(1);
        // Default threshold is 4, half is 2
        node.recordAction("click@100,200", "Button");
        node.recordAction("click@100,200", "Button");
        assertTrue(node.isActionSaturated("click@100,200"),
                "Action with 0 successes should saturate at threshold/2 = 2");
    }

    @Test
    void testAdaptiveThreshold_highSuccessRateSaturatesAtOnePointFiveThreshold() {
        ContentNode node = new ContentNode("hash1", "Activity1");
        node.setTotalActions(1);
        // >50% success rate → threshold * 1.5 = 6
        for (int i = 0; i < 5; i++) {
            node.recordAction("click@100,200", "Button");
            node.recordActionSuccess("click@100,200", true);
        }
        assertFalse(node.isActionSaturated("click@100,200"),
                "Action with 100% success rate should not saturate at 5 (threshold=6)");
        node.recordAction("click@100,200", "Button");
        node.recordActionSuccess("click@100,200", true);
        assertTrue(node.isActionSaturated("click@100,200"),
                "Action with 100% success rate should saturate at 6 (threshold*1.5)");
    }

    @Test
    void testGetSuccessCount() {
        ContentNode node = new ContentNode("hash1", "Activity1");
        assertEquals(0, node.getSuccessCount("click@100,200"));
        node.recordAction("click@100,200", "Button");
        node.recordActionSuccess("click@100,200", true);
        assertEquals(1, node.getSuccessCount("click@100,200"));
        node.recordAction("click@100,200", "Button");
        node.recordActionSuccess("click@100,200", false);
        assertEquals(1, node.getSuccessCount("click@100,200"));
    }
}
