package br.unb.cic.rvsmart.llm;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;

/**
 * HTTP client for the OpenAI-compatible SGLang inference server.
 *
 * Uses java.net.HttpURLConnection — no external HTTP library needed.
 * Supports both text-only and multimodal (image + text) messages.
 * Throws LlmException on HTTP errors, timeouts, or response parse failures.
 */
public class SglangClient {

    private static final Gson GSON = new Gson();

    private final String baseUrl;
    private final String model;
    private final double temperature;
    private final double topP;
    private final int topK;
    private final int maxTokens;
    private final int timeoutMs;

    public SglangClient(String baseUrl, String model, double temperature,
                        double topP, int topK, int maxTokens, int timeoutMs) {
        this.baseUrl = baseUrl;
        this.model = model;
        this.temperature = temperature;
        this.topP = topP;
        this.topK = topK;
        this.maxTokens = maxTokens;
        this.timeoutMs = timeoutMs;
    }

    /**
     * Send a chat completion request and return the model response.
     *
     * @param messages conversation messages (system, user, assistant roles)
     * @return parsed response with content, tool calls, and token counts
     * @throws LlmException if the request fails or the server returns an error
     */
    public ChatResponse chat(List<Message> messages) {
        String requestBody = buildRequestBody(messages);
        String responseBody = sendRequest(requestBody);
        return parseResponse(responseBody);
    }

    /**
     * Build the JSON request body for the chat completions endpoint.
     */
    String buildRequestBody(List<Message> messages) {
        JsonObject body = new JsonObject();
        body.addProperty("model", model);
        body.addProperty("temperature", temperature);
        body.addProperty("top_p", topP);
        body.addProperty("top_k", topK);
        body.addProperty("max_tokens", maxTokens);

        JsonArray messagesArray = new JsonArray();
        for (Message msg : messages) {
            JsonObject msgObj = new JsonObject();
            msgObj.addProperty("role", msg.getRole());

            if (msg.getContentParts() != null && !msg.getContentParts().isEmpty()) {
                // Multimodal: content is a list of parts
                JsonArray parts = new JsonArray();
                for (ContentPart part : msg.getContentParts()) {
                    JsonObject partObj = new JsonObject();
                    partObj.addProperty("type", part.getType());
                    if ("text".equals(part.getType())) {
                        partObj.addProperty("text", part.getText());
                    } else if ("image_url".equals(part.getType())) {
                        JsonObject imageUrl = new JsonObject();
                        imageUrl.addProperty("url", part.getImageUrl());
                        partObj.add("image_url", imageUrl);
                    }
                    parts.add(partObj);
                }
                msgObj.add("content", parts);
            } else {
                // Plain text content
                msgObj.addProperty("content", msg.getTextContent() != null ? msg.getTextContent() : "");
            }
            messagesArray.add(msgObj);
        }
        body.add("messages", messagesArray);

        return GSON.toJson(body);
    }

