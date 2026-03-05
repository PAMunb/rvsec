package br.unb.cic.rvsmart.strategy.scorers;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.ScreenItem;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.graph.DynamicStateGraph;
import br.unb.cic.rvsmart.output.RvTrack;
import br.unb.cic.rvsmart.staticdata.StaticMap;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import java.io.File;
import java.io.FileWriter;
import java.nio.file.Files;
import java.util.Collections;

import static org.junit.jupiter.api.Assertions.*;

class CoverageDensityScorerTest {

    private CoverageDensityScorer scorer;
    private DynamicStateGraph graph;
    private ScreenState screen;

    @BeforeEach
    void setUp() {
        RvTrack.logEnabled = false;
        scorer = new CoverageDensityScorer(200);
        graph = new DynamicStateGraph();
        screen = new ScreenState(Collections.<ScreenItem>emptyList(), "TestActivity");
    }

    @Test
    void testReturnsZeroWhenStaticMapIsNull() {
        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(0, scorer.score(action, screen, graph, null));
    }

    @Test
    void testReturnsZeroWhenStaticMapNotLoaded() {
        StaticMap staticMap = new StaticMap(null);
        Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
        assertEquals(0, scorer.score(action, screen, graph, staticMap));
    }

    @Test
    void testReturnsZeroForNonMopAction() throws Exception {
        String actionSig = "click@999,999"; // not in static map
        File tempFile = createStaticMapJson("click@100,200", true, true);
        try {
            StaticMap staticMap = new StaticMap(tempFile.getAbsolutePath());
            Action action = new Action(Action.Type.CLICK, 999, 999, "algorithm", "Button");
            assertEquals(0, scorer.score(action, screen, graph, staticMap));
        } finally {
            tempFile.delete();
        }
    }

    @Test
    void testReturnsMopDensityBaseForDirectMopAction() throws Exception {
        File tempFile = createStaticMapJson("click@100,200", true, false);
        try {
            StaticMap staticMap = new StaticMap(tempFile.getAbsolutePath());
            Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
            assertEquals(200, scorer.score(action, screen, graph, staticMap));
        } finally {
            tempFile.delete();
        }
    }

    @Test
    void testReturnsMopDensityBaseForTransitiveMopAction() throws Exception {
        File tempFile = createStaticMapJson("click@100,200", false, true);
        try {
            StaticMap staticMap = new StaticMap(tempFile.getAbsolutePath());
            Action action = new Action(Action.Type.CLICK, 100, 200, "algorithm", "Button");
            assertEquals(200, scorer.score(action, screen, graph, staticMap));
        } finally {
            tempFile.delete();
        }
    }

    private File createStaticMapJson(String actionSig, boolean directMop, boolean transitiveMop)
            throws Exception {
        File tempFile = Files.createTempFile("cov_density_test", ".json").toFile();
        String json = "{"
                + "\"reachability\": {"
                + "\"directly_reaches_mop\": {\"" + actionSig + "\": " + directMop + "},"
                + "\"reaches_mop\": {\"" + actionSig + "\": " + transitiveMop + "}"
                + "},"
                + "\"windows\": {},"
                + "\"transitions\": {}"
                + "}";
        try (FileWriter writer = new FileWriter(tempFile)) {
            writer.write(json);
        }
        return tempFile;
    }
}
