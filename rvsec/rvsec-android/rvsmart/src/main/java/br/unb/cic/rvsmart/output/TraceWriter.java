package br.unb.cic.rvsmart.output;

import com.google.gson.Gson;
import java.util.Map;
import java.util.TreeMap;

/**
 * Writes one JSON line to stdout per iteration capturing action, state, and timing.
 * JSONL format: each line is independent compact JSON.
 */
public class TraceWriter {
    private static final Gson GSON = new Gson();

    /**
     * Write a single trace line to stdout.
     */
    public void writeLine(int iteration, long timestampMs, String hash, String activity,
                          String actionType, String actionSource, boolean actionHadEffect,
                          int retries, int uniqueStates, double elapsedS,
                          int x, int y, String widgetClass) {
        writeLine(iteration, timestampMs, hash, activity, actionType, actionSource,
                actionHadEffect, retries, uniqueStates, elapsedS, x, y, widgetClass,
                -1, -1.0, -1, -1, -1, -1, false, null, null);
    }

    /**
     * Write a trace line with RVTRACK observability fields.
     * Fields with sentinel values (-1 for ints/longs, -1.0 for doubles) are omitted from output.
     * Null strings are omitted.
     */
    public void writeLine(int iteration, long timestampMs, String hash, String activity,
                          String actionType, String actionSource, boolean actionHadEffect,
                          int retries, int uniqueStates, double elapsedS,
                          int x, int y, String widgetClass,
                          int scoreTier, double saturationRate,
                          long captureMs, long scoringMs, long execMs, long totalMs,
                          boolean ooa, String ooaRecovery, String ooaForegroundPkg) {
        writeLine(iteration, timestampMs, hash, activity, actionType, actionSource,
                actionHadEffect, retries, uniqueStates, elapsedS, x, y, widgetClass,
                scoreTier, saturationRate, captureMs, scoringMs, execMs, totalMs,
                ooa, ooaRecovery, ooaForegroundPkg, null);
    }

    /**
     * Write a trace line with RVTRACK observability fields and per-scorer score breakdown.
     */
    public void writeLine(int iteration, long timestampMs, String hash, String activity,
                          String actionType, String actionSource, boolean actionHadEffect,
                          int retries, int uniqueStates, double elapsedS,
                          int x, int y, String widgetClass,
                          int scoreTier, double saturationRate,
                          long captureMs, long scoringMs, long execMs, long totalMs,
                          boolean ooa, String ooaRecovery, String ooaForegroundPkg,
                          Map<String, Object> scores) {
        TreeMap<String, Object> line = new TreeMap<>();
        line.put("iteration", iteration);
        line.put("timestamp_ms", timestampMs);
        line.put("hash", hash);
        line.put("activity", activity);
        line.put("action_type", actionType);
        line.put("action_source", actionSource);
        line.put("action_had_effect", actionHadEffect);
        line.put("action_x", x);
        line.put("action_y", y);
        if (widgetClass != null) {
            line.put("widget_class", widgetClass);
        }
        line.put("retries", retries);
        line.put("unique_states", uniqueStates);
        line.put("elapsed_s", elapsedS);
        // RVTRACK observability fields — omitted when not provided (sentinel values)
        if (scoreTier >= 0) line.put("score_tier", scoreTier);
        if (saturationRate >= 0.0) line.put("saturation_rate", saturationRate);
        if (captureMs >= 0) line.put("capture_ms", captureMs);
        if (scoringMs >= 0) line.put("scoring_ms", scoringMs);
        if (execMs >= 0) line.put("exec_ms", execMs);
        if (totalMs >= 0) line.put("total_ms", totalMs);
        if (ooa) {
            line.put("ooa", true);
            if (ooaRecovery != null) line.put("ooa_recovery", ooaRecovery);
            if (ooaForegroundPkg != null) line.put("ooa_foreground_pkg", ooaForegroundPkg);
        }
        if (scores != null && !scores.isEmpty()) {
            line.put("scores", scores);
        }
        System.out.println(GSON.toJson(line));
    }
}
