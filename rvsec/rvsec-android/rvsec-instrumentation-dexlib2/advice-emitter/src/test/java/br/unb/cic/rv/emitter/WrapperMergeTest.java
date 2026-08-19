package br.unb.cic.rv.emitter;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.AspectDescriptor;
import br.unb.cic.rv.descriptor.MonitorCallDescriptor;
import br.unb.cic.rv.descriptor.ParameterDescriptor;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Two specifications advising the same API call get one wrapper that fires
 * both, not two wrappers of which one is discarded (gh100 task 5.3, D-B1).
 *
 * <h2>Why merging rather than a wider key</h2>
 *
 * The {@code dex-mutator}'s wrapper registry is keyed on the original call
 * site's own {@code MethodReference}, because at a call site that is the only
 * identity available. The key therefore cannot be widened to distinguish two
 * advices — any extra component would be something the lookup cannot supply.
 * Emitting one wrapper per advice bound several wrappers to one key and the
 * last write won: the earlier advice's monitor events never fired at that site,
 * and the site was attributed to whichever specification registered last.
 *
 * <p>On the production descriptor that was not hypothetical — 96 wrappers over
 * 84 distinct keys, 10 keys bound more than once, 12 wrappers discarded, with
 * {@code SecureRandom.getInstance(String)} alone bound three times.
 */
class WrapperMergeTest {

    /**
     * An after-returning advice over {@code SecureRandom.getInstance(String)},
     * the shape that collided three ways in the production descriptor.
     */
    private static AdviceDescriptor adviceOver(String specName, String event) {
        AdviceDescriptor a = new AdviceDescriptor();
        a.setName(specName + "_g1");
        a.setSpecName(specName);
        a.setPosition("after");
        a.setAround(false);
        a.setParameters(List.of(new ParameterDescriptor("String", "algorithm")));
        a.setReturning(List.of(new ParameterDescriptor("java.security.SecureRandom", "r")));
        a.setExpression("call(public static java.security.SecureRandom "
                + "java.security.SecureRandom.getInstance(java.lang.String)) && args(algorithm)");
        MonitorCallDescriptor mc = new MonitorCallDescriptor();
        mc.setMethod("MultiSpec_1RuntimeMonitor." + event);
        mc.setSpecName(specName);
        mc.setEventId(event);
        mc.setUniqueId(event);
        mc.setArgs(List.of("algorithm", "r"));
        a.setMonitorCalls(List.of(mc));
        return a;
    }

    private static String generate(Path outputDir, AdviceDescriptor... advices)
            throws IOException {
        AspectDescriptor descriptor = new AspectDescriptor();
        descriptor.setAspectName("MultiSpec_1MonitorAspect");
        descriptor.setAdvices(List.of(advices));
        WrapperEmitter.generate(descriptor, outputDir).wrappers();
        return Files.readString(outputDir.resolve(WrapperEmitter.WRAPPER_PACKAGE)
                .resolve(WrapperEmitter.WRAPPER_CLASS_NAME + ".java"));
    }

    @Test
    void twoAdvicesOverTheSameCallShareOneWrapperThatFiresBoth(@TempDir Path outputDir)
            throws IOException {
        AspectDescriptor descriptor = new AspectDescriptor();
        descriptor.setAspectName("MultiSpec_1MonitorAspect");
        descriptor.setAdvices(List.of(
                adviceOver("SecureRandomSpec", "SecureRandomSpec_g1Event"),
                adviceOver("RandomStringPassword", "RandomStringPassword_g1Event")));

        List<WrapperEmitter.WrapperEntry> entries =
                WrapperEmitter.generate(descriptor, outputDir).wrappers();
        String source = Files.readString(outputDir.resolve(WrapperEmitter.WRAPPER_PACKAGE)
                .resolve(WrapperEmitter.WRAPPER_CLASS_NAME + ".java"));

        assertEquals(1, entries.size(),
                "one original call must produce exactly one wrapper entry, or the "
                        + "registry has two wrappers for one key and must discard one");
        assertTrue(source.contains("MultiSpec_1RuntimeMonitor.SecureRandomSpec_g1Event("),
                "the first advice's monitor call must fire:\n" + source);
        assertTrue(source.contains("MultiSpec_1RuntimeMonitor.RandomStringPassword_g1Event("),
                "the second advice's monitor call must fire too — it is the one the "
                        + "overwriting registry used to lose:\n" + source);
    }

