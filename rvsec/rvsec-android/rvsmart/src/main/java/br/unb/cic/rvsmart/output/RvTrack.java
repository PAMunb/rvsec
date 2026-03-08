package br.unb.cic.rvsmart.output;

import android.util.Log;

/**
 * Structured decision logging via logcat with [RVTRACK:<CATEGORY>] prefix.
 * All methods are static. Counters are aggregated for MetricsCollector.
 */
public class RvTrack {
    private static final String TAG = "RVSMART";

    // Aggregate counters
    private static int backtrackCount;
    private static int restartCount;
    private static int multiAttemptRetries;
    private static int systemDialogsDismissed;
    private static int crashRecoveries;
    private static int stuckLevel1Count;
    private static int stuckLevel2Count;
    private static int circuitBreakerTrips;
    private static int oomThrottleEvents;

    // Test support: disable Log.i() in unit tests
    public static boolean logEnabled = true;

    public static void resetCounters() {
        backtrackCount = 0;
        restartCount = 0;
        multiAttemptRetries = 0;
        systemDialogsDismissed = 0;
        crashRecoveries = 0;
        stuckLevel1Count = 0;
        stuckLevel2Count = 0;
        circuitBreakerTrips = 0;
        oomThrottleEvents = 0;
    }

    public static void parse(int iter, String activity, int elements, String hash, long captureMs) {
        log("PARSE", "iter=" + iter + " activity=" + activity + " elements=" + elements
                + " hash=" + hash + " capture_ms=" + captureMs);
    }

    public static void route(int iter, String mode, String path, String reason) {
        log("ROUTE", "iter=" + iter + " mode=" + mode + " path=" + path + " reason=" + reason);
    }

    public static void rank(int iter, String topActions) {
        log("RANK", "iter=" + iter + " top=\"" + topActions + "\"");
    }

    public static void select(int iter, int tier, String action, String coords, int score, String source) {
        log("SELECT", "iter=" + iter + " tier=" + tier + " action=" + action
                + " coords=" + coords + " score=" + score + " source=" + source);
    }

    public static void exec(int iter, String action, String coords, String source, long injectMs) {
        log("EXEC", "iter=" + iter + " action=" + action + " coords=" + coords
                + " source=" + source + " inject_ms=" + injectMs);
    }

    public static void state(int iter, boolean changed, String fromHash, String toHash,
                             String fromActivity, String toActivity) {
        log("STATE", "iter=" + iter + " changed=" + changed + " from_hash=" + fromHash
                + " to_hash=" + toHash + " from_activity=" + fromActivity + " to_activity=" + toActivity);
    }

    public static void learn(int iter, double reward, int stuckLevel, boolean hadEffect, int retries) {
        log("LEARN", "iter=" + iter + " reward=" + reward + " stuck_level=" + stuckLevel
                + " had_effect=" + hadEffect + " retries=" + retries);
        if (retries > 0) multiAttemptRetries += retries;
    }

    public static void strategy(int iter, int tier, String reason, int untestedCount, double saturation) {
        log("STRATEGY", "iter=" + iter + " tier=" + tier + " reason=" + reason
                + " untested_count=" + untestedCount + " saturation=" + String.format("%.2f", saturation));
    }

    public static void backtrack(int iter, int level, String fromState, String toState, int hops, String reason) {
        log("BACKTRACK", "iter=" + iter + " level=" + level + " from_state=" + fromState
                + " to_state=" + toState + " hops=" + hops + " reason=" + reason);
        backtrackCount++;
    }

    public static void reward(int iter, String type, double value, int steps, double gamma) {
        log("REWARD", "iter=" + iter + " type=" + type + " value=" + value
                + " steps=" + steps + " gamma=" + gamma);
    }

    public static void coverage(int iter, String method, int eventCount, String source) {
        log("COVERAGE", "iter=" + iter + " method=" + method + " event_count=" + eventCount
                + " source=" + source);
    }

    public static void llm(int iter, int tokensIn, int tokensOut, long timeMs, boolean success) {
        log("LLM", "iter=" + iter + " tokens_in=" + tokensIn + " tokens_out=" + tokensOut
                + " time_ms=" + timeMs + " success=" + success);
    }

    public static void stuck(int iter, int level, String hash, int consecutive, String action) {
        log("STUCK", "iter=" + iter + " level=" + level + " hash=" + hash
                + " consecutive=" + consecutive + " action=" + action);
        if (level == 1) stuckLevel1Count++;
        else if (level == 2) stuckLevel2Count++;
    }

    public static void crash(int iter, String type, String action, long restartMs) {
        log("CRASH", "iter=" + iter + " type=" + type + " action=" + action
                + " restart_ms=" + restartMs);
        crashRecoveries++;
    }

    public static void ooa(int iter, String foregroundPkg, String recoveryType) {
        log("OOA", "iter=" + iter + " foreground=" + foregroundPkg + " recovery=" + recoveryType);
    }

    public static void cycle(int iter, long captureMs, long execMs, long totalMs) {
        log("CYCLE", "iter=" + iter + " capture=" + captureMs + "ms exec=" + execMs
                + "ms total=" + totalMs + "ms");
    }

    public static void oom(int iter, double freePct, long throttleMs, int maxItems) {
        log("OOM", "iter=" + iter + " free_pct=" + String.format("%.1f", freePct)
                + " throttle_ms=" + throttleMs + " max_items=" + maxItems);
        oomThrottleEvents++;
    }

    // Counter accessors
    public static int getBacktrackCount() { return backtrackCount; }
    public static int getRestartCount() { return restartCount; }
    public static int getMultiAttemptRetries() { return multiAttemptRetries; }
    public static int getSystemDialogsDismissed() { return systemDialogsDismissed; }
    public static int getCrashRecoveries() { return crashRecoveries; }
    public static int getStuckLevel1Count() { return stuckLevel1Count; }
    public static int getStuckLevel2Count() { return stuckLevel2Count; }
    public static int getCircuitBreakerTrips() { return circuitBreakerTrips; }
    public static int getOomThrottleEvents() { return oomThrottleEvents; }

    // External increment methods
    public static void incrementSystemDialogs() { systemDialogsDismissed++; }
    public static void incrementRestarts() { restartCount++; }
    public static void incrementCircuitBreakerTrips() { circuitBreakerTrips++; }

    private static void log(String category, String message) {
        if (logEnabled) {
            Log.i(TAG, "[RVTRACK:" + category + "] " + message);
        }
    }
}
