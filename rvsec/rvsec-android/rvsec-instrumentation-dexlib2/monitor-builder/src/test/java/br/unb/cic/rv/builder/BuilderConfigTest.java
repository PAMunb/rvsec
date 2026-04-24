package br.unb.cic.rv.builder;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

class BuilderConfigTest {

    @Test
    void validatedAcceptsExistingFiles(@TempDir Path tmp) throws Exception {
        Path javac = Files.createFile(tmp.resolve("javac"));
        Path d8 = Files.createFile(tmp.resolve("d8"));
        Path rt = Files.createFile(tmp.resolve("rt.jar"));
        Path android = Files.createFile(tmp.resolve("android.jar"));
        BuilderConfig cfg = new BuilderConfig(javac, d8, rt, android, List.of());
        assertSame(cfg, cfg.validated());
    }

    @Test
    void validatedRejectsMissingFile(@TempDir Path tmp) throws Exception {
        Path javac = Files.createFile(tmp.resolve("javac"));
        Path d8 = Files.createFile(tmp.resolve("d8"));
        Path missing = tmp.resolve("missing.jar");
        Path android = Files.createFile(tmp.resolve("android.jar"));
        BuilderConfig cfg = new BuilderConfig(javac, d8, missing, android, List.of());
        assertThrows(IllegalArgumentException.class, cfg::validated);
    }

    @Test
    void nullFieldsRejected() {
        assertThrows(NullPointerException.class,
                () -> new BuilderConfig(null, null, null, null, null));
    }
}
