package br.unb.cic.rvsmart.core;

import br.unb.cic.rvsmart.llm.LlmCircuitBreaker;

import java.util.HashSet;
import java.util.Random;
import java.util.Set;

/**
 * Decides whether an iteration should use the LLM path or the algorithm path.
 *
 * Three operating modes control the top-level routing decision:
 *   PURE_ALGORITHM — always use the algorithm, never the LLM
 *   LLM_ONLY       — always attempt LLM (subject to circuit breaker)
 *   MULTIMODE      — blend LLM and algorithm using the configured strategy
 *
 * Four strategies apply within MULTIMODE:
 *   PROBABILISTIC   — route to LLM with probability llmRatio each iteration
 *   NEW_SCREEN_ONLY — route to LLM only when the current screen hash differs from the
 *                     last seen hash (i.e., a screen transition just occurred)
 *   STUCK_ONLY      — route to LLM whenever the circuit breaker permits (caller is
 *                     responsible for only calling when stuck)
 *   ARRIVAL_FIRST   — route to LLM unconditionally on screen arrival; fall back to
 *                     probabilistic (llmRatio) on subsequent iterations at the same screen
 *
 * The circuit breaker is checked for all LLM attempts in LLM_ONLY and MULTIMODE.
 * PURE_ALGORITHM never touches the circuit breaker.
 */
public class RoutingManager {

    public enum Mode {
        PURE_ALGORITHM,
        MULTIMODE,
        LLM_ONLY
    }

    public enum Strategy {
        PROBABILISTIC,
        NEW_SCREEN_ONLY,
        STUCK_ONLY,
        ARRIVAL_FIRST
    }

    private final Mode mode;
    private final Strategy strategy;
    private final double llmRatio;
    private final LlmCircuitBreaker circuitBreaker;
    private final Random random;

    // Hash of the last screen seen by shouldUseLlm; used by NEW_SCREEN_ONLY and
    // ARRIVAL_FIRST to detect screen transitions without requiring external state.
    private String lastSeenHash = null;
    private final Set<String> visitedScreens = new HashSet<>();

    /**
     * @param mode           operating mode (PURE_ALGORITHM, MULTIMODE, LLM_ONLY)
     * @param strategy       routing strategy for MULTIMODE (ignored in other modes)
     * @param llmRatio       probability [0.0, 1.0] used by PROBABILISTIC strategy
     * @param circuitBreaker circuit breaker protecting LLM calls
     * @param seed           random seed for deterministic testing; use -1 for non-deterministic
     */
    public RoutingManager(Mode mode, Strategy strategy, double llmRatio,
                          LlmCircuitBreaker circuitBreaker, long seed) {
        this.mode = mode;
        this.strategy = strategy;
        this.llmRatio = llmRatio;
        this.circuitBreaker = circuitBreaker;
        this.random = seed >= 0 ? new Random(seed) : new Random();
    }

    /**
     * Decide whether to use the LLM path for the current iteration.
     *
     * @param currentHash  screen content hash for the current iteration; used by
     *                     NEW_SCREEN_ONLY and ARRIVAL_FIRST to detect screen transitions
     * @param isOutOfApp   true when the agent has navigated outside the target app;
     *                     LLM is never invoked out-of-app regardless of mode or strategy
     * @return true when the LLM path should be attempted, false for algorithm path
     */
    public boolean shouldUseLlm(String currentHash, boolean isOutOfApp) {
        if (isOutOfApp) {
            return false;
        }

        switch (mode) {
            case PURE_ALGORITHM:
                return false;

            case LLM_ONLY:
                return circuitBreaker.shouldAttempt();

            case MULTIMODE:
                if (!visitedScreens.contains(currentHash)) {
                    visitedScreens.add(currentHash);
                    lastSeenHash = currentHash;
                    return circuitBreaker.shouldAttempt();
                }
                return shouldUseLlmMultimode(currentHash);

            default:
                return false;
        }
    }

    /**
     * Apply the MULTIMODE strategy to decide whether to route to LLM.
     * Circuit breaker is always consulted before allowing an LLM attempt.
     */
    private boolean shouldUseLlmMultimode(String currentHash) {
        switch (strategy) {
            case PROBABILISTIC:
                return random.nextDouble() < llmRatio && circuitBreaker.shouldAttempt();

            case NEW_SCREEN_ONLY: {
                // Route to LLM only when the screen hash changed since the last call.
                boolean isArrival = !currentHash.equals(lastSeenHash);
                lastSeenHash = currentHash;
                return isArrival && circuitBreaker.shouldAttempt();
            }

            case STUCK_ONLY:
                // Caller is responsible for only invoking shouldUseLlm when stuck;
                // strategy simply defers to the circuit breaker.
                return circuitBreaker.shouldAttempt();

            case ARRIVAL_FIRST: {
                // Use LLM unconditionally on the first iteration at a new screen, then
                // fall back to probabilistic (llmRatio) on subsequent iterations there.
                boolean isArrival = !currentHash.equals(lastSeenHash);
                lastSeenHash = currentHash;
                if (isArrival) return circuitBreaker.shouldAttempt();
                return random.nextDouble() < llmRatio && circuitBreaker.shouldAttempt();
            }

            default:
                return false;
        }
    }

    /**
     * Reset internal state accumulated across iterations.
     * Call this when starting a new exploration session so that NEW_SCREEN_ONLY and
     * ARRIVAL_FIRST do not carry over hash state from a previous run.
     */
    public void reset() {
        lastSeenHash = null;
        visitedScreens.clear();
    }

    /**
     * Record that an LLM call succeeded.
     * Delegates to the circuit breaker so it can reset failure counters.
     */
    public void recordLlmSuccess() {
        circuitBreaker.recordSuccess();
    }

    /**
     * Record that an LLM call failed.
     * Delegates to the circuit breaker so it can increment failure counters
     * and potentially trip to OPEN state.
     */
    public void recordLlmFailure() {
        circuitBreaker.recordFailure();
    }

    /** Expose mode for testing and logging. */
    public Mode getMode() {
        return mode;
    }

    /** Expose strategy for testing and logging. */
    public Strategy getStrategy() {
        return strategy;
    }

    /** Number of times the circuit breaker has tripped to OPEN state. */
    public int getCircuitBreakerTripCount() {
        return circuitBreaker.getTripCount();
    }
}
