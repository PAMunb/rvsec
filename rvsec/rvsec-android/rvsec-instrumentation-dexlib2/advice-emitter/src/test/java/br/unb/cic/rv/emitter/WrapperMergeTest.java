package br.unb.cic.rv.emitter;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.AspectDescriptor;
import br.unb.cic.rv.descriptor.MonitorCallDescriptor;
import br.unb.cic.rv.descriptor.ParameterDescriptor;
import br.unb.cic.rv.pointcut.AndroidClassIndex;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Collections;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
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

    // --- args() arity (INV-INS-159) ------------------------------------------
    //
    // An advice whose positional args() arity a concrete overload cannot satisfy
    // is left out of that overload's wrapper, and each excluded advice/overload
    // pair is counted in advicesExcludedByArity. An advice with no args() clause
    // is never constrained.

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
        return emit(outputDir, (AndroidClassIndex) null, advices);
    }

    private static WrapperEmitter.EmitResult emit(Path outputDir, AndroidClassIndex index,
                                                  AdviceDescriptor... advices)
            throws IOException {
        AspectDescriptor descriptor = new AspectDescriptor();
        descriptor.setAspectName("MultiSpec_1MonitorAspect");
        descriptor.setAdvices(List.of(advices));
        return WrapperEmitter.generate(descriptor, outputDir, index);
    }

    /** The wrapper method whose parameter list is exactly {@code paramList}. */
    private static String wrapperMethod(String source, String paramList) {
        int start = source.indexOf(paramList + " throws Exception {");
        assertTrue(start >= 0, "no wrapper with parameters " + paramList + ":\n" + source);
        return source.substring(start, source.indexOf("\n    }\n", start));
    }

    private static String wrapperSource(Path outputDir) throws IOException {
        return Files.readString(outputDir.resolve(WrapperEmitter.WRAPPER_PACKAGE)
                .resolve(WrapperEmitter.WRAPPER_CLASS_NAME + ".java"));
    }

    /**
     * The {@code TrustManagerFactory} group of the specification set: {@code g1}
     * binds {@code args(alg)} (arity 1) and {@code g2} binds {@code args(alg, *)}
     * (arity 2), both over {@code getInstance(String, ..)}, which the index
     * expands to the one- and the two-parameter overload. Each wrapper fires only
     * the advice its arity admits, and each overload excludes one pair.
     */
    @Test
    void anArityIncompatibleAdviceIsExcluded(@TempDir Path outputDir) throws IOException {
        AndroidClassIndex index = new AndroidClassIndex(EmitterTestFixtures.writeClassJar(
                outputDir.resolve("android-fixture.jar"),
                Map.of("javax/net/ssl/TrustManagerFactory", List.of(
                        "static getInstance (Ljava/lang/String;)Ljavax/net/ssl/TrustManagerFactory;",
                        "static getInstance (Ljava/lang/String;Ljava/lang/String;)"
                                + "Ljavax/net/ssl/TrustManagerFactory;"))));
        List<String> stringRest = List.of("java.lang.String", "..");
        WrapperEmitter.EmitResult result = emit(outputDir, index,
                tmfAdvice("g1", "args(alg)", stringRest, ALG_ONLY),
                tmfAdvice("g2", "args(alg, *)", stringRest, ALG_ONLY));
        String source = wrapperSource(outputDir);

        assertEquals(2, result.wrappers().size(), "one wrapper per overload");
        String oneParam = wrapperMethod(source, "(java.lang.String p0)");
        String twoParams = wrapperMethod(source, "(java.lang.String p0, java.lang.String p1)");
        assertTrue(oneParam.contains("TrustManagerFactorySpec_g1Event("),
                "getInstance(String) fires g1:\n" + source);
        assertFalse(oneParam.contains("TrustManagerFactorySpec_g2Event("),
                "getInstance(String) must not fire g2, whose args(alg, *) needs two "
                        + "parameters:\n" + source);
        assertTrue(twoParams.contains("TrustManagerFactorySpec_g2Event("),
                "getInstance(String, String) fires g2:\n" + source);
        assertFalse(twoParams.contains("TrustManagerFactorySpec_g1Event("),
                "getInstance(String, String) must not fire g1, whose args(alg) needs "
                        + "exactly one parameter:\n" + source);
        assertEquals(2, result.advicesExcludedByArity(),
                "one excluded advice/overload pair per overload");
    }

    /**
     * An {@code after} advice that declares parameters but no {@code args()}
     * clause binds them by position; it stays in the group of an overload whose
     * parameter count differs from its own parameter list.
     */
    @Test
    void anAdviceWithoutArgsIsUntouched(@TempDir Path outputDir) throws IOException {
        AndroidClassIndex index = new AndroidClassIndex(EmitterTestFixtures.writeClassJar(
                outputDir.resolve("android-fixture.jar"),
                Map.of("javax/net/ssl/SSLContext", List.of(
                        "init ([Ljavax/net/ssl/KeyManager;[Ljavax/net/ssl/TrustManager;"
                                + "Ljava/security/SecureRandom;)V"))));
        AdviceDescriptor init = new AdviceDescriptor();
        init.setName("SSLContextSpec_init");
        init.setSpecName("SSLContextSpec");
        init.setPosition("after");
        init.setAround(false);
        init.setParameters(List.of(
                new ParameterDescriptor("KeyManager[]", "km"),
                new ParameterDescriptor("TrustManager[]", "tm"),
                new ParameterDescriptor("SecureRandom", "sr"),
                new ParameterDescriptor("SSLContext", "ctx")));
        init.setExpression("call(public void javax.net.ssl.SSLContext.init(..)) && target(ctx)");
        MonitorCallDescriptor mc = new MonitorCallDescriptor();
        mc.setMethod("MultiSpec_1RuntimeMonitor.SSLContextSpec_initEvent");
        mc.setSpecName("SSLContextSpec");
        mc.setEventId("init");
        mc.setUniqueId("init");
        mc.setArgs(List.of("km", "tm", "sr", "ctx"));
        init.setMonitorCalls(List.of(mc));

        WrapperEmitter.EmitResult result = emit(outputDir, index, init);

        assertEquals(1, result.wrappers().size());
        assertTrue(wrapperSource(outputDir).contains(
                        "MultiSpec_1RuntimeMonitor.SSLContextSpec_initEvent(p0, p1, p2, recv);"),
                "the advice stays in the group and its monitor call is emitted:\n"
                        + wrapperSource(outputDir));
        assertEquals(0, result.advicesExcludedByArity(),
                "an advice without args() contributes nothing to the counter");
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
        assertTrue(fixed.wrappers().isEmpty(),
                "the only overload excluded the only advice, so no wrapper is emitted");
        assertFalse(wrapperSource(fixedDir)
                        .contains("MultiSpec_1RuntimeMonitor.TrustManagerFactorySpec_g2Event("),
                "an excluded advice fires no monitor call");
    }
}
