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
        WrapperEmitter.generate(descriptor, outputDir);
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
                WrapperEmitter.generate(descriptor, outputDir);
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
                WrapperEmitter.generate(descriptor, outputDir);

        assertEquals(2, entries.size(),
                "two different original calls must keep two wrappers");
    }
}
