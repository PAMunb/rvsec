package br.unb.cic.rvsmart.core;

import br.unb.cic.rvsmart.llm.LlmCircuitBreaker;
import br.unb.cic.rvsmart.output.RvTrack;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for the first-visit routing behavior in RoutingManager.
 *
 * In MULTIMODE with PROBABILISTIC strategy, the first time a screen hash is
 * encountered the LLM path is taken unconditionally (subject to circuit breaker),
 * bypassing the probabilistic roll. Subsequent visits to the same hash fall
 * through to normal PROBABILISTIC logic.
 */
class RoutingManagerFirstVisitTest {

    private static final long SEED = 42L;
    private static final String HASH_A = "hash_a";
    private static final String HASH_B = "hash_b";

    @BeforeEach
    void setUp() {
        RvTrack.logEnabled = false;
    }

    // (a) MULTIMODE + PROBABILISTIC, first-ever visit to "hash_a" → true.
    // llmRatio=0.0 so PROBABILISTIC would always return false, proving the
    // first-visit path fires instead.
    @Test
    void multimode_firstVisit_returnsTrue() {
        LlmCircuitBreaker cb = new LlmCircuitBreaker(3, 60_000L);
        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.MULTIMODE,
                RoutingManager.Strategy.PROBABILISTIC,
                0.0, cb, SEED);

        assertTrue(rm.shouldUseLlm(HASH_A, false),
                "First visit to HASH_A must route to LLM even with llmRatio=0.0");
    }

    // (b) After visiting "hash_a" once, second call with "hash_a" falls through
    // to PROBABILISTIC (which with llmRatio=0.0 returns false).
    @Test
    void multimode_secondVisitSameHash_fallsToProbabilistic() {
        LlmCircuitBreaker cb = new LlmCircuitBreaker(3, 60_000L);
        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.MULTIMODE,
                RoutingManager.Strategy.PROBABILISTIC,
                0.0, cb, SEED);

        // First visit — consumes the first-visit path
        rm.shouldUseLlm(HASH_A, false);

        // Second visit — falls through to PROBABILISTIC with ratio=0.0 → false
        assertFalse(rm.shouldUseLlm(HASH_A, false),
                "Second visit to HASH_A must fall through to PROBABILISTIC (ratio=0.0 → false)");
    }

    // (c) After visiting "hash_a", first visit to "hash_b" → true.
    @Test
    void multimode_firstVisitDifferentHash_returnsTrue() {
        LlmCircuitBreaker cb = new LlmCircuitBreaker(3, 60_000L);
        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.MULTIMODE,
                RoutingManager.Strategy.PROBABILISTIC,
                0.0, cb, SEED);

        // Visit hash_a first
        rm.shouldUseLlm(HASH_A, false);

        // First visit to hash_b — must trigger the first-visit path
        assertTrue(rm.shouldUseLlm(HASH_B, false),
                "First visit to HASH_B must route to LLM even with llmRatio=0.0");
    }

    // (d) PURE_ALGORITHM mode → false regardless of first visit.
    @Test
    void pureAlgorithm_firstVisitIgnored_returnsFalse() {
        LlmCircuitBreaker cb = new LlmCircuitBreaker(3, 60_000L);
        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.PURE_ALGORITHM,
                RoutingManager.Strategy.PROBABILISTIC,
                0.0, cb, SEED);

        assertFalse(rm.shouldUseLlm(HASH_A, false),
                "PURE_ALGORITHM must return false even on first visit");
    }

    // (e) LLM_ONLY mode → true (circuit breaker allows).
    @Test
    void llmOnly_returnsTrueRegardless() {
        LlmCircuitBreaker cb = new LlmCircuitBreaker(3, 60_000L);
        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.LLM_ONLY,
                RoutingManager.Strategy.PROBABILISTIC,
                0.0, cb, SEED);

        assertTrue(rm.shouldUseLlm(HASH_A, false),
                "LLM_ONLY must return true when circuit breaker allows");
        assertTrue(rm.shouldUseLlm(HASH_A, false),
                "LLM_ONLY must return true on repeated visits");
    }

    // (f) Visit "hash_a", call reset(), visit "hash_a" again → true (first visit again).
    @Test
    void reset_clearsVisitedScreens() {
        LlmCircuitBreaker cb = new LlmCircuitBreaker(3, 60_000L);
        RoutingManager rm = new RoutingManager(
                RoutingManager.Mode.MULTIMODE,
                RoutingManager.Strategy.PROBABILISTIC,
                0.0, cb, SEED);

        // First visit → true
        assertTrue(rm.shouldUseLlm(HASH_A, false));
        // Second visit → falls through to PROBABILISTIC → false
        assertFalse(rm.shouldUseLlm(HASH_A, false));

        // Reset clears the visited set
        rm.reset();

        // After reset, HASH_A is treated as first visit again → true
        assertTrue(rm.shouldUseLlm(HASH_A, false),
                "After reset, HASH_A must be treated as first visit again");
    }
}
