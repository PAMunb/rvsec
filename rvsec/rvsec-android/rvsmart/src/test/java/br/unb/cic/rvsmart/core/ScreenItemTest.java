package br.unb.cic.rvsmart.core;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class ScreenItemTest {

    @Test
    void testIsInteractiveReturnsTrueForLongClickableOnly() {
        ScreenItem item = new ScreenItem(
                "android.widget.ImageView", null, null, null,
                null, "com.example",
                false, false, false, true, true, false, 0);
        assertTrue(item.isInteractive(),
                "longClickable-only item should be interactive");
    }

    @Test
    void testIsInteractiveReturnsFalseForNonInteractive() {
        ScreenItem item = new ScreenItem(
                "android.widget.TextView", null, null, null,
                null, "com.example",
                false, false, false, true, false, false, 0);
        assertFalse(item.isInteractive(),
                "Non-interactive item should return false");
    }
}
