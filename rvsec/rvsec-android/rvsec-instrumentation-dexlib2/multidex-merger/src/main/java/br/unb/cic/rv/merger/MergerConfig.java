package br.unb.cic.rv.merger;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Objects;

/**
 * External-tool paths and keystore secrets used by {@link MultidexMerger}.
 *
 * <p>Per INV-INS-14 the dexlib2 variant signs APKs via {@code apksigner v3}
 * alone (no {@code d2j-apk-sign}, no {@code jarsigner}); this class is the
 * single place that enforces the presence + executability of the Android SDK
 * binaries that realize that contract.
 */
public final class MergerConfig {

    public final Path apksignerBin;
    public final Path zipalignBin;
    public final Path keystore;
    public final String keystorePassword;
    public final String keyAlias;
    public final String keyPassword;

    public MergerConfig(Path apksignerBin, Path zipalignBin, Path keystore,
                        String keystorePassword, String keyAlias, String keyPassword) {
        this.apksignerBin = Objects.requireNonNull(apksignerBin, "apksignerBin");
        this.zipalignBin = Objects.requireNonNull(zipalignBin, "zipalignBin");
        this.keystore = Objects.requireNonNull(keystore, "keystore");
        this.keystorePassword = Objects.requireNonNull(keystorePassword, "keystorePassword");
        this.keyAlias = Objects.requireNonNull(keyAlias, "keyAlias");
        this.keyPassword = Objects.requireNonNull(keyPassword, "keyPassword");
    }

    public MergerConfig validated() {
        requireFile(apksignerBin, "apksignerBin");
        requireFile(zipalignBin, "zipalignBin");
        requireFile(keystore, "keystore");
        return this;
    }

    private static void requireFile(Path p, String label) {
        if (!Files.isRegularFile(p)) {
            throw new IllegalArgumentException(label + " not a file: " + p);
        }
    }
}