    /**
     * Send HTTP POST to /v1/chat/completions and return the raw response body.
     */
    private String sendRequest(String requestBody) {
        HttpURLConnection conn = null;
        try {
            URL url = new URL(baseUrl + "/v1/chat/completions");
            conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setRequestProperty("Accept", "application/json");
            conn.setConnectTimeout(timeoutMs);
            conn.setReadTimeout(timeoutMs);
            conn.setDoOutput(true);

            byte[] bodyBytes = requestBody.getBytes(StandardCharsets.UTF_8);
            try (OutputStream os = conn.getOutputStream()) {
                os.write(bodyBytes);
            }

            int statusCode = conn.getResponseCode();
            if (statusCode != HttpURLConnection.HTTP_OK) {
                throw new LlmException("LLM server returned HTTP " + statusCode + " for " + baseUrl);
            }

            StringBuilder sb = new StringBuilder();
            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) {
                    sb.append(line).append('\n');
                }
            }
            return sb.toString();

        } catch (LlmException e) {
            throw e;
        } catch (IOException e) {
            throw new LlmException("LLM request failed: " + e.getMessage(), e);
        } finally {
            if (conn != null) {
                conn.disconnect();
            }
        }
    }

    /**
     * Parse the OpenAI-format JSON response into a ChatResponse.
     *
     * Expected structure:
     * {"choices": [{"message": {"content": "...", "tool_calls": [...]}}],
     *  "usage": {"prompt_tokens": N, "completion_tokens": M}}
     */
    ChatResponse parseResponse(String responseBody) {
        try {
            JsonObject root = GSON.fromJson(responseBody, JsonObject.class);
            JsonArray choices = root.getAsJsonArray("choices");
            if (choices == null || choices.size() == 0) {
                throw new LlmException("LLM response has no choices: " + responseBody);
            }

            JsonObject message = choices.get(0).getAsJsonObject().getAsJsonObject("message");
            String content = message.has("content") && !message.get("content").isJsonNull()
                    ? message.get("content").getAsString()
                    : "";

            List<ToolCall> toolCalls = new ArrayList<>();
            if (message.has("tool_calls") && !message.get("tool_calls").isJsonNull()) {
                JsonArray tcArray = message.getAsJsonArray("tool_calls");
                for (JsonElement tc : tcArray) {
                    JsonObject tcObj = tc.getAsJsonObject();
                    JsonObject functionObj = tcObj.has("function")
                            ? tcObj.getAsJsonObject("function")
                            : tcObj;
                    String name = functionObj.get("name").getAsString();
                    // arguments may be a JSON string or a JSON object
                    Map<String, Object> args = Collections.emptyMap();
                    if (functionObj.has("arguments")) {
                        JsonElement argsEl = functionObj.get("arguments");
                        if (argsEl.isJsonObject()) {
                            args = parseArgsObject(argsEl.getAsJsonObject());
                        } else if (argsEl.isJsonPrimitive()) {
                            // Arguments encoded as a JSON string
                            String argsStr = argsEl.getAsString();
                            try {
                                JsonObject argsObj = GSON.fromJson(argsStr, JsonObject.class);
                                args = parseArgsObject(argsObj);
                            } catch (Exception ignored) {
                                // Leave args empty on parse failure
                            }
                        }
                    }
                    toolCalls.add(new ToolCall(name, args));
                }
            }

            int promptTokens = 0;
            int completionTokens = 0;
            if (root.has("usage") && !root.get("usage").isJsonNull()) {
                JsonObject usage = root.getAsJsonObject("usage");
                if (usage.has("prompt_tokens")) promptTokens = usage.get("prompt_tokens").getAsInt();
                if (usage.has("completion_tokens")) completionTokens = usage.get("completion_tokens").getAsInt();
            }

            return new ChatResponse(content, toolCalls, promptTokens, completionTokens);

        } catch (LlmException e) {
            throw e;
        } catch (Exception e) {
            throw new LlmException("Failed to parse LLM response: " + e.getMessage(), e);
        }
    }

    /**
     * Convert a JsonObject of primitive values into a Map<String, Object>.
     */
    private Map<String, Object> parseArgsObject(JsonObject obj) {
        Map<String, Object> result = new java.util.LinkedHashMap<>();
        for (Map.Entry<String, JsonElement> entry : obj.entrySet()) {
            JsonElement val = entry.getValue();
            if (val.isJsonPrimitive()) {
                com.google.gson.JsonPrimitive prim = val.getAsJsonPrimitive();
                if (prim.isNumber()) {
                    // Use double for all numbers — callers cast as needed
                    result.put(entry.getKey(), prim.getAsDouble());
                } else if (prim.isBoolean()) {
                    result.put(entry.getKey(), prim.getAsBoolean());
                } else {
                    result.put(entry.getKey(), prim.getAsString());
                }
            } else if (val.isJsonNull()) {
                result.put(entry.getKey(), null);
            } else {
                result.put(entry.getKey(), val.toString());
            }
        }
        return result;
    }

    // --- Inner classes ---

    /**
     * A single message in the conversation.
     * Role is "system", "user", or "assistant".
     * Content is either plain text (textContent) or a list of parts (contentParts) for multimodal.
     */
    public static class Message {
        private final String role;
        private final String textContent;
        private final List<ContentPart> contentParts;

        /** Text-only message. */
        public Message(String role, String textContent) {
            this.role = role;
            this.textContent = textContent;
            this.contentParts = null;
        }

        /** Multimodal message with a list of content parts. */
        public Message(String role, List<ContentPart> contentParts) {
            this.role = role;
            this.textContent = null;
            this.contentParts = contentParts;
        }

        public String getRole() { return role; }
        public String getTextContent() { return textContent; }
        public List<ContentPart> getContentParts() { return contentParts; }
    }

    /**
     * A single part of a multimodal message content array.
     * Type is "text" or "image_url".
     */
    public static class ContentPart {
        private final String type;
        private final String text;
        private final String imageUrl;

        public static ContentPart text(String text) {
            return new ContentPart("text", text, null);
        }

        public static ContentPart imageUrl(String url) {
            return new ContentPart("image_url", null, url);
        }

        private ContentPart(String type, String text, String imageUrl) {
            this.type = type;
            this.text = text;
            this.imageUrl = imageUrl;
        }

        public String getType() { return type; }
        public String getText() { return text; }
        public String getImageUrl() { return imageUrl; }
    }

    /**
     * Parsed model response.
     */
    public static class ChatResponse {
        private final String content;
        private final List<ToolCall> toolCalls;
        private final int promptTokens;
        private final int completionTokens;

        public ChatResponse(String content, List<ToolCall> toolCalls,
                            int promptTokens, int completionTokens) {
            this.content = content;
            this.toolCalls = toolCalls != null ? toolCalls : Collections.<ToolCall>emptyList();
            this.promptTokens = promptTokens;
            this.completionTokens = completionTokens;
        }

        public String getContent() { return content; }
        public List<ToolCall> getToolCalls() { return toolCalls; }
        public int getPromptTokens() { return promptTokens; }
        public int getCompletionTokens() { return completionTokens; }
    }

    /**
     * A single tool call returned by the model.
     */
    public static class ToolCall {
        private final String name;
        private final Map<String, Object> arguments;

        public ToolCall(String name, Map<String, Object> arguments) {
            this.name = name;
            this.arguments = arguments != null ? arguments : Collections.<String, Object>emptyMap();
        }

        public String getName() { return name; }
        public Map<String, Object> getArguments() { return arguments; }
    }
}
