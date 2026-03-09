package br.unb.cic.rvsmart.core;

import br.unb.cic.rvsmart.graph.ContentGraph;
import br.unb.cic.rvsmart.output.RvTrack;
import br.unb.cic.rvsmart.recovery.StuckDetector;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.util.Arrays;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for Learner reward computation and state tracking.
 */
class LearnerTest {

    private ContentGraph graph;
    private StuckDetector stuckDetector;
    private Learner learner;

    @BeforeEach
    void setUp() {
        RvTrack.logEnabled = false;
        RvTrack.resetCounters();
        graph = new ContentGraph();
        stuckDetector = new StuckDetector(10);
        learner = new Learner(graph, stuckDetector);
    }

    @Test
    void testNewActivityReward() {
        graph.getOrCreate("h1", "ActivityA");
        graph.getOrCreate("h2", "ActivityB");
        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");

        double reward = learner.update(action, true, "h1", "h2",
                "ActivityA", "ActivityB", Collections.emptyList(), 0, 0);

        // New activity (+2.0) + new state (+1.0)
        assertEquals(3.0, reward, 0.001);
    }

    @Test
    void testNewStateReward() {
        graph.getOrCreate("h1", "ActivityA");
        graph.getOrCreate("h2", "ActivityA");
        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");

        double reward = learner.update(action, true, "h1", "h2",
                "ActivityA", "ActivityA", Collections.emptyList(), 0, 0);

        // New state (+1.0), same activity (no activity reward)
        assertEquals(1.0, reward, 0.001);
    }

    @Test
    void testNoEffectPenalty() {
        graph.getOrCreate("h1", "ActivityA");
        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");

        double reward = learner.update(action, false, "h1", "h1",
                "ActivityA", "ActivityA", Collections.emptyList(), 0, 0);

        // No effect (-0.1)
        assertEquals(-0.1, reward, 0.001);
    }

    @Test
    void testCoverageReward() {
        graph.getOrCreate("h1", "ActivityA");
        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        List<String> methods = Arrays.asList(
                "javax.crypto.Cipher.getInstance",
                "java.security.MessageDigest.getInstance");

        double reward = learner.update(action, false, "h1", "h1",
                "ActivityA", "ActivityA", methods, 0, 0);

        // No effect (-0.1) + 2 unique methods (+0.5 each = +1.0)
        assertEquals(0.9, reward, 0.001);
    }

    @Test
    void testCoverageDeduplication() {
        graph.getOrCreate("h1", "ActivityA");
        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        List<String> methods = Arrays.asList("javax.crypto.Cipher.getInstance");

        // First call: +0.5 for new method
        learner.update(action, false, "h1", "h1",
                "ActivityA", "ActivityA", methods, 0, 0);

        // Second call with same method: no additional coverage reward
        double reward = learner.update(action, false, "h1", "h1",
                "ActivityA", "ActivityA", methods, 1, 0);

        // No effect (-0.1), duplicate method (no reward)
        assertEquals(-0.1, reward, 0.001);
        assertEquals(1, learner.getConfirmedMethods().size());
    }

    @Test
    void testSourceAgnosticReward_INV_RSM_08() {
        graph.getOrCreate("h1", "ActivityA");
        graph.getOrCreate("h2", "ActivityB");

        // Action from algorithm source
        Action algAction = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        double algReward = learner.update(algAction, true, "h1", "h2",
                "ActivityA", "ActivityB", Collections.emptyList(), 0, 0);

        // Reset for clean comparison
        graph = new ContentGraph();
        stuckDetector = new StuckDetector(10);
        learner = new Learner(graph, stuckDetector);
        graph.getOrCreate("h1", "ActivityA");
        graph.getOrCreate("h2", "ActivityB");

        // Same action from LLM source
        Action llmAction = new Action(Action.Type.CLICK, 100, 200, "llm", "Button");
        double llmReward = learner.update(llmAction, true, "h1", "h2",
                "ActivityA", "ActivityB", Collections.emptyList(), 0, 0);

        // Same reward regardless of source (INV-RSM-08)
        assertEquals(algReward, llmReward, 0.001);
    }

    @Test
    void testGraphUpdatedWithTransition() {
        graph.getOrCreate("h1", "ActivityA");
        graph.getOrCreate("h2", "ActivityB");
        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");

        learner.update(action, true, "h1", "h2",
                "ActivityA", "ActivityB", Collections.emptyList(), 0, 0);

        // Graph should record the transition h1 -> h2
        assertTrue(graph.get("h1").getTransitions().contains("h2"));
    }

    @Test
    void testUniqueActivitiesTracked() {
        graph.getOrCreate("h1", "ActivityA");
        graph.getOrCreate("h2", "ActivityB");
        graph.getOrCreate("h3", "ActivityA");
        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");

        learner.update(action, true, "h1", "h2",
                "ActivityA", "ActivityB", Collections.emptyList(), 0, 0);
        learner.update(action, true, "h2", "h3",
                "ActivityB", "ActivityA", Collections.emptyList(), 1, 0);

        // Both activities tracked, no duplicates
        assertEquals(2, learner.getUniqueActivities().size());
        assertTrue(learner.getUniqueActivities().contains("ActivityA"));
        assertTrue(learner.getUniqueActivities().contains("ActivityB"));
    }
}
