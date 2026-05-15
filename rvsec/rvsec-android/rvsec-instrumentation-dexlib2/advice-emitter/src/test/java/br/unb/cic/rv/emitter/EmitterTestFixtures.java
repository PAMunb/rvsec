package br.unb.cic.rv.emitter;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.MonitorCallDescriptor;
import br.unb.cic.rv.descriptor.ParameterDescriptor;
import br.unb.cic.rv.pointcut.Match;
import br.unb.cic.rv.pointcut.TypeResolver;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Small builders for {@link AdviceDescriptor} / {@link EmitContext} used by
 * every emitter test. Kept spec-set agnostic — no JCA / Generic bias in the
 * sample shapes.
 */
final class EmitterTestFixtures {

    private EmitterTestFixtures() {}

    static AdviceDescriptor adviceBefore(String name) {
        AdviceDescriptor a = new AdviceDescriptor();
        a.setName(name);
        a.setSpecName("SampleSpec");
        a.setPosition("before");
        a.setAround(false);
        a.setParameters(Arrays.asList(new ParameterDescriptor("Iterator", "it")));
        a.setExpression("call(public boolean Iterator.hasNext()) && target(it)");
        a.setMonitorCalls(List.of(monitorCall("hasNextEvent", "it")));
        return a;
    }

    static AdviceDescriptor adviceAfter(String name) {
        AdviceDescriptor a = new AdviceDescriptor();
        a.setName(name);
        a.setSpecName("SampleSpec");
        a.setPosition("after");
        a.setAround(false);
        a.setParameters(List.of(new ParameterDescriptor("Iterator", "it")));
        a.setExpression("call(public Object Iterator.next()) && target(it)");
        a.setMonitorCalls(List.of(monitorCall("nextEvent", "it")));
        return a;
    }

    static AdviceDescriptor adviceAfterReturning(String name) {
        AdviceDescriptor a = new AdviceDescriptor();
        a.setName(name);
        a.setSpecName("SampleSpec");
        a.setPosition("after");
        a.setAround(false);
        a.setParameters(Collections.emptyList());
        a.setReturning(List.of(new ParameterDescriptor("Iterator", "result")));
        a.setExpression("call(public Iterator Collection.iterator())");
        a.setMonitorCalls(List.of(monitorCall("iteratorReturned", "result")));
        return a;
    }

    static AdviceDescriptor adviceAfterThrowing(String name, String thrownType) {
        AdviceDescriptor a = new AdviceDescriptor();
        a.setName(name);
        a.setSpecName("SampleSpec");
        a.setPosition("after");
        a.setAround(false);
        a.setParameters(Collections.emptyList());
        a.setThrowing(List.of(new ParameterDescriptor(thrownType, "t")));
        a.setExpression("call(public Object Iterator.next()) && target(it)");
        a.setMonitorCalls(List.of(monitorCall("nextThrewEvent", "t")));
        return a;
    }

    static AdviceDescriptor adviceStaticInit(String name, String pattern) {
        AdviceDescriptor a = new AdviceDescriptor();
        a.setName(name);
        a.setSpecName("SampleSpec");
        a.setPosition("before");
        a.setAround(false);
        a.setParameters(Collections.emptyList());
        a.setExpression("staticinitialization(" + pattern + ")");
        a.setMonitorCalls(List.of(monitorCall("classInitEvent")));
        return a;
    }

    static AdviceDescriptor adviceWithIfGuard(String name) {
        AdviceDescriptor a = adviceBefore(name);
        a.setExpression("call(public boolean Iterator.hasNext()) && target(it) && if(it != null)");
        return a;
    }

    static MonitorCallDescriptor monitorCall(String event, String... args) {
        MonitorCallDescriptor mc = new MonitorCallDescriptor();
        mc.setMethod("MultiSpec_1RuntimeMonitor." + event);
        mc.setSpecName("SampleSpec");
        mc.setEventId(event);
        mc.setUniqueId(event);
        mc.setArgs(Arrays.asList(args));
        return mc;
    }

    static EmitContext ctx(AdviceDescriptor advice) {
        Match match = new Match(bindings("it", 3), 3, null, false);
        TypeResolver resolver = new TypeResolver(List.of("java.util.Iterator", "java.util.Collection"));
        return new EmitContext(advice, match, resolver, "Lmop/MultiSpec_1RuntimeMonitor;");
    }

    /**
     * Build a binding map that includes the {@code $return} synthetic key so
     * shape-tests for {@code after returning(...)} advice pass under the
     * gh56 named-binding contract (where an unresolved {@code returning(name)}
     * triggers {@code UnresolvedBindingException}). The matcher populates
     * {@code $return} from the destination of the trailing {@code move-result*}
     * in real code; the fixture mirrors that via a synthetic register.
     */
    static Map<String, Integer> bindings(String name, int reg) {
        Map<String, Integer> m = new LinkedHashMap<>();
        m.put("arg00", reg);
        m.put(name, reg);
        m.put("$return", reg);
        // Catch-handler placeholder for after-throwing shape tests. In real
        // code the catch-block scratch is allocated by RegisterAllocator and
        // RegisterShifter rewrites the placeholder accordingly. Pre-gh56 this
        // came via the literal-0 fallback in registersFor; that fallback is
        // gone (it was the VerifyError vector), so the fixture mirrors the
        // catch-handler convention explicitly.
        m.put("t", 0);
        return m;
    }
}
