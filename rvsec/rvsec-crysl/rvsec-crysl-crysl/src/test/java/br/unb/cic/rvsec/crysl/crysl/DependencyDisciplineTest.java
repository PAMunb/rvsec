package br.unb.cic.rvsec.crysl.crysl;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Arrays;
import java.util.List;
import java.util.Properties;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * INV-CONF-16, on the CrySLParser side - the module where the Guava override actually has to land.
 *
 * <p>Like its counterpart in {@code -mop}, this reads the effective property values out of a
 * filtered resource and the resolved artifacts out of the file
 * {@code maven-dependency-plugin:build-classpath} writes, because neither of the two failures it
 * guards against is visible at compile time: {@code guava-19.0} compiles and then throws
 * {@code NoSuchMethodError: ImmutableMap$Builder.buildOrThrow()}, and an inherited
 * {@code slf4j-simple} binds a second logging backend without any build message.
 */
class DependencyDisciplineTest {

    private static Properties effectiveProperties;
    private static List<String> resolvedArtifacts;

    @BeforeAll
    static void readBuildOutputs() throws IOException {
        effectiveProperties = new Properties();
        try (InputStream in = DependencyDisciplineTest.class.getResourceAsStream(
                "/dependency-discipline.properties")) {
            assertTrue(in != null, "dependency-discipline.properties was not filtered into the "
                    + "test classpath; the testResources configuration of the parent pom is wrong");
            effectiveProperties.load(in);
        }

        Path classpathFile = Paths.get("target", "resolved-classpath.txt");
        assertTrue(Files.exists(classpathFile), "maven-dependency-plugin did not write "
                + classpathFile.toAbsolutePath() + "; the build-classpath execution is not bound");
        resolvedArtifacts = Arrays.stream(Files.readString(classpathFile).split(File.pathSeparator))
                .map(entry -> Paths.get(entry.trim()).getFileName().toString())
                .filter(name -> !name.isEmpty())
                .toList();
    }

    @Test
    @DisplayName("INV-CONF-16: the effective guava.version is the component override")
    void test_inv_conf_16_guava_version_is_overridden() {
        assertEquals("33.5.0-jre", effectiveProperties.getProperty("guava.version"));
    }

    @Test
    @DisplayName("INV-CONF-16: scala.version stays the reactor's 2.11.12")
    void test_inv_conf_16_scala_version_is_inherited() {
        assertEquals("2.11.12", effectiveProperties.getProperty("scala.version"));
    }

    @Test
    @DisplayName("INV-CONF-16: the resolved Guava is 33.5.0-jre, not the reactor's 19.0")
    void test_inv_conf_16_resolved_guava_is_the_override() {
        assertTrue(resolvedArtifacts.contains("guava-33.5.0-jre.jar"),
                "CrySLParser 4.0.6 calls ImmutableMap.Builder#buildOrThrow, absent from 19.0. "
                        + "Resolved: " + resolvedArtifacts);
        assertFalse(resolvedArtifacts.contains("guava-19.0.jar"),
                "the reactor pin must not reach this module. Resolved: " + resolvedArtifacts);
    }

    @Test
    @DisplayName("slf4j-simple is excluded and only the API remains")
    void test_slf4j_simple_absent_from_the_crysl_classpath() {
        assertFalse(resolvedArtifacts.stream().anyMatch(name -> name.startsWith("slf4j-simple")),
                "CrySLParser declares slf4j-simple in compile scope; the exclusion is what keeps a "
                        + "second logging backend off every consumer. Resolved: " + resolvedArtifacts);
        assertTrue(resolvedArtifacts.stream().anyMatch(name -> name.startsWith("slf4j-api")),
                "the API is expected to remain. Resolved: " + resolvedArtifacts);
    }
}
