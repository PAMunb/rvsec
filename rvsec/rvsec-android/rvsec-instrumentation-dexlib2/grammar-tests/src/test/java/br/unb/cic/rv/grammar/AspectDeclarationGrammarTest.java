package br.unb.cic.rv.grammar;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.AspectDescriptor;
import br.unb.cic.rv.descriptor.DescriptorReader;
import br.unb.cic.rv.grammar.util.AbsorbingStage;

import org.junit.jupiter.api.Test;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.regex.Pattern;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Backs the six aspect-declaration-mechanics matrix rows.
 *
 * <ul>
 *   <li><b>{@code aspect Foo { ... }}</b> and <b>{@code pointcut p(): ...} declaration</b> —
 *       <b>NOT-NEEDED β</b>, absorber {@code DESCRIPTOR_READER}: these declaration-syntax tokens have
 *       non-zero source demand ({@code Coverage.aj} declares one {@code aspect} and two named
 *       {@code pointcut}s) but the dexlib2 {@code PointcutExpressionParser} never sees them — JavaMOP's
 *       descriptor emit flattens every aspect/pointcut declaration into the {@code AdviceDescriptor.expression}
 *       strings, which carry only pointcut expressions (call/target/args/…). deferred.md §2.2.2.</li>
 *   <li><b>abstract aspect + concrete subaspect</b>, <b>aspect inheritance</b>,
 *       <b>{@code declare precedence}</b>, <b>privileged aspect</b> — <b>NOT-NEEDED α</b>: zero source
 *       demand across all corpora and no parser path (round-8 P-decision moved these from β to α,
 *       deferred.md §2.1).</li>
 * </ul>
 */
class AspectDeclarationGrammarTest {

    /** The pipeline stage that absorbs the {@code aspect}/{@code pointcut} declaration syntax. */
    static final AbsorbingStage ABSORBER = AbsorbingStage.DESCRIPTOR_READER;

    private static final Pattern ASPECT_DECL = Pattern.compile("(?<![A-Za-z0-9_])aspect\\s");
    private static final Pattern POINTCUT_DECL = Pattern.compile("(?<![A-Za-z0-9_])pointcut\\s");

    // ----- path β: aspect Foo { ... } / pointcut p(): ... ----------------------------------------

    /**
     * {@code aspect Foo { ... }} declaration syntax is absorbed by the JavaMOP descriptor emit /
     * {@code DescriptorReader}: source demand ≥ 1 ({@code Coverage.aj} declares an aspect), but every
     * {@code AdviceDescriptor.expression} the dexlib2 parser receives is a pure pointcut expression
     * with NO {@code aspect} declaration token.
     */
    @Test
    void aspectFooAbsorbedByDescriptorReader() throws Exception {
        // (a) source demand ≥ 1 — Coverage.aj declares one aspect.
        assertTrue(ASPECT_DECL.matcher(coverageAj()).results().toList().size() >= 1,
                "aspect Foo { } declaration appears in Coverage.aj (source demand ≥ 1)");

        // (b) absorbed: no AdviceDescriptor.expression carries the `aspect` declaration token.
        for (AdviceDescriptor a : canonicalDescriptor().getAdvices()) {
            assertTrue(ASPECT_DECL.matcher(a.getExpression()).results().toList().isEmpty(),
                    "the dexlib2 parser receives a pure pointcut expression with no `aspect` token: "
                            + a.getExpression());
        }

        // (c) named absorber.
        assertEquals(AbsorbingStage.DESCRIPTOR_READER, ABSORBER);
    }

    /**
     * {@code pointcut p(): ...} named-declaration syntax is absorbed the same way: source demand ≥ 1
     * ({@code Coverage.aj} declares two named pointcuts), but the flattened descriptor {@code expression}
     * fields carry no {@code pointcut} declaration token (the named pointcut is inlined / resolved at
     * descriptor-emit time; the JCA {@code BaseAspect.notwithin()} ref is the one named reference that
     * survives, resolved in-change via §4.B/§4.D against {@code baseAspectExclusions}, not as a
     * {@code pointcut} declaration).
     */
    @Test
    void namedPointcutDeclarationAbsorbedByDescriptorReader() throws Exception {
        assertTrue(POINTCUT_DECL.matcher(coverageAj()).results().toList().size() >= 1,
                "pointcut p(): ... declaration appears in Coverage.aj (source demand ≥ 1)");

        for (AdviceDescriptor a : canonicalDescriptor().getAdvices()) {
            assertTrue(POINTCUT_DECL.matcher(a.getExpression()).results().toList().isEmpty(),
                    "the dexlib2 parser receives a pure pointcut expression with no `pointcut` "
                            + "declaration token: " + a.getExpression());
        }

        assertEquals(AbsorbingStage.DESCRIPTOR_READER, ABSORBER);
    }

