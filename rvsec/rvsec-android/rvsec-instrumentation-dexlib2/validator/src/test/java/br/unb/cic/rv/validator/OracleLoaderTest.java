package br.unb.cic.rv.validator;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.*;

class OracleLoaderTest {

    @Test
    void failsWithFewerThanThreeOracles(@TempDir Path tmp) throws Exception {
        Files.createFile(tmp.resolve("cryptoapp-oracle.yaml"));
        var loaded = OracleLoader.load(tmp);
        Report r = OracleLoader.report(loaded);
        assertFalse(r.passed);
        assertEquals(1, ((Number) r.metrics.get("oracleCount")).intValue());
        assertTrue(r.message.contains("INV-INS-22"));
    }

    @Test
    void passesWithThreeOracles(@TempDir Path tmp) throws Exception {
        Files.createFile(tmp.resolve("cryptoapp-oracle.yaml"));
        Files.createFile(tmp.resolve("hateitorrateit-oracle.yaml"));
        Files.createFile(tmp.resolve("multidex-oracle.yaml"));
        var loaded = OracleLoader.load(tmp);
        Report r = OracleLoader.report(loaded);
        assertTrue(r.passed);
        assertEquals(3, ((Number) r.metrics.get("oracleCount")).intValue());
    }

    @Test
    void ignoresNonOracleYamls(@TempDir Path tmp) throws Exception {
        Files.createFile(tmp.resolve("cryptoapp-oracle.yaml"));
        Files.createFile(tmp.resolve("layer4-thresholds.yaml"));
        Files.createFile(tmp.resolve("README.md"));
        var loaded = OracleLoader.load(tmp);
        // thresholds file is NOT an oracle — glob filters on -oracle.yaml suffix.
        assertEquals(1, loaded.files().size());
    }
}
