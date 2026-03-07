package br.unb.cic.rvsmart.strategy;

import br.unb.cic.rvsmart.core.ScreenItem;
import br.unb.cic.rvsmart.output.RvTrack;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for InputValueGenerator — context-aware input value generation
 * with category detection and per-element value rotation.
 */
class InputValueGeneratorTest {

    private InputValueGenerator generator;

    @BeforeEach
    void setUp() {
        RvTrack.logEnabled = false;
        generator = new InputValueGenerator();
    }

    // --- Category detection tests ---

    @Test
    void testDetectsEmailByHint() {
        ScreenItem item = itemWithHint("Enter your email address", null, 0);
        assertEquals("email", generator.getCategory(item));
    }

    @Test
    void testDetectsEmailByResourceId() {
        ScreenItem item = itemWithHint(null, "com.example:id/email_field", 0);
        assertEquals("email", generator.getCategory(item));
    }

    @Test
    void testDetectsEmailCaseInsensitive() {
        ScreenItem item = itemWithHint("EMAIL Address", null, 0);
        assertEquals("email", generator.getCategory(item));
    }

    @Test
    void testDetectsPasswordByHint() {
        ScreenItem item = itemWithHint("Password", null, 0);
        assertEquals("password", generator.getCategory(item));
    }

    @Test
    void testDetectsPasswordByResourceIdWithPass() {
        ScreenItem item = itemWithHint(null, "id/pass_input", 0);
        assertEquals("password", generator.getCategory(item));
    }

    @Test
    void testDetectsNumberByInputType() {
        // inputType 2 = TYPE_CLASS_NUMBER
        ScreenItem item = itemWithHint(null, null, 2);
        assertEquals("number", generator.getCategory(item));
    }

    @Test
    void testDetectsNumberByHint() {
        ScreenItem item = itemWithHint("Enter amount", null, 0);
        assertEquals("number", generator.getCategory(item));
    }

    @Test
    void testDetectsPhoneByInputType() {
        // inputType 3 = TYPE_CLASS_PHONE
        ScreenItem item = itemWithHint(null, null, 3);
        assertEquals("phone", generator.getCategory(item));
    }

    @Test
    void testDetectsPhoneByHint() {
        ScreenItem item = itemWithHint("Phone number", null, 0);
        assertEquals("phone", generator.getCategory(item));
    }

    @Test
    void testDetectsUrlByHint() {
        ScreenItem item = itemWithHint("Enter URL", null, 0);
        assertEquals("url", generator.getCategory(item));
    }

    @Test
    void testDetectsUrlByResourceId() {
        ScreenItem item = itemWithHint(null, "id/website_input", 0);
        assertEquals("url", generator.getCategory(item));
    }

    @Test
    void testFallsBackToGeneric() {
        ScreenItem item = itemWithHint(null, null, 0);
        assertEquals("generic", generator.getCategory(item));
    }

    @Test
    void testFallsBackToGenericWithUnrelatedHint() {
        ScreenItem item = itemWithHint("Search here", "id/search_box", 0);
        assertEquals("generic", generator.getCategory(item));
    }

    // --- Value generation and rotation tests ---

    @Test
    void testGeneratesEmailValues() {
        ScreenItem item = itemWithHint("email", null, 0);
        assertEquals("test@test.com", generator.generateInput(item));
    }

    @Test
    void testRotatesThroughValuesOnRepeatedCalls() {
        ScreenItem item = itemWithHint("email", "id/email_field", 0);
        String first = generator.generateInput(item);
        String second = generator.generateInput(item);
        String third = generator.generateInput(item);

        assertEquals("test@test.com", first);
        assertEquals("user@example.org", second);
        assertEquals("a@b.c", third);
    }

    @Test
    void testRotationWrapsAround() {
        ScreenItem item = itemWithHint("email", "id/email_field", 0);
        // Email has 3 values; calling 4 times should wrap
        generator.generateInput(item); // test@test.com
        generator.generateInput(item); // user@example.org
        generator.generateInput(item); // a@b.c
        String fourth = generator.generateInput(item); // wraps to test@test.com
        assertEquals("test@test.com", fourth);
    }

    @Test
    void testDifferentElementsTrackSeparately() {
        ScreenItem item1 = itemWithHint("email", "id/email1", 0);
        ScreenItem item2 = itemWithHint("email", "id/email2", 0);

        // Both start at index 0
        assertEquals("test@test.com", generator.generateInput(item1));
        assertEquals("test@test.com", generator.generateInput(item2));

        // item1 advances to index 1, item2 stays at index 1
        assertEquals("user@example.org", generator.generateInput(item1));
        assertEquals("user@example.org", generator.generateInput(item2));
    }

    @Test
    void testGeneratesGenericValues() {
        ScreenItem item = itemWithHint(null, null, 0);
        assertEquals("test", generator.generateInput(item));
    }

    @Test
    void testGeneratesPasswordValues() {
        ScreenItem item = itemWithHint("password", null, 0);
        assertEquals("Test1234!", generator.generateInput(item));
    }

    // --- elementId tests ---

    @Test
    void testElementIdUsesResourceIdWhenPresent() {
        ScreenItem item = new ScreenItem("EditText", "pkg:id/input", null, null, null,
                "com.example", false, false, false, true, false, true, 0);
        assertEquals("res:pkg:id/input", InputValueGenerator.elementId(item));
    }

    @Test
    void testElementIdFallsBackToCoords() {
        // Bounds are null in test environment, so falls back to "coords:0,0"
        ScreenItem item = new ScreenItem("EditText", null, null, null, null,
                "com.example", false, false, false, true, false, true, 0);
        assertEquals("coords:0,0", InputValueGenerator.elementId(item));
    }

    // --- Input type priority over hint ---

    @Test
    void testInputTypeTakesPriorityOverHint() {
        // inputType=2 (NUMBER) should override hint containing "phone"
        ScreenItem item = itemWithHint("phone number", null, 2);
        assertEquals("number", generator.getCategory(item));
    }

    // --- Helpers ---

    private ScreenItem itemWithHint(String hint, String resourceId, int inputType) {
        return new ScreenItem("EditText", resourceId, null, null, null,
                "com.example", false, false, false, true, false, true,
                0, hint, inputType);
    }
}
