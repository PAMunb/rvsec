package br.unb.cic.rvsmart.llm;

import com.google.gson.Gson;
import com.google.gson.JsonObject;

import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Parses tool calls from LLM responses using a 3-level fallback strategy.
 *
 * Qwen3-VL with SGLang does not always use the native OpenAI tool_calls format (~50% rate).
 * This parser handles all three formats the model may produce:
 *   1. Native  — ChatResponse.toolCalls list is populated by SglangClient
 *   2. XML     — model wraps the call in <tool_call>...</tool_call> tags in its text
 *   3. JSON    — model embeds {"name": "...", "arguments": {...}} in its text
 *
 * Action types produced ("click", "long_click", "scroll", "type_text", "back") map
 * directly to Action.Type via AgentLoop conventions.
 */
public class ToolCallParser {

    private static final Gson GSON = new Gson();

    // Matches <tool_call>...</tool_call> or <function_call>...</function_call>
    private static final Pattern XML_TAG_PATTERN = Pattern.compile(
            "<(?:tool_call|function_call)>(.*?)</(?:tool_call|function_call)>",
            Pattern.DOTALL);

    // Matches a JSON object that has both "name" and "arguments" keys
    private static final Pattern JSON_INLINE_PATTERN = Pattern.compile(
            "\\{[^{}]*\"name\"[^{}]*\"arguments\"[^{}]*(?:\\{[^{}]*\\})[^{}]*\\}|" +
            "\\{[^{}]*\"arguments\"[^{}]*(?:\\{[^{}]*\\})[^{}]*\"name\"[^{}]*\\}",
            Pattern.DOTALL);

    /**
     * Parse a tool call from the model response using native → XML → JSON fallback.
     *
     * @param response the parsed ChatResponse from SglangClient
     * @return a ParsedAction, or null if no recognisable tool call was found
     */
    public ParsedAction parse(SglangClient.ChatResponse response) {
        if (response == null) return null;

        // Level 1: native tool_calls list
        if (response.getToolCalls() != null && !response.getToolCalls().isEmpty()) {
            SglangClient.ToolCall tc = response.getToolCalls().get(0);
            return buildParsedAction(tc.getName(), tc.getArguments());
        }

        // Level 2: XML tag in content text
        String content = response.getContent();
        if (content != null && !content.isEmpty()) {
            ParsedAction fromXml = parseXml(content);
            if (fromXml != null) return fromXml;

            // Level 3: inline JSON in content text
            return parseJsonInline(content);
        }

        return null;
    }

    /**
     * Parse <tool_call>JSON</tool_call> or <function_call>JSON</function_call>.
     */
    private ParsedAction parseXml(String content) {
        Matcher m = XML_TAG_PATTERN.matcher(content);
        if (!m.find()) return null;

        String inner = m.group(1).trim();
        return parseJsonString(inner);
    }

    /**
     * Find and parse the first inline JSON object with "name" + "arguments" keys.
     */
    private ParsedAction parseJsonInline(String content) {
        // Try to find a balanced JSON object containing "name" and "arguments"
        int start = content.indexOf("{");
        while (start >= 0 && start < content.length()) {
            int end = findMatchingBrace(content, start);
            if (end < 0) break;
            String candidate = content.substring(start, end + 1);
            ParsedAction action = parseJsonString(candidate);
            if (action != null) return action;
            start = content.indexOf("{", start + 1);
        }
        return null;
    }

    /**
     * Find the closing brace that matches the opening brace at position 'start'.
     */
    private int findMatchingBrace(String s, int start) {
        int depth = 0;
        for (int i = start; i < s.length(); i++) {
            char c = s.charAt(i);
            if (c == '{') depth++;
            else if (c == '}') {
                depth--;
                if (depth == 0) return i;
            }
        }
        return -1;
    }

    /**
     * Parse a JSON string into a ParsedAction if it contains "name" and "arguments".
     */
    private ParsedAction parseJsonString(String json) {
        try {
            JsonObject obj = GSON.fromJson(json, JsonObject.class);
            if (obj == null || !obj.has("name")) return null;

            String name = obj.get("name").getAsString();

            Map<String, Object> args = new java.util.LinkedHashMap<>();
            if (obj.has("arguments")) {
                com.google.gson.JsonElement argsEl = obj.get("arguments");
                if (argsEl.isJsonObject()) {
                    for (Map.Entry<String, com.google.gson.JsonElement> e :
                            argsEl.getAsJsonObject().entrySet()) {
                        com.google.gson.JsonElement v = e.getValue();
                        if (v.isJsonPrimitive()) {
                            com.google.gson.JsonPrimitive prim = v.getAsJsonPrimitive();
                            if (prim.isNumber()) args.put(e.getKey(), prim.getAsDouble());
                            else if (prim.isBoolean()) args.put(e.getKey(), prim.getAsBoolean());
                            else args.put(e.getKey(), prim.getAsString());
                        } else {
                            args.put(e.getKey(), v.toString());
                        }
                    }
                } else if (argsEl.isJsonPrimitive()) {
                    // Arguments embedded as a JSON string
                    return parseJsonString("{\"name\":\"" + name + "\",\"arguments\":" +
                            GSON.fromJson(argsEl.getAsString(), JsonObject.class) + "}");
                }
            }
            return buildParsedAction(name, args);

        } catch (Exception e) {
            return null;
        }
    }

    /**
     * Build a ParsedAction from a parsed action name and its arguments map.
     *
     * The action name maps to the canonical set used by Action.Type:
     *   click, long_click, scroll, type_text, back, etc.
     * Coordinates from Qwen3-VL are in [0, 1000) normalized space;
     * the caller must convert to pixels via CoordinateNormalizer.
     */
    private ParsedAction buildParsedAction(String name, Map<String, Object> args) {
        if (name == null) return null;

        String actionType = name.toLowerCase().replace("-", "_");

        int x = getIntArg(args, "x", 0);
        int y = getIntArg(args, "y", 0);
        String text = getStringArg(args, "text");
        String direction = getStringArg(args, "direction");

        return new ParsedAction(actionType, x, y, text, direction);
    }

    private int getIntArg(Map<String, Object> args, String key, int defaultValue) {
        if (args == null || !args.containsKey(key)) return defaultValue;
        Object val = args.get(key);
        if (val instanceof Number) return ((Number) val).intValue();
        try { return Integer.parseInt(String.valueOf(val)); } catch (Exception e) { return defaultValue; }
    }

    private String getStringArg(Map<String, Object> args, String key) {
        if (args == null || !args.containsKey(key)) return null;
        Object val = args.get(key);
        return val != null ? String.valueOf(val) : null;
    }

    // --- Inner class ---

    /**
     * The result of parsing a tool call from the LLM response.
     *
     * Coordinates (x, y) are in Qwen3-VL normalized [0, 1000) space.
     * Use CoordinateNormalizer to convert to device pixels before execution.
     */
    public static class ParsedAction {
        private final String actionType;
        private final int x;
        private final int y;
        private final String text;
        private final String direction;

        public ParsedAction(String actionType, int x, int y, String text, String direction) {
            this.actionType = actionType;
            this.x = x;
            this.y = y;
            this.text = text;
            this.direction = direction;
        }

        public String getActionType() { return actionType; }
        public int getX() { return x; }
        public int getY() { return y; }
        public String getText() { return text; }
        public String getDirection() { return direction; }

        @Override
        public String toString() {
            return "ParsedAction{type=" + actionType + ", x=" + x + ", y=" + y +
                    ", text=" + text + ", direction=" + direction + "}";
        }
    }
}
