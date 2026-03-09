package br.unb.cic.rvsmart.llm;

/**
 * Circuit breaker for LLM calls (INV-RSM-09).
 *
 * Protects the agent loop from cascading LLM failures by transitioning through
 * three states:
 *   CLOSED    — normal operation, all requests pass through
 *   OPEN      — failure threshold exceeded; requests are blocked until openDurationMs elapses
 *   HALF_OPEN — test state after OPEN expires; one attempt is allowed to probe recovery
 *
 * After a successful call in HALF_OPEN, the breaker resets to CLOSED.
 * After a failed call in HALF_OPEN, it returns to OPEN with a fresh timestamp.
 *
 * All methods are synchronized for thread safety.
 */
public class LlmCircuitBreaker {

    private enum State {
        CLOSED,
        OPEN,
        HALF_OPEN
    }

    private final int failureThreshold;
    private final long openDurationMs;

    private State state;
    private int failureCount;
    private long openedAtMs;
    private int tripCount;

    /**
     * Default thresholds: 3 failures trip the breaker, 60 s recovery window.
     */
    public LlmCircuitBreaker() {
        this(3, 60_000L);
    }

    public LlmCircuitBreaker(int failureThreshold, long openDurationMs) {
        this.failureThreshold = failureThreshold;
        this.openDurationMs = openDurationMs;
        this.state = State.CLOSED;
        this.failureCount = 0;
        this.openedAtMs = 0L;
    }

    /**
     * Returns true when the breaker is OPEN and the recovery window has not elapsed.
     * Callers should use shouldAttempt() for the combined open/half-open check.
     */
    public synchronized boolean isOpen() {
        if (state == State.OPEN) {
            return System.currentTimeMillis() - openedAtMs < openDurationMs;
        }
        return false;
    }

    /**
     * Record a successful LLM call.
     * Resets the failure counter and closes the breaker regardless of current state.
     */
    public synchronized void recordSuccess() {
        failureCount = 0;
        state = State.CLOSED;
    }

    /**
     * Record a failed LLM call.
     * When the failure count reaches the threshold the breaker trips to OPEN.
     * A failure in HALF_OPEN immediately returns to OPEN with a fresh timestamp.
     */
    public synchronized void recordFailure() {
        failureCount++;
        if (state == State.HALF_OPEN || failureCount >= failureThreshold) {
            state = State.OPEN;
            openedAtMs = System.currentTimeMillis();
            tripCount++;
        }
    }

    /**
     * Determine whether an LLM call should be attempted now.
     *
     * CLOSED     → true (normal operation)
     * OPEN, time not elapsed → false (block the call)
     * OPEN, time elapsed     → transition to HALF_OPEN → true (probe)
     * HALF_OPEN  → true (probe in progress)
     */
    public synchronized boolean shouldAttempt() {
        switch (state) {
            case CLOSED:
                return true;
            case OPEN:
                if (System.currentTimeMillis() - openedAtMs >= openDurationMs) {
                    state = State.HALF_OPEN;
                    return true;
                }
                return false;
            case HALF_OPEN:
                return true;
            default:
                return false;
        }
    }

    /** For testing: expose the current state name. */
    public synchronized String getStateName() {
        return state.name();
    }

    /** For testing: expose the current failure count. */
    public synchronized int getFailureCount() {
        return failureCount;
    }

    /** Number of times the circuit breaker has tripped to OPEN state. */
    public synchronized int getTripCount() {
        return tripCount;
    }
}
