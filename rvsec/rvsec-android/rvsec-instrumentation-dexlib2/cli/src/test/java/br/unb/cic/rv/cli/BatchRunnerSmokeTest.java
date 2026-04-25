package br.unb.cic.rv.cli;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Smoke tests for the CLI glue. Full end-to-end tests live under
 * {@code src/test/it/InstrumentationCliIT} once task 9.5's pipeline
 * integration lands (cryptoapp + hateitorrateit fixtures required).
 */
class BatchRunnerSmokeTest {

    @Test
    void perApkResultJsonShapeIsStable(@TempDir Path tmp) throws Exception {
        BatchRunner.PerApkResult result = new BatchRunner.PerApkResult(
                "foo.apk", true, "ok", "dexlib2_pipeline", Map.of("classes", 10, "methods", 200));
        Path out = tmp.resolve("results.json");
        new ObjectMapper().writerWithDefaultPrettyPrinter().writeValue(out.toFile(),
                Map.of("variant", "dexlib2", "results", List.of(result)));
        assertTrue(Files.size(out) > 0);
        String body = Files.readString(out);
        assertTrue(body.contains("\"variant\" : \"dexlib2\""),
                "variant tag must be present for the Python wrapper's contract");
        assertTrue(body.contains("\"apkName\" : \"foo.apk\""));
        assertTrue(body.contains("\"success\" : true"));
    }

    @Test
    void pipelineReturnsWellFormedFailureOnInvalidInput(@TempDir Path tmp) throws Exception {
        // Empty APK + minimal config — runPipeline must NEVER throw; it must
        // return a PerApkResult so the Python wrapper's batch loop keeps
        // processing the remaining APKs. The exact failure phase depends
        // on which validation triggers first; today the descriptor null
        // check fires before any I/O happens.
        Path apk = Files.createFile(tmp.resolve("sample.apk"));
        EffectiveConfig cfg = new EffectiveConfig(
                null, null, null, null, List.of(),
                null, null, true, null, "INFO");
        BatchRunner.PerApkResult r = BatchRunner.runPipeline(cfg, apk);
        assertEquals("sample.apk", r.apkName());
        assertFalse(r.success(),
                "with no descriptor configured, pipeline must return a non-success report");
        // config_validation when descriptor null; io_error if it tries to read
        // the empty zip; uncaught for unexpected runtime errors. All three
        // are well-formed failures, never exceptions.
        assertTrue(
                r.phase().equals("config_validation")
                        || r.phase().equals("io_error")
                        || r.phase().equals("uncaught"),
                "unexpected failure phase: " + r.phase() + " (msg: " + r.message() + ")");
    }
}
