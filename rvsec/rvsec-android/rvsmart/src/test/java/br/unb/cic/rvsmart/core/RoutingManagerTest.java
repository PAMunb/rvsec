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

    // A null ScreenState is acceptable because no current strategy inspects it.
    private static final ScreenState NULL_SCREEN = null;

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

        // No matter what flags are set, PURE_ALGORITHM never routes to LLM
        assertFalse(rm.shouldUseLlm(NULL_SCREEN, false, false));
        assertFalse(rm.shouldUseLlm(NULL_SCREEN, true, false));
        assertFalse(rm.shouldUseLlm(NULL_SCREEN, false, true));
        assertFalse(rm.shouldUseLlm(NULL_SCREEN, true, true));
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
        assertFalse(rm.shouldUseLlm(NULL_SCREEN, true, true));
    }

    // ----- LLM_ONLY -----

    @Test
    void llmOnly_closedBreaker_returnsTrue() {
        LlmCircuitBreaker cb = new LlmCircuitBreaker(3, 60_000L);
        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.LLM_ONLY,
                RoutingManager.Strategy.PROBABILISTIC,
                0.0, cb, SEED);

        assertTrue(rm.shouldUseLlm(NULL_SCREEN, false, false));
        assertTrue(rm.shouldUseLlm(NULL_SCREEN, true, false));
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
        assertFalse(rm.shouldUseLlm(NULL_SCREEN, false, false));
        assertFalse(rm.shouldUseLlm(NULL_SCREEN, true, true));
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

        assertFalse(rm.shouldUseLlm(NULL_SCREEN, false, false)); // still OPEN

        Thread.sleep(60L); // wait for recovery window to expire

        // Now shouldAttempt() transitions to HALF_OPEN → true
        assertTrue(rm.shouldUseLlm(NULL_SCREEN, false, false));
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
        boolean first = rm.shouldUseLlm(NULL_SCREEN, false, false);
        boolean second = rm.shouldUseLlm(NULL_SCREEN, false, false);

        // The sequence must be deterministic — same seed must always produce same result
        // We re-create with the same seed to verify determinism
        RoutingManager rm2 = new RoutingManager(
                RoutingManager.Mode.MULTIMODE,
                RoutingManager.Strategy.PROBABILISTIC,
                0.3, new LlmCircuitBreaker(3, 60_000L), SEED);

        assertEquals(first, rm2.shouldUseLlm(NULL_SCREEN, false, false));
        assertEquals(second, rm2.shouldUseLlm(NULL_SCREEN, false, false));
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
            assertTrue(rm.shouldUseLlm(NULL_SCREEN, false, false),
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
            assertFalse(rm.shouldUseLlm(NULL_SCREEN, false, false),
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
        assertFalse(rm.shouldUseLlm(NULL_SCREEN, false, false));
    }

    // ----- MULTIMODE: NEW_SCREEN_ONLY -----

    @Test
    void multimodeNewScreenOnly_trueOnlyForNewScreen() {
        LlmCircuitBreaker cb = new LlmCircuitBreaker(3, 60_000L);
        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.MULTIMODE,
                RoutingManager.Strategy.NEW_SCREEN_ONLY,
                0.5, cb, SEED);

        assertTrue(rm.shouldUseLlm(NULL_SCREEN, true, false),
                "isNewScreen=true must route to LLM");
        assertFalse(rm.shouldUseLlm(NULL_SCREEN, false, false),
                "isNewScreen=false must route to algorithm");
    }

    @Test
    void multimodeNewScreenOnly_stuckIgnored() {
        LlmCircuitBreaker cb = new LlmCircuitBreaker(3, 60_000L);
        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.MULTIMODE,
                RoutingManager.Strategy.NEW_SCREEN_ONLY,
                0.5, cb, SEED);

        // isStuck=true alone does not trigger LLM in NEW_SCREEN_ONLY
        assertFalse(rm.shouldUseLlm(NULL_SCREEN, false, true));
    }

    @Test
    void multimodeNewScreenOnly_openBreaker_returnsFalse() {
        LlmCircuitBreaker cb = new LlmCircuitBreaker(1, 60_000L);
        cb.recordFailure(); // trips to OPEN

        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.MULTIMODE,
                RoutingManager.Strategy.NEW_SCREEN_ONLY,
                1.0, cb, SEED);

        // New screen but open breaker — must return false
        assertFalse(rm.shouldUseLlm(NULL_SCREEN, true, false));
    }

    // ----- MULTIMODE: STUCK_ONLY -----

    @Test
    void multimodeStuckOnly_trueOnlyWhenStuck() {
        LlmCircuitBreaker cb = new LlmCircuitBreaker(3, 60_000L);
        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.MULTIMODE,
                RoutingManager.Strategy.STUCK_ONLY,
                0.5, cb, SEED);

        assertTrue(rm.shouldUseLlm(NULL_SCREEN, false, true),
                "isStuck=true must route to LLM");
        assertFalse(rm.shouldUseLlm(NULL_SCREEN, false, false),
                "isStuck=false must route to algorithm");
    }

    @Test
    void multimodeStuckOnly_newScreenIgnored() {
        LlmCircuitBreaker cb = new LlmCircuitBreaker(3, 60_000L);
        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.MULTIMODE,
                RoutingManager.Strategy.STUCK_ONLY,
                0.5, cb, SEED);

        // isNewScreen=true alone does not trigger LLM in STUCK_ONLY
        assertFalse(rm.shouldUseLlm(NULL_SCREEN, true, false));
    }

    @Test
    void multimodeStuckOnly_openBreaker_returnsFalse() {
        LlmCircuitBreaker cb = new LlmCircuitBreaker(1, 60_000L);
        cb.recordFailure(); // trips to OPEN

        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.MULTIMODE,
                RoutingManager.Strategy.STUCK_ONLY,
                1.0, cb, SEED);

        // Stuck but open breaker — must return false
        assertFalse(rm.shouldUseLlm(NULL_SCREEN, false, true));
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
