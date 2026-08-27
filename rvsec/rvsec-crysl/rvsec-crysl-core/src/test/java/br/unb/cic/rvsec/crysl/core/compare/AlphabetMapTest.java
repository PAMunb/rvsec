package br.unb.cic.rvsec.crysl.core.compare;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.Properties;
import java.util.Set;
import java.util.stream.Stream;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * The reader of {@code order_alphabet_map.csv}, against the committed file and against shapes the
 * committed file does not currently contain.
 *
 * <p>The committed file is reached through the same build-time property the schema drift check uses,
 * so this test cannot silently pass with the map absent: a missing map fails here rather than
 * skipping, for the reason that a check that can quietly not run is a green with nothing behind it.
 */
class AlphabetMapTest {

    private static Path committed;

    /**
     * The {@code .mop} corpus the committed map is stated over, in the sibling module's tree.
     *
     * <p>Read only so that the row-group count below can be stated as an arithmetic of the corpus
     * instead of as a literal. A literal there moves whenever a specification enters the directory,
     * which says nothing about this reader and costs one build cycle per group to rediscover.
     */
    private static final Path CORPUS = Paths.get("..", "..", "rvsec-mop", "src", "main",
            "resources", "jca_android").normalize();

    /**
     * The two specifications the map declares as G-ORDER skips, by owning no data row at all.
     *
     * <p>Declared, not derived: which files are skipped is the mapping decision this file records,
     * and its reason is prose in the map's own header.
     */
    private static final Set<String> ORDER_SKIPS =
            Set.of("IvChainJunction", "RandomStringPassword");

    private static int corpusSize() throws IOException {
        assertTrue(Files.isDirectory(CORPUS), "the .mop corpus is not at " + CORPUS.toAbsolutePath());
        try (Stream<Path> entries = Files.list(CORPUS)) {
            return (int) entries.filter(p -> p.getFileName().toString().endsWith(".mop")).count();
        }
    }

    @BeforeAll
    static void resolveCommittedMap() throws IOException {
        Properties properties = new Properties();
        try (InputStream in = AlphabetMapTest.class.getClassLoader()
                .getResourceAsStream("committed-schemas.properties")) {
            assertTrue(in != null, "committed-schemas.properties is not on the test classpath");
            properties.load(in);
        }
        String configured = properties.getProperty("committed.schemas.dir");
        assertFalse(configured == null || configured.isBlank() || configured.startsWith("${"),
                "committed.schemas.dir was not interpolated by the build: " + configured);
        committed = Path.of(configured).normalize().resolve("order_alphabet_map.csv");
        assertTrue(Files.isReadable(committed), "the committed alphabet map is not at " + committed);
    }

    @Test
    @DisplayName("10.3 · the committed map parses, comments and quoted commas included")
    void test_the_committed_map_parses() throws IOException {
        AlphabetMap map = AlphabetMap.read(committed);

        assertEquals(corpusSize() - ORDER_SKIPS.size(), map.rows().size(),
                "one group per specification carrying rows; the two G-ORDER skips are prose in the "
                        + "header and never data rows, which is what keeps them skips: "
                        + map.rows().keySet());

        List<AlphabetMap.Row> keyGenerator = map.rowsOf("KeyGeneratorSpec");
        assertEquals(9, keyGenerator.size(),
                "nine rows for eight events: init carries two, because one .mop event stands for "
                        + "the rule's i1 and its i3, and the map is deliberately not a bijection");
        assertEquals(8, keyGenerator.stream().map(AlphabetMap.Row::mopEvent).distinct().count(),
                "KeyGeneratorSpec grew from 5 events to 8, as the map's own header records");

        // The reason column of this row carries two commas inside its quotes. A naive split gives
        // it seven fields and reads 'order-unmapped' out of the wrong column, which is how a reader
        // silently turns a declared erasure into a mapping.
        List<AlphabetMap.Row> g3 = map.rowsOf("KeyGeneratorSpec", "g3");
        assertEquals(1, g3.size());
        assertEquals(AlphabetMap.Disposition.ORDER_UNMAPPED, g3.get(0).disposition());
        assertTrue(g3.get(0).reason().startsWith("the rejected-algorithm twin over the same"),
                "the reason survives the quoting intact: " + g3.get(0).reason());
    }

    @Test
    @DisplayName("10.3 · erasure is the disposition column and nothing else")
    void test_erasure_comes_from_the_disposition_column() throws IOException {
        AlphabetMap map = AlphabetMap.read(committed);

        assertTrue(map.erases("KeyGeneratorSpec", "g3"),
                "declared order-unmapped, and that declaration is the whole authority. No "
                        + "automaton shape licenses it: g3 loops only at the initial state");
        assertFalse(map.erases("KeyGeneratorSpec", "g1"),
                "g1 is mapped to the rule's g1 and must keep its letter");

        assertFalse(map.erases("KeyGeneratorSpec", "init"),
                "init carries two rows, i1 and i3, and both are mapped");
        assertEquals(2, map.rowsOf("KeyGeneratorSpec", "init").size(),
                "the map is deliberately not a bijection: one event, two rule symbols");
    }

    @Test
    @DisplayName("10.4 · an event with no row is neither mapped nor erased")
    void test_an_event_with_no_row_is_not_an_erasure() throws IOException {
        AlphabetMap map = AlphabetMap.read(committed);

        assertFalse(map.declares("KeyGeneratorSpec", "thereIsNoSuchEvent"));
        assertFalse(map.erases("KeyGeneratorSpec", "thereIsNoSuchEvent"),
                "absence of a row is not a declaration of anything, and erasing on it would be a "
                        + "decision nobody reviewed (INV-CONF-10)");
    }

    @Test
    @DisplayName("10.3 · the cross-renumbering the corpus needs a table for is visible")
    void test_cross_renumbering_is_readable() throws IOException {
        AlphabetMap map = AlphabetMap.read(committed);

        assertTrue(map.renames("SecureRandomSpec", "g3"),
                "the .mop calls it g3 and the rule calls it gI");
        assertTrue(map.renames("SecureRandomSpec", "setSeed1"),
                "setSeed1 is the rule's s2, not its s1; the name heuristic does not miss, it picks "
                        + "the wrong overload");
    }

    @Test
    @DisplayName("a disposition outside the closed set is refused rather than guessed")
    void test_an_unknown_disposition_is_refused(@TempDir Path dir) throws IOException {
        Path csv = dir.resolve("map.csv");
        Files.writeString(csv, "# comment\n" + AlphabetMap.HEADER
                + "\nSpec,e1,,,Rule.crysl,,probably-fine,because\n", StandardCharsets.UTF_8);

        IllegalArgumentException failure =
                assertThrows(IllegalArgumentException.class, () -> AlphabetMap.read(csv));
        assertTrue(failure.getMessage().contains("probably-fine"));
    }

    @Test
    @DisplayName("a file whose header moved is refused rather than read by position")
    void test_a_drifted_header_is_refused(@TempDir Path dir) throws IOException {
        Path csv = dir.resolve("map.csv");
        Files.writeString(csv, "spec,mop_event,disposition\nSpec,e1,mapped\n",
                StandardCharsets.UTF_8);

        IOException failure = assertThrows(IOException.class, () -> AlphabetMap.read(csv));
        assertTrue(failure.getMessage().contains("header"));
    }
}
