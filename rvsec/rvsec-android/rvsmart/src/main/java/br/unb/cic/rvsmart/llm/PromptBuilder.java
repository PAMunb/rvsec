package br.unb.cic.rvsmart.llm;

import br.unb.cic.rvsmart.core.ScreenItem;

import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/**
 * Builds the messages list for LLM exploration requests.
 *
 * Produces a two-message conversation:
 *   1. System message: role description and available action types
 *   2. User message: screenshot image, numbered UI element list, current activity,
 *      navigation hint, and visited activity summary
 *
 * Prompts are kept concise because Qwen3-VL-4B has limited context capacity.
 * The LLM is instructed to respond with a single tool call in JSON format.
 */
public class PromptBuilder {

    private static final String SYSTEM_CONTENT =
            "You are an Android UI testing agent. Your task is to explore the app by interacting with UI elements.\n" +
            "Available actions:\n" +
            "  click(x, y) — tap an element at normalized coordinates [0,1000)\n" +
            "  long_click(x, y) — long press at normalized coordinates\n" +
            "  scroll(x, y, direction) — scroll at position, direction: up/down/left/right\n" +
            "  type_text(text) — type text into the focused input field\n" +
            "  back() — press the system back button\n" +
            "Respond with exactly one action as JSON: {\"name\": \"<action>\", \"arguments\": {<args>}}";

    /**
     * Build the messages list for an exploration step.
     *
     * @param base64Screenshot  JPEG image encoded as base64 (no data URI prefix)
     * @param uiElements        current screen UI elements
     * @param currentActivity   fully-qualified activity class name
     * @param navigationHint    optional navigation suggestion from the algorithm (may be null)
     * @param visitedActivities set of activity names seen so far in the session
     * @return list of messages ready to pass to SglangClient.chat()
     */
    public List<SglangClient.Message> buildExplorationPrompt(
            String base64Screenshot,
            List<ScreenItem> uiElements,
            String currentActivity,
            String navigationHint,
            Set<String> visitedActivities) {

        List<SglangClient.Message> messages = new ArrayList<>();

        // System message: role and action vocabulary
        messages.add(new SglangClient.Message("system", SYSTEM_CONTENT));

        // User message: screenshot + context
        List<SglangClient.ContentPart> userParts = new ArrayList<>();

        // Screenshot image first so the model grounds its decision visually
        String imageDataUri = "data:image/jpeg;base64," + base64Screenshot;
        userParts.add(SglangClient.ContentPart.imageUrl(imageDataUri));

        // Context text: activity, UI elements, navigation hint, visited summary
        StringBuilder context = new StringBuilder();
        context.append("Current activity: ").append(currentActivity).append("\n\n");

        context.append("UI elements:\n");
        if (uiElements == null || uiElements.isEmpty()) {
            context.append("  (no elements)\n");
        } else {
            int index = 1;
            for (ScreenItem item : uiElements) {
                if (!item.isInteractive()) continue;
                context.append("  ").append(index++).append(". ");
                context.append(simpleClassName(item.getClassName()));
                if (item.getText() != null && !item.getText().isEmpty()) {
                    context.append(" \"").append(truncate(item.getText(), 40)).append("\"");
                } else if (item.getContentDescription() != null
                        && !item.getContentDescription().isEmpty()) {
                    context.append(" [").append(truncate(item.getContentDescription(), 40)).append("]");
                }
                if (item.getBounds() != null) {
                    android.graphics.Rect b = item.getBounds();
                    int cx = (b.left + b.right) / 2;
                    int cy = (b.top + b.bottom) / 2;
                    context.append(" @(").append(cx).append(",").append(cy).append(")");
                }
                context.append("\n");
            }
        }

        if (navigationHint != null && !navigationHint.isEmpty()) {
            context.append("\nNavigation hint: ").append(navigationHint).append("\n");
        }

        if (visitedActivities != null && !visitedActivities.isEmpty()) {
            context.append("\nVisited activities (").append(visitedActivities.size()).append("): ");
            context.append(String.join(", ", visitedActivities)).append("\n");
        }

        context.append("\nChoose ONE action to explore new UI states or trigger monitored operations.");

        userParts.add(SglangClient.ContentPart.text(context.toString()));

        messages.add(new SglangClient.Message("user", userParts));

        return messages;
    }

    /** Return the simple (unqualified) class name for display. */
    private String simpleClassName(String fullName) {
        if (fullName == null) return "View";
        int dot = fullName.lastIndexOf('.');
        return dot >= 0 ? fullName.substring(dot + 1) : fullName;
    }

    /** Truncate a string to at most maxLen characters. */
    private String truncate(String s, int maxLen) {
        if (s == null) return "";
        return s.length() <= maxLen ? s : s.substring(0, maxLen - 1) + "…";
    }
}
