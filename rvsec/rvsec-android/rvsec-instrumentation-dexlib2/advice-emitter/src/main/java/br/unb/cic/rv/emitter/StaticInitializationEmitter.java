package br.unb.cic.rv.emitter;

import br.unb.cic.rv.descriptor.AdviceDescriptor;
import br.unb.cic.rv.descriptor.MonitorCallDescriptor;

import com.android.tools.smali.dexlib2.Opcode;
import com.android.tools.smali.dexlib2.builder.BuilderInstruction;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction21c;
import com.android.tools.smali.dexlib2.builder.instruction.BuilderInstruction35c;
import com.android.tools.smali.dexlib2.iface.reference.MethodReference;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableMethodReference;
import com.android.tools.smali.dexlib2.immutable.reference.ImmutableTypeReference;

import java.util.ArrayList;
import java.util.List;

/**
 * Emits the instructions for {@code staticinitialization(<TypePattern>)}
 * advice.
 *
 * <p>Matches only on a class' {@code <clinit>}. When the class has no
 * {@code <clinit>}, the {@code dex-mutator} executor synthesizes one
 * (advice body + {@code return-void}) before serialization; when a
 * {@code <clinit>} exists, the body is prepended at method entry.
 *
 * <h2>Signature delivery (§4.Y)</h2>
 * The JavaMOP-compiled staticinit advice body invokes
 * {@code thisJoinPoint.getStaticPart().getSignature()} and passes the result
 * to {@code *staticinitEvent(Signature)}. That literal token has no register
 * binding, so routing it through {@link MonitorInvokeBuilder} raises
 * {@link MonitorInvokeBuilder.UnresolvedBindingException} and the site is
 * skipped. This emitter special-cases the token: at the statically-known
 * {@code <clinit>} owner it materialises a {@code org.aspectj.lang.ClassSignature}
 * over the matched class and hands it to the monitor:
 * <pre>
 *   const-class   vC, &lt;DeclaringType&gt;
 *   new-instance  vS, Lorg/aspectj/lang/ClassSignature;
 *   invoke-direct {vS, vC}, ClassSignature.&lt;init&gt;(Ljava/lang/Class;)V
 *   invoke-static {vS}, &lt;monitorOwner&gt;.&lt;event&gt;(Lorg/aspectj/lang/Signature;)V
 * </pre>
 * The {@code ClassSignature} substrate ships in {@code rvsec-core} (already on
 * the dexlib2 packaging allowlist), so no {@code aspectjrt} dependency is
 * re-introduced.
 */
public final class StaticInitializationEmitter implements AdviceEmitter {

    /** DEX descriptor of the fork-free {@code rvsec-core} Signature substrate. */
    public static final String CLASS_SIGNATURE_DESC = "Lorg/aspectj/lang/ClassSignature;";
    /** Descriptor of the {@code Signature} interface the monitor event accepts. */
    public static final String SIGNATURE_DESC = "Lorg/aspectj/lang/Signature;";
    /** The exact AspectJ source token the JavaMOP staticinit body passes. */
    public static final String SIGNATURE_ARG_TOKEN =
            "thisJoinPoint.getStaticPart().getSignature()";

    @Override
    public EmitPlan emit(EmitContext ctx) {
        if (deliversSignature(ctx.advice) && ctx.matchedClassDescriptor != null) {
            // Signature delivery: needs two scratch registers (vC for the
            // const-class, vS for the ClassSignature instance). The executor
            // spills them at the low end before prepending at method entry,
            // so emit against the conventional base v0 (const-class) / v1
            // (new-instance) — see DexWeaver's staticinit pre-pass.
            List<BuilderInstruction> ins = signatureDelivery(
                    ctx.monitorOwnerDescriptor,
                    eventMethodNames(ctx.advice),
                    ctx.matchedClassDescriptor,
                    /*regClass=*/ 0, /*regSig=*/ 1);
            return EmitPlan.of(ins, InsertionPoint.METHOD_ENTRY, RegisterRequest.scratch(2));
        }
        // Non-Signature staticinit advice (e.g. an event with explicit bound
        // args, or none): fall back to the generic monitor invoke.
        List<BuilderInstruction> ins = MonitorInvokeBuilder.buildInvoke(ctx);
        return EmitPlan.of(ins, InsertionPoint.METHOD_ENTRY);
    }

