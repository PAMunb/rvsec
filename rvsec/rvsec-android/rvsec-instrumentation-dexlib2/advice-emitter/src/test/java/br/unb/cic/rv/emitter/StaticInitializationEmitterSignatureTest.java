package br.unb.cic.rv.emitter;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.MonitorCallDescriptor;
import br.unb.cic.rv.pointcut.Match;
import br.unb.cic.rv.pointcut.TypeResolver;

import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction21c;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction35c;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.iface.reference.TypeReference;
import org.junit.jupiter.api.Test;

import java.util.Collections;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertTrue;

/**
 * Covers the §4.Y signature-delivery path of {@link StaticInitializationEmitter}
 * — the {@code const-class → new-instance → ClassSignature.<init> → invoke-static}
 * sequence for {@code staticinitialization} advice whose monitor call passes the
 * {@code thisJoinPoint.getStaticPart().getSignature()} token. The existing shape
 * test only exercised the generic-invoke fallback (an arg-less {@code classInitEvent},
 * where {@code deliversSignature} is false), leaving 76% of the emitter — including
 * the whole ClassSignature materialisation — untested. A regression in the emitted
 * opcode sequence, register wiring, or the ClassSignature/Signature descriptors
 * would produce bytecode ART rejects at {@code <clinit>} time, uncaught by any
 * other test.
 */
class StaticInitializationEmitterSignatureTest {

    private static final String MONITOR_OWNER = "Lmop/MultiSpec_1RuntimeMonitor;";

    /** A staticinit advice whose single monitor call delivers the Signature token. */
    private static AdviceDescriptor signatureAdvice(String eventFqn) {
        AdviceDescriptor a = new AdviceDescriptor();
        a.setName("si");
        a.setSpecName("SampleSpec");
        a.setPosition("before");
        a.setAround(false);
        a.setParameters(Collections.emptyList());
        a.setExpression("staticinitialization(java.util.ArrayList+)");
        MonitorCallDescriptor mc = new MonitorCallDescriptor();
        mc.setMethod(eventFqn);
        mc.setSpecName("SampleSpec");
        mc.setEventId("e");
        mc.setUniqueId("e");
        mc.setArgs(List.of(StaticInitializationEmitter.SIGNATURE_ARG_TOKEN));
        a.setMonitorCalls(List.of(mc));
        return a;
    }

    private static EmitContext ctxFor(AdviceDescriptor advice, String matchedClassDescriptor) {
        // The signature path reads matchedClassDescriptor, not the match bindings,
        // but EmitContext requires a non-null Match.
        Match match = new Match(java.util.Map.of(), -1, null, false);
        TypeResolver resolver = new TypeResolver(List.of("java.util.ArrayList"));
        return new EmitContext(advice, match, resolver, MONITOR_OWNER, matchedClassDescriptor);
    }

    @Test
    void emitSignatureDeliveryProducesClassSignatureSequence() {
        AdviceDescriptor a = signatureAdvice("MultiSpec_1RuntimeMonitor.ArrayListSpec_clinitEvent");
        EmitPlan plan = new StaticInitializationEmitter().emit(
                ctxFor(a, "Lcom/example/Foo;"));

        assertEquals(InsertionPoint.METHOD_ENTRY, plan.insertionPoint());
        assertEquals(2, plan.registers().scratchCount(),
                "signature delivery needs two scratch regs (const-class + ClassSignature)");

        List<BuilderInstruction> ins = plan.toInsert();
        assertEquals(4, ins.size());

        // [0] const-class v0, <matched declaring type>
        BuilderInstruction21c constClass = assertInstanceOf(BuilderInstruction21c.class, ins.get(0));
        assertEquals(Opcode.CONST_CLASS, constClass.getOpcode());
        assertEquals(0, constClass.getRegisterA());
        assertEquals("Lcom/example/Foo;",
                ((TypeReference) constClass.getReference()).getType(),
                "const-class MUST load the matched <clinit> owner, not the aspect");

        // [1] new-instance v1, Lorg/aspectj/lang/ClassSignature;
        BuilderInstruction21c newInstance = assertInstanceOf(BuilderInstruction21c.class, ins.get(1));
        assertEquals(Opcode.NEW_INSTANCE, newInstance.getOpcode());
        assertEquals(1, newInstance.getRegisterA());
        assertEquals(StaticInitializationEmitter.CLASS_SIGNATURE_DESC,
                ((TypeReference) newInstance.getReference()).getType());

        // [2] invoke-direct {v1, v0}, ClassSignature.<init>(Ljava/lang/Class;)V
        BuilderInstruction35c init = assertInstanceOf(BuilderInstruction35c.class, ins.get(2));
        assertEquals(Opcode.INVOKE_DIRECT, init.getOpcode());
        assertEquals(2, init.getRegisterCount());
        assertEquals(1, init.getRegisterC(), "receiver (the ClassSignature) is vSig=v1");
        assertEquals(0, init.getRegisterD(), "the Class argument is vClass=v0");
        MethodReference initRef = (MethodReference) init.getReference();
        assertEquals(StaticInitializationEmitter.CLASS_SIGNATURE_DESC, initRef.getDefiningClass());
        assertEquals("<init>", initRef.getName());
        assertEquals(List.of("Ljava/lang/Class;"),
                new java.util.ArrayList<>(initRef.getParameterTypes()));

        // [3] invoke-static {v1}, <monitorOwner>.ArrayListSpec_clinitEvent(Signature)V
        BuilderInstruction35c invoke = assertInstanceOf(BuilderInstruction35c.class, ins.get(3));
        assertEquals(Opcode.INVOKE_STATIC, invoke.getOpcode());
        assertEquals(1, invoke.getRegisterCount());
        assertEquals(1, invoke.getRegisterC(), "the Signature passed to the monitor is vSig=v1");
        MethodReference eventRef = (MethodReference) invoke.getReference();
        assertEquals(MONITOR_OWNER, eventRef.getDefiningClass());
        assertEquals("ArrayListSpec_clinitEvent", eventRef.getName());
        assertEquals(List.of(StaticInitializationEmitter.SIGNATURE_DESC),
                new java.util.ArrayList<>(eventRef.getParameterTypes()),
                "the monitor event accepts the Signature interface");
    }

