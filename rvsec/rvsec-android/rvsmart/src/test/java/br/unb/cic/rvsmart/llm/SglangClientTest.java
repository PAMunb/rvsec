package br.unb.cic.rvsmart.llm;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for SglangClient request building and response parsing.
 *
 * HTTP calls are not exercised — tests operate on the buildRequestBody() and
 * parseResponse() methods directly to verify JSON format correctness without
 * requiring a live SGLang server.
 */
class SglangClientTest {

    private SglangClient client;

    @BeforeEach
    void setUp() {
        client = new SglangClient(
                "http://localhost:30000",
                "Qwen/Qwen3-VL-4B-Instruct",
                0.01,
                0.6,
                50,
                2048,
                30_000);
    }

    // --- Request body building ---

    @Test
    void testRequestBodyContainsModel() {
        List<SglangClient.Message> messages = Collections.singletonList(
                new SglangClient.Message("user", "hello"));
        String body = client.buildRequestBody(messages);
        assertTrue(body.contains("Qwen/Qwen3-VL-4B-Instruct"), "Body must contain the model name");
    }

    @Test
    void testRequestBodyContainsParameters() {
        List<SglangClient.Message> messages = Collections.singletonList(
                new SglangClient.Message("user", "hello"));
        String body = client.buildRequestBody(messages);
        assertTrue(body.contains("temperature"), "Body must contain temperature");
        assertTrue(body.contains("top_p"), "Body must contain top_p");
        assertTrue(body.contains("top_k"), "Body must contain top_k");
        assertTrue(body.contains("max_tokens"), "Body must contain max_tokens");
    }

    @Test
    void testRequestBodyTextMessage() {
        List<SglangClient.Message> messages = Arrays.asList(
                new SglangClient.Message("system", "You are a tester."),
                new SglangClient.Message("user", "Click the button"));
        String body = client.buildRequestBody(messages);
        assertTrue(body.contains("system"), "Body must include system role");
        assertTrue(body.contains("user"), "Body must include user role");
        assertTrue(body.contains("You are a tester."), "Body must include system content");
        assertTrue(body.contains("Click the button"), "Body must include user content");
    }

    @Test
    void testRequestBodyMultimodalMessage() {
        List<SglangClient.ContentPart> parts = Arrays.asList(
                SglangClient.ContentPart.text("Describe this screen"),
                SglangClient.ContentPart.imageUrl("data:image/jpeg;base64,abc123=="));
        List<SglangClient.Message> messages = Collections.singletonList(
                new SglangClient.Message("user", parts));
        String body = client.buildRequestBody(messages);
        assertTrue(body.contains("image_url"), "Multimodal body must contain image_url type");
        assertTrue(body.contains("abc123"), "Multimodal body must contain base64 data");
        assertTrue(body.contains("Describe this screen"), "Multimodal body must contain text part");
    }

    // --- Response parsing ---

    @Test
    void testParseSimpleTextResponse() {
        String json = "{\n" +
                "  \"choices\": [{\"message\": {\"content\": \"I will click the button\", \"role\": \"assistant\"}}],\n" +
                "  \"usage\": {\"prompt_tokens\": 100, \"completion_tokens\": 20}\n" +
                "}";
        SglangClient.ChatResponse response = client.parseResponse(json);
        assertEquals("I will click the button", response.getContent());
        assertEquals(100, response.getPromptTokens());
        assertEquals(20, response.getCompletionTokens());
        assertTrue(response.getToolCalls().isEmpty());
    }

    @Test
    void testParseResponseWithToolCall() {
        String json = "{\n" +
                "  \"choices\": [{\"message\": {\n" +
                "    \"content\": null,\n" +
                "    \"role\": \"assistant\",\n" +
                "    \"tool_calls\": [{\"function\": {\"name\": \"click\", \"arguments\": \"{\\\"x\\\": 500, \\\"y\\\": 300}\"}}]\n" +
                "  }}],\n" +
                "  \"usage\": {\"prompt_tokens\": 80, \"completion_tokens\": 15}\n" +
                "}";
        SglangClient.ChatResponse response = client.parseResponse(json);
        assertEquals(1, response.getToolCalls().size());
        SglangClient.ToolCall tc = response.getToolCalls().get(0);
        assertEquals("click", tc.getName());
        assertTrue(tc.getArguments().containsKey("x"), "Arguments must contain x");
        assertTrue(tc.getArguments().containsKey("y"), "Arguments must contain y");
    }

    @Test
    void testParseResponseTokenCounts() {
        String json = "{\n" +
                "  \"choices\": [{\"message\": {\"content\": \"ok\", \"role\": \"assistant\"}}],\n" +
                "  \"usage\": {\"prompt_tokens\": 512, \"completion_tokens\": 64}\n" +
                "}";
        SglangClient.ChatResponse response = client.parseResponse(json);
        assertEquals(512, response.getPromptTokens());
        assertEquals(64, response.getCompletionTokens());
    }

    @Test
    void testParseResponseEmptyChoicesThrows() {
        String json = "{\"choices\": [], \"usage\": {}}";
        assertThrows(LlmException.class, () -> client.parseResponse(json));
    }

    @Test
    void testParseResponseMalformedJsonThrows() {
        assertThrows(LlmException.class, () -> client.parseResponse("not json at all"));
    }

    @Test
    void testParseResponseNoUsageReturnsZeroTokens() {
        String json = "{\n" +
                "  \"choices\": [{\"message\": {\"content\": \"hello\", \"role\": \"assistant\"}}]\n" +
                "}";
        SglangClient.ChatResponse response = client.parseResponse(json);
        assertEquals(0, response.getPromptTokens());
        assertEquals(0, response.getCompletionTokens());
    }

    @Test
    void testParseResponseNullContentBecomesEmpty() {
        String json = "{\n" +
                "  \"choices\": [{\"message\": {\"content\": null, \"role\": \"assistant\"}}],\n" +
                "  \"usage\": {\"prompt_tokens\": 10, \"completion_tokens\": 5}\n" +
                "}";
        SglangClient.ChatResponse response = client.parseResponse(json);
        assertEquals("", response.getContent());
    }

    // --- ContentPart factory methods ---

    @Test
    void testContentPartTextFactory() {
        SglangClient.ContentPart part = SglangClient.ContentPart.text("hello");
        assertEquals("text", part.getType());
        assertEquals("hello", part.getText());
        assertNull(part.getImageUrl());
    }

    @Test
    void testContentPartImageUrlFactory() {
        SglangClient.ContentPart part = SglangClient.ContentPart.imageUrl("data:image/jpeg;base64,abc");
        assertEquals("image_url", part.getType());
        assertEquals("data:image/jpeg;base64,abc", part.getImageUrl());
        assertNull(part.getText());
    }
}