    // ----- path α: zero source demand + no parser path -------------------------------------------

    @Test
    void abstractAspectHasZeroCorpusDemand() {
        assertDeclarationAbsentEverywhere(Pattern.compile("\\babstract\\s+aspect\\b"),
                "abstract aspect");
    }

    @Test
    void aspectInheritanceHasZeroCorpusDemand() {
        assertDeclarationAbsentEverywhere(Pattern.compile("\\baspect\\s+[A-Za-z0-9_]+\\s+extends\\b"),
                "aspect inheritance (aspect Bar extends Foo)");
    }

    @Test
    void declarePrecedenceHasZeroCorpusDemand() {
        assertDeclarationAbsentEverywhere(Pattern.compile("\\bdeclare\\s+precedence\\b"),
                "declare precedence");
    }

    @Test
    void privilegedAspectHasZeroCorpusDemand() {
        assertDeclarationAbsentEverywhere(Pattern.compile("\\bprivileged\\b"),
                "privileged aspect");
    }

    // ----- helpers -------------------------------------------------------------------------------

    /** Assert the declaration form fires zero times across all three compiled corpora and Coverage.aj
     *  (the full source surface). */
    private static void assertDeclarationAbsentEverywhere(Pattern p, String label) {
        for (String corpus : new String[]{"jca", "generic", "generic_new"}) {
            assertEquals(0, p.matcher(compiledAj(corpus)).results().toList().size(),
                    label + " has zero demand in the compiled .aj for " + corpus);
        }
        assertEquals(0, p.matcher(coverageAj()).results().toList().size(),
                label + " has zero demand in Coverage.aj");
    }

    /** The canonical production descriptor (JavaMOP descriptor emit output) — proves the dexlib2
     *  parser receives flattened {@code expression} strings, never declaration syntax. */
    private static AspectDescriptor canonicalDescriptor() throws Exception {
        try (InputStream in = AspectDeclarationGrammarTest.class.getClassLoader()
                .getResourceAsStream("MultiSpec_1MonitorAspect.json")) {
            // The canonical fixture ships in descriptor-reader's test resources; it is not on the
            // grammar-tests classpath, so resolve it from the sibling module's source tree.
            if (in != null) {
                return DescriptorReader.read(in);
            }
        }
        Path json = Paths.get(System.getenv("RVSEC_HOME"), "rvsec", "rvsec-android",
                "rvsec-instrumentation-dexlib2", "descriptor-reader", "src", "test", "resources",
                "MultiSpec_1MonitorAspect.json");
        assertTrue(Files.isRegularFile(json),
                "canonical descriptor JSON present at " + json);
        return DescriptorReader.read(json);
    }

    private static String compiledAj(String corpus) {
        String path = "compiled-aj-fixtures/" + corpus + "/MultiSpec_1MonitorAspect.aj";
        try (InputStream in = AspectDeclarationGrammarTest.class.getClassLoader()
                .getResourceAsStream(path)) {
            assertNotNull(in, "compiled .aj evidence file present on classpath: " + path);
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        } catch (java.io.IOException e) {
            throw new RuntimeException("failed to read compiled .aj fixture " + path, e);
        }
    }

    private static String coverageAj() {
        Path cov = Paths.get(System.getenv("RVSEC_HOME"), "rvsec", "rvsec-mop", "src", "main",
                "resources", "aspect", "Coverage.aj");
        try {
            return Files.readString(cov);
        } catch (java.io.IOException e) {
            throw new RuntimeException("failed to read Coverage.aj at " + cov, e);
        }
    }
}
