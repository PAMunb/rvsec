package br.unb.cic.rvsmart.llm;

import br.unb.cic.rvsmart.core.Config.PromptVersion;
import br.unb.cic.rvsmart.core.ScreenItem;
import br.unb.cic.rvsmart.output.RvTrack;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for PromptBuilder — verifies message structure and content inclusion.
 *
 * ScreenItem bounds are null to avoid android.graphics.Rect (not available in JUnit).
 * The builder handles null bounds gracefully by omitting coordinate information.
 */
class PromptBuilderTest {

    private PromptBuilder builder;

    @BeforeEach
    void setUp() {
        RvTrack.logEnabled = false;
        builder = new PromptBuilder();
    }

    // -------------------------------------------------------------------------
    // Helpers
    // -------------------------------------------------------------------------

    private PromptContext baseContext(String activity) {
        return PromptContext.builder()
                .base64Screenshot("abc123")
                .currentActivity(activity)
                .build();
    }

    private String getUserTextContent(SglangClient.Message userMessage) {
        if (userMessage.getContentParts() == null) {
            return userMessage.getTextContent() != null ? userMessage.getTextContent() : "";
        }
        StringBuilder sb = new StringBuilder();
        for (SglangClient.ContentPart part : userMessage.getContentParts()) {
            if ("text".equals(part.getType()) && part.getText() != null) {
                sb.append(part.getText());
            }
        }
        return sb.toString();
    }

    // -------------------------------------------------------------------------
    // PromptContext builder tests (task 2.5)
    // -------------------------------------------------------------------------

    @Test
    void testPromptContextBuilderSetsBaseFields() {
        Set<String> visited = new HashSet<>(Arrays.asList("MainActivity"));
        PromptContext ctx = PromptContext.builder()
                .base64Screenshot("img123")
                .currentActivity("com.example.MainActivity")
                .navigationHint("Go to Settings")
                .visitedActivities(visited)
                .iterationNumber(42)
                .build();

        assertEquals("img123", ctx.getBase64Screenshot());
        assertEquals("com.example.MainActivity", ctx.getCurrentActivity());
        assertEquals("Go to Settings", ctx.getNavigationHint());
        assertTrue(ctx.getVisitedActivities().contains("MainActivity"));
        assertEquals(42, ctx.getIterationNumber());
    }

    @Test
    void testPromptContextV17FieldsNullByDefault() {
        PromptContext ctx = PromptContext.builder()
                .base64Screenshot("img")
                .currentActivity("com.example.MainActivity")
                .build();

        assertNull(ctx.getElementInteractionCounts(), "V17 field must be null when not set");
        assertNull(ctx.getDirectMopElements(), "V17 field must be null when not set");
        assertNull(ctx.getIndirectMopElements(), "V17 field must be null when not set");
        assertNull(ctx.getElementScores(), "V17 field must be null when not set");
    }

    @Test
    void testPromptContextRecentActionsEmptyByDefault() {
        PromptContext ctx = PromptContext.builder()
                .base64Screenshot("img")
                .currentActivity("com.example.MainActivity")
                .build();

        assertNotNull(ctx.getRecentActions());
        assertTrue(ctx.getRecentActions().isEmpty());
    }

    @Test
    void testPromptContextBuilderThrowsWhenScreenshotNull() {
        assertThrows(IllegalStateException.class, () ->
                PromptContext.builder()
                        .currentActivity("com.example.MainActivity")
                        .build());
    }

    @Test
    void testPromptContextBuilderThrowsWhenActivityNull() {
        assertThrows(IllegalStateException.class, () ->
                PromptContext.builder()
                        .base64Screenshot("img")
                        .build());
    }

    // -------------------------------------------------------------------------
    // Message structure tests
    // -------------------------------------------------------------------------

    @Test
    void testProducesTwoMessages() {
        List<SglangClient.Message> messages = builder.build(PromptVersion.V13, baseContext("com.example.MainActivity"));
        assertEquals(2, messages.size(), "Must produce exactly 2 messages: system + user");
    }

