package br.unb.cic.rvsmart.strategy;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for ActivityBudgetTracker — per-Activity iteration budget.
 */
class ActivityBudgetTrackerTest {

    private ActivityBudgetTracker tracker;

    @BeforeEach
    void setUp() {
        // baseBudget=10, budgetPerWidget=3
        tracker = new ActivityBudgetTracker(10, 3);
    }

    @Test
    void budgetComputedCorrectly() {
        // 10 + 20*3 = 70
        tracker.registerActivity("MainActivity", 20);
        assertEquals(70, tracker.getRemainingBudget("MainActivity"));
    }

    @Test
    void isBudgetExhaustedReturnsFalseBeforeBudget() {
        tracker.registerActivity("MainActivity", 0); // budget = 10
        for (int i = 0; i < 9; i++) {
            tracker.recordIteration("MainActivity");
        }
        assertFalse(tracker.isBudgetExhausted("MainActivity"));
        assertEquals(1, tracker.getRemainingBudget("MainActivity"));
    }

    @Test
    void isBudgetExhaustedReturnsTrueAtBudget() {
        tracker.registerActivity("MainActivity", 0); // budget = 10
        for (int i = 0; i < 10; i++) {
            tracker.recordIteration("MainActivity");
        }
        assertTrue(tracker.isBudgetExhausted("MainActivity"));
        assertEquals(0, tracker.getRemainingBudget("MainActivity"));
    }

    @Test
    void unregisteredActivityReturnsNotExhausted() {
        assertFalse(tracker.isBudgetExhausted("UnknownActivity"));
        assertEquals(Integer.MAX_VALUE, tracker.getRemainingBudget("UnknownActivity"));
    }

    @Test
    void budgetIsPermanent() {
        tracker.registerActivity("MainActivity", 0); // budget = 10
        for (int i = 0; i < 15; i++) {
            tracker.recordIteration("MainActivity");
        }
        assertTrue(tracker.isBudgetExhausted("MainActivity"));
        assertEquals(0, tracker.getRemainingBudget("MainActivity"));
    }

    @Test
    void multipleActivitiesTrackedIndependently() {
        tracker.registerActivity("ActivityA", 5);  // budget = 10 + 5*3 = 25
        tracker.registerActivity("ActivityB", 10); // budget = 10 + 10*3 = 40

        // Exhaust A
        for (int i = 0; i < 25; i++) {
            tracker.recordIteration("ActivityA");
        }
        assertTrue(tracker.isBudgetExhausted("ActivityA"));
        assertFalse(tracker.isBudgetExhausted("ActivityB"));
        assertEquals(40, tracker.getRemainingBudget("ActivityB"));
    }
}
