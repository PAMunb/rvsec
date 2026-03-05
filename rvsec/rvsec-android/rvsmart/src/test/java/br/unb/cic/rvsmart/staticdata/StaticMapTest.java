package br.unb.cic.rvsmart.staticdata;

import org.junit.jupiter.api.Test;

import java.io.File;
import java.io.FileWriter;
import java.nio.file.Files;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for StaticMap — loading and querying static analysis data.
 * Exercises graceful degradation when data is unavailable.
 */
class StaticMapTest {

    @Test
    void testNullPathNotLoaded() {
        StaticMap map = new StaticMap(null);
        assertFalse(map.isLoaded());
    }

    @Test
    void testEmptyPathNotLoaded() {
        StaticMap map = new StaticMap("");
        assertFalse(map.isLoaded());
    }

    @Test
    void testHasDirectMopReturnsFalseWhenNotLoaded() {
        StaticMap map = new StaticMap(null);
        assertFalse(map.hasDirectMop("click@100,200"));
    }

    @Test
    void testHasMopReturnsFalseWhenNotLoaded() {
        StaticMap map = new StaticMap(null);
        assertFalse(map.hasMop("click@100,200"));
    }

    /**
     * Nonexistent file triggers FileNotFoundException, then Log.i (Android stub).
     * In unit tests, android.util.Log throws RuntimeException("Stub!"),
     * so this test verifies the exception propagates rather than being swallowed.
     * In production (on device), Log.i works and isLoaded=false is set gracefully.
     */
    @Test
    void testNonexistentFileThrowsInUnitTest() {
        // Android's Log.i is a stub in unit tests, so the catch block in
        // StaticMap constructor throws RuntimeException instead of logging.
        assertThrows(RuntimeException.class,
                () -> new StaticMap("/nonexistent/path/to/file.json"));
    }

    @Test
    void testLoadedMapQueriesCorrectly() throws Exception {
        File tempFile = Files.createTempFile("static_map_test", ".json").toFile();
        try {
            String json = "{"
                    + "\"reachability\": {"
                    + "\"directly_reaches_mop\": {\"click@100,200\": true, \"click@300,400\": false},"
                    + "\"reaches_mop\": {\"click@100,200\": true, \"click@500,600\": true}"
                    + "},"
                    + "\"windows\": {},"
                    + "\"transitions\": {}"
                    + "}";
            try (FileWriter writer = new FileWriter(tempFile)) {
                writer.write(json);
            }

            StaticMap map = new StaticMap(tempFile.getAbsolutePath());
            assertTrue(map.isLoaded());

            assertTrue(map.hasDirectMop("click@100,200"));
            assertFalse(map.hasDirectMop("click@300,400")); // false in JSON
            assertFalse(map.hasDirectMop("click@999,999")); // not in map

            assertTrue(map.hasMop("click@100,200"));
            assertTrue(map.hasMop("click@500,600"));
            assertFalse(map.hasMop("click@999,999")); // not in map
        } finally {
            tempFile.delete();
        }
    }

    @Test
    void testLoadedMapWithEmptyReachability() throws Exception {
        File tempFile = Files.createTempFile("static_map_test", ".json").toFile();
        try {
            String json = "{\"reachability\": {}, \"windows\": {}, \"transitions\": {}}";
            try (FileWriter writer = new FileWriter(tempFile)) {
                writer.write(json);
            }

            StaticMap map = new StaticMap(tempFile.getAbsolutePath());
            assertTrue(map.isLoaded());
            assertFalse(map.hasDirectMop("click@100,200"));
            assertFalse(map.hasMop("click@100,200"));
        } finally {
            tempFile.delete();
        }
    }
}
