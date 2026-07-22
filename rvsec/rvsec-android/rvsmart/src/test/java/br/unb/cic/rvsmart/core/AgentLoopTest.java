package br.unb.cic.rvsmart.core;

import br.unb.cic.rvsmart.graph.ContentGraph;
import br.unb.cic.rvsmart.graph.NavigationMap;
import br.unb.cic.rvsmart.graph.StructuralGraph;
import br.unb.cic.rvsmart.output.RvTrack;
import br.unb.cic.rvsmart.strategy.BacktrackStrategy;
import br.unb.cic.rvsmart.strategy.InputValueGenerator;
import br.unb.cic.rvsmart.strategy.PhaseController;
import br.unb.cic.rvsmart.strategy.PlateauDetector;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for AgentLoop utility methods and component integration.
 * Full loop testing requires Android runtime — these test extracted logic
 * and component wiring at the unit level.
 */
class AgentLoopTest {

    @BeforeEach
    void setUp() {
        RvTrack.logEnabled = false;
    }

    // --- LLM coordinate boundary protection (task 4.5) ---

    @Test
    void testStatusBarYCoordinateIsInBoundaryZone() {
        assertTrue(AgentLoop.isInBoundaryZone(50, 1920),
                "Y=50 should be in status bar boundary (top 5% of 1920)");
    }

    @Test
    void testNavBarYCoordinateIsInBoundaryZone() {
        assertTrue(AgentLoop.isInBoundaryZone(1850, 1920),
                "Y=1850 should be in nav bar boundary (bottom 6% of 1920)");
    }

    @Test
    void testValidYCoordinateIsNotInBoundaryZone() {
        assertFalse(AgentLoop.isInBoundaryZone(500, 1920),
                "Y=500 should not be in boundary zone");
    }

    @Test
    void testBoundaryEdgeCasesStatusBar() {
        assertTrue(AgentLoop.isInBoundaryZone(95, 1920),
                "Y=95 should be in status bar (< 96)");
        assertFalse(AgentLoop.isInBoundaryZone(96, 1920),
                "Y=96 should NOT be in status bar (>= 96)");
    }

    @Test
    void testBoundaryEdgeCasesNavBar() {
        assertTrue(AgentLoop.isInBoundaryZone(1805, 1920),
                "Y=1805 should be in nav bar (> 1804.8)");
        assertFalse(AgentLoop.isInBoundaryZone(1804, 1920),
                "Y=1804 should NOT be in nav bar (<= 1804.8)");
    }

    // --- Integration tests (task 5.3) ---

    @Test
    void testUICoverageTrackerGapDecreasesAfterInteractions() {
        UICoverageTracker tracker = new UICoverageTracker();
        ScreenItem item1 = new ScreenItem("Button", "pkg:id/btn1", null, null, null,
                "com.example", true, false, false, true, false, false, 0);
        ScreenItem item2 = new ScreenItem("Button", "pkg:id/btn2", null, null, null,
                "com.example", true, false, false, true, false, false, 0);

        tracker.registerScreenElements("hash1", Arrays.asList(item1, item2));
        float gapBefore = tracker.getCoverageGap("hash1");
        assertEquals(1.0f, gapBefore, 0.01f, "Full gap before any interaction");

        tracker.recordInteraction("hash1", "res:pkg:id/btn1");
        float gapAfter = tracker.getCoverageGap("hash1");
        assertEquals(0.5f, gapAfter, 0.01f, "Half gap after one of two interactions");
    }

    @Test
    void testPlateauDetectorDetectsPlateau() {
        // Phase transitions (incl. PHASE_3 stochastic boost) are now managed by PhaseController.
        // This test verifies PlateauDetector's plateau detection logic in isolation.
        PlateauDetector detector = new PlateauDetector();

        // No plateau initially
        assertFalse(detector.isPlateauDetected());

        // Simulate 10 no-progress iterations to trigger plateau
        for (int i = 0; i < 10; i++) {
            detector.recordIteration(false, false);
        }
        assertTrue(detector.isPlateauDetected());

        // New screen clears plateau
        detector.recordIteration(true, false);
        assertFalse(detector.isPlateauDetected());
    }

    @Test
    void testInputValueGeneratorContextAwareValues() {
        InputValueGenerator gen = new InputValueGenerator();

        // Email field
        ScreenItem emailItem = new ScreenItem("EditText", "id/email", null, null, null,
                "com.example", false, false, false, true, false, true,
                0, "email address", 0);
        String emailValue = gen.generateInput(emailItem);
        assertEquals("test@test.com", emailValue, "Email field should get email value");

        // Password field
        ScreenItem passItem = new ScreenItem("EditText", "id/password", null, null, null,
                "com.example", false, false, false, true, false, true,
                0, "enter password", 0);
        String passValue = gen.generateInput(passItem);
        assertEquals("Test1234!", passValue, "Password field should get password value");

        // Generic field
        ScreenItem genericItem = new ScreenItem("EditText", "id/search", null, null, null,
                "com.example", false, false, false, true, false, true,
                0, "search", 0);
        String genericValue = gen.generateInput(genericItem);
        assertEquals("test", genericValue, "Generic field should get 'test' value");
    }

