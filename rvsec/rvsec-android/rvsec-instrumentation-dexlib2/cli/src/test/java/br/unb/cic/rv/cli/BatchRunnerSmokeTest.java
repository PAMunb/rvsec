package br.unb.cic.rv.cli;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
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
    void pipelineReturnsNonSuccessUntilIntegrationLands(@TempDir Path tmp) throws Exception {
        Path apk = Files.createFile(tmp.resolve("sample.apk"));
        BatchRunner.PerApkResult r = BatchRunner.runPipeline(null, apk);
        assertEquals("sample.apk", r.apkName());
        // Contract: while the pipeline scaffold is in place (task 9.5 pending),
        // the result is a well-formed failure rather than an exception so the
        // Python wrapper's batch loop keeps processing other APKs.
        assertEquals(false, r.success());
        assertTrue(r.message().toLowerCase().contains("pending"));
    }
}