    @Test
    void emitWithoutMatchedClassFailsLoudRatherThanEmitV0() {
        // deliversSignature is true but matchedClassDescriptor is null, so the
        // emitter cannot materialise a ClassSignature and falls through to the
        // generic invoke — which cannot resolve the Signature token as a binding.
        // It MUST fail loud (UnresolvedBindingException, funnelled by DexWeaver
        // to plansSkippedUnresolvedBinding) rather than substitute v0 and emit a
        // malformed monitor invoke.
        AdviceDescriptor a = signatureAdvice("MultiSpec_1RuntimeMonitor.ArrayListSpec_clinitEvent");
        StaticInitializationEmitter emitter = new StaticInitializationEmitter();
        EmitContext ctx = ctxFor(a, null);
        org.junit.jupiter.api.Assertions.assertThrows(
                MonitorInvokeBuilder.UnresolvedBindingException.class,
                () -> emitter.emit(ctx),
                "a signature token with no matched class must be skipped, never v0-substituted");
    }

    @Test
    void deliversSignatureRecognisesExactlyTheToken() {
        assertTrue(StaticInitializationEmitter.deliversSignature(
                signatureAdvice("M.evt")), "the exact token with one arg delivers a signature");

        AdviceDescriptor noArgs = signatureAdvice("M.evt");
        noArgs.getMonitorCalls().get(0).setArgs(Collections.emptyList());
        assertFalse(StaticInitializationEmitter.deliversSignature(noArgs),
                "zero args is the generic (bound/none) shape");

        AdviceDescriptor twoArgs = signatureAdvice("M.evt");
        twoArgs.getMonitorCalls().get(0).setArgs(
                List.of(StaticInitializationEmitter.SIGNATURE_ARG_TOKEN, "extra"));
        assertFalse(StaticInitializationEmitter.deliversSignature(twoArgs),
                "more than one arg is not the signature-delivery shape");

        AdviceDescriptor otherArg = signatureAdvice("M.evt");
        otherArg.getMonitorCalls().get(0).setArgs(List.of("someBoundName"));
        assertFalse(StaticInitializationEmitter.deliversSignature(otherArg),
                "a single non-token arg is a normal bound argument");
    }

    @Test
    void eventMethodNameStripsQualifier() {
        assertEquals("ArrayListSpec_clinitEvent",
                StaticInitializationEmitter.eventMethodName(
                        signatureAdvice("MultiSpec_1RuntimeMonitor.ArrayListSpec_clinitEvent")));
        // No qualifier → the whole name is the event.
        assertEquals("bareEvent",
                StaticInitializationEmitter.eventMethodName(signatureAdvice("bareEvent")));
    }

    @Test
    void signatureDeliveryHelperWiresDistinctRegisters() {
        // Drive the static helper with non-default registers to pin the wiring
        // independently of emit()'s v0/v1 convention: the invoke-direct receiver
        // MUST be vSig and its argument vClass (reversing them constructs the
        // ClassSignature over the wrong reference).
        List<BuilderInstruction> ins = StaticInitializationEmitter.signatureDelivery(
                "Lmop/Owner;", "evt", "Lcom/example/Bar;", /*regClass=*/ 4, /*regSig=*/ 7);
        assertEquals(4, ins.size());
        assertEquals(4, ((BuilderInstruction21c) ins.get(0)).getRegisterA(), "const-class → vClass=v4");
        assertEquals(7, ((BuilderInstruction21c) ins.get(1)).getRegisterA(), "new-instance → vSig=v7");
        BuilderInstruction35c init = (BuilderInstruction35c) ins.get(2);
        assertEquals(7, init.getRegisterC(), "invoke-direct receiver MUST be vSig=v7");
        assertEquals(4, init.getRegisterD(), "invoke-direct argument MUST be vClass=v4");
        assertEquals(7, ((BuilderInstruction35c) ins.get(3)).getRegisterC(),
                "invoke-static passes vSig=v7 as the Signature");
    }
}
