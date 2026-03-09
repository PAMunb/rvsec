package br.unb.cic.rvsmart.output;

import br.unb.cic.rvsmart.graph.DynamicStateGraph;
import com.google.gson.Gson;
import java.text.SimpleDateFormat;
import java.util.*;

/**
 * Accumulates run statistics and writes final metrics report to stdout.
 * The last line of stdout is prefixed with RVSMART_METRICS: for extraction (INV-RSM-10).
 */
public class MetricsCollector {
    private static final String METRICS_PREFIX = "RVSMART_METRICS:";
    private static final Gson GSON = new Gson();

    // Metadata (set at construction)
    private final String packageName;
    private final String mode;
    private final int timeout;

    // Counters (incremented during run)
    private int iterations;
    private int algorithmActions;
    private int llmActions;
    private int multiAttemptRetries;
    private int forcedBacks;
    private int crashes;
    private int systemDialogs;

    // Coverage (set at end)
    private int uniqueMethods;
    private int totalCoverageEvents;
    private int mopMethodsReached;
    private boolean coverageEnabled;

    // LLM (Phase 2)
    private int llmTotalCalls;
    private int llmTokensIn;
    private int llmTokensOut;
    private double llmTotalTimeS;
    private int circuitBreakerTrips;

    public MetricsCollector(String packageName, String mode, int timeout) {
        this.packageName = packageName;
        this.mode = mode;
        this.timeout = timeout;
    }

    // Increment methods
    public void recordIteration(String source) {
        iterations++;
        if ("algorithm".equals(source)) algorithmActions++;
        else if ("llm".equals(source)) llmActions++;
    }
    public void recordRetries(int retries) { multiAttemptRetries += retries; }
    public void recordForcedBack() { forcedBacks++; }
    public void recordCrash() { crashes++; }
    public void recordSystemDialog() { systemDialogs++; }
    public void recordCoverageEvent(int unique, int total, int mop) {
        this.uniqueMethods = unique;
        this.totalCoverageEvents = total;
        this.mopMethodsReached = mop;
        this.coverageEnabled = total > 0;
    }
    public void recordLlmCall(int tokensIn, int tokensOut, double timeS) {
        llmTotalCalls++;
        llmTokensIn += tokensIn;
        llmTokensOut += tokensOut;
        llmTotalTimeS += timeS;
    }
    public void setCircuitBreakerTrips(int trips) {
        this.circuitBreakerTrips = trips;
    }

    /**
     * Write final metrics report to stdout with RVSMART_METRICS: prefix (INV-RSM-10).
     * Called exactly once at timeout.
     */
    public void writeFinalReport(long startTimeMs, DynamicStateGraph graph,
                                  int widgetsDiscovered, int widgetsInteracted,
                                  Set<String> uniqueActivities) {
        long elapsed = System.currentTimeMillis() - startTimeMs;
        double elapsedS = elapsed / 1000.0;
        double throughput = elapsedS > 0 ? iterations / elapsedS : 0;

        TreeMap<String, Object> report = new TreeMap<>();

        // metadata
        TreeMap<String, Object> metadata = new TreeMap<>();
        metadata.put("tool", "rvsmart");
        metadata.put("package", packageName);
        metadata.put("mode", mode);
        metadata.put("timeout", timeout);
        metadata.put("timestamp", getIsoTimestamp());
        metadata.put("version", "1.0.0");
        report.put("metadata", metadata);

        // exploration
        TreeMap<String, Object> exploration = new TreeMap<>();
        exploration.put("iterations", iterations);
        exploration.put("execution_time_s", round(elapsedS, 1));
        exploration.put("unique_states", graph.size());
        exploration.put("total_transitions", graph.totalTransitions());
        exploration.put("throughput_evt_per_s", round(throughput, 1));
        report.put("exploration", exploration);

        // decisions
        TreeMap<String, Object> decisions = new TreeMap<>();
        decisions.put("total_actions", iterations);
        decisions.put("algorithm_actions", algorithmActions);
        decisions.put("llm_actions", llmActions);
        decisions.put("multi_attempt_retries", multiAttemptRetries);
        decisions.put("forced_backs", forcedBacks);
        decisions.put("crashes", crashes);
        decisions.put("system_dialogs", systemDialogs);
        report.put("decisions", decisions);

        // ui_coverage
        TreeMap<String, Object> uiCoverage = new TreeMap<>();
        uiCoverage.put("unique_activities", uniqueActivities.size());
        uiCoverage.put("unique_hashes", graph.size());
        uiCoverage.put("widgets_discovered", widgetsDiscovered);
        uiCoverage.put("widgets_interacted", widgetsInteracted);
        double coverageRatio = widgetsDiscovered > 0 ? round((double) widgetsInteracted / widgetsDiscovered, 2) : 0.0;
        uiCoverage.put("coverage_ratio", coverageRatio);
        report.put("ui_coverage", uiCoverage);

        // confirmed_coverage
        TreeMap<String, Object> confirmedCoverage = new TreeMap<>();
        confirmedCoverage.put("enabled", coverageEnabled);
        confirmedCoverage.put("unique_methods", uniqueMethods);
        confirmedCoverage.put("total_events", totalCoverageEvents);
        confirmedCoverage.put("mop_methods_reached", mopMethodsReached);
        report.put("confirmed_coverage", confirmedCoverage);

        // llm
        TreeMap<String, Object> llm = new TreeMap<>();
        llm.put("total_calls", llmTotalCalls);
        llm.put("tokens_in", llmTokensIn);
        llm.put("tokens_out", llmTokensOut);
        llm.put("total_time_s", llmTotalTimeS);
        llm.put("circuit_breaker_trips", circuitBreakerTrips);
        report.put("llm", llm);

        System.out.println(METRICS_PREFIX + GSON.toJson(report));
    }

    private String getIsoTimestamp() {
        SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US);
        sdf.setTimeZone(TimeZone.getTimeZone("UTC"));
        return sdf.format(new Date());
    }

    private double round(double value, int decimals) {
        double factor = Math.pow(10, decimals);
        return Math.round(value * factor) / factor;
    }

    // Getters for testing
    public int getIterations() { return iterations; }
    public int getCrashes() { return crashes; }
    public int getForcedBacks() { return forcedBacks; }
    public int getMultiAttemptRetries() { return multiAttemptRetries; }
    public String getMetricsPrefix() { return METRICS_PREFIX; }
}
