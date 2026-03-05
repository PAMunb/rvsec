package br.unb.cic.rvsmart.core;

import br.unb.cic.rvsmart.llm.LlmCircuitBreaker;

import java.util.Random;

/**
 * Decides whether an iteration should use the LLM path or the algorithm path.
 *
 * Three operating modes control the top-level routing decision:
 *   PURE_ALGORITHM — always use the algorithm, never the LLM
 *   LLM_ONLY       — always attempt LLM (subject to circuit breaker)
 *   MULTIMODE      — blend LLM and algorithm using the configured strategy
 *
 * Three strategies apply within MULTIMODE:
 *   PROBABILISTIC  — route to LLM with probability llmRatio each iteration
 *   NEW_SCREEN_ONLY — route to LLM only on the first visit to an unseen screen
 *   STUCK_ONLY     — route to LLM only when the stuck detector signals blockage
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
        STUCK_ONLY
    }

    private final Mode mode;
    private final Strategy strategy;
    private final double llmRatio;
    private final LlmCircuitBreaker circuitBreaker;
    private final Random random;

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
     * @param currentScreen  the current screen state (unused in current strategies, reserved)
     * @param isNewScreen    true when the current screen hash was never seen before
     * @param isStuck        true when StuckDetector signals the agent is blocked
     * @return true when the LLM path should be attempted, false for algorithm path
     */
    public boolean shouldUseLlm(ScreenState currentScreen, boolean isNewScreen, boolean isStuck) {
        switch (mode) {
            case PURE_ALGORITHM:
                return false;

            case LLM_ONLY:
                return circuitBreaker.shouldAttempt();

            case MULTIMODE:
                return shouldUseLlmMultimode(isNewScreen, isStuck);

            default:
                return false;
        }
    }

    /**
     * Apply the MULTIMODE strategy to decide whether to route to LLM.
     * Circuit breaker is always consulted before allowing an LLM attempt.
     */
    private boolean shouldUseLlmMultimode(boolean isNewScreen, boolean isStuck) {
        switch (strategy) {
            case PROBABILISTIC:
                return random.nextDouble() < llmRatio && circuitBreaker.shouldAttempt();

            case NEW_SCREEN_ONLY:
                return isNewScreen && circuitBreaker.shouldAttempt();

            case STUCK_ONLY:
                return isStuck && circuitBreaker.shouldAttempt();

            default:
                return false;
        }
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
}
