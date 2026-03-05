package br.unb.cic.rvsmart.core;

import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Golden tests for structural hash equivalence with Python agent (INV-RSM-03).
 *
 * Reference hashes computed using Python agent's compute_screen_hash_from_description()
 * with json.dumps(sort_keys=True, separators=(",", ":")) + SHA-256[:12].
 *
 * To generate new reference hashes:
 *   cd modules/rv-agent
 *   python3 -c "
 *     import json, hashlib
 *     items = [{'class': '...', 'resource_id': '...', 'package': '...', ...}]
 *     items.sort(key=lambda x: (x['resource_id'] or 'zzz', x['class']))
 *     canonical = json.dumps({'activity': '...', 'items': items},
 *                            sort_keys=True, separators=(',', ':'))
 *     print(hashlib.sha256(canonical.encode()).hexdigest()[:12])
 *   "
 */
class ScreenStateTest {

    /**
     * CryptoApp MainActivity — 6 items captured from real PoC run on API 29.
     * Python reference: 5fcb1c0b4337
     */
    @Test
    void testCryptoAppMainActivityHash() {
        List<ScreenItem> items = Arrays.asList(
                item("FrameLayout", null, "br.unb.cic.cryptoapp",
                        false, false, false, true, false, false),
                item("TextView", null, "br.unb.cic.cryptoapp",
                        false, false, false, true, false, false),
                item("ImageView", null, "br.unb.cic.cryptoapp",
                        true, false, false, true, false, false),
                item("Button", "br.unb.cic.cryptoapp:id/buttonMessageDigest", "br.unb.cic.cryptoapp",
                        true, false, false, true, false, false),
                item("Button", "br.unb.cic.cryptoapp:id/buttonCipher", "br.unb.cic.cryptoapp",
                        true, false, false, true, false, false),
                item("Button", "br.unb.cic.cryptoapp:id/buttonGenerated", "br.unb.cic.cryptoapp",
                        true, false, false, true, false, false)
        );

        ScreenState state = new ScreenState(items, "MainActivity");
        assertEquals("5fcb1c0b4337", state.getHash());
    }

    /**
     * Empty screen — no items.
     * Python reference: 924e689d3b4e
     */
    @Test
    void testEmptyScreenHash() {
        ScreenState state = new ScreenState(Collections.<ScreenItem>emptyList(), "EmptyActivity");
        assertEquals("924e689d3b4e", state.getHash());
    }

    /**
     * Single EditText with resource ID.
     * Python reference: 00b4da4644e3
     */
    @Test
    void testSingleEditTextHash() {
        List<ScreenItem> items = Collections.singletonList(
                item("EditText", "com.example:id/input", "com.example",
                        true, false, false, true, false, true)
        );

        ScreenState state = new ScreenState(items, "FormActivity");
        assertEquals("00b4da4644e3", state.getHash());
    }

    /**
     * Verify that item order doesn't matter — hash sorts by (resource_id, class).
     */
    @Test
    void testOrderIndependence() {
        ScreenItem a = item("Button", "pkg:id/a", "pkg",
                true, false, false, true, false, false);
        ScreenItem b = item("TextView", null, "pkg",
                false, false, false, true, false, false);

        ScreenState state1 = new ScreenState(Arrays.asList(a, b), "Test");
        ScreenState state2 = new ScreenState(Arrays.asList(b, a), "Test");

        assertEquals(state1.getHash(), state2.getHash());
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

        assertNotEquals(state1.getHash(), state2.getHash());
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

        assertEquals(state1.getHash(), state2.getHash());
    }

    /**
     * Verify hash is exactly 12 characters.
     */
    @Test
    void testHashLength() {
        ScreenState state = new ScreenState(Collections.<ScreenItem>emptyList(), "Test");
        assertEquals(12, state.getHash().length());
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

    // --- Helper ---

    private ScreenItem item(String className, String resourceId, String packageName,
                            boolean clickable, boolean scrollable, boolean checkable,
                            boolean enabled, boolean longClickable, boolean editable) {
        return new ScreenItem(className, resourceId, null, null, null,
                packageName, clickable, scrollable, checkable, enabled,
                longClickable, editable, -1);
    }
}