    @Test
    void adviceOrderIsPreservedInTheMergedWrapper(@TempDir Path outputDir) throws IOException {
        String source = generate(outputDir,
                adviceOver("SecureRandomSpec", "firstEvent"),
                adviceOver("RandomStringPassword", "secondEvent"));

        int first = source.indexOf("MultiSpec_1RuntimeMonitor.firstEvent(");
        int second = source.indexOf("MultiSpec_1RuntimeMonitor.secondEvent(");
        assertTrue(first >= 0 && second >= 0, "both events must be present:\n" + source);
        assertTrue(first < second,
                "merged wrappers fire in descriptor order; reordering them would change "
                        + "the event sequence the monitors' state machines see");
    }

    @Test
    void aSingleAdviceStillProducesItsOwnWrapper(@TempDir Path outputDir) throws IOException {
        // The control: merging must not collapse distinct calls, only distinct
        // advices over the SAME call.
        AspectDescriptor descriptor = new AspectDescriptor();
        descriptor.setAspectName("MultiSpec_1MonitorAspect");
        AdviceDescriptor other = adviceOver("MessageDigestSpec", "MessageDigestSpec_g1Event");
        other.setExpression("call(public static java.security.MessageDigest "
                + "java.security.MessageDigest.getInstance(java.lang.String)) && args(algorithm)");
        descriptor.setAdvices(List.of(
                adviceOver("SecureRandomSpec", "SecureRandomSpec_g1Event"), other));

        List<WrapperEmitter.WrapperEntry> entries =
                WrapperEmitter.generate(descriptor, outputDir).wrappers();

        assertEquals(2, entries.size(),
                "two different original calls must keep two wrappers");
    }

    // --- args() arity, counter mode (gh104 E2, INV-INS-122) ------------------
    //
    // The three cases below pin a measurement, never a filter. Each asserts BOTH
    // the counter and the emission: the wrapper must keep firing every monitor
    // call it fires today, and the counter must merely say how many advice/
    // overload pairs a filter WOULD have excluded. If an emission assertion here
    // ever goes red the counter has started filtering, which is the one outcome
    // this group exists to prevent.

    /**
     * One after-returning advice over a {@code TrustManagerFactory.getInstance}
     * overload whose parameter list is spelled by {@code callParamTypes}. The
     * {@code argsClause} is appended verbatim ({@code null} = no {@code args()}
     * clause at all, which is clause 1 of the rule: no positional constraint).
     */
    private static AdviceDescriptor tmfAdvice(String event, String argsClause,
                                              List<String> callParamTypes,
                                              List<ParameterDescriptor> adviceParams) {
        AdviceDescriptor a = new AdviceDescriptor();
        a.setName("TrustManagerFactorySpec_" + event);
        a.setSpecName("TrustManagerFactorySpec");
        a.setPosition("after");
        a.setAround(false);
        a.setParameters(adviceParams);
        a.setReturning(List.of(
                new ParameterDescriptor("javax.net.ssl.TrustManagerFactory", "tmf")));
        a.setExpression("call(public static javax.net.ssl.TrustManagerFactory "
                + "javax.net.ssl.TrustManagerFactory.getInstance("
                + String.join(", ", callParamTypes) + "))"
                + (argsClause == null ? "" : " && " + argsClause));
        MonitorCallDescriptor mc = new MonitorCallDescriptor();
        mc.setMethod("MultiSpec_1RuntimeMonitor.TrustManagerFactorySpec_" + event + "Event");
        mc.setSpecName("TrustManagerFactorySpec");
        mc.setEventId(event);
        mc.setUniqueId(event);
        mc.setArgs(List.of("alg"));
        a.setMonitorCalls(List.of(mc));
        return a;
    }

    private static final List<ParameterDescriptor> ALG_ONLY =
            List.of(new ParameterDescriptor("String", "alg"));

    private static WrapperEmitter.EmitResult emit(Path outputDir, AdviceDescriptor... advices)
            throws IOException {
        AspectDescriptor descriptor = new AspectDescriptor();
        descriptor.setAspectName("MultiSpec_1MonitorAspect");
        descriptor.setAdvices(List.of(advices));
        return WrapperEmitter.generate(descriptor, outputDir);
    }

    private static String wrapperSource(Path outputDir) throws IOException {
        return Files.readString(outputDir.resolve(WrapperEmitter.WRAPPER_PACKAGE)
                .resolve(WrapperEmitter.WRAPPER_CLASS_NAME + ".java"));
    }

