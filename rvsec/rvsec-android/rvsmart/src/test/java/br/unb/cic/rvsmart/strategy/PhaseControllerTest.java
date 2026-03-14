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
    // Phase enum only has PHASE_1 and PHASE_3
    // -------------------------------------------------------------------------

    @Test
    void testPhaseEnumOnlyHasPhase1AndPhase3() {
        Phase[] values = Phase.values();
        assertEquals(2, values.length, "Phase enum should have exactly 2 values");
        assertEquals(Phase.PHASE_1, values[0]);
        assertEquals(Phase.PHASE_3, values[1]);
    }

    // -------------------------------------------------------------------------
    // Phase starts at PHASE_1
    // -------------------------------------------------------------------------

    @Test
    void testInitialPhaseIsPhase1() {
        assertEquals(PhaseController.Phase.PHASE_1, controller.currentPhase());
    }

    // -------------------------------------------------------------------------
    // PHASE_1 stays when untested actions remain
    // -------------------------------------------------------------------------

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
    // PHASE_1 stays when all actions executed but no plateau
    // -------------------------------------------------------------------------

    @Test
    void testPhase1StaysWhenAllActionsExecutedButNoPlateau() {
        // Add a content node with 2 total actions, both executed.
        ContentNode node = contentGraph.getOrCreate("hash-A", "MainActivity");
        node.setTotalActions(2);
        node.recordAction("click@100,200", "Button");
        node.recordAction("click@300,400", "Button");

        // One iteration with no plateau yet — should stay in PHASE_1
        controller.onIteration(0);

        assertEquals(PhaseController.Phase.PHASE_1, controller.currentPhase());
    }

    // -------------------------------------------------------------------------
    // PHASE_1 → PHASE_3 when all states explored AND plateau detected
    // -------------------------------------------------------------------------

    @Test
    void testPhase1TransitionsToPhase3WhenAllExploredAndPlateau() {
        // Empty graph means no untested actions in any reachable state.
        // Feed enough zero-coverage iterations to trigger plateau.
        for (int i = 0; i < PlateauDetector.WINDOW_SIZE; i++) {
            controller.onIteration(0);
        }

        assertEquals(PhaseController.Phase.PHASE_3, controller.currentPhase());
    }

    @Test
    void testPhase1DoesNotTransitionToPhase3BeforePlateauWindowFull() {
        // Empty graph (no untested actions), but not enough iterations for plateau.
        // Feed fewer than WINDOW_SIZE iterations.
        for (int i = 0; i < PlateauDetector.WINDOW_SIZE - 1; i++) {
            controller.onIteration(0);
        }

        assertEquals(PhaseController.Phase.PHASE_1, controller.currentPhase());
    }

    // -------------------------------------------------------------------------
    // New content state resets to PHASE_1 from PHASE_3
    // -------------------------------------------------------------------------

    @Test
    void testNewContentStateResetsToPhase1FromPhase3() {
        // Drive PHASE_1 → PHASE_3 via plateau (empty graph).
        for (int i = 0; i < PlateauDetector.WINDOW_SIZE; i++) {
            controller.onIteration(0);
        }
        assertEquals(PhaseController.Phase.PHASE_3, controller.currentPhase());

        controller.onNewContentState("beef1234");
        assertEquals(PhaseController.Phase.PHASE_1, controller.currentPhase());
    }

    // -------------------------------------------------------------------------
    // Cluster forcing: after threshold re-entries, isClusterForced returns true
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
    // Different clusters tracked independently
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

        // Advance to Phase 3 to test reset behavior.
        for (int i = 0; i < PlateauDetector.WINDOW_SIZE; i++) {
            controller.onIteration(0);
        }
        assertEquals(Phase.PHASE_3, controller.currentPhase());

        // Simulate PREFERENCE_FORCE_THRESHOLD re-entries for a preference cluster.
        String structHash = "pref_cluster";
        for (int i = 0; i < PhaseController.PREFERENCE_FORCE_THRESHOLD; i++) {
            controller.onPhase1Entry(structHash);
        }

        // Now onNewContentState with a preference activity should NOT reset to Phase 1.
        controller.onNewContentState("new_content_hash", "PreferenceActivity", structHash, false);
        assertEquals(Phase.PHASE_3, controller.currentPhase(),
                "Phase should not reset to PHASE_1 for preference activity exceeding threshold");
    }

    @Test
    void testPreferenceActivityReentryLimitIs5() {
        // BUG-05: Threshold for preference activities is 5 (PREFERENCE_FORCE_THRESHOLD).
        assertEquals(5, PhaseController.PREFERENCE_FORCE_THRESHOLD,
                "Preference force threshold should be 5");

        // Advance to Phase 3.
        for (int i = 0; i < PlateauDetector.WINDOW_SIZE; i++) {
            controller.onIteration(0);
        }
        assertEquals(Phase.PHASE_3, controller.currentPhase());

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

        // Advance to Phase 3.
        for (int i = 0; i < PlateauDetector.WINDOW_SIZE; i++) {
            controller.onIteration(0);
        }
        assertEquals(Phase.PHASE_3, controller.currentPhase());

        // Cycle detected: should NOT reset to Phase 1.
        controller.onNewContentState("cycle_hash", "MainActivity", "cluster_x", true);
        assertEquals(Phase.PHASE_3, controller.currentPhase(),
                "Cycle detection should prevent Phase 1 reset");
    }

    // -------------------------------------------------------------------------
    // gh41 — System actions excluded from untested check
    // -------------------------------------------------------------------------

    @Test
    void testSystemActionsExcludedFromUntestedCheck() {
        // A node with 5 widget totalActions and 3 widget executions + BACK + RESTART
        // should still be considered as having untested actions (3 < 5).
        ContentNode node = contentGraph.getOrCreate("hash-X", "MainActivity");
        node.setTotalActions(5);
        node.recordAction("click@100,200", "Button");
        node.recordAction("click@300,400", "Button");
        node.recordAction("click@500,600", "Button");
        node.recordAction("back@0,0", "");
        node.recordAction("restart@0,0", "");

        // executedActions.size() == 5, but only 3 are widget actions
        assertEquals(5, node.getExecutedActions().size());
        assertTrue(controller.hasUntestedActionsInAnyReachableState(),
                "Should return true: only 3 widget actions tested out of 5 totalActions");
    }

    @Test
    void testAllWidgetActionsTestedWithSystemActionsPresent() {
        // A node with 5 widget totalActions and all 5 tested + BACK + RESTART
        ContentNode node = contentGraph.getOrCreate("hash-Y", "MainActivity");
        node.setTotalActions(5);
        node.recordAction("click@100,200", "Button");
        node.recordAction("click@300,400", "Button");
        node.recordAction("click@500,600", "Button");
        node.recordAction("click@700,800", "Button");
        node.recordAction("click@900,1000", "Button");
        node.recordAction("back@0,0", "");
        node.recordAction("restart@0,0", "");

        // executedActions.size() == 7, but 5 widget actions match totalActions
        assertEquals(7, node.getExecutedActions().size());
        assertFalse(controller.hasUntestedActionsInAnyReachableState(),
                "Should return false: all 5 widget actions tested");
    }

    // -------------------------------------------------------------------------
    // gh41 — Cluster force threshold is 50
    // -------------------------------------------------------------------------

    @Test
    void testClusterForceThresholdIs50() {
        assertEquals(50, PhaseController.CLUSTER_FORCE_THRESHOLD,
                "Cluster force threshold should be 50");
    }

    @Test
    void testNormalPhase1ResetWhenNoCycleAndNoPreference() {
        // When there is no cycle and no preference activity, normal Phase 1 reset occurs.

        // Advance to Phase 3.
        for (int i = 0; i < PlateauDetector.WINDOW_SIZE; i++) {
            controller.onIteration(0);
        }
        assertEquals(Phase.PHASE_3, controller.currentPhase());

        // Normal new content state: should reset to Phase 1.
        controller.onNewContentState("new_hash", "MainActivity", "normal_cluster", false);
        assertEquals(Phase.PHASE_1, controller.currentPhase(),
                "Normal new content state should reset to Phase 1");
    }
}
