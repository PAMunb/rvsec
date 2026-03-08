package br.unb.cic.rvsmart.staticdata;

import org.junit.jupiter.api.Test;

import java.io.File;
import java.io.FileWriter;
import java.nio.file.Files;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for StaticMap — loading and querying static analysis data.
 * Tests use the JsonArray format produced by RvsecAnalysisClient (gh27).
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
    void testActivityHasDirectMopReturnsFalseWhenNotLoaded() {
        StaticMap map = new StaticMap(null);
        assertFalse(map.activityHasDirectMop("MainActivity"));
    }

    @Test
    void testActivityHasMopReturnsFalseWhenNotLoaded() {
        StaticMap map = new StaticMap(null);
        assertFalse(map.activityHasMop("MainActivity"));
    }

    /**
     * Nonexistent file triggers FileNotFoundException, then Log.i (Android stub).
     * In unit tests, android.util.Log throws RuntimeException("Stub!").
     */
    @Test
    void testNonexistentFileThrowsInUnitTest() {
        assertThrows(RuntimeException.class,
                () -> new StaticMap("/nonexistent/path/to/file.json"));
    }

    @Test
    void testParseReachabilityJsonArray() throws Exception {
        File tempFile = createJsonWithReachability(
                "com.example.app.MainActivity", true, true);
        try {
            StaticMap map = new StaticMap(tempFile.getAbsolutePath());
            assertTrue(map.isLoaded());
            assertTrue(map.activityHasDirectMop("MainActivity"));
            assertTrue(map.activityHasMop("MainActivity"));
        } finally {
            tempFile.delete();
        }
    }

    @Test
    void testParseTransitionsJsonArray() throws Exception {
        File tempFile = createJsonWithTransitions();
        try {
            StaticMap map = new StaticMap(tempFile.getAbsolutePath());
            assertTrue(map.isLoaded());
            List<String> transitions = map.getTransitions("MainActivity");
            assertFalse(transitions.isEmpty());
            assertTrue(transitions.contains("SettingsActivity"));
        } finally {
            tempFile.delete();
        }
    }

    @Test
    void testActivityNameNormalizationTraceFormat() {
        // Trace format: dots stripped from relative path
        assertEquals("SplashActivity",
                StaticMap.extractSimpleClassName("uiactivitiesSplashActivity"));
    }

    @Test
    void testActivityNameNormalizationFullyQualified() {
        assertEquals("SplashActivity",
                StaticMap.extractSimpleClassName(
                        "com.crazyhitty.chdev.ks.munch.ui.activities.SplashActivity"));
    }

    @Test
    void testActivityNameNormalizationSimpleName() {
        assertEquals("MainActivity",
                StaticMap.extractSimpleClassName("MainActivity"));
    }

    @Test
    void testParseEmptyMissingSectionsGracefully() throws Exception {
        File tempFile = Files.createTempFile("static_map_test", ".json").toFile();
        try {
            // JSON with empty arrays
            String json = "{\"reachability\":[], \"windows\":[], \"transitions\":[]}";
            try (FileWriter writer = new FileWriter(tempFile)) {
                writer.write(json);
            }
            StaticMap map = new StaticMap(tempFile.getAbsolutePath());
            assertTrue(map.isLoaded());
            assertFalse(map.activityHasDirectMop("AnyActivity"));
            assertTrue(map.getTransitions("AnyActivity").isEmpty());
        } finally {
            tempFile.delete();
        }
    }

    @Test
    void testGetMopMethodsForActivityWithDirectMop() throws Exception {
        File tempFile = createJsonWithReachability(
                "com.example.app.CryptoActivity", true, false);
        try {
            StaticMap map = new StaticMap(tempFile.getAbsolutePath());
            assertTrue(map.activityHasDirectMop("CryptoActivity"));
            // Trace-format query also works
            assertTrue(map.activityHasDirectMop("appCryptoActivity"));
        } finally {
            tempFile.delete();
        }
    }

    @Test
    void testGetTransitionsReturnsTargets() throws Exception {
        File tempFile = createJsonWithTransitions();
        try {
            StaticMap map = new StaticMap(tempFile.getAbsolutePath());
            List<String> transitions = map.getTransitions("MainActivity");
            assertFalse(transitions.isEmpty());
            // Self-transitions are excluded
            assertFalse(transitions.contains("MainActivity"));
        } finally {
            tempFile.delete();
        }
    }

    @Test
    void testSelfTransitionsExcluded() throws Exception {
        File tempFile = Files.createTempFile("static_map_test", ".json").toFile();
        try {
            String json = "{"
                    + "\"reachability\":[],"
                    + "\"windows\":[{\"id\":1,\"name\":\"com.example.MainActivity\",\"type\":\"ACTIVITY\",\"isMain\":true,\"widgets\":[]}],"
                    + "\"transitions\":[{\"sourceId\":1,\"targetId\":1,\"events\":[{\"type\":\"implicit_power_event\"}]}]"
                    + "}";
            try (FileWriter writer = new FileWriter(tempFile)) {
                writer.write(json);
            }
            StaticMap map = new StaticMap(tempFile.getAbsolutePath());
            assertTrue(map.isLoaded());
            assertTrue(map.getTransitions("MainActivity").isEmpty());
        } finally {
            tempFile.delete();
        }
    }

    // --- Helpers ---

    private File createJsonWithReachability(String className, boolean directMop, boolean transitiveMop)
            throws Exception {
        File tempFile = Files.createTempFile("static_map_test", ".json").toFile();
        String json = "{"
                + "\"reachability\":[{"
                + "\"className\":\"" + className + "\","
                + "\"isActivity\":true,"
                + "\"methods\":[{"
                + "\"name\":\"doEncrypt\","
                + "\"signature\":\"<" + className + ": void doEncrypt()>\","
                + "\"reachable\":true,"
                + "\"reachesMop\":" + transitiveMop + ","
                + "\"directlyReachesMop\":" + directMop
                + "}]"
                + "}],"
                + "\"windows\":[],"
                + "\"transitions\":[]"
                + "}";
        try (FileWriter writer = new FileWriter(tempFile)) {
            writer.write(json);
        }
        return tempFile;
    }

    private File createJsonWithTransitions() throws Exception {
        File tempFile = Files.createTempFile("static_map_test", ".json").toFile();
        String json = "{"
                + "\"reachability\":[],"
                + "\"windows\":["
                + "{\"id\":1,\"name\":\"com.example.app.MainActivity\",\"type\":\"ACTIVITY\",\"isMain\":true,\"widgets\":[]},"
                + "{\"id\":2,\"name\":\"com.example.app.SettingsActivity\",\"type\":\"ACTIVITY\",\"isMain\":false,\"widgets\":[]}"
                + "],"
                + "\"transitions\":["
                + "{\"sourceId\":1,\"targetId\":2,\"events\":[{\"type\":\"implicit_launch_event\"}]}"
                + "]"
                + "}";
        try (FileWriter writer = new FileWriter(tempFile)) {
            writer.write(json);
        }
        return tempFile;
    }
}