    /**
     * The positive case of the frozen {@code jca} descriptor, isolated: the
     * {@code TrustManagerFactory} group alone. {@code g1} and {@code g3} carry
     * {@code args(alg)} (arity 1), {@code g2} carries {@code args(alg, *)}
     * (arity 2), and all three are grouped on the one-parameter
     * {@code getInstance(String)} overload. Exactly one advice/overload pair is
     * arity-incompatible, and all three monitor calls must still fire.
     */
    @Test
    void anArityIncompatibleAdviceIsCountedAndStillFires(@TempDir Path outputDir)
            throws IOException {
        WrapperEmitter.EmitResult result = emit(outputDir,
                tmfAdvice("g1", "args(alg)", List.of("java.lang.String"), ALG_ONLY),
                tmfAdvice("g2", "args(alg, *)", List.of("java.lang.String"), ALG_ONLY),
                tmfAdvice("g3", "args(alg)", List.of("java.lang.String"), ALG_ONLY));
        String source = wrapperSource(outputDir);

        assertEquals(1, result.advicesExcludedByArity(),
                "g2 declares args(alg, *) — arity 2 — against a one-parameter "
                        + "overload; the unit of the count is advice/overload pairs, "
                        + "so exactly one pair is incompatible");
        assertEquals(1, result.wrappers().size(),
                "one original call still produces exactly one merged wrapper");
        assertTrue(source.contains("MultiSpec_1RuntimeMonitor.TrustManagerFactorySpec_g1Event("),
                "g1 must still fire:\n" + source);
        assertTrue(source.contains("MultiSpec_1RuntimeMonitor.TrustManagerFactorySpec_g2Event("),
                "g2 must STILL fire — it is counted, not excluded; this is the whole "
                        + "difference between the counter and a filter:\n" + source);
        assertTrue(source.contains("MultiSpec_1RuntimeMonitor.TrustManagerFactorySpec_g3Event("),
                "g3 must still fire:\n" + source);
    }

    /**
     * Clause 1: the absence of an {@code args()} clause means "no positional
     * constraint". It is never counted, and in particular it is never treated as
     * arity 0 — which is what the rule the lineage first wrote would have done,
     * silencing the 25 parameter-carrying {@code after} advices of the frozen
     * descriptor that declare no {@code args()}.
     */
    @Test
    void anAdviceWithNoArgsClauseIsNeverCounted(@TempDir Path outputDir) throws IOException {
        WrapperEmitter.EmitResult onOneParam = emit(outputDir,
                tmfAdvice("gtm1", null, List.of("java.lang.String"), ALG_ONLY));
        assertEquals(0, onOneParam.advicesExcludedByArity(),
                "no args() clause means no positional constraint, whatever the "
                        + "overload's parameter count");
        assertTrue(wrapperSource(outputDir)
                        .contains("MultiSpec_1RuntimeMonitor.TrustManagerFactorySpec_gtm1Event("),
                "the advice must still fire");

        Path threeParamDir = outputDir.resolve("three-params");
        WrapperEmitter.EmitResult onThreeParams = emit(threeParamDir,
                tmfAdvice("gtm1", null,
                        List.of("java.lang.String", "java.lang.String", "java.lang.String"),
                        ALG_ONLY));
        assertEquals(0, onThreeParams.advicesExcludedByArity(),
                "still zero on a three-parameter overload — clause 1 does not compare "
                        + "the advice's own parameter list against the call");
    }

    /**
     * Clause 2: the arity is the length of {@code ArgsPC.types()}, where a
     * trailing {@code ..} means "at least this many".
     * {@code ArgsPC.names()} drops the {@code ..} and would make
     * {@code args(alg, ..)} look like a fixed arity of 1, counting every
     * overload with two or more parameters.
     */
    @Test
    void aTrailingRestIsHonouredAsAtLeast(@TempDir Path outputDir) throws IOException {
        for (int arity = 1; arity <= 3; arity++) {
            Path dir = outputDir.resolve("at-least-" + arity);
            WrapperEmitter.EmitResult result = emit(dir,
                    tmfAdvice("g1", "args(alg, ..)",
                            Collections.nCopies(arity, "java.lang.String"), ALG_ONLY));
            assertEquals(0, result.advicesExcludedByArity(),
                    "args(alg, ..) is compatible with any overload of at least one "
                            + "parameter; failed at " + arity);
        }

        Path fixedDir = outputDir.resolve("fixed-head");
        WrapperEmitter.EmitResult fixed = emit(fixedDir,
                tmfAdvice("g2", "args(alg, prov, ..)", List.of("java.lang.String"),
                        List.of(new ParameterDescriptor("String", "alg"),
                                new ParameterDescriptor("String", "prov"))));
        assertEquals(1, fixed.advicesExcludedByArity(),
                "args(alg, prov, ..) needs at least two parameters and the overload "
                        + "has one — the head count is what the trailing .. leaves fixed");
        assertTrue(wrapperSource(fixedDir)
                        .contains("MultiSpec_1RuntimeMonitor.TrustManagerFactorySpec_g2Event("),
                "counted, and still emitted");
    }
}