    @Test
    void testFirstMessageIsSystem() {
        List<SglangClient.Message> messages = builder.build(PromptVersion.V13, baseContext("com.example.MainActivity"));
        assertEquals("system", messages.get(0).getRole());
    }

    @Test
    void testSecondMessageIsUser() {
        List<SglangClient.Message> messages = builder.build(PromptVersion.V13, baseContext("com.example.MainActivity"));
        assertEquals("user", messages.get(1).getRole());
    }

    @Test
    void testSystemMessageIsTextOnly() {
        List<SglangClient.Message> messages = builder.build(PromptVersion.V13, baseContext("com.example.MainActivity"));
        SglangClient.Message system = messages.get(0);
        assertNotNull(system.getTextContent(), "System message must have text content");
        assertNull(system.getContentParts(), "System message must not have content parts");
    }

    @Test
    void testUserMessageIsMultimodal() {
        List<SglangClient.Message> messages = builder.build(PromptVersion.V13, baseContext("com.example.MainActivity"));
        SglangClient.Message user = messages.get(1);
        assertNotNull(user.getContentParts(), "User message must have content parts for multimodal");
        assertFalse(user.getContentParts().isEmpty());
    }

    @Test
    void testUserMessageContainsImageDataUri() {
        PromptContext ctx = PromptContext.builder()
                .base64Screenshot("abc123")
                .currentActivity("com.example.MainActivity")
                .build();
        List<SglangClient.Message> messages = builder.build(PromptVersion.V13, ctx);

        SglangClient.Message user = messages.get(1);
        boolean hasDataUri = false;
        for (SglangClient.ContentPart part : user.getContentParts()) {
            if ("image_url".equals(part.getType()) && part.getImageUrl() != null
                    && part.getImageUrl().startsWith("data:image/jpeg;base64,")) {
                hasDataUri = true;
                break;
            }
        }
        assertTrue(hasDataUri, "Image URL must use data URI format");
    }

    // -------------------------------------------------------------------------
    // Content correctness tests
    // -------------------------------------------------------------------------

    @Test
    void testUserMessageContainsActivity() {
        List<SglangClient.Message> messages = builder.build(PromptVersion.V13,
                baseContext("com.example.SettingsActivity"));
        String textContent = getUserTextContent(messages.get(1));
        assertTrue(textContent.contains("SettingsActivity"), "User text must include the current activity name");
    }

    @Test
    void testUserMessageContainsNavigationHint() {
        PromptContext ctx = PromptContext.builder()
                .base64Screenshot("base64")
                .currentActivity("com.example.MainActivity")
                .navigationHint("Navigate to Settings to find cryptographic operations")
                .build();
        List<SglangClient.Message> messages = builder.build(PromptVersion.V13, ctx);

        String textContent = getUserTextContent(messages.get(1));
        assertTrue(textContent.contains("Navigate to Settings"), "User text must include the navigation hint");
    }

    @Test
    void testNoNavigationHintWhenNull() {
        List<SglangClient.Message> messages = builder.build(PromptVersion.V13, baseContext("com.example.MainActivity"));
        String textContent = getUserTextContent(messages.get(1));
        assertFalse(textContent.contains("Navigation hint"), "Navigation hint section must not appear when hint is null");
    }

    @Test
    void testUserMessageContainsVisitedActivities() {
        Set<String> visited = new HashSet<>(Arrays.asList("MainActivity", "SettingsActivity"));
        PromptContext ctx = PromptContext.builder()
                .base64Screenshot("base64")
                .currentActivity("com.example.MainActivity")
                .visitedActivities(visited)
                .build();
        List<SglangClient.Message> messages = builder.build(PromptVersion.V13, ctx);

        String textContent = getUserTextContent(messages.get(1));
        assertTrue(textContent.contains("Visited activities"), "User text must mention visited activities");
    }

