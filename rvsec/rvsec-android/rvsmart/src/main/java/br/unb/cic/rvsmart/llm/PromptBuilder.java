package br.unb.cic.rvsmart.llm;

import br.unb.cic.rvsmart.core.Config.PromptVersion;
import br.unb.cic.rvsmart.core.ScreenItem;

import java.util.ArrayList;
import java.util.List;

/**
 * Builds the messages list for LLM exploration requests.
 *
 * Entry point: {@link #build(PromptVersion, PromptContext)}.
 * Dispatches to V13 or V17 template based on the version parameter.
 * V12/V14/V15/V16 all fall through to the V13 template.
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

    /**
     * Build the messages list for an exploration step.
     *
     * @param version prompt template version; V13 and V17 are fully implemented;
     *                V12/V14/V15/V16 fall through to V13
     * @param ctx     all context data needed to assemble the prompt
     * @return list of messages ready to pass to SglangClient.chat()
     */
    public List<SglangClient.Message> build(PromptVersion version, PromptContext ctx) {
        switch (version) {
            case V17:
                return buildV17(ctx);
            // V12, V13, V14, V15, V16 all use the V13 template
            default:
                return buildV13(ctx);
        }
    }

    // -------------------------------------------------------------------------
    // V13 template (dialog-aware, simple element list)
    // -------------------------------------------------------------------------

    private static final String SYSTEM_V13 =
            "You are an Android UI testing agent. Your task is to explore the app by interacting with UI elements.\n" +
            "DIALOG HANDLING: If you see a permission dialog, click Allow/Accept/OK.\n" +
            "  If you see an error or modal dialog, dismiss it before any other action.\n" +
            "PRIORITY: MOP target elements > navigation to new screens > [UNTESTED] elements > [TESTED] elements.\n" +
            "Available actions:\n" +
            "  click(x, y) — tap an element at normalized coordinates [0,1000)\n" +
            "  long_click(x, y) — long press at normalized coordinates\n" +
            "  scroll(x, y, direction) — scroll at position, direction: up/down/left/right\n" +
            "  type_text(text) — type text into the focused input field\n" +
            "  back() — press the system back button\n" +
            "RULE: Do not click the same position twice in a row.\n" +
            "Respond with exactly one action as JSON: {\"name\": \"<action>\", \"arguments\": {<args>}}";

    private List<SglangClient.Message> buildV13(PromptContext ctx) {
        List<SglangClient.Message> messages = new ArrayList<>();

        // System message: role, dialog instructions, action vocabulary
        messages.add(new SglangClient.Message("system", SYSTEM_V13));

        // User message: screenshot + context text
        List<SglangClient.ContentPart> userParts = new ArrayList<>();

        // Screenshot image first so the model grounds its decision visually
        String imageDataUri = "data:image/jpeg;base64," + ctx.getBase64Screenshot();
        userParts.add(SglangClient.ContentPart.imageUrl(imageDataUri));

        StringBuilder context = new StringBuilder();
        context.append("Current activity: ").append(ctx.getCurrentActivity()).append("\n\n");

        context.append("UI elements:\n");
        List<ScreenItem> items = ctx.getUiElements();
        if (items.isEmpty()) {
            context.append("  (no elements)\n");
        } else {
            int index = 1;
            for (ScreenItem item : items) {
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

        String hint = ctx.getNavigationHint();
        if (hint != null && !hint.isEmpty()) {
            context.append("\nNavigation hint: ").append(hint).append("\n");
        }

        if (!ctx.getVisitedActivities().isEmpty()) {
            context.append("\nVisited activities (").append(ctx.getVisitedActivities().size()).append("): ");
            context.append(String.join(", ", ctx.getVisitedActivities())).append("\n");
        }

        context.append("\nIteration: ").append(ctx.getIterationNumber());
        context.append("\nChoose ONE action to explore new UI states or trigger monitored operations.");

        userParts.add(SglangClient.ContentPart.text(context.toString()));
        messages.add(new SglangClient.Message("user", userParts));

        return messages;
    }

    // -------------------------------------------------------------------------
    // V17 template (MOP-aware, test-status tags, action history)
    // -------------------------------------------------------------------------

    private static final String SYSTEM_V17 =
            "You are an Android UI automation assistant.\n" +
            "\n" +
            "REASONING STEPS:\n" +
            "1. SCREEN: Identify screen type (dialog, form, list, menu).\n" +
            "2. DIALOG: If blocking dialog present, handle it first.\n" +
            "3. MOP CHECK: If [DM] or [M] elements are shown, prioritize them.\n" +
            "4. NAVIGATION: Check for actions leading to unvisited screens.\n" +
            "5. ELEMENTS: Select [UNTESTED] element if no navigation or MOP target available.\n" +
            "6. ACTION: Call the action with normalized coordinates [0,1000).\n" +
            "\n" +
            "DIALOG HANDLING:\n" +
            "- Permission dialogs: Click \"Allow\", \"Accept\", \"OK\"\n" +
            "- Error dialogs: Dismiss before other actions\n" +
            "- Use back() if no dismiss button visible\n" +
            "\n" +
            "PRIORITY:\n" +
            "- Elements reaching monitored operations ([DM] direct / [M] transitive) > other actions\n" +
            "- Actions leading to NEW screens > same-screen actions\n" +
            "- [UNTESTED] > [TESTED-Nx] > [WELL-TESTED]\n" +
            "\n" +
            "RULES:\n" +
            "- Do not click the same position consecutively\n" +
            "- If last action had no effect, try a different element\n" +
            "- Explore new screens before testing same screen deeply\n" +
            "\n" +
            "AVOID: navigation bar (bottom), status bar (top)\n" +
            "\n" +
            "Available actions:\n" +
            "  click(x, y) — tap at normalized coordinates [0,1000)\n" +
            "  long_click(x, y) — long press\n" +
            "  scroll(x, y, direction) — direction: up/down/left/right\n" +
            "  type_text(text) — type into focused EditText\n" +
            "  back() — press system back\n" +
            "\n" +
            "Respond with exactly one action as JSON: {\"name\": \"<action>\", \"arguments\": {<args>}}";

    private List<SglangClient.Message> buildV17(PromptContext ctx) {
        List<SglangClient.Message> messages = new ArrayList<>();
        messages.add(new SglangClient.Message("system", SYSTEM_V17));

        List<SglangClient.ContentPart> userParts = new ArrayList<>();
        String imageDataUri = "data:image/jpeg;base64," + ctx.getBase64Screenshot();
        userParts.add(SglangClient.ContentPart.imageUrl(imageDataUri));

        StringBuilder sb = new StringBuilder();

        sb.append("Iteration ").append(ctx.getIterationNumber()).append("\n");

        // Recent actions section (last 5)
        if (!ctx.getRecentActions().isEmpty()) {
            sb.append("Recent actions: ");
            boolean first = true;
            for (br.unb.cic.rvsmart.core.Action a : ctx.getRecentActions()) {
                if (!first) sb.append(", ");
                sb.append(a.getType().name().toLowerCase())
                        .append("@(").append(a.getX()).append(",").append(a.getY()).append(")");
                first = false;
            }
            sb.append("\n");
        }

        sb.append("\nELEMENTS:\n");
        List<br.unb.cic.rvsmart.core.ScreenItem> items = ctx.getUiElements();
        if (items.isEmpty()) {
            sb.append("  (no elements)\n");
        } else {
            int index = 1;
            for (br.unb.cic.rvsmart.core.ScreenItem item : items) {
                if (!item.isInteractive()) continue;
                String elemId = safeElementId(item);
                int count = getInteractionCount(ctx, elemId);
                String statusTag = elementStatusTag(count);
                String mopMarker = elementMopMarker(ctx, elemId);

                sb.append("  ").append(index++).append(". ");
                sb.append(simpleClassName(item.getClassName()));
                if (item.getText() != null && !item.getText().isEmpty()) {
                    sb.append(" \"").append(truncate(item.getText(), 40)).append("\"");
                } else if (item.getContentDescription() != null
                        && !item.getContentDescription().isEmpty()) {
                    sb.append(" [").append(truncate(item.getContentDescription(), 40)).append("]");
                }
                if (item.getBounds() != null) {
                    try {
                        android.graphics.Rect b = item.getBounds();
                        int cx = (b.left + b.right) / 2;
                        int cy = (b.top + b.bottom) / 2;
                        sb.append(" @(").append(cx).append(",").append(cy).append(")");
                    } catch (RuntimeException ignored) {}
                }
                sb.append(" ").append(statusTag);
                if (!mopMarker.isEmpty()) sb.append(" ").append(mopMarker);
                sb.append("\n");
            }
        }

        // Screen info line
        int interacted = ctx.getElementInteractionCounts() != null
                ? ctx.getElementInteractionCounts().size() : 0;
        int total = 0;
        for (br.unb.cic.rvsmart.core.ScreenItem si : items) {
            if (si.isInteractive()) total++;
        }
        sb.append("\nSCREEN: ").append(ctx.getCurrentActivity())
                .append(" | ").append(interacted).append("/").append(total)
                .append(" actions tested | iter #").append(ctx.getIterationNumber()).append("\n");

        // MOP navigation hint
        String hint = ctx.getNavigationHint();
        if (hint != null && !hint.isEmpty()) {
            sb.append("\nMOP NAVIGATION:\n").append(hint).append("\n");
        }

        sb.append("\nSelect action. Prioritize elements reaching monitored operations, then navigation to new screens.");

        userParts.add(SglangClient.ContentPart.text(sb.toString()));
        messages.add(new SglangClient.Message("user", userParts));
        return messages;
    }

    /** Compute element ID from a ScreenItem without requiring Android Rect to be non-stub. */
    private String safeElementId(br.unb.cic.rvsmart.core.ScreenItem item) {
        String resId = item.getResourceId();
        if (resId != null && !resId.isEmpty()) return "res:" + resId;
        if (item.getBounds() != null) {
            try {
                android.graphics.Rect b = item.getBounds();
                return "coords:" + ((b.left + b.right) / 2) + "," + ((b.top + b.bottom) / 2);
            } catch (RuntimeException ignored) {}
        }
        return "unknown:" + System.identityHashCode(item);
    }

    private int getInteractionCount(PromptContext ctx, String elemId) {
        if (ctx.getElementInteractionCounts() == null) return 0;
        Integer c = ctx.getElementInteractionCounts().get(elemId);
        return c != null ? c : 0;
    }

    private String elementStatusTag(int count) {
        if (count == 0) return "[UNTESTED]";
        if (count < 5) return "[TESTED-" + count + "x]";
        return "[WELL-TESTED]";
    }

    private String elementMopMarker(PromptContext ctx, String elemId) {
        if (ctx.getDirectMopElements() != null && ctx.getDirectMopElements().contains(elemId))
            return "[DM]";
        if (ctx.getIndirectMopElements() != null && ctx.getIndirectMopElements().contains(elemId))
            return "[M]";
        return "";
    }

    // -------------------------------------------------------------------------
    // Helpers
    // -------------------------------------------------------------------------

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
