package br.unb.cic.rvsmart.core;

import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for dual hash semantics on ScreenState.
 *
 * Verifies that:
 * - contentHash changes when text/checkable changes while structHash stays the same.
 * - EditText text is excluded from contentHash.
 * - Text > 50 chars is trimmed in contentHash.
 * - Both hashes are 8 hex chars.
 */
class ScreenStateHashTest {

    /**
     * Non-interactive widget text (output-only TextViews) is excluded from contentHash.
     * A result TextView that shows dynamic output (e.g. cipher output) should not
     * cause a new content state on each ENCRYPT click.
     */
    @Test
    void testNonInteractiveWidgetTextExcludedFromContentHash() {
        // Non-interactive: clickable=false, scrollable=false, checkable=false, editable=false
        ScreenItem outputView1 = nonInteractiveItem("TextView", "pkg:id/result", "cipher_output_A");
        ScreenItem outputView2 = nonInteractiveItem("TextView", "pkg:id/result", "cipher_output_B");

        ScreenState state1 = new ScreenState(Collections.singletonList(outputView1), "Test");
        ScreenState state2 = new ScreenState(Collections.singletonList(outputView2), "Test");

        assertEquals(state1.getContentHash(), state2.getContentHash(),
                "Non-interactive widget text must be excluded from contentHash — "
                + "output-only TextViews should not create new content states");
    }

    /**
     * Changing text on an interactive (clickable) non-EditText widget changes contentHash
     * but not structHash.
     */
    @Test
    void testTextChangesContentHashNotStructHash() {
        ScreenItem item1 = item("TextView", "pkg:id/label", "Hello", false);
        ScreenItem item2 = item("TextView", "pkg:id/label", "Goodbye", false);

        ScreenState state1 = new ScreenState(Collections.singletonList(item1), "Test");
        ScreenState state2 = new ScreenState(Collections.singletonList(item2), "Test");

        assertNotEquals(state1.getContentHash(), state2.getContentHash(),
                "Different text should produce different contentHash");
        assertEquals(state1.getStructHash(), state2.getStructHash(),
                "Text change should NOT affect structHash");
    }

    /**
     * Changing checkable flag changes contentHash but not structHash.
     * (structHash includes the interactMask bitmask which contains checkable,
     * so this test specifically verifies contentHash includes the checkable field.)
     */
    @Test
    void testCheckableChangesContentHash() {
        ScreenItem checkable = itemCheckable("CheckBox", "pkg:id/cb", null, true);
        ScreenItem notCheckable = itemCheckable("CheckBox", "pkg:id/cb", null, false);

        ScreenState state1 = new ScreenState(Collections.singletonList(checkable), "Test");
        ScreenState state2 = new ScreenState(Collections.singletonList(notCheckable), "Test");

        assertNotEquals(state1.getContentHash(), state2.getContentHash(),
                "Checkable change should affect contentHash");
    }

    /**
     * EditText text is excluded from contentHash — two EditText items with
     * different text produce the same contentHash.
     */
    @Test
    void testEditTextTextExcludedFromContentHash() {
        ScreenItem editText1 = item("EditText", "pkg:id/input", "user typed abc", false);
        ScreenItem editText2 = item("EditText", "pkg:id/input", "user typed xyz", false);

        ScreenState state1 = new ScreenState(Collections.singletonList(editText1), "Test");
        ScreenState state2 = new ScreenState(Collections.singletonList(editText2), "Test");

        assertEquals(state1.getContentHash(), state2.getContentHash(),
                "EditText text should be excluded from contentHash");
    }

    /**
     * AppCompatEditText is also excluded (a common subclass).
     */
    @Test
    void testAppCompatEditTextExcludedFromContentHash() {
        ScreenItem e1 = item("AppCompatEditText", "pkg:id/input", "abc", false);
        ScreenItem e2 = item("AppCompatEditText", "pkg:id/input", "xyz", false);

        ScreenState state1 = new ScreenState(Collections.singletonList(e1), "Test");
        ScreenState state2 = new ScreenState(Collections.singletonList(e2), "Test");

        assertEquals(state1.getContentHash(), state2.getContentHash(),
                "AppCompatEditText text should be excluded from contentHash");
    }

