package br.unb.cic.rvsmart.core;

import br.unb.cic.rvsmart.output.RvTrack;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for UICoverageTracker — tracks per-screen element coverage
 * using hybrid element IDs (resourceId preferred, coords fallback).
 */
class UICoverageTrackerTest {

    private UICoverageTracker tracker;

    @BeforeEach
    void setUp() {
        RvTrack.logEnabled = false;
        tracker = new UICoverageTracker();
    }

    // --- Helper to create ScreenItem with resourceId (bounds=null in tests) ---

    private ScreenItem item(String className, String resourceId) {
        return new ScreenItem(className, resourceId, null, null, null,
                "pkg", true, false, false, true, false, false, 0);
    }

    private ScreenItem itemNoResId(String className) {
        return new ScreenItem(className, null, null, null, null,
                "pkg", true, false, false, true, false, false, 0);
    }

    // --- 1. Element registration with resourceId produces hybrid ID "res:{resourceId}" ---

    @Test
    void elementIdUsesResourceIdWhenPresent() {
        ScreenItem btn = item("Button", "pkg:id/btn1");
        String id = UICoverageTracker.elementId(btn);
        assertEquals("res:pkg:id/btn1", id);
    }

    // --- 2. Element registration without resourceId falls back ---

    @Test
    void elementIdFallsBackWhenNoResourceId() {
        ScreenItem noRes = itemNoResId("Button");
        String id = UICoverageTracker.elementId(noRes);
        // No resourceId AND null bounds → fallback to unknown:{hashCode}
        assertNotNull(id);
        assertTrue(id.startsWith("unknown:"), "Expected unknown: prefix, got: " + id);
    }

    @Test
    void elementIdWithEmptyResourceIdFallsBack() {
        ScreenItem emptyRes = new ScreenItem("Button", "", null, null, null,
                "pkg", true, false, false, true, false, false, 0);
        String id = UICoverageTracker.elementId(emptyRes);
        assertTrue(id.startsWith("unknown:"), "Expected unknown: prefix for empty resourceId, got: " + id);
    }

    // --- 3. Idempotent re-registration ---

    @Test
    void registerScreenElementsIsIdempotent() {
        List<ScreenItem> items = Arrays.asList(
                item("Button", "pkg:id/btn1"),
                item("EditText", "pkg:id/input1"),
                item("CheckBox", "pkg:id/chk1")
        );
        tracker.registerScreenElements("screen1", items);
        assertEquals(3, tracker.getTotalElements());

        // Re-register same screen with same items
        tracker.registerScreenElements("screen1", items);
        assertEquals(3, tracker.getTotalElements(), "Re-registration should not duplicate elements");
    }

    // --- 4. Coverage gap = 1.0 for unknown hash ---

    @Test
    void coverageGapIsOneForUnknownScreen() {
        assertEquals(1.0f, tracker.getCoverageGap("nonexistent"), 0.001f);
    }

    // --- 5. Coverage gap = 1.0 when no interactions ---

    @Test
    void coverageGapIsOneWhenNoInteractions() {
        List<ScreenItem> items = Arrays.asList(
                item("Button", "pkg:id/btn1"),
                item("Button", "pkg:id/btn2")
        );
        tracker.registerScreenElements("screen1", items);
        assertEquals(1.0f, tracker.getCoverageGap("screen1"), 0.001f);
    }

    // --- 6. Coverage gap decreases after interactions ---

    @Test
    void coverageGapDecreasesAfterInteractions() {
        List<ScreenItem> items = Arrays.asList(
                item("Button", "pkg:id/btn1"),
                item("Button", "pkg:id/btn2"),
                item("Button", "pkg:id/btn3"),
                item("Button", "pkg:id/btn4"),
                item("Button", "pkg:id/btn5"),
                item("Button", "pkg:id/btn6"),
                item("Button", "pkg:id/btn7"),
                item("Button", "pkg:id/btn8"),
                item("Button", "pkg:id/btn9"),
                item("Button", "pkg:id/btn10")
        );
        tracker.registerScreenElements("screen1", items);

        // Interact with 3 of 10 elements
        tracker.recordInteraction("screen1", "res:pkg:id/btn1");
        tracker.recordInteraction("screen1", "res:pkg:id/btn2");
        tracker.recordInteraction("screen1", "res:pkg:id/btn3");

        assertEquals(0.7f, tracker.getCoverageGap("screen1"), 0.001f);
    }

    // --- 7. Coverage gap = 0.0 when all elements tested ---

    @Test
    void coverageGapIsZeroWhenAllInteracted() {
        List<ScreenItem> items = Arrays.asList(
                item("Button", "pkg:id/btn1"),
                item("EditText", "pkg:id/input1")
        );
        tracker.registerScreenElements("screen1", items);

        tracker.recordInteraction("screen1", "res:pkg:id/btn1");
        tracker.recordInteraction("screen1", "res:pkg:id/input1");

        assertEquals(0.0f, tracker.getCoverageGap("screen1"), 0.001f);
    }

    // --- 8. Interaction recording increments count ---

    @Test
    void recordInteractionIncrementsCount() {
        List<ScreenItem> items = Collections.singletonList(
                item("Button", "pkg:id/btn1")
        );
        tracker.registerScreenElements("screen1", items);

        tracker.recordInteraction("screen1", "res:pkg:id/btn1");
        tracker.recordInteraction("screen1", "res:pkg:id/btn1");
        tracker.recordInteraction("screen1", "res:pkg:id/btn1");

        assertEquals(3, tracker.getTotalInteractions());
    }

    // --- 9. getTotalElements and getTotalInteractions ---

    @Test
    void totalElementsAndInteractionsAcrossScreens() {
        List<ScreenItem> screen1Items = Arrays.asList(
                item("Button", "pkg:id/btn1"),
                item("Button", "pkg:id/btn2")
        );
        List<ScreenItem> screen2Items = Arrays.asList(
                item("EditText", "pkg:id/input1"),
                item("CheckBox", "pkg:id/chk1"),
                item("Button", "pkg:id/btn3")
        );
        tracker.registerScreenElements("s1", screen1Items);
        tracker.registerScreenElements("s2", screen2Items);

        assertEquals(5, tracker.getTotalElements());
        assertEquals(0, tracker.getTotalInteractions());

        tracker.recordInteraction("s1", "res:pkg:id/btn1");
        tracker.recordInteraction("s2", "res:pkg:id/input1");
        assertEquals(2, tracker.getTotalInteractions());
    }
}
