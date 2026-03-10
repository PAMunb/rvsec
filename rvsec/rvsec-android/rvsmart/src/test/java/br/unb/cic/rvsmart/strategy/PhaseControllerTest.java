package br.unb.cic.rvsmart.strategy;

import br.unb.cic.rvsmart.core.UICoverageTracker;
import br.unb.cic.rvsmart.graph.ContentGraph;
import br.unb.cic.rvsmart.graph.ContentNode;
import br.unb.cic.rvsmart.output.RvTrack;
import br.unb.cic.rvsmart.strategy.PhaseController.Phase;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.mock;

class PhaseControllerTest {

    private ContentGraph contentGraph;
    private UICoverageTracker uiCoverageTracker;
    private PlateauDetector plateauDetector;
    private PhaseController controller;

    @BeforeEach
    void setUp() {
        RvTrack.logEnabled = false;
        contentGraph = new ContentGraph();
        uiCoverageTracker = mock(UICoverageTracker.class);
        plateauDetector = new PlateauDetector();
        controller = new PhaseController(contentGraph, uiCoverageTracker, plateauDetector);
    }

    // -------------------------------------------------------------------------
    // 4.4.1 — Phase starts at PHASE_1
    // -------------------------------------------------------------------------

    @Test
    void testInitialPhaseIsPhase1() {
        assertEquals(PhaseController.Phase.PHASE_1, controller.currentPhase());
    }

    // -------------------------------------------------------------------------
    // 4.4.2 — PHASE_1 → PHASE_2 when no untested actions remain
    // -------------------------------------------------------------------------

    @Test
    void testPhase1TransitionsToPhase2WhenAllActionsExecuted() {
        // Add a content node with 2 total actions, both executed.
        ContentNode node = contentGraph.getOrCreate("hash-A", "MainActivity");
        node.setTotalActions(2);
        node.recordAction("click@100,200", "Button");
        node.recordAction("click@300,400", "Button");

        // With all actions executed, one iteration should advance to PHASE_2.
        controller.onIteration(0);

        assertEquals(PhaseController.Phase.PHASE_2, controller.currentPhase());
    }

    @Test
    void testPhase1StaysWhenUntestedActionsRemain() {
        // Node has 3 total actions but only 1 executed.
        ContentNode node = contentGraph.getOrCreate("hash-B", "MainActivity");
        node.setTotalActions(3);
        node.recordAction("click@100,200", "Button");

        controller.onIteration(0);

        assertEquals(PhaseController.Phase.PHASE_1, controller.currentPhase());
    }

    // -------------------------------------------------------------------------
    // 4.4.3 — New content state resets to PHASE_1 from any phase
    // -------------------------------------------------------------------------

    @Test
    void testNewContentStateResetsToPhase1FromPhase2() {
        // Advance to PHASE_2: empty graph means no untested actions.
        controller.onIteration(0);
        assertEquals(PhaseController.Phase.PHASE_2, controller.currentPhase());

        // Discovering a new content state must reset to PHASE_1.
        controller.onNewContentState("abcd1234");
        assertEquals(PhaseController.Phase.PHASE_1, controller.currentPhase());
    }

    @Test
    void testNewContentStateResetsToPhase1FromPhase3() {
        // Drive PHASE_2 → PHASE_3 via plateau.
        controller.onIteration(0); // PHASE_1 → PHASE_2 (empty graph)
        for (int i = 0; i < PlateauDetector.WINDOW_SIZE; i++) {
            controller.onIteration(0);
        }
        assertEquals(PhaseController.Phase.PHASE_3, controller.currentPhase());

        controller.onNewContentState("beef1234");
        assertEquals(PhaseController.Phase.PHASE_1, controller.currentPhase());
    }

    // -------------------------------------------------------------------------
    // 4.4.4 — PHASE_2 → PHASE_3 after plateau
    // -------------------------------------------------------------------------

    @Test
    void testPhase2TransitionsToPhase3AfterPlateau() {
        // Start in PHASE_2: empty graph, trigger PHASE_1 → PHASE_2.
        controller.onIteration(0);
        assertEquals(PhaseController.Phase.PHASE_2, controller.currentPhase());

        // Feed WINDOW_SIZE zero-coverage iterations to build plateau.
        for (int i = 0; i < PlateauDetector.WINDOW_SIZE; i++) {
            controller.onIteration(0);
        }

        assertEquals(PhaseController.Phase.PHASE_3, controller.currentPhase());
    }

    @Test
    void testPhase2DoesNotTransitionBeforePlateauWindowFull() {
        // Advance to PHASE_2 with one iteration (this also feeds the plateau detector).
        controller.onIteration(0);
        assertEquals(PhaseController.Phase.PHASE_2, controller.currentPhase());

        // The first onIteration() call already fed 1 entry into the plateau detector.
        // To avoid filling the WINDOW_SIZE-entry window, add only WINDOW_SIZE - 2 more.
        // Total: 1 (PHASE_1 transition) + WINDOW_SIZE-2 (PHASE_2) = WINDOW_SIZE-1 < WINDOW_SIZE.
        for (int i = 0; i < PlateauDetector.WINDOW_SIZE - 2; i++) {
            controller.onIteration(0);
        }

        assertEquals(PhaseController.Phase.PHASE_2, controller.currentPhase());
    }

