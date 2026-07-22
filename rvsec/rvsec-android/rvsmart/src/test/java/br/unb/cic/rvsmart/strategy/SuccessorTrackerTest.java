package br.unb.cic.rvsmart.strategy;

import br.unb.cic.rvsmart.output.RvTrack;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class SuccessorTrackerTest {

    private SuccessorTracker tracker;

    @BeforeEach
    void setUp() {
        RvTrack.logEnabled = false;
        tracker = new SuccessorTracker(6, 4);
    }

    @Test
    void testRecordAndGetParents() {
        tracker.record("parent_A", "child_1");
        tracker.record("parent_B", "child_1");
        tracker.record("parent_A", "child_2");

        assertEquals(2, tracker.getParents("child_1").size());
        assertTrue(tracker.getParents("child_1").contains("parent_A"));
        assertTrue(tracker.getParents("child_1").contains("parent_B"));
    }

    @Test
    void testRecordAndGetChildren() {
        tracker.record("parent_A", "child_1");
        tracker.record("parent_A", "child_2");

        assertEquals(2, tracker.getChildren("parent_A").size());
        assertTrue(tracker.getChildren("parent_A").contains("child_1"));
        assertTrue(tracker.getChildren("parent_A").contains("child_2"));
    }

    @Test
    void testGetParentsReturnsEmptySetForUnknownHash() {
        assertTrue(tracker.getParents("unknown").isEmpty());
    }

    @Test
    void testGetChildrenReturnsEmptySetForUnknownHash() {
        assertTrue(tracker.getChildren("unknown").isEmpty());
    }

    @Test
    void testReEnableLifecycle() {
        // Initially not re-enabled
        assertFalse(tracker.isReEnabled("hash_A"));

        // Re-enable it
        tracker.reEnable("hash_A");
        assertTrue(tracker.isReEnabled("hash_A"));

        // Consume once — still re-enabled (count was set to maxReEnables=6)
        tracker.consumeReEnable("hash_A");
        assertTrue(tracker.isReEnabled("hash_A"));

        // Consume down to 0
        for (int i = 0; i < 5; i++) {
            tracker.consumeReEnable("hash_A");
        }
        assertFalse(tracker.isReEnabled("hash_A"));
    }

    @Test
    void testConsumeReEnableOnNonReEnabledHashIsNoOp() {
        tracker.consumeReEnable("not_re_enabled");
        assertFalse(tracker.isReEnabled("not_re_enabled"));
    }

    @Test
    void testReEnableIsCappedAtMaxReEnables() {
        // Re-enabling multiple times should not exceed maxReEnables in total
        tracker.reEnable("hash_B");
        tracker.consumeReEnable("hash_B"); // count = 5
        tracker.reEnable("hash_B");        // resets to 6
        assertTrue(tracker.isReEnabled("hash_B"));
    }

    @Test
    void testWidgetSaturationBelowThreshold() {
        tracker.recordWidgetValue("hash_A", "click@100,200", "text1");
        tracker.recordWidgetValue("hash_A", "click@100,200", "text2");
        tracker.recordWidgetValue("hash_A", "click@100,200", "text3");
        // Threshold is 4 — 3 distinct values should not be saturated
        assertFalse(tracker.isWidgetSaturated("hash_A", "click@100,200"));
    }

    @Test
    void testWidgetSaturationAtThreshold() {
        tracker.recordWidgetValue("hash_A", "set_text:a@100,200", "val1");
        tracker.recordWidgetValue("hash_A", "set_text:a@100,200", "val2");
        tracker.recordWidgetValue("hash_A", "set_text:a@100,200", "val3");
        tracker.recordWidgetValue("hash_A", "set_text:a@100,200", "val4");
        // Exactly 4 distinct values — saturated
        assertTrue(tracker.isWidgetSaturated("hash_A", "set_text:a@100,200"));
    }

    @Test
    void testWidgetSaturationDeduplicatesValues() {
        tracker.recordWidgetValue("hash_A", "click@50,60", "same_value");
        tracker.recordWidgetValue("hash_A", "click@50,60", "same_value");
        tracker.recordWidgetValue("hash_A", "click@50,60", "same_value");
        tracker.recordWidgetValue("hash_A", "click@50,60", "same_value");
        // Same value 4 times = only 1 distinct value — not saturated
        assertFalse(tracker.isWidgetSaturated("hash_A", "click@50,60"));
    }

    @Test
    void testWidgetSaturationForUnknownHash() {
        assertFalse(tracker.isWidgetSaturated("unknown_hash", "click@100,200"));
    }

    @Test
    void testWidgetSaturationForUnknownWidget() {
        tracker.recordWidgetValue("hash_A", "click@100,200", "val1");
        assertFalse(tracker.isWidgetSaturated("hash_A", "click@999,999"));
    }
}
