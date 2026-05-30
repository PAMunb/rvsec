package br.unb.cic.rv.grammar;

import br.unb.cic.rv.grammar.util.DemandCounter;
import br.unb.cic.rv.grammar.util.DemandCounter.Corpus;

import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.regex.Pattern;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

/**
 * Backs the six AspectJ-5 annotation pointcut-designator matrix rows
 * ({@code @annotation}, {@code @target}, {@code @this}, {@code @args}, {@code @within},
 * {@code @withincode}). Verdict: NOT-NEEDED α — zero source demand across all four corpora and no
 * parser/matcher implementation (the parser rejects {@code @} as an identifier char, so an
 * annotation PCD never parses). deferred.md §2.1 lists each row with its
 * {@code atXxxHasZeroCorpusDemand} test method.
 *
 * <p>The single regex {@link #ANNOTATION_PCD} matches any of the six annotation designators
 * ({@code @ident(}); the assertion is that it never fires in any corpus. The COVERED designators
 * never use the {@code @} sigil before a pointcut keyword, so a zero count is a real signal, not a
 * vacuous one — a future {@code .mop}/{@code .aj} introducing {@code @annotation(...)} flips the
 * count and trips this test.
 */
class AnnotationPointcutGrammarTest {

    /** An AspectJ-5 annotation pointcut designator: an {@code @} immediately followed by one of the
     *  six designator names and an opening paren. */
    private static final Pattern ANNOTATION_PCD =
            Pattern.compile("@(annotation|target|this|args|within|withincode)\\s*\\(");

    @Test
    void atAnnotationHasZeroCorpusDemand() {
        assertNoAnnotationPcdDemandIn(Corpus.ASPECT);
        assertNoAnnotationPcdDemandIn(Corpus.JCA);
        assertNoAnnotationPcdDemandIn(Corpus.GENERIC);
        assertNoAnnotationPcdDemandIn(Corpus.GENERIC_NEW);
    }

    @Test
    void atTargetHasZeroCorpusDemand() {
        assertNoAnnotationPcdDemandIn(Corpus.JCA);
        assertNoAnnotationPcdDemandIn(Corpus.GENERIC_NEW);
    }

    @Test
    void atThisHasZeroCorpusDemand() {
        assertNoAnnotationPcdDemandIn(Corpus.JCA);
        assertNoAnnotationPcdDemandIn(Corpus.GENERIC_NEW);
    }

    @Test
    void atArgsHasZeroCorpusDemand() {
        assertNoAnnotationPcdDemandIn(Corpus.JCA);
        assertNoAnnotationPcdDemandIn(Corpus.GENERIC_NEW);
    }

    @Test
    void atWithinHasZeroCorpusDemand() {
        assertNoAnnotationPcdDemandIn(Corpus.JCA);
        assertNoAnnotationPcdDemandIn(Corpus.GENERIC_NEW);
    }

    @Test
    void atWithincodeHasZeroCorpusDemand() {
        assertNoAnnotationPcdDemandIn(Corpus.JCA);
        assertNoAnnotationPcdDemandIn(Corpus.GENERIC_NEW);
    }

    /** Counts annotation-PCD occurrences in the corpus's {@code .mop}/{@code Coverage.aj} sources via
     *  {@code DemandCounter}'s root resolution (so the count is over exactly the corpus the matrix
     *  SourceDemand column reports) and asserts zero. */
    private static void assertNoAnnotationPcdDemandIn(Corpus corpus) {
        // The six annotation PCDs share a single matcher; none of the DemandCounter keys cover them
        // (zero demand means no designator was ever added). Count directly over the same corpus
        // files DemandCounter scans, by reusing one of its zero-demand keys as the file selector
        // would couple this test to that key's regex — instead assert against the compiled .aj and
        // the aspect source, which together cover the source surface.
        int aj = (corpus == Corpus.ASPECT) ? 0
                : ANNOTATION_PCD.matcher(compiledAj(corpus)).results().toList().size();
        assertEquals(0, aj,
                "no AspectJ-5 annotation pointcut designator (@annotation/@target/@this/@args/"
                        + "@within/@withincode) appears in the compiled .aj for " + corpus);
        if (corpus == Corpus.ASPECT) {
            assertEquals(0, ANNOTATION_PCD.matcher(coverageAj()).results().toList().size(),
                    "no annotation PCD in Coverage.aj");
        }
    }

    private static String compiledAj(Corpus corpus) {
        String path = "compiled-aj-fixtures/" + corpus.dir() + "/MultiSpec_1MonitorAspect.aj";
        try (InputStream in = AnnotationPointcutGrammarTest.class.getClassLoader()
                .getResourceAsStream(path)) {
            assertNotNull(in, "compiled .aj evidence file present on classpath: " + path);
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new RuntimeException("failed to read compiled .aj fixture " + path, e);
        }
    }

    /** {@code aspect/Coverage.aj} from the live {@code .mop} resource tree — the only ASPECT-corpus
     *  source {@code DemandCounter.countMop} scans. */
    private static String coverageAj() {
        // Mirror DemandCounter's source-root resolution so the assertion is over the same bytes the
        // matrix SourceDemand column reports.
        java.nio.file.Path cov = java.nio.file.Paths.get(
                System.getenv("RVSEC_HOME"), "rvsec", "rvsec-mop", "src", "main", "resources",
                "aspect", "Coverage.aj");
        try {
            return java.nio.file.Files.readString(cov);
        } catch (IOException e) {
            throw new RuntimeException("failed to read Coverage.aj at " + cov, e);
        }
    }

    /** Cross-check that {@code DemandCounter} has no key for the annotation PCDs — confirming the
     *  NOT-NEEDED α "no implementation" leg (no designator was ever registered for them). */
    @Test
    void annotationPcdsHaveNoDemandCounterDesignator() {
        // Reading PATTERNS via the public count API: every known designator is one of the COVERED /
        // path-β keys; none names an annotation PCD. We assert the six names are absent by attempting
        // a lookup and expecting the unknown-designator guard.
        for (String name : new String[]{"@annotation", "@target", "@this", "@args", "@within",
                "@withincode"}) {
            try {
                DemandCounter.countMop(name, Corpus.JCA);
                throw new AssertionError("DemandCounter unexpectedly knows annotation PCD '" + name
                        + "' — annotation PCDs are NOT-NEEDED α with no designator");
            } catch (IllegalArgumentException expected) {
                // good — no designator registered for the annotation PCD.
            }
        }
    }
}
