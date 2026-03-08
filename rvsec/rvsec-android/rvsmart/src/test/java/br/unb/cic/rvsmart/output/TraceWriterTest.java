package br.unb.cic.rvsmart.output;

import com.google.gson.Gson;
import com.google.gson.JsonObject;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for TraceWriter JSON output format and field correctness.
 * Captures stdout to validate JSONL output.
 */
class TraceWriterTest {

    private static final Gson GSON = new Gson();

    private TraceWriter writer;
    private ByteArrayOutputStream captured;
    private PrintStream originalOut;

    @BeforeEach
    void setUp() {
        writer = new TraceWriter();
        captured = new ByteArrayOutputStream();
        originalOut = System.out;
        System.setOut(new PrintStream(captured));
    }

    @AfterEach
    void tearDown() {
        System.setOut(originalOut);
    }

    private JsonObject writeAndParse(int iteration, long timestampMs, String hash, String activity,
                                      String actionType, String actionSource, boolean actionHadEffect,
                                      int retries, int uniqueStates, double elapsedS) {
        writer.writeLine(iteration, timestampMs, hash, activity,
                actionType, actionSource, actionHadEffect, retries, uniqueStates, elapsedS,
                540, 273, "android.widget.Button");
        String output = captured.toString().trim();
        return GSON.fromJson(output, JsonObject.class);
    }

    @Test
    void testOutputIsValidJson() {
        writer.writeLine(1, 1000L, "abc123", "MainActivity",
                "click", "algorithm", true, 0, 5, 1.5,
                540, 273, "android.widget.Button");
        String output = captured.toString().trim();
        // Should not throw
        JsonObject json = GSON.fromJson(output, JsonObject.class);
        assertNotNull(json);
    }

    @Test
    void testAllFieldsPresent() {
        JsonObject json = writeAndParse(1, 1000L, "abc123", "MainActivity",
                "click", "algorithm", true, 0, 5, 1.5);

        assertTrue(json.has("iteration"));
        assertTrue(json.has("timestamp_ms"));
        assertTrue(json.has("hash"));
        assertTrue(json.has("activity"));
        assertTrue(json.has("action_type"));
        assertTrue(json.has("action_source"));
        assertTrue(json.has("action_had_effect"));
        assertTrue(json.has("retries"));
        assertTrue(json.has("unique_states"));
        assertTrue(json.has("elapsed_s"));
    }

    @Test
    void testFieldCountBasicOverload() {
        JsonObject json = writeAndParse(1, 1000L, "abc123", "MainActivity",
                "click", "algorithm", true, 0, 5, 1.5);
        assertEquals(13, json.size(), "Basic trace line should have exactly 13 fields");
    }

    @Test
    void testIterationValue() {
        JsonObject json = writeAndParse(42, 1000L, "h", "A", "click", "algorithm", true, 0, 1, 0.0);
        assertEquals(42, json.get("iteration").getAsInt());
    }

    @Test
    void testTimestampValue() {
        JsonObject json = writeAndParse(1, 9999L, "h", "A", "click", "algorithm", true, 0, 1, 0.0);
        assertEquals(9999L, json.get("timestamp_ms").getAsLong());
    }

    @Test
    void testHashValue() {
        JsonObject json = writeAndParse(1, 1000L, "deadbeef1234", "A", "click", "algorithm", true, 0, 1, 0.0);
        assertEquals("deadbeef1234", json.get("hash").getAsString());
    }

    @Test
    void testActivityValue() {
        JsonObject json = writeAndParse(1, 1000L, "h", "com.example.LoginActivity",
                "click", "algorithm", true, 0, 1, 0.0);
        assertEquals("com.example.LoginActivity", json.get("activity").getAsString());
    }

    @Test
    void testActionTypeIsString() {
        JsonObject json = writeAndParse(1, 1000L, "h", "A", "long_click", "algorithm", true, 0, 1, 0.0);
        assertTrue(json.get("action_type").isJsonPrimitive());
        assertEquals("long_click", json.get("action_type").getAsString());
    }

    @Test
    void testActionSourceAlgorithm() {
        JsonObject json = writeAndParse(1, 1000L, "h", "A", "click", "algorithm", true, 0, 1, 0.0);
        assertEquals("algorithm", json.get("action_source").getAsString());
    }

    @Test
    void testActionSourceLlm() {
        JsonObject json = writeAndParse(1, 1000L, "h", "A", "click", "llm", true, 0, 1, 0.0);
        assertEquals("llm", json.get("action_source").getAsString());
    }