    /**
     * Text longer than 50 chars is trimmed to 50 chars in contentHash.
     * Two items whose text shares the same first 50 chars produce the same contentHash.
     */
    @Test
    void testLongTextIsTrimmedTo50Chars() {
        String prefix = "This is exactly fifty characters of text here!!!50"; // 50 chars
        String text1 = prefix + "extra_suffix_A";
        String text2 = prefix + "extra_suffix_B";

        assertEquals(50, prefix.length(), "Prefix should be exactly 50 chars");

        ScreenItem item1 = item("TextView", "pkg:id/t", text1, false);
        ScreenItem item2 = item("TextView", "pkg:id/t", text2, false);

        ScreenState state1 = new ScreenState(Collections.singletonList(item1), "Test");
        ScreenState state2 = new ScreenState(Collections.singletonList(item2), "Test");

        assertEquals(state1.getContentHash(), state2.getContentHash(),
                "Text beyond 50 chars should be trimmed — same first 50 chars = same contentHash");
    }

    /**
     * Structural hash is NOT affected by text changes (same as former computeHash behavior).
     */
    @Test
    void testStructHashUnaffectedByText() {
        List<ScreenItem> items1 = Arrays.asList(
                item("Button", "pkg:id/ok", "Submit", false),
                item("TextView", "pkg:id/label", "Error: something went wrong", false)
        );
        List<ScreenItem> items2 = Arrays.asList(
                item("Button", "pkg:id/ok", "Cancel", false),
                item("TextView", "pkg:id/label", "All good", false)
        );

        ScreenState state1 = new ScreenState(items1, "FormActivity");
        ScreenState state2 = new ScreenState(items2, "FormActivity");

        assertEquals(state1.getStructHash(), state2.getStructHash(),
                "StructHash should ignore text differences");
        assertNotEquals(state1.getContentHash(), state2.getContentHash(),
                "ContentHash should differ when text differs");
    }

    /**
     * Both hashes are exactly 8 hex characters.
     */
    @Test
    void testBothHashesAre8HexChars() {
        ScreenState state = new ScreenState(Collections.singletonList(
                item("Button", "pkg:id/btn", "OK", false)), "Test");

        assertEquals(8, state.getContentHash().length(),
                "contentHash should be 8 chars");
        assertEquals(8, state.getStructHash().length(),
                "structHash should be 8 chars");
        assertTrue(state.getContentHash().matches("[0-9a-f]{8}"),
                "contentHash should be valid hex: " + state.getContentHash());
        assertTrue(state.getStructHash().matches("[0-9a-f]{8}"),
                "structHash should be valid hex: " + state.getStructHash());
    }

    /**
     * Content hash and struct hash may differ for the same widget set
     * (they encode different information).
     * Verify they are computed independently.
     */
    @Test
    void testContentHashAndStructHashAreIndependent() {
        // Widget with text — content and struct hashes use different fields
        ScreenItem widget = item("Button", "pkg:id/btn", "Click Me", false);
        ScreenState state = new ScreenState(Collections.singletonList(widget), "Test");

        // Both are valid 8-char hex — they are allowed to differ
        assertNotNull(state.getContentHash());
        assertNotNull(state.getStructHash());
        // (They may or may not be equal — no assertion on equality here,
        // just confirm both are produced without error)
    }

    // --- Helpers ---

    /**
     * Create a ScreenItem with text and enabled=true.
     *
     * @param editable whether this is an editable (EditText-like) widget
     */
    private ScreenItem item(String className, String resourceId, String text, boolean editable) {
        return new ScreenItem(className, resourceId, text, null, null,
                "pkg", true, false, false, true, false, editable, -1);
    }

    /**
     * Create a ScreenItem with configurable checkable flag.
     */
    private ScreenItem itemCheckable(String className, String resourceId,
                                     String text, boolean checkable) {
        return new ScreenItem(className, resourceId, text, null, null,
                "pkg", true, false, checkable, true, false, false, -1);
    }

    /**
     * Create a non-interactive ScreenItem (output-only display widget).
     * clickable=false, scrollable=false, checkable=false, editable=false.
     */
    private ScreenItem nonInteractiveItem(String className, String resourceId, String text) {
        return new ScreenItem(className, resourceId, text, null, null,
                "pkg", false, false, false, true, false, false, -1);
    }
}
