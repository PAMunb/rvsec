package br.unb.cic.rv.grammar;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.MonitorCallDescriptor;
import br.unb.cic.rv.descriptor.ParameterDescriptor;
import br.unb.cic.rv.emitter.AfterEmitter;
import br.unb.cic.rv.emitter.AfterReturningEmitter;
import br.unb.cic.rv.emitter.BeforeEmitter;
import br.unb.cic.rv.emitter.EmitContext;
import br.unb.cic.rv.emitter.EmitPlan;
import br.unb.cic.rv.emitter.InsertionPoint;
import br.unb.cic.rv.pointcut.Match;
import br.unb.cic.rv.pointcut.TypeResolver;

import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.iface.instruction.formats.Instruction35c;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;

import org.junit.jupiter.api.Test;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Backs the advice-form matrix rows that the dexlib2 weaver emits inline:
 * <ul>
 *   <li><b>{@code before() advice}</b> — COVERED: {@link BeforeEmitter} emits the monitor invoke at
 *       the {@code BEFORE} insertion point (18 jca + 43 generic_new pipeline sites).</li>
 *   <li><b>{@code after() advice}</b> — COVERED: {@link AfterEmitter} emits at the {@code AFTER}
 *       insertion point (97 jca + 14 generic_new sites).</li>
 *   <li><b>{@code after() returning(Id)} advice</b> — COVERED: {@link AfterReturningEmitter} emits at
 *       {@code AFTER} via the wrapper-substitution path, no inline scratch (64 jca + 8 generic_new).</li>
 * </ul>
 *
 * <p>Each test asserts the real {@link EmitPlan} carries a {@code *RuntimeMonitor.*Event(...)} invoke
 * at the expected insertion point — the load-bearing behaviour, not a stand-in.
 * ({@code after() throwing(Id)} is COVERED separately by {@code AfterThrowingGrammarTest} (§4.T);
 * {@code around()} is EXPLICIT-NO-OP — {@code EmitterDispatch} throws UOE.)
 */
class AdviceFormGrammarTest {

    @Test
    void beforeAdviceEmitsMonitorInvokeAtEntry() {
        EmitPlan plan = new BeforeEmitter().emit(ctx(advice("before")));
        assertEquals(InsertionPoint.BEFORE, plan.insertionPoint(),
                "before() advice inserts the monitor invoke ahead of the matched site");
        assertTrue(hasMonitorInvoke(plan.toInsert()),
                "before() advice must emit the *RuntimeMonitor.*Event(...) invoke");
    }

    @Test
    void afterAdviceEmitsMonitorInvokeAtExit() {
        EmitPlan plan = new AfterEmitter().emit(ctx(advice("after")));
        assertEquals(InsertionPoint.AFTER, plan.insertionPoint(),
                "after() advice inserts the monitor invoke after the matched site");
        assertTrue(hasMonitorInvoke(plan.toInsert()),
                "after() advice must emit the *RuntimeMonitor.*Event(...) invoke");
    }

    @Test
    void afterReturningAdviceEmitsAtExitWithoutInlineScratch() {
        EmitPlan plan = new AfterReturningEmitter().emit(ctxReturning(adviceReturning("aret")));
        assertEquals(InsertionPoint.AFTER, plan.insertionPoint(),
                "after() returning(Id) advice inserts after the matched site");
        assertEquals(0, plan.registers().scratchCount(),
                "after returning routes through the wrapper system; no inline scratch");
        assertTrue(hasMonitorInvoke(plan.toInsert()),
                "after() returning advice must emit the *RuntimeMonitor.*Event(...) invoke");
    }

    private static boolean hasMonitorInvoke(List<BuilderInstruction> ins) {
        for (BuilderInstruction bi : ins) {
            if (bi.getOpcode() == Opcode.INVOKE_STATIC && bi instanceof Instruction35c) {
                MethodReference ref = (MethodReference) ((Instruction35c) bi).getReference();
                if (ref.getDefiningClass().contains("RuntimeMonitor")) {
                    return true;
                }
            }
        }
        return false;
    }

    /** {@code it} resolves to the target register via the {@code target(it)} clause in the expression. */
    private static EmitContext ctx(AdviceDescriptor advice) {
        Map<String, Integer> bindings = new LinkedHashMap<>();
        bindings.put("it", 3);
        Match match = new Match(bindings, 3, null, false);
        TypeResolver resolver = new TypeResolver(List.of("java.util.Iterator"));
        return new EmitContext(advice, match, resolver, "Lmop/MultiSpec_1RuntimeMonitor;");
    }

    /** {@code after returning(result)} binds the synthetic {@code $return} key to the move-result
     *  destination register (the gh56 named-binding contract; mirrors {@code EmitterTestFixtures}). */
    private static EmitContext ctxReturning(AdviceDescriptor advice) {
        Map<String, Integer> bindings = new LinkedHashMap<>();
        bindings.put("result", 3);
        bindings.put("$return", 3);
        Match match = new Match(bindings, 3, null, false);
        TypeResolver resolver = new TypeResolver(List.of("java.util.Iterator", "java.util.Collection"));
        return new EmitContext(advice, match, resolver, "Lmop/MultiSpec_1RuntimeMonitor;");
    }

    private static AdviceDescriptor advice(String position) {
        AdviceDescriptor a = new AdviceDescriptor();
        a.setName(position + "Advice");
        a.setSpecName("SampleSpec");
        a.setPosition(position);
        a.setAround(false);
        a.setParameters(List.of(new ParameterDescriptor("Iterator", "it")));
        a.setExpression("call(public boolean Iterator.hasNext()) && target(it)");
        a.setMonitorCalls(List.of(monitorCall("hasNextEvent", "it")));
        return a;
    }

    private static AdviceDescriptor adviceReturning(String name) {
        AdviceDescriptor a = new AdviceDescriptor();
        a.setName(name);
        a.setSpecName("SampleSpec");
        a.setPosition("after");
        a.setAround(false);
        a.setParameters(List.of());
        a.setReturning(List.of(new ParameterDescriptor("Iterator", "result")));
        a.setExpression("call(public Iterator Collection.iterator())");
        a.setMonitorCalls(List.of(monitorCall("iteratorReturned", "result")));
        return a;
    }

    private static MonitorCallDescriptor monitorCall(String eventId, String... args) {
        MonitorCallDescriptor mc = new MonitorCallDescriptor();
        mc.setMethod("MultiSpec_1RuntimeMonitor." + eventId);
        mc.setSpecName("SampleSpec");
        mc.setEventId(eventId);
        mc.setUniqueId(eventId);
        mc.setArgs(List.of(args));
        return mc;
    }
}
