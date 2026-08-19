package br.unb.cic.rv.emitter;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.AspectDescriptor;

import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.iface.instruction.ReferenceInstruction;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static br.unb.cic.rv.emitter.EmitterTestFixtures.ctx;
import static br.unb.cic.rv.emitter.EmitterTestFixtures.fused;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * The two emission paths must agree on which monitor calls they fire, and in
 * what order (gh100 task 5.2, INV-INS-104).
 *
 * <h2>Why a parity test rather than two independent assertions</h2>
 *
 * The weaver has an inline path and a wrapper path, and for fifteen months they
 * disagreed: {@code WrapperEmitter} iterated {@code monitorCalls} while the
 * inline path read {@code get(0)}. Nothing compared them, so the disagreement
 * was invisible — each path had tests, and each path passed its own.
 *
 * <p>This test compares them. The wrapper path is the reference, because it was
 * the one that was right, and because it is the path the production descriptor
 * actually takes for non-constructor after-advice. If a future refactor
 * reorders or drops an emission on either side, the two stop agreeing here even
 * if both still satisfy their own cardinality assertions.
 *
 * <p>The comparison is at the level of monitor event names in emission order.
 * The paths cannot be compared byte for byte — one produces DEX instructions,
 * the other Java source that javac and d8 turn into instructions later — and
 * the event sequence is the property the monitor's state machine depends on.
 */
class EmissionParityTest {

    /** {@code MultiSpec_1RuntimeMonitor.someEvent(} in the generated wrapper source. */
    private static final Pattern WRAPPER_CALL =
            Pattern.compile("^\\s*MultiSpec_1RuntimeMonitor\\.(\\w+)\\(", Pattern.MULTILINE);

    /** Monitor event names invoked by an inline plan, in emission order. */
    private static List<String> inlineEvents(List<BuilderInstruction> instructions) {
        List<String> events = new ArrayList<>();
        for (BuilderInstruction insn : instructions) {
            if (!(insn instanceof ReferenceInstruction ref)) continue;
            if (!(ref.getReference() instanceof MethodReference method)) continue;
            switch (insn.getOpcode()) {
                case INVOKE_STATIC, INVOKE_STATIC_RANGE -> events.add(method.getName());
                default -> { }
            }
        }
        return events;
    }

    /** Monitor event names invoked by the generated wrapper source, in source order. */
    private static List<String> wrapperEvents(String source) {
        List<String> events = new ArrayList<>();
        Matcher m = WRAPPER_CALL.matcher(source);
        while (m.find()) events.add(m.group(1));
        return events;
    }

    /**
     * An after-advice over a static factory, the shape the wrapper path takes.
     *
     * <p>{@code WrapperEmitter.shouldWrap} is {@code "after".equals(position)},
     * and the target must not be a constructor — constructors carry the
     * explicit {@code continue} that drops them to the inline path, which is
     * how the production descriptor's fused advices reach the truncating code
     * in the first place.
     */
    private static AdviceDescriptor wrappableAfterAdvice(String name) {
        AdviceDescriptor a = EmitterTestFixtures.adviceAfterReturning(name);
        a.setExpression("call(public static java.util.Collection java.util.Collections"
                + ".unmodifiableCollection(java.util.Collection))");
        return a;
    }

    private static String generateWrapperSource(AdviceDescriptor advice, Path outputDir)
            throws IOException {
        AspectDescriptor descriptor = new AspectDescriptor();
        descriptor.setAspectName("MultiSpec_1MonitorAspect");
        descriptor.setAdvices(List.of(advice));
        WrapperEmitter.generate(descriptor, outputDir).wrappers();
        return Files.readString(outputDir.resolve(WrapperEmitter.WRAPPER_PACKAGE)
                .resolve(WrapperEmitter.WRAPPER_CLASS_NAME + ".java"));
    }

    @Test
    void inlineAndWrapperPathsEmitTheSameFusedCallsInTheSameOrder(@TempDir Path outputDir)
            throws IOException {
        AdviceDescriptor advice = fused(wrappableAfterAdvice("fusedParity"), 3);
        List<String> declared = List.of("iteratorReturned",
                "iteratorReturned_fused2", "iteratorReturned_fused3");

        String wrapperSource = generateWrapperSource(advice, outputDir);
        assertTrue(wrapperSource.contains("MultiSpec_1RuntimeMonitor."),
                "the fixture must actually take the wrapper path, or this test compares "
                        + "the inline path against nothing");
        List<String> viaWrapper = wrapperEvents(wrapperSource);

        List<String> viaInline = inlineEvents(new AfterEmitter().emit(ctx(advice)).toInsert());

        assertEquals(declared, viaWrapper, "the wrapper path is the reference and must "
                + "emit every monitor call in descriptor order");
        assertEquals(viaWrapper, viaInline,
                "INV-INS-104: the inline and wrapper paths must emit the same monitor "
                        + "calls, in the same order, for the same advice");
    }

    @Test
    void thePathsAlsoAgreeOnAnUnfusedAdvice(@TempDir Path outputDir) throws IOException {
        // The control. Parity that held only for N=1 is what the tree had
        // before gh100, and it held while the paths disagreed for every N > 1.
        AdviceDescriptor advice = wrappableAfterAdvice("plainParity");

        List<String> viaWrapper = wrapperEvents(generateWrapperSource(advice, outputDir));
        List<String> viaInline = inlineEvents(new AfterEmitter().emit(ctx(advice)).toInsert());

        assertEquals(List.of("iteratorReturned"), viaWrapper);
        assertEquals(viaWrapper, viaInline);
    }
}
