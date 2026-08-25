package br.unb.cic.rvsec.crysl.core.calibration;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * The reader behind target 8's route, over a fragment shaped exactly like {@code rv-monitor}'s
 * output.
 *
 * <p>The fragment is short on purpose: what has to be pinned down is the two patterns and the
 * name translation, not the ten thousand lines the real file also contains. The real file is read
 * by {@code CalibrationGateTest} in the {@code -crysl} module, where the generated monitor is.
 */
class MonitorIndexCensusTest {

    /** Two specifications declared, one of which the generator indexes. */
    private static final String MONITOR = """
            package mop;
            public class MultiSpec_1RuntimeMonitor implements rvmonitorrt.Monitor {
            	private static final MapOfMonitor<CipherSpecMonitor> CipherSpec_c_Map = new MapOfMonitor<CipherSpecMonitor>(0) ;
            	class CipherSpecMonitor extends rvmonitorrt.Monitor { }
            	class KeyStoreSpecMonitor extends rvmonitorrt.Monitor { }
            	class RandomStringPasswordSpecMonitor extends rvmonitorrt.Monitor { }
            	void event() { MapOfMonitor<CipherSpecMonitor> matchedLastMap = null; }
            }
            """;

    @Test
    @DisplayName("a specification indexes when the monitor declares a MapOfMonitor field for it")
    void test_the_two_patterns() {
        MonitorIndexCensus census = MonitorIndexCensus.read(MONITOR);

        assertEquals(List.of("CipherSpec", "KeyStoreSpec", "RandomStringPasswordSpec"),
                census.declared(),
                "the aggregate class MultiSpec_1RuntimeMonitor is not a specification and is left "
                        + "out");
        assertEquals(List.of("CipherSpec"), census.indexing(),
                "the local variable of the same type is not a second declaration: the field is "
                        + "what the generator emits once per indexing specification");
        assertEquals(List.of("KeyStoreSpec", "RandomStringPasswordSpec"), census.notIndexing());
    }

    @Test
    @DisplayName("declared names are translated back to .mop file names before they are compared")
    void test_names_are_translated_to_file_names() {
        List<String> files = List.of("KeyStoreSpec", "RandomStringPassword", "IvChainJunction");

        assertEquals(List.of("KeyStoreSpec", "RandomStringPassword", "IvChainJunction"),
                MonitorIndexCensus.asFileNames(
                        List.of("KeyStoreSpec", "RandomStringPasswordSpec", "IvChainJunctionSpec"),
                        files),
                "the monitor names a specification by its DECLARED name, and five files of the set "
                        + "declare a name that is not the file name");
        assertEquals(List.of("SomethingElseSpec"),
                MonitorIndexCensus.asFileNames(List.of("SomethingElseSpec"), files),
                "a name matching no file is returned unchanged rather than dropped: silently "
                        + "losing a specification would turn a naming surprise into a smaller "
                        + "count, which is the shape of error this component exists to catch");
    }
}
