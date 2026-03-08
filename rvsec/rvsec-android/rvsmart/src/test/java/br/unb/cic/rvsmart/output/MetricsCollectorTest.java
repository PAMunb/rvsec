package br.unb.cic.rvsmart.output;

import br.unb.cic.rvsmart.graph.DynamicStateGraph;
import com.google.gson.Gson;
import com.google.gson.JsonObject;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.util.HashSet;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for MetricsCollector: counter increments, prefix format (INV-RSM-10),
 * JSON structure, and final report content.
 */
class MetricsCollectorTest {

    private static final Gson GSON = new Gson();
    private static final String PACKAGE = "br.unb.cic.testapp";
    private static final String MODE = "pure_algorithm";
    private static final int TIMEOUT = 60;

    private MetricsCollector collector;
    private ByteArrayOutputStream captured;
    private PrintStream originalOut;

    @BeforeEach
    void setUp() {
        collector = new MetricsCollector(PACKAGE, MODE, TIMEOUT);
        captured = new ByteArrayOutputStream();
        originalOut = System.out;
        System.setOut(new PrintStream(captured));
    }

    @AfterEach
    void tearDown() {
        System.setOut(originalOut);
    }

    // --- Counter tests ---

    @Test
    void testInitialIterationsZero() {
        assertEquals(0, collector.getIterations());
    }

    @Test
    void testInitialCrashesZero() {
        assertEquals(0, collector.getCrashes());
    }

    @Test
    void testInitialForcedBacksZero() {
        assertEquals(0, collector.getForcedBacks());
    }

    @Test
    void testInitialRetriesZero() {
        assertEquals(0, collector.getMultiAttemptRetries());
    }

    @Test
    void testRecordIterationIncrementsTotal() {
        collector.recordIteration("algorithm");
        collector.recordIteration("llm");
        assertEquals(2, collector.getIterations());
    }

    @Test
    void testRecordCrashIncrements() {
        collector.recordCrash();
        collector.recordCrash();
        assertEquals(2, collector.getCrashes());
    }

    @Test
    void testRecordForcedBackIncrements() {
        collector.recordForcedBack();
        assertEquals(1, collector.getForcedBacks());
    }

    @Test
    void testRecordRetriesAccumulates() {
        collector.recordRetries(2);
        collector.recordRetries(3);
        assertEquals(5, collector.getMultiAttemptRetries());
    }

    // --- Final report tests ---

    private JsonObject writeFinalReportAndParse() {
        DynamicStateGraph graph = new DynamicStateGraph();
        graph.recordVisit("hash1", "Activity1");
        graph.recordVisit("hash2", "Activity2");
        graph.recordTransition("hash1", "hash2");

        Set<String> activities = new HashSet<>();
        activities.add("Activity1");
        activities.add("Activity2");

        // Use a start time slightly in the past for non-zero elapsed time
        long startTime = System.currentTimeMillis() - 5000;
        collector.writeFinalReport(startTime, graph, 10, 7, activities);

        String output = captured.toString().trim();
        assertTrue(output.startsWith("RVSMART_METRICS:"), "Output must start with RVSMART_METRICS: prefix");

        String jsonPart = output.substring("RVSMART_METRICS:".length());
        return GSON.fromJson(jsonPart, JsonObject.class);
    }

    @Test
    void testMetricsPrefixPresent() {
        writeFinalReportAndParse();
        // Assertion is inside writeFinalReportAndParse
    }

    @Test
    void testMetricsPrefixValue() {
        assertEquals("RVSMART_METRICS:", collector.getMetricsPrefix());
    }

    @Test
    void testFinalReportIsValidJson() {
        JsonObject report = writeFinalReportAndParse();
        assertNotNull(report);
    }

    @Test
    void testAllSixSectionsPresent() {
        JsonObject report = writeFinalReportAndParse();
        assertTrue(report.has("metadata"), "Missing metadata section");
        assertTrue(report.has("exploration"), "Missing exploration section");
        assertTrue(report.has("decisions"), "Missing decisions section");
        assertTrue(report.has("ui_coverage"), "Missing ui_coverage section");
        assertTrue(report.has("confirmed_coverage"), "Missing confirmed_coverage section");
        assertTrue(report.has("llm"), "Missing llm section");
    }

    @Test
    void testSectionCount() {
        JsonObject report = writeFinalReportAndParse();
        assertEquals(6, report.size(), "Report should have exactly 6 sections");
    }

    @Test
    void testMetadataFields() {
        JsonObject report = writeFinalReportAndParse();
        JsonObject metadata = report.getAsJsonObject("metadata");

        assertEquals("rvsmart", metadata.get("tool").getAsString());
        assertEquals(PACKAGE, metadata.get("package").getAsString());
        assertEquals(MODE, metadata.get("mode").getAsString());
        assertEquals(TIMEOUT, metadata.get("timeout").getAsInt());
        assertTrue(metadata.has("timestamp"));
        assertEquals("1.0.0", metadata.get("version").getAsString());
    }

    @Test
    void testExplorationFields() {
        collector.recordIteration("algorithm");
        collector.recordIteration("algorithm");

        JsonObject report = writeFinalReportAndParse();
        JsonObject exploration = report.getAsJsonObject("exploration");

        assertEquals(2, exploration.get("iterations").getAsInt());
        assertTrue(exploration.has("execution_time_s"));
        assertEquals(2, exploration.get("unique_states").getAsInt());
        assertEquals(1, exploration.get("total_transitions").getAsInt());
        assertTrue(exploration.has("throughput_evt_per_s"));
    }

