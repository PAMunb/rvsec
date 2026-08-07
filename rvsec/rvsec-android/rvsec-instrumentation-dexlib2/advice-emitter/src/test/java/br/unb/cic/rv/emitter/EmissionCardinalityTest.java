package br.unb.cic.rv.emitter;

import br.unb.cic.rv.descriptor.AdviceDescriptor;

import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.iface.instruction.ReferenceInstruction;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import org.junit.jupiter.api.Test;

import java.util.ArrayList;
import java.util.List;

import static br.unb.cic.rv.emitter.EmitterTestFixtures.adviceAfter;
import static br.unb.cic.rv.emitter.EmitterTestFixtures.adviceAfterThrowing;
import static br.unb.cic.rv.emitter.EmitterTestFixtures.adviceBefore;
import static br.unb.cic.rv.emitter.EmitterTestFixtures.adviceStaticInit;
import static br.unb.cic.rv.emitter.EmitterTestFixtures.ctx;
import static br.unb.cic.rv.emitter.EmitterTestFixtures.fused;
import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * V0 — the acceptance test for INV-INS-104: an advice carrying N monitor calls
 * emits exactly N monitor invokes, in descriptor order, on every inline
 * emission path.
 *
 * <h2>Why this test exists and why it is written as a list, not a count</h2>
 *
 * JavaMOP fuses advices whose position and pointcut coincide, so an advice with
 * N &gt; 1 monitor calls is a normal descriptor shape — the production
 * descriptor holds 115 advices of which 17 carry more than one. The wrapper
 * path iterates them; the inline path reduces the list to {@code get(0)} and
 * drops the rest, which erases 9 events from every woven APK and, with them,
 * an entire {@code ErrorType} category from the recorded corpus.
 *
 * <p>The assertions compare the emitted monitor event names <em>as an ordered
 * list</em> against the descriptor's order rather than asserting a count.
 * {@code monitorCalls} is a list and the descriptor's order is the order the
 * generated monitor expects (D-A2); a count-only assertion would let a future
 * refactor reorder the emissions silently, and a set-only assertion would do
 * the same.
 *
 * <p>Per INV-INS-108 this test is executed against the <em>unrepaired</em>
 * weaver first and its failure committed as an artefact of gh100. The defect it
 * covers survived fifteen months because the instrument that would have seen it
 * shared its premise: truncation removes additional monitor calls from a site
 * that stays woven, so method coverage is byte-identical with and without the
 * defect. A test first observed green cannot distinguish "the repair works"
 * from "the test never discriminated".
 */
class EmissionCardinalityTest {

    /**
     * The monitor event names invoked by {@code instructions}, in emission
     * order.
     *
     * <p>Reads the method reference of every {@code invoke-static} rather than
     * counting instructions, so an emission that produced the right number of
     * invokes to the wrong events still fails. Non-invoke instructions are
     * ignored: the static-initialization signature path prefixes its invoke
     * with {@code const-class} / {@code new-instance} / {@code invoke-direct},
     * and this helper is about which monitor events fire, not about the
     * materialisation around them.
     */
    private static List<String> monitorEvents(List<BuilderInstruction> instructions) {
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

    /** The event names the descriptor declares, in descriptor order. */
    private static List<String> declaredEvents(AdviceDescriptor advice) {
        List<String> events = new ArrayList<>();
        advice.getMonitorCalls().forEach(call -> {
            String method = call.getMethod();
            int dot = method.lastIndexOf('.');
            events.add(dot >= 0 ? method.substring(dot + 1) : method);
        });
        return events;
    }

    @Test
    void fusedBeforeAdviceEmitsOneInvokePerMonitorCallInDescriptorOrder() {
        AdviceDescriptor a = fused(adviceBefore("fusedBefore"), 3);

        EmitPlan plan = new BeforeEmitter().emit(ctx(a));

        assertEquals(declaredEvents(a), monitorEvents(plan.toInsert()),
                "INV-INS-104: the inline before path must emit every monitor call "
                        + "the advice carries, in descriptor order");
    }

    @Test
    void fusedAfterAdviceEmitsOneInvokePerMonitorCallInDescriptorOrder() {
        AdviceDescriptor a = fused(adviceAfter("fusedAfter"), 3);

        EmitPlan plan = new AfterEmitter().emit(ctx(a));

        assertEquals(declaredEvents(a), monitorEvents(plan.toInsert()),
                "INV-INS-104: the inline after path must emit every monitor call "
                        + "the advice carries, in descriptor order");
    }

    @Test
    void fusedStaticInitAdviceEmitsOneInvokePerMonitorCallInDescriptorOrder() {
        // The arg-less classInitEvent shape, so deliversSignature is false and
        // the emitter takes the generic invoke fallback — the path that reads
        // primaryCall(). The signature-delivery path materialises a single
        // ClassSignature and is a different question, covered by
        // StaticInitializationEmitterSignatureTest.
        AdviceDescriptor a = fused(adviceStaticInit("fusedSi", "java.util.ArrayList+"), 3);

        EmitPlan plan = new StaticInitializationEmitter().emit(ctx(a));

        assertEquals(declaredEvents(a), monitorEvents(plan.toInsert()),
                "INV-INS-104: the static-initialization inline path must emit every "
                        + "monitor call the advice carries, in descriptor order");
    }

    @Test
    void fusedAfterThrowingHandlerEmitsOneInvokePerMonitorCallInDescriptorOrder() {
        // The after-throwing handler body IS the monitor invoke sequence — the
        // executor prepends move-exception and appends throw around exactly
        // plan.toInsert(). A truncated handler therefore drops the same events
        // as the other inline paths, on the exception edge.
        AdviceDescriptor a = fused(adviceAfterThrowing("fusedAth", "Exception"), 3);

        EmitPlan plan = new AfterThrowingEmitter().emit(ctx(a));

        assertEquals(declaredEvents(a), monitorEvents(plan.toInsert()),
                "INV-INS-104: the after-throwing handler must invoke every monitor "
                        + "call the advice carries, in descriptor order");
    }

    @Test
    void unfusedAdviceStillEmitsExactlyOneInvoke() {
        // The negative control. Every assertion above fails today by emitting
        // one invoke where three are due; this one pins that the repair does not
        // achieve its counts by emitting the whole list twice, or by emitting a
        // call the descriptor never declared.
        AdviceDescriptor a = adviceBefore("plainBefore");
        assertEquals(1, a.getMonitorCalls().size(), "fixture must stay unfused");

        EmitPlan plan = new BeforeEmitter().emit(ctx(a));

        assertEquals(List.of("hasNextEvent"), monitorEvents(plan.toInsert()),
                "an advice with one monitor call emits exactly one invoke");
    }
}
