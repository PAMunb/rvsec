package br.unb.cic.rvsmart.llm;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for LlmCircuitBreaker state machine.
 *
 * State transitions tested:
 *   CLOSED -> OPEN after failureThreshold failures
 *   OPEN   -> shouldAttempt() returns false while within openDurationMs
 *   OPEN   -> HALF_OPEN after openDurationMs elapses (tested with tiny duration)
 *   HALF_OPEN -> CLOSED on success
 *   HALF_OPEN -> OPEN on failure
 *   Any state -> CLOSED on success (recordSuccess resets)
 */
class LlmCircuitBreakerTest {

    private LlmCircuitBreaker breaker;

    @BeforeEach
    void setUp() {
        // threshold=3, duration=60s — standard configuration
        breaker = new LlmCircuitBreaker(3, 60_000L);
    }

    // --- Initial state ---

    @Test
    void testInitialStateIsClosed() {
        assertEquals("CLOSED", breaker.getStateName());
        assertTrue(breaker.shouldAttempt(), "New breaker must allow attempts");
        assertFalse(breaker.isOpen(), "New breaker must not be open");
    }

    // --- CLOSED -> failures -> OPEN ---

    @Test
    void testOneFailureKeepsClosed() {
        breaker.recordFailure();
        assertEquals("CLOSED", breaker.getStateName());
        assertTrue(breaker.shouldAttempt());
    }

    @Test
    void testTwoFailuresKeepsClosed() {
        breaker.recordFailure();
        breaker.recordFailure();
        assertEquals("CLOSED", breaker.getStateName());
        assertTrue(breaker.shouldAttempt());
    }

    @Test
    void testThreeFailuresTripsToOpen() {
        breaker.recordFailure();
        breaker.recordFailure();
        breaker.recordFailure();
        assertEquals("OPEN", breaker.getStateName());
        assertFalse(breaker.shouldAttempt(), "Tripped breaker must block attempts");
        assertTrue(breaker.isOpen());
    }

    // --- OPEN blocks requests ---

    @Test
    void testOpenBreakerBlocksAttempts() {
        tripBreaker(3);
        assertFalse(breaker.shouldAttempt());
        assertFalse(breaker.shouldAttempt());
    }

    @Test
    void testIsOpenReturnsTrueWhileOpen() {
        tripBreaker(3);
        assertTrue(breaker.isOpen());
    }

    // --- OPEN -> HALF_OPEN after duration elapses ---

    @Test
    void testOpenTransitionsToHalfOpenAfterDuration() throws InterruptedException {
        // Use a 50ms open duration so the test does not have to wait long
        LlmCircuitBreaker fastBreaker = new LlmCircuitBreaker(3, 50L);
        tripBreaker(fastBreaker, 3);
        assertEquals("OPEN", fastBreaker.getStateName());
        assertFalse(fastBreaker.shouldAttempt(), "Must block immediately after tripping");

        Thread.sleep(60); // Wait for open window to expire
        assertTrue(fastBreaker.shouldAttempt(), "Must allow attempt after open window expires");
        assertEquals("HALF_OPEN", fastBreaker.getStateName());
        assertFalse(fastBreaker.isOpen(), "isOpen must return false in HALF_OPEN");
    }

    // --- HALF_OPEN recovery ---

    @Test
    void testHalfOpenSuccessClosesBreaker() throws InterruptedException {
        LlmCircuitBreaker fastBreaker = new LlmCircuitBreaker(3, 50L);
        tripBreaker(fastBreaker, 3);
        Thread.sleep(60);
        fastBreaker.shouldAttempt(); // Triggers OPEN -> HALF_OPEN
        assertEquals("HALF_OPEN", fastBreaker.getStateName());

        fastBreaker.recordSuccess();
        assertEquals("CLOSED", fastBreaker.getStateName());
        assertTrue(fastBreaker.shouldAttempt());
    }

    @Test
    void testHalfOpenFailureReopens() throws InterruptedException {
        LlmCircuitBreaker fastBreaker = new LlmCircuitBreaker(3, 50L);
        tripBreaker(fastBreaker, 3);
        Thread.sleep(60);
        fastBreaker.shouldAttempt(); // OPEN -> HALF_OPEN
        assertEquals("HALF_OPEN", fastBreaker.getStateName());

        fastBreaker.recordFailure();
        assertEquals("OPEN", fastBreaker.getStateName());
        assertFalse(fastBreaker.shouldAttempt());
    }

    // --- recordSuccess resets from any state ---

    @Test
    void testSuccessFromClosedKeepsClosedAndResetsCount() {
        breaker.recordFailure();
        breaker.recordFailure();
        breaker.recordSuccess();
        assertEquals("CLOSED", breaker.getStateName());
        assertEquals(0, breaker.getFailureCount());
    }

    @Test
    void testSuccessFromOpenResetsToClosed() {
        tripBreaker(3);
        breaker.recordSuccess();
        assertEquals("CLOSED", breaker.getStateName());
        assertTrue(breaker.shouldAttempt());
    }

    // --- Failure count tracking ---

    @Test
    void testFailureCountIncrements() {
        breaker.recordFailure();
        assertEquals(1, breaker.getFailureCount());
        breaker.recordFailure();
        assertEquals(2, breaker.getFailureCount());
    }

    @Test
    void testSuccessResetsFailureCount() {
        breaker.recordFailure();
        breaker.recordFailure();
        breaker.recordSuccess();
        assertEquals(0, breaker.getFailureCount());
    }

    // --- Helper methods ---

    private void tripBreaker(int times) {
        tripBreaker(breaker, times);
    }

    private void tripBreaker(LlmCircuitBreaker b, int times) {
        for (int i = 0; i < times; i++) {
            b.recordFailure();
        }
    }
}