    @Test
    void testNoVisitedSectionWhenEmpty() {
        List<SglangClient.Message> messages = builder.build(PromptVersion.V13, baseContext("com.example.MainActivity"));
        String textContent = getUserTextContent(messages.get(1));
        assertFalse(textContent.contains("Visited activities"), "Visited activities section must not appear when set is empty");
    }

    @Test
    void testInteractiveElementsIncluded() {
        ScreenItem button = new ScreenItem(
                "android.widget.Button",
                "com.example:id/btn_login",
                "Login",
                null,
                null,
                "com.example",
                true, false, false, true, false, false, 0);
        PromptContext ctx = PromptContext.builder()
                .base64Screenshot("base64")
                .currentActivity("com.example.LoginActivity")
                .uiElements(Collections.singletonList(button))
                .build();
        List<SglangClient.Message> messages = builder.build(PromptVersion.V13, ctx);

        String textContent = getUserTextContent(messages.get(1));
        assertTrue(textContent.contains("Button"), "Interactive elements must appear in prompt");
    }

    @Test
    void testNonInteractiveElementsExcluded() {
        ScreenItem label = new ScreenItem(
                "android.widget.TextView",
                null,
                "Just a label",
                null,
                null,
                "com.example",
                false, false, false, true, false, false, 0);
        PromptContext ctx = PromptContext.builder()
                .base64Screenshot("base64")
                .currentActivity("com.example.MainActivity")
                .uiElements(Collections.singletonList(label))
                .build();
        List<SglangClient.Message> messages = builder.build(PromptVersion.V13, ctx);

        String textContent = getUserTextContent(messages.get(1));
        assertFalse(textContent.contains("Just a label"),
                "Non-interactive element text must not appear in the numbered list");
    }

    @Test
    void testV13SystemMessageContainsDialogInstructions() {
        List<SglangClient.Message> messages = builder.build(PromptVersion.V13, baseContext("com.example.MainActivity"));
        String systemText = messages.get(0).getTextContent();
        assertTrue(systemText.contains("dialog"), "V13 system message must include dialog handling instructions");
        assertTrue(systemText.contains("click"), "System message must list click action");
        assertTrue(systemText.contains("scroll"), "System message must list scroll action");
        assertTrue(systemText.contains("back"), "System message must list back action");
    }

    @Test
    void testV12FallsBackToV13() {
        List<SglangClient.Message> v12 = builder.build(PromptVersion.V12, baseContext("com.example.MainActivity"));
        List<SglangClient.Message> v13 = builder.build(PromptVersion.V13, baseContext("com.example.MainActivity"));
        // Both should produce same system message (V12 falls through to V13)
        assertEquals(v13.get(0).getTextContent(), v12.get(0).getTextContent(),
                "V12 should fall through to V13 template");
    }

    @Test
    void testV17ProducesTwoMessages() {
        List<SglangClient.Message> messages = builder.build(PromptVersion.V17, baseContext("com.example.MainActivity"));
        assertEquals(2, messages.size());
    }

    @Test
    void testV17SystemMessageContainsReasoningSteps() {
        List<SglangClient.Message> messages = builder.build(PromptVersion.V17, baseContext("com.example.MainActivity"));
        String system = messages.get(0).getTextContent();
        assertTrue(system.contains("REASONING STEPS"), "V17 system must have reasoning steps");
        assertTrue(system.contains("MOP CHECK"), "V17 system must have MOP check step");
        assertTrue(system.contains("PRIORITY"), "V17 system must have priority block");
    }

    @Test
    void testV17UserMessageContainsScreenInfoLine() {
        PromptContext ctx = PromptContext.builder()
                .base64Screenshot("img")
                .currentActivity("com.example.MainActivity")
                .iterationNumber(7)
                .build();
        List<SglangClient.Message> messages = builder.build(PromptVersion.V17, ctx);
        String text = getUserTextContent(messages.get(1));
        assertTrue(text.contains("SCREEN:"), "V17 user message must contain SCREEN info line");
        assertTrue(text.contains("iter #7"), "V17 user message must include iteration number");
    }

