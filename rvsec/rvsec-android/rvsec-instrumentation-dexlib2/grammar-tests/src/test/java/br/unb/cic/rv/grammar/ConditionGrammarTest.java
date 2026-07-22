package br.unb.cic.rv.grammar;

import br.unb.cic.rv.grammar.util.AbsorbingStage;
import br.unb.cic.rv.grammar.util.DemandCounter;
import br.unb.cic.rv.grammar.util.DemandCounter.Corpus;

import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.regex.Pattern;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Backs the matrix row "{@code condition(...)}" (§4.G'). NOT-NEEDED β: the JavaMOP MOP-extension
 * {@code condition(...)} carries non-zero SourceDemand (64 jca + 10 generic_new sites) but zero
 * PipelineDemand — the JavaMOP compiler folds the predicate into the emitted
 * {@code *RuntimeMonitor.*Event(...)} dispatch before the {@code .aj} is produced. Absorber:
 * {@code JAVA_MOP_COMPILER}.
 */
class ConditionGrammarTest {

    /** The pipeline stage that absorbs {@code condition(...)} before dexlib2 sees it. */
    static final AbsorbingStage ABSORBER = AbsorbingStage.JAVA_MOP_COMPILER;

    /** A {@code MultiSpec_1RuntimeMonitor.<spec>Event(...)} dispatch invocation — the form the
     *  compiler moves the condition logic into. */
    private static final Pattern RUNTIME_MONITOR_EVENT =
            Pattern.compile("RuntimeMonitor\\.[A-Za-z0-9_]+Event\\s*\\(");

    @Test
    void conditionAbsorbedByRuntimeMonitor() {
        // (a) SourceDemand non-zero in jca and generic_new.
        assertTrue(DemandCounter.countMop(DemandCounter.CONDITION, Corpus.JCA) >= 1,
                "condition(...) has source demand in jca .mop specs (64 sites)");
        assertTrue(DemandCounter.countMop(DemandCounter.CONDITION, Corpus.GENERIC_NEW) >= 1,
                "condition(...) has source demand in generic_new .mop specs (10 sites)");

        // (b) PipelineDemand zero — the compiled .aj has no condition( references.
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.CONDITION, Corpus.JCA),
                "condition(...) absorbed by the JavaMOP compiler — zero pipeline demand (jca)");
        assertEquals(0, DemandCounter.countCompiledAj(DemandCounter.CONDITION, Corpus.GENERIC_NEW),
                "condition(...) absorbed by the JavaMOP compiler — zero pipeline demand (generic_new)");

        // (c) Absorber JAVA_MOP_COMPILER — verified: the compiled jca .aj carries the
        // *RuntimeMonitor.*Event(...) dispatch invocations the condition logic moved into.
        assertEquals(AbsorbingStage.JAVA_MOP_COMPILER, ABSORBER);
        assertTrue(RUNTIME_MONITOR_EVENT.matcher(compiledJca()).find(),
                "compiled jca .aj must carry *RuntimeMonitor.*Event(...) dispatch (the moved "
                        + "condition logic — JavaMOP compiler absorption)");
    }

    private static String compiledJca() {
        try (InputStream in = ConditionGrammarTest.class.getClassLoader()
                .getResourceAsStream("compiled-aj-fixtures/jca/MultiSpec_1MonitorAspect.aj")) {
            assertNotNull(in, "jca compiled .aj evidence file present on classpath");
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        } catch (IOException e) {
            throw new RuntimeException("failed to read jca compiled .aj fixture", e);
        }
    }
}
