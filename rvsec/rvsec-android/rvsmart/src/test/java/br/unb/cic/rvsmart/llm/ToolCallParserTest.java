package br.unb.cic.rvsmart.llm;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for ToolCallParser — native, XML, and JSON fallback parsing.
 *
 * Sample responses reflect actual Qwen3-VL output formats observed in practice.
 */
class ToolCallParserTest {

    private ToolCallParser parser;

    @BeforeEach
    void setUp() {
        parser = new ToolCallParser();
    }

    // --- Level 1: Native tool_calls ---

    @Test
    void testNativeClickToolCall() {
        Map<String, Object> args = new HashMap<>();
        args.put("x", 500.0);
        args.put("y", 300.0);
        SglangClient.ToolCall tc = new SglangClient.ToolCall("click", args);
        SglangClient.ChatResponse response = new SglangClient.ChatResponse(
                "", Collections.singletonList(tc), 0, 0);

        ToolCallParser.ParsedAction action = parser.parse(response);
        assertNotNull(action);
        assertEquals("click", action.getActionType());
        assertEquals(500, action.getX());
        assertEquals(300, action.getY());
    }

    @Test
    void testNativeLongClickToolCall() {
        Map<String, Object> args = new HashMap<>();
        args.put("x", 200.0);
        args.put("y", 400.0);
        SglangClient.ToolCall tc = new SglangClient.ToolCall("long_click", args);
        SglangClient.ChatResponse response = new SglangClient.ChatResponse(
                "", Collections.singletonList(tc), 0, 0);

        ToolCallParser.ParsedAction action = parser.parse(response);
        assertNotNull(action);
        assertEquals("long_click", action.getActionType());
    }

    @Test
    void testNativeScrollToolCall() {
        Map<String, Object> args = new HashMap<>();
        args.put("x", 500.0);
        args.put("y", 500.0);
        args.put("direction", "up");
        SglangClient.ToolCall tc = new SglangClient.ToolCall("scroll", args);
        SglangClient.ChatResponse response = new SglangClient.ChatResponse(
                "", Collections.singletonList(tc), 0, 0);

        ToolCallParser.ParsedAction action = parser.parse(response);
        assertNotNull(action);
        assertEquals("scroll", action.getActionType());
        assertEquals("up", action.getDirection());
    }

    @Test
    void testNativeTypeTextToolCall() {
        Map<String, Object> args = new HashMap<>();
        args.put("text", "hello world");
        SglangClient.ToolCall tc = new SglangClient.ToolCall("type_text", args);
        SglangClient.ChatResponse response = new SglangClient.ChatResponse(
                "", Collections.singletonList(tc), 0, 0);

        ToolCallParser.ParsedAction action = parser.parse(response);
        assertNotNull(action);
        assertEquals("type_text", action.getActionType());
        assertEquals("hello world", action.getText());
    }

    @Test
    void testNativeBackToolCall() {
        SglangClient.ToolCall tc = new SglangClient.ToolCall("back", Collections.<String, Object>emptyMap());
        SglangClient.ChatResponse response = new SglangClient.ChatResponse(
                "", Collections.singletonList(tc), 0, 0);

        ToolCallParser.ParsedAction action = parser.parse(response);
        assertNotNull(action);
        assertEquals("back", action.getActionType());
    }

    @Test
    void testNativeTakesPriorityOverTextContent() {
        // Even if content has XML, native tool_calls must win
        Map<String, Object> args = new HashMap<>();
        args.put("x", 100.0);
        args.put("y", 200.0);
        SglangClient.ToolCall tc = new SglangClient.ToolCall("click", args);
        String xmlContent = "<tool_call>{\"name\": \"scroll\", \"arguments\": {\"x\": 500, \"y\": 500, \"direction\": \"down\"}}</tool_call>";
        SglangClient.ChatResponse response = new SglangClient.ChatResponse(
                xmlContent, Collections.singletonList(tc), 0, 0);

        ToolCallParser.ParsedAction action = parser.parse(response);
        assertNotNull(action);
        // Native click wins, not the XML scroll
        assertEquals("click", action.getActionType());
        assertEquals(100, action.getX());
    }

    // --- Level 2: XML fallback ---

    @Test
    void testXmlToolCallTag() {
        String content = "<tool_call>{\"name\": \"click\", \"arguments\": {\"x\": 500, \"y\": 300}}</tool_call>";
        SglangClient.ChatResponse response = new SglangClient.ChatResponse(
                content, Collections.<SglangClient.ToolCall>emptyList(), 0, 0);

        ToolCallParser.ParsedAction action = parser.parse(response);
        assertNotNull(action, "Should parse XML tool_call tag");
        assertEquals("click", action.getActionType());
        assertEquals(500, action.getX());
        assertEquals(300, action.getY());
    }