    @Test
    void testV17UserMessageContainsMopNavigation() {
        PromptContext ctx = PromptContext.builder()
                .base64Screenshot("img")
                .currentActivity("com.example.MainActivity")
                .navigationHint("Target: SettingsActivity (has monitored operations, ~1 transition away)")
                .build();
        List<SglangClient.Message> messages = builder.build(PromptVersion.V17, ctx);
        String text = getUserTextContent(messages.get(1));
        assertTrue(text.contains("MOP NAVIGATION:"), "V17 user message must include MOP navigation section");
        assertTrue(text.contains("SettingsActivity"), "V17 user message must include navigation hint content");
    }

    @Test
    void testV17NoMopNavigationWhenHintNull() {
        List<SglangClient.Message> messages = builder.build(PromptVersion.V17, baseContext("com.example.MainActivity"));
        String text = getUserTextContent(messages.get(1));
        assertFalse(text.contains("MOP NAVIGATION:"), "MOP NAVIGATION section must not appear when hint is null");
    }

    @Test
    void testV17ElementWithInteractionCount() {
        ScreenItem button = new ScreenItem(
                "android.widget.Button",
                "com.example:id/btn_ok",
                "OK",
                null,
                null,
                "com.example",
                true, false, false, true, false, false, 0);
        java.util.Map<String, Integer> counts = new java.util.HashMap<>();
        counts.put("res:com.example:id/btn_ok", 3);
        PromptContext ctx = PromptContext.builder()
                .base64Screenshot("img")
                .currentActivity("com.example.MainActivity")
                .uiElements(Collections.singletonList(button))
                .elementInteractionCounts(counts)
                .build();
        List<SglangClient.Message> messages = builder.build(PromptVersion.V17, ctx);
        String text = getUserTextContent(messages.get(1));
        assertTrue(text.contains("[TESTED-3x]"), "V17 must show interaction count tag");
    }

    @Test
    void testV17ElementUntestedWhenNoCount() {
        ScreenItem button = new ScreenItem(
                "android.widget.Button",
                "com.example:id/btn_new",
                "New",
                null,
                null,
                "com.example",
                true, false, false, true, false, false, 0);
        PromptContext ctx = PromptContext.builder()
                .base64Screenshot("img")
                .currentActivity("com.example.MainActivity")
                .uiElements(Collections.singletonList(button))
                .build();
        List<SglangClient.Message> messages = builder.build(PromptVersion.V17, ctx);
        String text = getUserTextContent(messages.get(1));
        assertTrue(text.contains("[UNTESTED]"), "V17 must show [UNTESTED] for elements with no interactions");
    }

    @Test
    void testV17ElementWithDirectMopMarker() {
        ScreenItem button = new ScreenItem(
                "android.widget.Button",
                "com.example:id/btn_encrypt",
                "Encrypt",
                null,
                null,
                "com.example",
                true, false, false, true, false, false, 0);
        java.util.Set<String> directMop = new HashSet<>(Arrays.asList("res:com.example:id/btn_encrypt"));
        PromptContext ctx = PromptContext.builder()
                .base64Screenshot("img")
                .currentActivity("com.example.MainActivity")
                .uiElements(Collections.singletonList(button))
                .directMopElements(directMop)
                .build();
        List<SglangClient.Message> messages = builder.build(PromptVersion.V17, ctx);
        String text = getUserTextContent(messages.get(1));
        assertTrue(text.contains("[DM]"), "V17 must show [DM] for direct MOP elements");
    }

    @Test
    void testV17DegradationNullMopSets() {
        // V17 must work gracefully when MOP sets are null
        PromptContext ctx = PromptContext.builder()
                .base64Screenshot("img")
                .currentActivity("com.example.MainActivity")
                .build();
        assertDoesNotThrow(() -> builder.build(PromptVersion.V17, ctx),
                "V17 must not throw when MOP sets are null");
    }
}
