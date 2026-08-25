package br.unb.cic.rvsec.crysl.crysl;

import br.unb.cic.rvsec.crysl.core.CiTags;
import br.unb.cic.rvsec.crysl.core.model.SourceStamp;
import br.unb.cic.rvsec.crysl.core.model.Version;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.Instant;
import java.util.Optional;
import org.junit.jupiter.api.Assumptions;

/**
 * Locates the two inputs that live outside this git repository, and says so out loud when it
 * cannot.
 *
 * <p>The corpus this component compares against is not in the checkout. The 49 upstream rules are in
 * {@code rvsec-cognicrypt}, a separate repository, and {@code android.jar} comes from
 * {@code $ANDROID_HOME}. CI checks out one repository and has no SDK, so every test that touches
 * either of them is unrunnable there — a fact of the environment, not something to work around by
 * vendoring a third copy of a corpus that already exists twice.
 *
 * <p>It is public, and its package-private neighbours are not, because the CLI's smoke test lives
 * in the {@code cli} test package and needs the same two paths and the same tag literal. A second
 * copy of either would be a second thing to keep in sync with the CI workflow.
 *
 * <p>Two mechanisms, doing different jobs. The {@link #TAG} lets the CI workflow exclude these tests
 * by name, so the green it prints is honestly labelled. The {@link Assumptions} below make a local
 * run that is missing an input <em>say which path was missing</em> rather than pass quietly: a test
 * that goes green when its corpus is absent is a false green wearing a different hat, and this
 * repository has shipped that twice already.
 */
public final class OracleCorpus {

    /**
     * JUnit tag for every test that reads an input from outside this repository.
     *
     * <p>The name itself lives in {@link CiTags}, in {@code rvsec-crysl-core}, because
     * {@code rvsec-crysl-mop} tags one test with it too and cannot see this class. This field stays
     * because most of the annotations in this module read better as {@code OracleCorpus.TAG}, but
     * it is an alias, not a second definition: there is one string, and {@code ReactorBuildIT}
     * checks the CI workflow against it.
     */
    public static final String TAG = CiTags.ORACLE_DEPENDENT;

    /** Overrides the walk-up search for the upstream rules. */
    private static final String RULES_ENV = "RVSEC_CRYSL_RULES";

    /** Overrides {@code $ANDROID_HOME/platforms/android-30/android.jar}. */
    private static final String JAR_ENV = "RVSEC_ANDROID_JAR";

    /** The API level the index assertions are anchored to. */
    static final String API_LEVEL = "android-30";

    private OracleCorpus() {
    }

    /**
     * The upstream oracle directory, read-only (INV-CONF-12).
     *
     * @return {@code rvsec-cognicrypt/CrySL-Rules}
     */
    public static Path cryslRules() {
        Optional<Path> located = fromEnv(RULES_ENV).or(OracleCorpus::searchUpwards);
        Assumptions.assumeTrue(located.isPresent(),
                "the upstream oracle was not found. It lives in the sibling repository "
                        + "rvsec-cognicrypt, at CrySL-Rules/, which is not part of this checkout. "
                        + "Set " + RULES_ENV + " to point at it, or place the repository beside "
                        + "rvsec. Searched upwards from " + Paths.get("").toAbsolutePath());
        return located.get();
    }

    /**
     * The platform jar the API index is built from.
     *
     * @return {@code $ANDROID_HOME/platforms/android-30/android.jar}
     */
    public static Path androidJar() {
        Optional<Path> located = fromEnv(JAR_ENV).or(() -> {
            String home = System.getenv("ANDROID_HOME");
            if (home == null || home.isBlank()) {
                return Optional.empty();
            }
            Path jar = Paths.get(home, "platforms", API_LEVEL, "android.jar");
            return Files.isReadable(jar) ? Optional.of(jar) : Optional.empty();
        });
        Assumptions.assumeTrue(located.isPresent(),
                "android.jar for " + API_LEVEL + " was not found. It comes from the Android SDK, "
                        + "which is not part of this checkout. Set ANDROID_HOME (currently "
                        + System.getenv("ANDROID_HOME") + ") or " + JAR_ENV + ".");
        return located.get();
    }

    /**
     * The stamp the lifted models carry in tests.
     *
     * <p>The commit is a placeholder here because a test is not a run: what the tests check is that
     * the identity the caller supplies is the identity the model ends up with, never that this class
     * knows which commit the oracle is at.
     */
    static Version version() {
        return new Version("CrySL-Rules",
                new SourceStamp("rvsec-cognicrypt", "test-fixture", Instant.EPOCH));
    }

    private static Optional<Path> fromEnv(String variable) {
        String value = System.getenv(variable);
        if (value == null || value.isBlank()) {
            return Optional.empty();
        }
        Path path = Paths.get(value);
        return Files.exists(path) ? Optional.of(path) : Optional.empty();
    }

    private static Optional<Path> searchUpwards() {
        Path current = Paths.get("").toAbsolutePath();
        while (current != null) {
            Path candidate = current.resolve("rvsec-cognicrypt").resolve("CrySL-Rules");
            if (Files.isDirectory(candidate)) {
                return Optional.of(candidate);
            }
            current = current.getParent();
        }
        return Optional.empty();
    }
}
