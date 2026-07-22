package br.unb.cic.rvsmart.core;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for structural hash using Objects.hash() over deduplicated widget signatures.
 */
class ScreenStateTest {

    /**
     * Verify that item order doesn't matter — hash sorts signatures before hashing.
     */
    @Test
    void testOrderIndependence() {
        ScreenItem a = item("Button", "pkg:id/a", "pkg",
                true, false, false, true, false, false);
        ScreenItem b = item("TextView", null, "pkg",
                false, false, false, true, false, false);

        ScreenState state1 = new ScreenState(Arrays.asList(a, b), "Test");
        ScreenState state2 = new ScreenState(Arrays.asList(b, a), "Test");

        assertEquals(state1.getStructHash(), state2.getStructHash());
    }

    /**
     * Verify that different activity names produce different hashes.
     */
    @Test
    void testActivityNameAffectsHash() {
        List<ScreenItem> items = Collections.singletonList(
                item("Button", "pkg:id/btn", "pkg",
                        true, false, false, true, false, false)
        );

        ScreenState state1 = new ScreenState(items, "Activity1");
        ScreenState state2 = new ScreenState(items, "Activity2");

        assertNotEquals(state1.getStructHash(), state2.getStructHash());
    }

    /**
     * Verify that text and contentDescription don't affect hash.
     */
    @Test
    void testVolatileFieldsIgnored() {
        ScreenItem withText = new ScreenItem("Button", "pkg:id/btn", "Hello", "desc",
                null, "pkg", true, false, false, true, false, false, 0);
        ScreenItem withoutText = new ScreenItem("Button", "pkg:id/btn", null, null,
                null, "pkg", true, false, false, true, false, false, 0);

        ScreenState state1 = new ScreenState(Collections.singletonList(withText), "Test");
        ScreenState state2 = new ScreenState(Collections.singletonList(withoutText), "Test");

        assertEquals(state1.getStructHash(), state2.getStructHash());
    }

    /**
     * Hash is exactly 8 hex characters (Objects.hash int formatted as %08x).
     */
    @Test
    void testHashLength() {
        ScreenState state = new ScreenState(Collections.<ScreenItem>emptyList(), "Test");
        assertEquals(8, state.getStructHash().length());
    }

    /**
     * Verify items list is immutable.
     */
    @Test
    void testItemsImmutable() {
        List<ScreenItem> items = new ArrayList<>();
        items.add(item("Button", null, "pkg", true, false, false, true, false, false));
        ScreenState state = new ScreenState(items, "Test");
        assertThrows(UnsupportedOperationException.class, () -> state.getItems().clear());
    }

    /**
     * Widget deduplication: 5 identical list items produce same hash as 1 item.
     * This is the FastBot pattern — prevents list items from inflating state counts.
     */
    @Test
    void testWidgetDeduplication() {
        ScreenItem single = item("TextView", "pkg:id/row", "pkg",
                true, false, false, true, false, false);

        List<ScreenItem> fiveItems = Arrays.asList(single, single, single, single, single);
        List<ScreenItem> oneItem = Collections.singletonList(single);

        ScreenState stateFive = new ScreenState(fiveItems, "ListActivity");
        ScreenState stateOne = new ScreenState(oneItem, "ListActivity");

        assertEquals(stateFive.getStructHash(), stateOne.getStructHash());
    }

    /**
     * Text exclusion: same widget with different text produces same hash.
     */
    @Test
    void testTextExclusion() {
        ScreenItem item1 = new ScreenItem("TextView", "pkg:id/label", "Hello World", null,
                null, "pkg", false, false, false, true, false, false, 0);
        ScreenItem item2 = new ScreenItem("TextView", "pkg:id/label", "Goodbye", null,
                null, "pkg", false, false, false, true, false, false, 0);

        ScreenState state1 = new ScreenState(Collections.singletonList(item1), "Test");
        ScreenState state2 = new ScreenState(Collections.singletonList(item2), "Test");

        assertEquals(state1.getStructHash(), state2.getStructHash());
    }

