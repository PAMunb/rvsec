package br.unb.cic.rvsec.crysl.mop;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.unb.cic.rvsec.crysl.core.model.Event;
import br.unb.cic.rvsec.crysl.core.model.Label;
import br.unb.cic.rvsec.crysl.core.model.Signature;
import br.unb.cic.rvsec.crysl.core.model.SourceStamp;
import br.unb.cic.rvsec.crysl.core.model.Version;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * The signatures an event's pointcut names, read the way the weaver matches them (INV-CONF-19).
 *
 * <p>The input is one synthetic {@code .mop} written into a temporary directory and lifted by
 * {@link MopLifter}, which is the route every corpus file takes to {@link PointcutExpander}. Each
 * event isolates one rule: the arity an {@code args(...)} without {@code ..} fixes, the arity it
 * contradicts, the lower bound an {@code args(...)} with {@code ..} leaves alone, and the binary name
 * of a nested type imported by its canonical name.
 */
class PointcutExpanderTest {

    private static final String SPEC = String.join("\n",
            "package mop;",
            "",
            "import java.util.concurrent.TimeUnit;",
            "import java.util.concurrent.locks.Condition;",
            "import javax.net.ssl.KeyManagerFactory;",
            "import java.security.KeyStore;",
            "import java.security.KeyStore.ProtectionParameter;",
            "import java.security.KeyStore.Entry;",
            "",
            "DemoSpec(Object o) {",
            "    event g1 after(String alg) returning(KeyManagerFactory o):",
            "      call(public static KeyManagerFactory KeyManagerFactory.getInstance(String))",
            "      && args(alg) {",
            "    }",
            "",
            "    event g2 after(String alg) returning(KeyManagerFactory o):",
            "      call(public static KeyManagerFactory KeyManagerFactory.getInstance(String, ..))",
            "      && args(alg, *) {",
            "    }",
            "",
            "    event g3 after(String alg) returning(KeyManagerFactory o):",
            "      call(public static KeyManagerFactory KeyManagerFactory.getInstance(String, ..))",
            "      && args(alg, ..) {",
            "    }",
            "",
            "    event w before(Condition o, long t):",
            "      call(* Condition.await(long, TimeUnit)) && target(o) && args(t) {",
            "    }",
            "",
            "    event e after(KeyStore o, String alias, ProtectionParameter p):",
            "      call(public Entry KeyStore.getEntry(String, ProtectionParameter))",
            "      && target(o) && args(alias, p) {",
            "    }",
            "",
            "    ere : (g1 | g2 | g3 | w | e)*",
            "",
            "    @fail {",
            "    }",
            "}",
            "");

    private static final String FACTORY = "javax.net.ssl.KeyManagerFactory";
    private static final String STRING = "java.lang.String";

    private static MopLift lift;

    @BeforeAll
    static void liftTheSyntheticSpecification(@TempDir Path dir) throws Exception {
        Path file = dir.resolve("DemoSpec.mop");
        Files.writeString(file, SPEC, StandardCharsets.UTF_8);
        lift = new MopLifter().read(file,
                new Version("synthetic", new SourceStamp("rvsec", "test-fixture", Instant.EPOCH)));
    }

    @Test
    @DisplayName("getInstance(String, ..) && args(alg, *) names getInstance(String, *)")
    void test_a_trailing_ellipsis_is_narrowed_to_the_args_arity() {
        assertEquals(Set.of(new Signature(FACTORY, "getInstance", List.of(STRING, "*"), FACTORY)),
                signaturesOf("g2"));
        assertEquals(List.of(new Label("g1"), new Label("g3")),
                lift.morphism().images().get(
                        new Signature(FACTORY, "getInstance", List.of(STRING), FACTORY)),
                "the one-argument call is claimed by g1 and by g3's lower bound, never by g2");
    }

    @Test
    @DisplayName("args(t) on await(long, TimeUnit) names no signature")
    void test_a_contradicted_fixed_arity_names_no_signature() {
        assertTrue(signaturesOf("w").isEmpty(),
                "a one-position args matches no two-argument call: " + signaturesOf("w"));
    }

    @Test
    @DisplayName("args(alg, ..) narrows nothing")
    void test_an_args_clause_with_an_ellipsis_narrows_nothing() {
        assertEquals(Set.of(new Signature(FACTORY, "getInstance", List.of(STRING, ".."), FACTORY)),
                signaturesOf("g3"));
    }

    @Test
    @DisplayName("ProtectionParameter imported from java.security.KeyStore.ProtectionParameter is "
            + "java.security.KeyStore$ProtectionParameter")
    void test_a_nested_type_is_spelled_by_its_binary_name() {
        assertEquals(Set.of(new Signature("java.security.KeyStore", "getEntry",
                        List.of(STRING, "java.security.KeyStore$ProtectionParameter"),
                        "java.security.KeyStore$Entry")),
                signaturesOf("e"));
    }

    private static Set<Signature> signaturesOf(String label) {
        return lift.model().events().stream()
                .filter(event -> event.label().name().equals(label))
                .map(Event::signatures)
                .findFirst()
                .orElseThrow(() -> new AssertionError("no event " + label));
    }
}