    @Test
    void testActionHadEffectTrue() {
        JsonObject json = writeAndParse(1, 1000L, "h", "A", "click", "algorithm", true, 0, 1, 0.0);
        assertTrue(json.get("action_had_effect").getAsBoolean());
    }

    @Test
    void testActionHadEffectFalse() {
        JsonObject json = writeAndParse(1, 1000L, "h", "A", "click", "algorithm", false, 0, 1, 0.0);
        assertFalse(json.get("action_had_effect").getAsBoolean());
    }

    @Test
    void testRetriesValue() {
        JsonObject json = writeAndParse(1, 1000L, "h", "A", "click", "algorithm", true, 3, 1, 0.0);
        assertEquals(3, json.get("retries").getAsInt());
    }

    @Test
    void testUniqueStatesValue() {
        JsonObject json = writeAndParse(1, 1000L, "h", "A", "click", "algorithm", true, 0, 15, 0.0);
        assertEquals(15, json.get("unique_states").getAsInt());
    }

    @Test
    void testElapsedSValue() {
        JsonObject json = writeAndParse(1, 1000L, "h", "A", "click", "algorithm", true, 0, 1, 42.7);
        assertEquals(42.7, json.get("elapsed_s").getAsDouble(), 0.001);
    }

    @Test
    void testOutputIsSingleLine() {
        writer.writeLine(1, 1000L, "h", "A", "click", "algorithm", true, 0, 1, 0.0,
                540, 273, "android.widget.Button");
        String output = captured.toString();
        // Should contain exactly one newline at the end (println)
        long newlineCount = output.chars().filter(c -> c == '\n').count();
        assertEquals(1, newlineCount, "Output should be a single line (JSONL format)");
    }

    // --- RVTRACK observability fields ---

    @Test
    void testRvtrackFieldsPresent() {
        writer.writeLine(1, 1000L, "h", "A", "click", "algorithm", true, 0, 5, 1.0,
                540, 273, "Button",
                2, 0.45, 12, 3, 45, 160,
                false, null, null);
        JsonObject json = GSON.fromJson(captured.toString().trim(), JsonObject.class);

        assertTrue(json.has("score_tier"));
        assertTrue(json.has("saturation_rate"));
        assertTrue(json.has("capture_ms"));
        assertTrue(json.has("scoring_ms"));
        assertTrue(json.has("exec_ms"));
        assertTrue(json.has("total_ms"));
        assertFalse(json.has("ooa"), "ooa=false should not appear in output");
    }

    @Test
    void testRvtrackFieldValues() {
        writer.writeLine(1, 1000L, "h", "A", "click", "algorithm", true, 0, 5, 1.0,
                540, 273, "Button",
                2, 0.45, 12, 3, 45, 160,
                false, null, null);
        JsonObject json = GSON.fromJson(captured.toString().trim(), JsonObject.class);

        assertEquals(2, json.get("score_tier").getAsInt());
        assertEquals(0.45, json.get("saturation_rate").getAsDouble(), 0.001);
        assertEquals(12, json.get("capture_ms").getAsLong());
        assertEquals(3, json.get("scoring_ms").getAsLong());
        assertEquals(45, json.get("exec_ms").getAsLong());
        assertEquals(160, json.get("total_ms").getAsLong());
    }

    @Test
    void testRvtrackSentinelValuesOmitted() {
        writer.writeLine(1, 1000L, "h", "A", "click", "algorithm", true, 0, 5, 1.0,
                540, 273, "Button",
                -1, -1.0, -1, -1, -1, -1,
                false, null, null);
        JsonObject json = GSON.fromJson(captured.toString().trim(), JsonObject.class);

        assertFalse(json.has("score_tier"), "Sentinel -1 should omit score_tier");
        assertFalse(json.has("saturation_rate"), "Sentinel -1.0 should omit saturation_rate");
        assertFalse(json.has("capture_ms"));
        assertFalse(json.has("scoring_ms"));
        assertFalse(json.has("exec_ms"));
        assertFalse(json.has("total_ms"));
    }