    // --- gh34 Group 7 integration tests (task 7.8) ---

    /**
     * Verifies that ContentGraph and StructuralGraph receive entries when the
     * same registration sequence as AgentLoop.runIteration() is executed.
     */
    @Test
    void testDualHashGraphRegistrationOnIteration() {
        ContentGraph contentGraph = new ContentGraph();
        StructuralGraph structuralGraph = new StructuralGraph();

        // Simulate the registration sequence from runIteration():
        // getOrCreate registers in ContentGraph; register() links struct → content
        String contentHash = "aabbccdd";
        String structHash = "11223344";
        String activity = "com.example.MainActivity";

        contentGraph.getOrCreate(contentHash, activity);
        structuralGraph.register(structHash, contentHash);

        // ContentGraph has one entry
        assertEquals(1, contentGraph.size(), "ContentGraph should have 1 entry after registration");
        assertNotNull(contentGraph.get(contentHash), "ContentNode should be retrievable by contentHash");

        // StructuralGraph clusters the contentHash under the structHash
        assertEquals(1, structuralGraph.size(), "StructuralGraph should have 1 cluster");
        assertTrue(structuralGraph.getCluster(structHash).contains(contentHash),
                "StructuralGraph cluster should contain the registered contentHash");

        // Reverse lookup
        assertEquals(structHash, structuralGraph.getStructHash(contentHash),
                "Reverse lookup from contentHash should return structHash");
    }

    /**
     * Verifies that PhaseController.onNewContentState() resets to PHASE_1 from any phase,
     * following the same wiring pattern as AgentLoop.runIteration() (isNewScreen check).
     */
    @Test
    void testPhaseControllerReceivesOnNewContentStateOnNewScreen() {
        ContentGraph contentGraph = new ContentGraph();
        UICoverageTracker tracker = new UICoverageTracker();
        PlateauDetector plateauDetector = new PlateauDetector();
        PhaseController phaseController = new PhaseController(contentGraph, tracker, plateauDetector);

        // Drive plateau — with empty ContentGraph and no untested actions in any reachable state,
        // PHASE_1 → PHASE_3 after WINDOW_SIZE iterations when plateau is detected.
        for (int i = 0; i < PlateauDetector.WINDOW_SIZE; i++) {
            phaseController.onIteration(0);
        }
        // Phase is beyond PHASE_1 (PHASE_3 after plateau detected)
        assertNotEquals(PhaseController.Phase.PHASE_1, phaseController.currentPhase(),
                "Phase should have advanced past PHASE_1 after sustained no-progress iterations");

        // Now simulate a new content state being discovered — should reset to PHASE_1
        phaseController.onNewContentState("new-content-hash-xyz");
        assertEquals(PhaseController.Phase.PHASE_1, phaseController.currentPhase(),
                "Discovering a new content state should reset phase to PHASE_1 from any phase");
    }

    /**
     * Verifies that NavigationMap records an edge after an action with effect,
     * following the same recording pattern as AgentLoop.runIteration().
     */
    @Test
    void testNavigationMapRecordsEdgeAfterActionWithEffect() {
        NavigationMap navigationMap = new NavigationMap();
        StructuralGraph structuralGraph = new StructuralGraph();
        BacktrackStrategy backtrackStrategy = new BacktrackStrategy(navigationMap, structuralGraph);

        String fromStruct = "struct-a";
        String toStruct = "struct-b";
        String actionSig = "CLICK:pkg:id/btn_submit";

        // Initially no path
        assertFalse(backtrackStrategy.canReach(fromStruct, toStruct),
                "No path should exist before recording");
        assertEquals(0, navigationMap.size(), "NavigationMap should be empty initially");

        // Simulate hadEffect == true: record the edge
        navigationMap.record(fromStruct, actionSig, toStruct);

        // NavigationMap should now have the edge
        assertEquals(1, navigationMap.size(), "NavigationMap should have 1 edge after recording");
        assertTrue(backtrackStrategy.canReach(fromStruct, toStruct),
                "Path should exist after NavigationMap edge is recorded");

        // planReplay should find the path and increment replayCount
        List<String> replay = backtrackStrategy.planReplay(fromStruct, toStruct);
        assertFalse(replay.isEmpty(), "Replay path should be non-empty");
        assertEquals(actionSig, replay.get(0), "Replay should contain the recorded action signature");
        assertEquals(1, backtrackStrategy.getReplayCount(),
                "Replay count should increment after successful planReplay");
    }
}
