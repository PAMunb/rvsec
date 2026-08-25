package br.unb.cic.rvsec.crysl.crysl.cli;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.net.URL;
import java.security.CodeSource;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * D-01, checked at runtime on the classpath the CLI actually runs on.
 *
 * <p>The three-module split rests on a measurement: both parsers coexist in one JVM once
 * {@code guava.version} is overridden to {@code 33.5.0-jre}. The module the CLI lives in is the one
 * that has to hold both, so this is where the measurement is worth keeping as a test.
 *
 * <p>It is not a duplicate of {@code DependencyDisciplineTest}. That one reads the effective pom and
 * the file {@code build-classpath} wrote — the build's own account of what it resolved. This one
 * asks the running JVM, through the class loader, which is the only place the failure it guards
 * against ever shows up: {@code guava-19.0} resolves, compiles and links fine, and throws
 * {@code NoSuchMethodError: ImmutableMap$Builder.buildOrThrow()} the first time {@code CrySLParser}
 * builds a map. A build log cannot see that; a loaded method can.
 *
 * <p>No corpus is read — the classes are loaded without initialisation — so it runs in CI.
 */
class OneJvmTwoParsersTest {

    @Test
    @DisplayName("D-01: the CrySL reader and the JavaMOP name space load in the same JVM")
    void test_both_parsers_are_on_one_classpath() {
        assertDoesNotThrow(() -> load("crysl.parsing.CrySLModelReader"),
                "the CrySL parser must be reachable from the module that hosts the CLI");
        assertDoesNotThrow(() -> load("javamop.util.MOPNameSpace"),
                "the JavaMOP side must be reachable from the same module, which is why "
                        + "rvsec-crysl-crysl depends on rvsec-crysl-mop");
        assertDoesNotThrow(() -> load("javamop.parser.SpecExtractor"),
                "SpecExtractor is what MopLifter parses with; if only the name space loaded, the "
                        + "dependency would be present without the parser being usable");
    }

    @Test
    @DisplayName("INV-CONF-16: the loaded Guava is the one that has buildOrThrow")
    void test_the_loaded_guava_answers_build_or_throw() throws ClassNotFoundException {
        Class<?> builder = load("com.google.common.collect.ImmutableMap$Builder");

        assertDoesNotThrow(() -> builder.getMethod("buildOrThrow"),
                "the reactor root pins guava.version to 19.0 for Soot, and 19.0 has no "
                        + "buildOrThrow. Inheriting that pin here compiles clean and dies at "
                        + "runtime inside CrySLParser - which is the whole reason the component "
                        + "parent overrides the property");

        CodeSource source = builder.getProtectionDomain().getCodeSource();
        assertTrue(source != null, "no code source for the loaded Guava; cannot say which jar it "
                + "came from");
        URL location = source.getLocation();
        assertTrue(location.toString().contains("33.5.0"),
                "the loaded Guava must be the component's override, not the reactor's 19.0. "
                        + "Loaded from " + location);
    }

    private static Class<?> load(String name) throws ClassNotFoundException {
        // initialize = false: presence on the classpath is the question, and running a parser's
        // static initialisers to answer it would make this test depend on their side effects.
        return Class.forName(name, false, OneJvmTwoParsersTest.class.getClassLoader());
    }
}