    @Test
    void testRvtrackOoaFields() {
        writer.writeLine(1, 1000L, "", "", "RESTART", "ooa", false, 0, 5, 1.0,
                0, 0, null,
                -1, -1.0, -1, -1, -1, 50,
                true, "launcher_fastpath", "com.android.launcher3");
        JsonObject json = GSON.fromJson(captured.toString().trim(), JsonObject.class);

        assertTrue(json.get("ooa").getAsBoolean());
        assertEquals("launcher_fastpath", json.get("ooa_recovery").getAsString());
        assertEquals("com.android.launcher3", json.get("ooa_foreground_pkg").getAsString());
    }

    @Test
    void testRvtrackOoaFalseOmitsFields() {
        writer.writeLine(1, 1000L, "h", "A", "click", "algorithm", true, 0, 5, 1.0,
                540, 273, "Button",
                2, 0.5, 10, 2, 30, 100,
                false, null, null);
        JsonObject json = GSON.fromJson(captured.toString().trim(), JsonObject.class);

        assertFalse(json.has("ooa"));
        assertFalse(json.has("ooa_recovery"));
        assertFalse(json.has("ooa_foreground_pkg"));
    }

    @Test
    void testRvtrackFieldCountWithAllFields() {
        writer.writeLine(1, 1000L, "h", "A", "click", "algorithm", true, 0, 5, 1.0,
                540, 273, "Button",
                2, 0.45, 12, 3, 45, 160,
                false, null, null);
        JsonObject json = GSON.fromJson(captured.toString().trim(), JsonObject.class);
        // 13 base + 6 rvtrack (score_tier, saturation_rate, capture_ms, scoring_ms, exec_ms, total_ms)
        assertEquals(19, json.size());
    }

    @Test
    void testRvtrackOoaFieldCount() {
        writer.writeLine(1, 1000L, "", "", "RESTART", "ooa", false, 0, 5, 1.0,
                0, 0, null,
                -1, -1.0, -1, -1, -1, 50,
                true, "tolerance_exceeded", "com.chrome.browser");
        JsonObject json = GSON.fromJson(captured.toString().trim(), JsonObject.class);
        // 12 base (no widget_class) + 1 total_ms + 3 ooa fields = 16
        assertEquals(16, json.size());
    }

    // --- Score breakdown tests (task 5.2) ---

    @Test
    void testScoreBreakdownInTrace() {
        java.util.Map<String, Object> scores = new java.util.TreeMap<>();
        scores.put("mop", 300);
        scores.put("decay", -45);
        scores.put("coverage", 80);
        scores.put("wtg", 200);
        scores.put("total", 535);
        scores.put("stochastic", false);

        writer.writeLine(1, 1000L, "h", "A", "click", "algorithm", true, 0, 5, 1.0,
                540, 273, "Button",
                2, 0.45, 12, 3, 45, 160,
                false, null, null, scores);
        JsonObject json = GSON.fromJson(captured.toString().trim(), JsonObject.class);

        assertTrue(json.has("scores"), "Trace should contain scores field");
        JsonObject scoresObj = json.getAsJsonObject("scores");
        assertEquals(300, scoresObj.get("mop").getAsInt());
        assertEquals(-45, scoresObj.get("decay").getAsInt());
        assertEquals(80, scoresObj.get("coverage").getAsInt());
        assertEquals(200, scoresObj.get("wtg").getAsInt());
        assertEquals(535, scoresObj.get("total").getAsInt());
        assertFalse(scoresObj.get("stochastic").getAsBoolean());
    }

    @Test
    void testNullScoresOmitsField() {
        writer.writeLine(1, 1000L, "h", "A", "click", "algorithm", true, 0, 5, 1.0,
                540, 273, "Button",
                2, 0.45, 12, 3, 45, 160,
                false, null, null, null);
        JsonObject json = GSON.fromJson(captured.toString().trim(), JsonObject.class);

        assertFalse(json.has("scores"), "Null scores should not appear in trace");
    }

    @Test
    void testBasicOverloadProducesSameOutputAsExtendedWithSentinels() {
        // Write with basic overload
        writer.writeLine(1, 1000L, "h", "A", "click", "algo", true, 0, 5, 1.0,
                100, 200, "Button");
        String basic = captured.toString().trim();

        // Reset
        captured.reset();

        // Write with extended overload using sentinel values
        writer.writeLine(1, 1000L, "h", "A", "click", "algo", true, 0, 5, 1.0,
                100, 200, "Button",
                -1, -1.0, -1, -1, -1, -1,
                false, null, null);
        String extended = captured.toString().trim();

        assertEquals(basic, extended, "Basic overload should produce same output as extended with sentinels");
    }
}
