package br.unb.cic.rvsec.crysl.mop;

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
 * INV-CONF-16, on the javamop side.
 *
 * <p>The two facts this asserts are not visible in a successful build: a wrong {@code guava.version}
 * compiles clean and dies at runtime with {@code NoSuchMethodError}, and a wrong
 * {@code scala.version} compiles clean and dies at runtime with
 * {@code NoClassDefFoundError: scala/Serializable}. Silence from the compiler is not evidence, so
 * the versions are read back from artifacts the build produced:
 *
 * <ul>
 *   <li>{@code dependency-discipline.properties} is interpolated by resource filtering, so it holds
 *       the effective property values, not the text of one pom;
 *   <li>{@code target/resolved-classpath.txt} is written by
 *       {@code maven-dependency-plugin:build-classpath} with {@code includeScope=runtime}, so it
 *       holds the artifacts actually resolved, including anything a transitive dependency moved.
 * </ul>
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
                .map(entry -> artifactNameOf(Paths.get(entry.trim())))
                .filter(name -> !name.isEmpty())
                .toList();
    }

    /**
     * The artifact a classpath entry stands for.
     *
     * <p>Whether an entry is a jar or a directory depends on how Maven was invoked, and both
     * invocations happen: built through the component aggregator alone
     * ({@code mvn -f rvsec/rvsec-crysl/pom.xml test}) the sibling modules resolve to jars in the
     * local repository, while built from the reactor root with {@code -am} they resolve to
     * {@code <module>/target/classes} directories, because the reactor prefers its own output. A
     * check written against the file name alone therefore reads {@code ptltl-…jar} under the first
     * invocation and the string {@code classes} under the second, and reports the dependency
     * missing when nothing is missing — a false red of exactly the shape RISK-010 is about, one
     * step removed. For a {@code target/classes} entry the artifact is named by the module
     * directory two levels up, which is what this recovers.
     */
    private static String artifactNameOf(Path entry) {
        Path fileName = entry.getFileName();
        if (fileName != null && fileName.toString().equals("classes")
                && entry.getParent() != null && entry.getParent().getParent() != null) {
            Path module = entry.getParent().getParent().getFileName();
            return module == null ? "" : module.toString();
        }
        return fileName == null ? "" : fileName.toString();
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
    @DisplayName("INV-CONF-16: ptltl and scala-library 2.11.12 are on the resolved classpath")
    void test_inv_conf_16_ptltl_is_present() {
        assertTrue(resolvedArtifacts.stream().anyMatch(name -> name.startsWith("ptltl")),
                "ptltl must not be excluded; it arrives through javamop -> rv-monitor. Resolved: "
                        + resolvedArtifacts);
        assertTrue(resolvedArtifacts.contains("scala-library-2.11.12.jar"),
                "ptltl was compiled against Scala 2.11.12. Resolved: " + resolvedArtifacts);
    }

    @Test
    @DisplayName("javamop pulls no Guava, so the override has no effect on this module")
    void test_guava_absent_from_the_mop_classpath() {
        assertFalse(resolvedArtifacts.stream().anyMatch(name -> name.startsWith("guava-")),
                "the guava.version override is expected to land on -crysl only, because javamop "
                        + "pulls no Guava at all. Resolved: " + resolvedArtifacts);
    }
}