    @Test
    void testDecisionsFields() {
        collector.recordIteration("algorithm");
        collector.recordIteration("llm");
        collector.recordCrash();
        collector.recordForcedBack();
        collector.recordRetries(2);
        collector.recordSystemDialog();

        JsonObject report = writeFinalReportAndParse();
        JsonObject decisions = report.getAsJsonObject("decisions");

        assertEquals(2, decisions.get("total_actions").getAsInt());
        assertEquals(1, decisions.get("algorithm_actions").getAsInt());
        assertEquals(1, decisions.get("llm_actions").getAsInt());
        assertEquals(2, decisions.get("multi_attempt_retries").getAsInt());
        assertEquals(1, decisions.get("forced_backs").getAsInt());
        assertEquals(1, decisions.get("crashes").getAsInt());
        assertEquals(1, decisions.get("system_dialogs").getAsInt());
    }

    @Test
    void testUiCoverageFields() {
        JsonObject report = writeFinalReportAndParse();
        JsonObject uiCoverage = report.getAsJsonObject("ui_coverage");

        assertEquals(2, uiCoverage.get("unique_activities").getAsInt());
        assertEquals(2, uiCoverage.get("unique_hashes").getAsInt());
        assertEquals(10, uiCoverage.get("widgets_discovered").getAsInt());
        assertEquals(7, uiCoverage.get("widgets_interacted").getAsInt());
        assertEquals(0.7, uiCoverage.get("coverage_ratio").getAsDouble(), 0.01);
    }

    @Test
    void testConfirmedCoverageFieldsDefault() {
        JsonObject report = writeFinalReportAndParse();
        JsonObject coverage = report.getAsJsonObject("confirmed_coverage");

        assertFalse(coverage.get("enabled").getAsBoolean());
        assertEquals(0, coverage.get("unique_methods").getAsInt());
        assertEquals(0, coverage.get("total_events").getAsInt());
        assertEquals(0, coverage.get("mop_methods_reached").getAsInt());
    }

    @Test
    void testConfirmedCoverageAfterRecording() {
        collector.recordCoverageEvent(15, 100, 5);

        JsonObject report = writeFinalReportAndParse();
        JsonObject coverage = report.getAsJsonObject("confirmed_coverage");

        assertTrue(coverage.get("enabled").getAsBoolean());
        assertEquals(15, coverage.get("unique_methods").getAsInt());
        assertEquals(100, coverage.get("total_events").getAsInt());
        assertEquals(5, coverage.get("mop_methods_reached").getAsInt());
    }

    @Test
    void testLlmFieldsDefault() {
        JsonObject report = writeFinalReportAndParse();
        JsonObject llm = report.getAsJsonObject("llm");

        assertEquals(0, llm.get("total_calls").getAsInt());
        assertEquals(0, llm.get("tokens_in").getAsInt());
        assertEquals(0, llm.get("tokens_out").getAsInt());
        assertEquals(0.0, llm.get("total_time_s").getAsDouble(), 0.001);
        assertEquals(0, llm.get("circuit_breaker_trips").getAsInt());
    }

    @Test
    void testThroughputCalculation() {
        // Record 10 iterations, with 5 seconds elapsed
        for (int i = 0; i < 10; i++) {
            collector.recordIteration("algorithm");
        }

        DynamicStateGraph graph = new DynamicStateGraph();
        graph.recordVisit("h1", "A1");
        Set<String> activities = new HashSet<>();
        activities.add("A1");

        long startTime = System.currentTimeMillis() - 5000;
        collector.writeFinalReport(startTime, graph, 0, 0, activities);

        String output = captured.toString().trim();
        String jsonPart = output.substring("RVSMART_METRICS:".length());
        JsonObject report = GSON.fromJson(jsonPart, JsonObject.class);
        JsonObject exploration = report.getAsJsonObject("exploration");

        double throughput = exploration.get("throughput_evt_per_s").getAsDouble();
        // 10 iterations / ~5 seconds = ~2.0 evt/s (allow some tolerance for timing)
        assertTrue(throughput > 1.0, "Throughput should be > 1.0 for 10 iterations in ~5s");
        assertTrue(throughput < 5.0, "Throughput should be < 5.0 for 10 iterations in ~5s");
    }

    @Test
    void testOutputIsSingleLine() {
        writeFinalReportAndParse();
        String output = captured.toString();
        long newlineCount = output.chars().filter(c -> c == '\n').count();
        assertEquals(1, newlineCount, "Report should be a single line");
    }

    @Test
    void testCoverageRatioZeroWhenNoWidgets() {
        DynamicStateGraph graph = new DynamicStateGraph();
        graph.recordVisit("h1", "A1");
        Set<String> activities = new HashSet<>();
        activities.add("A1");

        long startTime = System.currentTimeMillis() - 1000;
        collector.writeFinalReport(startTime, graph, 0, 0, activities);

        String output = captured.toString().trim();
        String jsonPart = output.substring("RVSMART_METRICS:".length());
        JsonObject report = GSON.fromJson(jsonPart, JsonObject.class);
        JsonObject uiCoverage = report.getAsJsonObject("ui_coverage");

        assertEquals(0.0, uiCoverage.get("coverage_ratio").getAsDouble(), 0.001);
    }
}
