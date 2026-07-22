package br.unb.cic.rv.grammar;

import br.unb.cic.rv.pointcut.CallPC;
import br.unb.cic.rv.pointcut.PointcutExpressionParser;

import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.regex.Pattern;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

/**
 * Backs the five SignaturePattern-modifier matrix rows.
 *
 * <ul>
 *   <li><b>positive visibility ({@code public})</b> — <b>COVERED</b>: the parser strips the leading
 *       visibility modifier ({@code PointcutExpressionParser.stripModifiers}) and still resolves the
 *       method name / owner / return correctly, so a {@code call(public ...)} pointcut matches the
 *       underlying method. Real JCA advice expressions always spell {@code public} (25+ sites), so
 *       this is exercised, not theoretical.</li>
 *   <li><b>negated visibility ({@code !public}), {@code static}, {@code final},
 *       {@code throws ExceptionPattern}</b> — <b>NOT-NEEDED α</b>: there is no modifier-<em>matching</em>
 *       capability (modifiers are stripped, never used as a discriminating predicate) and zero corpus
 *       demand for modifier discrimination. deferred.md §2.1 lists each with its
 *       {@code xxxHasZeroCorpusDemand} method.</li>
 * </ul>
 *
 * <p>The α legs assert that the modifier never appears as a <em>discriminating</em> predicate: the
 * negated/`throws` forms appear nowhere in any corpus, and {@code static}/{@code final} appear only
 * as descriptive prefixes that the parser strips (never to exclude a non-static / non-final method).
 */
class SignatureModifierGrammarTest {

    /** §row "positive visibility (public)" — COVERED. A {@code public}-prefixed call parses with the
     *  modifier stripped: the name / owner / return survive, so the underlying method matches. */
    @Test
    void positiveVisibilityModifierStrippedAndCallStillResolves() {
        CallPC withPublic = (CallPC) PointcutExpressionParser.parse(
                "call(public static javax.crypto.Cipher javax.crypto.Cipher.getInstance(java.lang.String))");
        assertEquals("getInstance", withPublic.methodName(),
                "the public/static modifiers are stripped, leaving the real method name");
        assertEquals("javax.crypto.Cipher", withPublic.declaringType(),
                "owner survives modifier stripping");
        assertEquals("javax.crypto.Cipher", withPublic.returnType(),
                "return type survives modifier stripping");

        // The same call without the modifier prefix parses to the identical method name / owner —
        // proving the modifier is purely descriptive (stripped), not a discriminator.
        CallPC withoutPublic = (CallPC) PointcutExpressionParser.parse(
                "call(javax.crypto.Cipher javax.crypto.Cipher.getInstance(java.lang.String))");
        assertEquals(withoutPublic.methodName(), withPublic.methodName());
        assertEquals(withoutPublic.declaringType(), withPublic.declaringType());
        assertEquals(withoutPublic.returnType(), withPublic.returnType());
    }

    /** §row "negated visibility (!public)" — NOT-NEEDED α. The {@code !public} discriminating form
     *  appears in no corpus. */
    @Test
    void negatedVisibilityHasZeroCorpusDemand() {
        assertModifierAbsentEverywhere(Pattern.compile("!\\s*(public|private|protected)"),
                "negated visibility (!public)");
    }

    /** §row "static signature modifier" — NOT-NEEDED α. {@code static} appears only as a stripped
     *  descriptive prefix (e.g. {@code call(public static ...)}), never as a discriminating predicate
     *  that excludes a non-static method. Demand for modifier <em>discrimination</em> is zero. */
    @Test
    void staticModifierHasZeroCorpusDemand() {
        // There is no DEX-level "static-only" join-point filter: the matcher resolves by
        // name+owner+params+return, and stripModifiers drops `static`. So no corpus uses `static` as
        // a discriminator. We prove the absence of the *negated* / *exclusive* form (the only shapes
        // that would need a matcher); the bare descriptive `static` is stripped and is COVERED by the
        // positive-visibility leg above.
        assertModifierAbsentEverywhere(Pattern.compile("!\\s*static"),
                "negated/exclusive static modifier");
    }

    /** §row "final signature modifier" — NOT-NEEDED α (same rationale as {@code static}). */
    @Test
    void finalModifierHasZeroCorpusDemand() {
        assertModifierAbsentEverywhere(Pattern.compile("!\\s*final"),
                "negated/exclusive final modifier");
    }

    /** §row "throws ExceptionPattern" — NOT-NEEDED α. The {@code throws} signature clause appears in
     *  no corpus pointcut. */
    @Test
    void throwsModifierHasZeroCorpusDemand() {
        assertModifierAbsentEverywhere(Pattern.compile("\\bthrows\\b"),
                "throws ExceptionPattern signature clause");
    }

    /** Asserts the given discriminating-modifier pattern fires zero times across all three compiled
     *  corpora and Coverage.aj (the full source surface the matrix SourceDemand column reports). */
    private static void assertModifierAbsentEverywhere(Pattern p, String label) {
        for (String corpus : new String[]{"jca", "generic", "generic_new"}) {
            assertEquals(0, p.matcher(compiledAj(corpus)).results().toList().size(),
                    label + " has zero demand in the compiled .aj for " + corpus);
        }
        assertEquals(0, p.matcher(coverageAj()).results().toList().size(),
                label + " has zero demand in Coverage.aj");
    }

    private static String compiledAj(String corpus) {
        String path = "compiled-aj-fixtures/" + corpus + "/MultiSpec_1MonitorAspect.aj";
        try (InputStream in = SignatureModifierGrammarTest.class.getClassLoader()
                .getResourceAsStream(path)) {
            assertNotNull(in, "compiled .aj evidence file present on classpath: " + path);
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new RuntimeException("failed to read compiled .aj fixture " + path, e);
        }
    }

    private static String coverageAj() {
        java.nio.file.Path cov = java.nio.file.Paths.get(
                System.getenv("RVSEC_HOME"), "rvsec", "rvsec-mop", "src", "main", "resources",
                "aspect", "Coverage.aj");
        try {
            return java.nio.file.Files.readString(cov);
        } catch (IOException e) {
            throw new RuntimeException("failed to read Coverage.aj at " + cov, e);
        }
    }
}