    @Override
    public String kind() { return "staticinitialization"; }

    /**
     * {@code true} when <em>every</em> monitor call this advice carries passes
     * the {@code thisJoinPoint.getStaticPart().getSignature()} token (the
     * generic_new staticinit shape).
     *
     * <p>All of them rather than the first: a fused advice's calls come from
     * events whose position and pointcut coincide, so they agree on the shape,
     * and an advice mixing the token with bound arguments is not a shape this
     * emitter can deliver. Reading only the first would route such an advice
     * down the signature path and silently drop everything after it
     * (INV-INS-104).
     */
    public static boolean deliversSignature(AdviceDescriptor advice) {
        List<MonitorCallDescriptor> calls = advice.getMonitorCalls();
        if (calls == null || calls.isEmpty()) return false;
        for (MonitorCallDescriptor call : calls) {
            if (call.getArgs() == null || call.getArgs().size() != 1) return false;
            if (!SIGNATURE_ARG_TOKEN.equals(call.getArgs().get(0).trim())) return false;
        }
        return true;
    }

    /** The short monitor event method names (after the last {@code .}), in descriptor order. */
    public static List<String> eventMethodNames(AdviceDescriptor advice) {
        List<MonitorCallDescriptor> calls = advice.getMonitorCalls();
        if (calls == null) return List.of();
        List<String> names = new ArrayList<>(calls.size());
        for (MonitorCallDescriptor call : calls) {
            String m = call.getMethod();
            if (m == null) { names.add(""); continue; }
            int dot = m.lastIndexOf('.');
            names.add(dot >= 0 ? m.substring(dot + 1) : m);
        }
        return names;
    }

    /**
     * Build the const-class + new-instance + invoke-direct sequence that
     * materialises a {@code ClassSignature} over
     * {@code declaringTypeDescriptor}, followed by one
     * {@code monitorOwner.<event>(Signature)} invoke per entry of
     * {@code events}, in that order.
     *
     * <p>The three materialisation instructions are emitted once and the
     * resulting instance is shared across the invokes: the events of a fused
     * advice fire at the same join point over the same class, so a second
     * {@code ClassSignature} would be the same object built twice.
     *
     * @param regClass scratch register receiving {@code const-class}; also the
     *                 single argument to {@code ClassSignature.<init>}.
     * @param regSig   scratch register receiving the {@code new-instance};
     *                 the receiver of {@code <init>} and the sole argument of
     *                 each monitor invoke.
     */
    public static List<BuilderInstruction> signatureDelivery(
            String monitorOwner, List<String> events, String declaringTypeDescriptor,
            int regClass, int regSig) {
        List<BuilderInstruction> out = new ArrayList<>(3 + events.size());

        // const-class vC, <DeclaringType>
        out.add(new BuilderInstruction21c(
                Opcode.CONST_CLASS, regClass,
                new ImmutableTypeReference(declaringTypeDescriptor)));

        // new-instance vS, Lorg/aspectj/lang/ClassSignature;
        out.add(new BuilderInstruction21c(
                Opcode.NEW_INSTANCE, regSig,
                new ImmutableTypeReference(CLASS_SIGNATURE_DESC)));

        // invoke-direct {vS, vC}, ClassSignature.<init>(Ljava/lang/Class;)V
        MethodReference initRef = new ImmutableMethodReference(
                CLASS_SIGNATURE_DESC, "<init>",
                List.of("Ljava/lang/Class;"), "V");
        out.add(new BuilderInstruction35c(
                Opcode.INVOKE_DIRECT, /*regCount=*/ 2,
                /*c=*/ regSig, /*d=*/ regClass, /*e=*/ 0, /*f=*/ 0, /*g=*/ 0,
                initRef));

        // invoke-static {vS}, <monitorOwner>.<event>(Lorg/aspectj/lang/Signature;)V
        for (String event : events) {
            MethodReference eventRef = new ImmutableMethodReference(
                    monitorOwner, event, List.of(SIGNATURE_DESC), "V");
            out.add(new BuilderInstruction35c(
                    Opcode.INVOKE_STATIC, /*regCount=*/ 1,
                    /*c=*/ regSig, /*d=*/ 0, /*e=*/ 0, /*f=*/ 0, /*g=*/ 0,
                    eventRef));
        }

        return out;
    }
}