    @Test
    void testXmlFunctionCallTag() {
        String content = "<function_call>{\"name\": \"scroll\", \"arguments\": {\"x\": 540, \"y\": 800, \"direction\": \"down\"}}</function_call>";
        SglangClient.ChatResponse response = new SglangClient.ChatResponse(
                content, Collections.<SglangClient.ToolCall>emptyList(), 0, 0);

        ToolCallParser.ParsedAction action = parser.parse(response);
        assertNotNull(action, "Should parse XML function_call tag");
        assertEquals("scroll", action.getActionType());
        assertEquals("down", action.getDirection());
    }

    @Test
    void testXmlToolCallWithTextAround() {
        String content = "I will click the settings button.\n" +
                "<tool_call>{\"name\": \"click\", \"arguments\": {\"x\": 750, \"y\": 120}}</tool_call>\n" +
                "This will open the menu.";
        SglangClient.ChatResponse response = new SglangClient.ChatResponse(
                content, Collections.<SglangClient.ToolCall>emptyList(), 0, 0);

        ToolCallParser.ParsedAction action = parser.parse(response);
        assertNotNull(action, "Should extract XML tool call from mixed text");
        assertEquals("click", action.getActionType());
        assertEquals(750, action.getX());
        assertEquals(120, action.getY());
    }

    // --- Level 3: JSON inline fallback ---

    @Test
    void testJsonInlineClick() {
        String content = "I will click here {\"name\": \"click\", \"arguments\": {\"x\": 500, \"y\": 300}}";
        SglangClient.ChatResponse response = new SglangClient.ChatResponse(
                content, Collections.<SglangClient.ToolCall>emptyList(), 0, 0);

        ToolCallParser.ParsedAction action = parser.parse(response);
        assertNotNull(action, "Should parse inline JSON tool call");
        assertEquals("click", action.getActionType());
        assertEquals(500, action.getX());
        assertEquals(300, action.getY());
    }

    @Test
    void testJsonInlineScroll() {
        String content = "Let me scroll down. {\"name\": \"scroll\", \"arguments\": {\"x\": 540, \"y\": 960, \"direction\": \"up\"}}";
        SglangClient.ChatResponse response = new SglangClient.ChatResponse(
                content, Collections.<SglangClient.ToolCall>emptyList(), 0, 0);

        ToolCallParser.ParsedAction action = parser.parse(response);
        assertNotNull(action, "Should parse inline JSON scroll");
        assertEquals("scroll", action.getActionType());
        assertEquals("up", action.getDirection());
    }

    @Test
    void testJsonInlineTypeText() {
        String content = "{\"name\": \"type_text\", \"arguments\": {\"text\": \"test@example.com\"}}";
        SglangClient.ChatResponse response = new SglangClient.ChatResponse(
                content, Collections.<SglangClient.ToolCall>emptyList(), 0, 0);

        ToolCallParser.ParsedAction action = parser.parse(response);
        assertNotNull(action, "Should parse inline JSON type_text");
        assertEquals("type_text", action.getActionType());
        assertEquals("test@example.com", action.getText());
    }

    // --- Null / empty cases ---

    @Test
    void testNullResponseReturnsNull() {
        assertNull(parser.parse(null));
    }

    @Test
    void testEmptyContentAndNoToolCallsReturnsNull() {
        SglangClient.ChatResponse response = new SglangClient.ChatResponse(
                "", Collections.<SglangClient.ToolCall>emptyList(), 0, 0);
        assertNull(parser.parse(response));
    }

    @Test
    void testContentWithNoRecognizableActionReturnsNull() {
        SglangClient.ChatResponse response = new SglangClient.ChatResponse(
                "I cannot determine the best action from the screenshot.",
                Collections.<SglangClient.ToolCall>emptyList(), 0, 0);
        assertNull(parser.parse(response));
    }

    // --- ParsedAction accessors ---

    @Test
    void testParsedActionDefaultsForMissingCoords() {
        SglangClient.ToolCall tc = new SglangClient.ToolCall(
                "back", Collections.<String, Object>emptyMap());
        SglangClient.ChatResponse response = new SglangClient.ChatResponse(
                "", Collections.singletonList(tc), 0, 0);

        ToolCallParser.ParsedAction action = parser.parse(response);
        assertNotNull(action);
        assertEquals(0, action.getX(), "Missing x must default to 0");
        assertEquals(0, action.getY(), "Missing y must default to 0");
        assertNull(action.getText());
        assertNull(action.getDirection());
    }
}
