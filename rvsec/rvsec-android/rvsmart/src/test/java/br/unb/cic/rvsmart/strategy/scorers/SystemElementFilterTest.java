package br.unb.cic.rvsmart.strategy.scorers;

import br.unb.cic.rvsmart.core.Action;
import br.unb.cic.rvsmart.core.ScreenItem;
import br.unb.cic.rvsmart.core.ScreenState;
import br.unb.cic.rvsmart.graph.DynamicStateGraph;

import org.junit.jupiter.api.Test;

import java.util.Collections;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for SystemElementFilter — penalizes actions on system UI elements.
 */
class SystemElementFilterTest {

    private final SystemElementFilter filter = new SystemElementFilter();
    private final DynamicStateGraph graph = new DynamicStateGraph();
    private final ScreenState screen = new ScreenState(
            Collections.<ScreenItem>emptyList(), "TestActivity");

    @Test
    void testReturnsPenaltyForSystemUiPackage() {
        Action action = new Action(Action.Type.CLICK, 100, 200, null,
                "algorithm", "ImageView", "com.android.systemui");
        assertEquals(-5000, filter.score(action, screen, graph, null));
    }

    @Test
    void testReturnsZeroForRegularPackage() {
        Action action = new Action(Action.Type.CLICK, 100, 200, null,
                "algorithm", "Button", "com.example.myapp");
        assertEquals(0, filter.score(action, screen, graph, null));
    }

    @Test
    void testReturnsZeroForNullPackage() {
        Action action = new Action(Action.Type.CLICK, 100, 200, null,
                "algorithm", "Button", null);
        assertEquals(0, filter.score(action, screen, graph, null));
    }

    @Test
    void testReturnsZeroForAndroidPackage() {
        // "android" package is NOT penalized by SystemElementFilter
        // (it is handled by SystemDialogDetector instead)
        Action action = new Action(Action.Type.CLICK, 100, 200, null,
                "algorithm", "Button", "android");
        assertEquals(0, filter.score(action, screen, graph, null));
    }
}
