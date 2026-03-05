package br.unb.cic.rvsmart.llm;

import br.unb.cic.rvsmart.core.ScreenItem;
import br.unb.cic.rvsmart.output.RvTrack;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
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

    // --- Message structure ---

    @Test
    void testProducesTwoMessages() {
        List<SglangClient.Message> messages = builder.buildExplorationPrompt(
                "abc123",
                Collections.<ScreenItem>emptyList(),
                "com.example.MainActivity",
                null,
                Collections.<String>emptySet());

        assertEquals(2, messages.size(), "Must produce exactly 2 messages: system + user");
    }

    @Test
    void testFirstMessageIsSystem() {
        List<SglangClient.Message> messages = builder.buildExplorationPrompt(
                "base64img",
                Collections.<ScreenItem>emptyList(),
                "com.example.MainActivity",
                null,
                Collections.<String>emptySet());

        assertEquals("system", messages.get(0).getRole());
    }

    @Test
    void testSecondMessageIsUser() {
        List<SglangClient.Message> messages = builder.buildExplorationPrompt(
                "base64img",
                Collections.<ScreenItem>emptyList(),
                "com.example.MainActivity",
                null,
                Collections.<String>emptySet());

        assertEquals("user", messages.get(1).getRole());
    }

    @Test
    void testSystemMessageIsTextOnly() {
        List<SglangClient.Message> messages = builder.buildExplorationPrompt(
                "base64img",
                Collections.<ScreenItem>emptyList(),
                "com.example.MainActivity",
                null,
                Collections.<String>emptySet());

        SglangClient.Message system = messages.get(0);
        assertNotNull(system.getTextContent(), "System message must have text content");
        assertNull(system.getContentParts(), "System message must not have content parts");
    }

    @Test
    void testUserMessageIsMultimodal() {
        List<SglangClient.Message> messages = builder.buildExplorationPrompt(
                "abc123==",
                Collections.<ScreenItem>emptyList(),
                "com.example.MainActivity",
                null,
                Collections.<String>emptySet());

        SglangClient.Message user = messages.get(1);
        assertNotNull(user.getContentParts(), "User message must have content parts for multimodal");
        assertFalse(user.getContentParts().isEmpty());
    }

    @Test
    void testUserMessageContainsImagePart() {
        String base64 = "iVBORw0KGgoAAAANSUhEUgAA";
        List<SglangClient.Message> messages = builder.buildExplorationPrompt(
                base64,
                Collections.<ScreenItem>emptyList(),
                "com.example.MainActivity",
                null,
                Collections.<String>emptySet());

        SglangClient.Message user = messages.get(1);
        boolean hasImagePart = false;
        for (SglangClient.ContentPart part : user.getContentParts()) {
            if ("image_url".equals(part.getType()) && part.getImageUrl() != null
                    && part.getImageUrl().contains(base64)) {
                hasImagePart = true;
                break;
            }
        }
        assertTrue(hasImagePart, "User message must contain the screenshot as image_url part");
    }

    @Test
    void testUserMessageContainsImageDataUri() {
        List<SglangClient.Message> messages = builder.buildExplorationPrompt(
                "abc123",
                Collections.<ScreenItem>emptyList(),
                "com.example.MainActivity",
                null,
                Collections.<String>emptySet());

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

    // --- Content includes context information ---

    @Test
    void testUserMessageContainsActivity() {
        List<SglangClient.Message> messages = builder.buildExplorationPrompt(
                "base64",
                Collections.<ScreenItem>emptyList(),
                "com.example.SettingsActivity",
                null,
                Collections.<String>emptySet());

        String textContent = getUserTextContent(messages.get(1));
        assertTrue(textContent.contains("SettingsActivity"),
                "User text must include the current activity name");
    }

    @Test
    void testUserMessageContainsNavigationHint() {
        List<SglangClient.Message> messages = builder.buildExplorationPrompt(
                "base64",
                Collections.<ScreenItem>emptyList(),
                "com.example.MainActivity",
                "Navigate to Settings to find cryptographic operations",
                Collections.<String>emptySet());

        String textContent = getUserTextContent(messages.get(1));
        assertTrue(textContent.contains("Navigate to Settings"),
                "User text must include the navigation hint");
    }

    @Test
    void testNoNavigationHintWhenNull() {
        List<SglangClient.Message> messages = builder.buildExplorationPrompt(
                "base64",
                Collections.<ScreenItem>emptyList(),
                "com.example.MainActivity",
                null,
                Collections.<String>emptySet());

        String textContent = getUserTextContent(messages.get(1));
        assertFalse(textContent.contains("Navigation hint"),
                "Navigation hint section must not appear when hint is null");
    }

    @Test
    void testUserMessageContainsVisitedActivities() {
        Set<String> visited = new HashSet<>(Arrays.asList("MainActivity", "SettingsActivity"));
        List<SglangClient.Message> messages = builder.buildExplorationPrompt(
                "base64",
                Collections.<ScreenItem>emptyList(),
                "com.example.MainActivity",
                null,
                visited);

        String textContent = getUserTextContent(messages.get(1));
        assertTrue(textContent.contains("Visited activities"),
                "User text must mention visited activities");
    }

    @Test
    void testNoVisitedSectionWhenEmpty() {
        List<SglangClient.Message> messages = builder.buildExplorationPrompt(
                "base64",
                Collections.<ScreenItem>emptyList(),
                "com.example.MainActivity",
                null,
                Collections.<String>emptySet());

        String textContent = getUserTextContent(messages.get(1));
        assertFalse(textContent.contains("Visited activities"),
                "Visited activities section must not appear when set is empty");
    }

    @Test
    void testInteractiveElementsIncluded() {
        // Clickable button
        ScreenItem button = new ScreenItem(
                "android.widget.Button",
                "com.example:id/btn_login",
                "Login",
                null,
                null,    // null bounds — no Android Rect needed
                "com.example",
                true, false, false, true, false, false, 0);

        List<SglangClient.Message> messages = builder.buildExplorationPrompt(
                "base64",
                Collections.singletonList(button),
                "com.example.LoginActivity",
                null,
                Collections.<String>emptySet());

        String textContent = getUserTextContent(messages.get(1));
        assertTrue(textContent.contains("Button"), "Interactive elements must appear in prompt");
    }

    @Test
    void testNonInteractiveElementsExcluded() {
        // Non-interactive TextView (no clickable/scrollable/checkable/editable)
        ScreenItem label = new ScreenItem(
                "android.widget.TextView",
                null,
                "Just a label",
                null,
                null,
                "com.example",
                false, false, false, true, false, false, 0);

        List<SglangClient.Message> messages = builder.buildExplorationPrompt(
                "base64",
                Collections.singletonList(label),
                "com.example.MainActivity",
                null,
                Collections.<String>emptySet());

        // Text "Just a label" from a non-interactive element should not appear
        // (because the builder skips non-interactive items)
        String textContent = getUserTextContent(messages.get(1));
        assertFalse(textContent.contains("Just a label"),
                "Non-interactive element text must not appear in the numbered list");
    }

    @Test
    void testSystemMessageMentionsAvailableActions() {
        List<SglangClient.Message> messages = builder.buildExplorationPrompt(
                "base64",
                Collections.<ScreenItem>emptyList(),
                "com.example.MainActivity",
                null,
                Collections.<String>emptySet());

        String systemText = messages.get(0).getTextContent();
        assertTrue(systemText.contains("click"), "System message must list click action");
        assertTrue(systemText.contains("scroll"), "System message must list scroll action");
        assertTrue(systemText.contains("back"), "System message must list back action");
    }

    // --- Helper ---

    /**
     * Extract the text content from a user (multimodal) message by finding the text part.
     */
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
}
