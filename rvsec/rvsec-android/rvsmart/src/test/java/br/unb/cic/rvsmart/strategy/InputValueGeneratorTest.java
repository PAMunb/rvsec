package br.unb.cic.rvsmart.strategy;

import br.unb.cic.rvsmart.core.ScreenItem;
import br.unb.cic.rvsmart.output.RvTrack;
import br.unb.cic.rvsmart.staticdata.StaticMap;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.File;
import java.io.FileWriter;
import java.nio.file.Files;

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

    // --- Static fallback tests ---

    @Test
    void testStaticInputTypeFallbackToPhone() throws Exception {
        // Runtime inputType == 0, static data has inputType == 3 (phone)
        File tempFile = createInputTypeJson("et_phone", 3);
        try {
            StaticMap staticMap = new StaticMap(tempFile.getAbsolutePath());
            assertTrue(staticMap.isLoaded());
            generator.setStaticMap(staticMap);

            // Item with runtime inputType 0 but resourceId matching static data
            ScreenItem item = itemWithHint(null, "et_phone", 0);
            assertEquals("phone", generator.getCategory(item),
                    "Should fallback to static inputType 3 (phone) when runtime is 0");
        } finally {
            tempFile.delete();
        }
    }

    @Test
    void testStaticInputTypeFallbackToNumber() throws Exception {
        File tempFile = createInputTypeJson("et_amount", 2);
        try {
            StaticMap staticMap = new StaticMap(tempFile.getAbsolutePath());
            assertTrue(staticMap.isLoaded());
            generator.setStaticMap(staticMap);

            ScreenItem item = itemWithHint(null, "et_amount", 0);
            assertEquals("number", generator.getCategory(item),
                    "Should fallback to static inputType 2 (number) when runtime is 0");
        } finally {
            tempFile.delete();
        }
    }

    @Test
    void testRuntimeInputTypeTakesPriorityOverStatic() throws Exception {
        File tempFile = createInputTypeJson("et_input", 3);
        try {
            StaticMap staticMap = new StaticMap(tempFile.getAbsolutePath());
            assertTrue(staticMap.isLoaded());
            generator.setStaticMap(staticMap);

            // Runtime inputType 2 (number) should override static inputType 3 (phone)
            ScreenItem item = itemWithHint(null, "et_input", 2);
            assertEquals("number", generator.getCategory(item),
                    "Runtime inputType should take priority over static");
        } finally {
            tempFile.delete();
        }
    }

    @Test
    void testNoStaticFallbackWhenStaticMapIsNull() {
        // No staticMap set -> generic category (resourceId must not match any pattern keyword)
        ScreenItem item = itemWithHint(null, "et_widget", 0);
        assertEquals("generic", generator.getCategory(item),
                "Without static map, should return generic");
    }

    // --- Helpers ---

    private ScreenItem itemWithHint(String hint, String resourceId, int inputType) {
        return new ScreenItem("EditText", resourceId, null, null, null,
                "com.example", false, false, false, true, false, true,
                0, hint, inputType);
    }

    private File createInputTypeJson(String widgetId, int inputType) throws Exception {
        File tempFile = Files.createTempFile("input_gen_test", ".json").toFile();
        String json = "{"
                + "\"reachability\":[],"
                + "\"windows\":[{"
                + "\"id\":1,\"name\":\"com.example.FormActivity\","
                + "\"widgets\":[{"
                + "\"idName\":\"" + widgetId + "\","
                + "\"type\":\"EditText\","
                + "\"inputType\":" + inputType
                + "}]"
                + "}],"
                + "\"transitions\":[]"
                + "}";
        try (FileWriter writer = new FileWriter(tempFile)) {
            writer.write(json);
        }
        return tempFile;
    }
}
