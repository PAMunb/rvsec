package br.unb.cic.rvsmart.core;

import org.junit.jupiter.api.Test;

import java.util.Collections;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for content-description inclusion in content hash (INV-RSM-47).
 * Verifies that contentDescription is included for interactive non-EditText widgets
 * and excluded for non-interactive widgets and EditText.
 */
class ScreenStateContentDescTest {

    @Test
    void testImageButtonDifferentContentDescProducesDifferentHash() {
        // Two ImageButtons with same className, resourceId, no text, but different content-desc
        ScreenItem btn1 = interactiveItemWithContentDesc("ImageButton", "pkg:id/icon", null, "Settings");
        ScreenItem btn2 = interactiveItemWithContentDesc("ImageButton", "pkg:id/icon", null, "Profile");

        ScreenState state1 = new ScreenState(Collections.singletonList(btn1), "Test");
        ScreenState state2 = new ScreenState(Collections.singletonList(btn2), "Test");

        assertNotEquals(state1.getContentHash(), state2.getContentHash(),
                "ImageButtons with different content-desc should produce different content hashes");
    }

    @Test
    void testNonInteractiveWidgetContentDescExcluded() {
        // Non-interactive TextView with different content-descriptions → same hash
        ScreenItem tv1 = nonInteractiveItemWithContentDesc("TextView", "pkg:id/balance", "Current balance: $42.50");
        ScreenItem tv2 = nonInteractiveItemWithContentDesc("TextView", "pkg:id/balance", "Current balance: $100.00");

        ScreenState state1 = new ScreenState(Collections.singletonList(tv1), "Test");
        ScreenState state2 = new ScreenState(Collections.singletonList(tv2), "Test");

        assertEquals(state1.getContentHash(), state2.getContentHash(),
                "Non-interactive widget content-desc should be excluded from content hash");
    }

    @Test
    void testNullContentDescTreatedAsEmpty() {
        ScreenItem withNull = interactiveItemWithContentDesc("ImageButton", "pkg:id/icon", null, null);
        ScreenItem withEmpty = interactiveItemWithContentDesc("ImageButton", "pkg:id/icon", null, "");

        ScreenState state1 = new ScreenState(Collections.singletonList(withNull), "Test");
        ScreenState state2 = new ScreenState(Collections.singletonList(withEmpty), "Test");

        assertEquals(state1.getContentHash(), state2.getContentHash(),
                "Null content-desc should be treated as empty string");
    }

    @Test
    void testEditTextContentDescExcluded() {
        ScreenItem et1 = editTextWithContentDesc("EditText", "pkg:id/input", "Search");
        ScreenItem et2 = editTextWithContentDesc("EditText", "pkg:id/input", "Enter text");

        ScreenState state1 = new ScreenState(Collections.singletonList(et1), "Test");
        ScreenState state2 = new ScreenState(Collections.singletonList(et2), "Test");

        assertEquals(state1.getContentHash(), state2.getContentHash(),
                "EditText content-desc should be excluded from content hash");
    }

    @Test
    void testContentDescTruncatedTo50Chars() {
        String prefix = "This is exactly fifty characters of text here!!!50"; // 50 chars
        String desc1 = prefix + "_suffix_A";
        String desc2 = prefix + "_suffix_B";

        ScreenItem item1 = interactiveItemWithContentDesc("ImageButton", "pkg:id/icon", null, desc1);
        ScreenItem item2 = interactiveItemWithContentDesc("ImageButton", "pkg:id/icon", null, desc2);

        ScreenState state1 = new ScreenState(Collections.singletonList(item1), "Test");
        ScreenState state2 = new ScreenState(Collections.singletonList(item2), "Test");

        assertEquals(state1.getContentHash(), state2.getContentHash(),
                "Content-desc beyond 50 chars should be trimmed — same first 50 = same hash");
    }

    @Test
    void testStructHashUnaffectedByContentDesc() {
        ScreenItem btn1 = interactiveItemWithContentDesc("ImageButton", "pkg:id/icon", null, "Settings");
        ScreenItem btn2 = interactiveItemWithContentDesc("ImageButton", "pkg:id/icon", null, "Profile");

        ScreenState state1 = new ScreenState(Collections.singletonList(btn1), "Test");
        ScreenState state2 = new ScreenState(Collections.singletonList(btn2), "Test");

        assertEquals(state1.getStructHash(), state2.getStructHash(),
                "Struct hash should not be affected by content-desc changes");
    }

    // --- Helpers ---

    private ScreenItem interactiveItemWithContentDesc(String className, String resourceId,
                                                       String text, String contentDesc) {
        return new ScreenItem(className, resourceId, text, contentDesc, null,
                "pkg", true, false, false, true, false, false, -1);
    }

    private ScreenItem nonInteractiveItemWithContentDesc(String className, String resourceId,
                                                          String contentDesc) {
        return new ScreenItem(className, resourceId, null, contentDesc, null,
                "pkg", false, false, false, true, false, false, -1);
    }

    private ScreenItem editTextWithContentDesc(String className, String resourceId,
                                                String contentDesc) {
        return new ScreenItem(className, resourceId, "typed text", contentDesc, null,
                "pkg", true, false, false, true, false, true, -1);
    }
}
