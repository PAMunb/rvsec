package br.unb.cic.rvsec.crysl.crysl.cli;

import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.crysl.OracleCorpus;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.List;
import java.util.Properties;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * The component is reached by the reactor's existing build command, and {@code main.basedir}
 * resolves inside it.
 *
 * <p>Both facts are invisible in a passing build, which is why they are asserted rather than
 * assumed. A module that is not listed in {@code rvsec/rvsec/pom.xml} is simply never built: the
 * reactor prints {@code BUILD SUCCESS} and the component's tests do not exist as far as anyone
 * watching is concerned. And {@code main.basedir}, set by {@code directory-maven-plugin} at the
 * {@code initialize} phase, fails by leaving the literal string {@code ${main.basedir}} in whatever
 * consumed it — no error, no warning, a path that is wrong in a way nothing reports.
 *
 * <p>It reads no corpus and needs no oracle, so it runs in CI. It is named {@code *IT} because it
 * asserts properties of the build rather than of a class; the parent pom adds {@code **}{@code
 * /*IT.java} to the surefire includes so the name does not quietly exempt it from running.
 */
class ReactorBuildIT {

    /** The three children the parent pom aggregates. */
    private static final List<String> CHILDREN =
            List.of("rvsec-crysl-core", "rvsec-crysl-mop", "rvsec-crysl-crysl");

    private static Path reactorRoot;

    @BeforeAll
    static void readMainBasedir() throws IOException {
        Properties properties = new Properties();
        try (InputStream in = ReactorBuildIT.class.getResourceAsStream("/reactor-build.properties")) {
            assertTrue(in != null, "reactor-build.properties was not filtered onto the test "
                    + "classpath; the testResources configuration of the parent pom is wrong");
            properties.load(in);
        }
        String value = properties.getProperty("main.basedir");
        assertTrue(value != null && !value.contains("${"),
                "main.basedir did not resolve; directory-maven-plugin left the literal placeholder "
                        + "behind, which is how every module that writes into rv-android/lib gets a "
                        + "wrong path with no error. Read: " + value);
        reactorRoot = Paths.get(value);
    }

    @Test
    @DisplayName("main.basedir resolves to the reactor root, the project directory-of names")
    void test_main_basedir_points_at_rvsec_parent() throws IOException {
        Path rootPom = reactorRoot.resolve("pom.xml");
        assertTrue(Files.isRegularFile(rootPom), "no pom.xml at main.basedir = " + reactorRoot);
        String text = Files.readString(rootPom);
        assertTrue(text.contains("<artifactId>rvsec-parent</artifactId>"),
                "main.basedir must be the directory of br.unb.cic:rvsec-parent, which is what the "
                        + "directory-of execution is configured to look up. Found at " + rootPom);
    }

    @Test
    @DisplayName("the component is a module of the reactor, so the existing build command reaches it")
    void test_component_is_registered_in_the_reactor() throws IOException {
        Path rvsecPom = reactorRoot.resolve("rvsec").resolve("pom.xml");
        assertTrue(Files.isRegularFile(rvsecPom), "expected the rvsec aggregator at " + rvsecPom);
        assertTrue(Files.readString(rvsecPom).contains("<module>rvsec-crysl</module>"),
                "rvsec/pom.xml does not list rvsec-crysl, so `mvn clean install -DskipMopAgent` "
                        + "never builds the component and never runs a line of its tests");
    }

    @Test
    @DisplayName("the four poms exist and the parent aggregates exactly the three children")
    void test_the_four_poms_are_present() throws IOException {
        Path component = reactorRoot.resolve("rvsec").resolve("rvsec-crysl");
        Path parentPom = component.resolve("pom.xml");
        assertTrue(Files.isRegularFile(parentPom), "expected the component parent at " + parentPom);
        String parentText = Files.readString(parentPom);
        for (String child : CHILDREN) {
            assertTrue(parentText.contains("<module>" + child + "</module>"),
                    "the component parent does not aggregate " + child);
            assertTrue(Files.isRegularFile(component.resolve(child).resolve("pom.xml")),
                    "missing pom for " + child);
        }
    }

    @Test
    @DisplayName("CI runs the component's tests, and says which half it is not running")
    void test_ci_runs_the_component_and_declares_the_exclusion() throws IOException {
        // The reactor build step in CI passes -DskipTests, so a component whose entire contract is
        // tests needs a second step that turns them back on. This assertion is a tripwire on that
        // step: deleting it is a one-line change that turns ~100 passing tests into no tests at all
        // while CI keeps printing green, and nothing else in the repository would notice.
        Path workflow = reactorRoot.resolve(".github").resolve("workflows").resolve("ci.yml");
        assertTrue(Files.isRegularFile(workflow), "expected the CI workflow at " + workflow);
        String text = Files.readString(workflow);

        assertTrue(text.contains("rvsec/rvsec-crysl/pom.xml"),
                "no CI step builds the conformance component; with -DskipTests on the reactor step, "
                        + "the component's tests would run nowhere but on a developer's machine");
        assertTrue(text.contains("-DskipTests=false"),
                "the component's CI step must re-enable tests explicitly, as the dexlib2 "
                        + "grammar-tests step does");

        // The oracle-dependent half cannot run in CI at all: the upstream rules are in a separate
        // repository and android.jar comes from an SDK the runner does not have. Excluding them is
        // correct; excluding them silently is not, because the green would then look total.
        assertTrue(text.contains("-DexcludedGroups=" + OracleCorpus.TAG),
                "the CI step must exclude the " + OracleCorpus.TAG + " tag by name. The name is "
                        + "CiTags.ORACLE_DEPENDENT, in rvsec-crysl-core, and this assertion is what "
                        + "keeps the workflow text and the @Tag annotations from drifting apart");
        assertTrue(text.contains("rvsec-cognicrypt") && text.contains("ANDROID_HOME"),
                "the CI step must name what it is not running and why - rvsec-cognicrypt and the "
                        + "Android SDK - so the partial green is declared where a reader of the "
                        + "green will see it");
    }
}