    // -------------------------------------------------------------------------
    // 4.4.5 — Cluster forcing: after 20 re-entries, isClusterForced returns true
    // -------------------------------------------------------------------------

    @Test
    void testClusterForcedAfterThresholdReentries() {
        String structHash = "a1b2c3d4";

        assertFalse(controller.isClusterForced(structHash));

        for (int i = 0; i < PhaseController.CLUSTER_FORCE_THRESHOLD; i++) {
            controller.onPhase1Entry(structHash);
        }

        assertTrue(controller.isClusterForced(structHash));
    }

    @Test
    void testClusterNotForcedBelowThreshold() {
        String structHash = "99aabbcc";

        for (int i = 0; i < PhaseController.CLUSTER_FORCE_THRESHOLD - 1; i++) {
            controller.onPhase1Entry(structHash);
        }

        assertFalse(controller.isClusterForced(structHash));
    }

    // -------------------------------------------------------------------------
    // 4.4.6 — Different clusters tracked independently
    // -------------------------------------------------------------------------

    @Test
    void testClustersTrackedIndependently() {
        String clusterA = "clusterA01";
        String clusterB = "clusterB01";

        // Force clusterA to threshold.
        for (int i = 0; i < PhaseController.CLUSTER_FORCE_THRESHOLD; i++) {
            controller.onPhase1Entry(clusterA);
        }

        // clusterB has only 1 re-entry.
        controller.onPhase1Entry(clusterB);

        assertTrue(controller.isClusterForced(clusterA));
        assertFalse(controller.isClusterForced(clusterB));
    }

    // -------------------------------------------------------------------------
    // BUG-05 — Preference activity detection and re-entry limit
    // -------------------------------------------------------------------------

    @Test
    void testPreferenceActivityDetected() {
        // BUG-05: Activities with "Preference", "Setting", "Config", or "About"
        // in the name are detected as preference activities. When re-entries
        // exceed PREFERENCE_FORCE_THRESHOLD, onNewContentState skips Phase 1 reset.

        // Advance to Phase 2 to test reset behavior.
        controller.onIteration(0);
        assertEquals(Phase.PHASE_2, controller.currentPhase());

        // Simulate PREFERENCE_FORCE_THRESHOLD re-entries for a preference cluster.
        String structHash = "pref_cluster";
        for (int i = 0; i < PhaseController.PREFERENCE_FORCE_THRESHOLD; i++) {
            controller.onPhase1Entry(structHash);
        }

        // Now onNewContentState with a preference activity should NOT reset to Phase 1.
        controller.onNewContentState("new_content_hash", "PreferenceActivity", structHash, false);
        assertEquals(Phase.PHASE_2, controller.currentPhase(),
                "Phase should not reset to PHASE_1 for preference activity exceeding threshold");
    }

    @Test
    void testPreferenceActivityReentryLimitIs5() {
        // BUG-05: Threshold for preference activities is 5 (PREFERENCE_FORCE_THRESHOLD).
        assertEquals(5, PhaseController.PREFERENCE_FORCE_THRESHOLD,
                "Preference force threshold should be 5");

        // Advance to Phase 2.
        controller.onIteration(0);
        assertEquals(Phase.PHASE_2, controller.currentPhase());

        // With only 4 re-entries (below threshold), reset still happens.
        String structHash = "pref_cluster_2";
        for (int i = 0; i < PhaseController.PREFERENCE_FORCE_THRESHOLD - 1; i++) {
            controller.onPhase1Entry(structHash);
        }

        controller.onNewContentState("hash_a", "SettingsActivity", structHash, false);
        assertEquals(Phase.PHASE_1, controller.currentPhase(),
                "Phase should reset to PHASE_1 when below preference threshold");
    }

    // -------------------------------------------------------------------------
    // BUG-02 — Cycle detection skips Phase 1 reset
    // -------------------------------------------------------------------------

    @Test
    void testCycleDetectionSkipsPhase1Reset() {
        // BUG-02: When isCycleDetected=true, onNewContentState must NOT reset
        // to Phase 1 — the agent would just re-enter the same loop.

        // Advance to Phase 2.
        controller.onIteration(0);
        assertEquals(Phase.PHASE_2, controller.currentPhase());

        // Cycle detected: should NOT reset to Phase 1.
        controller.onNewContentState("cycle_hash", "MainActivity", "cluster_x", true);
        assertEquals(Phase.PHASE_2, controller.currentPhase(),
                "Cycle detection should prevent Phase 1 reset");
    }

    @Test
    void testNormalPhase1ResetWhenNoCycleAndNoPreference() {
        // When there is no cycle and no preference activity, normal Phase 1 reset occurs.

        // Advance to Phase 2.
        controller.onIteration(0);
        assertEquals(Phase.PHASE_2, controller.currentPhase());

        // Normal new content state: should reset to Phase 1.
        controller.onNewContentState("new_hash", "MainActivity", "normal_cluster", false);
        assertEquals(Phase.PHASE_1, controller.currentPhase(),
                "Normal new content state should reset to Phase 1");
    }
}
