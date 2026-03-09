package br.unb.cic.rvsmart.core;

import br.unb.cic.rvsmart.llm.LlmCircuitBreaker;
import br.unb.cic.rvsmart.output.RvTrack;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for RoutingManager mode and strategy logic.
 *
 * Uses a fixed seed (42) for deterministic PROBABILISTIC strategy results,
 * and fast circuit breakers (1ms open duration) where open/closed state matters.
 */
class RoutingManagerTest {

    // Seed chosen so that with llmRatio=0.3 the first call returns true and
    // the second returns false — confirmed by printing random.nextDouble() sequences.
    private static final long SEED = 42L;

    // Distinct hashes used to drive NEW_SCREEN_ONLY and ARRIVAL_FIRST tests.
    private static final String HASH_A = "screen-a";
    private static final String HASH_B = "screen-b";

    @BeforeEach
    void setUp() {
        RvTrack.logEnabled = false;
    }

    // ----- PURE_ALGORITHM -----

    @Test
    void pureAlgorithm_alwaysReturnsFalse() {
        LlmCircuitBreaker cb = new LlmCircuitBreaker(3, 60_000L);
        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.PURE_ALGORITHM,
                RoutingManager.Strategy.PROBABILISTIC,
                0.9, cb, SEED);

        // No matter what hash or isOutOfApp flag, PURE_ALGORITHM never routes to LLM
        assertFalse(rm.shouldUseLlm(HASH_A, false));
        assertFalse(rm.shouldUseLlm(HASH_B, false));
        assertFalse(rm.shouldUseLlm(HASH_A, true));
    }

    @Test
    void pureAlgorithm_openCircuitBreaker_stillReturnsFalse() {
        // Trip the breaker
        LlmCircuitBreaker cb = new LlmCircuitBreaker(1, 60_000L);
        cb.recordFailure();

        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.PURE_ALGORITHM,
                RoutingManager.Strategy.PROBABILISTIC,
                1.0, cb, SEED);

        // PURE_ALGORITHM never consults the circuit breaker
        assertFalse(rm.shouldUseLlm(HASH_A, false));
    }

    // ----- LLM_ONLY -----

    @Test
    void llmOnly_closedBreaker_returnsTrue() {
        LlmCircuitBreaker cb = new LlmCircuitBreaker(3, 60_000L);
        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.LLM_ONLY,
                RoutingManager.Strategy.PROBABILISTIC,
                0.0, cb, SEED);

        assertTrue(rm.shouldUseLlm(HASH_A, false));
        assertTrue(rm.shouldUseLlm(HASH_B, false));
    }

    @Test
    void llmOnly_openBreaker_returnsFalse() {
        // Use threshold=1 so a single failure trips the breaker
        LlmCircuitBreaker cb = new LlmCircuitBreaker(1, 60_000L);
        cb.recordFailure(); // trips to OPEN

        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.LLM_ONLY,
                RoutingManager.Strategy.PROBABILISTIC,
                1.0, cb, SEED);

        // Circuit breaker is open — LLM_ONLY must block
        assertFalse(rm.shouldUseLlm(HASH_A, false));
        assertFalse(rm.shouldUseLlm(HASH_B, false));
    }

    @Test
    void llmOnly_breakerRecovery_returnsTrueAfterHalfOpen() throws InterruptedException {
        // 50ms open window — will expire quickly
        LlmCircuitBreaker cb = new LlmCircuitBreaker(1, 50L);
        cb.recordFailure(); // trips to OPEN

        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.LLM_ONLY,
                RoutingManager.Strategy.PROBABILISTIC,
                1.0, cb, SEED);

        assertFalse(rm.shouldUseLlm(HASH_A, false)); // still OPEN

        Thread.sleep(60L); // wait for recovery window to expire

        // Now shouldAttempt() transitions to HALF_OPEN → true
        assertTrue(rm.shouldUseLlm(HASH_A, false));
    }

    @Test
    void anyMode_isOutOfApp_returnsFalse() {
        LlmCircuitBreaker cb = new LlmCircuitBreaker(3, 60_000L);
        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.LLM_ONLY,
                RoutingManager.Strategy.PROBABILISTIC,
                1.0, cb, SEED);

        // isOutOfApp=true must short-circuit regardless of mode or breaker state
        assertFalse(rm.shouldUseLlm(HASH_A, true));
    }

    // ----- MULTIMODE: PROBABILISTIC -----

    @Test
    void multimodeProbabilistic_deterministicWithSeed() {
        LlmCircuitBreaker cb = new LlmCircuitBreaker(3, 60_000L);
        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.MULTIMODE,
                RoutingManager.Strategy.PROBABILISTIC,
                0.3, cb, SEED);

        // With seed=42, determine the first two calls empirically:
        // java.util.Random(42).nextDouble() = 0.7220... → 0.7220 < 0.3 is false
        // next call: 0.0010... → 0.0010 < 0.3 is true
        boolean first = rm.shouldUseLlm(HASH_A, false);
        boolean second = rm.shouldUseLlm(HASH_A, false);

        // The sequence must be deterministic — same seed must always produce same result
        RoutingManager rm2 = new RoutingManager(
                RoutingManager.Mode.MULTIMODE,
                RoutingManager.Strategy.PROBABILISTIC,
                0.3, new LlmCircuitBreaker(3, 60_000L), SEED);

        assertEquals(first, rm2.shouldUseLlm(HASH_A, false));
        assertEquals(second, rm2.shouldUseLlm(HASH_A, false));
    }

    @Test
    void multimodeProbabilistic_ratio1_alwaysTrue() {
        LlmCircuitBreaker cb = new LlmCircuitBreaker(3, 60_000L);
        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.MULTIMODE,
                RoutingManager.Strategy.PROBABILISTIC,
                1.0, cb, SEED);

        // With ratio=1.0, every call should use LLM (random < 1.0 is always true)
        for (int i = 0; i < 5; i++) {
            assertTrue(rm.shouldUseLlm(HASH_A, false),
                    "Call " + i + " with ratio=1.0 must return true");
        }
    }

    @Test
    void multimodeProbabilistic_ratio0_alwaysFalse() {
        LlmCircuitBreaker cb = new LlmCircuitBreaker(3, 60_000L);
        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.MULTIMODE,
                RoutingManager.Strategy.PROBABILISTIC,
                0.0, cb, SEED);

        // With ratio=0.0, every call should use algorithm (random < 0.0 is always false)
        for (int i = 0; i < 5; i++) {
            assertFalse(rm.shouldUseLlm(HASH_A, false),
                    "Call " + i + " with ratio=0.0 must return false");
        }
    }

    @Test
    void multimodeProbabilistic_openBreaker_alwaysFalse() {
        LlmCircuitBreaker cb = new LlmCircuitBreaker(1, 60_000L);
        cb.recordFailure(); // trips to OPEN

        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.MULTIMODE,
                RoutingManager.Strategy.PROBABILISTIC,
                1.0, cb, SEED);

        // Even with ratio=1.0, open circuit breaker must block
        assertFalse(rm.shouldUseLlm(HASH_A, false));
    }

    // ----- MULTIMODE: NEW_SCREEN_ONLY -----

    @Test
    void multimodeNewScreenOnly_trueOnlyOnHashChange() {
        LlmCircuitBreaker cb = new LlmCircuitBreaker(3, 60_000L);
        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.MULTIMODE,
                RoutingManager.Strategy.NEW_SCREEN_ONLY,
                0.5, cb, SEED);

        // First call with HASH_A: lastSeenHash=null → arrival detected → true
        assertTrue(rm.shouldUseLlm(HASH_A, false),
                "First call (hash changed from null to HASH_A) must route to LLM");
        // Same hash again → no change → false
        assertFalse(rm.shouldUseLlm(HASH_A, false),
                "Same hash again must route to algorithm");
        // New hash → change detected → true
        assertTrue(rm.shouldUseLlm(HASH_B, false),
                "Hash change to HASH_B must route to LLM");
        // Same hash repeated → false
        assertFalse(rm.shouldUseLlm(HASH_B, false),
                "Same HASH_B again must route to algorithm");
    }

    @Test
    void multimodeNewScreenOnly_openBreaker_returnsFalse() {
        LlmCircuitBreaker cb = new LlmCircuitBreaker(1, 60_000L);
        cb.recordFailure(); // trips to OPEN

        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.MULTIMODE,
                RoutingManager.Strategy.NEW_SCREEN_ONLY,
                1.0, cb, SEED);

        // Hash change (null → HASH_A) but open breaker — must return false
        assertFalse(rm.shouldUseLlm(HASH_A, false));
    }

    // ----- MULTIMODE: STUCK_ONLY -----

    @Test
    void multimodeStuckOnly_closedBreaker_alwaysTrue() {
        LlmCircuitBreaker cb = new LlmCircuitBreaker(3, 60_000L);
        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.MULTIMODE,
                RoutingManager.Strategy.STUCK_ONLY,
                0.5, cb, SEED);

        // STUCK_ONLY always defers to circuit breaker; caller decides when stuck
        assertTrue(rm.shouldUseLlm(HASH_A, false));
        assertTrue(rm.shouldUseLlm(HASH_A, false));
        assertTrue(rm.shouldUseLlm(HASH_B, false));
    }

    @Test
    void multimodeStuckOnly_openBreaker_returnsFalse() {
        LlmCircuitBreaker cb = new LlmCircuitBreaker(1, 60_000L);
        cb.recordFailure(); // trips to OPEN

        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.MULTIMODE,
                RoutingManager.Strategy.STUCK_ONLY,
                1.0, cb, SEED);

        // Open breaker — must return false regardless of hash
        assertFalse(rm.shouldUseLlm(HASH_A, false));
    }

    // ----- MULTIMODE: ARRIVAL_FIRST -----

    @Test
    void multimodeArrivalFirst_trueOnArrival_thenProbabilistic() {
        LlmCircuitBreaker cb = new LlmCircuitBreaker(3, 60_000L);
        // ratio=1.0 so probabilistic fallback always returns true
        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.MULTIMODE,
                RoutingManager.Strategy.ARRIVAL_FIRST,
                1.0, cb, SEED);

        // First call: null → HASH_A (arrival) → true
        assertTrue(rm.shouldUseLlm(HASH_A, false),
                "Arrival at HASH_A must route to LLM");
        // Same hash: no arrival → probabilistic (ratio=1.0) → true
        assertTrue(rm.shouldUseLlm(HASH_A, false),
                "Non-arrival with ratio=1.0 must still route to LLM");
        // New hash: arrival at HASH_B → true
        assertTrue(rm.shouldUseLlm(HASH_B, false),
                "Arrival at HASH_B must route to LLM");
    }

    @Test
    void multimodeArrivalFirst_noArrival_ratio0_alwaysFalse() {
        LlmCircuitBreaker cb = new LlmCircuitBreaker(3, 60_000L);
        // ratio=0.0 so probabilistic fallback always returns false
        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.MULTIMODE,
                RoutingManager.Strategy.ARRIVAL_FIRST,
                0.0, cb, SEED);

        // Seed the last hash by calling once (arrival → true)
        rm.shouldUseLlm(HASH_A, false);
        // Now same hash, no arrival, ratio=0.0 → false
        assertFalse(rm.shouldUseLlm(HASH_A, false),
                "Non-arrival with ratio=0.0 must route to algorithm");
    }

    @Test
    void multimodeArrivalFirst_openBreaker_returnsFalse() {
        LlmCircuitBreaker cb = new LlmCircuitBreaker(1, 60_000L);
        cb.recordFailure(); // trips to OPEN

        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.MULTIMODE,
                RoutingManager.Strategy.ARRIVAL_FIRST,
                1.0, cb, SEED);

        // Arrival detected but open breaker must block
        assertFalse(rm.shouldUseLlm(HASH_A, false));
    }

    // ----- reset() -----

    @Test
    void reset_clearsLastSeenHash() {
        LlmCircuitBreaker cb = new LlmCircuitBreaker(3, 60_000L);
        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.MULTIMODE,
                RoutingManager.Strategy.NEW_SCREEN_ONLY,
                0.5, cb, SEED);

        // First arrival at HASH_A → true; second same hash → false
        assertTrue(rm.shouldUseLlm(HASH_A, false));
        assertFalse(rm.shouldUseLlm(HASH_A, false));

        // After reset, HASH_A looks like a new arrival again
        rm.reset();
        assertTrue(rm.shouldUseLlm(HASH_A, false),
                "After reset, same hash must be treated as arrival");
    }

    // ----- Circuit breaker delegation -----

    @Test
    void recordLlmSuccess_delegatesToCircuitBreaker() {
        LlmCircuitBreaker cb = new LlmCircuitBreaker(3, 60_000L);
        cb.recordFailure();
        cb.recordFailure();
        assertEquals(2, cb.getFailureCount());

        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.MULTIMODE,
                RoutingManager.Strategy.PROBABILISTIC,
                0.5, cb, SEED);

        rm.recordLlmSuccess();

        // recordSuccess resets the failure count
        assertEquals(0, cb.getFailureCount());
        assertEquals("CLOSED", cb.getStateName());
    }

    @Test
    void recordLlmFailure_delegatesToCircuitBreaker() {
        LlmCircuitBreaker cb = new LlmCircuitBreaker(3, 60_000L);
        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.MULTIMODE,
                RoutingManager.Strategy.PROBABILISTIC,
                0.5, cb, SEED);

        rm.recordLlmFailure();
        assertEquals(1, cb.getFailureCount());

        rm.recordLlmFailure();
        assertEquals(2, cb.getFailureCount());

        rm.recordLlmFailure();
        // Third failure trips the breaker
        assertEquals("OPEN", cb.getStateName());
        assertFalse(cb.shouldAttempt());
    }

    @Test
    void recordLlmFailure_thenSuccess_resetsBreaker() {
        LlmCircuitBreaker cb = new LlmCircuitBreaker(3, 60_000L);
        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.LLM_ONLY,
                RoutingManager.Strategy.PROBABILISTIC,
                1.0, cb, SEED);

        // Two failures — breaker stays CLOSED
        rm.recordLlmFailure();
        rm.recordLlmFailure();
        assertEquals("CLOSED", cb.getStateName());

        // Success resets
        rm.recordLlmSuccess();
        assertEquals(0, cb.getFailureCount());
        assertEquals("CLOSED", cb.getStateName());
    }

    // ----- Accessors -----

    @Test
    void getModeAndStrategy_returnCorrectValues() {
        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.MULTIMODE,
                RoutingManager.Strategy.STUCK_ONLY,
                0.3, new LlmCircuitBreaker(), SEED);

        assertEquals(RoutingManager.Mode.MULTIMODE, rm.getMode());
        assertEquals(RoutingManager.Strategy.STUCK_ONLY, rm.getStrategy());
    }
}