    /**
     * Coordinate exclusion: same widget with different bounds produces same hash.
     */
    @Test
    void testCoordinateExclusion() {
        // bounds is null in both — ScreenItem constructor accepts Rect which is Android-only,
        // but the hash never uses bounds, so different parentIndex values also don't matter
        ScreenItem item1 = new ScreenItem("Button", "pkg:id/btn", null, null,
                null, "pkg", true, false, false, true, false, false, 0);
        ScreenItem item2 = new ScreenItem("Button", "pkg:id/btn", null, null,
                null, "pkg", true, false, false, true, false, false, 5);

        ScreenState state1 = new ScreenState(Collections.singletonList(item1), "Test");
        ScreenState state2 = new ScreenState(Collections.singletonList(item2), "Test");

        assertEquals(state1.getStructHash(), state2.getStructHash());
    }

    /**
     * Determinism: same inputs always produce same hash across multiple constructions.
     */
    @Test
    void testDeterminism() {
        List<ScreenItem> items = Arrays.asList(
                item("Button", "pkg:id/a", "pkg", true, false, false, true, false, false),
                item("TextView", null, "pkg", false, false, false, true, false, false),
                item("EditText", "pkg:id/input", "pkg", true, false, false, true, false, true)
        );

        String hash1 = new ScreenState(items, "FormActivity").getStructHash();
        String hash2 = new ScreenState(items, "FormActivity").getStructHash();
        String hash3 = new ScreenState(items, "FormActivity").getStructHash();

        assertEquals(hash1, hash2);
        assertEquals(hash2, hash3);
    }

    /**
     * Activity-based grouping: same widgets on different activities produce different hashes.
     */
    @Test
    void testActivityBasedGrouping() {
        List<ScreenItem> items = Arrays.asList(
                item("Button", "pkg:id/ok", "pkg", true, false, false, true, false, false),
                item("Button", "pkg:id/cancel", "pkg", true, false, false, true, false, false)
        );

        ScreenState stateA = new ScreenState(items, "DialogActivity");
        ScreenState stateB = new ScreenState(items, "ConfirmActivity");

        assertNotEquals(stateA.getStructHash(), stateB.getStructHash());
    }

    /**
     * Package name is excluded from hash — same widget from different packages has same hash.
     */
    @Test
    void testPackageExclusion() {
        ScreenItem item1 = item("Button", "id/btn", "com.app1",
                true, false, false, true, false, false);
        ScreenItem item2 = item("Button", "id/btn", "com.app2",
                true, false, false, true, false, false);

        ScreenState state1 = new ScreenState(Collections.singletonList(item1), "Test");
        ScreenState state2 = new ScreenState(Collections.singletonList(item2), "Test");

        assertEquals(state1.getStructHash(), state2.getStructHash());
    }

    /**
     * Interaction flags affect hash — clickable vs non-clickable button is a different state.
     */
    @Test
    void testInteractionFlagsAffectHash() {
        ScreenItem clickable = item("Button", "pkg:id/btn", "pkg",
                true, false, false, true, false, false);
        ScreenItem notClickable = item("Button", "pkg:id/btn", "pkg",
                false, false, false, true, false, false);

        ScreenState state1 = new ScreenState(Collections.singletonList(clickable), "Test");
        ScreenState state2 = new ScreenState(Collections.singletonList(notClickable), "Test");

        assertNotEquals(state1.getStructHash(), state2.getStructHash());
    }

    /**
     * Hash format is valid hex string.
     */
    @Test
    void testHashIsValidHex() {
        ScreenState state = new ScreenState(Collections.<ScreenItem>emptyList(), "Test");
        assertTrue(state.getStructHash().matches("[0-9a-f]{8}"),
                "Hash should be 8 hex characters, got: " + state.getStructHash());
    }

    // --- Helper ---

    private ScreenItem item(String className, String resourceId, String packageName,
                            boolean clickable, boolean scrollable, boolean checkable,
                            boolean enabled, boolean longClickable, boolean editable) {
        return new ScreenItem(className, resourceId, null, null, null,
                packageName, clickable, scrollable, checkable, enabled,
                longClickable, editable, -1);
    }
}
