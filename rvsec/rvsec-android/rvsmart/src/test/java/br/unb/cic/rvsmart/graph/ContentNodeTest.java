package br.unb.cic.rvsmart.graph;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class ContentNodeTest {

    @Test
    void testDefaultSaturationThresholdIs4() {
        ContentNode node = new ContentNode("hash1", "Activity1");
        node.setTotalActions(1);
        // Need 4 executions to saturate a normal action
        node.recordAction("click@100,200", "Button");
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
        // EditText uses multi-value threshold of 6
        for (int i = 0; i < 5; i++) {
            node.recordAction("set_text@100,200", "EditText");
        }
        assertTrue(node.getSaturationRate() < 1.0, "5 executions should not saturate EditText with threshold=6");
        node.recordAction("set_text@100,200", "EditText");
        assertEquals(1.0, node.getSaturationRate(), 0.01, "6 executions should saturate EditText with threshold=6");
    }
}
