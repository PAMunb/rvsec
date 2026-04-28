package br.unb.cic.rv.merger;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.junit.jupiter.api.Assertions.*;

class MergerConfigTest {

    @Test
    void validatedAcceptsPresentTools(@TempDir Path tmp) throws Exception {
        Path apksigner = Files.createFile(tmp.resolve("apksigner"));
        Path zipalign = Files.createFile(tmp.resolve("zipalign"));
        Path keystore = Files.createFile(tmp.resolve("keystore.jks"));
        MergerConfig cfg = new MergerConfig(apksigner, zipalign, keystore,
                "pass", "alias", "keypass");
        assertSame(cfg, cfg.validated());
    }

    @Test
    void validatedRejectsMissingKeystore(@TempDir Path tmp) throws Exception {
        Path apksigner = Files.createFile(tmp.resolve("apksigner"));
        Path zipalign = Files.createFile(tmp.resolve("zipalign"));
        Path keystore = tmp.resolve("missing.jks");
        MergerConfig cfg = new MergerConfig(apksigner, zipalign, keystore,
                "pass", "alias", "keypass");
        assertThrows(IllegalArgumentException.class, cfg::validated);
    }

    @Test
    void nullsRejected() {
        assertThrows(NullPointerException.class,
                () -> new MergerConfig(null, null, null, null, null, null));
    }
}
