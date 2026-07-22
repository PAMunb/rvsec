package br.unb.cic.rv.grammar;

import br.unb.cic.rv.grammar.util.AbsorbingStage;

import com.android.tools.smali.dexlib2.iface.DexFile;

import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Backs the advice-body reflective-API matrix rows that are absorbed by {@code coverage-weaver}
 * (§4.20 remaining rows):
 * {@code thisJoinPoint binding}, {@code thisJoinPointStaticPart binding},
 * {@code thisEnclosingJoinPointStaticPart binding}, {@code JoinPoint.getArgs()},
 * {@code JoinPoint.getTarget()}, {@code JoinPoint.getKind()}.
 *
 * <p>These are members of the {@code org.aspectj.lang.JoinPoint} reflective family whose <em>sole</em>
 * consumer is {@code Coverage.aj} (the MOP advice bodies that survive into the compiled {@code .aj}
 * are pass-through {@code *RuntimeMonitor.*Event(...)} dispatches — see {@code AdviceExecutionGrammarTest}
 * / Audit A.1). {@code coverage-weaver} replaces the entire reflective path with a weave-time
 * signature string and a direct {@code Lmop/Coverage;->log(...)} call, referencing NO
 * {@code org.aspectj.lang.*} type — so the family never reaches the dexlib2 instrumenter. Verdict:
 * NOT-NEEDED β, absorber {@code COVERAGE_WEAVER} (deferred.md §2.2.1-D/F).
 *
 * <p><b>Exception — {@code JoinPoint.getSignature()} is COVERED, not absorbed</b> (round-10 AC /
 * round-11 R11.5): the staticinit advice bodies in {@code generic_new} carry three live
 * {@code thisJoinPoint.getStaticPart().getSignature()} calls that the dexlib2 weaver genuinely
 * satisfies by delivering an {@code org.aspectj.lang.ClassSignature} (shipped via {@code rvsec-core}).
 * That row's evidence is {@code StaticInitializationGrammarTest.signatureDeliveryForStaticinitEvent}.
 * This test asserts the dividing line: {@code getSignature()} survives into the pipeline (and is
 * delivered), while the rest of the family does not.
 */
class JoinPointReflectiveApiGrammarTest {

    /** The pipeline stage that absorbs the non-{@code getSignature} reflective API. */
    static final AbsorbingStage ABSORBER = AbsorbingStage.COVERAGE_WEAVER;

    /**
     * The family is absorbed by {@code coverage-weaver}: a real coverage weave injects the direct
     * {@code Lmop/Coverage;->log(...)} call and references NO {@code org.aspectj.lang.*} reflective
     * type (no {@code JoinPoint}, no {@code getArgs}/{@code getTarget}/{@code getKind}/
     * {@code thisJoinPoint*}). This single woven-DEX scan is the absorption evidence for every
     * non-{@code getSignature} reflective-API row.
     */
    @Test
    void reflectiveApiFamilyAbsorbedByCoverageWeaver() throws Exception {
        DexFile woven = CoverageWeaveFixture.weaveAppClass();

        List<String> invoked = CoverageWeaveFixture.invokedMethodRefs(woven);
        assertTrue(invoked.contains("Lmop/Coverage;->log"),
                "coverage-weaver injects the direct Lmop/Coverage;->log(...) call (no reflective JoinPoint)");

        List<String> allRefs = CoverageWeaveFixture.allReferenceStrings(woven);
        assertTrue(allRefs.stream().noneMatch(r -> r.contains("Lorg/aspectj/lang/JoinPoint")),
                "no org.aspectj.lang.JoinPoint reference may appear — the reflective family is absorbed");
        // The reflective accessor method names never appear as invoked references either.
        for (String accessor : new String[]{"->getArgs(", "->getTarget(", "->getKind(",
                "->getThis(", "->getSourceLocation("}) {
            assertTrue(allRefs.stream().noneMatch(r -> r.contains(accessor)),
                    "coverage-woven DEX must not invoke the reflective accessor " + accessor);
        }

        assertEquals(AbsorbingStage.COVERAGE_WEAVER, ABSORBER);
    }

    /**
     * The dividing line: {@code getSignature()} is the one reflective accessor that survives into the
     * pipeline (3 sites in the {@code generic_new} compiled {@code .aj} staticinit advice bodies) and
     * is COVERED by §4.Y — NOT absorbed. This guards against accidentally re-classifying the
     * {@code getSignature()} row as β: if a future change made the weaver stop delivering the
     * {@code ClassSignature}, {@code StaticInitializationGrammarTest.signatureDeliveryForStaticinitEvent}
     * (the COVERED evidence) would fail, not this test. Here we only assert the pipeline-survival fact
     * that distinguishes {@code getSignature()} from the absorbed accessors above.
     */
    @Test
    void getSignatureSurvivesPipelineAndIsCovered() {
        String genericNew = CoverageWeaveFixture.readClasspath(
                "compiled-aj-fixtures/generic_new/MultiSpec_1MonitorAspect.aj");
        long sites = genericNew.lines()
                .filter(l -> l.contains("thisJoinPoint.getStaticPart().getSignature()"))
                .count();
        assertEquals(3, sites,
                "exactly 3 staticinit advice bodies in generic_new carry getSignature() — the COVERED "
                        + "§4.Y Signature-delivery sites (Collection_HashCode, Serializable_NoArgConstructor, "
                        + "URLConnection_OverrideGetPermission)");
    }
}
