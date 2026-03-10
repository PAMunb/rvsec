package br.unb.cic.rvsmart.core;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.file.Path;
import java.util.Properties;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for Config default loading and typed getters.
 */
class ConfigTest {

    @Test
    void testDefaults() {
        Config config = Config.defaults();
        assertEquals(100, config.getThrottleMs());
        assertEquals(3, config.getMaxRetriesPerCycle());
        assertEquals(150, config.getAdaptiveWaitMs());
        assertEquals(0.05f, config.getLlmProbability(), 0.001f);
        assertEquals(500.0f, config.getMopDirectScore(), 0.01f);
        assertEquals(300.0f, config.getMopTransitiveScore(), 0.01f);
        assertEquals(200.0f, config.getGradualDecayBase(), 0.01f);
        assertEquals(0.7f, config.getGradualDecayRate(), 0.01f);
        assertEquals(5, config.getGradualDecayMinVisits());
        assertEquals(-100.0f, config.getBackBaseScore(), 0.01f);
        assertEquals(-500.0f, config.getRestartBaseScore(), 0.01f);
        assertEquals(0.15f, config.getStochasticProbability(), 0.01f);
        assertEquals(6, config.getMaxReEnables());
        assertEquals(6, config.getMultiValueSaturationThreshold());
        assertEquals(10, config.getStuckMaxBlocks());
        assertEquals("http://192.168.0.36:30000/v1", config.getLlmBaseUrl());
        assertEquals("Qwen/Qwen3-VL-4B-Instruct", config.getLlmModel());
        assertEquals(10000, config.getLogcatBufferSize());
    }

    @Test
    void testCliOverrides() {
        Config config = Config.defaults();
        config.setPackageName("com.example");
        config.setTimeout(120);
        config.setMode("multimode");
        config.setSeed(42);
        config.setStaticDataPath("/data/analysis.json");

        assertEquals("com.example", config.getPackageName());
        assertEquals(120, config.getTimeout());
        assertEquals("multimode", config.getMode());
        assertEquals(42, config.getSeed().intValue());
        assertEquals("/data/analysis.json", config.getStaticDataPath());
    }

    @Test
    void testDefaultModeIsPureAlgorithm() {
        Config config = Config.defaults();
        assertEquals("pure_algorithm", config.getMode());
    }

    @Test
    void testNullSeedByDefault() {
        Config config = Config.defaults();
        assertNull(config.getSeed());
    }

    // --- Timing/throttle tests (Group 18) ---

    @Test
    void testThrottleDefaultIs100ms() {
        Config config = Config.defaults();
        assertEquals(100, config.getThrottleMs(),
                "Throttle reduced to 100ms for faster exploration; adaptive wait handles slow transitions");
    }

    @Test
    void testMaxRetriesDefaultIs3() {
        Config config = Config.defaults();
        assertEquals(3, config.getMaxRetriesPerCycle(),
                "Max retries set to 3 for multi-attempt retry within a single cycle");
    }

    @Test
    void testAdaptiveWaitDefaultIs150ms() {
        Config config = Config.defaults();
        assertEquals(150, config.getAdaptiveWaitMs(),
                "Adaptive wait provides extra time for slow transitions");
    }

    @Test
    void testTimingOverridesFromPropertiesFile(@TempDir Path tempDir) throws IOException {
        File propsFile = tempDir.resolve("test.properties").toFile();
        Properties props = new Properties();
        props.setProperty("throttle_ms", "300");
        props.setProperty("max_retries_per_cycle", "2");
        props.setProperty("adaptive_wait_ms", "250");
        try (FileOutputStream fos = new FileOutputStream(propsFile)) {
            props.store(fos, null);
        }

        Config config = Config.fromFile(propsFile);
        assertEquals(300, config.getThrottleMs());
        assertEquals(2, config.getMaxRetriesPerCycle());
        assertEquals(250, config.getAdaptiveWaitMs());
    }

    // --- Out-of-app detection tests (Group 20) ---

    @Test
    void testOutOfAppToleranceDefaultIs3() {
        Config config = Config.defaults();
        assertEquals(3, config.getOutOfAppTolerance(),
                "Out-of-app tolerance should default to 3 consecutive iterations");
    }

    @Test
    void testOutOfAppToleranceOverrideFromProperties(@TempDir Path tempDir) throws IOException {
        File propsFile = tempDir.resolve("test.properties").toFile();
        Properties props = new Properties();
        props.setProperty("out_of_app_tolerance", "5");
        try (FileOutputStream fos = new FileOutputStream(propsFile)) {
            props.store(fos, null);
        }

        Config config = Config.fromFile(propsFile);
        assertEquals(5, config.getOutOfAppTolerance(),
                "Out-of-app tolerance should be overridable via properties");
    }

    // --- Menu fuzz tests ---

    @Test
    void testMenuFuzzRateDefaultIs0_02() {
        Config config = Config.defaults();
        assertEquals(0.02f, config.getMenuFuzzRate(), 0.001f,
                "Menu fuzz rate should default to 2%");
    }

    // --- Periodic restart tests ---

    @Test
    void testPeriodicRestartThresholdDefaultIs200() {
        Config config = Config.defaults();
        assertEquals(200, config.getPeriodicRestartThreshold(),
                "Periodic restart threshold should default to 200 iterations");
    }

    // --- State refresh tests ---

    @Test
    void testCaptureRetryMinElementsDefaultIs3() {
        Config config = Config.defaults();
        assertEquals(3, config.getCaptureRetryMinElements(),
                "Capture retry min elements should default to 3");
    }

    @Test
    void testCaptureRetryMaxDefaultIs3() {
        Config config = Config.defaults();
        assertEquals(3, config.getCaptureRetryMax(),
                "Capture retry max should default to 3");
    }

    @Test
    void testCaptureRetryDelayMsDefaultIs1000() {
        Config config = Config.defaults();
        assertEquals(1000L, config.getCaptureRetryDelayMs(),
                "Capture retry delay should default to 1000ms");
    }

    @Test
    void testNewConfigOverridesFromPropertiesFile(@TempDir Path tempDir) throws IOException {
        File propsFile = tempDir.resolve("test.properties").toFile();
        Properties props = new Properties();
        props.setProperty("menu_fuzz_rate", "0.05");
        props.setProperty("periodic_restart_threshold", "100");
        props.setProperty("capture_retry_min_elements", "5");
        props.setProperty("capture_retry_max", "2");
        props.setProperty("capture_retry_delay_ms", "500");
        try (FileOutputStream fos = new FileOutputStream(propsFile)) {
            props.store(fos, null);
        }

        Config config = Config.fromFile(propsFile);
        assertEquals(0.05f, config.getMenuFuzzRate(), 0.001f);
        assertEquals(100, config.getPeriodicRestartThreshold());
        assertEquals(5, config.getCaptureRetryMinElements());
        assertEquals(2, config.getCaptureRetryMax());
        assertEquals(500L, config.getCaptureRetryDelayMs());
    }

    @Test
    void testAdaptiveWaitCanBeDisabledViaProperties(@TempDir Path tempDir) throws IOException {
        File propsFile = tempDir.resolve("test.properties").toFile();
        Properties props = new Properties();
        props.setProperty("adaptive_wait_ms", "0");
        try (FileOutputStream fos = new FileOutputStream(propsFile)) {
            props.store(fos, null);
        }

        Config config = Config.fromFile(propsFile);
        assertEquals(0, config.getAdaptiveWaitMs(),
                "Setting adaptive_wait_ms=0 disables the adaptive wait");
    }
}
